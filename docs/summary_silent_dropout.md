# Silent Dropout Detection Implementation

## Overview

This document outlines the implementation of the Silent Dropout Detection feature, which identifies patients who are still marked as active in the database but haven't had a provider visit in a specified period (default 90 days). This feature helps healthcare teams identify patients who may have effectively dropped out of the program without being officially marked as inactive.

## Components Implemented

1. **Database Schema Update**:
   - Added `last_visit_date` column to `patient_visit_metrics` table
   - Created index on this column for efficient queries

2. **Core Utility Module**:
   - Implemented `app/utils/silent_dropout.py` with key functions:
     - `get_silent_dropout_report()`: Identifies active patients without recent visits
     - `update_last_visit_date_for_patients()`: Updates visit dates from available data
     - `mark_patient_as_inactive()`: Utility to update patient status

3. **UI Page**:
   - Created `app/pages/silent_dropout_page.py` with Panel UI components
   - Implemented interactive tabular display with selectable rows
   - Added CSV export functionality
   - Provided bulk action to mark selected patients as inactive

4. **Integration**:
   - Added the Silent Dropout page to the main application tabs
   - Ensured proper error handling with fallback displays

5. **Unit Tests**:
   - Added comprehensive test coverage for the silent dropout utility

## Implementation Details

### Database Migration

Created migration file `010_add_last_visit_date.sql` to add a timestamp column tracking the last provider visit date:

```sql
ALTER TABLE patient_visit_metrics ADD COLUMN last_visit_date TEXT;
CREATE INDEX idx_patient_visit_metrics_last_visit_date ON patient_visit_metrics(last_visit_date);
```

### Silent Dropout Detection Logic

The core detection logic uses the following SQL query strategy:

1. Select active patients (configurable)
2. Join with visit metrics to find last visit date
3. Filter for patients whose last visit is older than the threshold date
4. Include patients with NULL last_visit_date (never visited)
5. Calculate days since last visit for sorting

The UI provides a configurable threshold (default 90 days) and allows filtering for active-only patients.

### Future Enhancements

1. **Enhanced Appointment Tracking**:
   - Create a dedicated appointments table for more accurate visit tracking
   - Track appointment types, outcomes, and providers

2. **Automated Follow-up**:
   - Add functionality to automatically generate follow-up tasks for silent dropouts
   - Implement notification system for care coordinators

3. **Re-engagement Analysis**:
   - Track re-engagement attempts and success rates
   - Analyze patterns in dropout behavior for preventive measures

4. **Predictive Analytics**:
   - Develop models to predict likelihood of dropout based on visit patterns
   - Implement early warning system for at-risk patients

## Usage

1. Navigate to the "Silent Dropouts" tab in the application
2. Adjust the threshold days if needed (default 90)
3. Click "Run Report" to generate the list
4. Export results using the "Download CSV" button
5. Select patients and use "Mark Selected as Inactive" to update their status

## Testing

The implementation includes unit tests covering:
- Report generation with various parameters
- Visit date updating functionality
- Patient status updating
- Handling of edge cases (empty results, etc.)

---

Document Author: gmetfr  
Date: 2025-05-12 