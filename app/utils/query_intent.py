from __future__ import annotations

"""Pydantic models representing the structured intent extracted from a user's natural-language analytics question.

Phase-1 of the assistant roadmap introduces a rigid schema so that the LLM must
return machine-readable JSON.  Down-stream steps—code generation, execution,
visualisation—rely exclusively on this validated structure.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, ValidationError, model_validator

# ---------------------------------------------------------------------------
# Primitive building-blocks
# ---------------------------------------------------------------------------


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

    @model_validator(mode="after")
    def _one_of_value_or_range(self):  # noqa: D401
        if (self.value is None and self.range is None) or (
            self.value is not None and self.range is not None
        ):
            raise ValueError(
                "Provide exactly one of `value` or `range` in a Filter")
        if self.range is not None:
            if not (
                isinstance(self.range, dict)
                and set(self.range.keys()) >= {"start", "end"}
            ):
                raise ValueError(
                    "`range` must be a dict with 'start' and 'end' keys")
        return self


class Condition(BaseModel):
    """An operator-based condition, e.g. bmi > 30 or date within ±30 days."""

    field: str = Field(...,
                       description="Column / attribute the condition applies to")
    operator: Literal[">", "<", ">=", "<=", "==", "!=", "in", "within", "between"] = Field(
        ..., description="Logical operator to apply"
    )
    value: Any = Field(...,
                       description="Comparison value (or list / tuple for ranges)")


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
    ]
    target_field: str = Field(...,
                              description="Primary metric or column of interest")
    filters: List[Filter] = Field(default_factory=list)
    conditions: List[Condition] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _basic_sanity_checks(self):  # noqa: D401
        """Ensure mandatory pieces for certain analysis types are present."""
        if self.analysis_type == "comparison" and len(self.filters) < 1:
            raise ValueError(
                "comparison analysis requires at least one filter criterion")
        return self

    # Convenience helpers -------------------------------------------------

    def get_filter(self, field: str) -> Optional[Filter]:
        """Return the first equality filter for *field* if present."""
        return next((f for f in self.filters if f.field == field), None)

    def has_condition(self, field: str, operator: str) -> bool:
        return any(c for c in self.conditions if c.field == field and c.operator == operator)


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
        return QueryIntent.parse_obj(data)
    except ValidationError as exc:
        raise ValueError(f"Intent JSON failed validation: {exc}") from exc
