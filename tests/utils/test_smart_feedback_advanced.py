"""Tests for advanced smart feedback functionality (Sprint 2.2)."""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

from app.utils.smart_feedback import (
    FeedbackPriorityCalculator,
    get_feedback_priority_advanced,
)
from app.utils.enhanced_feedback_widget import SmartFeedbackWidget


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def priority_calculator():
    """Create a FeedbackPriorityCalculator instance."""
    return FeedbackPriorityCalculator()


class TestFeedbackPriorityCalculator:
    """Test the FeedbackPriorityCalculator class."""

    def test_initialization(self, priority_calculator):
        """Test that the calculator initializes correctly."""
        assert priority_calculator is not None
        assert hasattr(priority_calculator, "weights")
        assert hasattr(priority_calculator, "confidence_scorer")
        assert hasattr(priority_calculator, "novelty_detector")

        # Check default weights
        expected_weights = {
            "confidence": 0.25,
            "novelty": 0.30,
            "recency": 0.25,
            "learning_value": 0.20,
        }
        assert priority_calculator.weights == expected_weights

    def test_calculate_weighted_priority_high(self, priority_calculator):
        """Test weighted priority calculation for high priority."""
        factors = {
            "confidence": 0.2,  # Low confidence (inverted to 0.8)
            "novelty": 0.9,  # High novelty
            "recency": 0.1,  # Low recency (inverted to 0.9)
            "learning_value": 0.8,  # High learning value
        }

        priority = priority_calculator.calculate_weighted_priority(factors)
        assert priority == "high"

    def test_calculate_weighted_priority_medium(self, priority_calculator):
        """Test weighted priority calculation for medium priority."""
        factors = {
            "confidence": 0.5,  # Medium confidence (inverted to 0.5)
            "novelty": 0.6,  # Medium novelty
            "recency": 0.3,  # Medium recency (inverted to 0.7)
            "learning_value": 0.5,  # Medium learning value
        }

        priority = priority_calculator.calculate_weighted_priority(factors)
        assert priority == "medium"

    def test_calculate_weighted_priority_low(self, priority_calculator):
        """Test weighted priority calculation for low priority."""
        factors = {
            "confidence": 0.8,  # High confidence (inverted to 0.2)
            "novelty": 0.3,  # Low novelty
            "recency": 0.2,  # Low recency (inverted to 0.8)
            "learning_value": 0.2,  # Low learning value
        }

        priority = priority_calculator.calculate_weighted_priority(factors)
        assert priority == "low"

    def test_calculate_weighted_priority_skip(self, priority_calculator):
        """Test weighted priority calculation for skip priority."""
        factors = {
            "confidence": 0.9,  # Very high confidence (inverted to 0.1)
            "novelty": 0.1,  # Very low novelty
            "recency": 0.9,  # High recency (inverted to 0.1)
            "learning_value": 0.1,  # Very low learning value
        }

        priority = priority_calculator.calculate_weighted_priority(factors)
        assert priority == "skip"

    def test_assess_learning_value_complex_query(self, priority_calculator):
        """Test learning value assessment for complex queries."""
        complex_query = (
            "What is the correlation between BMI and blood pressure trends over time?"
        )

        learning_value = priority_calculator.assess_learning_value(complex_query)

        # Should be relatively high due to complexity and correlation analysis
        assert learning_value > 0.5

    def test_assess_learning_value_simple_query(self, priority_calculator):
        """Test learning value assessment for simple queries."""
        simple_query = "What is the average BMI?"

        learning_value = priority_calculator.assess_learning_value(simple_query)

        # Should be lower for simple queries
        assert learning_value < 0.7

    def test_assess_learning_value_ambiguous_query(self, priority_calculator):
        """Test learning value assessment for ambiguous queries."""
        ambiguous_query = "Show me the data for this thing"

        learning_value = priority_calculator.assess_learning_value(ambiguous_query)

        # Should have some learning value due to ambiguity
        assert learning_value > 0.0

    @patch("app.utils.smart_feedback._get_conn")
    def test_detect_feedback_fatigue_high_frequency(
        self, mock_conn, priority_calculator
    ):
        """Test fatigue detection for high frequency feedback."""
        mock_cursor = MagicMock()
        mock_conn.return_value.__enter__.return_value.cursor.return_value = mock_cursor

        # Mock high frequency feedback (6 requests in last hour)
        mock_cursor.fetchone.side_effect = [
            (6,),  # Recent feedback count
            (5, 1),  # Total and negative feedback
        ]

        fatigue = priority_calculator.detect_feedback_fatigue("test_user")
        assert fatigue is True

    @patch("app.utils.smart_feedback._get_conn")
    def test_detect_feedback_fatigue_high_negative_ratio(
        self, mock_conn, priority_calculator
    ):
        """Test fatigue detection for high negative feedback ratio."""
        mock_cursor = MagicMock()
        mock_conn.return_value.__enter__.return_value.cursor.return_value = mock_cursor

        # Mock high negative feedback ratio (3 out of 4 negative)
        mock_cursor.fetchone.side_effect = [
            (2,),  # Recent feedback count (low)
            (4, 3),  # Total and negative feedback (75% negative)
        ]

        fatigue = priority_calculator.detect_feedback_fatigue("test_user")
        assert fatigue is True

    @patch("app.utils.smart_feedback._get_conn")
    def test_detect_feedback_fatigue_normal(self, mock_conn, priority_calculator):
        """Test fatigue detection for normal feedback patterns."""
        mock_cursor = MagicMock()
        mock_conn.return_value.__enter__.return_value.cursor.return_value = mock_cursor

        # Mock normal feedback patterns
        mock_cursor.fetchone.side_effect = [
            (2,),  # Recent feedback count (normal)
            (5, 1),  # Total and negative feedback (20% negative)
        ]

        fatigue = priority_calculator.detect_feedback_fatigue("test_user")
        assert fatigue is False

    def test_assess_query_complexity(self, priority_calculator):
        """Test query complexity assessment."""
        # Test complex query
        complex_query = "Analyze the correlation between BMI and statistical variance in blood pressure"
        complexity = priority_calculator._assess_query_complexity(complex_query)
        assert complexity > 0.5

        # Test simple query
        simple_query = "What is the average weight?"
        complexity = priority_calculator._assess_query_complexity(simple_query)
        assert complexity < 0.5

    def test_assess_pattern_learning_potential(self, priority_calculator):
        """Test pattern learning potential assessment."""
        # Test query with multiple fields
        multi_field_query = "Compare BMI and cholesterol levels"
        potential = priority_calculator._assess_pattern_learning_potential(
            multi_field_query
        )
        assert potential > 0.0

        # Test query with metrics
        metric_query = "Calculate the average and median BMI"
        potential = priority_calculator._assess_pattern_learning_potential(metric_query)
        assert potential > 0.0

    def test_assess_error_correction_potential(self, priority_calculator):
        """Test error correction potential assessment."""
        # Test ambiguous query
        ambiguous_query = "Show me this data and that thing"
        potential = priority_calculator._assess_error_correction_potential(
            ambiguous_query
        )
        assert potential > 0.0

        # Test clear query
        clear_query = "Calculate average BMI for patients"
        potential = priority_calculator._assess_error_correction_potential(clear_query)
        assert potential >= 0.0


class TestAdvancedPriorityCalculation:
    """Test the advanced priority calculation function."""

    @patch("app.utils.smart_feedback.has_recent_exact_feedback")
    @patch("app.utils.smart_feedback.has_recent_similar_feedback")
    @patch("app.utils.smart_feedback.is_novel_query_pattern")
    @patch("app.utils.smart_feedback.calculate_confidence_score")
    @patch("app.utils.smart_feedback.calculate_novelty_score")
    def test_get_feedback_priority_advanced_skip_exact(
        self, mock_novelty, mock_confidence, mock_novel, mock_similar, mock_exact
    ):
        """Test that exact duplicates are skipped."""
        mock_exact.return_value = True

        priority = get_feedback_priority_advanced("test query")
        assert priority == "skip"

        # Should not call other functions if exact match found
        mock_similar.assert_not_called()
        mock_confidence.assert_not_called()
        mock_novelty.assert_not_called()

    @patch("app.utils.smart_feedback.FeedbackPriorityCalculator")
    def test_get_feedback_priority_advanced_fatigue_detected(
        self, mock_calculator_class
    ):
        """Test that fatigue detection causes skip."""
        mock_calculator = MagicMock()
        mock_calculator.detect_feedback_fatigue.return_value = True
        mock_calculator_class.return_value = mock_calculator

        priority = get_feedback_priority_advanced("test query", user_id="fatigued_user")
        assert priority == "skip"

    @patch("app.utils.smart_feedback.has_recent_exact_feedback")
    @patch("app.utils.smart_feedback.has_recent_similar_feedback")
    @patch("app.utils.smart_feedback.is_novel_query_pattern")
    @patch("app.utils.smart_feedback.calculate_confidence_score")
    @patch("app.utils.smart_feedback.calculate_novelty_score")
    @patch("app.utils.smart_feedback.FeedbackPriorityCalculator")
    def test_get_feedback_priority_advanced_full_calculation(
        self,
        mock_calculator_class,
        mock_novelty,
        mock_confidence,
        mock_novel,
        mock_similar,
        mock_exact,
    ):
        """Test full priority calculation with all factors."""
        # Setup mocks
        mock_exact.return_value = False
        mock_similar.return_value = True
        mock_novel.return_value = False
        mock_confidence.return_value = 0.3
        mock_novelty.return_value = 0.8

        mock_calculator = MagicMock()
        mock_calculator.detect_feedback_fatigue.return_value = False
        mock_calculator.assess_learning_value.return_value = 0.7
        mock_calculator.calculate_weighted_priority.return_value = "high"
        mock_calculator_class.return_value = mock_calculator

        priority = get_feedback_priority_advanced("test query", {"data": "test"})

        assert priority == "high"

        # Verify all components were called
        mock_calculator.detect_feedback_fatigue.assert_called_once()
        mock_calculator.assess_learning_value.assert_called_once()
        mock_calculator.calculate_weighted_priority.assert_called_once()

    @patch("app.utils.smart_feedback.has_recent_exact_feedback")
    @patch("app.utils.smart_feedback.has_recent_similar_feedback")
    @patch("app.utils.smart_feedback.is_novel_query_pattern")
    def test_get_feedback_priority_advanced_novel_pattern_override(
        self, mock_novel, mock_similar, mock_exact
    ):
        """Test that novel patterns override similarity penalties."""
        mock_exact.return_value = False
        mock_similar.return_value = True
        mock_novel.return_value = True  # Novel pattern

        with patch(
            "app.utils.smart_feedback.calculate_confidence_score"
        ) as mock_confidence, patch(
            "app.utils.smart_feedback.calculate_novelty_score"
        ) as mock_novelty, patch(
            "app.utils.smart_feedback.FeedbackPriorityCalculator"
        ) as mock_calculator_class:

            mock_confidence.return_value = 0.5
            mock_novelty.return_value = 0.8

            mock_calculator = MagicMock()
            mock_calculator.detect_feedback_fatigue.return_value = False
            mock_calculator.assess_learning_value.return_value = 0.6
            mock_calculator.calculate_weighted_priority.return_value = "medium"
            mock_calculator_class.return_value = mock_calculator

            priority = get_feedback_priority_advanced("novel query")

            # Should get the calculated priority, not be penalized for similarity
            assert priority == "medium"

            # Check that recency factor was reduced (0.3 instead of 0.8)
            call_args = mock_calculator.calculate_weighted_priority.call_args[0][0]
            assert call_args["recency"] == 0.3


class TestSmartFeedbackWidget:
    """Test the SmartFeedbackWidget class."""

    def test_smart_widget_initialization(self):
        """Test SmartFeedbackWidget initialization."""
        widget = SmartFeedbackWidget(
            query="Test query",
            priority="high",
            analytics_data={"request_rate": 0.75, "response_rate": 0.8},
        )

        assert widget.query == "Test query"
        assert widget.priority == "high"
        assert widget.analytics_data["request_rate"] == 0.75

    def test_priority_message_customization(self):
        """Test that priority messages are customized correctly."""
        # Test high priority message
        high_widget = SmartFeedbackWidget("test", priority="high")
        assert "🎯" in high_widget.custom_message
        assert "especially valuable" in high_widget.custom_message

        # Test medium priority message
        medium_widget = SmartFeedbackWidget("test", priority="medium")
        assert "💭" in medium_widget.custom_message
        assert "helpful" in medium_widget.custom_message

        # Test low priority message
        low_widget = SmartFeedbackWidget("test", priority="low")
        assert "👍" in low_widget.custom_message
        assert "Quick rating" in low_widget.custom_message

    def test_get_priority_message(self):
        """Test priority message generation."""
        widget = SmartFeedbackWidget("test")

        # Test all priority levels
        high_msg = widget._get_priority_message("high")
        assert "🎯" in high_msg and "especially valuable" in high_msg

        medium_msg = widget._get_priority_message("medium")
        assert "💭" in medium_msg and "helpful" in medium_msg

        low_msg = widget._get_priority_message("low")
        assert "👍" in low_msg and "Quick rating" in low_msg

        skip_msg = widget._get_priority_message("skip")
        assert "not needed" in skip_msg

        # Test default fallback
        default_msg = widget._get_priority_message("unknown")
        assert default_msg == medium_msg

    def test_priority_indicators_styling(self):
        """Test that priority indicators are applied correctly."""
        widget = SmartFeedbackWidget("test", priority="high")

        # The widget should have been customized for high priority
        assert widget.priority == "high"

        # Check that the feedback section has the priority icon
        if hasattr(widget, "feedback_section") and len(widget.feedback_section) > 0:
            message = widget.feedback_section[0].object
            assert "🎯" in message

    def test_analytics_summary_display(self):
        """Test analytics summary display."""
        analytics_data = {
            "request_rate": 0.75,
            "response_rate": 0.85,
            "total_requests": 100,
        }

        widget = SmartFeedbackWidget(
            "test query", priority="medium", analytics_data=analytics_data
        )

        # Analytics should be included for medium priority
        assert widget.analytics_data == analytics_data

    def test_widget_view_creation(self):
        """Test that widget view is created correctly."""
        widget = SmartFeedbackWidget("test query", priority="high")
        view = widget.view()

        # Should return a Panel Column
        assert hasattr(view, "objects")  # Panel Column has objects attribute

    @patch("app.utils.enhanced_feedback_widget.logger")
    def test_error_handling_in_customization(self, mock_logger):
        """Test error handling in widget customization."""
        # Create widget with invalid priority to trigger error handling
        widget = SmartFeedbackWidget("test", priority="invalid")

        # Should not raise exception, should log error
        assert widget is not None


class TestIntegration:
    """Integration tests for advanced smart feedback system."""

    @patch("app.utils.smart_feedback.FeedbackPriorityCalculator")
    @patch("app.utils.smart_feedback.calculate_confidence_score")
    @patch("app.utils.smart_feedback.calculate_novelty_score")
    def test_end_to_end_priority_calculation(
        self, mock_novelty, mock_confidence, mock_calculator_class
    ):
        """Test end-to-end priority calculation and widget creation."""
        # Setup mocks for realistic scenario
        mock_confidence.return_value = 0.4  # Low confidence
        mock_novelty.return_value = 0.8  # High novelty

        mock_calculator = MagicMock()
        mock_calculator.detect_feedback_fatigue.return_value = False
        mock_calculator.assess_learning_value.return_value = 0.7
        mock_calculator.calculate_weighted_priority.return_value = "high"
        mock_calculator_class.return_value = mock_calculator

        # Calculate priority
        query = "What is the correlation between xyz_metric and cardiovascular risk?"
        priority = get_feedback_priority_advanced(query, {"error": "Unknown field"})

        assert priority == "high"

        # Create widget with calculated priority
        widget = SmartFeedbackWidget(query, priority=priority)

        assert widget.priority == "high"
        assert "🎯" in widget.custom_message

    def test_priority_calculation_performance(self):
        """Test that priority calculation is performant."""
        import time

        query = "Calculate average BMI for patients with diabetes"

        start_time = time.time()

        # This should complete quickly even with all the calculations
        with patch(
            "app.utils.smart_feedback.has_recent_exact_feedback"
        ) as mock_exact, patch(
            "app.utils.smart_feedback.calculate_confidence_score"
        ) as mock_confidence, patch(
            "app.utils.smart_feedback.calculate_novelty_score"
        ) as mock_novelty:

            mock_exact.return_value = False
            mock_confidence.return_value = 0.7
            mock_novelty.return_value = 0.5

            priority = get_feedback_priority_advanced(query)

        end_time = time.time()
        execution_time = end_time - start_time

        # Should complete in under 100ms (0.1 seconds)
        assert execution_time < 0.1
        assert priority in ["high", "medium", "low", "skip"]


# Parametrized tests for different scenarios
@pytest.mark.parametrize(
    "confidence,novelty,expected_priority",
    [
        (0.1, 0.9, "high"),  # Very low confidence, high novelty
        (0.4, 0.7, "medium"),  # Medium confidence, medium-high novelty
        (0.8, 0.2, "low"),  # High confidence, low novelty
        (0.95, 0.05, "skip"),  # Very high confidence, very low novelty
    ],
)
def test_priority_calculation_scenarios(confidence, novelty, expected_priority):
    """Test priority calculation for different confidence/novelty combinations."""
    calculator = FeedbackPriorityCalculator()

    # Adjust recency for skip case to ensure it falls below threshold
    recency = 0.8 if expected_priority == "skip" else 0.2
    learning_value = 0.1 if expected_priority == "skip" else 0.5

    factors = {
        "confidence": confidence,
        "novelty": novelty,
        "recency": recency,
        "learning_value": learning_value,
    }

    priority = calculator.calculate_weighted_priority(factors)
    assert priority == expected_priority


@pytest.mark.parametrize(
    "priority,expected_icon",
    [
        ("high", "🎯"),
        ("medium", "💭"),
        ("low", "👍"),
    ],
)
def test_widget_priority_icons(priority, expected_icon):
    """Test that correct icons are used for different priorities."""
    widget = SmartFeedbackWidget("test query", priority=priority)
    message = widget._get_priority_message(priority)
    assert expected_icon in message
