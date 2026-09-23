IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'customers')
BEGIN
    CREATE TABLE dbo.customers (
        id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_customers PRIMARY KEY,
        name NVARCHAR(200) NOT NULL CONSTRAINT UQ_customers_name UNIQUE,
        is_active BIT NOT NULL DEFAULT 1,
        created_at DATETIME NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME NOT NULL DEFAULT GETDATE()
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'projects')
BEGIN
    CREATE TABLE dbo.projects (
        id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_projects PRIMARY KEY,
        customer_id INT NOT NULL,
        name NVARCHAR(200) NOT NULL,
        description NVARCHAR(2000) NOT NULL DEFAULT '',
        budget_amount DECIMAL(12,2) NOT NULL,
        budget_unit NVARCHAR(20) NOT NULL,
        starts_on DATE NOT NULL,
        ends_on DATE NOT NULL,
        status NVARCHAR(20) NOT NULL DEFAULT 'active',
        created_at DATETIME NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT FK_projects_customer FOREIGN KEY (customer_id) REFERENCES dbo.customers(id),
        CONSTRAINT CK_projects_dates CHECK (ends_on >= starts_on),
        CONSTRAINT CK_projects_budget CHECK (budget_amount > 0),
        CONSTRAINT CK_projects_budget_unit CHECK (budget_unit IN ('hours', 'person_days')),
        CONSTRAINT CK_projects_status CHECK (status IN ('active', 'paused', 'completed'))
    );
    CREATE NONCLUSTERED INDEX IX_projects_customer ON dbo.projects(customer_id);
END
GO

IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'project_allocations')
BEGIN
    CREATE TABLE dbo.project_allocations (
        id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_project_allocations PRIMARY KEY,
        project_id INT NOT NULL,
        employee_id INT NOT NULL,
        created_at DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT FK_project_allocations_project FOREIGN KEY (project_id)
            REFERENCES dbo.projects(id) ON DELETE CASCADE,
        CONSTRAINT FK_project_allocations_employee FOREIGN KEY (employee_id)
            REFERENCES dbo.employees(id) ON DELETE CASCADE,
        CONSTRAINT UQ_project_allocations_project_employee UNIQUE (project_id, employee_id)
    );
    CREATE NONCLUSTERED INDEX IX_project_allocations_employee
        ON dbo.project_allocations(employee_id);
END
GO