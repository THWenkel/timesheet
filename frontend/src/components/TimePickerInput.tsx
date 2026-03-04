/* =============================================================================
   frontend/src/components/TimePickerInput.tsx

   A <select> dropdown for choosing a duration in 15-minute steps.

   Valid options: 00:15 to 23:45 (15 to 1425 minutes).
   The value is always stored as integer minutes internally.
   ============================================================================= */

import { generateTimeSlots } from "@/utils/timeUtils";

// Pre-generate all time slots once at module load time (96 slots, stable reference)
const TIME_SLOTS = generateTimeSlots();

interface TimePickerInputProps {
  /** Currently selected duration in minutes */
  value: number;
  /** Called when the selection changes — provides new minutes value */
  onChange: (minutes: number) => void;
  /** Optional validation error message to display */
  errorMessage?: string | null;
  /** Whether the picker is disabled */
  disabled?: boolean;
}

/**
 * Duration picker with 15-minute step increments.
 *
 * Renders all valid time slots from 00:15 to 23:45 as <option> elements.
 * Validation errors (e.g. daily 24h limit exceeded) are shown below the picker.
 */
export function TimePickerInput({
  value,
  onChange,
  errorMessage = null,
  disabled = false,
}: TimePickerInputProps): React.JSX.Element {
  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>): void => {
    const minutes = parseInt(event.target.value, 10);
    if (!isNaN(minutes)) {
      onChange(minutes);
    }
  };

  return (
    <div className="time-picker-input">
      <label htmlFor="time-picker">
        <strong>Duration</strong>
      </label>
      <select
        id="time-picker"
        value={value}
        onChange={handleChange}
        disabled={disabled}
        aria-label="Select duration"
        aria-describedby={errorMessage !== null ? "time-picker-error" : undefined}
        aria-invalid={errorMessage !== null}
      >
        {TIME_SLOTS.map((slot) => (
          <option key={slot.minutes} value={slot.minutes}>
            {slot.label}
          </option>
        ))}
      </select>
      {errorMessage !== null && (
        <p id="time-picker-error" className="error-message" role="alert">
          {errorMessage}
        </p>
      )}
    </div>
  );
}
