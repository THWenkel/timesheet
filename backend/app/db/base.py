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


__all__ = ["Base"]
