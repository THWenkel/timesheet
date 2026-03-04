# =============================================================================
# backend/app/db/session.py
#
# SQLAlchemy engine and session factory.
#
# Connection target: Microsoft SQL Server 2012
#   Host   : dbserver01 (configured via settings.db_server)
#   DB     : WiTERP     (configured via settings.db_name)
#   Auth   : SQL Server authentication — user sa
#
# Driver  : ODBC Driver 17 for SQL Server
#   The ODBC driver must be installed on the host machine separately.
#   Download: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
#
# ⚠️  SECURITY TODO (before go-live):
#   1. Replace the 'sa' account with a dedicated least-privilege SQL user
#      that has only SELECT/INSERT/UPDATE on the required tables.
#   2. Change Encrypt=no → Encrypt=yes and configure a valid TLS certificate
#      on the SQL Server to prevent credentials from travelling in plain text.
#   3. Rotate the password and store it in a secrets manager rather than .env.
# =============================================================================

from collections.abc import Generator

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _build_connection_string() -> str:
    """
    Build the SQLAlchemy connection URL for Microsoft SQL Server via pyodbc.

    Uses SQLAlchemy's mssql+pyodbc dialect with a raw ODBC connection string
    passed as the `odbc_connect` query parameter.  This approach gives us full
    control over every ODBC keyword, which is especially useful for SQL Server
    2012 compatibility and the unencrypted connection requirement.

    Returns:
        A full SQLAlchemy connection URL string.
    """
    # --- Raw ODBC connection string (passed to pyodbc) ---
    # Encrypt=no  → required for SQL Server 2012 without a TLS certificate.
    #              ⚠️  TODO: Change to Encrypt=yes before production.
    # TrustServerCertificate=yes → avoids certificate validation errors in dev.
    #              ⚠️  TODO: Remove / set to no in production with a valid cert.
    odbc_params = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={settings.db_server};"
        f"DATABASE={settings.db_name};"
        f"UID={settings.db_user};"
        f"PWD={settings.db_password};"
        f"Encrypt={settings.db_encrypt};"
        "TrustServerCertificate=yes;"
        "Connection Timeout=30;"
    )

    # URL-encode the raw ODBC string as a query parameter
    import urllib.parse

    encoded = urllib.parse.quote_plus(odbc_params)
    return f"mssql+pyodbc:///?odbc_connect={encoded}"


def _create_engine() -> Engine:
    """
    Create and configure the SQLAlchemy engine.

    pool_pre_ping=True ensures that stale connections are recycled
    automatically, which is especially important when the SQL Server
    drops idle connections after a period of inactivity.

    Returns:
        A configured SQLAlchemy Engine instance.
    """
    engine = create_engine(
        _build_connection_string(),
        # Validate connections before use to handle dropped connections gracefully
        pool_pre_ping=True,
        # Connection pool settings suitable for a small web application
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        echo=settings.debug,  # Log SQL statements when DEBUG=true
    )

    # Emit a USE statement on every new connection to ensure we are always
    # targeting the correct database, even if the ODBC DSN defaults elsewhere.
    @event.listens_for(engine, "connect")
    def set_database(  # pyright: ignore[reportUnusedFunction]
        dbapi_connection: object,
        connection_record: object,
    ) -> None:
        """
        Set the active database for each new DBAPI connection.

        This guarantees that all queries run against WiTERP regardless of
        the default database configured on the SQL Server login.
        """
        cursor = dbapi_connection.cursor()  # type: ignore[union-attr]
        cursor.execute(f"USE [{settings.db_name}]")  # type: ignore[union-attr]
        cursor.close()  # type: ignore[union-attr]

    return engine


# ---------------------------------------------------------------------------
# Module-level engine — reused across the application lifetime
# ---------------------------------------------------------------------------
engine: Engine = _create_engine()

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,  # Explicit transaction management
    autoflush=False,   # Flush only on explicit flush() or commit()
    expire_on_commit=False,  # Avoid lazy-load issues after commit
)


def get_db() -> Generator[Session]:
    """
    FastAPI dependency that provides a database session per request.

    Yields a Session and guarantees it is closed after the request finishes,
    even if an exception is raised.  Use this with FastAPI's Depends():

        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...

    Yields:
        An active SQLAlchemy Session bound to the request lifecycle.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        # Roll back any uncommitted transaction on error
        db.rollback()
        raise
    finally:
        # Always close the session to return the connection to the pool
        db.close()


def check_connection() -> bool:
    """
    Perform a lightweight connectivity check against the SQL Server.

    Executes SELECT 1 to verify the engine can successfully acquire a
    connection and the SQL Server is reachable.

    Returns:
        True if the connection succeeds, False otherwise.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
