"""Novelty detection for Smart Feedback System.

This module analyzes query patterns to detect novel queries that would
benefit from feedback collection.
"""

from __future__ import annotations

import logging
import re
from typing import List, Set

from app.services.correction_service import CorrectionService
from app.utils.feedback_db import _get_conn

logger = logging.getLogger(__name__)


class NoveltyDetector:
    """Detects novel query patterns for feedback prioritization."""

    def __init__(self):
        """Initialize the novelty detector."""
        self.correction_service = CorrectionService()

        # Common medical metrics that are well-understood
        self.common_metrics = {
            "bmi",
            "weight",
            "height",
            "age",
            "sbp",
            "dbp",
            "glucose",
            "a1c",
            "cholesterol",
            "triglycerides",
            "temperature",
            "heart_rate",
        }

        self._known_metrics = self._load_known_metrics()
        self._known_patterns = self._load_known_patterns()

        # Common analysis patterns
        self.common_patterns = [
            r"\baverage\s+\w+",
            r"\bcount\s+of\s+\w+",
            r"\btotal\s+\w+",
            r"\bmedian\s+\w+",
            r"\bmin\s+\w+",
            r"\bmax\s+\w+",
            r"\bpatients\s+with\s+\w+",
        ]

        # Novel/complex patterns that benefit from feedback
        self.novel_patterns = [
            r"\bcorrelation\s+between\s+\w+\s+and\s+\w+",
            r"\btrend\s+over\s+time",
            r"\bcompare\s+\w+\s+to\s+\w+",
            r"\bpredict\s+\w+",
            r"\bchange\s+in\s+\w+",
            r"\bpercentage\s+change",
            r"\bvariance\s+in\s+\w+",
        ]

    def is_novel_query_pattern(self, query: str, threshold: float = 0.7) -> bool:
        """Check if query represents a novel pattern.

        Args:
            query: Query text to analyze
            threshold: Novelty threshold (0.0-1.0)

        Returns:
            True if query is novel, False if similar to existing patterns
        """
        try:
            novelty_score = self.calculate_semantic_novelty(query)
            return novelty_score >= threshold
        except Exception as e:
            logger.error(f"Error checking novel query pattern: {e}")
            return True  # Err on the side of requesting feedback

    def calculate_semantic_novelty(self, query: str) -> float:
        """Calculate semantic novelty score (0.0-1.0).

        Args:
            query: Query text to analyze

        Returns:
            Novelty score from 0.0 (known) to 1.0 (completely novel)
        """
        try:
            novelty_factors = []

            # Factor 1: Pattern novelty (40% weight)
            pattern_novelty = self._calculate_pattern_novelty(query)
            novelty_factors.append(pattern_novelty)

            # Factor 2: Metric novelty (30% weight)
            metric_novelty = self._calculate_metric_novelty(query)
            novelty_factors.append(metric_novelty)

            # Factor 3: Similarity to existing queries (30% weight)
            similarity_novelty = self._calculate_similarity_novelty(query)
            novelty_factors.append(similarity_novelty)

            # Calculate weighted average
            weights = [0.4, 0.3, 0.3]
            weighted_score = sum(
                score * weight for score, weight in zip(novelty_factors, weights)
            )

            return min(1.0, max(0.0, weighted_score))

        except Exception as e:
            logger.error(f"Error calculating semantic novelty: {e}")
            return 0.5  # Default moderate novelty

    def detect_new_metrics(self, query: str) -> bool:
        """Detect if query asks for new/uncommon metrics.

        Args:
            query: Query text to analyze

        Returns:
            True if query contains new metrics, False otherwise
        """
        try:
            query_lower = query.lower()

            # Extract potential metric words (nouns that could be measurements)
            words = re.findall(r"\b[a-z_]+\b", query_lower)

            # Filter out common non-metric words
            stop_words = {
                "the",
                "and",
                "or",
                "but",
                "in",
                "on",
                "at",
                "to",
                "for",
                "of",
                "with",
                "by",
                "from",
                "up",
                "about",
                "into",
                "through",
                "during",
                "before",
                "after",
                "above",
                "below",
                "between",
                "among",
                "what",
                "where",
                "when",
                "why",
                "how",
                "all",
                "any",
                "both",
                "each",
                "few",
                "more",
                "most",
                "other",
                "some",
                "such",
                "no",
                "nor",
                "not",
                "only",
                "own",
                "same",
                "so",
                "than",
                "too",
                "very",
                "can",
                "will",
                "just",
                "should",
                "now",
                "patients",
                "patient",
                "average",
                "count",
                "total",
                "median",
                "min",
                "max",
                "show",
                "get",
                "find",
                "list",
                "give",
                "tell",
                "is",
                "are",
                "was",
                "were",
                "have",
                "has",
                "had",
                "do",
                "does",
                "did",
            }

            potential_metrics = [
                word for word in words if word not in stop_words and len(word) > 2
            ]

            # Check if any potential metrics are not in known metrics
            for metric in potential_metrics:
                if (
                    metric not in self.common_metrics
                    and metric not in self._known_metrics
                ):
                    # Additional check: is it a medical-sounding term?
                    if self._is_medical_term(metric):
                        logger.info(f"Detected potential new metric: {metric}")
                        return True

            return False

        except Exception as e:
            logger.error(f"Error detecting new metrics: {e}")
            return False

    def _calculate_pattern_novelty(self, query: str) -> float:
        """Calculate novelty based on query patterns."""
        query_lower = query.lower()

        # Check for common patterns (low novelty)
        for pattern in self.common_patterns:
            if re.search(pattern, query_lower):
                return 0.2  # Very common pattern

        # Check for novel/complex patterns (high novelty)
        for pattern in self.novel_patterns:
            if re.search(pattern, query_lower):
                return 0.8  # Novel pattern

        # Check for multiple analysis types in one query (moderate novelty)
        analysis_keywords = [
            "average",
            "count",
            "total",
            "median",
            "min",
            "max",
            "compare",
            "correlation",
        ]
        found_keywords = sum(
            1 for keyword in analysis_keywords if keyword in query_lower
        )

        if found_keywords > 2:
            return 0.6  # Complex multi-analysis query
        elif found_keywords == 0:
            return 0.7  # Unclear analysis type
        else:
            return 0.4  # Standard single analysis

    def _calculate_metric_novelty(self, query: str) -> float:
        """Calculate novelty based on metrics mentioned."""
        if self.detect_new_metrics(query):
            return 0.9  # New metrics are highly novel

        query_lower = query.lower()

        # Count known metrics in query
        known_metric_count = sum(
            1 for metric in self.common_metrics if metric in query_lower
        )

        if known_metric_count == 0:
            return 0.6  # No clear metrics mentioned
        elif known_metric_count == 1:
            return 0.3  # Single common metric
        else:
            return 0.5  # Multiple metrics (moderate novelty)

    def _calculate_similarity_novelty(self, query: str) -> float:
        """Calculate novelty based on similarity to existing queries."""
        try:
            # Get recent feedback queries to compare against
            with _get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT question FROM assistant_feedback 
                    ORDER BY created_at DESC 
                    LIMIT 100
                """
                )
                recent_queries = [row[0] for row in cursor.fetchall()]

            if not recent_queries:
                return 0.8  # No previous queries, so this is novel

            # Calculate similarity to existing queries
            max_similarity = 0.0
            for prev_query in recent_queries:
                similarity = self.correction_service._calculate_query_similarity(
                    query, prev_query
                )
                max_similarity = max(max_similarity, similarity)

            # Convert similarity to novelty (inverse relationship)
            novelty = 1.0 - max_similarity
            return novelty

        except Exception as e:
            logger.error(f"Error calculating similarity novelty: {e}")
            return 0.5  # Default moderate novelty

    def _is_medical_term(self, term: str) -> bool:
        """Check if a term looks like a medical measurement."""
        # Simple heuristics for medical terms
        medical_suffixes = ["_level", "_count", "_rate", "_pressure", "_index"]
        medical_prefixes = ["blood_", "heart_", "body_"]

        # Check for medical-sounding patterns
        if any(term.endswith(suffix) for suffix in medical_suffixes):
            return True
        if any(term.startswith(prefix) for prefix in medical_prefixes):
            return True

        # Check for common medical abbreviations pattern (2-4 letters/digits)
        # But exclude common non-medical words
        common_words = {
            "the",
            "and",
            "for",
            "are",
            "you",
            "can",
            "had",
            "her",
            "was",
            "one",
            "our",
            "out",
            "day",
            "get",
            "has",
            "him",
            "his",
            "how",
            "man",
            "new",
            "now",
            "old",
            "see",
            "two",
            "way",
            "who",
            "boy",
            "did",
            "its",
            "let",
            "put",
            "say",
            "she",
            "too",
            "use",
            "data",
            "show",
            "tell",
            "give",
            "find",
            "list",
            "me",
        }
        if (
            len(term) >= 2
            and len(term) <= 4
            and term.isalnum()
            and term.lower() not in common_words
        ):
            return True

        return False

    def _load_known_metrics(self) -> Set[str]:
        """Load known metrics from database and patterns."""
        known_metrics = set(self.common_metrics)

        try:
            # Load metrics from correction service patterns
            patterns = self.correction_service.find_similar_patterns("", limit=100)
            for pattern in patterns:
                # Extract potential metrics from pattern queries
                words = re.findall(r"\b[a-z_]+\b", pattern.query_pattern.lower())
                for word in words:
                    if self._is_medical_term(word):
                        known_metrics.add(word)

            # Load from recent feedback queries
            with _get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT DISTINCT question FROM assistant_feedback 
                    ORDER BY created_at DESC 
                    LIMIT 200
                """
                )
                for (question,) in cursor.fetchall():
                    words = re.findall(r"\b[a-z_]+\b", question.lower())
                    for word in words:
                        if self._is_medical_term(word):
                            known_metrics.add(word)

        except Exception as e:
            logger.error(f"Error loading known metrics: {e}")

        return known_metrics

    def _load_known_patterns(self) -> List[str]:
        """Load known query patterns from database."""
        patterns = []

        try:
            # Load from correction service
            learned_patterns = self.correction_service.find_similar_patterns(
                "", limit=50
            )
            patterns.extend([p.query_pattern for p in learned_patterns])

            # Load from recent feedback
            with _get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT DISTINCT question FROM assistant_feedback 
                    WHERE rating = 'up'
                    ORDER BY created_at DESC 
                    LIMIT 100
                """
                )
                patterns.extend([row[0] for row in cursor.fetchall()])

        except Exception as e:
            logger.error(f"Error loading known patterns: {e}")

        return patterns

    def _normalize_query(self, query: str) -> str:
        """Normalize query for pattern matching."""
        # Convert to lowercase
        normalized = query.lower()

        # Remove punctuation except spaces
        normalized = re.sub(r"[^\w\s]", " ", normalized)

        # Normalize whitespace
        normalized = re.sub(r"\s+", " ", normalized).strip()

        # Remove common stop words for better pattern matching
        stop_words = {
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
        }
        words = normalized.split()
        filtered_words = [word for word in words if word not in stop_words]

        return " ".join(filtered_words)
