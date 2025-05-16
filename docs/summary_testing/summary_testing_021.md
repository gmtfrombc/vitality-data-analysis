# Testing Session 021 – 2025-05-22

## Objective
Validate newly-implemented weight-change intent heuristic and relative change analysis in the live sandbox environment.

## Runtime Failure Observed
```
2025-05-14 20:52:10,275 - WARNING - Sandbox execution failed: Import of 'copy' is blocked in sandbox (only [...])
```
* The generated snippet from `_generate_relative_change_analysis_code` executes `from copy import deepcopy` to clone the intent object.
* The sandbox import-guard intentionally blocks the `copy` standard-library module (only whitelisted modules are allowed). As a result the snippet fails and the assistant falls back to the rule-engine, producing an incomplete / inaccurate answer.

## What We Tried
1. **Expanded Unit Tests** – All tests (incl. new weight-change tests) pass because they bypass the sandbox.
2. **Manual Query Replay** – Confirmed failure only occurs inside the sandbox runner.
3. **Log Inspection** – Verified that no other missing imports or SQL errors occur; the stack trace stops at the blocked import.

## Root Cause
Sandbox security policy excludes the `copy` module. The new analysis code relies on `deepcopy` for cloning the `QueryIntent` instance before mutation.

## Recommended Next Steps
1. **Eliminate `copy` Dependency**
   * Replace `deepcopy` with `intent.model_copy(deep=True)` (available in Pydantic ≥ 2) **or** use `json.loads(json.dumps(obj))` style cloning.
   * Advantage: keeps sandbox allowlist minimal.
2. **Alternative: Amend Sandbox Allowlist**
   * Add `copy` to the permitted modules list if a safe subset can be guaranteed.
3. **Integration Test**
   * Add a regression test that executes generated weight-change snippets inside the sandbox stub to detect blocked imports early.
4. **Documentation & Changelog**
   * Update CHANGELOG (done) and ROADMAP_CANVAS with issue & fix plan.

---
*Created by Assistant – Session 021* 