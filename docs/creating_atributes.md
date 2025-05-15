Creating patient_attributes.py in VP Data Analysis

This guide outlines a safe, incremental plan for centralizing patient attribute semantics in the Ask Anything Assistant (AAA). It reduces duplication, improves clarity, and helps support attributes like "program completer" or "GLP-1 engaged".

🎯 Goal

Create a single, centralized source of truth for all categorical patient attributes (e.g., gender, active status, smoking history), usable by both code and AI prompt builders.

✅ Overview of Benefits

Replaces scattered literals like == 1, == "F", etc.

Supports consistent labels in charts and explanations.

Makes it easier to add derived attributes like ProgramCompleter.

Enables intent parsing and clarifying question logic to reuse consistent schema.

📁 Step-by-Step Implementation Plan

Step 1 – Create the Single Source

File: app/utils/patient_attributes.py

Contents:

Create enums (e.g., Gender, Active)

Create ATTRIBUTE_LABELS dict

Define helper: label_for(field, value)

from enum import Enum

class Gender(Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"

class Active(Enum):
    ACTIVE = 1
    INACTIVE = 0

ATTRIBUTE_LABELS = {
    "gender": {"M": "Male", "F": "Female", "O": "Other"},
    "active": {1: "Active", 0: "Inactive"}
}

def label_for(field, value):
    return ATTRIBUTE_LABELS.get(field, {}).get(value, str(value))

Step 2 – Replace Scattered Literals

Replace hard-coded literals with Enum members:

# BEFORE
if row["gender"] == "F":
    ...

# AFTER
if row["gender"] == Gender.FEMALE.value:
    ...

Use label_for("gender", value) for consistent label display.

Step 3 – Update Display Maps

In db_query.py or wherever display labels are referenced, replace bool_fields or static dicts with ATTRIBUTE_LABELS.

UI and charts should use label_for() for display.

Step 4 – Expose to Prompt Builder

In ai_helper.get_data_schema():

Load field names from ATTRIBUTE_LABELS.

Optionally use Enum docstrings for inline AI guidance.

Delete duplicated field lists hardcoded in prompt.

Step 5 – Add Tests

Create unit tests for label_for() and enum coverage:

def test_label_for():
    assert label_for("gender", "M") == "Male"
    assert label_for("active", 0) == "Inactive"

Run existing test suite to catch regressions (mainly import paths).

Step 6 – Optional (Schema Constraint)

To add hard DB constraint:

ALTER TABLE patients ADD CONSTRAINT chk_active CHECK (active IN (0,1));

🕒 Time Estimate

Coding & Replace Pass: 3–5 hours

Test Fixes & CI Green: 2–3 hours

Code Review & Merge: 1 hour

⚠️ Risk Level

Low to Medium: Changes are mechanical and backed by tests.

Rollback Easy: Use git revert if needed.