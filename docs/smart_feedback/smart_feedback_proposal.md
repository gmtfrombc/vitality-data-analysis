# Smart Feedback Curation System

## Overview
Implement intelligent feedback curation that only requests user feedback when it would be most valuable for system improvement.

## Current State
- ✅ All queries show thumbs up/down regardless of previous feedback
- ✅ No duplicate detection or similarity matching
- ✅ No prioritization based on system confidence or learning needs

## Proposed Enhancement

### 1. Query Similarity Detection
```python
def should_request_feedback(query: str, results: dict) -> bool:
    """Determine if feedback would be valuable for this query."""
    
    # Check for recent similar queries
    similar_queries = find_similar_feedback_queries(query, days=30, threshold=0.8)
    
    if similar_queries:
        # If we have recent feedback on very similar queries
        recent_feedback = [q for q in similar_queries if q['days_ago'] <= 7]
        if recent_feedback and all(q['rating'] == 'up' for q in recent_feedback):
            return False  # Skip feedback - we know this works well
    
    # Check system confidence
    confidence_score = calculate_query_confidence(query, results)
    if confidence_score < 0.7:
        return True  # Request feedback on low-confidence answers
    
    # Check if this is a new pattern
    if is_novel_query_pattern(query):
        return True  # Request feedback on new types of questions
    
    # Check if this metric/analysis type needs more data
    if needs_more_feedback_data(query):
        return True  # Request feedback for under-represented categories
    
    return False  # Default: don't request feedback
```

### 2. Feedback Value Scoring
```python
class FeedbackPriority:
    HIGH = "high"      # New patterns, low confidence, critical metrics
    MEDIUM = "medium"  # Moderate confidence, some similar feedback exists  
    LOW = "low"        # High confidence, lots of similar positive feedback
    SKIP = "skip"      # Very similar recent positive feedback exists

def calculate_feedback_priority(query: str, results: dict) -> FeedbackPriority:
    """Calculate how valuable feedback would be for this query."""
    
    # Factor 1: Query novelty (30% weight)
    novelty_score = calculate_novelty_score(query)
    
    # Factor 2: System confidence (25% weight)  
    confidence_score = calculate_confidence_score(query, results)
    
    # Factor 3: Similar feedback recency (25% weight)
    recency_score = calculate_recency_score(query)
    
    # Factor 4: Learning value (20% weight)
    learning_score = calculate_learning_value(query)
    
    total_score = (novelty_score * 0.3 + 
                   (1 - confidence_score) * 0.25 +  # Lower confidence = higher priority
                   recency_score * 0.25 + 
                   learning_score * 0.2)
    
    if total_score >= 0.8:
        return FeedbackPriority.HIGH
    elif total_score >= 0.6:
        return FeedbackPriority.MEDIUM  
    elif total_score >= 0.3:
        return FeedbackPriority.LOW
    else:
        return FeedbackPriority.SKIP
```

### 3. Implementation Strategy

#### Phase 1: Basic Duplicate Detection (Easy - 1-2 hours)
```python
def has_recent_feedback(query: str, days: int = 7) -> bool:
    """Check if we have recent feedback for this exact or very similar query."""
    with _get_conn() as conn:
        cursor = conn.cursor()
        since_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Check exact matches first
        cursor.execute("""
            SELECT COUNT(*) FROM assistant_feedback 
            WHERE question = ? AND created_at >= ?
        """, (query, since_date))
        
        if cursor.fetchone()[0] > 0:
            return True
            
        # Check similar queries using existing similarity function
        cursor.execute("""
            SELECT question FROM assistant_feedback 
            WHERE created_at >= ?
        """, (since_date,))
        
        for (prev_query,) in cursor.fetchall():
            if calculate_query_similarity(query, prev_query) > 0.85:
                return True
                
        return False
```

#### Phase 2: Smart Curation (Medium - 4-6 hours)
```python
class SmartFeedbackWidget(EnhancedFeedbackWidget):
    """Enhanced feedback widget that only shows when feedback is valuable."""
    
    def __init__(self, query: str, results: dict, **params):
        self.priority = calculate_feedback_priority(query, results)
        
        if self.priority == FeedbackPriority.SKIP:
            # Don't show feedback widget at all
            super().__init__(query, **params)
            self.visible = False
            return
            
        super().__init__(query, **params)
        
        # Customize UI based on priority
        if self.priority == FeedbackPriority.HIGH:
            self._add_priority_message("Your feedback is especially valuable for this type of question!")
        elif self.priority == FeedbackPriority.MEDIUM:
            self._add_priority_message("Help us improve by rating this answer.")
        # LOW priority uses default messaging
```

#### Phase 3: Advanced Learning (Complex - 8-12 hours)
- Integrate with pattern learning system
- Track feedback effectiveness over time
- Auto-adjust similarity thresholds based on user behavior
- Implement feedback fatigue detection

### 4. Benefits

#### For Users:
- ✅ **Reduced feedback fatigue** - only see requests when truly helpful
- ✅ **More meaningful interactions** - know their feedback has high impact
- ✅ **Faster workflow** - fewer interruptions for redundant feedback

#### For System:
- ✅ **Higher quality feedback** - users more likely to engage when it matters
- ✅ **Better learning efficiency** - focus on areas that need improvement
- ✅ **Reduced noise** - avoid duplicate feedback on well-understood queries

### 5. Configuration Options
```python
FEEDBACK_CONFIG = {
    "similarity_threshold": 0.85,  # How similar queries must be to skip feedback
    "recency_window_days": 7,      # How recent feedback must be to matter
    "min_confidence_threshold": 0.7,  # Below this, always request feedback
    "max_feedback_per_day": 5,     # Prevent feedback fatigue
    "priority_boost_new_metrics": True,  # Always request feedback for new metric types
}
```

## Implementation Difficulty: **Medium** ⭐⭐⭐

- **Phase 1 (Basic)**: 2-3 hours - Leverage existing similarity functions
- **Phase 2 (Smart)**: 4-6 hours - Build on existing feedback widgets  
- **Phase 3 (Advanced)**: 8-12 hours - Deep integration with learning systems

The existing codebase already has:
- ✅ Query similarity calculation (`_calculate_query_similarity`)
- ✅ Feedback database and widgets
- ✅ Pattern learning infrastructure
- ✅ Intent parsing and confidence scoring

This makes implementation very feasible! 