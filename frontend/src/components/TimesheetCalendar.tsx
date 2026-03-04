/* =============================================================================
   frontend/src/components/TimesheetCalendar.tsx

   React-Calendar wrapper with dark-blue highlighting for days that have entries.

   The `tileClassName` prop is used to apply the CSS class 'has-entry' to
   any date that appears in the `datesWithEntries` array. The CSS for
   .has-entry is defined in App.css.

   Navigating to a different month triggers `onMonthChange` so the parent
   can reload the entry dates for the new month.
   ============================================================================= */

import Calendar from "react-calendar";
import "react-calendar/dist/Calendar.css";
import type { components } from "@/api/generated";
import { toISODateString } from "@/utils/timeUtils";

type DateWithEntries = components["schemas"]["DateWithEntries"];

// react-calendar uses Value = Date | [Date, Date] | null
type CalendarValue = Date | null;

interface TimesheetCalendarProps {
  /** Currently selected date */
  selectedDate: Date | null;
  /** Called when the user clicks a date tile */
  onDateSelect: (date: Date) => void;
  /** Called when the calendar navigates to a new month — provides year and month (1-12) */
  onMonthChange: (year: number, month: number) => void;
  /** Dates with entries to highlight in dark blue */
  datesWithEntries: DateWithEntries[];
}

/**
 * Calendar component with entry highlighting.
 *
 * Users click a day to select it. Days with existing timesheet entries
 * are highlighted in dark blue via the 'has-entry' CSS class.
 */
export function TimesheetCalendar({
  selectedDate,
  onDateSelect,
  onMonthChange,
  datesWithEntries,
}: TimesheetCalendarProps): React.JSX.Element {
  // Build a Set of ISO date strings for O(1) lookup when rendering tiles
  const entryDateSet = new Set(datesWithEntries.map((d) => d.entry_date));

  /**
   * Determine the CSS class for each calendar tile.
   * Returns 'has-entry' for tiles that have entries, undefined otherwise.
   */
  const getTileClassName = ({
    date,
    view,
  }: {
    date: Date;
    view: string;
  }): string | null => {
    if (view !== "month") return null;
    const isoDate = toISODateString(date);
    return entryDateSet.has(isoDate) ? "has-entry" : null;
  };

  /**
   * Handle calendar navigation (prev/next month arrows, year selection).
   * Extract year and month from the new active start date and notify the parent.
   */
  const handleActiveStartDateChange = ({
    activeStartDate,
  }: {
    activeStartDate: Date | null;
  }): void => {
    if (activeStartDate !== null) {
      onMonthChange(
        activeStartDate.getFullYear(),
        activeStartDate.getMonth() + 1, // getMonth() is 0-indexed
      );
    }
  };

  /**
   * Handle day click — pass the selected Date to the parent.
   * We cast the Calendar's value to Date since we use selectRange={false}.
   */
  const handleChange = (value: CalendarValue | [CalendarValue, CalendarValue]): void => {
    const date = Array.isArray(value) ? value[0] : value;
    if (date instanceof Date) {
      onDateSelect(date);
    }
  };

  return (
    <div className="timesheet-calendar">
      <Calendar
        value={selectedDate}
        onChange={handleChange}
        onActiveStartDateChange={handleActiveStartDateChange}
        tileClassName={getTileClassName}
        locale="de-DE"
        selectRange={false}
      />
    </div>
  );
}
