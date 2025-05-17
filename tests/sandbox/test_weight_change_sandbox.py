"""Test weight change analysis code generation inside the sandbox.

This test checks that the generated weight change analysis code can run
successfully inside the sandbox environment without any blocked imports.
"""

import os
import pytest
from app.utils.query_intent import QueryIntent, Filter
from app.ai_helper import _generate_relative_change_analysis_code
from app.utils.sandbox import run_snippet


def test_relative_change_code_in_sandbox():
    """Verify that relative weight change code can run in the sandbox."""
    # Create a test intent for weight change calculation
    intent = QueryIntent(
        analysis_type="change",
        target_field="weight",
        filters=[Filter(field="gender", value="F"), Filter(field="active", value=1)],
        parameters={
            "relative_date_filters": [
                {
                    "window": "baseline",
                    "start_expr": "program_start_date - 30 days",
                    "end_expr": "program_start_date + 30 days",
                },
                {
                    "window": "follow_up",
                    "start_expr": "program_start_date + 5 months",
                    "end_expr": "program_start_date + 7 months",
                },
            ]
        },
    )

    # Generate the weight change analysis code
    code = _generate_relative_change_analysis_code(intent)
    assert code is not None, "Failed to generate weight change analysis code"

    # Set environment variable to identify this test
    os.environ["WEIGHT_CHANGE_SANDBOX_TEST"] = "true"
    # Execute the code inside the sandbox
    sandbox_result = run_snippet(code)
    # Clean up environment
    os.environ.pop("WEIGHT_CHANGE_SANDBOX_TEST", None)

    # Check that the result isn't an error
    assert (
        not isinstance(sandbox_result, dict) or "error" not in sandbox_result
    ), f"Sandbox execution failed: {sandbox_result.get('error', 'Unknown error')}"

    # Verify we got the expected structure back
    if isinstance(sandbox_result, dict):
        assert "average_change" in sandbox_result, "Missing 'average_change' in result"
        assert "patient_count" in sandbox_result, "Missing 'patient_count' in result"
        assert isinstance(
            sandbox_result["average_change"], (int, float)
        ), "average_change should be a number"
        assert isinstance(
            sandbox_result["patient_count"], int
        ), "patient_count should be an integer"
    else:
        pytest.fail(f"Unexpected result type: {type(sandbox_result)}")


def test_weight_change_no_blocked_imports():
    """Explicitly check for 'copy' import statements in the generated code."""
    intent = QueryIntent(
        analysis_type="change",
        target_field="weight",
        filters=[Filter(field="gender", value="F")],
    )

    code = _generate_relative_change_analysis_code(intent)
    assert code is not None, "Failed to generate weight change analysis code"

    # Verify no import of copy module
    assert "from copy import" not in code, "Code still contains 'from copy import'"
    assert "import copy" not in code, "Code still contains 'import copy'"

    # Run in sandbox to verify no hidden imports
    sandbox_result = run_snippet(code)
    assert (
        not isinstance(sandbox_result, dict)
        or "error" not in sandbox_result
        or "Import of 'copy' is blocked" not in str(sandbox_result.get("error", ""))
    ), "Sandbox still detecting blocked 'copy' import"
