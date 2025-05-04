from __future__ import annotations

"""Pydantic models representing the structured intent extracted from a user's natural-language analytics question.

Phase-1 of the assistant roadmap introduces a rigid schema so that the LLM must
return machine-readable JSON.  Down-stream steps—code generation, execution,
visualisation—rely exclusively on this validated structure.
"""

from typing import Any, Dict, List, Literal, Optional, Union
from datetime import date, datetime
from pydantic import BaseModel, Field, ValidationError, model_validator

# ---------------------------------------------------------------------------
# Primitive building-blocks
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
        if self.analysis_type == "comparison" and len(self.filters) < 1:
            raise ValueError(
                "comparison analysis requires at least one filter criterion"
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

    try:
        # Pydantic v2 migrated – *model_validate* replaces deprecated *parse_obj*.
        # Keep a tiny fallback for projects still on v1.
        validate_fn = getattr(QueryIntent, "model_validate", None)
        if validate_fn is None:  # pragma: no cover – pydantic < 2.x
            validate_fn = QueryIntent.parse_obj  # type: ignore[attr-defined]

        return validate_fn(data)  # type: ignore[arg-type]
    except ValidationError as exc:
        raise ValueError(f"Intent JSON failed validation: {exc}") from exc
