# =============================================================================
# backend/app/models/timesheet.py
#
# SQLAlchemy ORM model for the `timesheet_entries` table.
#
# Design decisions:
#   - Time is stored as INTEGER minutes (e.g. 90 = 1h 30m).
#     This simplifies daily/weekly sum calculations and avoids TIME type
#     quirks across SQL Server versions.
#   - Valid minutes values are multiples of 15, enforced by the service layer.
#   - One employee can have multiple entries per day (multi-input support).
#   - Audit columns track creation and modification with employee references.
# =============================================================================

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.employee import Employee


class TimesheetEntry(Base):
    """
    Represents a single timesheet entry for one employee on one specific date.

    Columns:
        id           — auto-incremented primary key
        employee_id  — FK to employees.id
        entry_date   — date the work was performed (no time component)
        minutes      — duration in minutes (multiples of 15; validated in service layer)
                       e.g. 90 = 1h 30m, 480 = 8h
        description  — free-text description of work performed
        created_at   — UTC timestamp when the record was created
        updated_at   — UTC timestamp of the last modification (auto-updated)
        created_by   — employee_id of the user who created this record
        updated_by   — employee_id of the user who last updated this record
    """

    __tablename__ = "timesheet_entries"

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
    # Foreign key to the employee who owns this entry
    # -------------------------------------------------------------------------
    employee_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="References employees.id — the owner of this timesheet entry",
    )

    # -------------------------------------------------------------------------
    # Work date and duration
    # -------------------------------------------------------------------------
    entry_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Calendar date on which the work was performed (no time component)",
    )
    minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment=(
            "Duration of work in minutes. Must be a positive multiple of 15. "
            "Enforced by the service layer, not a DB constraint (SQL Server 2012 compat)."
        ),
    )

    # -------------------------------------------------------------------------
    # Free-text description
    # -------------------------------------------------------------------------
    description: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
        default="",
        comment="Free-text description of work performed on entry_date",
    )

    # -------------------------------------------------------------------------
    # Audit columns
    # -------------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="UTC timestamp when this entry was created",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="UTC timestamp of the last modification to this entry",
    )
    created_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
        comment="employee.id of the user who created this record (nullable in v1)",
    )
    updated_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
        comment="employee.id of the user who last updated this record (nullable in v1)",
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    employee: Mapped[Employee] = relationship(  # type: ignore[name-defined]
        "Employee",
        primaryjoin="TimesheetEntry.employee_id == Employee.id",
        foreign_keys="[TimesheetEntry.employee_id]",
        back_populates="timesheet_entries",
        lazy="select",
    )

    # -------------------------------------------------------------------------
    # Computed helpers
    # -------------------------------------------------------------------------
    @property
    def hours_display(self) -> str:
        """
        Return a human-readable hh:mm string representation of `minutes`.

        Example: minutes=90 → '01:30'
        """
        h, m = divmod(self.minutes, 60)
        return f"{h:02d}:{m:02d}"

    def __repr__(self) -> str:
        return (
            f"TimesheetEntry(id={self.id!r}, employee_id={self.employee_id!r}, "
            f"entry_date={self.entry_date!r}, minutes={self.minutes!r})"
        )



