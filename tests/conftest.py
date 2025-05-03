import sys
from pathlib import Path

# Ensure project root is on sys.path so pytest can find project modules
# Go up two levels from tests/conftest.py
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# You can add shared fixtures here later if needed
