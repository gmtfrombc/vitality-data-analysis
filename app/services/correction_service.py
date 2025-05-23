"""
Correction Service for AAA Learning System

This service handles the capture, analysis, and integration of user corrections
to continuously improve the Ask Anything AI Assistant's accuracy.

Key Features:
- Captures correction sessions when users provide feedback
- Analyzes error patterns and categorizes mistakes
- Integrates successful corrections into the knowledge base
- Provides similarity matching for future queries
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

from app.utils.saved_questions_db import DB_FILE
from app.utils.query_intent import QueryIntent, parse_intent_json
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


@dataclass
class IntentPattern:
    """Represents a learned intent pattern."""

    id: Optional[int] = None
    query_pattern: str = ""
    canonical_intent_json: str = ""
    confidence_boost: float = 0.1
    usage_count: int = 0
    success_rate: float = 1.0


class CorrectionService:
    """Main service for handling corrections and learning."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the correction service.

        Args:
            db_path: Optional database path (for testing)
        """
        self.db_path = db_path or DB_FILE
        self._ensure_tables_exist()

    def _ensure_tables_exist(self):
        """Ensure all required tables exist."""
        try:
            apply_pending_migrations(self.db_path)
        except Exception as e:
            logger.error(f"Failed to apply migrations: {e}")

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
            # Apply the correction based on type
            if correction_type == "intent_fix" and corrected_intent_json:
                self._learn_intent_pattern(session, corrected_intent_json)
            elif correction_type == "code_fix" and corrected_code:
                self._learn_code_template(session, corrected_code)

            # Update session status
            self.update_correction_session(
                session_id,
                {"status": "integrated", "reviewed_at": datetime.now().isoformat()},
            )

            logger.info(f"Applied correction for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply correction for session {session_id}: {e}")
            return False

    def _learn_intent_pattern(
        self, session: CorrectionSession, corrected_intent_json: str
    ):
        """Learn a new intent pattern from a correction."""
        try:
            # Validate the corrected intent
            corrected_intent = parse_intent_json(corrected_intent_json)

            # Create a pattern from the original query and corrected intent
            pattern = IntentPattern(
                query_pattern=self._normalize_query(session.original_query),
                canonical_intent_json=corrected_intent_json,
                confidence_boost=0.2,  # Higher boost for human-corrected patterns
                usage_count=0,
                success_rate=1.0,
            )

            self._store_intent_pattern(pattern, session.id)
            logger.info(f"Learned new intent pattern from session {session.id}")

        except Exception as e:
            logger.error(f"Failed to learn intent pattern: {e}")

    def _learn_code_template(self, session: CorrectionSession, corrected_code: str):
        """Learn a new code template from a correction."""
        try:
            if session.original_intent_json:
                intent = parse_intent_json(session.original_intent_json)
                intent_signature = self._create_intent_signature(intent)

                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO code_templates 
                        (intent_signature, template_code, template_description, 
                         created_from_session_id, success_rate)
                        VALUES (?, ?, ?, ?, 1.0)
                    """,
                        (
                            intent_signature,
                            corrected_code,
                            f"Template learned from correction session {session.id}",
                            session.id,
                        ),
                    )

                logger.info(f"Learned new code template from session {session.id}")

        except Exception as e:
            logger.error(f"Failed to learn code template: {e}")

    def _normalize_query(self, query: str) -> str:
        """Normalize a query for pattern matching."""
        # Simple normalization - could be more sophisticated
        return query.lower().strip()

    def _create_intent_signature(self, intent: QueryIntent) -> str:
        """Create a signature for intent matching."""
        signature = {
            "analysis_type": intent.analysis_type,
            "target_field": intent.target_field,
            "has_filters": len(intent.filters) > 0,
            "has_conditions": len(intent.conditions) > 0,
            "has_groupby": len(intent.group_by) > 0,
        }
        return json.dumps(signature, sort_keys=True)

    def _store_intent_pattern(
        self, pattern: IntentPattern, session_id: Optional[int] = None
    ):
        """Store an intent pattern in the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO intent_patterns 
                (query_pattern, canonical_intent_json, confidence_boost, 
                 usage_count, success_rate, created_from_session_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    pattern.query_pattern,
                    pattern.canonical_intent_json,
                    pattern.confidence_boost,
                    pattern.usage_count,
                    pattern.success_rate,
                    session_id,
                ),
            )

    def find_similar_patterns(self, query: str, limit: int = 5) -> List[IntentPattern]:
        """Find similar learned patterns for a query.

        Args:
            query: The input query to match
            limit: Maximum number of patterns to return

        Returns:
            List of similar intent patterns
        """
        normalized_query = self._normalize_query(query)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Simple similarity based on string containment
            # In practice, this could use more sophisticated similarity measures
            cursor.execute(
                """
                SELECT id, query_pattern, canonical_intent_json, confidence_boost,
                       usage_count, success_rate
                FROM intent_patterns
                WHERE query_pattern LIKE ? OR ? LIKE '%' || query_pattern || '%'
                ORDER BY usage_count DESC, success_rate DESC
                LIMIT ?
            """,
                (f"%{normalized_query}%", normalized_query, limit),
            )

            patterns = []
            for row in cursor.fetchall():
                patterns.append(
                    IntentPattern(
                        id=row["id"],
                        query_pattern=row["query_pattern"],
                        canonical_intent_json=row["canonical_intent_json"],
                        confidence_boost=row["confidence_boost"],
                        usage_count=row["usage_count"],
                        success_rate=row["success_rate"],
                    )
                )

            return patterns

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

    def get_learning_metrics(self, days: int = 30) -> Dict[str, any]:
        """Get learning metrics for the past N days."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get correction sessions created in the past N days
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total_sessions,
                    COUNT(CASE WHEN status = 'integrated' THEN 1 END) as integrated_sessions,
                    COUNT(CASE WHEN status = 'validated' THEN 1 END) as validated_sessions
                FROM correction_sessions
                WHERE datetime(created_at) >= datetime('now', '-{} days')
            """.format(
                    days
                )
            )

            session_stats = cursor.fetchone()

            # Get pattern usage
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total_patterns,
                    SUM(usage_count) as total_usage,
                    AVG(success_rate) as avg_success_rate
                FROM intent_patterns
            """
            )

            pattern_stats = cursor.fetchone()

            return {
                "correction_sessions": {
                    "total": session_stats["total_sessions"],
                    "integrated": session_stats["integrated_sessions"],
                    "validated": session_stats["validated_sessions"],
                },
                "learned_patterns": {
                    "total": pattern_stats["total_patterns"] or 0,
                    "total_usage": pattern_stats["total_usage"] or 0,
                    "avg_success_rate": pattern_stats["avg_success_rate"] or 0.0,
                },
            }
