# SPRINT 2 PROMPT - Enhanced Feedback UI

## PROJECT CONTEXT

You are working on the **AAA Learning Enhancements Project** - adding automated learning capabilities to the Ask Anything AI Assistant (AAA). This is Sprint 2 of a 5-sprint project.

### Project Overview
The AAA is a healthcare data analysis assistant that converts natural language queries to SQL. We're building an automated learning system that captures user corrections, analyzes errors, and learns patterns for improved accuracy.

### Previous Sprint Completion (Sprint 1)
✅ **Sprint 1 COMPLETED** - Database foundation and basic correction service:
- Database tables created: `correction_sessions`, `intent_patterns`, `code_templates`, `learning_metrics`, `query_similarity_cache`
- Basic `CorrectionService` class with core functionality:
  - `capture_correction_session()`
  - `get_correction_session()`  
  - `update_correction_session()`
- Data models: `CorrectionSession`, `IntentPattern`
- Comprehensive tests for basic functionality
- All existing functionality remains unchanged

## SPRINT 2 OBJECTIVES

**Goal**: Replace basic feedback widgets with enhanced versions that capture detailed corrections and provide initial error analysis.

**Key Deliverables**:
1. Enhanced feedback widget with correction capture interface
2. Basic error analysis and categorization
3. UI integration replacing existing feedback widgets
4. Foundation for automated suggestion system
5. Comprehensive testing of feedback workflow

**User Impact**: Enhanced feedback experience - users can now provide detailed corrections when they give thumbs down feedback.

## TECHNICAL REQUIREMENTS

### Enhanced Feedback Widget

Create `app/utils/enhanced_feedback_widget.py`:

```python
"""
Enhanced Feedback Widget for AAA Learning System

This widget extends the basic feedback functionality to capture detailed corrections
and integrate with the learning system for continuous improvement.

Features:
- Standard thumbs up/down feedback
- Detailed correction capture for negative feedback
- Integration with CorrectionService
- Real-time error analysis and suggestions
"""

from __future__ import annotations

import json
import logging
import panel as pn
import param
from typing import Optional, Dict, Any, Callable

from app.utils.feedback_db import insert_feedback
from app.services.correction_service import CorrectionService, CorrectionSession

logger = logging.getLogger(__name__)


class EnhancedFeedbackWidget(param.Parameterized):
    """Enhanced feedback widget with correction capture capabilities."""

    # Parameters
    query: str = param.String(default="")
    original_intent_json: str = param.String(default="")
    original_code: str = param.String(default="") 
    original_results: str = param.String(default="")
    feedback_submitted: bool = param.Boolean(default=False)
    correction_captured: bool = param.Boolean(default=False)

    def __init__(self, 
                 query: str,
                 original_intent_json: Optional[str] = None,
                 original_code: Optional[str] = None, 
                 original_results: Optional[str] = None,
                 on_correction_applied: Optional[Callable] = None,
                 **params):
        """Initialize the enhanced feedback widget.
        
        Args:
            query: The original user query
            original_intent_json: The parsed intent JSON (if available)
            original_code: The generated code (if available)
            original_results: The analysis results (if available)
            on_correction_applied: Callback when correction is applied
        """
        super().__init__(**params)
        
        self.query = query
        self.original_intent_json = original_intent_json or ""
        self.original_code = original_code or ""
        self.original_results = original_results or ""
        self.on_correction_applied = on_correction_applied
        
        # Initialize correction service
        self.correction_service = CorrectionService()
        
        # UI components
        self._create_components()
        
        # State tracking
        self.feedback_id: Optional[int] = None
        self.correction_session_id: Optional[int] = None

    def _create_components(self):
        """Create the UI components."""
        
        # Standard feedback section
        self.feedback_section = pn.Column(
            pn.pane.Markdown("**Was this answer helpful?**", margin=(5, 0)),
            pn.Row(
                pn.widgets.Button(
                    name="👍 Yes", 
                    button_type="success",
                    width=80,
                    margin=(0, 5, 0, 0)
                ),
                pn.widgets.Button(
                    name="👎 No", 
                    button_type="danger", 
                    width=80,
                    margin=(0, 5, 0, 0)
                ),
                align="start"
            ),
            margin=(10, 0),
            visible=True
        )
        
        # Get button references for event handling
        self.thumbs_up_btn = self.feedback_section[1][0]
        self.thumbs_down_btn = self.feedback_section[1][1]
        
        # Enhanced correction section (hidden initially)
        self.correction_section = pn.Column(
            pn.pane.Markdown("### Help us improve! 🎯", margin=(10, 0, 5, 0)),
            pn.pane.Markdown("Please provide the correct answer so we can learn:", margin=(0, 0, 5, 0)),
            
            pn.widgets.TextAreaInput(
                name="Correct Answer:",
                placeholder="What should the correct answer be? Be as specific as possible...",
                height=100,
                sizing_mode="stretch_width"
            ),
            
            pn.Row(
                pn.widgets.Button(
                    name="Submit Correction",
                    button_type="primary",
                    width=150
                ),
                pn.widgets.Button(
                    name="Skip",
                    button_type="light", 
                    width=80
                ),
                margin=(10, 0, 0, 0)
            ),
            
            visible=False,
            sizing_mode="stretch_width"
        )
        
        # Get correction component references
        self.correct_answer_input = self.correction_section[2]
        self.submit_correction_btn = self.correction_section[3][0]
        self.skip_correction_btn = self.correction_section[3][1]
        
        # Analysis section (hidden initially) - will be enhanced in Sprint 3
        self.analysis_section = pn.Column(
            pn.pane.Markdown("### 🔍 Analysis", margin=(10, 0, 5, 0)),
            pn.pane.Markdown("*Analyzing the error...*", name="analysis_text"),
            visible=False,
            sizing_mode="stretch_width"
        )
        
        # Thank you section (hidden initially)
        self.thank_you_section = pn.Column(
            pn.pane.Markdown("✅ **Thank you for your feedback!**", margin=(10, 0)),
            pn.pane.Markdown("Your input helps improve the assistant.", margin=(0, 0, 10, 0)),
            visible=False
        )
        
        # Set up event handlers
        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Set up event handlers for UI components."""
        
        self.thumbs_up_btn.on_click(self._on_thumbs_up)
        self.thumbs_down_btn.on_click(self._on_thumbs_down)
        self.submit_correction_btn.on_click(self._on_submit_correction)
        self.skip_correction_btn.on_click(self._on_skip_correction)

    def _on_thumbs_up(self, event):
        """Handle thumbs up feedback."""
        try:
            success = insert_feedback(
                question=self.query,
                rating="up"
            )
            
            if success:
                logger.info(f"Positive feedback recorded for query: {self.query[:50]}...")
                self._show_thank_you()
            else:
                logger.error("Failed to record positive feedback")
                
        except Exception as e:
            logger.error(f"Error recording positive feedback: {e}")

    def _on_thumbs_down(self, event):
        """Handle thumbs down feedback."""
        try:
            success = insert_feedback(
                question=self.query,
                rating="down"
            )
            
            if success:
                logger.info(f"Negative feedback recorded for query: {self.query[:50]}...")
                # Store feedback ID for correction session
                self.feedback_id = self._get_latest_feedback_id()
                self._show_correction_interface()
            else:
                logger.error("Failed to record negative feedback")
                
        except Exception as e:
            logger.error(f"Error recording negative feedback: {e}")

    def _get_latest_feedback_id(self) -> Optional[int]:
        """Get the ID of the most recently inserted feedback."""
        try:
            from app.utils.feedback_db import _get_conn
            
            with _get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id FROM assistant_feedback 
                    WHERE question = ? AND rating = 'down'
                    ORDER BY id DESC LIMIT 1
                """, (self.query,))
                
                row = cursor.fetchone()
                return row[0] if row else None
                
        except Exception as e:
            logger.error(f"Failed to get latest feedback ID: {e}")
            return None

    def _show_correction_interface(self):
        """Show the correction interface."""
        self.feedback_section.visible = False
        self.correction_section.visible = True

    def _on_submit_correction(self, event):
        """Handle correction submission."""
        correct_answer = self.correct_answer_input.value.strip()
        
        if not correct_answer:
            # Show error message
            self.correct_answer_input.placeholder = "Please provide a correct answer before submitting..."
            return
        
        try:
            # Create correction session
            if self.feedback_id:
                self.correction_session_id = self.correction_service.capture_correction_session(
                    feedback_id=self.feedback_id,
                    original_query=self.query,
                    human_correct_answer=correct_answer,
                    original_intent_json=self.original_intent_json or None,
                    original_code=self.original_code or None,
                    original_results=self.original_results or None
                )
                
                logger.info(f"Created correction session {self.correction_session_id}")
                
                # Show basic analysis (will be enhanced in Sprint 3)
                self._show_basic_analysis()
            else:
                logger.error("No feedback ID available for correction session")
                self._show_thank_you()
                
        except Exception as e:
            logger.error(f"Error submitting correction: {e}")
            self._show_thank_you()

    def _on_skip_correction(self, event):
        """Handle skipping the correction."""
        self._show_thank_you()

    def _show_basic_analysis(self):
        """Show basic analysis (placeholder for Sprint 3 enhancement)."""
        self.correction_section.visible = False
        self.analysis_section.visible = True
        
        # Basic analysis text
        analysis_text = self.analysis_section[1]
        analysis_text.object = "**Thank you for the correction!** We'll use this to improve our responses."
        
        # Auto-proceed to thank you after a moment
        import panel as pn
        pn.state.add_periodic_callback(lambda: self._show_thank_you(), 2000, count=1)

    def _show_thank_you(self):
        """Show thank you message."""
        self.feedback_section.visible = False
        self.correction_section.visible = False
        self.analysis_section.visible = False
        self.thank_you_section.visible = True
        self.feedback_submitted = True

    def view(self) -> pn.Column:
        """Get the complete widget view."""
        return pn.Column(
            self.feedback_section,
            self.correction_section,
            self.analysis_section,
            self.thank_you_section,
            sizing_mode="stretch_width",
            styles={'background': '#f8f9fa', 'padding': '15px', 'border-radius': '8px'}
        )


def create_enhanced_feedback_widget(
    query: str,
    original_intent_json: Optional[str] = None,
    original_code: Optional[str] = None,
    original_results: Optional[str] = None,
    on_correction_applied: Optional[Callable] = None
) -> pn.Column:
    """Create an enhanced feedback widget.
    
    Args:
        query: The original user query
        original_intent_json: The parsed intent JSON (if available)
        original_code: The generated code (if available)
        original_results: The analysis results (if available)
        on_correction_applied: Callback when correction is applied
        
    Returns:
        Panel Column widget
    """
    widget = EnhancedFeedbackWidget(
        query=query,
        original_intent_json=original_intent_json,
        original_code=original_code,
        original_results=original_results,
        on_correction_applied=on_correction_applied
    )
    
    return widget.view()
```

### Error Analysis Enhancement to CorrectionService

Add these methods to `app/services/correction_service.py`:

```python
def analyze_error_type(self, session_id: int) -> str:
    """Analyze the type of error in a correction session.
    
    Args:
        session_id: The correction session ID
        
    Returns:
        The determined error category
    """
    session = self.get_correction_session(session_id)
    if not session:
        return "unknown"
        
    # Basic heuristic-based error analysis
    error_category = "unknown"
    
    # Check if we have intent data to analyze
    if session.original_intent_json:
        try:
            from app.utils.query_intent import parse_intent_json
            intent = parse_intent_json(session.original_intent_json)
            
            # Intent-related errors
            if intent.analysis_type == "unknown":
                error_category = "ambiguous_intent"
            elif intent.target_field == "unknown":
                error_category = "unclear_target"
            elif not intent.filters and "active" in session.original_query.lower():
                error_category = "missing_filter"
            elif intent.analysis_type in ["count", "average"] and "distribution" in session.human_correct_answer.lower():
                error_category = "wrong_aggregation"
            else:
                error_category = "intent_mismatch"
                
        except Exception as e:
            logger.warning(f"Failed to parse intent for analysis: {e}")
            error_category = "intent_parse_error"
    
    # Code-related errors (if we have code but no intent issues)
    elif session.original_code and error_category == "unknown":
        if "GROUP BY" not in session.original_code and "group" in session.human_correct_answer.lower():
            error_category = "missing_groupby"
        elif "WHERE" not in session.original_code and "filter" in session.human_correct_answer.lower():
            error_category = "missing_where"
        else:
            error_category = "code_logic_error"
    
    # Update the session with the analysis
    self.update_correction_session(session_id, {
        "error_category": error_category,
        "correction_type": self._infer_correction_type(error_category)
    })
    
    logger.info(f"Analyzed session {session_id}: {error_category}")
    return error_category

def _infer_correction_type(self, error_category: str) -> str:
    """Infer the correction type from error category."""
    intent_errors = {
        "ambiguous_intent", "unclear_target", "missing_filter", 
        "wrong_aggregation", "intent_mismatch"
    }
    code_errors = {
        "missing_groupby", "missing_where", "code_logic_error"
    }
    
    if error_category in intent_errors:
        return "intent_fix"
    elif error_category in code_errors:
        return "code_fix"
    else:
        return "logic_fix"

def generate_correction_suggestions(self, session_id: int) -> List[Dict]:
    """Generate basic suggestions for correcting an error.
    
    Args:
        session_id: The correction session ID
        
    Returns:
        List of correction suggestions
    """
    session = self.get_correction_session(session_id)
    if not session:
        return []
    
    suggestions = []
    
    # Basic suggestions based on error category
    if session.error_category == "missing_filter":
        suggestions.append({
            "type": "add_filter",
            "description": "Add patient status filter (active/inactive)",
            "action": "Add Filter(field='active', value=1) to intent.filters"
        })
    
    elif session.error_category == "wrong_aggregation":
        suggestions.append({
            "type": "change_analysis_type", 
            "description": "Change analysis type from count/average to distribution",
            "action": "Update intent.analysis_type to 'distribution'"
        })
    
    # Always offer manual correction option
    suggestions.append({
        "type": "manual_correction",
        "description": "Manually review and correct",
        "action": "Human review and manual correction"
    })
    
    return suggestions
```

### UI Integration

Modify `app/data_assistant.py` to replace basic feedback with enhanced version:

In the `_display_final_results()` method, replace the existing feedback widget creation with:

```python
# Replace existing feedback widget creation with:
if self.feedback_widget is None:
    from app.utils.enhanced_feedback_widget import create_enhanced_feedback_widget
    
    self.feedback_widget = create_enhanced_feedback_widget(
        query=self.query_text,
        original_intent_json=json.dumps(self.engine.intent.model_dump()) if self.engine.intent and hasattr(self.engine.intent, 'model_dump') else None,
        original_code=self.engine.generated_code,
        original_results=json.dumps(self.engine.execution_results) if self.engine.execution_results else None,
        on_correction_applied=self._handle_correction_applied
    )

# Add callback method if it doesn't exist:
def _handle_correction_applied(self, session_id: int, suggestion: Dict):
    """Handle when a correction is applied."""
    logger.info(f"Correction applied for session {session_id}: {suggestion}")
    # Future implementation for Sprint 3
```

## FILES TO CREATE/MODIFY

### Files to Create
```
app/utils/enhanced_feedback_widget.py
tests/utils/test_enhanced_feedback_widget.py
```

### Files to Modify
```
app/data_assistant.py (replace feedback widget usage)
app/services/correction_service.py (add error analysis methods)
tests/services/test_correction_service_basic.py (expand tests)
```

## TESTING REQUIREMENTS

Create `tests/utils/test_enhanced_feedback_widget.py`:

```python
"""
Tests for EnhancedFeedbackWidget - Sprint 2 functionality.
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.utils.enhanced_feedback_widget import EnhancedFeedbackWidget
from app.utils.feedback_db import insert_feedback
from app.utils.db_migrations import apply_pending_migrations


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    try:
        Path(path).unlink()
        apply_pending_migrations(path)
        yield path
    finally:
        if Path(path).exists():
            Path(path).unlink()


class TestEnhancedFeedbackWidget:
    """Test the enhanced feedback widget functionality."""
    
    @patch('app.utils.enhanced_feedback_widget.insert_feedback')
    def test_positive_feedback(self, mock_insert):
        """Test positive feedback flow."""
        mock_insert.return_value = True
        
        widget = EnhancedFeedbackWidget(
            query="What is the average BMI?",
            original_intent_json='{"analysis_type": "average", "target_field": "bmi"}'
        )
        
        # Simulate thumbs up click
        widget._on_thumbs_up(None)
        
        # Verify feedback was recorded
        mock_insert.assert_called_once_with(
            question="What is the average BMI?",
            rating="up"
        )
        
        # Verify UI state
        assert widget.feedback_submitted
        assert widget.thank_you_section.visible

    @patch('app.utils.enhanced_feedback_widget.insert_feedback')
    def test_negative_feedback_flow(self, mock_insert):
        """Test negative feedback flow with correction capture."""
        mock_insert.return_value = True
        
        # Mock the feedback ID retrieval
        with patch.object(EnhancedFeedbackWidget, '_get_latest_feedback_id', return_value=123):
            widget = EnhancedFeedbackWidget(
                query="What is the average BMI?",
                original_intent_json='{"analysis_type": "average", "target_field": "bmi"}',
                original_code="SELECT AVG(bmi) FROM vitals"
            )
            
            # Simulate thumbs down click
            widget._on_thumbs_down(None)
            
            # Verify feedback was recorded
            mock_insert.assert_called_once_with(
                question="What is the average BMI?",
                rating="down"
            )
            
            # Verify correction interface is shown
            assert not widget.feedback_section.visible
            assert widget.correction_section.visible

    def test_correction_submission(self, temp_db):
        """Test correction submission functionality."""
        # Create widget with mock correction service
        with patch('app.utils.enhanced_feedback_widget.CorrectionService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.capture_correction_session.return_value = 456
            
            widget = EnhancedFeedbackWidget(
                query="What is the average BMI?",
                original_intent_json='{"analysis_type": "average", "target_field": "bmi"}'
            )
            widget.feedback_id = 123
            
            # Set correction text
            widget.correct_answer_input.value = "Should only include active patients"
            
            # Submit correction
            widget._on_submit_correction(None)
            
            # Verify correction session was created
            mock_service.capture_correction_session.assert_called_once()
            
            # Verify UI shows analysis section
            assert widget.analysis_section.visible

    def test_skip_correction(self):
        """Test skipping correction goes to thank you."""
        widget = EnhancedFeedbackWidget(query="Test query")
        
        widget._on_skip_correction(None)
        
        assert widget.thank_you_section.visible
        assert widget.feedback_submitted
```

Add error analysis tests to `tests/services/test_correction_service_basic.py`:

```python
def test_analyze_error_type_missing_filter(self, correction_service, temp_db):
    """Test error analysis for missing filter errors."""
    # Insert feedback
    insert_feedback(
        question="What is the average BMI of active patients?",
        rating="down",
        db_file=temp_db
    )
    
    # Get feedback ID and create session
    with sqlite3.connect(temp_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1")
        feedback_id = cursor.fetchone()[0]
    
    # Create correction session with intent missing active filter
    intent_json = json.dumps({
        "analysis_type": "average",
        "target_field": "bmi",
        "filters": [],  # Missing the active=1 filter
        "conditions": [],
        "parameters": {}
    })
    
    session_id = correction_service.capture_correction_session(
        feedback_id=feedback_id,
        original_query="What is the average BMI of active patients?",
        human_correct_answer="Should only include active patients",
        original_intent_json=intent_json
    )
    
    # Analyze the error
    error_category = correction_service.analyze_error_type(session_id)
    
    assert error_category == "missing_filter"
    
    # Verify the session was updated
    session = correction_service.get_correction_session(session_id)
    assert session.error_category == "missing_filter"
    assert session.correction_type == "intent_fix"

def test_generate_correction_suggestions(self, correction_service, temp_db):
    """Test generating correction suggestions."""
    # Create a correction session with missing filter error
    insert_feedback(
        question="Average BMI of active patients",
        rating="down",
        db_file=temp_db
    )
    
    with sqlite3.connect(temp_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1")
        feedback_id = cursor.fetchone()[0]
    
    session_id = correction_service.capture_correction_session(
        feedback_id=feedback_id,
        original_query="Average BMI of active patients",
        human_correct_answer="Should filter for active patients only"
    )
    
    # Update with error category
    correction_service.update_correction_session(session_id, {
        "error_category": "missing_filter",
        "correction_type": "intent_fix"
    })
    
    # Generate suggestions
    suggestions = correction_service.generate_correction_suggestions(session_id)
    
    assert len(suggestions) > 0
    assert any(s['type'] == 'add_filter' for s in suggestions)
    assert any(s['type'] == 'manual_correction' for s in suggestions)
```

## SUCCESS CRITERIA

You are done when:
- [ ] Enhanced feedback widget displays correctly in place of basic feedback
- [ ] Thumbs up feedback works exactly as before
- [ ] Thumbs down opens correction interface with text input
- [ ] Users can submit corrections successfully 
- [ ] Correction sessions are stored in database
- [ ] Basic error analysis categorizes common error types
- [ ] All existing functionality remains intact
- [ ] Comprehensive tests pass
- [ ] UI is intuitive and user-friendly

## DEVELOPMENT WORKFLOW

1. **Create enhanced feedback widget** - Start with UI components and basic functionality
2. **Add error analysis to CorrectionService** - Enhance with analysis methods
3. **Integrate with DataAnalysisAssistant** - Replace existing feedback widget
4. **Create comprehensive tests** - Test all new functionality
5. **Verify UI integration** - Ensure seamless user experience
6. **Run full test suite** - Ensure no breaking changes

## TESTING & GITHUB WORKFLOW

After completing implementation:

1. **Run the full test suite**:
   ```bash
   pytest tests/ -v
   pytest tests/utils/test_enhanced_feedback_widget.py -v
   pytest tests/services/test_correction_service_basic.py -v
   ```

2. **Test UI manually**:
   ```bash
   python run.py
   # Navigate to assistant, try queries, test both thumbs up and thumbs down
   ```

3. **Verify database integration**:
   ```bash
   python -c "from app.services.correction_service import CorrectionService; cs = CorrectionService(); print('Service initialized successfully')"
   ```

4. **Commit and push changes**:
   ```bash
   git add .
   git commit -m "Sprint 2: Add enhanced feedback UI with correction capture

   - Implement EnhancedFeedbackWidget with correction interface
   - Add error analysis and categorization to CorrectionService  
   - Replace basic feedback widgets in DataAnalysisAssistant
   - Add comprehensive tests for feedback workflow
   - Users can now provide detailed corrections after thumbs down
   - Basic error analysis categorizes common mistakes"
   
   git push origin main
   ```

## IMPORTANT NOTES

- **UI Consistency**: Maintain existing look and feel while adding new functionality
- **Error Handling**: Graceful degradation when correction service unavailable
- **User Experience**: Clear guidance for correction input
- **Data Validation**: Sanitize and validate user correction input
- **Logging**: Comprehensive logging for debugging and monitoring

## DEPENDENCIES ON SPRINT 1

This sprint builds directly on Sprint 1:
- Uses `CorrectionService` from Sprint 1
- Stores data in tables created in Sprint 1
- Extends basic functionality with UI components

## WHEN YOU'RE STUCK

If you encounter issues:
1. **Verify Sprint 1 completion** - Ensure all Sprint 1 components work
2. **Start with basic UI** - Get feedback widget working before adding complexity
3. **Mock complex dependencies** - Use mocks for testing when needed
4. **Maintain backward compatibility** - Never break existing functionality

---

**START IMPLEMENTING SPRINT 2 NOW** 