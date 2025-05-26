"""Tests for confidence scoring module."""

from app.utils.confidence_scoring import ConfidenceScorer


class TestConfidenceScorer:
    """Test cases for ConfidenceScorer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scorer = ConfidenceScorer()

    def test_confidence_scorer_intent_confidence(self):
        """Test intent confidence scoring."""
        # Test high confidence intent
        high_confidence_intent = {
            "analysis_type": "average",
            "target_field": "bmi",
            "filters": [{"field": "age", "value": 30}],
            "conditions": [],
            "raw_query": "average bmi",
        }
        score = self.scorer.score_intent_confidence(high_confidence_intent)
        assert 0.7 <= score <= 1.0, f"Expected high confidence, got {score}"

        # Test low confidence intent
        low_confidence_intent = {
            "analysis_type": "unknown",
            "target_field": "unknown",
            "filters": [],
            "conditions": [],
            "raw_query": "something unclear",
        }
        score = self.scorer.score_intent_confidence(low_confidence_intent)
        assert 0.0 <= score <= 0.5, f"Expected low confidence, got {score}"

        # Test moderate confidence intent
        moderate_intent = {
            "analysis_type": "comparison",
            "target_field": "weight",
            "filters": [{"field": "gender", "value": "F"}],
            "conditions": [],
            "raw_query": "compare weight between groups",
        }
        score = self.scorer.score_intent_confidence(moderate_intent)
        assert 0.4 <= score <= 0.8, f"Expected moderate confidence, got {score}"

    def test_confidence_scorer_execution_success(self):
        """Test execution success scoring."""
        # Test successful execution with data
        success_results = {
            "data": [{"bmi": 25.0}, {"bmi": 27.0}, {"bmi": 23.0}],
            "summary": "Analysis completed successfully",
            "visualization": {"type": "histogram"},
            "execution_time": 2.5,
        }
        score = self.scorer.score_execution_success(success_results)
        assert 0.7 <= score <= 1.0, f"Expected high success score, got {score}"

        # Test failed execution with errors
        error_results = {
            "error": "Database connection failed",
            "data": None,
            "execution_time": 15.0,
        }
        score = self.scorer.score_execution_success(error_results)
        assert 0.0 <= score <= 0.3, f"Expected low success score, got {score}"

        # Test empty results
        empty_results = {}
        score = self.scorer.score_execution_success(empty_results)
        assert score == 0.1, f"Expected very low score for empty results, got {score}"

    def test_confidence_scorer_result_quality(self):
        """Test result quality scoring."""
        # Test high quality results
        high_quality_results = {
            "data": [{"bmi": i} for i in range(25)],  # Good amount of data
            "summary": "This is a comprehensive analysis of BMI data showing clear patterns and trends.",
            "visualization": {"type": "histogram", "data": "chart_data"},
            "statistics": {"mean": 25.0, "std": 3.2, "count": 25},
            "count": 25,
        }
        score = self.scorer.score_result_quality(high_quality_results)
        assert 0.7 <= score <= 1.0, f"Expected high quality score, got {score}"

        # Test low quality results
        low_quality_results = {
            "data": [],  # No data
            "summary": "",  # No summary
            "statistics": {"mean": float("nan")},  # Invalid stats
        }
        score = self.scorer.score_result_quality(low_quality_results)
        assert 0.0 <= score <= 0.4, f"Expected low quality score, got {score}"

        # Test moderate quality results
        moderate_results = {
            "data": [{"bmi": 25.0}],  # Little data
            "summary": "Brief summary",
            "visualization": None,
            "statistics": {"mean": 25.0},
        }
        score = self.scorer.score_result_quality(moderate_results)
        assert 0.3 <= score <= 0.7, f"Expected moderate quality score, got {score}"

    def test_confidence_scorer_overall_confidence(self):
        """Test overall confidence calculation."""
        query = "What is the average BMI?"

        intent = {"analysis_type": "average", "target_field": "bmi", "raw_query": query}

        results = {
            "data": [{"bmi": 25.0}, {"bmi": 27.0}],
            "summary": "Average BMI calculated",
            "execution_time": 1.0,
        }

        # Test with both intent and results
        score = self.scorer.calculate_overall_confidence(query, intent, results)
        assert 0.0 <= score <= 1.0, f"Score should be between 0 and 1, got {score}"
        assert score > 0.5, f"Expected decent confidence for clear query, got {score}"

        # Test with query only
        score_query_only = self.scorer.calculate_overall_confidence(query)
        assert (
            0.0 <= score_query_only <= 1.0
        ), f"Score should be between 0 and 1, got {score_query_only}"

        # Test with complex query
        complex_query = "Compare correlation between BMI and blood pressure"
        score_complex = self.scorer.calculate_overall_confidence(complex_query)
        assert (
            score_complex < score_query_only
        ), "Complex query should have lower confidence"

    def test_confidence_scorer_error_handling(self):
        """Test error handling in confidence scoring."""
        # Test with malformed intent
        malformed_intent = "not a dict"
        score = self.scorer.score_intent_confidence(malformed_intent)
        assert score == 0.5, f"Expected default score for malformed intent, got {score}"

        # Test with malformed results
        malformed_results = "not a dict"
        score = self.scorer.score_execution_success(malformed_results)
        assert (
            score == 0.5
        ), f"Expected default score for malformed results, got {score}"

        # Test with None inputs
        score = self.scorer.calculate_overall_confidence("test query", None, None)
        assert 0.0 <= score <= 1.0, f"Should handle None inputs gracefully, got {score}"

    def test_medical_field_recognition(self):
        """Test recognition of medical fields in intent scoring."""
        # Test with known medical field
        medical_intent = {
            "analysis_type": "average",
            "target_field": "glucose",
            "raw_query": "average glucose level",
        }
        medical_score = self.scorer.score_intent_confidence(medical_intent)

        # Test with unknown field
        unknown_intent = {
            "analysis_type": "average",
            "target_field": "unknown_field",
            "raw_query": "average unknown_field",
        }
        unknown_score = self.scorer.score_intent_confidence(unknown_intent)

        assert (
            medical_score > unknown_score
        ), "Medical fields should have higher confidence"

    def test_pattern_recognition(self):
        """Test query pattern recognition in confidence scoring."""
        # Test high confidence patterns
        high_confidence_intent = {
            "analysis_type": "average",
            "target_field": "bmi",
            "raw_query": "average bmi of patients",
        }
        high_score = self.scorer.score_intent_confidence(high_confidence_intent)

        # Test low confidence patterns
        low_confidence_intent = {
            "analysis_type": "correlation",
            "target_field": "bmi",
            "raw_query": "correlation between bmi and other factors",
        }
        low_score = self.scorer.score_intent_confidence(low_confidence_intent)

        assert (
            high_score > low_score
        ), "Simple patterns should have higher confidence than complex ones"
