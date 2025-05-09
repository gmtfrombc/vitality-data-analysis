"""
Validation System Startup Script

This module provides functions to initialize the validation system
when the application starts.
"""

import logging
import sqlite3

from app.utils.validation_engine import ValidationEngine
from app.utils.rule_loader import initialize_validation_rules
from app.utils.db_migrations import apply_pending_migrations

# Set up logging
logger = logging.getLogger(__name__)


def get_db_path():
    """Get the path to the SQLite database from db_query for consistency."""
    # Import here to avoid circular imports
    import db_query

    return db_query.get_db_path()


def check_validation_tables():
    """
    Check if the validation tables exist in the database.

    Returns:
        True if tables exist, False otherwise
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check for validation_rules table
        cursor.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='validation_rules'
        """
        )

        tables_exist = cursor.fetchone() is not None
        conn.close()

        if not tables_exist:
            logger.info("Validation tables not found. Applying migrations...")
            apply_pending_migrations(db_path)

            # Check again after migrations
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='validation_rules'
            """
            )
            tables_exist = cursor.fetchone() is not None
            conn.close()

        return tables_exist

    except Exception as e:
        logger.error(f"Error checking validation tables: {e}")
        return False


def initialize_validation_system():
    """
    Initialize the validation system when the application starts.

    This function:
    1. Checks if validation tables exist
    2. Loads initial validation rules
    3. Runs validation on all patients

    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if tables exist and apply migrations if needed
        if not check_validation_tables():
            logger.warning(
                "Validation tables not found even after migrations. Something is wrong with the database setup."
            )
            return False

        # Initialize validation rules
        db_path = get_db_path()
        success = initialize_validation_rules(db_path)

        if not success:
            logger.warning("Failed to initialize validation rules.")
            return False

        # Create validation engine
        validation_engine = ValidationEngine(db_path)

        # Count existing validation results
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM validation_results")
        result_count = cursor.fetchone()[0]
        conn.close()

        # Only run validation if no results exist
        if result_count == 0:
            logger.info("No validation results found. Running initial validation...")
            validation_engine.validate_all_patients()
            logger.info("Initial validation complete.")
        else:
            logger.info(
                f"Found {result_count} existing validation results. Skipping initial validation."
            )

        return True

    except Exception as e:
        logger.error(f"Error initializing validation system: {e}")
        return False
