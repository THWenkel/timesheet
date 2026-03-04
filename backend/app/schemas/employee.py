# =============================================================================
# backend/app/schemas/employee.py
#
# Pydantic v2 schemas for the Employee resource.
#
# Schema hierarchy:
#   EmployeeBase        — shared fields (surname, lastname)
#   EmployeeCreate      — used for POST /api/employees (inherits Base)
#   EmployeeUpdate      — used for PUT /api/employees/{id} (all fields optional)
#   EmployeeRead        — used for API responses (includes id, audit fields)
#   EmployeeListItem    — lightweight version for dropdown lists (id + display_name)
# =============================================================================

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EmployeeBase(BaseModel):
    """
    Shared fields for Employee create and update operations.
    """

    surname: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["Max"],
        description="Employee given name / first name",
    )
    lastname: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["Mustermann"],
        description="Employee family name",
    )
    is_active: bool = Field(
        default=True,
        description="Whether this employee is active and visible in the UI",
    )


class EmployeeCreate(EmployeeBase):
    """
    Schema for creating a new employee (POST /api/employees).

    Inherits all fields from EmployeeBase.
    No additional fields needed for creation.
    """


class EmployeeUpdate(BaseModel):
    """
    Schema for partially updating an employee (PUT /api/employees/{id}).

    All fields are optional — only provided fields will be updated.
    """

    surname: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Updated given name",
    )
    lastname: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Updated family name",
    )
    is_active: bool | None = Field(
        default=None,
        description="Set to False to soft-delete the employee",
    )


class EmployeeRead(EmployeeBase):
    """
    Schema for reading an employee from the API (included in API responses).

    Includes all base fields plus the primary key and audit timestamps.
    Configured with from_attributes=True for seamless ORM model mapping.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Auto-incremented primary key")
    display_name: str = Field(
        description="Human-readable name: 'Surname Lastname'",
        examples=["Max Mustermann"],
    )
    created_at: datetime = Field(description="UTC timestamp of record creation")
    updated_at: datetime = Field(description="UTC timestamp of last modification")
    created_by: int | None = Field(default=None, description="employee.id who created this")
    updated_by: int | None = Field(default=None, description="employee.id who last updated this")


class EmployeeListItem(BaseModel):
    """
    Lightweight employee representation for dropdown/selector lists.

    Returns only the id and display_name to minimise payload size
    when populating the employee selector in the frontend.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Employee primary key")
    display_name: str = Field(
        description="Human-readable name shown in the selector: 'Surname Lastname'",
        examples=["Max Mustermann"],
    )
    is_active: bool = Field(description="Whether the employee is currently active")
