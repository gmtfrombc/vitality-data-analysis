"""Tests for condition-related intent clarification."""

from unittest.mock import patch

from app.utils.intent_clarification import clarifier, SlotType
from app.utils.query_intent import QueryIntent, Filter, CONDITION_FIELD


def test_identify_missing_condition_slots():
    """Test identification of missing condition information."""
    # Create a query intent with an unknown condition
    intent = QueryIntent(
        analysis_type="count",
        target_field=CONDITION_FIELD,
        filters=[Filter(field=CONDITION_FIELD, value="rare_disease")],
        conditions=[],
        parameters={},
        additional_fields=[],
        group_by=[],
        time_range=None,
    )

    # Mock the condition mapper to require clarification
    with patch(
        "app.utils.condition_mapper.condition_mapper.should_ask_clarifying_question",
        return_value=True,
    ):
        # Test that we correctly identify the missing slot
        slots = clarifier.identify_missing_slots(
            intent, "How many patients have rare_disease?"
        )

        # Find condition-related slots
        condition_slots = [
            slot for slot in slots if slot.type == SlotType.CONDITION_UNCLEAR
        ]

        # Verify results
        assert len(condition_slots) == 1
        assert condition_slots[0].description == "condition needs clarification"
        assert condition_slots[0].field_hint == "rare_disease"


def test_no_clarification_for_known_condition():
    """Test that we don't ask for clarification for a known condition."""
    # Create a query intent with a known condition
    intent = QueryIntent(
        analysis_type="count",
        target_field=CONDITION_FIELD,
        filters=[Filter(field=CONDITION_FIELD, value="hypertension")],
        conditions=[],
        parameters={},
        additional_fields=[],
        group_by=[],
        time_range=None,
    )

    # Mock the condition mapper to not require clarification
    with patch(
        "app.utils.condition_mapper.condition_mapper.should_ask_clarifying_question",
        return_value=False,
    ):
        # Test that we don't identify any condition-related slots
        slots = clarifier.identify_missing_slots(
            intent, "How many patients have hypertension?"
        )

        # Find condition-related slots
        condition_slots = [
            slot for slot in slots if slot.type == SlotType.CONDITION_UNCLEAR
        ]

        # Verify no condition-related slots
        assert len(condition_slots) == 0


def test_clarification_for_missing_condition():
    """Test that we ask for clarification when a condition query has no specified condition."""
    # Create a query intent with no specific condition
    intent = QueryIntent(
        analysis_type="count",
        target_field=CONDITION_FIELD,
        filters=[],  # No condition filter
        conditions=[],
        parameters={},
        additional_fields=[],
        group_by=[],
        time_range=None,
    )

    # Test that we identify the missing slot
    slots = clarifier.identify_missing_slots(
        intent, "How many patients have medical conditions?"
    )

    # Find condition-related slots
    condition_slots = [
        slot for slot in slots if slot.type == SlotType.CONDITION_UNCLEAR
    ]

    # Verify results
    assert len(condition_slots) == 1
    assert condition_slots[0].description == "condition not specified"


def test_get_specific_clarification_for_conditions():
    """Test that condition clarification questions are included in the final questions."""
    # Create a query intent with an unknown condition
    intent = QueryIntent(
        analysis_type="count",
        target_field=CONDITION_FIELD,
        filters=[Filter(field=CONDITION_FIELD, value="unknown_disease")],
        conditions=[],
        parameters={},
        additional_fields=[],
        group_by=[],
        time_range=None,
    )

    # Mock the condition mapper to require clarification
    with patch(
        "app.utils.condition_mapper.condition_mapper.should_ask_clarifying_question",
        return_value=True,
    ):
        # Test that we get a clarification question
        needs_clarification, questions = clarifier.get_specific_clarification(
            intent, "How many patients have unknown_disease?"
        )

        # Verify results
        assert needs_clarification is True
        assert len(questions) >= 1
        # The question should mention the unknown condition
        assert any("unknown_disease" in q for q in questions)
