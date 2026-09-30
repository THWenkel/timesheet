# AGENTS.md — Timesheet Project

This document is the authoritative reference for AI agents and developers working on this project.
It explains the full project structure, how to build, run, test, and maintain both backend and frontend,
as well as MCP tooling setup.

---

## Project Overview

A multi-user timesheet web application with:

- **Backend**: Python 3.14 + FastAPI + SQLAlchemy 2 ORM targeting Microsoft SQL Server 2012
- **Frontend**: React 19 + TypeScript strict + Vite + react-calendar
- **Administration**: .NET 10 WPF + MVVM Toolkit, using the FastAPI backend
- **Export**: CSV, Excel (openpyxl), PDF (reportlab)
- **Auth**: Scaffolded but not active in v1 — see `backend/app/core/security.py`

---

## Repository Structure

```text
timesheet/
├── .gitignore
├── AGENTS.md                    ← this file
├── README.md
├── admin/                      ← WPF administration client
│   ├── README.md
│   └── Timesheet.Admin/
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
│   │   │   ├── project.py       ← Customer, Project, and allocation ORM models
│   │   │   └── timesheet.py     ← TimesheetEntry ORM model
│   │   ├── schemas/
│   │   │   ├── employee.py      ← Pydantic v2 schemas for Employee
│   │   │   └── timesheet.py     ← Pydantic v2 schemas for TimesheetEntry + Export
│   │   ├── routers/
│   │   │   ├── employees.py     ← GET /api/employees
│   │   │   ├── projects.py      ← Customer/project administration API
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

## Datenbank Sicherungen durchführen

```sql
use WiTERP
truncate table [dbo].[timesheet_entries_backup]

use WiTERP
truncate table [dbo].[employees_backup]

-- Kein SET IDENTITY_INSERT nötig!
-- Wir lassen die Spalte ID einfach weg – die neue Tabelle vergibt
-- automatisch neue aufeinanderfolgende IDs.
INSERT INTO dbo.timesheet_entries_backup
(
    [id], [employee_id],[entry_date],[minutes],[description],[created_at],[updated_at],[created_by],[updated_by]
)
SELECT [id], [employee_id],[entry_date],[minutes],[description], [created_at], [updated_at], [created_by], [updated_by]
FROM dbo.timesheet_entries;


insert into [dbo].[employees_backup]
(
    [surname], [lastname], [is_active], [created_at], [updated_at],[created_by], [updated_by]
)
select [surname], [lastname], [is_active], [created_at], [updated_at],[created_by], [updated_by]
from dbo.employees;

```

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
python cli.py --password YOUR_SA_PASSWORD migrate

# Show applied and pending SQL migration scripts
python cli.py --password YOUR_SA_PASSWORD status

# Alembic: generate a new migration
alembic revision --autogenerate -m "description"

# Alembic: apply migrations
alembic upgrade head

# Alembic: rollback one step
alembic downgrade -1
```

---

## Frontend

- user Frontend is built with React 19 + TypeScript strict mode

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

### Authentifizierung (JWT)

Anleitung für Administratoren und Anwender (Spalten der Benutzerliste, Rollen, Passwörter): [BENUTZERVERWALTUNG.md](BENUTZERVERWALTUNG.md).

#### Konten, Passwörter, Anmeldung: so funktioniert es

Es gibt **keine Selbstregistrierung und kein „Passwort vergessen“ per E-Mail** (kein Mailversand im Projekt). Alle Konten und alle ersten Passwörter kommen von einem Administrator:

| Was | Wo | Wer |
|---|---|---|
| Konto anlegen bzw. Benutzernamen vergeben | Admin-Tool → Benutzer → Neu/Bearbeiten → Feld „Benutzername (Login)“ | Administrator |
| **Erstes Passwort setzen** | Admin-Tool → Benutzer markieren → **„Einmalpasswort“** | Administrator |
| Passwort vergessen / zurücksetzen | dasselbe: **„Einmalpasswort“** (macht das alte Passwort und alle Anmeldungen ungültig, hebt eine Sperre auf) | Administrator |
| Eigenes Passwort ändern | Web-App → „Change password“ (Adresse `/timesheet/change-password`), altes Passwort nötig | jeder Benutzer |
| Anmelden | Web-App `/timesheet/login` (Benutzername + Passwort) | jeder Benutzer |

Ablauf für einen neuen Benutzer:

1. Administrator vergibt im Admin-Tool einen **Benutzernamen** (mindestens 3 Zeichen, wird kleingeschrieben gespeichert).
2. Administrator klickt **„Einmalpasswort“**. Das Tool zeigt das Passwort **einmalig** an und kopiert es in die Zwischenablage. Es steht nirgends sonst und ist nur als Hash (Argon2id) gespeichert.
3. Administrator gibt Benutzername und Einmalpasswort auf sicherem Weg weiter (persönlich, Telefon; nicht per unverschlüsselter Mail).
4. Der Benutzer meldet sich an. Weil es ein Einmalpasswort ist, verlangt die Web-App **sofort ein eigenes Passwort** (mindestens 10 Zeichen). Erst danach funktioniert alles andere.

Regeln: 5 Fehlversuche sperren das Konto 15 Minuten (auch mit richtigem Passwort). Die Fehlermeldung ist immer dieselbe und verrät nicht, ob der Benutzername existiert. Ein Passwortwechsel oder Reset macht alle bisherigen Anmeldungen ungültig. Deaktivierte Benutzer können sich nicht anmelden und verlieren laufende Sitzungen sofort.

#### Erste Einrichtung (den ersten Administrator anlegen)

Ein Administrator muss existieren, bevor die Anmeldung erzwungen wird. Solange in `backend/.env` `AUTH_ENABLED=false` steht (Standard), fragt das Admin-Tool **nicht** nach einem Login, und die API lässt alles durch:

1. Backend starten, Admin-Tool öffnen (kein Login-Fenster).
2. Den eigenen Mitarbeiter bearbeiten: Benutzernamen eintragen, Haken **„Administrator“** setzen, speichern.
3. **„Einmalpasswort“** klicken, Passwort notieren.
4. In der Web-App unter `/timesheet/login` anmelden, das Einmalpasswort durch ein eigenes ersetzen. Damit ist geprüft, dass es funktioniert.
5. Erst jetzt in `backend/.env` `AUTH_ENABLED=true` und `SECRET_KEY=<mind. 32 Zeichen>` setzen (Erzeugen: `python -c "import secrets; print(secrets.token_hex(32))"`), Backend neu starten. Ohne gültigen Schlüssel startet die App absichtlich nicht.
6. Ab jetzt verlangt auch das Admin-Tool beim Start einen Login. Nur Konten mit „Administrator“ kommen hinein.

Vergisst der einzige Administrator sein Passwort, gibt es keinen Selbstweg: `AUTH_ENABLED=false` setzen, Backend neu starten, im Admin-Tool „Einmalpasswort“ setzen, wieder `AUTH_ENABLED=true`. Wer Zugriff auf die `.env` hat, kann das also. Die `.env` muss deshalb geschützt bleiben.

#### Technik

- Login: `POST /api/auth/login`. Das JWT liegt in einem **HttpOnly**-Cookie `ts_session` (`Secure`, `SameSite=Lax`, Laufzeit `ACCESS_TOKEN_EXPIRE_MINUTES`, Standard 480); JavaScript kann es nicht lesen. Ein zweites, lesbares Cookie `ts_csrf` trägt den CSRF-Token, der bei jedem POST/PUT/DELETE im Header `X-CSRF-Token` mitgeschickt werden muss (er steckt auch als Claim im JWT).
- Weitere Endpunkte: `GET /api/auth/me`, `POST /api/auth/logout`, `POST /api/auth/change-password`, `POST /api/auth/admin/reset-password/{id}` (nur Admin), `GET /api/auth/config` (öffentlich: ist die Anmeldung aktiv?).
- Rechte: Alle Router verlangen einen Login (`main.py`, `require_user`/`require_admin`). Normale Benutzer sehen und ändern nur ihre eigenen Zeiteinträge (`employee_id` wird gegen das Token geprüft, `created_by` kommt aus dem Token). Administratoren wählen in der Web-App den Mitarbeiter (Auswahl nur für `is_admin`; die Liste `GET /api/employees/` ist admin-only). Mitarbeiterverwaltung, Projekte, Kunden und Datensicherung sind nur für Administratoren (`is_admin`).
- Datenbank: Migration `010_employee_auth.sql` (Spalten `username`, `password_hash`, `is_admin`, `must_change_password`, `password_changed_at`, `failed_login_count`, `locked_until` in `employees` und `employees_backup`).
- **HTTPS:** TLS endet am Reverse Proxy (siehe `INSTALL_IIS_INTRANET.md`). In Produktion `COOKIE_SECURE=true` (Standard). Lokal über `http://` muss `COOKIE_SECURE=false` in `backend/.env` stehen, sonst schicken Browser und Admin-Tool die Cookies nicht mit.
- Einstellungen (`backend/.env.example`): `AUTH_ENABLED`, `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `COOKIE_SECURE`, `CORS_ORIGINS` (JSON-Liste, kein `*`), `PASSWORD_MIN_LENGTH`, `MAX_FAILED_LOGINS`, `LOCKOUT_MINUTES`.
- Sicherungen (`*_backup`, Datei-Export) von `employees` enthalten die Passwort-Hashes. Diese Dateien wie Zugangsdaten behandeln.
- **Reverse-Proxy (nginx, Domain `timesheet.wenkel.de`) und IIS-Betrieb dahinter:** [NGINX_REVERSE_PROXY.md](NGINX_REVERSE_PROXY.md), Konfigurationsdateien in `deploy/nginx-proxy/`. Frontend-Build für die Domain: `npm run build:domain`.
- Test-Konto: `testheini` (normaler Benutzer, Testkonto in der echten Datenbank). Das Passwort steht nicht im Repository; ein Administrator setzt es bei Bedarf mit „Einmalpasswort“ neu.

### Export

Single endpoint `GET /api/export` with query parameters:

- `format`: `csv` | `excel` | `pdf`
- `employee_id`: integer
- `from_date`: ISO date string
- `to_date`: ISO date string

Returns a `StreamingResponse` with appropriate `Content-Disposition` header for browser download.

- PDF generation requires the declared `pypdf` and `reportlab` runtime dependencies. After
    updating `backend/pyproject.toml`, rerun `python -m pip install -e ".[dev]"` in the backend
    virtual environment and restart the backend service.
- Browser-triggered downloads must build their URL from `apiBaseUrl` in
    `frontend/src/api/client.ts`. A root-relative `/api/...` URL bypasses the `/timesheet`
    IIS application and its reverse-proxy rule.

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
