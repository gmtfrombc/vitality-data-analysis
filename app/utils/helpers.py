"""General utility functions for the app."""

from typing import Dict, List
import datetime


def format_feedback_for_report(feedback_records: List[Dict]) -> str:
    """Format feedback records into a Markdown report.

    Parameters
    ----------
    feedback_records
        List of feedback records from load_feedback()

    Returns
    -------
    str
        Markdown-formatted report
    """
    if not feedback_records:
        return "No feedback records found."

    # Group by day (most recent first)
    days = {}
    for record in feedback_records:
        # Extract date part from timestamp
        created = record.get("created_at", "")
        if not created:
            day_key = "Unknown date"
        else:
            try:
                dt = datetime.datetime.fromisoformat(created.replace("Z", "+00:00"))
                day_key = dt.strftime("%Y-%m-%d")
            except (ValueError, AttributeError):
                day_key = "Unknown date"

        if day_key not in days:
            days[day_key] = []
        days[day_key].append(record)

    # Build report
    lines = ["# Feedback Triage Report", ""]

    for day, records in sorted(days.items(), reverse=True):
        lines.append(f"## {day}")
        lines.append("")

        # Count sentiments
        upvotes = sum(1 for r in records if r.get("rating") == "up")
        downvotes = sum(1 for r in records if r.get("rating") == "down")

        lines.append(
            f"**Summary:** {len(records)} responses — "
            f"{upvotes} 👍 ({upvotes/len(records)*100:.0f}%), "
            f"{downvotes} 👎 ({downvotes/len(records)*100:.0f}%)"
        )
        lines.append("")

        # List comments (focusing on downvotes first as they need attention)
        if downvotes > 0:
            lines.append("### Needs attention")
            lines.append("")

            for record in records:
                if record.get("rating") == "down":
                    comment = (
                        record.get("comment", "").strip() or "*No comment provided*"
                    )
                    question = (
                        record.get("question", "").strip() or "*Question not recorded*"
                    )
                    lines.append(f"- 👎 **Q:** {question}")
                    lines.append(f"  - **Feedback:** {comment}")
                    lines.append("")

        # Add positive feedback if there's any
        if upvotes > 0:
            lines.append("### Positive feedback")
            lines.append("")

            for record in records:
                if record.get("rating") == "up" and record.get("comment"):
                    comment = record.get("comment", "").strip()
                    if not comment:
                        continue  # Skip upvotes without comments

                    question = (
                        record.get("question", "").strip() or "*Question not recorded*"
                    )
                    lines.append(f"- 👍 **Q:** {question}")
                    lines.append(f"  - **Feedback:** {comment}")
                    lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)
