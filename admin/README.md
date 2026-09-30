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

Employees are normally **deactivated**, so existing timesheet entries and audit
references remain intact. The **Löschen** button removes an employee for good, but
only if the employee has no timesheet entries (the API refuses it otherwise).

### Installing on the admin PCs

```powershell
dotnet publish admin/Timesheet.Admin/Timesheet.Admin.csproj -c Release -r win-x64 --self-contained false -o publish
```

Copy the `publish` folder to the admin PCs (the .NET 10 Desktop Runtime must be installed there)
and start `Timesheet.Admin.exe`. The API address comes from the environment variable
`TIMESHEET_API_URL`, for production `https://cloudserver2.hopto.org/timesheet/` (set it once per
PC with `setx TIMESHEET_API_URL "https://cloudserver2.hopto.org/timesheet/"`, then restart the
tool). Keep the trailing slash, otherwise the `/timesheet` path is lost.

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

## Datensicherung und Wiederherstellung

Hauptfenster → **Sicherung**. Tabellen per Checkbox auswählen.

- **Sicherung in Datenbank:** kopiert die Tabellen in ihre `*_backup`-Tabellen (Migration `009_backup_tables.sql`). Der alte Inhalt einer Sicherungstabelle wird erst ersetzt, wenn die neue Sicherung vollständig geschrieben ist (eine Transaktion).
- **Sicherung in Dateien:** CSV und/oder JSON, eine Datei pro Tabelle: `<tabelle>_<yyyyMMdd_HHmmss>.csv|json`. Bestehende Dateien werden nie überschrieben. Der zuletzt gewählte Ordner wird in `%APPDATA%\Timesheet.Admin\settings.json` gemerkt.
- **Wiederherstellung** (aus `*_backup` oder aus Dateien): überschreibt vorhandene Datensätze (Abgleich über den Schlüssel), fügt fehlende ein und löscht nie etwas. Vorher wird der aktuelle Stand als JSON-Sicherheitskopie in einen Ordner geschrieben, die Bestätigung erfolgt zweistufig (Ja/Nein mit Auflistung, dann Eingabe von `WIEDERHERSTELLEN`).

Jede neue Migration, die Tabellen oder Spalten anlegt, muss die passende `*_backup`-Tabelle im selben Skript anlegen bzw. erweitern und die Tabelle in `TABLE_SPECS` (`backend/app/services/backup_service.py`) eintragen.

## Anmeldung und Benutzer

- Ist auf dem Server `AUTH_ENABLED=true`, öffnet sich beim Start ein Login-Fenster. Nur Benutzer mit dem Haken **Administrator** kommen hinein. Nach einem Reset verlangt das Fenster sofort ein neues Passwort. Ist `AUTH_ENABLED=false` (Ersteinrichtung), entfällt der Login.
- Benutzer bearbeiten: Benutzername (Login) und Administrator-Recht. **Einmalpasswort** setzt ein Zufallspasswort, kopiert es in die Zwischenablage und zeigt es einmalig an. Der Benutzer muss es beim ersten Login ändern.
- Die Sitzung ist ein Cookie (Standard 8 Stunden). Über `http://` funktioniert sie nur, wenn der Server `COOKIE_SECURE=false` hat (nur lokale Entwicklung); in Produktion `TIMESHEET_API_URL=https://...` setzen.
- Migration `010_employee_auth.sql`: Login-Spalten in `employees` und `employees_backup`.
