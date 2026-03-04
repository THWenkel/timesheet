# =============================================================================
# backend/app/services/export_service.py
#
# Export service — generates CSV, Excel (.xlsx), and PDF files from timesheet data.
#
# Each function accepts a list of TimesheetEntryRead records plus metadata
# (employee name, date range) and returns the file content as bytes.
#
# Format details:
#   CSV   — UTF-8 with BOM (ensures correct display in Microsoft Excel)
#   Excel — .xlsx via openpyxl with styled header row
#   PDF   — A4 table report via reportlab with title, metadata, and entry table
#
# The callers (export router) wrap these bytes in a FastAPI StreamingResponse
# with the appropriate Content-Type and Content-Disposition headers.
# =============================================================================

import csv
import io
from datetime import date

from app.schemas.timesheet import TimesheetEntryRead


def _minutes_to_display(minutes: int) -> str:
    """
    Convert integer minutes to 'hh:mm' display string.

    Args:
        minutes: Total minutes (must be >= 0).

    Returns:
        Zero-padded hours:minutes string, e.g. '08:30'.
    """
    h, m = divmod(minutes, 60)
    return f"{h:02d}:{m:02d}"


def generate_csv(
    entries: list[TimesheetEntryRead],
    employee_name: str,
    from_date: date,
    to_date: date,
) -> bytes:
    """
    Generate a CSV file from the given timesheet entries.

    The output is UTF-8 encoded with a BOM prefix so that Microsoft Excel
    opens it correctly without an import wizard.

    Columns: Date, Duration (hh:mm), Duration (minutes), Description

    A summary row with total minutes is appended at the end.

    Args:
        entries:       List of timesheet entries to export.
        employee_name: Display name of the employee (used in header comment).
        from_date:     Start of the export date range.
        to_date:       End of the export date range.

    Returns:
        CSV file content as bytes (UTF-8 with BOM).
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_MINIMAL)

    # --- Metadata header rows ---
    writer.writerow(["Timesheet Export"])
    writer.writerow(["Employee:", employee_name])
    writer.writerow(["Period:", f"{from_date} - {to_date}"])
    writer.writerow([])  # blank line separator

    # --- Data header ---
    writer.writerow(["Date", "Duration (hh:mm)", "Duration (min)", "Description"])

    # --- Data rows ---
    total_minutes = 0
    for entry in entries:
        writer.writerow([
            entry.entry_date.isoformat(),
            entry.hours_display,
            entry.minutes,
            entry.description,
        ])
        total_minutes += entry.minutes

    # --- Totals row ---
    writer.writerow([])
    writer.writerow([
        "TOTAL",
        _minutes_to_display(total_minutes),
        total_minutes,
        "",
    ])

    # Return UTF-8 with BOM for Excel compatibility
    return b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")


def generate_excel(
    entries: list[TimesheetEntryRead],
    employee_name: str,
    from_date: date,
    to_date: date,
) -> bytes:
    """
    Generate an Excel (.xlsx) workbook from the given timesheet entries.

    Uses openpyxl to create a styled spreadsheet with:
      - A title and metadata block at the top
      - A bold header row with column widths auto-fitted
      - Data rows with alternating row colours (light blue / white)
      - A totals row at the bottom with bold formatting

    Args:
        entries:       List of timesheet entries to export.
        employee_name: Display name of the employee.
        from_date:     Start of the export date range.
        to_date:       End of the export date range.

    Returns:
        Excel file content as bytes (.xlsx format).
    """
    # Import here to avoid loading openpyxl on every request — only needed for Excel export
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Timesheet"  # type: ignore[union-attr]

    # --- Colour constants ---
    header_fill = PatternFill(start_color="1B4F8A", end_color="1B4F8A", fill_type="solid")
    alt_row_fill = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
    total_fill = PatternFill(start_color="BDD7EE", end_color="BDD7EE", fill_type="solid")
    bold_white = Font(bold=True, color="FFFFFF")
    bold = Font(bold=True)

    # --- Title block ---
    ws.append(["Timesheet Export"])  # type: ignore[union-attr]
    ws["A1"].font = Font(bold=True, size=14)  # type: ignore[union-attr]
    ws.append(["Employee:", employee_name])  # type: ignore[union-attr]
    ws.append(["Period:", f"{from_date} - {to_date}"])  # type: ignore[union-attr]
    ws.append([])  # type: ignore[union-attr]  blank row

    # --- Column headers (row 5) ---
    header_row = ["Date", "Duration (hh:mm)", "Duration (min)", "Description"]
    ws.append(header_row)  # type: ignore[union-attr]
    header_row_idx = ws.max_row  # type: ignore[union-attr]
    for col_idx, _ in enumerate(header_row, start=1):
        cell = ws.cell(row=header_row_idx, column=col_idx)  # type: ignore[union-attr]
        cell.font = bold_white
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    # --- Data rows ---
    total_minutes = 0
    for i, entry in enumerate(entries):
        row_data = [
            entry.entry_date.isoformat(),
            entry.hours_display,
            entry.minutes,
            entry.description,
        ]
        ws.append(row_data)  # type: ignore[union-attr]
        total_minutes += entry.minutes
        # Alternate row shading for readability
        if i % 2 == 0:
            for col_idx in range(1, len(row_data) + 1):
                ws.cell(row=ws.max_row, column=col_idx).fill = alt_row_fill  # type: ignore[union-attr]

    # --- Totals row ---
    ws.append([])  # type: ignore[union-attr]  blank row
    totals_row = ["TOTAL", _minutes_to_display(total_minutes), total_minutes, ""]
    ws.append(totals_row)  # type: ignore[union-attr]
    for col_idx in range(1, len(totals_row) + 1):
        cell = ws.cell(row=ws.max_row, column=col_idx)  # type: ignore[union-attr]
        cell.font = bold
        cell.fill = total_fill

    # --- Column widths ---
    column_widths = [14, 18, 16, 60]
    for col_idx, width in enumerate(column_widths, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width  # type: ignore[union-attr]

    # --- Serialize to bytes ---
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def generate_pdf(
    entries: list[TimesheetEntryRead],
    employee_name: str,
    from_date: date,
    to_date: date,
) -> bytes:
    """
    Generate a PDF report from the given timesheet entries.

    Uses reportlab to produce an A4 PDF with:
      - Company/app title and report metadata at the top
      - A styled table with all entries (alternating row colours)
      - A totals row at the bottom of the table
      - Page numbers in the footer

    Args:
        entries:       List of timesheet entries to export.
        employee_name: Display name of the employee.
        from_date:     Start of the export date range.
        to_date:       End of the export date range.

    Returns:
        PDF file content as bytes.
    """
    # Import here to avoid loading reportlab unless a PDF export is requested
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = io.BytesIO()

    # --- Document setup ---
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    elements: list[object] = []

    # --- Title ---
    elements.append(Paragraph("Timesheet Export", styles["Title"]))
    elements.append(Spacer(1, 0.3 * cm))

    # --- Metadata ---
    elements.append(Paragraph(f"<b>Employee:</b> {employee_name}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Period:</b> {from_date} - {to_date}", styles["Normal"]))
    elements.append(Spacer(1, 0.5 * cm))

    # --- Table ---
    # Header row
    table_data: list[list[str]] = [
        ["Date", "Duration (hh:mm)", "Duration (min)", "Description"],
    ]

    total_minutes = 0
    for entry in entries:
        table_data.append([
            entry.entry_date.isoformat(),
            entry.hours_display,
            str(entry.minutes),
            entry.description,
        ])
        total_minutes += entry.minutes

    # Totals row
    table_data.append([
        "TOTAL",
        _minutes_to_display(total_minutes),
        str(total_minutes),
        "",
    ])

    # Available page width
    page_width = A4[0] - 4 * cm
    col_widths = [3 * cm, 3.5 * cm, 3.5 * cm, page_width - 10 * cm]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    # Table styling
    row_count = len(table_data)
    # reportlab style commands are 4- or 5-tuples (the GRID command includes a line-width arg)
    table_style_commands: list[tuple[str, object, object, object] | tuple[str, object, object, object, object]] = [
        # Header row style
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B4F8A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        # Data rows
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        # Alternating row colours
        *[
            ("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#DCE6F1"))
            for row_idx in range(2, row_count - 1, 2)
        ],
        # Totals row — last data row before the end
        ("BACKGROUND", (0, row_count - 1), (-1, row_count - 1), colors.HexColor("#BDD7EE")),
        ("FONTNAME", (0, row_count - 1), (-1, row_count - 1), "Helvetica-Bold"),
    ]

    table.setStyle(TableStyle(table_style_commands))  # type: ignore[arg-type]
    elements.append(table)

    # --- Build ---
    doc.build(elements)  # type: ignore[arg-type]
    return buffer.getvalue()
