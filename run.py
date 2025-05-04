#!/usr/bin/env python3
"""
Run script for the Metabolic Health Data Analysis application.

This script launches the Panel web application.
"""

import panel as pn
from app.pages.dashboard import dashboard_page
import app.pages.patient_view as patient_view
import app.pages.data_assistant as data_assistant
import logging
import atexit
import signal
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("app.log")],
)
logger = logging.getLogger(__name__)

# Store server reference for cleanup
_server = None


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


def create_app():
    """Create the main Panel application."""

    # Configure Panel settings
    pn.extension(sizing_mode="stretch_width")

    # Create the navigation bar
    menu = [
        ("Dashboard", "dashboard"),
        ("Patient View", "patient_view"),
        ("Data Analysis Assistant", "data_assistant"),
    ]

    # Create tabs for navigation
    tabs = pn.Tabs(
        ("Dashboard", dashboard_page()),
        ("Patient View", patient_view.patient_view_page()),
        ("Data Analysis Assistant", data_assistant.data_assistant_page()),
        dynamic=True,
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
    app = create_app()

    # Start the Panel server
    logger.info("Starting VP Analytics Platform")

    try:
        # Store server reference for cleanup
        _server = app.show(threaded=True)

        # Log process info for debugging
        logger.info(f"Server running with PID: {os.getpid()}")
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")
        cleanup_resources()
        sys.exit(1)
