#!/usr/bin/env python3
"""
Debug script to test code generation for weight queries.
"""

from app.utils.query_intent import QueryIntent, Filter
from app.utils.ai.code_generator import generate_code
from app.utils.ai_helper import AIHelper
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_weight_code_generation():
    """Test that weight queries generate correct code."""
    print("=== Testing Weight Code Generation ===")

    # Create AI helper
    helper = AIHelper()

    # Test the exact query that was failing
    query = "What is the average weight of patients?"

    print(f"\n--- Testing: '{query}' ---")

    # Get intent
    intent = helper.get_query_intent(query)
    print(f"Intent: {intent}")
    print(f"Analysis type: {intent.analysis_type}")
    print(f"Target field: {intent.target_field}")
    print(f"Filters: {intent.filters}")

    # Generate code
    code = generate_code(intent)
    print("\n--- Generated Code ---")
    print(code)

    # Check if the code contains the correct field
    if "weight" in code and "bmi" not in code:
        print("\n✅ Code correctly uses 'weight' field")
    elif "bmi" in code and "weight" not in code:
        print("\n❌ Code incorrectly uses 'bmi' instead of 'weight'")
    elif "weight" in code and "bmi" in code:
        print("\n⚠️ Code contains both 'weight' and 'bmi' - check context")
    else:
        print("\n❓ Code doesn't contain either 'weight' or 'bmi'")


def test_manual_intent():
    """Test with manually created intent to isolate the issue."""
    print("\n=== Testing Manual Intent ===")

    # Create intent manually
    intent = QueryIntent(
        analysis_type="average",
        target_field="weight",
        filters=[],
        conditions=[],
        parameters={},
        additional_fields=[],
        group_by=[],
        time_range=None,
    )
    intent.raw_query = "What is the average weight of patients?"

    print(f"Manual intent: {intent}")

    # Generate code
    code = generate_code(intent)
    print("\n--- Generated Code from Manual Intent ---")
    print(code)

    # Check if the code contains the correct field
    if "weight" in code and "bmi" not in code:
        print("\n✅ Manual intent code correctly uses 'weight' field")
    elif "bmi" in code and "weight" not in code:
        print("\n❌ Manual intent code incorrectly uses 'bmi' instead of 'weight'")
    elif "weight" in code and "bmi" in code:
        print("\n⚠️ Manual intent code contains both 'weight' and 'bmi' - check context")
    else:
        print("\n❓ Manual intent code doesn't contain either 'weight' or 'bmi'")


def test_active_patients_scenario():
    """Test the scenario that matches the last_executed_code.py exactly."""
    print("\n=== Testing Active Patients Scenario ===")

    # The last_executed_code.py had this SQL:
    # sql = """SELECT v.bmi FROM vitals v JOIN patients p ON v.patient_id = p.id WHERE p.active = 1"""
    # This suggests the intent had an active filter

    # Create intent with active filter
    intent = QueryIntent(
        analysis_type="average",
        target_field="weight",  # This should be weight, not BMI
        filters=[Filter(field="active", value=1)],
        conditions=[],
        parameters={},
        additional_fields=[],
        group_by=[],
        time_range=None,
    )
    intent.raw_query = "What is the average weight of patients?"

    print(f"Intent with active filter: {intent}")

    # Generate code
    code = generate_code(intent)
    print("\n--- Generated Code with Active Filter ---")
    print(code)

    # Check if the code contains the correct field
    if "weight" in code and "bmi" not in code:
        print("\n✅ Code with active filter correctly uses 'weight' field")
    elif "bmi" in code and "weight" not in code:
        print("\n❌ Code with active filter incorrectly uses 'bmi' instead of 'weight'")
    elif "weight" in code and "bmi" in code:
        print(
            "\n⚠️ Code with active filter contains both 'weight' and 'bmi' - check context"
        )
    else:
        print("\n❓ Code with active filter doesn't contain either 'weight' or 'bmi'")


if __name__ == "__main__":
    test_weight_code_generation()
    test_manual_intent()
    test_active_patients_scenario()
