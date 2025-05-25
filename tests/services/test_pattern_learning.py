"""
Tests for Sprint 4 Pattern Learning functionality

Tests the enhanced pattern learning capabilities including:
- Pattern learning from successful corrections
- Query similarity matching and scoring
- Pattern caching for performance
- Query routing based on learned patterns
"""

import json
import pytest
import sqlite3
import tempfile

from app.services.correction_service import (
    CorrectionService,
    IntentPattern,
)
from app.utils.feedback_db import insert_feedback


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        return f.name


@pytest.fixture
def correction_service(temp_db):
    """Create a CorrectionService instance with temporary database."""
    return CorrectionService(db_path=temp_db)


class TestPatternLearning:
    """Test pattern learning from corrections."""

    def test_normalize_query(self, correction_service):
        """Test query normalization for pattern matching."""
        # Test basic normalization (punctuation removed)
        assert (
            correction_service._normalize_query("How many patients?")
            == "count patients"
        )

        # Test number replacement
        assert (
            correction_service._normalize_query("BMI above 30") == "bmi above [NUMBER]"
        )

        # Test phrase replacement (punctuation removed)
        assert (
            correction_service._normalize_query("What is the average BMI?")
            == "average bmi"
        )

        # Test whitespace normalization
        assert (
            correction_service._normalize_query("  show   me   patients  ")
            == "get patients"
        )

    def test_calculate_query_similarity(self, correction_service):
        """Test query similarity calculation."""
        # Identical queries
        similarity = correction_service._calculate_query_similarity(
            "count patients", "count patients"
        )
        assert similarity == 1.0

        # Completely different queries
        similarity = correction_service._calculate_query_similarity(
            "count patients", "average bmi"
        )
        assert similarity == 0.0

        # Partial overlap
        similarity = correction_service._calculate_query_similarity(
            "count active patients", "count patients"
        )
        assert 0.5 < similarity < 1.0

    def test_create_intent_pattern(self, correction_service, temp_db):
        """Test creating new intent patterns."""
        # Create a pattern
        pattern_id = correction_service._create_intent_pattern(
            query_pattern="count active patients",
            canonical_intent_json='{"analysis_type": "count", "target_field": "patients"}',
            session_id=1,
        )

        assert pattern_id is not None

        # Verify pattern was stored
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM intent_patterns WHERE id = ?", (pattern_id,))
            row = cursor.fetchone()
            assert row is not None

    def test_update_pattern_usage(self, correction_service, temp_db):
        """Test updating pattern usage statistics."""
        # Create a pattern first
        pattern_id = correction_service._create_intent_pattern(
            query_pattern="count patients",
            canonical_intent_json='{"analysis_type": "count"}',
            session_id=1,
        )

        # Update usage (success)
        correction_service._update_pattern_usage(pattern_id, success=True)

        # Verify updated stats
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT usage_count, success_rate FROM intent_patterns WHERE id = ?",
                (pattern_id,),
            )
            row = cursor.fetchone()
            assert row[0] == 2  # usage_count increased
            assert row[1] == 1.0  # success_rate still 100%

    def test_find_existing_pattern_exact_match(self, correction_service, temp_db):
        """Test finding existing patterns with exact match."""
        # Create a pattern
        pattern_id = correction_service._create_intent_pattern(
            query_pattern="count active patients",
            canonical_intent_json='{"analysis_type": "count"}',
            session_id=1,
        )

        # Find exact match
        existing = correction_service._find_existing_pattern("count active patients")
        assert existing is not None
        assert existing.id == pattern_id

    def test_find_existing_pattern_similarity_match(self, correction_service, temp_db):
        """Test finding existing patterns with similarity matching."""
        # Create a pattern
        correction_service._create_intent_pattern(
            query_pattern="count active patients",
            canonical_intent_json='{"analysis_type": "count"}',
            session_id=1,
        )

        # Find similar pattern (should match with high similarity)
        existing = correction_service._find_existing_pattern("count patients active")
        assert existing is not None

    def test_learn_from_correction_intent_modification(
        self, correction_service, temp_db
    ):
        """Test learning from intent modification corrections."""
        # Create a correction session
        insert_feedback(question="How many patients?", rating="down", db_file=temp_db)

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1")
            feedback_id = cursor.fetchone()[0]

        session_id = correction_service.capture_correction_session(
            feedback_id=feedback_id,
            original_query="How many patients?",
            human_correct_answer="Should count only active patients",
        )

        session = correction_service.get_correction_session(session_id)

        # Create suggestion for learning
        suggestion = {
            "action_type": "intent_modification",
            "corrected_intent": '{"analysis_type": "count", "target_field": "patients", "filters": [{"field": "active", "value": 1}]}',
            "type": "intent_fix",
        }

        # Learn from correction
        correction_service._learn_from_correction(session, suggestion)

        # Verify pattern was learned
        patterns = correction_service.find_similar_patterns("how many patients")
        assert len(patterns) > 0

    def test_find_similar_patterns_with_scoring(self, correction_service, temp_db):
        """Test finding similar patterns with proper scoring."""
        # Create multiple patterns with different usage counts
        correction_service._create_intent_pattern(
            query_pattern="count patients",
            canonical_intent_json='{"analysis_type": "count"}',
            session_id=1,
        )

        pattern_id_2 = correction_service._create_intent_pattern(
            query_pattern="count active patients",
            canonical_intent_json='{"analysis_type": "count", "filters": [{"field": "active", "value": 1}]}',
            session_id=2,
        )

        # Update usage for second pattern to make it more popular
        for _ in range(5):
            correction_service._update_pattern_usage(pattern_id_2, success=True)

        # Find similar patterns
        patterns = correction_service.find_similar_patterns("count patients active")

        # Should return patterns, with higher usage pattern ranked higher
        assert len(patterns) > 0
        assert (
            patterns[0].usage_count >= patterns[-1].usage_count
            if len(patterns) > 1
            else True
        )


class TestPatternCaching:
    """Test pattern caching functionality."""

    def test_query_hash_generation(self, correction_service):
        """Test query hash generation for caching."""
        hash1 = correction_service._get_query_hash("count patients")
        hash2 = correction_service._get_query_hash("count patients")
        hash3 = correction_service._get_query_hash("average bmi")

        # Same query should produce same hash
        assert hash1 == hash2

        # Different queries should produce different hashes
        assert hash1 != hash3

    def test_cache_similar_patterns(self, correction_service, temp_db):
        """Test caching of similar patterns."""
        # Create a pattern in the database first
        pattern_id = correction_service._create_intent_pattern(
            query_pattern="count patients",
            canonical_intent_json='{"analysis_type": "count"}',
            session_id=1,
        )

        # Create pattern object for caching
        patterns = [
            IntentPattern(
                id=pattern_id,
                query_pattern="count patients",
                canonical_intent_json='{"analysis_type": "count"}',
                usage_count=5,
                success_rate=1.0,
            )
        ]

        # Cache the patterns
        query_hash = correction_service._get_query_hash("count patients")
        correction_service._cache_similar_patterns(query_hash, patterns)

        # Retrieve from cache
        cached = correction_service._get_cached_patterns(query_hash)
        assert cached is not None
        assert len(cached) == 1
        assert cached[0].id == pattern_id

    def test_cache_expiration(self, correction_service, temp_db):
        """Test that cache entries expire after 1 hour."""
        # Create a pattern in the database first
        pattern_id = correction_service._create_intent_pattern(
            query_pattern="count patients",
            canonical_intent_json='{"analysis_type": "count"}',
            session_id=1,
        )

        # Create patterns and cache them
        patterns = [
            IntentPattern(
                id=pattern_id,
                query_pattern="count patients",
                canonical_intent_json='{"analysis_type": "count"}',
                usage_count=5,
                success_rate=1.0,
            )
        ]

        query_hash = correction_service._get_query_hash("count patients")
        correction_service._cache_similar_patterns(query_hash, patterns)

        # Manually update cache timestamp to simulate expiration
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE query_similarity_cache 
                SET computed_at = datetime('now', '-2 hours')
                WHERE query_hash = ?
            """,
                (query_hash,),
            )

        # Should not retrieve expired cache
        cached = correction_service._get_cached_patterns(query_hash)
        assert cached is None

    def test_cleanup_old_cache_entries(self, correction_service, temp_db):
        """Test cleanup of old cache entries."""
        # Create some cache entries
        query_hash = correction_service._get_query_hash("test query")
        correction_service._cache_similar_patterns(query_hash, [])

        # Manually age the cache entry
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE query_similarity_cache 
                SET computed_at = datetime('now', '-10 days')
                WHERE query_hash = ?
            """,
                (query_hash,),
            )

        # Cleanup old entries
        correction_service.cleanup_old_cache_entries(days_old=7)

        # Verify entry was deleted
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM query_similarity_cache WHERE query_hash = ?",
                (query_hash,),
            )
            count = cursor.fetchone()[0]
            assert count == 0


class TestLearningMetrics:
    """Test learning metrics functionality."""

    def test_get_learning_metrics(self, correction_service, temp_db):
        """Test getting learning system metrics."""
        # Create some test data
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

        assert "patterns" in metrics
        assert "corrections" in metrics
        assert "cache" in metrics
        assert metrics["patterns"]["total"] >= 1
        assert metrics["corrections"]["total"] >= 1

    def test_update_learning_metrics(self, correction_service, temp_db):
        """Test updating learning metrics after corrections."""
        # Create a session
        insert_feedback(question="Test query", rating="down", db_file=temp_db)

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1")
            feedback_id = cursor.fetchone()[0]

        session_id = correction_service.capture_correction_session(
            feedback_id=feedback_id,
            original_query="Test query",
            human_correct_answer="Test answer",
        )

        session = correction_service.get_correction_session(session_id)
        suggestion = {"type": "intent_fix"}

        # Update metrics
        correction_service._update_learning_metrics(session, suggestion)

        # Verify metrics were updated
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM learning_metrics")
            count = cursor.fetchone()[0]
            assert count >= 1


class TestCodeTemplateLearning:
    """Test code template learning functionality."""

    def test_generate_intent_signature(self, correction_service):
        """Test generating intent signatures for template matching."""
        intent_json = '{"analysis_type": "count", "target_field": "patients", "filters": [{"field": "active", "value": 1}]}'
        signature = correction_service._generate_intent_signature(intent_json)

        assert signature is not None
        signature_data = json.loads(signature)
        assert signature_data["analysis_type"] == "count"
        assert signature_data["target_field"] == "patients"
        assert signature_data["has_filters"]

    def test_learn_code_template(self, correction_service, temp_db):
        """Test learning code templates from corrections."""
        # Create a session with original intent
        insert_feedback(question="Test query", rating="down", db_file=temp_db)

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1")
            feedback_id = cursor.fetchone()[0]

        session_id = correction_service.capture_correction_session(
            feedback_id=feedback_id,
            original_query="Count active patients",
            human_correct_answer="Should use proper SQL",
            original_intent_json='{"analysis_type": "count", "target_field": "patients"}',
            original_code="SELECT COUNT(*) FROM patients",
        )

        session = correction_service.get_correction_session(session_id)

        # Create suggestion with corrected code
        suggestion = {
            "action_type": "code_modification",
            "corrected_code": "SELECT COUNT(*) FROM patients WHERE active = 1",
            "type": "code_fix",
        }

        # Learn code template
        correction_service._learn_code_template(session, suggestion)

        # Verify template was created
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM code_templates")
            count = cursor.fetchone()[0]
            assert count >= 1

    def test_find_existing_template(self, correction_service, temp_db):
        """Test finding existing code templates."""
        # Create a template
        intent_signature = '{"analysis_type": "count", "has_filters": true}'
        correction_service._create_code_template(
            intent_signature=intent_signature,
            corrected_code="SELECT COUNT(*) FROM patients WHERE active = 1",
            session_id=1,
        )

        # Find existing template
        existing = correction_service._find_existing_template(intent_signature)
        assert existing is not None
        assert existing["intent_signature"] == intent_signature

    def test_update_template_usage(self, correction_service, temp_db):
        """Test updating code template usage statistics."""
        # Create a template
        intent_signature = '{"analysis_type": "count"}'
        correction_service._create_code_template(
            intent_signature=intent_signature,
            corrected_code="SELECT COUNT(*) FROM patients",
            session_id=1,
        )

        # Get template ID
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM code_templates ORDER BY id DESC LIMIT 1")
            template_id = cursor.fetchone()[0]

        # Update usage
        correction_service._update_template_usage(template_id, success=True)

        # Verify updated stats
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT usage_count, success_rate FROM code_templates WHERE id = ?",
                (template_id,),
            )
            row = cursor.fetchone()
            assert row[0] == 2  # usage_count increased
            assert row[1] == 1.0  # success_rate still 100%
