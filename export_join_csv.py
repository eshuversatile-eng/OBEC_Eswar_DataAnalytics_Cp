from pathlib import Path
import sqlite3
import pandas as pd

# -------------------------------------------------------
# Project Paths
# -------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATABASE_FILE = PROJECT_ROOT / "database" / "olist.db"

QUERY_FILE = PROJECT_ROOT / "sql" / "export_join.sql"

OUTPUT_CSV = PROJECT_ROOT / "outputs" / "task4_inner_join_export.csv"

# -------------------------------------------------------
# Connect
# -------------------------------------------------------

conn = sqlite3.connect(DATABASE_FILE)

conn.execute("PRAGMA foreign_keys = ON;")

# -------------------------------------------------------
# Read SQL Query
# -------------------------------------------------------

with open(QUERY_FILE, "r", encoding="utf-8") as f:

    sql = f.read()

# -------------------------------------------------------
# Execute Query
# -------------------------------------------------------

df = pd.read_sql_query(sql, conn)

# -------------------------------------------------------
# Export CSV
# -------------------------------------------------------

df.to_csv(

    OUTPUT_CSV,

    index=False,

    encoding="utf-8"

)

print(df.head())

print()

print(f"Rows Exported : {len(df)}")

print(f"Columns : {len(df.columns)}")

print(f"CSV Saved To : {OUTPUT_CSV}")

conn.close()