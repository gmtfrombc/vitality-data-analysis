# Sprint 2.2: Advanced Priority Logic & UI Enhancement

## 🎯 Sprint Mission
You are implementing **Sprint 2.2** of the Smart Feedback System for a medical data analysis assistant. Your goal is to implement multi-factor priority calculation and enhance the UI with priority-based messaging and basic analytics.

## 📋 Project Context

### What is the Smart Feedback System?
The Smart Feedback System intelligently curates when to request user feedback to reduce feedback fatigue while maximizing learning value. It uses confidence scoring, novelty detection, and advanced priority logic to make smart decisions.

### Previous Sprint Completion (Sprint 2.1 ✅)
- ✅ Confidence scoring implemented (`app/utils/confidence_scoring.py`)
- ✅ Novelty detection implemented (`app/utils/novelty_detection.py`)
- ✅ Enhanced smart feedback service with confidence and novelty functions
- ✅ Basic integration with existing priority calculation

### Phase 1 Foundation (COMPLETED ✅)
- ✅ Basic duplicate detection and priority system
- ✅ Database integration with existing feedback tables
- ✅ Smart curation logic and UI integration
- ✅ Files: `app/utils/smart_feedback.py`, `app/utils/enhanced_feedback_widget.py`

## 🚀 Sprint 2.2 Goal
Implement multi-factor priority calculation and enhance the UI with priority-based messaging and basic analytics.

**Duration**: 2-3 hours

## 📋 Technical Tasks

### 1. Advanced Priority Calculation (`app/utils/smart_feedback.py`)
- Implement weighted scoring system using confidence and novelty
- Add learning value assessment
- Create feedback fatigue detection

### 2. Enhanced UI Components (`app/utils/enhanced_feedback_widget.py`)
- Priority-based visual indicators
- Dynamic messaging based on priority
- Feedback analytics display

### 3. Basic Analytics (`app/utils/feedback_analytics.py`)
- Track feedback request patterns
- Monitor user engagement rates
- Basic effectiveness metrics

## 🎯 Deliverables

### 1. Enhanced Priority System (`app/utils/smart_feedback.py`)
Add this new class and enhance existing functions:

```python
class FeedbackPriorityCalculator:
    """Advanced priority calculation using multiple factors."""
    
    def __init__(self):
        """Initialize the priority calculator."""
        from app.utils.confidence_scoring import ConfidenceScorer
        from app.utils.novelty_detection import NoveltyDetector
        
        self.confidence_scorer = ConfidenceScorer()
        self.novelty_detector = NoveltyDetector()
        
        # Configurable weights for different factors
        self.weights = {
            'confidence': 0.25,      # Lower confidence = higher priority
            'novelty': 0.30,         # Higher novelty = higher priority
            'recency': 0.25,         # Recent similar feedback = lower priority
            'learning_value': 0.20   # Higher learning value = higher priority
        }
    
    def calculate_weighted_priority(self, factors: Dict[str, float]) -> str:
        """Calculate priority using weighted factors.
        
        Args:
            factors: Dictionary of factor scores (0.0-1.0)
            
        Returns:
            Priority level: 'high', 'medium', 'low', or 'skip'
        """
        
    def assess_learning_value(self, query: str) -> float:
        """Assess potential learning value of feedback (0.0-1.0).
        
        Args:
            query: Query text to analyze
            
        Returns:
            Learning value score
        """
        
    def detect_feedback_fatigue(self, user_id: str = 'anon') -> bool:
        """Detect if user is experiencing feedback fatigue.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if fatigue detected, False otherwise
        """

# Enhanced priority calculation function
def get_feedback_priority_advanced(query: str, results: Dict[str, Any] = None, 
                                 user_id: str = 'anon') -> str:
    """Advanced priority calculation with multiple factors.
    
    Args:
        query: Query text
        results: Analysis results (optional)
        user_id: User identifier for fatigue detection
        
    Returns:
        Priority level: 'high', 'medium', 'low', or 'skip'
    """
```

### 2. UI Enhancements (`app/utils/enhanced_feedback_widget.py`)
Enhance the existing widget class:

```python
class SmartFeedbackWidget(EnhancedFeedbackWidget):
    """Enhanced feedback widget with priority-based customization."""
    
    def __init__(self, query: str, priority: str = 'medium', 
                 analytics_data: Optional[Dict] = None, **params):
        """Initialize with priority-based customization.
        
        Args:
            query: The original user query
            priority: Feedback priority level
            analytics_data: Optional analytics data to display
            **params: Additional parameters
        """
        super().__init__(query, **params)
        self.priority = priority
        self.analytics_data = analytics_data or {}
        self._customize_for_priority(priority)
    
    def _customize_for_priority(self, priority: str):
        """Customize widget appearance based on priority.
        
        Args:
            priority: Priority level ('high', 'medium', 'low', 'skip')
        """
        
    def _add_priority_indicators(self, priority: str):
        """Add visual indicators based on priority.
        
        Args:
            priority: Priority level
        """
        
    def _show_analytics_summary(self):
        """Show brief analytics summary if available."""
        
    def _get_priority_message(self, priority: str) -> str:
        """Get priority-specific message.
        
        Args:
            priority: Priority level
            
        Returns:
            Customized message for the priority level
        """
```

### 3. Analytics Module (`app/utils/feedback_analytics.py`)
Create this new module:

```python
"""Basic analytics for Smart Feedback System.

This module tracks feedback request patterns and provides basic
effectiveness metrics for the smart feedback system.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from app.utils.feedback_db import _get_conn

logger = logging.getLogger(__name__)


class FeedbackAnalytics:
    """Tracks and analyzes feedback system performance."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the analytics tracker.
        
        Args:
            db_path: Optional database path (for testing)
        """
        self.db_path = db_path
        self._ensure_analytics_table()
    
    def track_feedback_request(self, query: str, priority: str, 
                             requested: bool, user_id: str = 'anon'):
        """Track a feedback request decision.
        
        Args:
            query: The query text
            priority: Calculated priority level
            requested: Whether feedback was actually requested
            user_id: User identifier
        """
        
    def get_engagement_metrics(self, days: int = 7) -> Dict[str, float]:
        """Get user engagement metrics for the specified period.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary of engagement metrics
        """
        
    def get_effectiveness_summary(self) -> Dict[str, Any]:
        """Get overall effectiveness summary.
        
        Returns:
            Dictionary of effectiveness metrics
        """
        
    def get_priority_distribution(self, days: int = 7) -> Dict[str, int]:
        """Get distribution of priority levels.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary of priority counts
        """
        
    def _ensure_analytics_table(self):
        """Ensure analytics table exists."""
        
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
```

### 4. Database Schema Addition
Create `migrations/010_feedback_analytics.sql`:

```sql
-- Migration 010: Feedback Analytics Tables
-- Adds tables for tracking smart feedback system performance

CREATE TABLE IF NOT EXISTS feedback_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_text TEXT NOT NULL,
    priority_level TEXT NOT NULL,
    requested BOOLEAN NOT NULL,
    user_id TEXT DEFAULT 'anon',
    confidence_score REAL,
    novelty_score REAL,
    learning_value_score REAL,
    fatigue_detected BOOLEAN DEFAULT FALSE,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feedback_requests_created_at 
ON feedback_requests(created_at);

CREATE INDEX IF NOT EXISTS idx_feedback_requests_priority 
ON feedback_requests(priority_level);

CREATE INDEX IF NOT EXISTS idx_feedback_requests_user_id 
ON feedback_requests(user_id);
```

## 🧪 Testing Strategy

### Unit Tests
Create `tests/utils/test_feedback_analytics.py`:
```python
def test_feedback_analytics_track_request()
def test_feedback_analytics_engagement_metrics()
def test_feedback_analytics_effectiveness_summary()
def test_feedback_analytics_priority_distribution()
```

### Integration Tests
Update existing test files:
```python
# In test_smart_feedback.py
def test_advanced_priority_calculation()
def test_weighted_priority_factors()
def test_fatigue_detection()

# In test_enhanced_feedback_widget.py
def test_priority_based_customization()
def test_priority_indicators()
def test_analytics_display()
```

### UI Tests
```python
def test_widget_appearance_by_priority()
def test_priority_messages()
def test_analytics_summary_display()
```

## 🔗 Integration Points

### Dependencies from Sprint 2.1:
- **Confidence Scoring**: `app/utils/confidence_scoring.py`
- **Novelty Detection**: `app/utils/novelty_detection.py`
- **Enhanced Smart Feedback**: Updated `app/utils/smart_feedback.py`

### Existing Infrastructure:
- **Database**: Existing feedback tables
- **UI Framework**: Panel components and existing widget structure
- **Correction Service**: For pattern data and similarity calculations

### Files to Modify:
- `app/utils/smart_feedback.py` - Add advanced priority calculation
- `app/utils/enhanced_feedback_widget.py` - Add priority-based customization
- `app/data_assistant.py` - Update to use new priority system and analytics

### Files to Create:
- `app/utils/feedback_analytics.py` - New analytics module
- `migrations/010_feedback_analytics.sql` - Database schema
- Test files for new functionality

## ✅ Success Criteria

- [ ] Multi-factor priority calculation works correctly
- [ ] UI adapts appropriately to different priority levels
- [ ] Analytics tracking captures relevant metrics
- [ ] Fatigue detection prevents over-requesting feedback
- [ ] Performance remains under 100ms for priority decisions
- [ ] User experience is improved with better messaging

## 🚨 Important Notes

### Code Quality:
- Follow existing codebase conventions
- Maintain backward compatibility with Phase 1
- Use existing database connection patterns
- Implement comprehensive error handling

### Performance:
- Cache analytics calculations where possible
- Optimize database queries with proper indexing
- Keep UI updates responsive
- Monitor memory usage for analytics data

### User Experience:
- Keep priority indicators subtle and informative
- Ensure messages are clear and helpful
- Don't overwhelm users with too much information
- Test with different priority scenarios

## 🔧 Implementation Tips

1. **Start with Priority Calculator**: Implement the weighted scoring system first
2. **Test Each Factor**: Verify confidence, novelty, and fatigue detection work independently
3. **UI Incremental Changes**: Make small UI changes and test frequently
4. **Analytics Last**: Implement analytics tracking after core functionality works
5. **Use Real Data**: Test with actual queries from the database

## 📊 Example Implementation Approach

### Weighted Priority Calculation:
```python
def calculate_weighted_priority(self, factors: Dict[str, float]) -> str:
    """Example implementation approach."""
    # Calculate weighted score
    weighted_score = 0.0
    
    # Lower confidence = higher priority (invert score)
    confidence_factor = 1.0 - factors.get('confidence', 0.5)
    weighted_score += confidence_factor * self.weights['confidence']
    
    # Higher novelty = higher priority
    novelty_factor = factors.get('novelty', 0.0)
    weighted_score += novelty_factor * self.weights['novelty']
    
    # Recent feedback = lower priority (invert recency)
    recency_factor = 1.0 - factors.get('recency', 0.0)
    weighted_score += recency_factor * self.weights['recency']
    
    # Higher learning value = higher priority
    learning_factor = factors.get('learning_value', 0.0)
    weighted_score += learning_factor * self.weights['learning_value']
    
    # Convert to priority levels
    if weighted_score >= 0.8:
        return 'high'
    elif weighted_score >= 0.6:
        return 'medium'
    elif weighted_score >= 0.3:
        return 'low'
    else:
        return 'skip'
```

### Priority-Based UI Customization:
```python
def _customize_for_priority(self, priority: str):
    """Example UI customization approach."""
    priority_config = {
        'high': {
            'color': 'orange',
            'icon': '🎯',
            'message': 'Your feedback is especially valuable for this question!'
        },
        'medium': {
            'color': 'blue',
            'icon': '💭',
            'message': 'Was this answer helpful?'
        },
        'low': {
            'color': 'gray',
            'icon': '👍',
            'message': 'Quick rating appreciated'
        }
    }
    
    config = priority_config.get(priority, priority_config['medium'])
    self._apply_priority_styling(config)
```

## 🎯 Next Sprint Setup

This sprint enables **Sprint 3.1: Pattern Learning Integration** by providing:
- Advanced priority calculation foundation
- Analytics infrastructure for tracking effectiveness
- Enhanced UI framework for displaying insights
- Fatigue detection for user behavior analysis

## 📞 When Complete

After completing this sprint:
1. Test all priority calculation scenarios
2. Verify UI changes work across different priorities
3. Confirm analytics data is being collected correctly
4. Test fatigue detection with simulated user behavior
5. Document any configuration options or improvements needed
6. Move to Sprint 3.1 for pattern learning integration

**Excellent work! You're building the smart decision-making layer! 🎯✨**