# =============================================================================
# backend/app/routers/timesheets.py
#
# FastAPI router for the /api/timesheets endpoint.
#
# Endpoints:
#   GET  /api/timesheets/dates      — dates with entries for a month (calendar colouring)
#   GET  /api/timesheets/day        — all entries for a specific day
#   GET  /api/timesheets/week       -- week summary (Mon-Sun) for a given date
#   GET  /api/timesheets/{id}       — single entry by ID
#   POST /api/timesheets            — create a new entry
#   PUT  /api/timesheets/{id}       — update an entry (partial)
#   DELETE /api/timesheets/{id}     — delete an entry
# =============================================================================

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.timesheet import TimesheetEntry
from app.schemas.timesheet import (
    DateWithEntries,
    DaySummary,
    TimesheetEntryCreate,
    TimesheetEntryRead,
    TimesheetEntryUpdate,
    WeekSummary,
)
from app.services import timesheet_service

router = APIRouter(prefix="/api/timesheets", tags=["timesheets"])


@router.get(
    "/dates",
    response_model=list[DateWithEntries],
    summary="Get dates with entries for a calendar month",
    description=(
        "Returns all dates within the specified year/month that have at least "
        "one timesheet entry for the given employee. "
        "Used by the frontend to colour-code calendar days (dark blue = has entries)."
    ),
)
def get_dates_with_entries(
    employee_id: int,
    year: int,
    month: int,
    db: Session = Depends(get_db),
) -> list[DateWithEntries]:
    """
    Return dates within a calendar month that have timesheet entries.

    Validates the month parameter (1-12) and delegates to the service layer.
    """
    if not 1 <= month <= 12:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"month must be between 1 and 12, got {month}",
        )
    return timesheet_service.get_dates_with_entries(db, employee_id, year, month)


@router.get(
    "/day",
    response_model=DaySummary,
    summary="Get all entries and total for a specific day",
)
def get_day_summary(
    employee_id: int,
    entry_date: date,
    db: Session = Depends(get_db),
) -> DaySummary:
    """
    Retrieve all timesheet entries for an employee on a specific date,
    along with the total minutes logged for that day.
    """
    return timesheet_service.get_day_summary(db, employee_id, entry_date)


@router.get(
    "/week",
    response_model=WeekSummary,
    summary="Get weekly summary (Mon-Sun) for a given date",
)
def get_week_summary(
    employee_id: int,
    any_date: date,
    db: Session = Depends(get_db),
) -> WeekSummary:
    """
    Return a week summary for the 7-day period (Monday to Sunday)
    that contains `any_date`.

    Includes per-day totals, total minutes for the full week,
    and whether each day has any entries.
    """
    return timesheet_service.get_week_summary(db, employee_id, any_date)


@router.get(
    "/{entry_id}",
    response_model=TimesheetEntryRead,
    summary="Get a single timesheet entry by ID",
)
def get_entry(
    entry_id: int,
    db: Session = Depends(get_db),
) -> TimesheetEntry:
    """
    Retrieve a single timesheet entry by its primary key.

    Raises HTTP 404 if the entry does not exist.
    """
    entry = db.get(TimesheetEntry, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TimesheetEntry with id={entry_id} not found",
        )
    return entry


@router.post(
    "/",
    response_model=TimesheetEntryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new timesheet entry",
)
def create_entry(
    payload: TimesheetEntryCreate,
    db: Session = Depends(get_db),
) -> TimesheetEntryRead:
    """
    Create a new timesheet entry for an employee on a specific date.

    Business rules enforced:
      - The employee must exist and be active.
      - The new entry's minutes + existing daily total must not exceed 1440 (24h).
      - Minutes must be a positive multiple of 15 (validated by Pydantic schema).

    Returns the created entry with the generated ID and audit timestamps.
    Raises HTTP 400 if business rules are violated.
    Raises HTTP 422 if input validation fails (Pydantic).
    """
    try:
        return timesheet_service.create_entry(db, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.put(
    "/{entry_id}",
    response_model=TimesheetEntryRead,
    summary="Update a timesheet entry (partial update)",
)
def update_entry(
    entry_id: int,
    payload: TimesheetEntryUpdate,
    db: Session = Depends(get_db),
) -> TimesheetEntryRead:
    """
    Partially update an existing timesheet entry.

    Only fields provided in the request body are updated.
    The 24h daily limit is re-validated after applying the new values.

    Raises HTTP 404 if the entry does not exist.
    Raises HTTP 400 if the update would violate business rules.
    """
    try:
        return timesheet_service.update_entry(db, entry_id, payload)
    except ValueError as exc:
        detail = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND if "not found" in detail
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a timesheet entry",
)
def delete_entry(
    entry_id: int,
    db: Session = Depends(get_db),
) -> None:
    """
    Permanently delete a timesheet entry.

    Raises HTTP 404 if the entry does not exist.
    """
    entry = db.get(TimesheetEntry, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TimesheetEntry with id={entry_id} not found",
        )
    db.delete(entry)
    db.commit()
