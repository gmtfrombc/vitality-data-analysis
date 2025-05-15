from __future__ import annotations

"""Generate condition gap reports.

This utility returns a *DataFrame* listing patients whose clinical measurements
imply a given condition (e.g. BMI ≥ 30 for obesity) **but** who do **not** have
that condition coded in their past-medical-history (PMH) table.

The helper is intentionally kept free of any Panel/UI dependencies so it can be
re-used by CLI scripts, background jobs, and the conversational assistant.

Example
-------
>>> from app.utils.gap_report import get_condition_gap_report
>>> df = get_condition_gap_report("obesity", active_only=True)
>>> print(df.head())
  patient_id   bmi        date
0         12  34.2  2025-05-01
"""

from typing import Dict, Tuple
import logging
import pandas as pd
from textwrap import dedent

from db_query import query_dataframe
from app.utils.condition_mapper import condition_mapper

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Threshold definitions for measurement-inferred conditions
# ---------------------------------------------------------------------------
# The structure maps the *canonical* condition name (see ConditionMapper) to a
# tuple consisting of:
#   1. SQL snippet that selects the *latest* relevant measurement per patient
#      and exposes three columns (patient_id, metric_value, date)
#   2. Name of the column that stores the metric in the final output
#
# The helper will later LEFT-JOIN this CTE against the PMH table to filter out
# patients that already have the diagnosis coded.

ConditionRule = Tuple[str, str]  # (cte_sql, metric_alias)


def _vitals_cte(metric: str, where_clause: str) -> str:
    """Return CTE selecting latest *metric* from vitals with *where_clause*."""
    return f"""
    latest_vitals AS (
        SELECT patient_id,
               {metric} AS metric_value,
               MAX(date) AS date
        FROM vitals
        WHERE {metric} IS NOT NULL
        GROUP BY patient_id
    ),
    candidates AS (
        SELECT lv.patient_id, lv.metric_value, lv.date
        FROM vitals v
        JOIN latest_vitals lv
          ON lv.patient_id = v.patient_id
         AND lv.date = v.date
        WHERE {where_clause}
    )"""


def _simple_lab_cte(test_name: str, where_clause: str) -> str:
    """Return CTE selecting latest lab *test_name* per patient."""
    return f"""
    latest_labs AS (
        SELECT patient_id,
               value AS metric_value,
               MAX(date) AS date
        FROM lab_results
        WHERE test_name = '{test_name}'
        GROUP BY patient_id
    ),
    candidates AS (
        SELECT ll.patient_id, ll.metric_value, ll.date
        FROM lab_results lr
        JOIN latest_labs ll
          ON ll.patient_id = lr.patient_id
         AND ll.date = lr.date
        WHERE lr.test_name = '{test_name}' AND {where_clause}
    )"""


# Build rules dict – extend as new conditions are supported
_RULES: Dict[str, ConditionRule] = {
    # Obesity – BMI ≥ 30
    "obesity": (
        _vitals_cte("bmi", "bmi >= 30"),
        "bmi",
    ),
    # Morbid obesity – BMI ≥ 40
    "morbid_obesity": (
        _vitals_cte("bmi", "bmi >= 40"),
        "bmi",
    ),
    # Prediabetes – A1C 5.7–6.4  (inclusive of lower bound, exclusive upper)
    "prediabetes": (
        _simple_lab_cte("A1C", "metric_value >= 5.7 AND metric_value < 6.5"),
        "a1c",
    ),
    # Type-2 diabetes – A1C ≥ 6.5
    "type_2_diabetes": (
        _simple_lab_cte("A1C", "metric_value >= 6.5"),
        "a1c",
    ),
}

# Allow common synonyms to reuse canonical rule
_RULE_ALIASES = {
    "t2dm": "type_2_diabetes",
    "diabetes": "type_2_diabetes",
}


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------


def get_condition_gap_report(
    condition: str,
    *,
    active_only: bool = False,
    db_path: str | None = None,
) -> pd.DataFrame:
    """Return a DataFrame with patients who meet *condition* criteria but lack PMH diagnosis.

    Parameters
    ----------
    condition : str
        Condition term, e.g. "obesity", "prediabetes".  Synonyms are resolved via
        :class:`ConditionMapper` and `_RULE_ALIASES`.
    active_only : bool, default False
        If *True*, restrict to patients marked as ``active = 1`` in the patients table.
    db_path : str, optional
        Path to SQLite DB.  Defaults to the active path resolved by ``db_query``.

    Returns
    -------
    pandas.DataFrame
        Columns: ``patient_id``, condition-specific metric (e.g. ``bmi``), ``date``.
    """

    # ------------------------------------------------------------------
    # Resolve canonical condition & rule
    # ------------------------------------------------------------------
    canonical = condition_mapper.get_canonical_condition(condition) or condition.lower()
    canonical = _RULE_ALIASES.get(canonical, canonical)

    if canonical not in _RULES:
        raise ValueError(
            f"Gap-report not supported for condition '{condition}'. Supported: {sorted(_RULES)}"
        )

    rule_cte, metric_alias = _RULES[canonical]

    # ------------------------------------------------------------------
    # Build PMH lookup clause for the *canonical* condition
    # ------------------------------------------------------------------
    codes_list_sql = condition_mapper.get_all_codes_as_sql_list(canonical)

    text_term = canonical.replace("_", " ").lower()
    pmh_filter_clauses = [f"LOWER(pmh.condition) LIKE '%{text_term}%'"]
    if codes_list_sql:
        pmh_filter_clauses.append(f"pmh.code IN ({codes_list_sql})")

    pmh_filter_sql = " OR ".join(pmh_filter_clauses)

    # ------------------------------------------------------------------
    # Assemble full SQL
    # ------------------------------------------------------------------
    sql = dedent(
        f"""
        WITH
        {rule_cte},
        pmh_match AS (
            SELECT DISTINCT patient_id
            FROM pmh
            WHERE {pmh_filter_sql}
        )
        SELECT c.patient_id,
               c.metric_value AS {metric_alias},
               c.date
        FROM candidates c
        LEFT JOIN pmh_match p ON p.patient_id = c.patient_id
        {{active_join}}
        WHERE p.patient_id IS NULL
        ORDER BY c.metric_value DESC;
        """
    )

    active_clause = ""
    if active_only:
        active_clause = (
            "JOIN patients ON patients.id = c.patient_id AND patients.active = 1"
        )

    sql = sql.replace("{active_join}", active_clause)

    logger.debug("Executing gap report SQL for %s: %s", canonical, sql)

    df = query_dataframe(sql, db_path=db_path)
    return df


__all__ = ["get_condition_gap_report"]
