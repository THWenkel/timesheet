-- =============================================================================
-- 011_timesheet_project.sql
--
-- Links timesheet entries to a project (dbo.timesheet_entries.project_id).
--
--   project_id  the project the time was booked on. NULL for entries that
--               were created before this migration; new entries must carry a
--               project (enforced by the API, not by the database, so old
--               rows stay valid).
--
-- Additive only: no DROP, no UPDATE, no DELETE, no change to existing columns.
-- Existing rows keep all their values and get project_id = NULL.
-- dbo.timesheet_entries_backup gets the same column in this script so a backup
-- run cannot fail on a missing column (see 009_backup_tables.sql).
--
-- Take a backup BEFORE applying this script (admin client "Datensicherung").
-- =============================================================================

IF COL_LENGTH('dbo.timesheet_entries', 'project_id') IS NULL
    ALTER TABLE dbo.timesheet_entries ADD project_id INT NULL;
GO

-- Deleting a project must never delete time entries: no ON DELETE CASCADE.
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_timesheet_entries_projects'
               AND parent_object_id = OBJECT_ID('dbo.timesheet_entries'))
    ALTER TABLE dbo.timesheet_entries ADD CONSTRAINT FK_timesheet_entries_projects
        FOREIGN KEY (project_id) REFERENCES dbo.projects (id);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_timesheet_entries_project_date'
               AND object_id = OBJECT_ID('dbo.timesheet_entries'))
    CREATE INDEX IX_timesheet_entries_project_date
        ON dbo.timesheet_entries (project_id, entry_date);
GO

-- Same column on the backup twin (no constraints, see 009).
IF COL_LENGTH('dbo.timesheet_entries_backup', 'project_id') IS NULL
    ALTER TABLE dbo.timesheet_entries_backup ADD project_id INT NULL;
GO
