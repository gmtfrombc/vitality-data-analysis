#!/usr/bin/env python3
"""
apply_migrations.py – Apply all SQL and Python migrations to a SQLite database.

Usage:
    python scripts/apply_migrations.py --db path/to/db.sqlite

If --db is omitted, defaults to 'patient_data.db' in the repo root.
"""

import argparse
import sqlite3
from pathlib import Path
import sys
import subprocess

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
DEFAULT_DB = Path(__file__).resolve().parent.parent / "patient_data.db"


def get_migration_files():
    files = sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*." + "*"))
    return files


def apply_sql_migration(conn, sql_path):
    sql = sql_path.read_text(encoding="utf-8")
    try:
        conn.executescript(sql)
        print(f"Applied migration: {sql_path.name}")
    except Exception as e:
        print(f"ERROR applying {sql_path.name}: {e}")
        raise


def apply_py_migration(py_path, db_path):
    try:
        result = subprocess.run(
            [sys.executable, str(py_path), str(db_path)], capture_output=True, text=True
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"ERROR applying {py_path.name}: {result.stderr}")
            raise RuntimeError(f"Migration {py_path.name} failed")
        else:
            print(f"Applied migration: {py_path.name}")
    except Exception as e:
        print(f"ERROR applying {py_path.name}: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Apply all SQL and Python migrations to a SQLite DB."
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB),
        help="Path to SQLite DB file (default: patient_data.db)",
    )
    args = parser.parse_args()

    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        print(f"Database file {db_path} does not exist. Creating new DB.")
    else:
        print(f"Using existing DB: {db_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        for migration_file in get_migration_files():
            if migration_file.suffix == ".sql":
                apply_sql_migration(conn, migration_file)
            elif migration_file.suffix == ".py":
                conn.commit()  # Commit any open transaction before running external script
                apply_py_migration(migration_file, db_path)
                conn = sqlite3.connect(str(db_path))  # Reconnect after script
            else:
                print(f"Skipping unknown migration type: {migration_file.name}")
        conn.commit()
        print("All migrations applied successfully.")
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
