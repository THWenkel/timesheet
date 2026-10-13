// =============================================================================
// frontend/src/hooks/useEmployeeProjects.ts
//
// Fetches the projects an employee is allocated to (GET /api/employees/{id}/projects).
//
// The time entry form needs the active projects only; the export also lists
// paused and completed ones (activeOnly = false).
// =============================================================================

import { useEffect, useState } from "react";
import { apiClient } from "@/api/client";
import type { components } from "@/api/generated";

export type EmployeeProject = components["schemas"]["EmployeeProject"];

interface UseEmployeeProjectsResult {
  projects: EmployeeProject[];
  /** True until the first response for the current employee arrived */
  isLoading: boolean;
  error: string | null;
}

/**
 * @param employeeId - Employee whose projects are loaded (null = no fetch)
 * @param activeOnly - Only projects with status "active" (default true)
 */
export function useEmployeeProjects(
  employeeId: number | null,
  activeOnly = true,
): UseEmployeeProjectsResult {
  const [projects, setProjects] = useState<EmployeeProject[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(employeeId !== null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (employeeId === null) {
      setProjects([]);
      setIsLoading(false);
      return;
    }

    let cancelled = false;

    const load = async (): Promise<void> => {
      setIsLoading(true);
      setError(null);

      const { data, error: apiError } = await apiClient.GET("/api/employees/{employee_id}/projects", {
        params: { path: { employee_id: employeeId }, query: { active_only: activeOnly } },
      });

      if (cancelled) return;

      if (apiError !== undefined) {
        setProjects([]);
        setError("Failed to load projects.");
      } else if (data !== undefined) {
        setProjects(data);
      }
      setIsLoading(false);
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [employeeId, activeOnly]);

  return { projects, isLoading, error };
}
