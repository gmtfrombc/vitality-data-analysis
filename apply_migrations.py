#!/usr/bin/env python3
"""
Apply database migrations

This script applies any pending database migrations, including
the new ones for the data validation system.
"""

import os
from pathlib import Path
import logging
from app.utils.db_migrations import apply_pending_migrations

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Apply all pending database migrations."""
    # Get the database path
    db_path = os.path.join(Path(__file__).parent, "patient_data.db")

    logger.info(f"Applying migrations to database at: {db_path}")
    apply_pending_migrations(db_path)
    logger.info("Migrations completed successfully")


if __name__ == "__main__":
    main()
