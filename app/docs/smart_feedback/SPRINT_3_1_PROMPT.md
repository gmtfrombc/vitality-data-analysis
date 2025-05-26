# Sprint 3.1: Pattern Learning Integration

## 🎯 Sprint Mission
You are implementing **Sprint 3.1** of the Smart Feedback System for a medical data analysis assistant. Your goal is to integrate the smart feedback system with the existing pattern learning infrastructure to enable adaptive feedback behavior based on learned patterns.

## 📋 Project Context

### What is the Smart Feedback System?
The Smart Feedback System intelligently curates when to request user feedback to reduce feedback fatigue while maximizing learning value. It now uses confidence scoring, novelty detection, advanced priority logic, and will integrate with pattern learning for adaptive behavior.

### Previous Sprint Completions
**Sprint 2.1 ✅**: Confidence scoring and novelty detection implemented
**Sprint 2.2 ✅**: Advanced priority logic and UI enhancements with basic analytics

### Phase 1 Foundation (COMPLETED ✅)
- ✅ Basic duplicate detection and priority system
- ✅ Database integration with existing feedback tables
- ✅ Smart curation logic and enhanced UI integration

### Existing Pattern Learning Infrastructure
- ✅ `CorrectionService` with pattern matching capabilities
- ✅ Database tables: `intent_patterns`, `correction_sessions`, `code_templates`
- ✅ Query similarity calculation and pattern storage
- ✅ Learning from user corrections and feedback

## 🚀 Sprint 3.1 Goal
Integrate smart feedback system with the existing pattern learning infrastructure to enable adaptive feedback behavior based on learned patterns.

**Duration**: 3-4 hours

## 📋 Technical Tasks

### 1. Pattern Learning Integration (`app/utils/smart_feedback.py`)
- Connect to `CorrectionService` for pattern data
- Use learned patterns to inform feedback decisions
- Implement pattern-based confidence boosting

### 2. Adaptive Threshold Management (`app/utils/adaptive_thresholds.py`)
- Auto-adjust similarity thresholds based on success rates
- Dynamic confidence thresholds based on pattern effectiveness
- User-specific threshold learning

### 3. Enhanced Pattern Matching (`app/services/correction_service.py`)
- Improve pattern matching for feedback decisions
- Add feedback-specific pattern types
- Implement pattern effectiveness tracking

## 🎯 Deliverables

### 1. Pattern-Aware Feedback Logic (`app/utils/smart_feedback.py`)
Add these functions to integrate with pattern learning:

```python
def should_request_feedback_with_patterns(query: str, results: Dict[str, Any] = None) -> bool:
    """Enhanced feedback logic using learned patterns.
    
    Args:
        query: The user's query text
        results: Analysis results (optional)
        
    Returns:
        True if feedback should be requested considering learned patterns
    """
    
def get_pattern_confidence_boost(query: str) -> float:
    """Get confidence boost from learned patterns.
    
    Args:
        query: Query text to analyze
        
    Returns:
        Confidence boost factor (0.0-1.0) based on pattern matches
    """
    
def assess_pattern_learning_value(query: str) -> float:
    """Assess learning value based on existing patterns.
    
    Args:
        query: Query text to analyze
        
    Returns:
        Learning value score considering pattern gaps
    """

# Enhanced priority calculation with pattern awareness
def get_feedback_priority_with_patterns(query: str, results: Dict[str, Any] = None, 
                                       user_id: str = 'anon') -> str:
    """Pattern-aware priority calculation.
    
    Args:
        query: Query text
        results: Analysis results (optional)
        user_id: User identifier
        
    Returns:
        Priority level considering learned patterns
    """
```

### 2. Adaptive Threshold System (`app/utils/adaptive_thresholds.py`)
Create this new module:

```python
"""Adaptive threshold management for Smart Feedback System.

This module automatically adjusts similarity and confidence thresholds
based on pattern effectiveness and user behavior.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

from app.services.correction_service import CorrectionService
from app.utils.feedback_analytics import FeedbackAnalytics

logger = logging.getLogger(__name__)


class AdaptiveThresholdManager:
    """Manages adaptive thresholds for smart feedback decisions."""
    
    def __init__(self):
        """Initialize the threshold manager."""
        self.correction_service = CorrectionService()
        self.analytics = FeedbackAnalytics()
        
        # Default thresholds
        self.default_thresholds = {
            'similarity_threshold': 0.80,
            'confidence_threshold': 0.70,
            'novelty_threshold': 0.70,
            'learning_value_threshold': 0.60
        }
        
        # Current adaptive thresholds
        self.current_thresholds = self.default_thresholds.copy()
    
    def adjust_similarity_threshold(self, success_rate: float):
        """Adjust similarity threshold based on success rate.
        
        Args:
            success_rate: Recent pattern matching success rate (0.0-1.0)
        """
        
    def update_confidence_threshold(self, pattern_effectiveness: float):
        """Update confidence threshold based on pattern effectiveness.
        
        Args:
            pattern_effectiveness: Effectiveness of confidence-based decisions
        """
        
    def get_user_specific_thresholds(self, user_id: str) -> Dict[str, float]:
        """Get user-specific thresholds based on behavior.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary of personalized thresholds
        """
        
    def update_thresholds_from_feedback(self):
        """Update thresholds based on recent feedback effectiveness."""
        
    def get_current_thresholds(self) -> Dict[str, float]:
        """Get current adaptive thresholds."""
        
    def reset_to_defaults(self):
        """Reset thresholds to default values."""
```

### 3. Enhanced Pattern Service (`app/services/correction_service.py`)
Add these methods to the existing `CorrectionService` class:

```python
# Add these methods to the existing CorrectionService class

def get_feedback_relevant_patterns(self, query: str, limit: int = 5) -> List[IntentPattern]:
    """Get patterns relevant for feedback decisions.
    
    Args:
        query: Query text to match against
        limit: Maximum number of patterns to return
        
    Returns:
        List of relevant intent patterns
    """
    
def track_pattern_feedback_effectiveness(self, pattern_id: int, success: bool):
    """Track effectiveness of pattern-based feedback decisions.
    
    Args:
        pattern_id: ID of the pattern used
        success: Whether the feedback was successful/useful
    """
    
def get_pattern_confidence_metrics(self) -> Dict[str, float]:
    """Get confidence metrics for pattern matching.
    
    Returns:
        Dictionary of pattern confidence metrics
    """
    
def calculate_pattern_coverage_gap(self, query: str) -> float:
    """Calculate how well current patterns cover this query type.
    
    Args:
        query: Query text to analyze
        
    Returns:
        Coverage gap score (0.0 = well covered, 1.0 = not covered)
    """
    
def get_pattern_learning_opportunities(self, days: int = 30) -> List[Dict[str, Any]]:
    """Identify opportunities for pattern learning.
    
    Args:
        days: Number of days to analyze
        
    Returns:
        List of learning opportunities
    """
```

### 4. Pattern Effectiveness Tracking
Add to the database schema (`migrations/011_pattern_effectiveness.sql`):

```sql
-- Migration 011: Pattern Effectiveness Tracking
-- Adds tracking for pattern-based feedback effectiveness

CREATE TABLE IF NOT EXISTS pattern_feedback_effectiveness (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id INTEGER,
    query_text TEXT NOT NULL,
    feedback_requested BOOLEAN NOT NULL,
    feedback_received BOOLEAN DEFAULT FALSE,
    feedback_positive BOOLEAN,
    confidence_boost_applied REAL,
    effectiveness_score REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pattern_id) REFERENCES intent_patterns(id)
);

CREATE INDEX IF NOT EXISTS idx_pattern_effectiveness_pattern_id 
ON pattern_feedback_effectiveness(pattern_id);

CREATE INDEX IF NOT EXISTS idx_pattern_effectiveness_created_at 
ON pattern_feedback_effectiveness(created_at);

-- Add effectiveness tracking to existing intent_patterns table
ALTER TABLE intent_patterns ADD COLUMN feedback_effectiveness REAL DEFAULT 1.0;
ALTER TABLE intent_patterns ADD COLUMN last_effectiveness_update TEXT;
```

## 🧪 Testing Strategy

### Unit Tests
Create `tests/utils/test_adaptive_thresholds.py`:
```python
def test_adaptive_threshold_manager_initialization()
def test_similarity_threshold_adjustment()
def test_confidence_threshold_update()
def test_user_specific_thresholds()
def test_threshold_updates_from_feedback()
```

### Integration Tests
Create `tests/services/test_pattern_feedback_integration.py`:
```python
def test_pattern_aware_feedback_decisions()
def test_pattern_confidence_boost()
def test_pattern_effectiveness_tracking()
def test_adaptive_threshold_integration()
```

### Pattern Learning Tests
Update existing tests:
```python
# In test_smart_feedback.py
def test_feedback_with_pattern_integration()
def test_pattern_based_priority_calculation()
def test_learning_value_assessment()

# In test_correction_service.py
def test_feedback_relevant_patterns()
def test_pattern_effectiveness_tracking()
def test_pattern_coverage_gap()
```

## 🔗 Integration Points

### Dependencies from Previous Sprints:
- **Confidence Scoring**: `app/utils/confidence_scoring.py`
- **Novelty Detection**: `app/utils/novelty_detection.py`
- **Advanced Priority Logic**: Enhanced `app/utils/smart_feedback.py`
- **Analytics**: `app/utils/feedback_analytics.py`

### Existing Pattern Learning Infrastructure:
- **CorrectionService**: `app/services/correction_service.py`
- **Database Tables**: `intent_patterns`, `correction_sessions`, `code_templates`
- **Pattern Matching**: Query similarity and pattern storage
- **Learning Pipeline**: Correction capture and pattern creation

### Files to Modify:
- `app/utils/smart_feedback.py` - Add pattern-aware functions
- `app/services/correction_service.py` - Add feedback-specific methods
- `app/data_assistant.py` - Update to use pattern-aware feedback logic

### Files to Create:
- `app/utils/adaptive_thresholds.py` - New adaptive threshold management
- `migrations/011_pattern_effectiveness.sql` - Database schema updates
- Test files for new functionality

## ✅ Success Criteria

- [ ] Pattern learning integration improves feedback decisions
- [ ] Adaptive thresholds adjust based on effectiveness data
- [ ] Pattern-based confidence boosting works correctly
- [ ] Effectiveness tracking captures useful metrics
- [ ] Performance remains under 100ms for feedback decisions
- [ ] Integration doesn't break existing pattern learning functionality

## 🚨 Important Notes

### Code Quality:
- Follow existing codebase conventions
- Maintain backward compatibility with existing pattern learning
- Use existing database connection patterns
- Implement comprehensive error handling

### Performance:
- Cache pattern lookups for frequently used queries
- Optimize database queries for pattern matching
- Monitor memory usage for pattern data
- Keep threshold calculations lightweight

### Pattern Learning Integration:
- Don't interfere with existing correction workflows
- Preserve pattern learning accuracy
- Ensure feedback effectiveness tracking is reliable
- Maintain pattern data integrity

## 🔧 Implementation Tips

1. **Start with Pattern Integration**: Connect to existing `CorrectionService` first
2. **Test Pattern Queries**: Verify pattern matching works with feedback logic
3. **Implement Adaptive Thresholds**: Build threshold management incrementally
4. **Track Effectiveness**: Add tracking after core functionality works
5. **Use Real Pattern Data**: Test with actual patterns from the database

## 📊 Example Implementation Approach

### Pattern-Aware Feedback Decision:
```python
def should_request_feedback_with_patterns(query: str, results: Dict[str, Any] = None) -> bool:
    """Example implementation approach."""
    # Get relevant patterns for this query
    correction_service = CorrectionService()
    relevant_patterns = correction_service.get_feedback_relevant_patterns(query)
    
    # Calculate pattern-based confidence boost
    pattern_boost = get_pattern_confidence_boost(query)
    
    # Adjust confidence score with pattern boost
    base_confidence = calculate_confidence_score(query, results)
    adjusted_confidence = min(1.0, base_confidence + pattern_boost)
    
    # Check if patterns suggest feedback is valuable
    learning_value = assess_pattern_learning_value(query)
    
    # Make decision based on adjusted factors
    if adjusted_confidence < 0.6 or learning_value > 0.7:
        return True
    
    # Check for pattern coverage gaps
    coverage_gap = correction_service.calculate_pattern_coverage_gap(query)
    if coverage_gap > 0.8:  # High gap = request feedback
        return True
    
    return False  # Patterns suggest feedback not needed
```

### Adaptive Threshold Adjustment:
```python
def adjust_similarity_threshold(self, success_rate: float):
    """Example threshold adjustment approach."""
    current_threshold = self.current_thresholds['similarity_threshold']
    
    if success_rate > 0.9:
        # High success rate = can be more restrictive
        new_threshold = min(0.95, current_threshold + 0.05)
    elif success_rate < 0.7:
        # Low success rate = be more permissive
        new_threshold = max(0.60, current_threshold - 0.05)
    else:
        # Moderate success rate = small adjustment
        adjustment = (success_rate - 0.8) * 0.1
        new_threshold = current_threshold + adjustment
    
    self.current_thresholds['similarity_threshold'] = new_threshold
    logger.info(f"Adjusted similarity threshold: {current_threshold:.2f} -> {new_threshold:.2f}")
```

## 🎯 Next Sprint Setup

This sprint enables **Sprint 3.2: Feedback Effectiveness Tracking** by providing:
- Pattern-aware feedback decisions for effectiveness measurement
- Adaptive thresholds that can be monitored and optimized
- Pattern effectiveness tracking infrastructure
- Integration foundation for comprehensive analytics

## 📞 When Complete

After completing this sprint:
1. Test pattern integration with various query types
2. Verify adaptive thresholds adjust correctly based on data
3. Confirm pattern effectiveness tracking works
4. Test performance with pattern lookups
5. Document any pattern learning improvements or issues
6. Move to Sprint 3.2 for comprehensive effectiveness tracking

**Outstanding! You're building the adaptive intelligence layer! 🧠🔄✨** 