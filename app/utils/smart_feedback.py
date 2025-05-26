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
