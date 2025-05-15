import pytest
import pandas as pd
from pandas.testing import assert_frame_equal

from app.utils.gap_report import get_condition_gap_report

# Mock data to be returned by query_dataframe
MOCK_PATIENT_DATA_OBESITY = pd.DataFrame(
    {"patient_id": [1, 2], "bmi": [32.5, 35.1], "date": ["2023-01-15", "2023-02-20"]}
)

MOCK_PATIENT_DATA_A1C = pd.DataFrame(
    {"patient_id": [3, 4], "a1c": [6.0, 7.2], "date": ["2023-03-10", "2023-04-05"]}
)

MOCK_EMPTY_DF_OBESITY = pd.DataFrame(columns=["patient_id", "bmi", "date"])
MOCK_EMPTY_DF_A1C = pd.DataFrame(columns=["patient_id", "a1c", "date"])


def test_get_condition_gap_report_obesity_active(mocker):
    """Test gap report for obesity with active_only=True."""
    mock_query_dataframe = mocker.patch(
        "app.utils.gap_report.query_dataframe",
        return_value=MOCK_PATIENT_DATA_OBESITY.copy(),
    )

    result_df = get_condition_gap_report("obesity", active_only=True)

    assert_frame_equal(result_df, MOCK_PATIENT_DATA_OBESITY)
    called_sql = mock_query_dataframe.call_args[0][0]

    assert "bmi >= 30" in called_sql
    assert "patients.active = 1" in called_sql
    assert "pmh_match" in called_sql
    assert "lower(pmh.condition) like '%obesity%'" in called_sql.lower()


def test_get_condition_gap_report_obesity_all_patients(mocker):
    """Test gap report for obesity with active_only=False."""
    mock_query_dataframe = mocker.patch(
        "app.utils.gap_report.query_dataframe",
        return_value=MOCK_PATIENT_DATA_OBESITY.copy(),
    )

    result_df = get_condition_gap_report("obesity", active_only=False)

    assert_frame_equal(result_df, MOCK_PATIENT_DATA_OBESITY)
    called_sql = mock_query_dataframe.call_args[0][0]

    assert "bmi >= 30" in called_sql
    assert "patients.active = 1" not in called_sql


def test_get_condition_gap_report_morbid_obesity(mocker):
    """Test gap report for morbid_obesity."""
    mock_query_dataframe = mocker.patch(
        "app.utils.gap_report.query_dataframe",
        return_value=MOCK_PATIENT_DATA_OBESITY.copy(),
    )

    result_df = get_condition_gap_report("morbid_obesity", active_only=False)

    # Assuming mock data is suitable
    assert_frame_equal(result_df, MOCK_PATIENT_DATA_OBESITY)
    called_sql = mock_query_dataframe.call_args[0][0]

    assert "bmi >= 40" in called_sql
    assert "lower(pmh.condition) like '%morbid obesity%'" in called_sql.lower()


def test_get_condition_gap_report_prediabetes(mocker):
    """Test gap report for prediabetes."""
    mock_query_dataframe = mocker.patch(
        "app.utils.gap_report.query_dataframe",
        return_value=MOCK_PATIENT_DATA_A1C.copy(),
    )

    result_df = get_condition_gap_report("prediabetes", active_only=False)

    assert_frame_equal(result_df, MOCK_PATIENT_DATA_A1C)
    called_sql = mock_query_dataframe.call_args[0][0]

    assert "metric_value >= 5.7 AND metric_value < 6.5" in called_sql
    assert "test_name = 'A1C'" in called_sql
    assert "lower(pmh.condition) like '%prediabetes%'" in called_sql.lower()


def test_get_condition_gap_report_type_2_diabetes(mocker):
    """Test gap report for type_2_diabetes."""
    mock_query_dataframe = mocker.patch(
        "app.utils.gap_report.query_dataframe",
        return_value=MOCK_PATIENT_DATA_A1C.copy(),
    )

    result_df = get_condition_gap_report("type_2_diabetes", active_only=True)

    assert_frame_equal(result_df, MOCK_PATIENT_DATA_A1C)
    called_sql = mock_query_dataframe.call_args[0][0]

    assert "metric_value >= 6.5" in called_sql
    assert "test_name = 'A1C'" in called_sql
    assert "patients.active = 1" in called_sql
    assert "lower(pmh.condition) like '%type 2 diabetes%'" in called_sql.lower()


def test_get_condition_gap_report_diabetes_alias(mocker):
    """Test gap report using an alias 'diabetes' for type_2_diabetes."""
    mock_query_dataframe = mocker.patch(
        "app.utils.gap_report.query_dataframe",
        return_value=MOCK_PATIENT_DATA_A1C.copy(),
    )

    result_df = get_condition_gap_report(
        "diabetes", active_only=False
    )  # 'diabetes' is an alias

    assert_frame_equal(result_df, MOCK_PATIENT_DATA_A1C)
    called_sql = mock_query_dataframe.call_args[0][0]

    assert "metric_value >= 6.5" in called_sql  # Check for Type 2 Diabetes criteria
    # Canonical name in SQL
    assert "lower(pmh.condition) like '%type 2 diabetes%'" in called_sql.lower()


def test_get_condition_gap_report_t2dm_alias(mocker):
    """Test gap report using an alias 't2dm' for type_2_diabetes."""
    mock_query_dataframe = mocker.patch(
        "app.utils.gap_report.query_dataframe",
        return_value=MOCK_PATIENT_DATA_A1C.copy(),
    )

    result_df = get_condition_gap_report(
        "t2dm", active_only=False
    )  # 't2dm' is an alias

    assert_frame_equal(result_df, MOCK_PATIENT_DATA_A1C)
    called_sql = mock_query_dataframe.call_args[0][0]

    assert "metric_value >= 6.5" in called_sql  # Check for Type 2 Diabetes criteria
    # Canonical name in SQL
    assert "lower(pmh.condition) like '%type 2 diabetes%'" in called_sql.lower()


def test_get_condition_gap_report_unsupported_condition(mocker):
    """Test gap report for an unsupported condition."""
    mocker.patch(
        "app.utils.gap_report.condition_mapper.get_canonical_condition",
        return_value="unknown_condition",
    )
    with pytest.raises(
        ValueError,
        match="Gap-report not supported for condition 'unknown_condition'. Supported:",
    ):
        get_condition_gap_report("unknown_condition")


def test_get_condition_gap_report_empty_results_obesity(mocker):
    """Test gap report when no obesity gaps are found."""
    mock_query_dataframe = mocker.patch(
        "app.utils.gap_report.query_dataframe",
        return_value=MOCK_EMPTY_DF_OBESITY.copy(),
    )

    result_df = get_condition_gap_report("obesity")

    assert result_df.empty
    assert list(result_df.columns) == ["patient_id", "bmi", "date"]


def test_get_condition_gap_report_empty_results_a1c(mocker):
    """Test gap report when no prediabetes gaps are found."""
    mock_query_dataframe = mocker.patch(
        "app.utils.gap_report.query_dataframe", return_value=MOCK_EMPTY_DF_A1C.copy()
    )

    result_df = get_condition_gap_report("prediabetes")

    assert result_df.empty
    assert list(result_df.columns) == ["patient_id", "a1c", "date"]


@pytest.mark.parametrize(
    "condition_name, metric_alias_expected, mock_data_in, expected_data_out",
    [
        ("obesity", "bmi", MOCK_PATIENT_DATA_OBESITY, MOCK_PATIENT_DATA_OBESITY),
        (
            "morbid_obesity",
            "bmi",
            MOCK_PATIENT_DATA_OBESITY,
            MOCK_PATIENT_DATA_OBESITY,
        ),  # Mock data may not be perfect for morbid
        ("prediabetes", "a1c", MOCK_PATIENT_DATA_A1C, MOCK_PATIENT_DATA_A1C),
        ("type_2_diabetes", "a1c", MOCK_PATIENT_DATA_A1C, MOCK_PATIENT_DATA_A1C),
    ],
)
def test_get_condition_gap_report_metric_alias(
    mocker, condition_name, metric_alias_expected, mock_data_in, expected_data_out
):
    """Test correct metric alias is used in output DataFrame and SQL."""
    mock_query_dataframe = mocker.patch(
        "app.utils.gap_report.query_dataframe", return_value=mock_data_in.copy()
    )

    result_df = get_condition_gap_report(condition_name)

    assert_frame_equal(result_df, expected_data_out)
    assert metric_alias_expected in result_df.columns

    called_sql = mock_query_dataframe.call_args[0][0]
    assert f"c.metric_value AS {metric_alias_expected}" in called_sql


def test_get_condition_gap_report_pmh_filter_logic(mocker):
    """Test the PMH filter SQL generation with and without mapped ICD-10 codes."""
    # Case 1: condition_mapper returns codes
    mock_get_canonical = mocker.patch(
        "app.utils.gap_report.condition_mapper.get_canonical_condition",
        return_value="obesity",
    )
    mock_get_codes = mocker.patch(
        "app.utils.gap_report.condition_mapper.get_all_codes_as_sql_list",
        return_value="'E66.0','E66.9'",
    )
    mock_query_df = mocker.patch(
        "app.utils.gap_report.query_dataframe",
        return_value=MOCK_EMPTY_DF_OBESITY.copy(),
    )

    get_condition_gap_report("obesity")

    sql_query_with_codes = mock_query_df.call_args[0][0]
    assert "lower(pmh.condition) like '%obesity%'" in sql_query_with_codes.lower()
    assert "pmh.code IN ('E66.0','E66.9')" in sql_query_with_codes
    # Check that OR connects the text and code conditions for PMH
    assert (
        "where lower(pmh.condition) like '%obesity%' or pmh.code in ('e66.0','e66.9')"
        in sql_query_with_codes.lower().replace("\n", " ")
    )

    # Case 2: condition_mapper returns no codes (None)
    mock_get_codes.return_value = None
    # Call again with new mock value for get_all_codes_as_sql_list
    get_condition_gap_report("obesity")

    sql_query_no_codes = mock_query_df.call_args[0][0]
    assert "lower(pmh.condition) like '%obesity%'" in sql_query_no_codes.lower()
    assert "pmh.code IN" not in sql_query_no_codes
    # Check that OR is not present if only text condition for PMH
    assert (
        "where lower(pmh.condition) like '%obesity%'"
        in sql_query_no_codes.lower().replace("\n", " ")
    )
    assert (
        " or "
        not in sql_query_no_codes.split("WHERE")[1]
        .split(")")[0]  # Convert "WHERE" to "where" if comparing against lowercased SQL
        .lower()
        if "where" in sql_query_no_codes.lower()
        else " or " not in sql_query_no_codes.split("WHERE")[1].split(")")[0]
    )

    # Case 3: condition_mapper returns empty string for codes
    mock_get_codes.return_value = ""
    get_condition_gap_report("obesity")

    sql_query_empty_str_codes = mock_query_df.call_args[0][0]
    assert "lower(pmh.condition) like '%obesity%'" in sql_query_empty_str_codes.lower()
    assert "pmh.code IN" not in sql_query_empty_str_codes
    assert (
        "where lower(pmh.condition) like '%obesity%'"
        in sql_query_empty_str_codes.lower().replace("\n", " ")
    )


def test_db_path_forwarded_to_query_dataframe(mocker):
    """Test that db_path parameter is correctly passed to query_dataframe."""
    mock_query_dataframe = mocker.patch(
        "app.utils.gap_report.query_dataframe",
        return_value=MOCK_EMPTY_DF_OBESITY.copy(),
    )
    custom_db_path = "test_db.sqlite"

    get_condition_gap_report("obesity", db_path=custom_db_path)

    # Check the kwargs of the call to query_dataframe
    _, called_kwargs = mock_query_dataframe.call_args
    assert "db_path" in called_kwargs
    assert called_kwargs["db_path"] == custom_db_path

    # Test with default db_path (None)
    get_condition_gap_report("obesity")  # db_path is None by default
    _, called_kwargs_default = mock_query_dataframe.call_args
    assert "db_path" in called_kwargs_default
    assert called_kwargs_default["db_path"] is None
