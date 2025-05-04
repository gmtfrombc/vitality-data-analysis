"""Tests for the app.utils.helpers module."""

from app.utils.helpers import format_feedback_for_report


def test_format_feedback_for_report_empty_list():
    """Test formatting an empty feedback list."""
    result = format_feedback_for_report([])
    assert result == "No feedback records found."


def test_format_feedback_for_report_one_day():
    """Test formatting feedback records from a single day."""
    feedback = [
        {
            "id": 1,
            "rating": "up",
            "created_at": "2025-03-01T10:30:00Z",
            "question": "How many active patients are there?",
            "comment": "Great answer!",
        },
        {
            "id": 2,
            "rating": "down",
            "created_at": "2025-03-01T14:20:00Z",
            "question": "What is the average BMI?",
            "comment": "Missing data by gender.",
        },
    ]

    result = format_feedback_for_report(feedback)

    # Basic validation
    assert "# Feedback Triage Report" in result
    assert "## 2025-03-01" in result
    assert "**Summary:** 2 responses" in result
    assert "1 👍 (50%)" in result
    assert "1 👎 (50%)" in result

    # Check sections
    assert "### Needs attention" in result
    assert "### Positive feedback" in result

    # Check content
    assert "**Q:** How many active patients are there?" in result
    assert "**Q:** What is the average BMI?" in result
    assert "**Feedback:** Great answer!" in result
    assert "**Feedback:** Missing data by gender." in result


def test_format_feedback_for_report_multiple_days():
    """Test formatting feedback records from multiple days."""
    feedback = [
        {
            "rating": "up",
            "created_at": "2025-03-01T10:30:00Z",
            "question": "Day 1 Question 1",
            "comment": "Day 1 Comment 1",
        },
        {
            "rating": "down",
            "created_at": "2025-03-02T14:20:00Z",
            "question": "Day 2 Question 1",
            "comment": "Day 2 Comment 1",
        },
    ]

    result = format_feedback_for_report(feedback)

    # Check that both days are included, with most recent first
    day_pos_1 = result.find("## 2025-03-02")
    day_pos_2 = result.find("## 2025-03-01")
    assert day_pos_1 != -1
    assert day_pos_2 != -1
    assert day_pos_1 < day_pos_2  # Most recent day (03-02) should appear first


def test_format_feedback_for_report_missing_fields():
    """Test formatting feedback with missing optional fields."""
    feedback = [
        {
            "rating": "up",
            "created_at": "2025-03-01T10:30:00Z",
            # Missing question
            "comment": "Good",
        },
        {
            "rating": "down",
            "created_at": "2025-03-01T14:20:00Z",
            "question": "Test question",
            # Missing comment
        },
        {
            "rating": "up",
            # Missing created_at
            "question": "Another question",
            "comment": "Nice",
        },
    ]

    result = format_feedback_for_report(feedback)

    # Check fallbacks for missing fields
    assert "*Question not recorded*" in result
    assert "*No comment provided*" in result
    assert "Unknown date" in result


def test_format_feedback_for_report_only_upvotes():
    """Test formatting feedback with only upvotes."""
    feedback = [
        {
            "rating": "up",
            "created_at": "2025-03-01T10:30:00Z",
            "question": "Question 1",
            "comment": "Comment 1",
        },
        {
            "rating": "up",
            "created_at": "2025-03-01T14:20:00Z",
            "question": "Question 2",
            "comment": "Comment 2",
        },
    ]

    result = format_feedback_for_report(feedback)

    # Should have positive feedback section but no needs attention
    assert "### Positive feedback" in result
    assert "### Needs attention" not in result
    assert "2 👍 (100%)" in result
    assert "0 👎 (0%)" in result


def test_format_feedback_for_report_only_downvotes():
    """Test formatting feedback with only downvotes."""
    feedback = [
        {
            "rating": "down",
            "created_at": "2025-03-01T10:30:00Z",
            "question": "Question 1",
            "comment": "Comment 1",
        },
        {
            "rating": "down",
            "created_at": "2025-03-01T14:20:00Z",
            "question": "Question 2",
            "comment": "Comment 2",
        },
    ]

    result = format_feedback_for_report(feedback)

    # Should have needs attention section but no positive feedback
    assert "### Needs attention" in result
    assert "### Positive feedback" not in result
    assert "0 👍 (0%)" in result
    assert "2 👎 (100%)" in result


def test_format_feedback_for_report_upvotes_without_comments():
    """Test that upvotes without comments aren't included in positive feedback."""
    feedback = [
        {
            "rating": "up",
            "created_at": "2025-03-01T10:30:00Z",
            "question": "Question 1",
            # No comment provided
        },
        {
            "rating": "up",
            "created_at": "2025-03-01T14:20:00Z",
            "question": "Question 2",
            "comment": "",  # Empty comment
        },
        {
            "rating": "up",
            "created_at": "2025-03-01T15:20:00Z",
            "question": "Question 3",
            "comment": "Good answer",  # With comment
        },
    ]

    result = format_feedback_for_report(feedback)

    # Should include upvote with comment but not the others
    assert "Question 3" in result
    assert "Good answer" in result
    assert "Question 1" not in result
    assert "Question 2" not in result


def test_format_feedback_for_report_invalid_timestamp():
    """Test handling of invalid timestamp formats."""
    feedback = [
        {
            "rating": "up",
            "created_at": "invalid-timestamp",
            "question": "Question",
            "comment": "Comment",
        }
    ]

    result = format_feedback_for_report(feedback)

    # Should use fallback for invalid timestamp
    assert "## Unknown date" in result
