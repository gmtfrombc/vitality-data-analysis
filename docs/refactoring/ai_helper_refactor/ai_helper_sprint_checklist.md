# 🛠️ Refactoring & Stabilization Plan: Sprint Checklist

---

## Sprint 1: Remove Legacy & Centralize Models

**Files likely involved:**

* `app/utils/ai_helper.py`

* `app/ai_helper.py`

* `app/ai_helper_original.py`

* `app/ai_helper_old.py`

* `app/ai_helper_backup.py`

* Any module with legacy logic or models/constants

* Any file importing shared models/constants (e.g., `QueryIntent`, `DateRange`, `Filter`)

**Sprint 1 Checklist:**

* [ ] Identify all legacy or backup files (e.g., `ai_helper_old.py`, `ai_helper_original.py`, `ai_helper_backup.py`).

* [ ] Scan the codebase and tests for any live imports or references to these legacy files.

* [ ] If a legacy file has **no active references**, move it to an `archive/` folder or delete it (if using version control).

* [ ] For any shared model or constant that is **actively used**, ensure it resides in a single canonical location (such as `app/models/` or `app/core/`).

* [ ] Update all code and tests to import shared models/constants from this canonical location.

* [ ] Ensure **no imports or direct references remain** to any legacy files.

* [ ] Run all tests and lint checks to confirm stability.

* [ ] Summarize files archived, imports updated, and confirm all code now uses only the new, canonical modules.

---

## **Sprint 2: Split Code Generator & Eliminate Cross-Imports**

**Files likely involved:**

* `app/utils/ai/code_generator.py`

* `app/utils/ai_helper.py`

* `app/utils/ai/intent_parser.py`

* Any new codegen submodules created (e.g., `codegen/basic.py`, `codegen/trend.py`)

* Related test files

* [ ] Map code generation logic into clear functional groups

* [ ] Move grouped logic into separate files (`codegen/basic.py`, `codegen/trend.py`, etc.)

* [ ] Create or update a lightweight orchestrator (e.g., `generate_code`)

* [ ] Move test-specific overrides/hooks out of production code

* [ ] Refactor cross-module imports to only use interfaces, not implementation details

* [ ] Run all tests and update any broken references as modules move

---

## **Sprint 3: Centralize Error Handling & Configuration**

**Files likely involved:**

* `app/utils/ai/llm_interface.py`

* `app/utils/ai_helper.py`

* `app/utils/ai/intent_parser.py`

* `app/utils/ai/code_generator.py`

* `app/config.py` (to be created if not present)

* Any module reading config or handling errors

* [ ] Design shared exception/error types (for LLM, DB, parse, etc.)

* [ ] Refactor modules to raise and handle only these errors

* [ ] Centralize all config/env var loading in `config.py`

* [ ] Refactor modules to accept config as arguments (not read env vars directly)

* [ ] Document all configuration options in one place

---

## **Sprint 4: Implement Dependency Injection & Test Improvements**

**Files likely involved:**

* `app/utils/ai_helper.py`

* `app/utils/ai/llm_interface.py`

* `app/db_query.py` (or wherever DB logic lives)

* All major test files

* Any module creating its own dependencies

* [ ] Refactor modules/classes to accept dependencies (LLM, DB, config) via constructor or parameters

* [ ] Implement or adopt a minimal DI container (optional, but useful)

* [ ] Update all tests to use mocks/stubs for public interfaces, not internals

* [ ] Remove monkeypatching of private helpers in tests

* [ ] Add/extend fixtures for test injection

* [ ] Verify coverage for all dependency scenarios

---

## **Sprint 5: Documentation & De-risk Migration**

**[x] Document new architecture, module boundaries, and dependency graph**
  - See updated `docs/design/ARCHITECTURE.md` for full details.

**[x] Add/extend public API docs for main classes/functions**
  - All major classes and public methods now have Google-style docstrings and usage examples.

**[x] Document all configuration/env requirements**
  - All environment variables and config options are now documented in the README, with reference to `app/config.py`.

**[x] Document test strategy and how to inject dependencies**
  - The README now documents test coverage, isolation, and DI usage in tests.

**[x] Maintain parallel branch/feature flag while migrating**
**[x] Remove legacy/compatibility code only after tests pass cleanly**
  - All legacy/compatibility code is now quarantined in `archive/`, and the migration checklist is complete.

---

### ✅ Completion Marker
- All documentation steps above are complete, up to date, and pushed.
- All tests green (see `final_test_results.txt`).
- Legacy/compat code removed or quarantined.
- Project ready for handoff, onboarding, or migration.
