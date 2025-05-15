"""
Preprocessing functions for AI interactions.

This module contains functions to prepare data for AI processing and to validate and
correct AI-generated narratives to ensure consistent representation of clinical metrics.
"""

import re
from typing import Dict, Any
from app.utils.metric_reference import get_reference, extract_metrics_from_text


def preprocess_results_for_ai(results: Dict[str, Any], query: str) -> Dict[str, Any]:
    """Prepare analysis results for AI processing by adding reference ranges.

    Args:
        results: The analysis results dictionary
        query: The original user query that generated these results

    Returns:
        Processed results with reference ranges added
    """
    # Make a copy to avoid modifying the original
    enriched_results = results.copy() if results else {}

    # Detect metrics mentioned in query or results
    metrics = extract_metrics_from_text(query)

    # Add reference section if not present
    if "reference" not in enriched_results:
        enriched_results["reference"] = {}

    # Add reference ranges for all detected metrics
    ref_data = get_reference()
    for metric in metrics:
        if metric in ref_data and metric not in enriched_results["reference"]:
            enriched_results["reference"][metric] = ref_data[metric]

    return enriched_results


def validate_narrative(narrative: str, query: str, results: Dict[str, Any]) -> str:
    """Ensures AI-generated narratives use proper clinical categorization language.

    Args:
        narrative: The AI-generated narrative text
        query: The original user query
        results: The analysis results including reference ranges

    Returns:
        Corrected narrative with proper categorical references
    """
    if not narrative:
        return narrative

    # Extract metrics from query and results
    metrics = extract_metrics_from_text(query)

    # Get reference data
    ref_data = get_reference()

    # Fix specific threshold mentions with proper categories
    for metric in metrics:
        if metric not in ref_data:
            continue

        # Detect threshold patterns like "above 6.5" or "below 120"
        reference_ranges = ref_data[metric]

        # Look for specific threshold mentions related to this metric
        # Pattern: "above/over/greater than X" where X is a number
        for pattern, direction in [
            # Qualifiers BEFORE the number
            (
                r"(?:above|over|greater than|higher than|>=?|≥)\s+(\d+\.?\d*)\s*%?",
                "above",
            ),
            (r"(?:below|under|less than|lower than|<=?|≤)\s+(\d+\.?\d*)\s*%?", "below"),
            # Qualifiers AFTER the number e.g. "6.5% or more"
            (
                r"(\d+\.?\d*)\s*%?\s*(?:or more|and above|or above|and greater|or greater|and higher|or higher)",
                "above",
            ),
            (
                r"(\d+\.?\d*)\s*%?\s*(?:or less|and below|or below|and lower|or lower)",
                "below",
            ),
        ]:
            matches = re.findall(pattern, narrative, re.IGNORECASE)

            for match in matches:
                threshold_str = match  # original string as it appears in narrative
                threshold_val = float(match)

                # Find the appropriate category for this threshold
                category = None
                for cat_name, range_data in reference_ranges.items():
                    if cat_name == "units":
                        continue

                    if (
                        isinstance(range_data, dict)
                        and "min" in range_data
                        and "max" in range_data
                    ):
                        min_val = range_data.get("min")
                        max_val = range_data.get("max")

                        # Check if the threshold matches this category's boundaries
                        if (
                            direction == "above"
                            and min_val is not None
                            and abs(threshold_val - min_val) < 0.1
                        ):
                            category = cat_name
                            break
                        elif (
                            direction == "below"
                            and max_val is not None
                            and abs(threshold_val - max_val) < 0.1
                        ):
                            # Find the category with the next lower max value
                            for other_cat, other_range in reference_ranges.items():
                                if (
                                    other_cat != "units"
                                    and isinstance(other_range, dict)
                                    and "max" in other_range
                                    and other_range["max"] is not None
                                    and other_range["max"] < threshold_val
                                ):
                                    category = other_cat
                                    break
                            break

                if category:
                    # Replace the threshold mention with the category name
                    if direction == "above":
                        replacement = f"in the {category} range"
                        # Build a broad pattern capturing the original phrase with numeric value
                        pattern_to_replace = rf"(?:above|over|greater than|higher than|>=?|≥)?\s*{re.escape(threshold_str)}\s*%?\s*(?:or more|and above|or above|and greater|or greater|and higher|or higher)?"
                        narrative = re.sub(
                            pattern_to_replace,
                            replacement,
                            narrative,
                            flags=re.IGNORECASE,
                        )
                    else:
                        # Most "below" references are to normal ranges
                        replacement = "in the normal range"
                        # Build a broad pattern capturing the original phrase with numeric value
                        pattern_to_replace = rf"(?:below|under|less than|lower than|<=?|≤)?\s*{re.escape(threshold_str)}\s*%?\s*(?:or less|and below|or below|and lower|or lower)?"
                        narrative = re.sub(
                            pattern_to_replace,
                            replacement,
                            narrative,
                            flags=re.IGNORECASE,
                        )

                    correct_value = min_val if direction == "above" else max_val
                    # Format number minimally (avoid trailing .0)
                    correct_str = (
                        (
                            f"{correct_value:.1f}"
                            if correct_value is not None
                            else threshold_str
                        )
                        .rstrip("0")
                        .rstrip(".")
                    )

                    # Replace only the numeric part to preserve phrasing such as "or more"
                    narrative = re.sub(
                        re.escape(threshold_str),
                        correct_str,
                        narrative,
                        count=1,
                        flags=re.IGNORECASE,
                    )

    return narrative
