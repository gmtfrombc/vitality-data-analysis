# app/config.py

import os
from dotenv import load_dotenv

# Load environment variables from .env (no-op if already loaded)
load_dotenv()

# --- OpenAI / LLM Settings ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4")  # Override in .env if needed

# --- Application Modes ---
OFFLINE_MODE = not bool(OPENAI_API_KEY) or os.getenv("OFFLINE_MODE", "0") == "1"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# --- Database/Storage Settings ---
# Main DB URL for SQLAlchemy or similar (used by app)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///patient_data.db")
# Override for direct SQLite path (used by legacy helpers)
MH_DB_PATH = os.getenv("MH_DB_PATH", "patient_data.db")
# Shared DB file for saved questions, logs, etc. (used by utils)
VP_DATA_DB = os.getenv(
    "VP_DATA_DB",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "patient_data.db"),
)

# --- Email/Notification Settings ---
SMTP_SERVER = os.getenv("SMTP_SERVER", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
NOTIFICATION_SENDER = os.getenv("NOTIFICATION_SENDER", "no-reply@example.com")

# --- Test/Feature Flags ---
ONLINE_LLM_TESTS = os.getenv("ONLINE_LLM_TESTS", "0") == "1"
HAPPY_PATH_TEST = os.getenv("HAPPY_PATH_TEST", "false").lower() == "true"
WEIGHT_CHANGE_SANDBOX_TEST = (
    os.getenv("WEIGHT_CHANGE_SANDBOX_TEST", "false").lower() == "true"
)

# --- Add any other future app config here ---
# For example:
# FEATURE_FLAG_X = os.getenv("FEATURE_FLAG_X", "off") == "on"

# Helper to print current config (for debugging, optional)


def print_config():
    print("OPENAI_API_KEY set:", bool(OPENAI_API_KEY))
    print("MODEL_NAME:", MODEL_NAME)
    print("OFFLINE_MODE:", OFFLINE_MODE)
    print("LOG_LEVEL:", LOG_LEVEL)
    print("DATABASE_URL:", DATABASE_URL)
    print("MH_DB_PATH:", MH_DB_PATH)
    print("VP_DATA_DB:", VP_DATA_DB)
    print("SMTP_SERVER:", SMTP_SERVER)
    print("SMTP_PORT:", SMTP_PORT)
    print("SMTP_USER set:", bool(SMTP_USER))
    print("NOTIFICATION_SENDER:", NOTIFICATION_SENDER)
    print("ONLINE_LLM_TESTS:", ONLINE_LLM_TESTS)
    print("HAPPY_PATH_TEST:", HAPPY_PATH_TEST)
    print("WEIGHT_CHANGE_SANDBOX_TEST:", WEIGHT_CHANGE_SANDBOX_TEST)


def get_mh_db_path() -> str:
    """Return the current MH_DB_PATH from the environment (for test overrides)."""
    return os.getenv("MH_DB_PATH", "patient_data.db")


def get_vp_data_db() -> str:
    """Return the current VP_DATA_DB from the environment (for test overrides)."""
    return os.getenv(
        "VP_DATA_DB",
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "..", "patient_data.db"
        ),
    )


def is_env_tricky_pipeline():
    return os.getenv("TEST_TRICKY_PIPELINE", "false").lower() == "true"


def get_env_case_number():
    return os.getenv("TEST_CASE_NUMBER")


def is_env_weight_trend():
    return os.getenv("TEST_WEIGHT_TREND", "false").lower() == "true"


def is_happy_path_test():
    return os.getenv("HAPPY_PATH_TEST", "false").lower() == "true"


def is_weight_change_sandbox_test():
    return os.getenv("WEIGHT_CHANGE_SANDBOX_TEST", "false").lower() == "true"


DEBUG_MODE = os.getenv("DEBUG", "0").lower() in ("true", "1", "yes", "y")

if __name__ == "__main__":
    print_config()
