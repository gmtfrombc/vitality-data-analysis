"""
Model Preferences Management

This module handles user preferences for LLM model selection, providing
persistence and default model management for the Data Analysis Assistant.

Features:
- Save/load user model preferences
- Default model fallback
- Available model definitions
- Preference persistence to local file
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Available models with their display names and API identifiers
AVAILABLE_MODELS = {
    "gpt-4": {
        "display_name": "ChatGPT 4.0 (Recommended)",
        "api_name": "gpt-4",
        "description": "Most capable model, better reasoning and accuracy",
        "cost": "Higher cost",
    },
    "gpt-3.5-turbo": {
        "display_name": "ChatGPT 3.5 Turbo (Testing)",
        "api_name": "gpt-3.5-turbo",
        "description": "Faster and more cost-effective for testing",
        "cost": "Lower cost",
    },
}

# Default model
DEFAULT_MODEL = "gpt-4"

# Preferences file location
PREFERENCES_FILE = Path(__file__).parent.parent.parent / "model_preferences.json"


def get_available_models() -> Dict[str, Dict[str, str]]:
    """Get the dictionary of available models.

    Returns:
        Dict mapping model keys to model information
    """
    return AVAILABLE_MODELS.copy()


def get_model_display_options() -> Dict[str, str]:
    """Get model options formatted for dropdown display.

    Returns:
        Dict mapping display names to model keys
    """
    return {
        info["display_name"]: model_key for model_key, info in AVAILABLE_MODELS.items()
    }


def load_model_preference() -> str:
    """Load the user's preferred model from file.

    Returns:
        The preferred model key, or DEFAULT_MODEL if none saved
    """
    try:
        if PREFERENCES_FILE.exists():
            with open(PREFERENCES_FILE, "r") as f:
                prefs = json.load(f)
                model = prefs.get("preferred_model", DEFAULT_MODEL)

                # Validate that the model is still available
                if model in AVAILABLE_MODELS:
                    # logger.info(f"Loaded model preference: {model}")
                    return model
                else:
                    logger.warning(
                        f"Saved model '{model}' no longer available, using default"
                    )

    except Exception as e:
        logger.warning(f"Failed to load model preferences: {e}")

    return DEFAULT_MODEL


def save_model_preference(model_key: str) -> bool:
    """Save the user's preferred model to file.

    Args:
        model_key: The model key to save as preferred

    Returns:
        True if saved successfully, False otherwise
    """
    if model_key not in AVAILABLE_MODELS:
        logger.error(f"Invalid model key: {model_key}")
        return False

    try:
        # Ensure directory exists
        PREFERENCES_FILE.parent.mkdir(exist_ok=True)

        # Load existing preferences or create new
        prefs = {}
        if PREFERENCES_FILE.exists():
            try:
                with open(PREFERENCES_FILE, "r") as f:
                    prefs = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load existing preferences: {e}")
                prefs = {}

        # Update model preference
        prefs["preferred_model"] = model_key

        # Save to file
        with open(PREFERENCES_FILE, "w") as f:
            json.dump(prefs, f, indent=2)

        # logger.info(f"Saved model preference: {model_key}")
        return True

    except Exception as e:
        logger.error(f"Failed to save model preference: {e}")
        return False


def get_model_api_name(model_key: str) -> str:
    """Get the API name for a model key.

    Args:
        model_key: The model key

    Returns:
        The API name for the model, or DEFAULT_MODEL if invalid
    """
    if model_key in AVAILABLE_MODELS:
        return AVAILABLE_MODELS[model_key]["api_name"]
    else:
        logger.warning(f"Invalid model key '{model_key}', using default")
        return AVAILABLE_MODELS[DEFAULT_MODEL]["api_name"]


def get_model_info(model_key: str) -> Optional[Dict[str, str]]:
    """Get full information for a model.

    Args:
        model_key: The model key

    Returns:
        Model information dict, or None if invalid
    """
    return AVAILABLE_MODELS.get(model_key)
