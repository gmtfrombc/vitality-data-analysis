from __future__ import annotations

"""Silent Dropout Detection Page

Panel page that identifies patients who are still marked as active but haven't
had any clinical activity (lab tests, mental health screenings, or vitals measurements)
in the last 90 days. These are "silent dropouts" - patients who have effectively 
stopped participating in the program but haven't been officially marked as inactive.

Relies on :pyfunc:`app.utils.silent_dropout.get_clinical_inactivity_report` for the
core detection logic.
"""

import panel as pn
import param
import pandas as pd
import logging
import io

from app.utils.silent_dropout import (
    get_clinical_inactivity_report,
    mark_patient_as_inactive,
)

logger = logging.getLogger(__name__)

pn.extension()  # ensure widgets and FileDownload available


class SilentDropoutPage(param.Parameterized):
    """Panel UI for the Silent Dropout Report."""

    # User-selectable parameters
    inactivity_days = param.Integer(
        default=90,
        bounds=(30, 365),
        doc="Days without clinical activity to consider dropout",
    )
    minimum_activity_count = param.Integer(
        default=2, bounds=(1, 10), doc="Minimum number of past activities required"
    )
    active_only = param.Boolean(default=True, doc="Only show patients marked as active")

    run_report = param.Action(lambda self: self._generate_report())
    mark_inactive = param.Action(lambda self: self._mark_selected_inactive())

    def __init__(self, **params):
        super().__init__(**params)

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
            "### No silent dropouts found for selected criteria.", visible=False
        )

        self._download_btn = pn.widgets.FileDownload(
            label="Download CSV",
            button_type="success",
            filename="silent_dropouts.csv",
            disabled=True,
        )

        self._mark_inactive_btn = pn.widgets.Button(
            name="Mark Selected as Inactive",
            button_type="danger",
            disabled=True,
        )
        self._mark_inactive_btn.on_click(self._mark_selected_inactive)

        self._status = pn.pane.Markdown("")

        # Add total count display
        self._total_count = pn.pane.Markdown(
            "### Total silent dropouts: 0",
            styles={
                "background": "#f8f9fa",
                "padding": "10px",
                "border-radius": "5px",
                "border": "1px solid #dee2e6",
                "font-weight": "bold",
                "text-align": "center",
            },
        )

        # Initial visibility setup
        self._update_visibility()

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    def _generate_report(self, *_):  # noqa: D401 – internal
        """Run silent dropout report and refresh table & download."""
        try:
            self._df = get_clinical_inactivity_report(
                inactivity_days=self.inactivity_days,
                minimum_activity_count=self.minimum_activity_count,
                active_only=self.active_only,
            )

            # Reset selection
            self._selected_patients = []
            self._mark_inactive_btn.disabled = True

            # Clear status
            self._status.object = ""

            # Update total count
            total_patients = len(self._df)
            self._total_count.object = f"### Total silent dropouts: {total_patients}"

            # Set background color based on count
            if total_patients > 100:
                bg_color = "#f8d7da"  # Red-ish for high numbers
            elif total_patients > 50:
                bg_color = "#fff3cd"  # Yellow-ish for medium numbers
            else:
                bg_color = "#d4edda"  # Green-ish for low numbers

            self._total_count.styles.update({"background": bg_color})

        except Exception as exc:
            logger.error("Silent dropout report failed: %s", exc)
            self._df = pd.DataFrame()
            self._status.object = f"""
            <div style="color: #721c24; background-color: #f8d7da; padding: 10px; border: 1px solid #f5c6cb; border-radius: 5px;">
              <strong>Error generating report:</strong> {exc}
            </div>
            """
            self._total_count.object = "### Total silent dropouts: 0"

        # Update download button
        if not self._df.empty:
            csv_bytes = self._df.to_csv(index=False).encode()
            self._download_btn.filename = f"silent_dropouts_{self.inactivity_days}days_{self.minimum_activity_count}acts.csv"
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

    def _on_row_click(self, event):
        """Handle row selection events."""
        self._selected_patients = [row["patient_id"] for row in event.rows]
        self._mark_inactive_btn.disabled = len(self._selected_patients) == 0

    # ------------------------------------------------------------------
    # View
    # ------------------------------------------------------------------

    def view(self):  # noqa: D401 – Panel convention
        """Return layout for embedding in main app."""

        controls = pn.Row(
            pn.widgets.IntInput.from_param(
                self.param.inactivity_days, name="Inactivity days threshold"
            ),
            pn.widgets.IntInput.from_param(
                self.param.minimum_activity_count, name="Min activities"
            ),
            pn.widgets.Checkbox.from_param(self.param.active_only, name="Active only"),
            pn.widgets.Button.from_param(
                self.param.run_report, name="Run Report", button_type="primary"
            ),
            self._download_btn,
            sizing_mode="stretch_width",
        )

        action_bar = pn.Row(
            self._mark_inactive_btn,
            self._status,
            sizing_mode="stretch_width",
        )

        return pn.Column(
            pn.pane.Markdown("# Silent Dropout Detection"),
            pn.pane.Markdown(
                """Identify patients who are still marked as active but haven't had any clinical activity 
                (lab tests, mental health screenings, or vitals) in the specified number of days. 
                Patients must have at least the specified minimum number of past activities to be considered
                potential silent dropouts."""
            ),
            controls,
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
def silent_dropout_page():  # noqa: D401 – entry-point
    return SilentDropoutPage().view()
