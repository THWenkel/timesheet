# Timesheet Administration

WPF administration client for maintaining Timesheet employees, customers, and projects.
The client uses the FastAPI backend and does not connect to SQL Server directly.

## Database migration

Apply `backend/migrations/002_projects.sql` with the existing migration CLI before using
project management. It creates customers, projects, and employee-project assignments.
Afterwards, apply `backend/migrations/003_customer_notes.sql` to add customer notes:

Migration `backend/migrations/004_customer_details.sql` adds address, purchasing,
supplier, logistics, and contact-person fields without changing existing values.
Migration `backend/migrations/005_country_codes2.sql` imports the ISO codes. Migration
`backend/migrations/006_country_code2_names.sql` corrects the table name to
`dbo.CountryCode2` and adds the English country name for all 249 entries.
Migration `backend/migrations/007_project_commercial_details.sql` moves purchase number,
unloading point, and consuming plant from customers to projects and adds project-specific
contact fields. Existing values are copied to related projects before customer columns
are removed.

```powershell
cd backend
python cli.py --password "YOUR_DATABASE_PASSWORD" migrate
python cli.py --password "YOUR_DATABASE_PASSWORD" status
```

## Build and run

```powershell
dotnet build admin/Timesheet.Admin/Timesheet.Admin.csproj
dotnet run --project admin/Timesheet.Admin/Timesheet.Admin.csproj
```

The backend must be running. By default the client uses `http://localhost:8000/`.
Override that address when necessary:

```powershell
$env:TIMESHEET_API_URL = "http://server:8000/"
dotnet run --project admin/Timesheet.Admin/Timesheet.Admin.csproj
```

Deleting an employee is deliberately implemented as deactivation so existing
timesheet entries and audit references remain intact.

## Customer management

Use the **Kunden** button in the main window to list, create, edit, or deactivate
customers. Customer records contain a unique name, two street lines, postal code,
city, country, supplier number, general contact name, phone, email, notes, and an
active status.
Deactivated customers remain linked to existing projects but are omitted from the
active customer selection.

The country field is an editable, filtered dropdown backed by `CountryCode2`. Type
part of a two-letter code or country name to reduce the list; only a code from the
lookup table can be saved. Existing customers with an empty country remain readable
and require a valid country code the next time they are edited.

## Project management

Use the **Projekte** button in the main window to create or edit projects. A project
contains its name, optional description, customer, budget, budget unit, date range,
status, purchase number, unloading point, consuming plant, project-specific contact
details, and assigned employees. Customers must be created in customer administration
before they can be selected for a project.

Selecting an employee in the main window loads that employee's assigned projects into
the lower grid. Budgets are stored either as hours or person-days; no implicit conversion
is performed until a standard number of hours per person-day has been agreed.