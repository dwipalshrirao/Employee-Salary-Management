# 02. Backend Specification (Django + Django REST Framework)

Depends on: `00-overview.md` (conventions), `01-database-schema.md` (tables).
Analytics endpoints are specified in `03-analytics-spec.md`.

## 1. Stack and layout
Python 3.12, **Django 5.2 LTS or newer (5.1+ is required for the SQLite options below)** with **Django REST Framework (DRF)**, SQLite, argon2-cffi, drf-spectacular (OpenAPI), pytest and pytest-django. JSON API only: no templates and **no Django admin site** (it is not a feature and would add attack surface). Layout is in `00-overview.md` sec 5.

`make openapi` runs `python manage.py spectacular --file docs/openapi.json --format openapi-json`. Annotate every view with `@extend_schema` (request, response, query parameters, error responses) so the contract is accurate; the frontend tests and MSW handlers are written from it.

Project layout (`backend/`):
```
manage.py  pyproject.toml
config/        settings.py  urls.py  wsgi.py
common/        clock.py  errors.py (AppError classes + exception handler)  serializers.py (StrictSerializer, page query)
               pagination.py  middleware.py (request id, Cache-Control: no-store)
accounts/      models.py (HrUser)  auth.py (SessionAuth)  throttle.py  services.py  views.py  serializers.py  urls.py
catalog/       models.py (CurrencyRate, Country, Department, JobTitle)  selectors.py  services.py (currency rates)
               views.py (lookups, currency rates)  serializers.py  urls.py
employees/     models.py (Employee, SalaryHistory)  selectors.py  views.py  serializers.py  urls.py
               services/ (employees.py  hierarchy.py  bulk_updates.py  history.py)
               management/commands/seed.py   seeding/ (seed package)
analytics/     services.py  bands.py  views.py  serializers.py  urls.py
tests/         unit/  api/  conftest.py  factories.py
```

Layer rules:
- **Views** (DRF `APIView` or generic views): parse input with a serializer, call one service or selector, shape the response. No ORM queries and no business rules in views.
- **Serializers**: validate and shape input and output. Query parameters (filters, sort, paging) are validated by query serializers.
- **Services**: business rules and all writes. Each write method runs in `transaction.atomic()` and takes a `Clock`.
- **Selectors**: read-only queries (list, detail, search, analytics) returning querysets or rows. They use the ORM (bound parameters only).
- **Models**: schema, constraints and indexes (`01-database-schema.md`). No business logic beyond small helpers.

## 2. Configuration
`config/settings.py` reads environment variables (see `00-overview.md` sec 6) through one small helper and fails at start-up if `SECRET_KEY` is missing when `DEBUG` is false. Key settings:

| Setting | Value |
|---|---|
| `INSTALLED_APPS` | `django.contrib.auth`, `contenttypes`, `sessions`, `rest_framework`, `drf_spectacular`, `accounts`, `catalog`, `employees`, `analytics`, `common` (no admin, no messages) |
| `AUTH_USER_MODEL` | `accounts.HrUser` |
| `PASSWORD_HASHERS` | `["django.contrib.auth.hashers.Argon2PasswordHasher"]` |
| `DATABASES["default"]` | SQLite at `DATABASE_PATH`, with `OPTIONS = {"init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;", "transaction_mode": "IMMEDIATE", "timeout": 5}`. Django turns `foreign_keys` on by itself |
| `USE_TZ`, `TIME_ZONE` | `True`, `"UTC"` |
| Sessions | `SESSION_ENGINE` database (default), `SESSION_COOKIE_NAME` from env, `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE="Lax"`, `SESSION_COOKIE_SECURE=COOKIE_SECURE`, `SESSION_COOKIE_AGE=SESSION_ABSOLUTE_HOURS*3600` |
| CSRF | `CSRF_USE_SESSIONS=True` (token lives in the session, no `csrftoken` cookie), `CSRF_HEADER_NAME="HTTP_X_CSRF_TOKEN"` (so the header stays `X-CSRF-Token`), `CSRF_COOKIE_SECURE=COOKIE_SECURE`, `CSRF_TRUSTED_ORIGINS` from env |
| Security headers | `X_FRAME_OPTIONS="DENY"`, `SECURE_CONTENT_TYPE_NOSNIFF=True`, `SECURE_REFERRER_POLICY="no-referrer"`; `common.middleware` adds `Cache-Control: no-store` on `/api/` |
| `REST_FRAMEWORK` | authentication `accounts.auth.SessionAuth`; default permission `IsAuthenticated`; renderer and parser `JSON` only; `EXCEPTION_HANDLER = common.errors.handler`; schema class from drf-spectacular |
| `DEBUG`, `ALLOWED_HOSTS` | from env; `DEBUG` false by default |

Tests override settings with pytest-django's `settings` fixture.

## 3. Database, transactions and time
- Models are described in `01-database-schema.md`. Each app has an initial migration generated with `makemigrations` and reviewed by hand (generated column, constraints, indexes).
- Every service method that writes runs in `with transaction.atomic():`; any exception rolls back. `ATOMIC_REQUESTS` stays off.
- `common/clock.py` defines `Clock.today()` and `Clock.now()` (UTC, timezone-aware) and `get_clock()`. Services receive a clock (default `get_clock()`). Tests use a fixture that installs a fixed clock and restores the system clock afterwards. Do not call `timezone.now()` or `date.today()` outside `clock.py` (a test scans the code base for them).

## 4. Authentication and sessions (F1)

**Model.** Django's built-in session framework (database backend, table `django_session`) with a custom user model `HrUser` (email login, Argon2 passwords). The cookie holds the random session key. Django stores the session key in the database as is; it does not hash it. This is an accepted trade-off: anyone who can read the database already has all the data, and hashing would need a custom session backend.

**Login** `POST /api/auth/login` (view with `authentication_classes = []` and `permission_classes = [AllowAny]`)
1. JSON only (the view accepts only the JSON parser, so other content types are rejected). DRF enforces CSRF only for authenticated requests, so login is exempt; it relies on `SameSite=Lax` plus the JSON-only rule.
2. Check the login throttle for `(client_ip, lower(email))`. It counts **failed** attempts in Django's cache; after `LOGIN_MAX_FAILURES` failures within `LOGIN_WINDOW_MINUTES` the view returns 429 `rate_limited` with `Retry-After`. The local-memory cache works for one process; several workers would need a shared cache (documented limit).
3. `authenticate()` with Django's `ModelBackend`. The user manager's `get_by_natural_key` looks up the email with `iexact`. A wrong password and an unknown email give the same 401 `Invalid email or password` (Django also runs a dummy hash for unknown users to keep timing similar). Inactive users cannot log in.
4. On success call `login(request, user)`. Django issues a **new session key** at login (prevents session fixation). Store `login_at` and `last_seen_at` (from the `Clock`) in the session and clear the failure counter.
5. Cookie flags come from settings (`HttpOnly`, `SameSite=Lax`, `Secure` when enabled).
6. Return `200 { "user": {id, email, full_name}, "csrf_token": get_token(request) }`.

**Current user** `GET /api/auth/me`: returns the same body when the session is valid, otherwise 401.

**Logout** `POST /api/auth/logout` (CSRF enforced): `logout(request)` flushes the session; the cookie is cleared; 204.

**Session validation** (`accounts.auth.SessionAuth`, a subclass of DRF `SessionAuthentication`, used by every protected view):
- After normal session authentication, reject (401) and flush the session when `login_at` is older than `SESSION_ABSOLUTE_HOURS`, or `last_seen_at` is older than `SESSION_IDLE_MINUTES` (both compared with the `Clock`), or the user is inactive.
- Update `last_seen_at` at most once per minute to avoid a write on every request.
- `authenticate_header()` returns `"Session"`, so an unauthenticated request gets **401** (without it DRF answers 403).

**CSRF.** DRF's `SessionAuthentication` enforces CSRF on `POST`, `PUT`, `PATCH` and `DELETE` for session-authenticated requests. With `CSRF_USE_SESSIONS=True` and `CSRF_HEADER_NAME="HTTP_X_CSRF_TOKEN"`, the frontend keeps sending `X-CSRF-Token` with the value returned by login and `me`; the contract is unchanged. A failure returns 403 `csrf_failed` (the exception handler maps DRF's "CSRF Failed" error). Behind HTTPS and a proxy, set `CSRF_TRUSTED_ORIGINS`, because Django checks the Origin or Referer header on secure requests.

**Cleanup.** Run `python manage.py clearsessions` at start-up (and on a schedule if available). Expired sessions are also rejected even if they have not been cleared.

## 5. API contract

All routes are under `/api`. All except `/api/health` and `POST /api/auth/login` require a valid session (DRF default permission `IsAuthenticated`; those two views use `AllowAny`). All responses are JSON and carry `Cache-Control: no-store`.

### 5.1 Conventions
Pagination, errors and money are defined in `00-overview.md` sec 6. Unknown query parameters are ignored; invalid values return 422.

### 5.2 Auth, health, lookups

| Method and path | Purpose | Success |
|---|---|---|
| `POST /api/auth/login` | Sign in | 200 |
| `POST /api/auth/logout` | Sign out | 204 |
| `GET /api/auth/me` | Current user and CSRF token | 200 |
| `GET /api/health` | Liveness (no auth) | 200 `{"status":"ok"}` |
| `GET /api/lookups` | Reference data | 200 |

`GET /api/lookups` response (cache on the client; `Cache-Control: private, max-age=60`):
```json
{
  "countries":   [{ "code": "IN", "name": "India", "currency_code": "INR" }],
  "departments": [{ "id": 1, "name": "Engineering" }],
  "job_titles":  [{ "id": 1, "name": "Software Engineer", "level": 2 }],
  "currency_rates": [{ "currency_code": "INR", "rate_per_usd": 83.0, "updated_at": "2026-01-01T00:00:00Z" }]
}
```

### 5.3 Employees

| Method and path | Purpose | Success |
|---|---|---|
| `GET /api/employees` | List with filters, sort, pagination | 200 |
| `POST /api/employees` | Create (writes `hire` history row) | 201 |
| `GET /api/employees/{id}` | Detail | 200 |
| `PATCH /api/employees/{id}` | Partial update (writes history if pay changed) | 200 |
| `POST /api/employees/{id}/deactivate` | Soft delete | 200 |
| `POST /api/employees/{id}/reactivate` | Restore | 200 |
| `GET /api/employees/{id}/history` | Salary history, newest first | 200 |
| `GET /api/employees/{id}/direct-reports` | Paginated direct reports | 200 |

**List query parameters**

| Param | Type | Notes |
|---|---|---|
| `q` | string, max 100 | Matches name or email (case-insensitive contains) |
| `country_code` | string | Exact |
| `department_id` | int | Exact |
| `job_title_id` | int | Exact |
| `manager_id` | int | Direct reports of this manager |
| `status` | `active` (default), `inactive`, `all` | |
| `sort_by` | `full_name` (default), `email`, `hire_date`, `base_salary`, `total_comp`, `department`, `job_title`, `country` | Whitelist mapped to columns in code; never pass user text into `ORDER BY` |
| `sort_dir` | `asc` (default), `desc` | Secondary sort is always `id` for stable pages |
| `page`, `page_size` | int | See conventions |

**List item**
```json
{
  "id": 42, "full_name": "Asha Patel", "email": "asha.patel.42@acme.example",
  "department": {"id": 1, "name": "Engineering"},
  "job_title": {"id": 3, "name": "Senior Software Engineer"},
  "country": {"code": "IN", "name": "India"},
  "manager": {"id": 7, "full_name": "Ravi Shah"},
  "hire_date": "2021-04-12", "status": "active",
  "base_salary_cents": 4500000, "bonus_cents": 450000, "allowances_cents": 180000,
  "total_comp_cents": 5130000
}
```
`manager` is `null` for the top of the hierarchy. Build the list with **one joined query plus one count query** (no per-row queries).

**Detail** adds `direct_reports_count` and `local` (see 5.4), plus `created_at`, `updated_at`.

**Create body**
```json
{ "full_name": "...", "email": "...", "department_id": 1, "job_title_id": 3, "country_code": "IN",
  "manager_id": 7, "hire_date": "2026-10-01",
  "base_salary_cents": 4500000, "bonus_cents": 0, "allowances_cents": 0 }
```

**Patch body**: any subset of `full_name, email, department_id, job_title_id, country_code, manager_id (nullable), hire_date, base_salary_cents, bonus_cents, allowances_cents`, plus optional `change_reason` (max 200, used only when pay changes; default "Manual edit"). With a partial serializer (`partial=True`), check `key in validated_data` so an explicit `"manager_id": null` (remove manager) differs from an omitted field. `status` cannot be patched.

**History item**
```json
{ "id": 9, "effective_date": "2026-10-31", "change_type": "bulk_update", "reason": "FY27 raise",
  "batch_id": "6f1c...", "created_at": "...",
  "new":      { "base_salary_cents": 4725000, "bonus_cents": 450000, "allowances_cents": 180000, "total_comp_cents": 5355000 },
  "previous": { "base_salary_cents": 4500000, "bonus_cents": 450000, "allowances_cents": 180000, "total_comp_cents": 5130000 } }
```
`previous` is `null` for `hire`. Totals are computed in the service.

### 5.4 Local currency (display only)
Employee detail includes:
```json
"local": { "currency_code": "INR", "rate_per_usd": 83.0,
           "base_salary_cents": 373500000, "bonus_cents": 37350000,
           "allowances_cents": 14940000, "total_comp_cents": 425790000 }
```
Amounts are in local minor units: `round(usd_cents * rate_per_usd)` using round-half-up on the product. The country's currency comes from `countries.currency_code`. These values are never stored and never used in analytics.

### 5.5 Bulk update (F7)

| Method and path | Purpose |
|---|---|
| `POST /api/bulk-updates/preview` | Calculate the effect; changes nothing |
| `POST /api/bulk-updates/apply` | Apply in one transaction |

Request (both). Example: add $1,200 per year to the allowances of one department in one country.
```json
{ "filter": { "country_code": "IN", "department_id": 1, "job_title_id": null, "manager_id": null },
  "apply_to_all": false,
  "component": "allowances",
  "mode": "fixed_amount",
  "percentage": null,
  "amount_cents": 120000 }
```
`apply` also requires `"expected_count": 123` and `"reason": "FY27 team allowance"` (1 to 200 chars).

Rules:
- Only **active** employees are matched. Each request changes **one component**: `component` is `base`, `bonus` or `allowances`. The other two components stay as they are.
- `mode = "percent"`: `percentage` is required (decimal with at most 2 places, between `BULK_MIN_PERCENT` and `BULK_MAX_PERCENT`, not 0) and `amount_cents` must be absent. Convert to integer basis points (`bp = round(percentage * 100)`) before any math. New value = `CAST(ROUND(current * (10000 + bp) / 10000.0) AS INTEGER)`, rounding half away from zero (SQLite `ROUND`).
- `mode = "fixed_amount"`: `amount_cents` is required (integer from 1 to `MAX_AMOUNT_CENTS`, annual, USD, always **added**) and `percentage` must be absent. New value = `current + amount_cents`. To reduce a component use `percent` mode with a negative percentage.
- A request that sends the wrong combination (for example `percent` mode with `amount_cents`) returns 422.
- All amounts are **annual**. A monthly amount is entered as 12 times its value (for example $100 per month is `120000`). A bulk update changes the current annual amount **immediately**. One-off payments, month-specific payments and future-dated changes are not modelled.
- **Affected employees** are matched employees whose value would actually change. For example, a percentage change of a bonus that is 0 changes nothing, so those employees are not counted and get no history row.
- A request with an empty filter and `apply_to_all=false` is rejected (422). This protects against an accidental organisation-wide change.
- If any resulting value would exceed `MAX_AMOUNT_CENTS`, reject the request with 422 `result_too_large` and change nothing. A base salary never goes below 1 cent.

Preview response:
```json
{ "component": "allowances", "mode": "fixed_amount", "affected_count": 123,
  "sum_before_cents": 0, "sum_after_cents": 0, "sum_delta_cents": 0,
  "sample": [ { "id": 42, "full_name": "...", "before_cents": 0, "after_cents": 0 } ] }
```
The sums are totals of the chosen component over the affected employees. `sample` has up to 10 employees, ordered by id. If `affected_count` is 0, return 200 with zeros and an empty sample.

Apply response: `{ "batch_id": "...", "component": "allowances", "affected_count": 123, "sum_delta_cents": 0 }`. If the number of affected employees at apply time differs from `expected_count`, change nothing and return 409 `stale_preview`.

### 5.6 Analytics
See `03-analytics-spec.md`. All under `/api/analytics/...`.

### 5.7 Salary history search (F10)

| Method and path | Purpose | Success |
|---|---|---|
| `GET /api/salary-history` | Every pay change across all employees, with search and filters | 200 |

Query parameters:

| Param | Type | Notes |
|---|---|---|
| `employee` | string, max 100 | Case-insensitive contains match on the employee's full name or email |
| `reason` | string, max 100 | Case-insensitive contains match on the reason |
| `change_type` | `hire`, `manual_edit`, `bulk_update` | Exact |
| `date_from`, `date_to` | `YYYY-MM-DD` | Inclusive range on `effective_date`; `date_from` later than `date_to` returns 422 |
| `batch_id` | string | Exact; used to show every row of one bulk update |
| `sort_by` | `effective_date` (default), `employee`, `change_type` | Whitelist mapped to columns in code |
| `sort_dir` | `desc` (default), `asc` | Ties break by history `id` in the same direction |
| `page`, `page_size` | int | See conventions |

Item (the same `new` and `previous` blocks as the per-employee history in 5.3, plus the employee):
```json
{ "id": 9,
  "employee": { "id": 42, "full_name": "Asha Patel", "email": "asha.patel.42@acme.example" },
  "effective_date": "2026-10-31", "change_type": "bulk_update", "reason": "FY27 raise", "batch_id": "6f1c...",
  "new":      { "base_salary_cents": 4725000, "bonus_cents": 450000, "allowances_cents": 180000, "total_comp_cents": 5355000 },
  "previous": { "base_salary_cents": 4500000, "bonus_cents": 450000, "allowances_cents": 180000, "total_comp_cents": 5130000 } }
```
Notes:
- History of inactive employees is included.
- The acting HR user is not recorded and not returned (audit trail is out of scope).
- Build the page with **one joined select plus one count query** (no per-row queries). Escape `%` and `_` in search text and use `LIKE ... ESCAPE`.

### 5.8 Currency rates (F11, API only, no screen)

HR does not need to change rates in the app, so there is no UI for this. The endpoints exist so rates can be maintained through the API (for example with `curl` or the generated OpenAPI docs). They use the same session and CSRF rules as every other route.

| Method and path | Purpose | Success |
|---|---|---|
| `GET /api/currency-rates` | List all rates, sorted by code | 200 |
| `GET /api/currency-rates/{code}` | One rate | 200 |
| `POST /api/currency-rates` | Create a currency | 201 |
| `PATCH /api/currency-rates/{code}` | Change the rate | 200 |
| `DELETE /api/currency-rates/{code}` | Delete a currency | 204 |

Item:
```json
{ "currency_code": "EUR", "rate_per_usd": 0.92, "updated_at": "2026-11-01T09:30:00Z", "country_codes": ["DE"] }
```
`country_codes` lists the countries that use the currency.

Create body: `{ "currency_code": "EUR", "rate_per_usd": 0.92 }`. Patch body: `{ "rate_per_usd": 0.93 }` (the code cannot change, because countries refer to it).

Rules:
- `currency_code` is exactly three uppercase letters (`^[A-Z]{3}$`); anything else returns 422. A code that already exists returns 409.
- `rate_per_usd` means local units per 1 USD. It must be a finite number greater than 0 and at most 1,000,000.
- **USD is the base currency** (all stored amounts are USD): its rate is fixed at 1 and cannot be changed (422) or deleted (409).
- A currency that any country uses cannot be deleted (409, the message lists the country codes).
- Updating a rate sets `updated_at` from the `Clock`. It changes only the local-currency amounts shown from then on; stored USD amounts are never touched.
- Rate changes are not kept in a history (audit trail is out of scope); only `updated_at` is stored.
- `GET /api/lookups` returns the current rates, so the app shows a changed rate after the lookup cache expires (up to one minute) or on reload.
- Countries are seeded reference data. A new currency only has an effect once a country refers to it, and there is no endpoint to add countries.

Example (no screen, so use the API directly):
```
# 1. Sign in; the cookie jar keeps the session, the response contains csrf_token
curl -c jar.txt -H "Content-Type: application/json" \
     -d '{"email":"<hr email>","password":"<password>"}' https://<host>/api/auth/login
# 2. Change a rate, sending the cookie and the CSRF token from step 1
curl -b jar.txt -X PATCH -H "Content-Type: application/json" -H "X-CSRF-Token: <csrf_token>" \
     -d '{"rate_per_usd": 0.93}' https://<host>/api/currency-rates/EUR
```

## 6. Validation rules (DRF serializers)

| Field | Rule |
|---|---|
| `full_name` | 1 to 120 chars after trimming |
| `email` | Valid email, max 254, stored as given, compared case-insensitively |
| `*_cents` | Integers; `base_salary_cents` 1 to `MAX_AMOUNT_CENTS`; bonus and allowances 0 to `MAX_AMOUNT_CENTS` |
| `hire_date` | Valid date, not later than today |
| `country_code` | Exists in `countries` |
| `department_id`, `job_title_id` | Exist |
| `manager_id` | Exists, active, not the employee itself, no cycle (see 7.2) |
| `change_reason`, `reason` | Trimmed, max 200 |
| `percentage` | See 5.5 |
| `q` | Max 100 chars; Django's `icontains` escapes `%` and `_` automatically (covered by a test) |
| `employee`, `reason` (history search) | Max 100 chars each; matched with `icontains` like `q` |
| `date_from`, `date_to` | Valid dates; `date_from` not later than `date_to` |
| `currency_code` | Exactly three uppercase letters |
| `rate_per_usd` | Finite number greater than 0, at most 1,000,000 |

All write serializers inherit `StrictSerializer`, which rejects unknown fields (422), so clients cannot set `status`, ids or totals. List endpoints use a shared page query serializer: `page_size` above `MAX_PAGE_SIZE` returns 422 (it is not clamped). Cross-field and database-backed rules are checked in services and return 422 (invalid value) or 409 (conflicts with current state, such as a duplicate email).

## 7. Services

### 7.1 EmployeeService
- **create(data)**: validate lookups and manager; insert employee; insert a `hire` history row with `effective_date = hire_date`, reason "New hire" and `prev_*` null; everything runs in one `transaction.atomic()` block. Duplicate email returns 409 (catch `IntegrityError` from the case-insensitive unique constraint).
- **update(id, patch)**: load or 404; validate any changed lookup or manager; apply; if any of the three pay fields changed, insert one `manual_edit` history row (`effective_date = today`, previous values from before the change); set `updated_at`; run all of this in one `transaction.atomic()` block. A patch that changes nothing returns the current employee and writes nothing.
- **deactivate(id)**: 409 if the employee has active direct reports (message names the count); set `status='inactive'`.
- **reactivate(id)**: 409 if the manager exists and is inactive; set `status='active'`.
- **list(filters, sort, page)** and **get(id)** as in 5.3.
- **history(id)**: ordered by `effective_date DESC, id DESC`; build `new` and `previous` blocks.

### 7.2 HierarchyService
- `validate_manager(employee_id | None, manager_id)`: manager exists, active, not self, no cycle (an iterative walk up `manager_id` with a visited set and a depth guard; the recursive SQL in `01` sec 6 is the equivalent alternative). Used by create (no employee id yet, so only existence and active checks) and update.
- `direct_reports(manager_id, status, page)` and `active_report_count(manager_id)`.

### 7.3 BulkUpdateService
- **Component and expression.** Map `component` to a model field through a whitelist (`base` to `base_salary_cents`, `bonus` to `bonus_cents`, `allowances` to `allowances_cents`); never use client text as a field name. Build the new-value expression from `mode` with ORM expressions: percent gives `Cast(Round(F(col) * (10000 + bp) / 10000.0), IntegerField())` (SQLite `ROUND` rounds half away from zero), fixed amount gives `F(col) + amount`.
- **Matching set.** A queryset using the shared filter builder (same as the list), `status='active'`, annotated with `new_value` and filtered with `~Q(new_value=F(col))` so unchanged rows are excluded.
- **preview(request)**: one `aggregate(count, Sum(col), Sum(new_value), Max(new_value))` over the matching set, plus one limited query for the sample. Reject with `result_too_large` when the maximum new value exceeds `MAX_AMOUNT_CENTS`.
- **apply(request, expected_count, reason)**, inside one `transaction.atomic()` (the database connection uses `IMMEDIATE` transactions, so the write lock is taken up front):
  1. Run the aggregate; if the count differs from `expected_count`, roll back and raise `stale_preview`; if the maximum is too large, roll back and raise `result_too_large`.
  2. Generate `batch_id = uuid4()`.
  3. Read the matching rows once with `values(...)` plus the annotated `new_value` (the new value always comes from the database expression, never from Python math). Build one `SalaryHistory` per row (new value for the chosen component, current values for the other two, **previous** values for all three, `change_type='bulk_update'`, `effective_date=today`, `batch_id`, `reason`) and insert them with `bulk_create(batch_size=1000)`.
  4. `matching_set.update(<col>=<new_value expression>, updated_at=now)`. Run it after the history insert, with the same matching set (still valid, because the insert did not change `employees`).
  5. Verify the updated row count equals the number of history rows and `expected_count`; otherwise roll back.
  For 10,000 rows this is two statements plus batched inserts and takes well under a second. Never loop over employees issuing one query per employee.

### 7.4 HistoryService (F10)
- **search(filters, sort, page)**: one queryset over `SalaryHistory` with `select_related("employee")` and these conditions when present: `Q(employee__full_name__icontains=p) | Q(employee__email__icontains=p)` for `employee`, `reason__icontains=r`, `change_type=t`, `effective_date__range=(from, to)` (inclusive), `batch_id=b`. `icontains` escapes `%` and `_` for you. `sort_by` maps through a whitelist (`effective_date`, `employee` to `employee__full_name`, `change_type`) with `id` as the tie-breaker in the same direction. A second `count()` on the same filter gives `total`.
- Build the `new` and `previous` blocks with the same helper the per-employee history uses (totals computed in code, no second query).

### 7.5 CurrencyRateService (F11)
- **list()**: all rows ordered by code, with `country_codes` from one grouped query over `countries`.
- **get(code)**: 404 if missing.
- **create(code, rate)**: validate format and range; 409 if the code exists; `updated_at` from the `Clock`.
- **update_rate(code, rate)**: 404 if missing; 422 for `USD`; validate range; set `rate_per_usd` and `updated_at`.
- **delete(code)**: 404 if missing; 409 for `USD`; 409 if any country uses it (message lists the codes).
- Routes are thin: parse, call the service, return the item.

## 8. Error handling
- `common/errors.py` defines the `AppError` subclasses (`NotFoundError`, `ConflictError`, `StaleCountError`, `ResultTooLargeError`, `RateLimitedError`) and the DRF exception handler. The handler returns the standard shape from `00-overview.md` sec 6:
  - `AppError` subclasses and DRF `ValidationError` (DRF's default 400 is changed to **422** `validation_error`, with `details` as `{field, message}` pairs);
  - `NotAuthenticated` and `AuthenticationFailed` become 401 `unauthorized`;
  - a DRF permission error whose message starts with "CSRF Failed" becomes 403 `csrf_failed`;
  - `Http404` and `NotFound` become 404 `not_found`; unsupported content types become 422 `validation_error`.
- Django's own 404 and 500 handlers (`handler404`, `handler500`) return the same JSON shape. With `DEBUG` false, a 500 returns `internal_error` with a request id and a generic message; stack traces go to logs only.

## 9. Security checklist (each item has a test)
- Every route except health and login requires a session (default permission `IsAuthenticated`; a parametrized test walks `urlpatterns`).
- State-changing routes require a valid CSRF token in `X-CSRF-Token`.
- Passwords use Argon2 through Django's hasher and are never logged or returned. Session keys and CSRF tokens are never logged. (Session keys are stored unhashed by Django; see sec 4.)
- Login: generic error, failed-attempt throttle, new session key per login.
- Cookie flags: `HttpOnly`, `SameSite=Lax`, `Secure` when enabled.
- SQL: ORM expressions or bound parameters only; `sort_by`, `component` and `measure` are whitelists; `icontains` escapes wildcard characters.
- Write serializers reject unknown fields (`StrictSerializer`), so clients cannot set `status`, ids or totals.
- Responses never include `password` or session data.
- Security headers on every response: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`; `Cache-Control: no-store` on API routes.
- No Django admin site, no templates, no browsable API renderer (JSON renderer only).
- CORS is not enabled (same origin). If it is ever needed, use `django-cors-headers` with exact origins and credentials, never `*`.
- `DEBUG=false`, `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` set in any deployed environment; `python manage.py check --deploy` is clean.
- Secrets (`SECRET_KEY`, passwords) only from the environment; `.env` is gitignored.

## 10. Performance
- List: one queryset with `select_related` for department, job title, country and manager, sliced for the page, plus one `count()` on the same filter. Page size capped at 100.
- Avoid N+1: the list and history queries must use `select_related`; a test asserts the number of queries with `django_assert_num_queries`.
- Bulk update and seed use set-based expressions and `bulk_create`.
- Measure on the seeded database with the perf smoke test (`05` sec 2) before declaring the list target met.

## 11. Logging
Request-id middleware (`common/middleware.py`); one structured log line per request (method, path, status, duration ms, user id). No bodies, no amounts, no tokens.
