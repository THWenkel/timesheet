# =============================================================================
# backend/app/routers/export.py
#
# FastAPI router for the /api/export endpoint.
#
# Endpoint:
#   GET /api/export — generate and download a timesheet report
#
# Query parameters:
#   format:       'csv' | 'excel' | 'pdf'
#   employee_id:  integer (required)
#   from_date:    ISO date string (required)
#   to_date:      ISO date string (required)
#   project_id:   integer (required for excel/pdf, ignored for csv)
#
# Returns a StreamingResponse with the file content and a Content-Disposition
# header that triggers a browser download with an appropriate filename.
# =============================================================================

import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import AuthContext, ensure_employee_access, require_user
from app.db.session import get_db
from app.models.employee import Employee
from app.models.project import Customer, Project, ProjectAllocation
from app.schemas.timesheet import ExportFormat
from app.services import budget_service, export_service, timesheet_service

router = APIRouter(prefix="/api/export", tags=["export"])


def _get_content_type(fmt: ExportFormat) -> str:
    """
    Map an ExportFormat to the appropriate HTTP Content-Type header value.

    Args:
        fmt: The requested export format.

    Returns:
        MIME type string for the given format.
    """
    mapping: dict[ExportFormat, str] = {
        ExportFormat.CSV: "text/csv; charset=utf-8",
        ExportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ExportFormat.PDF: "application/pdf",
    }
    return mapping[fmt]


def _get_filename(
    fmt: ExportFormat,
    employee_name: str,
    from_date: date,
    to_date: date,
    scope: str | None = None,
) -> str:
    """
    Build a descriptive filename for the download based on the export parameters.

    The employee name and scope are sanitised to remove characters not safe for filenames.
    Example: 'timesheet_Acme_Portal_Max_Mustermann_2026-01-01_2026-01-31.xlsx'

    Args:
        fmt:           The export format.
        employee_name: Display name of the employee (e.g. 'Max Mustermann').
        from_date:     Start of the export period.
        to_date:       End of the export period.
        scope:         Optional customer and project name to put into the filename.

    Returns:
        A safe filename string including the appropriate file extension.
    """
    # Replace spaces and unsafe chars with underscores
    safe_name = "".join(c if c.isalnum() else "_" for c in employee_name)
    if scope:
        safe_name = "".join(c if c.isalnum() else "_" for c in scope) + "_" + safe_name
    extensions: dict[ExportFormat, str] = {
        ExportFormat.CSV: "csv",
        ExportFormat.EXCEL: "xlsx",
        ExportFormat.PDF: "pdf",
    }
    ext = extensions[fmt]
    return f"timesheet_{safe_name}_{from_date}_{to_date}.{ext}"


@router.get(
    "/",
    summary="Export timesheet data as CSV, Excel or PDF",
    description=(
        "Generate a downloadable timesheet report for an employee over a date range. "
        "Supported formats: csv (UTF-8 with BOM), excel (.xlsx), pdf (A4 table report). "
        "The response triggers a browser download with an appropriate filename."
    ),
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "File download",
            "headers": {
                "Content-Disposition": {
                    "schema": {"type": "string"},
                    "description": "Attachment filename for browser download",
                }
            },
        },
        400: {"description": "Invalid parameters"},
        404: {"description": "Employee not found"},
    },
)
def export_timesheets(
    format: ExportFormat,
    employee_id: int,
    from_date: date,
    to_date: date,
    project_id: int | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext | None = Depends(require_user),
) -> StreamingResponse:
    """
    Export timesheet entries for an employee within a date range.

    Steps:
      1. Validate the employee exists.
      2. Excel/PDF: validate the project; the export covers that project only.
      3. Fetch all entries in the date range via the timesheet service.
      4. Generate the file bytes via the export service (CSV/Excel/PDF).
      5. Return a StreamingResponse with appropriate Content-Type and filename.

    CSV ignores ``project_id`` and exports all entries as before.
    """
    ensure_employee_access(auth, employee_id)

    # --- Validate date range ---
    if from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"from_date ({from_date}) must not be after to_date ({to_date})",
        )

    # --- Validate employee exists ---
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with id={employee_id} not found",
        )

    # --- Project and customer (Excel / PDF only) ---
    context: export_service.ExportContext | None = None
    if format != ExportFormat.CSV:
        if project_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="project_id is required for excel and pdf exports",
            )
        project = db.get(Project, project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with id={project_id} not found",
            )
        allocated = db.execute(
            select(ProjectAllocation.id).where(
                ProjectAllocation.project_id == project_id,
                ProjectAllocation.employee_id == employee_id,
            )
        ).first()
        if allocated is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employee is not assigned to this project",
            )
        customer = db.get(Customer, project.customer_id)
        if customer is None:  # cannot happen (FK), keeps the type checker honest
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Customer not found")
        context = export_service.ExportContext(
            customer=customer,
            project=project,
            budget=budget_service.get_budget_overview(db, project, employee_id, to_date),
        )

    # --- Fetch entries ---
    entries = timesheet_service.get_entries_for_range(
        db, employee_id, from_date, to_date, project_id=None if context is None else project_id
    )

    # --- Generate file content ---
    employee_name = employee.display_name
    file_bytes: bytes

    if format == ExportFormat.CSV:
        file_bytes = export_service.generate_csv(entries, employee_name, from_date, to_date)
    elif format == ExportFormat.EXCEL:
        file_bytes = export_service.generate_excel(
            entries, employee_name, from_date, to_date, context
        )
    else:  # PDF
        file_bytes = export_service.generate_pdf(entries, employee_name, from_date, to_date, context)

    # --- Build response with download headers ---
    filename = _get_filename(
        format,
        employee_name,
        from_date,
        to_date,
        None if context is None else f"{context.customer.name}_{context.project.name}",
    )
    content_type = _get_content_type(format)

    return StreamingResponse(
        content=io.BytesIO(file_bytes),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(file_bytes)),
        },
    )
