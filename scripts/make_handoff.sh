#!/usr/bin/env bash
# Regenerate docs/HANDOFF_LATEST.md via the helper python script.
# Usage: ./scripts/make_handoff.sh

set -euo pipefail

python "$(dirname "$0")/create_handoff.py"

echo "📝  docs/HANDOFF_LATEST.md refreshed. Commit & push when ready." 