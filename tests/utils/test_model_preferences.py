"""
Tests for Model Preferences Management

Tests the model selection and persistence functionality for the Data Analysis Assistant.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch

from app.utils.model_preferences import (
    get_available_models,
    get_model_display_options,
    load_model_preference,
    save_model_preference,
    get_model_api_name,
    get_model_info,
    DEFAULT_MODEL,
    AVAILABLE_MODELS,
)


@pytest.fixture
def temp_preferences_file():
    """Create a temporary preferences file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = Path(f.name)

    # Patch the PREFERENCES_FILE constant
    with patch("app.utils.model_preferences.PREFERENCES_FILE", temp_path):
        yield temp_path

    # Clean up
    if temp_path.exists():
        temp_path.unlink()


class TestModelPreferences:
    """Test model preferences functionality."""

    def test_get_available_models(self):
        """Test getting available models."""
        models = get_available_models()

        assert isinstance(models, dict)
        assert "gpt-4" in models
        assert "gpt-3.5-turbo" in models

        # Verify structure
        for model_key, model_info in models.items():
            assert "display_name" in model_info
            assert "api_name" in model_info
            assert "description" in model_info
            assert "cost" in model_info

    def test_get_model_display_options(self):
        """Test getting model display options for dropdown."""
        options = get_model_display_options()

        assert isinstance(options, dict)
        assert len(options) == len(AVAILABLE_MODELS)

        # Verify mapping
        for display_name, model_key in options.items():
            assert model_key in AVAILABLE_MODELS
            assert AVAILABLE_MODELS[model_key]["display_name"] == display_name

    def test_load_model_preference_default(self, temp_preferences_file):
        """Test loading model preference when no file exists."""
        # Ensure file doesn't exist
        if temp_preferences_file.exists():
            temp_preferences_file.unlink()

        model = load_model_preference()
        assert model == DEFAULT_MODEL

    def test_save_and_load_model_preference(self, temp_preferences_file):
        """Test saving and loading model preferences."""
        # Save a preference
        result = save_model_preference("gpt-3.5-turbo")
        assert result is True

        # Load it back
        model = load_model_preference()
        assert model == "gpt-3.5-turbo"

        # Verify file contents
        with open(temp_preferences_file, "r") as f:
            data = json.load(f)
        assert data["preferred_model"] == "gpt-3.5-turbo"

    def test_save_invalid_model(self, temp_preferences_file):
        """Test saving an invalid model key."""
        result = save_model_preference("invalid-model")
        assert result is False

    def test_load_invalid_saved_model(self, temp_preferences_file):
        """Test loading when saved model is no longer available."""
        # Save invalid model directly to file
        with open(temp_preferences_file, "w") as f:
            json.dump({"preferred_model": "invalid-model"}, f)

        # Should return default
        model = load_model_preference()
        assert model == DEFAULT_MODEL

    def test_get_model_api_name(self):
        """Test getting API name for model keys."""
        assert get_model_api_name("gpt-4") == "gpt-4"
        assert get_model_api_name("gpt-3.5-turbo") == "gpt-3.5-turbo"

        # Invalid model should return default
        assert (
            get_model_api_name("invalid") == AVAILABLE_MODELS[DEFAULT_MODEL]["api_name"]
        )

    def test_get_model_info(self):
        """Test getting model information."""
        info = get_model_info("gpt-4")
        assert info is not None
        assert info["display_name"] == "ChatGPT 4.0 (Recommended)"
        assert info["api_name"] == "gpt-4"

        # Invalid model
        info = get_model_info("invalid")
        assert info is None

    def test_preferences_file_creation(self, temp_preferences_file):
        """Test that preferences file is created if it doesn't exist."""
        # Remove file only (can't remove system temp directory)
        if temp_preferences_file.exists():
            temp_preferences_file.unlink()

        # Save preference should create file
        result = save_model_preference("gpt-3.5-turbo")
        assert result is True
        assert temp_preferences_file.exists()

    def test_corrupted_preferences_file(self, temp_preferences_file):
        """Test handling of corrupted preferences file."""
        # Write invalid JSON
        with open(temp_preferences_file, "w") as f:
            f.write("invalid json content")

        # Should return default and not crash
        model = load_model_preference()
        assert model == DEFAULT_MODEL

    def test_preserve_other_preferences(self, temp_preferences_file):
        """Test that saving model preference preserves other settings."""
        # Create file with other preferences
        initial_prefs = {
            "preferred_model": "gpt-4",
            "other_setting": "value",
            "theme": "dark",
        }
        with open(temp_preferences_file, "w") as f:
            json.dump(initial_prefs, f)

        # Save new model preference
        save_model_preference("gpt-3.5-turbo")

        # Verify other settings are preserved
        with open(temp_preferences_file, "r") as f:
            prefs = json.load(f)

        assert prefs["preferred_model"] == "gpt-3.5-turbo"
        assert prefs["other_setting"] == "value"
        assert prefs["theme"] == "dark"
