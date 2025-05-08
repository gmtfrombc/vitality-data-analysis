import sys
from pathlib import Path
import os
import importlib

# Ensure project root is on sys.path so pytest can find project modules
# Go up two levels from tests/conftest.py
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Force offline mode for ai_helper by removing OPENAI_API_KEY before modules import
os.environ.pop("OPENAI_API_KEY", None)

# You can add shared fixtures here later if needed

os.environ.setdefault("OPENAI_API_KEY", "dummy-test-key")

try:
    from app import ai_helper as _ai_helper
    _ai_helper._OFFLINE_MODE = False  # type: ignore[attr-defined]
except Exception:
    # If ai_helper not yet imported, set flag via importlib when it's loaded
    import builtins

    _orig_import = builtins.__import__

    def _patched_import(name, globals=None, locals=None, fromlist=(), level=0):
        mod = _orig_import(name, globals, locals, fromlist, level)
        if name == "app.ai_helper":
            try:
                mod._OFFLINE_MODE = False  # type: ignore[attr-defined]
            except Exception:
                pass
        return mod

    builtins.__import__ = _patched_import
