# ACME Salary Management

Web app for the ACME HR Manager to maintain compensation data and answer pay questions for about 10,000 employees across six countries. It replaces the spreadsheets used for employee pay, salary history, bulk changes and pay insights.

## What it does

- **Login and sessions:** one seeded HR user, server-side sessions, CSRF-protected writes and login throttling.
- **Employees:** server-side search, filters, sorting and pagination; create, edit, deactivate and reactivate.
- **Reporting lines:** one manager per employee, direct reports, cycle validation and guarded deactivation.
- **Salary history:** every pay change is recorded with before/after values, a reason and a batch id for bulk changes.
- **Bulk pay updates:** preview a percentage or fixed annual change for a filtered group, then apply it in one transaction.
- **Pay insights:** headcount, total/average/min/max pay, pay mix, country and department comparisons, salary bands, job-title pay and outliers.
- **History search:** search every pay change by employee, reason, type, date range or bulk batch.
- **Currency rates:** API-only CRUD for static USD conversion rates; there is intentionally no screen for this.

The product requirements are in [`docs/PRD.md`](docs/PRD.md), the implementation specs are in [`specs/`](specs/), and the software design notes are in [`docs/DESIGN.md`](docs/DESIGN.md). The visual design reference is [`design/DESIGN.md`](design/DESIGN.md).

## How this was built

This project was built with **spec-driven development** and **test-driven development (TDD)**. Behaviour, data rules and API contracts were written in [`specs/`](specs/) before implementation. Each feature followed the red-green-refactor loop: write a failing test, make it pass with the smallest change, then refactor.

The UI was designed in **Google Stitch**. Stitch was connected to **opencode** (an AI coding tool) through the **Model Context Protocol (MCP)**, so the screens could be imported into the frontend workflow as the visual reference. The app itself is implemented with MUI, MUI X DataGrid and Recharts rather than pasting the generated HTML or CSS.

## Stack

- **Backend:** Python 3.12, Django 5.2, Django REST Framework, SQLite (WAL mode), Argon2 passwords, drf-spectacular.
- **Frontend:** React 18, Vite, MUI, MUI X DataGrid, TanStack Query, React Hook Form, Zod, Recharts.
- **Tests:** pytest/pytest-django, Vitest, React Testing Library, MSW.
- **Lint:** ruff, ESLint and Prettier.

Money is stored and transmitted as integer USD cents. The frontend formats it with `frontend/src/lib/money.js`. Local-currency amounts are display-only conversions using the static rates in the database.

## Repository layout

```text
backend/        Django project, apps, migrations, seed command and tests
frontend/       React app, tests, MUI theme and API client
docs/           PRD, generated OpenAPI contract and design notes
specs/          Behaviour, data, API and testing specifications
design/         Visual design system and Stitch handoff notes
prompts/        AI prompt logs
Makefile        Setup, run, seed, test, lint and OpenAPI commands
```

## Prerequisites

- Python 3.12
- Node.js 20+ and npm
- GNU Make
- No separate database server: SQLite is bundled with Python.

## Quick start

1. Copy the environment template and edit the local values:

   ```bash
   cp .env.example .env
   ```

   At minimum, set:

   ```dotenv
   DEBUG=true
   SECRET_KEY=dev-only-change-me
   SEED_HR_EMAIL=hr@acme.example
   SEED_HR_PASSWORD=choose-a-local-password
   ```

   `.env` is ignored by Git. Do not commit real passwords or secrets.

2. Install backend and frontend dependencies:

   ```bash
   make setup
   ```

   If `python3.12` is not on your `PATH`, pass another interpreter:

   ```bash
   make setup PYTHON=python3
   ```

3. Create the database schema and seed the demo data:

   ```bash
   make migrate
   make seed
   ```

   `make seed` runs 10,000 employees, the hierarchy and salary history with `--reset --verify`. It is destructive: it flushes the database first. If `SEED_HR_PASSWORD` is empty, the seed prints a generated password once.

   To verify an existing seed without replacing it:

   ```bash
   make seed SEED_ARGS=--verify
   ```

4. Start the API and frontend in separate terminals:

   ```bash
   make backend
   ```

   ```bash
   make frontend
   ```

5. Open <http://localhost:5173> and sign in with `SEED_HR_EMAIL` / `SEED_HR_PASSWORD`.

The API runs at <http://127.0.0.1:8000>. Interactive API docs are at <http://127.0.0.1:8000/api/docs/> and the generated schema is at <http://127.0.0.1:8000/api/docs/schema/>. The health check is `GET /api/health`.

A click-by-click walkthrough is in [`docs/DEMO.md`](docs/DEMO.md).

## Configuration

The backend reads configuration from environment variables. The `make backend`, `make migrate` and `make seed` targets load the repository-root `.env` automatically; Django itself does not load `.env` files.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_PATH` | `backend/data/acme.sqlite3` | SQLite database file |
| `SECRET_KEY` | empty | Required when `DEBUG=false` |
| `DEBUG` | `false` | Local development should use `true` |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated hosts |
| `CSRF_TRUSTED_ORIGINS` | empty | Trusted HTTPS origins when deployed |
| `COOKIE_SECURE` | `false` | Set `true` behind HTTPS |
| `SESSION_COOKIE_NAME` | `acme_session` | Session cookie name |
| `SESSION_ABSOLUTE_HOURS` | `8` | Maximum session lifetime |
| `SESSION_IDLE_MINUTES` | `60` | Idle timeout |
| `LOGIN_MAX_FAILURES` | `5` | Failed logins before a temporary block |
| `LOGIN_WINDOW_MINUTES` | `15` | Failed-login window |
| `BULK_MIN_PERCENT` | `-50` | Minimum bulk percentage change |
| `BULK_MAX_PERCENT` | `100` | Maximum bulk percentage change |
| `MAX_PAGE_SIZE` | `100` | Maximum list page size |
| `SEED_HR_EMAIL` | `hr@acme.example` | Seeded HR login email |
| `SEED_HR_PASSWORD` | empty | Seeded HR password; empty prints a generated one |

## API overview

All business routes except `POST /api/auth/login` and `GET /api/health` require a session. Writes also require the CSRF token returned by login or `GET /api/auth/me`, sent in `X-CSRF-Token`. The API returns JSON only.

Main routes:

| Area | Routes |
|---|---|
| Auth | `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` |
| Lookups | `GET /api/lookups` |
| Employees | `GET/POST /api/employees`, `GET/PATCH /api/employees/{id}` |
| Reporting and history | `GET /api/employees/{id}/direct-reports`, `/history` |
| Status | `POST /api/employees/{id}/deactivate`, `/reactivate` |
| Bulk updates | `POST /api/bulk-updates/preview`, `/apply` |
| History search | `GET /api/salary-history` |
| Analytics | `GET /api/analytics/summary`, `/breakdown`, `/distribution`, `/outliers`, `/team/{manager_id}` |
| Currency rates | `GET/POST /api/currency-rates`, `GET/PATCH/DELETE /api/currency-rates/{code}` |
| Developer tooling | `GET /api/docs/`, `GET /api/docs/schema/` |

The authoritative contract is [`docs/openapi.json`](docs/openapi.json). Regenerate it after backend changes:

```bash
make openapi
```

## Currency rates with curl

Currency rates are API-only. The seeded currencies are USD, INR, GBP, EUR, CAD and SGD. USD is the fixed base currency: it cannot be updated or deleted. A currency used by a country cannot be deleted.

```bash
BASE=http://127.0.0.1:8000
COOKIE=/tmp/acme-cookies.txt

LOGIN_JSON=$(curl -s -c "$COOKIE" \
  -H "Content-Type: application/json" \
  -d '{"email":"hr@acme.example","password":"choose-a-local-password"}' \
  "$BASE/api/auth/login")

CSRF=$(printf '%s' "$LOGIN_JSON" | python3 -c \
  'import json, sys; print(json.load(sys.stdin)["csrf_token"])')

# List all rates.
curl -s -b "$COOKIE" "$BASE/api/currency-rates"

# Change the EUR rate.
curl -s -b "$COOKIE" -X PATCH \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -d '{"rate_per_usd":0.93}' \
  "$BASE/api/currency-rates/EUR"
```

The employee detail response includes a display-only `local` block. Changing a rate does not change stored USD amounts. The lookups endpoint caches for up to 60 seconds, so the UI may need a reload to show a new rate.

## Testing and quality checks

```bash
make test        # backend fast suite + frontend tests
make test-slow   # 10k seed performance and verification checks
make lint        # ruff, ESLint and Prettier
make openapi     # regenerate docs/openapi.json
```

The fast suite excludes tests marked `slow`. The slow suite uses the full 10,000-employee seed and checks the main list, detail and analytics endpoints against generous performance thresholds.

Frontend-only commands:

```bash
cd frontend
npm run test:watch
npm run build
```

## Seed data

The seed is deterministic: `--seed 42` and the fixed seed date `2026-10-01` produce the same data. It creates:

- 6 countries, 6 currencies, 9 departments and the job-title catalogue.
- 10,000 employees in a five-level hierarchy.
- About 25,000–30,000 salary-history rows.
- One HR user from `SEED_HR_EMAIL` / `SEED_HR_PASSWORD`.

The seed refuses to run over existing employees unless `--reset` is supplied. `make seed` supplies `--reset --verify` by default.

## Performance and trade-offs

The design targets the seeded 10k dataset: employee list under 150 ms p95, analytics under 100 ms, seed under 15 seconds, and fast test suites under 30 seconds. Indexes and SQL aggregations are used instead of per-row queries.

Deliberate limitations are documented in the PRD:

- SQLite has a single writer and no native median/percentile functions.
- The login throttle is in process memory, so a multi-worker deployment needs a shared cache.
- FX rates are static and display-only; there is no live FX integration.
- Salary history records what changed and when, not who changed it.
- Only one HR user exists; there are no roles or permissions.
- There is no currency-rate screen, CSV import/export, payroll, tax or org-chart visualisation.
- The app is designed for local/interview use; a production deployment needs a WSGI server, HTTPS, `DEBUG=false`, a real `SECRET_KEY`, `COOKIE_SECURE=true`, and proper `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS`.

See [`docs/DESIGN.md`](docs/DESIGN.md) and [`docs/PRD.md`](docs/PRD.md) section 6 for the full reasoning.

## Troubleshooting

**`SECRET_KEY is required when DEBUG is false`**  
Set `SECRET_KEY` in `.env`, or set `DEBUG=true` for local development.

**`make backend` cannot find `.env`**  
Create it with `cp .env.example .env`. Only the Make targets load it.

**`Employees already exist. Run with --reset to replace the seed.`**  
Use `make seed` to reset, or `make seed SEED_ARGS=--verify` to check the existing data.

**Lost the seeded HR password**  
Set `SEED_HR_PASSWORD` in `.env` and run `make seed` to reset the database and recreate the user.

**`python3.12` is missing**  
Run `make setup PYTHON=python3`, or install Python 3.12.

**Port 8000 or 5173 is already in use**  
Stop the other process, or run the backend/frontend commands manually with different ports.

**Currency changes do not appear immediately**  
Lookups are cached for up to 60 seconds; reload the app after the cache expires.
