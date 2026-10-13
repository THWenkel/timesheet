/* =============================================================================
   frontend/src/pages/HomePage.tsx

   The main timesheet entry page.

   Layout:
   ┌─────────────────────────────────────────────────────────────┐
   │  Logged-in user (change password / log out)                 │
   ├──────────────────────┬──────────────────────────────────────┤
   │  Calendar            │  Entry form (Project + TimePicker +  │
   │                      │  Description)                        │
   │  (react-calendar)    │  + Save button                       │
   │                      │  + Day Summary                       │
   │                      │  + Week Summary                      │
   ├──────────────────────┴──────────────────────────────────────┤
   │  Export Panel                                               │
   └─────────────────────────────────────────────────────────────┘
   ============================================================================= */

import { useState } from "react";
import { Link, useNavigate } from "react-router";
import type { components } from "@/api/generated";
import { useAuth } from "@/auth/AuthContext";
import { EmployeeSelector } from "@/components/EmployeeSelector";
import { TimesheetCalendar } from "@/components/TimesheetCalendar";
import { TimePickerInput } from "@/components/TimePickerInput";
import { DescriptionInput } from "@/components/DescriptionInput";
import { DaySummary } from "@/components/DaySummary";
import { WeekSummary } from "@/components/WeekSummary";
import { ProjectSelect } from "@/components/ProjectSelect";
import { ExportPanel } from "@/components/ExportPanel";
import { useEmployeeProjects } from "@/hooks/useEmployeeProjects";
import {
  useCalendarDates,
  useCreateEntry,
  useDaySummary,
  useDeleteEntry,
  useUpdateEntry,
  useWeekSummary,
} from "@/hooks/useTimesheetEntries";
import { toISODateString, validateDailyLimit } from "@/utils/timeUtils";

type EmployeeListItem = components["schemas"]["EmployeeListItem"];
type TimesheetEntryRead = components["schemas"]["TimesheetEntryRead"];

/**
 * Main timesheet page.
 *
 * Manages the top-level state:
 *   - Which employee is selected
 *   - Which date is selected in the calendar
 *   - The current calendar month (for fetching entry dates)
 *   - Form state (minutes, description)
 */
export function HomePage(): React.JSX.Element {
  // --- Whose timesheet is shown: the logged-in employee, or (administrators only) a chosen one ---
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [chosenEmployee, setChosenEmployee] = useState<EmployeeListItem | null>(null);
  const isAdmin = user?.is_admin === true;
  const selectedEmployee = isAdmin && chosenEmployee !== null ? chosenEmployee : user;
  const isOwnTimesheet = selectedEmployee?.id === user?.id;

  // --- Calendar state ---
  const today = new Date();
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [calendarYear, setCalendarYear] = useState<number>(today.getFullYear());
  const [calendarMonth, setCalendarMonth] = useState<number>(today.getMonth() + 1);

  // --- Entry form state ---
  const [minutes, setMinutes] = useState<number>(60); // Default: 1 hour
  const [description, setDescription] = useState<string>("");
  // Chosen project; the effective value is derived below because it depends on the project list
  const [chosenProjectId, setChosenProjectId] = useState<number | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);

  // --- Edit mode: null = create mode, non-null = editing an existing entry ---
  const [editingEntry, setEditingEntry] = useState<TimesheetEntryRead | null>(null);
  // Track what kind of save just happened for the success message
  const [lastSaveWasUpdate, setLastSaveWasUpdate] = useState<boolean>(false);

  // --- API hooks ---
  const { datesWithEntries, refetch: refetchCalendar } = useCalendarDates(
    selectedEmployee?.id ?? null,
    calendarYear,
    calendarMonth,
  );

  const {
    daySummary,
    isLoading: isDayLoading,
    refetch: refetchDay,
  } = useDaySummary(selectedEmployee?.id ?? null, selectedDate);

  const {
    weekSummary,
    isLoading: isWeekLoading,
    refetch: refetchWeek,
  } = useWeekSummary(selectedEmployee?.id ?? null, selectedDate);

  const { projects, isLoading: isProjectsLoading } = useEmployeeProjects(
    selectedEmployee?.id ?? null,
  );
  // One project: always preselected. Several: the choice must be one of them. None: no booking.
  const onlyProject = projects.length === 1 ? projects[0] : undefined;
  const projectId =
    onlyProject !== undefined
      ? onlyProject.id
      : projects.some((p) => p.id === chosenProjectId)
        ? chosenProjectId
        : null;
  const hasNoProject = !isProjectsLoading && projects.length === 0;

  const { createEntry, isSubmitting, error: saveError } = useCreateEntry();
  const { updateEntry, isSubmitting: isUpdating, error: updateError } = useUpdateEntry();
  const { deleteEntry, isDeleting, error: deleteError } = useDeleteEntry();

  // --- Validation ---
  // In create mode: all logged minutes count toward the limit.
  // In edit mode: subtract the editing entry’s original minutes so we
  // only count the “other” entries when validating the new value.
  const existingDayMinutes = daySummary?.total_minutes ?? 0;
  const otherDayMinutes =
    editingEntry !== null ? existingDayMinutes - editingEntry.minutes : existingDayMinutes;
  const dailyLimitError = validateDailyLimit(otherDayMinutes, minutes);

  // --- Handlers ---

  const handleEmployeeSelect = (employee: EmployeeListItem): void => {
    setChosenEmployee(employee);
    setSelectedDate(null);
    setEditingEntry(null);
    setChosenProjectId(null);
    setMinutes(60);
    setDescription("");
    setSaveSuccess(false);
  };

  const handleLogout = async (): Promise<void> => {
    await logout();
    void navigate("/login", { replace: true });
  };

  const handleDateSelect = (date: Date): void => {
    setSelectedDate(date);
    setEditingEntry(null);
    setSaveSuccess(false);
    setLastSaveWasUpdate(false);
    // Reset form to defaults for the new date
    setMinutes(60);
    setDescription("");
  };

  const handleMonthChange = (year: number, month: number): void => {
    setCalendarYear(year);
    setCalendarMonth(month);
  };

  const handleEditEntry = (entry: TimesheetEntryRead): void => {
    setEditingEntry(entry);
    // Legacy entries have no project: null forces a choice before saving
    setChosenProjectId(entry.project_id ?? null);
    setMinutes(entry.minutes);
    setDescription(entry.description);
    setSaveSuccess(false);
  };

  const handleCancelEdit = (): void => {
    setEditingEntry(null);
    setMinutes(60);
    setDescription("");
    setSaveSuccess(false);
    setLastSaveWasUpdate(false);
  };

  const handleSave = async (): Promise<void> => {
    if (selectedEmployee === null || selectedDate === null) return;
    if (dailyLimitError !== null || projectId === null) return;

    if (editingEntry !== null) {
      // --- Update existing entry ---
      const success = await updateEntry(editingEntry.id, {
        project_id: projectId,
        minutes,
        description,
      });
      if (success) {
        setLastSaveWasUpdate(true);
        setSaveSuccess(true);
        setEditingEntry(null);
        setMinutes(60);
        setDescription("");
        refetchCalendar();
        refetchDay();
        refetchWeek();
      }
    } else {
      // --- Create new entry ---
      const success = await createEntry({
        employee_id: selectedEmployee.id,
        project_id: projectId,
        entry_date: toISODateString(selectedDate),
        minutes,
        description,
      });
      if (success) {
        setLastSaveWasUpdate(false);
        setSaveSuccess(true);
        setMinutes(60);
        setDescription("");
        refetchCalendar();
        refetchDay();
        refetchWeek();
      }
    }
  };

  const handleDelete = async (): Promise<void> => {
    if (editingEntry === null) return;
    const label = `${editingEntry.hours_display}${
      editingEntry.description.length > 0 ? ` – ${editingEntry.description}` : ""
    }`;
    if (!window.confirm(`Delete this entry permanently?

${label}`)) return;

    const success = await deleteEntry(editingEntry.id);
    if (success) {
      setLastSaveWasUpdate(false);
      setSaveSuccess(false);
      setEditingEntry(null);
      setMinutes(60);
      setDescription("");
      refetchCalendar();
      refetchDay();
      refetchWeek();
    }
  };

  const isAnySubmitting = isSubmitting || isUpdating || isDeleting;
  const isFormDisabled =
    selectedEmployee === null || selectedDate === null || isAnySubmitting || hasNoProject;
  const canSave = !isFormDisabled && dailyLimitError === null && projectId !== null;
  const activeError = deleteError ?? (editingEntry !== null ? updateError : saveError);

  return (
    <main className="home-page">
      <h1 className="home-page__title">Timesheet</h1>

      {/* ── Logged-in user ── */}
      <section className="home-page__employee-section home-page__user-bar">
        <span>
          Signed in as <strong>{user?.display_name}</strong>
        </span>
        <Link to="/change-password">Change password</Link>
        <button type="button" className="home-page__cancel-btn" onClick={() => void handleLogout()}>
          Log out
        </button>
      </section>

      {/* ── Administrators: choose whose timesheet to view and edit ── */}
      {isAdmin && (
        <section className="home-page__employee-section">
          <EmployeeSelector
            selectedEmployeeId={selectedEmployee?.id ?? null}
            onSelect={handleEmployeeSelect}
          />
          {!isOwnTimesheet && (
            <p className="home-page__edit-banner" role="status">
              You are viewing and editing the timesheet of{" "}
              <strong>{selectedEmployee?.display_name}</strong>.
            </p>
          )}
        </section>
      )}

      {/* ── Main content grid ── */}
      <div className="home-page__grid">
        {/* Left column: Calendar */}
        <section className="home-page__calendar-section">
          <TimesheetCalendar
            selectedDate={selectedDate}
            onDateSelect={handleDateSelect}
            onMonthChange={handleMonthChange}
            datesWithEntries={datesWithEntries}
          />
        </section>

        {/* Right column: Form + Summaries */}
        <section className="home-page__form-section">
          {selectedDate !== null ? (
            <>
              <h2 className="home-page__selected-date">
                {selectedDate.toLocaleDateString("de-DE", {
                  weekday: "long",
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </h2>

              <ProjectSelect
                id="entry-project"
                projects={projects}
                value={projectId}
                onChange={setChosenProjectId}
                isLoading={isProjectsLoading}
                disabled={isFormDisabled}
              />

              <TimePickerInput
                value={minutes}
                onChange={setMinutes}
                errorMessage={dailyLimitError}
                disabled={isFormDisabled}
              />

              <DescriptionInput
                value={description}
                onChange={setDescription}
                disabled={isFormDisabled}
              />

              {editingEntry !== null && (
                <p className="home-page__edit-banner" role="status">
                  Editing entry — modify the fields above and click “Update Entry” to save.
                </p>
              )}

              {activeError !== null && (
                <p className="error-message" role="alert">
                  {activeError}
                </p>
              )}

              {saveSuccess && (
                <p className="success-message" role="status">
                  {lastSaveWasUpdate ? "Entry updated successfully!" : "Entry saved successfully!"}
                </p>
              )}

              <div className="home-page__btn-group">
                <button
                  type="button"
                  className="home-page__save-btn"
                  onClick={() => void handleSave()}
                  disabled={!canSave}
                  aria-busy={isAnySubmitting}
                >
                  {isAnySubmitting
                    ? "Saving…"
                    : editingEntry !== null
                      ? "Update Entry"
                      : "Save Entry"}
                </button>

                {editingEntry !== null && (
                  <button
                    type="button"
                    className="home-page__cancel-btn"
                    onClick={handleCancelEdit}
                    disabled={isAnySubmitting}
                  >
                    Cancel
                  </button>
                )}

                {editingEntry !== null && (
                  <button
                    type="button"
                    className="home-page__delete-btn"
                    onClick={() => void handleDelete()}
                    disabled={isAnySubmitting}
                  >
                    Delete Entry
                  </button>
                )}
              </div>

              {/* Day Summary */}
              <DaySummary
                daySummary={daySummary}
                isLoading={isDayLoading}
                onEditEntry={handleEditEntry}
                editingEntryId={editingEntry?.id ?? null}
              />
            </>
          ) : (
            <p className="home-page__no-date-hint">
              ← Select a date in the calendar to add or view entries.
            </p>
          )}

          {/* Week Summary — shown when a date is selected */}
          {selectedDate !== null && (
            <WeekSummary weekSummary={weekSummary} isLoading={isWeekLoading} />
          )}
        </section>
      </div>

      {/* ── Export Panel ── */}
      <section className="home-page__export-section">
        <ExportPanel employeeId={selectedEmployee?.id ?? null} />
      </section>
    </main>
  );
}
