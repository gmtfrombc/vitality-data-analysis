#!/usr/bin/env python3
"""
Debug script to test reference ranges table functionality.
"""

from app.utils.metric_reference import extract_metrics_from_text, get_reference
from app.analysis_helpers import create_reference_ranges_table, format_results
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_metric_extraction():
    """Test metric extraction from various queries."""
    print("=== Testing Metric Extraction ===")

    test_queries = [
        "Show me patients with high A1C",
        "What's the average BMI?",
        "Find patients with elevated blood pressure",
        "Show glucose levels over 100",
        "Compare cholesterol and triglycerides",
        "BMI distribution for diabetic patients",
    ]

    for query in test_queries:
        metrics = extract_metrics_from_text(query)
        print(f"Query: '{query}'")
        print(f"Extracted metrics: {metrics}")
        print()


def test_reference_table_creation():
    """Test reference table creation."""
    print("=== Testing Reference Table Creation ===")

    test_cases = [
        ({}, "Show me patients with high A1C"),
        ({}, "What's the average BMI?"),
    ]

    for results, query in test_cases:
        print(f"Query: '{query}'")
        table = create_reference_ranges_table(results, query)
        if table:
            print(f"Table created successfully: {type(table)}")
            # Try to get the HTML content if it's an HTML pane
            if hasattr(table, "object"):
                html_content = table.object
                print(f"HTML content length: {len(html_content)} characters")
                print("Full HTML content:")
                print(html_content)
                print("\n" + "-" * 50 + "\n")
        else:
            print("No table created (returned None)")
        print()


def test_format_results_integration():
    """Test the integration with format_results function."""
    print("=== Testing format_results Integration ===")

    # Create a mock intent object
    class MockIntent:
        def __init__(self, query):
            self.raw_query = query

    test_cases = [
        ({"average_a1c": 7.2}, MockIntent("Show me patients with high A1C")),
        ({"average_bmi": 28.5}, MockIntent("What's the average BMI?")),
    ]

    for results, intent in test_cases:
        print(f"Query: '{intent.raw_query}'")
        print(f"Results: {results}")

        try:
            formatted = format_results(results, intent)
            print(f"Formatted results count: {len(formatted)}")

            # Check if any of the formatted results is our reference table
            for i, item in enumerate(formatted):
                print(f"Item {i}: {type(item)}")
                if hasattr(item, "object") and "Clinical Reference Ranges" in str(
                    item.object
                ):
                    print(f"Found reference table at index {i}!")
                    print("Reference table HTML preview:")
                    print(item.object[:300] + "...")

        except Exception as e:
            print(f"Error in format_results: {e}")
            import traceback

            traceback.print_exc()

        print("\n" + "-" * 50 + "\n")


def test_reference_data():
    """Test reference data loading."""
    print("=== Testing Reference Data ===")

    try:
        ref_data = get_reference()
        print("Reference data loaded successfully")
        print(f"Available metrics: {list(ref_data.keys())}")

        # Test a specific metric
        if "a1c" in ref_data:
            print(f"A1C data: {ref_data['a1c']}")

    except Exception as e:
        print(f"Error loading reference data: {e}")


if __name__ == "__main__":
    print("Debug Reference Ranges Table\n")

    test_reference_data()
    print("\n" + "=" * 50 + "\n")

    test_metric_extraction()
    print("\n" + "=" * 50 + "\n")

    test_reference_table_creation()
    print("\n" + "=" * 50 + "\n")

    test_format_results_integration()
