// =============================================================================
// frontend/src/utils/timeUtils.ts
//
// Utility functions for time conversion and validation.
//
// All time values in the API are stored and transmitted as integer minutes.
// These utilities handle converting between minutes and display formats,
// generating time slot options for the TimePicker dropdown, and validating
// that daily totals don't exceed 24 hours.
// =============================================================================

/**
 * Convert an integer minute count to a 'hh:mm' display string.
 *
 * @param minutes - Total duration in minutes (must be >= 0)
 * @returns Zero-padded 'hh:mm' string, e.g. 90 → '01:30'
 *
 * @example
 * minutesToDisplay(90)   // → '01:30'
 * minutesToDisplay(480)  // → '08:00'
 * minutesToDisplay(0)    // → '00:00'
 */
export function minutesToDisplay(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

/**
 * Parse a 'hh:mm' string into an integer minute count.
 *
 * @param display - Time string in 'hh:mm' format
 * @returns Total minutes as an integer
 * @throws Error if the string is not in a valid 'hh:mm' format
 *
 * @example
 * displayToMinutes('01:30')  // → 90
 * displayToMinutes('08:00')  // → 480
 */
export function displayToMinutes(display: string): number {
  const parts = display.split(":");
  if (parts.length !== 2) {
    throw new Error(`Invalid time format: '${display}'. Expected 'hh:mm'.`);
  }
  const [hoursStr, minutesStr] = parts;
  const hours = parseInt(hoursStr ?? "0", 10);
  const minutes = parseInt(minutesStr ?? "0", 10);

  if (isNaN(hours) || isNaN(minutes)) {
    throw new Error(`Invalid time format: '${display}'. Hours and minutes must be numbers.`);
  }

  return hours * 60 + minutes;
}

/**
 * Generate all valid time slot options in 15-minute steps from 00:00 to 23:45.
 *
 * Returns an array of objects with `minutes` (integer) and `label` (hh:mm string)
 * suitable for populating a <select> dropdown.
 *
 * @returns Array of { minutes: number, label: string } objects (96 items total)
 *
 * @example
 * generateTimeSlots()[0]  // → { minutes: 15, label: '00:15' }
 * generateTimeSlots()[3]  // → { minutes: 60, label: '01:00' }
 */
export function generateTimeSlots(): { minutes: number; label: string }[] {
  const slots: { minutes: number; label: string }[] = [];
  // 15 minutes is the minimum; 23:45 (1425 minutes) is the maximum for a single entry
  for (let m = 15; m <= 1425; m += 15) {
    slots.push({ minutes: m, label: minutesToDisplay(m) });
  }
  return slots;
}

/**
 * Validate that adding `newMinutes` to an existing daily total would not
 * exceed 1440 minutes (24 hours).
 *
 * @param existingMinutes - Minutes already logged for the day (excluding current entry)
 * @param newMinutes      - Proposed minutes to add
 * @returns null if valid, or an error message string if the limit would be exceeded
 *
 * @example
 * validateDailyLimit(900, 480)   // → null (1380 ≤ 1440)
 * validateDailyLimit(900, 600)   // → 'Adding 10h 00m would exceed 24h...'
 */
export function validateDailyLimit(
  existingMinutes: number,
  newMinutes: number,
): string | null {
  const total = existingMinutes + newMinutes;
  if (total > 1440) {
    const available = 1440 - existingMinutes;
    return (
      `Adding ${minutesToDisplay(newMinutes)} would exceed 24h for this day. ` +
      `Already logged: ${minutesToDisplay(existingMinutes)}. ` +
      `Available: ${minutesToDisplay(available)}.`
    );
  }
  return null;
}

/**
 * Format a Date object as an ISO date string 'YYYY-MM-DD'.
 *
 * Uses local date parts (not UTC) to avoid timezone offset issues.
 *
 * @param date - A JavaScript Date object
 * @returns ISO date string, e.g. '2026-03-04'
 */
export function toISODateString(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/**
 * Get the Monday (start) and Sunday (end) of the week containing the given date.
 *
 * @param date - Any date within the target week
 * @returns { weekStart: Date, weekEnd: Date } where weekStart is Mon, weekEnd is Sun
 */
export function getWeekBounds(date: Date): { weekStart: Date; weekEnd: Date } {
  const d = new Date(date);
  // dayOfWeek: 0=Sun, 1=Mon, ..., 6=Sat → adjust to 0=Mon, ..., 6=Sun
  const dayOfWeek = (d.getDay() + 6) % 7;
  const weekStart = new Date(d);
  weekStart.setDate(d.getDate() - dayOfWeek);

  const weekEnd = new Date(weekStart);
  weekEnd.setDate(weekStart.getDate() + 6);

  return { weekStart, weekEnd };
}
