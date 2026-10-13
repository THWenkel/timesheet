/* =============================================================================
   frontend/src/components/ProjectSelect.tsx

   Project dropdown for the entry form and the export panel.

   - One project: it is shown selected and the field is locked.
   - Several projects: the user has to choose one.
   - No project: a hint replaces the field.
   ============================================================================= */

import type { EmployeeProject } from "@/hooks/useEmployeeProjects";

interface ProjectSelectProps {
  id: string;
  projects: EmployeeProject[];
  /** Selected project ID, null = nothing chosen yet */
  value: number | null;
  onChange: (projectId: number | null) => void;
  isLoading?: boolean;
  disabled?: boolean;
}

function projectLabel(project: EmployeeProject): string {
  const order = project.purchase_number.length > 0 ? ` (${project.purchase_number})` : "";
  return `${project.customer_name} – ${project.name}${order}`;
}

export function ProjectSelect({
  id,
  projects,
  value,
  onChange,
  isLoading = false,
  disabled = false,
}: ProjectSelectProps): React.JSX.Element {
  if (isLoading) {
    return <p className="project-select__hint">Loading projects…</p>;
  }

  if (projects.length === 0) {
    return (
      <p className="error-message" role="alert">
        No project is assigned to you yet. Please contact the administration.
      </p>
    );
  }

  const onlyOne = projects.length === 1;

  return (
    <div className="project-select">
      <label htmlFor={id} className="project-select__label">
        Project
      </label>
      <select
        id={id}
        className="project-select__input"
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
        disabled={disabled || onlyOne}
        required
      >
        {!onlyOne && (
          <option value="" disabled>
            Select a project…
          </option>
        )}
        {projects.map((project) => (
          <option key={project.id} value={project.id}>
            {projectLabel(project)}
          </option>
        ))}
      </select>
    </div>
  );
}
