# AAA Learning System Implementation

## Overview

This document outlines the implementation of the enhanced learning system for the Ask Anything AI Assistant (AAA). The system enables continuous improvement through user feedback, correction capture, and automated pattern learning.

## System Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     AAA Learning System                        │
├─────────────────────────────────────────────────────────────────┤
│  Enhanced Feedback    │  Correction       │  Pattern Learning  │
│  Widget              │  Service          │  Engine            │
│                      │                   │                    │
│  • Thumbs up/down    │  • Error analysis │  • Intent patterns │
│  • Correction input  │  • Categorization │  • Code templates  │
│  • Suggestions UI   │  • Auto-suggestions│  • Similarity match│
└─────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │     Database Tables      │
                    │                         │
                    │ • correction_sessions   │
                    │ • intent_patterns      │
                    │ • code_templates       │
                    │ • learning_metrics     │
                    └─────────────────────────┘
```

## Key Features

### 1. Enhanced Feedback Collection
- **File**: `app/utils/enhanced_feedback_widget.py`
- **Purpose**: Captures detailed user corrections beyond simple thumbs up/down
- **Features**:
  - Interactive correction interface
  - Real-time error analysis
  - Automated suggestion generation
  - Progress tracking

### 2. Intelligent Error Analysis
- **File**: `app/services/correction_service.py`
- **Purpose**: Analyzes errors and categorizes them for targeted learning
- **Categories**:
  - `missing_filter` - Query missing patient status/demographic filters
  - `wrong_aggregation` - Incorrect analysis type (avg vs distribution)
  - `unclear_target` - Ambiguous target field
  - `missing_groupby` - Missing grouping in generated code
  - `code_logic_error` - General code generation issues

### 3. Pattern Learning & Storage
- **Tables**: `intent_patterns`, `code_templates`
- **Purpose**: Store successful corrections as reusable patterns
- **Matching**: Semantic similarity for query routing

### 4. Automated Suggestions
- **Purpose**: Provide specific, actionable correction suggestions
- **Types**:
  - Add missing filters
  - Change analysis types
  - Include grouping clauses
  - Manual review options

## Database Schema

### Correction Sessions
```sql
CREATE TABLE correction_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feedback_id INTEGER,
    original_query TEXT NOT NULL,
    original_intent_json TEXT,
    original_code TEXT,
    original_results TEXT,
    human_correct_answer TEXT,
    correction_type TEXT,
    error_category TEXT,
    status TEXT DEFAULT 'pending',
    reviewed_by TEXT,
    reviewed_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### Learned Patterns
```sql
CREATE TABLE intent_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_pattern TEXT NOT NULL,
    canonical_intent_json TEXT NOT NULL,
    confidence_boost REAL DEFAULT 0.1,
    usage_count INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 1.0,
    created_from_session_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_used_at TEXT
);
```

## Usage Examples

### 1. Basic Integration

```python
from app.utils.enhanced_feedback_widget import create_enhanced_feedback_widget

# Create enhanced feedback widget
feedback_widget = create_enhanced_feedback_widget(
    query="What is the average BMI?",
    original_intent_json=json.dumps(intent.model_dump()),
    original_code=generated_code,
    original_results=json.dumps(results),
    on_correction_applied=handle_correction_callback
)

# Add to your Panel layout
layout.append(feedback_widget)
```

### 2. Query Enhancement with Pattern Matching

```python
from app.services.correction_service import CorrectionService

# Check for learned patterns before LLM processing
correction_service = CorrectionService()
similar_patterns = correction_service.find_similar_patterns(user_query)

if similar_patterns:
    # Use learned pattern with confidence boost
    learned_intent = json.loads(similar_patterns[0].canonical_intent_json)
    confidence_boost = similar_patterns[0].confidence_boost
    # Process with enhanced confidence
else:
    # Fall back to normal LLM processing
    intent = ai_helper.get_query_intent(user_query)
```

### 3. Correction Workflow

```python
# In your feedback handler
def handle_negative_feedback(query, intent_json, code, results):
    # Create correction session
    session_id = correction_service.capture_correction_session(
        feedback_id=feedback_id,
        original_query=query,
        human_correct_answer=user_correction,
        original_intent_json=intent_json,
        original_code=code,
        original_results=results
    )
    
    # Analyze error
    error_category = correction_service.analyze_error_type(session_id)
    
    # Generate suggestions
    suggestions = correction_service.generate_correction_suggestions(session_id)
    
    # Present to user for selection
    show_correction_suggestions(suggestions)
```

## Integration Points

### 1. DataAnalysisAssistant Updates
Replace the basic feedback widget with the enhanced version:

```python
# In app/data_assistant.py::_display_final_results()
if self.feedback_widget is None:
    self.feedback_widget = create_enhanced_feedback_widget(
        query=self.query_text,
        original_intent_json=json.dumps(self.engine.intent.model_dump()) if self.engine.intent else None,
        original_code=self.engine.generated_code,
        original_results=json.dumps(self.engine.execution_results),
        on_correction_applied=self._handle_correction_applied
    )
```

### 2. Engine Enhancement
Add pattern matching to the analysis engine:

```python
# In app/engine.py::process_query()
def process_query(self, query):
    # Check for learned patterns first
    correction_service = CorrectionService()
    patterns = correction_service.find_similar_patterns(query)
    
    if patterns and patterns[0].success_rate > 0.9:
        # Use learned pattern
        self.intent = parse_intent_json(patterns[0].canonical_intent_json)
        # Boost confidence
        self.intent.parameters["confidence"] = min(1.0, 
            self.intent.parameters.get("confidence", 0.5) + patterns[0].confidence_boost
        )
    else:
        # Normal processing
        self.intent = ai.get_query_intent(query)
    
    return self.intent
```

## Metrics & Monitoring

### Performance Tracking
```python
# Get learning system metrics
metrics = correction_service.get_learning_metrics(days=30)

print(f"Correction Sessions: {metrics['correction_sessions']['total']}")
print(f"Success Rate: {metrics['learned_patterns']['avg_success_rate']:.2%}")
print(f"Pattern Usage: {metrics['learned_patterns']['total_usage']}")
```

### Key Performance Indicators
- **Accuracy Rate**: Percentage of queries answered correctly
- **Pattern Match Rate**: Percentage of queries matched to learned patterns
- **Correction Integration Rate**: Percentage of corrections successfully applied
- **User Satisfaction**: Thumbs up vs thumbs down ratio

## Testing

### Running Tests
```bash
# Run correction system tests
pytest tests/learning/test_correction_integration.py -v

# Run all learning-related tests
pytest tests/learning/ -v

# Run with coverage
pytest tests/learning/ --cov=app.services.correction_service --cov-report=html
```

### Test Coverage
- Unit tests for CorrectionService
- Integration tests for feedback workflow
- End-to-end correction flow tests
- Performance and edge case testing

## Migration Guide

### Phase 1: Database Setup (Week 1)
1. Run migration 009: `python -m app.utils.db_migrations`
2. Verify tables created: `correction_sessions`, `intent_patterns`, etc.

### Phase 2: Enhanced Feedback (Week 2)
1. Replace basic feedback widgets with enhanced versions
2. Test correction capture workflow
3. Verify error analysis functionality

### Phase 3: Pattern Learning (Week 3)
1. Integrate pattern matching into query processing
2. Enable automated correction suggestions
3. Test end-to-end learning workflow

### Phase 4: Optimization (Week 4)
1. Performance tuning and caching
2. Advanced similarity algorithms
3. Metrics dashboard implementation

## Best Practices

### Error Handling
- Always validate JSON intent before learning
- Graceful fallback when learning systems fail
- Comprehensive logging for debugging

### Performance
- Implement caching for frequently used patterns
- Background processing for analysis tasks
- Periodic cleanup of old correction sessions

### Security
- Sanitize all user-provided corrections
- Validate code templates before storage
- Audit trail for all learning operations

### Monitoring
- Track learning system performance metrics
- Alert on unusual error rates or patterns
- Regular review of correction sessions

## Future Enhancements

### Advanced Pattern Matching
- Semantic similarity using embeddings
- Multi-language support for queries
- Context-aware pattern selection

### Machine Learning Integration
- Automated error categorization
- Predictive accuracy scoring
- Cluster analysis for query patterns

### User Experience
- Proactive suggestion of similar queries
- Confidence indicators for answers
- Personalized learning per user

## Troubleshooting

### Common Issues

**Patterns not matching:**
- Check query normalization logic
- Verify pattern storage in database
- Review similarity threshold settings

**Correction suggestions not appearing:**
- Confirm error analysis is working
- Check suggestion generation logic
- Verify UI event handlers

**Performance issues:**
- Enable query caching
- Optimize database indexes
- Review pattern matching efficiency

### Debug Mode
```python
# Enable detailed logging
import logging
logging.getLogger('app.services.correction_service').setLevel(logging.DEBUG)

# Test pattern matching
patterns = correction_service.find_similar_patterns("test query", limit=10)
for pattern in patterns:
    print(f"Pattern: {pattern.query_pattern} (confidence: {pattern.confidence_boost})")
```

## Support

For questions or issues with the learning system:

1. Check the test suite for examples
2. Review error logs in `logs/ai_trace.log`
3. Consult the database schema documentation
4. Run the comprehensive test suite for diagnostics

---

*This learning system represents a significant enhancement to the AAA's capabilities, enabling continuous improvement through user feedback and automated pattern recognition.* 