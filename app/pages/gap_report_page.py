from __future__ import annotations

"""Data-Quality Gaps Page

Panel page that surfaces patients whose measurements imply a clinical
condition but lack a matching diagnosis in PMH.

Relies on :pyfunc:`app.utils.gap_report.get_condition_gap_report` so the core
logic is shared with CLI and assistant integrations.
"""

import panel as pn
import param
import pandas as pd
import logging
import io

from app.utils.gap_report import get_condition_gap_report
from app.utils.silent_dropout import (
    get_clinical_inactivity_report,
    mark_patient_as_inactive,
)
from app.utils.date_helpers import format_date_for_display

logger = logging.getLogger(__name__)

pn.extension()  # ensure widgets and FileDownload available


class GapReportPage(param.Parameterized):
    """Panel UI for the Condition Gap Report."""

    # Report type selector
    report_type = param.Selector(
        default="Condition Gaps",
        objects=["Condition Gaps", "Engagement Issues"],
        doc="Type of report to generate",
    )

    # User-selectable parameters
    condition = param.ObjectSelector(default="obesity", objects=[])
    active_only = param.Boolean(default=True, doc="Restrict to active patients only")

    # Silent dropout specific parameters
    inactivity_days = param.Integer(
        default=90,
        bounds=(30, 365),
        doc="Days without clinical activity to consider dropout",
    )
    minimum_activity_count = param.Integer(
        default=2, bounds=(1, 10), doc="Minimum number of past activities required"
    )

    run_report = param.Action(lambda self: self._generate_report())
    mark_inactive = param.Action(lambda self: self._mark_selected_inactive())

    def __init__(self, **params):
        super().__init__(**params)

        # Populate available conditions from gap-report helper rules
        from app.utils.gap_report import _RULES  # type: ignore – internal import

        # Store options for each report type
        self._condition_options = sorted(_RULES.keys())
        self._engagement_options = ["Silent Dropouts"]

        # Set initial condition dropdown options
        self.param.condition.objects = self._condition_options
        self.condition = self.param.condition.objects[0]

        # Placeholder DataFrame & widgets
        self._df: pd.DataFrame = pd.DataFrame()
        self._selected_patients = []

        self._table_panel = pn.widgets.Tabulator(
            self._df,
            pagination="remote",
            page_size=20,
            sizing_mode="stretch_width",
            selectable=True,
        )
        self._table_panel.on_click(self._on_row_click)

        self._blank = pn.pane.Markdown(
            "### No gaps found for selected criteria.", visible=False
        )

        self._download_btn = pn.widgets.FileDownload(
            label="Download CSV",
            button_type="success",
            filename="gap_report.csv",
            disabled=True,
        )

        # Add total count display
        self._total_count = pn.pane.Markdown(
            "### Total records: 0",
            styles={
                "background": "#f8f9fa",
                "padding": "10px",
                "border-radius": "5px",
                "border": "1px solid #dee2e6",
                "font-weight": "bold",
                "text-align": "center",
            },
            visible=False,
        )

        # Add mark inactive button for silent dropouts
        self._mark_inactive_btn = pn.widgets.Button(
            name="Mark Selected as Inactive",
            button_type="danger",
            disabled=True,
            visible=False,
        )
        self._mark_inactive_btn.on_click(self._mark_selected_inactive)

        # Status message
        self._status = pn.pane.Markdown("", visible=False)

        # Register callback for report type change
        self.param.watch(self._update_report_type_ui, "report_type")

        # Initial visibility setup
        self._update_visibility()

    def _update_report_type_ui(self, event):
        """Update UI based on selected report type."""
        if event.new == "Condition Gaps":
            self.param.condition.objects = self._condition_options
            self.condition = self._condition_options[0]
            self._mark_inactive_btn.visible = False
        else:  # Engagement Issues
            self.param.condition.objects = self._engagement_options
            self.condition = self._engagement_options[0]
            self._mark_inactive_btn.visible = True

        # Reset the table
        self._df = pd.DataFrame()
        self._table_panel.value = self._df
        self._update_visibility()

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    def _generate_report(self, *_):  # noqa: D401 – internal
        """Run report and refresh table & download."""
        try:
            if self.report_type == "Condition Gaps":
                self._df = get_condition_gap_report(
                    self.condition, active_only=self.active_only
                )

                # Format dates for display
                if not self._df.empty and "date" in self._df.columns:
                    self._df["date"] = self._df["date"].apply(
                        lambda d: format_date_for_display(d, format_str="%b %d, %Y")
                    )

                self._total_count.object = f"### Total gaps: {len(self._df)}"
                self._mark_inactive_btn.visible = False
            else:  # Engagement Issues
                if self.condition == "Silent Dropouts":
                    self._df = get_clinical_inactivity_report(
                        inactivity_days=self.inactivity_days,
                        minimum_activity_count=self.minimum_activity_count,
                        active_only=self.active_only,
                    )

                    self._total_count.object = (
                        f"### Total silent dropouts: {len(self._df)}"
                    )
                    self._mark_inactive_btn.visible = True

                    # Set background color based on count
                    total_patients = len(self._df)
                    if total_patients > 100:
                        bg_color = "#f8d7da"  # Red-ish for high numbers
                    elif total_patients > 50:
                        bg_color = "#fff3cd"  # Yellow-ish for medium numbers
                    else:
                        bg_color = "#d4edda"  # Green-ish for low numbers

                    self._total_count.styles.update({"background": bg_color})

            # Reset selection
            self._selected_patients = []
            self._mark_inactive_btn.disabled = True

            # Clear status
            self._status.object = ""
            self._status.visible = False

            # Show total count if there are records
            self._total_count.visible = not self._df.empty

        except Exception as exc:
            logger.error("Report generation failed: %s", exc)
            self._df = pd.DataFrame()
            self._status.object = f"""
            <div style="color: #721c24; background-color: #f8d7da; padding: 10px; border: 1px solid #f5c6cb; border-radius: 5px;">
              <strong>Error generating report:</strong> {exc}
            </div>
            """
            self._status.visible = True
            self._total_count.visible = False

        # Update download button
        if not self._df.empty:
            csv_bytes = self._df.to_csv(index=False).encode()
            filename_prefix = self.report_type.lower().replace(" ", "_")
            self._download_btn.filename = (
                f"{filename_prefix}_{self.condition.lower()}.csv"
            )
            self._download_btn.file = io.BytesIO(csv_bytes)
            self._download_btn.disabled = False
        else:
            self._download_btn.disabled = True

        # Update table widget
        self._table_panel.value = self._df
        self._table_panel.selection = []

        self._update_visibility()

    def _mark_selected_inactive(self, *_):
        """Mark selected patients as inactive."""
        if not self._selected_patients:
            self._status.object = """
            <div style="color: #856404; background-color: #fff3cd; padding: 10px; border: 1px solid #ffeeba; border-radius: 5px;">
              ⚠️ No patients selected.
            </div>
            """
            self._status.visible = True
            return

        try:
            success_count = 0
            for patient_id in self._selected_patients:
                if mark_patient_as_inactive(patient_id):
                    success_count += 1

            self._status.object = f"""
            <div style="color: #155724; background-color: #d4edda; padding: 10px; border: 1px solid #c3e6cb; border-radius: 5px;">
              ✅ Marked {success_count} of {len(self._selected_patients)} patients as inactive.
            </div>
            """
            self._status.visible = True

            # Refresh the report if any changes were made
            if success_count > 0:
                self._generate_report()

        except Exception as exc:
            logger.error("Failed to mark patients as inactive: %s", exc)
            self._status.object = f"""
            <div style="color: #721c24; background-color: #f8d7da; padding: 10px; border: 1px solid #f5c6cb; border-radius: 5px;">
              <strong>Error marking patients inactive:</strong> {exc}
            </div>
            """
            self._status.visible = True

    def _on_row_click(self, event):
        """Handle row selection events."""
        if (
            self.report_type == "Engagement Issues"
            and self.condition == "Silent Dropouts"
        ):
            self._selected_patients = [row["patient_id"] for row in event.rows]
            self._mark_inactive_btn.disabled = len(self._selected_patients) == 0
        else:
            self._selected_patients = []
            self._mark_inactive_btn.disabled = True

    # ------------------------------------------------------------------
    # View
    # ------------------------------------------------------------------

    def view(self):  # noqa: D401 – Panel convention
        """Return layout for embedding in main app."""

        # Report type toggle - using a more compact indicator with better styling
        toggle_container = pn.Row(
            pn.pane.Markdown("**Report Type:**", margin=(10, 5, 5, 5)),
            pn.layout.HSpacer(width=10),
            pn.pane.Markdown(
                "**Condition Gaps**",
                styles={
                    "color": "#007bff",
                    "font-weight": (
                        "bold" if self.report_type == "Condition Gaps" else "normal"
                    ),
                },
                margin=(10, 5, 5, 0),
            ),
            pn.widgets.Switch(
                value=self.report_type == "Engagement Issues",
                width=40,
                height=25,
                margin=(5, 5, 5, 5),
                styles={"padding": "0px"},
            ),
            pn.pane.Markdown(
                "**Engagement Issues**",
                styles={
                    "color": "#28a745",
                    "font-weight": (
                        "bold" if self.report_type == "Engagement Issues" else "normal"
                    ),
                },
                margin=(10, 0, 5, 5),
            ),
            css_classes=["toggle-container"],
            margin=(0, 0, 10, 0),
            width=450,
            styles={
                "background": "#f8f9fa",
                "border-radius": "10px",
                "padding": "10px",
            },
        )

        # Add callback to handle toggle changes
        def toggle_report_type(event):
            if event.new:
                self.report_type = "Engagement Issues"
                toggle_container[2].styles.update({"font-weight": "normal"})
                toggle_container[4].styles.update({"font-weight": "bold"})
            else:
                self.report_type = "Condition Gaps"
                toggle_container[2].styles.update({"font-weight": "bold"})
                toggle_container[4].styles.update({"font-weight": "normal"})

        toggle_container[3].param.watch(toggle_report_type, "value")

        # Basic controls for all reports
        common_controls = pn.Row(
            pn.widgets.Select.from_param(self.param.condition, name="Selection"),
            pn.widgets.Checkbox.from_param(self.param.active_only, name="Active only"),
            pn.widgets.Button.from_param(
                self.param.run_report, name="Run", button_type="primary"
            ),
            self._download_btn,
            sizing_mode="stretch_width",
        )

        # Silent dropout specific controls (conditionally visible)
        dropout_controls = pn.Row(
            pn.widgets.IntInput.from_param(
                self.param.inactivity_days, name="Inactivity days threshold"
            ),
            pn.widgets.IntInput.from_param(
                self.param.minimum_activity_count, name="Min activities"
            ),
            visible=False,
            sizing_mode="stretch_width",
        )

        # Update visibility based on report type
        def update_controls(*events):
            if self.report_type == "Engagement Issues":
                dropout_controls.visible = True
            else:
                dropout_controls.visible = False

        self.param.watch(update_controls, "report_type")
        # Initial call to set visibility
        update_controls()

        action_bar = pn.Row(
            self._mark_inactive_btn,
            self._status,
            sizing_mode="stretch_width",
        )

        return pn.Column(
            pn.pane.Markdown("# Data-Quality Gap Report"),
            pn.pane.Markdown(
                "Identify data quality gaps and potential silent dropouts in your patient population."
            ),
            toggle_container,
            common_controls,
            dropout_controls,
            self._total_count,
            pn.layout.Divider(),
            self._blank,
            self._table_panel,
            pn.layout.Divider(),
            action_bar,
            sizing_mode="stretch_width",
        )

    def _update_visibility(self):
        # Reactive visibility: if table empty hide
        if self._df.empty:
            self._table_panel.visible = False
            self._blank.visible = True
        else:
            self._table_panel.visible = True
            self._blank.visible = False


# Helper accessor for run.py


def gap_report_page():  # noqa: D401 – entry-point
    return GapReportPage().view()
