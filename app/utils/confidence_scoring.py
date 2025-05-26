"""Confidence scoring for Smart Feedback System.

This module analyzes query intent and execution results to calculate
confidence scores that inform feedback request decisions.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """Calculates confidence scores for queries and results."""

    def __init__(self):
        """Initialize the confidence scorer."""
        # Known high-confidence patterns
        self.high_confidence_patterns = [
            r"\baverage\s+\w+",
            r"\bcount\s+of\s+\w+",
            r"\btotal\s+\w+",
            r"\bmedian\s+\w+",
            r"\bmin\s+\w+",
            r"\bmax\s+\w+",
        ]

        # Known low-confidence patterns
        self.low_confidence_patterns = [
            r"\bcompare\s+\w+\s+to\s+\w+",
            r"\bcorrelation\s+between",
            r"\btrend\s+over\s+time",
            r"\bpredict\s+\w+",
        ]

        # Medical field indicators
        self.medical_fields = {
            "bmi",
            "weight",
            "height",
            "sbp",
            "dbp",
            "glucose",
            "a1c",
            "cholesterol",
            "triglycerides",
            "age",
            "temperature",
        }

    def score_intent_confidence(self, intent: dict) -> float:
        """Score confidence in intent parsing (0.0-1.0).

        Args:
            intent: Parsed intent dictionary

        Returns:
            Confidence score for intent parsing
        """
        try:
            confidence_factors = []

            # Factor 1: Analysis type clarity (30% weight)
            analysis_type = intent.get("analysis_type", "unknown")
            if analysis_type == "unknown":
                confidence_factors.append(0.2)
            elif analysis_type in ["count", "average", "sum", "min", "max"]:
                # Simple aggregations are high confidence
                confidence_factors.append(0.9)
            elif analysis_type in ["median", "distribution"]:
                confidence_factors.append(0.8)
            elif analysis_type in ["comparison", "trend", "correlation"]:
                confidence_factors.append(0.6)  # More complex analyses
            else:
                confidence_factors.append(0.7)  # Default for known types

            # Factor 2: Target field clarity (25% weight)
            target_field = intent.get("target_field", "")
            if not target_field or target_field == "unknown":
                confidence_factors.append(0.3)
            elif target_field.lower() in self.medical_fields:
                confidence_factors.append(0.9)  # Known medical fields
            else:
                confidence_factors.append(0.7)  # Other fields

            # Factor 3: Filter specificity (20% weight)
            filters = intent.get("filters", [])
            if not filters:
                # No filters is moderate confidence
                confidence_factors.append(0.6)
            elif len(filters) > 3:
                # Too many filters might be confusing
                confidence_factors.append(0.5)
            else:
                confidence_factors.append(0.8)  # Good filter count

            # Factor 4: Condition clarity (15% weight)
            conditions = intent.get("conditions", [])
            if conditions:
                # Check if conditions are well-formed
                valid_conditions = sum(
                    1
                    for c in conditions
                    if c.get("field") and c.get("operator") and "value" in c
                )
                condition_score = (
                    valid_conditions / len(conditions) if conditions else 0
                )
                confidence_factors.append(condition_score)
            else:
                confidence_factors.append(0.7)  # No conditions is neutral

            # Factor 5: Raw query pattern matching (10% weight)
            raw_query = intent.get("raw_query", "").lower()
            if any(
                re.search(pattern, raw_query)
                for pattern in self.high_confidence_patterns
            ):
                confidence_factors.append(0.9)
            elif any(
                re.search(pattern, raw_query)
                for pattern in self.low_confidence_patterns
            ):
                confidence_factors.append(0.4)
            else:
                confidence_factors.append(0.7)

            # Calculate weighted average
            weights = [0.3, 0.25, 0.2, 0.15, 0.1]
            weighted_score = sum(
                score * weight for score, weight in zip(confidence_factors, weights)
            )

            return min(1.0, max(0.0, weighted_score))

        except Exception as e:
            logger.error(f"Error scoring intent confidence: {e}")
            return 0.5  # Default moderate confidence

    def score_execution_success(self, results: dict) -> float:
        """Score execution success based on results (0.0-1.0).

        Args:
            results: Execution results dictionary

        Returns:
            Confidence score for execution success
        """
        try:
            if not results:
                return 0.1  # No results is very low confidence

            confidence_factors = []

            # Factor 1: Presence of data (40% weight)
            if "data" in results and results["data"]:
                data = results["data"]
                if isinstance(data, list) and len(data) > 0:
                    confidence_factors.append(0.9)
                elif isinstance(data, dict) and data:
                    confidence_factors.append(0.8)
                else:
                    confidence_factors.append(0.3)
            else:
                confidence_factors.append(0.2)

            # Factor 2: No errors (30% weight)
            if "error" in results and results["error"]:
                confidence_factors.append(0.1)
            elif "errors" in results and results["errors"]:
                confidence_factors.append(0.2)
            else:
                confidence_factors.append(0.9)

            # Factor 3: Execution time (20% weight)
            execution_time = results.get("execution_time", 0)
            if execution_time > 10:  # Very slow execution
                confidence_factors.append(0.5)
            elif execution_time > 5:  # Slow execution
                confidence_factors.append(0.7)
            else:  # Fast execution
                confidence_factors.append(0.9)

            # Factor 4: Result completeness (10% weight)
            expected_keys = ["data", "summary", "visualization"]
            present_keys = sum(
                1 for key in expected_keys if key in results and results[key]
            )
            completeness_score = present_keys / len(expected_keys)
            confidence_factors.append(completeness_score)

            # Calculate weighted average
            weights = [0.4, 0.3, 0.2, 0.1]
            weighted_score = sum(
                score * weight for score, weight in zip(confidence_factors, weights)
            )

            return min(1.0, max(0.0, weighted_score))

        except Exception as e:
            logger.error(f"Error scoring execution success: {e}")
            return 0.5  # Default moderate confidence

    def score_result_quality(self, results: dict) -> float:
        """Score quality of analysis results (0.0-1.0).

        Args:
            results: Analysis results dictionary

        Returns:
            Confidence score for result quality
        """
        try:
            if not results:
                return 0.1

            confidence_factors = []

            # Factor 1: Data volume (30% weight)
            data = results.get("data", [])
            if isinstance(data, list):
                if len(data) == 0:
                    confidence_factors.append(0.2)  # No data
                elif len(data) < 5:
                    confidence_factors.append(0.5)  # Very little data
                elif len(data) < 20:
                    confidence_factors.append(0.7)  # Some data
                else:
                    confidence_factors.append(0.9)  # Good amount of data
            else:
                confidence_factors.append(0.6)  # Non-list data

            # Factor 2: Summary quality (25% weight)
            summary = results.get("summary", "")
            if not summary:
                confidence_factors.append(0.3)
            elif len(summary) < 50:
                confidence_factors.append(0.5)  # Very brief summary
            elif len(summary) > 500:
                # Very long summary might be verbose
                confidence_factors.append(0.7)
            else:
                confidence_factors.append(0.9)  # Good summary length

            # Factor 3: Visualization presence (20% weight)
            if "visualization" in results and results["visualization"]:
                confidence_factors.append(0.9)
            else:
                confidence_factors.append(0.4)

            # Factor 4: Statistical validity (15% weight)
            # Check for reasonable statistical values
            if "statistics" in results:
                stats = results["statistics"]
                if isinstance(stats, dict):
                    # Check for NaN or infinite values
                    has_valid_stats = all(
                        isinstance(v, (int, float))
                        and str(v).lower() not in ["nan", "inf", "-inf"]
                        for v in stats.values()
                        if isinstance(v, (int, float))
                    )
                    confidence_factors.append(0.9 if has_valid_stats else 0.3)
                else:
                    confidence_factors.append(0.6)
            else:
                confidence_factors.append(0.7)  # No stats is neutral

            # Factor 5: Result consistency (10% weight)
            # Check if results are internally consistent
            if "count" in results and "data" in results:
                expected_count = results.get("count", 0)
                actual_count = len(results.get("data", []))
                if expected_count == actual_count:
                    confidence_factors.append(0.9)
                else:
                    confidence_factors.append(0.5)
            else:
                confidence_factors.append(0.7)

            # Calculate weighted average
            weights = [0.3, 0.25, 0.2, 0.15, 0.1]
            weighted_score = sum(
                score * weight for score, weight in zip(confidence_factors, weights)
            )

            return min(1.0, max(0.0, weighted_score))

        except Exception as e:
            logger.error(f"Error scoring result quality: {e}")
            return 0.5  # Default moderate confidence

    def calculate_overall_confidence(
        self, query: str, intent: Optional[dict] = None, results: Optional[dict] = None
    ) -> float:
        """Calculate overall confidence score.

        Args:
            query: Original query text
            intent: Parsed intent (optional)
            results: Analysis results (optional)

        Returns:
            Overall confidence score (0.0-1.0)
        """
        try:
            confidence_scores = []
            weights = []

            # Intent confidence (30% weight if available)
            if intent:
                intent_score = self.score_intent_confidence(intent)
                confidence_scores.append(intent_score)
                weights.append(0.3)

            # Execution success (35% weight if available)
            if results:
                execution_score = self.score_execution_success(results)
                confidence_scores.append(execution_score)
                weights.append(0.35)

            # Result quality (35% weight if available)
            if results:
                quality_score = self.score_result_quality(results)
                confidence_scores.append(quality_score)
                weights.append(0.35)

            # If no intent or results, use query-based heuristics
            if not confidence_scores:
                query_lower = query.lower()
                if any(
                    pattern in query_lower for pattern in ["average", "count", "total"]
                ):
                    return 0.7  # Simple queries are moderately confident
                elif any(
                    pattern in query_lower
                    for pattern in ["compare", "correlation", "predict"]
                ):
                    return 0.4  # Complex queries are less confident
                else:
                    return 0.5  # Default

            # Normalize weights
            total_weight = sum(weights)
            if total_weight > 0:
                normalized_weights = [w / total_weight for w in weights]
                overall_score = sum(
                    score * weight
                    for score, weight in zip(confidence_scores, normalized_weights)
                )
            else:
                overall_score = sum(confidence_scores) / len(confidence_scores)

            return min(1.0, max(0.0, overall_score))

        except Exception as e:
            logger.error(f"Error calculating overall confidence: {e}")
            return 0.5  # Default moderate confidence
