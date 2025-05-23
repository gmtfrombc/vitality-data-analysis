# SPRINT 3 PROMPT - Error Analysis & Automated Suggestions

## PROJECT CONTEXT

You are working on the **AAA Learning Enhancements Project** - adding automated learning capabilities to the Ask Anything AI Assistant (AAA). This is Sprint 3 of a 5-sprint project.

### Project Overview
The AAA is a healthcare data analysis assistant that converts natural language queries to SQL. We're building an automated learning system that captures user corrections, analyzes errors, and learns patterns for improved accuracy.

### Previous Sprint Completions

✅ **Sprint 1 COMPLETED** - Database foundation and basic correction service:
- Database tables: `correction_sessions`, `intent_patterns`, `code_templates`, `learning_metrics`, `query_similarity_cache`
- Basic `CorrectionService` with CRUD operations
- Data models: `CorrectionSession`, `IntentPattern`

✅ **Sprint 2 COMPLETED** - Enhanced feedback UI with correction capture:
- `EnhancedFeedbackWidget` with correction interface
- UI integration replacing basic feedback widgets  
- Basic error analysis methods in `CorrectionService`
- Users can now provide detailed corrections after thumbs down

## SPRINT 3 OBJECTIVES

**Goal**: Enhance error analysis with sophisticated categorization and implement intelligent automated suggestions that users can apply with one click.

**Key Deliverables**:
1. Sophisticated error analysis with detailed categorization
2. Intelligent automated suggestion generation
3. One-click suggestion application functionality
4. Enhanced UI showing suggestions with descriptions
5. Improved user guidance for corrections

**User Impact**: Users receive specific, actionable suggestions for fixing errors rather than generic messages.

## TECHNICAL REQUIREMENTS

### Enhanced Error Analysis

Enhance `app/services/correction_service.py` with sophisticated analysis:

```python
def analyze_error_type(self, session_id: int) -> str:
    """Enhanced error analysis with sophisticated categorization.
    
    Args:
        session_id: The correction session ID
        
    Returns:
        The determined error category with detailed reasoning
    """
    session = self.get_correction_session(session_id)
    if not session:
        return "unknown"
    
    error_category = "unknown"
    analysis_context = {}
    
    # Analyze intent-related errors
    if session.original_intent_json:
        intent_analysis = self._analyze_intent_errors(session)
        error_category = intent_analysis.get("category", "unknown")
        analysis_context.update(intent_analysis.get("context", {}))
    
    # Analyze code-related errors  
    if session.original_code and error_category == "unknown":
        code_analysis = self._analyze_code_errors(session)
        error_category = code_analysis.get("category", "unknown")
        analysis_context.update(code_analysis.get("context", {}))
    
    # Analyze results-related errors
    if session.original_results and error_category == "unknown":
        results_analysis = self._analyze_results_errors(session)
        error_category = results_analysis.get("category", "unknown")
        analysis_context.update(results_analysis.get("context", {}))
    
    # Store detailed analysis
    self.update_correction_session(session_id, {
        "error_category": error_category,
        "correction_type": self._infer_correction_type(error_category),
        "analysis_context": json.dumps(analysis_context) if analysis_context else None
    })
    
    logger.info(f"Enhanced analysis for session {session_id}: {error_category} with context {analysis_context}")
    return error_category

def _analyze_intent_errors(self, session: CorrectionSession) -> Dict[str, Any]:
    """Analyze intent-related errors with detailed context."""
    try:
        from app.utils.query_intent import parse_intent_json
        intent = parse_intent_json(session.original_intent_json)
        
        analysis = {"category": "unknown", "context": {}}
        
        # Missing filter analysis
        if self._is_missing_filter_error(session, intent):
            analysis["category"] = "missing_filter"
            analysis["context"] = {
                "query_mentions": self._extract_filter_mentions(session.original_query),
                "missing_filters": self._identify_missing_filters(session.original_query, intent),
                "suggested_values": self._suggest_filter_values(session)
            }
        
        # Wrong aggregation analysis
        elif self._is_wrong_aggregation_error(session, intent):
            analysis["category"] = "wrong_aggregation"
            analysis["context"] = {
                "current_type": intent.analysis_type,
                "suggested_type": self._infer_correct_analysis_type(session.human_correct_answer),
                "reasoning": self._explain_aggregation_choice(session)
            }
        
        # Unclear target analysis
        elif intent.target_field == "unknown" or intent.target_field == "":
            analysis["category"] = "unclear_target"
            analysis["context"] = {
                "possible_targets": self._extract_possible_targets(session.original_query),
                "suggested_target": self._suggest_target_field(session.human_correct_answer)
            }
        
        # Ambiguous intent analysis
        elif intent.analysis_type == "unknown":
            analysis["category"] = "ambiguous_intent"
            analysis["context"] = {
                "query_keywords": self._extract_intent_keywords(session.original_query),
                "suggested_intent": self._infer_intent_from_correction(session.human_correct_answer)
            }
        
        return analysis
        
    except Exception as e:
        logger.warning(f"Failed to analyze intent errors: {e}")
        return {"category": "intent_parse_error", "context": {"error": str(e)}}

def _analyze_code_errors(self, session: CorrectionSession) -> Dict[str, Any]:
    """Analyze code-related errors with detailed context."""
    analysis = {"category": "unknown", "context": {}}
    code = session.original_code.upper()
    correction = session.human_correct_answer.lower()
    
    # Missing GROUP BY analysis
    if "GROUP BY" not in code and any(keyword in correction for keyword in ["group", "by category", "breakdown"]):
        analysis["category"] = "missing_groupby"
        analysis["context"] = {
            "suggested_groupby": self._suggest_groupby_fields(session),
            "why_needed": "User requested breakdown/grouping in correction"
        }
    
    # Missing WHERE clause analysis
    elif "WHERE" not in code and any(keyword in correction for keyword in ["filter", "only", "exclude", "include"]):
        analysis["category"] = "missing_where"
        analysis["context"] = {
            "suggested_filters": self._suggest_where_conditions(session),
            "filter_reasoning": self._explain_filter_need(session)
        }
    
    # Join issues analysis
    elif "JOIN" in code and "wrong" in correction:
        analysis["category"] = "incorrect_join"
        analysis["context"] = {
            "current_joins": self._extract_joins(code),
            "suggested_approach": self._suggest_join_fix(session)
        }
    
    # General logic errors
    else:
        analysis["category"] = "code_logic_error"
        analysis["context"] = {
            "code_issues": self._identify_code_issues(session),
            "suggested_fixes": self._suggest_code_fixes(session)
        }
    
    return analysis

def _analyze_results_errors(self, session: CorrectionSession) -> Dict[str, Any]:
    """Analyze results-related errors."""
    analysis = {"category": "unknown", "context": {}}
    
    try:
        results = json.loads(session.original_results) if session.original_results else {}
        correction = session.human_correct_answer.lower()
        
        # Incorrect calculation
        if any(keyword in correction for keyword in ["wrong number", "incorrect calculation", "should be"]):
            analysis["category"] = "calculation_error"
            analysis["context"] = {
                "current_result": results,
                "error_type": self._identify_calculation_error(session),
                "suggested_fix": self._suggest_calculation_fix(session)
            }
        
        # Missing data points
        elif "missing" in correction or "incomplete" in correction:
            analysis["category"] = "incomplete_data"
            analysis["context"] = {
                "current_coverage": self._analyze_data_coverage(results),
                "missing_elements": self._identify_missing_data(session)
            }
            
        return analysis
        
    except Exception as e:
        logger.warning(f"Failed to analyze results errors: {e}")
        return {"category": "results_parse_error", "context": {"error": str(e)}}

# Helper methods for detailed analysis
def _is_missing_filter_error(self, session: CorrectionSession, intent) -> bool:
    """Check if this is a missing filter error."""
    query_lower = session.original_query.lower()
    correction_lower = session.human_correct_answer.lower()
    
    # Query mentions filtering but intent has no filters
    mentions_filter = any(word in query_lower for word in ["active", "inactive", "current", "recent"])
    has_filters = intent.filters and len(intent.filters) > 0
    correction_mentions_filter = any(word in correction_lower for word in ["filter", "only", "exclude", "active"])
    
    return mentions_filter and not has_filters and correction_mentions_filter

def _extract_filter_mentions(self, query: str) -> List[str]:
    """Extract filter-related terms from query."""
    filter_terms = ["active", "inactive", "current", "recent", "male", "female", "over", "under", "above", "below"]
    found_terms = []
    query_lower = query.lower()
    
    for term in filter_terms:
        if term in query_lower:
            found_terms.append(term)
    
    return found_terms

def _suggest_filter_values(self, session: CorrectionSession) -> Dict[str, Any]:
    """Suggest appropriate filter values based on context."""
    suggestions = {}
    query_lower = session.original_query.lower()
    
    if "active" in query_lower:
        suggestions["active"] = 1
    if "inactive" in query_lower:
        suggestions["active"] = 0
    if "male" in query_lower:
        suggestions["gender"] = "M"
    if "female" in query_lower:
        suggestions["gender"] = "F"
    
    return suggestions
```

### Intelligent Suggestion Generation

Enhance suggestion generation with detailed, actionable suggestions:

```python
def generate_correction_suggestions(self, session_id: int) -> List[Dict[str, Any]]:
    """Generate intelligent, actionable correction suggestions.
    
    Args:
        session_id: The correction session ID
        
    Returns:
        List of detailed correction suggestions with application instructions
    """
    session = self.get_correction_session(session_id)
    if not session:
        return []
    
    suggestions = []
    
    # Get analysis context if available
    context = {}
    if session.analysis_context:
        try:
            context = json.loads(session.analysis_context)
        except:
            pass
    
    # Generate category-specific suggestions
    if session.error_category == "missing_filter":
        suggestions.extend(self._generate_filter_suggestions(session, context))
    
    elif session.error_category == "wrong_aggregation":
        suggestions.extend(self._generate_aggregation_suggestions(session, context))
    
    elif session.error_category == "unclear_target":
        suggestions.extend(self._generate_target_suggestions(session, context))
    
    elif session.error_category == "missing_groupby":
        suggestions.extend(self._generate_groupby_suggestions(session, context))
    
    elif session.error_category == "code_logic_error":
        suggestions.extend(self._generate_code_fix_suggestions(session, context))
    
    # Always provide manual correction option
    suggestions.append({
        "id": f"manual_{session_id}",
        "type": "manual_correction",
        "title": "Manual Review",
        "description": "Manually review and correct the analysis",
        "action_type": "manual",
        "confidence": 1.0,
        "estimated_effort": "Medium",
        "application_steps": [
            "Review the original query and correct answer",
            "Manually adjust the analysis approach",
            "Re-run the analysis with corrections"
        ]
    })
    
    # Sort by confidence score
    suggestions.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    
    return suggestions

def _generate_filter_suggestions(self, session: CorrectionSession, context: Dict) -> List[Dict]:
    """Generate filter-related suggestions."""
    suggestions = []
    
    # Specific filter suggestions based on context
    if "missing_filters" in context:
        for filter_field, suggested_value in context.get("suggested_values", {}).items():
            suggestions.append({
                "id": f"add_filter_{filter_field}_{session.id}",
                "type": "add_filter",
                "title": f"Add {filter_field.title()} Filter",
                "description": f"Add filter: {filter_field} = {suggested_value}",
                "action_type": "intent_modification",
                "confidence": 0.85,
                "estimated_effort": "Low",
                "application_data": {
                    "filter_field": filter_field,
                    "filter_value": suggested_value,
                    "filter_operator": "="
                },
                "application_steps": [
                    f"Add Filter(field='{filter_field}', value={suggested_value}) to intent.filters",
                    "Re-generate SQL with updated intent",
                    "Re-run analysis with filtered data"
                ]
            })
    
    return suggestions

def _generate_aggregation_suggestions(self, session: CorrectionSession, context: Dict) -> List[Dict]:
    """Generate aggregation-related suggestions."""
    suggestions = []
    
    current_type = context.get("current_type", "unknown")
    suggested_type = context.get("suggested_type", "distribution")
    
    suggestions.append({
        "id": f"change_aggregation_{session.id}",
        "type": "change_analysis_type",
        "title": f"Change to {suggested_type.title()} Analysis",
        "description": f"Change from {current_type} to {suggested_type}",
        "action_type": "intent_modification",
        "confidence": 0.90,
        "estimated_effort": "Low",
        "application_data": {
            "new_analysis_type": suggested_type,
            "reasoning": context.get("reasoning", "Based on user correction")
        },
        "application_steps": [
            f"Update intent.analysis_type to '{suggested_type}'",
            "Re-generate code for new analysis type",
            "Re-run analysis with updated approach"
        ]
    })
    
    return suggestions

def _generate_target_suggestions(self, session: CorrectionSession, context: Dict) -> List[Dict]:
    """Generate target field suggestions."""
    suggestions = []
    
    possible_targets = context.get("possible_targets", [])
    suggested_target = context.get("suggested_target", "")
    
    if suggested_target:
        suggestions.append({
            "id": f"set_target_{suggested_target}_{session.id}",
            "type": "set_target_field",
            "title": f"Set Target Field to {suggested_target.title()}",
            "description": f"Analyze {suggested_target} instead of current target",
            "action_type": "intent_modification",
            "confidence": 0.80,
            "estimated_effort": "Low",
            "application_data": {
                "target_field": suggested_target
            },
            "application_steps": [
                f"Update intent.target_field to '{suggested_target}'",
                "Re-generate SQL for new target field",
                "Re-run analysis"
            ]
        })
    
    return suggestions

def apply_correction(self, session_id: int, suggestion_id: str) -> Dict[str, Any]:
    """Apply a correction suggestion to fix the identified error.
    
    Args:
        session_id: The correction session ID
        suggestion_id: The ID of the suggestion to apply
        
    Returns:
        Result of applying the correction
    """
    session = self.get_correction_session(session_id)
    suggestions = self.generate_correction_suggestions(session_id)
    
    # Find the selected suggestion
    suggestion = next((s for s in suggestions if s["id"] == suggestion_id), None)
    if not suggestion:
        return {"success": False, "error": "Suggestion not found"}
    
    try:
        result = {"success": False, "suggestion": suggestion}
        
        if suggestion["action_type"] == "intent_modification":
            result = self._apply_intent_modification(session, suggestion)
        
        elif suggestion["action_type"] == "code_modification":
            result = self._apply_code_modification(session, suggestion)
        
        elif suggestion["action_type"] == "manual":
            result = {"success": True, "message": "Manual review recommended"}
        
        # Update session status if successful
        if result.get("success"):
            self.update_correction_session(session_id, {
                "status": "integrated",
                "reviewed_at": datetime.now().isoformat()
            })
            
            # Learn from successful application
            self._learn_from_correction(session, suggestion)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to apply correction {suggestion_id}: {e}")
        return {"success": False, "error": str(e)}

def _apply_intent_modification(self, session: CorrectionSession, suggestion: Dict) -> Dict:
    """Apply an intent modification suggestion."""
    if not session.original_intent_json:
        return {"success": False, "error": "No original intent to modify"}
    
    try:
        from app.utils.query_intent import parse_intent_json
        intent = parse_intent_json(session.original_intent_json)
        
        app_data = suggestion.get("application_data", {})
        
        # Apply the specific modification
        if suggestion["type"] == "add_filter":
            # Add filter to intent
            new_filter = {
                "field": app_data["filter_field"],
                "value": app_data["filter_value"],
                "operator": app_data.get("filter_operator", "=")
            }
            if not hasattr(intent, 'filters') or not intent.filters:
                intent.filters = []
            intent.filters.append(new_filter)
        
        elif suggestion["type"] == "change_analysis_type":
            intent.analysis_type = app_data["new_analysis_type"]
        
        elif suggestion["type"] == "set_target_field":
            intent.target_field = app_data["target_field"]
        
        # Store the corrected intent
        corrected_intent_json = json.dumps(intent.model_dump() if hasattr(intent, 'model_dump') else intent.__dict__)
        
        self.update_correction_session(session.id, {
            "corrected_intent_json": corrected_intent_json
        })
        
        return {
            "success": True, 
            "corrected_intent": corrected_intent_json,
            "message": f"Successfully applied {suggestion['title']}"
        }
        
    except Exception as e:
        return {"success": False, "error": f"Failed to modify intent: {e}"}
```

### Enhanced UI Integration

Update `app/utils/enhanced_feedback_widget.py` to show intelligent suggestions:

```python
def _show_enhanced_analysis(self):
    """Show enhanced analysis with intelligent suggestions."""
    if not self.correction_session_id:
        self._show_thank_you()
        return
    
    try:
        # Perform error analysis
        error_category = self.correction_service.analyze_error_type(self.correction_session_id)
        
        # Generate suggestions
        suggestions = self.correction_service.generate_correction_suggestions(self.correction_session_id)
        
        # Update analysis section with suggestions
        self._display_suggestions(error_category, suggestions)
        
        self.correction_section.visible = False
        self.analysis_section.visible = True
        
    except Exception as e:
        logger.error(f"Failed to show enhanced analysis: {e}")
        self._show_thank_you()

def _display_suggestions(self, error_category: str, suggestions: List[Dict]):
    """Display suggestions in the UI."""
    # Clear existing analysis section
    self.analysis_section.clear()
    
    # Add header
    self.analysis_section.append(
        pn.pane.Markdown("### 🔍 Error Analysis & Suggestions", margin=(10, 0, 5, 0))
    )
    
    # Add error category explanation
    category_text = self._get_category_explanation(error_category)
    self.analysis_section.append(
        pn.pane.Markdown(f"**Issue Detected:** {category_text}", margin=(0, 0, 10, 0))
    )
    
    # Add suggestions
    if suggestions:
        self.analysis_section.append(
            pn.pane.Markdown("**Suggested Fixes:**", margin=(0, 0, 5, 0))
        )
        
        for i, suggestion in enumerate(suggestions[:3]):  # Show top 3 suggestions
            suggestion_widget = self._create_suggestion_widget(suggestion)
            self.analysis_section.append(suggestion_widget)
    
    # Add skip option
    skip_btn = pn.widgets.Button(
        name="Skip Suggestions",
        button_type="light",
        width=150,
        margin=(10, 0, 0, 0)
    )
    skip_btn.on_click(lambda event: self._show_thank_you())
    self.analysis_section.append(skip_btn)

def _create_suggestion_widget(self, suggestion: Dict) -> pn.Column:
    """Create a widget for a single suggestion."""
    confidence_color = "success" if suggestion["confidence"] > 0.8 else "warning" if suggestion["confidence"] > 0.6 else "light"
    
    apply_btn = pn.widgets.Button(
        name=f"Apply: {suggestion['title']}",
        button_type=confidence_color,
        width=200,
        margin=(5, 0)
    )
    
    # Store suggestion ID for application
    apply_btn.suggestion_id = suggestion["id"]
    apply_btn.on_click(self._on_apply_suggestion)
    
    suggestion_widget = pn.Column(
        pn.pane.Markdown(f"**{suggestion['title']}** (Confidence: {suggestion['confidence']:.0%})", margin=(5, 0, 0, 0)),
        pn.pane.Markdown(suggestion['description'], margin=(0, 0, 5, 0)),
        apply_btn,
        styles={'border': '1px solid #dee2e6', 'padding': '10px', 'margin': '5px 0', 'border-radius': '5px'}
    )
    
    return suggestion_widget

def _on_apply_suggestion(self, event):
    """Handle applying a suggestion."""
    suggestion_id = event.obj.suggestion_id
    
    try:
        result = self.correction_service.apply_correction(self.correction_session_id, suggestion_id)
        
        if result.get("success"):
            # Show success message
            success_widget = pn.pane.Markdown(
                f"✅ **Applied Successfully!** {result.get('message', '')}", 
                margin=(10, 0)
            )
            self.analysis_section.append(success_widget)
            
            # Trigger callback if provided
            if self.on_correction_applied:
                self.on_correction_applied(self.correction_session_id, result.get("suggestion", {}))
            
            # Auto-proceed to thank you
            pn.state.add_periodic_callback(lambda: self._show_thank_you(), 2000, count=1)
        else:
            # Show error message
            error_widget = pn.pane.Markdown(
                f"❌ **Failed to apply:** {result.get('error', 'Unknown error')}", 
                margin=(10, 0)
            )
            self.analysis_section.append(error_widget)
            
    except Exception as e:
        logger.error(f"Error applying suggestion: {e}")
        error_widget = pn.pane.Markdown(
            f"❌ **Error:** {str(e)}", 
            margin=(10, 0)
        )
        self.analysis_section.append(error_widget)
```

## FILES TO CREATE/MODIFY

### Files to Modify
```
app/services/correction_service.py (enhance error analysis and suggestions)
app/utils/enhanced_feedback_widget.py (add suggestions UI)
tests/services/test_correction_service_basic.py (expand tests)
```

### Files to Create
```
tests/services/test_error_analysis.py
tests/integration/test_correction_workflow.py
```

## SUCCESS CRITERIA

You are done when:
- [ ] Error analysis accurately categorizes 80%+ of common error types
- [ ] Suggestions are specific and actionable with clear application steps
- [ ] Users can apply suggestions with one click
- [ ] Suggestion application works correctly and updates the system
- [ ] Manual correction option is always available
- [ ] UI provides clear guidance and feedback
- [ ] All existing functionality remains intact
- [ ] Comprehensive tests pass
- [ ] System learns from successful corrections

## TESTING & GITHUB WORKFLOW

After completing implementation:

1. **Run the enhanced test suite**:
   ```bash
   pytest tests/services/test_error_analysis.py -v
   pytest tests/integration/test_correction_workflow.py -v
   pytest tests/ -v
   ```

2. **Test correction workflow manually**:
   ```bash
   python run.py
   # Test various error scenarios and suggestion applications
   ```

3. **Commit and push changes**:
   ```bash
   git add .
   git commit -m "Sprint 3: Add sophisticated error analysis and automated suggestions

   - Enhance error analysis with detailed categorization and context
   - Implement intelligent suggestion generation with confidence scores
   - Add one-click suggestion application functionality
   - Enhance UI with detailed suggestions and application status
   - Users can now receive and apply specific, actionable corrections
   - System learns from successful corrections for future improvements"
   
   git push origin main
   ```

---

**START IMPLEMENTING SPRINT 3 NOW** 