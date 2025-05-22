#!/usr/bin/env python3
"""
Run script for the Metabolic Health Data Analysis application.

This script launches the Panel web application.
"""

import panel as pn
import logging
import atexit
import signal
import sys
import os
from pathlib import Path
import traceback
from dotenv import load_dotenv

# from app.pages.ai_assistant import ai_assistant_page  # Commented out to disable SQL assistant for Data Assistant tab
# Use robust Data Analysis Assistant
from app.data_assistant import data_assistant_page

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Store server reference for cleanup
_server = None

# Load environment variables from .env file
load_dotenv()


def cleanup_resources():
    """Cleanup function to ensure resources are properly released."""
    logger.info("Cleaning up resources...")
    # Stop periodic callbacks
    try:
        if hasattr(pn.state, "_periodic_callbacks"):
            for cb in list(pn.state._periodic_callbacks):
                try:
                    cb.stop()
                    logger.info(f"Stopped callback: {cb}")
                except Exception as e:
                    logger.error(f"Error stopping callback: {e}")
    except Exception as e:
        logger.error(f"Error cleaning up callbacks: {e}")

    # Close server if it exists
    global _server
    if _server:
        try:
            logger.info("Shutting down server...")
            _server.stop()
            _server = None
        except Exception as e:
            logger.error(f"Error stopping server: {e}")


def signal_handler(sig, frame):
    """Handle termination signals by cleaning up and exiting."""
    logger.info(f"Received signal {sig}, shutting down...")
    cleanup_resources()
    sys.exit(0)


def safe_import(module_path, fallback_message=None):
    """
    Safely import a module with error handling.

    Args:
        module_path: String path to the module to import
        fallback_message: Message to display if import fails

    Returns:
        The imported module or a dummy module with a get_page function that displays an error message
    """
    try:
        # Try to import the module
        __import__(module_path)
        module = sys.modules[module_path]
        logger.info(f"Successfully imported {module_path}")
        return module
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error importing {module_path}: {e}\n{error_details}")

        # Create a fallback module
        class FallbackModule:
            @staticmethod
            def gap_report_page():
                message = (
                    fallback_message or f"Error loading module {module_path}: {str(e)}"
                )
                return pn.Column(
                    pn.pane.Markdown("# Module Load Error"),
                    pn.pane.Markdown(message),
                    pn.pane.Markdown("Check application logs for details."),
                )

            @staticmethod
            def get_page():
                return FallbackModule.gap_report_page()

        return FallbackModule


def safe_apply_migrations(db_path):
    """
    Safely apply database migrations with error handling.

    Args:
        db_path: Path to the SQLite database

    Returns:
        True if successful, False otherwise
    """
    try:
        # Import the apply_pending_migrations function
        from app.utils.db_migrations import apply_pending_migrations

        # Apply migrations
        logger.info("Checking for database migrations...")
        apply_pending_migrations(db_path)
        logger.info("Database is up to date")
        return True
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error applying database migrations: {e}\n{error_details}")
        return False


def safe_initialize_validation_system():
    """
    Safely initialize the validation system with error handling.

    Returns:
        True if successful, False otherwise
    """
    try:
        # Import the initialize_validation_system function
        from app.utils.validation_startup import initialize_validation_system

        # Initialize the validation system
        logger.info("Initializing validation system...")
        result = initialize_validation_system()
        if result:
            logger.info("Validation system initialized successfully")
        else:
            logger.warning("Validation system initialization returned False")
        return result
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error initializing validation system: {e}\n{error_details}")
        return False


def create_app():
    """Create the main Panel application."""

    # Configure Panel settings
    pn.extension(notifications=True, sizing_mode="stretch_width")

    # Apply database migrations
    db_path = os.path.join(Path(__file__).parent, "patient_data.db")
    migration_success = safe_apply_migrations(db_path)

    # Initialize validation system
    validation_success = safe_initialize_validation_system()

    # Safely import modules with fallback messages
    dashboard = safe_import(
        "app.pages.dashboard",
        "Dashboard module could not be loaded. Check logs for details.",
    )

    patient_view = safe_import(
        "app.pages.patient_view",
        "Patient View module could not be loaded. Check logs for details.",
    )

    data_assistant = safe_import(
        "app.data_assistant",
        "Data Assistant module could not be loaded. Check logs for details.",
    )

    evaluation_page = safe_import(
        "app.pages.evaluation_page",
        "Evaluation Dashboard module could not be loaded. Check logs for details.",
    )

    gap_report_page_mod = safe_import(
        "app.pages.gap_report_page",
        "Gap Report module could not be loaded. Check logs for details.",
    )

    data_validation = safe_import(
        "app.pages.data_validation",
        "Data Validation module could not be loaded. Check logs for details.",
    )

    # Create the main application layout with combined Data Quality & Engagement tab
    print("Registering Data Assistant tab with data_assistant_page")
    tabs = pn.Tabs(
        ("Dashboard", dashboard.dashboard_page()),
        ("Data Assistant", data_assistant_page()),
        ("Patient View", patient_view.patient_view_page()),
        ("Data Validation", data_validation.get_page()),
        ("Data Quality & Engagement", gap_report_page_mod.gap_report_page()),
        ("Evaluation", evaluation_page.evaluation_page()),
    )

    # Create the template
    template = pn.template.MaterialTemplate(
        title="VP Analytics Platform",
        logo="https://upload.wikimedia.org/wikipedia/commons/5/53/Vue_Dashboard.png",
        main=tabs,
        main_max_width="1800px",
        sidebar_width=0,  # Hide sidebar initially
    )

    return template


if __name__ == "__main__":
    # Register signal handlers and cleanup
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(cleanup_resources)

    # Get the application template
    try:
        logger.info("Creating application...")
        app = create_app()
        logger.info("Application created successfully")
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error creating application: {e}\n{error_details}")
        sys.exit(1)

    # Start the Panel server
    logger.info("Starting VP Analytics Platform")

    try:
        # Store server reference for cleanup
        _server = app.show(threaded=True)

        # Log process info for debugging
        logger.info(f"Server running with PID: {os.getpid()}")
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error starting server: {e}\n{error_details}")
        cleanup_resources()
        sys.exit(1)
