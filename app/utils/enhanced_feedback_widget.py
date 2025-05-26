"""
Enhanced Feedback Widget for AAA Learning System

This widget extends the basic feedback functionality to capture detailed corrections
and integrate with the learning system for continuous improvement.

Features:
- Standard thumbs up/down feedback
- Detailed correction capture for negative feedback
- Integration with CorrectionService
- Real-time error analysis and suggestions
- Priority-based customization and analytics display
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
        custom_message: Optional[str] = None,
        **params,
    ):
        """Initialize the enhanced feedback widget.

        Args:
            query: The original user query
            original_intent_json: The parsed intent JSON (if available)
            original_code: The generated code (if available)
            original_results: The analysis results (if available)
            on_correction_applied: Callback when correction is applied
            custom_message: Custom feedback message based on priority
        """
        super().__init__(**params)

        self.query = query
        self.original_intent_json = original_intent_json or ""
        self.original_code = original_code or ""
        self.original_results = original_results or ""
        self.on_correction_applied = on_correction_applied
        self.custom_message = custom_message or "**Was this answer helpful?**"

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
            pn.pane.Markdown(self.custom_message, margin=(5, 0)),
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
                    WHERE question = ? 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """,
                    (self.query,),
                )
                result = cursor.fetchone()
                return result[0] if result else None

        except Exception as e:
            logger.error(f"Error getting latest feedback ID: {e}")
            return None

    def _show_correction_interface(self):
        """Show the correction interface."""
        self.feedback_section.visible = False
        self.correction_section.visible = True

    def _on_submit_correction(self, event):
        """Handle correction submission."""
        try:
            correct_answer = self.correct_answer_input.value.strip()

            if not correct_answer:
                # Show error message
                self.correct_answer_input.placeholder = (
                    "Please provide a correction before submitting..."
                )
                return

            # Store the correction
            session_id = self.correction_service.capture_correction_session(
                feedback_id=self.feedback_id,
                original_query=self.query,
                human_correct_answer=correct_answer,
                original_intent_json=self.original_intent_json,
                original_code=self.original_code,
                original_results=self.original_results,
            )
            success = session_id is not None

            if success:
                logger.info(f"Correction stored for query: {self.query[:50]}...")
                self.correction_captured = True
                self.correction_session_id = session_id

                # Analyze and show suggestions
                self._analyze_and_show_suggestions()
            else:
                logger.error("Failed to store correction")

        except Exception as e:
            logger.error(f"Error submitting correction: {e}")
            self._show_thank_you()

    def _on_skip_correction(self, event):
        """Handle skipping correction."""
        self._show_thank_you()

    def _analyze_and_show_suggestions(self):
        """Analyze the correction and show suggestions."""
        try:
            # Use the session ID we already have from capture_correction_session
            if not self.correction_session_id:
                logger.warning("No correction session found")
                self._show_thank_you()
                return

            # Analyze the error type
            error_category = self.correction_service.analyze_error_type(
                self.correction_session_id
            )
            logger.info(f"Error category: {error_category}")

            # Generate suggestions
            suggestions = self.correction_service.generate_correction_suggestions(
                self.correction_session_id
            )

            if suggestions:
                logger.info(f"Generated {len(suggestions)} suggestions")
                self._show_suggestions(suggestions)
            else:
                logger.info("No suggestions generated")
                self._show_thank_you()

        except Exception as e:
            logger.error(f"Error analyzing correction: {e}")
            self._show_thank_you()

    def _show_suggestions(self, suggestions: list):
        """Show correction suggestions to the user."""
        try:
            # Hide correction interface
            self.correction_section.visible = False

            # Update analysis section
            analysis_text = self.analysis_section[1]
            analysis_text.object = "**Analysis complete!** Here are some suggestions:"

            # Clear previous suggestions
            suggestions_container = self.analysis_section[2]
            suggestions_container.clear()

            # Add suggestion buttons
            for i, suggestion in enumerate(suggestions):
                suggestion_text = suggestion.get("description", "No description")
                confidence = suggestion.get("confidence", 0.0)

                # Create suggestion button with confidence indicator
                confidence_indicator = (
                    "🟢" if confidence > 0.8 else "🟡" if confidence > 0.6 else "🔴"
                )
                button_text = f"{confidence_indicator} {suggestion_text[:60]}..."

                suggestion_btn = pn.widgets.Button(
                    name=button_text,
                    button_type="primary" if confidence > 0.8 else "default",
                    width=400,
                    margin=(5, 0),
                )

                # Store suggestion data in button for callback
                suggestion_btn._suggestion_data = suggestion

                # Add click handler
                suggestion_btn.on_click(
                    lambda event, s=suggestion: self._apply_suggestion(s)
                )

                suggestions_container.append(suggestion_btn)

            # Add skip button
            skip_btn = pn.widgets.Button(
                name="Skip suggestions",
                button_type="light",
                width=150,
                margin=(10, 0),
            )
            skip_btn.on_click(lambda event: self._show_thank_you())
            suggestions_container.append(skip_btn)

            # Show analysis section
            self.analysis_section.visible = True

        except Exception as e:
            logger.error(f"Error showing suggestions: {e}")
            self._show_thank_you()

    def _apply_suggestion(self, suggestion: Dict[str, Any]):
        """Apply a selected suggestion."""
        try:
            logger.info(f"Applying suggestion: {suggestion.get('type', 'unknown')}")

            # Apply the suggestion through correction service
            success = self.correction_service.apply_correction(
                session_id=self.correction_session_id,
                correction_type=suggestion.get("type", "manual_correction"),
                corrected_intent_json=suggestion.get("corrected_intent_json"),
                corrected_code=suggestion.get("corrected_code"),
            )

            if success:
                logger.info("Suggestion applied successfully")

                # Call the callback if provided
                if self.on_correction_applied:
                    try:
                        self.on_correction_applied(
                            self.correction_session_id, suggestion
                        )
                    except Exception as callback_error:
                        logger.error(f"Error in correction callback: {callback_error}")

                # Show success message
                self.analysis_section.visible = False
                self.thank_you_section[0].object = (
                    "✅ **Suggestion applied successfully!**"
                )
                self.thank_you_section[1].object = (
                    "The assistant has been updated with your correction."
                )
                self.thank_you_section.visible = True

            else:
                logger.error("Failed to apply suggestion")
                self._show_thank_you()

        except Exception as e:
            logger.error(f"Error applying suggestion: {e}")
            self._show_thank_you()

    def _show_thank_you(self):
        """Show thank you message and hide other sections."""
        self.feedback_section.visible = False
        self.correction_section.visible = False
        self.analysis_section.visible = False
        self.thank_you_section.visible = True
        self.feedback_submitted = True

    def view(self) -> pn.Column:
        """Return the complete widget view."""
        return pn.Column(
            self.feedback_section,
            self.correction_section,
            self.analysis_section,
            self.thank_you_section,
            sizing_mode="stretch_width",
        )


class SmartFeedbackWidget(EnhancedFeedbackWidget):
    """Enhanced feedback widget with priority-based customization."""

    def __init__(
        self,
        query: str,
        priority: str = "medium",
        analytics_data: Optional[Dict] = None,
        **params,
    ):
        """Initialize with priority-based customization.

        Args:
            query: The original user query
            priority: Feedback priority level
            analytics_data: Optional analytics data to display
            **params: Additional parameters
        """
        # Set custom message based on priority before calling super().__init__
        custom_message = self._get_priority_message(priority)
        params["custom_message"] = custom_message

        super().__init__(query, **params)
        self.priority = priority
        self.analytics_data = analytics_data or {}

        # Customize widget for priority after initialization
        self._customize_for_priority(priority)

    def _customize_for_priority(self, priority: str):
        """Customize widget appearance based on priority.

        Args:
            priority: Priority level ('high', 'medium', 'low', 'skip')
        """
        try:
            # Add priority indicators
            self._add_priority_indicators(priority)

            # Show analytics if available and priority is medium or high
            if priority in ["medium", "high"] and self.analytics_data:
                self._show_analytics_summary()

        except Exception as e:
            logger.error(f"Error customizing widget for priority {priority}: {e}")

    def _add_priority_indicators(self, priority: str):
        """Add visual indicators based on priority.

        Args:
            priority: Priority level
        """
        try:
            priority_config = {
                "high": {
                    "color": "orange",
                    "icon": "🎯",
                    "border_style": "solid",
                    "border_color": "#ff6b35",
                },
                "medium": {
                    "color": "blue",
                    "icon": "💭",
                    "border_style": "solid",
                    "border_color": "#007bff",
                },
                "low": {
                    "color": "gray",
                    "icon": "👍",
                    "border_style": "dashed",
                    "border_color": "#6c757d",
                },
            }

            config = priority_config.get(priority, priority_config["medium"])

            # Add priority indicator to the feedback message
            if hasattr(self, "feedback_section") and len(self.feedback_section) > 0:
                current_message = self.feedback_section[0].object
                priority_indicator = f"{config['icon']} "

                # Update the message with priority indicator
                self.feedback_section[0].object = priority_indicator + current_message

                # Style the feedback section with priority colors
                self.feedback_section.styles = {
                    "border": f"2px {config['border_style']} {config['border_color']}",
                    "border-radius": "8px",
                    "padding": "10px",
                    # Light background
                    "background-color": f"{config['border_color']}10",
                }

        except Exception as e:
            logger.error(f"Error adding priority indicators: {e}")

    def _show_analytics_summary(self):
        """Show brief analytics summary if available."""
        try:
            if not self.analytics_data:
                return

            # Create analytics summary
            analytics_text = "📊 **System Insights:** "

            # Add key metrics
            if "request_rate" in self.analytics_data:
                request_rate = self.analytics_data["request_rate"]
                analytics_text += f"Request rate: {request_rate:.1%} | "

            if "response_rate" in self.analytics_data:
                response_rate = self.analytics_data["response_rate"]
                analytics_text += f"Response rate: {response_rate:.1%} | "

            if "total_requests" in self.analytics_data:
                total_requests = self.analytics_data["total_requests"]
                analytics_text += f"Total requests: {total_requests}"

            # Add analytics section to the widget
            analytics_section = pn.pane.Markdown(
                analytics_text,
                margin=(0, 0, 5, 0),
                styles={"font-size": "0.9em", "color": "#666"},
            )

            # Insert analytics before the feedback buttons
            if hasattr(self, "feedback_section") and len(self.feedback_section) > 1:
                self.feedback_section.insert(1, analytics_section)

        except Exception as e:
            logger.error(f"Error showing analytics summary: {e}")

    def _get_priority_message(self, priority: str) -> str:
        """Get priority-specific message.

        Args:
            priority: Priority level

        Returns:
            Customized message for the priority level
        """
        priority_messages = {
            "high": "🎯 **Your feedback is especially valuable for this question!**",
            "medium": "💭 **Was this answer helpful?**",
            "low": "👍 **Quick rating appreciated**",
            "skip": "**Feedback not needed for this query**",
        }

        return priority_messages.get(priority, priority_messages["medium"])


def create_enhanced_feedback_widget(
    query: str,
    original_intent_json: Optional[str] = None,
    original_code: Optional[str] = None,
    original_results: Optional[str] = None,
    on_correction_applied: Optional[Callable] = None,
    custom_message: Optional[str] = None,
) -> pn.Column:
    """Create an enhanced feedback widget.

    Args:
        query: The original user query
        original_intent_json: The parsed intent JSON (if available)
        original_code: The generated code (if available)
        original_results: The analysis results (if available)
        on_correction_applied: Callback when correction is applied
        custom_message: Custom feedback message

    Returns:
        Panel Column containing the feedback widget
    """
    widget = EnhancedFeedbackWidget(
        query=query,
        original_intent_json=original_intent_json,
        original_code=original_code,
        original_results=original_results,
        on_correction_applied=on_correction_applied,
        custom_message=custom_message,
    )

    return widget.view()


def create_smart_feedback_widget(
    query: str,
    priority: str = "medium",
    analytics_data: Optional[Dict] = None,
    original_intent_json: Optional[str] = None,
    original_code: Optional[str] = None,
    original_results: Optional[str] = None,
    on_correction_applied: Optional[Callable] = None,
) -> pn.Column:
    """Create a smart feedback widget with priority-based customization.

    Args:
        query: The original user query
        priority: Feedback priority level
        analytics_data: Optional analytics data to display
        original_intent_json: The parsed intent JSON (if available)
        original_code: The generated code (if available)
        original_results: The analysis results (if available)
        on_correction_applied: Callback when correction is applied

    Returns:
        Panel Column containing the smart feedback widget
    """
    widget = SmartFeedbackWidget(
        query=query,
        priority=priority,
        analytics_data=analytics_data,
        original_intent_json=original_intent_json,
        original_code=original_code,
        original_results=original_results,
        on_correction_applied=on_correction_applied,
    )

    return widget.view()
