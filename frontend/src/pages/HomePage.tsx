/* =============================================================================
   frontend/src/pages/HomePage.tsx

   The main timesheet entry page.

   Layout:
   ┌─────────────────────────────────────────────────────────────┐
   │  Employee Selector                                          │
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
import type { components } from "@/api/generated";
import { EmployeeSelector } from "@/components/EmployeeSelector";
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
  useWeekSummary,
} from "@/hooks/useTimesheetEntries";
import { toISODateString, validateDailyLimit } from "@/utils/timeUtils";

type EmployeeListItem = components["schemas"]["EmployeeListItem"];

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
  // --- Selected employee ---
  const [selectedEmployee, setSelectedEmployee] = useState<EmployeeListItem | null>(null);

  // --- Calendar state ---
  const today = new Date();
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [calendarYear, setCalendarYear] = useState<number>(today.getFullYear());
  const [calendarMonth, setCalendarMonth] = useState<number>(today.getMonth() + 1);

  // --- Entry form state ---
  const [minutes, setMinutes] = useState<number>(60); // Default: 1 hour
  const [description, setDescription] = useState<string>("");
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);

  // --- API hooks ---
  const {
    datesWithEntries,
    refetch: refetchCalendar,
  } = useCalendarDates(selectedEmployee?.id ?? null, calendarYear, calendarMonth);

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

  // --- Validation ---
  // Calculate how many minutes are already logged for the selected day
  // (from the day summary — excludes the current form value)
  const existingDayMinutes = daySummary?.total_minutes ?? 0;
  const dailyLimitError = validateDailyLimit(existingDayMinutes, minutes);

  // --- Handlers ---

  const handleEmployeeSelect = (employee: EmployeeListItem): void => {
    setSelectedEmployee(employee);
    setSelectedDate(null); // Reset date selection when changing employee
    setSaveSuccess(false);
  };

  const handleDateSelect = (date: Date): void => {
    setSelectedDate(date);
    setSaveSuccess(false);
    // Reset form to defaults for the new date
    setMinutes(60);
    setDescription("");
  };

  const handleMonthChange = (year: number, month: number): void => {
    setCalendarYear(year);
    setCalendarMonth(month);
  };

  const handleSave = async (): Promise<void> => {
    if (selectedEmployee === null || selectedDate === null) return;
    if (dailyLimitError !== null) return;

    const success = await createEntry({
      employee_id: selectedEmployee.id,
      entry_date: toISODateString(selectedDate),
      minutes,
      description,
    });

    if (success) {
      setSaveSuccess(true);
      setMinutes(60);
      setDescription("");
      // Refresh calendar highlighting and summaries
      refetchCalendar();
      refetchDay();
      refetchWeek();
    }
  };

  const isFormDisabled = selectedEmployee === null || selectedDate === null || isSubmitting;
  const canSave = !isFormDisabled && dailyLimitError === null;

  return (
    <main className="home-page">
      <h1 className="home-page__title">Timesheet</h1>

      {/* ── Employee Selector ── */}
      <section className="home-page__employee-section">
        <EmployeeSelector
          selectedEmployeeId={selectedEmployee?.id ?? null}
          onSelect={handleEmployeeSelect}
        />
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

              {saveError !== null && (
                <p className="error-message" role="alert">
                  {saveError}
                </p>
              )}

              {saveSuccess && (
                <p className="success-message" role="status">
                  Entry saved successfully!
                </p>
              )}

              <button
                type="button"
                className="home-page__save-btn"
                onClick={() => void handleSave()}
                disabled={!canSave}
                aria-busy={isSubmitting}
              >
                {isSubmitting ? "Saving…" : "Save Entry"}
              </button>

              {/* Day Summary */}
              <DaySummary daySummary={daySummary} isLoading={isDayLoading} />
            </>
          ) : (
            <p className="home-page__no-date-hint">
              {selectedEmployee !== null
                ? "← Select a date in the calendar to add or view entries."
                : "Select an employee above, then pick a date in the calendar."}
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
