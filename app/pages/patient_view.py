"""
Patient View Page Component

This page provides detailed information about a selected patient.
"""

import matplotlib
import hvplot.pandas
import holoviews as hv
import panel as pn
import param
import pandas as pd
import db_query
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('patient_view')

# Add the parent directory to path so we can import db_query
sys.path.append(str(Path(__file__).parent.parent.parent))

# Initialize rendering backend for HoloViews plots
hv.extension('bokeh')

# Set explicit renderer
renderer = hv.renderer('bokeh')
renderer.theme = 'dark'

# Configure matplotlib to use non-GUI backend
matplotlib.use('agg')

# Third-party imports

# Load Panel extensions to ensure proper plot rendering
pn.extension('tabulator')
pn.extension('plotly')


class PatientView(param.Parameterized):
    """Patient view page displaying detailed patient information"""

    selected_patient_id = param.String(default=None)  # Start with no default
    patient_data = param.Dict(default={})

    def __init__(self, **params):
        super().__init__(**params)
        # Get list of all patients for the dropdown
        patients_df = db_query.get_all_patients()
        self.patient_options = [(str(row['id']), f"{row['first_name']} {row['last_name']}")
                                for _, row in patients_df.iterrows()]

        # Set default patient ID to the first available patient
        if not self.selected_patient_id and len(patients_df) > 0:
            self.selected_patient_id = str(patients_df.iloc[0]['id'])
            logger.info(
                f"Setting default patient ID to: {self.selected_patient_id}")

        self._update_patient_data()

    def view(self):
        """Generate the patient view"""

        # Create title
        title = pn.pane.Markdown("# Patient View", sizing_mode="stretch_width")
        description = pn.pane.Markdown(
            "View detailed information about a patient and their health data."
        )

        # Create patient selector
        patients_df = db_query.get_all_patients()
        patient_dict = {f"{row['first_name']} {row['last_name']}": str(row['id'])
                        for _, row in patients_df.iterrows()}

        # Create a reverse mapping for lookups by ID
        id_to_name = {v: k for k, v in patient_dict.items()}

        # Set initial patient ID - use the first patient's ID if current ID not found
        if not self.selected_patient_id in patient_dict.values() and len(patient_dict) > 0:
            self.selected_patient_id = list(patient_dict.values())[0]

        # When displaying the dropdown, show the name that corresponds to the ID
        name_to_display = id_to_name.get(self.selected_patient_id, list(
            patient_dict.keys())[0] if patient_dict else None)

        patient_select = pn.widgets.Select(
            name='Select Patient',
            options=patient_dict,
            value=name_to_display
        )

        # Use a callback that handles both names and IDs
        def on_patient_select(event):
            selected_value = event.new

            # Handle the case when the selection is a patient name
            if selected_value in patient_dict:
                selected_id = patient_dict[selected_value]
                print(
                    f"Debug: Selected patient name '{selected_value}' with ID: {selected_id}")
                self.selected_patient_id = selected_id
            # Handle the case when the selection is already a patient ID
            elif selected_value in id_to_name:
                print(
                    f"Debug: Selected patient directly by ID: {selected_value}")
                self.selected_patient_id = selected_value
            # The selection is neither a valid name nor ID
            else:
                print(
                    f"Debug: Selected value '{selected_value}' not recognized as name or ID")

        patient_select.param.watch(on_patient_select, 'value')

        # Add callback to update data when patient changes
        self.param.watch(self._update_patient_data, 'selected_patient_id')

        # Create patient info card
        def patient_info_card(patient_id):
            print(
                f"Debug: Creating patient info card for patient ID: '{patient_id}'")
            # Always get fresh data
            patient_data = db_query.get_patient_overview(patient_id)
            demographics = patient_data.get('demographics', {})
            print(f"Debug: Patient info card data: {demographics}")

            if not demographics:
                return pn.pane.Markdown("No patient data available")

            # Format dates for display
            birth_date = format_date(demographics.get('birth_date', ''))
            program_start = format_date(
                demographics.get('program_start_date', ''))

            info_text = f"""
            ### {demographics.get('first_name', '')} {demographics.get('last_name', '')}
            
            **ID:** {demographics.get('id', '')}  
            **Gender:** {demographics.get('gender', '')}  
            **Birth Date:** {birth_date}  
            **Ethnicity:** {demographics.get('ethnicity', '')}  
            **Engagement Score:** {demographics.get('engagement_score', '')}  
            **Program Start:** {program_start}
            """

            return pn.pane.Markdown(info_text)

        # Helper function to format dates
        def format_date(date_str):
            """Format date string from 'YYYY-MM-DD 00:00:00' to 'YYYY/MM/DD'"""
            if pd.isna(date_str) or date_str is None:
                return ""
            # Check if date has time component and remove it
            if " " in date_str:
                date_part = date_str.split(" ")[0]
            else:
                date_part = date_str

            # Convert YYYY-MM-DD to YYYY/MM/DD
            if "-" in date_part:
                year, month, day = date_part.split("-")
                return f"{year}/{month}/{day}"

            return date_part

        # Helper function for consistent plot formatting
        def format_plot_time_axis(plot, program_start_date, patient_data):
            """Apply consistent time axis formatting to all plots"""
            logger.info("Formatting plot time axis - using simple settings")

            try:
                # Use only the basic options that are known to work with Curve type
                plot = plot.opts(
                    width=600,
                    height=400,
                    tools=['hover'],
                    xrotation=45,
                    fontscale=1.0,
                    show_grid=True
                )
                logger.info("Successfully applied basic plot formatting")
                return plot
            except Exception as e:
                logger.error(
                    f"Error in format_plot_time_axis: {e}", exc_info=True)
                # Return the original plot if formatting fails
                return plot

        def create_scores_tab(patient_id):
            print(f"Debug: Getting scores for patient ID: '{patient_id}'")
            scores_df = db_query.get_patient_scores(patient_id)
            print(f"Debug: Scores data rows: {len(scores_df)}")
            logger.info(
                f"Scores data for patient {patient_id}: {len(scores_df)} rows")

            if not scores_df.empty:
                logger.info(f"Scores columns: {scores_df.columns.tolist()}")
                logger.info(
                    f"Sample scores data: {scores_df.head(1).to_dict('records')}")

            # Get patient data for program start date
            patient_data = db_query.get_patient_overview(patient_id)
            program_start_date = patient_data.get(
                'demographics', {}).get('program_start_date', None)

            if scores_df.empty:
                return pn.pane.Markdown("No metabolic health scores available")

            # Format dates for display in tables
            scores_df_display = scores_df.copy()
            if 'date' in scores_df_display.columns:
                scores_df_display['date'] = scores_df_display['date'].apply(
                    format_date)

            # For plotting, we need datetime objects
            plot_df = scores_df.copy()
            if 'date' in plot_df.columns:
                # Keep the original date format for conversion to datetime
                plot_df['date'] = pd.to_datetime(plot_df['date'])
                # Sort by date for proper line plotting
                plot_df = plot_df.sort_values('date')
                logger.info(f"Plot data prepared with {len(plot_df)} rows")

            # Original table view (always show this)
            scores_table = pn.widgets.Tabulator(
                scores_df_display,
                sizing_mode='stretch_width',
                show_index=False
            )
            logger.info("Created scores table")

            # Direct plotting approach
            plots = []
            try:
                # Group by date and score_type for plotting
                for score_type in plot_df['score_type'].unique():
                    # Filter data for this score type
                    score_data = plot_df[plot_df['score_type'] == score_type]

                    if not score_data.empty and len(score_data) > 0:
                        logger.info(
                            f"Creating plot for score type: {score_type} with {len(score_data)} points")

                        # Create plot
                        score_plot = score_data.hvplot(
                            x='date',
                            y='score_value',
                            title=f'{score_type.replace("_", " ").title()} Over Time',
                            xlabel='Date',
                            ylabel=f'{score_type.replace("_", " ").title()}',
                            width=600,
                            height=350,
                            grid=True,
                            line_width=2.0
                        )
                        score_plot = format_plot_time_axis(
                            score_plot, program_start_date, patient_data)
                        plots.append(pn.pane.HoloViews(
                            score_plot, sizing_mode='stretch_width'))
                        logger.info(f"Added plot for {score_type}")
            except Exception as e:
                logger.error(f"Error creating score plots: {e}", exc_info=True)
                print(f"Error creating score plots: {e}")

            # Create layout
            logger.info(f"Total plots created: {len(plots)}")
            components = [
                pn.pane.Markdown("### Scores Data"),
                scores_table
            ]

            if plots:
                components.extend([
                    pn.layout.Divider(),
                    pn.pane.Markdown("### Score Trends"),
                    pn.pane.Markdown(
                        "*Click and drag to zoom in, double-click to reset view*"),
                    *plots  # Display plots vertically for better visibility
                ])
                logger.info("Added plots to layout")

            return pn.Column(*components, sizing_mode='stretch_width')

        def create_vitals_tab(patient_id):
            print(f"Debug: Getting vitals for patient ID: '{patient_id}'")
            # Always get the current ID, not a cached version
            current_id = patient_id
            vitals_df = db_query.get_patient_vitals(current_id)
            print(f"Debug: Vitals data rows: {len(vitals_df)}")
            logger.info(
                f"Vitals data for patient {patient_id}: {len(vitals_df)} rows")

            if not vitals_df.empty:
                logger.info(f"Vitals columns: {vitals_df.columns.tolist()}")
                logger.info(
                    f"Sample vitals data: {vitals_df.head(1).to_dict('records')}")

            # Get patient data for program start date
            patient_data = db_query.get_patient_overview(patient_id)
            program_start_date = patient_data.get(
                'demographics', {}).get('program_start_date', None)
            logger.info(f"Program start date: {program_start_date}")

            if vitals_df.empty:
                logger.warning("No vitals data available for plotting")
                return pn.pane.Markdown("No vitals data available")

            # Format dates for display in tables
            vitals_df_display = vitals_df.copy()
            if 'date' in vitals_df_display.columns:
                vitals_df_display['date'] = vitals_df_display['date'].apply(
                    format_date)

            # For plotting, we need datetime objects
            plot_df = vitals_df.copy()
            if 'date' in plot_df.columns:
                # Keep the original date format for conversion to datetime
                plot_df['date'] = pd.to_datetime(plot_df['date'])
                # Sort by date for proper line plotting
                plot_df = plot_df.sort_values('date')
                logger.info(f"Plot data prepared with {len(plot_df)} rows")

            # Only create plots if we have data with dates
            plots = []
            try:
                if not plot_df.empty and 'date' in plot_df.columns and 'weight' in plot_df.columns:
                    # Filter out null values
                    weight_data = plot_df[plot_df['weight'].notnull()]
                    logger.info(
                        f"Weight data points for plotting: {len(weight_data)}")

                    if not weight_data.empty:
                        logger.info("Creating weight plot")
                        weight_plot = weight_data.hvplot(
                            x='date', y='weight',
                            title='Weight Over Time',
                            xlabel='Date', ylabel='Weight (kg)',
                            width=600, height=350,
                            grid=True,
                            line_width=2.0
                        )
                        weight_plot = format_plot_time_axis(
                            weight_plot, program_start_date, patient_data)
                        plots.append(pn.pane.HoloViews(
                            weight_plot, sizing_mode='stretch_width'))
                        logger.info(
                            "Weight plot created and added to plots list")

                if not plot_df.empty and 'date' in plot_df.columns:
                    bp_plots = []

                    # Create systolic plot if data exists
                    if 'sbp' in plot_df.columns:
                        sbp_data = plot_df[plot_df['sbp'].notnull()]
                        logger.info(
                            f"SBP data points for plotting: {len(sbp_data)}")

                        if not sbp_data.empty:
                            logger.info("Creating SBP plot")
                            sbp_plot = sbp_data.hvplot(
                                x='date', y='sbp',
                                title='Blood Pressure Over Time',
                                xlabel='Date', ylabel='mmHg (Systolic)',
                                width=600, height=350,
                                grid=True,
                                line_width=2.0
                            )
                            sbp_plot = format_plot_time_axis(
                                sbp_plot, program_start_date, patient_data)
                            bp_plots.append(sbp_plot)
                            logger.info("SBP plot created")

                    # Create diastolic plot if data exists
                    if 'dbp' in plot_df.columns:
                        dbp_data = plot_df[plot_df['dbp'].notnull()]
                        logger.info(
                            f"DBP data points for plotting: {len(dbp_data)}")

                        if not dbp_data.empty:
                            logger.info("Creating DBP plot")
                            dbp_plot = dbp_data.hvplot(
                                x='date', y='dbp',
                                title='',
                                xlabel='Date', ylabel='mmHg (Diastolic)',
                                width=600, height=350,
                                grid=True,
                                line_width=2.0
                            )
                            dbp_plot = format_plot_time_axis(
                                dbp_plot, program_start_date, patient_data)
                            bp_plots.append(dbp_plot)
                            logger.info("DBP plot created")

                    # Combine BP plots if both exist
                    if len(bp_plots) > 1:
                        logger.info("Combining BP plots")
                        bp_plot = bp_plots[0] * bp_plots[1]
                        plots.append(pn.pane.HoloViews(
                            bp_plot, sizing_mode='stretch_width'))
                        logger.info("Combined BP plot added to plots list")
                    elif len(bp_plots) == 1:
                        logger.info("Adding single BP plot")
                        plots.append(pn.pane.HoloViews(
                            bp_plots[0], sizing_mode='stretch_width'))
                        logger.info("Single BP plot added to plots list")

                logger.info(f"Total plots created: {len(plots)}")
            except Exception as e:
                logger.error(
                    f"Error creating vitals plots: {e}", exc_info=True)
                print(f"Error creating vitals plots: {e}")
                # Continue execution even if plot creation fails

            # Create table view of data
            vitals_table = pn.widgets.Tabulator(
                vitals_df_display,
                sizing_mode='stretch_width',
                show_index=False  # Hide index column for cleaner display
            )
            logger.info("Vitals table created")

            # Create layout with plots if available
            if plots:
                logger.info("Returning layout with plots")
                layout = pn.Column(
                    pn.pane.Markdown("### Vitals Data"),
                    vitals_table,
                    pn.layout.Divider(),
                    pn.pane.Markdown("### Vitals Trends"),
                    pn.pane.Markdown(
                        "*Click and drag to zoom in, double-click to reset view*"),
                    *plots,  # Display plots vertically for better visibility
                    sizing_mode='stretch_width'
                )
                logger.info("Vitals layout created with plots")
                return layout
            else:
                logger.info("Returning layout without plots")
                return pn.Column(
                    pn.pane.Markdown("### Vitals Data"),
                    vitals_table,
                    sizing_mode='stretch_width'
                )

        def create_mental_health_tab(patient_id):
            print(
                f"Debug: Getting mental health data for patient ID: '{patient_id}'")
            # Always get the current ID, not a cached version
            current_id = patient_id
            mh_df = db_query.get_patient_mental_health(current_id)
            print(f"Debug: Mental health data rows: {len(mh_df)}")

            # Get patient data for program start date
            patient_data = db_query.get_patient_overview(patient_id)
            program_start_date = patient_data.get(
                'demographics', {}).get('program_start_date', None)

            if mh_df.empty:
                return pn.pane.Markdown("No mental health data available")

            # Format dates for display in tables
            mh_df_display = mh_df.copy()
            if 'date' in mh_df_display.columns:
                mh_df_display['date'] = mh_df_display['date'].apply(
                    format_date)

            # For plotting, we need datetime objects
            plot_df = mh_df.copy()
            if 'date' in plot_df.columns:
                # Keep the original date format for conversion to datetime
                plot_df['date'] = pd.to_datetime(plot_df['date'])
                # Sort by date for proper line plotting
                plot_df = plot_df.sort_values('date')

            # Create a similar pivot but with assessment_type as rows for display
            try:
                # Sort data by date (descending)
                display_df = mh_df_display.sort_values('date', ascending=False)

                # Create a pivot table with assessment types as rows and dates as columns
                pivot_df = display_df.pivot_table(
                    index='assessment_type',
                    columns='date',
                    values='score',
                    aggfunc='first'  # In case of duplicates, take the first value
                ).reset_index()

                # Format the pivot table for better display
                pivot_df.columns.name = None  # Remove the columns name

                # Create table view of restructured data
                mh_table = pn.widgets.Tabulator(
                    pivot_df,
                    sizing_mode='stretch_width',
                    show_index=False  # Hide index column for cleaner display
                )
            except Exception as e:
                print(f"Error creating mental health pivot table: {e}")
                # If pivot fails, fall back to original table
                mh_table = pn.widgets.Tabulator(
                    mh_df_display,
                    sizing_mode='stretch_width',
                    show_index=False  # Hide index column for cleaner display
                )

            # Try to create plots if we have enough data
            plots = []
            try:
                # Create plots - we need to pivot data since assessment types are rows
                plot_pivot_data = plot_df.pivot_table(
                    index='date', columns='assessment_type', values='score', aggfunc='mean'
                ).reset_index()

                # Need at least one assessment type
                if not plot_pivot_data.empty and len(plot_pivot_data.columns) > 1:
                    # Create individual plots for each assessment type
                    for col in plot_pivot_data.columns:
                        if col != 'date':  # Skip the date column
                            # Create a dataframe with only the data for this assessment type with no nulls
                            assessment_data = plot_pivot_data[[
                                'date', col]].dropna()
                            if not assessment_data.empty:
                                individual_plot = assessment_data.hvplot(
                                    x='date', y=col,
                                    title=f'{col} Score Over Time',
                                    xlabel='Date', ylabel='Score',
                                    width=600, height=350,
                                    grid=True,
                                    line_width=2.0
                                )
                                individual_plot = format_plot_time_axis(
                                    individual_plot, program_start_date, patient_data)
                                plots.append(pn.pane.HoloViews(
                                    individual_plot, sizing_mode='stretch_width'))
            except Exception as e:
                print(f"Error creating mental health plots: {e}")

            # Return layout with or without plots
            if plots:
                return pn.Column(
                    pn.pane.Markdown("### Mental Health Assessments by Type"),
                    mh_table,
                    pn.layout.Divider(),
                    pn.pane.Markdown("### Mental Health Score Trends"),
                    pn.pane.Markdown(
                        "*Click and drag to zoom in, double-click to reset view*"),
                    *plots,  # Display plots vertically for better visibility
                    sizing_mode='stretch_width'
                )
            else:
                # Fall back to table-only view if plot creation fails
                return pn.Column(
                    pn.pane.Markdown("### Mental Health Assessments by Type"),
                    mh_table,
                    sizing_mode='stretch_width'
                )

        def create_labs_tab(patient_id):
            print(f"Debug: Getting lab data for patient ID: '{patient_id}'")
            # Always get the current ID, not a cached version
            current_id = patient_id
            labs_df = db_query.get_patient_labs(current_id)
            print(f"Debug: Lab data rows: {len(labs_df)}")

            # Get patient data for program start date
            patient_data = db_query.get_patient_overview(patient_id)
            program_start_date = patient_data.get(
                'demographics', {}).get('program_start_date', None)

            if labs_df.empty:
                return pn.pane.Markdown("No lab data available")

            # Format dates for display in tables
            labs_df_display = labs_df.copy()
            if 'date' in labs_df_display.columns:
                labs_df_display['date'] = labs_df_display['date'].apply(
                    format_date)

            # For plotting, we need datetime objects
            plot_df = labs_df.copy()
            if 'date' in plot_df.columns:
                # Keep the original date format for conversion to datetime
                plot_df['date'] = pd.to_datetime(plot_df['date'])
                # Sort by date for proper line plotting
                plot_df = plot_df.sort_values('date')

            # Create a line plot showing trends for key lab values over time
            # First, get a list of common lab tests we want to plot
            key_labs = ['Total Cholesterol', 'HDL', 'LDL',
                        'Triglycerides', 'Glucose', 'HbA1c']

            # Filter for only these labs and create a more readable format for plotting
            key_plot_df = plot_df[plot_df['test_name'].isin(key_labs)]

            # Restructure the data to have test_names as rows and dates as columns
            # First, sort by date (descending)
            labs_display_sorted = labs_df_display.sort_values(
                'date', ascending=False)

            # Pivot the data to get test names as rows and dates as columns
            try:
                pivot_df = labs_display_sorted.pivot_table(
                    index='test_name',
                    columns='date',
                    values='value',
                    aggfunc='first'  # In case of duplicates, take the first value
                ).reset_index()

                # Format the pivot table for better display
                pivot_df.columns.name = None  # Remove the columns name

                # Create table view of restructured data
                labs_table = pn.widgets.Tabulator(
                    pivot_df,
                    sizing_mode='stretch_width',
                    show_index=False  # Hide index column for cleaner display
                )
            except Exception as e:
                print(f"Error creating lab pivot table: {e}")
                # If pivot fails, fall back to original table
                labs_table = pn.widgets.Tabulator(
                    labs_df_display,
                    sizing_mode='stretch_width',
                    show_index=False  # Hide index column for cleaner display
                )

            # Create individual plots for each important lab test
            plots = []
            try:
                # Create separate plots for each key lab test
                for lab_test in key_labs:
                    test_data = key_plot_df[key_plot_df['test_name'] == lab_test]

                    if not test_data.empty and len(test_data) > 0:
                        # Convert to clean format for plotting
                        lab_plot = test_data.hvplot(
                            x='date', y='value',
                            title=f'{lab_test} Over Time',
                            xlabel='Date', ylabel=f'{lab_test} Value',
                            height=350, width=600,
                            grid=True,
                            line_width=2.0
                        )
                        lab_plot = format_plot_time_axis(
                            lab_plot, program_start_date, patient_data)
                        plots.append(pn.pane.HoloViews(
                            lab_plot, sizing_mode='stretch_width'))
            except Exception as e:
                print(f"Error creating lab plots: {e}")

            # Return layout with or without plots
            if plots:
                return pn.Column(
                    pn.pane.Markdown("### Lab Results by Test"),
                    labs_table,
                    pn.layout.Divider(),
                    pn.pane.Markdown("### Lab Value Trends"),
                    pn.pane.Markdown(
                        "*Click and drag to zoom in, double-click to reset view*"),
                    *plots,  # Display plots vertically for better visibility
                    sizing_mode='stretch_width'
                )
            else:
                # Fall back to just showing the table
                return pn.Column(
                    pn.pane.Markdown("### Lab Results by Test"),
                    labs_table,
                    sizing_mode='stretch_width'
                )

        # Edit patient button that opens a form
        edit_button = pn.widgets.Button(
            name='Edit Patient',
            button_type='primary',
            width=100
        )

        # Create tabs
        tabs = pn.Tabs(
            ('Vitals', pn.bind(create_vitals_tab, self.param.selected_patient_id)),
            ('Mental Health', pn.bind(
                create_mental_health_tab, self.param.selected_patient_id)),
            ('Lab Results', pn.bind(create_labs_tab, self.param.selected_patient_id)),
            ('Scores', pn.bind(create_scores_tab, self.param.selected_patient_id)),
            dynamic=True
        )

        # Combine everything
        layout = pn.Column(
            title,
            description,
            pn.layout.Divider(),
            pn.Row(patient_select, edit_button),
            pn.layout.Divider(),
            pn.bind(patient_info_card, self.param.selected_patient_id),
            pn.layout.Divider(),
            tabs,
            sizing_mode='stretch_width'
        )

        return layout

    def _update_patient_data(self, *events):
        """Update the patient data when a new patient is selected"""
        print(
            f"Debug: Updating patient data for ID: '{self.selected_patient_id}'")
        self.patient_data = db_query.get_patient_overview(
            self.selected_patient_id)
        print(f"Debug: Patient data received: {self.patient_data}")
