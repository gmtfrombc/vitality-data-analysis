#!/usr/bin/env python3
"""
Calculate Assistant Evaluation Metrics

This script calculates and stores assistant evaluation metrics as part of the
WS-6 Continuous Feedback & Evaluation work stream. It can be run manually or
scheduled as a cron job to periodically update the metrics database.

Usage:
    python calculate_metrics.py [--days=30] [--notify]

Options:
    --days=N    Calculate metrics for the last N days (default: 30)
    --notify    Show desktop notification with summary after calculation

Example cron setup (daily at midnight):
    0 0 * * * cd /path/to/project && python calculate_metrics.py --notify
"""

import sys
import os
import argparse
import logging
import json
from datetime import datetime
import subprocess
import numpy as np
from app.utils.evaluation_framework import generate_evaluation_report

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join("logs", f"metrics_{datetime.now().strftime('%Y-%m-%d')}.log")
        ),
    ],
)
logger = logging.getLogger("metrics_calculator")

# Custom JSON encoder to handle NumPy types


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def show_notification(title, message):
    """Show desktop notification on macOS."""
    try:
        # Use AppleScript for macOS notifications
        apple_script = f"""
        display notification "{message}" with title "{title}"
        """
        subprocess.run(["osascript", "-e", apple_script], check=True)
        logger.info(f"Notification displayed: {title} - {message}")
        return True
    except Exception as e:
        logger.error(f"Failed to show notification: {e}")
        return False


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Calculate assistant evaluation metrics"
    )
    parser.add_argument(
        "--days", type=int, default=30, help="Number of days to analyze (default: 30)"
    )
    parser.add_argument(
        "--notify", action="store_true", help="Show desktop notification with results"
    )
    return parser.parse_args()


def main():
    """Main entry point for the metrics calculation script."""
    # Parse arguments
    args = parse_args()
    days = args.days
    notify = args.notify

    logger.info(f"Starting metrics calculation for the last {days} days")

    try:
        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)

        # Calculate metrics and generate report
        report = generate_evaluation_report(days=days, save_metrics=True)

        # Log summary information
        metrics = report["metrics"]
        satisfaction_rate = (
            metrics["satisfaction"]["satisfaction_rate"] * 100
            if "satisfaction" in metrics
            else 0
        )
        feedback_count = (
            metrics["satisfaction"]["feedback_count"]
            if "satisfaction" in metrics
            else 0
        )
        query_count = metrics["response"]["query_count"] if "response" in metrics else 0

        summary = (
            f"Metrics calculated for {days} days: "
            f"Satisfaction: {satisfaction_rate:.1f}%, "
            f"Feedback: {feedback_count}, "
            f"Queries: {query_count}"
        )

        logger.info(summary)

        # Save report to file
        report_path = os.path.join(
            "logs", f"metrics_report_{datetime.now().strftime('%Y-%m-%d')}.json"
        )
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, cls=NumpyEncoder)

        logger.info(f"Report saved to {report_path}")

        # Show notification if requested
        if notify:
            title = "Assistant Metrics Updated"
            message = f"Satisfaction: {satisfaction_rate:.1f}%, Queries: {query_count}"
            show_notification(title, message)

        return 0

    except Exception as e:
        logger.error(f"Error calculating metrics: {e}", exc_info=True)

        if notify:
            show_notification("Metrics Calculation Failed", str(e))

        return 1


if __name__ == "__main__":
    sys.exit(main())
