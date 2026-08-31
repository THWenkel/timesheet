# TESTING.md — Inline Entry Editing Feature

Manual + Playwright test protocol for the **inline timesheet entry editing** feature.

---

## Prerequisites

Both servers must be running before testing.

### Start Backend

```powershell
cd C:\Develop\timesheet\backend
.\.venv\Scripts\activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify: `http://localhost:8000/docs` should load the Swagger UI.

### Start Frontend

```powershell
cd C:\Develop\timesheet\frontend
npm run dev
```

Verify: `http://localhost:5173/` should load the Timesheet app.

### Verify Backend Health

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/employees/" -Method GET | ConvertTo-Json
```

Expected: JSON response containing `"display_name": "Thomas Wenkel"`.

---

## Test Setup

- **Employee:** Thomas Wenkel
- **Test date:** 28.04.2026
- **Pre-condition:** Entry for 28.04.2026 exists: `08:00` / `"div. Calls, and BUGFIXING"`

Verify via API:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/timesheets/day?employee_id=1&entry_date=2026-04-28" -Method GET | ConvertTo-Json -Depth 5
```

Expected: one entry with `minutes: 480`, `description: "div. Calls, and BUGFIXING"`.

---

## Test Cases

---

### TC-01 — Page loads and employee dropdown is populated

**Steps:**

1. Open `http://localhost:5173/`
2. Wait for the employee dropdown to load (≤ 2 seconds)

**Expected:**

- Page title = "Timesheet"
- Dropdown contains the option "Thomas Wenkel"
- Dropdown shows "— Select employee —" as default (nothing selected)
- No console errors related to the API

---

### TC-02 — Select employee and date, form appears in create mode

**Steps:**

1. Select "Thomas Wenkel" from the dropdown
2. Click on **28. April 2026** in the calendar

**Expected:**

- Heading "Dienstag, 28. April 2026" appears above the form
- Duration picker is visible and defaults to `01:00`
- Description field is empty
- Button label is **"Save Entry"** (not "Update Entry")
- **No "Cancel" button** is visible
- **No amber edit banner** is visible
- Day Summary section shows the existing entry row

---

### TC-03 — Entry row is clickable and shows pointer cursor

**Steps:**

1. (After TC-02) Look at the entry table below the form
2. Hover over the entry row "08:00 div. Calls, and BUGFIXING"

**Expected:**

- Row cursor changes to pointer on hover
- Row shows a subtle blue-grey hover background

---

### TC-04 — Clicking an entry row loads data into the form

**Steps:**

1. Click the entry row "08:00 div. Calls, and BUGFIXING"

**Expected:**

- Duration picker changes to **08:00** (value = 480 minutes)
- Description field shows **"div. Calls, and BUGFIXING"**
- The clicked row gets a **blue highlight** (`background-color: #dbeafe`, blue outline)
- An **amber banner** appears: *"Editing entry — modify the fields above and click "Update Entry" to save."*
- Button label changes to **"Update Entry"**
- A **"Cancel"** button appears next to it
- The "Save Entry" label is **no longer visible**

---

### TC-05 — Update Entry saves the changes to the API

**Steps:**

1. (After TC-04 — entry is loaded in form)
2. Change duration to **07:30** (450 minutes)
3. Change description to **"div. Calls, Meetings and BUGFIXING"**
4. Click **"Update Entry"**
5. Wait for the save to complete

**Expected:**

- Green success message: **"Entry updated successfully!"**
- Edit banner disappears
- Cancel button disappears; button label returns to "Save Entry"
- Row highlight clears
- Duration picker resets to `01:00` (60 minutes)
- Description field clears to empty
- The entry table refreshes and shows the updated values: **07:30** / **"div. Calls, Meetings and BUGFIXING"**
- Week summary row for Tuesday 28.04 updates to **07:30**

**API verification:**

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/timesheets/day?employee_id=1&entry_date=2026-04-28" -Method GET | ConvertTo-Json -Depth 5
```

Expected: `minutes: 450`, `description: "div. Calls, Meetings and BUGFIXING"`, `updated_at` timestamp is recent.

---

### TC-06 — Cancel discards changes and resets the form

**Steps:**

1. Click the entry row to enter edit mode
2. Change duration to **02:00** (do NOT save)
3. Click **"Cancel"**

**Expected:**

- Edit banner disappears
- Button label returns to **"Save Entry"**
- Cancel button disappears
- Row highlight clears
- Duration picker resets to **01:00** (default)
- Description field is **empty**
- The entry in the table is **unchanged** (no API call was made)

---

### TC-07 — Selecting a different date clears edit mode (no stale data)

**Steps:**

1. Click the entry row on 28.04 to enter edit mode
2. Verify the amber edit banner is visible
3. Click on **27. April 2026** in the calendar

**Expected:**

- Edit mode immediately clears
- No amber edit banner
- Button label is **"Save Entry"**
- No Cancel button
- Duration resets to `01:00`, description is empty
- The form shows the context of the new date (Apr 27)

---

### TC-08 — Creating a new entry (existing flow unchanged)

**Steps:**

1. Click a date with **no existing entries** (e.g., 25. April 2026)
2. Verify "No entries for this day." message appears
3. Set duration to **04:00** (240 minutes)
4. Enter description **"Team standup"**
5. Click **"Save Entry"**

**Expected:**

- Green success message: **"Entry saved successfully!"** (not "updated")
- No edit banner at any point
- Duration resets to `01:00`, description clears
- New row appears in the entry table: **"Edit entry: 04:00 – Team standup"**
- The new row is immediately **clickable** for future editing
- Calendar highlights the date (dark blue tile)

**Cleanup** (delete the test entry):

```powershell
$day = Invoke-RestMethod -Uri "http://localhost:8000/api/timesheets/day?employee_id=1&entry_date=2026-04-25" -Method GET
Invoke-RestMethod -Uri "http://localhost:8000/api/timesheets/$($day.entries[0].id)" -Method DELETE
```

---

## Restore Test Data

After running TC-05 (which changes the Apr 28 entry), restore the original values:

```powershell
$body = '{"minutes": 480, "description": "div. Calls, and BUGFIXING"}'
Invoke-RestMethod -Uri "http://localhost:8000/api/timesheets/68" -Method PUT -ContentType "application/json" -Body $body | ConvertTo-Json
```

---

## Test Results (28.04.2026 run)

| TC    | Description                        | Result   |
|------ |------------------------------------|----------|
| TC-01 | Page loads, dropdown populated     | ✅ PASS  |
| TC-02 | Select employee + date, create mode| ✅ PASS  |
| TC-03 | Entry row has pointer cursor       | ✅ PASS  |
| TC-04 | Click row loads data + edit mode   | ✅ PASS  |
| TC-05 | Update Entry saves to API          | ✅ PASS  |
| TC-06 | Cancel resets form, no API call    | ✅ PASS  |
| TC-07 | Date change clears edit mode       | ✅ PASS  |
| TC-08 | Create new entry (unchanged flow)  | ✅ PASS  |
