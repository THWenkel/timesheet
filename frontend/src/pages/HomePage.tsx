/* =============================================================================
   frontend/src/pages/HomePage.tsx

   The main timesheet entry page.

   Layout:
   ┌─────────────────────────────────────────────────────────────┐
   │  Logged-in user (change password / log out)                 │
   ├──────────────────────┬──────────────────────────────────────┤
   │  Calendar            │  Entry form (TimePicker + Description)│
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
import { TimesheetCalendar } from "@/components/TimesheetCalendar";
import { TimePickerInput } from "@/components/TimePickerInput";
import { DescriptionInput } from "@/components/DescriptionInput";
import { DaySummary } from "@/components/DaySummary";
import { WeekSummary } from "@/components/WeekSummary";
import { ExportPanel } from "@/components/ExportPanel";
import {
  useCalendarDates,
  useCreateEntry,
  useDaySummary,
  useUpdateEntry,
  useWeekSummary,
} from "@/hooks/useTimesheetEntries";
import { toISODateString, validateDailyLimit } from "@/utils/timeUtils";

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
  // --- The logged-in employee (timesheets are always entered for oneself) ---
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const selectedEmployee = user;

  // --- Calendar state ---
  const today = new Date();
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [calendarYear, setCalendarYear] = useState<number>(today.getFullYear());
  const [calendarMonth, setCalendarMonth] = useState<number>(today.getMonth() + 1);

  // --- Entry form state ---
  const [minutes, setMinutes] = useState<number>(60); // Default: 1 hour
  const [description, setDescription] = useState<string>("");
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

  const { createEntry, isSubmitting, error: saveError } = useCreateEntry();
  const { updateEntry, isSubmitting: isUpdating, error: updateError } = useUpdateEntry();

  // --- Validation ---
  // In create mode: all logged minutes count toward the limit.
  // In edit mode: subtract the editing entry’s original minutes so we
  // only count the “other” entries when validating the new value.
  const existingDayMinutes = daySummary?.total_minutes ?? 0;
  const otherDayMinutes =
    editingEntry !== null ? existingDayMinutes - editingEntry.minutes : existingDayMinutes;
  const dailyLimitError = validateDailyLimit(otherDayMinutes, minutes);

  // --- Handlers ---

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
    if (dailyLimitError !== null) return;

    if (editingEntry !== null) {
      // --- Update existing entry ---
      const success = await updateEntry(editingEntry.id, { minutes, description });
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

  const isAnySubmitting = isSubmitting || isUpdating;
  const isFormDisabled = selectedEmployee === null || selectedDate === null || isAnySubmitting;
  const canSave = !isFormDisabled && dailyLimitError === null;
  const activeError = editingEntry !== null ? updateError : saveError;

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
