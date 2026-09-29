/* =============================================================================
   frontend/src/components/EmployeeSelector.tsx

   Dropdown for selecting the active employee.
   Loaded from GET /api/employees/ via the useEmployees hook.
   ============================================================================= */

import type { components } from "@/api/generated";
import { useEmployees } from "@/hooks/useEmployees";

type EmployeeListItem = components["schemas"]["EmployeeListItem"];

interface EmployeeSelectorProps {
  /** Currently selected employee ID, or null if none selected */
  selectedEmployeeId: number | null;
  /** Called when an employee is selected */
  onSelect: (employee: EmployeeListItem) => void;
}

/**
 * Employee selector dropdown.
 *
 * Displays all active employees in "Surname Lastname" format, ordered
 * by lastname. Shows a loading indicator while fetching and an error
 * message if the fetch fails.
 */
export function EmployeeSelector({
  selectedEmployeeId,
  onSelect,
}: EmployeeSelectorProps): React.JSX.Element {
  const { employees, isLoading, error } = useEmployees();

  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>): void => {
    const id = parseInt(event.target.value, 10);
    const employee = employees.find((e) => e.id === id);
    if (employee !== undefined) {
      onSelect(employee);
    }
  };

  return (
    <div className="employee-selector">
      <label htmlFor="employee-select">
        <strong>Employee</strong>
      </label>
      {error !== null && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}
      <select
        id="employee-select"
        value={selectedEmployeeId ?? ""}
        onChange={handleChange}
        disabled={isLoading || error !== null}
        aria-label="Select employee"
      >
        <option value="" disabled>
          {isLoading ? "Loading employees…" : "— Select employee —"}
        </option>
        {employees.map((emp) => (
          <option key={emp.id} value={emp.id}>
            {emp.display_name}
          </option>
        ))}
      </select>
    </div>
  );
}
