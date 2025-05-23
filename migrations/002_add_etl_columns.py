import sqlite3

DB_PATH = None  # Will be set by migration runner


def column_exists(conn, table, column):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def add_column_if_missing(conn, table, column, coltype):
    if not column_exists(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
        print(f"Added column {column} to {table}")
    else:
        print(f"Column {column} already exists in {table}")


def migrate(db_path):
    conn = sqlite3.connect(db_path)
    try:
        # Patients table columns
        add_column_if_missing(conn, "patients", "provider_id", "INTEGER")
        add_column_if_missing(conn, "patients", "health_coach_id", "INTEGER")
        add_column_if_missing(conn, "patients", "lesson_status", "TEXT")
        add_column_if_missing(conn, "patients", "lessons_completed", "INTEGER")
        add_column_if_missing(conn, "patients", "provider_visits", "INTEGER")
        add_column_if_missing(conn, "patients", "health_coach_visits", "INTEGER")
        add_column_if_missing(conn, "patients", "cancelled_visits", "INTEGER")
        add_column_if_missing(conn, "patients", "no_show_visits", "INTEGER")
        add_column_if_missing(conn, "patients", "rescheduled_visits", "INTEGER")
        add_column_if_missing(conn, "patients", "roles", "TEXT")
        # PMH table column
        add_column_if_missing(conn, "pmh", "code", "TEXT")
        conn.commit()
        print("Migration 002_add_etl_columns.py applied successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python 002_add_etl_columns.py <db_path>")
        sys.exit(1)
    migrate(sys.argv[1])
