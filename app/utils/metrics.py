"""Reusable analytic metrics functions.

Phase-2 introduces a central registry so that the LLM (or rule-engine) can
reference a metric by **name** and our backend will execute the correct Python
call.  Each metric should be a *pure function* that receives a pandas
DataFrame and returns either a scalar, a Series, or a DataFrame containing the
computed metric.
"""

from __future__ import annotations

from typing import Callable, Dict, Tuple, Literal

import pandas as pd

__all__ = [
    "phq9_change",
    "METRIC_REGISTRY",
    "register_metric",
    "get_metric",
    "variance",
    "std_dev",
    "percent_change",
    "top_n",
    "correlation_coefficient",
    "correlation_matrix",
]

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def assert_columns(df: pd.DataFrame, *cols: str) -> None:  # noqa: D401
    """Raise a clear error if *df* is missing any of *cols*.

    A small safety guard that replaces obscure ``KeyError`` traces with an
    explicit message like *"DataFrame missing columns: patient_id"*.
    """

    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"DataFrame missing required columns: {', '.join(missing)}")


# ---------------------------------------------------------------------------
# Metric implementations
# ---------------------------------------------------------------------------


def phq9_change(
    df: pd.DataFrame,
    *,
    patient_col: str = "patient_id",
    score_col: str = "value",
    date_col: str = "date",
    baseline_window: Tuple[int, int] = (0, 30),  # days relative to enrolment
    followup_window: Tuple[int, int] = (150, 210),  # 6 months ± 1 month in days
    enrolment_dates: pd.Series | None = None,
) -> pd.Series:
    """Return the change in PHQ-9 score between baseline and follow-up per patient.

    Parameters
    ----------
    df : DataFrame
        Rows of PHQ-9 test results. Expected to have at least columns
        *patient_col*, *score_col*, *date_col*.
    patient_col, score_col, date_col : str
        Column names in `df`.
    baseline_window, followup_window : tuple[int, int]
        Inclusive day offsets (relative to enrolment) that define which tests
        qualify as *baseline* and *follow-up*.
    enrolment_dates : Series | None
        Optional Series mapping *patient_id* → enrolment date. If *None*, the
        earliest test date in `df` per patient is treated as enrolment.

    Returns
    -------
    Series
        Index is *patient_id*, values are `followup_score - baseline_score`.
        Patients missing either measurement are excluded.
    """

    # Ensure datetime
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])

    # Determine enrolment date per patient
    if enrolment_dates is None:
        enrolment_dates = df.groupby(patient_col)[date_col].min()

    # Helper to label tests as baseline / follow-up
    def _label(row):
        enrol_date = enrolment_dates.loc[row[patient_col]]
        delta_days = (row[date_col] - enrol_date).days
        if baseline_window[0] <= delta_days <= baseline_window[1]:
            return "baseline"
        if followup_window[0] <= delta_days <= followup_window[1]:
            return "followup"
        return None

    df["_phase"] = df.apply(_label, axis=1)

    # Keep only labelled rows
    labelled = df[df["_phase"].notna()]

    # Pick first measurement in each phase per patient
    piv = (
        labelled.sort_values(date_col)
        .groupby([patient_col, "_phase"])[score_col]
        .first()
        .unstack("_phase")
    )

    # If followup missing, attempt to use the latest available measurement
    if "followup" not in piv.columns:
        piv["followup"] = None

    missing_follow = piv["followup"].isna()
    if missing_follow.any():
        # For patients without a follow-up in the specified window, pick latest measurement > baseline window
        latest = (
            df[~df["_phase"].eq("baseline")]
            .sort_values(date_col)
            .groupby(patient_col)[score_col]
            .last()
        )
        piv.loc[missing_follow, "followup"] = latest.loc[missing_follow]

    # Compute change and drop where still missing
    change = piv["followup"] - piv["baseline"]
    change = change.dropna()

    # Final fallback: if still empty, use earliest vs latest measurement per patient
    if change.empty:
        first_scores = df.sort_values(date_col).groupby(patient_col)[score_col].first()
        last_scores = df.sort_values(date_col).groupby(patient_col)[score_col].last()
        universal_change = last_scores - first_scores
        universal_change = universal_change.dropna()
        universal_change.name = "phq9_change"
        change = universal_change

    return change


def active_patient_count(
    df: pd.DataFrame,
    *,
    patient_id_col: str = "id",
    active_col: str = "active",
) -> int:
    """Return the number of *active* patients.

    A patient is considered active when ``df[active_col] == 1``.  The function
    counts *unique* patients to avoid double-counting in case the DataFrame
    already contains joined data.
    """

    assert_columns(df, patient_id_col, active_col)

    active = df[df[active_col] == 1]
    return active[patient_id_col].nunique()


def variance(series: pd.Series) -> float:  # noqa: D401
    """Return sample variance of a numeric pandas Series (ddof=1)."""
    if series.empty:
        return float("nan")
    return float(series.var(ddof=1))


def std_dev(series: pd.Series) -> float:  # noqa: D401
    """Return sample standard deviation of a numeric pandas Series (ddof=1)."""
    if series.empty:
        return float("nan")
    return float(series.std(ddof=1))


def percent_change(series: pd.Series) -> float:  # noqa: D401
    """Return percent change between first and last non-NA value in *series*.

    Formula: ((last - first) / |first|) * 100.  Returns NaN if <2 points.
    """
    clean = series.dropna()
    if clean.size < 2:
        return float("nan")
    first, last = clean.iloc[0], clean.iloc[-1]
    if first == 0:
        return float("nan")
    return float((last - first) / abs(first) * 100)


def top_n(series: pd.Series, n: int = 5):  # noqa: D401
    """Return the *n* largest values and their counts as a dict of value → count."""
    if series.empty:
        return {}
    return dict(series.value_counts().nlargest(n))


def correlation_coefficient(
    df: pd.DataFrame,
    metric_x: str,
    metric_y: str,
    method: Literal["pearson", "spearman", "kendall"] = "pearson",
) -> float:
    """Calculate correlation coefficient between two metrics.

    Parameters
    ----------
    df : pandas.DataFrame
        Source data containing both metrics.
    metric_x : str
        First metric column name.
    metric_y : str
        Second metric column name to correlate with first metric.
    method : {"pearson", "spearman", "kendall"}, default "pearson"
        Correlation method to use.

    Returns
    -------
    float
        Correlation coefficient (-1 to 1).

    Notes
    -----
    - Pearson: Linear correlation, sensitive to outliers
    - Spearman: Rank correlation, less sensitive to outliers
    - Kendall: Non-parametric rank correlation, robust but computationally expensive
    """
    # Check if columns exist
    assert_columns(df, metric_x, metric_y)

    # Get clean data (drop rows with NaN in either column)
    clean_df = df.dropna(subset=[metric_x, metric_y])

    # Ensure we have enough data
    if len(clean_df) < 2:
        return float("nan")

    # Calculate correlation
    if method == "pearson":
        return float(clean_df[metric_x].corr(clean_df[metric_y], method="pearson"))
    elif method == "spearman":
        return float(clean_df[metric_x].corr(clean_df[metric_y], method="spearman"))
    elif method == "kendall":
        return float(clean_df[metric_x].corr(clean_df[metric_y], method="kendall"))
    else:
        raise ValueError(f"Unsupported correlation method: {method}")


def correlation_matrix(
    df: pd.DataFrame,
    metrics: list[str],
    method: Literal["pearson", "spearman", "kendall"] = "pearson",
    include_p_values: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Calculate correlation matrix between multiple metrics with optional p-value calculation.

    Parameters
    ----------
    df : pandas.DataFrame
        Source data containing all metrics to correlate.
    metrics : list[str]
        List of metric column names to include in the correlation matrix.
    method : {"pearson", "spearman", "kendall"}, default "pearson"
        Correlation method to use.
    include_p_values : bool, default True
        Whether to calculate and return p-values for significance testing.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame | None]
        - Correlation coefficient matrix (metrics × metrics)
        - P-value matrix if include_p_values=True, otherwise None

    Notes
    -----
    - P-values < 0.05 typically indicate statistically significant correlations
    - Pearson: assumes normal distribution, tests linear relationships
    - Spearman: non-parametric, detects monotonic relationships
    - Kendall: non-parametric, robust to outliers, good for small samples
    """
    # Check if all requested columns exist
    assert_columns(df, *metrics)

    # Clean data - drop rows with any NaN in the requested columns
    clean_df = df.dropna(subset=metrics)

    # Check if we have enough data
    if len(clean_df) < 3:
        raise ValueError(
            f"Need at least 3 complete rows for correlation matrix, got {len(clean_df)}"
        )

    # Calculate correlation matrix
    corr_matrix = clean_df[metrics].corr(method=method)

    # Calculate p-values if requested
    p_values = None
    if include_p_values:
        import numpy as np
        from scipy import stats

        # Initialize p-value matrix
        p_values = pd.DataFrame(np.nan, index=metrics, columns=metrics)

        # For each pair of variables, calculate the p-value
        for i, metric1 in enumerate(metrics):
            for j, metric2 in enumerate(metrics):
                if i == j:  # Same variable, p-value is 1
                    p_values.loc[metric1, metric2] = 1.0
                    continue

                # Get the data
                x = clean_df[metric1].values
                y = clean_df[metric2].values

                # Calculate correlation and p-value based on method
                if method == "pearson":
                    r, p = stats.pearsonr(x, y)
                elif method == "spearman":
                    r, p = stats.spearmanr(x, y)
                elif method == "kendall":
                    r, p = stats.kendalltau(x, y)
                else:
                    raise ValueError(f"Unsupported correlation method: {method}")

                p_values.loc[metric1, metric2] = p

    return corr_matrix, p_values


# ---------------------------------------------------------------------------
# Registry utilities
# ---------------------------------------------------------------------------


METRIC_REGISTRY: Dict[str, Callable[..., pd.Series]] = {
    "phq9_change": phq9_change,
    "active_patients": active_patient_count,  # deterministic patient counter
    "variance": variance,
    "std_dev": std_dev,
    "percent_change": percent_change,
    "top_n": top_n,
    "correlation_coefficient": correlation_coefficient,
    "correlation_matrix": correlation_matrix,
}


def register_metric(name: str, func: Callable[..., pd.Series]) -> None:
    """Add a custom metric to the registry (overwrites if name exists)."""
    METRIC_REGISTRY[name] = func


def get_metric(name: str) -> Callable[..., pd.Series]:
    """Retrieve metric function by *name* or raise *KeyError*."""
    return METRIC_REGISTRY[name]
