# =============================================================================
# backend/app/schemas/timesheet.py
#
# Pydantic v2 schemas for the TimesheetEntry resource and export requests.
#
# Schema hierarchy:
#   TimesheetEntryBase    — shared fields (entry_date, minutes, description)
#   TimesheetEntryCreate  — used for POST /api/timesheets
#   TimesheetEntryUpdate  — used for PUT /api/timesheets/{id}
#   TimesheetEntryRead    — used for API responses
#   DateWithEntries       — list of dates that have entries (for calendar colouring)
#   DaySummary            — total minutes for a single day
#   WeekSummary           — per-day + total minutes for a 7-day week range
#   ExportRequest         — query parameters for the export endpoint
# =============================================================================

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Custom type for validated minutes value
# ---------------------------------------------------------------------------
MinutesValue = Annotated[
    int,
    Field(
        ge=15,
        le=1440,  # Maximum 24 hours per entry
        description=(
            "Duration in minutes. Must be a positive multiple of 15 "
            "and at most 1440 (24 hours)."
        ),
    ),
]


class TimesheetEntryBase(BaseModel):
    """
    Shared fields for timesheet entry create and update operations.
    """

    entry_date: date = Field(
        ...,
        description="Calendar date on which the work was performed",
        examples=["2026-03-04"],
    )
    minutes: MinutesValue = Field(
        ...,
        description="Duration in minutes -- must be a multiple of 15 (15-1440)",
        examples=[90, 480],
    )
    description: str = Field(
        default="",
        max_length=2000,
        description="Free-text description of work performed",
        examples=["Implemented timesheet entry form and unit tests"],
    )

    @field_validator("minutes")
    @classmethod
    def minutes_must_be_multiple_of_15(cls, value: int) -> int:
        """
        Validate that the minutes value is a positive multiple of 15.

        This enforces the 15-minute time step requirement across all entry points.
        """
        if value % 15 != 0:
            msg = f"minutes must be a multiple of 15, got {value}"
            raise ValueError(msg)
        return value


class TimesheetEntryCreate(TimesheetEntryBase):
    """
    Schema for creating a new timesheet entry (POST /api/timesheets).

    Requires employee_id to associate the entry with an employee.
    All base fields (entry_date, minutes, description) are also required.
    """

    employee_id: int = Field(
        ...,
        ge=1,
        description="ID of the employee submitting this entry",
    )


class TimesheetEntryUpdate(BaseModel):
    """
    Schema for updating an existing timesheet entry (PUT /api/timesheets/{id}).

    All fields are optional — only provided fields will be updated.
    Validation rules (multiples of 15, etc.) still apply.
    """

    minutes: int | None = Field(
        default=None,
        ge=15,
        le=1440,
        description="Updated duration in minutes (multiple of 15)",
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Updated work description",
    )

    @field_validator("minutes")
    @classmethod
    def minutes_must_be_multiple_of_15(cls, value: int | None) -> int | None:
        """Validate the updated minutes value is a multiple of 15 if provided."""
        if value is not None and value % 15 != 0:
            msg = f"minutes must be a multiple of 15, got {value}"
            raise ValueError(msg)
        return value


class TimesheetEntryRead(TimesheetEntryBase):
    """
    Full timesheet entry schema for API responses.

    Includes the primary key, employee reference, and audit timestamps.
    Configured with from_attributes=True for ORM model mapping.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Auto-incremented primary key")
    employee_id: int = Field(description="ID of the employee who owns this entry")
    hours_display: str = Field(
        description="Human-readable duration in hh:mm format (derived from minutes)",
        examples=["01:30", "08:00"],
    )
    created_at: datetime = Field(description="UTC timestamp when the entry was created")
    updated_at: datetime = Field(description="UTC timestamp of the last modification")
    created_by: int | None = Field(default=None, description="employee.id who created this entry")
    updated_by: int | None = Field(default=None, description="employee.id who last updated this")


class DateWithEntries(BaseModel):
    """
    Represents a date that has at least one timesheet entry for an employee.

    Used by the frontend to colour calendar days in dark blue when entries exist.
    """

    entry_date: date = Field(description="Date that has existing entries")
    total_minutes: int = Field(description="Total minutes logged on this date")
    entry_count: int = Field(description="Number of individual entries on this date")


class DaySummary(BaseModel):
    """
    Summary of all timesheet entries for a single employee on a specific day.
    """

    entry_date: date = Field(description="The day being summarised")
    total_minutes: int = Field(description="Sum of all entry minutes on this date")
    total_display: str = Field(
        description="Total duration in hh:mm format",
        examples=["08:30"],
    )
    entries: list[TimesheetEntryRead] = Field(
        description="All individual entries for this day",
    )


class WeekDayEntry(BaseModel):
    """A single day within a weekly summary."""

    entry_date: date = Field(description="Calendar date of this weekday")
    day_name: str = Field(description="Day name (Monday, Tuesday, ...)")
    total_minutes: int = Field(description="Total minutes logged on this day")
    total_display: str = Field(description="Total in hh:mm format")
    has_entries: bool = Field(description="Whether any entries exist for this day")


class WeekSummary(BaseModel):
    """
    Summary of an employee's timesheet entries for a 7-day week.

    The week is defined by any date within it — the service calculates
    the Monday and Sunday of the containing week automatically.
    """

    week_start: date = Field(description="Monday of the summarised week")
    week_end: date = Field(description="Sunday of the summarised week")
    days: list[WeekDayEntry] = Field(
        description="One entry per day (Monday-Sunday), 7 items",
    )
    week_total_minutes: int = Field(description="Total minutes logged over the full week")
    week_total_display: str = Field(
        description="Week total in hh:mm format",
        examples=["42:15"],
    )


class ExportFormat(StrEnum):
    """
    Supported export file formats.

    csv   — Comma-separated values, UTF-8 with BOM (Excel-compatible)
    excel — Microsoft Excel .xlsx via openpyxl
    pdf   — PDF report via reportlab
    """

    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"
