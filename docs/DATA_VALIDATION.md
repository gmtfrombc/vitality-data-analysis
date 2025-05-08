# Data Validation System Design

This document outlines the approach for implementing a data validation and correction system for the Metabolic Health Program data.

## Overview

The data validation system will identify missing or inaccurate patient data and provide an interface for reviewing and correcting issues. The system addresses a common challenge in healthcare data collection: information that is missing, incorrectly entered, or outside expected ranges.

## User Journey

1. User opens the Data Validation tab in the application
2. System displays a dashboard summarizing data quality issues
3. User selects a patient record to review
4. System displays the patient's data timeline with flagged issues
5. User can:
   - Add missing data
   - Correct inaccurate values
   - Mark issues as "reviewed" (accept as is)
6. All changes are tracked in an audit log

## Implementation Approach

### Phase 1: Define Basic Rule Structure

We'll create a simple rule system with three types of validation rules:

**1. Missing Data Rules**
```python
# Example of a missing data rule
{
    "rule_id": "BMI_FREQUENCY_CHECK",
    "description": "Patient should have BMI recorded at least once every two months",
    "rule_type": "missing_data",
    "validation_logic": "date_diff_check",
    "parameters": {
        "field": "bmi",
        "max_days_between": 60
    },
    "severity": "warning"
}
```

**2. Range Validation Rules**
```python
# Example of a range validation rule
{
    "rule_id": "VALID_BMI_RANGE",
    "description": "Human BMI values typically fall between 15-70",
    "rule_type": "range_check",
    "validation_logic": "range_check",
    "parameters": {
        "field": "bmi",
        "min_value": 15,
        "max_value": 70
    },
    "severity": "error"
}
```

**3. Consistency Rules**
```python
# Example of a consistency rule
{
    "rule_id": "WEIGHT_HEIGHT_CONSISTENCY",
    "description": "Weight and height should result in a valid BMI calculation",
    "rule_type": "consistency_check",
    "validation_logic": "calculated_field_check",
    "parameters": {
        "formula": "weight_kg / (height_m * height_m)",
        "result_field": "bmi",
        "tolerance": 0.1
    },
    "severity": "warning"
}
```

### Phase 2: Patient-Level Validation View

We'll create a patient-centric view that:

1. Shows a timeline of all measurements
2. Highlights missing or problematic data points
3. Allows inline editing of values
4. Tracks changes with an audit trail

### Phase 3: Dashboard and Reporting

We'll build a summary dashboard that:

1. Shows overall data quality metrics
2. Lists patients with the most issues
3. Provides filtering by issue type and severity
4. Generates reports on data quality trends

## Database Changes

We'll need to add the following tables:

1. `validation_rules` - Stores the rules
2. `validation_results` - Stores identified issues
3. `data_corrections` - Tracks changes made to fix issues
4. `correction_audit` - Audit log of who made changes and why

## User Interface

The interface will be simple and focused on clinical workflows:

1. **Dashboard View**: Summary statistics and patient list
2. **Patient Timeline View**: Chronological display of all patient data
3. **Issue Details**: Explanation of each validation issue
4. **Correction Form**: Simple interface for making corrections

## Rule Creation Process

Instead of complex configuration, we'll use a simple approach:

1. Create an initial set of common validation rules
2. Allow editing rules through a simple form
3. Store rules in CSV or simple JSON format
4. Support basic rule testing on sample data

## Next Steps

1. Create database migration for validation tables
2. Build basic rule engine with simple validators
3. Implement patient timeline visualization
4. Create correction interface with audit logging
5. Build dashboard view with key metrics 