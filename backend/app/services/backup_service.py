# =============================================================================
# backend/app/services/backup_service.py
#
# Backup and restore of the application tables.
#
#   * backup_to_db      — copy tables into their dbo.<table>_backup twin
#   * export_table      — serialize a table as CSV or JSON (the admin client
#                         writes the file, see admin/Timesheet.Admin)
#   * restore_from_db   — restore tables from their *_backup twin
#   * restore_from_file — restore one table from CSV/JSON content
#
# Safety rules:
#   * Only tables listed in TABLE_SPECS can be touched. Table and column names
#     that end up in SQL come from this whitelist or from INFORMATION_SCHEMA,
#     never from request data.
#   * Every operation runs in one transaction. On any error nothing is changed,
#     in particular a *_backup table keeps its old content.
#   * Restore is upsert-only: existing rows (matched by key) are overwritten,
#     missing rows are inserted, nothing is ever deleted. Deleting parents
#     would cascade to timesheet_entries and project_allocations.
# =============================================================================

import csv
import io
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast

from fastapi import HTTPException, status
from sqlalchemy import CursorResult, text
from sqlalchemy.orm import Session

from app.schemas.backup import (
    BackupDbResponse,
    BackupTableInfo,
    BackupTableResult,
    RestoreResponse,
    RestoreTableResult,
)

FILE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class TableSpec:
    name: str
    key: str

    @property
    def backup_name(self) -> str:
        return f"{self.name}_backup"


# Parents first: this is also the order used for restores.
TABLE_SPECS: tuple[TableSpec, ...] = (
    TableSpec("CountryCode2", "country_code"),
    TableSpec("customers", "id"),
    TableSpec("employees", "id"),
    TableSpec("projects", "id"),
    TableSpec("project_allocations", "id"),
    TableSpec("timesheet_entries", "id"),
)
_SPEC_BY_NAME = {spec.name: spec for spec in TABLE_SPECS}


@dataclass(frozen=True)
class Column:
    name: str
    data_type: str
    nullable: bool


def _spec(table: str) -> TableSpec:
    spec = _SPEC_BY_NAME.get(table)
    if spec is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown table '{table}'")
    return spec


def _specs(tables: list[str]) -> list[TableSpec]:
    """Resolve requested names, de-duplicated, in restore (dependency) order."""
    requested = {_spec(t).name for t in tables}
    return [s for s in TABLE_SPECS if s.name in requested]


def _q(name: str) -> str:
    return f"[{name}]"


def _exists(db: Session, table: str) -> bool:
    return db.execute(text("SELECT OBJECT_ID(:n, 'U')"), {"n": f"dbo.{table}"}).scalar() is not None


def _columns(db: Session, table: str) -> list[Column]:
    rows = db.execute(
        text(
            "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = :t ORDER BY ORDINAL_POSITION"
        ),
        {"t": table},
    ).all()
    return [Column(str(r[0]), str(r[1]), r[2] == "YES") for r in rows]


def _has_identity(db: Session, table: str) -> bool:
    count = db.execute(
        text("SELECT COUNT(*) FROM sys.identity_columns WHERE object_id = OBJECT_ID(:n)"),
        {"n": f"dbo.{table}"},
    ).scalar()
    return bool(count)


def _count(db: Session, table: str) -> int:
    # Table name comes from the TABLE_SPECS whitelist.
    return int(db.execute(text(f"SELECT COUNT(*) FROM dbo.{_q(table)}")).scalar() or 0)  # noqa: S608


def _rowcount(result: object) -> int:
    return max(cast("CursorResult[Any]", result).rowcount, 0)


def _require_backup_table(db: Session, spec: TableSpec) -> list[Column]:
    """Return the source columns after checking the backup twin can hold them."""
    if not _exists(db, spec.backup_name):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Backup table dbo.{spec.backup_name} is missing. Apply the pending migrations.",
        )
    source = _columns(db, spec.name)
    backup = {c.name for c in _columns(db, spec.backup_name)}
    missing = [c.name for c in source if c.name not in backup]
    if missing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"dbo.{spec.backup_name} lacks columns {missing}. Apply the pending migrations.",
        )
    return source


# -----------------------------------------------------------------------------
# Overview
# -----------------------------------------------------------------------------
def list_tables(db: Session) -> list[BackupTableInfo]:
    result: list[BackupTableInfo] = []
    for spec in TABLE_SPECS:
        exists = _exists(db, spec.backup_name)
        result.append(
            BackupTableInfo(
                name=spec.name,
                backup_table=spec.backup_name,
                row_count=_count(db, spec.name),
                backup_exists=exists,
                backup_row_count=_count(db, spec.backup_name) if exists else None,
            )
        )
    return result


# -----------------------------------------------------------------------------
# Backup into the database
# -----------------------------------------------------------------------------
def backup_to_db(db: Session, tables: list[str]) -> BackupDbResponse:
    specs = _specs(tables)
    results: list[BackupTableResult] = []
    try:
        for spec in specs:
            columns = _require_backup_table(db, spec)
            cols = ", ".join(_q(c.name) for c in columns)
            backup = f"dbo.{_q(spec.backup_name)}"
            identity = _has_identity(db, spec.backup_name)
            # Old backup content is only removed inside this transaction: if the
            # INSERT fails, the rollback restores it.
            db.execute(text(f"DELETE FROM {backup}"))  # noqa: S608
            if identity:
                db.execute(text(f"SET IDENTITY_INSERT {backup} ON"))
            result = db.execute(
                text(
                    f"INSERT INTO {backup} ({cols}) "  # noqa: S608
                    f"SELECT {cols} FROM dbo.{_q(spec.name)}"
                )
            )
            if identity:
                db.execute(text(f"SET IDENTITY_INSERT {backup} OFF"))
            results.append(BackupTableResult(table=spec.name, rows=_rowcount(result)))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return BackupDbResponse(results=results)


# -----------------------------------------------------------------------------
# Export (CSV / JSON)
# -----------------------------------------------------------------------------
def _serialize(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat(timespec="milliseconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def export_table(db: Session, table: str, fmt: str) -> tuple[bytes, str]:
    """Return (file content, media type) for a whole table."""
    spec = _spec(table)
    columns = _columns(db, spec.name)
    names = [c.name for c in columns]
    cols = ", ".join(_q(n) for n in names)
    rows = db.execute(
        text(f"SELECT {cols} FROM dbo.{_q(spec.name)} ORDER BY {_q(spec.key)}")  # noqa: S608
    ).all()
    data = [[_serialize(v) for v in row] for row in rows]

    if fmt == "json":
        payload = {
            "schema_version": FILE_SCHEMA_VERSION,
            "table": spec.name,
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "columns": names,
            "rows": [dict(zip(names, row, strict=True)) for row in data],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"), (
            "application/json"
        )

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(names)
    for row in data:
        writer.writerow(["" if v is None else v for v in row])
    return buffer.getvalue().encode("utf-8"), "text/csv"


# -----------------------------------------------------------------------------
# Restore
# -----------------------------------------------------------------------------
def restore_from_db(
    db: Session, tables: list[str], *, confirm: bool, dry_run: bool
) -> RestoreResponse:
    _check_confirmed(confirm, dry_run)
    results: list[RestoreTableResult] = []
    try:
        for spec in _specs(tables):
            columns = _require_backup_table(db, spec)
            backup = f"dbo.{_q(spec.backup_name)}"
            target = f"dbo.{_q(spec.name)}"
            key = _q(spec.key)
            match = f"t.{key} = b.{key}"
            source_rows = _count(db, spec.backup_name)
            matching = int(
                db.execute(
                    text(f"SELECT COUNT(*) FROM {backup} b JOIN {target} t ON {match}")  # noqa: S608
                ).scalar()
                or 0
            )
            if dry_run:
                results.append(
                    RestoreTableResult(
                        table=spec.name,
                        source_rows=source_rows,
                        updated=matching,
                        inserted=source_rows - matching,
                    )
                )
                continue

            cols = ", ".join(_q(c.name) for c in columns)
            assignments = ", ".join(
                f"t.{_q(c.name)} = b.{_q(c.name)}" for c in columns if c.name != spec.key
            )
            identity = _has_identity(db, spec.name)
            updated = db.execute(
                text(f"UPDATE t SET {assignments} FROM {target} t JOIN {backup} b ON {match}")  # noqa: S608
            )
            if identity:
                db.execute(text(f"SET IDENTITY_INSERT {target} ON"))
            inserted = db.execute(
                text(
                    f"INSERT INTO {target} ({cols}) SELECT {cols} FROM {backup} b "  # noqa: S608
                    f"WHERE NOT EXISTS (SELECT 1 FROM {target} t WHERE {match})"
                )
            )
            if identity:
                db.execute(text(f"SET IDENTITY_INSERT {target} OFF"))
            results.append(
                RestoreTableResult(
                    table=spec.name,
                    source_rows=source_rows,
                    updated=_rowcount(updated),
                    inserted=_rowcount(inserted),
                )
            )
        if dry_run:
            db.rollback()
        else:
            db.commit()
    except Exception:
        db.rollback()
        raise
    return RestoreResponse(dry_run=dry_run, results=results)


def restore_from_file(
    db: Session, table: str, fmt: str, content: str, *, confirm: bool, dry_run: bool
) -> RestoreResponse:
    _check_confirmed(confirm, dry_run)
    spec = _spec(table)
    columns = _columns(db, spec.name)
    rows = _parse_file(spec, columns, fmt, content)  # validates everything before any write
    key = _q(spec.key)
    target = f"dbo.{_q(spec.name)}"

    keys = [r[spec.key] for r in rows]
    if len(set(keys)) != len(keys):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Duplicate keys in file")

    updated = inserted = 0
    try:
        identity = _has_identity(db, spec.name)
        if identity and not dry_run:
            db.execute(text(f"SET IDENTITY_INSERT {target} ON"))
        set_clause = ", ".join(f"{_q(c.name)} = :{c.name}" for c in columns if c.name != spec.key)
        col_list = ", ".join(_q(c.name) for c in columns)
        placeholders = ", ".join(f":{c.name}" for c in columns)
        for row in rows:
            exists = db.execute(
                text(f"SELECT COUNT(*) FROM {target} WHERE {key} = :k"),  # noqa: S608
                {"k": row[spec.key]},
            ).scalar()
            if exists:
                updated += 1
                if not dry_run:
                    db.execute(
                        text(f"UPDATE {target} SET {set_clause} WHERE {key} = :{spec.key}"),  # noqa: S608
                        row,
                    )
            else:
                inserted += 1
                if not dry_run:
                    db.execute(
                        text(f"INSERT INTO {target} ({col_list}) VALUES ({placeholders})"),  # noqa: S608
                        row,
                    )
        if identity and not dry_run:
            db.execute(text(f"SET IDENTITY_INSERT {target} OFF"))
        if dry_run:
            db.rollback()
        else:
            db.commit()
    except Exception:
        db.rollback()
        raise
    return RestoreResponse(
        dry_run=dry_run,
        results=[
            RestoreTableResult(
                table=spec.name, source_rows=len(rows), updated=updated, inserted=inserted
            )
        ],
    )


def _check_confirmed(confirm: bool, dry_run: bool) -> None:
    if not dry_run and not confirm:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Restore requires confirm=true (or dry_run=true)"
        )


def _coerce(column: Column, raw: object) -> object:
    """Convert a value from a CSV/JSON file to the Python type of its column."""
    if raw is None or (raw == "" and column.nullable):
        if raw is None and not column.nullable:
            raise ValueError(f"column '{column.name}' must not be NULL")
        return None
    dt = column.data_type
    try:
        if dt in {"int", "bigint", "smallint", "tinyint"}:
            return int(cast("str | int", raw))
        if dt == "bit":
            if isinstance(raw, str):
                if raw.strip().lower() not in {"true", "false", "1", "0"}:
                    raise ValueError(raw)
                return raw.strip().lower() in {"true", "1"}
            return bool(raw)
        if dt in {"decimal", "numeric", "money"}:
            return Decimal(str(raw))
        if dt == "date":
            return date.fromisoformat(str(raw))
        if dt in {"datetime", "datetime2", "smalldatetime"}:
            return datetime.fromisoformat(str(raw))
    except (ValueError, ArithmeticError) as exc:
        raise ValueError(f"column '{column.name}': invalid value {raw!r}") from exc
    return str(raw)


def _parse_file(
    spec: TableSpec, columns: list[Column], fmt: str, content: str
) -> list[dict[str, object]]:
    names = [c.name for c in columns]
    raw_rows: list[dict[str, object]]
    try:
        if fmt == "json":
            doc = json.loads(content)
            if not isinstance(doc, dict):
                raise ValueError("JSON root must be an object")
            payload = cast("dict[str, Any]", doc)
            if payload.get("schema_version") != FILE_SCHEMA_VERSION:
                raise ValueError(f"unsupported schema_version {payload.get('schema_version')!r}")
            if payload.get("table") != spec.name:
                raise ValueError(f"file is for table {payload.get('table')!r}, not {spec.name!r}")
            rows_value: object = payload.get("rows")
            if not isinstance(rows_value, list):
                raise ValueError("'rows' must be a list")
            raw_rows = cast("list[dict[str, object]]", rows_value)
            for r in raw_rows:
                if set(r) != set(names):
                    raise ValueError(f"row columns {sorted(r)} do not match {sorted(names)}")
        else:
            reader = csv.DictReader(io.StringIO(content.lstrip("﻿")))
            if set(reader.fieldnames or []) != set(names):
                raise ValueError(f"CSV header {reader.fieldnames} does not match {names}")
            raw_rows = [cast("dict[str, object]", r) for r in reader]
        return [{c.name: _coerce(c, r[c.name]) for c in columns} for r in raw_rows]
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Invalid file: {exc}") from exc
