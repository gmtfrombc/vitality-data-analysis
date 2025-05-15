# Potentially Unused Python Files

This document lists Python files in the `app/` directory that are potentially unused in the codebase.
These files are not imported by any other file and don't have a main function or entry point.

| File | Line Count | Reason |
|------|------------|--------|
| app/utils/advanced_correlation.py | 389 | not imported, no entry point |
| app/utils/auto_viz_mapper.py | 256 | not imported, no entry point |
| app/utils/db_connector.py | 64 | not imported, no entry point |
| app/utils/helpers.py | 97 | not imported, no entry point |
| app/utils/schema_cache.py | 97 | not imported, no entry point |
| app/utils/validation_startup.py | 125 | not imported, no entry point |

## Note on Analysis

This analysis is based on static code analysis and may not capture all dynamic imports or advanced usage patterns.
Files listed here should be reviewed carefully before removing or archiving them.

## Identification Criteria

A file is considered 'unused' if all of the following are true:
1. It is not imported by any other file (directly or via string-based imports)
2. It does not contain a main() function or if __name__ == "__main__" block
3. It is not a Panel UI component or page
4. It does not define a function with a _page() suffix

The script specifically excludes test files (test_*.py) and __init__.py files from analysis.
