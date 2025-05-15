#!/usr/bin/env python3
"""
Script to generate a markdown tree representation of the project structure.

This script walks through the project directory recursively and generates a
markdown tree, excluding specified directories and file extensions.
"""

import pathlib
from typing import List, Set, Dict
import os


def generate_project_structure(
    root_dir: pathlib.Path,
    excluded_dirs: Set[str],
    excluded_extensions: Set[str],
    output_file: pathlib.Path,
    max_depth: int = None,
) -> None:
    """
    Generate a markdown tree representation of the project structure.

    Args:
        root_dir: The root directory to start from
        excluded_dirs: Set of directory names to exclude
        excluded_extensions: Set of file extensions to exclude
        output_file: Path to the output markdown file
        max_depth: Maximum depth to traverse (None for unlimited)
    """
    # Get the project name from the root directory
    project_name = root_dir.name

    # Dictionary to store directory structure
    structure: Dict[str, List] = {"type": "dir", "name": project_name, "children": []}

    # Walk the directory and build the structure
    _build_directory_structure(
        root_dir,
        structure,
        excluded_dirs,
        excluded_extensions,
        max_depth,
        current_depth=0,
    )

    # Write the structure to markdown file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# Project Structure: {project_name}\n\n")
        f.write(
            "This document provides an overview of the project's directory structure.\n\n"
        )
        f.write("## Directory Tree\n\n")
        f.write("```\n")
        _write_structure_as_markdown(structure, f)
        f.write("```\n\n")

        f.write("## Notes\n\n")
        f.write("_Excluded directories:_ ")
        f.write(", ".join(sorted(excluded_dirs)))
        f.write("\n\n")
        f.write("_Excluded file extensions:_ ")
        f.write(", ".join(sorted(excluded_extensions)))

        print(f"Project structure written to {output_file}")


def _build_directory_structure(
    current_dir: pathlib.Path,
    parent_structure: Dict,
    excluded_dirs: Set[str],
    excluded_extensions: Set[str],
    max_depth: int,
    current_depth: int,
) -> None:
    """
    Recursively build the directory structure.

    Args:
        current_dir: Current directory being processed
        parent_structure: Parent structure to add items to
        excluded_dirs: Set of directory names to exclude
        excluded_extensions: Set of file extensions to exclude
        max_depth: Maximum depth to traverse
        current_depth: Current depth in the traversal
    """
    # Check if we've reached max depth
    if max_depth is not None and current_depth > max_depth:
        return

    # Get all items in the current directory
    items = []

    # Process both directories and files in the path
    for item_path in sorted(current_dir.iterdir()):
        # Skip hidden items unless they are explicitly allowed
        if item_path.name.startswith(".") and item_path.name not in excluded_dirs:
            continue

        # Skip excluded directories
        if item_path.is_dir() and item_path.name in excluded_dirs:
            continue

        # Skip files with excluded extensions
        if item_path.is_file() and item_path.suffix in excluded_extensions:
            continue

        # Add the item to our list
        items.append(item_path)

    # Sort items: directories first, then files
    items.sort(key=lambda p: (0 if p.is_dir() else 1, p.name.lower()))

    # Process each item
    for item_path in items:
        if item_path.is_dir():
            # Create a new structure for this directory
            dir_structure = {"type": "dir", "name": item_path.name, "children": []}
            parent_structure["children"].append(dir_structure)

            # Recursively process this directory
            _build_directory_structure(
                item_path,
                dir_structure,
                excluded_dirs,
                excluded_extensions,
                max_depth,
                current_depth + 1,
            )
        else:
            # Add file to the structure
            parent_structure["children"].append(
                {"type": "file", "name": item_path.name}
            )


def _write_structure_as_markdown(structure: Dict, file, indent: str = "") -> None:
    """
    Write the structure as a markdown tree.

    Args:
        structure: The structure to write
        file: The file to write to
        indent: Current indentation
    """
    if structure["type"] == "dir":
        # Write directory name
        file.write(f"{indent}{structure['name']}/\n")

        # Write children with increased indentation
        for child in structure["children"]:
            _write_structure_as_markdown(child, file, indent + "  ")
    else:
        # Write file name
        file.write(f"{indent}{structure['name']}\n")


def main():
    """Main function to run the script."""
    # Define the root directory and output file
    root_dir = pathlib.Path.cwd()
    output_file = root_dir / "docs" / "PROJECT_STRUCTURE.md"

    # Ensure the output directory exists
    os.makedirs(output_file.parent, exist_ok=True)

    # Define excluded directories and extensions
    excluded_dirs = {
        ".git",
        ".ruff_cache",
        ".pytest_cache",
        "__pycache__",
        ".github",
        "venv",
        ".venv",
        "logs",
    }

    excluded_extensions = {".db", ".sh", ".env", ".exit"}

    print(f"Generating project structure for {root_dir}...")
    generate_project_structure(
        root_dir, excluded_dirs, excluded_extensions, output_file
    )


if __name__ == "__main__":
    main()
