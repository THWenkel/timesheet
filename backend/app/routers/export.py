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
#
# Returns a StreamingResponse with the file content and a Content-Disposition
# header that triggers a browser download with an appropriate filename.
# =============================================================================

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.employee import Employee
from app.schemas.timesheet import ExportFormat
from app.services import export_service, timesheet_service

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


def _get_filename(fmt: ExportFormat, employee_name: str, from_date: date, to_date: date) -> str:
    """
    Build a descriptive filename for the download based on the export parameters.

    The employee name is sanitised to remove characters not safe for filenames.
    Example: 'timesheet_Max_Mustermann_2026-01-01_2026-01-31.xlsx'

    Args:
        fmt:           The export format.
        employee_name: Display name of the employee (e.g. 'Max Mustermann').
        from_date:     Start of the export period.
        to_date:       End of the export period.

    Returns:
        A safe filename string including the appropriate file extension.
    """
    # Replace spaces and unsafe chars with underscores
    safe_name = "".join(c if c.isalnum() else "_" for c in employee_name)
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
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Export timesheet entries for an employee within a date range.

    Steps:
      1. Validate the employee exists.
      2. Fetch all entries in the date range via the timesheet service.
      3. Generate the file bytes via the export service (CSV/Excel/PDF).
      4. Return a StreamingResponse with appropriate Content-Type and filename.
    """
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

    # --- Fetch entries ---
    entries = timesheet_service.get_entries_for_range(db, employee_id, from_date, to_date)

    # --- Generate file content ---
    employee_name = employee.display_name
    file_bytes: bytes

    if format == ExportFormat.CSV:
        file_bytes = export_service.generate_csv(entries, employee_name, from_date, to_date)
    elif format == ExportFormat.EXCEL:
        file_bytes = export_service.generate_excel(entries, employee_name, from_date, to_date)
    else:  # PDF
        file_bytes = export_service.generate_pdf(entries, employee_name, from_date, to_date)

    # --- Build response with download headers ---
    filename = _get_filename(format, employee_name, from_date, to_date)
    content_type = _get_content_type(format)

    import io
    return StreamingResponse(
        content=io.BytesIO(file_bytes),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(file_bytes)),
        },
    )
