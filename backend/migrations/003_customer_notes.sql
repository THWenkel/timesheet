IF NOT EXISTS (
    SELECT 1
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'dbo'
      AND TABLE_NAME = 'customers'
      AND COLUMN_NAME = 'notes'
)
BEGIN
    ALTER TABLE dbo.customers
        ADD notes NVARCHAR(2000) NOT NULL
            CONSTRAINT DF_customers_notes DEFAULT '';
END
GO