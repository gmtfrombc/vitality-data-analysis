import time

from app.pages.data_validation import DataValidationPage


def test_patient_list_refresh_is_cached():
    """Second load of patient list should be faster due to cache."""
    page = DataValidationPage()

    # Clear any cache populated during __init__
    page._patient_list_cache.clear()

    # First load – executes SQL
    start = time.perf_counter()
    page._load_patient_list()
    first_duration = time.perf_counter() - start

    # Second load – should hit cache
    start = time.perf_counter()
    page._load_patient_list()
    second_duration = time.perf_counter() - start

    # Allow small fluctuations but expect ≥ 30 % speed-up
    assert second_duration <= first_duration * 0.7 + 0.001, (
        f"Caching ineffective: first={first_duration:.4f}s second={second_duration:.4f}s"
    )
