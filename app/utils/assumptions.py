# Centralized missing data message for all UI and helpers
"""
POLICY & ASSUMPTIONS REFERENCE

All application-level assumptions, default values, fallback logic, and policy decisions
must be defined in this module. Update this reference as new assumptions are added.

Default Constants:
- CLARIFICATION_CONFIDENCE_THRESHOLD: Minimum confidence for skipping clarification
- NO_DATA_MESSAGE: Message for empty query results
- DEFAULT_TIME_WINDOW_MONTHS: Default time window for time-based queries
- DEFAULT_GENDER: Default gender filter
- DEFAULT_PATIENT_STATUS: Default for patient activity status (active/all)
- DEFAULT_AGGREGATOR: Default metric aggregation (average/min/max)
- DEFAULT_BMI_SOURCE: Metric instance source (e.g., 'most_recent')

Helper Functions:
- resolve_time_window
- resolve_gender_filter
- resolve_patient_status
- resolve_metric_source
- get_default_aggregator
- get_fallback_intent

Pattern: When a new default or fallback is required, add the constant and a helper
function if logic is needed. Document the new assumption both in this reference and
in its docstring.
"""
from app.utils.query_intent import QueryIntent

NO_DATA_MESSAGE = (
    "No data available for the selected criteria."  # Centralized missing data message
)
# app/utils/assumptions.py

"""
Assumptions and Default Policy Helpers

This module centralizes all defaults, fallback logic, and assumption documentation
for data analysis, intent parsing, and user query processing.
"""

# Minimum intent confidence to skip clarification prompt
CLARIFICATION_CONFIDENCE_THRESHOLD = 0.7

# --- Default Constants ---

DEFAULT_TIME_WINDOW_MONTHS = 3
DEFAULT_GENDER = "all"
DEFAULT_PATIENT_STATUS = "active"  # Options: "active", "all"
DEFAULT_AGGREGATOR = "average"  # for multi-value queries
DEFAULT_BMI_SOURCE = "most_recent"

# --- Helper Functions ---


def resolve_time_window(params: dict) -> int:
    """
    Returns the time window (months) to use for queries.
    If not provided, uses DEFAULT_TIME_WINDOW_MONTHS.
    """
    return params.get("window", DEFAULT_TIME_WINDOW_MONTHS)


def resolve_gender_filter(query: str) -> str:
    """
    Determines gender filter based on query content.
    If gender not specified, returns DEFAULT_GENDER.
    """
    # naive check (expand as needed)
    if "female" in query.lower():
        return "female"
    if "male" in query.lower():
        return "male"
    return DEFAULT_GENDER


def resolve_patient_status(query: str) -> str:
    """
    Determines patient activity filter from query.
    Defaults to 'active' unless 'all' or 'inactive' specified.
    """
    q = query.lower()
    if "all patients" in q or "inactive" in q:
        return "all"
    return DEFAULT_PATIENT_STATUS


def resolve_metric_source(query: str) -> str:
    """
    Determines which metric instance to use (e.g., 'most recent' for BMI).
    Defaults to most recent.
    """
    if "earliest" in query.lower():
        return "earliest"
    # Add more logic as needed
    return DEFAULT_BMI_SOURCE


def get_default_aggregator(query: str) -> str:
    """
    Returns aggregator to use for multi-value queries (average/min/max).
    """
    q = query.lower()
    if "minimum" in q or "lowest" in q:
        return "min"
    if "maximum" in q or "highest" in q:
        return "max"
    return DEFAULT_AGGREGATOR


def get_fallback_intent(raw_query: str) -> QueryIntent:
    """
    Returns a safe fallback QueryIntent for completely unparseable or ambiguous queries.
    Fallback intent policy is defined here.
    """
    q = raw_query.lower()
    import re

    match = re.search(r"from ([a-z]+) to ([a-z]+) (\d{4})", q)
    if match:
        month_map = {
            "january": 1,
            "february": 2,
            "march": 3,
            "april": 4,
            "may": 5,
            "june": 6,
            "july": 7,
            "august": 8,
            "september": 9,
            "october": 10,
            "november": 11,
            "december": 12,
        }
        start_month = month_map.get(match.group(1))
        end_month = month_map.get(match.group(2))
        year = int(match.group(3))
        if start_month and end_month:
            from calendar import monthrange

            start_date = f"{year}-{start_month:02d}-01"
            end_day = monthrange(year, end_month)[1]
            end_date = f"{year}-{end_month:02d}-{end_day:02d}"
            return QueryIntent(
                analysis_type="trend",
                target_field="weight",
                filters=[],
                conditions=[],
                parameters={"original_query": raw_query, "is_fallback": True},
                additional_fields=[],
                group_by=[],
                time_range=DateRange(start_date=start_date, end_date=end_date),
            )
    if any(kw in q for kw in ["weight trend", "weight trends", "trend of weight"]):
        return QueryIntent(
            analysis_type="trend",
            target_field="weight",
            filters=[],
            conditions=[],
            parameters={"original_query": raw_query, "is_fallback": True},
            additional_fields=[],
            group_by=[],
            time_range=None,
        )
    if any(kw in q for kw in ["trend", "change", "over time"]):
        return QueryIntent(
            analysis_type="trend",
            target_field="unknown",
            filters=[],
            conditions=[],
            parameters={"original_query": raw_query, "is_fallback": True},
            additional_fields=[],
            group_by=[],
            time_range=None,
        )
    return QueryIntent(
        analysis_type="count",
        target_field="unknown",
        filters=[],
        conditions=[],
        parameters={"original_query": raw_query, "is_fallback": True},
        additional_fields=[],
        group_by=[],
        time_range=None,
    )


# --- Docstring for Transparency ---


"""
All assumptions used in query interpretation, filtering, or analysis generation should
be routed through these helpers or constants. When updating policy, do so here and update
relevant documentation/tests.
"""
"""
ADDING NEW ASSUMPTIONS:

- Define all new application-wide default values or policies in this file.
- Use uppercase for constants; use helpers for logic-based assumptions.
- Reference assumptions.py in any module that uses the constant or helper.
- Update this docstring as needed.
"""


def get_safe_default_value(data_type="scalar"):
    """
    Returns a safe default for the given data type.
    """
    if data_type == "scalar":
        return 0
    if data_type == "string":
        return "N/A"
    if data_type == "list":
        return []
    return None
