"""
Enhanced Feedback Widget for AAA Learning System

This widget extends the basic feedback functionality to capture detailed corrections
and integrate with the learning system for continuous improvement.

Features:
- Standard thumbs up/down feedback
- Detailed correction capture for negative feedback
- Integration with CorrectionService
- Real-time error analysis and suggestions
"""

from __future__ import annotations

import logging
import panel as pn
import param
from typing import Optional, Dict, Any, Callable

from app.utils.feedback_db import insert_feedback
from app.services.correction_service import CorrectionService

logger = logging.getLogger(__name__)


class EnhancedFeedbackWidget(param.Parameterized):
    """Enhanced feedback widget with correction capture capabilities."""

    # Parameters
    query: str = param.String(default="")
    original_intent_json: str = param.String(default="")
    original_code: str = param.String(default="")
    original_results: str = param.String(default="")
    feedback_submitted: bool = param.Boolean(default=False)
    correction_captured: bool = param.Boolean(default=False)

    def __init__(
        self,
        query: str,
        original_intent_json: Optional[str] = None,
        original_code: Optional[str] = None,
        original_results: Optional[str] = None,
        on_correction_applied: Optional[Callable] = None,
        **params,
    ):
        """Initialize the enhanced feedback widget.

        Args:
            query: The original user query
            original_intent_json: The parsed intent JSON (if available)
            original_code: The generated code (if available)
            original_results: The analysis results (if available)
            on_correction_applied: Callback when correction is applied
        """
        super().__init__(**params)

        self.query = query
        self.original_intent_json = original_intent_json or ""
        self.original_code = original_code or ""
        self.original_results = original_results or ""
        self.on_correction_applied = on_correction_applied

        # Initialize correction service
        self.correction_service = CorrectionService()

        # UI components
        self._create_components()

        # State tracking
        self.feedback_id: Optional[int] = None
        self.correction_session_id: Optional[int] = None

    def _create_components(self):
        """Create the UI components."""

        # Standard feedback section
        self.feedback_section = pn.Column(
            pn.pane.Markdown("**Was this answer helpful?**", margin=(5, 0)),
            pn.Row(
                pn.widgets.Button(
                    name="👍 Yes", button_type="success", width=80, margin=(0, 5, 0, 0)
                ),
                pn.widgets.Button(
                    name="👎 No", button_type="danger", width=80, margin=(0, 5, 0, 0)
                ),
                align="start",
            ),
            margin=(10, 0),
            visible=True,
        )

        # Get button references for event handling
        self.thumbs_up_btn = self.feedback_section[1][0]
        self.thumbs_down_btn = self.feedback_section[1][1]

        # Enhanced correction section (hidden initially)
        self.correction_section = pn.Column(
            pn.pane.Markdown("### Help us improve! 🎯", margin=(10, 0, 5, 0)),
            pn.pane.Markdown(
                "Please provide the correct answer so we can learn:",
                margin=(0, 0, 5, 0),
            ),
            pn.widgets.TextAreaInput(
                name="Correct Answer:",
                placeholder="What should the correct answer be? Be as specific as possible...",
                height=100,
                sizing_mode="stretch_width",
            ),
            pn.Row(
                pn.widgets.Button(
                    name="Submit Correction", button_type="primary", width=150
                ),
                pn.widgets.Button(name="Skip", button_type="light", width=80),
                margin=(10, 0, 0, 0),
            ),
            visible=False,
            sizing_mode="stretch_width",
        )

        # Get correction component references
        self.correct_answer_input = self.correction_section[2]
        self.submit_correction_btn = self.correction_section[3][0]
        self.skip_correction_btn = self.correction_section[3][1]

        # Analysis and suggestions section (hidden initially)
        self.analysis_section = pn.Column(
            pn.pane.Markdown("### 🔍 Analysis & Suggestions", margin=(10, 0, 5, 0)),
            pn.pane.Markdown("*Analyzing the error...*", name="analysis_text"),
            pn.Column(name="suggestions_container"),
            visible=False,
            sizing_mode="stretch_width",
        )

        # Thank you section (hidden initially)
        self.thank_you_section = pn.Column(
            pn.pane.Markdown("✅ **Thank you for your feedback!**", margin=(10, 0)),
            pn.pane.Markdown(
                "Your input helps improve the assistant.", margin=(0, 0, 10, 0)
            ),
            visible=False,
        )

        # Set up event handlers
        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Set up event handlers for UI components."""

        self.thumbs_up_btn.on_click(self._on_thumbs_up)
        self.thumbs_down_btn.on_click(self._on_thumbs_down)
        self.submit_correction_btn.on_click(self._on_submit_correction)
        self.skip_correction_btn.on_click(self._on_skip_correction)

    def _on_thumbs_up(self, event):
        """Handle thumbs up feedback."""
        try:
            success = insert_feedback(question=self.query, rating="up")

            if success:
                logger.info(
                    f"Positive feedback recorded for query: {self.query[:50]}..."
                )
                self._show_thank_you()
            else:
                logger.error("Failed to record positive feedback")

        except Exception as e:
            logger.error(f"Error recording positive feedback: {e}")

    def _on_thumbs_down(self, event):
        """Handle thumbs down feedback."""
        try:
            success = insert_feedback(question=self.query, rating="down")

            if success:
                logger.info(
                    f"Negative feedback recorded for query: {self.query[:50]}..."
                )
                # Store feedback ID for correction session
                self.feedback_id = self._get_latest_feedback_id()
                self._show_correction_interface()
            else:
                logger.error("Failed to record negative feedback")

        except Exception as e:
            logger.error(f"Error recording negative feedback: {e}")

    def _get_latest_feedback_id(self) -> Optional[int]:
        """Get the ID of the most recently inserted feedback."""
        try:
            from app.utils.feedback_db import _get_conn

            with _get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id FROM assistant_feedback 
                    WHERE question = ? AND rating = 'down'
                    ORDER BY id DESC LIMIT 1
                """,
                    (self.query,),
                )

                row = cursor.fetchone()
                return row[0] if row else None

        except Exception as e:
            logger.error(f"Failed to get latest feedback ID: {e}")
            return None

    def _show_correction_interface(self):
        """Show the correction interface."""
        self.feedback_section.visible = False
        self.correction_section.visible = True

    def _on_submit_correction(self, event):
        """Handle correction submission."""
        correct_answer = self.correct_answer_input.value.strip()

        if not correct_answer:
            # Show error message
            self.correct_answer_input.placeholder = (
                "Please provide a correct answer before submitting..."
            )
            return

        try:
            # Create correction session
            if self.feedback_id:
                self.correction_session_id = (
                    self.correction_service.capture_correction_session(
                        feedback_id=self.feedback_id,
                        original_query=self.query,
                        human_correct_answer=correct_answer,
                        original_intent_json=self.original_intent_json or None,
                        original_code=self.original_code or None,
                        original_results=self.original_results or None,
                    )
                )

                logger.info(f"Created correction session {self.correction_session_id}")

                # Analyze the error
                self._analyze_and_show_suggestions()
            else:
                logger.error("No feedback ID available for correction session")
                self._show_thank_you()

        except Exception as e:
            logger.error(f"Error submitting correction: {e}")
            self._show_thank_you()

    def _on_skip_correction(self, event):
        """Handle skipping the correction."""
        self._show_thank_you()

    def _analyze_and_show_suggestions(self):
        """Analyze the error and show suggestions."""
        if not self.correction_session_id:
            self._show_thank_you()
            return

        try:
            # Hide correction interface
            self.correction_section.visible = False

            # Show analysis section
            self.analysis_section.visible = True

            # Perform error analysis
            error_category = self.correction_service.analyze_error_type(
                self.correction_session_id
            )

            # Update analysis text
            analysis_text = self.analysis_section[1]
            analysis_text.object = (
                f"**Error Category:** {error_category.replace('_', ' ').title()}"
            )

            # Generate and show suggestions
            suggestions = self.correction_service.generate_correction_suggestions(
                self.correction_session_id
            )
            self._show_suggestions(suggestions)

        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            self._show_thank_you()

    def _show_suggestions(self, suggestions: list):
        """Show correction suggestions."""
        suggestions_container = self.analysis_section[2]

        if not suggestions:
            suggestions_container.append(
                pn.pane.Markdown(
                    "*No specific suggestions available. Thank you for the feedback!*"
                )
            )
            # Auto-proceed to thank you after a moment
            pn.state.add_periodic_callback(
                lambda: self._show_thank_you(), 3000, count=1
            )
            return

        # Create suggestion buttons
        for i, suggestion in enumerate(suggestions):
            suggestion_card = pn.Column(
                pn.pane.Markdown(f"**{suggestion['description']}**"),
                pn.pane.Markdown(
                    f"*Action: {suggestion['action']}*",
                    styles={"font-size": "0.9em", "color": "#666"},
                ),
                pn.widgets.Button(
                    name=f"Apply Suggestion {i+1}",
                    button_type=(
                        "success"
                        if suggestion["type"] != "manual_correction"
                        else "light"
                    ),
                    width=150,
                    margin=(5, 0, 10, 0),
                ),
                styles={
                    "border": "1px solid #ddd",
                    "padding": "10px",
                    "margin": "5px 0",
                    "border-radius": "5px",
                },
            )

            # Set up suggestion button handler
            suggestion_btn = suggestion_card[2]
            suggestion_btn.param.watch(
                lambda event, idx=i: self._apply_suggestion(suggestions[idx]), "clicks"
            )

            suggestions_container.append(suggestion_card)

        # Add "Finish" button
        finish_btn = pn.widgets.Button(
            name="Finish", button_type="primary", width=100, margin=(15, 0, 0, 0)
        )
        finish_btn.on_click(lambda event: self._show_thank_you())
        suggestions_container.append(finish_btn)

    def _apply_suggestion(self, suggestion: Dict[str, Any]):
        """Apply a correction suggestion."""
        try:
            suggestion_type = suggestion["type"]

            if suggestion_type == "manual_correction":
                # For manual corrections, just mark as reviewed
                self.correction_service.update_correction_session(
                    self.correction_session_id,
                    {"status": "pending", "reviewed_by": "user"},
                )
                logger.info(
                    f"Marked correction session {self.correction_session_id} for manual review"
                )
            else:
                # For automated suggestions, attempt to apply
                success = self.correction_service.apply_correction(
                    self.correction_session_id, suggestion_type
                )

                if success:
                    logger.info(f"Applied correction suggestion: {suggestion_type}")

                    # Trigger callback if provided
                    if self.on_correction_applied:
                        self.on_correction_applied(
                            self.correction_session_id, suggestion
                        )
                else:
                    logger.warning(
                        f"Failed to apply correction suggestion: {suggestion_type}"
                    )

            self.correction_captured = True

        except Exception as e:
            logger.error(f"Error applying suggestion: {e}")

    def _show_thank_you(self):
        """Show thank you message."""
        self.feedback_section.visible = False
        self.correction_section.visible = False
        self.analysis_section.visible = False
        self.thank_you_section.visible = True
        self.feedback_submitted = True

    def view(self) -> pn.Column:
        """Get the complete widget view."""
        return pn.Column(
            self.feedback_section,
            self.correction_section,
            self.analysis_section,
            self.thank_you_section,
            sizing_mode="stretch_width",
            styles={"background": "#f8f9fa", "padding": "15px", "border-radius": "8px"},
        )


def create_enhanced_feedback_widget(
    query: str,
    original_intent_json: Optional[str] = None,
    original_code: Optional[str] = None,
    original_results: Optional[str] = None,
    on_correction_applied: Optional[Callable] = None,
) -> pn.Column:
    """Create an enhanced feedback widget.

    Args:
        query: The original user query
        original_intent_json: The parsed intent JSON (if available)
        original_code: The generated code (if available)
        original_results: The analysis results (if available)
        on_correction_applied: Callback when correction is applied

    Returns:
        Panel Column widget
    """
    widget = EnhancedFeedbackWidget(
        query=query,
        original_intent_json=original_intent_json,
        original_code=original_code,
        original_results=original_results,
        on_correction_applied=on_correction_applied,
    )

    return widget.view()
