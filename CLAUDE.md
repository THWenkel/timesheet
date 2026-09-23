# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`AGENTS.md` is the authoritative, more detailed project reference (setup, env vars, security checklist, DB backup SQL). Read it for anything not covered here. `admin/README.md` documents the WPF admin client and what each SQL migration does.

## Components

Three clients of one database, all going through the FastAPI backend:

- `backend/` — Python 3.14, FastAPI, SQLAlchemy 2 (sync sessions), pyodbc → SQL Server 2012 (`dbserver01` / `WiTERP`, ODBC Driver 17).
- `frontend/` — React 19 + TypeScript strict + Vite. The employee-facing time entry UI.
- `admin/Timesheet.Admin/` — .NET 10 WPF + CommunityToolkit MVVM. Manages employees, customers, projects. Never talks to SQL Server directly; UI text is German.

## Commands

Backend (run from `backend/`, venv at `.venv`):

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000   # Swagger at /docs, health at /health
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\pyright.exe                                # strict mode
python cli.py --password <pw> status                       # show applied/pending SQL migrations
python cli.py --password <pw> migrate                      # apply pending SQL migrations
```

Frontend (run from `frontend/`):

```powershell
npm run dev              # :5173, proxies /api → VITE_API_URL or http://localhost:8000
npm run generate-api     # regenerate src/api/generated.ts — backend must be running
npm run typecheck
npm run format:check
npm run build            # tsc --noEmit && vite build
npm run test             # vitest run
npx vitest run path/to/file.test.ts      # single test file
npx vitest run -t "test name"            # single test by name
```

Admin:

```powershell
dotnet build admin/Timesheet.Admin/Timesheet.Admin.csproj
dotnet run --project admin/Timesheet.Admin/Timesheet.Admin.csproj   # TIMESHEET_API_URL overrides http://localhost:8000/
```

There are no backend or admin automated tests, and the frontend has Vitest configured (`src/test/setup.ts`) but few or no test files. End-to-end verification is done manually or via Playwright MCP against the running app. See `TESTING.md` for the test-case format used.

## Architecture

### Backend layering

`routers/` (HTTP, `Depends(get_db)`) → `services/` (validation + business logic) → `models/` (ORM). `schemas/` holds the Pydantic v2 request/response models that define the OpenAPI contract. All routes are prefixed `/api/...`. `projects.py` exports three routers (`router`, `customers_router`, `country_codes_router`), and each is registered separately in `main.py`.

`app/db/session.py` builds a raw ODBC connection string (URL-encoded into `mssql+pyodbc:///?odbc_connect=`) and runs `USE [WiTERP]` on every new connection. Settings come from `backend/.env` via `app/core/config.py`. `DB_PASSWORD` is required, so importing the app without it fails.

Auth (`app/core/security.py`) is a middleware scaffold that is a no-op while `AUTH_ENABLED=false`. The frontend picks the employee from a dropdown.

### Schema changes: the SQL scripts are the real source of truth

`backend/migrations/NNN_*.sql` scripts are applied by `cli.py`. It tracks them in the `schema_migrations` table, splits batches on `\nGO`, and runs each script in its own transaction. `alembic/versions/` is empty, so Alembic is configured but not in use. When you change the schema:

1. Add a new numbered SQL script. It must be SQL Server 2012 compatible, and scripts that have already been applied must never be edited.
2. Update the matching ORM model in `app/models/` and the Pydantic schema by hand.
3. Regenerate the frontend types (`npm run generate-api`). `generated.ts` is git-ignored.
4. Update the admin client's hand-written DTOs and API clients (`admin/Timesheet.Admin/Models/*.cs`, `Services/*ApiClient.cs`). Nothing generates them, so they drift silently.

### Domain conventions

- Time is stored as **integer minutes**: multiples of 15, from 15 to 1440. The frontend converts to and from `hh:mm` in `src/utils/timeUtils.ts`.
- Every table has audit columns (`created_at`, `updated_at`, `created_by`, `updated_by`), and every timesheet write carries an `employee_id`.
- Deleting an employee or customer is a **deactivation** (`is_active`), never a hard delete, so existing entries and project links stay intact.
- Projects belong to a customer and are assigned to employees through `project_allocations`. Budgets are in hours *or* person-days, and there is deliberately no conversion between them.
- Customer country must be a code that exists in the `CountryCode2` lookup table.
- Export: `GET /api/export?format=csv|excel|pdf&employee_id=&from_date=&to_date=` streams the file from `services/export_service.py`.

### Frontend

The frontend is one page (`pages/HomePage.tsx`) composed of components. Data is fetched in hooks (`hooks/`) through the typed `openapi-fetch` client in `src/api/client.ts`. The `@/` import alias maps to `src/`.

### Admin client

`App.xaml.cs` wires everything by hand, with no DI container: one shared `HttpClient`, the API clients, `UserDialogService`, and window services that open the customer and project management windows. ViewModels live in `ViewModels/` and views in `Views/`.

## Style constraints enforced by tooling

- Ruff: line length 100, double quotes, LF line endings, type annotations required (`ANN`), no `print` except in `cli.py`, pathlib instead of `os.path`. `B008` is allowed in routers for `Depends()` defaults.
- Pyright strict applies, and unknown types are errors. Local stubs for untyped C extensions live in `backend/stubs/`, for example `pyodbc.pyi`.
- Frontend formatting uses Prettier (`.prettierrc`).
