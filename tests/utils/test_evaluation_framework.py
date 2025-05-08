"""Unit tests for the Assistant Evaluation Framework.

Part of *WS-6 Continuous Feedback & Evaluation* work stream.
"""

import pytest
import json
from datetime import datetime, timedelta
import sqlite3
import tempfile
import os

from app.utils.evaluation_framework import (
    compute_satisfaction_metrics,
    compute_response_metrics,
    compute_intent_metrics,
    compute_query_pattern_metrics,
    compute_visualization_metrics,
    compute_all_metrics,
    store_metrics,
    load_metrics_history,
    generate_evaluation_report,
    _extract_intent_type,
    _check_clarification,
    _count_metrics,
)


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    fd, path = tempfile.mkstemp()
    conn = sqlite3.connect(path)

    # Create necessary tables
    conn.execute(
        """
    CREATE TABLE assistant_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT DEFAULT 'anon',
        question TEXT NOT NULL,
        rating TEXT CHECK(rating IN ('up','down')) NOT NULL,
        comment TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """
    )

    conn.execute(
        """
    CREATE TABLE assistant_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT NOT NULL,
        intent_json TEXT,
        generated_code TEXT,
        result_summary TEXT,
        duration_ms INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """
    )

    conn.execute(
        """
    CREATE TABLE assistant_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        metric_type TEXT NOT NULL,
        metric_name TEXT NOT NULL,
        metric_value REAL,
        metric_details TEXT,
        period_start TEXT,
        period_end TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(metric_type, metric_name, period_start, period_end)
    );
    """
    )

    # Insert test data
    conn.execute(
        """
    INSERT INTO assistant_feedback (user_id, question, rating, comment, created_at)
    VALUES ('test_user', 'What is the average BMI?', 'up', 'Great answer!', '2025-05-01 12:00:00');
    """
    )

    conn.execute(
        """
    INSERT INTO assistant_feedback (user_id, question, rating, comment, created_at)
    VALUES ('test_user', 'What is the trend in weight loss?', 'down', 'Visualization was confusing', '2025-05-01 12:30:00');
    """
    )

    # Insert test logs
    intent1 = json.dumps(
        {"intent_type": "aggregate", "metrics": ["bmi"], "needs_clarification": False}
    )
    intent2 = json.dumps(
        {"intent_type": "trend", "metrics": ["weight"], "needs_clarification": True}
    )

    conn.execute(
        """
    INSERT INTO assistant_logs (query, intent_json, generated_code, result_summary, duration_ms, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            "What is the average BMI?",
            intent1,
            "import pandas as pd\ndf = db_query.run_query('SELECT AVG(bmi) FROM patients')",
            "The average BMI is 24.5",
            150,
            "2025-05-01 12:00:00",
        ),
    )

    conn.execute(
        """
    INSERT INTO assistant_logs (query, intent_json, generated_code, result_summary, duration_ms, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            "What is the trend in weight loss?",
            intent2,
            "import pandas as pd\nimport hvplot.pandas\ndf = db_query.run_query('SELECT date, AVG(weight) FROM patients GROUP BY date')\nvisualization = df.hvplot(x='date', y='weight')",
            "The weight trend shows a consistent decline",
            250,
            "2025-05-01 12:30:00",
        ),
    )

    conn.commit()
    conn.close()

    yield path

    os.close(fd)
    os.unlink(path)


def test_compute_satisfaction_metrics(temp_db):
    """Test satisfaction metrics computation."""
    metrics = compute_satisfaction_metrics(days=30, db_file=temp_db)

    assert "satisfaction_rate" in metrics
    assert "feedback_count" in metrics
    assert "comments_rate" in metrics

    assert metrics["feedback_count"] == 2
    assert metrics["satisfaction_rate"] == 0.5  # 1 up, 1 down
    assert metrics["comments_rate"] == 1.0  # Both have comments


def test_compute_response_metrics(temp_db):
    """Test response metrics computation."""
    metrics = compute_response_metrics(days=30, db_file=temp_db)

    assert "avg_response_time_ms" in metrics
    assert "query_count" in metrics
    assert "code_size_avg" in metrics

    assert metrics["query_count"] == 2
    assert metrics["avg_response_time_ms"] == 200  # Average of 150 and 250


def test_compute_intent_metrics(temp_db):
    """Test intent metrics computation."""
    metrics = compute_intent_metrics(days=30, db_file=temp_db)

    assert "clarification_rate" in metrics
    assert "intent_distribution" in metrics
    assert "multi_metric_rate" in metrics

    # 1 out of 2 needs clarification
    assert metrics["clarification_rate"] == 0.5
    assert "aggregate" in metrics["intent_distribution"]
    assert "trend" in metrics["intent_distribution"]


def test_compute_query_pattern_metrics(temp_db):
    """Test query pattern metrics computation."""
    metrics = compute_query_pattern_metrics(days=30, db_file=temp_db)

    assert "common_keywords" in metrics
    assert "query_length_avg" in metrics

    assert metrics["common_keywords"]["bmi"] == 1
    assert metrics["common_keywords"]["weight"] == 1


def test_compute_visualization_metrics(temp_db):
    """Test visualization metrics computation."""
    metrics = compute_visualization_metrics(days=30, db_file=temp_db)

    assert "visualization_rate" in metrics
    assert "visualized_satisfaction" in metrics

    # The second query has visualization in code
    assert metrics["visualization_rate"] == 0.5


def test_compute_all_metrics(temp_db):
    """Test all metrics computation together."""
    all_metrics = compute_all_metrics(days=30, db_file=temp_db)

    # Check that all categories are present
    assert "satisfaction" in all_metrics
    assert "response" in all_metrics
    assert "intent" in all_metrics
    assert "query_patterns" in all_metrics
    assert "visualization" in all_metrics


def test_store_and_load_metrics(temp_db):
    """Test storing metrics and loading them back."""
    # Generate test metrics
    test_metrics = {
        "satisfaction": {"satisfaction_rate": 0.75, "feedback_count": 10},
        "response": {"avg_response_time_ms": 180, "query_count": 20},
    }

    # Set test period
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    # Store metrics
    success = store_metrics(test_metrics, start_date, end_date, db_file=temp_db)
    assert success is True

    # Load metrics back
    history_df = load_metrics_history(
        metric_type="satisfaction", days=30, db_file=temp_db
    )

    # Verify data
    assert not history_df.empty
    assert "satisfaction_rate" in history_df["metric_name"].values

    # Verify metric value
    satisfaction_rate = history_df[history_df["metric_name"] == "satisfaction_rate"][
        "metric_value"
    ].iloc[0]
    assert satisfaction_rate == 0.75


def test_generate_evaluation_report(temp_db):
    """Test generating a full evaluation report."""
    report = generate_evaluation_report(days=30, db_file=temp_db, save_metrics=True)

    # Check report structure
    assert "period_start" in report
    assert "period_end" in report
    assert "metrics" in report
    assert "generated_at" in report

    # Check metrics are included
    assert "satisfaction" in report["metrics"]
    assert "response" in report["metrics"]


def test_helper_functions():
    """Test the helper functions for intent parsing."""
    # Test intent type extraction
    intent_json = json.dumps(
        {"intent_type": "correlation", "metrics": ["weight", "bmi"]}
    )
    assert _extract_intent_type(intent_json) == "correlation"

    # Test clarification check
    intent_json = json.dumps({"needs_clarification": True})
    assert _check_clarification(intent_json) is True

    # Test metrics count
    intent_json = json.dumps({"metrics": ["weight", "bmi", "blood_pressure"]})
    assert _count_metrics(intent_json) == 3


def test_empty_db(temp_db):
    """Test handling empty database gracefully."""
    # Clear the database
    conn = sqlite3.connect(temp_db)
    conn.execute("DELETE FROM assistant_feedback")
    conn.execute("DELETE FROM assistant_logs")
    conn.commit()
    conn.close()

    # Test metrics functions with empty data
    satisfaction = compute_satisfaction_metrics(days=30, db_file=temp_db)
    response = compute_response_metrics(days=30, db_file=temp_db)

    # Verify default values for empty data
    assert satisfaction["feedback_count"] == 0
    assert satisfaction["satisfaction_rate"] == 0
    assert response["query_count"] == 0
