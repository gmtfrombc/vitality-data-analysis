# Sprint 2.1: Confidence Scoring & Novelty Detection

## 🎯 Sprint Mission
You are implementing **Sprint 2.1** of the Smart Feedback System for a medical data analysis assistant. Your goal is to enhance feedback decisions with confidence scoring and novelty detection to make more intelligent decisions about when to request user feedback.

## 📋 Project Context

### What is the Smart Feedback System?
The Smart Feedback System intelligently curates when to request user feedback to reduce feedback fatigue while maximizing learning value. It analyzes queries and results to determine if feedback would be valuable.

### Phase 1 Foundation (COMPLETED ✅)
- ✅ Basic duplicate detection: Skip feedback for exact queries (24h) and similar queries (7d, >80% similarity)
- ✅ Priority system: High/Medium/Low/Skip with custom messages
- ✅ Database integration with existing feedback tables
- ✅ Smart curation logic: `should_request_feedback()`, `get_feedback_priority()`, `get_feedback_message()`
- ✅ UI integration with enhanced feedback widget
- ✅ Files: `app/utils/smart_feedback.py`, `app/utils/enhanced_feedback_widget.py`, updated `app/data_assistant.py`

## 🚀 Sprint 2.1 Goal
Implement confidence scoring for query results and novelty detection for new query patterns to improve feedback request decisions.

**Duration**: 2-3 hours

## 📋 Technical Tasks

### 1. Enhance Smart Feedback Service (`app/utils/smart_feedback.py`)
- Add `calculate_confidence_score()` function
- Add `calculate_novelty_score()` function  
- Add `is_novel_query_pattern()` function
- Integrate confidence and novelty into priority calculation

### 2. Create Confidence Scoring Module (`app/utils/confidence_scoring.py`)
- Implement intent confidence analysis
- Add result quality assessment
- Create execution success indicators

### 3. Add Novelty Detection (`app/utils/novelty_detection.py`)
- Query pattern analysis
- Semantic similarity to existing patterns
- New metric/field detection

## 🎯 Deliverables

### 1. Enhanced `app/utils/smart_feedback.py`
Add these functions to the existing file:

```python
def calculate_confidence_score(query: str, results: Dict[str, Any]) -> float:
    """Calculate confidence score for query results (0.0-1.0).
    
    Args:
        query: The user's query text
        results: Analysis results from the data assistant
        
    Returns:
        Confidence score from 0.0 (low confidence) to 1.0 (high confidence)
    """
    
def calculate_novelty_score(query: str) -> float:
    """Calculate novelty score for query pattern (0.0-1.0).
    
    Args:
        query: The user's query text
        
    Returns:
        Novelty score from 0.0 (known pattern) to 1.0 (completely novel)
    """
    
def is_novel_query_pattern(query: str, threshold: float = 0.7) -> bool:
    """Check if query represents a novel pattern.
    
    Args:
        query: The user's query text
        threshold: Novelty threshold (default 0.7)
        
    Returns:
        True if query is novel, False if similar to existing patterns
    """

# Update existing function to use confidence and novelty
def get_feedback_priority(query: str, results: Dict[str, Any] = None) -> str:
    """Enhanced priority calculation with confidence and novelty.
    
    Args:
        query: Query text
        results: Analysis results (optional)

    Returns:
        Priority level: 'high', 'medium', 'low', or 'skip'
    """
```

### 2. New `app/utils/confidence_scoring.py`
Create this new module:

```python
"""Confidence scoring for Smart Feedback System.

This module analyzes query intent and execution results to calculate
confidence scores that inform feedback request decisions.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """Calculates confidence scores for queries and results."""
    
    def __init__(self):
        """Initialize the confidence scorer."""
        pass
    
    def score_intent_confidence(self, intent: dict) -> float:
        """Score confidence in intent parsing (0.0-1.0).
        
        Args:
            intent: Parsed intent dictionary
            
        Returns:
            Confidence score for intent parsing
        """
        
    def score_execution_success(self, results: dict) -> float:
        """Score execution success based on results (0.0-1.0).
        
        Args:
            results: Execution results dictionary
            
        Returns:
            Confidence score for execution success
        """
        
    def score_result_quality(self, results: dict) -> float:
        """Score quality of analysis results (0.0-1.0).
        
        Args:
            results: Analysis results dictionary
            
        Returns:
            Confidence score for result quality
        """
        
    def calculate_overall_confidence(self, query: str, intent: Optional[dict] = None, 
                                   results: Optional[dict] = None) -> float:
        """Calculate overall confidence score.
        
        Args:
            query: Original query text
            intent: Parsed intent (optional)
            results: Analysis results (optional)
            
        Returns:
            Overall confidence score (0.0-1.0)
        """
```

### 3. New `app/utils/novelty_detection.py`
Create this new module:

```python
"""Novelty detection for Smart Feedback System.

This module analyzes query patterns to detect novel queries that would
benefit from feedback collection.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, Any, List, Set

from app.services.correction_service import CorrectionService
from app.utils.feedback_db import _get_conn

logger = logging.getLogger(__name__)


class NoveltyDetector:
    """Detects novel query patterns for feedback prioritization."""
    
    def __init__(self):
        """Initialize the novelty detector."""
        self.correction_service = CorrectionService()
        self._known_metrics = self._load_known_metrics()
        self._known_patterns = self._load_known_patterns()
    
    def is_novel_query_pattern(self, query: str, threshold: float = 0.7) -> bool:
        """Check if query represents a novel pattern.
        
        Args:
            query: Query text to analyze
            threshold: Novelty threshold (0.0-1.0)
            
        Returns:
            True if query is novel, False if similar to existing patterns
        """
        
    def calculate_semantic_novelty(self, query: str) -> float:
        """Calculate semantic novelty score (0.0-1.0).
        
        Args:
            query: Query text to analyze
            
        Returns:
            Novelty score from 0.0 (known) to 1.0 (completely novel)
        """
        
    def detect_new_metrics(self, query: str) -> bool:
        """Detect if query asks for new/uncommon metrics.
        
        Args:
            query: Query text to analyze
            
        Returns:
            True if query contains new metrics, False otherwise
        """
        
    def _load_known_metrics(self) -> Set[str]:
        """Load known metrics from database and patterns."""
        
    def _load_known_patterns(self) -> List[str]:
        """Load known query patterns from database."""
        
    def _normalize_query(self, query: str) -> str:
        """Normalize query for pattern matching."""
```

## 🧪 Testing Strategy

### Unit Tests
Create `tests/utils/test_confidence_scoring.py`:
```python
def test_confidence_scorer_intent_confidence()
def test_confidence_scorer_execution_success()
def test_confidence_scorer_result_quality()
def test_confidence_scorer_overall_confidence()
```

Create `tests/utils/test_novelty_detection.py`:
```python
def test_novelty_detector_novel_pattern()
def test_novelty_detector_known_pattern()
def test_novelty_detector_new_metrics()
def test_novelty_detector_semantic_novelty()
```

### Integration Tests
Update `test_smart_feedback.py`:
```python
def test_enhanced_priority_with_confidence_and_novelty()
def test_confidence_scoring_integration()
def test_novelty_detection_integration()
```

## 🔗 Integration Points

### Existing Infrastructure to Use:
- **Similarity Calculation**: `CorrectionService._calculate_query_similarity()`
- **Database**: Existing feedback tables + correction learning tables
- **Intent Parsing**: `app/utils/query_intent.py`
- **Pattern Learning**: `app/services/correction_service.py`

### Files to Modify:
- `app/utils/smart_feedback.py` - Add new functions and enhance existing ones
- `app/data_assistant.py` - May need updates to pass results to confidence scoring

### Files to Create:
- `app/utils/confidence_scoring.py` - New confidence scoring module
- `app/utils/novelty_detection.py` - New novelty detection module
- Test files for new modules

## ✅ Success Criteria

- [ ] Confidence scoring accurately reflects result quality
- [ ] Novelty detection identifies new vs. known patterns  
- [ ] Enhanced priority calculation uses multiple factors
- [ ] All tests pass and maintain backward compatibility
- [ ] Performance stays under 100ms for feedback decisions
- [ ] Integration with existing smart feedback logic works seamlessly

## 🚨 Important Notes

### Code Quality:
- Follow existing codebase conventions (snake_case, docstrings)
- Use existing database connection patterns
- Implement comprehensive error handling
- Add logging for debugging and monitoring

### Performance:
- Cache expensive operations (pattern matching, database queries)
- Optimize for <100ms feedback decision time
- Use existing similarity calculation functions

### Backward Compatibility:
- Don't break existing Phase 1 functionality
- Maintain existing API contracts
- Ensure existing tests still pass

## 🔧 Implementation Tips

1. **Start with Confidence Scoring**: Implement basic confidence scoring first
2. **Use Existing Infrastructure**: Leverage `CorrectionService` similarity functions
3. **Test Early and Often**: Write tests as you implement each function
4. **Keep It Simple**: Start with basic algorithms, optimize later
5. **Log Everything**: Add comprehensive logging for debugging

## 📊 Example Implementation Approach

### Confidence Scoring Algorithm:
```python
def calculate_confidence_score(query: str, results: Dict[str, Any]) -> float:
    """Example implementation approach."""
    confidence_factors = []
    
    # Factor 1: Intent clarity (based on query structure)
    intent_score = _score_intent_clarity(query)
    confidence_factors.append(intent_score * 0.3)
    
    # Factor 2: Execution success (based on results)
    if results:
        execution_score = _score_execution_success(results)
        confidence_factors.append(execution_score * 0.4)
    
    # Factor 3: Result completeness
    if results:
        completeness_score = _score_result_completeness(results)
        confidence_factors.append(completeness_score * 0.3)
    
    return sum(confidence_factors) / len(confidence_factors)
```

### Novelty Detection Algorithm:
```python
def calculate_novelty_score(query: str) -> float:
    """Example implementation approach."""
    novelty_factors = []
    
    # Factor 1: Semantic similarity to known patterns
    similarity_score = _calculate_pattern_similarity(query)
    novelty_factors.append(1.0 - similarity_score)  # Invert similarity
    
    # Factor 2: New metrics detection
    new_metrics_score = _detect_new_metrics_score(query)
    novelty_factors.append(new_metrics_score)
    
    # Factor 3: Query structure novelty
    structure_score = _analyze_query_structure_novelty(query)
    novelty_factors.append(structure_score)
    
    return sum(novelty_factors) / len(novelty_factors)
```

## 🎯 Next Sprint Setup

This sprint enables **Sprint 2.2: Advanced Priority Logic & UI Enhancement** by providing:
- Confidence scores for weighted priority calculation
- Novelty scores for learning value assessment
- Enhanced priority logic foundation
- Analytics data for UI enhancements

## 📞 When Complete

After completing this sprint:
1. Run all tests to ensure functionality works
2. Test integration with existing smart feedback system
3. Verify performance meets <100ms requirement
4. Document any issues or improvements for next sprint
5. Move to Sprint 2.2 for advanced priority logic and UI enhancements

**Good luck! You're building the intelligence layer of the feedback system! 🧠✨** 