"""Basic analytics for Smart Feedback System.

This module tracks feedback request patterns and provides basic
effectiveness metrics for the smart feedback system.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from app.utils.feedback_db import _get_conn

logger = logging.getLogger(__name__)


class FeedbackAnalytics:
    """Tracks and analyzes feedback system performance."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the analytics tracker.

        Args:
            db_path: Optional database path (for testing)
        """
        self.db_path = db_path
        self._ensure_analytics_table()

    def track_feedback_request(
        self,
        query: str,
        priority: str,
        requested: bool,
        user_id: str = "anon",
        confidence_score: Optional[float] = None,
        novelty_score: Optional[float] = None,
        learning_value_score: Optional[float] = None,
        fatigue_detected: bool = False,
    ):
        """Track a feedback request decision.

        Args:
            query: The query text
            priority: Calculated priority level
            requested: Whether feedback was actually requested
            user_id: User identifier
            confidence_score: Confidence score (optional)
            novelty_score: Novelty score (optional)
            learning_value_score: Learning value score (optional)
            fatigue_detected: Whether fatigue was detected
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO feedback_requests 
                    (query_text, priority_level, requested, user_id, 
                     confidence_score, novelty_score, learning_value_score, 
                     fatigue_detected, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        query[:500],  # Truncate long queries
                        priority,
                        requested,
                        user_id,
                        confidence_score,
                        novelty_score,
                        learning_value_score,
                        fatigue_detected,
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()
                logger.debug(
                    f"Tracked feedback request: priority={priority}, requested={requested}"
                )

        except Exception as e:
            logger.error(f"Error tracking feedback request: {e}")

    def get_engagement_metrics(self, days: int = 7) -> Dict[str, float]:
        """Get user engagement metrics for the specified period.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary of engagement metrics
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get request and response counts
                cursor.execute(
                    """
                    SELECT 
                        COUNT(*) as total_requests,
                        SUM(CASE WHEN requested = 1 THEN 1 ELSE 0 END) as feedback_requested,
                        COUNT(DISTINCT user_id) as unique_users
                    FROM feedback_requests 
                    WHERE created_at > ?
                """,
                    (cutoff_date.isoformat(),),
                )

                result = cursor.fetchone()
                total_requests = result[0] if result[0] else 0
                feedback_requested = result[1] if result[1] else 0
                unique_users = result[2] if result[2] else 0

                # Get actual feedback responses (handle missing table gracefully)
                try:
                    cursor.execute(
                        """
                        SELECT COUNT(*) 
                        FROM assistant_feedback 
                        WHERE created_at > ?
                    """,
                        (cutoff_date.isoformat(),),
                    )

                    result = cursor.fetchone()
                    actual_responses = result[0] if result else 0
                except Exception:
                    # Table might not exist in test environment
                    actual_responses = 0

                # Calculate metrics
                request_rate = (
                    feedback_requested / total_requests if total_requests > 0 else 0.0
                )
                response_rate = (
                    actual_responses / feedback_requested
                    if feedback_requested > 0
                    else 0.0
                )
                avg_requests_per_user = (
                    total_requests / unique_users if unique_users > 0 else 0.0
                )

                return {
                    "total_requests": total_requests,
                    "feedback_requested": feedback_requested,
                    "actual_responses": actual_responses,
                    "unique_users": unique_users,
                    "request_rate": request_rate,
                    "response_rate": response_rate,
                    "avg_requests_per_user": avg_requests_per_user,
                }

        except Exception as e:
            logger.error(f"Error getting engagement metrics: {e}")
            return {}

    def get_effectiveness_summary(self) -> Dict[str, Any]:
        """Get overall effectiveness summary.

        Returns:
            Dictionary of effectiveness metrics
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get priority distribution
                cursor.execute(
                    """
                    SELECT priority_level, COUNT(*) 
                    FROM feedback_requests 
                    GROUP BY priority_level
                """
                )
                priority_dist = dict(cursor.fetchall())

                # Get fatigue detection stats
                cursor.execute(
                    """
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN fatigue_detected = 1 THEN 1 ELSE 0 END) as fatigue_detected
                    FROM feedback_requests
                """
                )
                result = cursor.fetchone()
                total_requests = result[0] if result[0] else 0
                fatigue_detected = result[1] if result[1] else 0

                # Get average scores by priority
                cursor.execute(
                    """
                    SELECT 
                        priority_level,
                        AVG(confidence_score) as avg_confidence,
                        AVG(novelty_score) as avg_novelty,
                        AVG(learning_value_score) as avg_learning_value
                    FROM feedback_requests 
                    WHERE confidence_score IS NOT NULL
                    GROUP BY priority_level
                """
                )

                priority_scores = {}
                for row in cursor.fetchall():
                    priority_scores[row[0]] = {
                        "avg_confidence": row[1],
                        "avg_novelty": row[2],
                        "avg_learning_value": row[3],
                    }

                return {
                    "priority_distribution": priority_dist,
                    "fatigue_rate": (
                        fatigue_detected / total_requests if total_requests > 0 else 0.0
                    ),
                    "total_requests": total_requests,
                    "priority_scores": priority_scores,
                }

        except Exception as e:
            logger.error(f"Error getting effectiveness summary: {e}")
            return {}

    def get_priority_distribution(self, days: int = 7) -> Dict[str, int]:
        """Get distribution of priority levels.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary of priority counts
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT priority_level, COUNT(*) 
                    FROM feedback_requests 
                    WHERE created_at > ?
                    GROUP BY priority_level
                """,
                    (cutoff_date.isoformat(),),
                )

                return dict(cursor.fetchall())

        except Exception as e:
            logger.error(f"Error getting priority distribution: {e}")
            return {}

    def get_user_behavior_summary(
        self, user_id: str = "anon", days: int = 30
    ) -> Dict[str, Any]:
        """Get user-specific behavior summary.

        Args:
            user_id: User identifier
            days: Number of days to analyze

        Returns:
            Dictionary of user behavior metrics
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get user request patterns
                cursor.execute(
                    """
                    SELECT 
                        COUNT(*) as total_requests,
                        SUM(CASE WHEN requested = 1 THEN 1 ELSE 0 END) as feedback_requested,
                        SUM(CASE WHEN fatigue_detected = 1 THEN 1 ELSE 0 END) as fatigue_instances
                    FROM feedback_requests 
                    WHERE user_id = ? AND created_at > ?
                """,
                    (user_id, cutoff_date.isoformat()),
                )

                result = cursor.fetchone()
                total_requests = result[0] if result[0] else 0
                feedback_requested = result[1] if result[1] else 0
                fatigue_instances = result[2] if result[2] else 0

                # Get user feedback responses (handle missing table gracefully)
                try:
                    cursor.execute(
                        """
                        SELECT 
                            COUNT(*) as total_feedback,
                            SUM(CASE WHEN rating = 'up' THEN 1 ELSE 0 END) as positive_feedback
                        FROM assistant_feedback 
                        WHERE user_id = ? AND created_at > ?
                    """,
                        (user_id, cutoff_date.isoformat()),
                    )

                    feedback_result = cursor.fetchone()
                    total_feedback = feedback_result[0] if feedback_result[0] else 0
                    positive_feedback = feedback_result[1] if feedback_result[1] else 0
                except Exception:
                    # Table might not exist in test environment
                    total_feedback = 0
                    positive_feedback = 0

                return {
                    "total_requests": total_requests,
                    "feedback_requested": feedback_requested,
                    "total_feedback": total_feedback,
                    "positive_feedback": positive_feedback,
                    "fatigue_instances": fatigue_instances,
                    "request_rate": (
                        feedback_requested / total_requests
                        if total_requests > 0
                        else 0.0
                    ),
                    "response_rate": (
                        total_feedback / feedback_requested
                        if feedback_requested > 0
                        else 0.0
                    ),
                    "positive_rate": (
                        positive_feedback / total_feedback
                        if total_feedback > 0
                        else 0.0
                    ),
                    "fatigue_rate": (
                        fatigue_instances / total_requests
                        if total_requests > 0
                        else 0.0
                    ),
                }

        except Exception as e:
            logger.error(f"Error getting user behavior summary: {e}")
            return {}

    def _ensure_analytics_table(self):
        """Ensure analytics table exists."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS feedback_requests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query_text TEXT NOT NULL,
                        priority_level TEXT NOT NULL,
                        requested BOOLEAN NOT NULL,
                        user_id TEXT DEFAULT 'anon',
                        confidence_score REAL,
                        novelty_score REAL,
                        learning_value_score REAL,
                        fatigue_detected BOOLEAN DEFAULT FALSE,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Create indexes for performance
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_feedback_requests_created_at 
                    ON feedback_requests(created_at)
                """
                )

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_feedback_requests_priority 
                    ON feedback_requests(priority_level)
                """
                )

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_feedback_requests_user_id 
                    ON feedback_requests(user_id)
                """
                )

                conn.commit()
                logger.debug("Analytics table and indexes ensured")

        except Exception as e:
            logger.error(f"Error ensuring analytics table: {e}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if self.db_path:
            return sqlite3.connect(self.db_path)
        else:
            return _get_conn()
