class AppError(Exception):
    """Base exception for application errors."""

    pass


class LLMError(AppError):
    """Exception raised for LLM-related errors (OpenAI, etc)."""

    pass


class IntentParseError(AppError):
    """Exception raised for intent parsing errors."""

    pass
