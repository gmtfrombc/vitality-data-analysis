#!/usr/bin/env python
"""Test script for weight change analysis with unit conversion.

This script generates and executes code for weight change analysis and prints
the results to verify the unit conversion is working correctly.
"""

from app.utils.query_intent import QueryIntent
from app.ai_helper import _generate_relative_change_analysis_code
from app.utils.sandbox import run_snippet


def main():
    """Generate and execute weight change analysis code."""
    # Create a test intent for weight change analysis
    intent = QueryIntent(
        analysis_type="change",
        target_field="weight",
        filters=[{"field": "gender", "value": "F"}],
        parameters={
            "relative_date_filters": [
                {
                    "window": "baseline",
                    "start_expr": "program_start_date - 30 days",
                    "end_expr": "program_start_date + 30 days",
                },
                {
                    "window": "follow_up",
                    "start_expr": "program_start_date + 150 days",
                    "end_expr": "program_start_date + 210 days",
                },
            ]
        },
    )

    # Generate the code
    code = _generate_relative_change_analysis_code(intent)

    # Print the code for inspection
    print("Generated code:")
    print("-" * 40)
    print(code)
    print("-" * 40)

    # Execute the code in the sandbox
    print("\nExecuting code...")
    result = run_snippet(code)

    # Display results
    print("\nResults:")
    print("-" * 40)
    if isinstance(result, dict):
        for key, value in result.items():
            print(f"{key}: {value}")
    else:
        print(f"Result: {result}")

    # Check for unit specification in results
    if isinstance(result, dict) and "unit" in result:
        print(f"\nWeight change is reported in {result['unit']}")

    return result


if __name__ == "__main__":
    main()
