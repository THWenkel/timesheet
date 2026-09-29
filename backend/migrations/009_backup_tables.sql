-- =============================================================================
-- 009_backup_tables.sql
--
-- Adds the *_backup tables that the admin "Datensicherung" feature writes to.
--
-- Rules:
--   * additive only: nothing is dropped, truncated, or modified in existing tables
--   * dbo.employees_backup and dbo.timesheet_entries_backup already exist in
--     production (created by hand, see AGENTS.md) and are NOT touched here
--   * the backup tables mirror the source columns 1:1 (same names and types)
--   * no IDENTITY, no FOREIGN KEY, no constraints on the backup tables, so a
--     backup run can never fail because of referential rules
--
-- Every future migration that adds a table or column must also create/extend
-- the matching *_backup table in the same script.
-- =============================================================================

IF OBJECT_ID('dbo.CountryCode2_backup', 'U') IS NULL
    CREATE TABLE dbo.CountryCode2_backup (
        country_code CHAR(2)       NOT NULL,
        country_name NVARCHAR(200) NOT NULL
    );
GO

IF OBJECT_ID('dbo.customers_backup', 'U') IS NULL
    CREATE TABLE dbo.customers_backup (
        id              INT            NOT NULL,
        name            NVARCHAR(200)  NOT NULL,
        is_active       BIT            NOT NULL,
        created_at      DATETIME       NOT NULL,
        updated_at      DATETIME       NOT NULL,
        notes           NVARCHAR(2000) NOT NULL,
        street_1        NVARCHAR(200)  NOT NULL,
        street_2        NVARCHAR(200)  NOT NULL,
        postal_code     NVARCHAR(20)   NOT NULL,
        city            NVARCHAR(100)  NOT NULL,
        country         NVARCHAR(100)  NOT NULL,
        supplier_number NVARCHAR(100)  NOT NULL,
        contact_person  NVARCHAR(200)  NOT NULL,
        contact_phone   NVARCHAR(50)   NOT NULL,
        contact_email   NVARCHAR(254)  NOT NULL
    );
GO

IF OBJECT_ID('dbo.projects_backup', 'U') IS NULL
    CREATE TABLE dbo.projects_backup (
        id              INT            NOT NULL,
        customer_id     INT            NOT NULL,
        name            NVARCHAR(200)  NOT NULL,
        description     NVARCHAR(2000) NOT NULL,
        budget_amount   DECIMAL(12,2)  NOT NULL,
        budget_unit     NVARCHAR(20)   NOT NULL,
        starts_on       DATE           NOT NULL,
        ends_on         DATE           NOT NULL,
        status          NVARCHAR(20)   NOT NULL,
        created_at      DATETIME       NOT NULL,
        updated_at      DATETIME       NOT NULL,
        purchase_number NVARCHAR(100)  NOT NULL,
        unloading_point NVARCHAR(200)  NOT NULL,
        consuming_plant NVARCHAR(200)  NOT NULL,
        contact_person  NVARCHAR(200)  NOT NULL,
        contact_phone   NVARCHAR(50)   NOT NULL,
        contact_email   NVARCHAR(254)  NOT NULL,
        hourly_rate     DECIMAL(10,2)  NOT NULL,
        daily_rate      DECIMAL(10,2)  NOT NULL
    );
GO

IF OBJECT_ID('dbo.project_allocations_backup', 'U') IS NULL
    CREATE TABLE dbo.project_allocations_backup (
        id          INT      NOT NULL,
        project_id  INT      NOT NULL,
        employee_id INT      NOT NULL,
        created_at  DATETIME NOT NULL
    );
GO
