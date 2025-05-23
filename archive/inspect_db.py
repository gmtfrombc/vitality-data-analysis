#!/usr/bin/env python3
"""
Database Schema Inspector

This script examines the schema of the patient_data.db database
and prints sample data to help understand the structure.
"""

import sqlite3
import os
import pandas as pd
from pathlib import Path
import json


def get_db_path():
    """Get the path to the SQLite database."""
    return os.path.join(Path(__file__).parent, "patient_data.db")


def inspect_table(conn, table_name):
    """Print schema and sample data for a table."""
    print(f"\n{'=' * 40}")
    print(f"TABLE: {table_name}")
    print(f"{'=' * 40}")

    # Get schema
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()

    print("\nSCHEMA:")
    for col in columns:
        print(f"  {col[1]} ({col[2]}){' PRIMARY KEY' if col[5] else ''}")

    # Get sample data
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 3", conn)
        print("\nSAMPLE DATA:")
        if not df.empty:
            print(json.dumps(df.to_dict("records"), indent=2))
        else:
            print("  No data")

        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"\nTotal rows: {count}")
    except Exception as e:
        print(f"Error getting sample data: {e}")


def main():
    """Main function to inspect the database."""
    db_path = get_db_path()
    print(f"Inspecting database: {db_path}")

    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)

    # Get list of all tables
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    print(f"\nFound {len(tables)} tables: {', '.join(tables)}")

    # Inspect each table
    for table in tables:
        inspect_table(conn, table)

    conn.close()
    print("\nInspection complete.")


if __name__ == "__main__":
    main()
