/* =============================================================================
   frontend/src/components/WeekSummary.tsx

   Displays a Mon–Sun week summary table with per-day totals and a week total.
   ============================================================================= */

import type { components } from "@/api/generated";

type WeekSummaryData = components["schemas"]["WeekSummary"];

interface WeekSummaryProps {
  /** Week summary data from the API — null means no date is selected */
  weekSummary: WeekSummaryData | null;
  /** True while the API request is loading */
  isLoading: boolean;
}

/**
 * Weekly summary table showing Mon–Sun totals and the grand total for the week.
 *
 * Highlights days that have entries.
 * The week range is derived from the server response (week_start, week_end).
 */
export function WeekSummary({ weekSummary, isLoading }: WeekSummaryProps): React.JSX.Element {
  if (isLoading) {
    return (
      <div className="week-summary week-summary--loading">
        <p>Loading week summary…</p>
      </div>
    );
  }

  if (weekSummary === null) {
    return (
      <div className="week-summary week-summary--empty">
        <p>Select a date to view the weekly summary.</p>
      </div>
    );
  }

  const { week_start, week_end, days, week_total_minutes, week_total_display } = weekSummary;

  return (
    <div className="week-summary">
      <h3 className="week-summary__title">
        Week Summary:{" "}
        <time dateTime={week_start}>
          {new Date(week_start + "T00:00:00").toLocaleDateString("de-DE", {
            day: "2-digit",
            month: "2-digit",
          })}
        </time>
        {" – "}
        <time dateTime={week_end}>
          {new Date(week_end + "T00:00:00").toLocaleDateString("de-DE", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
          })}
        </time>
      </h3>

      <table className="week-summary__table" aria-label="Weekly summary">
        <thead>
          <tr>
            <th scope="col">Day</th>
            <th scope="col">Date</th>
            <th scope="col">Total</th>
          </tr>
        </thead>
        <tbody>
          {days.map((day) => (
            <tr
              key={day.entry_date}
              className={day.has_entries ? "week-summary__row--has-entries" : ""}
            >
              <td>{day.day_name}</td>
              <td>
                <time dateTime={day.entry_date}>
                  {new Date(day.entry_date + "T00:00:00").toLocaleDateString("de-DE", {
                    day: "2-digit",
                    month: "2-digit",
                  })}
                </time>
              </td>
              <td className="week-summary__duration">
                {day.has_entries ? (
                  <strong>{day.total_display}</strong>
                ) : (
                  <span className="week-summary__no-entries">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="week-summary__total-row">
            <td colSpan={2}>
              <strong>Week Total</strong>
            </td>
            <td className="week-summary__duration">
              <strong>
                {week_total_display}
                {week_total_minutes > 0 && (
                  <span className="week-summary__minutes"> ({week_total_minutes} min)</span>
                )}
              </strong>
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
