# app/reference_ranges.py

REFERENCE_RANGES = {
    "glucose_level": (70, 99),  # mg/dL
    "a1c": (4.0, 5.6),  # %
    "total_cholesterol": (0, 200),  # mg/dL
    "ldl": (0, 100),  # mg/dL
    "hdl": (40, 999),  # mg/dL
    "triglycerides": (0, 150),  # mg/dL
    "sbp": (90, 120),  # mmHg
    "dbp": (60, 80),  # mmHg
    "bmi": (18.5, 24.9),  # kg/m²
    # BMI clinical/action thresholds
    "bmi_overweight": 25,  # Overweight threshold
    "bmi_obese": 30,  # Obesity threshold
    "bmi_morbid_obesity": 40,  # Morbid obesity threshold
    # BMI outlier/sanity checks
    "bmi_min": 12,  # Physiologic lower bound for adults
    "bmi_max": 70,  # Physiologic upper bound for adults
    # A1C diagnostic thresholds
    "a1c_prediabetes_min": 5.7,  # Prediabetes minimum
    "a1c_prediabetes_max": 6.4,  # Prediabetes maximum (upper bound < 6.5)
    "a1c_diabetes_min": 6.5,  # Diabetes diagnostic minimum
    # Extend as needed
}


def get_reference_range(measure):
    """Return (low, high) reference range tuple or None."""
    return REFERENCE_RANGES.get(measure)


def flag_abnormal(value, measure):
    """Return True if value is out of reference range for measure."""
    rng = get_reference_range(measure)
    if rng is None or value is None:
        return False
    low, high = rng
    return value < low or value > high
