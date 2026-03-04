// =============================================================================
// frontend/src/hooks/useTimesheetEntries.ts
//
// Custom hook for timesheet entry data operations.
//
// Provides:
//   - Dates with entries for a calendar month (for tileClassName colouring)
//   - Day summary (all entries + total for a specific date)
//   - Week summary (Mon–Sun totals for a given date)
//   - Create and update entry mutations
// =============================================================================

import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/api/client";
import type { components } from "@/api/generated";
import { toISODateString } from "@/utils/timeUtils";

type DateWithEntries = components["schemas"]["DateWithEntries"];
type DaySummary = components["schemas"]["DaySummary"];
type WeekSummary = components["schemas"]["WeekSummary"];
type TimesheetEntryCreate = components["schemas"]["TimesheetEntryCreate"];
type TimesheetEntryUpdate = components["schemas"]["TimesheetEntryUpdate"];

// ---------------------------------------------------------------------------
// Hook: useCalendarDates
// ---------------------------------------------------------------------------

interface UseCalendarDatesResult {
  /** Dates in the current month that have at least one entry */
  datesWithEntries: DateWithEntries[];
  isLoading: boolean;
  error: string | null;
  /** Refetch the dates (call after creating/updating an entry) */
  refetch: () => void;
}

/**
 * Fetch the list of dates with entries for a specific employee and calendar month.
 *
 * Used to colour calendar tiles dark blue for dates that have entries.
 *
 * @param employeeId - Selected employee ID (null = no fetch)
 * @param year       - Calendar year to fetch
 * @param month      - Calendar month to fetch (1–12)
 */
export function useCalendarDates(
  employeeId: number | null,
  year: number,
  month: number,
): UseCalendarDatesResult {
  const [datesWithEntries, setDatesWithEntries] = useState<DateWithEntries[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchTrigger, setFetchTrigger] = useState<number>(0);

  useEffect(() => {
    if (employeeId === null) {
      setDatesWithEntries([]);
      return;
    }

    let cancelled = false;

    const fetch = async (): Promise<void> => {
      setIsLoading(true);
      setError(null);

      const { data, error: apiError } = await apiClient.GET("/api/timesheets/dates", {
        params: { query: { employee_id: employeeId, year, month } },
      });

      if (cancelled) return;

      if (apiError !== undefined) {
        setError("Failed to load calendar data.");
      } else if (data !== undefined) {
        setDatesWithEntries(data);
      }
      setIsLoading(false);
    };

    void fetch();
    return () => {
      cancelled = true;
    };
  }, [employeeId, year, month, fetchTrigger]);

  const refetch = useCallback((): void => {
    setFetchTrigger((n) => n + 1);
  }, []);

  return { datesWithEntries, isLoading, error, refetch };
}

// ---------------------------------------------------------------------------
// Hook: useDaySummary
// ---------------------------------------------------------------------------

interface UseDaySummaryResult {
  daySummary: DaySummary | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Fetch all entries and the total for a specific employee on a specific date.
 *
 * @param employeeId - Selected employee ID (null = no fetch)
 * @param date       - Selected date (null = no fetch)
 */
export function useDaySummary(
  employeeId: number | null,
  date: Date | null,
): UseDaySummaryResult {
  const [daySummary, setDaySummary] = useState<DaySummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchTrigger, setFetchTrigger] = useState<number>(0);

  const dateStr = date !== null ? toISODateString(date) : null;

  useEffect(() => {
    if (employeeId === null || dateStr === null) {
      setDaySummary(null);
      return;
    }

    let cancelled = false;

    const fetch = async (): Promise<void> => {
      setIsLoading(true);
      setError(null);

      const { data, error: apiError } = await apiClient.GET("/api/timesheets/day", {
        params: { query: { employee_id: employeeId, entry_date: dateStr } },
      });

      if (cancelled) return;

      if (apiError !== undefined) {
        setError("Failed to load day entries.");
      } else if (data !== undefined) {
        setDaySummary(data);
      }
      setIsLoading(false);
    };

    void fetch();
    return () => {
      cancelled = true;
    };
  }, [employeeId, dateStr, fetchTrigger]);

  const refetch = useCallback((): void => {
    setFetchTrigger((n) => n + 1);
  }, []);

  return { daySummary, isLoading, error, refetch };
}

// ---------------------------------------------------------------------------
// Hook: useWeekSummary
// ---------------------------------------------------------------------------

interface UseWeekSummaryResult {
  weekSummary: WeekSummary | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Fetch the Mon–Sun week summary for the week containing the given date.
 *
 * @param employeeId - Selected employee ID (null = no fetch)
 * @param date       - Any date within the target week (null = no fetch)
 */
export function useWeekSummary(
  employeeId: number | null,
  date: Date | null,
): UseWeekSummaryResult {
  const [weekSummary, setWeekSummary] = useState<WeekSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchTrigger, setFetchTrigger] = useState<number>(0);

  const dateStr = date !== null ? toISODateString(date) : null;

  useEffect(() => {
    if (employeeId === null || dateStr === null) {
      setWeekSummary(null);
      return;
    }

    let cancelled = false;

    const fetch = async (): Promise<void> => {
      setIsLoading(true);
      setError(null);

      const { data, error: apiError } = await apiClient.GET("/api/timesheets/week", {
        params: { query: { employee_id: employeeId, any_date: dateStr } },
      });

      if (cancelled) return;

      if (apiError !== undefined) {
        setError("Failed to load week summary.");
      } else if (data !== undefined) {
        setWeekSummary(data);
      }
      setIsLoading(false);
    };

    void fetch();
    return () => {
      cancelled = true;
    };
  }, [employeeId, dateStr, fetchTrigger]);

  const refetch = useCallback((): void => {
    setFetchTrigger((n) => n + 1);
  }, []);

  return { weekSummary, isLoading, error, refetch };
}

// ---------------------------------------------------------------------------
// Mutation: useCreateEntry
// ---------------------------------------------------------------------------

interface UseCreateEntryResult {
  createEntry: (payload: TimesheetEntryCreate) => Promise<boolean>;
  isSubmitting: boolean;
  error: string | null;
}

/**
 * Mutation hook for creating a new timesheet entry via POST /api/timesheets/.
 *
 * @returns { createEntry, isSubmitting, error }
 *   createEntry returns true on success, false on failure.
 */
export function useCreateEntry(): UseCreateEntryResult {
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const createEntry = async (payload: TimesheetEntryCreate): Promise<boolean> => {
    setIsSubmitting(true);
    setError(null);

    const { error: apiError } = await apiClient.POST("/api/timesheets/", {
      body: payload,
    });

    setIsSubmitting(false);

    if (apiError !== undefined) {
      const msg =
        typeof apiError === "object" &&
        apiError !== null &&
        "detail" in apiError &&
        typeof (apiError as { detail: unknown }).detail === "string"
          ? (apiError as { detail: string }).detail
          : "Failed to save entry.";
      setError(msg);
      return false;
    }

    return true;
  };

  return { createEntry, isSubmitting, error };
}

// ---------------------------------------------------------------------------
// Mutation: useUpdateEntry
// ---------------------------------------------------------------------------

interface UseUpdateEntryResult {
  updateEntry: (entryId: number, payload: TimesheetEntryUpdate) => Promise<boolean>;
  isSubmitting: boolean;
  error: string | null;
}

/**
 * Mutation hook for updating an existing timesheet entry via PUT /api/timesheets/{id}.
 *
 * @returns { updateEntry, isSubmitting, error }
 *   updateEntry returns true on success, false on failure.
 */
export function useUpdateEntry(): UseUpdateEntryResult {
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const updateEntry = async (
    entryId: number,
    payload: TimesheetEntryUpdate,
  ): Promise<boolean> => {
    setIsSubmitting(true);
    setError(null);

    const { error: apiError } = await apiClient.PUT("/api/timesheets/{entry_id}", {
      params: { path: { entry_id: entryId } },
      body: payload,
    });

    setIsSubmitting(false);

    if (apiError !== undefined) {
      const msg =
        typeof apiError === "object" &&
        apiError !== null &&
        "detail" in apiError &&
        typeof (apiError as { detail: unknown }).detail === "string"
          ? (apiError as { detail: string }).detail
          : "Failed to update entry.";
      setError(msg);
      return false;
    }

    return true;
  };

  return { updateEntry, isSubmitting, error };
}
