-- Databricks SQL Setup Script
-- ============================
-- Run this in your Databricks SQL Warehouse to create the required tables.
-- Adjust the catalog and schema names as needed.

-- Create catalog and schema (if needed)
-- CREATE CATALOG IF NOT EXISTS workspace;
-- CREATE SCHEMA IF NOT EXISTS workspace.default;

-- Use the appropriate catalog/schema
USE CATALOG workspace;
USE SCHEMA default;

-- Create products table
CREATE TABLE IF NOT EXISTS products (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name STRING NOT NULL,
    category STRING NOT NULL,
    price DOUBLE NOT NULL
);

-- Create sales table
CREATE TABLE IF NOT EXISTS sales (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id BIGINT NOT NULL,
    quantity INT NOT NULL,
    total DOUBLE NOT NULL,
    sale_date DATE NOT NULL,
    region STRING NOT NULL
);

-- Insert sample products (only if table is empty)
INSERT INTO products (name, category, price)
SELECT * FROM (
    SELECT 'Laptop' as name, 'Electronics' as category, 999.99 as price
    UNION ALL SELECT 'Smartphone', 'Electronics', 699.99
    UNION ALL SELECT 'Headphones', 'Electronics', 149.99
    UNION ALL SELECT 'Keyboard', 'Electronics', 79.99
    UNION ALL SELECT 'Mouse', 'Electronics', 49.99
    UNION ALL SELECT 'Desk Chair', 'Furniture', 299.99
    UNION ALL SELECT 'Standing Desk', 'Furniture', 449.99
    UNION ALL SELECT 'Monitor Stand', 'Furniture', 59.99
    UNION ALL SELECT 'Python Book', 'Books', 39.99
    UNION ALL SELECT 'AI Textbook', 'Books', 89.99
) AS new_products
WHERE NOT EXISTS (SELECT 1 FROM products LIMIT 1);

-- Insert sample sales data (only if table is empty)
-- This creates 200 random sales records for the past 90 days
INSERT INTO sales (product_id, quantity, total, sale_date, region)
SELECT
    FLOOR(RAND() * 10) + 1 as product_id,
    FLOOR(RAND() * 5) + 1 as quantity,
    (FLOOR(RAND() * 5) + 1) * (
        CASE FLOOR(RAND() * 10)
            WHEN 0 THEN 999.99
            WHEN 1 THEN 699.99
            WHEN 2 THEN 149.99
            WHEN 3 THEN 79.99
            WHEN 4 THEN 49.99
            WHEN 5 THEN 299.99
            WHEN 6 THEN 449.99
            WHEN 7 THEN 59.99
            WHEN 8 THEN 39.99
            ELSE 89.99
        END
    ) as total,
    DATE_SUB(CURRENT_DATE(), CAST(FLOOR(RAND() * 90) AS INT)) as sale_date,
    CASE FLOOR(RAND() * 4)
        WHEN 0 THEN 'North'
        WHEN 1 THEN 'South'
        WHEN 2 THEN 'East'
        ELSE 'West'
    END as region
FROM (
    SELECT explode(sequence(1, 200)) as i
) AS numbers
WHERE NOT EXISTS (SELECT 1 FROM sales LIMIT 1);

-- Verify the data
SELECT 'Products count:' as info, COUNT(*) as count FROM products
UNION ALL
SELECT 'Sales count:', COUNT(*) FROM sales;

-- Sample queries to test
-- SELECT * FROM products;
-- SELECT region, SUM(total) as total_sales FROM sales GROUP BY region;
-- SELECT p.name, SUM(s.total) as revenue FROM sales s JOIN products p ON s.product_id = p.id GROUP BY p.name ORDER BY revenue DESC LIMIT 5;
