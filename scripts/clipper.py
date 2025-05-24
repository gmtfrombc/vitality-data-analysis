#!/usr/bin/env python3
"""
Run pytest inside the active venv, stream live output so you see the
progress bar immediately, then print a clipped failure block ready
to paste into Cursor.

Bound in VS Code to ⌘⇧⌃C via tasks.json.
"""

import subprocess
import sys
import re

CURSOR_PROMPT = (
    "\n📌 Prompt for Cursor agent:\n"
    "Fix the failing tests below. Stop only when pytest is green.\n"
)


def run_pytest_and_clip_output() -> None:
    # Use the Python that launched this script (inside venv)
    cmd = [sys.executable, "-m", "pytest", "--maxfail=20", "--tb=short", "-q"]

    # Start pytest and stream stdout line by line
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,  # line‐buffered
    )

    progress_lines: list[str] = []
    clipped_lines: list[str] = []
    capturing_failures = False

    assert proc.stdout is not None  # for type checkers
    for raw_line in proc.stdout:
        line = raw_line.rstrip("\n")

        # Echo every line immediately so you see progress live
        print(line)

        # Store dotted progress lines for reference (optional)
        if not capturing_failures and re.match(r"^[\.F]+.*\[\s*\d+%", line):
            progress_lines.append(line)
            continue

        # Detect the main FAILURES header
        if re.match(r"=+ FAILURES =+", line):
            capturing_failures = True
            clipped_lines.append(line)
            continue

        # Also capture the short summary block
        if capturing_failures and re.match(r"=+ short test summary info =+", line):
            clipped_lines.append(line)
            continue

        # Stop before warnings to avoid noise
        if capturing_failures and re.match(r"=+ warnings summary =+", line):
            break

        if capturing_failures:
            clipped_lines.append(line)

    proc.wait()

    if clipped_lines:
        # Print the summary block (without re-printing progress lines)
        print(CURSOR_PROMPT + "\n".join(clipped_lines))
    else:
        # All green -- just tell Cursor everything passed
        print("\n✅ All tests passed – nothing to fix.")


if __name__ == "__main__":
    run_pytest_and_clip_output()
