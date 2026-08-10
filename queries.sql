-- ============================================================
-- OLIST PART-1: SIX REQUIRED SQL QUERIES
-- Database: database/olist.db
--
-- IMPORTANT SCHEMA NOTE:
-- customers.customer_id = PRIMARY KEY
-- orders.customer_id    = FOREIGN KEY
-- customer_unique_id exists in customers, not directly in orders.
-- ============================================================


-- ============================================================
-- QUERY 1: WHERE with IN
-- Customers from SP, RJ, or MG.
-- ============================================================
SELECT
    customer_unique_id,
    customer_city,
    customer_state
FROM customers
WHERE customer_state IN ('SP', 'RJ', 'MG')
ORDER BY customer_state ASC, customer_city ASC;


-- ============================================================
-- QUERY 2: WHERE with NOT IN on the same column
-- Customers outside SP, RJ, and MG.
-- ============================================================
SELECT
    customer_unique_id,
    customer_city,
    customer_state
FROM customers
WHERE customer_state IS NOT NULL
  AND customer_state NOT IN ('SP', 'RJ', 'MG')
ORDER BY customer_state ASC, customer_city ASC;


-- ============================================================
-- QUERY 3: BETWEEN on a date column
-- Orders purchased during calendar year 2017.
--
-- customer_unique_id is obtained by joining customers because
-- orders contains customer_id, not customer_unique_id.
-- ============================================================
SELECT
    o.order_id,
    c.customer_unique_id,
    o.order_status,
    o.order_purchase_timestamp
FROM orders AS o
INNER JOIN customers AS c
    ON c.customer_id = o.customer_id
WHERE o.order_purchase_timestamp
      BETWEEN '2017-01-01 00:00:00'
          AND '2017-12-31 23:59:59'
ORDER BY o.order_purchase_timestamp ASC;


-- ============================================================
-- QUERY 4: ORDER BY at least two columns
-- State ascending and purchase timestamp descending.
-- ============================================================
SELECT
    c.customer_state,
    c.customer_city,
    o.order_id,
    o.order_status,
    o.order_purchase_timestamp
FROM orders AS o
INNER JOIN customers AS c
    ON c.customer_id = o.customer_id
ORDER BY
    c.customer_state ASC,
    o.order_purchase_timestamp DESC;


-- ============================================================
-- QUERY 5: NOT EXISTS
-- Find parent customer records with no matching order.
--
-- With the complete Olist dataset this may correctly return
-- zero rows.
-- ============================================================
SELECT
    c.customer_id,
    c.customer_unique_id,
    c.customer_city,
    c.customer_state
FROM customers AS c
WHERE NOT EXISTS (
    SELECT 1
    FROM orders AS o
    WHERE o.customer_id = c.customer_id
);


-- ============================================================
-- QUERY 6: LIKE using the % wildcard
-- Customers whose city contains "rio".
-- ============================================================
SELECT
    customer_unique_id,
    customer_city,
    customer_state
FROM customers
WHERE LOWER(customer_city) LIKE '%rio%'
ORDER BY customer_city ASC, customer_state ASC;
