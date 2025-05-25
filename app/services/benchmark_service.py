"""
Performance Benchmark Service for AAA Admin Monitoring

This service provides automated performance benchmarking capabilities,
testing system performance under various conditions and generating
comprehensive performance analysis.

Sprint 2.3 Features:
- Automated performance testing
- Benchmark result analysis
- Performance trend tracking
- Optimization recommendations
- Comparative analysis
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import statistics

from app.utils.saved_questions_db import DB_FILE
from app.utils.learning_metrics import LearningSystemMonitor
from app.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Individual benchmark test result."""

    test_name: str
    test_type: str  # 'query', 'learning', 'database', 'cache'
    duration_ms: float
    success: bool
    error_message: Optional[str]
    metadata: Dict[str, Any]
    timestamp: datetime


@dataclass
class BenchmarkSuite:
    """Complete benchmark suite results."""

    suite_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    total_tests: int
    successful_tests: int
    failed_tests: int
    avg_duration_ms: float
    results: List[BenchmarkResult]
    performance_score: float
    recommendations: List[str]


@dataclass
class PerformanceBaseline:
    """Performance baseline for comparison."""

    baseline_id: str
    created_at: datetime
    test_type: str
    avg_duration_ms: float
    success_rate: float
    metadata: Dict[str, Any]


class BenchmarkService:
    """Service for automated performance benchmarking."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the benchmark service.

        Args:
            db_path: Optional database path (for testing)
        """
        self.db_path = db_path or DB_FILE
        self.dashboard_service = DashboardService(db_path)
        self.monitor = LearningSystemMonitor(db_path)
        self._ensure_benchmark_tables()

    def _ensure_benchmark_tables(self):
        """Ensure benchmark tables exist."""
        try:
            with self._get_connection() as conn:
                # Benchmark suites table
                conn.execute(
                    """
                CREATE TABLE IF NOT EXISTS benchmark_suites (
                    suite_id TEXT PRIMARY KEY,
                    started_at DATETIME,
                    completed_at DATETIME,
                    total_tests INTEGER,
                    successful_tests INTEGER,
                    failed_tests INTEGER,
                    avg_duration_ms REAL,
                    performance_score REAL,
                    recommendations TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
                )

                # Individual benchmark results
                conn.execute(
                    """
                CREATE TABLE IF NOT EXISTS benchmark_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    suite_id TEXT,
                    test_name TEXT,
                    test_type TEXT,
                    duration_ms REAL,
                    success BOOLEAN,
                    error_message TEXT,
                    metadata TEXT,
                    timestamp DATETIME,
                    FOREIGN KEY (suite_id) REFERENCES benchmark_suites (suite_id)
                )
                """
                )

                # Performance baselines
                conn.execute(
                    """
                CREATE TABLE IF NOT EXISTS performance_baselines (
                    baseline_id TEXT PRIMARY KEY,
                    test_type TEXT,
                    avg_duration_ms REAL,
                    success_rate REAL,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
                )

                # Create indexes
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_benchmark_results_suite ON benchmark_results(suite_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_benchmark_results_type ON benchmark_results(test_type)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_benchmark_suites_date ON benchmark_suites(started_at)"
                )

        except Exception as e:
            logger.error(f"Error creating benchmark tables: {e}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    async def run_benchmark_suite(self, suite_name: str = "default") -> BenchmarkSuite:
        """Run a complete benchmark suite.

        Args:
            suite_name: Name of the benchmark suite

        Returns:
            Complete benchmark suite results
        """
        suite_id = f"{suite_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        started_at = datetime.now()

        logger.info(f"Starting benchmark suite: {suite_id}")

        try:
            # Define benchmark tests
            tests = [
                (
                    "database_connection",
                    "database",
                    self._benchmark_database_connection,
                ),
                ("query_performance", "query", self._benchmark_query_performance),
                ("cache_performance", "cache", self._benchmark_cache_performance),
                ("learning_system", "learning", self._benchmark_learning_system),
                ("dashboard_load", "dashboard", self._benchmark_dashboard_load),
                ("concurrent_queries", "query", self._benchmark_concurrent_queries),
                ("memory_usage", "system", self._benchmark_memory_usage),
                ("response_time", "system", self._benchmark_response_time),
            ]

            results = []

            # Run tests with thread pool for I/O bound operations
            with ThreadPoolExecutor(max_workers=4) as executor:
                for test_name, test_type, test_func in tests:
                    try:
                        logger.info(f"Running benchmark test: {test_name}")

                        # Run test with timeout
                        start_time = time.time()
                        future = executor.submit(test_func)

                        try:
                            result = future.result(timeout=30)  # 30 second timeout
                            duration_ms = (time.time() - start_time) * 1000

                            benchmark_result = BenchmarkResult(
                                test_name=test_name,
                                test_type=test_type,
                                duration_ms=duration_ms,
                                success=True,
                                error_message=None,
                                metadata=result,
                                timestamp=datetime.now(),
                            )

                        except Exception as e:
                            duration_ms = (time.time() - start_time) * 1000
                            benchmark_result = BenchmarkResult(
                                test_name=test_name,
                                test_type=test_type,
                                duration_ms=duration_ms,
                                success=False,
                                error_message=str(e),
                                metadata={},
                                timestamp=datetime.now(),
                            )

                        results.append(benchmark_result)

                    except Exception as e:
                        logger.error(f"Error running benchmark test {test_name}: {e}")
                        # Add failed result
                        results.append(
                            BenchmarkResult(
                                test_name=test_name,
                                test_type=test_type,
                                duration_ms=0.0,
                                success=False,
                                error_message=str(e),
                                metadata={},
                                timestamp=datetime.now(),
                            )
                        )

            # Calculate suite metrics
            completed_at = datetime.now()
            total_tests = len(results)
            successful_tests = sum(1 for r in results if r.success)
            failed_tests = total_tests - successful_tests

            successful_durations = [r.duration_ms for r in results if r.success]
            avg_duration_ms = (
                statistics.mean(successful_durations) if successful_durations else 0.0
            )

            # Calculate performance score (0-100)
            performance_score = self._calculate_performance_score(results)

            # Generate recommendations
            recommendations = self._generate_recommendations(results)

            # Create benchmark suite
            suite = BenchmarkSuite(
                suite_id=suite_id,
                started_at=started_at,
                completed_at=completed_at,
                total_tests=total_tests,
                successful_tests=successful_tests,
                failed_tests=failed_tests,
                avg_duration_ms=avg_duration_ms,
                results=results,
                performance_score=performance_score,
                recommendations=recommendations,
            )

            # Save to database
            self._save_benchmark_suite(suite)

            logger.info(
                f"Benchmark suite completed: {suite_id}, Score: {performance_score:.1f}"
            )
            return suite

        except Exception as e:
            logger.error(f"Error running benchmark suite: {e}")
            raise

    def _benchmark_database_connection(self) -> Dict[str, Any]:
        """Benchmark database connection performance."""
        try:
            start_time = time.time()
            with self._get_connection() as conn:
                # Test basic query
                cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master")
                result = cursor.fetchone()

                # Test more complex query
                cursor = conn.execute(
                    """
                SELECT COUNT(*) as count, 
                       AVG(CASE WHEN created_at > datetime('now', '-7 days') THEN 1 ELSE 0 END) as recent_ratio
                FROM intent_patterns
                """
                )
                pattern_stats = cursor.fetchone()

            connection_time = (time.time() - start_time) * 1000

            return {
                "connection_time_ms": connection_time,
                "tables_count": result[0] if result else 0,
                "pattern_count": pattern_stats["count"] if pattern_stats else 0,
                "recent_pattern_ratio": (
                    pattern_stats["recent_ratio"] if pattern_stats else 0.0
                ),
            }

        except Exception as e:
            logger.error(f"Database benchmark error: {e}")
            raise

    def _benchmark_query_performance(self) -> Dict[str, Any]:
        """Benchmark query performance."""
        try:
            queries = [
                ("simple_count", "SELECT COUNT(*) FROM intent_patterns"),
                (
                    "complex_join",
                    """
                SELECT 'intent' as pattern_type, COUNT(*) as count, AVG(pa.confidence_score) as avg_confidence
                FROM intent_patterns p
                LEFT JOIN pattern_applications pa ON p.id = pa.pattern_id
                GROUP BY 'intent'
                """,
                ),
                (
                    "time_range",
                    """
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM intent_patterns 
                WHERE created_at >= datetime('now', '-30 days')
                GROUP BY DATE(created_at)
                ORDER BY date
                """,
                ),
            ]

            query_results = {}

            with self._get_connection() as conn:
                for query_name, query_sql in queries:
                    start_time = time.time()
                    cursor = conn.execute(query_sql)
                    results = cursor.fetchall()
                    query_time = (time.time() - start_time) * 1000

                    query_results[query_name] = {
                        "duration_ms": query_time,
                        "row_count": len(results),
                    }

            return query_results

        except Exception as e:
            logger.error(f"Query benchmark error: {e}")
            raise

    def _benchmark_cache_performance(self) -> Dict[str, Any]:
        """Benchmark cache performance."""
        try:
            # Test dashboard service caching
            start_time = time.time()
            health_status = self.dashboard_service.get_health_status()
            first_call_time = (time.time() - start_time) * 1000

            # Second call should be faster if cached
            start_time = time.time()
            health_status_cached = self.dashboard_service.get_health_status()
            second_call_time = (time.time() - start_time) * 1000

            cache_efficiency = (
                max(0, (first_call_time - second_call_time) / first_call_time)
                if first_call_time > 0
                else 0
            )

            return {
                "first_call_ms": first_call_time,
                "second_call_ms": second_call_time,
                "cache_efficiency": cache_efficiency,
                "cache_hit_improvement": first_call_time - second_call_time,
            }

        except Exception as e:
            logger.error(f"Cache benchmark error: {e}")
            raise

    def _benchmark_learning_system(self) -> Dict[str, Any]:
        """Benchmark learning system performance."""
        try:
            start_time = time.time()

            # Test learning system health
            health = self.monitor.get_system_health()
            health_check_time = (time.time() - start_time) * 1000

            # Test pattern retrieval
            start_time = time.time()
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                SELECT id as pattern_id, 'intent' as pattern_type, success_rate as confidence_score 
                FROM intent_patterns 
                ORDER BY success_rate DESC 
                LIMIT 10
                """
                )
                patterns = cursor.fetchall()
            pattern_retrieval_time = (time.time() - start_time) * 1000

            return {
                "health_check_ms": health_check_time,
                "pattern_retrieval_ms": pattern_retrieval_time,
                "pattern_count": len(patterns),
                "database_connected": health.database_connected,
                "learning_active": health.pattern_learning_active,
                "cache_performance": health.cache_performance,
            }

        except Exception as e:
            logger.error(f"Learning system benchmark error: {e}")
            raise

    def _benchmark_dashboard_load(self) -> Dict[str, Any]:
        """Benchmark dashboard loading performance."""
        try:
            # Simulate dashboard component loading
            components = [
                ("health_status", lambda: self.dashboard_service.get_health_status()),
                (
                    "current_metrics",
                    lambda: self.dashboard_service._get_current_metrics(),
                ),
                ("system_info", lambda: self.dashboard_service._get_system_info()),
            ]

            component_times = {}
            total_start = time.time()

            for component_name, component_func in components:
                start_time = time.time()
                try:
                    result = component_func()
                    component_time = (time.time() - start_time) * 1000
                    component_times[component_name] = {
                        "duration_ms": component_time,
                        "success": True,
                    }
                except Exception as e:
                    component_time = (time.time() - start_time) * 1000
                    component_times[component_name] = {
                        "duration_ms": component_time,
                        "success": False,
                        "error": str(e),
                    }

            total_load_time = (time.time() - total_start) * 1000

            return {
                "total_load_time_ms": total_load_time,
                "component_times": component_times,
                "successful_components": sum(
                    1 for c in component_times.values() if c["success"]
                ),
            }

        except Exception as e:
            logger.error(f"Dashboard load benchmark error: {e}")
            raise

    def _benchmark_concurrent_queries(self) -> Dict[str, Any]:
        """Benchmark concurrent query performance."""
        try:
            import threading

            def run_query():
                with self._get_connection() as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM intent_patterns")
                    return cursor.fetchone()[0]

            # Run 5 concurrent queries
            threads = []
            results = []
            start_time = time.time()

            for i in range(5):
                thread = threading.Thread(target=lambda: results.append(run_query()))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            concurrent_time = (time.time() - start_time) * 1000

            return {
                "concurrent_queries": 5,
                "total_time_ms": concurrent_time,
                "avg_time_per_query_ms": concurrent_time / 5,
                "successful_queries": len(results),
            }

        except Exception as e:
            logger.error(f"Concurrent query benchmark error: {e}")
            raise

    def _benchmark_memory_usage(self) -> Dict[str, Any]:
        """Benchmark memory usage."""
        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()

            return {
                "rss_mb": memory_info.rss / 1024 / 1024,  # Resident Set Size
                "vms_mb": memory_info.vms / 1024 / 1024,  # Virtual Memory Size
                "memory_percent": process.memory_percent(),
                "cpu_percent": process.cpu_percent(),
            }

        except ImportError:
            # psutil not available, use basic metrics
            return {
                "rss_mb": 0,
                "vms_mb": 0,
                "memory_percent": 0,
                "cpu_percent": 0,
                "note": "psutil not available for detailed metrics",
            }
        except Exception as e:
            logger.error(f"Memory benchmark error: {e}")
            raise

    def _benchmark_response_time(self) -> Dict[str, Any]:
        """Benchmark overall system response time."""
        try:
            # Test multiple operations and measure response times
            operations = []

            # Database operations
            start_time = time.time()
            with self._get_connection() as conn:
                conn.execute("SELECT 1").fetchone()
            operations.append(("db_ping", (time.time() - start_time) * 1000))

            # Health check
            start_time = time.time()
            self.dashboard_service.get_health_status()
            operations.append(("health_check", (time.time() - start_time) * 1000))

            # Calculate statistics
            response_times = [op[1] for op in operations]

            return {
                "operations": dict(operations),
                "avg_response_time_ms": statistics.mean(response_times),
                "max_response_time_ms": max(response_times),
                "min_response_time_ms": min(response_times),
                "total_operations": len(operations),
            }

        except Exception as e:
            logger.error(f"Response time benchmark error: {e}")
            raise

    def _calculate_performance_score(self, results: List[BenchmarkResult]) -> float:
        """Calculate overall performance score (0-100)."""
        try:
            if not results:
                return 0.0

            # Success rate component (40% of score)
            success_rate = sum(1 for r in results if r.success) / len(results)
            success_score = success_rate * 40

            # Performance component (60% of score)
            successful_results = [r for r in results if r.success]
            if not successful_results:
                return success_score

            # Define performance thresholds (ms)
            thresholds = {
                "database": 100,
                "query": 500,
                "cache": 50,
                "learning": 200,
                "dashboard": 1000,
                "system": 100,
            }

            performance_scores = []
            for result in successful_results:
                threshold = thresholds.get(result.test_type, 500)
                # Score based on how much faster than threshold
                if result.duration_ms <= threshold:
                    score = 100
                elif result.duration_ms <= threshold * 2:
                    score = 100 - ((result.duration_ms - threshold) / threshold) * 50
                else:
                    score = 25  # Minimum score for working but slow operations

                performance_scores.append(score)

            avg_performance_score = (
                statistics.mean(performance_scores) if performance_scores else 0
            )
            performance_component = (avg_performance_score / 100) * 60

            total_score = success_score + performance_component
            return min(100, max(0, total_score))

        except Exception as e:
            logger.error(f"Error calculating performance score: {e}")
            return 0.0

    def _generate_recommendations(self, results: List[BenchmarkResult]) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []

        try:
            # Analyze failed tests
            failed_tests = [r for r in results if not r.success]
            if failed_tests:
                recommendations.append(
                    f"⚠️ {len(failed_tests)} tests failed - investigate error logs"
                )

            # Analyze slow operations
            successful_results = [r for r in results if r.success]
            if successful_results:
                avg_duration = statistics.mean(
                    [r.duration_ms for r in successful_results]
                )

                if avg_duration > 1000:
                    recommendations.append(
                        "🐌 Average response time > 1s - consider performance optimization"
                    )

                # Check specific test types
                db_tests = [r for r in successful_results if r.test_type == "database"]
                if (
                    db_tests
                    and statistics.mean([r.duration_ms for r in db_tests]) > 200
                ):
                    recommendations.append(
                        "💾 Database queries are slow - consider indexing or query optimization"
                    )

                cache_tests = [r for r in successful_results if r.test_type == "cache"]
                if (
                    cache_tests
                    and statistics.mean([r.duration_ms for r in cache_tests]) > 100
                ):
                    recommendations.append(
                        "🗄️ Cache performance is suboptimal - review caching strategy"
                    )

                query_tests = [r for r in successful_results if r.test_type == "query"]
                if (
                    query_tests
                    and statistics.mean([r.duration_ms for r in query_tests]) > 500
                ):
                    recommendations.append(
                        "🔍 Query performance needs improvement - optimize complex queries"
                    )

            # Success rate recommendations
            success_rate = (
                sum(1 for r in results if r.success) / len(results) if results else 0
            )
            if success_rate < 0.9:
                recommendations.append(
                    "❌ Success rate < 90% - system stability needs attention"
                )
            elif success_rate < 0.95:
                recommendations.append(
                    "⚡ Success rate < 95% - minor stability improvements needed"
                )

            # If no issues found
            if not recommendations:
                recommendations.append(
                    "✅ System performance is optimal - no immediate action required"
                )

            return recommendations

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return ["❓ Unable to generate recommendations due to analysis error"]

    def _save_benchmark_suite(self, suite: BenchmarkSuite):
        """Save benchmark suite to database."""
        try:
            with self._get_connection() as conn:
                # Save suite
                conn.execute(
                    """
                INSERT INTO benchmark_suites 
                (suite_id, started_at, completed_at, total_tests, successful_tests, 
                 failed_tests, avg_duration_ms, performance_score, recommendations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        suite.suite_id,
                        suite.started_at,
                        suite.completed_at,
                        suite.total_tests,
                        suite.successful_tests,
                        suite.failed_tests,
                        suite.avg_duration_ms,
                        suite.performance_score,
                        json.dumps(suite.recommendations),
                    ),
                )

                # Save individual results
                for result in suite.results:
                    conn.execute(
                        """
                    INSERT INTO benchmark_results 
                    (suite_id, test_name, test_type, duration_ms, success, error_message, metadata, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            suite.suite_id,
                            result.test_name,
                            result.test_type,
                            result.duration_ms,
                            result.success,
                            result.error_message,
                            json.dumps(result.metadata),
                            result.timestamp,
                        ),
                    )

                conn.commit()

        except Exception as e:
            logger.error(f"Error saving benchmark suite: {e}")

    def get_benchmark_history(self, days: int = 30) -> List[BenchmarkSuite]:
        """Get benchmark history for the specified period."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                SELECT * FROM benchmark_suites 
                WHERE started_at >= datetime('now', '-{} days')
                ORDER BY started_at DESC
                """.format(
                        days
                    )
                )

                suites = []
                for row in cursor.fetchall():
                    # Get results for this suite
                    results_cursor = conn.execute(
                        """
                    SELECT * FROM benchmark_results 
                    WHERE suite_id = ?
                    ORDER BY timestamp
                    """,
                        (row["suite_id"],),
                    )

                    results = []
                    for result_row in results_cursor.fetchall():
                        result = BenchmarkResult(
                            test_name=result_row["test_name"],
                            test_type=result_row["test_type"],
                            duration_ms=result_row["duration_ms"],
                            success=bool(result_row["success"]),
                            error_message=result_row["error_message"],
                            metadata=(
                                json.loads(result_row["metadata"])
                                if result_row["metadata"]
                                else {}
                            ),
                            timestamp=datetime.fromisoformat(result_row["timestamp"]),
                        )
                        results.append(result)

                    suite = BenchmarkSuite(
                        suite_id=row["suite_id"],
                        started_at=datetime.fromisoformat(row["started_at"]),
                        completed_at=(
                            datetime.fromisoformat(row["completed_at"])
                            if row["completed_at"]
                            else None
                        ),
                        total_tests=row["total_tests"],
                        successful_tests=row["successful_tests"],
                        failed_tests=row["failed_tests"],
                        avg_duration_ms=row["avg_duration_ms"],
                        results=results,
                        performance_score=row["performance_score"],
                        recommendations=(
                            json.loads(row["recommendations"])
                            if row["recommendations"]
                            else []
                        ),
                    )
                    suites.append(suite)

                return suites

        except Exception as e:
            logger.error(f"Error getting benchmark history: {e}")
            return []

    def create_performance_baseline(
        self, baseline_name: str, test_type: str = "all"
    ) -> PerformanceBaseline:
        """Create a performance baseline from recent benchmark data."""
        try:
            with self._get_connection() as conn:
                # Get recent benchmark results
                if test_type == "all":
                    cursor = conn.execute(
                        """
                    SELECT AVG(duration_ms) as avg_duration, 
                           AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) as success_rate,
                           COUNT(*) as total_count
                    FROM benchmark_results 
                    WHERE timestamp >= datetime('now', '-7 days')
                    """
                    )
                else:
                    cursor = conn.execute(
                        """
                    SELECT AVG(duration_ms) as avg_duration, 
                           AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) as success_rate,
                           COUNT(*) as total_count
                    FROM benchmark_results 
                    WHERE test_type = ? AND timestamp >= datetime('now', '-7 days')
                    """,
                        (test_type,),
                    )

                result = cursor.fetchone()

                if not result or result["total_count"] == 0:
                    raise ValueError(
                        f"No recent benchmark data found for test type: {test_type}"
                    )

                baseline_id = (
                    f"{baseline_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )

                baseline = PerformanceBaseline(
                    baseline_id=baseline_id,
                    created_at=datetime.now(),
                    test_type=test_type,
                    avg_duration_ms=result["avg_duration"] or 0.0,
                    success_rate=result["success_rate"] or 0.0,
                    metadata={
                        "sample_count": result["total_count"],
                        "baseline_name": baseline_name,
                    },
                )

                # Save baseline
                conn.execute(
                    """
                INSERT INTO performance_baselines 
                (baseline_id, test_type, avg_duration_ms, success_rate, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        baseline.baseline_id,
                        baseline.test_type,
                        baseline.avg_duration_ms,
                        baseline.success_rate,
                        json.dumps(baseline.metadata),
                    ),
                )

                conn.commit()
                return baseline

        except Exception as e:
            logger.error(f"Error creating performance baseline: {e}")
            raise
