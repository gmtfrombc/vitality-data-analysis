import sqlite3
import pandas as pd

# Connect to the SQLite database
conn = sqlite3.connect("patient_data.db")
cursor = conn.cursor()

# Get list of all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("Tables in database:")
for table in tables:
    table_name = table[0]
    print(f"\n{table_name}:")

    # Get schema for each table
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()

    # Create a DataFrame for better display of the columns
    columns_df = pd.DataFrame(
        columns, columns=["cid", "name", "type", "notnull", "default_value", "pk"]
    )
    print(columns_df[["name", "type", "pk"]])

    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    row_count = cursor.fetchone()[0]
    print(f"Total rows: {row_count}")

    # Show sample data (first 3 rows)
    if row_count > 0:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
        sample_data = cursor.fetchall()

        # Get column names for the DataFrame
        column_names = [column[1] for column in columns]

        if sample_data:
            print("\nSample data:")
            sample_df = pd.DataFrame(sample_data, columns=column_names)
            print(sample_df.head())

# Close the connection
conn.close()
