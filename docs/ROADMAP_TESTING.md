# ROADMAP\_TESTING.md

## Continuous Feedback & Evaluation Roadmap

### Purpose

The goal of this document is to guide the iterative improvement of the 'Ask Anything Assistant' (AAA) application through clear, structured steps involving user feedback, data analysis, and automated retraining of the intent classifier and assumptions.

## AI Assistant Guidance for `model_retraining.py`

### Overview

Create a Python script, `model_retraining.py`, that:

* Automatically reads daily feedback logs from the SQLite database (`assistant_feedback`).
* Analyzes thumbs-down responses and associated comments.
* Suggests clear improvements to default assumptions.
* Provides an interactive session for the user to approve, modify, or decline these suggestions.
* Retrains the intent classification model.
* Updates application templates and assumptions as approved by the user.

### Detailed Steps for Implementation

**Step 1: Database Connection**

* Connect to SQLite database and fetch feedback records from the `assistant_feedback` table where feedback = thumbs down.

**Step 2: Feedback Analysis**

* Parse feedback records and group common feedback issues based on:

  * Metric misunderstood (e.g., BMI, Blood Pressure).
  * Frequent comments indicating confusion over default assumptions.

**Step 3: Suggesting Improvements**

* Generate concise, actionable recommendations.
* Example:

  * "Consider changing default assumption for 'BMI' from 'all patients' to 'active patients only'."

**Step 4: Interactive Console Session**

* Present recommendations to the user in an interactive CLI (command-line interface).
* Allow user responses to each suggestion:

  * Approve (Yes)
  * Modify (User enters new assumption)
  * Decline (No)

**Step 5: Retraining the Intent Classifier**

* Use approved feedback to update training data.
* Retrain the intent classifier (use scikit-learn, spaCy, or similar NLP library).
* Save the retrained model to the appropriate directory for immediate use.

**Step 6: Updating Application Templates**

* Automatically modify Python templates or configuration files (e.g., `metric_catalogue.csv`) based on approved changes.
* Ensure changes are logged clearly.

**Step 7: Logging and Reporting**

* Generate and save a simple markdown summary report (`daily_retraining_report.md`) detailing actions taken and changes implemented.

## Enhancing User Experience & Feedback Collection

### UI Improvements for Feedback Collection

**Step 1: Feedback Widget Visibility and Positioning**

* Ensure feedback mechanisms (thumbs up/down) are prominently displayed and clearly associated with the results.
* Position feedback controls in a consistent location for all query results.
* Implement a visible confirmation (e.g., "Thank you" message) when feedback is submitted.

**Step 2: Query Refinement UI**

* Place query refinement controls in a logical position that follows the user's workflow:
  * First show results
  * Then offer refinement options
  * Finally collect feedback on the experience
* Ensure refinement text input is properly visible when activated.
* Maintain consistency between refinement UI state and internal application state.

**Step 3: Feedback Storage and Retrieval**

* Verify all feedback is correctly recorded in the `assistant_feedback` table.
* Implement connection between feedback UI events and database storage.
* Create diagnostic tools to validate feedback capture rates.

**Step 4: Query Refinement Impact Analysis**

* Track and analyze how often users refine queries vs. starting new ones.
* Capture specific refinement patterns to inform intent classification improvements.
* Develop metrics to measure the impact of refinements on overall user satisfaction.

**Step 5: Testing & Validation Framework**

* Create automated tests to verify UI state transitions with feedback and refinement flows.
* Implement integration tests that confirm database feedback records match UI interactions.
* Develop regression tests to ensure UI improvements don't break existing functionality.