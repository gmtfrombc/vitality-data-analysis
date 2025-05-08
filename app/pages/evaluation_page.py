"""Evaluation Dashboard Page

This page provides access to the Assistant Evaluation Framework dashboard
for monitoring metrics and KPIs related to the Data Analysis Assistant.
"""

import panel as pn

from app.components.evaluation_dashboard import evaluation_dashboard

# Initialize extensions
pn.extension("tabulator")


def evaluation_page() -> pn.viewable.Viewable:
    """Create and return the evaluation dashboard page.

    Returns:
        panel.viewable.Viewable: The evaluation dashboard page
    """
    title = pn.pane.Markdown(
        "# Assistant Evaluation Dashboard", sizing_mode="stretch_width"
    )

    description = pn.pane.Markdown(
        """
        This dashboard provides insights into the performance and effectiveness of the Data Analysis Assistant.
        Monitor satisfaction, response quality, intent classification accuracy, and visualization metrics over time.
        
        All data is collected from user feedback and interaction logs, helping us continuously improve the assistant.
        """,
        sizing_mode="stretch_width",
    )

    # Get the evaluation dashboard
    dashboard = evaluation_dashboard()

    # Combine everything
    return pn.Column(
        title, description, pn.layout.Divider(), dashboard, sizing_mode="stretch_width"
    )
