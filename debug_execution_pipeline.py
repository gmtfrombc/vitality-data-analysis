#!/usr/bin/env python3
"""
Debug script to test the complete execution pipeline.
"""

from app.data_assistant import DataAnalysisAssistant
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_complete_pipeline():
    """Test the complete pipeline from query to execution."""
    print("=== Testing Complete Execution Pipeline ===")

    # Create assistant instance
    assistant = DataAnalysisAssistant(test_mode=True)

    # Test the exact query that was failing
    query = "What is the average weight of patients?"

    print(f"\n--- Testing: '{query}' ---")

    # Set the query
    assistant.query_text = query
    assistant.ui.query_input.value = query

    # Reset workflow
    assistant.workflow.reset()
    assistant.ui.update_stage_indicators(assistant.workflow.current_stage)

    try:
        # Process the query (this should work for simple queries)
        assistant._process_query()

        # Check the intent
        intent = assistant.engine.intent
        print(f"Intent: {intent}")
        if intent:
            print(f"Analysis type: {intent.analysis_type}")
            print(f"Target field: {intent.target_field}")
            print(f"Filters: {intent.filters}")

        # Check the generated code
        generated_code = assistant.engine.generated_code
        print("\n--- Generated Code ---")
        print(generated_code)

        # Check if the code contains the correct field
        if "weight" in generated_code and "bmi" not in generated_code:
            print("\n✅ Generated code correctly uses 'weight' field")
        elif "bmi" in generated_code and "weight" not in generated_code:
            print("\n❌ Generated code incorrectly uses 'bmi' instead of 'weight'")
        elif "weight" in generated_code and "bmi" in generated_code:
            print("\n⚠️ Generated code contains both 'weight' and 'bmi' - check context")
        else:
            print("\n❓ Generated code doesn't contain either 'weight' or 'bmi'")

        # Check the execution results
        results = assistant.engine.execution_results
        print("\n--- Execution Results ---")
        print(f"Results: {results}")

        # Check if the result makes sense for weight (should be around 180, not 35)
        if isinstance(results, (int, float)):
            if 150 <= results <= 250:
                print(f"✅ Result {results} looks like a reasonable weight value")
            elif 20 <= results <= 50:
                print(f"❌ Result {results} looks like BMI, not weight!")
            else:
                print(f"❓ Result {results} is unexpected for either weight or BMI")

        return True

    except Exception as e:
        print(f"❌ Error in pipeline: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_complete_pipeline()
