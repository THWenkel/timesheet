IF COL_LENGTH('dbo.customers', 'street_1') IS NULL
    ALTER TABLE dbo.customers ADD street_1 NVARCHAR(200) NOT NULL
        CONSTRAINT DF_customers_street_1 DEFAULT '';
GO
IF COL_LENGTH('dbo.customers', 'street_2') IS NULL
    ALTER TABLE dbo.customers ADD street_2 NVARCHAR(200) NOT NULL
        CONSTRAINT DF_customers_street_2 DEFAULT '';
GO
IF COL_LENGTH('dbo.customers', 'postal_code') IS NULL
    ALTER TABLE dbo.customers ADD postal_code NVARCHAR(20) NOT NULL
        CONSTRAINT DF_customers_postal_code DEFAULT '';
GO
IF COL_LENGTH('dbo.customers', 'city') IS NULL
    ALTER TABLE dbo.customers ADD city NVARCHAR(100) NOT NULL
        CONSTRAINT DF_customers_city DEFAULT '';
GO
IF COL_LENGTH('dbo.customers', 'country') IS NULL
    ALTER TABLE dbo.customers ADD country NVARCHAR(100) NOT NULL
        CONSTRAINT DF_customers_country DEFAULT '';
GO
IF COL_LENGTH('dbo.customers', 'purchase_number') IS NULL
    ALTER TABLE dbo.customers ADD purchase_number NVARCHAR(100) NOT NULL
        CONSTRAINT DF_customers_purchase_number DEFAULT '';
GO
IF COL_LENGTH('dbo.customers', 'supplier_number') IS NULL
    ALTER TABLE dbo.customers ADD supplier_number NVARCHAR(100) NOT NULL
        CONSTRAINT DF_customers_supplier_number DEFAULT '';
GO
IF COL_LENGTH('dbo.customers', 'unloading_point') IS NULL
    ALTER TABLE dbo.customers ADD unloading_point NVARCHAR(200) NOT NULL
        CONSTRAINT DF_customers_unloading_point DEFAULT '';
GO
IF COL_LENGTH('dbo.customers', 'consuming_plant') IS NULL
    ALTER TABLE dbo.customers ADD consuming_plant NVARCHAR(200) NOT NULL
        CONSTRAINT DF_customers_consuming_plant DEFAULT '';
GO
IF COL_LENGTH('dbo.customers', 'contact_person') IS NULL
    ALTER TABLE dbo.customers ADD contact_person NVARCHAR(200) NOT NULL
        CONSTRAINT DF_customers_contact_person DEFAULT '';
GO
IF COL_LENGTH('dbo.customers', 'contact_phone') IS NULL
    ALTER TABLE dbo.customers ADD contact_phone NVARCHAR(50) NOT NULL
        CONSTRAINT DF_customers_contact_phone DEFAULT '';
GO
IF COL_LENGTH('dbo.customers', 'contact_email') IS NULL
    ALTER TABLE dbo.customers ADD contact_email NVARCHAR(254) NOT NULL
        CONSTRAINT DF_customers_contact_email DEFAULT '';
GO