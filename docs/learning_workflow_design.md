# Enhanced Learning Workflow Design for AAA

## Overview
This document outlines the enhanced learning workflow for the Ask Anything AI Assistant (AAA) to achieve >90% accuracy through iterative improvement.

## Core Learning Loop

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Incorrect Answer│───▶│ Human Review &   │───▶│ Correction      │
│ (Thumbs Down)   │    │ Correct Answer   │    │ Integration     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         ▲                       │                         │
         │                       ▼                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ User Re-queries │◀───│ Pattern Storage  │◀───│ Knowledge Update│
│ (Test Success)  │    │ & Validation     │    │ & Enhancement   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Detailed Correction Process

### Phase 1: Error Detection & Capture
**Trigger:** User clicks thumbs down feedback button

**Files Involved:**
- `app/data_assistant.py::_record_feedback()` - Captures initial feedback
- `app/utils/feedback_db.py::insert_feedback()` - Stores feedback with metadata
- `migrations/005_add_feedback_table.sql` - Feedback table structure

**Enhanced Data Capture:**
```python
# Extended feedback table structure
CREATE TABLE IF NOT EXISTS correction_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feedback_id INTEGER,
    original_query TEXT NOT NULL,
    original_intent_json TEXT,
    original_code TEXT,
    original_results TEXT,
    human_correct_answer TEXT,
    correction_type TEXT, -- 'intent_fix', 'code_fix', 'logic_fix'
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending', -- 'pending', 'integrated', 'validated'
    FOREIGN KEY (feedback_id) REFERENCES assistant_feedback(id)
);
```

### Phase 2: Human Review Interface
**New Component:** `app/services/correction_service.py`

**Key Functions:**
```python
class CorrectionService:
    def capture_correction_session(self, feedback_id: int, correct_answer: str) -> int
    def analyze_error_type(self, session_id: int) -> str  
    def generate_correction_suggestions(self, session_id: int) -> List[Dict]
    def apply_correction(self, session_id: int, correction_type: str) -> bool
```

**Files to Create:**
- `app/pages/correction_interface.py` - UI for correction review
- `app/utils/error_analysis.py` - Automated error categorization
- `app/utils/correction_patterns.py` - Pattern matching for similar errors

### Phase 3: Knowledge Integration

#### 3a. Intent Pattern Learning
**Files Involved:**
- `app/utils/query_intent.py::inject_learned_patterns()` - New function
- `app/utils/ai/intent_parser.py::enhance_with_examples()` - Enhanced prompting

**Learning Mechanism:**
```python
# New table for intent pattern storage
CREATE TABLE IF NOT EXISTS intent_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_pattern TEXT NOT NULL,
    canonical_intent_json TEXT NOT NULL,
    confidence_boost REAL DEFAULT 0.1,
    usage_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

#### 3b. Code Template Enhancement  
**Files Involved:**
- `app/utils/ai/codegen/templates.py` - New deterministic templates
- `app/utils/ai/code_generator.py::enhance_with_templates()` - Template matching

**Template Storage:**
```python
# Code pattern templates based on corrections
CREATE TABLE IF NOT EXISTS code_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_signature TEXT NOT NULL, -- JSON schema of intent pattern
    template_code TEXT NOT NULL,
    template_description TEXT,
    success_rate REAL DEFAULT 1.0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

#### 3c. Query Routing Enhancement
**Files Involved:**
- `app/utils/query_router.py` - New routing logic (to create)
- `app/engine.py::enhanced_process_query()` - Updated main flow

**Routing Logic:**
1. Check exact match in `saved_questions` (100% confidence)
2. Check semantic similarity to corrected patterns (high confidence)
3. Check template applicability (medium confidence)  
4. Fall back to LLM with enhanced examples (variable confidence)

### Phase 4: Validation & Testing

#### Automated Validation
**Files to Create:**
- `tests/learning/test_correction_integration.py` - Correction workflow tests
- `scripts/validation/validate_corrections.py` - Batch validation tool

**Validation Process:**
```python
class CorrectionValidator:
    def validate_correction(self, session_id: int) -> ValidationResult
    def run_regression_tests(self) -> List[TestResult]  
    def measure_improvement_metrics(self) -> Dict[str, float]
```

#### Performance Tracking
**Files Involved:**
- `app/utils/evaluation_framework.py` - Enhanced with correction metrics
- `scripts/analytics/correction_analytics.py` - New analytics tools

**Key Metrics:**
- Correction success rate
- Pattern matching effectiveness  
- Template usage statistics
- Query confidence improvement over time

## Implementation Phases

### Phase 1: Enhanced Feedback Capture (Week 1-2)
1. Extend feedback database schema
2. Create correction session capture
3. Build human review interface
4. Add error categorization

### Phase 2: Pattern Learning System (Week 3-4)  
1. Implement intent pattern storage
2. Create template matching system
3. Build query routing logic
4. Add similarity detection

### Phase 3: Integration & Testing (Week 5-6)
1. Integrate learning into main workflow
2. Create validation framework
3. Build regression testing
4. Performance monitoring

### Phase 4: Optimization & Scaling (Week 7-8)
1. Performance tuning
2. Advanced pattern matching
3. Confidence scoring refinement
4. Documentation and training

## Success Metrics

**Primary KPIs:**
- Query accuracy rate: Target >90%
- First-time resolution rate: Target >85%
- Correction integration success: Target >95%
- Time to correct answer: Target <30 seconds

**Secondary Metrics:**
- Pattern matching hit rate
- Template usage effectiveness
- Confidence score correlation with accuracy
- User satisfaction scores

## Risk Mitigation

**Data Quality:**
- Human correction validation
- Peer review process for complex corrections
- Automated sanity checking

**Performance:**
- Lazy loading of patterns and templates
- Caching of frequently used corrections
- Background processing of learning updates

**Security:**
- Sanitization of human-provided corrections
- Code template validation
- Sandbox execution maintained

This workflow design provides a comprehensive, systematic approach to learning from corrections while maintaining the modularity and stability of the existing codebase. 