IF COL_LENGTH('dbo.projects', 'purchase_number') IS NULL
    ALTER TABLE dbo.projects ADD purchase_number NVARCHAR(100) NOT NULL
        CONSTRAINT DF_projects_purchase_number DEFAULT '';
GO
IF COL_LENGTH('dbo.projects', 'unloading_point') IS NULL
    ALTER TABLE dbo.projects ADD unloading_point NVARCHAR(200) NOT NULL
        CONSTRAINT DF_projects_unloading_point DEFAULT '';
GO
IF COL_LENGTH('dbo.projects', 'consuming_plant') IS NULL
    ALTER TABLE dbo.projects ADD consuming_plant NVARCHAR(200) NOT NULL
        CONSTRAINT DF_projects_consuming_plant DEFAULT '';
GO
IF COL_LENGTH('dbo.projects', 'contact_person') IS NULL
    ALTER TABLE dbo.projects ADD contact_person NVARCHAR(200) NOT NULL
        CONSTRAINT DF_projects_contact_person DEFAULT '';
GO
IF COL_LENGTH('dbo.projects', 'contact_phone') IS NULL
    ALTER TABLE dbo.projects ADD contact_phone NVARCHAR(50) NOT NULL
        CONSTRAINT DF_projects_contact_phone DEFAULT '';
GO
IF COL_LENGTH('dbo.projects', 'contact_email') IS NULL
    ALTER TABLE dbo.projects ADD contact_email NVARCHAR(254) NOT NULL
        CONSTRAINT DF_projects_contact_email DEFAULT '';
GO

UPDATE project
SET purchase_number = customer.purchase_number,
    unloading_point = customer.unloading_point,
    consuming_plant = customer.consuming_plant,
    contact_person = customer.contact_person,
    contact_phone = customer.contact_phone,
    contact_email = customer.contact_email
FROM dbo.projects AS project
INNER JOIN dbo.customers AS customer ON customer.id = project.customer_id;
GO

IF OBJECT_ID('dbo.DF_customers_purchase_number', 'D') IS NOT NULL
    ALTER TABLE dbo.customers DROP CONSTRAINT DF_customers_purchase_number;
GO
IF COL_LENGTH('dbo.customers', 'purchase_number') IS NOT NULL
    ALTER TABLE dbo.customers DROP COLUMN purchase_number;
GO

IF OBJECT_ID('dbo.DF_customers_unloading_point', 'D') IS NOT NULL
    ALTER TABLE dbo.customers DROP CONSTRAINT DF_customers_unloading_point;
GO
IF COL_LENGTH('dbo.customers', 'unloading_point') IS NOT NULL
    ALTER TABLE dbo.customers DROP COLUMN unloading_point;
GO

IF OBJECT_ID('dbo.DF_customers_consuming_plant', 'D') IS NOT NULL
    ALTER TABLE dbo.customers DROP CONSTRAINT DF_customers_consuming_plant;
GO
IF COL_LENGTH('dbo.customers', 'consuming_plant') IS NOT NULL
    ALTER TABLE dbo.customers DROP COLUMN consuming_plant;
GO