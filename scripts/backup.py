#!/usr/bin/env python3
"""Automated backup script for AAA Admin Dashboard."""

import sqlite3
from datetime import datetime
from pathlib import Path


def backup_database():
    """Backup the main database."""
    db_path = "patient_data.db"
    backup_dir = Path("/Users/gmtfr/VP Data Analysis - 4-2025") / "backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"database_backup_{timestamp}.db"

    # Create backup
    with sqlite3.connect(db_path) as source:
        with sqlite3.connect(str(backup_path)) as backup:
            source.backup(backup)

    print(f"Database backed up to: {backup_path}")

    # Cleanup old backups (keep last 7 days)
    import glob
    import os

    backup_files = glob.glob(str(backup_dir / "database_backup_*.db"))
    backup_files.sort()

    if len(backup_files) > 7:
        for old_backup in backup_files[:-7]:
            os.remove(old_backup)
            print(f"Removed old backup: {old_backup}")


if __name__ == "__main__":
    backup_database()
