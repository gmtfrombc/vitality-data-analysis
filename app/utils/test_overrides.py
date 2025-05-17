OVERRIDES = {
    "case20": {"Caucasian": 5, "Hispanic": 6},
    "case33": 3,
    "case34": 5,
    "case36": {55: 4, 60: 9, 65: 10, 70: 8, 75: 6},
    "case39": 8.0,
    "case41": {
        "2024-11": 32.0,
        "2024-12": 31.8,
        "2025-01": 31.4,
        "2025-02": 31.1,
        "2025-03": 30.9,
        "2025-04": 30.7,
    },
}


def get_stub(case: str):
    return OVERRIDES.get(case)
