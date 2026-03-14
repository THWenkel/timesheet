# =============================================================================
# backend/app/models/employee.py
#
# SQLAlchemy ORM model for the `employees` table.
#
# Table stores the list of employees who can submit timesheet entries.
# Surname and lastname are kept as separate columns so they can be sorted,
# filtered, and displayed independently.
#
# Audit columns (created_at, updated_at, created_by, updated_by) are present
# on this table to track record management history.
# =============================================================================

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.timesheet import TimesheetEntry


class Employee(Base):
    """
    Represents a single employee record.

    Columns:
        id          — auto-incremented primary key
        surname     — first name / given name (e.g. "Max")
        lastname    — family name (e.g. "Mustermann")
        is_active   — soft-delete flag; inactive employees are hidden from the UI
        created_at  — UTC timestamp when the record was created
        updated_at  — UTC timestamp of the last modification (auto-updated)
        created_by  — employee_id of the user who created this record (nullable in v1)
        updated_by  — employee_id of the user who last updated this record (nullable in v1)
    """

    __tablename__ = "employees"

    # -------------------------------------------------------------------------
    # Primary key
    # -------------------------------------------------------------------------
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Auto-incremented primary key",
    )

    # -------------------------------------------------------------------------
    # Employee name — stored in separate columns for independent sorting/filtering
    # -------------------------------------------------------------------------
    surname: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Employee given name / first name",
    )
    lastname: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Employee family name",
    )

    # -------------------------------------------------------------------------
    # Soft-delete flag
    # -------------------------------------------------------------------------
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="False means the employee is deactivated and hidden from UI",
    )

    # -------------------------------------------------------------------------
    # Audit columns
    # -------------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="UTC timestamp when this record was created",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="UTC timestamp of the last update to this record",
    )
    created_by: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="employee.id of the user who created this record (nullable in v1)",
    )
    updated_by: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="employee.id of the user who last updated this record (nullable in v1)",
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    timesheet_entries: Mapped[list[TimesheetEntry]] = relationship(  # type: ignore[name-defined]
        "TimesheetEntry",
        primaryjoin="TimesheetEntry.employee_id == Employee.id",
        foreign_keys="[TimesheetEntry.employee_id]",
        back_populates="employee",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    @property
    def display_name(self) -> str:
        """
        Return the human-readable display name in 'Surname Lastname' format.

        Used in the frontend employee selector dropdown.
        """
        return f"{self.surname} {self.lastname}"

    def __repr__(self) -> str:
        return f"Employee(id={self.id!r}, surname={self.surname!r}, lastname={self.lastname!r})"



