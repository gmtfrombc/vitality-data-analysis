## Daily User Workflow (Graeme's Daily Cycle)

To maximize simplicity and effectiveness, follow these daily steps after completing question sessions:

### End of Day Cycle

**1. Run `model_retraining.py`**

* In your IDE (Cursor), open a terminal session and execute:

  ```bash
  python model_retraining.py --reset-metrics
  ```

**2. Interactive Approval Session**

* The script auto-analyzes feedback logs.
* Presents recommended changes:

  * Clearly displayed with simple Yes/No or Modify options.

**Example Interaction:**

```
Recommended Change:
- Change default assumption for BMI queries to 'Active patients only'.
Approve (y), Modify (m), or Decline (n)?
```

**3. Model Retraining**

* The script retrains the intent classifier automatically based on approved changes.

**4. Template and Assumption Updates**

* After approval, the script updates templates and assumptions automatically:

  * Updates `metric_catalogue.csv`.
  * Updates internal Python analysis templates if necessary.

**5. Review and Save Report**

* At the end of the session, a report (`daily_retraining_report.md`) is generated summarizing:

  * Approved changes
  * Model retraining status
  * Template updates

### Post-Retraining Validation  

After the script finishes and the markdown report is generated, run the quick regression checks to make sure nothing broke:

```bash
# Fast sanity tests (< 10 s)
pytest -m smoke

# Full unit-test suite (optional if time allows)
pytest

# End-to-end golden self-test
./run_self_test.sh
```
*If any tests fail, address the error before committing* – see the test output for file locations and fix notes.

Once all tests pass:
* Review `logs/daily_retraining_report_<date>.md` and `docs/template_change_queue.md` for accuracy.
* Commit the following artefacts to version control:
  * `models/intent_classifier.pkl` (use Git LFS if the repo enforces it)
  * Updated `data/intent_training_data.jsonl` (new training examples)
  * Any changed templates (e.g. `metric_catalogue.csv`) or Python files
  * Updated documentation files (this workflow, change queue, reports if desired)

### Optional Follow-up

* Briefly review the generated markdown report to confirm all changes are correctly implemented.
* Manually commit changes to version control if necessary.

---

## Recommended Best Practices

* Regularly backup the SQLite database.
* Maintain version control (e.g., Git) of template files, assumptions (`metric_catalogue.csv`), and the trained intent model.
* Conduct weekly detailed reviews to assess long-term trends and make strategic improvements.

---

This structured roadmap will streamline your daily improvement cycles, ensuring continual enhancement of the AAA's accuracy, usability, and efficiency.
