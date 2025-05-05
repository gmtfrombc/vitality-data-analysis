"""Intent clarification utilities for identifying missing information and generating specific requests.

This module provides a slot-based clarification system that identifies what specific information
is missing from an intent (slots) and generates targeted questions to fill those gaps.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Tuple

from .query_intent import QueryIntent, _CANONICAL_FIELDS

logger = logging.getLogger(__name__)


class SlotType(Enum):
    """Types of slots that can be missing from an intent."""

    TIME_RANGE = auto()
    METRIC = auto()
    DEMOGRAPHIC_FILTER = auto()
    COMPARISON_GROUP = auto()
    ANALYSIS_SPECIFIC = auto()
    INTENT_UNCLEAR = auto()


@dataclass
class MissingSlot:
    """A specific piece of information missing from the intent."""

    type: SlotType
    description: str
    field_hint: str = ""  # Optional hint about which field is affected
    question: str = ""  # The actual question to ask the user


class SlotBasedClarifier:
    """Identifies missing information in intents and generates specific clarifying questions."""

    # Common demographics for filtering
    DEMOGRAPHICS = frozenset(["gender", "age", "ethnicity", "active"])

    # Core clinical metrics
    CORE_METRICS = frozenset(["weight", "bmi", "sbp", "dbp", "score_value"])

    # Analysis types that typically need time ranges
    TIME_DEPENDENT_ANALYSES = frozenset(
        ["trend", "change", "comparison", "percent_change", "average_change"]
    )

    # Analysis types that need group-by or filters for comparison
    COMPARISON_ANALYSES = frozenset(
        ["comparison", "change", "percent_change", "comparison", "top_n"]
    )

    def __init__(self):
        """Initialize the clarifier with default settings."""
        pass

    def identify_missing_slots(
        self, intent: QueryIntent, raw_query: str
    ) -> List[MissingSlot]:
        """Identify what specific information is missing from the intent.

        Args:
            intent: The parsed query intent
            raw_query: The original query text

        Returns:
            A list of MissingSlot objects representing the information gaps
        """
        missing_slots = []

        # Check if analysis type is unknown or unclear
        # Support both dict from legacy code and QueryIntent - special test handling
        if isinstance(intent, dict):
            # Handle dict intents (from older code or tests)
            if intent.get("analysis_type") == "unknown":
                return [
                    MissingSlot(
                        type=SlotType.INTENT_UNCLEAR,
                        description="unclear analysis intent from dict",
                        question="Could you please clarify what kind of analysis you're looking for? For example: trends, comparisons, averages, etc.",
                    )
                ]
        elif intent.parameters.get("is_fallback", False):
            return [
                MissingSlot(
                    type=SlotType.INTENT_UNCLEAR,
                    description="unclear analysis intent",
                    question="Could you please clarify what kind of analysis you're looking for? For example: trends, comparisons, averages, etc.",
                )
            ]

        # 1. Check for missing time range in time-dependent analyses
        if (
            intent.analysis_type in self.TIME_DEPENDENT_ANALYSES
            and not intent.has_date_filter()
        ):
            missing_slots.append(
                MissingSlot(
                    type=SlotType.TIME_RANGE,
                    description="time range missing",
                    question="What time period would you like to analyze? For example: 'last 3 months', 'Q1 2025', or 'January to March 2025'.",
                )
            )

        # 2. Check for missing or non-canonical metric
        if intent.target_field not in _CANONICAL_FIELDS:
            missing_slots.append(
                MissingSlot(
                    type=SlotType.METRIC,
                    description="unclear metric",
                    field_hint=intent.target_field,
                    question="Which specific health metric would you like to analyze? For example: weight, BMI, blood pressure, etc.",
                )
            )
        elif intent.target_field == "score_value" and not intent.filters:
            # If score_value is used without specifying which score type
            missing_slots.append(
                MissingSlot(
                    type=SlotType.METRIC,
                    description="score type unspecified",
                    field_hint="score_type",
                    question="Which specific score are you interested in? For example: PHQ-9, GAD-7, etc.",
                )
            )

        # 3. Check for missing demographic filters in comparison analyses
        if intent.analysis_type in self.COMPARISON_ANALYSES:
            if not intent.group_by and not any(
                f.field in self.DEMOGRAPHICS for f in intent.filters
            ):
                missing_slots.append(
                    MissingSlot(
                        type=SlotType.DEMOGRAPHIC_FILTER,
                        description="demographic filter missing",
                        question="Would you like to filter or group the results by any specific patient characteristic? For example: gender, age group, ethnicity, etc.",
                    )
                )

        # 4. For correlation, check if we have enough metrics
        if intent.analysis_type == "correlation" and not intent.additional_fields:
            missing_slots.append(
                MissingSlot(
                    type=SlotType.ANALYSIS_SPECIFIC,
                    description="second correlation metric missing",
                    question=f"Which other metric would you like to correlate with {intent.target_field}?",
                )
            )

        # 5. For top_n, check if we have an n value
        if intent.analysis_type == "top_n" and not intent.parameters.get("n"):
            missing_slots.append(
                MissingSlot(
                    type=SlotType.ANALYSIS_SPECIFIC,
                    description="n value missing",
                    question="How many top results would you like to see? For example: top 5, top 10, etc.",
                )
            )

        return missing_slots

    def generate_slot_questions(self, missing_slots: List[MissingSlot]) -> List[str]:
        """Generate specific questions for the missing slots.

        Args:
            missing_slots: List of identified missing slots

        Returns:
            List of questions to ask the user
        """
        # For now, just return the questions from the slots
        # Future: Could customize or prioritize questions based on importance
        return [slot.question for slot in missing_slots]

    def get_specific_clarification(
        self, intent: QueryIntent, raw_query: str
    ) -> Tuple[bool, List[str]]:
        """Determine if clarification is needed and return specific questions.

        Args:
            intent: The parsed query intent
            raw_query: The original query text

        Returns:
            Tuple of (needs_clarification, list_of_questions)
        """
        # Handle dict intent (might come from tests or monkeypatching)
        if isinstance(intent, dict):
            return True, ["Could you please clarify what you're looking for?"]

        missing_slots = self.identify_missing_slots(intent, raw_query)

        if not missing_slots:
            return False, []

        questions = self.generate_slot_questions(missing_slots)
        return True, questions

    def create_fallback_intent(self, raw_query: str) -> QueryIntent:
        """Create a safe fallback intent for when parsing fails completely.

        Args:
            raw_query: The original query text

        Returns:
            A safe generic intent that will trigger appropriate clarification
        """
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


# Create a singleton instance for import by other modules
clarifier = SlotBasedClarifier()
