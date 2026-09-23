from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    notes: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    street_1: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    street_2: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    supplier_number: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    contact_person: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    contact_phone: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    contact_email: Mapped[str] = mapped_column(String(254), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CountryCode2(Base):
    __tablename__ = "CountryCode2"

    country_code: Mapped[str] = mapped_column(String(2), primary_key=True)
    country_name: Mapped[str] = mapped_column(String(200), nullable=False)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    purchase_number: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    unloading_point: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    consuming_plant: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    contact_person: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    contact_phone: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    contact_email: Mapped[str] = mapped_column(String(254), nullable=False, default="")
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    daily_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    budget_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    budget_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ProjectAllocation(Base):
    __tablename__ = "project_allocations"
    __table_args__ = (
        UniqueConstraint("project_id", "employee_id", name="UQ_project_allocations_project_employee"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
