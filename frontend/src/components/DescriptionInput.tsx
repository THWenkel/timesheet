/* =============================================================================
   frontend/src/components/DescriptionInput.tsx

   Multi-line text area for entering a free-text description of work performed.
   ============================================================================= */

interface DescriptionInputProps {
  /** Current text value */
  value: string;
  /** Called when text changes */
  onChange: (value: string) => void;
  /** Whether the input is disabled */
  disabled?: boolean;
}

/**
 * Free-text description input for describing work performed on a given day.
 *
 * Maximum 2000 characters (matches the backend DB column constraint).
 * Displays a character counter when nearing the limit.
 */
export function DescriptionInput({
  value,
  onChange,
  disabled = false,
}: DescriptionInputProps): React.JSX.Element {
  const MAX_LENGTH = 2000;
  const remaining = MAX_LENGTH - value.length;
  const isNearLimit = remaining < 100;

  const handleChange = (event: React.ChangeEvent<HTMLTextAreaElement>): void => {
    onChange(event.target.value);
  };

  return (
    <div className="description-input">
      <label htmlFor="description-textarea">
        <strong>Description</strong>
      </label>
      <textarea
        id="description-textarea"
        value={value}
        onChange={handleChange}
        disabled={disabled}
        maxLength={MAX_LENGTH}
        rows={4}
        placeholder="Describe the work performed on this day…"
        aria-label="Work description"
      />
      {isNearLimit && (
        <p className={`char-counter ${remaining < 20 ? "char-counter--critical" : ""}`}>
          {remaining} characters remaining
        </p>
      )}
    </div>
  );
}
