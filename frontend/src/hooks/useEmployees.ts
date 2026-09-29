// =============================================================================
// frontend/src/hooks/useEmployees.ts
//
// Custom hook for fetching the employee list from the API.
//
// Returns the list of active employees suitable for the selector dropdown,
// along with loading and error states.
// =============================================================================

import { useEffect, useState } from "react";
import { apiClient } from "@/api/client";
import type { components } from "@/api/generated";

type EmployeeListItem = components["schemas"]["EmployeeListItem"];

interface UseEmployeesResult {
  /** List of active employees, ordered by lastname then surname */
  employees: EmployeeListItem[];
  /** True while the API request is in flight */
  isLoading: boolean;
  /** Error message if the request failed, null otherwise */
  error: string | null;
  /** Re-fetch the employee list */
  refetch: () => void;
}

/**
 * Fetch the list of active employees from GET /api/employees/.
 *
 * Automatically fetches on mount. Call `refetch` to manually re-fetch.
 *
 * @returns UseEmployeesResult with employees, isLoading, error, refetch
 */
export function useEmployees(): UseEmployeesResult {
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [fetchTrigger, setFetchTrigger] = useState<number>(0);

  useEffect(() => {
    let cancelled = false;

    const fetchEmployees = async (): Promise<void> => {
      setIsLoading(true);
      setError(null);

      const { data, error: apiError } = await apiClient.GET("/api/employees/", {});

      if (cancelled) return;

      if (apiError !== undefined) {
        setError("Failed to load employees. Please check the connection.");
      } else if (data !== undefined) {
        setEmployees(data);
      }
      setIsLoading(false);
    };

    void fetchEmployees();

    // Cleanup: cancel state updates if the component unmounts before fetch completes
    return () => {
      cancelled = true;
    };
  }, [fetchTrigger]);

  const refetch = (): void => {
    setFetchTrigger((n) => n + 1);
  };

  return { employees, isLoading, error, refetch };
}
