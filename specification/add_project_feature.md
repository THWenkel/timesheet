# Feature Specification: Projects, Customers & Extended Tracking

**Date:** 2026-03-14  
**Status:** Draft

---

## 1. Overview

This document describes all planned extensions to the Timesheet application beyond the initial v1 scope.
The changes add project and customer management, budget tracking, activity categorisation, a dashboard,
public holiday support, and a copy-previous-week convenience action.

---

## 2. Feature List

### 2.1 Customer Management

- New entity: **Customer** (`id`, `name`, `notes`, `is_active`, audit columns)
- Dedicated frontend page **"Customers"** (menu entry) with:
  - List view (name, active status)
  - Create / Edit / Soft-delete (deactivate) actions
- Customers are selected from a dropdown when creating or editing a project (no free-text)

---

### 2.2 Project Management

- New entity: **Project** (`id`, `customer_id` FK, `name`, `description`, `max_hours` DECIMAL, `status`, audit columns)
- **Status** values: `active` | `paused` | `completed`
  - Completed projects are hidden from the timesheet entry dropdown but remain visible in reports and the Projects page
- Dedicated frontend page **"Projects"** (menu entry) with:
  - List view (name, customer, status, budget used/total)
  - Create / Edit / Archive (set status = completed) actions

---

### 2.3 Per-User Hour Allocation

- New entity: **ProjectAllocation** (`id`, `project_id` FK, `employee_id` FK, `allocated_hours` DECIMAL, audit columns)
- A project's `max_hours` can be split across multiple employees
- UI on the Project detail/edit page: allocation table — add/remove employee rows, set hours per row
- Validation: sum of per-user allocations ≤ project `max_hours` (warn, do not hard-block)

---

### 2.4 Budget Tracking

- Tracked values computed on-the-fly from `timesheet_entries` (no separate stored aggregate):
  - **Project total hours used** = SUM of minutes for all entries linked to the project
  - **Per-user hours used** = SUM of minutes for entries of that employee + project
- API endpoints expose `hours_used`, `hours_allocated`, `hours_remaining` on Project and ProjectAllocation responses
- **Visual indicators** in the Projects list and the timesheet entry project dropdown:
  - 🟡 Warning when usage > 80 % of budget
  - 🔴 Over-budget when usage ≥ 100 %

---

### 2.5 Project Selection in Timesheet Entry

- `timesheet_entries` gains a `project_id` FK (nullable for migration compatibility; required in UI)
- The timesheet entry form gains a **Project** dropdown (above or below the Employee selector)
- **Auto-select rule:** if exactly one active project exists (optionally: scoped to the current employee's allocations), it is pre-selected automatically
- Only `active` projects are shown; `paused` projects are shown with a visual indicator; `completed` projects are hidden

---

### 2.6 Activity Types / Tags

- New entity: **ActivityType** (`id`, `name`, `color`, `is_active`, audit columns)
- Seed data: "Development", "Meeting", "Support", "Review", "Other"
- Maintained on a settings/admin page (or inline in the Projects page)
- `timesheet_entries` gains an `activity_type_id` FK (nullable)
- The timesheet entry form gains an **Activity** dropdown
- Reports and the Dashboard can break down hours by activity type

---

### 2.7 Project Status Lifecycle

- Projects move through: `active` → `paused` → `active` (reversible) → `completed` (terminal, reversible by admin)
- Status change is a single PATCH endpoint: `PATCH /api/projects/{id}/status`
- UI: status badge with dropdown action menu on the Projects list row

---

### 2.8 Budget Warning Indicators

- Threshold configuration: warn at 80 % (default), configurable per project (optional future)
- Shown in:
  - Projects list page — coloured progress bar per row
  - Project dropdown in timesheet entry form — colour-coded label
  - Dashboard (see 2.9)

---

### 2.9 Dashboard / Overview Page

- New frontend page **"Dashboard"** (default/home or separate menu entry)
- Widgets:
  - **Active projects** table: name, customer, hours used / allocated, % bar, status badge
  - **My allocations** table: projects I'm allocated to, my hours used / allocated
  - **Weekly summary**: current week hours across all projects (reuses existing WeekSummary component)
- Data served by a new API endpoint: `GET /api/dashboard?employee_id=…`

---

### 2.10 Public Holidays

- New entity: **PublicHoliday** (`id`, `holiday_date` DATE, `name`, `country_code` CHAR(2), audit columns)
- Maintenance UI: simple list page, import from iCal/CSV (v2), or manual entry
- Calendar integration: holiday dates are returned alongside timesheet entries; the frontend renders them as greyed-out / labelled days in react-calendar
- No time entries can be saved on a public holiday (soft warning, not hard block)

---

### 2.11 Copy Previous Week

- Button **"Copy from last week"** on the timesheet calendar view
- Behaviour:
  1. Fetch all entries from the 7 days prior to the currently displayed week
  2. Duplicate them into the current week (same weekday offsets, same project, activity, minutes, description)
  3. Skip days that already have entries (no overwrite); show a summary of what was copied / skipped
- Implemented as a dedicated API endpoint: `POST /api/timesheets/copy-week` with `{ source_week_start, target_week_start, employee_id }`

---

## 3. Database Changes (migration 002)

| Table | Change |
| --- | --- |
| `customers` | New table |
| `projects` | New table (FK → customers) |
| `project_allocations` | New table (FK → projects, employees) |
| `activity_types` | New table |
| `public_holidays` | New table |
| `timesheet_entries` | Add `project_id` (FK, nullable), `activity_type_id` (FK, nullable) |

---

## 4. API Changes (new endpoints)

| Method | Path | Description |
| --- | --- | --- |
| GET/POST | `/api/customers` | List / create customers |
| GET/PUT/DELETE | `/api/customers/{id}` | Read / update / deactivate |
| GET/POST | `/api/projects` | List / create projects |
| GET/PUT | `/api/projects/{id}` | Read / update project |
| PATCH | `/api/projects/{id}/status` | Change project status |
| GET/POST | `/api/projects/{id}/allocations` | List / set allocations |
| GET/POST | `/api/activity-types` | List / create activity types |
| GET/PUT | `/api/activity-types/{id}` | Read / update |
| GET/POST | `/api/public-holidays` | List / create holidays |
| DELETE | `/api/public-holidays/{id}` | Remove holiday |
| GET | `/api/dashboard` | Aggregated dashboard data |
| POST | `/api/timesheets/copy-week` | Copy previous week entries |

---

## 5. Frontend Pages & Components (new/modified)

| Page / Component | Status |
| --- | --- |
| `CustomersPage` | New |
| `ProjectsPage` | New |
| `ProjectDetail` (edit + allocations) | New |
| `ActivityTypesPage` | New (or merged into settings) |
| `PublicHolidaysPage` | New |
| `DashboardPage` | New |
| `HomePage` | Modified — add project + activity selectors |
| `TimesheetCalendar` | Modified — highlight public holidays |
| `ExportPanel` | Modified — add project/activity filter |
| Navbar / Menu | Modified — add new menu entries |

---

## 6. Out of Scope (v2)

- iCal/CSV import for public holidays
- Per-project configurable warning thresholds
- Role-based access control (planned for auth activation, separate spec)
- Invoice generation
