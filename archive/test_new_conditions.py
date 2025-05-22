"""Manual script for exercising condition mapper with sample queries.

This is NOT part of the automated pytest suite; it's intended for ad-hoc local
runs (``python test_new_conditions.py``).  We rename the helper function so
pytest doesn't treat its parameter as a fixture.
"""

from app.utils.condition_mapper import condition_mapper
import logging

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)


def check_condition(condition_name: str):
    """Print mapping information for *condition_name*."""
    print(f"\n--- Testing condition: {condition_name} ---")

    # Get canonical name
    canonical = condition_mapper.get_canonical_condition(condition_name)
    print(f"Canonical name: {canonical}")

    # Get ICD codes
    codes = condition_mapper.get_icd_codes(condition_name)
    print(f"ICD-10 codes: {codes}")

    # Get SQL list
    sql_list = condition_mapper.get_all_codes_as_sql_list(condition_name)
    print(f"SQL list: {sql_list}")

    # Check if we should ask a clarifying question
    should_ask = condition_mapper.should_ask_clarifying_question(condition_name)
    print(f"Should ask clarifying question: {should_ask}")


if __name__ == "__main__":
    # Test the newly added conditions
    check_condition("chronic kidney disease")
    check_condition("ckd")  # synonym
    check_condition("obstructive sleep apnea")
    check_condition("osa")  # synonym
    check_condition("pcos")
    check_condition("polycystic ovary syndrome")  # synonym

    # Test the separated hypercholesterolemia
    check_condition("high cholesterol")
    check_condition("hypercholesterolemia")

    # Test hyperlipidemia to ensure it still works
    check_condition("hyperlipidemia")
    check_condition("dyslipidemia")  # synonym

    # Test the separated obesity-related conditions
    print("\n=== TESTING OBESITY-RELATED CONDITIONS ===")
    check_condition("obesity")
    check_condition("obese")  # synonym
    check_condition("morbid obesity")
    check_condition("severe obesity")  # synonym
    check_condition("overweight")
    check_condition("bmi between 25 and 30")  # synonym
    # Edge case tests
    check_condition("bmi 32")  # should map to obesity
    check_condition("bmi 42")  # should map to morbid_obesity
