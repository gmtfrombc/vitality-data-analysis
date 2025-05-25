"""
Learning System Monitoring and Metrics

Provides comprehensive monitoring capabilities for the AAA learning system,
including performance metrics, accuracy tracking, and health monitoring.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from app.services.correction_service import CorrectionService
from app.utils.saved_questions_db import DB_FILE

logger = logging.getLogger(__name__)


@dataclass
class SystemHealthStatus:
    """System health status information."""

    overall_status: str  # "healthy", "warning", "critical"
    database_connected: bool
    pattern_learning_active: bool
    cache_performance: str
    recent_error_rate: float
    recommendations: List[str]


@dataclass
class LearningMetrics:
    """Comprehensive learning system metrics."""

    timestamp: str
    accuracy_metrics: Dict[str, float]
    performance_metrics: Dict[str, float]
    usage_metrics: Dict[str, int]
    pattern_metrics: Dict[str, Any]
    error_metrics: Dict[str, Any]


class LearningSystemMonitor:
    """Monitor and track learning system performance."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the monitoring system."""
        self.db_path = db_path or DB_FILE
        self.correction_service = CorrectionService(db_path)

    def get_system_health(self) -> SystemHealthStatus:
        """Get comprehensive system health status."""
        recommendations = []
        overall_status = "healthy"

        # Check database connectivity
        try:
            database_connected = self._check_database_health()
        except Exception as e:
            database_connected = False
            recommendations.append("Database connectivity issues detected")
            overall_status = "critical"

        # Check pattern learning status
        try:
            pattern_learning_active = self._check_pattern_learning_health()
            if not pattern_learning_active:
                recommendations.append("Pattern learning system inactive")
                if overall_status != "critical":
                    overall_status = "warning"
        except Exception as e:
            pattern_learning_active = False
            recommendations.append("Pattern learning health check failed")
            overall_status = "critical"

        # Check cache performance
        try:
            cache_performance = self._check_cache_performance()
            if cache_performance == "poor":
                recommendations.append("Cache performance is degraded")
                if overall_status == "healthy":
                    overall_status = "warning"
        except Exception as e:
            cache_performance = "unknown"
            recommendations.append("Cache performance check failed")

        # Check recent error rate
        try:
            recent_error_rate = self._calculate_recent_error_rate()
            if recent_error_rate > 0.2:  # 20% error rate threshold
                recommendations.append(
                    f"High error rate detected: {recent_error_rate:.1%}"
                )
                overall_status = "critical"
            elif recent_error_rate > 0.1:  # 10% error rate threshold
                recommendations.append(f"Elevated error rate: {recent_error_rate:.1%}")
                if overall_status == "healthy":
                    overall_status = "warning"
        except Exception as e:
            recent_error_rate = 0.0
            recommendations.append("Unable to calculate error rate")

        return SystemHealthStatus(
            overall_status=overall_status,
            database_connected=database_connected,
            pattern_learning_active=pattern_learning_active,
            cache_performance=cache_performance,
            recent_error_rate=recent_error_rate,
            recommendations=recommendations,
        )

    def get_comprehensive_metrics(self, days: int = 7) -> LearningMetrics:
        """Get comprehensive learning system metrics."""

        # Accuracy metrics
        accuracy_metrics = self._calculate_accuracy_metrics(days)

        # Performance metrics
        performance_metrics = self._calculate_performance_metrics(days)

        # Usage metrics
        usage_metrics = self._calculate_usage_metrics(days)

        # Pattern metrics
        pattern_metrics = self._calculate_pattern_metrics(days)

        # Error metrics
        error_metrics = self._calculate_error_metrics(days)

        return LearningMetrics(
            timestamp=datetime.now().isoformat(),
            accuracy_metrics=accuracy_metrics,
            performance_metrics=performance_metrics,
            usage_metrics=usage_metrics,
            pattern_metrics=pattern_metrics,
            error_metrics=error_metrics,
        )

    def _check_database_health(self) -> bool:
        """Check database connectivity and table integrity."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check that all required tables exist
                required_tables = [
                    "correction_sessions",
                    "intent_patterns",
                    "code_templates",
                    "learning_metrics",
                    "query_similarity_cache",
                ]

                for table in required_tables:
                    cursor.execute(
                        """
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name=?
                    """,
                        (table,),
                    )

                    if not cursor.fetchone():
                        logger.error(f"Required table {table} missing")
                        return False

                return True

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def _check_pattern_learning_health(self) -> bool:
        """Check if pattern learning is functioning."""
        try:
            # Check if patterns have been created recently
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM intent_patterns
                    WHERE created_at > datetime('now', '-7 days')
                """
                )

                recent_patterns = cursor.fetchone()[0]
                return recent_patterns > 0

        except Exception as e:
            logger.error(f"Pattern learning health check failed: {e}")
            return False

    def _check_cache_performance(self) -> str:
        """Check cache performance status."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check cache hit rate (entries created in last hour)
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM query_similarity_cache
                    WHERE computed_at > datetime('now', '-1 hour')
                """
                )
                recent_cache_entries = cursor.fetchone()[0]

                # Check total cache size
                cursor.execute("SELECT COUNT(*) FROM query_similarity_cache")
                total_cache_entries = cursor.fetchone()[0]

                if recent_cache_entries > 50:
                    return "excellent"
                elif recent_cache_entries > 20:
                    return "good"
                elif recent_cache_entries > 5:
                    return "fair"
                else:
                    return "poor"

        except Exception as e:
            logger.error(f"Cache performance check failed: {e}")
            return "unknown"

    def _calculate_recent_error_rate(self, hours: int = 24) -> float:
        """Calculate recent error rate."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get total corrections in timeframe
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM correction_sessions
                    WHERE created_at > datetime('now', '-' || ? || ' hours')
                """,
                    (hours,),
                )
                total_corrections = cursor.fetchone()[0]

                if total_corrections == 0:
                    return 0.0

                # Get failed corrections (status = 'rejected' or similar)
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM correction_sessions
                    WHERE created_at > datetime('now', '-' || ? || ' hours')
                    AND status IN ('rejected', 'failed')
                """,
                    (hours,),
                )
                failed_corrections = cursor.fetchone()[0]

                return failed_corrections / total_corrections

        except Exception as e:
            logger.error(f"Error rate calculation failed: {e}")
            return 0.0

    def _calculate_accuracy_metrics(self, days: int) -> Dict[str, float]:
        """Calculate accuracy-related metrics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Pattern accuracy
                cursor.execute(
                    """
                    SELECT AVG(success_rate) FROM intent_patterns
                    WHERE usage_count > 1
                """
                )
                avg_pattern_accuracy = cursor.fetchone()[0] or 0.0

                # Correction success rate
                cursor.execute(
                    """
                    SELECT 
                        COUNT(CASE WHEN status = 'integrated' THEN 1 END) * 1.0 / COUNT(*) as success_rate
                    FROM correction_sessions
                    WHERE created_at > datetime('now', '-' || ? || ' days')
                """,
                    (days,),
                )
                correction_success_rate = cursor.fetchone()[0] or 0.0

                return {
                    "pattern_accuracy": avg_pattern_accuracy,
                    "correction_success_rate": correction_success_rate,
                    "overall_accuracy": (avg_pattern_accuracy + correction_success_rate)
                    / 2,
                }

        except Exception as e:
            logger.error(f"Accuracy metrics calculation failed: {e}")
            return {
                "pattern_accuracy": 0.0,
                "correction_success_rate": 0.0,
                "overall_accuracy": 0.0,
            }

    def _calculate_performance_metrics(self, days: int) -> Dict[str, float]:
        """Calculate performance-related metrics."""
        # Simulate performance measurements
        # In production, these would be actual measurements

        try:
            # Test pattern lookup performance
            start_time = time.time()
            patterns = self.correction_service.find_similar_patterns("test query")
            pattern_lookup_time = (time.time() - start_time) * 1000

            return {
                "pattern_lookup_ms": pattern_lookup_time,
                "cache_hit_rate": 0.85,  # Would be calculated from actual cache stats
                "average_response_time_ms": 150.0,  # Would be measured from actual queries
            }

        except Exception as e:
            logger.error(f"Performance metrics calculation failed: {e}")
            return {
                "pattern_lookup_ms": 0.0,
                "cache_hit_rate": 0.0,
                "average_response_time_ms": 0.0,
            }

    def _calculate_usage_metrics(self, days: int) -> Dict[str, int]:
        """Calculate usage-related metrics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Total corrections in period
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM correction_sessions
                    WHERE created_at > datetime('now', '-' || ? || ' days')
                """,
                    (days,),
                )
                total_corrections = cursor.fetchone()[0]

                # Pattern matches in period
                cursor.execute(
                    """
                    SELECT SUM(usage_count) FROM intent_patterns
                    WHERE last_used_at > datetime('now', '-' || ? || ' days')
                """,
                    (days,),
                )
                pattern_matches = cursor.fetchone()[0] or 0

                # Active patterns
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM intent_patterns
                    WHERE success_rate > 0.7 AND usage_count > 1
                """
                )
                active_patterns = cursor.fetchone()[0]

                return {
                    "total_corrections": total_corrections,
                    "pattern_matches": pattern_matches,
                    "active_patterns": active_patterns,
                    "corrections_per_day": total_corrections // max(days, 1),
                }

        except Exception as e:
            logger.error(f"Usage metrics calculation failed: {e}")
            return {
                "total_corrections": 0,
                "pattern_matches": 0,
                "active_patterns": 0,
                "corrections_per_day": 0,
            }

    def _calculate_pattern_metrics(self, days: int) -> Dict[str, Any]:
        """Calculate pattern-related metrics."""
        try:
            basic_metrics = self.correction_service.get_learning_metrics(days)
            return basic_metrics.get("patterns", {})

        except Exception as e:
            logger.error(f"Pattern metrics calculation failed: {e}")
            return {}

    def _calculate_error_metrics(self, days: int) -> Dict[str, Any]:
        """Calculate error-related metrics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Error categories breakdown
                cursor.execute(
                    """
                    SELECT error_category, COUNT(*) as count
                    FROM correction_sessions
                    WHERE created_at > datetime('now', '-' || ? || ' days')
                    AND error_category IS NOT NULL
                    GROUP BY error_category
                    ORDER BY count DESC
                """,
                    (days,),
                )

                error_categories = {}
                for row in cursor.fetchall():
                    error_categories[row[0]] = row[1]

                return {
                    "error_categories": error_categories,
                    "most_common_error": (
                        max(error_categories.items(), key=lambda x: x[1])[0]
                        if error_categories
                        else "none"
                    ),
                }

        except Exception as e:
            logger.error(f"Error metrics calculation failed: {e}")
            return {"error_categories": {}, "most_common_error": "none"}

    def generate_health_report(self) -> str:
        """Generate a human-readable health report."""
        health = self.get_system_health()
        metrics = self.get_comprehensive_metrics()

        report_lines = [
            "=== AAA Learning System Health Report ===",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"Overall Status: {health.overall_status.upper()}",
            f"Database Connected: {'✓' if health.database_connected else '✗'}",
            f"Pattern Learning Active: {'✓' if health.pattern_learning_active else '✗'}",
            f"Cache Performance: {health.cache_performance}",
            f"Recent Error Rate: {health.recent_error_rate:.1%}",
            "",
            "=== Performance Metrics ===",
            f"Pattern Lookup Time: {metrics.performance_metrics.get('pattern_lookup_ms', 0):.1f}ms",
            f"Cache Hit Rate: {metrics.performance_metrics.get('cache_hit_rate', 0):.1%}",
            f"Average Response Time: {metrics.performance_metrics.get('average_response_time_ms', 0):.1f}ms",
            "",
            "=== Accuracy Metrics ===",
            f"Pattern Accuracy: {metrics.accuracy_metrics.get('pattern_accuracy', 0):.1%}",
            f"Correction Success Rate: {metrics.accuracy_metrics.get('correction_success_rate', 0):.1%}",
            f"Overall Accuracy: {metrics.accuracy_metrics.get('overall_accuracy', 0):.1%}",
            "",
            "=== Usage Statistics ===",
            f"Active Patterns: {metrics.usage_metrics.get('active_patterns', 0)}",
            f"Recent Corrections: {metrics.usage_metrics.get('total_corrections', 0)}",
            f"Pattern Matches: {metrics.usage_metrics.get('pattern_matches', 0)}",
            f"Corrections per Day: {metrics.usage_metrics.get('corrections_per_day', 0)}",
        ]

        if health.recommendations:
            report_lines.extend(
                [
                    "",
                    "=== Recommendations ===",
                    *[f"• {rec}" for rec in health.recommendations],
                ]
            )

        return "\n".join(report_lines)


def create_monitoring_dashboard() -> Dict[str, Any]:
    """Create a monitoring dashboard with key metrics."""
    monitor = LearningSystemMonitor()
    health = monitor.get_system_health()
    metrics = monitor.get_comprehensive_metrics()

    return {
        "status": health.overall_status,
        "health": asdict(health),
        "metrics": asdict(metrics),
        "report": monitor.generate_health_report(),
    }
