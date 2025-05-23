import sqlite3
import sys


def column_exists(conn, table, column):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def index_exists(conn, index_name):
    cur = conn.execute("PRAGMA index_list(patient_visit_metrics)")
    return any(row[1] == index_name for row in cur.fetchall())


def migrate(db_path):
    conn = sqlite3.connect(db_path)
    try:
        if not column_exists(conn, "patient_visit_metrics", "last_visit_date"):
            conn.execute(
                "ALTER TABLE patient_visit_metrics ADD COLUMN last_visit_date TEXT"
            )
            print("Added column last_visit_date to patient_visit_metrics")
        else:
            print("Column last_visit_date already exists in patient_visit_metrics")
        if not index_exists(conn, "idx_patient_visit_metrics_last_visit_date"):
            conn.execute(
                "CREATE INDEX idx_patient_visit_metrics_last_visit_date ON patient_visit_metrics(last_visit_date)"
            )
            print(
                "Created index idx_patient_visit_metrics_last_visit_date on patient_visit_metrics(last_visit_date)"
            )
        else:
            print(
                "Index idx_patient_visit_metrics_last_visit_date already exists on patient_visit_metrics"
            )
        conn.commit()
        print("Migration 010_add_last_visit_date.py applied successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python 010_add_last_visit_date.py <db_path>")
        sys.exit(1)
    migrate(sys.argv[1])
