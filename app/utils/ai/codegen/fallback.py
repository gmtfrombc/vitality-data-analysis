"""
fallback.py

Fallback code generation for unknown or unsupported analysis types.
"""


def generate_fallback_code(query, intent=None):
    """Generate fallback code for unknown/unsupported analysis types."""
    import json

    code = "# Fallback: Unable to confidently determine analysis intent\n"
    code += f"# Original query: {json.dumps(query)}\n"
    if intent is not None:
        try:
            if hasattr(intent, "model_dump"):
                intent_repr = intent.model_dump()
            elif hasattr(intent, "dict"):
                intent_repr = intent.dict()
            else:
                intent_repr = intent
            code += "# Parsed intent (low confidence):\n"
            code += "# " + json.dumps(intent_repr, indent=2) + "\n"
        except Exception:
            code += "# [Intent could not be serialized]\n"
    code += "import pandas as pd\n"
    code += "# TODO: Implement analysis logic for the query above.\n"
    code += "results = {'error': 'Unable to confidently generate analysis code for this query.'}\n"
    return code
