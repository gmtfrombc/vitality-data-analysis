#!/usr/bin/env python3
"""
Simplified test app to diagnose and fix BrowserInfo issues.
"""

import panel as pn
import logging
from app.pages.dashboard import dashboard_page
from app.pages.ai_assistant import ai_assistant_page
import db_query

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Simple patient view page that doesn't use any browser info or complex widgets


def simple_patient_view():
    patients_df = db_query.get_all_patients()
    active_patients = patients_df[patients_df["active"] == 1]

    # Create a simple table to display patients
    table = pn.widgets.Tabulator(
        active_patients[["id", "first_name", "last_name", "gender", "birth_date"]],
        show_index=False,
        sizing_mode="stretch_width",
    )

    # Create a simple layout
    layout = pn.Column(
        pn.pane.Markdown("# Patient Overview"),
        pn.pane.Markdown("This is a simplified view showing active patients only."),
        table,
        sizing_mode="stretch_width",
    )

    return layout


if __name__ == "__main__":
    # Configure Panel settings
    pn.extension(sizing_mode="stretch_width")

    # Create tabs with simplified views
    tabs = pn.Tabs(
        ("Dashboard", dashboard_page()),
        ("Simple Patient View", simple_patient_view()),
        ("AI Assistant", ai_assistant_page()),
        sizing_mode="stretch_width",
    )

    # Create a simple header
    header = pn.pane.Markdown(
        "# VP Analytics Platform",
        styles={"background-color": "#054471", "color": "white", "padding": "10px"},
    )

    # Create a simple app layout
    app = pn.Column(header, tabs, sizing_mode="stretch_width")

    # Start the server
    logger.info("Starting simplified test app")
    app.show()
