import pandas as pd
import pytest

from app.utils.date_helpers import normalize_date_series, normalize_date_strings


@pytest.mark.parametrize(
    "input_value,expected",
    [
        ("2025-05-10", "2025-05-10"),
        ("2025-05-10T14:30:00", "2025-05-10"),
        ("2025-05-10T14:30:00Z", "2025-05-10"),
        ("2025-05-10 14:30:00", "2025-05-10"),
        (pd.Timestamp("2025-05-10"), "2025-05-10"),
        (None, None),
        (pd.NaT, None),
        ("not a date", None),
    ],
)
def test_normalize_date_series_single(input_value, expected):
    """Each scalar value should be normalised independently to YYYY-MM-DD or None."""
    ser = normalize_date_series([input_value])
    assert ser.iloc[0] == expected


def test_normalize_date_series_mixed_list():
    """Mixed valid + invalid inputs preserve ordering and correctly set None."""
    inputs = [
        "2025-01-01",
        "bad",
        "2025-02-03T08:00:00Z",
        None,
        pd.Timestamp("2025-03-04 12:00"),
    ]
    expected = [
        "2025-01-01",
        None,
        "2025-02-03",
        None,
        "2025-03-04",
    ]

    result = normalize_date_series(inputs)
    assert list(result) == expected


def test_normalize_date_strings_alias():
    """Alias should point to the same implementation."""
    data = ["2025-07-15T00:00:00Z"]
    assert list(normalize_date_series(data)) == list(normalize_date_strings(data))
