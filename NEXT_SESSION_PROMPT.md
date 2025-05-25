# Next Session Tasks: Complete Reference Range Integration

## Context Summary

We've been working on enhancing the Ask Anything Assistant (AAA) system to properly use clinical reference ranges from `data/metric_reference.yaml` instead of hardcoded values. This improves medical accuracy and transparency.

### What We've Already Accomplished ✅

1. **Fixed A1C Hardcoded Values in Code Generation:**
   - Updated `app/utils/ai/analysis_templates.py` (line ~120)
   - Updated `app/utils/ai/codegen/comparison.py` (line ~35)
   - Both now use `get_range('a1c', 'high')['min']` instead of hardcoded `7.0`

2. **Enhanced Narrative Builder:**
   - Modified `app/utils/ai/narrative_builder.py` to include reference ranges in AI prompts
   - AI now automatically mentions clinical thresholds (e.g., "high A1C (≥6.5%)")

3. **Added Reference Range Tables:**
   - Enhanced `app/analysis_helpers.py` with `create_reference_ranges_table()` function
   - Results now show collapsible reference range tables when applicable

4. **Fixed Intent Parsing Issues:**
   - Fixed operator normalization in `app/utils/query_intent.py` (line 142)
   - Fixed clarification workflow return values in `app/query_refinement/clarification_workflow.py`

### Current Status 🎯

The system is working correctly! The query "Compare blood pressure values for patients with high vs normal A1C" now:
- ✅ Parses correctly without stopping at clarification
- ✅ Uses dynamic reference ranges (6.5% threshold) instead of hardcoded 7.0%
- ✅ Generates proper analysis with clinical context
- ✅ Shows reference range tables in results

## Remaining Tasks for Next Session

### 🔧 **Priority 1: Fix Gap Report Hardcoded Values**

**File:** `app/utils/gap_report.py` (lines 102, 107)

**Current Problem:**
```python
# Lines 102, 107 - HARDCODED VALUES
"prediabetes": _simple_lab_cte("A1C", "metric_value >= 5.7 AND metric_value < 6.5"),
"type_2_diabetes": _simple_lab_cte("A1C", "metric_value >= 6.5"),
```

**Required Fix:**
Replace hardcoded A1C thresholds with dynamic lookups from `data/metric_reference.yaml`:

```python
from app.utils.metric_reference import get_range

# Get thresholds dynamically
prediabetes_min = get_range('a1c', 'prediabetes')['min']  # Should be 5.7
prediabetes_max = get_range('a1c', 'prediabetes')['max']  # Should be 6.4
diabetes_min = get_range('a1c', 'high')['min']  # Should be 6.5

"prediabetes": _simple_lab_cte("A1C", f"metric_value >= {prediabetes_min} AND metric_value <= {prediabetes_max}"),
"type_2_diabetes": _simple_lab_cte("A1C", f"metric_value >= {diabetes_min}"),
```

### 🔧 **Priority 2: Update Gap Report Tests**

**File:** `tests/utils/test_gap_report.py` (lines 82, 99, 119, 138)

**Current Problem:**
Tests have hardcoded assertions like:
```python
assert "metric_value >= 5.7 AND metric_value < 6.5" in called_sql
assert "metric_value >= 6.5" in called_sql
```

**Required Fix:**
Update test assertions to use dynamic values:
```python
from app.utils.metric_reference import get_range

prediabetes_min = get_range('a1c', 'prediabetes')['min']
prediabetes_max = get_range('a1c', 'prediabetes')['max'] 
diabetes_min = get_range('a1c', 'high')['min']

assert f"metric_value >= {prediabetes_min} AND metric_value <= {prediabetes_max}" in called_sql
assert f"metric_value >= {diabetes_min}" in called_sql
```

### 🔧 **Priority 3: Verify Reference Range System**

**Test the complete workflow:**

1. **Test A1C Comparison Query:**
   ```
   "Compare blood pressure values for patients with high vs normal A1C"
   ```
   - Should use 6.5% threshold (not 7.0%)
   - Should show reference ranges in results
   - Should include clinical context in narrative

2. **Test Gap Report:**
   ```python
   from app.utils.gap_report import get_condition_gap_report
   df = get_condition_gap_report("prediabetes")
   df2 = get_condition_gap_report("type_2_diabetes")
   ```
   - Should use dynamic thresholds from metric_reference.yaml
   - Should not have hardcoded 5.7, 6.4, 6.5 values

3. **Test Reference Range Display:**
   - Query any metric-related question
   - Verify reference range table appears
   - Verify clinical thresholds mentioned in narrative

## Key Files and Their Current State

### ✅ **Already Fixed Files:**
- `app/utils/ai/analysis_templates.py` - Uses dynamic A1C ranges
- `app/utils/ai/codegen/comparison.py` - Uses dynamic A1C ranges  
- `app/utils/ai/narrative_builder.py` - Enhanced with reference context
- `app/analysis_helpers.py` - Added reference range tables
- `app/utils/query_intent.py` - Fixed operator validation
- `app/query_refinement/clarification_workflow.py` - Fixed return values

### 🔧 **Files Needing Updates:**
- `app/utils/gap_report.py` - Replace hardcoded A1C thresholds
- `tests/utils/test_gap_report.py` - Update test assertions

### 📚 **Reference Files:**
- `data/metric_reference.yaml` - Contains all clinical reference ranges
- `app/utils/metric_reference.py` - Helper functions for accessing ranges

## Testing Commands

After making changes, test with:

```bash
# Test the application
python3 run.py

# Test gap report functionality  
python3 -c "from app.utils.gap_report import get_condition_gap_report; print(get_condition_gap_report('prediabetes').head())"

# Run gap report tests
python3 -m pytest tests/utils/test_gap_report.py -v

# Test A1C comparison query in the UI
# Navigate to localhost and try: "Compare blood pressure values for patients with high vs normal A1C"
```

## Expected Outcomes

After completing these tasks:

1. **Gap Report** will use dynamic clinical thresholds instead of hardcoded values
2. **All Tests** will pass with dynamic reference ranges
3. **Complete System** will consistently use `data/metric_reference.yaml` for all clinical thresholds
4. **Medical Accuracy** will be improved with proper clinical reference ranges
5. **Transparency** will be enhanced with reference range tables in results

## Notes

- The system is currently working well - this is cleanup/consistency work
- The main analysis engine already uses proper reference ranges
- Focus on gap report functionality as the primary remaining hardcoded area
- All reference ranges are properly defined in `data/metric_reference.yaml`
- The learning enhancement and admin dashboard features are working correctly

## Application Status

The application should be running on `localhost:61890` and working correctly for most queries. The fixes needed are for consistency and completeness of the reference range integration. 