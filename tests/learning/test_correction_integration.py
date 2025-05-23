"""
Test suite for the correction learning system integration.

Tests the complete flow from feedback capture through correction application
and pattern learning for the AAA learning system.
"""

import pytest
import json
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.correction_service import (
    CorrectionService,
    IntentPattern,
)
from app.utils.enhanced_feedback_widget import EnhancedFeedbackWidget
from app.utils.feedback_db import insert_feedback
from app.utils.query_intent import QueryIntent
from app.utils.db_migrations import apply_pending_migrations


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    try:
        Path(path).unlink()  # Remove the temp file so we can create a clean DB
        apply_pending_migrations(path)
        yield path
    finally:
        if Path(path).exists():
            Path(path).unlink()


@pytest.fixture
def correction_service(temp_db):
    """Create a correction service with test database."""
    return CorrectionService(db_path=temp_db)


@pytest.fixture
def sample_intent():
    """Create a sample QueryIntent for testing."""
    return QueryIntent(
        analysis_type="average",
        target_field="bmi",
        filters=[],
        conditions=[],
        parameters={},
    )


class TestCorrectionService:
    """Test the CorrectionService functionality."""

    def test_capture_correction_session(self, correction_service, temp_db):
        """Test capturing a correction session."""
        # First insert a feedback record
        insert_feedback(
            question="What is the average BMI?",
            rating="down",
            comment="Wrong calculation",
            db_file=temp_db,
        )

        # Get the feedback ID
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1")
            feedback_id = cursor.fetchone()[0]

        # Capture correction session
        session_id = correction_service.capture_correction_session(
            feedback_id=feedback_id,
            original_query="What is the average BMI?",
            human_correct_answer="The average BMI of active patients is 26.5",
            original_intent_json='{"analysis_type": "average", "target_field": "bmi"}',
            original_code="SELECT AVG(bmi) FROM vitals",
            original_results="{'average_bmi': 24.2}",
        )

        assert session_id is not None
        assert session_id > 0

        # Verify the session was stored
        session = correction_service.get_correction_session(session_id)
        assert session is not None
        assert session.original_query == "What is the average BMI?"
        assert (
            session.human_correct_answer == "The average BMI of active patients is 26.5"
        )
        assert session.status == "pending"

    def test_analyze_error_type_missing_filter(self, correction_service, temp_db):
        """Test error analysis for missing filter errors."""
        # Insert feedback
        insert_feedback(
            question="What is the average BMI of active patients?",
            rating="down",
            db_file=temp_db,
        )

        # Get feedback ID
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1")
            feedback_id = cursor.fetchone()[0]

        # Create correction session with intent that's missing active filter
        intent_json = json.dumps(
            {
                "analysis_type": "average",
                "target_field": "bmi",
                "filters": [],  # Missing the active=1 filter
                "conditions": [],
                "parameters": {},
            }
        )

        session_id = correction_service.capture_correction_session(
            feedback_id=feedback_id,
            original_query="What is the average BMI of active patients?",
            human_correct_answer="Should only include active patients",
            original_intent_json=intent_json,
        )

        # Analyze the error
        error_category = correction_service.analyze_error_type(session_id)

        assert error_category == "missing_filter"

        # Verify the session was updated
        session = correction_service.get_correction_session(session_id)
        assert session.error_category == "missing_filter"
        assert session.correction_type == "intent_fix"

    def test_analyze_error_type_wrong_aggregation(self, correction_service, temp_db):
        """Test error analysis for wrong aggregation type."""
        # Insert feedback
        insert_feedback(
            question="Show me BMI distribution", rating="down", db_file=temp_db
        )

        # Get feedback ID
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1")
            feedback_id = cursor.fetchone()[0]

        # Create correction session with wrong analysis type
        intent_json = json.dumps(
            {
                "analysis_type": "average",  # Should be "distribution"
                "target_field": "bmi",
                "filters": [],
                "conditions": [],
                "parameters": {},
            }
        )

        session_id = correction_service.capture_correction_session(
            feedback_id=feedback_id,
            original_query="Show me BMI distribution",
            human_correct_answer="Should show distribution, not average",
            original_intent_json=intent_json,
        )

        # Analyze the error
        error_category = correction_service.analyze_error_type(session_id)

        assert error_category == "wrong_aggregation"

    def test_generate_correction_suggestions(self, correction_service, temp_db):
        """Test generating correction suggestions."""
        # Create a correction session with missing filter error
        insert_feedback(
            question="Average BMI of active patients", rating="down", db_file=temp_db
        )

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1")
            feedback_id = cursor.fetchone()[0]

        session_id = correction_service.capture_correction_session(
            feedback_id=feedback_id,
            original_query="Average BMI of active patients",
            human_correct_answer="Should filter for active patients only",
        )

        # Update with error category
        correction_service.update_correction_session(
            session_id,
            {"error_category": "missing_filter", "correction_type": "intent_fix"},
        )

        # Generate suggestions
        suggestions = correction_service.generate_correction_suggestions(session_id)

        assert len(suggestions) > 0
        assert any(s["type"] == "add_filter" for s in suggestions)
        assert any(s["type"] == "manual_correction" for s in suggestions)

    def test_learn_intent_pattern(self, correction_service, temp_db):
        """Test learning intent patterns from corrections."""
        # Create and process a correction session
        insert_feedback(
            question="How many active patients?", rating="down", db_file=temp_db
        )

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1")
            feedback_id = cursor.fetchone()[0]

        session_id = correction_service.capture_correction_session(
            feedback_id=feedback_id,
            original_query="How many active patients?",
            human_correct_answer="Should count only active patients",
        )

        # Apply correction with corrected intent
        corrected_intent = {
            "analysis_type": "count",
            "target_field": "patients",
            "filters": [{"field": "active", "value": 1}],
            "conditions": [],
            "parameters": {},
        }

        success = correction_service.apply_correction(
            session_id=session_id,
            correction_type="intent_fix",
            corrected_intent_json=json.dumps(corrected_intent),
        )

        assert success

        # Check that a pattern was learned
        patterns = correction_service.find_similar_patterns("how many active patients")
        assert len(patterns) > 0
        assert "active" in patterns[0].query_pattern

    def test_find_similar_patterns(self, correction_service, temp_db):
        """Test finding similar patterns for queries."""
        # First, create some learned patterns
        pattern1 = IntentPattern(
            query_pattern="how many active patients",
            canonical_intent_json='{"analysis_type": "count", "target_field": "patients"}',
            confidence_boost=0.2,
            usage_count=5,
            success_rate=1.0,
        )

        correction_service._store_intent_pattern(pattern1)

        pattern2 = IntentPattern(
            query_pattern="count of patients",
            canonical_intent_json='{"analysis_type": "count", "target_field": "patients"}',
            confidence_boost=0.1,
            usage_count=3,
            success_rate=0.9,
        )

        correction_service._store_intent_pattern(pattern2)

        # Find similar patterns
        similar = correction_service.find_similar_patterns(
            "how many patients are active"
        )

        assert len(similar) > 0
        # Should find the first pattern due to higher usage count
        assert similar[0].query_pattern == "how many active patients"

    def test_get_learning_metrics(self, correction_service, temp_db):
        """Test retrieving learning metrics."""
        # Create some correction sessions and patterns
        insert_feedback("Test query 1", "down", db_file=temp_db)
        insert_feedback("Test query 2", "down", db_file=temp_db)

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM assistant_feedback ORDER BY id LIMIT 2")
            feedback_ids = [row[0] for row in cursor.fetchall()]

        # Create correction sessions
        session1_id = correction_service.capture_correction_session(
            feedback_id=feedback_ids[0],
            original_query="Test query 1",
            human_correct_answer="Correct answer 1",
        )

        session2_id = correction_service.capture_correction_session(
            feedback_id=feedback_ids[1],
            original_query="Test query 2",
            human_correct_answer="Correct answer 2",
        )

        # Mark one as integrated
        correction_service.update_correction_session(
            session1_id, {"status": "integrated"}
        )

        # Add a learned pattern
        pattern = IntentPattern(
            query_pattern="test pattern",
            canonical_intent_json='{"analysis_type": "count"}',
            usage_count=10,
            success_rate=0.95,
        )
        correction_service._store_intent_pattern(pattern)

        # Get metrics
        metrics = correction_service.get_learning_metrics(days=30)

        assert metrics["correction_sessions"]["total"] == 2
        assert metrics["correction_sessions"]["integrated"] == 1
        assert metrics["learned_patterns"]["total"] == 1
        assert metrics["learned_patterns"]["total_usage"] == 10


class TestEnhancedFeedbackWidget:
    """Test the enhanced feedback widget functionality."""

    @patch("app.utils.enhanced_feedback_widget.insert_feedback")
    def test_positive_feedback(self, mock_insert, temp_db):
        """Test positive feedback flow."""
        mock_insert.return_value = True

        widget = EnhancedFeedbackWidget(
            query="What is the average BMI?",
            original_intent_json='{"analysis_type": "average", "target_field": "bmi"}',
        )

        # Simulate thumbs up click
        widget._on_thumbs_up(None)

        # Verify feedback was recorded
        mock_insert.assert_called_once_with(
            question="What is the average BMI?", rating="up"
        )

        # Verify UI state
        assert widget.feedback_submitted
        assert widget.thank_you_section.visible

    @patch("app.utils.enhanced_feedback_widget.insert_feedback")
    def test_negative_feedback_flow(self, mock_insert, temp_db):
        """Test negative feedback flow with correction capture."""
        mock_insert.return_value = True

        # Mock the feedback ID retrieval
        with patch.object(
            EnhancedFeedbackWidget, "_get_latest_feedback_id", return_value=123
        ):
            widget = EnhancedFeedbackWidget(
                query="What is the average BMI?",
                original_intent_json='{"analysis_type": "average", "target_field": "bmi"}',
                original_code="SELECT AVG(bmi) FROM vitals",
            )

            # Simulate thumbs down click
            widget._on_thumbs_down(None)

            # Verify feedback was recorded
            mock_insert.assert_called_once_with(
                question="What is the average BMI?", rating="down"
            )

            # Verify correction interface is shown
            assert not widget.feedback_section.visible
            assert widget.correction_section.visible

    def test_correction_submission(self, temp_db):
        """Test correction submission and analysis."""
        # Create widget with mock correction service
        with patch(
            "app.utils.enhanced_feedback_widget.CorrectionService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.capture_correction_session.return_value = 456
            mock_service.analyze_error_type.return_value = "missing_filter"
            mock_service.generate_correction_suggestions.return_value = [
                {
                    "type": "add_filter",
                    "description": "Add patient status filter",
                    "action": "Add active filter",
                }
            ]

            widget = EnhancedFeedbackWidget(
                query="What is the average BMI of active patients?",
                original_intent_json='{"analysis_type": "average", "target_field": "bmi"}',
            )
            widget.feedback_id = 123

            # Set correction text
            widget.correct_answer_input.value = "Should only include active patients"

            # Submit correction
            widget._on_submit_correction(None)

            # Verify correction session was created
            mock_service.capture_correction_session.assert_called_once()

            # Verify analysis was performed
            mock_service.analyze_error_type.assert_called_once_with(456)

            # Verify suggestions were generated
            mock_service.generate_correction_suggestions.assert_called_once_with(456)

            # Verify UI shows analysis section
            assert widget.analysis_section.visible


class TestIntegrationFlow:
    """Test the complete integration flow."""

    def test_complete_correction_flow(self, temp_db):
        """Test the complete flow from feedback to learned pattern."""
        # Initialize correction service
        correction_service = CorrectionService(db_path=temp_db)

        # Step 1: Insert negative feedback
        insert_feedback(
            question="How many active patients are there?",
            rating="down",
            comment="Missing active filter",
            db_file=temp_db,
        )

        # Get feedback ID
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1")
            feedback_id = cursor.fetchone()[0]

        # Step 2: Capture correction session
        original_intent = {
            "analysis_type": "count",
            "target_field": "patients",
            "filters": [],  # Missing active filter
            "conditions": [],
            "parameters": {},
        }

        session_id = correction_service.capture_correction_session(
            feedback_id=feedback_id,
            original_query="How many active patients are there?",
            human_correct_answer="Should count only active patients",
            original_intent_json=json.dumps(original_intent),
        )

        # Step 3: Analyze error
        error_category = correction_service.analyze_error_type(session_id)
        assert error_category == "missing_filter"

        # Step 4: Apply correction
        corrected_intent = {
            "analysis_type": "count",
            "target_field": "patients",
            "filters": [{"field": "active", "value": 1}],
            "conditions": [],
            "parameters": {},
        }

        success = correction_service.apply_correction(
            session_id=session_id,
            correction_type="intent_fix",
            corrected_intent_json=json.dumps(corrected_intent),
        )

        assert success

        # Step 5: Verify pattern was learned
        patterns = correction_service.find_similar_patterns("how many active patients")
        assert len(patterns) > 0

        learned_intent = json.loads(patterns[0].canonical_intent_json)
        assert learned_intent["analysis_type"] == "count"
        assert len(learned_intent["filters"]) == 1
        assert learned_intent["filters"][0]["field"] == "active"

        # Step 6: Verify session status
        session = correction_service.get_correction_session(session_id)
        assert session.status == "integrated"

        # Step 7: Check metrics
        metrics = correction_service.get_learning_metrics()
        assert metrics["correction_sessions"]["total"] >= 1
        assert metrics["correction_sessions"]["integrated"] >= 1
        assert metrics["learned_patterns"]["total"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
