#!/usr/bin/env python3
"""Daily runner for the Synthetic Golden-Dataset Self-Test Loop.

This script runs the self-test and sends a notification with the results.
It's designed to be run as a daily scheduled task (e.g., via cron or systemd timer).

Usage:
    python run_daily_self_test.py [--notify] [--output-dir DIR]

Options:
    --notify       Send email notification with test results
    --output-dir   Directory to store test results (default: test_results)
"""

from tests.golden.synthetic_self_test import run_self_test
import os
import sys
import argparse
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import our self-test module

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Log to stdout/stderr
        logging.FileHandler(project_root / "logs" / "daily_self_test.log"),
    ],
)
logger = logging.getLogger("daily_self_test")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run daily synthetic self-test")
    parser.add_argument("--notify", action="store_true", help="Send email notification")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="test_results",
        help="Directory to store test results",
    )
    parser.add_argument(
        "--recipients", type=str, help="Comma-separated list of email recipients"
    )
    return parser.parse_args()


def send_notification(report, recipients):
    """Send email notification with test results."""
    if not recipients:
        logger.warning("No recipients specified for notification")
        return

    # Load SMTP settings from environment or .env
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("NOTIFICATION_SENDER", "no-reply@example.com")

    if not all([smtp_server, smtp_user, smtp_password]):
        logger.error("Missing SMTP settings, cannot send notification")
        return

    # Parse recipient list
    recipient_list = [r.strip() for r in recipients.split(",") if r.strip()]

    # Build the email
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ", ".join(recipient_list)

    # Determine subject based on results
    success_rate = report["passed_tests"] / report["total_tests"]
    status = (
        "SUCCESS"
        if success_rate == 1.0
        else "WARNING" if success_rate >= 0.8 else "FAILURE"
    )
    msg["Subject"] = (
        f"[Data Assistant Self-Test] {status}: {report['passed_tests']}/{report['total_tests']} tests passed"
    )

    # Create the email body
    body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .success {{ color: green; }}
            .warning {{ color: orange; }}
            .failure {{ color: red; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
        </style>
    </head>
    <body>
        <h2>Data Analysis Assistant Self-Test Results</h2>
        <p>Timestamp: {report['timestamp']}</p>
        <p class="{status.lower()}">
            <strong>Result: {report['passed_tests']}/{report['total_tests']} tests passed ({success_rate:.1%})</strong>
        </p>
        
        <h3>Test Details</h3>
        <table>
            <tr>
                <th>Name</th>
                <th>Query</th>
                <th>Status</th>
                <th>Error</th>
            </tr>
    """

    # Add rows for each test
    for test in report["tests"]:
        status_class = "success" if test["passed"] else "failure"
        status_text = "✓ Passed" if test["passed"] else "✗ Failed"
        error = test.get("error", "") if not test["passed"] else ""

        body += f"""
            <tr>
                <td>{test['name']}</td>
                <td>{test['query']}</td>
                <td class="{status_class}">{status_text}</td>
                <td>{error}</td>
            </tr>
        """

    body += """
        </table>
        
        <p>
            <small>This is an automated notification from the Data Analysis Assistant Self-Test system.
            Please do not reply to this email.</small>
        </p>
    </body>
    </html>
    """

    # Attach the body and send the email
    msg.attach(MIMEText(body, "html"))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        logger.info(f"Notification sent to {recipients}")
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")


def main():
    """Run the daily self-test."""
    args = parse_args()

    # Set up the output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    # Run the self-test
    logger.info("Starting daily self-test run")
    try:
        passed, total, report = run_self_test(output_dir)

        # Write a summary to stdout
        success_rate = passed / total
        status = (
            "SUCCESS"
            if success_rate == 1.0
            else "WARNING" if success_rate >= 0.8 else "FAILURE"
        )

        print(f"\n{'='*60}")
        print(f"DAILY SELF-TEST: {status}")
        print(f"{passed}/{total} tests passed ({success_rate:.1%})")
        print(f"{'='*60}")
        print(f"Detailed report saved to: {output_dir}/{report['timestamp']}")
        print(f"{'='*60}\n")

        # Send notification if requested
        if args.notify:
            send_notification(report, args.recipients)

        # Exit with appropriate status code
        sys.exit(0 if passed == total else 1)

    except Exception as e:
        logger.exception(f"Error running self-test: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
