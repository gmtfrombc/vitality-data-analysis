"""Online integration test that validates GPT-4 emits the V2 intent JSON schema.

Run only when both environment variables are present:
  • ONLINE_LLM_TESTS=1  – explicit opt-in so CI & normal dev runs stay offline.
  • OPENAI_API_KEY      – actual OpenAI credentials for real calls.

Example:
    $ ONLINE_LLM_TESTS=1 OPENAI_API_KEY=sk-... pytest -m online

The test reads natural-language prompts from *llm_prompts.yaml* and asserts
that *AIHelper.get_query_intent()* returns a valid *QueryIntent* instance.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from app.utils.ai_helper import AIHelper
from app.utils.query_intent import QueryIntent

# -----------------------------------------------------------------------------
# Skip logic – only run when explicitly requested *and* when key exists.
# -----------------------------------------------------------------------------
if os.getenv("ONLINE_LLM_TESTS") != "1":
    pytest.skip(
        "Set ONLINE_LLM_TESTS=1 to enable GPT integration tests",
        allow_module_level=True,
    )

if not os.getenv("OPENAI_API_KEY"):
    pytest.skip(
        "OPENAI_API_KEY missing – cannot call OpenAI API", allow_module_level=True
    )

pytestmark = pytest.mark.online  # Allows selecting via -m online


@pytest.fixture(scope="module")
def prompts() -> list[str]:  # noqa: D401 - fixture
    """Load natural-language prompts for validation."""
    prompts_path = Path(__file__).with_name("llm_prompts.yaml")
    with prompts_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_llm_intent_prompts(prompts: list[str]):
    """Ensure GPT returns parsable *QueryIntent* for each prompt."""
    helper = AIHelper()

    bad_cases: list[str] = []
    for prompt in prompts:
        intent = helper.get_query_intent(prompt)
        if not isinstance(intent, QueryIntent):
            bad_cases.append(prompt)
            continue
        # Extra sanity – ensure mandatory keys populated
        assert intent.analysis_type, "analysis_type blank"
        assert intent.target_field is not None, "target_field missing"

    if bad_cases:
        joined = "\n  – " + "\n  – ".join(bad_cases)
        pytest.fail(f"LLM failed to return valid intent for:{joined}")
