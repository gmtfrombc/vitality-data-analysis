from __future__ import annotations

"""Intent parsing and validation for data analysis assistant.

Defines structures and validation for QueryIntent, the core interface between
natural language input and data analysis.
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional, Tuple, Union, Iterable

from pydantic import BaseModel, Field, model_validator

try:
    from pydantic import ValidationError  # noqa
except ImportError:  # pragma: no cover - compatibility with pydantic v1
    from pydantic import ValidationError  # type: ignore

from .condition_mapper import condition_mapper

__all__ = [
    "QueryIntent",
    "Filter",
    "Condition",
    "parse_intent_json",
    "inject_condition_filters_from_query",
]


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper exposed for import convenience
# ---------------------------------------------------------------------------

# Constants for condition handling in queries
CONDITION_FIELD = "condition"
PMH_TABLE = "pmh"

# ---------------------------------------------------------------------------
# Core data models for intent parsing
# ---------------------------------------------------------------------------


class DateRange(BaseModel):
    """A date range with standardized start and end dates.

    Used to filter data within a specific time period.
    """

    start_date: Union[str, date, datetime] = Field(
        ..., description="Start date (inclusive)"
    )
    end_date: Union[str, date, datetime] = Field(
        ..., description="End date (inclusive)"
    )

    @model_validator(mode="after")
    def _validate_dates(self):
        """Ensure dates are valid and start is before end."""
        # Convert string dates to date objects if needed
        if isinstance(self.start_date, str):
            try:
                self.start_date = datetime.fromisoformat(
                    self.start_date.replace("Z", "+00:00")
                )
            except ValueError:
                # Try more forgiving date parsing
                from dateutil import parser

                try:
                    self.start_date = parser.parse(self.start_date)
                except ValueError:
                    raise ValueError(f"Invalid start date format: {self.start_date}")

        if isinstance(self.end_date, str):
            try:
                self.end_date = datetime.fromisoformat(
                    self.end_date.replace("Z", "+00:00")
                )
            except ValueError:
                # Try more forgiving date parsing
                from dateutil import parser

                try:
                    self.end_date = parser.parse(self.end_date)
                except ValueError:
                    raise ValueError(f"Invalid end date format: {self.end_date}")

        # Verify start date is before or equal to end date
        if self.start_date > self.end_date:
            raise ValueError(
                f"Start date {self.start_date} is after end date {self.end_date}"
            )

        return self


class Filter(BaseModel):
    """A filter describing which records to keep.

    Two mutually-exclusive styles are supported:
    1. Equality filter – provide `value` only:  gender == "F"
    2. Range filter   – provide `range` dict with keys `start` & `end`.
       Example: {"field": "test_date", "range": {"start": "2024-01-01", "end": "2024-06-30"}}
    """

    field: str = Field(..., description="Column / attribute to filter on")
    value: Any | None = Field(
        default=None,
        description="Value that `field` must equal (omit if using a range)",
    )
    range: Dict[str, Any] | None = Field(
        default=None,
        description="Start/end range for inclusive filtering; mutually exclusive with `value`",
    )
    date_range: DateRange | None = Field(
        default=None,
        description="Date range filter for time-based queries; mutually exclusive with `value` and `range`",
    )

    @model_validator(mode="after")
    def _one_of_value_or_range(self):  # noqa: D401
        value_count = sum(
            1 for x in [self.value, self.range, self.date_range] if x is not None
        )
        if value_count != 1:
            raise ValueError(
                "Provide exactly one of `value`, `range`, or `date_range` in a Filter"
            )

        if self.range is not None:
            if not (
                isinstance(self.range, dict)
                and set(self.range.keys()) >= {"start", "end"}
            ):
                raise ValueError("`range` must be a dict with 'start' and 'end' keys")
        return self


class Condition(BaseModel):
    """An operator-based condition, e.g. bmi > 30 or date within ±30 days."""

    field: str = Field(..., description="Column / attribute the condition applies to")
    operator: Literal[">", "<", ">=", "<=", "==", "!=", "in", "within", "between"] = (
        Field(..., description="Logical operator to apply")
    )
    value: Any = Field(..., description="Comparison value (or list / tuple for ranges)")


# ---------------------------------------------------------------------------
# Main intent schema
# ---------------------------------------------------------------------------


class QueryIntent(BaseModel):
    """Validated structure describing *what* the user wants to analyse."""

    analysis_type: Literal[
        "count",
        "average",
        "median",
        "distribution",
        "comparison",
        "trend",
        "change",
        "sum",
        "min",
        "max",
        "average_change",
        "rate",
        "variance",
        "std_dev",
        "percent_change",
        "top_n",
        "correlation",
    ]
    target_field: str = Field(..., description="Primary metric or column of interest")
    filters: List[Filter] = Field(default_factory=list)
    conditions: List[Condition] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    # Restored optional v2 fields -------------------------------------------
    additional_fields: List[str] = Field(
        default_factory=list,
        description="Optional extra metric/column names for multi-metric queries.",
    )
    group_by: List[str] = Field(
        default_factory=list,
        description="Optional list of columns to group the aggregate by.",
    )
    # New field for date range filtering ------------------------------------
    time_range: DateRange | None = Field(
        default=None,
        description="Global date range filter that applies to the entire query",
    )

    @model_validator(mode="after")
    def _basic_sanity_checks(self):  # noqa: D401
        """Ensure mandatory pieces for certain analysis types are present."""
        if self.analysis_type == "comparison":
            if len(self.filters) < 1 and not self.group_by:
                raise ValueError(
                    "comparison analysis requires at least one filter or group_by field"
                )
        return self

    # Convenience helpers -------------------------------------------------

    def get_filter(self, field: str) -> Optional[Filter]:
        """Return the first equality filter for *field* if present."""
        return next((f for f in self.filters if f.field == field), None)

    def has_condition(self, field: str, operator: str) -> bool:
        return any(
            c for c in self.conditions if c.field == field and c.operator == operator
        )

    def has_date_filter(self) -> bool:
        """Return True if this intent has any date-related filters or ranges."""
        # Check global time_range
        if self.time_range is not None:
            return True

        # Check date filters
        date_fields = {
            "date",
            "test_date",
            "program_start_date",
            "program_end_date",
            "birth_date",
        }

        # Check for date_range in filters
        for f in self.filters:
            if f.date_range is not None:
                return True
            if f.field in date_fields and (f.value is not None or f.range is not None):
                return True

        # Check date conditions
        for c in self.conditions:
            if c.field in date_fields:
                return True

        return False

    def get_date_range(self) -> Optional[DateRange]:
        """Get the effective date range from this intent, if any."""
        if self.time_range is not None:
            return self.time_range

        # Look for date_range in filters
        for f in self.filters:
            if f.date_range is not None:
                return f.date_range
            if f.field == "date" and f.range is not None:
                # Convert generic range to DateRange
                return DateRange(start_date=f.range["start"], end_date=f.range["end"])

        return None


# ---------------------------------------------------------------------------
# Helper exposed for import convenience
# ---------------------------------------------------------------------------


def parse_intent_json(raw: str) -> QueryIntent:
    """Load JSON returned by the LLM into a validated `QueryIntent` instance."""
    import json

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Intent JSON is not valid: {exc}") from exc

    # ------------------------------------------------------------------
    # Sanitize time_range: remove or nullify when dates are missing/empty
    # ------------------------------------------------------------------
    if isinstance(data, dict) and "time_range" in data:
        tr = data.get("time_range")
        if isinstance(tr, dict):
            # Treat blank strings as None
            start = (tr.get("start_date") or "").strip()
            end = (tr.get("end_date") or "").strip()
            if not start and not end:
                # Nothing specified – drop time_range entirely to avoid validation error
                data["time_range"] = None
            else:
                # Remove keys that are blank so partial ranges still validate via string/None conversion
                if not start:
                    tr.pop("start_date", None)
                if not end:
                    tr.pop("end_date", None)
                # If after removal dict is empty, set to None
                if not tr:
                    data["time_range"] = None

    try:
        # Pydantic v2 migrated – *model_validate* replaces deprecated *parse_obj*.
        # Keep a tiny fallback for projects still on v1.
        validate_fn = getattr(QueryIntent, "model_validate", None)
        if validate_fn is None:  # pragma: no cover – pydantic < 2.x
            validate_fn = QueryIntent.parse_obj  # type: ignore[attr-defined]

        return validate_fn(data)  # type: ignore[arg-type]
    except ValidationError as exc:
        raise ValueError(f"Intent JSON failed validation: {exc}") from exc


# ---------------------------------------------------------------------------
# Field-name normalisation helpers – part of *Intent-Engine Hardening* (WS-2)
# ---------------------------------------------------------------------------


# Canonical column names recognised by downstream SQL & analysis layers.
# Keep this list in sync with ai_helper.get_query_intent() prompt.
_CANONICAL_FIELDS = {
    "patient_id",
    "date",
    "score_type",
    "score_value",
    "gender",
    "age",
    "ethnicity",
    "bmi",
    "weight",
    "sbp",
    "dbp",
    "active",
    "program_completer",
    "condition",  # Added for condition mapping
}

# Common synonyms → canonical column name (lower-case keys)
# Extend this map as new vocabulary emerges.
SYNONYM_MAP: dict[str, str] = {
    # BMI variations
    "body mass index": "bmi",
    "b.m.i": "bmi",
    # Weight variations
    "body weight": "weight",
    "wt": "weight",
    # Blood pressure shorthand
    "bp": "sbp",  # default to systolic if unspecified
    "blood pressure": "sbp",
    "systolic": "sbp",
    "systolic bp": "sbp",
    "diastolic": "dbp",
    "diastolic bp": "dbp",
    # Glycated haemoglobin
    "a1c": "score_value",  # maps to lab_results.score_value when score_type == "A1C"
    "hba1c": "score_value",
    "hemoglobin a1c": "score_value",
    "systolic blood pressure": "sbp",
    "diastolic blood pressure": "dbp",
    "sys bp": "sbp",
    "dia bp": "dbp",
    # Blood sugar / glucose
    "blood sugar": "score_value",
    "sugar": "score_value",
    "glucose": "score_value",
    # Generic score shortcut
    "score": "score_value",
    # Program completion aliases
    "program completer": "program_completer",
    "program completers": "program_completer",
    "program finisher": "program_completer",
    "program finishers": "program_completer",
    "completer": "program_completer",
    "finishers": "program_completer",
    # Condition-related aliases
    "diagnosis": "condition",
    "medical condition": "condition",
    "health condition": "condition",
    "problem": "condition",
    "medical problem": "condition",
    "pmh": "condition",  # Past medical history
    "diagnoses": "condition",
    "conditions": "condition",
    # Obesity-related condition aliases
    "obesity": "condition",
    "morbid obesity": "condition",
    "severe obesity": "condition",
    "overweight": "condition",
}


def _normalise_field_name(name: str) -> str:  # noqa: D401
    """Return canonical field name for *name*, applying the synonym map."""

    if not name:
        return name
    key = name.strip().lower()
    # Direct match or synonym mapping
    canonical = SYNONYM_MAP.get(key, key)
    # In rare cases, LLM may return plural form "patients" – normalise to patient_id
    if canonical in {"patient", "patients"}:
        canonical = "patient_id"
    return canonical


def _get_condition_icd_codes(condition_value: str) -> List[str]:
    """Get ICD-10 codes for a condition value.

    Args:
        condition_value: The condition term or value to look up.

    Returns:
        A list of ICD-10 codes for the condition, or an empty list if not found.
    """
    if not condition_value:
        return []

    return condition_mapper.get_icd_codes(condition_value)


def normalise_intent_fields(intent: "QueryIntent") -> None:  # noqa: D401
    """In-place normalisation of *intent*'s field names according to SYNONYM_MAP."""

    intent.target_field = _normalise_field_name(intent.target_field)
    # Additional fields
    intent.additional_fields = [
        _normalise_field_name(f) for f in intent.additional_fields
    ]
    # Group-by fields
    intent.group_by = [_normalise_field_name(g) for g in intent.group_by]
    # Filters
    for f in intent.filters:
        f.field = _normalise_field_name(f.field)
    # Conditions
    for c in intent.conditions:
        c.field = _normalise_field_name(c.field)

    # No return – mutation in-place keeps references intact.


def get_condition_filter_sql(condition_value: str) -> Tuple[str, bool]:
    """Generate SQL filter for a condition.

    Args:
        condition_value: The condition term to look up.

    Returns:
        A tuple of (SQL clause, success flag). If successful, the SQL clause will
        filter PMH records by the appropriate ICD-10 codes. If unsuccessful, an empty
        string and False will be returned.
    """
    codes = condition_mapper.get_all_codes_as_sql_list(condition_value)
    if codes:
        return f"{PMH_TABLE}.code IN ({codes})", True
    return "", False


def get_canonical_condition(term: str) -> Optional[str]:
    """Get the canonical condition name for a given term.

    Args:
        term: The condition term or synonym to look up.

    Returns:
        The canonical condition name if found, None otherwise.
    """
    return condition_mapper.get_canonical_condition(term)


# ---------------------------------------------------------------------------
# NEW: helper to inject condition filters from raw query text
# ---------------------------------------------------------------------------


def _extract_condition_terms(text: str) -> Iterable[str]:
    """Yield canonical condition names mentioned in *text*.

    Uses the condition_mapper's term index for substring matching.
    """
    lower_q = text.lower()
    for term, canonical in condition_mapper.term_to_canonical.items():
        if term in lower_q:
            yield canonical


def inject_condition_filters_from_query(intent: "QueryIntent", raw_query: str) -> None:
    """Add condition filters to *intent* when raw text mentions known conditions.

    If one or more clinical conditions are detected in *raw_query* and the intent
    does not already include a condition filter, we append them.  For simple
    patient counts we also set ``target_field = 'condition'`` so downstream
    templates route via ICD-10 mapping.
    """
    existing_conditions = {
        f.value.lower() for f in intent.filters if f.field == CONDITION_FIELD
    }
    new_conditions = [
        c for c in _extract_condition_terms(raw_query) if c not in existing_conditions
    ]

    if not new_conditions:
        return

    # Import here to avoid circular dependency at module import time
    from app.utils.query_intent import Filter as _Filter  # type: ignore

    for cond in new_conditions:
        # Use canonical condition as value (underscores -> space for readability)
        intent.filters.append(
            _Filter(field=CONDITION_FIELD, value=cond.replace("_", " "))
        )

    # If this is a simple patient count and target_field is not already a metric
    if intent.analysis_type == "count" and intent.target_field in {
        "patient_id",
        "patient",
        "patients",
        "",
    }:
        intent.target_field = CONDITION_FIELD

    # Ensure field names are normalised for any newly added filters
    normalise_intent_fields(intent)


# ---------------------------------------------------------------------------
# Confidence-scoring helper – assigns 0–1 score to how "certain" the parsed
# intent likely is.  Used by the UI to decide if clarifying questions are needed.
# ---------------------------------------------------------------------------

_AMBIGUOUS_WORDS = {
    "stats",
    "statistics",
    "recent",
    "latest",
    "better",
    "good",
    "bad",
    "okay",
    "improve",
    "improvement",
}


def compute_intent_confidence(
    intent: "QueryIntent", raw_query: str
) -> float:  # noqa: D401
    """Return a heuristic confidence 0–1 for *intent* given *raw_query*.

    Simple rule-based metric:
    • Start at 1.0 and subtract penalties for potential ambiguity.
    • Cap at [0, 1].  Not statistically grounded but useful for gating UI flow.
    """

    score = 1.0

    # 1. Unknown analysis type → heavy penalty
    if intent.analysis_type == "unknown":
        score -= 0.6

    # 2. Target field not canonical → penalty
    if intent.target_field not in _CANONICAL_FIELDS:
        score -= 0.2

    # 3. Generic target fields with no group_by / filters
    if intent.target_field in {"score_value", "value"} and not (
        intent.filters or intent.group_by or intent.additional_fields
    ):
        score -= 0.15

    # 4. Query contains ambiguous language
    q_lower = raw_query.lower()
    if any(word in q_lower for word in _AMBIGUOUS_WORDS):
        score -= 0.15

    # 5. No filters or conditions for analyses that usually need them
    if intent.analysis_type in {"comparison", "change", "trend"} and not (
        intent.filters or intent.conditions or intent.time_range
    ):
        score -= 0.15

    # Normalise between 0 and 1
    return max(0.0, min(1.0, score))


# ---------------------------------------------------------------------------
# Update __all__
# ---------------------------------------------------------------------------
__all__ += [
    "SYNONYM_MAP",
    "normalise_intent_fields",
    "DateRange",
    "compute_intent_confidence",
    "get_condition_filter_sql",
    "get_canonical_condition",
    "CONDITION_FIELD",
    "PMH_TABLE",
    "inject_condition_filters_from_query",
]
