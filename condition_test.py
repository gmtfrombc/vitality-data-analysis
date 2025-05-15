"""Test script for condition mapper with OpenAI fallback."""

from app.utils.condition_mapper import condition_mapper
import logging

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)


def test_known_condition():
    """Test with a condition in our core mappings."""
    print("\n--- Testing with known condition: type 2 diabetes ---")

    # Get canonical name
    canonical = condition_mapper.get_canonical_condition("type 2 diabetes")
    print(f"Canonical name: {canonical}")

    # Get ICD codes
    codes = condition_mapper.get_icd_codes("type 2 diabetes")
    print(f"ICD-10 codes: {codes}")

    # Get SQL list
    sql_list = condition_mapper.get_all_codes_as_sql_list("type 2 diabetes")
    print(f"SQL list: {sql_list}")

    # Check if we should ask a clarifying question
    should_ask = condition_mapper.should_ask_clarifying_question("type 2 diabetes")
    print(f"Should ask clarifying question: {should_ask}")


def test_synonym():
    """Test with a synonym of a known condition."""
    print("\n--- Testing with synonym: t2dm ---")

    # Get canonical name
    canonical = condition_mapper.get_canonical_condition("t2dm")
    print(f"Canonical name: {canonical}")

    # Get ICD codes
    codes = condition_mapper.get_icd_codes("t2dm")
    print(f"ICD-10 codes: {codes}")


def test_unknown_condition():
    """Test with a condition not in our core mappings."""
    print("\n--- Testing with unknown condition: migraine ---")

    # Get canonical name (should be None)
    canonical = condition_mapper.get_canonical_condition("migraine")
    print(f"Canonical name: {canonical}")

    # Get ICD codes (should trigger OpenAI lookup)
    codes = condition_mapper.get_icd_codes("migraine")
    print(f"ICD-10 codes: {codes}")

    # Check if we should ask a clarifying question
    should_ask = condition_mapper.should_ask_clarifying_question("migraine")
    print(f"Should ask clarifying question: {should_ask}")


if __name__ == "__main__":
    test_known_condition()
    test_synonym()
    test_unknown_condition()
