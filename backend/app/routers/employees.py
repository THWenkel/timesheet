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
#   DELETE /api/employees/{id} — delete an employee that has no timesheet entries
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.security import (
    AuthContext,
    ensure_employee_access,
    require_admin,
    require_user,
)
from app.db.session import get_db
from app.models.employee import Employee
from app.models.project import ProjectAllocation
from app.models.timesheet import TimesheetEntry
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeListItem,
    EmployeeRead,
    EmployeeUpdate,
)

router = APIRouter(prefix="/api/employees", tags=["employees"])


def _clean_username(username: str | None) -> str | None:
    return username.strip().lower() if username else None


def _ensure_username_free(db: Session, username: str | None, own_id: int | None) -> None:
    """Usernames are unique; raise 409 if another employee already has this one."""
    if username is None:
        return
    other = db.execute(select(Employee.id).where(Employee.username == username)).scalar()
    if other is not None and other != own_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{username}' is already in use",
        )


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
    _admin: AuthContext | None = Depends(require_admin),
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
    "/admin",
    response_model=list[EmployeeRead],
    summary="List employees with administration details",
)
def list_employees_for_admin(
    include_inactive: bool = True,
    db: Session = Depends(get_db),
    _admin: AuthContext | None = Depends(require_admin),
) -> list[Employee]:
    """Return complete employee records for the administration client."""
    stmt = select(Employee).order_by(Employee.lastname, Employee.surname)
    if not include_inactive:
        stmt = stmt.where(Employee.is_active == True)  # noqa: E712
    return list(db.execute(stmt).scalars().all())


@router.get(
    "/{employee_id}",
    response_model=EmployeeRead,
    summary="Get a single employee by ID",
)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext | None = Depends(require_user),
) -> Employee:
    """
    Retrieve a single employee record by their primary key.

    Raises HTTP 404 if the employee does not exist.
    """
    ensure_employee_access(auth, employee_id)
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
    _admin: AuthContext | None = Depends(require_admin),
) -> Employee:
    """
    Create a new employee record in the employees table.

    Returns the created employee including the generated primary key.
    """
    employee = Employee(
        surname=payload.surname,
        lastname=payload.lastname,
        is_active=payload.is_active,
        username=_clean_username(payload.username),
        is_admin=payload.is_admin,
    )
    _ensure_username_free(db, employee.username, None)
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
    admin: AuthContext | None = Depends(require_admin),
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

    # An administrator must not lock themselves out: with their own account deactivated or
    # stripped of the admin right, the session ends at once and nobody may be left to fix it.
    if admin is not None and admin.employee_id == employee_id:
        if payload.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account",
            )
        if payload.is_admin is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot remove your own administrator right",
            )

    # Apply only the fields that were provided (not None)
    if payload.surname is not None:
        employee.surname = payload.surname
    if payload.lastname is not None:
        employee.lastname = payload.lastname
    if payload.is_active is not None:
        employee.is_active = payload.is_active
    if payload.username is not None:
        username = _clean_username(payload.username)
        _ensure_username_free(db, username, employee_id)
        employee.username = username
    if payload.is_admin is not None:
        employee.is_admin = payload.is_admin

    db.commit()
    db.refresh(employee)
    return employee


@router.delete(
    "/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an employee (only if there are no timesheet entries)",
)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    admin: AuthContext | None = Depends(require_admin),
) -> None:
    """
    Permanently delete an employee record.

    Only allowed for employees without any timesheet data: the database would
    otherwise cascade the delete to all their entries (working time that reports
    depend on). Employees with entries can only be deactivated.

    Raises HTTP 404 if the employee does not exist.
    Raises HTTP 400 if an administrator tries to delete their own account.
    Raises HTTP 409 if timesheet entries exist for or were created by the employee.
    """
    if admin is not None and admin.employee_id == employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with id={employee_id} not found",
        )

    entry_count = db.execute(
        select(func.count())
        .select_from(TimesheetEntry)
        .where(
            or_(
                TimesheetEntry.employee_id == employee_id,
                TimesheetEntry.created_by == employee_id,
                TimesheetEntry.updated_by == employee_id,
            )
        )
    ).scalar_one()
    if entry_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"{employee.display_name} has {entry_count} timesheet entries and cannot "
                "be deleted. Deactivate the employee instead."
            ),
        )

    # Project assignments carry no working time; they go with the employee.
    db.execute(delete(ProjectAllocation).where(ProjectAllocation.employee_id == employee_id))
    db.delete(employee)
    db.commit()
