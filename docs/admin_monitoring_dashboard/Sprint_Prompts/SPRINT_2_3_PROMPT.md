# SPRINT 2.3 PROMPT - Performance Benchmarks & Export

## PROJECT CONTEXT

You are working on the **Admin Monitoring Dashboard Project** - creating a web-based monitoring interface for the AAA (Ask Anything AI Assistant) Learning System. This is Sprint 2.3 of an 8-sprint project across 3 phases.

### Project Overview
The AAA is a healthcare data analysis assistant with a recently deployed Learning Enhancement system. We're building a modern, visual dashboard that allows non-technical healthcare administrators to monitor system health, performance, and learning metrics through a web interface.

### Current System Status (After Sprint 2.2)
The AAA now has:
- **Complete Phase 1**: Basic dashboard with health status, interactive features, and user testing
- **Historical Trends**: Time-series charts showing system performance over time
- **Learning Analytics**: Comprehensive learning system analytics with pattern effectiveness tracking
- **MetricsCollector**: Automated background data collection
- **Interactive Charts**: Bokeh visualizations with time period selectors and learning insights

### Sprint 2.3 Focus
This sprint focuses on **Performance Benchmarks & Export** - implementing automated performance benchmarking, comprehensive export capabilities, and professional report generation.

## SPRINT 2.3 OBJECTIVES

**Goal**: Implement automated performance benchmarking suite and comprehensive export capabilities with professional report generation for different audiences.

**Key Deliverables**:
1. Automated Performance Benchmark Service for system performance testing
2. Export Service with CSV/PDF report generation capabilities
3. Professional Report Templates for different stakeholder audiences
4. Scheduled Report Generation and automated delivery
5. Performance Analysis and Optimization Recommendations
6. Export Panel with intuitive interface for report generation

**User Impact**: Healthcare administrators can generate professional reports for stakeholders and automatically benchmark system performance.

## TECHNICAL REQUIREMENTS

### Performance Benchmark Service

Create `app/services/benchmark_service.py`:

```python
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

import asyncio
import json
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
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
                conn.execute("""
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
                """)
                
                # Individual benchmark results
                conn.execute("""
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
                """)
                
                # Performance baselines
                conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_baselines (
                    baseline_id TEXT PRIMARY KEY,
                    test_type TEXT,
                    avg_duration_ms REAL,
                    success_rate REAL,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # Create indexes
                conn.execute("CREATE INDEX IF NOT EXISTS idx_benchmark_results_suite ON benchmark_results(suite_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_benchmark_results_type ON benchmark_results(test_type)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_benchmark_suites_date ON benchmark_suites(started_at)")
                
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
                ("database_connection", "database", self._benchmark_database_connection),
                ("query_performance", "query", self._benchmark_query_performance),
                ("cache_performance", "cache", self._benchmark_cache_performance),
                ("learning_system", "learning", self._benchmark_learning_system),
                ("dashboard_load", "dashboard", self._benchmark_dashboard_load),
                ("concurrent_queries", "query", self._benchmark_concurrent_queries),
                ("memory_usage", "system", self._benchmark_memory_usage),
                ("response_time", "system", self._benchmark_response_time)
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
                                timestamp=datetime.now()
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
                                timestamp=datetime.now()
                            )
                        
                        results.append(benchmark_result)
                        
                    except Exception as e:
                        logger.error(f"Error running benchmark test {test_name}: {e}")
                        # Add failed result
                        results.append(BenchmarkResult(
                            test_name=test_name,
                            test_type=test_type,
                            duration_ms=0.0,
                            success=False,
                            error_message=str(e),
                            metadata={},
                            timestamp=datetime.now()
                        ))
            
            # Calculate suite metrics
            completed_at = datetime.now()
            total_tests = len(results)
            successful_tests = sum(1 for r in results if r.success)
            failed_tests = total_tests - successful_tests
            
            successful_durations = [r.duration_ms for r in results if r.success]
            avg_duration_ms = statistics.mean(successful_durations) if successful_durations else 0.0
            
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
                recommendations=recommendations
            )
            
            # Save to database
            self._save_benchmark_suite(suite)
            
            logger.info(f"Benchmark suite completed: {suite_id}, Score: {performance_score:.1f}")
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
                cursor = conn.execute("""
                SELECT COUNT(*) as count, 
                       AVG(CASE WHEN created_at > datetime('now', '-7 days') THEN 1 ELSE 0 END) as recent_ratio
                FROM learned_patterns
                """)
                pattern_stats = cursor.fetchone()
                
            connection_time = (time.time() - start_time) * 1000
            
            return {
                'connection_time_ms': connection_time,
                'tables_count': result[0] if result else 0,
                'pattern_count': pattern_stats['count'] if pattern_stats else 0,
                'recent_pattern_ratio': pattern_stats['recent_ratio'] if pattern_stats else 0.0
            }
            
        except Exception as e:
            logger.error(f"Database benchmark error: {e}")
            raise
    
    def _benchmark_query_performance(self) -> Dict[str, Any]:
        """Benchmark query performance."""
        try:
            queries = [
                ("simple_count", "SELECT COUNT(*) FROM learned_patterns"),
                ("complex_join", """
                SELECT p.pattern_type, COUNT(*) as count, AVG(p.confidence_score) as avg_confidence
                FROM learned_patterns p
                LEFT JOIN pattern_applications pa ON p.pattern_id = pa.pattern_id
                GROUP BY p.pattern_type
                """),
                ("time_range", """
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM learned_patterns 
                WHERE created_at >= datetime('now', '-30 days')
                GROUP BY DATE(created_at)
                ORDER BY date
                """)
            ]
            
            query_results = {}
            
            with self._get_connection() as conn:
                for query_name, query_sql in queries:
                    start_time = time.time()
                    cursor = conn.execute(query_sql)
                    results = cursor.fetchall()
                    query_time = (time.time() - start_time) * 1000
                    
                    query_results[query_name] = {
                        'duration_ms': query_time,
                        'row_count': len(results)
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
            
            cache_efficiency = max(0, (first_call_time - second_call_time) / first_call_time) if first_call_time > 0 else 0
            
            return {
                'first_call_ms': first_call_time,
                'second_call_ms': second_call_time,
                'cache_efficiency': cache_efficiency,
                'cache_hit_improvement': first_call_time - second_call_time
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
                cursor = conn.execute("""
                SELECT pattern_id, pattern_type, confidence_score 
                FROM learned_patterns 
                ORDER BY confidence_score DESC 
                LIMIT 10
                """)
                patterns = cursor.fetchall()
            pattern_retrieval_time = (time.time() - start_time) * 1000
            
            return {
                'health_check_ms': health_check_time,
                'pattern_retrieval_ms': pattern_retrieval_time,
                'pattern_count': len(patterns),
                'database_connected': health.database_connected,
                'learning_active': health.pattern_learning_active,
                'cache_performance': health.cache_performance
            }
            
        except Exception as e:
            logger.error(f"Learning system benchmark error: {e}")
            raise
    
    def _benchmark_dashboard_load(self) -> Dict[str, Any]:
        """Benchmark dashboard loading performance."""
        try:
            # Simulate dashboard component loading
            components = [
                ('health_status', lambda: self.dashboard_service.get_health_status()),
                ('current_metrics', lambda: self.dashboard_service._get_current_metrics()),
                ('system_info', lambda: self.dashboard_service._get_system_info())
            ]
            
            component_times = {}
            total_start = time.time()
            
            for component_name, component_func in components:
                start_time = time.time()
                try:
                    result = component_func()
                    component_time = (time.time() - start_time) * 1000
                    component_times[component_name] = {
                        'duration_ms': component_time,
                        'success': True
                    }
                except Exception as e:
                    component_time = (time.time() - start_time) * 1000
                    component_times[component_name] = {
                        'duration_ms': component_time,
                        'success': False,
                        'error': str(e)
                    }
            
            total_load_time = (time.time() - total_start) * 1000
            
            return {
                'total_load_time_ms': total_load_time,
                'component_times': component_times,
                'successful_components': sum(1 for c in component_times.values() if c['success'])
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
                    cursor = conn.execute("SELECT COUNT(*) FROM learned_patterns")
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
                'concurrent_queries': 5,
                'total_time_ms': concurrent_time,
                'avg_time_per_query_ms': concurrent_time / 5,
                'successful_queries': len(results)
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
                'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
                'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
                'memory_percent': process.memory_percent(),
                'cpu_percent': process.cpu_percent()
            }
            
        except ImportError:
            # psutil not available, use basic metrics
            return {
                'rss_mb': 0,
                'vms_mb': 0,
                'memory_percent': 0,
                'cpu_percent': 0,
                'note': 'psutil not available for detailed metrics'
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
            operations.append(('db_ping', (time.time() - start_time) * 1000))
            
            # Health check
            start_time = time.time()
            self.dashboard_service.get_health_status()
            operations.append(('health_check', (time.time() - start_time) * 1000))
            
            # Calculate statistics
            response_times = [op[1] for op in operations]
            
            return {
                'operations': dict(operations),
                'avg_response_time_ms': statistics.mean(response_times),
                'max_response_time_ms': max(response_times),
                'min_response_time_ms': min(response_times),
                'total_operations': len(operations)
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
                'database': 100,
                'query': 500,
                'cache': 50,
                'learning': 200,
                'dashboard': 1000,
                'system': 100
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
            
            avg_performance_score = statistics.mean(performance_scores) if performance_scores else 0
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
                recommendations.append(f"⚠️ {len(failed_tests)} tests failed - investigate error logs")
            
            # Analyze slow operations
            successful_results = [r for r in results if r.success]
            if successful_results:
                avg_duration = statistics.mean([r.duration_ms for r in successful_results])
                
                if avg_duration > 1000:
                    recommendations.append("🐌 Average response time > 1s - consider performance optimization")
                
                # Check specific test types
                db_tests = [r for r in successful_results if r.test_type == 'database']
                if db_tests and statistics.mean([r.duration_ms for r in db_tests]) > 200:
                    recommendations.append("💾 Database queries are slow - consider indexing or query optimization")
                
                cache_tests = [r for r in successful_results if r.test_type == 'cache']
                if cache_tests and statistics.mean([r.duration_ms for r in cache_tests]) > 100:
                    recommendations.append("🗄️ Cache performance is suboptimal - review caching strategy")
                
                query_tests = [r for r in successful_results if r.test_type == 'query']
                if query_tests and statistics.mean([r.duration_ms for r in query_tests]) > 500:
                    recommendations.append("🔍 Query performance needs improvement - optimize complex queries")
            
            # Success rate recommendations
            success_rate = sum(1 for r in results if r.success) / len(results) if results else 0
            if success_rate < 0.9:
                recommendations.append("❌ Success rate < 90% - system stability needs attention")
            elif success_rate < 0.95:
                recommendations.append("⚡ Success rate < 95% - minor stability improvements needed")
            
            # If no issues found
            if not recommendations:
                recommendations.append("✅ System performance is optimal - no immediate action required")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return ["❓ Unable to generate recommendations due to analysis error"]
    
    def _save_benchmark_suite(self, suite: BenchmarkSuite):
        """Save benchmark suite to database."""
        try:
            with self._get_connection() as conn:
                # Save suite
                conn.execute("""
                INSERT INTO benchmark_suites 
                (suite_id, started_at, completed_at, total_tests, successful_tests, 
                 failed_tests, avg_duration_ms, performance_score, recommendations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    suite.suite_id,
                    suite.started_at,
                    suite.completed_at,
                    suite.total_tests,
                    suite.successful_tests,
                    suite.failed_tests,
                    suite.avg_duration_ms,
                    suite.performance_score,
                    json.dumps(suite.recommendations)
                ))
                
                # Save individual results
                for result in suite.results:
                    conn.execute("""
                    INSERT INTO benchmark_results 
                    (suite_id, test_name, test_type, duration_ms, success, error_message, metadata, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        suite.suite_id,
                        result.test_name,
                        result.test_type,
                        result.duration_ms,
                        result.success,
                        result.error_message,
                        json.dumps(result.metadata),
                        result.timestamp
                    ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error saving benchmark suite: {e}")
    
    def get_benchmark_history(self, days: int = 30) -> List[BenchmarkSuite]:
        """Get benchmark history for the specified period."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                SELECT * FROM benchmark_suites 
                WHERE started_at >= datetime('now', '-{} days')
                ORDER BY started_at DESC
                """.format(days))
                
                suites = []
                for row in cursor.fetchall():
                    # Get results for this suite
                    results_cursor = conn.execute("""
                    SELECT * FROM benchmark_results 
                    WHERE suite_id = ?
                    ORDER BY timestamp
                    """, (row['suite_id'],))
                    
                    results = []
                    for result_row in results_cursor.fetchall():
                        result = BenchmarkResult(
                            test_name=result_row['test_name'],
                            test_type=result_row['test_type'],
                            duration_ms=result_row['duration_ms'],
                            success=bool(result_row['success']),
                            error_message=result_row['error_message'],
                            metadata=json.loads(result_row['metadata']) if result_row['metadata'] else {},
                            timestamp=datetime.fromisoformat(result_row['timestamp'])
                        )
                        results.append(result)
                    
                    suite = BenchmarkSuite(
                        suite_id=row['suite_id'],
                        started_at=datetime.fromisoformat(row['started_at']),
                        completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                        total_tests=row['total_tests'],
                        successful_tests=row['successful_tests'],
                        failed_tests=row['failed_tests'],
                        avg_duration_ms=row['avg_duration_ms'],
                        results=results,
                        performance_score=row['performance_score'],
                        recommendations=json.loads(row['recommendations']) if row['recommendations'] else []
                    )
                    suites.append(suite)
                
                return suites
                
        except Exception as e:
            logger.error(f"Error getting benchmark history: {e}")
            return []
    
    def create_performance_baseline(self, baseline_name: str, test_type: str = "all") -> PerformanceBaseline:
        """Create a performance baseline from recent benchmark data."""
        try:
            with self._get_connection() as conn:
                # Get recent benchmark results
                if test_type == "all":
                    cursor = conn.execute("""
                    SELECT AVG(duration_ms) as avg_duration, 
                           AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) as success_rate,
                           COUNT(*) as total_count
                    FROM benchmark_results 
                    WHERE timestamp >= datetime('now', '-7 days')
                    """)
                else:
                    cursor = conn.execute("""
                    SELECT AVG(duration_ms) as avg_duration, 
                           AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) as success_rate,
                           COUNT(*) as total_count
                    FROM benchmark_results 
                    WHERE test_type = ? AND timestamp >= datetime('now', '-7 days')
                    """, (test_type,))
                
                result = cursor.fetchone()
                
                if not result or result['total_count'] == 0:
                    raise ValueError(f"No recent benchmark data found for test type: {test_type}")
                
                baseline_id = f"{baseline_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                baseline = PerformanceBaseline(
                    baseline_id=baseline_id,
                    created_at=datetime.now(),
                    test_type=test_type,
                    avg_duration_ms=result['avg_duration'] or 0.0,
                    success_rate=result['success_rate'] or 0.0,
                    metadata={
                        'sample_count': result['total_count'],
                        'baseline_name': baseline_name
                    }
                )
                
                # Save baseline
                conn.execute("""
                INSERT INTO performance_baselines 
                (baseline_id, test_type, avg_duration_ms, success_rate, metadata)
                VALUES (?, ?, ?, ?, ?)
                """, (
                    baseline.baseline_id,
                    baseline.test_type,
                    baseline.avg_duration_ms,
                    baseline.success_rate,
                    json.dumps(baseline.metadata)
                ))
                
                conn.commit()
                return baseline
                
        except Exception as e:
            logger.error(f"Error creating performance baseline: {e}")
            raise
```

### Export Service

Create `app/services/export_service.py`:

```python
"""
Export Service for AAA Admin Monitoring

This service provides comprehensive export capabilities for dashboard data,
including CSV exports, PDF reports, and scheduled report generation.

Sprint 2.3 Features:
- CSV data export
- PDF report generation
- Professional report templates
- Scheduled report delivery
- Multi-format export support
"""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path
import tempfile

from app.utils.saved_questions_db import DB_FILE
from app.services.dashboard_service import DashboardService
from app.services.learning_analytics import LearningAnalyticsService
from app.services.benchmark_service import BenchmarkService

logger = logging.getLogger(__name__)

# Try to import reportlab for PDF generation
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.linecharts import HorizontalLineChart
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("ReportLab not available - PDF export will be disabled")


@dataclass
class ExportRequest:
    """Export request configuration."""
    export_type: str  # 'csv', 'pdf', 'json'
    data_types: List[str]  # ['health', 'performance', 'learning', 'benchmarks']
    time_period: int  # days
    format_options: Dict[str, Any]
    recipient_email: Optional[str] = None
    schedule: Optional[str] = None  # 'daily', 'weekly', 'monthly'


@dataclass
class ExportResult:
    """Export operation result."""
    export_id: str
    export_type: str
    file_path: Optional[str]
    file_content: Optional[bytes]
    success: bool
    error_message: Optional[str]
    created_at: datetime
    metadata: Dict[str, Any]


class ExportService:
    """Service for data export and report generation."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the export service.
        
        Args:
            db_path: Optional database path (for testing)
        """
        self.db_path = db_path or DB_FILE
        self.dashboard_service = DashboardService(db_path)
        self.analytics_service = LearningAnalyticsService(db_path)
        self.benchmark_service = BenchmarkService(db_path)
        
        # Create export directory
        self.export_dir = Path("exports")
        self.export_dir.mkdir(exist_ok=True)
    
    def export_data(self, request: ExportRequest) -> ExportResult:
        """Export data based on the request configuration.
        
        Args:
            request: Export request configuration
            
        Returns:
            Export result with file path or content
        """
        export_id = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            logger.info(f"Starting export: {export_id}, type: {request.export_type}")
            
            # Collect data based on request
            data = self._collect_export_data(request)
            
            # Generate export based on type
            if request.export_type == 'csv':
                result = self._export_csv(export_id, data, request)
            elif request.export_type == 'pdf':
                result = self._export_pdf(export_id, data, request)
            elif request.export_type == 'json':
                result = self._export_json(export_id, data, request)
            else:
                raise ValueError(f"Unsupported export type: {request.export_type}")
            
            logger.info(f"Export completed successfully: {export_id}")
            return result
            
        except Exception as e:
            logger.error(f"Export failed: {export_id}, error: {e}")
            return ExportResult(
                export_id=export_id,
                export_type=request.export_type,
                file_path=None,
                file_content=None,
                success=False,
                error_message=str(e),
                created_at=datetime.now(),
                metadata={}
            )
    
    def _collect_export_data(self, request: ExportRequest) -> Dict[str, Any]:
        """Collect data for export based on request."""
        data = {}
        
        try:
            if 'health' in request.data_types:
                data['health'] = {
                    'current_status': self.dashboard_service.get_health_status(),
                    'timestamp': datetime.now().isoformat()
                }
            
            if 'performance' in request.data_types:
                # Get performance metrics from dashboard
                data['performance'] = {
                    'current_metrics': self.dashboard_service._get_current_metrics(),
                    'system_info': self.dashboard_service._get_system_info(),
                    'timestamp': datetime.now().isoformat()
                }
            
            if 'learning' in request.data_types:
                data['learning'] = {
                    'pattern_effectiveness': self.analytics_service.get_pattern_effectiveness(request.time_period),
                    'correction_analysis': self.analytics_service.get_correction_analysis(request.time_period),
                    'learning_progress': self.analytics_service.get_learning_progress(request.time_period),
                    'user_feedback': self.analytics_service.get_user_feedback_analytics(request.time_period),
                    'timestamp': datetime.now().isoformat()
                }
            
            if 'benchmarks' in request.data_types:
                benchmark_history = self.benchmark_service.get_benchmark_history(request.time_period)
                data['benchmarks'] = {
                    'recent_suites': benchmark_history,
                    'summary': self._summarize_benchmarks(benchmark_history),
                    'timestamp': datetime.now().isoformat()
                }
            
            return data
            
        except Exception as e:
            logger.error(f"Error collecting export data: {e}")
            raise
    
    def _summarize_benchmarks(self, benchmark_history: List) -> Dict[str, Any]:
        """Summarize benchmark history for export."""
        if not benchmark_history:
            return {}
        
        try:
            total_suites = len(benchmark_history)
            avg_score = sum(suite.performance_score for suite in benchmark_history) / total_suites
            avg_duration = sum(suite.avg_duration_ms for suite in benchmark_history) / total_suites
            
            return {
                'total_suites': total_suites,
                'avg_performance_score': avg_score,
                'avg_duration_ms': avg_duration,
                'latest_score': benchmark_history[0].performance_score if benchmark_history else 0,
                'trend': 'improving' if len(benchmark_history) > 1 and 
                        benchmark_history[0].performance_score > benchmark_history[-1].performance_score else 'stable'
            }
            
        except Exception as e:
            logger.error(f"Error summarizing benchmarks: {e}")
            return {}
    
    def _export_csv(self, export_id: str, data: Dict[str, Any], request: ExportRequest) -> ExportResult:
        """Export data as CSV format."""
        try:
            file_path = self.export_dir / f"{export_id}.csv"
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow(['Export ID', export_id])
                writer.writerow(['Generated', datetime.now().isoformat()])
                writer.writerow(['Time Period (days)', request.time_period])
                writer.writerow([])  # Empty row
                
                # Export each data type
                for data_type, data_content in data.items():
                    writer.writerow([f'=== {data_type.upper()} DATA ==='])
                    
                    if data_type == 'health':
                        self._write_health_csv(writer, data_content)
                    elif data_type == 'performance':
                        self._write_performance_csv(writer, data_content)
                    elif data_type == 'learning':
                        self._write_learning_csv(writer, data_content)
                    elif data_type == 'benchmarks':
                        self._write_benchmarks_csv(writer, data_content)
                    
                    writer.writerow([])  # Empty row between sections
            
            return ExportResult(
                export_id=export_id,
                export_type='csv',
                file_path=str(file_path),
                file_content=None,
                success=True,
                error_message=None,
                created_at=datetime.now(),
                metadata={'file_size': file_path.stat().st_size}
            )
            
        except Exception as e:
            logger.error(f"CSV export error: {e}")
            raise
    
    def _write_health_csv(self, writer, health_data):
        """Write health data to CSV."""
        writer.writerow(['Component', 'Status', 'Details'])
        
        health_status = health_data['current_status']
        for component, details in health_status.components.items():
            writer.writerow([component, details.get('status', 'unknown'), str(details)])
        
        writer.writerow([])
        writer.writerow(['Overall Status', health_status.overall_status])
        writer.writerow(['Last Updated', health_status.last_updated])
    
    def _write_performance_csv(self, writer, performance_data):
        """Write performance data to CSV."""
        writer.writerow(['Metric', 'Value', 'Unit'])
        
        current_metrics = performance_data['current_metrics']
        for metric, value in current_metrics.items():
            writer.writerow([metric, value, ''])
    
    def _write_learning_csv(self, writer, learning_data):
        """Write learning data to CSV."""
        # Pattern effectiveness
        writer.writerow(['=== PATTERN EFFECTIVENESS ==='])
        writer.writerow(['Pattern ID', 'Type', 'Success Rate', 'Total Applications', 'Trend'])
        
        for pattern in learning_data['pattern_effectiveness']:
            writer.writerow([
                pattern.pattern_id,
                pattern.pattern_type,
                f"{pattern.success_rate:.2%}",
                pattern.total_applications,
                pattern.trend
            ])
        
        writer.writerow([])
        
        # Correction analysis
        writer.writerow(['=== CORRECTION ANALYSIS ==='])
        correction_analysis = learning_data['correction_analysis']
        writer.writerow(['Total Corrections', correction_analysis.total_corrections])
        writer.writerow(['Successful Corrections', correction_analysis.successful_corrections])
        writer.writerow(['Success Rate', f"{correction_analysis.success_rate:.2%}"])
        writer.writerow(['Avg Time to Success (min)', f"{correction_analysis.avg_time_to_success:.1f}"])
    
    def _write_benchmarks_csv(self, writer, benchmark_data):
        """Write benchmark data to CSV."""
        writer.writerow(['Suite ID', 'Started At', 'Performance Score', 'Total Tests', 'Success Rate'])
        
        for suite in benchmark_data['recent_suites']:
            success_rate = suite.successful_tests / suite.total_tests if suite.total_tests > 0 else 0
            writer.writerow([
                suite.suite_id,
                suite.started_at.isoformat(),
                f"{suite.performance_score:.1f}",
                suite.total_tests,
                f"{success_rate:.2%}"
            ])
    
    def _export_pdf(self, export_id: str, data: Dict[str, Any], request: ExportRequest) -> ExportResult:
        """Export data as PDF report."""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab is required for PDF export")
        
        try:
            file_path = self.export_dir / f"{export_id}.pdf"
            
            # Create PDF document
            doc = SimpleDocTemplate(
                str(file_path),
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # Build story (content)
            story = []
            styles = getSampleStyleSheet()
            
            # Title page
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                alignment=1  # Center
            )
            
            story.append(Paragraph("AAA System Monitoring Report", title_style))
            story.append(Spacer(1, 20))
            
            # Report metadata
            story.append(Paragraph(f"<b>Report ID:</b> {export_id}", styles['Normal']))
            story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
            story.append(Paragraph(f"<b>Time Period:</b> {request.time_period} days", styles['Normal']))
            story.append(Spacer(1, 30))
            
            # Add sections for each data type
            for data_type, data_content in data.items():
                if data_type == 'health':
                    self._add_health_pdf_section(story, data_content, styles)
                elif data_type == 'performance':
                    self._add_performance_pdf_section(story, data_content, styles)
                elif data_type == 'learning':
                    self._add_learning_pdf_section(story, data_content, styles)
                elif data_type == 'benchmarks':
                    self._add_benchmarks_pdf_section(story, data_content, styles)
                
                story.append(PageBreak())
            
            # Build PDF
            doc.build(story)
            
            return ExportResult(
                export_id=export_id,
                export_type='pdf',
                file_path=str(file_path),
                file_content=None,
                success=True,
                error_message=None,
                created_at=datetime.now(),
                metadata={'file_size': file_path.stat().st_size}
            )
            
        except Exception as e:
            logger.error(f"PDF export error: {e}")
            raise
    
    def _add_health_pdf_section(self, story, health_data, styles):
        """Add health section to PDF."""
        story.append(Paragraph("System Health Status", styles['Heading1']))
        story.append(Spacer(1, 12))
        
        health_status = health_data['current_status']
        
        # Overall status
        status_color = colors.green if health_status.overall_status == 'healthy' else colors.red
        story.append(Paragraph(f"<b>Overall Status:</b> <font color='{status_color}'>{health_status.overall_status.upper()}</font>", styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Component status table
        component_data = [['Component', 'Status', 'Details']]
        for component, details in health_status.components.items():
            status = details.get('status', 'unknown')
            component_data.append([component.title(), status, str(details.get('icon', ''))])
        
        component_table = Table(component_data)
        component_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(component_table)
        story.append(Spacer(1, 20))
        
        # Recommendations
        if health_status.recommendations:
            story.append(Paragraph("Recommendations:", styles['Heading2']))
            for rec in health_status.recommendations:
                story.append(Paragraph(f"• {rec}", styles['Normal']))
            story.append(Spacer(1, 12))
    
    def _add_performance_pdf_section(self, story, performance_data, styles):
        """Add performance section to PDF."""
        story.append(Paragraph("Performance Metrics", styles['Heading1']))
        story.append(Spacer(1, 12))
        
        # Current metrics table
        metrics_data = [['Metric', 'Value']]
        current_metrics = performance_data['current_metrics']
        
        for metric, value in current_metrics.items():
            if isinstance(value, float):
                formatted_value = f"{value:.2f}"
            else:
                formatted_value = str(value)
            metrics_data.append([metric.replace('_', ' ').title(), formatted_value])
        
        metrics_table = Table(metrics_data)
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(metrics_table)
    
    def _add_learning_pdf_section(self, story, learning_data, styles):
        """Add learning analytics section to PDF."""
        story.append(Paragraph("Learning System Analytics", styles['Heading1']))
        story.append(Spacer(1, 12))
        
        # Learning progress summary
        progress = learning_data['learning_progress']
        story.append(Paragraph(f"<b>Overall Learning Rate:</b> {progress.overall_learning_rate:.1%}", styles['Normal']))
        story.append(Paragraph(f"<b>Patterns Learned:</b> {progress.patterns_learned}", styles['Normal']))
        story.append(Paragraph(f"<b>Learning Velocity:</b> {progress.learning_velocity:.1f} patterns/day", styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Top patterns table
        story.append(Paragraph("Top Performing Patterns", styles['Heading2']))
        pattern_data = [['Pattern ID', 'Type', 'Success Rate', 'Applications']]
        
        top_patterns = sorted(learning_data['pattern_effectiveness'], 
                            key=lambda p: p.success_rate, reverse=True)[:10]
        
        for pattern in top_patterns:
            pattern_data.append([
                pattern.pattern_id[:20] + "..." if len(pattern.pattern_id) > 20 else pattern.pattern_id,
                pattern.pattern_type,
                f"{pattern.success_rate:.1%}",
                str(pattern.total_applications)
            ])
        
        pattern_table = Table(pattern_data)
        pattern_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(pattern_table)
    
    def _add_benchmarks_pdf_section(self, story, benchmark_data, styles):
        """Add benchmarks section to PDF."""
        story.append(Paragraph("Performance Benchmarks", styles['Heading1']))
        story.append(Spacer(1, 12))
        
        # Summary
        summary = benchmark_data['summary']
        if summary:
            story.append(Paragraph(f"<b>Total Benchmark Suites:</b> {summary['total_suites']}", styles['Normal']))
            story.append(Paragraph(f"<b>Average Performance Score:</b> {summary['avg_performance_score']:.1f}/100", styles['Normal']))
            story.append(Paragraph(f"<b>Average Duration:</b> {summary['avg_duration_ms']:.1f}ms", styles['Normal']))
            story.append(Spacer(1, 12))
        
        # Recent benchmarks table
        story.append(Paragraph("Recent Benchmark Results", styles['Heading2']))
        benchmark_data_table = [['Suite ID', 'Date', 'Score', 'Tests', 'Success Rate']]
        
        for suite in benchmark_data['recent_suites'][:10]:  # Last 10 suites
            success_rate = suite.successful_tests / suite.total_tests if suite.total_tests > 0 else 0
            benchmark_data_table.append([
                suite.suite_id[:20] + "..." if len(suite.suite_id) > 20 else suite.suite_id,
                suite.started_at.strftime('%Y-%m-%d'),
                f"{suite.performance_score:.1f}",
                str(suite.total_tests),
                f"{success_rate:.1%}"
            ])
        
        benchmark_table = Table(benchmark_data_table)
        benchmark_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(benchmark_table)
    
    def _export_json(self, export_id: str, data: Dict[str, Any], request: ExportRequest) -> ExportResult:
        """Export data as JSON format."""
        try:
            file_path = self.export_dir / f"{export_id}.json"
            
            # Convert data to JSON-serializable format
            json_data = {
                'export_id': export_id,
                'generated_at': datetime.now().isoformat(),
                'time_period_days': request.time_period,
                'data_types': request.data_types,
                'data': self._serialize_for_json(data)
            }
            
            with open(file_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(json_data, jsonfile, indent=2, default=str)
            
            return ExportResult(
                export_id=export_id,
                export_type='json',
                file_path=str(file_path),
                file_content=None,
                success=True,
                error_message=None,
                created_at=datetime.now(),
                metadata={'file_size': file_path.stat().st_size}
            )
            
        except Exception as e:
            logger.error(f"JSON export error: {e}")
            raise
    
    def _serialize_for_json(self, data: Any) -> Any:
        """Convert data to JSON-serializable format."""
        if hasattr(data, '__dict__'):
            # Convert dataclass or object to dict
            return {k: self._serialize_for_json(v) for k, v in data.__dict__.items()}
        elif isinstance(data, dict):
            return {k: self._serialize_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._serialize_for_json(item) for item in data]
        elif isinstance(data, (datetime, )):
            return data.isoformat()
        else:
            return data
    
    def get_export_templates(self) -> List[Dict[str, Any]]:
        """Get available export templates."""
        return [
            {
                'id': 'executive_summary',
                'name': 'Executive Summary',
                'description': 'High-level overview for executives',
                'data_types': ['health', 'performance'],
                'format': 'pdf',
                'time_period': 7
            },
            {
                'id': 'technical_report',
                'name': 'Technical Report',
                'description': 'Detailed technical analysis',
                'data_types': ['health', 'performance', 'learning', 'benchmarks'],
                'format': 'pdf',
                'time_period': 30
            },
            {
                'id': 'learning_analytics',
                'name': 'Learning Analytics Report',
                'description': 'Focus on learning system performance',
                'data_types': ['learning'],
                'format': 'pdf',
                'time_period': 30
            },
            {
                'id': 'performance_data',
                'name': 'Performance Data Export',
                'description': 'Raw performance data for analysis',
                'data_types': ['performance', 'benchmarks'],
                'format': 'csv',
                'time_period': 90
            },
            {
                'id': 'complete_export',
                'name': 'Complete System Export',
                'description': 'All available data in JSON format',
                'data_types': ['health', 'performance', 'learning', 'benchmarks'],
                'format': 'json',
                'time_period': 30
            }
        ]
```

### Export Panel Component

Create `app/components/admin_dashboard/export_panel.py`:

```python
"""
Export Panel Component for Admin Dashboard

Provides user interface for data export and report generation.

Sprint 2.3 Features:
- Export template selection
- Custom export configuration
- Report generation interface
- Download management
"""

import panel as pn
import asyncio
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

from app.services.export_service import ExportService, ExportRequest, ExportResult

logger = logging.getLogger(__name__)

pn.extension('bokeh')


class ExportPanel:
    """Panel for data export and report generation."""
    
    def __init__(self, export_service: Optional[ExportService] = None):
        """Initialize the export panel.
        
        Args:
            export_service: Optional export service (for testing)
        """
        self.export_service = export_service or ExportService()
        
        # Create UI components
        self._create_components()
    
    def _create_components(self):
        """Create all UI components."""
        # Template selector
        templates = self.export_service.get_export_templates()
        template_options = {t['name']: t['id'] for t in templates}
        
        self.template_selector = pn.widgets.Select(
            name="Report Template",
            value=list(template_options.values())[0],
            options=template_options,
            width=300
        )
        
        # Custom configuration
        self.data_type_selector = pn.widgets.CheckBoxGroup(
            name="Data Types",
            value=['health', 'performance'],
            options=['health', 'performance', 'learning', 'benchmarks'],
            inline=False
        )
        
        self.format_selector = pn.widgets.RadioButtonGroup(
            name="Export Format",
            value='pdf',
            options=['csv', 'pdf', 'json'],
            button_type='primary'
        )
        
        self.time_period_slider = pn.widgets.IntSlider(
            name="Time Period (days)",
            value=30,
            start=7,
            end=90,
            step=7,
            width=300
        )
        
        # Export buttons
        self.export_button = pn.widgets.Button(
            name="Generate Report",
            button_type='primary',
            width=150
        )
        
        self.template_export_button = pn.widgets.Button(
            name="Use Template",
            button_type='success',
            width=150
        )
        
        # Status and results
        self.status_text = pn.pane.HTML(
            "<p>Ready to generate reports</p>",
            width=600
        )
        
        self.download_links = pn.Column(width=600)
        
        # Bind events
        self.template_selector.param.watch(self._on_template_change, 'value')
        self.export_button.on_click(self._on_custom_export)
        self.template_export_button.on_click(self._on_template_export)
    
    def _on_template_change(self, event):
        """Handle template selection change."""
        try:
            templates = self.export_service.get_export_templates()
            selected_template = next(t for t in templates if t['id'] == event.new)
            
            # Update form with template values
            self.data_type_selector.value = selected_template['data_types']
            self.format_selector.value = selected_template['format']
            self.time_period_slider.value = selected_template['time_period']
            
        except Exception as e:
            logger.error(f"Error updating template: {e}")
    
    def _on_custom_export(self, event):
        """Handle custom export button click."""
        try:
            self.status_text.object = "<p>🔄 Generating custom report...</p>"
            
            # Create export request
            request = ExportRequest(
                export_type=self.format_selector.value,
                data_types=self.data_type_selector.value,
                time_period=self.time_period_slider.value,
                format_options={}
            )
            
            # Run export in background
            asyncio.create_task(self._run_export(request, "Custom Report"))
            
        except Exception as e:
            logger.error(f"Error starting custom export: {e}")
            self.status_text.object = f"<p>❌ Error: {str(e)}</p>"
    
    def _on_template_export(self, event):
        """Handle template export button click."""
        try:
            self.status_text.object = "<p>🔄 Generating template report...</p>"
            
            # Get selected template
            templates = self.export_service.get_export_templates()
            selected_template = next(t for t in templates if t['id'] == self.template_selector.value)
            
            # Create export request from template
            request = ExportRequest(
                export_type=selected_template['format'],
                data_types=selected_template['data_types'],
                time_period=selected_template['time_period'],
                format_options={}
            )
            
            # Run export in background
            asyncio.create_task(self._run_export(request, selected_template['name']))
            
        except Exception as e:
            logger.error(f"Error starting template export: {e}")
            self.status_text.object = f"<p>❌ Error: {str(e)}</p>"
    
    async def _run_export(self, request: ExportRequest, report_name: str):
        """Run export operation asynchronously."""
        try:
            # Run export
            result = self.export_service.export_data(request)
            
            if result.success:
                self.status_text.object = f"<p>✅ {report_name} generated successfully!</p>"
                
                # Add download link
                download_link = self._create_download_link(result, report_name)
                self.download_links.append(download_link)
                
                # Keep only last 5 downloads
                if len(self.download_links) > 5:
                    self.download_links.pop(0)
                    
            else:
                self.status_text.object = f"<p>❌ Export failed: {result.error_message}</p>"
                
        except Exception as e:
            logger.error(f"Error running export: {e}")
            self.status_text.object = f"<p>❌ Export error: {str(e)}</p>"
    
    def _create_download_link(self, result: ExportResult, report_name: str) -> pn.Row:
        """Create download link for export result."""
        try:
            file_size_mb = result.metadata.get('file_size', 0) / (1024 * 1024)
            
            download_html = f"""
            <div style="background: #f0f8ff; padding: 10px; border-radius: 5px; margin: 5px 0;">
                <h4 style="margin: 0 0 5px 0;">📄 {report_name}</h4>
                <p style="margin: 0; color: #666;">
                    Format: {result.export_type.upper()} | 
                    Size: {file_size_mb:.2f} MB | 
                    Generated: {result.created_at.strftime('%Y-%m-%d %H:%M')}
                </p>
                <a href="/download/{result.export_id}" 
                   style="color: #0066cc; text-decoration: none;">
                   📥 Download Report
                </a>
            </div>
            """
            
            return pn.pane.HTML(download_html, width=580)
            
        except Exception as e:
            logger.error(f"Error creating download link: {e}")
            return pn.pane.HTML("<p>Error creating download link</p>")
    
    def get_panel(self):
        """Get the complete export panel."""
        return pn.Column(
            pn.pane.HTML("<h2>📊 Export & Reports</h2>"),
            
            # Template section
            pn.Row(
                pn.Column(
                    pn.pane.HTML("<h3>📋 Quick Templates</h3>"),
                    self.template_selector,
                    self.template_export_button,
                    width=350
                ),
                pn.Spacer(width=50),
                pn.Column(
                    pn.pane.HTML("<h3>⚙️ Custom Export</h3>"),
                    self.data_type_selector,
                    self.format_selector,
                    self.time_period_slider,
                    self.export_button,
                    width=350
                )
            ),
            
            pn.Divider(),
            
            # Status and downloads
            pn.pane.HTML("<h3>📥 Export Status & Downloads</h3>"),
            self.status_text,
            self.download_links,
            
            width=800
        )
```

## TESTING REQUIREMENTS

### Unit Tests

Create `tests/services/test_benchmark_service.py`:

```python
"""
Tests for Benchmark Service

Sprint 2.3 Testing:
- Benchmark execution
- Performance scoring
- Recommendation generation
- Data persistence
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime

from app.services.benchmark_service import BenchmarkService, BenchmarkResult, BenchmarkSuite


class TestBenchmarkService:
    """Test cases for BenchmarkService."""
    
    @pytest.fixture
    def benchmark_service(self, tmp_path):
        """Create benchmark service with test database."""
        db_path = tmp_path / "test_benchmark.db"
        return BenchmarkService(str(db_path))
    
    @pytest.mark.asyncio
    async def test_run_benchmark_suite(self, benchmark_service):
        """Test running a complete benchmark suite."""
        suite = await benchmark_service.run_benchmark_suite("test_suite")
        
        assert suite is not None
        assert suite.suite_id.startswith("test_suite_")
        assert suite.total_tests > 0
        assert suite.performance_score >= 0
        assert suite.performance_score <= 100
        assert len(suite.results) == suite.total_tests
        assert len(suite.recommendations) > 0
    
    def test_calculate_performance_score(self, benchmark_service):
        """Test performance score calculation."""
        # Create mock results
        results = [
            BenchmarkResult("test1", "database", 50.0, True, None, {}, datetime.now()),
            BenchmarkResult("test2", "query", 200.0, True, None, {}, datetime.now()),
            BenchmarkResult("test3", "cache", 25.0, True, None, {}, datetime.now()),
            BenchmarkResult("test4", "system", 1000.0, False, "Error", {}, datetime.now())
        ]
        
        score = benchmark_service._calculate_performance_score(results)
        
        assert 0 <= score <= 100
        # Should be less than 100 due to one failed test and some slow operations
        assert score < 100
    
    def test_generate_recommendations(self, benchmark_service):
        """Test recommendation generation."""
        # Create results with various performance characteristics
        results = [
            BenchmarkResult("fast_test", "database", 50.0, True, None, {}, datetime.now()),
            BenchmarkResult("slow_test", "query", 2000.0, True, None, {}, datetime.now()),
            BenchmarkResult("failed_test", "cache", 0.0, False, "Connection error", {}, datetime.now())
        ]
        
        recommendations = benchmark_service._generate_recommendations(results)
        
        assert len(recommendations) > 0
        # Should include recommendations for failed test and slow query
        assert any("failed" in rec.lower() for rec in recommendations)
    
    def test_benchmark_database_connection(self, benchmark_service):
        """Test database connection benchmark."""
        result = benchmark_service._benchmark_database_connection()
        
        assert isinstance(result, dict)
        assert 'connection_time_ms' in result
        assert result['connection_time_ms'] >= 0
    
    def test_benchmark_query_performance(self, benchmark_service):
        """Test query performance benchmark."""
        result = benchmark_service._benchmark_query_performance()
        
        assert isinstance(result, dict)
        assert len(result) > 0
        
        # Check that all queries have duration and row count
        for query_name, query_result in result.items():
            assert 'duration_ms' in query_result
            assert 'row_count' in query_result
            assert query_result['duration_ms'] >= 0
    
    def test_get_benchmark_history(self, benchmark_service):
        """Test getting benchmark history."""
        # Initially should be empty
        history = benchmark_service.get_benchmark_history(30)
        assert history == []
        
        # After running a benchmark, should have results
        # Note: This would require actually running a benchmark first
        # In a real test, you might mock the database or use fixtures
```

### Integration Tests

Create `tests/services/test_export_service.py`:

```python
"""
Tests for Export Service

Sprint 2.3 Testing:
- Data export functionality
- Report generation
- Format handling
- Template system
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch

from app.services.export_service import ExportService, ExportRequest, ExportResult


class TestExportService:
    """Test cases for ExportService."""
    
    @pytest.fixture
    def export_service(self, tmp_path):
        """Create export service with test database."""
        db_path = tmp_path / "test_export.db"
        service = ExportService(str(db_path))
        # Override export directory for testing
        service.export_dir = tmp_path / "exports"
        service.export_dir.mkdir(exist_ok=True)
        return service
    
    def test_export_csv(self, export_service):
        """Test CSV export functionality."""
        request = ExportRequest(
            export_type='csv',
            data_types=['health'],
            time_period=7,
            format_options={}
        )
        
        with patch.object(export_service.dashboard_service, 'get_health_status') as mock_health:
            mock_health.return_value = Mock(
                overall_status='healthy',
                components={'database': {'status': 'connected'}},
                recommendations=[],
                last_updated='2024-01-01'
            )
            
            result = export_service.export_data(request)
            
            assert result.success
            assert result.export_type == 'csv'
            assert result.file_path is not None
            assert Path(result.file_path).exists()
    
    def test_export_json(self, export_service):
        """Test JSON export functionality."""
        request = ExportRequest(
            export_type='json',
            data_types=['performance'],
            time_period=30,
            format_options={}
        )
        
        with patch.object(export_service.dashboard_service, '_get_current_metrics') as mock_metrics:
            mock_metrics.return_value = {'response_time': 100, 'error_rate': 0.01}
            
            result = export_service.export_data(request)
            
            assert result.success
            assert result.export_type == 'json'
            assert result.file_path is not None
            
            # Verify JSON content
            with open(result.file_path, 'r') as f:
                data = json.load(f)
                assert 'export_id' in data
                assert 'data' in data
                assert 'performance' in data['data']
    
    @pytest.mark.skipif(not hasattr(ExportService, '_export_pdf'), reason="PDF export requires reportlab")
    def test_export_pdf(self, export_service):
        """Test PDF export functionality."""
        request = ExportRequest(
            export_type='pdf',
            data_types=['health', 'performance'],
            time_period=14,
            format_options={}
        )
        
        # Mock the required services
        with patch.object(export_service.dashboard_service, 'get_health_status') as mock_health, \
             patch.object(export_service.dashboard_service, '_get_current_metrics') as mock_metrics:
            
            mock_health.return_value = Mock(
                overall_status='healthy',
                components={'database': {'status': 'connected'}},
                recommendations=[],
                last_updated='2024-01-01'
            )
            mock_metrics.return_value = {'response_time': 100}
            
            result = export_service.export_data(request)
            
            assert result.success
            assert result.export_type == 'pdf'
            assert result.file_path is not None
            assert Path(result.file_path).suffix == '.pdf'
    
    def test_get_export_templates(self, export_service):
        """Test export template retrieval."""
        templates = export_service.get_export_templates()
        
        assert len(templates) > 0
        
        for template in templates:
            assert 'id' in template
            assert 'name' in template
            assert 'data_types' in template
            assert 'format' in template
            assert template['format'] in ['csv', 'pdf', 'json']
    
    def test_collect_export_data(self, export_service):
        """Test data collection for export."""
        request = ExportRequest(
            export_type='json',
            data_types=['health', 'performance'],
            time_period=7,
            format_options={}
        )
        
        with patch.object(export_service.dashboard_service, 'get_health_status') as mock_health, \
             patch.object(export_service.dashboard_service, '_get_current_metrics') as mock_metrics:
            
            mock_health.return_value = Mock(overall_status='healthy')
            mock_metrics.return_value = {'response_time': 100}
            
            data = export_service._collect_export_data(request)
            
            assert 'health' in data
            assert 'performance' in data
            assert 'timestamp' in data['health']
            assert 'timestamp' in data['performance']
    
    def test_serialize_for_json(self, export_service):
        """Test JSON serialization."""
        from dataclasses import dataclass
        from datetime import datetime
        
        @dataclass
        class TestData:
            name: str
            value: int
            timestamp: datetime
        
        test_obj = TestData("test", 42, datetime.now())
        
        serialized = export_service._serialize_for_json(test_obj)
        
        assert isinstance(serialized, dict)
        assert serialized['name'] == "test"
        assert serialized['value'] == 42
        assert isinstance(serialized['timestamp'], str)  # Should be ISO format
    
    def test_export_error_handling(self, export_service):
        """Test export error handling."""
        request = ExportRequest(
            export_type='invalid_format',
            data_types=['health'],
            time_period=7,
            format_options={}
        )
        
        result = export_service.export_data(request)
        
        assert not result.success
        assert result.error_message is not None
        assert "Unsupported export type" in result.error_message
```

## SUCCESS CRITERIA

### Functional Requirements
- [ ] **Automated Benchmark Service**: Comprehensive performance testing with 8+ test types
- [ ] **Export Service**: Multi-format export (CSV, PDF, JSON) with professional templates
- [ ] **Performance Analysis**: Automated scoring and optimization recommendations
- [ ] **Report Templates**: 5+ predefined templates for different audiences
- [ ] **Export Panel**: Intuitive interface for report generation and download
- [ ] **Scheduled Reports**: Framework for automated report generation

### Technical Requirements
- [ ] **Benchmark Accuracy**: Reliable performance measurements and trend analysis
- [ ] **Export Quality**: Professional PDF reports with charts and tables
- [ ] **Data Integrity**: Accurate data collection and serialization
- [ ] **Performance**: Efficient export generation for large datasets
- [ ] **Error Handling**: Robust error handling and user feedback

### User Experience Requirements
- [ ] **Template System**: Easy-to-use predefined report templates
- [ ] **Custom Configuration**: Flexible export options for advanced users
- [ ] **Download Management**: Clear download links and file management
- [ ] **Status Feedback**: Real-time progress and completion notifications
- [ ] **Professional Output**: High-quality reports suitable for stakeholders

### Testing Requirements
- [ ] **Unit Test Coverage**: ≥85% coverage for benchmark and export services
- [ ] **Integration Tests**: Complete testing of export workflows
- [ ] **Performance Tests**: Benchmark service accuracy and reliability
- [ ] **Format Tests**: Validation of all export formats (CSV, PDF, JSON)
- [ ] **Template Tests**: Verification of all report templates

## DEVELOPMENT WORKFLOW

### Phase 1: Benchmark Service (Days 1-3)
1. **Create Benchmark Service**
   - Implement 8 benchmark test types
   - Add performance scoring algorithm
   - Build recommendation engine
   - Add data persistence

2. **Testing & Validation**
   - Unit tests for all benchmark functions
   - Performance validation
   - Recommendation accuracy

### Phase 2: Export Service (Days 4-6)
1. **Create Export Service**
   - Multi-format export support
   - Professional PDF generation
   - Template system
   - Data serialization

2. **Report Templates**
   - Executive summary template
   - Technical report template
   - Learning analytics template
   - Performance data export
   - Complete system export

### Phase 3: Integration & UI (Days 7)
1. **Export Panel**
   - Template selection interface
   - Custom export configuration
   - Download management
   - Status feedback

2. **Dashboard Integration**
   - Add export tab to dashboard
   - Integrate with existing services
   - Ensure consistent styling

## VALIDATION STEPS

### Pre-Development Validation
- [ ] Review benchmark requirements and test types
- [ ] Confirm export format specifications
- [ ] Validate report template designs
- [ ] Ensure PDF generation library availability

### Development Validation
- [ ] **Benchmark Validation**: Verify benchmark accuracy against known performance baselines
- [ ] **Export Validation**: Test all export formats with sample data
- [ ] **Template Validation**: Review report templates with stakeholders
- [ ] **Integration Testing**: Ensure seamless integration with existing dashboard

### Post-Development Validation
- [ ] **User Testing**: Healthcare administrators test export functionality
- [ ] **Performance Testing**: Verify export generation performance
- [ ] **Quality Assurance**: Review generated reports for accuracy and presentation
- [ ] **Documentation Review**: Ensure comprehensive documentation for export features

## IMPORTANT NOTES

### Performance Considerations
- **Benchmark Timing**: Ensure benchmarks don't impact system performance
- [ ] **Export Size**: Handle large exports efficiently with streaming or chunking
- [ ] **PDF Generation**: Optimize PDF creation for complex reports
- [ ] **Concurrent Exports**: Handle multiple simultaneous export requests

### Quality Assurance
- [ ] **Report Accuracy**: Validate all data in generated reports
- [ ] **Professional Presentation**: Ensure reports meet professional standards
- [ ] **Template Consistency**: Maintain consistent formatting across templates
- [ ] **Error Recovery**: Provide clear error messages and recovery options

### Security Considerations
- [ ] **Data Privacy**: Ensure exported data doesn't contain sensitive information
- [ ] **File Access**: Secure download links and file cleanup
- [ ] **Export Permissions**: Consider user permissions for different export types
- [ ] **Audit Trail**: Log export activities for security monitoring

### Future Enhancements
- [ ] **Email Delivery**: Add email delivery for scheduled reports
- [ ] **Advanced Charts**: Include more sophisticated visualizations in PDF reports
- [ ] **Custom Templates**: Allow users to create custom report templates
- [ ] **API Integration**: Provide API endpoints for programmatic export access
</rewritten_file> 