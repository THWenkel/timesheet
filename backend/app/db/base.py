# =============================================================================
# backend/app/db/base.py
#
# SQLAlchemy declarative base.
#
# All ORM model classes must inherit from `Base`. This module also re-exports
# all models so that Alembic's env.py can import a single symbol and have
# access to the full metadata for autogenerate migrations.
# =============================================================================

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Shared declarative base for all ORM models.

    Usage:
        from app.db.base import Base

        class MyModel(Base):
            __tablename__ = "my_table"
            ...
    """


# Import all models here so that Alembic can detect them during autogenerate.
# This avoids the common pitfall of Alembic not seeing models that were never
# imported before calling metadata.create_all() / env.py.
# (Imports are placed here at the bottom to avoid circular imports.)
from app.models.employee import Employee  # noqa: E402
from app.models.timesheet import TimesheetEntry  # noqa: E402

__all__ = ["Base", "Employee", "TimesheetEntry"]
