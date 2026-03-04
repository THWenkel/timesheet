# AGENTS.md — Timesheet Project

This document is the authoritative reference for AI agents and developers working on this project.
It explains the full project structure, how to build, run, test, and maintain both backend and frontend,
as well as MCP tooling setup.

---

## Project Overview

A multi-user timesheet web application with:

- **Backend**: Python 3.14 + FastAPI + SQLAlchemy 2 ORM targeting Microsoft SQL Server 2012
- **Frontend**: React 19 + TypeScript strict + Vite + react-calendar
- **Export**: CSV, Excel (openpyxl), PDF (reportlab)
- **Auth**: Scaffolded but not active in v1 — see `backend/app/core/security.py`

---

## Repository Structure

```text
timesheet/
├── .gitignore
├── AGENTS.md                    ← this file
├── README.md
├── specification/
│   └── initialprompt.md         ← original project specification
├── backend/                     ← Python FastAPI backend
│   ├── app/
│   │   ├── main.py              ← FastAPI app entrypoint
│   │   ├── core/
│   │   │   ├── config.py        ← pydantic-settings configuration
│   │   │   └── security.py      ← auth scaffold (NOT active in v1)
│   │   ├── db/
│   │   │   ├── base.py          ← SQLAlchemy declarative base
│   │   │   └── session.py       ← engine + session factory
│   │   ├── models/
│   │   │   ├── employee.py      ← Employee ORM model
│   │   │   └── timesheet.py     ← TimesheetEntry ORM model
│   │   ├── schemas/
│   │   │   ├── employee.py      ← Pydantic v2 schemas for Employee
│   │   │   └── timesheet.py     ← Pydantic v2 schemas for TimesheetEntry + Export
│   │   ├── routers/
│   │   │   ├── employees.py     ← GET /api/employees
│   │   │   ├── timesheets.py    ← GET/POST/PUT /api/timesheets
│   │   │   └── export.py        ← GET /api/export
│   │   └── services/
│   │       ├── timesheet_service.py ← business logic + validation
│   │       └── export_service.py    ← CSV / Excel / PDF generation
│   ├── migrations/              ← raw SQL migration scripts (for CLI tool)
│   │   └── 001_initial_schema.sql
│   ├── alembic/                 ← Alembic ORM migration environment
│   │   ├── env.py
│   │   └── versions/
│   ├── alembic.ini
│   ├── cli.py                   ← CLI maintenance tool
│   ├── pyproject.toml           ← dependencies, Ruff, Pyright config
│   ├── .env.example             ← env var template
│   └── .venv/                   ← Python virtual environment (not in git)
└── frontend/                    ← React + TypeScript frontend
    ├── src/
    │   ├── api/
    │   │   ├── generated.ts     ← AUTO-GENERATED — do not edit manually
    │   │   └── client.ts        ← openapi-fetch client
    │   ├── components/
    │   │   ├── EmployeeSelector.tsx
    │   │   ├── TimesheetCalendar.tsx
    │   │   ├── TimePickerInput.tsx
    │   │   ├── DescriptionInput.tsx
    │   │   ├── DaySummary.tsx
    │   │   ├── WeekSummary.tsx
    │   │   └── ExportPanel.tsx
    │   ├── pages/
    │   │   └── HomePage.tsx
    │   ├── hooks/
    │   │   ├── useTimesheetEntries.ts
    │   │   └── useEmployees.ts
    │   ├── utils/
    │   │   └── timeUtils.ts
    │   ├── App.tsx
    │   └── main.tsx
    ├── public/
    ├── vite.config.ts
    ├── tsconfig.json
    ├── tsconfig.node.json
    ├── vitest.config.ts
    ├── .prettierrc
    └── package.json
```

---

## Backend

### Prerequisites

- Python 3.14+
- ODBC Driver 17 for SQL Server installed on the machine
- Access to `dbserver01` SQL Server instance with database `WiTERP`

### Setup

```powershell
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install all dependencies
pip install -e ".[dev]"
```

### Environment Variables

Copy `.env.example` to `.env` and fill in values:

```powershell
copy .env.example .env
```

`.env` is git-ignored. Never commit secrets.

### Running the Backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API available at: http://localhost:8000  
OpenAPI schema: http://localhost:8000/openapi.json  
Swagger UI: http://localhost:8000/docs  
ReDoc: http://localhost:8000/redoc  

### Linting & Type Checking

```powershell
cd backend

# Ruff lint
.\.venv\Scripts\ruff.exe check .

# Ruff format check
.\.venv\Scripts\ruff.exe format --check .

# Pyright strict type checking
.\.venv\Scripts\pyright.exe
```

### Database Migrations

Two migration mechanisms coexist:

1. **Alembic** — ORM-driven, for development/automatic schema management
2. **CLI tool** — raw SQL scripts in `migrations/`, for controlled production deployments

```powershell
cd backend
.\.venv\Scripts\Activate.ps1

# Run all pending SQL migration scripts (CLI tool)
python cli.py migrate --password YOUR_SA_PASSWORD

# Alembic: generate a new migration
alembic revision --autogenerate -m "description"

# Alembic: apply migrations
alembic upgrade head

# Alembic: rollback one step
alembic downgrade -1
```

---

## Frontend

### Prerequisites

- Node.js >= 20.19.0
- npm >= 10

### Setup

```powershell
cd frontend
npm install
```

### Running the Frontend

```powershell
cd frontend
npm run dev
```

App available at: http://localhost:5173  
API calls to `/api/*` are proxied to `http://localhost:8000` — no CORS configuration needed.

> **Both backend and frontend must be running** for the full app to work.

### Generate API Types

After backend schema changes, regenerate TypeScript types from the OpenAPI schema:

```powershell
cd frontend
npm run generate-api
```

This runs `openapi-typescript` against `http://localhost:8000/openapi.json` and writes to `src/api/generated.ts`.
The `generated.ts` file is git-ignored and must be regenerated locally.

### Build for Production

```powershell
cd frontend
npm run build
```

Output in `frontend/dist/`.

### Linting & Formatting

```powershell
cd frontend

# TypeScript type check
npm run typecheck

# Prettier format check
npm run format:check

# Prettier format (write)
npm run format
```

### Testing

```powershell
cd frontend

# Run unit tests (Vitest)
npm run test

# Run tests with coverage
npm run test:coverage

# Run tests in watch mode
npm run test:watch
```

---

## MCP Tooling

### context7

Used for documentation lookups during development (library docs, API references).

To use context7 in an agent prompt:

- Ask for documentation: "Using context7, look up the SQLAlchemy 2 async session documentation"
- The MCP server resolves library IDs and returns up-to-date docs

### Playwright (Web Testing)

Used for end-to-end browser tests against the running application.

Ensure the app is running (both backend on :8000 and frontend on :5173) before running Playwright tests.

Playwright MCP is configured to connect to the running browser session in VS Code.

---

## Architecture Notes

### Time Storage

Time entries are stored as **integer minutes** (e.g. 90 = 1h 30m).

- Simplifies arithmetic for daily/weekly summaries

- Frontend converts to/from `hh:mm` display format via `src/utils/timeUtils.ts`
- Valid values: multiples of 15, in range 15–1440 (max 24h per day)

### Authentication (v1: not active)

- `backend/app/core/security.py` contains a scaffold for JWT-based auth
- In v1, the `Authorization` header is parsed but **not enforced**
- The employee is selected via a dropdown in the frontend
- **TODO**: Activate auth middleware before production deployment

### Export

Single endpoint `GET /api/export` with query parameters:
- `format`: `csv` | `excel` | `pdf`
- `employee_id`: integer
- `from_date`: ISO date string
- `to_date`: ISO date string

Returns a `StreamingResponse` with appropriate `Content-Disposition` header for browser download.

### Multi-User Design
- All DB writes include `employee_id` FK to the `employees` table
- Audit columns (`created_at`, `updated_at`, `created_by`, `updated_by`) on all entities
- Architecture supports concurrent multi-user usage from day one
- Initial deployment is single-user (one employee selects themselves)

---

## Security Checklist (Before Go-Live)

- [ ] Replace `sa` SQL Server user with a dedicated least-privilege account
- [ ] Enable encrypted SQL Server connection (`Encrypt=yes`, valid TLS certificate)
- [ ] Activate JWT authentication in `backend/app/core/security.py`
- [ ] Move `DB_PASSWORD` out of `.env` file into a secrets manager
- [ ] Enable HTTPS for the FastAPI app (reverse proxy recommended)
- [ ] Review and restrict CORS if frontend and backend are on different origins
