PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_unique_id TEXT PRIMARY KEY,
    customer_city TEXT NOT NULL,
    customer_state TEXT NOT NULL
);

CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    customer_unique_id TEXT NOT NULL,
    order_status TEXT,
    order_purchase_timestamp TEXT,
    order_approved_at TEXT,
    order_delivered_customer_date TEXT,
    order_estimated_delivery_date TEXT,
    delivery_days REAL,
    delay_days REAL,
    item_count INTEGER,
    seller_count INTEGER,
    item_value REAL,
    freight_value REAL,
    payment_value REAL,
    review_score REAL,

    FOREIGN KEY (customer_unique_id)
        REFERENCES customers(customer_unique_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);