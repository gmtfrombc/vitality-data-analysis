# Smart Feedback System - Next Cursor Assistant Prompt

## 🎯 Your Mission
You are implementing **Phase 2 & 3** of the Smart Feedback System for a medical data analysis assistant. Your goal is to build intelligent feedback curation that reduces user fatigue while maximizing learning value.

## 📋 Current State (Phase 1 - COMPLETED ✅)
- ✅ Basic duplicate detection working (`app/utils/smart_feedback.py`)
- ✅ Priority system (High/Medium/Low/Skip) implemented
- ✅ Enhanced feedback widget with custom messages
- ✅ Integration with main data assistant (`app/data_assistant.py`)
- ✅ Database foundation with correction service (`app/services/correction_service.py`)

## 🚀 Your Starting Point: Sprint 2.1

### Immediate Task: Confidence Scoring & Novelty Detection (2-3 hours)

**Goal**: Enhance feedback decisions with confidence scoring and novelty detection.

**Files to Create/Modify**:
1. **Enhance** `app/utils/smart_feedback.py` - Add confidence and novelty functions
2. **Create** `app/utils/confidence_scoring.py` - Intent and result quality scoring
3. **Create** `app/utils/novelty_detection.py` - Query pattern novelty analysis

### Key Functions to Implement:

```python
# In app/utils/smart_feedback.py
def calculate_confidence_score(query: str, results: Dict[str, Any]) -> float:
    """Calculate confidence score for query results (0.0-1.0)."""
    
def calculate_novelty_score(query: str) -> float:
    """Calculate novelty score for query pattern (0.0-1.0)."""
    
def get_feedback_priority(query: str, results: Dict[str, Any] = None) -> str:
    """Enhanced priority calculation with confidence and novelty."""
```

## 📚 Key Resources Available

### Existing Infrastructure You Can Use:
- **Similarity Calculation**: `CorrectionService._calculate_query_similarity()`
- **Database**: Existing feedback tables + correction learning tables
- **Intent Parsing**: `app/utils/query_intent.py`
- **Pattern Learning**: `app/services/correction_service.py`

### Testing Framework:
- Use existing test patterns in `test_smart_feedback.py`
- Follow pytest conventions with fixtures
- Test with temporary database (`temp_db` fixture)

## 🎯 Success Criteria for Sprint 2.1:
- [ ] Confidence scoring reflects result quality accurately
- [ ] Novelty detection identifies new vs. known patterns
- [ ] Enhanced priority calculation uses multiple factors
- [ ] All tests pass and maintain backward compatibility
- [ ] Performance stays under 100ms for feedback decisions

## 📖 Full Project Plan
See `SMART_FEEDBACK_PHASE_2_3_PROJECT_PLAN.md` for complete sprint details, deliverables, and technical specifications.

## 🔧 Implementation Tips:
1. **Start Small**: Implement basic confidence scoring first
2. **Use Existing Code**: Leverage `CorrectionService` similarity functions
3. **Test Early**: Write tests as you implement each function
4. **Maintain Compatibility**: Don't break existing Phase 1 functionality
5. **Log Everything**: Add logging for debugging and monitoring

## 🚨 Important Notes:
- Follow existing code conventions (snake_case, docstrings)
- Use existing database connection patterns
- Maintain backward compatibility with Phase 1
- Test with real data from `patient_data.db`
- Performance is critical - cache expensive operations

## 📞 When You're Ready for Next Sprint:
After completing Sprint 2.1, move to Sprint 2.2 (Advanced Priority Logic & UI Enhancement) as detailed in the full project plan.

**Good luck! The foundation is solid - now let's make it intelligent! 🧠✨** 