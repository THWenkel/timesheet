# =============================================================================
# backend/app/schemas/budget.py
#
# Budget consumption overview of one project (used by the PDF/Excel export).
# All durations are integer minutes; conversion to hours or person-days happens
# at the edge (see budget_service.minutes_to_unit).
# =============================================================================

from datetime import date

from pydantic import BaseModel, Field


class BudgetMonth(BaseModel):
    """Booked time of one calendar month."""

    month: date = Field(description="First day of the month")
    project_minutes: int = Field(description="All employees booked on the project this month")
    employee_minutes: int = Field(description="Part of project_minutes booked by the employee")
    cumulative_minutes: int = Field(description="Project total up to and including this month")
    remaining_minutes: int | None = Field(
        description="Budget minus cumulative_minutes (negative = overrun); None without budget"
    )


class BudgetOverview(BaseModel):
    """Budget, consumption per month and remaining budget of a project."""

    project_id: int
    budget_unit: str = Field(description="'hours' or 'person_days'")
    budget_amount: float = Field(description="Budget in budget_unit")
    budget_minutes: int | None = Field(description="Budget in minutes; None when no budget is set")
    hours_per_person_day: float
    total_minutes: int = Field(description="Project total booked up to the end of the period")
    employee_minutes: int = Field(description="Part of total_minutes booked by the employee")
    remaining_minutes: int | None = Field(description="Remaining budget (negative = overrun)")
    percent_used: float | None = Field(description="total_minutes / budget_minutes * 100")
    months: list[BudgetMonth]
