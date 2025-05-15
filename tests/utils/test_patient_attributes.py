"""Tests for app.utils.patient_attributes."""

from __future__ import annotations


from app.utils.patient_attributes import (
    Gender,
    Active,
    ETOH,
    Tobacco,
    GLP1Full,
    AssessmentType,
    RiskLevel,
    ScoreType,
    label_for,
    is_program_completer,
    get_patient_status,
)


class TestEnumValues:
    """Test to verify enum values align with database schema."""

    def test_gender_enum(self):
        """Test gender enum values."""
        assert Gender.MALE.value == "M"
        assert Gender.FEMALE.value == "F"
        assert Gender.OTHER.value == "O"

    def test_active_enum(self):
        """Test active enum values."""
        assert Active.ACTIVE.value == 1
        assert Active.INACTIVE.value == 0

    def test_etoh_enum(self):
        """Test ETOH enum values."""
        assert ETOH.YES.value == 1
        assert ETOH.NO.value == 0

    def test_tobacco_enum(self):
        """Test tobacco enum values."""
        assert Tobacco.YES.value == 1
        assert Tobacco.NO.value == 0

    def test_glp1_full_enum(self):
        """Test GLP1Full enum values."""
        assert GLP1Full.ON_GLP1.value == 1
        assert GLP1Full.NOT_ON_GLP1.value == 0

    def test_assessment_type_enum(self):
        """Test AssessmentType enum values."""
        assert AssessmentType.PHQ9.value == "PHQ-9"
        assert AssessmentType.PHQ9_LOWER.value == "phq9"
        assert AssessmentType.GAD7.value == "GAD-7"
        assert AssessmentType.GAD7_LOWER.value == "gad7"

    def test_risk_level_enum(self):
        """Test RiskLevel enum values."""
        assert RiskLevel.MINIMAL.value == "Minimal"
        assert RiskLevel.MILD.value == "Mild"
        assert RiskLevel.MODERATE.value == "Moderate"
        assert RiskLevel.MODERATELY_SEVERE.value == "Moderately Severe"
        assert RiskLevel.SEVERE.value == "Severe"

    def test_score_type_enum(self):
        """Test ScoreType enum values."""
        assert ScoreType.VITALITY.value == "vitality_score"
        assert ScoreType.HEART_FIT.value == "heart_fit_score"


class TestLabelFor:
    """Test the label_for helper function."""

    def test_label_for_gender(self):
        """Test gender labels."""
        assert label_for("gender", "M") == "Male"
        assert label_for("gender", "F") == "Female"
        assert label_for("gender", "O") == "Other"
        # Test using enum value directly
        assert label_for("gender", Gender.MALE.value) == "Male"

    def test_label_for_active(self):
        """Test active status labels."""
        assert label_for("active", 1) == "Active"
        assert label_for("active", 0) == "Inactive"
        # Test using enum value directly
        assert label_for("active", Active.ACTIVE.value) == "Active"

    def test_label_for_ethnicity(self):
        """Test ethnicity labels."""
        assert label_for("ethnicity", "Caucasian") == "Caucasian"
        assert label_for("ethnicity", "Hispanic") == "Hispanic"
        assert (
            label_for("ethnicity", "Not Hispanic or Latino") == "Not Hispanic or Latino"
        )

    def test_label_for_boolean_fields(self):
        """Test boolean field labels."""
        assert label_for("etoh", 1) == "Yes"
        assert label_for("etoh", 0) == "No"
        assert label_for("tobacco", 1) == "Yes"
        assert label_for("tobacco", 0) == "No"
        assert label_for("glp1_full", 1) == "On GLP-1"
        assert label_for("glp1_full", 0) == "Not on GLP-1"

    def test_label_for_assessment_type(self):
        """Test assessment type labels."""
        assert label_for("assessment_type", "PHQ-9") == "PHQ-9 Depression Screening"
        assert label_for("assessment_type", "phq9") == "PHQ-9 Depression Screening"
        assert label_for("assessment_type", "GAD-7") == "GAD-7 Anxiety Screening"
        assert label_for("assessment_type", "gad7") == "GAD-7 Anxiety Screening"

    def test_label_for_risk_level(self):
        """Test risk level labels."""
        assert label_for("risk_level", "Minimal") == "Minimal Risk"
        assert label_for("risk_level", "Mild") == "Mild Risk"
        assert label_for("risk_level", "Moderate") == "Moderate Risk"
        assert label_for("risk_level", "Moderately Severe") == "Moderately Severe Risk"
        assert label_for("risk_level", "Severe") == "Severe Risk"

    def test_label_for_score_type(self):
        """Test score type labels."""
        assert label_for("score_type", "vitality_score") == "Vitality Score"
        assert label_for("score_type", "heart_fit_score") == "Heart Fitness Score"

    def test_label_for_missing(self):
        """Test handling of missing or unknown values."""
        assert label_for("gender", "X") == "X"  # Unknown gender code
        assert label_for("nonexistent_field", "value") == "value"  # Unknown field


class TestDerivedAttributes:
    """Test derived attribute functions."""

    def test_is_program_completer(self):
        """Test program completer logic."""
        # Active patients are never completers
        assert not is_program_completer(Active.ACTIVE.value, 10)

        # Inactive with enough visits = completer
        assert is_program_completer(Active.INACTIVE.value, 7)
        assert is_program_completer(Active.INACTIVE.value, 8)

        # Inactive with not enough visits = not completer
        assert not is_program_completer(Active.INACTIVE.value, 6)

        # Handle None provider_visits
        assert not is_program_completer(Active.INACTIVE.value, None)

    def test_get_patient_status(self):
        """Test patient status text generation."""
        # Active patients
        assert get_patient_status(Active.ACTIVE.value, 3) == "Active (3 visits)"
        assert get_patient_status(Active.ACTIVE.value, None) == "Active"

        # Program completer
        assert get_patient_status(Active.INACTIVE.value, 7) == "Program Completer"
        assert get_patient_status(Active.INACTIVE.value, 10) == "Program Completer"

        # Discontinued
        assert get_patient_status(Active.INACTIVE.value, 5) == "Inactive (Discontinued)"
        assert get_patient_status(Active.INACTIVE.value, 0) == "Inactive (Discontinued)"
        assert (
            get_patient_status(Active.INACTIVE.value, None) == "Inactive (Discontinued)"
        )


class TestHelperFunctions:
    """Test helper functions in the patient_attributes module."""

    def test_label_for_function(self):
        """Test the label_for function."""
        assert label_for("gender", Gender.MALE.value) == "Male"
        assert label_for("gender", Gender.FEMALE.value) == "Female"
        assert label_for("gender", Gender.OTHER.value) == "Other"
        assert label_for("active", Active.ACTIVE.value) == "Active"
        assert label_for("active", Active.INACTIVE.value) == "Inactive"
        assert label_for("tobacco", Tobacco.YES.value) == "Yes"
        assert label_for("tobacco", Tobacco.NO.value) == "No"

    def test_db_query_usage(self):
        """Test that the label_for function works as expected in db_query.py."""
        from app.utils.patient_attributes import Active, ETOH, Tobacco, GLP1Full

        # Create a mock demographics dictionary to simulate patient data
        demographics = {
            "active": Active.ACTIVE.value,
            "etoh": ETOH.YES.value,
            "tobacco": Tobacco.NO.value,
            "glp1_full": GLP1Full.ON_GLP1.value,
        }

        # Create the formatted_bools dictionary the same way db_query does
        bool_fields = {
            "active": Active,
            "etoh": ETOH,
            "tobacco": Tobacco,
            "glp1_full": GLP1Full,
        }

        formatted_bools = {}
        for field, enum_class in bool_fields.items():
            if field in demographics:
                value = demographics.get(field, 0)
                formatted_bools[enum_class.__name__] = label_for(field, value)

        # Verify the formatted values
        assert formatted_bools["Active"] == "Active"
        assert formatted_bools["ETOH"] == "Yes"
        assert formatted_bools["Tobacco"] == "No"
        assert formatted_bools["GLP1Full"] == "On GLP-1"
