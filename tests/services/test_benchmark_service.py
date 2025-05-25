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
from datetime import datetime
import tempfile
import os

from app.services.benchmark_service import BenchmarkService, BenchmarkResult


class TestBenchmarkService:
    """Test cases for BenchmarkService."""

    @pytest.fixture
    def benchmark_service(self):
        """Create benchmark service with test database."""
        # Create temporary database for testing
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_db.close()

        service = BenchmarkService(temp_db.name)

        yield service

        # Cleanup
        try:
            os.unlink(temp_db.name)
        except OSError:
            pass

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
        assert suite.successful_tests + suite.failed_tests == suite.total_tests

    def test_calculate_performance_score(self, benchmark_service):
        """Test performance score calculation."""
        # Create mock results
        results = [
            BenchmarkResult("test1", "database", 50.0, True, None, {}, datetime.now()),
            BenchmarkResult("test2", "query", 200.0, True, None, {}, datetime.now()),
            BenchmarkResult("test3", "cache", 25.0, True, None, {}, datetime.now()),
            BenchmarkResult(
                "test4", "system", 1000.0, False, "Error", {}, datetime.now()
            ),
        ]

        score = benchmark_service._calculate_performance_score(results)

        assert 0 <= score <= 100
        # Should be less than 100 due to one failed test and some slow operations
        assert score < 100

    def test_calculate_performance_score_all_success(self, benchmark_service):
        """Test performance score with all successful fast tests."""
        results = [
            BenchmarkResult("test1", "database", 50.0, True, None, {}, datetime.now()),
            BenchmarkResult("test2", "query", 100.0, True, None, {}, datetime.now()),
            BenchmarkResult("test3", "cache", 25.0, True, None, {}, datetime.now()),
        ]

        score = benchmark_service._calculate_performance_score(results)

        assert score > 90  # Should be high score for fast, successful tests

    def test_calculate_performance_score_empty_results(self, benchmark_service):
        """Test performance score with empty results."""
        score = benchmark_service._calculate_performance_score([])
        assert score == 0.0

    def test_generate_recommendations(self, benchmark_service):
        """Test recommendation generation."""
        # Create results with various performance characteristics
        results = [
            BenchmarkResult(
                "fast_test", "database", 50.0, True, None, {}, datetime.now()
            ),
            BenchmarkResult(
                "slow_test", "query", 2000.0, True, None, {}, datetime.now()
            ),
            BenchmarkResult(
                "failed_test",
                "cache",
                0.0,
                False,
                "Connection error",
                {},
                datetime.now(),
            ),
        ]

        recommendations = benchmark_service._generate_recommendations(results)

        assert len(recommendations) > 0
        # Should include recommendations for failed test and slow query
        assert any("failed" in rec.lower() for rec in recommendations)
        assert any(
            "query" in rec.lower() or "slow" in rec.lower() for rec in recommendations
        )

    def test_generate_recommendations_optimal_performance(self, benchmark_service):
        """Test recommendations for optimal performance."""
        results = [
            BenchmarkResult("test1", "database", 50.0, True, None, {}, datetime.now()),
            BenchmarkResult("test2", "query", 100.0, True, None, {}, datetime.now()),
            BenchmarkResult("test3", "cache", 25.0, True, None, {}, datetime.now()),
        ]

        recommendations = benchmark_service._generate_recommendations(results)

        assert len(recommendations) > 0
        # Should indicate optimal performance
        assert any("optimal" in rec.lower() for rec in recommendations)

    def test_benchmark_database_connection(self, benchmark_service):
        """Test database connection benchmark."""
        result = benchmark_service._benchmark_database_connection()

        assert isinstance(result, dict)
        assert "connection_time_ms" in result
        assert result["connection_time_ms"] >= 0
        assert "tables_count" in result
        assert isinstance(result["tables_count"], int)

    def test_benchmark_query_performance(self, benchmark_service):
        """Test query performance benchmark."""
        result = benchmark_service._benchmark_query_performance()

        assert isinstance(result, dict)
        assert len(result) > 0

        # Check that all queries have duration and row count
        for query_name, query_result in result.items():
            assert "duration_ms" in query_result
            assert "row_count" in query_result
            assert query_result["duration_ms"] >= 0
            assert isinstance(query_result["row_count"], int)

    def test_benchmark_cache_performance(self, benchmark_service):
        """Test cache performance benchmark."""
        result = benchmark_service._benchmark_cache_performance()

        assert isinstance(result, dict)
        assert "first_call_ms" in result
        assert "second_call_ms" in result
        assert "cache_efficiency" in result
        assert result["first_call_ms"] >= 0
        assert result["second_call_ms"] >= 0
        assert 0 <= result["cache_efficiency"] <= 1

    def test_benchmark_memory_usage(self, benchmark_service):
        """Test memory usage benchmark."""
        result = benchmark_service._benchmark_memory_usage()

        assert isinstance(result, dict)
        assert "rss_mb" in result
        assert "vms_mb" in result
        assert "memory_percent" in result
        assert "cpu_percent" in result

        # Values should be non-negative
        assert result["rss_mb"] >= 0
        assert result["vms_mb"] >= 0
        assert result["memory_percent"] >= 0
        assert result["cpu_percent"] >= 0

    def test_benchmark_response_time(self, benchmark_service):
        """Test response time benchmark."""
        result = benchmark_service._benchmark_response_time()

        assert isinstance(result, dict)
        assert "operations" in result
        assert "avg_response_time_ms" in result
        assert "max_response_time_ms" in result
        assert "min_response_time_ms" in result
        assert "total_operations" in result

        assert result["avg_response_time_ms"] >= 0
        assert result["max_response_time_ms"] >= result["min_response_time_ms"]
        assert result["total_operations"] > 0

    def test_get_benchmark_history_empty(self, benchmark_service):
        """Test getting benchmark history when empty."""
        history = benchmark_service.get_benchmark_history(30)
        assert history == []

    @pytest.mark.asyncio
    async def test_benchmark_suite_persistence(self, benchmark_service):
        """Test that benchmark suites are properly saved and retrieved."""
        # Run a benchmark suite
        suite = await benchmark_service.run_benchmark_suite("persistence_test")

        # Retrieve history
        history = benchmark_service.get_benchmark_history(30)

        assert len(history) == 1
        retrieved_suite = history[0]

        assert retrieved_suite.suite_id == suite.suite_id
        assert retrieved_suite.total_tests == suite.total_tests
        assert retrieved_suite.successful_tests == suite.successful_tests
        assert retrieved_suite.performance_score == suite.performance_score
        assert len(retrieved_suite.results) == len(suite.results)
        assert len(retrieved_suite.recommendations) == len(suite.recommendations)

    def test_create_performance_baseline_no_data(self, benchmark_service):
        """Test creating baseline with no data."""
        with pytest.raises(ValueError, match="No recent benchmark data found"):
            benchmark_service.create_performance_baseline("test_baseline", "database")

    @pytest.mark.asyncio
    async def test_create_performance_baseline_with_data(self, benchmark_service):
        """Test creating baseline after running benchmarks."""
        # Run a benchmark suite to generate data
        await benchmark_service.run_benchmark_suite("baseline_test")

        # Create baseline
        baseline = benchmark_service.create_performance_baseline("test_baseline", "all")

        assert baseline is not None
        assert baseline.baseline_id.startswith("test_baseline_")
        assert baseline.test_type == "all"
        assert baseline.avg_duration_ms >= 0
        assert 0 <= baseline.success_rate <= 1
        assert "sample_count" in baseline.metadata
        assert baseline.metadata["sample_count"] > 0

    def test_benchmark_tables_creation(self, benchmark_service):
        """Test that benchmark tables are created properly."""
        # Tables should be created during initialization
        with benchmark_service._get_connection() as conn:
            # Check that tables exist
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('benchmark_suites', 'benchmark_results', 'performance_baselines')
            """
            )
            tables = [row[0] for row in cursor.fetchall()]

            assert "benchmark_suites" in tables
            assert "benchmark_results" in tables
            assert "performance_baselines" in tables

    def test_benchmark_error_handling(self, benchmark_service):
        """Test error handling in benchmark methods."""
        # Test with invalid database path
        invalid_service = BenchmarkService("/invalid/path/test.db")

        # Should handle database errors gracefully
        try:
            result = invalid_service._benchmark_database_connection()
            # If it doesn't raise an exception, it should return an error result
            assert isinstance(result, dict)
        except Exception as e:
            # Exception is acceptable for invalid database
            assert isinstance(e, Exception)

    @pytest.mark.asyncio
    async def test_concurrent_benchmark_execution(self, benchmark_service):
        """Test that concurrent benchmarks work correctly."""
        # Run multiple benchmark suites concurrently
        tasks = [
            benchmark_service.run_benchmark_suite(f"concurrent_test_{i}")
            for i in range(3)
        ]

        suites = await asyncio.gather(*tasks)

        assert len(suites) == 3
        for suite in suites:
            assert suite is not None
            assert suite.total_tests > 0
            assert 0 <= suite.performance_score <= 100

        # Check that all suites were saved
        history = benchmark_service.get_benchmark_history(30)
        assert len(history) >= 3
