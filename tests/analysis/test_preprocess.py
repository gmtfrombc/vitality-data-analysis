from app.utils.preprocess import preprocess_results_for_ai, validate_narrative
from app.utils.metric_reference import extract_metrics_from_text


def test_extract_metrics_from_text():
    """Test that metrics are correctly extracted from text."""
    query = "How does A1C compare to blood pressure?"
    metrics = extract_metrics_from_text(query)
    assert "a1c" in metrics
    assert "sbp" in metrics or "dbp" in metrics

    query = "What's the relationship between BMI and cholesterol?"
    metrics = extract_metrics_from_text(query)
    assert "bmi" in metrics
    assert "total_cholesterol" in metrics


def test_preprocess_results_for_ai():
    """Test that preprocessing adds reference ranges to results."""
    query = "Compare blood pressure values for patients with high vs. normal A1C"
    results = {
        "stats": {"high_a1c": {"sbp_mean": 130}, "normal_a1c": {"sbp_mean": 120}}
    }

    processed = preprocess_results_for_ai(results, query)

    # Should have added reference section
    assert "reference" in processed

    # Should include references for metrics in query
    assert "a1c" in processed["reference"]
    assert "sbp" in processed["reference"] or "dbp" in processed["reference"]


def test_validate_narrative_a1c():
    """Test that narrative validation corrects A1C thresholds."""
    query = "Compare metrics for patients with high A1C"
    results = {
        "reference": {
            "a1c": {
                "normal": {"min": None, "max": 5.6},
                "pre_diabetes": {"min": 5.7, "max": 6.4},
                "high": {"min": 6.5, "max": None},
            }
        }
    }

    narrative = "Patients with A1C above 6.5 showed worse outcomes."
    validated = validate_narrative(narrative, query, results)

    # Should replace "above 6.5" with category
    assert "above 6.5" not in validated
    assert "in the high range" in validated


def test_validate_narrative_blood_pressure():
    """Test that narrative validation corrects blood pressure thresholds."""
    query = "Compare metrics for patients with high blood pressure"
    results = {
        "reference": {
            "sbp": {
                "normal": {"min": 90, "max": 120},
                "elevated": {"min": 121, "max": 129},
                "high": {"min": 130, "max": None},
            }
        }
    }

    narrative = "Patients with systolic BP above 130 showed worse outcomes."
    validated = validate_narrative(narrative, query, results)

    # Should replace "above 130" with category
    assert "above 130" not in validated
    assert "in the high range" in validated


def test_validate_narrative_preserves_text():
    """Test that validation preserves text without thresholds."""
    query = "Show weight distribution"
    results = {}

    narrative = "The weight distribution shows a median of 180 pounds."
    validated = validate_narrative(narrative, query, results)

    # Should preserve original text
    assert validated == narrative
