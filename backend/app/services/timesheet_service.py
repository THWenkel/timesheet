# =============================================================================
# backend/app/services/timesheet_service.py
#
# Business logic for timesheet entry management.
#
# Responsibilities:
#   - CRUD operations for TimesheetEntry records
#   - 24-hour-per-day validation (total minutes for an employee on a date ≤ 1440)
#   - Calculating day and week summaries
#   - Fetching the list of dates with entries (for calendar colouring)
# =============================================================================

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.timesheet import TimesheetEntry
from app.schemas.timesheet import (
    DateWithEntries,
    DaySummary,
    TimesheetEntryCreate,
    TimesheetEntryRead,
    TimesheetEntryUpdate,
    WeekDayEntry,
    WeekSummary,
)


def _minutes_to_display(minutes: int) -> str:
    """
    Convert an integer minute count to a human-readable hh:mm string.

    Args:
        minutes: Total duration in minutes (must be >= 0).

    Returns:
        A zero-padded string in the format 'hh:mm', e.g. '08:30'.
    """
    h, m = divmod(minutes, 60)
    return f"{h:02d}:{m:02d}"


def _get_day_total(db: Session, employee_id: int, entry_date: date, exclude_id: int | None = None) -> int:
    """
    Calculate the total minutes already logged for an employee on a specific date.

    Optionally excludes a specific entry by ID (used during update operations
    to avoid counting the entry being updated against itself).

    Args:
        db:          Active database session.
        employee_id: The employee whose entries should be summed.
        entry_date:  The date to calculate the total for.
        exclude_id:  Optional entry ID to exclude from the sum.

    Returns:
        Total minutes already logged on the given date.
    """
    stmt = select(func.coalesce(func.sum(TimesheetEntry.minutes), 0)).where(
        TimesheetEntry.employee_id == employee_id,
        TimesheetEntry.entry_date == entry_date,
    )
    if exclude_id is not None:
        # Exclude the entry that is being updated so we don't double-count it
        stmt = stmt.where(TimesheetEntry.id != exclude_id)
    result: int = db.execute(stmt).scalar_one()
    return result


def get_entries_for_date(
    db: Session,
    employee_id: int,
    entry_date: date,
) -> list[TimesheetEntryRead]:
    """
    Fetch all timesheet entries for a specific employee on a specific date.

    Args:
        db:          Active database session.
        employee_id: Employee to fetch entries for.
        entry_date:  The date to fetch entries for.

    Returns:
        A list of TimesheetEntryRead schemas, sorted by entry creation time.
    """
    stmt = (
        select(TimesheetEntry)
        .where(
            TimesheetEntry.employee_id == employee_id,
            TimesheetEntry.entry_date == entry_date,
        )
        .order_by(TimesheetEntry.created_at)
    )
    rows = db.execute(stmt).scalars().all()
    return [TimesheetEntryRead.model_validate(row) for row in rows]


def get_entries_for_range(
    db: Session,
    employee_id: int,
    from_date: date,
    to_date: date,
) -> list[TimesheetEntryRead]:
    """
    Fetch all timesheet entries for an employee within a date range (inclusive).

    Used for export operations.

    Args:
        db:          Active database session.
        employee_id: Employee to fetch entries for.
        from_date:   Start of the date range (inclusive).
        to_date:     End of the date range (inclusive).

    Returns:
        A list of TimesheetEntryRead schemas ordered by date then creation time.
    """
    stmt = (
        select(TimesheetEntry)
        .where(
            TimesheetEntry.employee_id == employee_id,
            TimesheetEntry.entry_date >= from_date,
            TimesheetEntry.entry_date <= to_date,
        )
        .order_by(TimesheetEntry.entry_date, TimesheetEntry.created_at)
    )
    rows = db.execute(stmt).scalars().all()
    return [TimesheetEntryRead.model_validate(row) for row in rows]


def get_dates_with_entries(
    db: Session,
    employee_id: int,
    year: int,
    month: int,
) -> list[DateWithEntries]:
    """
    Return all dates within a calendar month that have at least one entry.

    This is used by the frontend react-calendar to highlight dates with entries
    in dark blue via the tileClassName prop.

    Args:
        db:          Active database session.
        employee_id: Employee to check entries for.
        year:        Calendar year (e.g. 2026).
        month:       Calendar month 1-12.

    Returns:
        A list of DateWithEntries containing entry_date, total_minutes, and entry_count.
    """
    # Build date range for the specified month
    from_date = date(year, month, 1)
    # Last day of the month: first day of next month minus one day
    if month == 12:
        to_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        to_date = date(year, month + 1, 1) - timedelta(days=1)

    stmt = (
        select(
            TimesheetEntry.entry_date,
            func.sum(TimesheetEntry.minutes).label("total_minutes"),
            func.count(TimesheetEntry.id).label("entry_count"),
        )
        .where(
            TimesheetEntry.employee_id == employee_id,
            TimesheetEntry.entry_date >= from_date,
            TimesheetEntry.entry_date <= to_date,
        )
        .group_by(TimesheetEntry.entry_date)
        .order_by(TimesheetEntry.entry_date)
    )
    rows = db.execute(stmt).all()
    return [
        DateWithEntries(
            entry_date=row.entry_date,
            total_minutes=row.total_minutes,
            entry_count=row.entry_count,
        )
        for row in rows
    ]


def create_entry(
    db: Session,
    payload: TimesheetEntryCreate,
    acting_user_id: int | None = None,
) -> TimesheetEntryRead:
    """
    Create a new timesheet entry after validating the 24h daily limit.

    Validation rules:
      - The employee must exist and be active.
      - Adding the new entry's minutes to the existing day total must not
        exceed 1440 minutes (24 hours).

    Args:
        db:             Active database session.
        payload:        Validated TimesheetEntryCreate schema.
        acting_user_id: The employee performing the action (for audit cols; None in v1).

    Returns:
        The newly created entry as a TimesheetEntryRead schema.

    Raises:
        ValueError: If the employee is not found, not active, or the 24h limit is exceeded.
    """
    # --- Validate employee exists and is active ---
    employee = db.get(Employee, payload.employee_id)
    if employee is None:
        msg = f"Employee with id={payload.employee_id} not found"
        raise ValueError(msg)
    if not employee.is_active:
        msg = f"Employee with id={payload.employee_id} is not active"
        raise ValueError(msg)

    # --- Validate 24h daily limit ---
    existing_minutes = _get_day_total(db, payload.employee_id, payload.entry_date)
    if existing_minutes + payload.minutes > 1440:
        available = 1440 - existing_minutes
        msg = (
            f"Adding {payload.minutes} min would exceed 24h for "
            f"{payload.entry_date}. Already logged: {existing_minutes} min "
            f"({_minutes_to_display(existing_minutes)}). "
            f"Available: {available} min ({_minutes_to_display(available)})."
        )
        raise ValueError(msg)

    # --- Create the database record ---
    entry = TimesheetEntry(
        employee_id=payload.employee_id,
        entry_date=payload.entry_date,
        minutes=payload.minutes,
        description=payload.description,
        created_by=acting_user_id,
        updated_by=acting_user_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return TimesheetEntryRead.model_validate(entry)


def update_entry(
    db: Session,
    entry_id: int,
    payload: TimesheetEntryUpdate,
    acting_user_id: int | None = None,
) -> TimesheetEntryRead:
    """
    Update an existing timesheet entry.

    Only fields provided in the payload are updated (partial update).
    The 24h daily limit is re-validated after applying the new minutes value.

    Args:
        db:             Active database session.
        entry_id:       Primary key of the entry to update.
        payload:        Validated TimesheetEntryUpdate schema (partial fields).
        acting_user_id: The employee performing the update (for audit cols; None in v1).

    Returns:
        The updated entry as a TimesheetEntryRead schema.

    Raises:
        ValueError: If the entry is not found or the 24h limit is exceeded.
    """
    # --- Load existing entry ---
    entry = db.get(TimesheetEntry, entry_id)
    if entry is None:
        msg = f"TimesheetEntry with id={entry_id} not found"
        raise ValueError(msg)

    # --- Apply partial updates ---
    if payload.minutes is not None:
        # Validate 24h limit excluding the current entry's own minutes
        existing_minutes = _get_day_total(
            db, entry.employee_id, entry.entry_date, exclude_id=entry_id
        )
        new_minutes = payload.minutes
        if existing_minutes + new_minutes > 1440:
            available = 1440 - existing_minutes
            msg = (
                f"Updating to {new_minutes} min would exceed 24h for "
                f"{entry.entry_date}. Other entries: {existing_minutes} min. "
                f"Available: {available} min ({_minutes_to_display(available)})."
            )
            raise ValueError(msg)
        entry.minutes = new_minutes

    if payload.description is not None:
        entry.description = payload.description

    entry.updated_by = acting_user_id

    db.commit()
    db.refresh(entry)
    return TimesheetEntryRead.model_validate(entry)


def get_day_summary(
    db: Session,
    employee_id: int,
    entry_date: date,
) -> DaySummary:
    """
    Build a day summary with all entries and the total for a specific date.

    Args:
        db:          Active database session.
        employee_id: Employee to summarise.
        entry_date:  The specific date to summarise.

    Returns:
        A DaySummary containing the individual entries and total minutes.
    """
    entries = get_entries_for_date(db, employee_id, entry_date)
    total = sum(e.minutes for e in entries)
    return DaySummary(
        entry_date=entry_date,
        total_minutes=total,
        total_display=_minutes_to_display(total),
        entries=entries,
    )


def get_week_summary(
    db: Session,
    employee_id: int,
    any_date_in_week: date,
) -> WeekSummary:
    """
    Build a weekly summary for the 7-day week (Mon-Sun) containing `any_date_in_week`.

    Args:
        db:                 Active database session.
        employee_id:        Employee to summarise.
        any_date_in_week:   Any date within the target week.

    Returns:
        A WeekSummary with per-day totals (Mon-Sun) and a grand total for the week.
    """
    # Calculate the Monday of the week containing the given date
    week_start = any_date_in_week - timedelta(days=any_date_in_week.weekday())
    week_end = week_start + timedelta(days=6)  # Sunday

    # Fetch all entries for the full week in one database query
    stmt = (
        select(
            TimesheetEntry.entry_date,
            func.sum(TimesheetEntry.minutes).label("total_minutes"),
        )
        .where(
            TimesheetEntry.employee_id == employee_id,
            TimesheetEntry.entry_date >= week_start,
            TimesheetEntry.entry_date <= week_end,
        )
        .group_by(TimesheetEntry.entry_date)
    )
    rows = db.execute(stmt).all()

    # Build a lookup dict { date -> total_minutes }
    day_totals: dict[date, int] = {row.entry_date: row.total_minutes for row in rows}

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    days: list[WeekDayEntry] = []

    for i in range(7):
        current = week_start + timedelta(days=i)
        total = day_totals.get(current, 0)
        days.append(
            WeekDayEntry(
                entry_date=current,
                day_name=day_names[i],
                total_minutes=total,
                total_display=_minutes_to_display(total),
                has_entries=current in day_totals,
            )
        )

    week_total = sum(d.total_minutes for d in days)

    return WeekSummary(
        week_start=week_start,
        week_end=week_end,
        days=days,
        week_total_minutes=week_total,
        week_total_display=_minutes_to_display(week_total),
    )
