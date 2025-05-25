"""
Comprehensive integration tests for the complete correction learning system.
Tests the full workflow from feedback capture through pattern learning.
"""

import pytest
import json
import tempfile
import sqlite3
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.correction_service import (
    CorrectionService,
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

        # Check suggestion structure
        for suggestion in suggestions:
            assert "type" in suggestion
            assert "description" in suggestion
            assert "action" in suggestion

    def test_apply_correction(self, correction_service, temp_db):
        """Test applying a correction."""
        # Create correction session
        insert_feedback(question="test query", rating="down", db_file=temp_db)

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1")
            feedback_id = cursor.fetchone()[0]

        session_id = correction_service.capture_correction_session(
            feedback_id=feedback_id,
            original_query="test query",
            human_correct_answer="test answer",
        )

        # Apply correction
        result = correction_service.apply_correction(
            session_id=session_id,
            correction_type="manual_correction",
            corrected_intent_json='{"analysis_type": "corrected"}',
        )

        assert result is True

        # Verify session was updated
        session = correction_service.get_correction_session(session_id)
        assert session.status == "integrated"

    def test_learn_intent_pattern(self, correction_service, temp_db):
        """Test learning intent patterns from corrections."""
        # Create and apply a correction
        insert_feedback(question="average BMI active", rating="down", db_file=temp_db)

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1")
            feedback_id = cursor.fetchone()[0]

        session_id = correction_service.capture_correction_session(
            feedback_id=feedback_id,
            original_query="average BMI active",
            human_correct_answer="Should include active filter",
            original_intent_json='{"analysis_type": "average", "target_field": "bmi", "filters": []}',
        )

        # Apply correction with corrected intent
        corrected_intent = {
            "analysis_type": "average",
            "target_field": "bmi",
            "filters": [{"field": "active", "operator": "=", "value": 1}],
        }

        correction_service.apply_correction(
            session_id=session_id,
            correction_type="intent_fix",
            corrected_intent_json=json.dumps(corrected_intent),
        )

        # Check that pattern was learned
        patterns = correction_service.find_similar_patterns("average BMI active")
        assert len(patterns) > 0
        assert patterns[0].usage_count >= 1

    def test_find_similar_patterns(self, correction_service, temp_db):
        """Test finding similar patterns."""
        # Create a pattern first
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO intent_patterns 
                (query_pattern, canonical_intent_json, confidence_boost, usage_count, success_rate)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    "average bmi active",
                    '{"analysis_type": "average", "target_field": "bmi", "filters": [{"field": "active", "value": 1}]}',
                    0.2,
                    5,
                    0.9,
                ),
            )

        # Test finding similar patterns
        patterns = correction_service.find_similar_patterns(
            "average BMI for active patients"
        )
        assert len(patterns) > 0
        assert patterns[0].success_rate == 0.9

        # Test with exact match
        patterns = correction_service.find_similar_patterns("average bmi active")
        assert len(patterns) > 0

    def test_get_learning_metrics(self, correction_service, temp_db):
        """Test getting learning metrics."""
        # Create some test data
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()

            # Add some patterns
            cursor.execute(
                """
                INSERT INTO intent_patterns 
                (query_pattern, canonical_intent_json, usage_count, success_rate)
                VALUES (?, ?, ?, ?)
            """,
                ("test pattern", '{"test": "data"}', 3, 0.8),
            )

            # Add some correction sessions
            cursor.execute(
                """
                INSERT INTO correction_sessions 
                (original_query, human_correct_answer, status)
                VALUES (?, ?, ?)
            """,
                ("test query", "test answer", "integrated"),
            )

        # Get metrics
        metrics = correction_service.get_learning_metrics()

        assert "patterns" in metrics
        assert "corrections" in metrics
        assert "cache" in metrics

        assert metrics["patterns"]["total"] >= 1
        assert metrics["corrections"]["total"] >= 1


class TestEnhancedFeedbackWidget:
    """Test the enhanced feedback widget integration."""

    @patch("app.utils.enhanced_feedback_widget.insert_feedback")
    def test_positive_feedback(self, mock_insert, temp_db):
        """Test positive feedback submission."""
        widget = EnhancedFeedbackWidget(
            query="test query",
            original_intent_json='{"test": "intent"}',
            original_code="SELECT * FROM test",
        )

        # Simulate positive feedback
        widget._on_thumbs_up(None)

        # Should call insert_feedback with positive rating
        mock_insert.assert_called_once()
        args = mock_insert.call_args[1]
        assert args["rating"] == "up"

    @patch("app.utils.enhanced_feedback_widget.insert_feedback")
    def test_negative_feedback_flow(self, mock_insert, temp_db):
        """Test negative feedback flow with correction interface."""
        widget = EnhancedFeedbackWidget(
            query="test query",
            original_intent_json='{"test": "intent"}',
            original_code="SELECT * FROM test",
        )

        # Simulate negative feedback
        widget._on_thumbs_down(None)

        # Should show correction interface
        assert widget.correction_section.visible is True

        # Should call insert_feedback with negative rating
        mock_insert.assert_called_once()
        args = mock_insert.call_args[1]
        assert args["rating"] == "down"

    def test_correction_submission(self, temp_db):
        """Test correction submission workflow."""
        with patch(
            "app.utils.enhanced_feedback_widget.CorrectionService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.capture_correction_session.return_value = 123
            mock_service.analyze_error_type.return_value = "missing_filter"
            mock_service.generate_correction_suggestions.return_value = [
                {
                    "type": "add_filter",
                    "description": "Add active=1 filter",
                    "action": "Add Filter(field='active', value=1) to intent.filters",
                }
            ]

            widget = EnhancedFeedbackWidget(
                query="test query",
                original_intent_json='{"analysis_type": "average"}',
                original_code="SELECT AVG(bmi) FROM vitals",
            )

            # Simulate correction submission
            widget.feedback_id = 123
            widget.correct_answer_input.value = "Should include active filter"
            widget._on_submit_correction(None)

            # Verify service calls
            mock_service.capture_correction_session.assert_called_once()
            mock_service.analyze_error_type.assert_called_once()
            mock_service.generate_correction_suggestions.assert_called_once()


class TestIntegrationFlow:
    """Test complete integration workflows."""

    def test_complete_correction_flow(self, temp_db):
        """Test the complete flow from feedback to pattern learning."""
        correction_service = CorrectionService(db_path=temp_db)

        # 1. Simulate initial query with incorrect result
        original_query = "What is the average BMI of active patients?"
        original_intent = {
            "analysis_type": "average",
            "target_field": "bmi",
            "filters": [],  # Missing active filter
            "conditions": [],
            "parameters": {},
        }
        original_code = "SELECT AVG(bmi) FROM vitals"
        original_results = '{"average_bmi": 24.2}'

        # 2. User provides negative feedback
        insert_feedback(
            question=original_query,
            rating="down",
            comment="Should only include active patients",
            db_file=temp_db,
        )

        # Get feedback ID
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1")
            feedback_id = cursor.fetchone()[0]

        # 3. Create correction session
        session_id = correction_service.capture_correction_session(
            feedback_id=feedback_id,
            original_query=original_query,
            human_correct_answer="Should filter for active patients only",
            original_intent_json=json.dumps(original_intent),
            original_code=original_code,
            original_results=original_results,
        )

        assert session_id is not None

        # 4. Analyze error type
        error_category = correction_service.analyze_error_type(session_id)
        assert error_category == "missing_filter"

        # 5. Generate suggestions
        suggestions = correction_service.generate_correction_suggestions(session_id)
        assert len(suggestions) > 0

        # Find the add filter suggestion
        filter_suggestion = next(
            (s for s in suggestions if s["type"] == "add_filter"), None
        )
        assert filter_suggestion is not None

        # 6. Apply correction
        corrected_intent = {
            "analysis_type": "average",
            "target_field": "bmi",
            "filters": [{"field": "active", "operator": "=", "value": 1}],
            "conditions": [],
            "parameters": {},
        }

        result = correction_service.apply_correction(
            session_id, "intent_fix", corrected_intent_json=json.dumps(corrected_intent)
        )
        assert result is True

        # 7. Verify pattern was learned
        patterns = correction_service.find_similar_patterns(original_query)
        assert len(patterns) > 0
        assert patterns[0].success_rate == 1.0

        # 8. Test pattern matching on similar query
        similar_query = "average BMI for active patients"
        similar_patterns = correction_service.find_similar_patterns(similar_query)
        assert len(similar_patterns) > 0

        # Verify the pattern has correct intent
        corrected_intent_loaded = json.loads(similar_patterns[0].canonical_intent_json)
        assert len(corrected_intent_loaded.get("filters", [])) > 0

    def test_pattern_learning_accuracy(self, temp_db):
        """Test that pattern learning improves accuracy over time."""
        correction_service = CorrectionService(db_path=temp_db)
        base_query = "count active patients"

        # Create multiple correction sessions for similar queries
        queries_and_corrections = [
            ("count active patients", "Should count only active=1"),
            ("how many active patients", "Should filter by active status"),
            ("number of active patients", "Include only active patients in count"),
        ]

        for query, correction in queries_and_corrections:
            # Create feedback and session
            insert_feedback(question=query, rating="down", db_file=temp_db)

            with sqlite3.connect(temp_db) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1"
                )
                feedback_id = cursor.fetchone()[0]

            session_id = correction_service.capture_correction_session(
                feedback_id=feedback_id,
                original_query=query,
                human_correct_answer=correction,
                original_intent_json=json.dumps(
                    {
                        "analysis_type": "count",
                        "target_field": "patients",
                        "filters": [],
                    }
                ),
            )

            # Analyze and apply correction
            correction_service.analyze_error_type(session_id)

            # Apply correction with proper intent
            corrected_intent = {
                "analysis_type": "count",
                "target_field": "patients",
                "filters": [{"field": "active", "operator": "=", "value": 1}],
            }

            correction_service.apply_correction(
                session_id,
                "intent_fix",
                corrected_intent_json=json.dumps(corrected_intent),
            )

        # Test that system learned the pattern
        patterns = correction_service.find_similar_patterns("count active patients")
        assert len(patterns) > 0
        assert patterns[0].usage_count >= 1
        assert patterns[0].success_rate > 0.8

    def test_query_routing_performance(self, temp_db):
        """Test query routing performance and accuracy."""
        correction_service = CorrectionService(db_path=temp_db)

        # Create a learned pattern first
        insert_feedback(question="average BMI active", rating="down", db_file=temp_db)

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1")
            feedback_id = cursor.fetchone()[0]

        session_id = correction_service.capture_correction_session(
            feedback_id=feedback_id,
            original_query="average BMI active",
            human_correct_answer="Should include active filter",
            original_intent_json=json.dumps(
                {"analysis_type": "average", "target_field": "bmi", "filters": []}
            ),
        )

        correction_service.analyze_error_type(session_id)

        corrected_intent = {
            "analysis_type": "average",
            "target_field": "bmi",
            "filters": [{"field": "active", "operator": "=", "value": 1}],
        }

        correction_service.apply_correction(
            session_id, "intent_fix", corrected_intent_json=json.dumps(corrected_intent)
        )

        # Test pattern lookup performance
        start_time = time.time()
        patterns = correction_service.find_similar_patterns(
            "average BMI for active patients"
        )
        lookup_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        assert lookup_time < 100  # Should be under 100ms
        assert len(patterns) > 0

    def test_error_handling_robustness(self, temp_db):
        """Test system robustness with invalid inputs and edge cases."""
        correction_service = CorrectionService(db_path=temp_db)

        # Test with invalid session ID
        result = correction_service.apply_correction(99999, "invalid_correction")
        assert result is False

        # Test with malformed intent JSON
        insert_feedback(question="test query", rating="down", db_file=temp_db)
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1")
            feedback_id = cursor.fetchone()[0]

        session_id = correction_service.capture_correction_session(
            feedback_id=feedback_id,
            original_query="test query",
            human_correct_answer="test answer",
            original_intent_json="invalid json",
        )

        # Should handle gracefully
        error_category = correction_service.analyze_error_type(session_id)
        assert error_category in ["intent_parse_error", "unknown"]

        suggestions = correction_service.generate_correction_suggestions(session_id)
        # Should always have manual correction option
        assert any(s["type"] == "manual_correction" for s in suggestions)

    def test_ui_integration_workflow(self, temp_db):
        """Test the UI integration workflow."""
        # Mock the correction service to avoid database dependencies
        with patch(
            "app.utils.enhanced_feedback_widget.CorrectionService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.capture_correction_session.return_value = 123
            mock_service.analyze_error_type.return_value = "missing_filter"
            mock_service.generate_correction_suggestions.return_value = [
                {
                    "type": "add_filter",
                    "description": "Add active=1 filter",
                    "action": "Add Filter(field='active', value=1) to intent.filters",
                }
            ]
            mock_service.apply_correction.return_value = True

            widget = EnhancedFeedbackWidget(
                query="test query",
                original_intent_json='{"analysis_type": "average"}',
                original_code="SELECT AVG(bmi) FROM vitals",
            )

            # Simulate UI workflow
            widget.feedback_id = 123
            widget.correct_answer_input.value = "Should include active filter"

            # Submit correction
            widget._on_submit_correction(None)

            # Verify service calls
            mock_service.capture_correction_session.assert_called_once()
            mock_service.analyze_error_type.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
