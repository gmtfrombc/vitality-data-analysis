#!/usr/bin/env python3
"""
Debug script to test intent parsing for weight vs BMI queries.
"""

from app.utils.ai.code_generator import generate_code
from app.utils.ai_helper import AIHelper
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_weight_vs_bmi_intent():
    """Test that weight and BMI queries are parsed correctly."""
    print("=== Testing Weight vs BMI Intent Parsing ===")

    # Create AI helper
    helper = AIHelper()

    test_queries = [
        "What is the average weight of patients?",
        "What is the average BMI of patients?",
        "Show me the average weight for active patients",
        "What's the average BMI for active patients?",
        "Average weight by gender",
        "Average BMI by gender",
    ]

    for query in test_queries:
        print(f"\n--- Testing: '{query}' ---")
        try:
            intent = helper.get_query_intent(query)
            print(f"Analysis type: {intent.analysis_type}")
            print(f"Target field: {intent.target_field}")
            print(f"Filters: {intent.filters}")

            # Generate code to see what SQL is produced
            code = generate_code(intent)

            # Extract the SQL from the code
            lines = code.split("\n")
            sql_lines = [line for line in lines if "SELECT" in line and "FROM" in line]
            if sql_lines:
                print(f"Generated SQL: {sql_lines[0]}")
            else:
                print("No SQL found in generated code")

        except Exception as e:
            print(f"Error: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    test_weight_vs_bmi_intent()
