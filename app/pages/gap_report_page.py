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
from app.utils.date_helpers import format_date_for_display

logger = logging.getLogger(__name__)

pn.extension()  # ensure widgets and FileDownload available


class GapReportPage(param.Parameterized):
    """Panel UI for the Condition Gap Report."""

    # User-selectable parameters
    condition = param.ObjectSelector(default="obesity", objects=[])
    active_only = param.Boolean(default=True, doc="Restrict to active patients only")

    run_report = param.Action(lambda self: self._generate_report())

    def __init__(self, **params):
        super().__init__(**params)

        # Populate available conditions from gap-report helper rules
        from app.utils.gap_report import _RULES  # type: ignore – internal import

        self.param.condition.objects = sorted(_RULES.keys())
        self.condition = self.param.condition.objects[0]

        # Placeholder DataFrame & widgets
        self._df: pd.DataFrame = pd.DataFrame()

        self._table_panel = pn.widgets.Tabulator(
            self._df, pagination="remote", page_size=20, sizing_mode="stretch_width"
        )

        self._blank = pn.pane.Markdown(
            "### No gaps found for selected criteria.", visible=False
        )

        self._download_btn = pn.widgets.FileDownload(
            label="Download CSV",
            button_type="success",
            filename="gap_report.csv",
            disabled=True,
        )

        # Initial visibility setup
        self._update_visibility()

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    def _generate_report(self, *_):  # noqa: D401 – internal
        """Run gap report and refresh table & download."""
        try:
            self._df = get_condition_gap_report(
                self.condition, active_only=self.active_only
            )

            # Format dates for display
            if not self._df.empty and "date" in self._df.columns:
                self._df["date"] = self._df["date"].apply(
                    lambda d: format_date_for_display(d, format_str="%b %d, %Y")
                )

        except Exception as exc:
            logger.error("Gap report failed: %s", exc)
            self._df = pd.DataFrame()

        # Update download button
        if not self._df.empty:
            csv_bytes = self._df.to_csv(index=False).encode()
            self._download_btn.filename = f"gap_report_{self.condition}.csv"
            self._download_btn.file = io.BytesIO(csv_bytes)
            self._download_btn.disabled = False
        else:
            self._download_btn.disabled = True

        # Update table widget
        self._table_panel.value = self._df

        self._update_visibility()

    # ------------------------------------------------------------------
    # View
    # ------------------------------------------------------------------

    def view(self):  # noqa: D401 – Panel convention
        """Return layout for embedding in main app."""

        controls = pn.Row(
            pn.widgets.Select.from_param(self.param.condition, name="Condition"),
            pn.widgets.Checkbox.from_param(self.param.active_only, name="Active only"),
            pn.widgets.Button.from_param(
                self.param.run_report, name="Run", button_type="primary"
            ),
            self._download_btn,
            sizing_mode="stretch_width",
        )

        return pn.Column(
            pn.pane.Markdown("# Data-Quality Gap Report"),
            pn.pane.Markdown(
                "Identify patients whose clinical measurements suggest a condition but lack the corresponding diagnosis."
            ),
            controls,
            pn.layout.Divider(),
            self._blank,
            self._table_panel,
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
