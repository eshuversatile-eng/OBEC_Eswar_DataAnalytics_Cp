-- ============================================================
-- TASK 5: REFERENTIAL-INTEGRITY VALIDATION
-- Parent table: customers
-- Parent key: customers.customer_unique_id
-- Child table: orders
-- Foreign key: orders.customer_unique_id
-- ============================================================


-- ------------------------------------------------------------
-- 5A. COUNT(DISTINCT ...) starting sanity check
-- ------------------------------------------------------------
-- Compares:
-- 1. Total customer records
-- 2. Distinct customer primary keys
-- 3. Total order records
-- 4. Distinct customer foreign keys appearing in orders
--
-- This query is only a starting check. It does not by itself
-- prove whether the relationship is 1:1 or 1:many.

SELECT
    (SELECT COUNT(*)
     FROM customers) AS total_customer_rows,

    (SELECT COUNT(DISTINCT customer_unique_id)
     FROM customers) AS distinct_customer_ids,

    (SELECT COUNT(*)
     FROM orders) AS total_order_rows,

    (SELECT COUNT(DISTINCT customer_unique_id)
     FROM orders) AS distinct_customers_with_orders;


-- ------------------------------------------------------------
-- 5B. Grouped child-count query
-- ------------------------------------------------------------
-- Counts the number of matching order rows for each customer.
-- Any customer with order_count > 1 demonstrates that the
-- relationship is one-to-many rather than one-to-one.

SELECT
    o.customer_unique_id,
    COUNT(*) AS order_count
FROM orders AS o
GROUP BY o.customer_unique_id
ORDER BY
    order_count DESC,
    o.customer_unique_id ASC;


-- ------------------------------------------------------------
-- Optional summary of the grouped child-count query
-- ------------------------------------------------------------
-- Reports:
-- 1. Maximum number of orders linked to one customer
-- 2. Number of customers having more than one order

SELECT
    MAX(customer_order_summary.order_count) AS maximum_orders_per_customer,
    SUM(
        CASE
            WHEN customer_order_summary.order_count > 1 THEN 1
            ELSE 0
        END
    ) AS customers_with_multiple_orders
FROM (
    SELECT
        o.customer_unique_id,
        COUNT(*) AS order_count
    FROM orders AS o
    GROUP BY o.customer_unique_id
) AS customer_order_summary;


-- ------------------------------------------------------------
-- 5C. Explicit orphan check
-- ------------------------------------------------------------
-- Finds child rows in orders whose customer_unique_id does not
-- have a matching primary-key value in customers.
--
-- Expected result after a valid import: zero rows.

SELECT
    o.order_id,
    o.customer_unique_id,
    o.order_status,
    o.order_purchase_timestamp
FROM orders AS o
LEFT JOIN customers AS c
    ON o.customer_unique_id = c.customer_unique_id
WHERE c.customer_unique_id IS NULL;


-- ------------------------------------------------------------
-- Optional orphan-count summary
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS orphan_order_count
FROM orders AS o
LEFT JOIN customers AS c
    ON o.customer_unique_id = c.customer_unique_id
WHERE c.customer_unique_id IS NULL;
