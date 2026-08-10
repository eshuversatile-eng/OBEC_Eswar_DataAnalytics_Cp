-- ===============================================
-- TASK 6
-- Export INNER JOIN Result
-- ===============================================

SELECT

    c.customer_unique_id,
    c.customer_city,
    c.customer_state,

    o.order_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,

    o.delivery_days,
    o.delay_days,

    o.item_count,
    o.seller_count,

    o.item_value,
    o.freight_value,
    o.payment_value,

    o.review_score

FROM customers AS c

INNER JOIN orders AS o

ON c.customer_unique_id = o.customer_unique_id

ORDER BY

    c.customer_state,
    o.order_purchase_timestamp;