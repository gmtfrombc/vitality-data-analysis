#!/usr/bin/env python3
"""
Script to identify stale files in the codebase.

This script finds .md, .csv, .txt, and .json files that haven't been modified
in the last 10 days and are larger than 1KB, then generates a report.
"""

import os
import pathlib
import datetime
import re
from typing import List, Tuple


def is_stale_and_large(
    file_path: pathlib.Path, days_threshold: int = 5, min_size_kb: float = 0.1
) -> bool:
    """
    Check if file hasn't been modified for days_threshold days and is larger than min_size_kb.

    Args:
        file_path: Path to the file
        days_threshold: Number of days since last modification to consider stale
        min_size_kb: Minimum file size in KB to include

    Returns:
        True if the file meets the criteria, False otherwise
    """
    # Check if file exists
    if not file_path.exists():
        return False

    # Get last modified time
    mtime = file_path.stat().st_mtime
    mod_date = datetime.datetime.fromtimestamp(mtime)
    now = datetime.datetime.now()
    days_since_modified = (now - mod_date).days

    # Get file size in KB
    size_kb = file_path.stat().st_size / 1024

    # Return True if file is stale and large enough
    return days_since_modified >= days_threshold and size_kb >= min_size_kb


def estimate_purpose(file_path: pathlib.Path) -> str:
    """
    Estimate the purpose of a file based on its name and extension.

    Args:
        file_path: Path to the file

    Returns:
        String describing the estimated purpose
    """
    filename = file_path.name.lower()
    stem = file_path.stem.lower()
    extension = file_path.suffix.lower()
    parent = file_path.parent.name.lower()

    # Check for common patterns in filename
    if re.search(r"config|settings|conf", stem):
        return "Configuration"
    elif re.search(r"data|export|dataset", stem):
        return "Data export"
    elif re.search(r"log|report", stem):
        return "Log/Report"
    elif re.search(r"readme|guide|manual|doc", stem):
        return "Documentation"
    elif re.search(r"test|fixture", stem):
        return "Test data"
    elif re.search(r"backup|archive", stem):
        return "Backup/Archive"
    elif re.search(r"summary|overview", stem):
        return "Summary"
    elif re.search(r"schema|model", stem):
        return "Schema definition"
    elif re.search(r"sample|example", stem):
        return "Example data"

    # Check based on location
    if parent == "docs":
        return "Documentation"
    elif parent == "data":
        return "Data file"
    elif parent == "tests" or parent.startswith("test"):
        return "Test data"

    # Check based on extension
    if extension == ".md":
        return "Markdown document"
    elif extension == ".csv":
        return "CSV data"
    elif extension == ".json":
        return "JSON data"
    elif extension == ".txt":
        return "Text file"

    # Default
    return "Unknown purpose"


def find_stale_files(
    base_dir: pathlib.Path, days_threshold: int = 5, min_size_kb: float = 0.1
) -> List[Tuple[pathlib.Path, datetime.datetime, str]]:
    """
    Find stale files in the project directory.

    Args:
        base_dir: Base directory to search
        days_threshold: Number of days since last modification to consider stale
        min_size_kb: Minimum file size in KB to include

    Returns:
        List of tuples containing (file_path, mod_date, purpose)
    """
    stale_files = []

    # File extensions to include
    extensions = {".md", ".csv", ".txt", ".json"}

    # Debug counters
    total_files = 0
    venv_skipped = 0
    wrong_extension = 0
    too_recent = 0
    too_small = 0
    included = 0

    print(f"Searching in directory: {base_dir}")
    print(f"Looking for files not modified in the last {days_threshold} days")
    print(f"Looking for files larger than {min_size_kb} KB")
    print(f"Extensions considered: {', '.join(extensions)}")

    for path in base_dir.rglob("*"):
        if path.is_file():
            total_files += 1

            # Skip files in venv directory
            if "venv" in path.parts:
                venv_skipped += 1
                continue

            # Skip if not one of our target extensions
            if path.suffix.lower() not in extensions:
                wrong_extension += 1
                continue

            # Check modification time
            mtime = path.stat().st_mtime
            mod_date = datetime.datetime.fromtimestamp(mtime)
            now = datetime.datetime.now()
            days_since_modified = (now - mod_date).days

            if days_since_modified < days_threshold:
                too_recent += 1
                continue

            # Check file size in KB
            size_kb = path.stat().st_size / 1024
            if size_kb < min_size_kb:
                too_small += 1
                continue

            # File meets all criteria - add to list
            included += 1
            purpose = estimate_purpose(path)
            stale_files.append((path, mod_date, purpose))

    # Print debug information
    print("\nFile search statistics:")
    print(f"- Total files examined: {total_files}")
    print(f"- Files skipped (in venv): {venv_skipped}")
    print(f"- Files skipped (wrong extension): {wrong_extension}")
    print(f"- Files skipped (modified within {days_threshold} days): {too_recent}")
    print(f"- Files skipped (smaller than {min_size_kb} KB): {too_small}")
    print(f"- Files included in report: {included}")

    return stale_files


def write_markdown_report(
    stale_files: List[Tuple[pathlib.Path, datetime.datetime, str]],
    output_path: pathlib.Path,
    days_threshold: int,
    min_size_kb: float,
):
    """
    Write report of stale files to a markdown file.

    Args:
        stale_files: List of tuples containing (file_path, mod_date, purpose)
        output_path: Path to write the report
        days_threshold: Number of days threshold used for staleness
        min_size_kb: Minimum file size in KB used for filtering
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Stale Files Report\n\n")
        f.write("This report lists files that:\n")
        f.write(f"- Have not been modified in the last {days_threshold} days\n")
        f.write(f"- Are larger than {min_size_kb} KB in size\n")
        f.write("- Have extensions `.md`, `.csv`, `.txt`, or `.json`\n\n")

        if not stale_files:
            f.write("No stale files found matching the criteria.\n")
            return

        f.write(f"## Files Found ({len(stale_files)})\n\n")
        f.write("| File | Last Modified | Size | Estimated Purpose |\n")
        f.write("|------|--------------|------|-------------------|\n")

        # Sort by last modified date (oldest first)
        for file_path, mod_date, purpose in sorted(stale_files, key=lambda x: x[1]):
            # Get relative path
            rel_path = file_path.relative_to(pathlib.Path.cwd())

            # Format date
            date_str = mod_date.strftime("%Y-%m-%d")

            # Get size in KB
            size_kb = file_path.stat().st_size / 1024
            size_str = f"{size_kb:.1f} KB"

            # Write row
            f.write(f"| {rel_path} | {date_str} | {size_str} | {purpose} |\n")

        f.write("\n## Next Steps\n\n")
        f.write(
            "For each file in this list, consider one of the following actions:\n\n"
        )
        f.write(
            "1. **Archive** - Move to an archive folder if the data is no longer actively used but needs to be kept\n"
        )
        f.write("2. **Update** - Review and update if the content is still relevant\n")
        f.write("3. **Delete** - Remove if the file is no longer needed\n")
        f.write(
            "4. **Ignore** - Leave as-is if the file is intentionally unchanged\n\n"
        )

        f.write(
            "**Note:** This analysis does not automatically delete or modify any files. Review each file carefully before taking action.\n"
        )


def main():
    """Main function to run the script."""
    base_dir = pathlib.Path.cwd()
    output_path = base_dir / "docs" / "STALE_FILES_REPORT.md"

    # Use more inclusive criteria
    days_threshold = 5  # Less stale
    min_size_kb = 0.1  # Smaller files

    print(f"Searching for stale files in {base_dir}...")
    stale_files = find_stale_files(base_dir, days_threshold, min_size_kb)

    # Create docs directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Write the report
    write_markdown_report(stale_files, output_path, days_threshold, min_size_kb)
    print(f"Analysis complete. Found {len(stale_files)} stale files.")
    print(f"Results written to {output_path}")


if __name__ == "__main__":
    main()
