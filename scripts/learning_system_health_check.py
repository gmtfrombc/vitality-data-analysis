#!/usr/bin/env python3
"""
Learning System Health Check Script

Comprehensive health monitoring script for the AAA Learning System.
Can be run manually or scheduled for automated monitoring.

Usage:
    python scripts/learning_system_health_check.py [--detailed] [--json] [--alert-threshold=warning]
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.correction_service import CorrectionService
from app.utils.learning_metrics import (
    LearningSystemMonitor,
    create_monitoring_dashboard,
)


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_health_check(detailed=False, json_output=False, alert_threshold="warning"):
    """Run comprehensive health check and return results."""

    try:
        # Initialize monitoring
        monitor = LearningSystemMonitor()

        # Get system health
        health = monitor.get_system_health()

        # Get comprehensive metrics if detailed
        metrics = None
        if detailed:
            metrics = monitor.get_comprehensive_metrics()

        # Create dashboard data
        dashboard = create_monitoring_dashboard()

        # Determine if alert should be triggered
        should_alert = (
            (alert_threshold == "critical" and health.overall_status == "critical")
            or (
                alert_threshold == "warning"
                and health.overall_status in ["warning", "critical"]
            )
            or (alert_threshold == "any" and health.overall_status != "healthy")
        )

        results = {
            "timestamp": datetime.now().isoformat(),
            "health": {
                "status": health.overall_status,
                "database_connected": health.database_connected,
                "pattern_learning_active": health.pattern_learning_active,
                "cache_performance": health.cache_performance,
                "recent_error_rate": health.recent_error_rate,
                "recommendations": health.recommendations,
            },
            "should_alert": should_alert,
            "alert_threshold": alert_threshold,
        }

        if detailed and metrics:
            results["metrics"] = {
                "accuracy": metrics.accuracy_metrics,
                "performance": metrics.performance_metrics,
                "usage": metrics.usage_metrics,
                "patterns": metrics.pattern_metrics,
                "errors": metrics.error_metrics,
            }

        if json_output:
            return results
        else:
            return format_human_readable_report(results, dashboard["report"])

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        error_result = {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "health": {
                "status": "critical",
                "database_connected": False,
                "pattern_learning_active": False,
                "cache_performance": "unknown",
                "recent_error_rate": 1.0,
                "recommendations": [
                    "Health check system failure - immediate attention required"
                ],
            },
            "should_alert": True,
            "alert_threshold": alert_threshold,
        }

        if json_output:
            return error_result
        else:
            return f"CRITICAL ERROR: Health check failed - {e}"


def format_human_readable_report(results, full_report):
    """Format results for human-readable output."""

    health = results["health"]
    status_emoji = {"healthy": "✅", "warning": "⚠️", "critical": "❌"}

    lines = [
        "=" * 60,
        "AAA LEARNING SYSTEM HEALTH CHECK",
        "=" * 60,
        f"Timestamp: {results['timestamp']}",
        f"Overall Status: {status_emoji.get(health['status'], '❓')} {health['status'].upper()}",
        "",
        "COMPONENT STATUS:",
        f"  Database: {'✅' if health['database_connected'] else '❌'} {'Connected' if health['database_connected'] else 'Disconnected'}",
        f"  Pattern Learning: {'✅' if health['pattern_learning_active'] else '❌'} {'Active' if health['pattern_learning_active'] else 'Inactive'}",
        f"  Cache Performance: {health['cache_performance'].title()}",
        f"  Error Rate: {health['recent_error_rate']:.1%}",
        "",
    ]

    if health["recommendations"]:
        lines.extend(
            [
                "RECOMMENDATIONS:",
                *[f"  • {rec}" for rec in health["recommendations"]],
                "",
            ]
        )

    if results.get("metrics"):
        metrics = results["metrics"]
        lines.extend(
            [
                "DETAILED METRICS:",
                f"  Pattern Accuracy: {metrics['accuracy'].get('pattern_accuracy', 0):.1%}",
                f"  Correction Success: {metrics['accuracy'].get('correction_success_rate', 0):.1%}",
                f"  Response Time: {metrics['performance'].get('average_response_time_ms', 0):.1f}ms",
                f"  Active Patterns: {metrics['usage'].get('active_patterns', 0)}",
                f"  Recent Corrections: {metrics['usage'].get('total_corrections', 0)}",
                "",
            ]
        )

    if results["should_alert"]:
        lines.extend(
            [
                "🚨 ALERT TRIGGERED 🚨",
                f"Alert threshold '{results['alert_threshold']}' exceeded",
                "Immediate attention may be required",
                "",
            ]
        )

    lines.extend(
        [
            "=" * 60,
            "For detailed report, run with --detailed flag",
            "For JSON output, run with --json flag",
            "=" * 60,
        ]
    )

    return "\n".join(lines)


def run_performance_benchmark():
    """Run performance benchmarks and return results."""

    try:
        correction_service = CorrectionService()

        # Test pattern lookup performance
        import time

        test_queries = [
            "average BMI active patients",
            "count patients by status",
            "blood pressure trends",
            "medication adherence rates",
            "patient demographics",
        ]

        lookup_times = []
        for query in test_queries:
            start_time = time.time()
            patterns = correction_service.find_similar_patterns(query)
            lookup_time = (time.time() - start_time) * 1000
            lookup_times.append(lookup_time)

        avg_lookup_time = sum(lookup_times) / len(lookup_times)
        max_lookup_time = max(lookup_times)

        # Test cache performance
        start_time = time.time()
        correction_service.cleanup_old_cache_entries(30)  # Test cache cleanup
        cache_cleanup_time = (time.time() - start_time) * 1000

        return {
            "average_lookup_time_ms": avg_lookup_time,
            "max_lookup_time_ms": max_lookup_time,
            "cache_cleanup_time_ms": cache_cleanup_time,
            "benchmark_passed": avg_lookup_time < 100 and max_lookup_time < 200,
        }

    except Exception as e:
        logger.error(f"Performance benchmark failed: {e}")
        return {"error": str(e), "benchmark_passed": False}


def main():
    """Main entry point for the health check script."""

    parser = argparse.ArgumentParser(description="AAA Learning System Health Check")
    parser.add_argument(
        "--detailed", action="store_true", help="Include detailed metrics"
    )
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument(
        "--alert-threshold",
        choices=["healthy", "warning", "critical", "any"],
        default="warning",
        help="Alert threshold level",
    )
    parser.add_argument(
        "--benchmark", action="store_true", help="Run performance benchmarks"
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress non-essential output"
    )

    args = parser.parse_args()

    if not args.quiet:
        logger.info("Starting AAA Learning System health check...")

    try:
        # Run main health check
        results = run_health_check(
            detailed=args.detailed,
            json_output=args.json,
            alert_threshold=args.alert_threshold,
        )

        # Run performance benchmark if requested
        if args.benchmark:
            if not args.quiet:
                logger.info("Running performance benchmarks...")

            benchmark_results = run_performance_benchmark()

            if args.json:
                if isinstance(results, dict):
                    results["benchmark"] = benchmark_results
                else:
                    results = {"health_check": results, "benchmark": benchmark_results}

        # Output results
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(results)

            if args.benchmark:
                benchmark = benchmark_results
                print("\n" + "=" * 60)
                print("PERFORMANCE BENCHMARK RESULTS")
                print("=" * 60)

                if "error" in benchmark:
                    print(f"❌ Benchmark failed: {benchmark['error']}")
                else:
                    status = (
                        "✅ PASSED" if benchmark["benchmark_passed"] else "❌ FAILED"
                    )
                    print(f"Overall: {status}")
                    print(
                        f"Average Lookup Time: {benchmark['average_lookup_time_ms']:.2f}ms"
                    )
                    print(f"Max Lookup Time: {benchmark['max_lookup_time_ms']:.2f}ms")
                    print(
                        f"Cache Cleanup Time: {benchmark['cache_cleanup_time_ms']:.2f}ms"
                    )

        # Set exit code based on health status
        if isinstance(results, dict):
            health_status = results.get("health", {}).get("status", "unknown")
            should_alert = results.get("should_alert", False)
        else:
            # For string results, assume critical if contains error
            health_status = "critical" if "CRITICAL" in str(results) else "unknown"
            should_alert = True

        if health_status == "critical":
            sys.exit(2)  # Critical error
        elif health_status == "warning" or should_alert:
            sys.exit(1)  # Warning
        else:
            sys.exit(0)  # Healthy

    except Exception as e:
        logger.error(f"Health check script failed: {e}")
        if args.json:
            print(
                json.dumps({"error": str(e), "timestamp": datetime.now().isoformat()})
            )
        else:
            print(f"CRITICAL ERROR: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
