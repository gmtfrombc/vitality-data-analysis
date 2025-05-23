#!/usr/bin/env python3
"""
Script to identify unused Python files in the codebase.

This script analyzes the Python files in the codebase to find files that are
not imported by any other file and don't have a main function or
if __name__ == "__main__" block.
"""

import os
import ast
import pathlib
import re
from collections import defaultdict
from typing import Dict, List, Set, Tuple


def count_lines(file_path: pathlib.Path) -> int:
    """Count the number of lines in a file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def has_main_or_entry_point(file_path: pathlib.Path) -> bool:
    """Check if file has a main function or if __name__ == "__main__" block."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            tree = ast.parse(content, filename=file_path)

        # Check for def main()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "main":
                return True

        # Check for if __name__ == "__main__":
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                try:
                    condition = node.test
                    if (
                        isinstance(condition, ast.Compare)
                        and isinstance(condition.left, ast.Name)
                        and condition.left.id == "__name__"
                        and isinstance(condition.ops[0], ast.Eq)
                        and isinstance(condition.comparators[0], ast.Constant)
                        and condition.comparators[0].value == "__main__"
                    ):
                        return True
                except (AttributeError, IndexError):
                    continue

        # Check for typical Panel page patterns
        if re.search(r"def \w+_page\(\):", content):
            return True

        # Check for param.Parameterized classes, which are likely UI components
        if re.search(r"class \w+\(param\.Parameterized\):", content):
            return True

        return False
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return False


def get_imports(file_path: pathlib.Path) -> List[str]:
    """Extract all import statements from a file."""
    imports = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=file_path)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_path = node.module
                    imports.append(module_path)

        return imports
    except Exception as e:
        print(f"Error analyzing imports in {file_path}: {e}")
        return []


def find_python_files(base_dir: pathlib.Path) -> List[pathlib.Path]:
    """Find all Python files in the codebase excluding venv and test files."""
    py_files = []

    for path in base_dir.rglob("*.py"):
        # Skip files in venv directory
        if "venv" in path.parts:
            continue

        # Exclude test files and __init__.py files
        if path.name.startswith("test_") or path.name == "__init__.py":
            continue

        # Only include files under app/ directory
        if "app" in path.parts:
            py_files.append(path)

    return py_files


def check_string_references(
    file_path: pathlib.Path, py_files: List[pathlib.Path]
) -> Set[pathlib.Path]:
    """
    Check if a file is referenced by string in other files.
    This catches dynamic imports or module name references.
    """
    # Get module name and file name (without .py)
    file_stem = file_path.stem
    rel_path = file_path.relative_to(pathlib.Path.cwd())
    module_path = str(rel_path.with_suffix("")).replace("/", ".")

    referenced_by = set()

    # Check for string references in other files
    for other_file in py_files:
        if other_file == file_path:
            continue

        try:
            with open(other_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for module name references
            if re.search(
                rf'[\'"]({re.escape(file_stem)}|{re.escape(module_path)})[\'"]', content
            ):
                referenced_by.add(other_file)

            # Special case for pages in routing tables
            if "pages" in str(file_path) and re.search(
                rf'[\'"]({re.escape(file_stem)})[\'"]', content
            ):
                referenced_by.add(other_file)

        except Exception as e:
            print(f"Error checking string references in {other_file}: {e}")

    return referenced_by


def check_if_page_component(file_path: pathlib.Path) -> bool:
    """Check if a file is a Panel page component."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check if it's a Panel page
        if "import panel as pn" in content and "pn.extension" in content:
            return True

        # Check for Panel component class
        if re.search(r"class \w+\(.*\):", content) and "param.Parameterized" in content:
            return True

        # Check if there's a page-returning function
        if re.search(r"def \w+_page\(\):", content):
            return True

        # Check for "get_page" function
        if "def get_page(" in content:
            return True

        # Specific to this codebase, check if it's in the pages directory
        if "pages" in file_path.parts:
            return True

        return False
    except Exception as e:
        print(f"Error checking if {file_path} is a page component: {e}")
        return False


def build_import_graph(
    py_files: List[pathlib.Path],
) -> Dict[pathlib.Path, Set[pathlib.Path]]:
    """Build a graph of which files import which other files."""
    # Map of module name to path
    module_to_path = {}

    # First, build a mapping of module names to file paths
    for file_path in py_files:
        # Get the module name (relative to the repo root)
        rel_path = file_path.relative_to(pathlib.Path.cwd())
        module_name = str(rel_path.with_suffix("")).replace("/", ".")
        module_to_path[module_name] = file_path

        # Also map the short module name (just the filename) for local imports
        short_name = file_path.stem
        module_to_path[short_name] = file_path

    # Graph of which files import which
    imported_by = defaultdict(set)

    # Now analyze each file's imports
    for file_path in py_files:
        imports = get_imports(file_path)

        for imp in imports:
            # Handle partial imports like 'app.utils.plots'
            parts = imp.split(".")
            for i in range(len(parts)):
                partial = ".".join(parts[: i + 1])
                if partial in module_to_path:
                    imported_file = module_to_path[partial]
                    imported_by[imported_file].add(file_path)

    # Also check string references for dynamic imports
    for file_path in py_files:
        string_refs = check_string_references(file_path, py_files)
        imported_by[file_path].update(string_refs)

    return imported_by


def find_unused_files(base_dir: pathlib.Path) -> List[Tuple[pathlib.Path, int, str]]:
    """Find Python files that are not imported and don't have entry points."""
    unused_files = []

    py_files = find_python_files(base_dir)
    imported_by = build_import_graph(py_files)

    for file_path in py_files:
        line_count = count_lines(file_path)
        has_entry_point = has_main_or_entry_point(file_path)
        is_imported = file_path in imported_by and len(imported_by[file_path]) > 0
        is_page = check_if_page_component(file_path)

        # Skip page components - they're often loaded dynamically
        if is_page:
            continue

        reason = []
        if not is_imported:
            reason.append("not imported")
        if not has_entry_point:
            reason.append("no entry point")

        if not is_imported and not has_entry_point:
            unused_files.append((file_path, line_count, ", ".join(reason)))

    return unused_files


def write_markdown_report(
    unused_files: List[Tuple[pathlib.Path, int, str]], output_path: pathlib.Path
):
    """Write the results to a markdown file."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Potentially Unused Python Files\n\n")
        f.write(
            "This document lists Python files in the `app/` directory that are potentially unused in the codebase.\n"
        )
        f.write(
            "These files are not imported by any other file and don't have a main function or entry point.\n\n"
        )

        if not unused_files:
            f.write(
                "No unused files detected in the app/ directory. All files are either imported, contain entry points, or are UI components.\n\n"
            )
        else:
            f.write("| File | Line Count | Reason |\n")
            f.write("|------|------------|--------|\n")

            for file_path, line_count, reason in sorted(
                unused_files, key=lambda x: x[0]
            ):
                rel_path = file_path.relative_to(pathlib.Path.cwd())
                f.write(f"| {rel_path} | {line_count} | {reason} |\n")

        f.write("\n## Note on Analysis\n\n")
        f.write(
            "This analysis is based on static code analysis and may not capture all dynamic imports or advanced usage patterns.\n"
        )
        f.write(
            "Files listed here should be reviewed carefully before removing or archiving them.\n\n"
        )

        f.write("## Identification Criteria\n\n")
        f.write("A file is considered 'unused' if all of the following are true:\n")
        f.write(
            "1. It is not imported by any other file (directly or via string-based imports)\n"
        )
        f.write(
            '2. It does not contain a main() function or if __name__ == "__main__" block\n'
        )
        f.write("3. It is not a Panel UI component or page\n")
        f.write("4. It does not define a function with a _page() suffix\n\n")

        f.write(
            "The script specifically excludes test files (test_*.py) and __init__.py files from analysis.\n"
        )


def main():
    """Main function to run the script."""
    base_dir = pathlib.Path.cwd()
    output_path = base_dir / "docs" / "UNUSED_PYTHON_FILES.md"

    print(f"Analyzing Python files in {base_dir}...")
    unused_files = find_unused_files(base_dir)

    # Create docs directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    write_markdown_report(unused_files, output_path)
    print(f"Analysis complete. Found {len(unused_files)} potentially unused files.")
    print(f"Results written to {output_path}")


if __name__ == "__main__":
    main()
