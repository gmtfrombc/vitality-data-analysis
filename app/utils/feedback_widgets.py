"""Panel UI components for gathering user feedback.

Part of *WS-6 Continuous Feedback & Evaluation* work stream.

This module provides reusable Panel widgets for collecting feedback on assistant results,
which is then stored in the assistant_feedback table for continuous improvement.
"""

from __future__ import annotations

import logging
import panel as pn
import param

from app.utils.feedback_db import insert_feedback

logger = logging.getLogger(__name__)


class FeedbackWidget(param.Parameterized):
    """A lightweight feedback widget with thumbs up/down and optional comments."""

    # Parameters
    query: param.String = param.String(default="")
    rating: param.String = param.String(default="")
    show_comment: param.Boolean = param.Boolean(default=False)
    comment: param.String = param.String(default="")
    submitted: param.Boolean = param.Boolean(default=False)

    def __init__(self, query: str, **params):
        """Initialize the feedback widget with the query being rated.

        Parameters
        ----------
        query : str
            The query text that's being rated
        """
        super().__init__(**params)
        self.query = query

        # Create UI components
        self._create_components()

    def _create_components(self):
        """Create all the UI components for the feedback widget."""
        # Rating buttons
        self.thumbs_up = pn.widgets.Button(
            name="👍 Helpful", button_type="success", width=110
        )
        self.thumbs_down = pn.widgets.Button(
            name="👎 Not Helpful", button_type="danger", width=110
        )

        # Comment box
        self.comment_input = pn.widgets.TextAreaInput(
            name="Tell us more (optional):",
            placeholder="What could be improved?",
            rows=2,
            visible=False,
        )

        # Submit button
        self.submit_button = pn.widgets.Button(
            name="Submit Feedback", button_type="primary", disabled=True, width=150
        )

        # Thank you message
        self.thank_you = pn.pane.Markdown(
            "**Thank you for your feedback!** It helps us improve the assistant.",
            visible=False,
        )

        # Wire up event handlers
        self.thumbs_up.on_click(self._on_thumbs_up)
        self.thumbs_down.on_click(self._on_thumbs_down)
        self.comment_input.param.watch(self._on_comment_change, "value")
        self.submit_button.on_click(self._on_submit)

    def _on_thumbs_up(self, event):
        """Handle thumbs up click."""
        self.rating = "up"
        self._update_ui("up")

    def _on_thumbs_down(self, event):
        """Handle thumbs down click."""
        self.rating = "down"
        self._update_ui("down")

    def _update_ui(self, rating: str):
        """Update UI based on rating selection."""
        # Update button styles
        self.thumbs_up.button_type = "success" if rating == "up" else "light"
        self.thumbs_down.button_type = "danger" if rating == "down" else "light"

        # Show comment box for thumbs down by default
        self.show_comment = rating == "down"
        self.comment_input.visible = self.show_comment

        # Enable submit button
        self.submit_button.disabled = False

    def _on_comment_change(self, event):
        """Handle comment changes."""
        self.comment = event.new

    def _on_submit(self, event):
        """Handle submission of feedback."""
        try:
            success = insert_feedback(
                question=self.query,
                rating=self.rating,
                comment=self.comment or None,  # Use None for empty string
            )

            if success:
                logger.info(
                    f"Feedback submitted: {self.rating} for query: {self.query[:50]}..."
                )
                self.submitted = True
                self._show_thank_you()
            else:
                logger.error(
                    f"Failed to insert feedback for query: {self.query[:50]}..."
                )
                # We could show an error message here, but for simplicity we'll
                # still show the thank you message to not disrupt user experience
                self._show_thank_you()

        except Exception as exc:
            logger.exception(f"Error submitting feedback: {exc}")
            # Again, show thank you despite the error
            self._show_thank_you()

    def _show_thank_you(self):
        """Show thank you message and hide other components."""
        # Hide all input components
        self.thumbs_up.visible = False
        self.thumbs_down.visible = False
        self.comment_input.visible = False
        self.submit_button.visible = False

        # Show thank you message
        self.thank_you.visible = True

    def view(self) -> pn.Column:
        """Return the complete widget view."""
        header = pn.pane.Markdown("### Help Us Improve", margin=(0, 0, 5, 0))
        description = pn.pane.Markdown(
            "Was this analysis helpful?", margin=(0, 0, 10, 0)
        )

        buttons_row = pn.Row(
            self.thumbs_up,
            pn.Spacer(width=10),
            self.thumbs_down,
            sizing_mode="stretch_width",
        )

        return pn.Column(
            header,
            description,
            buttons_row,
            self.comment_input,
            pn.Spacer(height=5),
            self.submit_button,
            self.thank_you,
            sizing_mode="stretch_width",
            styles={
                "background": "#f8f9fa",
                "border-radius": "5px",
                "padding": "15px",
                "margin-top": "20px",
            },
            css_classes=["feedback-widget"],
        )


def create_feedback_widget(query: str) -> pn.viewable.Viewable:
    """Create and return a feedback widget for the given query.

    Parameters
    ----------
    query : str
        The query being rated

    Returns
    -------
    panel.viewable.Viewable
        The feedback widget component
    """
    widget = FeedbackWidget(query=query)
    return widget.view()
