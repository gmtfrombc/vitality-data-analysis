from app.utils.metric_reference import categorize_value, get_range


def test_categorize_value_a1c():
    """Categorisation of A1C values should align with reference ranges."""
    assert categorize_value("a1c", 5.5) == "normal"
    assert categorize_value("a1c", 6.6) == "high"
    assert categorize_value("a1c", 6.0) == "pre_diabetes"


def test_get_range():
    rng = get_range("sbp", "normal")
    assert rng["min"] == 90 and rng["max"] == 120
