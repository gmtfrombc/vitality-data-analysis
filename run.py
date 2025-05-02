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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("app.log")],
)
logger = logging.getLogger(__name__)


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
    # Get the application template
    app = create_app()

    # Start the Panel server
    logger.info("Starting VP Analytics Platform")

    try:
        app.show(threaded=True)
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")
