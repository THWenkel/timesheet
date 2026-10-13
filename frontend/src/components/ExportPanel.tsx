/* =============================================================================
   frontend/src/components/ExportPanel.tsx

   Export panel allowing the user to download timesheet data as CSV, Excel, or PDF.

   Excel and PDF are created per project (customer, order number and budget
   consumption are printed); CSV exports all entries and needs no project.

   The export triggers a browser download via a GET request to /api/export/
   with the appropriate query parameters. The browser's built-in download
   mechanism handles the file save dialog.
   ============================================================================= */

import { useState } from "react";
import { apiBaseUrl } from "@/api/client";
import { ProjectSelect } from "@/components/ProjectSelect";
import { useEmployeeProjects } from "@/hooks/useEmployeeProjects";
import { toISODateString } from "@/utils/timeUtils";

type ExportFormat = "csv" | "excel" | "pdf";

interface ExportPanelProps {
  /** Currently selected employee ID — null disables the export */
  employeeId: number | null;
}

/**
 * Export panel with format selection (CSV / Excel / PDF) and date range picker.
 *
 * Clicking "Download" triggers a GET /api/export/ request which returns a
 * file download. The browser handles the save dialog automatically via
 * the Content-Disposition: attachment header from the backend.
 */
export function ExportPanel({ employeeId }: ExportPanelProps): React.JSX.Element {
  // Default date range: current month
  const today = new Date();
  const firstOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);

  const [format, setFormat] = useState<ExportFormat>("pdf");
  const [fromDate, setFromDate] = useState<string>(toISODateString(firstOfMonth));
  const [toDate, setToDate] = useState<string>(toISODateString(today));
  const [isDownloading, setIsDownloading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [chosenProjectId, setChosenProjectId] = useState<number | null>(null);

  // Export also covers paused and completed projects
  const { projects, isLoading: isProjectsLoading } = useEmployeeProjects(employeeId, false);
  const needsProject = format !== "csv";
  const onlyProject = projects.length === 1 ? projects[0] : undefined;
  const projectId =
    onlyProject !== undefined
      ? onlyProject.id
      : projects.some((p) => p.id === chosenProjectId)
        ? chosenProjectId
        : null;

  const handleFormatChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    setFormat(event.target.value as ExportFormat);
  };

  const handleDownload = async (): Promise<void> => {
    if (employeeId === null || (needsProject && projectId === null)) return;

    setIsDownloading(true);
    setError(null);

    try {
      // Build the export URL manually for a direct browser download.
      // Using fetch() with a blob response so we can trigger the download
      // without opening a new browser tab.
      const params = new URLSearchParams({
        format,
        employee_id: String(employeeId),
        from_date: fromDate,
        to_date: toDate,
      });
      if (needsProject && projectId !== null) {
        params.set("project_id", String(projectId));
      }

      const response = await fetch(`${apiBaseUrl}/api/export/?${params.toString()}`, {
        credentials: "include",
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        const detail =
          body !== null &&
          typeof body === "object" &&
          "detail" in body &&
          typeof (body as { detail: unknown }).detail === "string"
            ? (body as { detail: string }).detail
            : `Export failed (HTTP ${response.status})`;
        setError(detail);
        return;
      }

      // Extract filename from Content-Disposition header (if available)
      const disposition = response.headers.get("Content-Disposition") ?? "";
      const filenameMatch = /filename="([^"]+)"/.exec(disposition);
      const filename =
        filenameMatch?.[1] ?? `timesheet_export.${format === "excel" ? "xlsx" : format}`;

      // Create a blob URL, trigger click on a hidden anchor, then revoke
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred.");
    } finally {
      setIsDownloading(false);
    }
  };

  const isDisabled = employeeId === null || isDownloading;
  const cannotDownload = isDisabled || (needsProject && projectId === null);

  return (
    <div className="export-panel">
      <h3 className="export-panel__title">Export</h3>

      {employeeId === null && (
        <p className="export-panel__hint">Please select an employee to enable export.</p>
      )}

      {/* Format selection */}
      <fieldset className="export-panel__format" disabled={isDisabled}>
        <legend>Format</legend>
        {(["csv", "excel", "pdf"] as ExportFormat[]).map((fmt) => (
          <label key={fmt} className="export-panel__format-option">
            <input
              type="radio"
              name="export-format"
              value={fmt}
              checked={format === fmt}
              onChange={handleFormatChange}
            />
            {fmt === "csv" ? "CSV" : fmt === "excel" ? "Excel (.xlsx)" : "PDF (A4 report)"}
          </label>
        ))}
      </fieldset>

      {/* Project (Excel / PDF only) */}
      {needsProject && (
        <ProjectSelect
          id="export-project"
          projects={projects}
          value={projectId}
          onChange={setChosenProjectId}
          isLoading={isProjectsLoading}
          disabled={isDisabled}
        />
      )}

      {/* Date range */}
      <div className="export-panel__date-range">
        <label htmlFor="export-from">From</label>
        <input
          id="export-from"
          type="date"
          value={fromDate}
          onChange={(e) => setFromDate(e.target.value)}
          disabled={isDisabled}
          max={toDate}
        />
        <label htmlFor="export-to">To</label>
        <input
          id="export-to"
          type="date"
          value={toDate}
          onChange={(e) => setToDate(e.target.value)}
          disabled={isDisabled}
          min={fromDate}
        />
      </div>

      {/* Error message */}
      {error !== null && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}

      {/* Download button */}
      <button
        type="button"
        className="export-panel__download-btn"
        onClick={() => void handleDownload()}
        disabled={cannotDownload}
        aria-busy={isDownloading}
      >
        {isDownloading ? "Generating…" : "Download"}
      </button>
    </div>
  );
}
