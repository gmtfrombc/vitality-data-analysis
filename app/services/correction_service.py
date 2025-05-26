"""
Correction Service for AAA Learning System

This service handles the capture, analysis, and integration of user corrections
to continuously improve the Ask Anything AI Assistant's accuracy.

Key Features:
- Captures correction sessions when users provide feedback
- Analyzes error patterns and categorizes mistakes
- Integrates successful corrections into the knowledge base
- Provides similarity matching for future queries
- SPRINT 4: Advanced pattern learning and query routing
"""

from __future__ import annotations

import json
import logging
import sqlite3
import hashlib
import math
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from app.utils.saved_questions_db import DB_FILE
from app.utils.query_intent import parse_intent_json
from app.utils.db_migrations import apply_pending_migrations

logger = logging.getLogger(__name__)


@dataclass
class CorrectionSession:
    """Represents a correction session with all relevant data."""

    id: Optional[int] = None
    feedback_id: Optional[int] = None
    original_query: str = ""
    original_intent_json: Optional[str] = None
    original_code: Optional[str] = None
    original_results: Optional[str] = None
    human_correct_answer: str = ""
    correction_type: Optional[str] = None
    error_category: Optional[str] = None
    status: str = "pending"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    corrected_intent_json: Optional[str] = None  # Added for Sprint 4


@dataclass
class IntentPattern:
    """Represents a learned intent pattern."""

    id: Optional[int] = None
    query_pattern: str = ""
    canonical_intent_json: str = ""
    confidence_boost: float = 0.1
    usage_count: int = 0
    success_rate: float = 1.0
    last_used_at: Optional[str] = None


class CorrectionService:
    """Main service for handling corrections and learning."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the correction service.

        Args:
            db_path: Optional database path (for testing)
        """
        self.db_path = db_path or DB_FILE
        self._ensure_tables_exist()
        self._create_performance_indexes()

    def _ensure_tables_exist(self):
        """Ensure all required tables exist."""
        try:
            apply_pending_migrations(self.db_path)
        except Exception as e:
            logger.error(f"Failed to apply migrations: {e}")

    def _create_performance_indexes(self):
        """Create additional indexes for performance."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Check if indexes already exist to avoid spam
                cursor.execute(
                    """
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name='idx_intent_patterns_success_rate'
                """
                )

                if cursor.fetchone():
                    # Indexes already exist, no need to log
                    return

                # Additional performance indexes for Sprint 4
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_intent_patterns_success_rate ON intent_patterns(success_rate DESC)",
                    "CREATE INDEX IF NOT EXISTS idx_intent_patterns_last_used ON intent_patterns(last_used_at DESC)",
                    "CREATE INDEX IF NOT EXISTS idx_query_similarity_cache_computed ON query_similarity_cache(computed_at DESC)",
                    "CREATE INDEX IF NOT EXISTS idx_correction_sessions_created ON correction_sessions(created_at DESC)",
                ]

                for index_sql in indexes:
                    cursor.execute(index_sql)

                logger.debug("Created performance indexes")

        except Exception as e:
            logger.warning(f"Failed to create performance indexes: {e}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def capture_correction_session(
        self,
        feedback_id: int,
        original_query: str,
        human_correct_answer: str,
        original_intent_json: Optional[str] = None,
        original_code: Optional[str] = None,
        original_results: Optional[str] = None,
    ) -> int:
        """Capture a new correction session.

        Args:
            feedback_id: ID from assistant_feedback table
            original_query: The original user query
            human_correct_answer: The correct answer provided by human
            original_intent_json: The original parsed intent (if available)
            original_code: The original generated code (if available)
            original_results: The original results (if available)

        Returns:
            The ID of the created correction session
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO correction_sessions 
                (feedback_id, original_query, original_intent_json, original_code, 
                 original_results, human_correct_answer, status)
                VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """,
                (
                    feedback_id,
                    original_query,
                    original_intent_json,
                    original_code,
                    original_results,
                    human_correct_answer,
                ),
            )
            session_id = cursor.lastrowid
            logger.info(
                f"Created correction session {session_id} for feedback {feedback_id}"
            )
            return session_id

    def analyze_error_type(self, session_id: int) -> str:
        """Analyze the type of error in a correction session.

        Args:
            session_id: The correction session ID

        Returns:
            The determined error category
        """
        session = self.get_correction_session(session_id)
        if not session:
            return "unknown"

        # Simple heuristic-based error analysis
        # In practice, this could use ML or more sophisticated analysis

        error_category = "unknown"

        # Check if we have intent data to analyze
        if session.original_intent_json:
            try:
                intent = parse_intent_json(session.original_intent_json)

                # Intent-related errors
                if intent.analysis_type == "unknown":
                    error_category = "ambiguous_intent"
                elif intent.target_field == "unknown":
                    error_category = "unclear_target"
                elif not intent.filters and "active" in session.original_query.lower():
                    error_category = "missing_filter"
                elif (
                    intent.analysis_type in ["count", "average"]
                    and "distribution" in session.human_correct_answer.lower()
                ):
                    error_category = "wrong_aggregation"
                else:
                    error_category = "intent_mismatch"

            except Exception as e:
                logger.warning(f"Failed to parse intent for analysis: {e}")
                error_category = "intent_parse_error"

        # Code-related errors (if we have code but no intent issues)
        elif session.original_code and error_category == "unknown":
            if (
                "GROUP BY" not in session.original_code
                and "group" in session.human_correct_answer.lower()
            ):
                error_category = "missing_groupby"
            elif (
                "WHERE" not in session.original_code
                and "filter" in session.human_correct_answer.lower()
            ):
                error_category = "missing_where"
            else:
                error_category = "code_logic_error"

        # Update the session with the analysis
        self.update_correction_session(
            session_id,
            {
                "error_category": error_category,
                "correction_type": self._infer_correction_type(error_category),
            },
        )

        logger.info(f"Analyzed session {session_id}: {error_category}")
        return error_category

    def _infer_correction_type(self, error_category: str) -> str:
        """Infer the correction type from error category."""
        intent_errors = {
            "ambiguous_intent",
            "unclear_target",
            "missing_filter",
            "wrong_aggregation",
            "intent_mismatch",
        }
        code_errors = {"missing_groupby", "missing_where", "code_logic_error"}

        if error_category in intent_errors:
            return "intent_fix"
        elif error_category in code_errors:
            return "code_fix"
        else:
            return "logic_fix"

    def generate_correction_suggestions(self, session_id: int) -> List[Dict]:
        """Generate suggestions for correcting an error.

        Args:
            session_id: The correction session ID

        Returns:
            List of correction suggestions
        """
        session = self.get_correction_session(session_id)
        if not session:
            return []

        suggestions = []

        # Based on error category, provide specific suggestions
        if session.error_category == "missing_filter":
            suggestions.append(
                {
                    "type": "add_filter",
                    "description": "Add patient status filter (active/inactive)",
                    "action": "Add Filter(field='active', value=1) to intent.filters",
                }
            )

        elif session.error_category == "wrong_aggregation":
            suggestions.append(
                {
                    "type": "change_analysis_type",
                    "description": "Change analysis type from count/average to distribution",
                    "action": "Update intent.analysis_type to 'distribution'",
                }
            )

        elif session.error_category == "missing_groupby":
            suggestions.append(
                {
                    "type": "add_grouping",
                    "description": "Add GROUP BY clause to generated code",
                    "action": "Include grouping in code generation template",
                }
            )

        # Always offer manual correction option
        suggestions.append(
            {
                "type": "manual_correction",
                "description": "Manually create corrected intent or code",
                "action": "Human review and manual correction",
            }
        )

        return suggestions

    def apply_correction(
        self,
        session_id: int,
        correction_type: str,
        corrected_intent_json: Optional[str] = None,
        corrected_code: Optional[str] = None,
    ) -> bool:
        """Apply a correction and learn from it.

        Args:
            session_id: The correction session ID
            correction_type: Type of correction being applied
            corrected_intent_json: Corrected intent (if applicable)
            corrected_code: Corrected code (if applicable)

        Returns:
            True if correction was successfully applied
        """
        session = self.get_correction_session(session_id)
        if not session:
            return False

        try:
            # Create suggestion object for learning
            suggestion = {
                "action_type": (
                    "intent_modification"
                    if correction_type == "intent_fix"
                    else "code_modification"
                ),
                "corrected_intent": corrected_intent_json,
                "corrected_code": corrected_code,
                "type": correction_type,
            }

            # Learn from the correction
            self._learn_from_correction(session, suggestion)

            # Update session status
            self.update_correction_session(
                session_id,
                {
                    "status": "integrated",
                    "reviewed_at": datetime.now().isoformat(),
                    "corrected_intent_json": corrected_intent_json,
                },
            )

            logger.info(f"Applied correction for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply correction for session {session_id}: {e}")
            return False

    def _learn_from_correction(self, session: CorrectionSession, suggestion: Dict):
        """Learn patterns from successful corrections.

        Args:
            session: The correction session
            suggestion: The applied suggestion
        """
        try:
            # Learn intent patterns
            if suggestion.get("action_type") == "intent_modification":
                self._learn_intent_pattern(session, suggestion)

            # Learn code templates
            if session.original_code and suggestion.get("corrected_code"):
                self._learn_code_template(session, suggestion)

            # Update learning metrics
            self._update_learning_metrics(session, suggestion)

            logger.info(f"Learned from session {session.id}: {suggestion['type']}")

        except Exception as e:
            logger.error(f"Failed to learn from correction {session.id}: {e}")

    def _learn_intent_pattern(self, session: CorrectionSession, suggestion: Dict):
        """Learn an intent pattern from a successful correction."""
        try:
            # Normalize the query for pattern matching
            normalized_query = self._normalize_query(session.original_query)

            # Get the corrected intent
            corrected_intent_json = suggestion.get("corrected_intent")
            if not corrected_intent_json and hasattr(session, "corrected_intent_json"):
                corrected_intent_json = session.corrected_intent_json

            if not corrected_intent_json:
                logger.warning(
                    f"No corrected intent available for session {session.id}"
                )
                return

            # Check if similar pattern already exists
            existing_pattern = self._find_existing_pattern(normalized_query)

            if existing_pattern:
                # Update existing pattern
                self._update_pattern_usage(existing_pattern.id, success=True)
                logger.info(f"Updated existing pattern {existing_pattern.id}")
            else:
                # Create new pattern
                pattern_id = self._create_intent_pattern(
                    query_pattern=normalized_query,
                    canonical_intent_json=corrected_intent_json,
                    session_id=session.id,
                )
                logger.info(f"Created new intent pattern {pattern_id}")

        except Exception as e:
            logger.error(f"Failed to learn intent pattern: {e}")

    def _learn_code_template(self, session: CorrectionSession, suggestion: Dict):
        """Learn a code template from successful correction."""
        try:
            corrected_code = suggestion.get("corrected_code")
            if not corrected_code:
                return

            # Generate intent signature for template matching
            intent_signature = self._generate_intent_signature(
                session.original_intent_json
            )

            # Check for existing template
            existing_template = self._find_existing_template(intent_signature)

            if existing_template:
                self._update_template_usage(existing_template["id"], success=True)
            else:
                self._create_code_template(intent_signature, corrected_code, session.id)

        except Exception as e:
            logger.error(f"Failed to learn code template: {e}")

    def _generate_intent_signature(self, intent_json: str) -> str:
        """Generate a signature for intent matching."""
        try:
            intent_data = json.loads(intent_json) if intent_json else {}

            # Create a normalized signature
            signature = {
                "analysis_type": intent_data.get("analysis_type", "unknown"),
                "target_field": intent_data.get("target_field", "unknown"),
                "has_filters": bool(intent_data.get("filters")),
                "has_grouping": bool(intent_data.get("grouping")),
            }

            return json.dumps(signature, sort_keys=True)

        except Exception as e:
            logger.warning(f"Failed to generate intent signature: {e}")
            return "{}"

    def _find_existing_template(self, intent_signature: str) -> Optional[Dict]:
        """Find existing code template for intent signature."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM code_templates 
                    WHERE intent_signature = ?
                    ORDER BY usage_count DESC
                    LIMIT 1
                """,
                    (intent_signature,),
                )

                row = cursor.fetchone()
                return dict(row) if row else None

        except Exception as e:
            logger.error(f"Failed to find existing template: {e}")
            return None

    def _create_code_template(
        self, intent_signature: str, corrected_code: str, session_id: int
    ):
        """Create a new code template."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO code_templates 
                    (intent_signature, template_code, template_description, 
                     created_from_session_id, success_rate, usage_count)
                    VALUES (?, ?, ?, ?, 1.0, 1)
                """,
                    (
                        intent_signature,
                        corrected_code,
                        f"Template learned from correction session {session_id}",
                        session_id,
                    ),
                )

                logger.info(f"Created new code template from session {session_id}")

        except Exception as e:
            logger.error(f"Failed to create code template: {e}")

    def _update_template_usage(self, template_id: int, success: bool = True):
        """Update code template usage statistics."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get current stats
                cursor.execute(
                    """
                    SELECT usage_count, success_rate FROM code_templates WHERE id = ?
                """,
                    (template_id,),
                )

                row = cursor.fetchone()
                if not row:
                    return

                current_usage = row["usage_count"]
                current_success_rate = row["success_rate"]

                # Calculate new stats
                new_usage = current_usage + 1
                if success:
                    new_success_rate = (
                        (current_success_rate * current_usage) + 1
                    ) / new_usage
                else:
                    new_success_rate = (
                        current_success_rate * current_usage
                    ) / new_usage

                # Update template
                cursor.execute(
                    """
                    UPDATE code_templates 
                    SET usage_count = ?, success_rate = ?, last_used_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """,
                    (new_usage, new_success_rate, template_id),
                )

                logger.info(
                    f"Updated template {template_id}: usage={new_usage}, success_rate={new_success_rate:.2f}"
                )

        except Exception as e:
            logger.error(f"Failed to update template usage: {e}")

    def _normalize_query(self, query: str) -> str:
        """Normalize a query for pattern matching.

        Args:
            query: The original query

        Returns:
            Normalized query string for pattern matching
        """
        # Convert to lowercase
        normalized = query.lower().strip()

        # Remove punctuation
        normalized = re.sub(r"[^\w\s]", "", normalized)

        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", normalized)

        # Replace numbers with placeholders for generalization
        normalized = re.sub(r"\b\d+\b", "[NUMBER]", normalized)

        # Replace specific names/IDs with placeholders
        normalized = re.sub(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", "[NAME]", normalized)

        # Standardize common phrases
        phrase_replacements = {
            "how many": "count",
            "what is the average": "average",
            "what is the total": "sum",
            "show me": "get",
            "tell me": "get",
            "what are": "get",
            "give me": "get",
        }

        for phrase, replacement in phrase_replacements.items():
            normalized = normalized.replace(phrase, replacement)

        return normalized

    def _find_existing_pattern(self, normalized_query: str) -> Optional[IntentPattern]:
        """Find an existing pattern that matches the normalized query."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # First, try exact match
                cursor.execute(
                    """
                    SELECT * FROM intent_patterns 
                    WHERE query_pattern = ?
                    ORDER BY usage_count DESC
                    LIMIT 1
                """,
                    (normalized_query,),
                )

                row = cursor.fetchone()
                if row:
                    return self._row_to_intent_pattern(row)

                # Then try similarity matching
                cursor.execute(
                    """
                    SELECT * FROM intent_patterns
                    ORDER BY usage_count DESC
                """
                )

                patterns = cursor.fetchall()

                # Find most similar pattern
                best_match = None
                best_similarity = 0.0

                for pattern_row in patterns:
                    similarity = self._calculate_query_similarity(
                        normalized_query, pattern_row["query_pattern"]
                    )
                    if (
                        similarity > 0.5 and similarity > best_similarity
                    ):  # 50% similarity threshold
                        best_similarity = similarity
                        best_match = self._row_to_intent_pattern(pattern_row)

                return best_match

        except Exception as e:
            logger.error(f"Failed to find existing pattern: {e}")
            return None

    def _calculate_query_similarity(self, query1: str, query2: str) -> float:
        """Calculate similarity between two queries.

        Args:
            query1: First query
            query2: Second query

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Simple word-based similarity for now
        words1 = set(query1.split())
        words2 = set(query2.split())

        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0

        # Check for conflicting medical terms that should prevent matching
        conflicting_terms = {
            frozenset(["weight", "bmi"]),
            frozenset(["weight", "height"]),
            frozenset(["bmi", "height"]),
            frozenset(["sbp", "dbp"]),  # systolic vs diastolic
            frozenset(["glucose", "bmi"]),
            frozenset(["a1c", "weight"]),
        }

        for conflict_set in conflicting_terms:
            if (
                len(conflict_set.intersection(words1)) > 0
                and len(conflict_set.intersection(words2)) > 0
            ):
                # Check if they contain different terms from the conflict set
                terms1 = conflict_set.intersection(words1)
                terms2 = conflict_set.intersection(words2)
                if terms1 != terms2:  # Different conflicting terms
                    return 0.0  # No similarity for conflicting medical terms

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    def _create_intent_pattern(
        self, query_pattern: str, canonical_intent_json: str, session_id: int
    ) -> int:
        """Create a new intent pattern."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO intent_patterns 
                (query_pattern, canonical_intent_json, confidence_boost, usage_count, 
                 success_rate, created_from_session_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (query_pattern, canonical_intent_json, 0.1, 1, 1.0, session_id),
            )
            return cursor.lastrowid

    def _update_pattern_usage(self, pattern_id: int, success: bool = True):
        """Update pattern usage statistics."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get current stats
                cursor.execute(
                    """
                    SELECT usage_count, success_rate FROM intent_patterns WHERE id = ?
                """,
                    (pattern_id,),
                )

                row = cursor.fetchone()
                if not row:
                    return

                current_usage = row["usage_count"]
                current_success_rate = row["success_rate"]

                # Calculate new stats
                new_usage = current_usage + 1
                if success:
                    new_success_rate = (
                        (current_success_rate * current_usage) + 1
                    ) / new_usage
                else:
                    new_success_rate = (
                        current_success_rate * current_usage
                    ) / new_usage

                # Update pattern
                cursor.execute(
                    """
                    UPDATE intent_patterns 
                    SET usage_count = ?, success_rate = ?, last_used_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """,
                    (new_usage, new_success_rate, pattern_id),
                )

                logger.info(
                    f"Updated pattern {pattern_id}: usage={new_usage}, success_rate={new_success_rate:.2f}"
                )

        except Exception as e:
            logger.error(f"Failed to update pattern usage: {e}")

    def _row_to_intent_pattern(self, row) -> IntentPattern:
        """Convert database row to IntentPattern object."""
        return IntentPattern(
            id=row["id"],
            query_pattern=row["query_pattern"],
            canonical_intent_json=row["canonical_intent_json"],
            confidence_boost=row["confidence_boost"],
            usage_count=row["usage_count"],
            success_rate=row["success_rate"],
            last_used_at=row["last_used_at"] if "last_used_at" in row.keys() else None,
        )

    def find_similar_patterns(self, query: str, limit: int = 5) -> List[IntentPattern]:
        """Find similar learned patterns for a query.

        Args:
            query: The user query
            limit: Maximum number of patterns to return

        Returns:
            List of similar patterns sorted by relevance and success rate
        """
        normalized_query = self._normalize_query(query)

        # Check cache first
        cache_key = self._get_query_hash(normalized_query)
        cached_patterns = self._get_cached_patterns(cache_key)
        if cached_patterns:
            return cached_patterns[:limit]

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get all patterns ordered by usage and success rate
                cursor.execute(
                    """
                    SELECT * FROM intent_patterns
                    WHERE success_rate >= 0.7
                    ORDER BY usage_count DESC, success_rate DESC
                """
                )

                patterns = cursor.fetchall()

                # Calculate similarity scores
                scored_patterns = []
                for pattern_row in patterns:
                    pattern = self._row_to_intent_pattern(pattern_row)
                    similarity = self._calculate_query_similarity(
                        normalized_query, pattern.query_pattern
                    )

                    if similarity > 0.3:  # Minimum similarity threshold
                        # Combined score: similarity * success_rate * log(usage_count)
                        usage_factor = math.log(max(pattern.usage_count, 1) + 1)
                        combined_score = (
                            similarity * pattern.success_rate * usage_factor
                        )

                        scored_patterns.append((combined_score, pattern))

                # Sort by combined score
                scored_patterns.sort(key=lambda x: x[0], reverse=True)

                # Extract patterns
                result_patterns = [
                    pattern for score, pattern in scored_patterns[:limit]
                ]

                # Cache the results
                self._cache_similar_patterns(cache_key, result_patterns)

                return result_patterns

        except Exception as e:
            logger.error(f"Failed to find similar patterns: {e}")
            return []

    def _get_query_hash(self, query: str) -> str:
        """Get hash for query caching."""
        return hashlib.md5(query.encode()).hexdigest()

    def _get_cached_patterns(self, query_hash: str) -> Optional[List[IntentPattern]]:
        """Get cached similar patterns."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT similar_patterns FROM query_similarity_cache 
                    WHERE query_hash = ? AND computed_at > datetime('now', '-1 hour')
                """,
                    (query_hash,),
                )

                row = cursor.fetchone()
                if row:
                    pattern_ids = json.loads(row["similar_patterns"])
                    return self._get_patterns_by_ids(pattern_ids)

        except Exception as e:
            logger.warning(f"Failed to get cached patterns: {e}")

        return None

    def _cache_similar_patterns(self, query_hash: str, patterns: List[IntentPattern]):
        """Cache similar patterns for faster lookup."""
        try:
            pattern_ids = [p.id for p in patterns if p.id]

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO query_similarity_cache 
                    (query_hash, similar_patterns, computed_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                    (query_hash, json.dumps(pattern_ids)),
                )

        except Exception as e:
            logger.warning(f"Failed to cache patterns: {e}")

    def _get_patterns_by_ids(self, pattern_ids: List[int]) -> List[IntentPattern]:
        """Get patterns by their IDs."""
        if not pattern_ids:
            return []

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                placeholders = ",".join("?" * len(pattern_ids))
                cursor.execute(
                    f"""
                    SELECT * FROM intent_patterns 
                    WHERE id IN ({placeholders})
                    ORDER BY usage_count DESC, success_rate DESC
                """,
                    pattern_ids,
                )

                return [self._row_to_intent_pattern(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Failed to get patterns by IDs: {e}")
            return []

    def cleanup_old_cache_entries(self, days_old: int = 7):
        """Clean up old cache entries to maintain performance."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    DELETE FROM query_similarity_cache 
                    WHERE computed_at < datetime('now', '-' || ? || ' days')
                """,
                    (days_old,),
                )

                deleted = cursor.rowcount
                logger.info(f"Cleaned up {deleted} old cache entries")

        except Exception as e:
            logger.warning(f"Failed to cleanup cache entries: {e}")

    def _update_learning_metrics(self, session: CorrectionSession, suggestion: Dict):
        """Update learning metrics after successful correction."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get today's metrics or create new entry
                today = datetime.now().date().isoformat()
                cursor.execute(
                    """
                    SELECT * FROM learning_metrics WHERE metric_date = ?
                """,
                    (today,),
                )

                row = cursor.fetchone()
                if row:
                    # Update existing metrics
                    cursor.execute(
                        """
                        UPDATE learning_metrics 
                        SET correction_applied = correction_applied + 1,
                            accuracy_rate = (correct_answers + 1.0) / (total_queries + 1.0)
                        WHERE metric_date = ?
                    """,
                        (today,),
                    )
                else:
                    # Create new metrics entry
                    cursor.execute(
                        """
                        INSERT INTO learning_metrics 
                        (metric_date, total_queries, correct_answers, correction_applied, accuracy_rate)
                        VALUES (?, 1, 1, 1, 1.0)
                    """,
                        (today,),
                    )

        except Exception as e:
            logger.warning(f"Failed to update learning metrics: {e}")

    def get_correction_session(self, session_id: int) -> Optional[CorrectionSession]:
        """Get a correction session by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM correction_sessions WHERE id = ?
            """,
                (session_id,),
            )

            row = cursor.fetchone()
            if row:
                return CorrectionSession(
                    id=row["id"],
                    feedback_id=row["feedback_id"],
                    original_query=row["original_query"],
                    original_intent_json=row["original_intent_json"],
                    original_code=row["original_code"],
                    original_results=row["original_results"],
                    human_correct_answer=row["human_correct_answer"],
                    correction_type=row["correction_type"],
                    error_category=row["error_category"],
                    status=row["status"],
                    reviewed_by=row["reviewed_by"],
                    reviewed_at=row["reviewed_at"],
                    corrected_intent_json=row["corrected_intent_json"],
                )
            return None

    def update_correction_session(
        self, session_id: int, updates: Dict[str, any]
    ) -> bool:
        """Update a correction session."""
        if not updates:
            return False

        set_clause = ", ".join(f"{key} = ?" for key in updates.keys())
        values = list(updates.values()) + [session_id]

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"""
                    UPDATE correction_sessions 
                    SET {set_clause}
                    WHERE id = ?
                """,
                    values,
                )

                return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Failed to update correction session {session_id}: {e}")
            return False

    def get_learning_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get learning system performance metrics."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Pattern usage metrics
                cursor.execute(
                    """
                    SELECT 
                        COUNT(*) as total_patterns,
                        AVG(usage_count) as avg_usage,
                        AVG(success_rate) as avg_success_rate,
                        COUNT(CASE WHEN success_rate > 0.9 THEN 1 END) as high_confidence_patterns
                    FROM intent_patterns
                """
                )
                pattern_stats = cursor.fetchone()

                # Recent correction metrics
                cursor.execute(
                    """
                    SELECT 
                        COUNT(*) as total_corrections,
                        COUNT(CASE WHEN status = 'integrated' THEN 1 END) as successful_corrections,
                        COUNT(CASE WHEN created_at > datetime('now', '-' || ? || ' days') THEN 1 END) as recent_corrections
                    FROM correction_sessions
                """,
                    (days,),
                )
                correction_stats = cursor.fetchone()

                # Cache performance
                cursor.execute(
                    """
                    SELECT COUNT(*) as cached_queries
                    FROM query_similarity_cache
                    WHERE computed_at > datetime('now', '-1 hour')
                """
                )
                cache_stats = cursor.fetchone()

                return {
                    "patterns": {
                        "total": pattern_stats["total_patterns"] or 0,
                        "average_usage": pattern_stats["avg_usage"] or 0,
                        "average_success_rate": pattern_stats["avg_success_rate"] or 0,
                        "high_confidence": pattern_stats["high_confidence_patterns"]
                        or 0,
                    },
                    "corrections": {
                        "total": correction_stats["total_corrections"] or 0,
                        "successful": correction_stats["successful_corrections"] or 0,
                        "recent": correction_stats["recent_corrections"] or 0,
                        "success_rate": (
                            correction_stats["successful_corrections"] or 0
                        )
                        / max(correction_stats["total_corrections"] or 1, 1),
                    },
                    "cache": {"recent_entries": cache_stats["cached_queries"] or 0},
                }

        except Exception as e:
            logger.error(f"Failed to get learning metrics: {e}")
            return {}
