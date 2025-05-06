"""Assistant Evaluation Framework for continuous improvement.

Part of *WS-6 Continuous Feedback & Evaluation* work stream.

This module provides tools to analyze assistant performance across multiple dimensions:
1. User satisfaction metrics (from feedback data)
2. Response quality metrics (time, error rate, complexity)
3. Intent classification accuracy
4. Query pattern analysis
5. Visualization effectiveness

The framework integrates with existing feedback and query logging systems
to provide actionable insights for improving the Data Analysis Assistant.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Union, Any
from pathlib import Path

from app.utils.feedback_db import load_feedback
from app.utils.query_logging import fetch_recent
from app.utils.saved_questions_db import DB_FILE

logger = logging.getLogger(__name__)

# Metrics categories
SATISFACTION_METRICS = "satisfaction"
RESPONSE_METRICS = "response"
INTENT_METRICS = "intent"
QUERY_PATTERN_METRICS = "query_patterns"
VISUALIZATION_METRICS = "visualization"

# Table for storing evaluation metrics history
METRICS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS assistant_metrics (
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

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def _get_metrics_conn(db_file: str | None = None) -> sqlite3.Connection:
    """Return connection and ensure assistant_metrics table exists."""
    db_path = db_file or DB_FILE
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    with conn:
        conn.execute(METRICS_TABLE_SQL)
    return conn


def _load_feedback_as_df(days: int = 30, db_file: str | None = None) -> pd.DataFrame:
    """Load feedback data from the database as a DataFrame."""
    feedback_rows = load_feedback(db_file=db_file, limit=1000)
    if not feedback_rows:
        return pd.DataFrame(
            columns=["user_id", "question", "rating", "comment", "created_at"]
        )

    df = pd.DataFrame(feedback_rows)
    # Convert timestamps to datetime
    df["created_at"] = pd.to_datetime(df["created_at"])

    # Filter for specified time period
    cutoff = datetime.now() - timedelta(days=days)
    df = df[df["created_at"] >= cutoff]

    return df


def _load_logs_as_df(days: int = 30, db_file: str | None = None) -> pd.DataFrame:
    """Load assistant logs from the database as a DataFrame."""
    logs = fetch_recent(limit=1000, db_file=db_file)
    if not logs:
        return pd.DataFrame(
            columns=[
                "query",
                "intent_json",
                "generated_code",
                "result_summary",
                "duration_ms",
                "created_at",
            ]
        )

    df = pd.DataFrame(logs)
    # Convert timestamps to datetime
    df["created_at"] = pd.to_datetime(df["created_at"])

    # Filter for specified time period
    cutoff = datetime.now() - timedelta(days=days)
    df = df[df["created_at"] >= cutoff]

    # Parse intent_json into separate columns where possible
    df["intent_type"] = df["intent_json"].apply(lambda x: _extract_intent_type(x))
    df["has_clarification"] = df["intent_json"].apply(lambda x: _check_clarification(x))
    df["metrics_count"] = df["intent_json"].apply(lambda x: _count_metrics(x))
    df["has_visualization"] = df["generated_code"].apply(
        lambda x: "visualization" in str(x).lower() if x else False
    )

    return df


def _extract_intent_type(intent_json: str) -> str:
    """Extract the intent type from the intent JSON."""
    try:
        data = json.loads(intent_json)
        return data.get("intent_type", "unknown")
    except Exception:
        return "unknown"


def _check_clarification(intent_json: str) -> bool:
    """Check if the intent involved clarification."""
    try:
        data = json.loads(intent_json)
        return data.get("needs_clarification", False)
    except Exception:
        return False


def _count_metrics(intent_json: str) -> int:
    """Count the metrics in the intent."""
    try:
        data = json.loads(intent_json)
        metrics = data.get("metrics", [])
        return len(metrics) if isinstance(metrics, list) else 1
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------


def compute_satisfaction_metrics(
    days: int = 30, db_file: str | None = None
) -> Dict[str, Union[float, int]]:
    """Compute user satisfaction metrics from feedback data.

    Parameters
    ----------
    days
        Number of days to include in the analysis
    db_file
        Override database path (used in tests)

    Returns
    -------
    Dict with satisfaction metrics
    """
    df = _load_feedback_as_df(days=days, db_file=db_file)

    if df.empty:
        return {
            "satisfaction_rate": 0,
            "feedback_count": 0,
            "comments_rate": 0,
            "avg_feedback_per_day": 0,
        }

    # Calculate basic metrics
    total_feedback = len(df)
    positive_feedback = len(df[df["rating"] == "up"])
    comments_count = len(df[~df["comment"].isna()])

    # Group by day and count
    df["date"] = df["created_at"].dt.date
    daily_counts = df.groupby("date").size()

    metrics = {
        "satisfaction_rate": (
            positive_feedback / total_feedback if total_feedback > 0 else 0
        ),
        "feedback_count": total_feedback,
        "comments_rate": comments_count / total_feedback if total_feedback > 0 else 0,
        "avg_feedback_per_day": daily_counts.mean() if not daily_counts.empty else 0,
    }

    return metrics


def compute_response_metrics(
    days: int = 30, db_file: str | None = None
) -> Dict[str, Union[float, int]]:
    """Compute response quality metrics from assistant logs.

    Parameters
    ----------
    days
        Number of days to include in the analysis
    db_file
        Override database path (used in tests)

    Returns
    -------
    Dict with response quality metrics
    """
    df = _load_logs_as_df(days=days, db_file=db_file)

    if df.empty:
        return {
            "avg_response_time_ms": 0,
            "query_count": 0,
            "code_size_avg": 0,
            "queries_per_day": 0,
        }

    # Calculate basic metrics
    total_queries = len(df)
    avg_response_time = df["duration_ms"].mean() if "duration_ms" in df.columns else 0

    # Calculate code complexity/size
    df["code_size"] = df["generated_code"].apply(lambda x: len(x) if x else 0)
    avg_code_size = df["code_size"].mean()

    # Group by day and count
    df["date"] = df["created_at"].dt.date
    daily_counts = df.groupby("date").size()

    metrics = {
        "avg_response_time_ms": avg_response_time,
        "query_count": total_queries,
        "code_size_avg": avg_code_size,
        "queries_per_day": daily_counts.mean() if not daily_counts.empty else 0,
    }

    return metrics


def compute_intent_metrics(
    days: int = 30, db_file: str | None = None
) -> Dict[str, Union[float, int, Dict]]:
    """Analyze intent classification patterns and accuracy.

    Parameters
    ----------
    days
        Number of days to include in the analysis
    db_file
        Override database path (used in tests)

    Returns
    -------
    Dict with intent classification metrics
    """
    df = _load_logs_as_df(days=days, db_file=db_file)

    if df.empty:
        return {
            "clarification_rate": 0,
            "intent_distribution": {},
            "multi_metric_rate": 0,
        }

    # Calculate clarification rate
    clarification_count = df["has_clarification"].sum()

    # Calculate intent type distribution
    intent_counts = df["intent_type"].value_counts().to_dict()

    # Calculate multi-metric rate
    multi_metric_count = len(df[df["metrics_count"] > 1])

    metrics = {
        "clarification_rate": clarification_count / len(df),
        "intent_distribution": intent_counts,
        "multi_metric_rate": multi_metric_count / len(df),
    }

    return metrics


def compute_query_pattern_metrics(
    days: int = 30, db_file: str | None = None
) -> Dict[str, Any]:
    """Analyze common query patterns and topics.

    Parameters
    ----------
    days
        Number of days to include in the analysis
    db_file
        Override database path (used in tests)

    Returns
    -------
    Dict with query pattern metrics
    """
    df = _load_logs_as_df(days=days, db_file=db_file)

    if df.empty:
        return {"common_keywords": {}, "query_length_avg": 0, "query_complexity": 0}

    # Calculate query length
    df["query_length"] = df["query"].apply(len)
    avg_query_length = df["query_length"].mean()

    # Simple keyword extraction (in production, use more sophisticated NLP)
    common_keywords = {}
    # Health-related terms to track
    keywords = [
        "weight",
        "bmi",
        "blood pressure",
        "glucose",
        "cholesterol",
        "average",
        "correlation",
        "trend",
        "distribution",
        "gender",
        "age",
        "ethnicity",
    ]

    for keyword in keywords:
        common_keywords[keyword] = df["query"].str.contains(keyword, case=False).sum()

    # Proxy for query complexity - longer queries with multiple metrics
    query_complexity = (df["query_length"] * df["metrics_count"]).mean() / 100

    metrics = {
        "common_keywords": common_keywords,
        "query_length_avg": avg_query_length,
        "query_complexity": query_complexity,
    }

    return metrics


def compute_visualization_metrics(
    days: int = 30, db_file: str | None = None
) -> Dict[str, Union[float, int]]:
    """Analyze visualization effectiveness.

    Parameters
    ----------
    days
        Number of days to include in the analysis
    db_file
        Override database path (used in tests)

    Returns
    -------
    Dict with visualization metrics
    """
    logs_df = _load_logs_as_df(days=days, db_file=db_file)
    feedback_df = _load_feedback_as_df(days=days, db_file=db_file)

    if logs_df.empty:
        return {"visualization_rate": 0, "visualized_satisfaction": 0}

    # Calculate visualization rate
    vis_count = logs_df["has_visualization"].sum()
    vis_rate = vis_count / len(logs_df)

    # If we have feedback data, calculate satisfaction rate for visualized queries
    visualized_satisfaction = 0
    if not feedback_df.empty and not logs_df.empty:
        # Join logs and feedback on query
        merged = pd.merge(
            logs_df, feedback_df, left_on="query", right_on="question", how="inner"
        )
        if not merged.empty:
            vis_feedback = merged[merged["has_visualization"]]
            if len(vis_feedback) > 0:
                visualized_satisfaction = (vis_feedback["rating"] == "up").sum() / len(
                    vis_feedback
                )

    metrics = {
        "visualization_rate": vis_rate,
        "visualized_satisfaction": visualized_satisfaction,
    }

    return metrics


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_all_metrics(
    days: int = 30, db_file: str | None = None
) -> Dict[str, Dict[str, Any]]:
    """Compute all assistant evaluation metrics.

    Parameters
    ----------
    days
        Number of days to include in the analysis
    db_file
        Override database path (used in tests)

    Returns
    -------
    Dict containing all metrics grouped by category
    """
    metrics = {
        SATISFACTION_METRICS: compute_satisfaction_metrics(days, db_file),
        RESPONSE_METRICS: compute_response_metrics(days, db_file),
        INTENT_METRICS: compute_intent_metrics(days, db_file),
        QUERY_PATTERN_METRICS: compute_query_pattern_metrics(days, db_file),
        VISUALIZATION_METRICS: compute_visualization_metrics(days, db_file),
    }

    return metrics


def _convert_numpy_types(obj):
    """Convert NumPy types to Python native types for JSON serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: _convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_numpy_types(item) for item in obj]
    else:
        return obj


def store_metrics(
    metrics: Dict[str, Dict[str, Any]],
    period_start: datetime,
    period_end: datetime,
    db_file: str | None = None,
) -> bool:
    """Store computed metrics in the database.

    Parameters
    ----------
    metrics
        Dict containing all metrics grouped by category
    period_start
        Start of the analysis period
    period_end
        End of the analysis period
    db_file
        Override database path (used in tests)

    Returns
    -------
    bool indicating success
    """
    # Format dates for storage
    start_str = period_start.isoformat()
    end_str = period_end.isoformat()

    # Convert metrics data to serialize NumPy types
    metrics = _convert_numpy_types(metrics)

    try:
        conn = _get_metrics_conn(db_file)
        with conn:
            for metric_type, metrics_dict in metrics.items():
                for metric_name, metric_value in metrics_dict.items():
                    # Convert complex values to JSON
                    if isinstance(metric_value, (dict, list)):
                        details = json.dumps(metric_value)
                        value = None
                    else:
                        details = None
                        value = metric_value

                    # Insert or replace metrics
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO assistant_metrics
                        (metric_type, metric_name, metric_value, metric_details, period_start, period_end)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (metric_type, metric_name, value, details, start_str, end_str),
                    )
        return True
    except Exception as e:
        logger.error(f"Failed to store metrics: {e}")
        return False


def load_metrics_history(
    metric_type: str | None = None, days: int = 90, db_file: str | None = None
) -> pd.DataFrame:
    """Load historical metrics data.

    Parameters
    ----------
    metric_type
        Optional filter for specific metric type
    days
        Number of days of history to retrieve
    db_file
        Override database path (used in tests)

    Returns
    -------
    DataFrame with historical metrics
    """
    conn = _get_metrics_conn(db_file)
    conn.row_factory = sqlite3.Row

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    if metric_type:
        query = """
        SELECT * FROM assistant_metrics 
        WHERE metric_type = ? AND period_end > ? 
        ORDER BY period_end ASC
        """
        rows = conn.execute(query, (metric_type, cutoff)).fetchall()
    else:
        query = """
        SELECT * FROM assistant_metrics 
        WHERE period_end > ? 
        ORDER BY period_end ASC
        """
        rows = conn.execute(query, (cutoff,)).fetchall()

    # Convert to DataFrame
    if not rows:
        return pd.DataFrame(
            columns=[
                "metric_type",
                "metric_name",
                "metric_value",
                "metric_details",
                "period_start",
                "period_end",
            ]
        )

    df = pd.DataFrame([dict(row) for row in rows])

    # Convert date strings to datetime
    if "period_start" in df.columns:
        df["period_start"] = pd.to_datetime(df["period_start"])
    if "period_end" in df.columns:
        df["period_end"] = pd.to_datetime(df["period_end"])

    # Parse JSON details when present
    if "metric_details" in df.columns:
        df["parsed_details"] = df["metric_details"].apply(
            lambda x: json.loads(x) if pd.notna(x) and x else None
        )

    return df


def generate_evaluation_report(
    days: int = 30, db_file: str | None = None, save_metrics: bool = True
) -> Dict[str, Any]:
    """Generate a comprehensive evaluation report.

    Parameters
    ----------
    days
        Number of days to include in the analysis
    db_file
        Override database path (used in tests)
    save_metrics
        Whether to save metrics to the database

    Returns
    -------
    Dict containing the evaluation report
    """
    # Set period for analysis
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Compute all metrics
    metrics = compute_all_metrics(days=days, db_file=db_file)

    # Store metrics if requested
    if save_metrics:
        store_metrics(metrics, start_date, end_date, db_file)

    # Add metadata to report
    report = {
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "days_analyzed": days,
        "metrics": metrics,
        "generated_at": datetime.now().isoformat(),
    }

    return report
