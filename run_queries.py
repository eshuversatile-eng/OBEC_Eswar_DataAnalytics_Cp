from pathlib import Path
import sqlite3


# ============================================================
# Project paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Canonical Part-1 database.
DATABASE_FILE = PROJECT_ROOT / "database" / "olist.db"

QUERY_FILES = [
    PROJECT_ROOT / "sql" / "queries.sql",
]

OUTPUT_FILE = PROJECT_ROOT / "outputs" / "query_results.txt"


# ============================================================
# Database helpers
# ============================================================

def table_columns(connection, table_name):
    """Return the real column names for a SQLite table."""
    rows = connection.execute(
        f"PRAGMA table_info({table_name});"
    ).fetchall()

    return {row[1] for row in rows}


def validate_schema(connection):
    """
    Validate the FULL Olist schema used by database/olist.db.

    In this schema:
      customers.customer_id = parent primary key
      orders.customer_id    = child foreign key
      customers.customer_unique_id is a customer identity field,
      but it is NOT stored directly in orders.
    """
    customer_columns = table_columns(connection, "customers")
    order_columns = table_columns(connection, "orders")

    required_customer_columns = {
        "customer_id",
        "customer_unique_id",
        "customer_city",
        "customer_state",
    }

    required_order_columns = {
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
    }

    missing_customers = (
        required_customer_columns - customer_columns
    )

    missing_orders = (
        required_order_columns - order_columns
    )

    if missing_customers or missing_orders:
        messages = []

        if missing_customers:
            messages.append(
                "Missing customers columns: "
                + ", ".join(sorted(missing_customers))
            )

        if missing_orders:
            messages.append(
                "Missing orders columns: "
                + ", ".join(sorted(missing_orders))
            )

        raise RuntimeError(
            "The database schema does not match the full Olist "
            "Part-1 schema.\n"
            + "\n".join(messages)
            + f"\nDatabase checked: {DATABASE_FILE}"
        )


# ============================================================
# Connect to SQLite
# ============================================================

def connect_db():
    if not DATABASE_FILE.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_FILE}\n"
            "Build database/olist.db before running queries."
        )

    connection = sqlite3.connect(
        DATABASE_FILE,
        timeout=30,
    )

    # SQLite requires this on every connection.
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA busy_timeout = 30000;")

    status = connection.execute(
        "PRAGMA foreign_keys;"
    ).fetchone()[0]

    if status != 1:
        connection.close()
        raise RuntimeError(
            "SQLite foreign-key enforcement could not be enabled."
        )

    validate_schema(connection)

    # These indexes make JOIN and NOT EXISTS lookups fast.
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_orders_customer
        ON orders(customer_id);
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_orders_purchase_date
        ON orders(order_purchase_timestamp);
        """
    )

    print("=" * 80)
    print("OLIST PART-1 SQL QUERY RUNNER")
    print("=" * 80)
    print(f"Database Used      : {DATABASE_FILE}")
    print(f"Foreign Key Status : {status}")

    order_columns = sorted(
        table_columns(connection, "orders")
    )

    print(
        "Orders Columns     : "
        + ", ".join(order_columns)
    )

    return connection


# ============================================================
# Read SQL file
# ============================================================

def load_queries(file_path):
    if not file_path.exists():
        raise FileNotFoundError(
            f"SQL file not found: {file_path}"
        )

    sql = file_path.read_text(
        encoding="utf-8"
    )

    queries = [
        query.strip()
        for query in sql.split(";")
        if query.strip()
    ]

    return queries


# ============================================================
# Execute queries
# ============================================================

def execute_queries(connection, queries, title, output):
    cursor = connection.cursor()

    for query_number, query in enumerate(
        queries,
        start=1,
    ):
        print()
        print("=" * 90)
        print(f"{title} : QUERY {query_number}")
        print("=" * 90)

        output.append("")
        output.append("=" * 90)
        output.append(
            f"{title} : QUERY {query_number}"
        )
        output.append("=" * 90)
        output.append(query)

        try:
            cursor.execute(query)

            if cursor.description is None:
                connection.commit()

                message = "Query Executed Successfully."
                print(message)
                output.append(message)
                continue

            columns = [
                item[0]
                for item in cursor.description
            ]

            rows = cursor.fetchall()

            print("Columns")
            print(columns)
            print(f"Rows Returned : {len(rows)}")

            output.append("Columns")
            output.append(", ".join(columns))
            output.append(
                f"Rows Returned : {len(rows)}"
            )

            # Display/save only first 20 rows so large query
            # results remain readable.
            for row in rows[:20]:
                row_text = " | ".join(
                    str(value)
                    for value in row
                )

                print(row_text)
                output.append(row_text)

            if len(rows) > 20:
                message = (
                    f"... {len(rows) - 20} more rows"
                )

                print(message)
                output.append(message)

        except sqlite3.Error as error:
            message = (
                f"SQL ERROR in QUERY "
                f"{query_number}: {error}"
            )

            print(message)
            output.append(message)


# ============================================================
# Main
# ============================================================

def main():
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = connect_db()
    output = []

    try:
        for sql_file in QUERY_FILES:
            queries = load_queries(sql_file)

            execute_queries(
                connection,
                queries,
                sql_file.name,
                output,
            )

    finally:
        connection.close()

    OUTPUT_FILE.write_text(
        "\n".join(output) + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print("All queries finished.")
    print(f"Results Saved To   : {OUTPUT_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
    
    