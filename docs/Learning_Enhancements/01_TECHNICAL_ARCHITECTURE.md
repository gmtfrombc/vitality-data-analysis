# Technical Architecture - AAA Learning Enhancements

## System Design Overview

The Learning Enhancements system extends the existing AAA architecture with automated learning capabilities while maintaining backward compatibility and system stability.

## Component Architecture

### 1. Enhanced Feedback Collection Layer

**File**: `app/utils/enhanced_feedback_widget.py`

**Purpose**: Replace basic thumbs up/down feedback with detailed correction capture

**Key Classes**:
```python
class EnhancedFeedbackWidget(param.Parameterized):
    """Enhanced feedback widget with correction capture capabilities."""
    
    # Core functionality
    - capture_positive_feedback()
    - capture_negative_feedback()
    - show_correction_interface()
    - analyze_and_suggest()
    - apply_suggestions()
```

**Integration Points**:
- Replaces existing feedback widgets in `app/data_assistant.py`
- Integrates with `CorrectionService` for backend processing
- Uses Panel UI framework for consistent interface

### 2. Correction Processing Service

**File**: `app/services/correction_service.py`

**Purpose**: Core learning engine that processes corrections and manages patterns

**Key Classes**:
```python
class CorrectionService:
    """Main service for handling corrections and learning."""
    
    # Core methods
    - capture_correction_session()
    - analyze_error_type()
    - generate_correction_suggestions()
    - apply_correction()
    - find_similar_patterns()
    - get_learning_metrics()

class CorrectionSession:
    """Data model for correction sessions."""
    
class IntentPattern:
    """Data model for learned intent patterns."""
```

**Responsibilities**:
- Error analysis and categorization
- Pattern learning and storage
- Similarity matching for query routing
- Metrics collection and reporting

### 3. Database Schema Extensions

**File**: `migrations/009_correction_learning_tables.sql`

**New Tables**:

```sql
-- Core correction tracking
correction_sessions (
    id, feedback_id, original_query, original_intent_json,
    original_code, original_results, human_correct_answer,
    correction_type, error_category, status, reviewed_by,
    reviewed_at, created_at
)

-- Learned patterns for query routing
intent_patterns (
    id, query_pattern, canonical_intent_json,
    confidence_boost, usage_count, success_rate,
    created_from_session_id, created_at, last_used_at
)

-- Code templates for deterministic generation
code_templates (
    id, intent_signature, template_code, template_description,
    success_rate, usage_count, created_from_session_id,
    created_at, last_used_at
)

-- Performance tracking
learning_metrics (
    id, metric_date, total_queries, correct_answers,
    pattern_matches, template_matches, correction_applied,
    accuracy_rate, created_at
)

-- Query similarity caching
query_similarity_cache (
    id, query_hash, similar_patterns, computed_at
)
```

### 4. Query Processing Enhancement

**File**: `app/engine.py` (modifications)

**Enhancement**: Add pattern matching before LLM processing

```python
def process_query(self, query):
    # NEW: Check for learned patterns first
    correction_service = CorrectionService()
    patterns = correction_service.find_similar_patterns(query)
    
    if patterns and patterns[0].success_rate > 0.9:
        # Use learned pattern (high confidence)
        self.intent = parse_intent_json(patterns[0].canonical_intent_json)
        self.intent.parameters["confidence"] = 0.95
        return self.intent
    
    # EXISTING: Fall back to normal LLM processing
    return self.get_query_intent()
```

## Data Flow Architecture

### 1. Normal Query Processing
```
User Query → Pattern Check → [Match] → Instant Response (High Confidence)
           → [No Match] → LLM Processing → Standard Workflow
```

### 2. Correction Learning Flow
```
Incorrect Answer → 👎 Feedback → Correction Input → Error Analysis
                → Suggestions → Apply Fix → Store Pattern → Future Reuse
```

### 3. Pattern Matching Algorithm
```
Input Query → Normalize → Hash → Cache Check → [Hit] → Return Patterns
           → [Miss] → Database Search → Similarity Score → Cache Result
```

## Error Categories and Analysis

### Error Classification System
```python
ERROR_CATEGORIES = {
    'missing_filter': 'Query missing patient status/demographic filters',
    'wrong_aggregation': 'Incorrect analysis type (avg vs distribution)',
    'unclear_target': 'Ambiguous target field',
    'missing_groupby': 'Missing grouping in generated code',
    'code_logic_error': 'General code generation issues',
    'intent_mismatch': 'LLM misunderstood user intent',
    'data_fix': 'Data quality or validation issues'
}
```

### Correction Types
```python
CORRECTION_TYPES = {
    'intent_fix': 'Correction to query intent parsing',
    'code_fix': 'Correction to generated analysis code',
    'logic_fix': 'Correction to analysis logic',
    'data_fix': 'Correction to data handling'
}
```

## Integration Strategy

### 1. Backward Compatibility
- All existing functionality remains unchanged
- New features are additive, not replacement
- Graceful degradation when learning system unavailable

### 2. Progressive Enhancement
- **Sprint 1**: Database foundation (no user impact)
- **Sprint 2**: Enhanced feedback UI (optional usage)
- **Sprint 3**: Error analysis (helpful but not required)
- **Sprint 4**: Pattern learning (performance improvement)
- **Sprint 5**: Full integration (seamless experience)

### 3. Performance Considerations

**Caching Strategy**:
```python
# Query similarity cache for fast pattern lookup
CACHE_STRATEGY = {
    'similarity_cache_ttl': 3600,  # 1 hour
    'pattern_cache_size': 1000,   # Most frequent patterns
    'background_refresh': True    # Update cache asynchronously
}
```

**Database Optimization**:
```sql
-- Performance indexes
CREATE INDEX idx_intent_patterns_usage_count ON intent_patterns(usage_count DESC);
CREATE INDEX idx_correction_sessions_status ON correction_sessions(status);
CREATE INDEX idx_query_similarity_cache_hash ON query_similarity_cache(query_hash);
```

## Security and Data Protection

### 1. Input Sanitization
```python
def sanitize_correction_input(user_input: str) -> str:
    """Sanitize user-provided corrections."""
    # Remove potential SQL injection patterns
    # Limit input length
    # Validate against allowed patterns
    return cleaned_input
```

### 2. Pattern Validation
```python
def validate_learned_pattern(pattern: IntentPattern) -> bool:
    """Validate learned patterns before storage."""
    # Ensure JSON is valid
    # Check for malicious code patterns
    # Verify intent structure
    return is_valid
```

### 3. Audit Trail
- All corrections logged with timestamps
- User identification for accountability
- Rollback capability for problematic patterns

## Monitoring and Observability

### 1. Key Metrics
```python
MONITORING_METRICS = {
    'accuracy_rate': 'Percentage of queries answered correctly',
    'pattern_hit_rate': 'Percentage of queries using learned patterns',
    'correction_rate': 'Rate of user corrections per day',
    'learning_velocity': 'Rate of new pattern creation',
    'system_confidence': 'Average confidence score of responses'
}
```

### 2. Alerting
- Performance degradation alerts
- High error rate notifications
- Pattern learning anomalies
- Database health monitoring

### 3. Debugging Tools
```python
def debug_pattern_matching(query: str) -> Dict:
    """Debug information for pattern matching."""
    return {
        'normalized_query': normalize_query(query),
        'candidate_patterns': find_candidates(query),
        'similarity_scores': calculate_similarities(query),
        'selected_pattern': get_best_match(query),
        'confidence_boost': calculate_boost(query)
    }
```

## Testing Strategy

### 1. Unit Testing
- Individual component testing
- Mock external dependencies
- Edge case validation

### 2. Integration Testing
- End-to-end workflow testing
- Database transaction testing
- UI component integration

### 3. Performance Testing
- Pattern matching speed benchmarks
- Database query optimization
- Memory usage validation

### 4. User Acceptance Testing
- Correction workflow usability
- Error analysis accuracy
- Suggestion relevance

## Deployment Architecture

### 1. Database Migrations
```bash
# Migration execution order
009_correction_learning_tables.sql  # Sprint 1
010_performance_indexes.sql         # Sprint 4
011_cleanup_constraints.sql         # Sprint 5
```

### 2. Feature Flags
```python
FEATURE_FLAGS = {
    'enhanced_feedback_enabled': True,
    'error_analysis_enabled': True,
    'pattern_learning_enabled': True,
    'auto_suggestions_enabled': True
}
```

### 3. Rollback Plan
- Each sprint is independently deployable
- Database changes are reversible
- Feature flags allow quick disabling

## Future Enhancement Opportunities

### 1. Advanced Pattern Matching
- Semantic similarity using embeddings
- Multi-language query support
- Context-aware pattern selection

### 2. Machine Learning Integration
- Automated error categorization
- Predictive accuracy scoring
- Cluster analysis for query patterns

### 3. User Personalization
- Individual learning profiles
- Personalized suggestion ranking
- Adaptive confidence thresholds

---

*This architecture provides a robust foundation for the AAA learning enhancements while maintaining system stability and enabling future growth.* 