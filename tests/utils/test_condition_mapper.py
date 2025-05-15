"""Tests for the condition_mapper module."""

import pytest
import yaml
from unittest.mock import patch, mock_open

from app.utils.condition_mapper import ConditionMapper


@pytest.fixture
def mock_yaml_data():
    """Fixture providing mock data for tests."""
    return {
        "conditions": [
            {
                "canonical": "type_2_diabetes",
                "description": "Type 2 diabetes mellitus",
                "codes": ["E11.9", "E11.8"],
                "synonyms": ["type 2 diabetes", "t2dm"],
            },
            {
                "canonical": "hypertension",
                "description": "High blood pressure",
                "codes": ["I10"],
                "synonyms": ["high blood pressure", "htn"],
            },
            {
                "canonical": "obesity",
                "description": "Obesity",
                "codes": ["E66.9", "E66.8"],
                "synonyms": ["obese", "overweight"],
            },
        ]
    }


@pytest.fixture
def mock_mapper(mock_yaml_data):
    """Create a ConditionMapper with mock data."""
    with patch("builtins.open", mock_open()):
        with patch("yaml.safe_load", return_value=mock_yaml_data):
            return ConditionMapper("mock_file.yaml")


def test_init_with_default_file():
    """Test initialization with default file path."""
    with patch("os.path.dirname", return_value="/fake/path"):
        with patch("os.path.join", return_value="/fake/path/condition_mappings.yaml"):
            with patch("builtins.open", mock_open()) as mock_file:
                with patch("yaml.safe_load", return_value={"conditions": []}):
                    mapper = ConditionMapper()
                    mock_file.assert_called_once_with(
                        "/fake/path/condition_mappings.yaml", "r"
                    )


def test_load_mappings_success(mock_yaml_data):
    """Test successful loading of mappings."""
    with patch("builtins.open", mock_open()):
        with patch("yaml.safe_load", return_value=mock_yaml_data):
            mapper = ConditionMapper("test.yaml")

            # Check that mappings were loaded correctly
            assert len(mapper.mappings) == 3
            assert "type_2_diabetes" in mapper.mappings
            assert "hypertension" in mapper.mappings
            assert "obesity" in mapper.mappings

            # Check reverse mappings
            assert mapper.codes_to_canonical["E11.9"] == "type_2_diabetes"
            assert mapper.codes_to_canonical["I10"] == "hypertension"

            # Check term-to-canonical mappings
            assert mapper.term_to_canonical["t2dm"] == "type_2_diabetes"
            assert mapper.term_to_canonical["htn"] == "hypertension"


def test_load_mappings_file_error():
    """Test handling of file error when loading mappings."""
    with patch("builtins.open", side_effect=IOError("File not found")):
        with patch("logging.Logger.error") as mock_log:
            mapper = ConditionMapper("fake_file.yaml")
            assert len(mapper.mappings) == 0
            mock_log.assert_called_once()


def test_load_mappings_yaml_error():
    """Test handling of YAML parsing error."""
    with patch("builtins.open", mock_open()):
        with patch("yaml.safe_load", side_effect=yaml.YAMLError("Invalid YAML")):
            with patch("logging.Logger.error") as mock_log:
                mapper = ConditionMapper("bad_yaml.yaml")
                assert len(mapper.mappings) == 0
                mock_log.assert_called_once()


def test_load_mappings_empty_data():
    """Test handling of empty data."""
    with patch("builtins.open", mock_open()):
        with patch("yaml.safe_load", return_value={}):
            with patch("logging.Logger.warning") as mock_log:
                mapper = ConditionMapper("empty.yaml")
                assert len(mapper.mappings) == 0
                mock_log.assert_called_once()


def test_get_canonical_condition(mock_mapper):
    """Test getting canonical condition name from term."""
    # Test direct canonical name
    assert mock_mapper.get_canonical_condition("type_2_diabetes") == "type_2_diabetes"

    # Test synonym
    assert mock_mapper.get_canonical_condition("t2dm") == "type_2_diabetes"

    # Test case insensitivity
    assert mock_mapper.get_canonical_condition("T2DM") == "type_2_diabetes"

    # Test non-existent term
    assert mock_mapper.get_canonical_condition("non_existent") is None

    # Test empty input
    assert mock_mapper.get_canonical_condition("") is None
    assert mock_mapper.get_canonical_condition(None) is None


def test_get_icd_codes(mock_mapper):
    """Test getting ICD-10 codes for a condition."""
    # Test with canonical name
    assert set(mock_mapper.get_icd_codes("type_2_diabetes")) == {"E11.9", "E11.8"}

    # Test with synonym
    assert set(mock_mapper.get_icd_codes("t2dm")) == {"E11.9", "E11.8"}

    # Test with non-existent condition
    assert mock_mapper.get_icd_codes("non_existent") == []


def test_get_description(mock_mapper):
    """Test getting description for a condition."""
    assert mock_mapper.get_description("type_2_diabetes") == "Type 2 diabetes mellitus"
    assert mock_mapper.get_description("t2dm") == "Type 2 diabetes mellitus"
    assert mock_mapper.get_description("non_existent") == ""


def test_get_all_codes_as_sql_list(mock_mapper):
    """Test getting SQL formatted list of codes."""
    expected = "'E11.9', 'E11.8'"
    assert mock_mapper.get_all_codes_as_sql_list("type_2_diabetes") == expected
    assert mock_mapper.get_all_codes_as_sql_list("t2dm") == expected
    assert mock_mapper.get_all_codes_as_sql_list("non_existent") == ""


def test_should_ask_clarifying_question(mock_mapper):
    """Test should_ask_clarifying_question method."""
    # Mock get_canonical_condition to test each branch
    with patch.object(mock_mapper, "get_canonical_condition") as mock_get_canonical:
        # Known condition should not need clarification
        mock_get_canonical.return_value = "type_2_diabetes"
        assert mock_mapper.should_ask_clarifying_question("t2dm") is False

        # Unknown condition should need clarification if no OpenAI client
        mock_get_canonical.return_value = None
        mock_mapper.client = None
        assert mock_mapper.should_ask_clarifying_question("rare_disease") is True
