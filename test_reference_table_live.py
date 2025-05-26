#!/usr/bin/env python3
"""
Live test script to verify reference table appears in a real workflow.
"""

from app.data_assistant import DataAnalysisAssistant
import panel as pn
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_simple_query_with_reference_table():
    """Test a simple query that should work and show reference table."""
    print("=== Testing Simple Query with Reference Table ===")

    # Initialize Panel
    pn.extension()

    # Create assistant instance
    assistant = DataAnalysisAssistant(test_mode=True)

    # Test with the BMI query that was failing
    query = "What is the average BMI of patients?"

    print(f"\n--- Testing query: '{query}' ---")

    # Set the query
    assistant.query_text = query
    assistant.ui.query_input.value = query

    # Reset workflow
    assistant.workflow.reset()
    assistant.ui.update_stage_indicators(assistant.workflow.current_stage)

    try:
        # Process the query (this should work for simple queries)
        assistant._process_query()

        # Check if we have results
        if assistant.engine.execution_results is not None:
            print("✅ Query executed successfully")
            print(f"Results: {assistant.engine.execution_results}")

            # Check if reference table was created
            results = assistant.ui.result_container.objects
            print(f"Number of result objects: {len(results)}")

            reference_table_found = False
            for i, obj in enumerate(results):
                print(f"Object {i}: {type(obj)}")
                if hasattr(obj, "object") and "Clinical Reference Ranges" in str(
                    obj.object
                ):
                    reference_table_found = True
                    print(f"✅ Found reference table at index {i}")
                    break

            if not reference_table_found:
                print("❌ Reference table NOT found")

            return reference_table_found
        else:
            print("❌ No results generated")

    except Exception as e:
        print(f"❌ Error processing query: {e}")
        import traceback

        traceback.print_exc()

    return False


def test_manual_reference_table():
    """Test creating reference table manually with known good data."""
    print("\n=== Testing Manual Reference Table Creation ===")

    from app.analysis_helpers import create_reference_ranges_table

    # Test with the BMI case specifically
    results = 34.76969209558824  # The scalar result that was causing issues
    query = "What is the average BMI of patients?"

    print(f"\nTesting: '{query}' with scalar result: {results}")
    table = create_reference_ranges_table(results, query)

    if table:
        print("✅ Reference table created successfully")
        if hasattr(table, "object"):
            html_content = table.object
            print(f"HTML content length: {len(html_content)} characters")
            # Check if it contains expected content
            if "Clinical Reference Ranges" in html_content:
                print("✅ Contains expected title")
            if "table" in html_content.lower():
                print("✅ Contains table HTML")
            if "BMI" in html_content or "Bmi" in html_content:
                print("✅ Contains BMI data")
            return True
    else:
        print("❌ No reference table created")

    return False


def test_none_query_handling():
    """Test that None query is handled gracefully."""
    print("\n=== Testing None Query Handling ===")

    from app.analysis_helpers import create_reference_ranges_table

    # Test with None query (the problematic case from the log)
    results = 34.76969209558824
    query = None

    print("Testing with None query")
    try:
        table = create_reference_ranges_table(results, query)
        if table is None:
            print("✅ None query handled gracefully (returned None)")
            return True
        else:
            print("❌ None query should return None but didn't")
            return False
    except Exception as e:
        print(f"❌ Error with None query: {e}")
        return False


if __name__ == "__main__":
    print("Live Reference Table Test\n")

    # Test manual creation first
    manual_success = test_manual_reference_table()

    # Test None handling
    none_success = test_none_query_handling()

    # Test with simple workflow
    workflow_success = test_simple_query_with_reference_table()

    print("\n=== Summary ===")
    print(f"Manual creation: {'✅ PASS' if manual_success else '❌ FAIL'}")
    print(f"None query handling: {'✅ PASS' if none_success else '❌ FAIL'}")
    print(f"Workflow test: {'✅ PASS' if workflow_success else '❌ FAIL'}")

    if manual_success and none_success:
        print("\n✅ Reference table functionality is working!")
        print("The issue might be with query text retrieval in the live app.")
    else:
        print("\n❌ Reference table functionality needs debugging.")
