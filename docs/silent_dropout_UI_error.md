# Silent Dropout UI Error: Table Click Handler Issue

## Error Description

When clicking on a patient ID in the Silent Dropout detection table, the following error occurs:

```
AttributeError("'CellClickEvent' object has no attribute 'rows'")
```

The error is triggered specifically when a user clicks on a cell in the Tabulator table. The underlying issue is a mismatch between event types - our handler is expecting a row selection event with a `rows` attribute, but we're receiving a cell click event (`CellClickEvent`) which has a different structure.

## Technical Details

- **Location**: `app/pages/silent_dropout_page.py` in the `_on_row_click` method
- **Component**: Panel's Tabulator widget with click event handling
- **Current Implementation**: 
  ```python
  self._table_panel.on_click(self._on_row_click)

  def _on_row_click(self, event):
      """Handle row selection events."""
      self._selected_patients = [row['patient_id'] for row in event.rows]
      self._mark_inactive_btn.disabled = len(self._selected_patients) == 0
  ```

- **Root Cause**: The table is generating `CellClickEvent` when a cell is clicked, but our handler attempts to access `event.rows`, which only exists on row selection events, not cell click events.

## Proposed Fix

Update the `_on_row_click` method in `app/pages/silent_dropout_page.py` to handle both types of events:

```python
def _on_row_click(self, event):
    """Handle row selection and cell click events."""
    # For row selection events
    if hasattr(event, 'rows'):
        self._selected_patients = [row['patient_id'] for row in event.rows]
    # For cell click events
    elif hasattr(event, 'column') and event.column == 'patient_id' and hasattr(event, 'row'):
        # Get the patient ID from the clicked cell
        patient_id = self._table_panel.value.iloc[event.row]['patient_id']
        # Toggle selection for this patient
        if patient_id in self._selected_patients:
            self._selected_patients.remove(patient_id)
        else:
            self._selected_patients.append(patient_id)
    
    # Update button state
    self._mark_inactive_btn.disabled = len(self._selected_patients) == 0
```

## Alternative Solution

Configure the Tabulator to use row selection mode instead of cell clicking:

```python
self._table_panel = pn.widgets.Tabulator(
    self._df,
    pagination="remote",
    page_size=20,
    sizing_mode="stretch_width",
    selectable='checkbox',  # Use checkbox selection mode
    show_index=False
)

# Then modify event handler to use the simpler row selection mode
def _on_row_click(self, event):
    """Handle row selection events."""
    self._selected_patients = [row['patient_id'] for row in event.rows]
    self._mark_inactive_btn.disabled = len(self._selected_patients) == 0
```

## Implementation Steps

1. Either modify `_on_row_click` to handle both event types as shown in the first solution
2. Or change the Tabulator configuration to use checkbox selection mode
3. Add error handling to gracefully handle unexpected event structures
4. Add test case to verify both cell clicks and row selections work correctly

## Impact

- Low severity - this is a UI usability issue that doesn't affect core functionality
- Only impacts the Silent Dropout Detection page when users try to select patients by clicking cells
- The workaround is to use the tabulator's native row selection checkboxes when available 