#!/usr/bin/env python3
"""
Test script to verify the reference table fix works in both modes.
"""

from app.data_assistant import DataAnalysisAssistant
import panel as pn
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_narrative_mode_with_reference_table():
    """Test that reference table appears in narrative mode."""
    print("=== Testing Narrative Mode with Reference Table ===")

    # Create assistant instance
    assistant = DataAnalysisAssistant(test_mode=True)

    # Mock the engine results and intent
    class MockIntent:
        def __init__(self, query):
            self.raw_query = query

    # Set up mock data
    assistant.query_text = "Show me patients with high A1C"
    assistant.engine.execution_results = {"average_a1c": 7.2}
    assistant.engine.intent = MockIntent("Show me patients with high A1C")
    assistant.show_narrative = "Narrative"

    # Mock the interpret_results method to return a narrative
    def mock_interpret_results():
        return "The analysis shows that patients have an average A1C of 7.2%, which is in the high range."

    assistant.engine.interpret_results = mock_interpret_results

    # Call the display method
    assistant._display_final_results()

    # Check the results
    results = assistant.ui.result_container.objects
    print(f"Number of result objects: {len(results)}")

    # Look for reference table
    reference_table_found = False
    for i, obj in enumerate(results):
        print(f"Object {i}: {type(obj)}")
        if hasattr(obj, "object") and "Clinical Reference Ranges" in str(obj.object):
            reference_table_found = True
            print(f"✅ Found reference table at index {i}")
            print("Reference table preview:")
            print(obj.object[:200] + "...")
            break

    if not reference_table_found:
        print("❌ Reference table NOT found in narrative mode")

    return reference_table_found


def test_tabular_mode_with_reference_table():
    """Test that reference table appears in tabular mode."""
    print("\n=== Testing Tabular Mode with Reference Table ===")

    # Create assistant instance
    assistant = DataAnalysisAssistant(test_mode=True)

    # Mock the engine results and intent
    class MockIntent:
        def __init__(self, query):
            self.raw_query = query

    # Set up mock data
    assistant.query_text = "What's the average BMI?"
    assistant.engine.execution_results = {"average_bmi": 28.5}
    assistant.engine.intent = MockIntent("What's the average BMI?")
    assistant.show_narrative = "Tabular"  # Set to tabular mode

    # Call the display method
    assistant._display_final_results()

    # Check the results
    results = assistant.ui.result_container.objects
    print(f"Number of result objects: {len(results)}")

    # Look for reference table
    reference_table_found = False
    for i, obj in enumerate(results):
        print(f"Object {i}: {type(obj)}")
        if hasattr(obj, "object") and "Clinical Reference Ranges" in str(obj.object):
            reference_table_found = True
            print(f"✅ Found reference table at index {i}")
            print("Reference table preview:")
            print(obj.object[:200] + "...")
            break

    if not reference_table_found:
        print("❌ Reference table NOT found in tabular mode")

    return reference_table_found


if __name__ == "__main__":
    print("Testing Reference Table Fix\n")

    # Initialize Panel
    pn.extension()

    # Test both modes
    narrative_success = test_narrative_mode_with_reference_table()
    tabular_success = test_tabular_mode_with_reference_table()

    print("\n=== Summary ===")
    print(f"Narrative mode: {'✅ PASS' if narrative_success else '❌ FAIL'}")
    print(f"Tabular mode: {'✅ PASS' if tabular_success else '❌ FAIL'}")

    if narrative_success and tabular_success:
        print("\n🎉 All tests passed! Reference table fix is working.")
    else:
        print("\n⚠️ Some tests failed. Check the implementation.")
