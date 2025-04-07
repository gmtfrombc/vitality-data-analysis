"""
Metabolic Health Data Analysis & AI-Assisted SQL Query Web Application

This is the main entry point for the Panel-based web application.
"""

import logging
from app.pages.ai_assistant import AIAssistant
from app.pages.patient_view import PatientView
from app.pages.dashboard import Dashboard
import hvplot.pandas
import holoviews as hv
import param
import panel as pn
import db_query
import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the parent directory to path so we can import db_query
sys.path.append(str(Path(__file__).parent.parent))

# Import visualization and UI packages

# Load Panel extensions for better visualization

# Initialize Panel with all extensions at once (more reliable than separate calls)
pn.extension('tabulator', sizing_mode="stretch_width")
hv.extension('bokeh')

# Set theme to a valid option
pn.config.theme = 'dark'

# Import page modules

# Create the main layout

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('metabolic_health_app')


def create_app():
    # Create sidebar with navigation
    def sidebar():
        menu = pn.widgets.RadioButtonGroup(
            options=['Dashboard', 'Patient View', 'AI Assistant'],
            button_type='primary'
        )

        logo = pn.pane.Markdown("# MHP Data Analysis")

        return pn.Column(
            logo,
            pn.layout.Divider(),
            pn.Row(pn.pane.Markdown("### Navigation")),
            menu,
            pn.layout.Divider(),
            pn.Row(pn.pane.Markdown(f"### Database Info")),
            pn.pane.Markdown(
                f"**Patients:** {len(db_query.get_all_patients())}"),
            sizing_mode='fixed',
            width=300
        ), menu

    # Create the pages
    dashboard = Dashboard()
    patient_view = PatientView()
    ai_assistant = AIAssistant()

    # Create the sidebar
    side_panel, menu = sidebar()

    # Create main content area that changes with menu selection
    @pn.depends(menu.param.value)
    def get_content(page):
        if page == 'Dashboard':
            return dashboard.view()
        elif page == 'Patient View':
            return patient_view.view()
        elif page == 'AI Assistant':
            return ai_assistant.view()
        else:
            return pn.pane.Markdown("# Page not found")

    # Combine sidebar and content in template
    template = pn.template.MaterialTemplate(
        title="Metabolic Health Data Analysis",
        sidebar=side_panel,
        main=get_content,
        header_background="#054471",
    )

    return template


app = create_app()

if __name__ == "__main__":
    app.show()
