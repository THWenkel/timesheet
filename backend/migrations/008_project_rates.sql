IF COL_LENGTH('dbo.projects', 'hourly_rate') IS NULL
    ALTER TABLE dbo.projects ADD hourly_rate DECIMAL(10,2) NOT NULL
        CONSTRAINT DF_projects_hourly_rate DEFAULT 0;
GO
IF COL_LENGTH('dbo.projects', 'daily_rate') IS NULL
    ALTER TABLE dbo.projects ADD daily_rate DECIMAL(10,2) NOT NULL
        CONSTRAINT DF_projects_daily_rate DEFAULT 0;
GO
IF OBJECT_ID('dbo.CK_projects_hourly_rate', 'C') IS NULL
    ALTER TABLE dbo.projects ADD CONSTRAINT CK_projects_hourly_rate CHECK (hourly_rate >= 0);
GO
IF OBJECT_ID('dbo.CK_projects_daily_rate', 'C') IS NULL
    ALTER TABLE dbo.projects ADD CONSTRAINT CK_projects_daily_rate CHECK (daily_rate >= 0);
GO
