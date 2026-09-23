from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class BudgetUnit(StrEnum):
    HOURS = "hours"
    PERSON_DAYS = "person_days"


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


def _empty_employee_ids() -> list[int]:
    return []


class ProjectWrite(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    customer_name: str = Field(min_length=1, max_length=200)
    purchase_number: str = Field(default="", max_length=100)
    unloading_point: str = Field(default="", max_length=200)
    consuming_plant: str = Field(default="", max_length=200)
    contact_person: str = Field(default="", max_length=200)
    contact_phone: str = Field(default="", max_length=50)
    contact_email: str = Field(default="", max_length=254)
    hourly_rate: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)
    daily_rate: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)
    budget_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    budget_unit: BudgetUnit
    starts_on: date
    ends_on: date
    status: ProjectStatus = ProjectStatus.ACTIVE
    employee_ids: list[int] = Field(default_factory=_empty_employee_ids)

    @model_validator(mode="after")
    def validate_dates_and_employees(self) -> ProjectWrite:
        if self.ends_on < self.starts_on:
            raise ValueError("ends_on must be on or after starts_on")
        if len(self.employee_ids) != len(set(self.employee_ids)):
            raise ValueError("employee_ids must not contain duplicates")
        return self


class ProjectRead(ProjectWrite):
    id: int
    assigned_employees: list[str]
    created_at: datetime
    updated_at: datetime


class CustomerWrite(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    notes: str = Field(default="", max_length=2000)
    street_1: str = Field(default="", max_length=200)
    street_2: str = Field(default="", max_length=200)
    postal_code: str = Field(default="", max_length=20)
    city: str = Field(default="", max_length=100)
    country: str = Field(default="", max_length=2)
    supplier_number: str = Field(default="", max_length=100)
    contact_person: str = Field(default="", max_length=200)
    contact_phone: str = Field(default="", max_length=50)
    contact_email: str = Field(default="", max_length=254)
    is_active: bool = True


class CustomerRead(CustomerWrite):
    id: int
    created_at: datetime
    updated_at: datetime


class CountryCodeRead(BaseModel):
    country_code: str
    country_name: str

