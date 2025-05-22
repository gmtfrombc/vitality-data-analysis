# 📝 AI Helper System Audit & Refactoring Plan

**Project:** Ask Anything AI Assistant Health App
**Focus:** Refactored `ai_helper` system (modularization, test stability, maintainability)

---

## 1. Architectural Assessment

### a. **Strengths of Current State**

* **Major functionality has been modularized:**

  * LLM interface, code generation, intent parsing, and (to some degree) narrative/results are in dedicated files.
* **Testing harness exists:**

  * Golden/tricky tests and use of stubs/patches indicate a strong foundation for future test-driven development.
* **Backward compatibility:**

  * The `app/ai_helper.py` wrapper supports gradual migration away from legacy patterns.

### b. **Current Pain Points & Fragility**

* **Circular dependencies and tight coupling**

  * Several modules (e.g., `intent_parser` ↔ `llm_interface`, `ai_helper` ↔ `code_generator`) import each other, often indirectly via helper or model classes.
  * Some shared constants and helpers are scattered, leading to import “spaghetti.”
* **Incomplete migration and code duplication**

  * Legacy methods (sometimes renamed) are still present in new modules.
  * There’s logic split between legacy and refactored modules (ex: two `get_query_intent` implementations).
  * The temporary wrapper (`app/ai_helper.py`) is a band-aid, not a solution.
* **Oversized/overloaded modules**

  * `code_generator.py` and, to a lesser extent, `ai_helper.py` and `intent_parser.py` contain too much logic for one file. This makes the codebase hard to reason about and refactor safely.
* **Test fragility**

  * Tests are “green” but heavily patch internal implementation details (esp. direct monkeypatching of private helpers or stubs). Any small change to code structure breaks tests.
  * Test stubs duplicate logic, making real regression detection hard.
* **Inconsistent error handling & fallback logic**

  * Some errors are caught and reported at the wrong layer, masking real root causes or letting unexpected data through.
  * LLM errors, config (API key) errors, and schema mismatches are handled in multiple inconsistent ways.
* **Configuration is scattered**

  * API keys, model choices, prompts, and offline/test modes are handled inconsistently and checked across multiple modules.
* **Dependency injection is minimal or non-existent**

  * Most modules instantiate their own dependencies (e.g., LLM client), making it hard to mock or substitute components for testing or new backends.

---

## 2. Code-Level Issues (with Examples)

### a. **Circular Dependencies**

* `ai_helper.py` and `code_generator.py` both import intent models from each other via helpers and utility modules.
* Test stubs sometimes patch private methods across modules, introducing hidden dependency chains.

### b. **Migration Incompleteness**

* Dual versions of methods: new-style (`app/utils/ai_helper.py`) and legacy (`app/ai_helper_original.py`).
* The wrapper file (`app/ai_helper.py`) exposes both, causing confusion about what’s “live.”

### c. **Oversized Modules**

* `code_generator.py` tries to cover every code generation strategy, test override, and special case.

  * Example: Hardcoded handlers for specific test cases embedded with “magic” values.

### d. **Test Integration**

* Tests such as `test_golden_query` and `test_tricky_pipeline` monkeypatch both high-level (`AIHelper`) and deep, private helpers (`_ask_llm`), making refactors risky.
* Tests “fix” code issues in-place, e.g., manually patching string replacements for known bugs.

### e. **Error Handling**

* Error handling logic (e.g., for LLM offline mode, JSON parse failures, API issues) is duplicated or scattered.

  * Sometimes a failure is reported as an error in `results`, sometimes as a fallback intent, and sometimes as a crash.

### f. **Configuration**

* API key and offline detection logic appears in multiple places (sometimes as `_OFFLINE_MODE` globals, sometimes as function calls).

---

## 3. Refactoring & Stabilization Plan

### **A. Immediate Cleanup (Sprint 1-2)**

1. **Remove legacy method duplication:**

   * Audit for all methods/classes with legacy and new versions (e.g., `get_query_intent`) and consolidate into a single canonical implementation.
   * Remove or quarantine `ai_helper_original.py` and clearly document any needed temporary references.
2. **Retire the wrapper (`app/ai_helper.py`)**

   * Update all imports to use the new, canonical locations (likely `app/utils/ai_helper.py`).
   * Remove “legacy compatibility” only after passing all tests.

### **B. Decouple Modules & Kill Circular Dependencies (Sprint 2-3)**

3. **Isolate shared constants, models, and interfaces**

   * Move things like `QueryIntent`, prompt templates, schema helpers, and config into their own dedicated modules (e.g., `app/models/query_intent.py`, `app/config.py`, `app/prompts/`).
   * Remove any cross-imports for these foundational pieces.
4. **Refactor `code_generator.py` into smaller, focused files**

   * Example split:

     * `codegen/basic.py` (simple SQL & aggregate generation)
     * `codegen/trend.py` (trend/time series logic)
     * `codegen/relative.py` (relative/complex window logic)
     * `codegen/test_overrides.py` (test-specific handlers, with hooks for monkeypatching)
   * Each file should expose a clear interface; high-level `generate_code(intent, schema)` orchestrates.

### **C. Modernize Error Handling & Configuration (Sprint 3-4)**

5. **Centralize error management**

   * Create a shared error type or exception hierarchy for all LLM, DB, and parse errors.
   * Ensure errors bubble up to the right level and are consistently logged/returned.
6. **Centralize configuration**

   * All environment variables, API keys, and feature flags should live in a single `config.py` or equivalent.
   * Only the config layer reads from env; everything else takes config as arguments.

### **D. Implement Dependency Injection and Test Improvements (Sprint 4+)**

7. **Use dependency injection for LLM, DB, and config**

   * Pass LLM clients and DB handlers as arguments or via lightweight dependency injection containers.
   * This makes it easy to substitute stubs/fakes/mocks in tests **without monkeypatching** private methods.
8. **Refactor tests for interface-level patching**

   * Tests should patch only the public interfaces (e.g., mock LLM client, mock DB) rather than private helpers.
   * Add fixtures to inject these dependencies and make it explicit what is being tested.

### **E. Migration & Documentation (Final Sprint)**

9. **Document new architecture**

   * Include clear module boundaries, public APIs, dependency graph, and test strategy.
   * Document config and environment requirements.
10. **De-risk migration**

    * Maintain a parallel branch or feature flags while switching legacy to new until regression suite is stable and tests no longer require hacks.

---

## 4. Example Concrete Steps (First Two Sprints)

### **Sprint 1: Remove Legacy, Centralize Models**

* Identify all legacy methods/classes still referenced.
* Move shared models and constants to `app/models/` or `app/core/`.
* Switch all imports to point at new modules.
* Quarantine/delete `ai_helper_original.py` (move to `archive/` if unsure).

### **Sprint 2: Split Code Generator & Kill Cross-Imports**

* Map which codegen logic belongs together; move to separate files.
* Create a lightweight `generate_code` orchestrator.
* Move test-specific overrides out of production code—replace with explicit test hooks.
* Run tests after each major move and refactor tests as you go.

---

## 5. Summary Table

| Priority | Task                                | Sprint |
| -------- | ----------------------------------- | ------ |
| High     | Remove legacy/duplicated logic      | 1      |
| High     | Centralize models/constants         | 1      |
| High     | Update all imports to new structure | 1      |
| High     | Split `code_generator.py`           | 2      |
| Med      | Remove wrapper file after migration | 2      |
| Med      | Centralize error/config handling    | 3      |
| Med      | Implement dependency injection      | 4      |
| Med      | Refactor test harness               | 4      |
| Med      | Document architecture and migration | 5      |

---

## 6. Closing Thoughts

* **Your architecture is headed in the right direction,** but legacy coupling, scattered config, and oversized modules are holding you back.
* **The biggest risk** is that “any change breaks tests”—this is fixable with interface-driven DI, focused test stubs, and better module boundaries.
* **Each recommended sprint is incremental:** you don’t need a rewrite—just staged, well-tested refactors and decoupling.

---

**If you need a more detailed implementation checklist for any one of these steps, or would like code examples for dependency injection or interface decoupling, just ask.**

Let your team know: you have a strong foundation, and a focused, incremental refactor will get you to robust, stable, and maintainable code—without another rewrite.
