"""Tests for the app.utils.sandbox module."""

import pytest
import pandas as pd
import numpy as np
from app.utils.sandbox import run_snippet, run_user_code, SandboxResult


def test_run_snippet_simple_value():
    """Test running a simple snippet that returns a scalar value."""
    code = """
# Simple scalar value
results = 42
"""
    result = run_snippet(code)
    assert result == 42


def test_run_snippet_pandas_series():
    """Test running a snippet that returns a pandas Series."""
    code = """
import pandas as pd
# Create a simple Series
results = pd.Series([1, 2, 3, 4, 5])
"""
    result = run_snippet(code)
    assert isinstance(result, pd.Series)
    assert len(result) == 5
    assert list(result) == [1, 2, 3, 4, 5]


def test_run_snippet_pandas_dataframe():
    """Test running a snippet that returns a pandas DataFrame."""
    code = """
import pandas as pd
# Create a simple DataFrame
results = pd.DataFrame({
    'A': [1, 2, 3],
    'B': [4, 5, 6]
})
"""
    result = run_snippet(code)
    assert isinstance(result, pd.DataFrame)
    assert result.shape == (3, 2)
    assert list(result.columns) == ["A", "B"]
    assert result["A"].tolist() == [1, 2, 3]


def test_run_snippet_dictionary():
    """Test running a snippet that returns a dictionary."""
    code = """
# Create a dictionary
results = {
    'name': 'Test',
    'value': 123,
    'items': [1, 2, 3]
}
"""
    result = run_snippet(code)
    assert isinstance(result, dict)
    assert result["name"] == "Test"
    assert result["value"] == 123
    assert result["items"] == [1, 2, 3]


def test_run_snippet_no_results_variable():
    """Test handling when snippet doesn't define a results variable."""
    code = """
# No results variable defined
x = 42
"""
    result = run_snippet(code)
    assert isinstance(result, dict)
    assert "error" in result
    assert "did not define a `results` variable" in result["error"]


def test_run_snippet_syntax_error():
    """Test handling of syntax errors in the snippet."""
    code = """
# This has a syntax error
if True
    results = 42
"""
    result = run_snippet(code)
    assert isinstance(result, dict)
    assert "error" in result
    assert (
        "expected ':'" in result["error"] or "invalid syntax" in result["error"].lower()
    )


def test_run_snippet_runtime_error():
    """Test handling of runtime errors in the snippet."""
    code = """
# This will raise a runtime error
x = 1 / 0
results = 42
"""
    result = run_snippet(code)
    assert isinstance(result, dict)
    assert "error" in result
    assert "division by zero" in result["error"].lower()


def test_run_snippet_with_whitelist_imports():
    """Test that whitelisted imports are allowed."""
    code = """
import pandas as pd
import numpy as np
import math
import json
import datetime
import os
import sys
import re

# Use some of them to ensure they're actually imported
results = {
    'pd_series': pd.Series([1, 2, 3]),
    'np_array': np.array([4, 5, 6]),
    'math_pi': math.pi,
    'current_dir': os.getcwd(),
    'date': datetime.datetime.now().isoformat(),
    'match': re.search(r'test', 'testing').group(0)
}
"""
    result = run_snippet(code)
    assert isinstance(result, dict)
    assert isinstance(result["pd_series"], pd.Series)
    assert isinstance(result["np_array"], np.ndarray)
    assert result["math_pi"] == pytest.approx(3.14159, 0.00001)
    assert isinstance(result["current_dir"], str)
    assert isinstance(result["date"], str)
    assert result["match"] == "test"


def test_run_snippet_blocked_import():
    """Test that non-whitelisted imports are blocked."""
    code = """
# Try to import a non-whitelisted module
import subprocess

# This should not execute
results = 42
"""
    result = run_snippet(code)
    assert isinstance(result, dict)
    assert "error" in result
    assert "blocked in sandbox" in result["error"]
    assert "subprocess" in result["error"]


def test_run_user_code_basic():
    """Test the new run_user_code API with a simple snippet."""
    code = """
# Simple calculation
results = 2 + 2
"""
    result = run_user_code(code)
    assert isinstance(result, SandboxResult)
    assert result.type == "scalar"
    assert result.value == 4


def test_run_user_code_types():
    """Test type detection in run_user_code."""
    # Test scalar result
    scalar_code = "results = 3.14"
    scalar_result = run_user_code(scalar_code)
    assert scalar_result.type == "scalar"
    assert scalar_result.value == 3.14

    # Test DataFrame result
    df_code = """
import pandas as pd
results = pd.DataFrame({'x': [1, 2, 3]})
"""
    df_result = run_user_code(df_code)
    assert df_result.type == "dataframe"
    assert isinstance(df_result.value, pd.DataFrame)
    assert "shape" in df_result.meta

    # Test Series result
    series_code = """
import pandas as pd
results = pd.Series([10, 20, 30])
"""
    series_result = run_user_code(series_code)
    assert series_result.type == "series"
    assert isinstance(series_result.value, pd.Series)
    assert "length" in series_result.meta

    # Test dict result
    dict_code = "results = {'a': 1, 'b': 2}"
    dict_result = run_user_code(dict_code)
    assert dict_result.type == "dict"
    assert dict_result.value == {"a": 1, "b": 2}
    assert "keys" in dict_result.meta


def test_run_user_code_error():
    """Test error handling in run_user_code."""
    error_code = """
# This will raise an error
x = [1, 2, 3]
results = x[10]  # Index out of range
"""
    result = run_user_code(error_code)
    assert result.type == "error"
    assert (
        "index out of range" in result.value.lower()
        or "out of bounds" in result.value.lower()
    )


def test_run_user_code_large_dataframe():
    """Test handling of excessively large DataFrames."""
    large_df_code = """
import pandas as pd
import numpy as np

# Create a DataFrame that exceeds the limit
results = pd.DataFrame(np.random.rand(1000, 1001))  # Just above 1,000,000 cell limit
"""
    result = run_user_code(large_df_code)
    assert result.type == "error"
    assert "dataframe too large" in result.value.lower()


def test_run_user_code_large_series():
    """Test handling of excessively large Series."""
    large_series_code = """
import pandas as pd
import numpy as np

# Create a Series that exceeds the limit
results = pd.Series(range(1100000))  # Above the 1,000,000 limit
"""
    result = run_user_code(large_series_code)
    assert result.type == "error"
    assert "series too large" in result.value.lower()


def test_long_running_code_timeout():
    """Test that long-running code is terminated with a timeout."""
    timeout_code = """
import time
# Sleep for longer than the timeout threshold
time.sleep(10)
results = "This should not be reached"
"""
    result = run_user_code(timeout_code)
    assert result.type == "error"
    assert "timed out" in result.value.lower()


def test_none_result():
    """Test handling of None results."""
    none_code = """
# Set results to None
results = None
"""
    result = run_user_code(none_code)
    assert result.type == "object"
    assert isinstance(result.value, dict)
    assert result.value == {}
