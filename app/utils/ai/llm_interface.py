"""
LLM Interface Module

This module handles all direct interactions with the LLM APIs (like OpenAI).
It provides a clean interface for making LLM calls, handling retries, and
managing API-specific quirks.
"""

import os
import logging
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import logging.handlers

# Configure logging
log_format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
logger = logging.getLogger("llm_interface")
logger.setLevel(logging.DEBUG)

# Ensure we log to a dedicated file
log_dir = Path(__file__).resolve().parent.parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file_path = log_dir / "ai_trace.log"

if not any(
    isinstance(h, logging.FileHandler) and h.baseFilename == str(log_file_path)
    for h in logger.handlers
):
    file_handler = logging.handlers.RotatingFileHandler(
        log_file_path, maxBytes=1_000_000, backupCount=3
    )
    file_handler.setFormatter(logging.Formatter(log_format))
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

# Load environment variables
load_dotenv()

# Initialize OpenAI API client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Determine if we are running in offline/test mode (no API key)
_OFFLINE_MODE = not bool(os.getenv("OPENAI_API_KEY"))


def ask_llm(
    prompt: str,
    query: str,
    model: str = "gpt-4",
    temperature: float = 0.3,
    max_tokens: int = 500,
):
    """Send prompt + query to the LLM and return the raw assistant content.

    In offline mode (e.g., during pytest when no OPENAI_API_KEY is set), this
    function raises ``RuntimeError`` immediately so callers can fallback to
    deterministic or template-based generation without waiting for network
    timeouts.

    Args:
        prompt: The system prompt to send to the LLM
        query: The user query to send to the LLM
        model: The model to use (default: "gpt-4")
        temperature: The temperature to use for generation (default: 0.3)
        max_tokens: The maximum number of tokens to generate (default: 500)

    Returns:
        The raw text response from the LLM

    Raises:
        RuntimeError: If in offline mode (no API key set)
    """
    if _OFFLINE_MODE:
        raise RuntimeError("LLM call skipped – offline mode (no API key)")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": query},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # Log token usage if present (helps with cost debugging)
    if hasattr(response, "usage") and response.usage:
        logger.info(
            "LLM tokens -> prompt: %s, completion: %s, total: %s",
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            response.usage.total_tokens,
        )

    return response.choices[0].message.content


def is_offline_mode() -> bool:
    """Return whether we're running in offline mode (no API key)."""
    return _OFFLINE_MODE
