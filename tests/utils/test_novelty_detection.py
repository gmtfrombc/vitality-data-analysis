"""Tests for novelty detection module."""

from unittest.mock import patch, MagicMock

from app.utils.novelty_detection import NoveltyDetector


class TestNoveltyDetector:
    """Test cases for NoveltyDetector class."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("app.utils.novelty_detection._get_conn"), patch.object(
            NoveltyDetector, "_load_known_metrics", return_value=set()
        ), patch.object(NoveltyDetector, "_load_known_patterns", return_value=[]):
            self.detector = NoveltyDetector()

    def test_novelty_detector_novel_pattern(self):
        """Test detection of novel query patterns."""
        # Test novel pattern
        novel_query = "correlation between new_metric and blood_pressure_variability"
        with patch.object(
            self.detector, "calculate_semantic_novelty", return_value=0.8
        ):
            assert self.detector.is_novel_query_pattern(novel_query, threshold=0.7)

        # Test known pattern
        known_query = "average bmi of patients"
        with patch.object(
            self.detector, "calculate_semantic_novelty", return_value=0.5
        ):
            assert not self.detector.is_novel_query_pattern(known_query, threshold=0.7)

        # Test edge case at threshold
        edge_query = "some query"
        with patch.object(
            self.detector, "calculate_semantic_novelty", return_value=0.7
        ):
            assert self.detector.is_novel_query_pattern(edge_query, threshold=0.7)

    def test_novelty_detector_known_pattern(self):
        """Test detection of known query patterns."""
        # Test common patterns
        common_queries = [
            "average bmi",
            "count of patients",
            "total weight",
            "median age",
            "patients with diabetes",
        ]

        for query in common_queries:
            novelty_score = self.detector._calculate_pattern_novelty(query)
            assert (
                novelty_score <= 0.5
            ), f"Common query '{query}' should have low novelty, got {novelty_score}"

    def test_novelty_detector_new_metrics(self):
        """Test detection of new metrics in queries."""
        # Test with new metric
        new_metric_query = "average xyz_level in patients"
        assert self.detector.detect_new_metrics(new_metric_query)

        # Test with known metric
        known_metric_query = "average bmi in patients"
        assert not self.detector.detect_new_metrics(known_metric_query)

        # Test with no clear metrics (but "data" might be detected as medical term)
        no_metric_query = "show me the information"
        assert not self.detector.detect_new_metrics(no_metric_query)

        # Test with medical-sounding abbreviation
        abbrev_query = "average xyz in patients"
        assert self.detector.detect_new_metrics(abbrev_query)

    def test_novelty_detector_semantic_novelty(self):
        """Test semantic novelty calculation."""
        # Mock the individual novelty calculation methods
        with patch.object(
            self.detector, "_calculate_pattern_novelty", return_value=0.6
        ), patch.object(
            self.detector, "_calculate_metric_novelty", return_value=0.8
        ), patch.object(
            self.detector, "_calculate_similarity_novelty", return_value=0.7
        ):

            novelty_score = self.detector.calculate_semantic_novelty("test query")

            # Expected: (0.6 * 0.4) + (0.8 * 0.3) + (0.7 * 0.3) = 0.24 + 0.24 + 0.21 = 0.69
            expected_score = (0.6 * 0.4) + (0.8 * 0.3) + (0.7 * 0.3)
            assert (
                abs(novelty_score - expected_score) < 0.01
            ), f"Expected {expected_score}, got {novelty_score}"

    def test_pattern_novelty_calculation(self):
        """Test pattern novelty calculation."""
        # Test common patterns (should have low novelty)
        common_patterns = ["average bmi", "count of patients", "total weight"]

        for pattern in common_patterns:
            score = self.detector._calculate_pattern_novelty(pattern)
            assert (
                score <= 0.3
            ), f"Common pattern '{pattern}' should have low novelty, got {score}"

        # Test novel patterns (should have high novelty)
        novel_patterns = [
            "correlation between bmi and glucose",
            "trend over time for weight",
            "predict future bmi",
        ]

        for pattern in novel_patterns:
            score = self.detector._calculate_pattern_novelty(pattern)
            assert (
                score >= 0.7
            ), f"Novel pattern '{pattern}' should have high novelty, got {score}"

        # Test complex multi-analysis queries
        complex_query = "average bmi and count patients and median weight"
        score = self.detector._calculate_pattern_novelty(complex_query)
        # This query contains "average" which matches a common pattern, so it gets low novelty
        assert (
            score <= 0.3
        ), f"Query with common pattern should have low novelty, got {score}"

    def test_metric_novelty_calculation(self):
        """Test metric novelty calculation."""
        # Test with new metrics
        with patch.object(self.detector, "detect_new_metrics", return_value=True):
            score = self.detector._calculate_metric_novelty("new metric query")
            assert score >= 0.8, f"New metrics should have high novelty, got {score}"

        # Test with known single metric
        single_metric_query = "average bmi"
        score = self.detector._calculate_metric_novelty(single_metric_query)
        assert (
            0.4 <= score <= 0.6
        ), f"Single known metric should have moderate novelty, got {score}"

        # Test with multiple known metrics
        multi_metric_query = "bmi and weight and height"
        score = self.detector._calculate_metric_novelty(multi_metric_query)
        assert (
            0.4 <= score <= 0.6
        ), f"Multiple metrics should have moderate novelty, got {score}"

        # Test with no clear metrics
        no_metric_query = "show me something"
        score = self.detector._calculate_metric_novelty(no_metric_query)
        assert (
            0.5 <= score <= 0.7
        ), f"No clear metrics should have moderate novelty, got {score}"

    @patch("app.utils.novelty_detection._get_conn")
    def test_similarity_novelty_calculation(self, mock_get_conn):
        """Test similarity-based novelty calculation."""
        # Mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        # Test with no previous queries
        mock_cursor.fetchall.return_value = []
        score = self.detector._calculate_similarity_novelty("test query")
        assert (
            score >= 0.7
        ), f"No previous queries should result in high novelty, got {score}"

        # Test with similar previous queries
        mock_cursor.fetchall.return_value = [("average bmi",), ("mean bmi",)]
        with patch.object(
            self.detector.correction_service,
            "_calculate_query_similarity",
            return_value=0.9,
        ):
            score = self.detector._calculate_similarity_novelty("average bmi")
            assert (
                score <= 0.2
            ), f"Very similar query should have low novelty, got {score}"

        # Test with dissimilar previous queries
        mock_cursor.fetchall.return_value = [("count patients",), ("total weight",)]
        with patch.object(
            self.detector.correction_service,
            "_calculate_query_similarity",
            return_value=0.1,
        ):
            score = self.detector._calculate_similarity_novelty("correlation analysis")
            assert (
                score >= 0.8
            ), f"Dissimilar query should have high novelty, got {score}"

    def test_medical_term_detection(self):
        """Test medical term detection."""
        # Test medical suffixes
        assert self.detector._is_medical_term("glucose_level")
        assert self.detector._is_medical_term("heart_rate")
        assert self.detector._is_medical_term("blood_pressure")

        # Test medical prefixes
        assert self.detector._is_medical_term("blood_glucose")
        assert self.detector._is_medical_term("heart_rhythm")
        assert self.detector._is_medical_term("body_temperature")

        # Test medical abbreviations
        assert self.detector._is_medical_term("bmi")
        assert self.detector._is_medical_term("sbp")
        assert self.detector._is_medical_term("a1c")

        # Test non-medical terms
        assert not self.detector._is_medical_term("the")
        assert not self.detector._is_medical_term("and")
        assert not self.detector._is_medical_term("patient")
        assert not self.detector._is_medical_term("verylongwordthatisnotmedical")

    def test_query_normalization(self):
        """Test query normalization."""
        # Test basic normalization
        query = "What is the average BMI?"
        normalized = self.detector._normalize_query(query)
        expected = "what is average bmi"
        assert normalized == expected, f"Expected '{expected}', got '{normalized}'"

        # Test punctuation removal
        query = "Show me the BMI, weight, and height!"
        normalized = self.detector._normalize_query(query)
        expected = "show me bmi weight height"
        assert normalized == expected, f"Expected '{expected}', got '{normalized}'"

        # Test stop word removal
        query = "the average of the BMI for the patients"
        normalized = self.detector._normalize_query(query)
        expected = "average bmi patients"
        assert normalized == expected, f"Expected '{expected}', got '{normalized}'"

    def test_error_handling(self):
        """Test error handling in novelty detection."""
        # Test with malformed query
        with patch.object(
            self.detector,
            "_calculate_pattern_novelty",
            side_effect=Exception("Test error"),
        ):
            score = self.detector.calculate_semantic_novelty("test query")
            assert score == 0.5, f"Expected default score on error, got {score}"

        # Test novel pattern check with error
        with patch.object(
            self.detector,
            "calculate_semantic_novelty",
            side_effect=Exception("Test error"),
        ):
            result = self.detector.is_novel_query_pattern("test query")
            assert result is True, "Should err on the side of requesting feedback"

        # Test new metrics detection with error
        with patch("re.findall", side_effect=Exception("Test error")):
            result = self.detector.detect_new_metrics("test query")
            assert (
                result is False
            ), "Should return False on error in new metrics detection"

    @patch("app.utils.novelty_detection._get_conn")
    def test_load_known_metrics(self, mock_get_conn):
        """Test loading of known metrics."""
        # Mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        # Mock feedback queries
        mock_cursor.fetchall.return_value = [
            ("average bmi of patients",),
            ("glucose level analysis",),
            ("heart rate monitoring",),
        ]

        # Mock correction service patterns
        mock_pattern = MagicMock()
        mock_pattern.query_pattern = "average xyz_level"

        with patch.object(
            self.detector.correction_service,
            "find_similar_patterns",
            return_value=[mock_pattern],
        ):
            metrics = self.detector._load_known_metrics()

            # Should include common metrics plus detected ones
            assert "bmi" in metrics
            assert "glucose" in metrics
            assert len(metrics) >= len(self.detector.common_metrics)

    @patch("app.utils.novelty_detection._get_conn")
    def test_load_known_patterns(self, mock_get_conn):
        """Test loading of known patterns."""
        # Mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        # Mock feedback queries
        mock_cursor.fetchall.return_value = [("average bmi",), ("count patients",)]

        # Mock correction service patterns
        mock_pattern = MagicMock()
        mock_pattern.query_pattern = "total weight"

        with patch.object(
            self.detector.correction_service,
            "find_similar_patterns",
            return_value=[mock_pattern],
        ):
            patterns = self.detector._load_known_patterns()

            assert "total weight" in patterns
            assert "average bmi" in patterns
            assert "count patients" in patterns
            assert len(patterns) >= 3
