"""
LLM Interface Module

This module handles all direct interactions with the LLM APIs (like OpenAI).
It provides a clean interface for making LLM calls, handling retries, and
managing API-specific quirks.

Example:
    >>> from app.utils.ai.llm_interface import ask_llm
    >>> response = ask_llm("Summarize this data", "What is the average BMI?")
"""

import logging
from pathlib import Path
from app.config import OPENAI_API_KEY, OFFLINE_MODE
import logging.handlers
import json
from app.errors import LLMError

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

# Determine if we are running in offline/test mode (no API key)
_OFFLINE_MODE = OFFLINE_MODE


def ask_llm(
    prompt: str,
    query: str,
    model: str = "gpt-4",
    temperature: float = 0.3,
    max_tokens: int = 500,
    client=None,
    api_key=None,
):
    """
    Send prompt + query to the LLM and return the raw assistant content.

    In offline mode (e.g., during pytest when no OPENAI_API_KEY is set), this
    function raises ``LLMError`` immediately so callers can fallback to
    deterministic or template-based generation without waiting for network
    timeouts.

    Args:
        prompt (str): The system prompt to send to the LLM.
        query (str): The user query to send to the LLM.
        model (str, optional): The model to use (default: "gpt-4").
        temperature (float, optional): The temperature to use for generation (default: 0.3).
        max_tokens (int, optional): The maximum number of tokens to generate (default: 500).
        client (object, optional): Optional OpenAI client instance (for DI/testing).
        api_key (str, optional): Optional API key (for DI/testing).

    Returns:
        str: The raw text response from the LLM.

    Raises:
        LLMError: If in offline mode (no API key set) or API call fails.
    """
    if _OFFLINE_MODE:
        raise LLMError("LLM call skipped – offline mode (no API key)")

    # Allow DI of client or fallback to new client if not provided
    if client is None:
        from openai import OpenAI

        _api_key = api_key if api_key is not None else OPENAI_API_KEY
        client = OpenAI(api_key=_api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        logger.error("LLM API call failed: %s", e)
        raise LLMError(f"LLM API call failed: {e}") from e

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
    """
    Return whether we're running in offline mode (no API key).

    Returns:
        bool: True if offline mode is active, False otherwise.
    """
    return _OFFLINE_MODE


def generate_analysis_code(intent, data_schema, custom_prompt=None):
    """
    Generate Python code for analyzing data based on query intent.

    Args:
        intent: The structured intent representation
        data_schema: Schema of available data
        custom_prompt: Optional custom prompt to override default

    Returns:
        str: Generated Python code for analysis
    """
    if is_offline_mode():
        # Return a simple placeholder in offline mode
        return """
        # Offline mode - no LLM available
        import pandas as pd
        
        # Sample analysis code
        def analyze():
            return {"message": "Analysis code generation requires LLM. Running in offline mode."}
            
        results = analyze()
        """

    # Base system prompt
    base_prompt = f"""
    You are an expert Python developer specializing in data analysis. Generate executable Python code to analyze patient data based on the specified intent.

    The available data schema is:
    {json.dumps(data_schema, indent=2)}

    The code must use **only** the helper functions exposed in the runtime (e.g., `db_query.get_all_vitals()`, `db_query.get_all_scores()`, `db_query.get_all_patients()`).
    Do NOT read external CSV or Excel files from disk, and do NOT attempt internet downloads.

    The code should use pandas and should be clean, efficient, and well-commented **and MUST assign the final output to a variable named `results`**. The UI downstream expects this variable.

    Return only the Python code (no markdown fences) and ensure the last line sets `results`.

    Include proper error handling and make sure to handle edge cases like empty dataframes and missing values.
    """

    # Use custom prompt if provided
    system_prompt = custom_prompt if custom_prompt else base_prompt

    # Create intent payload
    if hasattr(intent, "model_dump"):
        intent_payload = json.dumps(intent.model_dump())
    elif hasattr(intent, "dict"):
        intent_payload = json.dumps(intent.dict())
    else:
        intent_payload = json.dumps(intent)

    # Generate code
    query = f"Generate Python code for this analysis intent: {intent_payload}"

    try:
        response = ask_llm(
            prompt=system_prompt,
            query=query,
            model="gpt-4",
            temperature=0.2,
            max_tokens=1000,
        )

        # Clean the response
        if "```python" in response:
            code = response.split("```python")[1].split("```")[0].strip()
        elif "```" in response:
            code = response.split("```")[1].split("```")[0].strip()
        else:
            code = response.strip()

        # Ensure results variable is defined
        if "results =" not in code:
            code += "\n\n# Ensure results variable exists\nif 'results' not in locals():\n    results = {'error': 'No results generated'}"

        return code

    except Exception as e:
        logger.error("Failed to generate analysis code: %s", e)
        return f"""
        # Error generating code: {str(e)}
        def analysis_error():
            return {{"error": "{str(e)}"}}
            
        results = analysis_error()
        """
