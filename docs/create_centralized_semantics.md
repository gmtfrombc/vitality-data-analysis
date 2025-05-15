# Centralising Patient-Attribute Semantics

*Created: 2025-05-11*

## Problem

Patient characteristics (e.g. `active`, `gender`, `etoh`, `tobacco`, `glp1_full`) are stored correctly in the
SQLite schema but **their meaning is duplicated in multiple places**:

* raw `1/0`, `"M"/"F"` literals in UI pages and tests
* ad-hoc label dictionaries inside individual modules (`db_query.py`, `data_assistant.py`)
* prompt-template text in `ai_helper.py`

This leads to:

1. Risk of drift when a value changes (e.g. adding `Active.INACTIVE = 0` but UI expects `2`).
2. Large search-surface when adding a new attribute ( >8 find-replace operations ).
3. Hard-coded labels blocking i18n or clinical terminology updates.

## Recommended Solution

1. **Single-source module** `app/utils/patient_attributes.py`
   * `Enum` classes (`Active`, `Gender`, …) with values matching DB.
   * `ATTRIBUTE_LABELS`: `{field: {value: human_label}}`.
   * Helpers:
     * `label_for(field, value)` – UI-friendly string.
     * `boolean_value(value)` – Yes/No for 0/1 convenience.
2. **Mechanical replace**
   * Replace `patients_df["active"] == 1` → `== Active.ACTIVE`.
   * Replace `"F"` / `"M"` literals with `Gender.FEMALE` / `Gender.MALE`.
   * Use `label_for` wherever labels are shown to humans.
3. **Expose to AI**
   * Pass `ATTRIBUTE_LABELS` to `ai_helper.get_data_schema()` so LLM knows canonical names.
4. **Schema Validation**
   * Keep existing `schema_cache.py`; extend it to validate Enum values (optional CHECK constraints).

## What Went Wrong in First Attempt

* We edited `app/pages/data_assistant.py` manually and accidentally corrupted
  indentation and removed the `Active` import ⇒ >150 syntax errors.
* Massive in-line replacements without running the linter after each chunk made
  problems hard to spot.

## Recovery Plan

1. **Rollback** `app/pages/data_assistant.py` to last clean commit.
2. Apply *only* the safe enum replacements (5 literal lines in BMI/general stats paths).
3. Update tests (`test_app.py`, any others) to use `Active` enum.
4. Run `ruff --fix` + full `pytest -q`.
5. Once passing, continue with step-2 of the refactor plan (other modules).

## Next Steps for Next Assistant

| Priority | Task | File(s) |
|----------|------|---------|
| 🔶 1 | Re-apply enum replacements in `data_assistant.py` (5 spots) | `app/pages/data_assistant.py` |
| 🔶 2 | Replace literals in `db_query.py` & `patient_view.py` (already partly done) | multiple |
| 🔷 3 | Remove now-unused local label dicts; call `label_for` | `db_query.py`, `data_assistant.py` |
| 🔷 4 | Extend unit tests for `label_for` and enum equality | `tests/utils` |
| 🔷 5 | Update AI prompt builder to reference `ATTRIBUTE_LABELS` | `app/ai_helper.py` |

---
*Hand-off prepared by Assistant #n on 2025-05-11.* 