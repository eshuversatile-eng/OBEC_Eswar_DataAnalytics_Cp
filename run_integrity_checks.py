from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "olist.db"
OUT = ROOT / "outputs" / "integrity_results.txt"

QUERIES = {
    "Order row/distinct-key sanity": """
        SELECT COUNT(*) AS order_rows,
               COUNT(DISTINCT order_id) AS distinct_orders,
               COUNT(DISTINCT customer_id) AS distinct_customer_ids
        FROM orders
    """,
    "Parents with more than one child order": """
        SELECT COUNT(*) FROM (
            SELECT customer_id FROM orders
            GROUP BY customer_id HAVING COUNT(*) > 1
        )
    """,
    "Orphan orders": """
        SELECT COUNT(*) FROM orders o
        LEFT JOIN customers c ON c.customer_id=o.customer_id
        WHERE c.customer_id IS NULL
    """,
    "Orphan order items": """
        SELECT COUNT(*) FROM order_items oi
        LEFT JOIN orders o ON o.order_id=oi.order_id
        WHERE o.order_id IS NULL
    """,
    "Maximum items per order": """
        SELECT MAX(child_count) FROM (
            SELECT order_id, COUNT(*) child_count
            FROM order_items GROUP BY order_id
        )
    """,
}


def main() -> None:
    lines = []
    with sqlite3.connect(DB) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        for label, query in QUERIES.items():
            result = conn.execute(query).fetchall()
            lines.append(f"{label}: {result}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
