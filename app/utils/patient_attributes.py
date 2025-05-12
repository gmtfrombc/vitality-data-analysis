"""Patient attribute definitions for the Metabolic Health Program.

This module centralizes all categorical patient attributes as Enum classes and display labels.
It establishes a single source of truth for attributes like gender, active status,
and health risk factors to reduce duplication and improve clarity throughout the codebase.
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Dict, Optional


class Gender(Enum):
    """Patient gender categories."""

    MALE = "M"
    FEMALE = "F"
    OTHER = "O"


class Active(Enum):
    """Patient program active status."""

    ACTIVE = 1
    INACTIVE = 0


class ETOH(Enum):
    """Patient alcohol consumption status."""

    YES = 1
    NO = 0


class Tobacco(Enum):
    """Patient tobacco use status."""

    YES = 1
    NO = 0


class GLP1Full(Enum):
    """Patient GLP-1 prescription status."""

    ON_GLP1 = 1
    NOT_ON_GLP1 = 0


class Ethnicity(Enum):
    """Patient ethnicity categories."""

    CAUCASIAN = "Caucasian"
    HISPANIC = "Hispanic"
    ASIAN = "Asian"
    AFRICAN_AMERICAN = "African American"
    OTHER = "Other"
    NOT_HISPANIC = "Not Hispanic or Latino"
    HISPANIC_LATINO = "Hispanic or Latino"


class AssessmentType(Enum):
    """Mental health assessment types."""

    PHQ9 = "PHQ-9"
    PHQ9_LOWER = "phq9"
    GAD7 = "GAD-7"
    GAD7_LOWER = "gad7"


class RiskLevel(Enum):
    """Risk level classifications from mental health assessments."""

    MINIMAL = "Minimal"
    MILD = "Mild"
    MODERATE = "Moderate"
    MODERATELY_SEVERE = "Moderately Severe"
    SEVERE = "Severe"


class ScoreType(Enum):
    """Types of scores tracked in the system."""

    VITALITY = "vitality_score"
    HEART_FIT = "heart_fit_score"


# Display labels for attributes
ATTRIBUTE_LABELS: Dict[str, Dict[Any, str]] = {
    "gender": {
        Gender.MALE.value: "Male",
        Gender.FEMALE.value: "Female",
        Gender.OTHER.value: "Other",
        "M": "Male",
        "F": "Female",
        "O": "Other",
    },
    "active": {
        Active.ACTIVE.value: "Active",
        Active.INACTIVE.value: "Inactive",
        1: "Active",
        0: "Inactive",
    },
    "etoh": {ETOH.YES.value: "Yes", ETOH.NO.value: "No", 1: "Yes", 0: "No"},
    "tobacco": {Tobacco.YES.value: "Yes", Tobacco.NO.value: "No", 1: "Yes", 0: "No"},
    "glp1_full": {
        GLP1Full.ON_GLP1.value: "On GLP-1",
        GLP1Full.NOT_ON_GLP1.value: "Not on GLP-1",
        1: "On GLP-1",
        0: "Not on GLP-1",
    },
    "ethnicity": {
        Ethnicity.CAUCASIAN.value: "Caucasian",
        Ethnicity.HISPANIC.value: "Hispanic",
        Ethnicity.ASIAN.value: "Asian",
        Ethnicity.AFRICAN_AMERICAN.value: "African American",
        Ethnicity.OTHER.value: "Other",
        Ethnicity.NOT_HISPANIC.value: "Not Hispanic or Latino",
        Ethnicity.HISPANIC_LATINO.value: "Hispanic or Latino",
    },
    "assessment_type": {
        AssessmentType.PHQ9.value: "PHQ-9 Depression Screening",
        AssessmentType.PHQ9_LOWER.value: "PHQ-9 Depression Screening",
        AssessmentType.GAD7.value: "GAD-7 Anxiety Screening",
        AssessmentType.GAD7_LOWER.value: "GAD-7 Anxiety Screening",
    },
    "risk_level": {
        RiskLevel.MINIMAL.value: "Minimal Risk",
        RiskLevel.MILD.value: "Mild Risk",
        RiskLevel.MODERATE.value: "Moderate Risk",
        RiskLevel.MODERATELY_SEVERE.value: "Moderately Severe Risk",
        RiskLevel.SEVERE.value: "Severe Risk",
    },
    "score_type": {
        ScoreType.VITALITY.value: "Vitality Score",
        ScoreType.HEART_FIT.value: "Heart Fitness Score",
    },
}


def label_for(field: str, value: Any) -> str:
    """Return the human-readable label for a field value.

    Args:
        field: The database field name (e.g., "gender", "active")
        value: The raw value stored in the database

    Returns:
        A user-friendly display label or the string representation of the value if not found
    """
    return ATTRIBUTE_LABELS.get(field, {}).get(value, str(value))


# Derived attributes based on multiple fields
def is_program_completer(active: int, provider_visits: Optional[int]) -> bool:
    """Check if a patient has completed the Metabolic Health Program.

    A program completer is defined as someone who:
    1. Is currently inactive (active=0)
    2. Has completed at least 7 provider visits

    Args:
        active: Active status (0=inactive, 1=active)
        provider_visits: Number of provider visits (or None if unknown)

    Returns:
        True if the patient meets the program completer criteria
    """
    if provider_visits is None:
        return False

    return active == Active.INACTIVE.value and provider_visits >= 7


def get_patient_status(
    active: int,
    provider_visits: Optional[int],
    program_start_date: Optional[str] = None,
) -> str:
    """Get a detailed description of patient program status.

    Args:
        active: Active status (0=inactive, 1=active)
        provider_visits: Number of provider visits
        program_start_date: ISO format date when patient started program (optional)

    Returns:
        A string describing the patient's current program status
    """
    if active == Active.ACTIVE.value:
        visits_text = f" ({provider_visits} visits)" if provider_visits else ""
        return f"Active{visits_text}"
    elif is_program_completer(active, provider_visits):
        return "Program Completer"
    else:
        return "Inactive (Discontinued)"
