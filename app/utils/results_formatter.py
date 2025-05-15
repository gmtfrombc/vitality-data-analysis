"""Result formatter utilities for consistent output handling.

This module provides utilities to ensure consistent output formatting from analysis
results, particularly for test environments. It helps normalize rich dictionary
results to scalar values when needed and handles visualization errors gracefully.
"""

from typing import Any, Dict, Union
import logging

# Expose public API
__all__ = ["extract_scalar", "normalize_visualization_error", "format_test_result"]

logger = logging.getLogger(__name__)


def extract_scalar(result: Any, key: str = "average_change") -> Union[float, int, Any]:
    """Extract a scalar value from a dictionary result.

    In our newer implementation, many analysis functions return rich dictionaries with
    multiple metrics. This function extracts a scalar value for tests that expect simple
    scalar returns.

    Args:
        result: The result to normalize (dict, scalar, or other)
        key: The dictionary key to extract if result is a dict

    Returns:
        A scalar value if possible, otherwise the original result
    """
    if isinstance(result, dict) and key in result:
        return result[key]
    return result


def normalize_visualization_error(result: Any) -> Dict[str, Any]:
    """Convert visualization errors to a standardized stub result.

    When visualization libraries are disabled or fail in the sandbox, this
    function provides a consistent placeholder response.

    Args:
        result: The original result (may be an error dict or other value)

    Returns:
        A dict with visualization stub and original data when possible
    """
    # If already a dict with error related to visualization
    if isinstance(result, dict) and "error" in result:
        error_msg = str(result["error"])
        if any(
            msg in error_msg
            for msg in [
                "Plotting libraries are disabled",
                "hvplot is not available",
                "holoviews is not available",
                "import of 'holoviews'",
                "import of 'hvplot'",
            ]
        ):
            logger.info("Normalizing visualization error to stub result")
            # Keep the original data if available
            normalized = {
                "data": result.get("data", {}),
                "visualization": "<stubbed chart object>",
                "visualization_disabled": True,
            }

            # If we have a fallback flag, preserve it
            if "fallback" in result:
                normalized["fallback"] = result["fallback"]

            return normalized

    # If not a visualization error, return unchanged
    return result


def format_test_result(
    result: Any, expected_scalar: bool = False, scalar_key: str = "average_change"
) -> Any:
    """Format a result for test comparison, normalizing as needed.

    This function handles various result formats to ensure they match
    test expectations:

    1. Normalizes visualization errors to stub objects
    2. Extracts scalar values when expected_scalar=True
    3. Returns the original result format when no formatting is needed

    Args:
        result: The raw result from analysis
        expected_scalar: Whether a scalar value is expected by the test
        scalar_key: Key to extract if result is a dict and scalar is expected

    Returns:
        Formatted result matching test expectations
    """
    # First handle visualization errors
    result = normalize_visualization_error(result)

    # If scalar expected, extract it
    if expected_scalar:
        return extract_scalar(result, scalar_key)

    return result
