from pathlib import Path
import sqlite3
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = PROJECT_ROOT / "data" / "olist_order_analysis_export.csv"
DATABASE_FILE = PROJECT_ROOT / "database" / "olist_relational.db"
VERIFICATION_FILE = PROJECT_ROOT / "outputs" / "verification_output.txt"

def connect_db():
    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_FILE)

    # SQLite requires this on every connection.
    conn.execute("PRAGMA foreign_keys = ON;")

    status = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
    return conn, status
    # Returns both database connection and foreign key status (1 = enabled, 0 = disabled).

def load_data():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"CSV not found: {INPUT_CSV}")  
    #Stops the program with a clear error if the CSV is missing.

    df = pd.read_csv(INPUT_CSV, low_memory=False)
    #Reads the Olist CSV into a Pandas DataFrame called df.
    required_columns = [
        "customer_unique_id",
        "customer_city",
        "customer_state",
        "order_id",
        "order_status",
    ]
    #Starts a list of columns required for this minimal relational database.
    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]
    #Checks whether any required columns are absent from the CSV.
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    #Removes rows that have no customer key or order key.
    #Those rows cannot be used in a valid relational structure.
    df = df.dropna(
    subset=["customer_unique_id", "order_id"]
    ).copy()
    return df

    #Defines the function that creates the two relational tables.
def create_tables(conn):
    conn.executescript(
        '''
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS customers;

        CREATE TABLE customers (
            customer_unique_id TEXT PRIMARY KEY,
            customer_city TEXT,
            customer_state TEXT
        );

        CREATE TABLE orders (
            order_id TEXT PRIMARY KEY,
            customer_unique_id TEXT NOT NULL,
            order_status TEXT,

            FOREIGN KEY (customer_unique_id)
                REFERENCES customers(customer_unique_id)
        );
        '''
    )

    conn.commit()

    #Defines a function that loads actual Olist rows into the two tables.
def insert_data(conn, df):
    customers = (
        df[                             #Keeps only these customer fields.
            [
                "customer_unique_id",
                "customer_city",
                "customer_state",
            ]
        ]
        .drop_duplicates(subset=["customer_unique_id"]) #Keeps only one row for each customer.
        .fillna("unknown")          #Replaces missing city or state values with "unknown".
    )

    orders = (
        df[
            [
                "order_id",
                "customer_unique_id",
                "order_status",
            ]
        ]
        .drop_duplicates(subset=["order_id"])      #Keeps only one row per order because order_id is the primary key.
    )

    conn.executemany(                               #Executes one INSERT repeatedly for many customer rows.
        '''
        INSERT INTO customers (
            customer_unique_id,
            customer_city,
            customer_state
        )                                           
        VALUES (?, ?, ?);                    
        ''',
        customers.itertuples(index=False, name=None),
    )

    conn.executemany(                               #Executes one INSERT repeatedly for many order rows.
        '''
        INSERT INTO orders (
            order_id,
            customer_unique_id,
            order_status
        )
        VALUES (?, ?, ?);
        ''',
        orders.itertuples(index=False, name=None),
    )

    conn.commit()

    return len(customers), len(orders)               #Returns the number of parent and child records inserted.

#Defines the function that proves the foreign key is really enforced.
def test_foreign_key(conn):
    # Try an intentionally invalid database operation.
    try:
        # This customer ID does not exist in the customers table,
        # so SQLite should reject the order because of the foreign key.
        conn.execute(
            '''
            INSERT INTO orders (
                order_id,
                customer_unique_id,
                order_status
            )
            VALUES (?, ?, ?);
            ''',
            (
                "INVALID_ORDER_999",
                "CUSTOMER_DOES_NOT_EXIST",
                "processing",
            ),
        )

        conn.commit()

        return (
            "FAILED: Invalid foreign-key insert was accepted.",
            "No SQLite error was raised.",
        )

    except sqlite3.IntegrityError as error:             #Catches the expected SQLite integrity error.
        conn.rollback()                                 #Cancels the failed transaction.

        return (                                        #Returns the proof of correct enforcement.
            "PASSED: Invalid foreign-key insert was rejected.",
            f"SQLite error: {error}",
        )

def save_verification(                                  #Defines the function that writes the required evidence to a file.
    foreign_key_status,
    customer_count,
    order_count,
    test_result,
    sqlite_message,
):
    VERIFICATION_FILE.parent.mkdir(                     #Makes sure the outputs folder exists.
        parents=True,
        exist_ok=True,
    )

    lines = [
        "TASK 1 - SQLITE FOREIGN KEY VERIFICATION",
        "=" * 50,                                                       #Creates 50 = characters for formatting.
        f"PRAGMA foreign_keys status: {foreign_key_status}",            #Records whether SQLite foreign-key enforcement was enabled.
        f"Customers inserted: {customer_count:,}",                      #Records how many customer rows were loaded.
        f"Orders inserted: {order_count:,}",                            #Records how many orders were loaded.
        test_result,
        sqlite_message,
    ]

    VERIFICATION_FILE.write_text(                                       #Writes the report to disk.
        "\n".join(lines) + "\n",                                        #Joins all the report lines with line breaks.
        encoding="utf-8",                                               #Saves it as UTF-8 text.
    )

    for line in lines:
        print(line)                                                     #Prints the same evidence in the VS Code terminal.

    print(f"Verification saved to: {VERIFICATION_FILE}")

#Defines the complete execution sequence.
def main():
    df = load_data()                                #Loads the Olist CSV into a Pandas DataFrame and checks for required columns.

    conn, foreign_key_status = connect_db()         #Opens SQLite and enables foreign keys.

    try:
        create_tables(conn)
        #Loads the valid parent and child records.
        customer_count, order_count = insert_data(
            conn,
            df,
        )
        #Attempts the invalid insert and captures the result.
        test_result, sqlite_message = test_foreign_key(conn)
        #Saves all evidence.
        save_verification(
            foreign_key_status,
            customer_count,
            order_count,
            test_result,
            sqlite_message,
        )
        #Passes the important values to the report.
    finally:
        conn.close()

        #Checks whether this file was executed directly.
if __name__ == "__main__":
    main()