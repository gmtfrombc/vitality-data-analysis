"""
Learning Analytics Service for AAA Admin Monitoring

This service provides comprehensive analytics for the learning system,
tracking pattern effectiveness, correction success rates, and learning progress.

Sprint 2.2 Features:
- Pattern effectiveness analysis
- Correction success tracking
- User feedback analytics
- Learning progress metrics
- Pattern lifecycle management
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from collections import defaultdict

from app.utils.saved_questions_db import DB_FILE
from app.utils.learning_metrics import LearningSystemMonitor
from app.services.correction_service import CorrectionService

logger = logging.getLogger(__name__)


@dataclass
class PatternEffectiveness:
    """Pattern effectiveness metrics."""

    pattern_id: str
    pattern_type: str
    success_rate: float
    total_applications: int
    successful_applications: int
    failed_applications: int
    avg_confidence: float
    last_used: str
    trend: str  # "improving", "declining", "stable"


@dataclass
class CorrectionAnalysis:
    """Correction success analysis."""

    total_corrections: int
    successful_corrections: int
    success_rate: float
    avg_time_to_success: float
    common_correction_types: List[Dict[str, Any]]
    correction_trends: Dict[str, float]


@dataclass
class LearningProgress:
    """Learning progress metrics."""

    overall_learning_rate: float
    patterns_learned: int
    patterns_improved: int
    patterns_deprecated: int
    learning_velocity: float  # patterns per day
    confidence_improvement: float
    milestone_progress: Dict[str, Any]


class LearningAnalyticsService:
    """Service for learning system analytics."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the learning analytics service.

        Args:
            db_path: Optional database path (for testing)
        """
        self.db_path = db_path or DB_FILE
        self.monitor = LearningSystemMonitor(db_path)
        self.correction_service = CorrectionService(db_path)

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_pattern_effectiveness(self, days: int = 30) -> List[PatternEffectiveness]:
        """Get pattern effectiveness metrics for the specified period.

        Args:
            days: Number of days to analyze

        Returns:
            List of pattern effectiveness metrics
        """
        try:
            with self._get_connection() as conn:
                # Get pattern usage and success data
                query = """
                SELECT 
                    p.id as pattern_id,
                    'intent_pattern' as pattern_type,
                    p.confidence_boost,
                    p.created_at,
                    COUNT(pa.id) as total_applications,
                    SUM(CASE WHEN pa.success = 1 THEN 1 ELSE 0 END) as successful_applications,
                    AVG(pa.confidence_score) as avg_confidence,
                    MAX(pa.applied_at) as last_used
                FROM intent_patterns p
                LEFT JOIN pattern_applications pa ON p.id = CAST(pa.pattern_id AS INTEGER)
                    AND pa.applied_at >= datetime('now', '-{} days')
                GROUP BY p.id, p.confidence_boost, p.created_at
                HAVING COUNT(pa.id) > 0
                ORDER BY total_applications DESC
                """.format(
                    days
                )

                cursor = conn.execute(query)
                rows = cursor.fetchall()

                effectiveness_list = []
                for row in rows:
                    total_apps = row["total_applications"] or 0
                    successful_apps = row["successful_applications"] or 0
                    success_rate = (
                        (successful_apps / total_apps) if total_apps > 0 else 0.0
                    )

                    # Calculate trend
                    trend = self._calculate_pattern_trend(
                        conn, str(row["pattern_id"]), days
                    )

                    effectiveness = PatternEffectiveness(
                        pattern_id=str(row["pattern_id"]),
                        pattern_type=row["pattern_type"],
                        success_rate=success_rate,
                        total_applications=total_apps,
                        successful_applications=successful_apps,
                        failed_applications=total_apps - successful_apps,
                        avg_confidence=row["avg_confidence"] or 0.0,
                        last_used=row["last_used"] or "Never",
                        trend=trend,
                    )
                    effectiveness_list.append(effectiveness)

                return effectiveness_list

        except Exception as e:
            logger.error(f"Error getting pattern effectiveness: {e}")
            return []

    def _calculate_pattern_trend(
        self, conn: sqlite3.Connection, pattern_id: str, days: int
    ) -> str:
        """Calculate trend for a specific pattern."""
        try:
            # Get success rates for first and second half of the period
            half_days = days // 2

            query_recent = """
            SELECT AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
            FROM pattern_applications 
            WHERE pattern_id = ? AND applied_at >= datetime('now', '-{} days')
            """.format(
                half_days
            )

            query_older = """
            SELECT AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
            FROM pattern_applications 
            WHERE pattern_id = ? 
            AND applied_at >= datetime('now', '-{} days')
            AND applied_at < datetime('now', '-{} days')
            """.format(
                days, half_days
            )

            recent_result = conn.execute(query_recent, (pattern_id,)).fetchone()
            older_result = conn.execute(query_older, (pattern_id,)).fetchone()

            recent_rate = (
                recent_result["success_rate"]
                if recent_result and recent_result["success_rate"]
                else 0
            )
            older_rate = (
                older_result["success_rate"]
                if older_result and older_result["success_rate"]
                else 0
            )

            if recent_rate > older_rate + 0.1:
                return "improving"
            elif recent_rate < older_rate - 0.1:
                return "declining"
            else:
                return "stable"

        except Exception as e:
            logger.error(f"Error calculating pattern trend: {e}")
            return "unknown"

    def get_correction_analysis(self, days: int = 30) -> CorrectionAnalysis:
        """Get correction success analysis for the specified period.

        Args:
            days: Number of days to analyze

        Returns:
            Correction analysis metrics
        """
        try:
            with self._get_connection() as conn:
                # Get correction statistics
                query = """
                SELECT 
                    correction_type,
                    COUNT(*) as total_corrections,
                    SUM(CASE WHEN status = 'integrated' THEN 1 ELSE 0 END) as successful_corrections,
                    COUNT(*) as type_count
                FROM correction_sessions 
                WHERE created_at >= datetime('now', '-{} days')
                GROUP BY correction_type
                ORDER BY type_count DESC
                """.format(
                    days
                )

                cursor = conn.execute(query)
                rows = cursor.fetchall()

                if not rows:
                    return CorrectionAnalysis(
                        total_corrections=0,
                        successful_corrections=0,
                        success_rate=0.0,
                        avg_time_to_success=0.0,
                        common_correction_types=[],
                        correction_trends={},
                    )

                # Aggregate totals
                total_corrections = sum(row["total_corrections"] for row in rows)
                successful_corrections = sum(
                    row["successful_corrections"] for row in rows
                )
                success_rate = (
                    (successful_corrections / total_corrections)
                    if total_corrections > 0
                    else 0.0
                )

                # Get average time to success
                avg_time_query = """
                SELECT AVG(CASE WHEN status = 'integrated' 
                    THEN (julianday(reviewed_at) - julianday(created_at)) * 24 * 60 
                    ELSE NULL END) as avg_time_minutes
                FROM correction_sessions 
                WHERE created_at >= datetime('now', '-{} days')
                AND status = 'integrated'
                """.format(
                    days
                )

                avg_time_result = conn.execute(avg_time_query).fetchone()
                avg_time_to_success = (
                    avg_time_result["avg_time_minutes"]
                    if avg_time_result and avg_time_result["avg_time_minutes"]
                    else 0.0
                )

                # Build common correction types
                common_types = [
                    {
                        "type": row["correction_type"] or "unknown",
                        "count": row["type_count"],
                        "percentage": (
                            (row["type_count"] / total_corrections) * 100
                            if total_corrections > 0
                            else 0
                        ),
                    }
                    for row in rows[:5]  # Top 5 types
                ]

                # Get correction trends (weekly comparison)
                trends = self._get_correction_trends(conn, days)

                return CorrectionAnalysis(
                    total_corrections=total_corrections,
                    successful_corrections=successful_corrections,
                    success_rate=success_rate,
                    avg_time_to_success=avg_time_to_success,
                    common_correction_types=common_types,
                    correction_trends=trends,
                )

        except Exception as e:
            logger.error(f"Error getting correction analysis: {e}")
            return CorrectionAnalysis(
                total_corrections=0,
                successful_corrections=0,
                success_rate=0.0,
                avg_time_to_success=0.0,
                common_correction_types=[],
                correction_trends={},
            )

    def _get_correction_trends(
        self, conn: sqlite3.Connection, days: int
    ) -> Dict[str, float]:
        """Get correction trends over time."""
        try:
            # Compare current week vs previous week
            current_week_query = """
            SELECT COUNT(*) as count
            FROM correction_sessions 
            WHERE created_at >= datetime('now', '-7 days')
            """

            previous_week_query = """
            SELECT COUNT(*) as count
            FROM correction_sessions 
            WHERE created_at >= datetime('now', '-14 days')
            AND created_at < datetime('now', '-7 days')
            """

            current_count = conn.execute(current_week_query).fetchone()["count"]
            previous_count = conn.execute(previous_week_query).fetchone()["count"]

            if previous_count > 0:
                weekly_change = (
                    (current_count - previous_count) / previous_count
                ) * 100
            else:
                weekly_change = 0.0

            return {
                "weekly_change_percent": weekly_change,
                "current_week_count": current_count,
                "previous_week_count": previous_count,
            }

        except Exception as e:
            logger.error(f"Error getting correction trends: {e}")
            return {}

    def get_learning_progress(self, days: int = 30) -> LearningProgress:
        """Get overall learning progress metrics.

        Args:
            days: Number of days to analyze

        Returns:
            Learning progress metrics
        """
        try:
            with self._get_connection() as conn:
                # Get pattern statistics
                pattern_stats_query = """
                SELECT 
                    COUNT(*) as total_patterns,
                    SUM(CASE WHEN created_at >= datetime('now', '-{} days') THEN 1 ELSE 0 END) as new_patterns,
                    AVG(confidence_boost) as avg_confidence
                FROM intent_patterns
                """.format(
                    days
                )

                pattern_stats = conn.execute(pattern_stats_query).fetchone()

                # Get improved patterns (those with increasing success rates)
                improved_patterns = self._count_improved_patterns(conn, days)

                # Get deprecated patterns (assume patterns with low usage are deprecated)
                deprecated_query = """
                SELECT COUNT(*) as count
                FROM intent_patterns p
                LEFT JOIN pattern_applications pa ON CAST(p.id AS TEXT) = pa.pattern_id
                WHERE p.created_at <= datetime('now', '-{} days')
                GROUP BY p.id
                HAVING COUNT(pa.id) = 0 OR AVG(CASE WHEN pa.success = 1 THEN 1.0 ELSE 0.0 END) < 0.3
                """.format(
                    days
                )

                deprecated_result = conn.execute(deprecated_query).fetchall()
                deprecated_count = len(deprecated_result)

                # Calculate learning velocity (patterns per day)
                new_patterns = pattern_stats["new_patterns"] or 0
                learning_velocity = new_patterns / days if days > 0 else 0

                # Get confidence improvement
                confidence_improvement = self._calculate_confidence_improvement(
                    conn, days
                )

                # Get milestone progress
                milestones = self._get_milestone_progress(conn)

                return LearningProgress(
                    overall_learning_rate=self._calculate_learning_rate(conn, days),
                    patterns_learned=new_patterns,
                    patterns_improved=improved_patterns,
                    patterns_deprecated=deprecated_count,
                    learning_velocity=learning_velocity,
                    confidence_improvement=confidence_improvement,
                    milestone_progress=milestones,
                )

        except Exception as e:
            logger.error(f"Error getting learning progress: {e}")
            return LearningProgress(
                overall_learning_rate=0.0,
                patterns_learned=0,
                patterns_improved=0,
                patterns_deprecated=0,
                learning_velocity=0.0,
                confidence_improvement=0.0,
                milestone_progress={},
            )

    def _count_improved_patterns(self, conn: sqlite3.Connection, days: int) -> int:
        """Count patterns that have improved in the specified period."""
        try:
            # This is a simplified version - in practice, you'd track pattern performance over time
            query = """
            SELECT COUNT(DISTINCT pattern_id) as count
            FROM pattern_applications 
            WHERE applied_at >= datetime('now', '-{} days')
            AND success = 1
            """.format(
                days
            )

            result = conn.execute(query).fetchone()
            return result["count"] if result else 0

        except Exception as e:
            logger.error(f"Error counting improved patterns: {e}")
            return 0

    def _calculate_confidence_improvement(
        self, conn: sqlite3.Connection, days: int
    ) -> float:
        """Calculate average confidence improvement over the period."""
        try:
            # Compare average confidence of recent patterns vs older patterns
            recent_query = """
            SELECT AVG(confidence_boost) as avg_confidence
            FROM intent_patterns 
            WHERE created_at >= datetime('now', '-{} days')
            """.format(
                days // 2
            )

            older_query = """
            SELECT AVG(confidence_boost) as avg_confidence
            FROM intent_patterns 
            WHERE created_at >= datetime('now', '-{} days')
            AND created_at < datetime('now', '-{} days')
            """.format(
                days, days // 2
            )

            recent_result = conn.execute(recent_query).fetchone()
            older_result = conn.execute(older_query).fetchone()

            recent_confidence = (
                recent_result["avg_confidence"]
                if recent_result and recent_result["avg_confidence"]
                else 0
            )
            older_confidence = (
                older_result["avg_confidence"]
                if older_result and older_result["avg_confidence"]
                else 0
            )

            return recent_confidence - older_confidence

        except Exception as e:
            logger.error(f"Error calculating confidence improvement: {e}")
            return 0.0

    def _calculate_learning_rate(self, conn: sqlite3.Connection, days: int) -> float:
        """Calculate overall learning rate based on successful pattern applications."""
        try:
            query = """
            SELECT 
                COUNT(*) as total_applications,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_applications
            FROM pattern_applications 
            WHERE applied_at >= datetime('now', '-{} days')
            """.format(
                days
            )

            result = conn.execute(query).fetchone()
            total = result["total_applications"] or 0
            successful = result["successful_applications"] or 0

            return (successful / total) if total > 0 else 0.0

        except Exception as e:
            logger.error(f"Error calculating learning rate: {e}")
            return 0.0

    def _get_milestone_progress(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Get progress towards learning milestones."""
        try:
            # Define milestones and check progress
            milestones = {
                "patterns_milestone_100": {
                    "target": 100,
                    "current": 0,
                    "description": "100 learned patterns",
                },
                "success_rate_milestone_90": {
                    "target": 0.90,
                    "current": 0.0,
                    "description": "90% pattern success rate",
                },
                "corrections_milestone_50": {
                    "target": 50,
                    "current": 0,
                    "description": "50 successful corrections",
                },
            }

            # Get current pattern count
            pattern_count = conn.execute(
                "SELECT COUNT(*) as count FROM intent_patterns"
            ).fetchone()["count"]
            milestones["patterns_milestone_100"]["current"] = pattern_count

            # Get current success rate
            success_rate_query = """
            SELECT AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as rate
            FROM pattern_applications 
            WHERE applied_at >= datetime('now', '-30 days')
            """
            success_result = conn.execute(success_rate_query).fetchone()
            success_rate = (
                success_result["rate"]
                if success_result and success_result["rate"]
                else 0.0
            )
            milestones["success_rate_milestone_90"]["current"] = success_rate

            # Get successful corrections count
            corrections_count = conn.execute(
                "SELECT COUNT(*) as count FROM correction_sessions WHERE status = 'integrated'"
            ).fetchone()["count"]
            milestones["corrections_milestone_50"]["current"] = corrections_count

            return milestones

        except Exception as e:
            logger.error(f"Error getting milestone progress: {e}")
            return {}

    def get_user_feedback_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get user feedback analytics and sentiment analysis.

        Args:
            days: Number of days to analyze

        Returns:
            User feedback analytics
        """
        try:
            with self._get_connection() as conn:
                # Get feedback statistics
                feedback_query = """
                SELECT 
                    feedback_type,
                    rating,
                    COUNT(*) as count,
                    AVG(rating) as avg_rating
                FROM user_feedback 
                WHERE created_at >= datetime('now', '-{} days')
                GROUP BY feedback_type, rating
                ORDER BY feedback_type, rating
                """.format(
                    days
                )

                cursor = conn.execute(feedback_query)
                feedback_data = cursor.fetchall()

                # Process feedback data
                feedback_summary = defaultdict(
                    lambda: {"total": 0, "avg_rating": 0.0, "ratings": {}}
                )

                for row in feedback_data:
                    feedback_type = row["feedback_type"]
                    rating = row["rating"]
                    count = row["count"]

                    feedback_summary[feedback_type]["total"] += count
                    feedback_summary[feedback_type]["ratings"][rating] = count
                    feedback_summary[feedback_type]["avg_rating"] = row["avg_rating"]

                return dict(feedback_summary)

        except Exception as e:
            logger.error(f"Error getting user feedback analytics: {e}")
            return {}
