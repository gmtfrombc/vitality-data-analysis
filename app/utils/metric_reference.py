from pathlib import Path
import yaml
import functools


@functools.lru_cache
def get_reference() -> dict:
    """Return cached dict of clinical reference ranges.

    The data file lives at data/metric_reference.yaml.  We cache the parsed
    contents so callers can fetch it repeatedly without re-reading disk.
    """
    data_path = Path(__file__).resolve().parents[2] / "data" / "metric_reference.yaml"
    if not data_path.exists():
        raise FileNotFoundError(f"Reference range file not found: {data_path}")

    with data_path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@functools.lru_cache
def get_range(metric: str, category: str) -> dict | None:
    """Return the min/max range dict for a given metric and category.

    Args:
        metric: Metric key as defined in ``metric_reference.yaml`` (e.g. ``"a1c"``).
        category: Category label under that metric (e.g. ``"normal"``, ``"high"``).

    Returns:
        Dict with ``{"min": float|None, "max": float|None}`` or ``None`` if not found.
    """
    ref = get_reference()
    metric = metric.lower()
    if metric not in ref:
        return None

    cat_dict = ref[metric].get(category)
    if isinstance(cat_dict, dict):
        return cat_dict.copy()
    return None


def categorize_value(metric: str, value: float | int | None) -> str | None:
    """Categorise *value* according to reference ranges.

    The first matching category is returned in the order defined in the YAML file.

    Args:
        metric: Metric name (case-insensitive).
        value: Numeric value to categorise. If *None* returns *None*.

    Returns:
        Category string (e.g. ``"normal"``, ``"high"``) or ``None`` if no match.
    """
    if value is None:
        return None

    ref = get_reference()
    metric = metric.lower()
    if metric not in ref:
        return None

    # iterate preserving YAML order (PyYAML preserves order by default)
    for cat, bounds in ref[metric].items():
        if cat == "units":
            continue
        if not isinstance(bounds, dict):
            continue
        min_val = bounds.get("min")
        max_val = bounds.get("max")
        if (min_val is None or value >= min_val) and (
            max_val is None or value <= max_val
        ):
            return cat

    return None


def extract_metrics_from_text(text: str) -> list[str]:
    """Extract metric names mentioned in text by comparing with known metrics in reference.

    Args:
        text: String to search for metric mentions

    Returns:
        List of metric names found in the text
    """
    text = text.lower()
    ref = get_reference()

    # Create a list of all metrics and their common aliases
    metric_aliases = {
        "a1c": ["a1c", "hba1c", "hemoglobin a1c", "glycated hemoglobin"],
        "sbp": [
            "sbp",
            "systolic",
            "systolic bp",
            "systolic blood pressure",
            "blood pressure",
        ],
        "dbp": [
            "dbp",
            "diastolic",
            "diastolic bp",
            "diastolic blood pressure",
            "blood pressure",
        ],
        "bmi": ["bmi", "body mass index"],
        "weight": ["weight", "body weight"],
        "height": ["height"],
        "glucose": ["glucose", "blood glucose", "blood sugar"],
        "total_cholesterol": ["cholesterol", "total cholesterol"],
        "ldl": ["ldl", "ldl cholesterol", "low density lipoprotein"],
        "hdl": ["hdl", "hdl cholesterol", "high density lipoprotein"],
        "triglycerides": ["triglycerides", "trigs"],
        "apolipoprotein_b": ["apolipoprotein b", "apob"],
        "alt": ["alt", "alanine aminotransferase"],
        "ast": ["ast", "aspartate aminotransferase"],
        "phq9": ["phq9", "phq-9", "depression score", "depression screening"],
        "gad7": ["gad7", "gad-7", "anxiety score", "anxiety screening"],
        "vitality_score": ["vitality score", "vitality", "vs"],
        "heart_fit_score": ["heart fit score", "heart fitness", "vo2 max"],
    }

    # For each metric that's actually in our reference yaml, check if it's in the text
    found_metrics = []
    for metric, aliases in metric_aliases.items():
        if metric in ref and any(alias in text for alias in aliases):
            found_metrics.append(metric)

    return found_metrics
