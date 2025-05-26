"""Smart feedback curation to reduce feedback fatigue and improve data quality.

This module implements intelligent feedback request logic that only asks for
feedback when it would be most valuable for system improvement.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from app.utils.feedback_db import _get_conn
from app.services.correction_service import CorrectionService

logger = logging.getLogger(__name__)

# Import new modules for Sprint 2.1
try:
    from app.utils.confidence_scoring import ConfidenceScorer
    from app.utils.novelty_detection import NoveltyDetector
except ImportError as e:
    logger.warning(f"Could not import confidence/novelty modules: {e}")
    ConfidenceScorer = None
    NoveltyDetector = None


class FeedbackPriorityCalculator:
    """Advanced priority calculation using multiple factors."""

    def __init__(self):
        """Initialize the priority calculator."""
        from app.utils.confidence_scoring import ConfidenceScorer
        from app.utils.novelty_detection import NoveltyDetector

        self.confidence_scorer = ConfidenceScorer()
        self.novelty_detector = NoveltyDetector()

        # Configurable weights for different factors
        self.weights = {
            "confidence": 0.25,  # Lower confidence = higher priority
            "novelty": 0.30,  # Higher novelty = higher priority
            "recency": 0.25,  # Recent similar feedback = lower priority
            "learning_value": 0.20,  # Higher learning value = higher priority
        }

    def calculate_weighted_priority(self, factors: Dict[str, float]) -> str:
        """Calculate priority using weighted factors.

        Args:
            factors: Dictionary of factor scores (0.0-1.0)

        Returns:
            Priority level: 'high', 'medium', 'low', or 'skip'
        """
        try:
            # Calculate weighted score
            weighted_score = 0.0

            # Lower confidence = higher priority (invert score)
            confidence_factor = 1.0 - factors.get("confidence", 0.5)
            weighted_score += confidence_factor * self.weights["confidence"]

            # Higher novelty = higher priority
            novelty_factor = factors.get("novelty", 0.0)
            weighted_score += novelty_factor * self.weights["novelty"]

            # Recent feedback = lower priority (invert recency)
            recency_factor = 1.0 - factors.get("recency", 0.0)
            weighted_score += recency_factor * self.weights["recency"]

            # Higher learning value = higher priority
            learning_factor = factors.get("learning_value", 0.0)
            weighted_score += learning_factor * self.weights["learning_value"]

            # Convert to priority levels
            if weighted_score >= 0.75:
                return "high"
            elif weighted_score >= 0.55:
                return "medium"
            elif weighted_score >= 0.35:
                return "low"
            else:
                return "skip"

        except Exception as e:
            logger.error(f"Error calculating weighted priority: {e}")
            return "medium"  # Fail safe

    def assess_learning_value(self, query: str) -> float:
        """Assess potential learning value of feedback (0.0-1.0).

        Args:
            query: Query text to analyze

        Returns:
            Learning value score
        """
        try:
            learning_factors = []

            # Factor 1: Query complexity (30% weight)
            complexity_score = self._assess_query_complexity(query)
            learning_factors.append(complexity_score * 0.3)

            # Factor 2: Potential for pattern learning (40% weight)
            pattern_score = self._assess_pattern_learning_potential(query)
            learning_factors.append(pattern_score * 0.4)

            # Factor 3: Error correction opportunity (30% weight)
            error_score = self._assess_error_correction_potential(query)
            learning_factors.append(error_score * 0.3)

            return sum(learning_factors)

        except Exception as e:
            logger.error(f"Error assessing learning value: {e}")
            return 0.5  # Default moderate learning value

    def detect_feedback_fatigue(self, user_id: str = "anon") -> bool:
        """Detect if user is experiencing feedback fatigue.

        Args:
            user_id: User identifier

        Returns:
            True if fatigue detected, False otherwise
        """
        try:
            with _get_conn() as conn:
                cursor = conn.cursor()

                # Check feedback frequency in last hour
                one_hour_ago = datetime.now() - timedelta(hours=1)
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM assistant_feedback 
                    WHERE created_at > ? AND user_id = ?
                """,
                    (one_hour_ago.isoformat(), user_id),
                )

                recent_feedback_count = cursor.fetchone()[0]

                # Check negative feedback ratio in last 24 hours
                one_day_ago = datetime.now() - timedelta(days=1)
                cursor.execute(
                    """
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN rating = 'down' THEN 1 ELSE 0 END) as negative
                    FROM assistant_feedback 
                    WHERE created_at > ? AND user_id = ?
                """,
                    (one_day_ago.isoformat(), user_id),
                )

                result = cursor.fetchone()
                total_feedback = result[0] if result[0] else 0
                negative_feedback = result[1] if result[1] else 0

                # Fatigue indicators:
                # 1. More than 5 feedback requests in last hour
                # 2. More than 70% negative feedback in last 24 hours (with at least 3 feedbacks)
                if recent_feedback_count > 5:
                    logger.info(
                        f"Feedback fatigue detected: {recent_feedback_count} requests in last hour"
                    )
                    return True

                if total_feedback >= 3 and (negative_feedback / total_feedback) > 0.7:
                    logger.info(
                        f"Feedback fatigue detected: {negative_feedback}/{total_feedback} negative feedback"
                    )
                    return True

                return False

        except Exception as e:
            logger.error(f"Error detecting feedback fatigue: {e}")
            return False  # Err on the side of not detecting fatigue

    def _assess_query_complexity(self, query: str) -> float:
        """Assess query complexity for learning value."""
        try:
            complexity_indicators = [
                r"\bcorrelation\b",
                r"\bcompare\b",
                r"\btrends?\b",  # Match both trend and trends
                r"\bpredict\b",
                r"\banalysis\b",
                r"\bstatistical\b",
                r"\bregression\b",
                r"\bvariance\b",
            ]

            import re

            matches = sum(
                1
                for pattern in complexity_indicators
                if re.search(pattern, query.lower())
            )

            # Normalize to 0.0-1.0 scale with more generous scoring
            return min(1.0, matches / 2.0)

        except Exception as e:
            logger.error(f"Error assessing query complexity: {e}")
            return 0.5

    def _assess_pattern_learning_potential(self, query: str) -> float:
        """Assess potential for learning new patterns."""
        try:
            # Check if query contains new field combinations
            correction_service = CorrectionService()

            # Simple heuristic: queries with multiple fields have higher learning potential
            import re

            field_mentions = len(
                re.findall(r"\b\w+\s+(?:and|with|vs|versus)\s+\w+\b", query.lower())
            )

            # Queries asking for specific metrics have learning potential
            metric_patterns = [
                r"\baverage\b",
                r"\bmedian\b",
                r"\bcount\b",
                r"\bsum\b",
                r"\bmax\b",
                r"\bmin\b",
            ]
            metric_matches = sum(
                1 for pattern in metric_patterns if re.search(pattern, query.lower())
            )

            # Combine factors with more generous scoring
            pattern_score = (
                (field_mentions * 0.5) + (min(metric_matches, 2) * 0.3) + 0.2
            )  # Base score for any query
            return min(1.0, pattern_score)

        except Exception as e:
            logger.error(f"Error assessing pattern learning potential: {e}")
            return 0.5

    def _assess_error_correction_potential(self, query: str) -> float:
        """Assess potential for error correction learning."""
        try:
            # Queries with ambiguous terms have higher error correction potential
            ambiguous_terms = [
                r"\bthis\b",
                r"\bthat\b",
                r"\bit\b",
                r"\bthese\b",
                r"\bthose\b",
                r"\bstuff\b",
                r"\bthing\b",
                r"\bdata\b",
            ]

            import re

            ambiguity_score = sum(
                1 for term in ambiguous_terms if re.search(term, query.lower())
            )

            # Normalize and cap at 1.0
            return min(1.0, ambiguity_score / 3.0)

        except Exception as e:
            logger.error(f"Error assessing error correction potential: {e}")
            return 0.5


def should_request_feedback(query: str, results: Dict[str, Any] = None) -> bool:
    """Determine if feedback would be valuable for this query.

    Args:
        query: The user's query text
        results: Analysis results (optional, for future confidence scoring)

    Returns:
        True if feedback should be requested, False to skip
    """
    try:
        # Phase 1: Basic duplicate detection
        if has_recent_similar_feedback(query, days=7):
            logger.info(
                f"Skipping feedback request - similar query recently rated: {query[:50]}..."
            )
            return False

        # Phase 1: Check for exact duplicates in last 24 hours
        if has_recent_exact_feedback(query, days=1):
            logger.info(
                f"Skipping feedback request - exact query recently rated: {query[:50]}..."
            )
            return False

        # Future phases can add:
        # - Confidence scoring
        # - Novelty detection
        # - Learning value assessment

        return True  # Default: request feedback

    except Exception as e:
        logger.error(f"Error in smart feedback logic: {e}")
        return True  # Fail safe: always request feedback if logic fails


def has_recent_exact_feedback(query: str, days: int = 1) -> bool:
    """Check if we have recent feedback for this exact query.

    Args:
        query: Query text to check
        days: Number of days to look back

    Returns:
        True if recent exact feedback exists
    """
    try:
        with _get_conn() as conn:
            cursor = conn.cursor()
            since_date = (datetime.now() - timedelta(days=days)).isoformat()

            cursor.execute(
                """
                SELECT COUNT(*) FROM assistant_feedback 
                WHERE question = ? AND created_at >= ?
            """,
                (query, since_date),
            )

            count = cursor.fetchone()[0]
            return count > 0

    except Exception as e:
        logger.error(f"Error checking exact feedback: {e}")
        return False


def has_recent_similar_feedback(
    query: str, days: int = 7, similarity_threshold: float = 0.80
) -> bool:
    """Check if we have recent feedback for similar queries.

    Args:
        query: Query text to check
        days: Number of days to look back
        similarity_threshold: Minimum similarity score (0.0-1.0)

    Returns:
        True if recent similar feedback exists
    """
    try:
        # Use existing correction service for similarity calculation
        cs = CorrectionService()

        with _get_conn() as conn:
            cursor = conn.cursor()
            since_date = (datetime.now() - timedelta(days=days)).isoformat()

            # Get recent feedback questions
            cursor.execute(
                """
                SELECT question, rating FROM assistant_feedback 
                WHERE created_at >= ?
                ORDER BY created_at DESC
            """,
                (since_date,),
            )

            recent_feedback = cursor.fetchall()

            for prev_query, rating in recent_feedback:
                similarity = cs._calculate_query_similarity(query, prev_query)

                if similarity >= similarity_threshold:
                    logger.info(
                        f"Found similar query (similarity: {similarity:.2f}): '{prev_query}' rated '{rating}'"
                    )

                    # If similar query was rated positively, skip feedback
                    if rating == "up":
                        return True

                    # If similar query was rated negatively, still request feedback
                    # (might be a different issue or improvement made)

            return False

    except Exception as e:
        logger.error(f"Error checking similar feedback: {e}")
        return False


def get_feedback_priority(query: str, results: Dict[str, Any] = None) -> str:
    """Enhanced priority calculation with confidence and novelty.

    Args:
        query: Query text
        results: Analysis results (optional)

    Returns:
        Priority level: 'high', 'medium', 'low', or 'skip'
    """
    try:
        # Phase 1: Basic duplicate detection (unchanged)
        if has_recent_exact_feedback(query, days=1):
            return "skip"

        if has_recent_similar_feedback(query, days=7):
            # Check if this is a novel pattern despite similarity
            if is_novel_query_pattern(query, threshold=0.8):
                # Novel pattern overrides similarity - still request feedback
                pass
            else:
                return "low"  # Similar and not novel

        # Phase 2: Enhanced priority calculation using confidence and novelty
        confidence_score = calculate_confidence_score(query, results)
        novelty_score = calculate_novelty_score(query)

        # Calculate weighted priority score
        # Lower confidence = higher priority for feedback
        # Higher novelty = higher priority for feedback
        confidence_factor = 1.0 - confidence_score  # Invert confidence
        novelty_factor = novelty_score

        # Weighted combination (60% novelty, 40% confidence)
        priority_score = (novelty_factor * 0.6) + (confidence_factor * 0.4)

        # Determine priority based on score
        if priority_score >= 0.8:
            return "high"
        elif priority_score >= 0.6:
            return "medium"
        elif priority_score >= 0.3:
            return "low"
        else:
            return "skip"

    except Exception as e:
        logger.error(f"Error calculating feedback priority: {e}")
        return "medium"  # Fail safe


def get_feedback_message(priority: str) -> str:
    """Get appropriate feedback message based on priority.

    Args:
        priority: Priority level from get_feedback_priority()

    Returns:
        User-facing message for the feedback widget
    """
    messages = {
        "high": "🎯 Your feedback is especially valuable for this novel or complex question!",
        "medium": "💭 Was this answer helpful?",
        "low": "👍 Quick rating appreciated (we have some feedback on similar questions)",
        "skip": "",  # No message if skipped
    }

    return messages.get(priority, messages["medium"])


def calculate_confidence_score(query: str, results: Dict[str, Any]) -> float:
    """Calculate confidence score for query results (0.0-1.0).

    Args:
        query: The user's query text
        results: Analysis results from the data assistant

    Returns:
        Confidence score from 0.0 (low confidence) to 1.0 (high confidence)
    """
    try:
        if ConfidenceScorer is None:
            logger.warning("ConfidenceScorer not available, using fallback")
            return 0.5  # Default moderate confidence

        scorer = ConfidenceScorer()

        # Try to extract intent from results if available
        intent = None
        if results and "intent" in results:
            intent = results["intent"]

        return scorer.calculate_overall_confidence(query, intent, results)

    except Exception as e:
        logger.error(f"Error calculating confidence score: {e}")
        return 0.5  # Default moderate confidence


def calculate_novelty_score(query: str) -> float:
    """Calculate novelty score for query pattern (0.0-1.0).

    Args:
        query: The user's query text

    Returns:
        Novelty score from 0.0 (known pattern) to 1.0 (completely novel)
    """
    try:
        if NoveltyDetector is None:
            logger.warning("NoveltyDetector not available, using fallback")
            return 0.5  # Default moderate novelty

        detector = NoveltyDetector()
        return detector.calculate_semantic_novelty(query)

    except Exception as e:
        logger.error(f"Error calculating novelty score: {e}")
        return 0.5  # Default moderate novelty


def is_novel_query_pattern(query: str, threshold: float = 0.7) -> bool:
    """Check if query represents a novel pattern.

    Args:
        query: The user's query text
        threshold: Novelty threshold (default 0.7)

    Returns:
        True if query is novel, False if similar to existing patterns
    """
    try:
        if NoveltyDetector is None:
            logger.warning("NoveltyDetector not available, using fallback")
            return True  # Err on the side of requesting feedback

        detector = NoveltyDetector()
        return detector.is_novel_query_pattern(query, threshold)

    except Exception as e:
        logger.error(f"Error checking novel query pattern: {e}")
        return True  # Err on the side of requesting feedback


def get_feedback_priority_advanced(
    query: str, results: Dict[str, Any] = None, user_id: str = "anon"
) -> str:
    """Advanced priority calculation with multiple factors.

    Args:
        query: Query text
        results: Analysis results (optional)
        user_id: User identifier for fatigue detection

    Returns:
        Priority level: 'high', 'medium', 'low', or 'skip'
    """
    try:
        calculator = FeedbackPriorityCalculator()

        # Check for feedback fatigue first
        if calculator.detect_feedback_fatigue(user_id):
            logger.info(f"Skipping feedback request due to fatigue for user: {user_id}")
            return "skip"

        # Phase 1: Basic duplicate detection (unchanged)
        if has_recent_exact_feedback(query, days=1):
            return "skip"

        # Calculate recency factor
        recency_factor = 0.0
        if has_recent_similar_feedback(query, days=7):
            # Check if this is a novel pattern despite similarity
            if is_novel_query_pattern(query, threshold=0.8):
                recency_factor = 0.3  # Some recency penalty but not full
            else:
                recency_factor = 0.8  # High recency penalty

        # Calculate all factors
        factors = {
            "confidence": calculate_confidence_score(query, results),
            "novelty": calculate_novelty_score(query),
            "recency": recency_factor,
            "learning_value": calculator.assess_learning_value(query),
        }

        # Log factors for debugging
        logger.debug(f"Priority factors for query '{query[:50]}...': {factors}")

        # Calculate weighted priority
        priority = calculator.calculate_weighted_priority(factors)

        logger.info(
            f"Advanced priority calculated: {priority} for query: {query[:50]}..."
        )
        return priority

    except Exception as e:
        logger.error(f"Error calculating advanced feedback priority: {e}")
        return "medium"  # Fail safe
