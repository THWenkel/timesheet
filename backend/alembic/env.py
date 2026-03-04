# =============================================================================
# backend/alembic/env.py
#
# Alembic environment configuration.
#
# This module is called by Alembic to set up the migration context.
# It reads the database URL from the application settings (pydantic-settings)
# rather than hardcoding it in alembic.ini, keeping secrets out of config files.
#
# Supports both online mode (direct DB connection) and offline mode
# (SQL script output for DBA review before applying to production).
# =============================================================================

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import app settings to get the database URL
from app.core.config import settings

# Import Base with all models registered so Alembic can detect schema changes
from app.db.base import Base
from app.db.session import _build_connection_string

# ---------------------------------------------------------------------------
# Alembic Config object — provides access to values in alembic.ini
# ---------------------------------------------------------------------------
config = context.config

# Set up Python logging using the alembic.ini [loggers] configuration
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Override the sqlalchemy.url with the dynamically built connection string
# from the application settings. This avoids duplicating the DB URL in ini.
# ---------------------------------------------------------------------------
config.set_main_option("sqlalchemy.url", _build_connection_string())

# Target metadata — Alembic uses this for --autogenerate comparisons
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Generates SQL statements to stdout/file without connecting to the DB.
    Useful for generating SQL scripts for manual DBA review before applying
    changes to a production database.

    Usage:
        alembic upgrade head --sql > upgrade.sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Include schema information in the generated SQL
        include_schemas=True,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (direct database connection).

    Creates a connection to the SQL Server and runs the migration scripts
    within a transaction.  Each migration is atomic — on failure the
    transaction is rolled back automatically.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Don't pool connections for migration runs
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------------
# Entry point — called by Alembic
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
