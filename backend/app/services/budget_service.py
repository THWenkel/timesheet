# =============================================================================
# backend/app/services/budget_service.py
#
# Budget consumption of a project: booked time per month (all employees),
# the share of one employee, and the remaining budget.
#
# Budgets are stored in hours or person-days. Person-days are converted with
# settings.hours_per_person_day.
# =============================================================================

from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.project import Project
from app.models.timesheet import TimesheetEntry
from app.schemas.budget import BudgetMonth, BudgetOverview


def budget_to_minutes(project: Project) -> int | None:
    """Budget of the project in minutes, None if it has no (or a zero) budget."""
    amount = float(project.budget_amount)
    if amount <= 0:
        return None
    hours = amount * settings.hours_per_person_day if project.budget_unit == "person_days" else amount
    return round(hours * 60)


def minutes_to_unit(minutes: int, unit: str) -> float:
    """Convert minutes into the budget unit ('hours' or 'person_days')."""
    hours = minutes / 60
    return hours / settings.hours_per_person_day if unit == "person_days" else hours


def _next_month(day: date) -> date:
    return date(day.year + 1, 1, 1) if day.month == 12 else date(day.year, day.month + 1, 1)


def get_budget_overview(
    db: Session, project: Project, employee_id: int, to_date: date
) -> BudgetOverview:
    """
    Consumption of ``project`` from the first booking (or project start) up to ``to_date``.

    Counts every employee's time, so the remaining budget is the project's, not the
    employee's. The employee's own share is reported separately.
    """
    year = func.year(TimesheetEntry.entry_date)
    month = func.month(TimesheetEntry.entry_date)
    rows = db.execute(
        select(
            year.label("y"),
            month.label("m"),
            func.sum(TimesheetEntry.minutes).label("total"),
            func.sum(
                case((TimesheetEntry.employee_id == employee_id, TimesheetEntry.minutes), else_=0)
            ).label("mine"),
        )
        .where(TimesheetEntry.project_id == project.id, TimesheetEntry.entry_date <= to_date)
        .group_by(year, month)
    ).all()
    booked = {date(int(r.y), int(r.m), 1): (int(r.total), int(r.mine)) for r in rows}

    budget = budget_to_minutes(project)
    first = min([date(project.starts_on.year, project.starts_on.month, 1), *booked])
    last = date(to_date.year, to_date.month, 1)

    months: list[BudgetMonth] = []
    cumulative = 0
    current = first
    while current <= last:
        total, mine = booked.get(current, (0, 0))
        cumulative += total
        months.append(
            BudgetMonth(
                month=current,
                project_minutes=total,
                employee_minutes=mine,
                cumulative_minutes=cumulative,
                remaining_minutes=None if budget is None else budget - cumulative,
            )
        )
        current = _next_month(current)

    return BudgetOverview(
        project_id=project.id,
        budget_unit=project.budget_unit,
        budget_amount=float(project.budget_amount),
        budget_minutes=budget,
        hours_per_person_day=settings.hours_per_person_day,
        total_minutes=cumulative,
        employee_minutes=sum(m.employee_minutes for m in months),
        remaining_minutes=None if budget is None else budget - cumulative,
        percent_used=None if budget is None else round(cumulative / budget * 100, 1),
        months=months,
    )
