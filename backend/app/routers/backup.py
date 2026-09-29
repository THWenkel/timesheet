# =============================================================================
# backend/app/routers/backup.py
#
# FastAPI router for the /api/backup endpoints (admin data backup and restore).
#
# Endpoints:
#   GET  /api/backup/tables              — tables with row counts and backup state
#   POST /api/backup/db                  — copy tables into their *_backup twins
#   GET  /api/backup/export/{table}      — download a table as CSV or JSON
#   POST /api/backup/restore/db          — restore tables from their *_backup twins
#   POST /api/backup/restore/import      — restore one table from CSV/JSON content
#
# TODO (JWT login task): restrict all of these to admins (require_admin).
# =============================================================================

from typing import Literal

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.backup import (
    BackupDbRequest,
    BackupDbResponse,
    BackupTableInfo,
    RestoreDbRequest,
    RestoreImportRequest,
    RestoreResponse,
)
from app.services import backup_service

router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.get("/tables", response_model=list[BackupTableInfo], summary="List backup-able tables")
def list_tables(db: Session = Depends(get_db)) -> list[BackupTableInfo]:
    return backup_service.list_tables(db)


@router.post("/db", response_model=BackupDbResponse, summary="Back up tables into *_backup tables")
def backup_to_db(body: BackupDbRequest, db: Session = Depends(get_db)) -> BackupDbResponse:
    return backup_service.backup_to_db(db, body.tables)


@router.get("/export/{table}", summary="Export a table as CSV or JSON")
def export_table(
    table: str, format: Literal["csv", "json"] = "csv", db: Session = Depends(get_db)
) -> Response:
    content, media_type = backup_service.export_table(db, table, format)
    return Response(content=content, media_type=media_type)


@router.post(
    "/restore/db",
    response_model=RestoreResponse,
    summary="Restore tables from *_backup tables (upsert, never deletes)",
)
def restore_from_db(body: RestoreDbRequest, db: Session = Depends(get_db)) -> RestoreResponse:
    return backup_service.restore_from_db(
        db, body.tables, confirm=body.confirm, dry_run=body.dry_run
    )


@router.post(
    "/restore/import",
    response_model=RestoreResponse,
    summary="Restore one table from CSV/JSON content (upsert, never deletes)",
)
def restore_from_file(body: RestoreImportRequest, db: Session = Depends(get_db)) -> RestoreResponse:
    return backup_service.restore_from_file(
        db, body.table, body.format, body.content, confirm=body.confirm, dry_run=body.dry_run
    )
