#!/usr/bin/env python
"""Regenerate docs/HANDOFF_LATEST.md from latest summary + top of CHANGELOG.

Usage:
    python scripts/create_handoff.py

The script finds the highest-numbered `summary_testing_XXX.md`,
extracts its contents, grabs the `[Unreleased]` section of CHANGELOG
( until the first blank line after that header ) and writes/overwrites
`docs/HANDOFF_LATEST.md`.
"""
from __future__ import annotations

import re
from pathlib import Path
import datetime

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
# Updated to include the summary_testing subdirectory
SUMMARY_DIR = DOCS / "summary_testing"
CHANGELOG = ROOT / "CHANGELOG.md"

HANDOFF = DOCS / "HANDOFF_LATEST.md"

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def _latest_summary() -> Path | None:
    pattern = re.compile(r"summary_testing_(\d+)\.md")
    summaries = []
    # Look in the summary_testing directory
    for p in SUMMARY_DIR.glob("summary_testing_*.md"):
        m = pattern.match(p.name)
        if m:
            summaries.append((int(m.group(1)), p))
    if summaries:
        return sorted(summaries)[-1][1]
    return None


def _extract_unreleased(changelog: Path) -> str:
    txt = changelog.read_text(encoding="utf-8")
    start = txt.find("[Unreleased]")
    if start == -1:
        return ""
    # slice from start to first blank line after it
    rest = txt[start:].splitlines()
    collected = []
    for line in rest[1:]:
        if line.strip() == "":
            break
        collected.append(line)
    return "\n".join(collected)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------


def main() -> None:
    summary_path = _latest_summary()
    if summary_path is None:
        raise FileNotFoundError(
            "No summary_testing_*.md found in docs/summary_testing/"
        )

    summary_text = summary_path.read_text(encoding="utf-8")
    unreleased = _extract_unreleased(CHANGELOG)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    handoff = f"""# Handoff – Data-Validation Work-Stream\n\n_Last refreshed: {now}_\n\n---\n## Latest Sprint Summary\n\n{summary_text}\n\n---\n## Unreleased CHANGELOG (excerpt)\n\n{unreleased}\n\n---\n## Quick Links\n* Roadmap: `ROADMAP_CANVAS.md`\n* ChangeLog: `CHANGELOG.md`\n* Validation UI: `app/pages/data_validation.py`\n* Validation Engine: `app/utils/validation_engine.py`\n* Rule Seeder: `etl/seed_validation_rules.py`\n"""

    HANDOFF.write_text(handoff, encoding="utf-8")
    print(f"Updated {HANDOFF.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
