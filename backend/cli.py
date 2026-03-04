#!/usr/bin/env python
# =============================================================================
# backend/cli.py
#
# Database maintenance CLI tool.
#
# Runs raw SQL migration scripts from the `migrations/` folder against the
# configured SQL Server database.  Migration scripts are executed in filename
# order (alphabetical / numeric prefix).  A `schema_migrations` table in the
# database tracks which scripts have already been applied, so the tool is
# idempotent — running `migrate` multiple times only applies new scripts.
#
# Usage:
#   python cli.py migrate --password <sa_password>
#   python cli.py status  --password <sa_password>
#   python cli.py rollback --script 001_initial_schema.sql --password <sa_password>
#
# ⚠️  SECURITY TODO (before go-live):
#   - Remove the --password CLI argument.
#   - Read the password exclusively from the .env file or a secrets manager.
#   - Replace the 'sa' account with a dedicated least-privilege SQL user.
# =============================================================================

import argparse
import sys
from pathlib import Path

import pyodbc

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# SQL to create the tracking table if it does not exist yet.
# Uses a minimal schema compatible with SQL Server 2012.
CREATE_TRACKING_TABLE_SQL = """
IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_NAME = 'schema_migrations'
)
CREATE TABLE schema_migrations (
    id            INT IDENTITY(1,1) PRIMARY KEY,
    script_name   NVARCHAR(255) NOT NULL UNIQUE,
    applied_at    DATETIME NOT NULL DEFAULT GETDATE(),
    applied_by    NVARCHAR(100) NOT NULL DEFAULT SYSTEM_USER
);
"""


# ─────────────────────────────────────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_connection_string(server: str, database: str, user: str, password: str) -> str:
    """
    Build a raw pyodbc connection string for SQL Server.

    Args:
        server:   SQL Server hostname (e.g. 'dbserver01').
        database: Target database name (e.g. 'WiTERP').
        user:     SQL Server login username (e.g. 'sa').
        password: SQL Server login password.

    Returns:
        A pyodbc connection string.
    """
    # Encrypt=no — required for SQL Server 2012 without a TLS certificate.
    # ⚠️  TODO: Change to Encrypt=yes before production.
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        "Encrypt=no;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=30;"
    )


def _get_connection(args: argparse.Namespace) -> pyodbc.Connection:
    """
    Establish and return a pyodbc connection to SQL Server.

    Args:
        args: Parsed CLI arguments containing server, database, user, password.

    Returns:
        An open pyodbc.Connection.

    Raises:
        SystemExit: If the connection cannot be established.
    """
    conn_str = _build_connection_string(args.server, args.database, args.user, args.password)
    try:
        conn = pyodbc.connect(conn_str, autocommit=False)
        return conn
    except pyodbc.Error as exc:
        print(f"[error] Cannot connect to database: {exc}", file=sys.stderr)
        sys.exit(1)


def _ensure_tracking_table(cursor: pyodbc.Cursor) -> None:
    """
    Create the schema_migrations tracking table if it does not already exist.

    This table records which migration scripts have been applied so that
    subsequent runs of `migrate` only execute new scripts.

    Args:
        cursor: An active database cursor.
    """
    cursor.execute(CREATE_TRACKING_TABLE_SQL)
    cursor.commit()


def _get_applied_scripts(cursor: pyodbc.Cursor) -> set[str]:
    """
    Return the set of script filenames that have already been applied.

    Args:
        cursor: An active database cursor.

    Returns:
        A set of script_name strings (e.g. {'001_initial_schema.sql'}).
    """
    cursor.execute("SELECT script_name FROM schema_migrations")
    return {row.script_name for row in cursor.fetchall()}


def _mark_applied(cursor: pyodbc.Cursor, script_name: str) -> None:
    """
    Record a script as applied in the tracking table.

    Args:
        cursor:      An active database cursor.
        script_name: Filename of the migration script (e.g. '001_initial_schema.sql').
    """
    cursor.execute(
        "INSERT INTO schema_migrations (script_name) VALUES (?)",
        script_name,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────────────────────────────────────

def cmd_migrate(args: argparse.Namespace) -> None:
    """
    Run all pending SQL migration scripts from the migrations/ directory.

    Scripts are executed in alphabetical/numeric order.  Only scripts that
    have not yet been recorded in the schema_migrations table are executed.

    Each script is run in a transaction — if any script fails, its transaction
    is rolled back and the CLI exits with a non-zero status code.  Successfully
    applied scripts are committed individually so that a later failure does not
    roll back already-applied migrations.

    Args:
        args: Parsed CLI arguments.
    """
    conn = _get_connection(args)
    cursor = conn.cursor()

    print(f"[migrate] Connected to {args.server}/{args.database}")

    # Ensure the tracking table exists before querying it
    _ensure_tracking_table(cursor)

    # Get list of scripts already applied
    applied = _get_applied_scripts(cursor)

    # Gather and sort migration scripts from the migrations/ directory
    if not MIGRATIONS_DIR.exists():
        print(f"[migrate] Migrations directory not found: {MIGRATIONS_DIR}", file=sys.stderr)
        sys.exit(1)

    scripts = sorted(MIGRATIONS_DIR.glob("*.sql"))
    pending = [s for s in scripts if s.name not in applied]

    if not pending:
        print("[migrate] No pending migrations. Database is up to date.")
        conn.close()
        return

    print(f"[migrate] {len(pending)} pending migration(s):")
    for script in pending:
        print(f"          • {script.name}")

    # Apply each pending script
    for script in pending:
        print(f"[migrate] Applying {script.name} ...", end=" ")
        sql = script.read_text(encoding="utf-8")
        try:
            # Execute the full SQL script — split on GO statements for SQL Server
            # GO is not a T-SQL command; it's a batch separator used by SSMS/sqlcmd
            batches = [b.strip() for b in sql.split("\nGO") if b.strip()]
            for batch in batches:
                cursor.execute(batch)
            _mark_applied(cursor, script.name)
            cursor.commit()
            print("OK")
        except pyodbc.Error as exc:
            cursor.rollback()
            print(f"FAILED\n[error] {exc}", file=sys.stderr)
            conn.close()
            sys.exit(1)

    print(f"[migrate] Done. Applied {len(pending)} migration(s).")
    conn.close()


def cmd_status(args: argparse.Namespace) -> None:
    """
    Show the migration status — which scripts are applied vs pending.

    Args:
        args: Parsed CLI arguments.
    """
    conn = _get_connection(args)
    cursor = conn.cursor()

    _ensure_tracking_table(cursor)
    applied = _get_applied_scripts(cursor)
    conn.close()

    scripts = sorted(MIGRATIONS_DIR.glob("*.sql")) if MIGRATIONS_DIR.exists() else []

    print(f"Migration status for {args.server}/{args.database}:")
    print(f"  Migrations directory: {MIGRATIONS_DIR}")
    print()

    if not scripts:
        print("  No migration scripts found.")
        return

    for script in scripts:
        mark = "✓ applied" if script.name in applied else "✗ pending"
        print(f"  [{mark}] {script.name}")

    print()
    print(f"  {len(applied)} applied, {len(scripts) - len(applied)} pending")


# ─────────────────────────────────────────────────────────────────────────────
# Argument parser
# ─────────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    """
    Build and return the argument parser for the CLI tool.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="python cli.py",
        description="Timesheet database maintenance CLI",
    )

    # -------------------------------------------------------------------------
    # Global connection arguments (shared across all sub-commands)
    # -------------------------------------------------------------------------
    parser.add_argument(
        "--server",
        default="dbserver01",
        help="SQL Server hostname (default: dbserver01)",
    )
    parser.add_argument(
        "--database",
        default="WiTERP",
        help="Target database name (default: WiTERP)",
    )
    parser.add_argument(
        "--user",
        default="sa",
        help="SQL Server login username (default: sa)",
    )
    # ⚠️  TODO: Remove --password CLI arg before go-live.
    #     Read the password from .env or a secrets manager instead.
    parser.add_argument(
        "--password",
        required=True,
        help="SQL Server login password  ⚠️  NOTE: Remove this CLI arg before production!",
    )

    # -------------------------------------------------------------------------
    # Sub-commands
    # -------------------------------------------------------------------------
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "migrate",
        help="Apply all pending SQL migration scripts from the migrations/ folder",
    )
    sub.add_parser(
        "status",
        help="Show which migration scripts have been applied and which are pending",
    )

    return parser


# ─────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """
    CLI entrypoint — parse arguments and dispatch to the appropriate command.
    """
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "migrate":
        cmd_migrate(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
