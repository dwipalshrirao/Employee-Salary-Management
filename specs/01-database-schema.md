# 01. Database Schema (SQLite)

## 1. Design principles
1. **Integer money.** All amounts are integer cents in USD. Floating-point numbers cannot store most decimal values exactly, so sums and percentage raises over 10,000 rows could drift; integers are exact, and SQLite has no real decimal type.
2. **Lookup tables** for country, department and job title. Filters use small integer keys, dropdowns come from one source, and `GROUP BY` runs on integers.
3. **Current state on `employees`, history in `salary_history`.** Reads of the current salary (list, analytics) never touch history. History is append-only.
4. **Derived total is stored.** `total_comp_cents` is a stored generated column, so analytics and sorting use one column and stay consistent.
5. **Soft delete only.** Employees are deactivated, never deleted, so history and reporting lines stay intact.
6. **Constraints in the database** for anything checkable on a single row (positive amounts, valid status, no self-manager). Cross-row rules live in services and are tested.
7. **Few, purposeful indexes.** Each index below names the query it serves. Extra indexes slow the bulk update and seed.

## 2. ER diagram

```mermaid
erDiagram
  currency_rates ||--o{ countries : prices
  countries ||--o{ employees : located_in
  departments ||--o{ employees : belongs_to
  job_titles ||--o{ employees : holds
  employees ||--o{ employees : manages
  employees ||--o{ salary_history : has

  hr_users { int id PK  text email UK  text password_hash  int is_active }
  currency_rates { text currency_code PK  real rate_per_usd  text updated_at }
  countries { text code PK  text name  text currency_code FK }
  departments { int id PK  text name UK }
  job_titles { int id PK  text name UK  int level }
  employees { int id PK  text email UK  int department_id FK  int job_title_id FK  text country_code FK  int manager_id FK  int base_salary_cents  int bonus_cents  int allowances_cents  int total_comp_cents  text status }
  salary_history { int id PK  int employee_id FK  text effective_date  text change_type  text batch_id  int base_salary_cents }
```

## 3. Tables (DDL)

The SQL below is the target schema. In Django it is produced by the models and migrations (see the implementation notes after the DDL). The `sessions` table is Django's built-in `django_session` (session key, data, expiry), so it is not defined here, and the `hr_users` password column is Django's `password` field.

Timestamps are UTC ISO 8601 text. Dates are `YYYY-MM-DD` text. SQLite compares both correctly as strings.

```sql
CREATE TABLE hr_users (
  id            INTEGER PRIMARY KEY,
  email         TEXT NOT NULL COLLATE NOCASE UNIQUE,
  full_name     TEXT NOT NULL,
  password      TEXT NOT NULL,              -- Django format: algorithm$salt$hash (Argon2)
  is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  created_at    TEXT NOT NULL
);

CREATE TABLE currency_rates (
  currency_code TEXT PRIMARY KEY CHECK (length(currency_code) = 3),
  rate_per_usd  REAL NOT NULL CHECK (rate_per_usd > 0),   -- local units per 1 USD
  updated_at    TEXT NOT NULL
);

CREATE TABLE countries (
  code          TEXT PRIMARY KEY CHECK (length(code) = 2),
  name          TEXT NOT NULL UNIQUE,
  currency_code TEXT NOT NULL REFERENCES currency_rates(currency_code)
);

CREATE TABLE departments (
  id   INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE job_titles (
  id    INTEGER PRIMARY KEY,
  name  TEXT NOT NULL UNIQUE,
  level INTEGER NOT NULL CHECK (level BETWEEN 1 AND 7)
);

CREATE TABLE employees (
  id                INTEGER PRIMARY KEY,
  full_name         TEXT NOT NULL,
  email             TEXT NOT NULL COLLATE NOCASE UNIQUE,
  department_id     INTEGER NOT NULL REFERENCES departments(id),
  job_title_id      INTEGER NOT NULL REFERENCES job_titles(id),
  country_code      TEXT    NOT NULL REFERENCES countries(code),
  manager_id        INTEGER REFERENCES employees(id),
  hire_date         TEXT NOT NULL,
  status            TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
  base_salary_cents INTEGER NOT NULL CHECK (base_salary_cents > 0),
  bonus_cents       INTEGER NOT NULL DEFAULT 0 CHECK (bonus_cents >= 0),
  allowances_cents  INTEGER NOT NULL DEFAULT 0 CHECK (allowances_cents >= 0),
  total_comp_cents  INTEGER GENERATED ALWAYS AS
                      (base_salary_cents + bonus_cents + allowances_cents) STORED,
  created_at        TEXT NOT NULL,
  updated_at        TEXT NOT NULL,
  CHECK (manager_id IS NULL OR manager_id <> id)
);

CREATE TABLE salary_history (
  id                     INTEGER PRIMARY KEY,
  employee_id            INTEGER NOT NULL REFERENCES employees(id),
  effective_date         TEXT NOT NULL,
  change_type            TEXT NOT NULL CHECK (change_type IN ('hire', 'manual_edit', 'bulk_update')),
  reason                 TEXT,
  batch_id               TEXT,                       -- uuid, set for bulk_update rows only
  base_salary_cents      INTEGER NOT NULL,           -- values AFTER the change
  bonus_cents            INTEGER NOT NULL,
  allowances_cents       INTEGER NOT NULL,
  prev_base_salary_cents INTEGER,                    -- values BEFORE the change; NULL for 'hire'
  prev_bonus_cents       INTEGER,
  prev_allowances_cents  INTEGER,
  created_at             TEXT NOT NULL
);
```

Implementation notes (Django):
- **Models and tables.** Apps `accounts` (`HrUser`, table `hr_users`, `USERNAME_FIELD = "email"`, built on `AbstractBaseUser` with `full_name`, `is_active`, `created_at`), `catalog` (`CurrencyRate`, `Country`, `Department`, `JobTitle`) and `employees` (`Employee`, `SalaryHistory`). Set `db_table` explicitly so the table names match the DDL.
- **Money** is `BigIntegerField`. **Dates** are `DateField`; **timestamps** are timezone-aware `DateTimeField` (`USE_TZ=True`). Django stores them as UTC text and the API returns ISO 8601 with `Z`. `rate_per_usd` is a `FloatField`.
- **Stored total.** `total_comp_cents = GeneratedField(expression=F("base_salary_cents") + F("bonus_cents") + F("allowances_cents"), output_field=BigIntegerField(), db_persist=True)`. Never write it. It must be in the initial `CreateModel` (a stored generated column cannot be added later in SQLite).
- **Constraints** (in each model's `Meta.constraints`): `CheckConstraint` for positive base, non-negative bonus and allowances, valid `status`, valid `change_type`, `manager_id <> id`, `level` between 1 and 7, and rate greater than 0; `UniqueConstraint(Lower("email"))` for case-insensitive unique email on `employees` and `hr_users`.
- **Indexes** are declared in `Meta.indexes` with the names in sec 4, for example `models.Index(fields=["status", "country_code"], name="idx_emp_status_country")` and `models.Index(Lower("full_name"), name="idx_emp_name")` (sort by name with `Lower("full_name")` so the index is used). The history indexes use descending fields (`fields=["-effective_date", "-id"]`), and `idx_history_batch` is a partial index (`condition=Q(batch_id__isnull=False)`).
- **Foreign keys** use `on_delete=models.PROTECT` (employees are never hard-deleted).
- Money upper bound is enforced in the DRF serializers (`MAX_AMOUNT_CENTS = 1_000_000_000`, i.e. $10M), not in SQL.
- `change_type` and `status` are text with CHECK constraints (readable in the DB, no extra table).

## 4. Indexes

| Index | Columns | Serves |
|---|---|---|
| (unique) | `employees.email` NOCASE | Duplicate check, lookup by email |
| `idx_emp_status_country` | `(status, country_code)` | List filtered by status and country; analytics `WHERE status='active'` grouped by country |
| `idx_emp_status_dept` | `(status, department_id)` | List filtered by department; analytics by department |
| `idx_emp_title` | `(job_title_id)` | Filter and analytics by job title; outlier peer groups |
| `idx_emp_manager` | `(manager_id)` | Direct reports, "has active reports" check, manager filter, team view |
| `idx_emp_name` | `(full_name COLLATE NOCASE)` | Sorting by name |
| `idx_history_employee_effective` | `salary_history(employee_id, effective_date DESC, id DESC)` | Employee history timeline, latest row |
| `idx_history_batch` | `salary_history(batch_id) WHERE batch_id IS NOT NULL` | Look up all rows of one bulk update |
| `idx_history_effective` | `salary_history(effective_date DESC, id DESC)` | History page: default sort and date-range filter across all employees |

Notes:
- **Search (`q`)** uses `LIKE '%term%'` on name and email. That is a scan, which is about 10 to 20 ms on 10,000 rows, so it is acceptable. At larger scale use SQLite FTS5 or Postgres trigram indexes.
- **History search** (`employee`, `reason`) also uses `LIKE '%term%'`: reasons are scanned on about 30,000 history rows and employee names through the join. That is a few milliseconds to a few tens of milliseconds, so it is acceptable. At larger scale use FTS5 or trigram indexes.
- **Sorting by `total_comp_cents`** on 10,000 rows is an in-memory sort and is fast; it does not need its own index.
- **Analytics** aggregate over active employees. At this size a scan or the status indexes are enough. Do not add covering indexes unless a measured query misses its target.

## 5. Integrity rules and invariants

Enforced in the database (CHECK, FK, UNIQUE): positive base salary, non-negative bonus/allowances, valid status, no self-manager, unique email (case-insensitive), valid country/department/title.

Enforced in services (cross-row), each with a unit test:
1. **Current = latest history.** After every write, `employees.{base,bonus,allowances}` equal the newest `salary_history` row (highest `effective_date`, then `id`). Create writes a `hire` row; manual edit and bulk update write one row per changed employee. Both happen in the same transaction as the employee update.
2. **No backdating.** Every change takes effect today (from the injected `Clock`). The seed script is the only code that writes past dates.
3. **No cycles.** A manager assignment must not create a loop (query in section 6).
4. **Manager must be active.** An employee's manager must exist and be `active` when assigned.
5. **No orphaned active reports.** An employee with active direct reports cannot be deactivated.
6. **Reactivation needs an active manager** (or no manager).
7. **History is append-only.** Services and selectors only insert and read history rows; there is no update or delete code path (`SalaryHistory.save()` raises if the row already exists).
8. **Every country has a currency rate** (FK guarantees it).

## 6. Hierarchy queries

Would assigning `:new_manager` to `:emp` create a cycle? Walk up from the new manager; if the chain reaches `:emp`, it would. `UNION` (not `UNION ALL`) stops the recursion if bad data ever contains a loop.

```sql
WITH RECURSIVE chain(id) AS (
  SELECT :new_manager
  UNION
  SELECT e.manager_id FROM employees e JOIN chain c ON e.id = c.id
  WHERE e.manager_id IS NOT NULL
)
SELECT 1 FROM chain WHERE id = :emp LIMIT 1;
```

Direct reports (paginated): `SELECT ... FROM employees WHERE manager_id = :id AND (:status IS NULL OR status = :status)` (uses `idx_emp_manager`).

Has active reports: `SELECT EXISTS(SELECT 1 FROM employees WHERE manager_id = :id AND status = 'active')`.

In Django, implement the cycle check as an iterative walk up `manager_id` with a visited set and a depth guard (each step is a primary-key lookup), or run the SQL above with bound parameters; both give the same answer and both are tested. Hierarchy depth in the seed is 5 levels, so these queries are trivial.

## 7. Migrations and connection settings

- Each Django app has an initial migration created with `makemigrations` and reviewed by hand. A test runs `makemigrations --check` to make sure the models and migrations agree. pytest-django builds the test database from the migrations.
- Connection settings (in `DATABASES["default"]`, see `02-backend-spec.md` sec 2): Django turns `PRAGMA foreign_keys = ON` on by itself; `OPTIONS["init_command"]` sets `journal_mode=WAL` and `synchronous=NORMAL`; `OPTIONS["timeout"]` of 5 seconds is the busy timeout; `OPTIONS["transaction_mode"] = "IMMEDIATE"` takes the write lock at the start of a write transaction.
- Database file lives in `backend/data/` (gitignored). Tests use an in-memory database.

## 8. Query plans to verify (automated test in 05 sec 2)

Call `QuerySet.explain()` (SQLite returns the query plan) on the seeded database and assert the plan text contains the index name:
1. List with `status='active' AND country_code=?` mentions `idx_emp_status_country`.
2. List with `manager_id=?` mentions `idx_emp_manager`.
3. History for one employee mentions `idx_history_employee_effective` and has no temp B-tree for sorting.
4. Direct-reports count mentions `idx_emp_manager`.
5. History list with default sort (no filters) mentions `idx_history_effective` and has no temp B-tree for sorting.

If SQLite prefers a different index for a combined filter, that is fine as long as the query meets the latency target; the test asserts only the four cases above.

## 9. Capacity and future changes
- 10,000 employees at about 150 bytes plus indexes is a few MB. History is about 25,000 to 30,000 rows. The database file stays well under 20 MB.
- **Moving to Postgres:** `INTEGER` cents become `BIGINT`; generated column syntax is the same idea; `COLLATE NOCASE` becomes `citext` or a lower() index; median and percentiles become possible with `percentile_cont`; add trigram indexes for search.
- **Changing the pay structure later.** Today the three components (base, bonus, allowances) are columns, as fixed by the PRD. This keeps analytics a plain `SUM` over one generated column, enforces types and constraints, and needs no joins. If a component is added occasionally, it is one migration (new column with default 0, updated generated total, matching history columns). If components become many, country-specific or HR-defined, move to rows: `pay_components(id, code, name)` plus `employee_pay(employee_id, component_id, amount_cents)` (and the same shape for history), and sum over rows. The cost is joins, pivoting and a more complex total, so do it only when the structure really changes often.
- **Adding an audit trail later:** add an `audit_log` table (actor `hr_user_id`, entity, action, field, old/new, timestamp, optional `batch_id`) and write to it from the service methods that already wrap every change. No existing table needs to change.
