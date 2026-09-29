# =============================================================================
# backend/app/schemas/backup.py
#
# Pydantic request/response models for the /api/backup endpoints.
# =============================================================================

from typing import Literal

from pydantic import BaseModel, Field


class BackupTableInfo(BaseModel):
    """One table that can be backed up and restored."""

    name: str
    backup_table: str
    row_count: int
    backup_exists: bool
    backup_row_count: int | None = None


class BackupDbRequest(BaseModel):
    tables: list[str] = Field(min_length=1)


class BackupTableResult(BaseModel):
    table: str
    rows: int


class BackupDbResponse(BaseModel):
    results: list[BackupTableResult]


class RestoreDbRequest(BaseModel):
    tables: list[str] = Field(min_length=1)
    # Must be true for a real restore. dry_run only reports what would happen.
    confirm: bool = False
    dry_run: bool = False


class RestoreImportRequest(BaseModel):
    table: str
    format: Literal["csv", "json"]
    content: str
    confirm: bool = False
    dry_run: bool = False


class RestoreTableResult(BaseModel):
    table: str
    source_rows: int
    # Rows that already exist (matched by key) and get overwritten
    updated: int
    # Rows missing in the table that get inserted
    inserted: int


class RestoreResponse(BaseModel):
    dry_run: bool
    results: list[RestoreTableResult]
