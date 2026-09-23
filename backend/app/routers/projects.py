from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.employee import Employee
from app.models.project import CountryCode2, Customer, Project, ProjectAllocation
from app.schemas.project import (
    BudgetUnit,
    CountryCodeRead,
    CustomerRead,
    CustomerWrite,
    ProjectRead,
    ProjectStatus,
    ProjectWrite,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])
customers_router = APIRouter(prefix="/api/customers", tags=["customers"])
country_codes_router = APIRouter(prefix="/api/country-codes", tags=["country-codes"])


def _get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _get_or_create_customer(db: Session, name: str) -> Customer:
    normalized_name = name.strip()
    customer = db.execute(
        select(Customer).where(func.lower(Customer.name) == normalized_name.lower())
    ).scalar_one_or_none()
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Customer must be created in customer administration first",
        )
    return customer


def _normalize_country_code(db: Session, country: str) -> str:
    country_code = country.strip().upper()
    if db.get(CountryCode2, country_code) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown ISO 3166-1 alpha-2 country code: {country_code}",
        )
    return country_code


def _validate_employee_ids(db: Session, employee_ids: list[int]) -> None:
    if not employee_ids:
        return
    existing_ids = set(
        db.execute(select(Employee.id).where(Employee.id.in_(employee_ids))).scalars().all()
    )
    missing_ids = sorted(set(employee_ids) - existing_ids)
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown employee IDs: {missing_ids}",
        )


def _replace_allocations(db: Session, project_id: int, employee_ids: list[int]) -> None:
    db.execute(delete(ProjectAllocation).where(ProjectAllocation.project_id == project_id))
    db.add_all(
        ProjectAllocation(project_id=project_id, employee_id=employee_id)
        for employee_id in employee_ids
    )


def _to_read(db: Session, project: Project) -> ProjectRead:
    customer_name = db.execute(
        select(Customer.name).where(Customer.id == project.customer_id)
    ).scalar_one()
    employees = db.execute(
        select(Employee)
        .join(ProjectAllocation, ProjectAllocation.employee_id == Employee.id)
        .where(ProjectAllocation.project_id == project.id)
        .order_by(Employee.lastname, Employee.surname)
    ).scalars().all()
    return ProjectRead(
        id=project.id,
        name=project.name,
        description=project.description,
        customer_name=customer_name,
        purchase_number=project.purchase_number,
        unloading_point=project.unloading_point,
        consuming_plant=project.consuming_plant,
        contact_person=project.contact_person,
        contact_phone=project.contact_phone,
        contact_email=project.contact_email,
        hourly_rate=project.hourly_rate,
        daily_rate=project.daily_rate,
        budget_amount=project.budget_amount,
        budget_unit=BudgetUnit(project.budget_unit),
        starts_on=project.starts_on,
        ends_on=project.ends_on,
        status=ProjectStatus(project.status),
        employee_ids=[employee.id for employee in employees],
        assigned_employees=[employee.display_name for employee in employees],
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@customers_router.get("/", response_model=list[CustomerRead])
def list_customers(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
) -> list[Customer]:
    statement = select(Customer).order_by(Customer.name)
    if not include_inactive:
        statement = statement.where(Customer.is_active == True)  # noqa: E712
    return list(db.execute(statement).scalars().all())


@country_codes_router.get("/", response_model=list[CountryCodeRead])
def list_country_codes(db: Session = Depends(get_db)) -> list[CountryCode2]:
    return list(db.execute(select(CountryCode2).order_by(CountryCode2.country_code)).scalars().all())


@customers_router.post(
    "/",
    response_model=CustomerRead,
    status_code=status.HTTP_201_CREATED,
)
def create_customer(payload: CustomerWrite, db: Session = Depends(get_db)) -> Customer:
    normalized_name = payload.name.strip()
    country_code = _normalize_country_code(db, payload.country)
    existing = db.execute(
        select(Customer).where(func.lower(Customer.name) == normalized_name.lower())
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A customer with this name already exists",
        )
    customer = Customer(
        name=normalized_name,
        notes=payload.notes.strip(),
        street_1=payload.street_1.strip(),
        street_2=payload.street_2.strip(),
        postal_code=payload.postal_code.strip(),
        city=payload.city.strip(),
        country=country_code,
        supplier_number=payload.supplier_number.strip(),
        contact_person=payload.contact_person.strip(),
        contact_phone=payload.contact_phone.strip(),
        contact_email=payload.contact_email.strip(),
        is_active=payload.is_active,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@customers_router.put("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: int,
    payload: CustomerWrite,
    db: Session = Depends(get_db),
) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    normalized_name = payload.name.strip()
    country_code = _normalize_country_code(db, payload.country)
    duplicate = db.execute(
        select(Customer).where(
            func.lower(Customer.name) == normalized_name.lower(),
            Customer.id != customer_id,
        )
    ).scalar_one_or_none()
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A customer with this name already exists",
        )
    customer.name = normalized_name
    customer.notes = payload.notes.strip()
    customer.street_1 = payload.street_1.strip()
    customer.street_2 = payload.street_2.strip()
    customer.postal_code = payload.postal_code.strip()
    customer.city = payload.city.strip()
    customer.country = country_code
    customer.supplier_number = payload.supplier_number.strip()
    customer.contact_person = payload.contact_person.strip()
    customer.contact_phone = payload.contact_phone.strip()
    customer.contact_email = payload.contact_email.strip()
    customer.is_active = payload.is_active
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/", response_model=list[ProjectRead])
def list_projects(
    employee_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[ProjectRead]:
    statement = select(Project).order_by(Project.name)
    if employee_id is not None:
        statement = statement.join(ProjectAllocation).where(
            ProjectAllocation.employee_id == employee_id
        )
    projects = db.execute(statement).scalars().all()
    return [_to_read(db, project) for project in projects]


@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectWrite, db: Session = Depends(get_db)) -> ProjectRead:
    _validate_employee_ids(db, payload.employee_ids)
    customer = _get_or_create_customer(db, payload.customer_name)
    project = Project(
        customer_id=customer.id,
        name=payload.name.strip(),
        description=payload.description.strip(),
        purchase_number=payload.purchase_number.strip(),
        unloading_point=payload.unloading_point.strip(),
        consuming_plant=payload.consuming_plant.strip(),
        contact_person=payload.contact_person.strip(),
        contact_phone=payload.contact_phone.strip(),
        contact_email=payload.contact_email.strip(),
        hourly_rate=payload.hourly_rate,
        daily_rate=payload.daily_rate,
        budget_amount=payload.budget_amount,
        budget_unit=payload.budget_unit.value,
        starts_on=payload.starts_on,
        ends_on=payload.ends_on,
        status=payload.status.value,
    )
    db.add(project)
    db.flush()
    _replace_allocations(db, project.id, payload.employee_ids)
    db.commit()
    db.refresh(project)
    return _to_read(db, project)


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    payload: ProjectWrite,
    db: Session = Depends(get_db),
) -> ProjectRead:
    project = _get_project_or_404(db, project_id)
    _validate_employee_ids(db, payload.employee_ids)
    customer = _get_or_create_customer(db, payload.customer_name)
    project.customer_id = customer.id
    project.name = payload.name.strip()
    project.description = payload.description.strip()
    project.purchase_number = payload.purchase_number.strip()
    project.unloading_point = payload.unloading_point.strip()
    project.consuming_plant = payload.consuming_plant.strip()
    project.contact_person = payload.contact_person.strip()
    project.contact_phone = payload.contact_phone.strip()
    project.contact_email = payload.contact_email.strip()
    project.hourly_rate = payload.hourly_rate
    project.daily_rate = payload.daily_rate
    project.budget_amount = payload.budget_amount
    project.budget_unit = payload.budget_unit.value
    project.starts_on = payload.starts_on
    project.ends_on = payload.ends_on
    project.status = payload.status.value
    _replace_allocations(db, project.id, payload.employee_ids)
    db.commit()
    db.refresh(project)
    return _to_read(db, project)
