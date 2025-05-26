"""Tests for feedback analytics module."""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.utils.feedback_analytics import FeedbackAnalytics


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def analytics(temp_db):
    """Create FeedbackAnalytics instance with temporary database."""
    return FeedbackAnalytics(db_path=temp_db)


def test_feedback_analytics_initialization(analytics):
    """Test that FeedbackAnalytics initializes correctly."""
    assert analytics is not None
    assert analytics.db_path is not None

    # Check that table was created
    with analytics._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='feedback_requests'
        """
        )
        assert cursor.fetchone() is not None


def test_track_feedback_request(analytics):
    """Test tracking feedback requests."""
    # Track a feedback request
    analytics.track_feedback_request(
        query="What is the average BMI?",
        priority="high",
        requested=True,
        user_id="test_user",
        confidence_score=0.8,
        novelty_score=0.6,
        learning_value_score=0.7,
        fatigue_detected=False,
    )

    # Verify it was stored
    with analytics._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM feedback_requests")
        result = cursor.fetchone()

        assert result is not None
        assert result[1] == "What is the average BMI?"  # query_text
        assert result[2] == "high"  # priority_level
        assert result[3] == 1  # requested (True)
        assert result[4] == "test_user"  # user_id
        assert result[5] == 0.8  # confidence_score
        assert result[6] == 0.6  # novelty_score
        assert result[7] == 0.7  # learning_value_score
        assert result[8] == 0  # fatigue_detected (False)


def test_track_feedback_request_minimal(analytics):
    """Test tracking feedback request with minimal data."""
    analytics.track_feedback_request(
        query="Simple query", priority="medium", requested=False
    )

    with analytics._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM feedback_requests")
        result = cursor.fetchone()

        assert result is not None
        assert result[1] == "Simple query"
        assert result[2] == "medium"
        assert result[3] == 0  # requested (False)
        assert result[4] == "anon"  # default user_id


def test_get_engagement_metrics_empty(analytics):
    """Test engagement metrics with no data."""
    metrics = analytics.get_engagement_metrics(days=7)

    expected = {
        "total_requests": 0,
        "feedback_requested": 0,
        "actual_responses": 0,
        "unique_users": 0,
        "request_rate": 0.0,
        "response_rate": 0.0,
        "avg_requests_per_user": 0.0,
    }

    assert metrics == expected


def test_get_engagement_metrics_with_data(analytics):
    """Test engagement metrics with sample data."""
    # Add sample data
    test_data = [
        ("query1", "high", True, "user1"),
        ("query2", "medium", True, "user1"),
        ("query3", "low", False, "user2"),
        ("query4", "high", True, "user2"),
    ]

    for query, priority, requested, user_id in test_data:
        analytics.track_feedback_request(query, priority, requested, user_id)

    metrics = analytics.get_engagement_metrics(days=7)

    # Since assistant_feedback table doesn't exist, actual_responses will be 0
    assert metrics["total_requests"] == 4
    assert metrics["feedback_requested"] == 3
    assert metrics["actual_responses"] == 0  # No assistant_feedback table in test
    assert metrics["unique_users"] == 2
    assert metrics["request_rate"] == 0.75  # 3/4
    assert metrics["response_rate"] == 0.0  # 0/3 (no responses)
    assert metrics["avg_requests_per_user"] == 2.0  # 4/2


def test_get_effectiveness_summary(analytics):
    """Test effectiveness summary calculation."""
    # Add sample data with different priorities
    test_data = [
        ("query1", "high", True, False, 0.3, 0.8, 0.7),
        ("query2", "medium", True, False, 0.7, 0.5, 0.6),
        ("query3", "low", False, True, 0.9, 0.2, 0.3),
        ("query4", "high", True, False, 0.4, 0.9, 0.8),
    ]

    with analytics._get_connection() as conn:
        cursor = conn.cursor()
        for query, priority, requested, fatigue, conf, nov, learn in test_data:
            cursor.execute(
                """
                INSERT INTO feedback_requests 
                (query_text, priority_level, requested, fatigue_detected,
                 confidence_score, novelty_score, learning_value_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (query, priority, requested, fatigue, conf, nov, learn),
            )
        conn.commit()

    summary = analytics.get_effectiveness_summary()

    assert "priority_distribution" in summary
    assert "fatigue_rate" in summary
    assert "total_requests" in summary
    assert "priority_scores" in summary

    # Check priority distribution
    assert summary["priority_distribution"]["high"] == 2
    assert summary["priority_distribution"]["medium"] == 1
    assert summary["priority_distribution"]["low"] == 1

    # Check fatigue rate (1 out of 4)
    assert summary["fatigue_rate"] == 0.25

    # Check total requests
    assert summary["total_requests"] == 4


def test_get_priority_distribution(analytics):
    """Test priority distribution calculation."""
    # Add data from different time periods
    now = datetime.now()
    old_date = now - timedelta(days=10)
    recent_date = now - timedelta(days=3)

    with analytics._get_connection() as conn:
        cursor = conn.cursor()

        # Old data (should not be included in 7-day window)
        cursor.execute(
            """
            INSERT INTO feedback_requests 
            (query_text, priority_level, requested, created_at)
            VALUES (?, ?, ?, ?)
        """,
            ("old_query", "high", True, old_date.isoformat()),
        )

        # Recent data (should be included)
        cursor.execute(
            """
            INSERT INTO feedback_requests 
            (query_text, priority_level, requested, created_at)
            VALUES (?, ?, ?, ?)
        """,
            ("recent_query1", "high", True, recent_date.isoformat()),
        )

        cursor.execute(
            """
            INSERT INTO feedback_requests 
            (query_text, priority_level, requested, created_at)
            VALUES (?, ?, ?, ?)
        """,
            ("recent_query2", "medium", False, recent_date.isoformat()),
        )

        conn.commit()

    distribution = analytics.get_priority_distribution(days=7)

    # Should only include recent data
    assert distribution.get("high", 0) == 1
    assert distribution.get("medium", 0) == 1
    assert distribution.get("low", 0) == 0


def test_get_user_behavior_summary(analytics):
    """Test user behavior summary calculation."""
    user_id = "test_user"

    # Add sample feedback requests
    test_requests = [
        ("query1", "high", True, False),
        ("query2", "medium", True, True),  # fatigue detected
        ("query3", "low", False, False),
    ]

    with analytics._get_connection() as conn:
        cursor = conn.cursor()
        for query, priority, requested, fatigue in test_requests:
            cursor.execute(
                """
                INSERT INTO feedback_requests 
                (query_text, priority_level, requested, user_id, fatigue_detected)
                VALUES (?, ?, ?, ?, ?)
            """,
                (query, priority, requested, user_id, fatigue),
            )
        conn.commit()

    # Mock assistant_feedback table
    with patch.object(analytics, "_get_connection") as mock_conn:
        mock_cursor = MagicMock()
        mock_conn.return_value.__enter__.return_value.cursor.return_value = mock_cursor

        # First call: feedback_requests query
        # Second call: assistant_feedback query
        mock_cursor.fetchone.side_effect = [
            (3, 2, 1),  # total_requests, feedback_requested, fatigue_instances
            (2, 1),  # total_feedback, positive_feedback
        ]

        summary = analytics.get_user_behavior_summary(user_id)

        assert summary["total_requests"] == 3
        assert summary["feedback_requested"] == 2
        assert summary["total_feedback"] == 2
        assert summary["positive_feedback"] == 1
        assert summary["fatigue_instances"] == 1
        assert summary["request_rate"] == 2 / 3
        assert summary["response_rate"] == 1.0  # 2/2
        assert summary["positive_rate"] == 0.5  # 1/2
        assert summary["fatigue_rate"] == 1 / 3  # 1/3


def test_error_handling(analytics):
    """Test error handling in analytics methods."""
    # Test with corrupted database connection
    with patch.object(analytics, "_get_connection") as mock_conn:
        mock_conn.side_effect = Exception("Database error")

        # All methods should handle errors gracefully
        assert analytics.get_engagement_metrics() == {}
        assert analytics.get_effectiveness_summary() == {}
        assert analytics.get_priority_distribution() == {}
        assert analytics.get_user_behavior_summary() == {}

        # track_feedback_request should not raise exception
        analytics.track_feedback_request("test", "medium", True)


def test_long_query_truncation(analytics):
    """Test that long queries are truncated properly."""
    long_query = "x" * 1000  # 1000 character query

    analytics.track_feedback_request(
        query=long_query, priority="medium", requested=True
    )

    with analytics._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT query_text FROM feedback_requests")
        result = cursor.fetchone()

        # Should be truncated to 500 characters
        assert len(result[0]) == 500
        assert result[0] == "x" * 500


@pytest.mark.parametrize(
    "priority,expected_count", [("high", 2), ("medium", 1), ("low", 1), ("skip", 0)]
)
def test_priority_distribution_parametrized(analytics, priority, expected_count):
    """Test priority distribution with different priority levels."""
    # Add test data
    test_data = [
        ("query1", "high"),
        ("query2", "high"),
        ("query3", "medium"),
        ("query4", "low"),
    ]

    for query, prio in test_data:
        analytics.track_feedback_request(query, prio, True)

    distribution = analytics.get_priority_distribution()
    assert distribution.get(priority, 0) == expected_count
