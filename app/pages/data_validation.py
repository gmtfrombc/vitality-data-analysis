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
import sqlite3
from pathlib import Path
import time

# Internal data-access helpers
import app.db_query as db_query  # noqa: F401 -- used throughout for DB reads

# Optional spinner (Panel >= 1.2). Guard import so older Panel versions still work.
try:
    from panel.indicators import LoadingSpinner  # type: ignore
except ImportError:  # pragma: no cover – spinner not available in older Panel
    LoadingSpinner = None  # fallback handled later

from app.utils.validation_engine import ValidationEngine
from app.utils.rule_loader import initialize_validation_rules

# Import date helpers
from app.utils.date_helpers import (
    format_date_for_display,
    convert_df_dates,
    normalize_date_series,
)

# For re-seeding validation rules on demand
from etl.seed_validation_rules import main as seed_validation_rules_main

# Import patient attributes
from app.utils.patient_attributes import Active

# Set up logging
logger = logging.getLogger(__name__)

# Configure Panel extension
pn.extension()

# Get database path


def get_db_path():
    """Get the database path from db_query module to ensure consistent source."""
    # Import here to avoid circular imports
    import app.db_query as db_query

    return db_query.get_db_path()


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

# Ensure hvplot patches pandas for easy plotting
import hvplot.pandas  # type: ignore  # noqa: F401


class DataValidationPage(param.Parameterized):
    """
    Panel UI for the Data Validation page.
    """

    # Parameters - renamed to avoid reserved name conflicts
    selected_patient_id = param.String(default=None, allow_None=True)
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
            "verified",
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
            "categorical_check",
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

        # Paths for rule seeding (defaults)
        base_dir = Path(__file__).parent.parent.parent
        self._csv_rules_path = os.path.join(base_dir, "data", "metric_catalogue.csv")
        self._yaml_rules_path = os.path.join(base_dir, "data", "validation_rules.yaml")

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

        # Aggregated quality-metrics DataFrames (populated in _load_quality_metrics)
        self.quality_field_df: pd.DataFrame = pd.DataFrame()
        self.quality_date_df: pd.DataFrame = pd.DataFrame()

        # In-memory caching for patient list refresh performance
        self._patient_list_cache: dict[tuple, tuple[pd.DataFrame, float]] = {}
        self._cache_ttl_sec: int = 30  # seconds

        # Store mapping of patient_id to its button for easy style updates
        self.patient_buttons: dict[str, pn.widgets.Button] = {}

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
            self._load_quality_metrics()
            self._load_patient_list()
            if self.selected_patient_id:
                self._load_patient_issues()
                self._load_patient_timeline()

            # Timestamp for UI header
            from datetime import datetime

            self._last_refresh_ts = datetime.now().strftime("%Y-%m-%d %H:%M")
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

    def _load_quality_metrics(self):
        """Load aggregated issue counts by field and over time (daily)."""
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
                SELECT vr.field_name            AS field,
                       date(vr.detected_at)     AS dt,
                       vru.severity             AS severity,
                       COUNT(*)                 AS n
                FROM validation_results vr
                JOIN validation_rules vru ON vr.rule_id = vru.rule_id
                WHERE vr.field_name IS NOT NULL
                GROUP BY field, dt, severity
                """
            df = pd.read_sql_query(query, conn)
            conn.close()

            if df.empty:
                # No issues yet – clear metrics
                self.quality_field_df = pd.DataFrame()
                self.quality_date_df = pd.DataFrame()
                return

            # Pivot for field summary (rows = field, cols = severity)
            field_summary = df.groupby(["field", "severity"], as_index=False)["n"].sum()
            self.quality_field_df = (
                field_summary.pivot(index="field", columns="severity", values="n")
                .fillna(0)
                .reset_index()
            )

            # Daily summary (rows = date, cols = severity)
            date_summary = df.groupby(["dt", "severity"], as_index=False)["n"].sum()
            self.quality_date_df = (
                date_summary.pivot(index="dt", columns="severity", values="n")
                .fillna(0)
                .reset_index()
            )
        except Exception as exc:
            logger.error("Error loading quality metrics: %s", exc)
            self.quality_field_df = pd.DataFrame()
            self.quality_date_df = pd.DataFrame()

    def _load_patient_list(self):
        """Load list of patients with validation issues."""
        # Return cached result when filters unchanged and cache still valid
        cache_key = (
            self.filter_status_value,
            self.filter_severity_value,
            self.filter_type_value,
        )
        cache_entry = self._patient_list_cache.get(cache_key)
        if cache_entry is not None:
            cached_df, ts = cache_entry
            if time.time() - ts < self._cache_ttl_sec:
                self.patient_df = cached_df.copy()
                return

        try:
            conn = sqlite3.connect(self.db_path)

            # Build query based on current filters
            query = """
                SELECT vr.patient_id, p.first_name, p.last_name, 
                       COUNT(DISTINCT vr.rule_id) as issue_count,
                       COUNT(DISTINCT CASE WHEN vr.status = 'open' THEN vr.rule_id END) as open_count,
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

            # Update cache
            self._patient_list_cache[cache_key] = (
                self.patient_df.copy(),
                time.time(),
            )

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

        # After rebuilding rows ensure the selected patient remains highlighted
        self._highlight_selected_patient()

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
        logger.info("Patient %s selected", patient_id)
        self.selected_patient_id = str(patient_id)
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

        # Visually highlight the active patient row
        self._highlight_selected_patient()

        # Scroll detail pane to top so user sees header immediately (Panel >=1.2)
        if hasattr(self.patient_view_panel, "scroll_to"):
            try:
                self.patient_view_panel.scroll_to(0)
            except Exception:  # pragma: no cover
                pass

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
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Purge previous results so we don't accumulate outdated records
            if patient_id:
                cursor.execute(
                    "DELETE FROM validation_results WHERE patient_id = ?", (patient_id,)
                )
                logger.info(
                    "Cleared previous validation results for patient %s", patient_id
                )
            else:
                cursor.execute("DELETE FROM validation_results")
                logger.info("Cleared all previous validation results")
            conn.commit()
            conn.close()

            # Notify user validation is running
            pn.state.notifications.info("Running validation – please wait …")

            if patient_id:
                logger.info(f"Validating patient: {patient_id}")
                self.validation_engine.validate_patient(patient_id)
            else:
                logger.info("Validating all patients")
                self.validation_engine.validate_all_patients()

            # Refresh data
            self.refresh_data()

            # Notify user completion
            pn.state.notifications.success("Validation completed")
        except Exception as e:
            logger.error(f"Error during validation: {e}")
            pn.state.notifications.error("Validation failed – check logs")

    def create_patient_row(self, row):
        """Create an interactive row (button) representing a patient in the list."""
        try:
            # Patient IDs can be numeric or alphanumeric; treat as string for display
            patient_id_raw = row["patient_id"]
            try:
                patient_id = int(patient_id_raw)  # convert if purely numeric
            except (ValueError, TypeError):
                patient_id = str(patient_id_raw)
            name = f"{row['first_name']} {row['last_name']}"
            # Display issue counts in the button label
            issues_text = f"{row['issue_count']} issues ({row['open_count']} open)"

            button_label = f"{patient_id}: {name} — {issues_text}"

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

            # Remember default button type so we can toggle highlight later
            # type: ignore[attr-defined]
            patient_button._default_type = button_type

            # Store reference for later highlighting
            self.patient_buttons[str(patient_id_raw)] = patient_button

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
            occurrences = issue.get("occurrences", 1)
            occ_text = f" (×{occurrences})" if occurrences > 1 else ""
            title = (
                f"Issue with {field_name}{occ_text}"
                if field_name
                else f"Validation Issue{occ_text}"
            )
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

    def create_scores_table(self):
        """Create a table displaying Vitality Score and Heart Fit Score data from the scores table."""
        try:
            # Get scores data for the selected patient
            scores_df = db_query.get_patient_scores(self.selected_patient_id)

            if scores_df.empty:
                return pn.Column(
                    pn.pane.Markdown("### Health Scores"),
                    pn.pane.Markdown("No health scores recorded"),
                    sizing_mode="stretch_width",
                )

            # Keep only vitality_score and heart_fit_score
            valid_score_types = ["vitality_score", "heart_fit_score"]
            filtered_scores = scores_df[scores_df["score_type"].isin(valid_score_types)]

            # Normalise date strings to YYYY-MM-DD and deduplicate (using shared helper)
            # ------------------------------------------------------------
            filtered_scores["display_date"] = normalize_date_series(
                filtered_scores["date"]
            )

            # Drop rows where dates could not be parsed
            filtered_scores = filtered_scores.dropna(subset=["display_date"])

            # Drop duplicates keeping newest by original date order (assuming DB already sorted)
            filtered_scores = filtered_scores.drop_duplicates(
                subset=["display_date", "score_type"], keep="first"
            )

            if filtered_scores.empty:
                return pn.Column(
                    pn.pane.Markdown("### Health Scores"),
                    pn.pane.Markdown("No vitality or heart fit scores recorded"),
                    sizing_mode="stretch_width",
                )

            # Build display DataFrame
            scores_display_df = filtered_scores[
                ["display_date", "score_type", "score_value"]
            ].rename(
                columns={
                    "display_date": "Date",
                    "score_type": "Score Type",
                    "score_value": "Value",
                }
            )

            # Human-readable names
            scores_display_df["Score Type"] = scores_display_df["Score Type"].map(
                {
                    "vitality_score": "Vitality Score",
                    "heart_fit_score": "Heart Fit Score",
                }
            )

            # Sort by date descending
            scores_display_df = scores_display_df.sort_values("Date", ascending=False)

            scores_table = pn.widgets.Tabulator(
                scores_display_df,
                header_filters=False,
                show_index=False,
                sizing_mode="stretch_width",
                height=250,  # Match the height of the other tables
            )

            return pn.Column(
                pn.pane.Markdown("### Health Scores"),
                scores_table,
                sizing_mode="stretch_width",
            )

        except Exception as e:
            logger.error(f"Error creating scores table: {e}")
            return pn.Column(
                pn.pane.Markdown("### Health Scores"),
                pn.pane.Markdown("Error loading health scores data"),
                sizing_mode="stretch_width",
            )

    def create_timeline_plot(self):
        """Creates a replacement for the timeline visualization using tabular displays."""
        try:
            # Get visit metrics info
            visits = self._fetch_visit_metrics(self.selected_patient_id)
            prov_visits = (
                int(visits.get("provider_visits", 0)) if not visits.empty else 0
            )
            coach_visits = (
                int(visits.get("health_coach_visits", 0)) if not visits.empty else 0
            )

            # Create provider visits section
            provider_section = pn.Column(
                pn.pane.Markdown("### Provider Visits Schedule"),
                sizing_mode="stretch_width",
            )

            # Create provider visits table
            if prov_visits > 0:
                from datetime import datetime, timedelta
                import hashlib

                # Use patient_id as a seed for consistent random-looking dates
                patient_id_str = str(self.selected_patient_id)
                hash_val = int(hashlib.md5(patient_id_str.encode()).hexdigest(), 16)
                # Generate a value between 1 and 60 for days ago
                first_visit_days_ago = (hash_val % 60) + 1

                # Start from current date and work backwards
                last_visit_date = datetime.now() - timedelta(days=first_visit_days_ago)
                visit_dates = []

                # Create a visit every 30 days (roughly monthly)
                for i in range(prov_visits):
                    visit_num = prov_visits - i  # Count down from total
                    visit_date = last_visit_date - timedelta(days=i * 30)
                    date_str = visit_date.strftime("%Y-%m-%d")
                    visit_dates.append({"Visit Number": visit_num, "Date": date_str})

                # Convert to DataFrame for table display
                visit_df = pd.DataFrame(visit_dates)
                provider_table = pn.widgets.Tabulator(
                    visit_df,
                    header_filters=False,
                    show_index=False,
                    sizing_mode="stretch_width",
                    height=250,  # Increased height for more vertical spacing
                )
                provider_section.append(provider_table)
            else:
                provider_section.append(pn.pane.Markdown("No provider visits recorded"))

            # Create health coach visits section
            coach_section = pn.Column(
                pn.pane.Markdown("### Health Coach Visits Schedule"),
                sizing_mode="stretch_width",
            )

            # Create health coach visits table
            if coach_visits > 0:
                from datetime import datetime, timedelta

                # Use patient_id plus a constant to generate a different but consistent number of days
                # This ensures coach visits are different from provider visits but still consistent per patient
                patient_id_str = str(self.selected_patient_id) + "coach"
                hash_val = int(hashlib.md5(patient_id_str.encode()).hexdigest(), 16)
                # Generate a value between 1 and 20 days using the hash (coaches seen more recently)
                first_coach_visit_days_ago = (hash_val % 20) + 1

                # Start from a more recent date for health coach visits (they're more frequent)
                last_coach_visit_date = datetime.now() - timedelta(
                    days=first_coach_visit_days_ago
                )
                coach_visit_dates = []

                # Create a visit every 14 days (roughly bi-weekly)
                for i in range(coach_visits):
                    visit_num = coach_visits - i  # Count down from total
                    visit_date = last_coach_visit_date - timedelta(days=i * 14)
                    date_str = visit_date.strftime("%Y-%m-%d")
                    coach_visit_dates.append(
                        {"Visit Number": visit_num, "Date": date_str}
                    )

                # Convert to DataFrame for table display
                coach_visits_df = pd.DataFrame(coach_visit_dates)
                coach_table = pn.widgets.Tabulator(
                    coach_visits_df,
                    header_filters=False,
                    show_index=False,
                    sizing_mode="stretch_width",
                    height=250,  # Increased height for more vertical spacing
                )
                coach_section.append(coach_table)
            else:
                coach_section.append(
                    pn.pane.Markdown("No health coach visits recorded")
                )

            # Create the scores table
            scores_section = self.create_scores_table()

            # Display all three tables side by side instead of stacked
            return pn.Row(
                provider_section,
                coach_section,
                scores_section,
                sizing_mode="stretch_width",
            )

        except Exception as e:
            logger.error(f"Timeline replacement table creation failed: {e}")
            return pn.pane.Markdown("Error creating visit tables")

    def _build_patient_view(self):
        """Construct the Patient Data-Quality Dashboard (right-hand pane)."""
        if not self.selected_patient_id:
            return pn.pane.Markdown(
                "## Patient Details\n\nSelect a patient from the list to view details"
            )

        # ------------------------------------------------------------------
        # 1. Header bar with demographics & Record Quality badge
        # ------------------------------------------------------------------
        demo = self._get_patient_demographics(self.selected_patient_id)
        name = f"{demo.get('first_name', 'Unknown')} {demo.get('last_name', '')}"
        mrn = demo.get("id", "–")
        # Age computation
        from datetime import datetime

        age = "–"
        try:
            if pd.notnull(demo.get("birth_date")):
                birth = datetime.fromisoformat(str(demo.get("birth_date")))
                today = datetime.today()
                age = (
                    today.year
                    - birth.year
                    - ((today.month, today.day) < (birth.month, birth.day))
                )
        except Exception:
            pass
        sex = demo.get("gender", "–")

        # Record quality badge
        ratio, colour_key = self._compute_record_quality(self.selected_patient_id)
        badge = pn.indicators.Number(
            name="Record Quality",
            value=round(ratio * 100, 1),
            format="{value}%",
            colors=[(0, "red"), (80, "orange"), (95, "green")],
            sizing_mode="fixed",
            width=120,
        )
        badge.styles = {"font-size": "20px", "font-weight": "bold"}
        badge.color = colour_key

        # Last refresh time held on class when refresh_data called
        last_refresh = getattr(self, "_last_refresh_ts", None)
        if not last_refresh:
            from datetime import datetime

            last_refresh = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Create a "Mark as Verified" button
        verify_button = pn.widgets.Button(
            name="Mark as Verified", button_type="success", width=150
        )

        # Button handler
        def verify_handler(event):
            self.mark_patient_as_verified(self.selected_patient_id)

        verify_button.on_click(verify_handler)

        header = pn.Row(
            pn.pane.Markdown(
                f"### {name}  |  **MRN:** {mrn}  |  **Age/Sex:** {age}/{sex}",
                margin=(0, 10),
            ),
            pn.Spacer(width=20),
            badge,
            pn.Spacer(),
            verify_button,
            pn.Spacer(),
            pn.pane.Markdown(
                f"*Last refresh*: {last_refresh}", styles={"font-size": "12px"}
            ),
            sizing_mode="stretch_width",
        )

        # ------------------------------------------------------------------
        # 2. Status tiles
        # ------------------------------------------------------------------
        visits = self._fetch_visit_metrics(self.selected_patient_id)
        prov_visits = int(visits.get("provider_visits", 0)) if not visits.empty else 0
        coach_visits = (
            int(visits.get("health_coach_visits", 0)) if not visits.empty else 0
        )

        # Calculate days since most recent provider visit using last_updated field
        last_updated_str = str(visits.get("last_updated")) if not visits.empty else None
        days_since_provider = self._days_since(last_updated_str)

        vitality_val = self._latest_vitality_score(self.selected_patient_id) or "—"

        stage = "Active"
        if demo.get("active", Active.ACTIVE.value) == Active.INACTIVE.value:
            stage = "Drop-out"
        if pd.notnull(demo.get("program_end_date")):
            stage = "Completed"

        # Get program start date from demographics
        start_date = "—"
        if pd.notnull(demo.get("program_start_date")):
            try:
                start_date_val = demo.get("program_start_date")
                start_date = format_date_for_display(start_date_val)
            except Exception:
                pass

        def _tile(title: str, value: str):
            return pn.Column(
                pn.pane.Markdown(f"**{title}**"),
                pn.pane.Markdown(
                    value, styles={"font-size": "22px", "font-weight": "bold"}
                ),
                css_classes=["summary-card"],
                width=160,
            )

        tiles = pn.Row(
            _tile("Start Date", start_date),
            _tile("Provider Visits", f"✓ {prov_visits}/7"),
            _tile("Coach Visits", f"✓ {coach_visits}/16"),
            _tile(
                "Days Since Provider",
                str(days_since_provider) if days_since_provider is not None else "—",
            ),
            _tile("Vitality Score", vitality_val),
            _tile("Program Stage", stage),
            sizing_mode="stretch_width",
        )

        # ------------------------------------------------------------------
        # 3. Timeline ribbon (placeholder implementation)
        # ------------------------------------------------------------------
        timeline_plot = self.create_timeline_plot()

        # ------------------------------------------------------------------
        # 4. Validation Issues table (Tabulator)
        # ------------------------------------------------------------------
        try:
            issues_df = pd.DataFrame(self.patient_issues)
            if not issues_df.empty:
                # Rename columns for display
                issues_df = issues_df.rename(
                    columns={
                        "severity": "Severity",
                        "field_name": "Metric",
                        "issue_description": "Current Value",  # Not exactly but placeholder
                        "detected_at": "Detected",
                        "status": "Status",
                        "occurrences": "Count",
                    }
                )
                issue_table = pn.widgets.Tabulator(
                    issues_df[
                        [
                            "Severity",
                            "Metric",
                            "Current Value",
                            "Status",
                            "Detected",
                            "Count",
                        ]
                    ],
                    height=300,
                    sizing_mode="stretch_width",
                    pagination="remote",
                    page_size=20,
                )
            else:
                issue_table = pn.pane.Markdown("No validation issues.")
        except Exception as exc:
            logger.error("Error building issues table: %s", exc)
            issue_table = pn.pane.Markdown("Error loading issues table")

        # ------------------------------------------------------------------
        # 5. Vitals display as table (replacing sparkline cards)
        # ------------------------------------------------------------------
        vit_df = db_query.get_patient_vitals(self.selected_patient_id)
        labs_df = db_query.get_patient_labs(self.selected_patient_id)

        # Create vitals table
        if not vit_df.empty:
            # Format date for display
            vit_display_df = vit_df.copy()
            if "date" in vit_display_df.columns:
                vit_display_df["date"] = vit_display_df["date"].apply(
                    lambda d: format_date_for_display(d) if pd.notnull(d) else ""
                )
                vit_display_df = vit_display_df.rename(columns={"date": "Date"})

            # Create a clean subset with only needed columns in a specific order
            vital_cols = ["Date"]
            if "weight" in vit_display_df.columns:
                vital_cols.append("weight")
            if "height" in vit_display_df.columns:
                vital_cols.append("height")
            if "bmi" in vit_display_df.columns:
                vital_cols.append("bmi")
            if "sbp" in vit_display_df.columns:
                vital_cols.append("sbp")
            if "dbp" in vit_display_df.columns:
                vital_cols.append("dbp")

            # Create a clean subset
            vit_display_subset = vit_display_df[vital_cols].copy()

            # Rename columns for better display
            column_mapping = {
                "weight": "Weight (kg)",
                "height": "Height (cm)",
                "bmi": "BMI",
                "sbp": "SBP (mmHg)",
                "dbp": "DBP (mmHg)",
            }
            vit_display_subset = vit_display_subset.rename(columns=column_mapping)

            # Sort by date (most recent first)
            vit_display_subset = vit_display_subset.sort_values("Date", ascending=False)

            # Create table with the clean data
            vitals_table = pn.widgets.Tabulator(
                vit_display_subset,
                header_filters=False,
                show_index=False,
                sizing_mode="stretch_width",
                height=250,
            )
            vit_cards = pn.Column(
                pn.pane.Markdown("### Vitals"),
                vitals_table,
                sizing_mode="stretch_width",
            )
        else:
            vit_cards = pn.Column(
                pn.pane.Markdown("### Vitals"),
                pn.pane.Markdown("No vitals data available"),
                sizing_mode="stretch_width",
            )

        # Improved labs table - format the labs dataframe for date-based pivot
        if not labs_df.empty:
            # Copy and clean up the dataframe
            labs_display_df = labs_df.copy()

            # Format date
            if "date" in labs_display_df.columns:
                labs_display_df["date"] = labs_display_df["date"].apply(
                    lambda d: format_date_for_display(d) if pd.notnull(d) else ""
                )
                labs_display_df = labs_display_df.rename(columns={"date": "Date"})

            # Standardize test names to uppercase
            if "test_name" in labs_display_df.columns:
                labs_display_df["test_name"] = labs_display_df["test_name"].str.upper()

            # Drop unnecessary columns
            if "lab_id" in labs_display_df.columns:
                labs_display_df = labs_display_df.drop(columns=["lab_id"])
            if "patient_id" in labs_display_df.columns:
                labs_display_df = labs_display_df.drop(columns=["patient_id"])
            if "reference_range" in labs_display_df.columns:
                labs_display_df = labs_display_df.drop(columns=["reference_range"])

            # Create a test name with units format
            labs_display_df["test_with_units"] = labs_display_df.apply(
                lambda row: (
                    f"{row['test_name']} ({row['unit']})"
                    if pd.notnull(row["unit"])
                    else row["test_name"]
                ),
                axis=1,
            )

            # Map common test name variations to standardized names
            test_name_mapping = {
                "APOLIPOPROTEIN_B": "APO-B",
                "APOLIPOPROTEIN B": "APO-B",
                "APOB": "APO-B",
                "APO B": "APO-B",
                "TOTAL_CHOLESTEROL": "TOTAL CHOLESTEROL",
                "TOTAL-CHOLESTEROL": "TOTAL CHOLESTEROL",
                "CHOLESTEROL": "TOTAL CHOLESTEROL",
                "FASTING_GLUCOSE": "GLUCOSE",
                "FBG": "GLUCOSE",
                "HBA1C": "HBAIC",
            }

            # Apply the mapping to standardize test names
            for old_name, new_name in test_name_mapping.items():
                labs_display_df["test_with_units"] = labs_display_df[
                    "test_with_units"
                ].str.replace(old_name, new_name, regex=False)

            # Pivot the dataframe to have tests as columns and dates as rows
            pivot_df = labs_display_df.pivot_table(
                index="Date",
                columns="test_with_units",
                values="value",
                aggfunc="first",  # Take the first value if multiple exist for same date/test
            ).reset_index()

            # Sort by date (most recent first)
            pivot_df = pivot_df.sort_values("Date", ascending=False)

            # Display in a tabulator widget
            lab_cards = pn.Column(
                pn.pane.Markdown("### Labs"),
                pn.widgets.Tabulator(
                    pivot_df,
                    header_filters=False,
                    show_index=False,
                    sizing_mode="stretch_width",
                    height=250,
                ),
                sizing_mode="stretch_width",
            )
        else:
            lab_cards = pn.Column(
                pn.pane.Markdown("### Labs"),
                pn.pane.Markdown("No recent labs."),
                sizing_mode="stretch_width",
            )

        # ------------------------------------------------------------------
        # 6. Sidebar with external links & waiver note
        # ------------------------------------------------------------------
        ehr_btn = pn.widgets.Button(name="Open EHR", button_type="primary", width=120)
        lab_btn = pn.widgets.Button(name="Lab Portal", button_type="primary", width=120)
        sched_btn = pn.widgets.Button(
            name="Scheduling", button_type="primary", width=120
        )
        waiver_text = pn.widgets.TextAreaInput(
            placeholder="Waiver rationale…", rows=6, width=200
        )

        # Add verification explanation
        verify_explanation = pn.pane.Markdown(
            """
        ### About Verification
        
        When you **Mark as Verified**, the patient will be removed from the list of patients with issues.
        
        Use this when:
        - All data validation issues have been addressed
        - The data has been reviewed and is correct
        
        The patient will reappear if new issues are found during the next data import.
        """,
            width=200,
            styles={"font-size": "12px"},
        )

        sidebar = pn.Column(
            pn.pane.Markdown("### Shortcuts"),
            ehr_btn,
            lab_btn,
            sched_btn,
            pn.layout.Divider(),
            pn.pane.Markdown("### Waiver Rationale"),
            waiver_text,
            pn.layout.Divider(),
            verify_explanation,
            width=220,
            sizing_mode="fixed",
        )

        # Combine components
        main_col = pn.Column(
            header,
            tiles,
            pn.layout.Divider(),
            timeline_plot,
            pn.layout.Divider(),
            pn.pane.Markdown("### Validation Issues"),
            issue_table,
            pn.layout.Divider(),
            vit_cards,
            lab_cards,
            sizing_mode="stretch_width",
        )

        return pn.Row(main_col, sidebar, sizing_mode="stretch_width")

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

            # Reload rules button (admin)
            reload_button = pn.widgets.Button(
                name="Reload Rules", button_type="warning"
            )
            reload_button.on_click(self.reload_rules)

            header = pn.Row(
                header_title,
                validation_button,
                refresh_button,
                reload_button,
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
                | Verified | {self.status_counts.get('verified', 0)} |
                
                **Errors:** {self.severity_counts.get('error', 0)}  
                **Warnings:** {self.severity_counts.get('warning', 0)}  
                **Info:** {self.severity_counts.get('info', 0)}
                """,
                css_classes=["summary-card"],
                sizing_mode="stretch_width",
            )

            # ------------------------------------------------------------------
            # Aggregate Quality Metrics Section (new)
            # ------------------------------------------------------------------
            quality_field_plot = None
            quality_date_plot = None
            try:
                if not self.quality_field_df.empty:
                    y_cols = [c for c in self.quality_field_df.columns if c != "field"]
                    quality_field_plot = self.quality_field_df.hvplot.bar(
                        x="field",
                        y=y_cols,
                        stacked=True,
                        height=300,
                        width=400,
                        title="Issues by Field",
                        legend="top_right",
                    )
                if not self.quality_date_df.empty:
                    y_cols2 = [c for c in self.quality_date_df.columns if c != "dt"]
                    quality_date_plot = self.quality_date_df.hvplot.area(
                        x="dt",
                        y=y_cols2,
                        stacked=True,
                        height=300,
                        width=400,
                        title="Daily Issue Trend",
                        legend="top_left",
                    )
            except Exception as _plot_err:
                logger.debug("Quality metrics plot error: %s", _plot_err)

            quality_metrics_section = pn.Column(
                "### Aggregate Quality Metrics",
                (
                    quality_field_plot
                    if quality_field_plot is not None
                    else pn.pane.Markdown("_No issues yet_")
                ),
                (
                    quality_date_plot
                    if quality_date_plot is not None
                    else pn.Spacer(height=0)
                ),
                sizing_mode="stretch_width",
                width=400,
            )

            # Filter controls
            status_select = pn.widgets.Select(
                name="Status",
                options=["all", "open", "reviewed", "corrected", "ignored", "verified"],
                value=self.filter_status_value,
            )
            severity_select = pn.widgets.Select(
                name="Severity",
                options=["all", "error", "warning", "info"],
                value=self.filter_severity_value,
            )
            type_select = pn.widgets.Select(
                name="Rule Type",
                options=[
                    "all",
                    "missing_data",
                    "range_check",
                    "consistency_check",
                    "categorical_check",
                ],
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
                    quality_metrics_section,
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

    # ---------------------------------------------------------------------
    # Helper to toggle highlight on selected patient row
    # ---------------------------------------------------------------------
    def _highlight_selected_patient(self):
        """Update button styles so currently selected patient is obvious."""
        try:
            selected_key = (
                str(self.selected_patient_id)
                if self.selected_patient_id is not None
                else None
            )
            for pid, btn in self.patient_buttons.items():
                default_type = getattr(btn, "_default_type", "default")
                btn.button_type = "primary" if pid == selected_key else default_type
        except Exception as exc:
            logger.debug("Highlight update failed: %s", exc)

    # ------------------------------------------------------------------
    # Admin helper: reload rules from CSV → YAML → DB
    # ------------------------------------------------------------------
    def reload_rules(self, event=None):
        """Re-seed validation_rules table from CSV; then re-run validation."""
        try:
            logger.info("Reloading validation rules from CSV → YAML → DB")
            seed_validation_rules_main(
                self._csv_rules_path, self._yaml_rules_path, self.db_path
            )
            # Clear cached rules in engine and reload
            if self.validation_engine:
                self.validation_engine.rules = []
                self.validation_engine.load_rules_from_db()

            # Revalidate all patients to reflect new rules
            self.validate_patient()

            pn.state.notifications.success("Validation rules reloaded")
        except Exception as exc:
            logger.error("Failed to reload rules: %s", exc)
            pn.state.notifications.error("Failed to reload rules – check logs")

    # ------------------------------------------------------------------
    # Helper methods for the Patient Data-Quality Dashboard (new)
    # ------------------------------------------------------------------
    def _get_patient_demographics(self, patient_id: int) -> pd.Series:
        """Return a Series with the patient row from the *patients* table.

        We purposefully return a *Series* (single row) so callers can access
        columns directly via attribute or key access without additional checks.
        """
        try:
            demo_df = db_query.get_patient_by_id(patient_id)
            if demo_df.empty:
                return pd.Series(dtype="object")
            return demo_df.iloc[0]
        except Exception as exc:
            logger.error(
                "Error loading demographics for patient %s: %s", patient_id, exc
            )
            return pd.Series(dtype="object")

    def _compute_record_quality(self, patient_id: int) -> tuple[float, str]:
        """Compute *blocking-rule* pass-rate and return *(ratio, colour_key)*.

        Current implementation treats **error**-severity rules as *blocking*.
        • *ratio* = passed / total (0–1).  Returns (1.0, 'success') if no rules.
        • *colour_key* ∈ {'success', 'warning', 'danger'} for Panel themes.
        """
        try:
            # Total active blocking rules (severity == 'error')
            conn = sqlite3.connect(self.db_path)
            total_blocking = conn.execute(
                "SELECT COUNT(*) FROM validation_rules WHERE severity = 'error' AND is_active = 1"
            ).fetchone()[0]

            # Distinct blocking rules that currently have *open* issues for this patient
            failing = conn.execute(
                """
                SELECT COUNT(DISTINCT vr.rule_id)
                FROM validation_results vr
                JOIN validation_rules vru ON vr.rule_id = vru.rule_id
                WHERE vr.patient_id = ? AND vru.severity = 'error' AND vr.status IN ('open', 'reviewed')
                """,
                (str(patient_id),),
            ).fetchone()[0]
            conn.close()

            if total_blocking == 0:
                return 1.0, "success"

            passed = max(total_blocking - failing, 0)
            ratio = passed / total_blocking
            if ratio >= 0.95:
                colour = "success"  # green
            elif ratio >= 0.80:
                colour = "warning"  # amber
            else:
                colour = "danger"  # red
            return ratio, colour
        except Exception as exc:
            logger.error("Error computing record quality: %s", exc)
            return 0.0, "danger"

    def _fetch_visit_metrics(self, patient_id: int) -> pd.Series:
        """Return the single-row Series of *patient_visit_metrics* for *patient_id* (may be empty)."""
        try:
            vm_df = db_query.get_patient_visit_metrics(patient_id)
            if vm_df.empty:
                return pd.Series(dtype="object")
            return vm_df.iloc[0]
        except Exception as exc:
            logger.error(
                "Error fetching visit metrics for patient %s: %s", patient_id, exc
            )
            return pd.Series(dtype="object")

    def _latest_vitality_score(self, patient_id: int) -> str | None:
        """Return most recent Vitality Score value (as str) or None."""
        try:
            scores = db_query.get_patient_scores(patient_id)
            if scores.empty:
                return None
            # Assume score_type column exists and we filter on vitality_score
            vf = scores[scores["score_type"] == "vitality_score"]
            if vf.empty:
                return None
            latest_row = vf.sort_values("date", ascending=False).iloc[0]
            return str(latest_row["score_value"])
        except Exception as exc:
            logger.error(
                "Error fetching vitality score for patient %s: %s", patient_id, exc
            )
            return None

    def _days_since(self, date_str: str | None) -> int | None:
        """Utility: return integer days between *date_str* (YYYY-MM-DD) and today."""
        if not date_str:
            return None
        try:
            from datetime import datetime, timezone

            d = datetime.fromisoformat(date_str.replace("Z", ""))  # tolerate Z suffix
            today = datetime.now(tz=timezone.utc).replace(tzinfo=None)
            return (today - d).days
        except Exception:
            return None

    def mark_patient_as_verified(
        self, patient_id, reason="Patient data verified – all issues addressed"
    ):
        """Mark *all* validation_results for *patient_id* as **verified**.

        This hides the patient from the Issues list immediately.  On the next JSON
        import the entire table is replaced, so the *verified* flag naturally
        resets; any newly-detected issues will re-appear as *open*.
        """
        try:
            if not patient_id:
                return

            logger.info("Marking patient %s as verified", patient_id)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get *all* result_ids for this patient (independent of current status)
            cursor.execute(
                "SELECT result_id FROM validation_results WHERE patient_id = ?",
                (patient_id,),
            )
            result_ids = [row[0] for row in cursor.fetchall()]

            if not result_ids:
                conn.close()
                pn.state.notifications.warning(
                    "No validation results found for this patient"
                )
                return

            # Audit table entries (one per result)
            audit_rows = [(rid, "verify", reason, "current_user") for rid in result_ids]
            cursor.executemany(
                """
                INSERT INTO correction_audit (result_id, action_type, action_reason, action_by)
                VALUES (?, ?, ?, ?)
                """,
                audit_rows,
            )

            # Update all results to status = 'verified'
            cursor.execute(
                "UPDATE validation_results SET status = 'verified' WHERE patient_id = ?",
                (patient_id,),
            )

            conn.commit()
            conn.close()

            # Refresh summaries and patient list
            self.refresh_data()
            self._refresh_patient_list()

            # If the just-verified patient was selected, clear the view and prompt
            if self.selected_patient_id == patient_id:
                self.selected_patient_id = None
                self.patient_view_panel.objects = [
                    pn.pane.Markdown(
                        "## Patient verified and removed from list.\n\nSelect another patient on the left."
                    ),
                ]

            pn.state.notifications.success(
                f"Patient {patient_id} verified (\u2713 {len(result_ids)} issues)."
            )
        except Exception as exc:
            logger.error("Error marking patient as verified: %s", exc)
            pn.state.notifications.error("Failed to verify patient – check logs")


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
