# =============================================================================
# backend/app/routers/employees.py
#
# FastAPI router for the /api/employees endpoint.
#
# Endpoints:
#   GET  /api/employees        — list all active employees (for selector dropdown)
#   GET  /api/employees/{id}   — get a single employee by ID
#   POST /api/employees        — create a new employee record
#   PUT  /api/employees/{id}   — update an employee record (partial update)
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.employee import Employee
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeListItem,
    EmployeeRead,
    EmployeeUpdate,
)

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.get(
    "/",
    response_model=list[EmployeeListItem],
    summary="List all active employees",
    description=(
        "Returns all active employees ordered by lastname then surname. "
        "Used to populate the employee selector dropdown in the frontend."
    ),
)
def list_employees(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
) -> list[Employee]:
    """
    Retrieve all employees from the database.

    By default returns only active employees (is_active=True).
    Pass include_inactive=true to include deactivated employees as well.
    """
    stmt = select(Employee).order_by(Employee.lastname, Employee.surname)
    if not include_inactive:
        # Filter to only active employees for the frontend dropdown
        stmt = stmt.where(Employee.is_active == True)  # noqa: E712 — must use == for SQL Server BIT compatibility
    rows = db.execute(stmt).scalars().all()
    return list(rows)


@router.get(
    "/{employee_id}",
    response_model=EmployeeRead,
    summary="Get a single employee by ID",
)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
) -> Employee:
    """
    Retrieve a single employee record by their primary key.

    Raises HTTP 404 if the employee does not exist.
    """
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with id={employee_id} not found",
        )
    return employee


@router.post(
    "/",
    response_model=EmployeeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new employee",
)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
) -> Employee:
    """
    Create a new employee record in the employees table.

    Returns the created employee including the generated primary key.
    """
    employee = Employee(
        surname=payload.surname,
        lastname=payload.lastname,
        is_active=payload.is_active,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.put(
    "/{employee_id}",
    response_model=EmployeeRead,
    summary="Update an employee (partial update)",
)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
) -> Employee:
    """
    Partially update an employee record.

    Only fields explicitly provided in the request body will be updated.
    Raises HTTP 404 if the employee does not exist.
    """
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with id={employee_id} not found",
        )

    # Apply only the fields that were provided (not None)
    if payload.surname is not None:
        employee.surname = payload.surname
    if payload.lastname is not None:
        employee.lastname = payload.lastname
    if payload.is_active is not None:
        employee.is_active = payload.is_active

    db.commit()
    db.refresh(employee)
    return employee
