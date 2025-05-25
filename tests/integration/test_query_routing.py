"""
Integration tests for Sprint 4 Query Routing functionality

Tests the complete flow of query routing including:
- Pattern matching in the engine
- Fallback to LLM processing
- Intent comparison and validation
- Performance optimization
"""

import json
import pytest
import sqlite3
import tempfile
from unittest.mock import Mock, patch

from app.engine import AnalysisEngine
from app.services.correction_service import CorrectionService
from app.utils.feedback_db import insert_feedback
from app.utils.query_intent import QueryIntent


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        return f.name


@pytest.fixture
def correction_service(temp_db):
    """Create a CorrectionService instance with temporary database."""
    return CorrectionService(db_path=temp_db)


@pytest.fixture
def analysis_engine():
    """Create an AnalysisEngine instance for testing."""
    return AnalysisEngine()


class TestQueryRouting:
    """Test query routing with pattern matching."""

    def test_high_confidence_pattern_routing(
        self, analysis_engine, correction_service, temp_db
    ):
        """Test routing to high-confidence learned patterns."""
        # Create a high-confidence pattern
        pattern_id = correction_service._create_intent_pattern(
            query_pattern="count active patients",
            canonical_intent_json='{"analysis_type": "count", "target_field": "patients", "filters": [{"field": "active", "value": 1}]}',
            session_id=1,
        )

        # Update pattern to have high confidence
        for _ in range(5):  # Make it popular
            correction_service._update_pattern_usage(pattern_id, success=True)

        # Mock the correction service to return our pattern
        with patch(
            "app.services.correction_service.CorrectionService"
        ) as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service

            # Create a mock pattern with high confidence
            mock_pattern = Mock()
            mock_pattern.id = pattern_id
            mock_pattern.success_rate = 0.95
            mock_pattern.usage_count = 6
            mock_pattern.canonical_intent_json = '{"analysis_type": "count", "target_field": "patients", "filters": [{"field": "active", "value": 1}]}'

            mock_service.find_similar_patterns.return_value = [mock_pattern]

            # Mock parse_intent_json to return a proper QueryIntent
            with patch("app.utils.query_intent.parse_intent_json") as mock_parse:
                mock_intent = Mock(spec=QueryIntent)
                mock_intent.analysis_type = "count"
                mock_intent.target_field = "patients"
                mock_intent.parameters = {}
                mock_parse.return_value = mock_intent

                # Process query
                result = analysis_engine.process_query_with_patterns()

                # Verify pattern was used
                mock_service.find_similar_patterns.assert_called_once()
                mock_service._update_pattern_usage.assert_called_once_with(
                    pattern_id, success=True
                )

                # Verify intent was set with pattern metadata
                assert hasattr(analysis_engine.intent, "parameters")
                assert (
                    analysis_engine.intent.parameters.get("source") == "learned_pattern"
                )
                assert analysis_engine.intent.parameters.get("confidence") == 0.95

    def test_medium_confidence_pattern_with_llm_validation(
        self, analysis_engine, correction_service
    ):
        """Test medium confidence patterns with LLM validation."""
        # Mock the correction service
        with patch(
            "app.services.correction_service.CorrectionService"
        ) as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service

            # Create a mock pattern with medium confidence
            mock_pattern = Mock()
            mock_pattern.id = 1
            mock_pattern.success_rate = 0.8  # Medium confidence
            mock_pattern.usage_count = 3
            mock_pattern.canonical_intent_json = (
                '{"analysis_type": "count", "target_field": "patients"}'
            )

            mock_service.find_similar_patterns.return_value = [mock_pattern]

            # Mock parse_intent_json and get_query_intent
            with patch(
                "app.utils.query_intent.parse_intent_json"
            ) as mock_parse, patch.object(
                analysis_engine, "get_query_intent"
            ) as mock_get_intent:

                # Create mock intents
                pattern_intent = Mock(spec=QueryIntent)
                pattern_intent.analysis_type = "count"
                pattern_intent.target_field = "patients"
                pattern_intent.parameters = {}

                llm_intent = Mock(spec=QueryIntent)
                llm_intent.analysis_type = "count"
                llm_intent.target_field = "patients"

                mock_parse.return_value = pattern_intent
                mock_get_intent.return_value = llm_intent

                # Mock intent comparison to return True (similar)
                with patch.object(
                    analysis_engine, "_intents_are_similar", return_value=True
                ):
                    # Process query
                    result = analysis_engine.process_query_with_patterns()

                    # Verify both pattern and LLM were consulted
                    mock_service.find_similar_patterns.assert_called_once()
                    mock_get_intent.assert_called_once()

                    # Verify pattern was used after validation
                    assert (
                        analysis_engine.intent.parameters.get("source")
                        == "pattern_validated"
                    )
                    assert analysis_engine.intent.parameters.get("confidence") == 0.85

    def test_fallback_to_llm_processing(self, analysis_engine):
        """Test fallback to LLM when no suitable patterns exist."""
        # Mock the correction service to return no patterns
        with patch(
            "app.services.correction_service.CorrectionService"
        ) as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.find_similar_patterns.return_value = []

            # Mock get_query_intent
            with patch.object(analysis_engine, "get_query_intent") as mock_get_intent:
                mock_intent = Mock(spec=QueryIntent)
                mock_get_intent.return_value = mock_intent

                # Process query
                result = analysis_engine.process_query_with_patterns()

                # Verify fallback to LLM
                mock_service.find_similar_patterns.assert_called_once()
                mock_get_intent.assert_called_once()
                assert result == mock_intent

    def test_pattern_matching_failure_fallback(self, analysis_engine):
        """Test fallback when pattern matching fails with exception."""
        # Mock the correction service to raise an exception
        with patch(
            "app.services.correction_service.CorrectionService"
        ) as mock_service_class:
            mock_service_class.side_effect = Exception("Database error")

            # Mock get_query_intent
            with patch.object(analysis_engine, "get_query_intent") as mock_get_intent:
                mock_intent = Mock(spec=QueryIntent)
                mock_get_intent.return_value = mock_intent

                # Process query
                result = analysis_engine.process_query_with_patterns()

                # Verify fallback to LLM despite exception
                mock_get_intent.assert_called_once()
                assert result == mock_intent

    def test_intent_similarity_comparison(self, analysis_engine):
        """Test intent similarity comparison logic."""
        # Create two similar intents
        intent1 = Mock(spec=QueryIntent)
        intent1.analysis_type = "count"
        intent1.target_field = "patients"
        intent1.filters = []

        intent2 = Mock(spec=QueryIntent)
        intent2.analysis_type = "count"
        intent2.target_field = "patients"
        intent2.filters = []

        # Should be similar
        assert analysis_engine._intents_are_similar(intent1, intent2)

        # Create different intents
        intent3 = Mock(spec=QueryIntent)
        intent3.analysis_type = "average"  # Different analysis type
        intent3.target_field = "patients"
        intent3.filters = []

        # Should not be similar
        assert not analysis_engine._intents_are_similar(intent1, intent3)

    def test_intent_similarity_with_different_filters(self, analysis_engine):
        """Test intent similarity with different filter counts."""
        # Create intents with different filter counts
        intent1 = Mock(spec=QueryIntent)
        intent1.analysis_type = "count"
        intent1.target_field = "patients"
        intent1.filters = [Mock()]  # One filter

        intent2 = Mock(spec=QueryIntent)
        intent2.analysis_type = "count"
        intent2.target_field = "patients"
        intent2.filters = [Mock(), Mock()]  # Two filters

        # Should not be similar due to different filter counts
        assert not analysis_engine._intents_are_similar(intent1, intent2)

    def test_intent_similarity_exception_handling(self, analysis_engine):
        """Test intent similarity comparison with exception handling."""
        # Create intent that will cause an exception
        intent1 = Mock(spec=QueryIntent)
        intent1.analysis_type = "count"
        intent1.target_field = "patients"

        intent2 = Mock(spec=QueryIntent)
        # Create a mock that raises an exception when compared
        mock_analysis_type = Mock()
        mock_analysis_type.__eq__ = Mock(side_effect=Exception("Comparison error"))
        intent2.analysis_type = mock_analysis_type

        # Should return False on exception
        assert not analysis_engine._intents_are_similar(intent1, intent2)


class TestQueryRoutingPerformance:
    """Test performance aspects of query routing."""

    def test_pattern_caching_improves_performance(
        self, analysis_engine, correction_service, temp_db
    ):
        """Test that pattern caching improves query performance."""
        # Create a pattern and cache it
        pattern_id = correction_service._create_intent_pattern(
            query_pattern="count patients",
            canonical_intent_json='{"analysis_type": "count", "target_field": "patients"}',
            session_id=1,
        )

        # Simulate cached patterns
        query_hash = correction_service._get_query_hash("count patients")
        patterns = [
            correction_service._row_to_intent_pattern(
                {
                    "id": pattern_id,
                    "query_pattern": "count patients",
                    "canonical_intent_json": '{"analysis_type": "count", "target_field": "patients"}',
                    "confidence_boost": 0.1,
                    "usage_count": 1,
                    "success_rate": 1.0,
                    "last_used_at": None,
                }
            )
        ]
        correction_service._cache_similar_patterns(query_hash, patterns)

        # Test that cached patterns are retrieved
        cached = correction_service._get_cached_patterns(query_hash)
        assert cached is not None
        assert len(cached) == 1
        assert cached[0].id == pattern_id

    def test_pattern_lookup_with_scoring(self, correction_service, temp_db):
        """Test pattern lookup with proper scoring algorithm."""
        # Create multiple patterns with different characteristics
        pattern1_id = correction_service._create_intent_pattern(
            query_pattern="count patients",
            canonical_intent_json='{"analysis_type": "count"}',
            session_id=1,
        )

        pattern2_id = correction_service._create_intent_pattern(
            query_pattern="count active patients",
            canonical_intent_json='{"analysis_type": "count", "filters": [{"field": "active", "value": 1}]}',
            session_id=2,
        )

        # Make pattern2 more popular
        for _ in range(3):
            correction_service._update_pattern_usage(pattern2_id, success=True)

        # Find patterns for a query
        patterns = correction_service.find_similar_patterns("count patients active")

        # Verify patterns are returned and properly scored
        assert len(patterns) > 0
        # The more popular pattern should be ranked higher
        if len(patterns) > 1:
            assert patterns[0].usage_count >= patterns[1].usage_count

    def test_cache_cleanup_performance(self, correction_service, temp_db):
        """Test cache cleanup for maintaining performance."""
        # Create multiple cache entries
        for i in range(10):
            query_hash = correction_service._get_query_hash(f"test query {i}")
            correction_service._cache_similar_patterns(query_hash, [])

        # Age some entries
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE query_similarity_cache 
                SET computed_at = datetime('now', '-10 days')
                WHERE id <= 5
            """
            )

        # Cleanup old entries
        correction_service.cleanup_old_cache_entries(days_old=7)

        # Verify old entries were cleaned up
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM query_similarity_cache")
            remaining_count = cursor.fetchone()[0]
            assert remaining_count <= 5  # Should have removed at least 5 old entries


class TestEndToEndQueryRouting:
    """Test end-to-end query routing scenarios."""

    def test_complete_learning_and_routing_cycle(
        self, analysis_engine, correction_service, temp_db
    ):
        """Test complete cycle from learning to routing."""
        # Step 1: Create a correction session (simulating user feedback)
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

        # Step 2: Apply correction and learn pattern
        corrected_intent = {
            "analysis_type": "count",
            "target_field": "patients",
            "filters": [{"field": "active", "value": 1}],
        }

        success = correction_service.apply_correction(
            session_id=session_id,
            correction_type="intent_fix",
            corrected_intent_json=json.dumps(corrected_intent),
        )
        assert success

        # Step 3: Verify pattern was learned
        patterns = correction_service.find_similar_patterns("how many active patients")
        assert len(patterns) > 0

        # Step 4: Test routing to learned pattern
        with patch(
            "app.services.correction_service.CorrectionService"
        ) as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.find_similar_patterns.return_value = patterns

            # Make the pattern high confidence for routing
            patterns[0].success_rate = 0.95
            patterns[0].usage_count = 5

            with patch("app.utils.query_intent.parse_intent_json") as mock_parse:
                mock_intent = Mock(spec=QueryIntent)
                mock_intent.parameters = {}
                mock_parse.return_value = mock_intent

                # Process similar query
                analysis_engine.query = "how many active patients"
                result = analysis_engine.process_query_with_patterns()

                # Verify pattern was used
                assert result.parameters.get("source") == "learned_pattern"

    def test_learning_metrics_tracking(self, correction_service, temp_db):
        """Test that learning metrics are properly tracked."""
        # Create some patterns and corrections
        correction_service._create_intent_pattern(
            query_pattern="count patients",
            canonical_intent_json='{"analysis_type": "count"}',
            session_id=1,
        )

        # Create correction session
        insert_feedback(question="Test query", rating="down", db_file=temp_db)

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1")
            feedback_id = cursor.fetchone()[0]

        correction_service.capture_correction_session(
            feedback_id=feedback_id,
            original_query="Test query",
            human_correct_answer="Test answer",
        )

        # Get metrics
        metrics = correction_service.get_learning_metrics()

        # Verify metrics structure
        assert "patterns" in metrics
        assert "corrections" in metrics
        assert "cache" in metrics

        # Verify pattern metrics
        assert metrics["patterns"]["total"] >= 1
        assert "average_usage" in metrics["patterns"]
        assert "average_success_rate" in metrics["patterns"]
        assert "high_confidence" in metrics["patterns"]

        # Verify correction metrics
        assert metrics["corrections"]["total"] >= 1
        assert "successful" in metrics["corrections"]
        assert "recent" in metrics["corrections"]
        assert "success_rate" in metrics["corrections"]
