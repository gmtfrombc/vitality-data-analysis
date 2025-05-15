# Testing Session 013 – 2025-05-14

## Goal
Resume centralised patient-attribute semantics refactor paused in Session 012; ensure enums are consistently used across codebase and tests without breaking UI or visualisations.

## Step-by-Step Plan for Next Assistant
1. **Branch:** `git checkout -b feat/attribute-enum-cleanup`.
2. **Patch `data_assistant.py`:** Replace ~5 hard-coded `active`, gender, etc. literals with `Active`, `Gender`, `label_for` helpers.  Commit & run tests after each logical chunk.
3. **Clean `db_query.py`:** Remove duplicate `bool_fields` map; use `label_for` wherever boolean labels needed.
4. **Global sweep:** Search for remaining raw literals (`== 1`, `'M'/'F'`) across repo and replace with Enum/label helpers.
5. **Update tests:** Adjust assertions that expect numeric/gender literals to use Enums or canonical labels.
6. **Expose labels:** Modify `ai_helper.get_data_schema()` to include `ATTRIBUTE_LABELS` so the LLM uses canonical names.
7. **DB constraints (optional):** Draft migration `009_enum_constraints.sql` adding `CHECK` constraints for enum columns; integrate with migration runner.
8. **Validation:** Run full test suite & coverage (`pytest -q && coverage report`) – maintain ≥ 60 % threshold.
9. **Docs & PR:** Update CHANGELOG, ROADMAP, and open PR referencing WS-1 milestone.

## Notes
* Work incrementally; keep tests green.
* Verify Panel UI still renders patient-attribute labels correctly post-refactor.
* Enum helpers live in `app/utils/patient_attributes.py`.

*Prepared by Assistant #n – end of Session 013* 