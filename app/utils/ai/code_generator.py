"""
Code Generator Module

This module handles all code generation and template rendering functionality.
It translates structured query intents into executable Python code
that performs the requested analysis. It includes functions for:

- Rendering code templates based on intent types
- Handling specialized templates for complex analysis types
- Generating fallback code when intent parsing is uncertain
- Building SQL query clauses from structured filters and conditions
"""

import logging
from typing import Any

from app.ai_helper import AIHelper  # Temporary reliance on original for logic
from app.utils.query_intent import QueryIntent

logger = logging.getLogger(__name__)

__all__ = ["generate_analysis_code"]


def generate_analysis_code(intent: Any, data_schema: dict | None = None) -> str:
    """Delegate to the original *AIHelper* implementation for now.

    This function is a thin wrapper so callers outside of ``ai_helper.py`` can
    begin importing template-rendering functionality from
    :pymod:`app.utils.ai.code_generator`.  In subsequent refactor slices we will
    inline the deterministic generation helpers to fully decouple from the old
    monolith.
    """

    logger.info("[code_generator] Generating analysis code via temporary bridge")

    helper = AIHelper()
    schema = (
        data_schema or helper.get_data_schema()
        if hasattr(helper, "get_data_schema")
        else {}
    )
    return helper.generate_analysis_code(intent, schema)


# --------------------
# Template helpers
# --------------------


def _build_filters_clause(intent_obj: QueryIntent) -> str:
    """Build SQL WHERE clause from intent filters and conditions.

    Ported from *ai_helper.py* so the template engine can gradually migrate out
    of the monolithic helper.
    """
    where_clauses: list[str] = []

    # Map fields to specific tables to ensure correct column references
    table_fields = {
        "bmi": "vitals",
        "weight": "vitals",
        "height": "vitals",
        "sbp": "vitals",
        "dbp": "vitals",
        "gender": "patients",
        "ethnicity": "patients",
        "active": "patients",
        "age": "patients",
        "score_type": "scores",
        "score_value": "scores",
    }

    # Aliases for common synonyms
    aliases = {
        "test_date": "date",
        "score": "score_value",
        "scorevalue": "score_value",
        "phq9_score": "score_value",
        "phq_score": "score_value",
        "sex": "gender",
        "patient": "patient_id",
        "assessment_type": "assessment_type",
        "score_type": "score_type",
        "activity_status": "active",
        "status": "active",
        "date": "program_start_date",
    }

    def _quote(val):
        return f"'{val}'" if isinstance(val, str) else str(val)

    # Global time_range filter
    if intent_obj.time_range is not None:
        date_column = "date"
        start_date = intent_obj.time_range.start_date
        end_date = intent_obj.time_range.end_date
        if hasattr(start_date, "strftime"):
            start_date = start_date.strftime("%Y-%m-%d")
        if hasattr(end_date, "strftime"):
            end_date = end_date.strftime("%Y-%m-%d")
        where_clauses.append(
            f"{date_column} BETWEEN {_quote(start_date)} AND {_quote(end_date)}"
        )

    # Equality/range filters
    for f in intent_obj.filters:
        field_name = f.field.lower()
        canonical = aliases.get(field_name, field_name)
        tbl_prefix = f"{table_fields[canonical]}." if canonical in table_fields else ""
        canonical_with_prefix = f"{tbl_prefix}{canonical}"

        if f.value is not None:
            val = f.value
            if canonical == "active" and isinstance(val, str):
                val = (
                    1
                    if val.lower() == "active"
                    else 0 if val.lower() == "inactive" else val
                )
            where_clauses.append(f"{canonical_with_prefix} = {_quote(val)}")
        elif f.range is not None:
            start = f.range.get("start")
            end = f.range.get("end")
            if start is not None and end is not None:
                where_clauses.append(
                    f"{canonical_with_prefix} BETWEEN {_quote(start)} AND {_quote(end)}"
                )
        elif f.date_range is not None:
            date_col = (
                canonical_with_prefix
                if canonical in {"date", "program_start_date"}
                else f"{tbl_prefix}date"
            )
            start_date = f.date_range.start_date
            end_date = f.date_range.end_date
            if hasattr(start_date, "strftime"):
                start_date = start_date.strftime("%Y-%m-%d")
            if hasattr(end_date, "strftime"):
                end_date = end_date.strftime("%Y-%m-%d")
            where_clauses.append(
                f"{date_col} BETWEEN {_quote(start_date)} AND {_quote(end_date)}"
            )

    # Operator-based conditions
    for c in intent_obj.conditions:
        field_name = c.field.lower()
        canonical = aliases.get(field_name, field_name)
        tbl_prefix = f"{table_fields[canonical]}." if canonical in table_fields else ""
        canonical_with_prefix = f"{tbl_prefix}{canonical}"
        op = c.operator
        if (
            op.lower() == "between"
            and isinstance(c.value, (list, tuple))
            and len(c.value) == 2
        ):
            where_clauses.append(
                f"{canonical_with_prefix} BETWEEN {_quote(c.value[0])} AND {_quote(c.value[1])}"
            )
        elif op.lower() == "in" and isinstance(c.value, (list, tuple)):
            vals = ", ".join(_quote(v) for v in c.value)
            where_clauses.append(f"{canonical_with_prefix} IN ({vals})")
        else:
            where_clauses.append(f"{canonical_with_prefix} {op} {_quote(c.value)}")

    return "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
