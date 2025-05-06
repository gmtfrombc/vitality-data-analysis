"""
Data Validation Page

This module provides a Panel-based UI for validating and correcting patient data,
identifying missing or problematic measurements.
"""

import os
import logging
import panel as pn
import param
import pandas as pd
import holoviews as hv
import sqlite3
from pathlib import Path

# Optional spinner (Panel >= 1.2). Guard import so older Panel versions still work.
try:
    from panel.indicators import LoadingSpinner  # type: ignore
except ImportError:  # pragma: no cover – spinner not available in older Panel
    LoadingSpinner = None  # fallback handled later

from app.utils.validation_engine import ValidationEngine
from app.utils.rule_loader import initialize_validation_rules

# Import date helpers
from app.utils.date_helpers import format_date_for_display, convert_df_dates

# Set up logging
logger = logging.getLogger(__name__)

# Configure Panel extension
pn.extension()

# Get database path


def get_db_path():
    base_dir = Path(__file__).parent.parent.parent
    return os.path.join(base_dir, "patient_data.db")


# CSS for the page
CSS = """
<style>
.patient-row {
    cursor: pointer;
    transition: background-color 0.2s;
}
.patient-row:hover {
    background-color: #f5f5f5 !important;
}
.summary-card {
    background-color: #f9f9f9;
    border-radius: 5px;
    padding: 15px;
    margin-bottom: 15px;
}
.issue-card {
    background-color: white;
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 15px;
    margin-bottom: 10px;
}
.issue-card-error {
    border-left: 5px solid #dc3545;
}
.issue-card-warning {
    border-left: 5px solid #ffc107;
}
.issue-card-info {
    border-left: 5px solid #17a2b8;
}
.timeline-plot {
    height: 400px;
    width: 100%;
}
</style>
"""


class DataValidationPage(param.Parameterized):
    """
    Panel UI for the Data Validation page.
    """

    # Parameters - renamed to avoid reserved name conflicts
    selected_patient_id = param.String(default=None)
    selected_issue_id = param.Integer(default=None)
    # Renamed from current_correction_value
    correction_value = param.String(default="")
    # Renamed from current_correction_reason
    correction_reason = param.String(default="")
    show_correction_form = param.Boolean(default=False)
    filter_status_value = param.Selector(
        default="open",
        objects=[  # Renamed from filter_status
            "all",
            "open",
            "reviewed",
            "corrected",
            "ignored",
        ],
    )
    filter_severity_value = param.Selector(  # Renamed from filter_severity
        default="all", objects=["all", "error", "warning", "info"]
    )
    filter_type_value = param.Selector(
        default="all",
        objects=[  # Renamed from filter_type
            "all",
            "missing_data",
            "range_check",
            "consistency_check",
        ],
    )
    # Added to replace direct assignment
    correction_field_name = param.String(default="")

    def __init__(self, **params):
        super().__init__(**params)

        self.db_path = get_db_path()
        try:
            self.validation_engine = ValidationEngine(self.db_path)
            logger.info("Validation engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize validation engine: {e}")
            self.validation_engine = None

        # Initialize database with default rules if none exist
        try:
            self._ensure_rules_exist()
        except Exception as e:
            logger.error(f"Error ensuring rules exist: {e}")

        # Loading spinner for patient list refresh
        self.patient_list_spinner = (
            LoadingSpinner(
                value=True, visible=False, width=20, height=20, sizing_mode="fixed"
            )
            if LoadingSpinner
            else None
        )

        # Initialize data structures
        self.patient_df = pd.DataFrame()
        self.patient_issues = []
        self.patient_demographics = pd.DataFrame()
        self.patient_vitals = pd.DataFrame()
        self.status_counts = {}
        self.severity_counts = {}
        self.rule_type_counts = {}
        self.total_issues = 0
        self.patient_count = 0

        # Container that will hold patient rows so we can refresh dynamically
        self.patient_list_column = pn.Column(sizing_mode="stretch_width", width=300)

        # Placeholder for the patient-detail view; will be swapped on patient selection
        self.patient_view_panel = pn.Column(
            pn.pane.Markdown(
                "## Patient Details\n\nSelect a patient from the list to view details"
            ),
            sizing_mode="stretch_width",
        )

        # Load dashboard data
        try:
            self.refresh_data()
        except Exception as e:
            logger.error(f"Error during initial data refresh: {e}")

    def _ensure_rules_exist(self):
        """Make sure validation rules exist in the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if any rules exist
            cursor.execute("SELECT COUNT(*) FROM validation_rules")
            count = cursor.fetchone()[0]

            if count == 0:
                logger.info(
                    "No validation rules found in database. Initializing from default file."
                )
                conn.close()
                initialize_validation_rules(self.db_path)
            else:
                logger.info(f"Found {count} validation rules in database.")
                conn.close()

        except Exception as e:
            logger.error(f"Error checking for existing rules: {e}")
            raise

    def refresh_data(self, event=None):
        """Refresh all data from the database."""
        try:
            self._load_summary_data()
            self._load_patient_list()
            if self.selected_patient_id:
                self._load_patient_issues()
                self._load_patient_timeline()
        except Exception as e:
            logger.error(f"Error refreshing data: {e}")

    def _load_summary_data(self):
        """Load summary statistics for the dashboard."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get counts by status
            cursor.execute(
                "SELECT status, COUNT(*) FROM validation_results GROUP BY status"
            )
            self.status_counts = {row[0]: row[1] for row in cursor.fetchall()}
            self.total_issues = sum(self.status_counts.values())

            # Get counts by severity
            cursor.execute(
                """
                SELECT vru.severity, COUNT(*) 
                FROM validation_results vr
                JOIN validation_rules vru ON vr.rule_id = vru.rule_id
                GROUP BY vru.severity
            """
            )
            self.severity_counts = {row[0]: row[1] for row in cursor.fetchall()}

            # Get counts by rule type
            cursor.execute(
                """
                SELECT vru.rule_type, COUNT(*) 
                FROM validation_results vr
                JOIN validation_rules vru ON vr.rule_id = vru.rule_id
                GROUP BY vru.rule_type
            """
            )
            self.rule_type_counts = {row[0]: row[1] for row in cursor.fetchall()}

            # Get patient count
            cursor.execute("SELECT COUNT(DISTINCT patient_id) FROM validation_results")
            self.patient_count = cursor.fetchone()[0]

            conn.close()

        except Exception as e:
            logger.error(f"Error loading summary data: {e}")
            self.status_counts = {}
            self.severity_counts = {}
            self.rule_type_counts = {}
            self.total_issues = 0
            self.patient_count = 0

    def _load_patient_list(self):
        """Load list of patients with validation issues."""
        try:
            conn = sqlite3.connect(self.db_path)

            # Build query based on current filters
            query = """
                SELECT vr.patient_id, p.first_name, p.last_name, 
                       COUNT(*) as issue_count,
                       SUM(CASE WHEN vr.status = 'open' THEN 1 ELSE 0 END) as open_count,
                       MAX(CASE WHEN vru.severity = 'error' THEN 1 ELSE 0 END) as has_errors
                FROM validation_results vr
                JOIN patients p ON vr.patient_id = p.id
                JOIN validation_rules vru ON vr.rule_id = vru.rule_id
                WHERE 1=1
            """

            params = []

            # Add filters
            if self.filter_status_value != "all":
                query += " AND vr.status = ?"
                params.append(self.filter_status_value)

            if self.filter_severity_value != "all":
                query += " AND vru.severity = ?"
                params.append(self.filter_severity_value)

            if self.filter_type_value != "all":
                query += " AND vru.rule_type = ?"
                params.append(self.filter_type_value)

            # Group and order
            query += """
                GROUP BY vr.patient_id, p.first_name, p.last_name
                ORDER BY open_count DESC, has_errors DESC, issue_count DESC
            """

            # Execute query
            self.patient_df = pd.read_sql_query(query, conn, params=params)

            conn.close()

        except Exception as e:
            logger.error(f"Error loading patient list: {e}")
            self.patient_df = pd.DataFrame(
                columns=[
                    "patient_id",
                    "first_name",
                    "last_name",
                    "issue_count",
                    "open_count",
                    "has_errors",
                ]
            )

    def _refresh_patient_list(self):
        """Reload patient DataFrame and rebuild the visible list."""
        # Show spinner while refreshing
        if self.patient_list_spinner is not None:
            self.patient_list_spinner.visible = True
        self._load_patient_list()

        rows = []
        try:
            for _, row in self.patient_df.iterrows():
                rows.append(self.create_patient_row(row))
        except Exception as exc:
            logger.error("Error rebuilding patient rows: %s", exc)
            rows = [pn.pane.Markdown("Error loading patient list")]

        # Replace children in the container (triggers UI update)
        self.patient_list_column.objects = rows

        # Hide spinner after refresh
        if self.patient_list_spinner is not None:
            self.patient_list_spinner.visible = False

    def _load_patient_issues(self):
        """Load validation issues for the selected patient."""
        if not self.selected_patient_id:
            self.patient_issues = []
            return

        try:
            self.patient_issues = self.validation_engine.get_patient_issues(
                self.selected_patient_id
            )
        except Exception as e:
            logger.error(f"Error loading patient issues: {e}")
            self.patient_issues = []

    def _load_patient_timeline(self):
        """Load timeline data for the selected patient."""
        if not self.selected_patient_id:
            self.patient_demographics = pd.DataFrame()
            self.patient_vitals = pd.DataFrame()
            return

        try:
            # Get patient data
            self.patient_demographics, self.patient_vitals = (
                self.validation_engine.get_patient_data(self.selected_patient_id)
            )

            # Convert dates to datetime using our helper function
            if not self.patient_vitals.empty:
                date_columns = ["date", "measurement_date"]
                self.patient_vitals = convert_df_dates(
                    self.patient_vitals,
                    [col for col in date_columns if col in self.patient_vitals.columns],
                    utc=True,
                )

        except Exception as e:
            logger.error(f"Error loading patient timeline: {e}")
            self.patient_demographics = pd.DataFrame()
            self.patient_vitals = pd.DataFrame()

    def select_patient(self, patient_id):
        """
        Handle patient selection.

        Args:
            patient_id: ID of the selected patient
        """
        self.selected_patient_id = patient_id
        self.selected_issue_id = None
        self.show_correction_form = False
        self._load_patient_issues()
        self._load_patient_timeline()

        # Rebuild the patient-detail panel dynamically
        try:
            new_view = self._build_patient_view()
            self.patient_view_panel.objects = [new_view]
        except Exception as exc:
            logger.error("Error updating patient view: %s", exc)

    def select_issue(self, issue_id):
        """
        Handle issue selection.

        Args:
            issue_id: ID of the selected issue
        """
        self.selected_issue_id = issue_id
        self.show_correction_form = False

    def show_correction(self, result_id, field_name):
        """
        Show the correction form for an issue.

        Args:
            result_id: ID of the validation result
            field_name: Name of the field to correct
        """
        self.selected_issue_id = result_id
        # Update Parameter attributes directly
        self.correction_field_name = field_name
        self.correction_value = ""
        self.correction_reason = ""
        self.show_correction_form = True

        # Re-render patient view with correction form visible
        try:
            self.patient_view_panel.objects = [self._build_patient_view()]
        except Exception as exc:
            logger.error("Error rebuilding patient view after show_correction: %s", exc)

    def submit_correction(self, event=None):
        """Submit a correction for an issue."""
        if not self.selected_issue_id or not self.correction_value:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get information about the issue
            cursor.execute(
                """
                SELECT vr.patient_id, vr.field_name, vr.rule_id
                FROM validation_results vr
                WHERE vr.result_id = ?
            """,
                (self.selected_issue_id,),
            )

            row = cursor.fetchone()
            if not row:
                logger.error(f"Issue not found: {self.selected_issue_id}")
                conn.close()
                return

            patient_id, field_name, rule_id = row

            # Insert correction
            cursor.execute(
                """
                INSERT INTO data_corrections 
                (result_id, patient_id, field_name, table_name, record_id, new_value, applied_by)
                VALUES (?, ?, ?, 'vitals', 0, ?, 'current_user')
            """,
                (self.selected_issue_id, patient_id, field_name, self.correction_value),
            )

            correction_id = cursor.lastrowid

            # Add audit record
            cursor.execute(
                """
                INSERT INTO correction_audit 
                (correction_id, result_id, action_type, action_reason, action_by)
                VALUES (?, ?, 'correction', ?, 'current_user')
            """,
                (correction_id, self.selected_issue_id, self.correction_reason),
            )

            # Update issue status
            cursor.execute(
                """
                UPDATE validation_results
                SET status = 'corrected'
                WHERE result_id = ?
            """,
                (self.selected_issue_id,),
            )

            conn.commit()
            conn.close()

            # Reset form flag and refresh data
            self.show_correction_form = False
            self.refresh_data()

            # Re-render patient view to reflect updated status
            self.patient_view_panel.objects = [self._build_patient_view()]

        except Exception as e:
            logger.error(f"Error submitting correction: {e}")

    def mark_as_reviewed(self, result_id, reason="Reviewed and confirmed as correct"):
        """
        Mark an issue as reviewed.

        Args:
            result_id: ID of the validation result
            reason: Reason for marking as reviewed
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Add audit record
            cursor.execute(
                """
                INSERT INTO correction_audit 
                (result_id, action_type, action_reason, action_by)
                VALUES (?, 'review', ?, 'current_user')
            """,
                (result_id, reason),
            )

            # Update issue status
            cursor.execute(
                """
                UPDATE validation_results
                SET status = 'reviewed'
                WHERE result_id = ?
            """,
                (result_id,),
            )

            conn.commit()
            conn.close()

            # Refresh data
            self.refresh_data()

        except Exception as e:
            logger.error(f"Error marking as reviewed: {e}")

    def validate_patient(self, patient_id=None):
        """
        Run validation on a patient or all patients.

        Args:
            patient_id: ID of the patient to validate, or None for all patients
        """
        if not self.validation_engine:
            logger.error("Validation engine is not initialized")
            return

        try:
            if patient_id:
                logger.info(f"Validating patient: {patient_id}")
                self.validation_engine.validate_patient(patient_id)
            else:
                logger.info("Validating all patients")
                self.validation_engine.validate_all_patients()

            # Refresh data
            self.refresh_data()
        except Exception as e:
            logger.error(f"Error during validation: {e}")

    def create_patient_row(self, row):
        """Create an interactive row (button) representing a patient in the list."""
        try:
            patient_id = row["patient_id"]
            name = f"{row['first_name']} {row['last_name']}"
            # Display issue counts in the button label
            issues_text = f"{row['issue_count']} issues ({row['open_count']} open)"

            button_label = f"{name} — {issues_text}"

            # Choose button colour based on severity (red tint if any errors)
            button_type = "danger" if row.get("has_errors", 0) == 1 else "default"

            patient_button = pn.widgets.Button(
                name=button_label,
                button_type=button_type,
                width_policy="max",  # let the column control the width
                align="start",
                css_classes=["patient-row"],
            )

            # Clicking the button selects the patient and updates the view
            patient_button.on_click(lambda *_: self.select_patient(patient_id))

            return patient_button
        except Exception as e:
            logger.error(f"Error creating patient row: {e}")
            return pn.pane.Markdown("Error loading patient data")

    def create_issue_card(self, issue):
        """Create a card for displaying a validation issue."""
        try:
            result_id = issue["result_id"]
            field_name = issue.get("field_name", "")
            description = issue.get("issue_description", "No description")
            status = issue.get("status", "open")
            severity = issue.get("severity", "info")
            detected_at = issue.get("detected_at", "")

            # Format date for display
            try:
                detected_date = format_date_for_display(detected_at)
            except Exception:
                detected_date = detected_at

            # Create card layout
            title = f"Issue with {field_name}" if field_name else "Validation Issue"
            title_md = pn.pane.Markdown(f"### {title}", sizing_mode="stretch_width")

            description_md = pn.pane.Markdown(description, sizing_mode="stretch_width")

            status_md = pn.pane.Markdown(
                f"**Status:** {status} | **Severity:** {severity} | **Detected:** {detected_date}",
                sizing_mode="stretch_width",
            )

            # Create buttons
            correct_button = pn.widgets.Button(
                name="Correct", button_type="primary", width=100
            )
            review_button = pn.widgets.Button(
                name="Mark as Reviewed", button_type="success", width=150
            )

            # Button handlers
            def correct_handler(event, r_id=result_id, f_name=field_name):
                self.show_correction(r_id, f_name)

            def review_handler(event, r_id=result_id):
                self.mark_as_reviewed(r_id)

            correct_button.on_click(correct_handler)
            review_button.on_click(review_handler)

            buttons = pn.Row(correct_button, review_button, sizing_mode="fixed")

            # Combine elements into card
            card = pn.Column(
                title_md,
                description_md,
                status_md,
                buttons,
                sizing_mode="stretch_width",
                css_classes=["issue-card", f"issue-card-{severity}"],
            )

            return card
        except Exception as e:
            logger.error(f"Error creating issue card: {e}")
            return pn.pane.Markdown("Error loading issue")

    def create_timeline_plot(self):
        """Create a timeline plot of patient measurements."""
        try:
            if self.patient_vitals.empty:
                return pn.pane.Markdown("No data available for timeline visualization")

            # Ensure dates are datetime - use utc=False to keep tz-naive
            date_columns = ["date", "measurement_date"]
            vitals_with_dates = convert_df_dates(
                self.patient_vitals,
                [col for col in date_columns if col in self.patient_vitals.columns],
                utc=False,
            )

            # Make a copy to avoid modifying the original data
            plot_data = vitals_with_dates.copy()

            # Filter out rows with invalid dates
            if "date" in plot_data.columns:
                plot_data = plot_data.dropna(subset=["date"])
                # Ensure dates are sorted
                plot_data = plot_data.sort_values("date")

            # Create holoviews dataset
            try:
                # Get numeric columns for plotting
                numeric_cols = plot_data.select_dtypes(
                    include=["number"]
                ).columns.tolist()
                numeric_cols = [
                    col
                    for col in numeric_cols
                    if col not in ["patient_id", "id", "vital_id"]
                ]

                if (
                    not numeric_cols
                    or plot_data.empty
                    or "date" not in plot_data.columns
                ):
                    return pn.pane.Markdown(
                        "No suitable data for timeline visualization"
                    )

                # Create plot with error handling and additional logging
                try:
                    # Log the data we're plotting to help debug
                    logger.info(f"Creating timeline plot with {len(plot_data)} rows")
                    logger.info(f"Date column type: {plot_data['date'].dtype}")

                    # Create curves one by one and handle errors for each individually
                    curves = []
                    for col in numeric_cols:
                        try:
                            # Filter out NaN values for this column
                            col_data = plot_data[["date", col]].dropna()
                            if not col_data.empty:
                                try:
                                    # Create a curve using the filtered data
                                    curve = hv.Curve(col_data, "date", col, label=col)
                                    curves.append(curve)
                                except Exception as curve_e:
                                    logger.error(
                                        f"Error creating curve from filtered data for {col}: {curve_e}"
                                    )
                        except Exception as e:
                            logger.error(f"Error preparing data for column {col}: {e}")

                    if not curves:
                        return pn.pane.Markdown(
                            "No valid data for timeline visualization"
                        )

                    # Combine curves into overlay
                    overlay = hv.Overlay(curves)

                    # Set plot options
                    plot = overlay.opts(
                        width=800,
                        height=400,
                        title="Patient Measurements Timeline",
                        xlabel="Date",
                        ylabel="Value",
                        legend_position="right",
                        tools=["hover"],
                    )

                    return pn.pane.HoloViews(plot, sizing_mode="stretch_width")

                except Exception as e:
                    logger.error(f"Error creating HoloViews plot: {e}")
                    return pn.pane.Markdown(f"Error creating visualization: {str(e)}")

            except Exception as e:
                logger.error(f"Error preparing timeline data: {e}")
                return pn.pane.Markdown("Error preparing timeline data")

        except Exception as e:
            logger.error(f"Timeline plot creation failed: {e}")
            # Provide a fallback view with raw data
            try:
                # Create a simple table of the most recent measurements as fallback
                if not self.patient_vitals.empty:
                    recent_data = self.patient_vitals.sort_values(
                        "date", ascending=False
                    ).head(5)
                    return pn.Column(
                        pn.pane.Markdown(
                            "## Recent Measurements (Timeline visualization failed)"
                        ),
                        pn.pane.DataFrame(recent_data, sizing_mode="stretch_width"),
                    )
            except Exception:
                pass

            return pn.pane.Markdown("Failed to create timeline visualization")

    def _build_patient_view(self):
        """Constructs the right-hand patient detail pane based on current selection."""
        if not self.selected_patient_id:
            return pn.pane.Markdown(
                "## Patient Details\n\nSelect a patient from the list to view details"
            )

        # Header with name (if demographics loaded)
        if not self.patient_demographics.empty:
            name = f"{self.patient_demographics['first_name'].iloc[0]} {self.patient_demographics['last_name'].iloc[0]}"
            header = pn.pane.Markdown(f"## Patient: {name}")
        else:
            header = pn.pane.Markdown("## Patient Details")

        timeline_plot = self.create_timeline_plot()

        # Issue cards
        cards = [self.create_issue_card(issue) for issue in self.patient_issues]
        issue_list = pn.Column(
            "### Validation Issues", *cards, sizing_mode="stretch_width"
        )

        # Correction form
        if self.show_correction_form:
            new_value_input = pn.widgets.TextInput(
                name="New Value", value=self.correction_value
            )
            reason_input = pn.widgets.TextAreaInput(
                name="Reason for Correction", value=self.correction_reason
            )

            # Bind inputs to param values
            new_value_input.param.watch(
                lambda e: setattr(self, "correction_value", e.new), "value"
            )
            reason_input.param.watch(
                lambda e: setattr(self, "correction_reason", e.new), "value"
            )

            correction_form = pn.Column(
                "### Correction Form",
                new_value_input,
                reason_input,
                pn.Row(
                    pn.widgets.Button(
                        name="Submit",
                        button_type="primary",
                        width=100,
                        on_click=lambda _: self.submit_correction(),
                    ),
                    pn.widgets.Button(
                        name="Cancel",
                        button_type="default",
                        width=100,
                        width_policy="fit",
                        on_click=lambda _: self._cancel_correction(),
                    ),
                ),
                sizing_mode="stretch_width",
            )
        else:
            correction_form = None

        components = [header, timeline_plot, issue_list]
        if correction_form:
            components.append(correction_form)

        return pn.Column(*components, sizing_mode="stretch_width")

    def _cancel_correction(self):
        """Hide correction form without making changes."""
        self.show_correction_form = False
        # Rebuild patient view to hide the form
        try:
            self.patient_view_panel.objects = [self._build_patient_view()]
        except Exception as exc:
            logger.error("Error rebuilding patient view on cancel: %s", exc)

    def get_layout(self):
        """Generate the complete UI layout."""
        try:
            # Dashboard header
            header_title = pn.pane.Markdown(
                "# Data Validation Dashboard", sizing_mode="stretch_width"
            )

            validation_button = pn.widgets.Button(
                name="Run Validation", button_type="primary"
            )
            validation_button.on_click(lambda event: self.validate_patient())

            refresh_button = pn.widgets.Button(
                name="Refresh Data", button_type="default"
            )
            refresh_button.on_click(lambda event: self.refresh_data())

            header = pn.Row(
                header_title,
                validation_button,
                refresh_button,
                sizing_mode="stretch_width",
            )

            # Summary cards
            status_summary = pn.pane.Markdown(
                f"""
                ### Data Quality Summary
                
                **Total Issues:** {self.total_issues}  
                **Patients Affected:** {self.patient_count}
                
                | Status | Count |
                |--------|-------|
                | Open | {self.status_counts.get('open', 0)} |
                | Reviewed | {self.status_counts.get('reviewed', 0)} |
                | Corrected | {self.status_counts.get('corrected', 0)} |
                | Ignored | {self.status_counts.get('ignored', 0)} |
                
                **Errors:** {self.severity_counts.get('error', 0)}  
                **Warnings:** {self.severity_counts.get('warning', 0)}  
                **Info:** {self.severity_counts.get('info', 0)}
                """,
                css_classes=["summary-card"],
                sizing_mode="stretch_width",
            )

            # Filter controls
            status_select = pn.widgets.Select(
                name="Status",
                options=["all", "open", "reviewed", "corrected", "ignored"],
                value=self.filter_status_value,
            )
            severity_select = pn.widgets.Select(
                name="Severity",
                options=["all", "error", "warning", "info"],
                value=self.filter_severity_value,
            )
            type_select = pn.widgets.Select(
                name="Rule Type",
                options=["all", "missing_data", "range_check", "consistency_check"],
                value=self.filter_type_value,
            )

            def update_filters(event):
                """Update filter parameters and refresh patient list."""
                # Update the Parameterized attributes directly
                self.filter_status_value = status_select.value
                self.filter_severity_value = severity_select.value
                self.filter_type_value = type_select.value

                # Reload patient list with new filters
                self._refresh_patient_list()

                logger.info(
                    "Filters applied – status=%s, severity=%s, type=%s",
                    self.filter_status_value,
                    self.filter_severity_value,
                    self.filter_type_value,
                )

            filter_button = pn.widgets.Button(
                name="Apply Filters", button_type="primary"
            )
            filter_button.on_click(update_filters)

            filters = pn.Row(
                pn.Column(
                    "### Filter Issues",
                    status_select,
                    severity_select,
                    type_select,
                    filter_button,
                ),
                sizing_mode="fixed",
                width=300,
            )

            # Build initial patient list into the container if it's empty
            if not self.patient_list_column.objects:
                self._refresh_patient_list()

            patient_list = pn.Column(
                "### Patients with Issues",
                (
                    pn.Row(
                        self.patient_list_spinner,
                        self.patient_list_column,
                        sizing_mode="stretch_width",
                    )
                    if self.patient_list_spinner
                    else self.patient_list_column
                ),
                sizing_mode="stretch_width",
                width=300,
            )

            # Set up patient view layout
            if self.selected_patient_id and not self.patient_demographics.empty:
                patient_name = f"{self.patient_demographics['first_name'].iloc[0]} {self.patient_demographics['last_name'].iloc[0]}"
                patient_header = pn.pane.Markdown(
                    f"## Patient: {patient_name}", sizing_mode="stretch_width"
                )
            else:
                patient_header = pn.pane.Markdown(
                    "## Patient Details", sizing_mode="stretch_width"
                )

            # Timeline plot
            timeline_plot = (
                self.create_timeline_plot()
                if self.selected_patient_id
                else pn.pane.Markdown("Select a patient to view timeline")
            )

            # Issue list
            issue_cards = []
            if self.selected_patient_id:
                for issue in self.patient_issues:
                    issue_cards.append(self.create_issue_card(issue))

            issue_list = pn.Column(
                "### Validation Issues", *issue_cards, sizing_mode="stretch_width"
            )

            # Correction form
            correction_form = pn.Column(
                "### Correction Form",
                pn.widgets.TextInput(name="New Value", value=self.correction_value),
                pn.widgets.TextAreaInput(
                    name="Reason for Correction", value=self.correction_reason
                ),
                pn.Row(
                    pn.widgets.Button(name="Submit", button_type="primary", width=100),
                    pn.widgets.Button(name="Cancel", button_type="default", width=100),
                ),
                visible=self.show_correction_form,
            )

            # Bind correction form widgets to parameters
            def bind_correction_value(target, event):
                self.param.correction_value.value = event.new

            def bind_correction_reason(target, event):
                self.param.correction_reason.value = event.new

            # Get widgets by index for binding
            correction_form[1].param.watch(bind_correction_value, "value")
            correction_form[2].param.watch(bind_correction_reason, "value")

            # Set up button handlers
            def submit_correction_wrapper(event):
                self.submit_correction()

            def cancel_correction(event):
                self.param.show_correction_form.value = False

            correction_form[3][0].on_click(submit_correction_wrapper)
            correction_form[3][1].on_click(cancel_correction)

            # Build / update patient view via helper for reuse
            patient_view = self._build_patient_view()
            # Replace objects inside the persistent panel (keeps reference stable)
            self.patient_view_panel.objects = [patient_view]

            # Overall layout
            dashboard_layout = pn.Row(
                pn.Column(
                    status_summary,
                    filters,
                    patient_list,
                    sizing_mode="fixed",
                    width=400,
                ),
                self.patient_view_panel,
                sizing_mode="stretch_width",
            )

            # Complete layout
            layout = pn.Column(header, dashboard_layout, sizing_mode="stretch_width")

            return layout
        except Exception as e:
            logger.error(f"Error building layout: {e}")
            return pn.Column(
                pn.pane.Markdown("# Data Validation Dashboard"),
                pn.pane.Markdown(f"Error loading dashboard: {str(e)}"),
                pn.widgets.Button(
                    name="Refresh",
                    button_type="primary",
                    on_click=lambda event: self.refresh_data(),
                ),
            )


# Create instance with exception handling
try:
    validation_page = DataValidationPage()
    logger.info("DataValidationPage instance created successfully")
except Exception as e:
    logger.error(f"Error creating DataValidationPage instance: {e}")
    validation_page = None


def get_page():
    """Return the complete data validation page."""
    try:
        if validation_page:
            return pn.pane.HTML(CSS, sizing_mode="fixed") + validation_page.get_layout()
        else:
            return pn.Column(
                pn.pane.HTML(CSS, sizing_mode="fixed"),
                pn.pane.Markdown("# Error Loading Data Validation"),
                pn.pane.Markdown(
                    "Unable to initialize validation page. Check logs for details."
                ),
            )
    except Exception as e:
        logger.error(f"Error in get_page(): {e}")
        return pn.Column(
            pn.pane.HTML(CSS, sizing_mode="fixed"),
            pn.pane.Markdown("# Error Loading Data Validation"),
            pn.pane.Markdown(f"Unexpected error: {str(e)}"),
        )
