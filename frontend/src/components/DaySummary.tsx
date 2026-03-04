/* =============================================================================
   frontend/src/components/DaySummary.tsx

   Displays all timesheet entries for the selected day and the day total.
   ============================================================================= */

import type { components } from "@/api/generated";

type DaySummaryData = components["schemas"]["DaySummary"];

interface DaySummaryProps {
  /** Day summary data from the API — null means no date is selected */
  daySummary: DaySummaryData | null;
  /** True while the API request is loading */
  isLoading: boolean;
}

/**
 * Day summary panel showing all individual entries and the total for the selected date.
 *
 * Shows a list of entries with their duration and description.
 * Displays the total duration at the bottom.
 * Shows a loading indicator while data is being fetched.
 */
export function DaySummary({ daySummary, isLoading }: DaySummaryProps): React.JSX.Element {
  if (isLoading) {
    return (
      <div className="day-summary day-summary--loading">
        <p>Loading entries…</p>
      </div>
    );
  }

  if (daySummary === null) {
    return (
      <div className="day-summary day-summary--empty">
        <p>Select a date to view entries.</p>
      </div>
    );
  }

  const { entry_date, entries, total_minutes, total_display } = daySummary;

  return (
    <div className="day-summary">
      <h3 className="day-summary__title">
        Entries for{" "}
        <time dateTime={entry_date}>
          {new Date(entry_date + "T00:00:00").toLocaleDateString("de-DE", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
          })}
        </time>
      </h3>

      {entries.length === 0 ? (
        <p className="day-summary__no-entries">No entries for this day.</p>
      ) : (
        <table className="day-summary__table" aria-label="Day entries">
          <thead>
            <tr>
              <th scope="col">Duration</th>
              <th scope="col">Description</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr key={entry.id}>
                <td className="day-summary__duration">{entry.hours_display}</td>
                <td className="day-summary__description">
                  {entry.description.length > 0 ? entry.description : <em>No description</em>}
                </td>
              </tr>
            ))}
          </tbody>
          {total_minutes > 0 && (
            <tfoot>
              <tr className="day-summary__total-row">
                <td>
                  <strong>{total_display}</strong>
                </td>
                <td>
                  <strong>Total ({total_minutes} min)</strong>
                </td>
              </tr>
            </tfoot>
          )}
        </table>
      )}
    </div>
  );
}
