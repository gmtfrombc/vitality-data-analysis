"""
Dashboard Page Component

This page provides an overview of patient data and key metrics.
"""

import hvplot.pandas
import holoviews as hv
import panel as pn
import param
import pandas as pd
import db_query
import sys
from pathlib import Path

# Add the parent directory to path so we can import db_query
sys.path.append(str(Path(__file__).parent.parent.parent))

# Third-party imports


class Dashboard(param.Parameterized):
    """Dashboard page displaying patient overview data and statistics"""

    refresh_data = param.Action(lambda x: x.param.trigger('refresh_data'))

    def __init__(self, **params):
        super().__init__(**params)
        self.stats = db_query.get_program_stats()

    def view(self):
        """Generate the dashboard view"""

        # Create title and description
        title = pn.pane.Markdown("# Dashboard", sizing_mode="stretch_width")
        description = pn.pane.Markdown(
            "This dashboard provides an overview of all patient data and key metrics."
        )

        # Create cards for quick stats
        total_patients = self.stats.get('total_patients', 0)
        patients_card = pn.indicators.Number(
            name='Total Patients',
            value=total_patients,
            format='{value}',
            colors=[(0, 'green')],
            font_size='24pt'
        )

        # Get average engagement score
        engagement_stats = self.stats.get('engagement_scores', {})
        avg_engagement = engagement_stats.get('avg', 0)
        engagement_card = pn.indicators.Number(
            name='Avg Engagement Score',
            value=avg_engagement,
            format='{value:.1f}',
            colors=[(0, 'blue')],
            font_size='24pt'
        )

        # Get gender distribution
        gender_dist = self.stats.get('gender_distribution', {})
        gender_df = pd.DataFrame({
            'Gender': list(gender_dist.keys()),
            'Count': list(gender_dist.values())
        })
        gender_plot = gender_df.hvplot.bar(
            x='Gender', y='Count', title='Gender Distribution',
            hover_cols=['Gender', 'Count']
        )

        # Get vital signs averages
        vitals_avg = self.stats.get('vitals_averages', {})
        vitals_df = pd.DataFrame({
            'Metric': ['Weight (kg)', 'BMI', 'SBP (mmHg)', 'DBP (mmHg)'],
            'Value': [
                vitals_avg.get('weight', 0),
                vitals_avg.get('bmi', 0),
                vitals_avg.get('sbp', 0),
                vitals_avg.get('dbp', 0)
            ]
        })
        vitals_plot = vitals_df.hvplot.bar(
            x='Metric', y='Value', title='Average Vital Signs',
            hover_cols=['Metric', 'Value']
        )

        # Find patients with abnormal values
        abnormal_df = db_query.find_patients_with_abnormal_values()
        abnormal_table = pn.widgets.Tabulator(
            abnormal_df,
            pagination='remote',
            page_size=5,
            sizing_mode='stretch_width'
        )

        # Create layout
        stats_row = pn.Row(
            patients_card,
            engagement_card,
            sizing_mode='stretch_width'
        )

        plots_row = pn.Row(
            pn.Column(pn.pane.HoloViews(gender_plot)),
            pn.Column(pn.pane.HoloViews(vitals_plot)),
            sizing_mode='stretch_width'
        )

        # Create refresh button
        refresh_button = pn.widgets.Button(
            name='Refresh Data',
            button_type='primary',
            width=100
        )
        refresh_button.on_click(self._refresh_data)

        # Combine everything
        layout = pn.Column(
            title,
            description,
            pn.layout.Divider(),
            stats_row,
            pn.layout.Divider(),
            plots_row,
            pn.layout.Divider(),
            pn.Row(pn.pane.Markdown("## Attention Required"), refresh_button),
            abnormal_table,
            sizing_mode='stretch_width'
        )

        return layout

    def _refresh_data(self, event=None):
        """Refresh the data displayed in the dashboard"""
        self.stats = db_query.get_program_stats()
