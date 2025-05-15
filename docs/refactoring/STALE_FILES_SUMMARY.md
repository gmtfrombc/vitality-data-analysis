# Stale Files Summary and Recommendations

Based on the analysis in [STALE_FILES_REPORT.md](./STALE_FILES_REPORT.md), we've identified 73 files that haven't been modified recently and may be candidates for cleanup. This document provides recommendations for handling these files by category.

## Summary by Category

| Category | File Count | Recommendation |
|----------|------------|----------------|
| Test reports and logs | 24 | Archive in logs/archive directory |
| Documentation summaries | 29 | Consolidate into fewer, well-organized documents |
| Data files | 10 | Review and keep only what's needed for current functionality |
| Configuration files | 4 | Update or document purpose |
| Readme files | 6 | Update to reflect current project state |

## Detailed Recommendations

### Test Reports and Logs (24 files)

Most of these files are in the `logs/` directory and represent test runs from May 2025. Consider:

1. Creating a logs archive structure: `logs/archive/YYYY-MM/`
2. Moving older logs into this structure
3. Implementing log rotation to automatically clean up older logs

Example implementation:
```bash
mkdir -p logs/archive/2025-05
find logs -name "self_test_2025-05-*" -type d -mtime +7 -exec mv {} logs/archive/2025-05/ \;
```

### Documentation Summaries (29 files)

The `docs/` directory contains many `summary_*.md` files that appear to be separate pieces of documentation:

1. Review all summary files to identify which are still relevant
2. Consolidate related summaries into single, well-organized documents
3. Create a documentation index in `docs/README.md` to help navigate

For example, all data validation summaries could be combined into a single comprehensive document.

### Data Files (10 files)

Data files like `data_examples.json`, `mock_patients.json`, and others should be:

1. Evaluated for current relevance to the project
2. Documented for their purpose and usage
3. Moved to `data/examples/` if they're reference files but not actively used

### Configuration Files (4 files)

Files like `requirements.txt` are not modified often by design, but should be:

1. Reviewed to ensure dependencies are up to date
2. Documented to explain why specific versions are required
3. Tested periodically to verify they still work with current code

### README Files (6 files)

README files should always reflect the current state of the project:

1. Update `README.md` and `README_data_assistant.md` with latest information
2. Ensure they include setup instructions, usage examples, and contribution guidelines
3. Check that links and references are still valid

## Implementation Plan

1. Create an `archive/` folder for deprecated files that need to be preserved
2. Update all README files to reflect current project state
3. Consolidate related documentation into single, well-organized files
4. Implement automated log rotation for test runs
5. Document data files and configurations that are infrequently changed but important

This refactoring will help keep the codebase clean and maintainable while preserving important historical information in an organized way. 