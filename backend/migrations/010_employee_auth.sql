-- =============================================================================
-- 010_employee_auth.sql
--
-- Login data for the JWT authentication, stored on dbo.employees.
--
--   username             login name (unique among employees that have one)
--   password_hash        Argon2id hash, never the password itself
--   is_admin             may use the admin client and admin endpoints
--   must_change_password set after an admin reset; forces a new password at login
--   password_changed_at  invalidates tokens issued before the last change
--   failed_login_count   consecutive failed logins (reset on success)
--   locked_until         login blocked until this time after too many failures
--
-- Additive only. dbo.employees_backup gets the same columns in this script so a
-- backup run cannot fail on a missing column (see 009_backup_tables.sql).
-- =============================================================================

IF COL_LENGTH('dbo.employees', 'username') IS NULL
    ALTER TABLE dbo.employees ADD username NVARCHAR(100) NULL;
GO
IF COL_LENGTH('dbo.employees', 'password_hash') IS NULL
    ALTER TABLE dbo.employees ADD password_hash NVARCHAR(255) NULL;
GO
IF COL_LENGTH('dbo.employees', 'is_admin') IS NULL
    ALTER TABLE dbo.employees ADD is_admin BIT NOT NULL
        CONSTRAINT DF_employees_is_admin DEFAULT 0;
GO
IF COL_LENGTH('dbo.employees', 'must_change_password') IS NULL
    ALTER TABLE dbo.employees ADD must_change_password BIT NOT NULL
        CONSTRAINT DF_employees_must_change_password DEFAULT 0;
GO
IF COL_LENGTH('dbo.employees', 'password_changed_at') IS NULL
    ALTER TABLE dbo.employees ADD password_changed_at DATETIME NULL;
GO
IF COL_LENGTH('dbo.employees', 'failed_login_count') IS NULL
    ALTER TABLE dbo.employees ADD failed_login_count INT NOT NULL
        CONSTRAINT DF_employees_failed_login_count DEFAULT 0;
GO
IF COL_LENGTH('dbo.employees', 'locked_until') IS NULL
    ALTER TABLE dbo.employees ADD locked_until DATETIME NULL;
GO

-- Filtered unique index: many employees may still have no username (NULL).
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_employees_username'
               AND object_id = OBJECT_ID('dbo.employees'))
    CREATE UNIQUE INDEX UX_employees_username ON dbo.employees (username)
        WHERE username IS NOT NULL;
GO

-- Same columns on the backup twin (no constraints besides defaults for NOT NULL).
IF COL_LENGTH('dbo.employees_backup', 'username') IS NULL
    ALTER TABLE dbo.employees_backup ADD username NVARCHAR(100) NULL;
GO
IF COL_LENGTH('dbo.employees_backup', 'password_hash') IS NULL
    ALTER TABLE dbo.employees_backup ADD password_hash NVARCHAR(255) NULL;
GO
IF COL_LENGTH('dbo.employees_backup', 'is_admin') IS NULL
    ALTER TABLE dbo.employees_backup ADD is_admin BIT NOT NULL
        CONSTRAINT DF_employees_backup_is_admin DEFAULT 0;
GO
IF COL_LENGTH('dbo.employees_backup', 'must_change_password') IS NULL
    ALTER TABLE dbo.employees_backup ADD must_change_password BIT NOT NULL
        CONSTRAINT DF_employees_backup_must_change_password DEFAULT 0;
GO
IF COL_LENGTH('dbo.employees_backup', 'password_changed_at') IS NULL
    ALTER TABLE dbo.employees_backup ADD password_changed_at DATETIME NULL;
GO
IF COL_LENGTH('dbo.employees_backup', 'failed_login_count') IS NULL
    ALTER TABLE dbo.employees_backup ADD failed_login_count INT NOT NULL
        CONSTRAINT DF_employees_backup_failed_login_count DEFAULT 0;
GO
IF COL_LENGTH('dbo.employees_backup', 'locked_until') IS NULL
    ALTER TABLE dbo.employees_backup ADD locked_until DATETIME NULL;
GO
