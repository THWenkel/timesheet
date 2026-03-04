-- =============================================================================
-- migrations/001_initial_schema.sql
--
-- Initial database schema for the Timesheet application.
-- Target: Microsoft SQL Server 2012, database WiTERP
--
-- Creates:
--   1. employees        — employee master data
--   2. timesheet_entries — individual timesheet entries per employee per day
--   3. schema_migrations — tracks which SQL migration scripts have been applied
--
-- Applied by: python cli.py migrate --password <password>
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. employees table
-- ─────────────────────────────────────────────────────────────────────────────

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'employees'
)
BEGIN
    CREATE TABLE dbo.employees (
        id          INT IDENTITY(1,1)   NOT NULL,
        surname     NVARCHAR(100)       NOT NULL,
        lastname    NVARCHAR(100)       NOT NULL,
        is_active   BIT                 NOT NULL DEFAULT 1,

        -- Audit columns
        created_at  DATETIME            NOT NULL DEFAULT GETDATE(),
        updated_at  DATETIME            NOT NULL DEFAULT GETDATE(),
        created_by  INT                 NULL,     -- FK to employees.id (self-referential, nullable in v1)
        updated_by  INT                 NULL,     -- FK to employees.id (self-referential, nullable in v1)

        CONSTRAINT PK_employees PRIMARY KEY CLUSTERED (id ASC)
    );

    PRINT 'Created table: employees';
END
ELSE
BEGIN
    PRINT 'Table already exists: employees (skipped)';
END

GO

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. timesheet_entries table
-- ─────────────────────────────────────────────────────────────────────────────

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'timesheet_entries'
)
BEGIN
    CREATE TABLE dbo.timesheet_entries (
        id           INT IDENTITY(1,1)  NOT NULL,
        employee_id  INT                NOT NULL,
        entry_date   DATE               NOT NULL,
        -- Duration stored as integer minutes (e.g. 90 = 1h 30m).
        -- Must be a positive multiple of 15; enforced by application layer.
        minutes      INT                NOT NULL,
        description  NVARCHAR(2000)     NOT NULL DEFAULT '',

        -- Audit columns
        created_at   DATETIME           NOT NULL DEFAULT GETDATE(),
        updated_at   DATETIME           NOT NULL DEFAULT GETDATE(),
        created_by   INT                NULL,    -- FK to employees.id (nullable in v1)
        updated_by   INT                NULL,    -- FK to employees.id (nullable in v1)

        CONSTRAINT PK_timesheet_entries PRIMARY KEY CLUSTERED (id ASC),

        -- FK: entry must belong to an existing employee
        CONSTRAINT FK_timesheet_entries_employee
            FOREIGN KEY (employee_id)
            REFERENCES dbo.employees (id)
            ON DELETE CASCADE,

        -- FK: audit references (SET NULL on delete to preserve history)
        CONSTRAINT FK_timesheet_entries_created_by
            FOREIGN KEY (created_by)
            REFERENCES dbo.employees (id)
            ON DELETE NO ACTION,

        CONSTRAINT FK_timesheet_entries_updated_by
            FOREIGN KEY (updated_by)
            REFERENCES dbo.employees (id)
            ON DELETE NO ACTION
    );

    -- Index to speed up per-employee / per-date lookups (most common query pattern)
    CREATE NONCLUSTERED INDEX IX_timesheet_entries_employee_date
        ON dbo.timesheet_entries (employee_id ASC, entry_date ASC);

    PRINT 'Created table: timesheet_entries';
END
ELSE
BEGIN
    PRINT 'Table already exists: timesheet_entries (skipped)';
END

GO

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. schema_migrations tracking table (created by CLI tool if not present)
-- ─────────────────────────────────────────────────────────────────────────────

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'schema_migrations'
)
BEGIN
    CREATE TABLE dbo.schema_migrations (
        id           INT IDENTITY(1,1) NOT NULL,
        script_name  NVARCHAR(255)     NOT NULL,
        applied_at   DATETIME          NOT NULL DEFAULT GETDATE(),
        applied_by   NVARCHAR(100)     NOT NULL DEFAULT SYSTEM_USER,

        CONSTRAINT PK_schema_migrations PRIMARY KEY CLUSTERED (id ASC),
        CONSTRAINT UQ_schema_migrations_script UNIQUE (script_name)
    );

    PRINT 'Created table: schema_migrations';
END
ELSE
BEGIN
    PRINT 'Table already exists: schema_migrations (skipped)';
END

GO

PRINT '001_initial_schema.sql applied successfully.';
