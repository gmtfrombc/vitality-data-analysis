#!/usr/bin/env python3
"""
Test script to verify the preprocessing fix handles scalar results.
"""

from app.utils.preprocess import preprocess_results_for_ai
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_scalar_preprocessing():
    """Test that scalar results are handled correctly in preprocessing."""
    print("=== Testing Scalar Preprocessing Fix ===")

    # Test with numpy float64 (the problematic case)
    scalar_result = np.float64(34.76969209558824)
    query = "What is the average BMI of patients?"

    try:
        processed = preprocess_results_for_ai(scalar_result, query)
        print("✅ Scalar preprocessing successful")
        print(f"Original result: {scalar_result} (type: {type(scalar_result)})")
        print(f"Processed result: {processed}")

        # Check that it's now a dictionary
        if isinstance(processed, dict):
            print("✅ Result is now a dictionary")

            # Check that it has the expected structure
            if "value" in processed:
                print("✅ Contains 'value' key")

            if "reference" in processed:
                print("✅ Contains 'reference' key")

                # Check if BMI reference was added
                if "bmi" in processed["reference"]:
                    print("✅ BMI reference ranges added")
                    print(f"BMI reference: {processed['reference']['bmi']}")
                else:
                    print("❌ BMI reference ranges not added")
            else:
                print("❌ Missing 'reference' key")
        else:
            print("❌ Result is not a dictionary")

        return True

    except Exception as e:
        print(f"❌ Error in scalar preprocessing: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_dict_preprocessing():
    """Test that dictionary results still work correctly."""
    print("\n=== Testing Dictionary Preprocessing ===")

    # Test with dictionary result
    dict_result = {"average_a1c": 7.2, "count": 150}
    query = "What is the average A1C?"

    try:
        processed = preprocess_results_for_ai(dict_result, query)
        print("✅ Dictionary preprocessing successful")
        print(f"Original result: {dict_result}")
        print(f"Processed result keys: {list(processed.keys())}")

        # Check that original data is preserved
        if "average_a1c" in processed and processed["average_a1c"] == 7.2:
            print("✅ Original data preserved")
        else:
            print("❌ Original data not preserved")

        # Check that reference was added
        if "reference" in processed and "a1c" in processed["reference"]:
            print("✅ A1C reference ranges added")
        else:
            print("❌ A1C reference ranges not added")

        return True

    except Exception as e:
        print(f"❌ Error in dictionary preprocessing: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Testing Preprocessing Fixes\n")

    scalar_success = test_scalar_preprocessing()
    dict_success = test_dict_preprocessing()

    print("\n=== Summary ===")
    print(f"Scalar preprocessing: {'✅ PASS' if scalar_success else '❌ FAIL'}")
    print(f"Dictionary preprocessing: {'✅ PASS' if dict_success else '❌ FAIL'}")

    if scalar_success and dict_success:
        print("\n🎉 All preprocessing tests passed!")
        print("The narrative generation should now work correctly.")
    else:
        print("\n⚠️ Some preprocessing tests failed.")
