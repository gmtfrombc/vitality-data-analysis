# SPRINT 4 PROMPT - Pattern Learning & Query Routing

## PROJECT CONTEXT

You are working on the **AAA Learning Enhancements Project** - adding automated learning capabilities to the Ask Anything AI Assistant (AAA). This is Sprint 4 of a 5-sprint project.

### Project Overview
The AAA is a healthcare data analysis assistant that converts natural language queries to SQL. We're building an automated learning system that captures user corrections, analyzes errors, and learns patterns for improved accuracy.

### Previous Sprint Completions

✅ **Sprint 1 COMPLETED** - Database foundation and basic correction service:
- Database tables with learning infrastructure
- Basic `CorrectionService` with CRUD operations
- Data models: `CorrectionSession`, `IntentPattern`

✅ **Sprint 2 COMPLETED** - Enhanced feedback UI with correction capture:
- `EnhancedFeedbackWidget` with correction interface
- UI integration replacing basic feedback widgets
- Basic error analysis methods in `CorrectionService`

✅ **Sprint 3 COMPLETED** - Sophisticated error analysis and automated suggestions:
- Enhanced error analysis with detailed categorization
- Intelligent suggestion generation with confidence scores
- One-click suggestion application functionality
- Users receive specific, actionable corrections

## SPRINT 4 OBJECTIVES

**Goal**: Implement pattern learning from corrections and add query routing based on learned patterns to dramatically improve response accuracy and speed.

**Key Deliverables**:
1. Pattern learning from successful corrections
2. Query routing to learned patterns before LLM processing
3. Enhanced query processing pipeline
4. Performance optimization for pattern matching
5. Code template learning and application

**User Impact**: Faster responses and higher accuracy for similar queries - learned patterns provide instant, correct answers.

## TECHNICAL REQUIREMENTS

### Pattern Learning System

Enhance `app/services/correction_service.py` with pattern learning capabilities:

```python
def _learn_from_correction(self, session: CorrectionSession, suggestion: Dict):
    """Learn patterns from successful corrections.
    
    Args:
        session: The correction session
        suggestion: The applied suggestion
    """
    try:
        # Learn intent patterns
        if suggestion.get("action_type") == "intent_modification":
            self._learn_intent_pattern(session, suggestion)
        
        # Learn code templates
        if session.original_code and suggestion.get("corrected_code"):
            self._learn_code_template(session, suggestion)
        
        # Update learning metrics
        self._update_learning_metrics(session, suggestion)
        
        logger.info(f"Learned from session {session.id}: {suggestion['type']}")
        
    except Exception as e:
        logger.error(f"Failed to learn from correction {session.id}: {e}")

def _learn_intent_pattern(self, session: CorrectionSession, suggestion: Dict):
    """Learn an intent pattern from a successful correction."""
    try:
        # Normalize the query for pattern matching
        normalized_query = self._normalize_query(session.original_query)
        
        # Get the corrected intent
        corrected_intent_json = suggestion.get("corrected_intent")
        if not corrected_intent_json and hasattr(session, 'corrected_intent_json'):
            corrected_intent_json = session.corrected_intent_json
        
        if not corrected_intent_json:
            logger.warning(f"No corrected intent available for session {session.id}")
            return
        
        # Check if similar pattern already exists
        existing_pattern = self._find_existing_pattern(normalized_query)
        
        if existing_pattern:
            # Update existing pattern
            self._update_pattern_usage(existing_pattern.id, success=True)
            logger.info(f"Updated existing pattern {existing_pattern.id}")
        else:
            # Create new pattern
            pattern_id = self._create_intent_pattern(
                query_pattern=normalized_query,
                canonical_intent_json=corrected_intent_json,
                session_id=session.id
            )
            logger.info(f"Created new intent pattern {pattern_id}")
            
    except Exception as e:
        logger.error(f"Failed to learn intent pattern: {e}")

def _normalize_query(self, query: str) -> str:
    """Normalize a query for pattern matching.
    
    Args:
        query: The original query
        
    Returns:
        Normalized query string for pattern matching
    """
    import re
    
    # Convert to lowercase
    normalized = query.lower().strip()
    
    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Replace numbers with placeholders for generalization
    normalized = re.sub(r'\b\d+\b', '[NUMBER]', normalized)
    
    # Replace specific names/IDs with placeholders
    normalized = re.sub(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', '[NAME]', normalized)
    
    # Standardize common phrases
    phrase_replacements = {
        'how many': 'count',
        'what is the average': 'average',
        'what is the total': 'sum',
        'show me': 'get',
        'tell me': 'get',
        'what are': 'get',
        'give me': 'get'
    }
    
    for phrase, replacement in phrase_replacements.items():
        normalized = normalized.replace(phrase, replacement)
    
    return normalized

def _find_existing_pattern(self, normalized_query: str) -> Optional[IntentPattern]:
    """Find an existing pattern that matches the normalized query."""
    try:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # First, try exact match
            cursor.execute("""
                SELECT * FROM intent_patterns 
                WHERE query_pattern = ?
                ORDER BY usage_count DESC
                LIMIT 1
            """, (normalized_query,))
            
            row = cursor.fetchone()
            if row:
                return self._row_to_intent_pattern(row)
            
            # Then try similarity matching
            cursor.execute("""
                SELECT * FROM intent_patterns
                ORDER BY usage_count DESC
            """)
            
            patterns = cursor.fetchall()
            
            # Find most similar pattern
            best_match = None
            best_similarity = 0.0
            
            for pattern_row in patterns:
                similarity = self._calculate_query_similarity(normalized_query, pattern_row["query_pattern"])
                if similarity > 0.8 and similarity > best_similarity:  # 80% similarity threshold
                    best_similarity = similarity
                    best_match = self._row_to_intent_pattern(pattern_row)
            
            return best_match
            
    except Exception as e:
        logger.error(f"Failed to find existing pattern: {e}")
        return None

def _calculate_query_similarity(self, query1: str, query2: str) -> float:
    """Calculate similarity between two queries.
    
    Args:
        query1: First query
        query2: Second query
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    # Simple word-based similarity for now
    words1 = set(query1.split())
    words2 = set(query2.split())
    
    if not words1 and not words2:
        return 1.0
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0.0

def _create_intent_pattern(self, query_pattern: str, canonical_intent_json: str, session_id: int) -> int:
    """Create a new intent pattern."""
    with self._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO intent_patterns 
            (query_pattern, canonical_intent_json, confidence_boost, usage_count, 
             success_rate, created_from_session_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            query_pattern, canonical_intent_json, 0.1, 1, 1.0, session_id
        ))
        return cursor.lastrowid

def _update_pattern_usage(self, pattern_id: int, success: bool = True):
    """Update pattern usage statistics."""
    try:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get current stats
            cursor.execute("""
                SELECT usage_count, success_rate FROM intent_patterns WHERE id = ?
            """, (pattern_id,))
            
            row = cursor.fetchone()
            if not row:
                return
            
            current_usage = row["usage_count"]
            current_success_rate = row["success_rate"]
            
            # Calculate new stats
            new_usage = current_usage + 1
            if success:
                new_success_rate = ((current_success_rate * current_usage) + 1) / new_usage
            else:
                new_success_rate = (current_success_rate * current_usage) / new_usage
            
            # Update pattern
            cursor.execute("""
                UPDATE intent_patterns 
                SET usage_count = ?, success_rate = ?, last_used_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_usage, new_success_rate, pattern_id))
            
            logger.info(f"Updated pattern {pattern_id}: usage={new_usage}, success_rate={new_success_rate:.2f}")
            
    except Exception as e:
        logger.error(f"Failed to update pattern usage: {e}")

def find_similar_patterns(self, query: str, limit: int = 5) -> List[IntentPattern]:
    """Find similar learned patterns for a query.
    
    Args:
        query: The user query
        limit: Maximum number of patterns to return
        
    Returns:
        List of similar patterns sorted by relevance and success rate
    """
    normalized_query = self._normalize_query(query)
    
    # Check cache first
    cache_key = self._get_query_hash(normalized_query)
    cached_patterns = self._get_cached_patterns(cache_key)
    if cached_patterns:
        return cached_patterns[:limit]
    
    try:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all patterns ordered by usage and success rate
            cursor.execute("""
                SELECT * FROM intent_patterns
                WHERE success_rate >= 0.7
                ORDER BY usage_count DESC, success_rate DESC
            """)
            
            patterns = cursor.fetchall()
            
            # Calculate similarity scores
            scored_patterns = []
            for pattern_row in patterns:
                pattern = self._row_to_intent_pattern(pattern_row)
                similarity = self._calculate_query_similarity(normalized_query, pattern.query_pattern)
                
                if similarity > 0.5:  # Minimum similarity threshold
                    # Combined score: similarity * success_rate * log(usage_count)
                    import math
                    usage_factor = math.log(max(pattern.usage_count, 1) + 1)
                    combined_score = similarity * pattern.success_rate * usage_factor
                    
                    scored_patterns.append((combined_score, pattern))
            
            # Sort by combined score
            scored_patterns.sort(key=lambda x: x[0], reverse=True)
            
            # Extract patterns
            result_patterns = [pattern for score, pattern in scored_patterns[:limit]]
            
            # Cache the results
            self._cache_similar_patterns(cache_key, result_patterns)
            
            return result_patterns
            
    except Exception as e:
        logger.error(f"Failed to find similar patterns: {e}")
        return []

def _get_query_hash(self, query: str) -> str:
    """Get hash for query caching."""
    import hashlib
    return hashlib.md5(query.encode()).hexdigest()

def _get_cached_patterns(self, query_hash: str) -> Optional[List[IntentPattern]]:
    """Get cached similar patterns."""
    try:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT similar_patterns FROM query_similarity_cache 
                WHERE query_hash = ? AND computed_at > datetime('now', '-1 hour')
            """, (query_hash,))
            
            row = cursor.fetchone()
            if row:
                pattern_ids = json.loads(row["similar_patterns"])
                return self._get_patterns_by_ids(pattern_ids)
            
    except Exception as e:
        logger.warning(f"Failed to get cached patterns: {e}")
    
    return None

def _cache_similar_patterns(self, query_hash: str, patterns: List[IntentPattern]):
    """Cache similar patterns for faster lookup."""
    try:
        pattern_ids = [p.id for p in patterns if p.id]
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO query_similarity_cache 
                (query_hash, similar_patterns, computed_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (query_hash, json.dumps(pattern_ids)))
            
    except Exception as e:
        logger.warning(f"Failed to cache patterns: {e}")

def _learn_code_template(self, session: CorrectionSession, suggestion: Dict):
    """Learn a code template from successful correction."""
    try:
        corrected_code = suggestion.get("corrected_code")
        if not corrected_code:
            return
        
        # Generate intent signature for template matching
        intent_signature = self._generate_intent_signature(session.original_intent_json)
        
        # Check for existing template
        existing_template = self._find_existing_template(intent_signature)
        
        if existing_template:
            self._update_template_usage(existing_template["id"], success=True)
        else:
            self._create_code_template(intent_signature, corrected_code, session.id)
            
    except Exception as e:
        logger.error(f"Failed to learn code template: {e}")

def _generate_intent_signature(self, intent_json: str) -> str:
    """Generate a signature for intent matching."""
    try:
        intent_data = json.loads(intent_json) if intent_json else {}
        
        # Create a normalized signature
        signature = {
            "analysis_type": intent_data.get("analysis_type", "unknown"),
            "target_field": intent_data.get("target_field", "unknown"),
            "has_filters": bool(intent_data.get("filters")),
            "has_grouping": bool(intent_data.get("grouping"))
        }
        
        return json.dumps(signature, sort_keys=True)
        
    except Exception as e:
        logger.warning(f"Failed to generate intent signature: {e}")
        return "{}"
```

### Query Processing Enhancement

Modify `app/engine.py` to add pattern matching before LLM processing:

```python
def process_query(self, query):
    """Enhanced query processing with pattern matching.
    
    First checks for learned patterns, falls back to LLM if no high-confidence match.
    """
    from app.services.correction_service import CorrectionService
    
    try:
        # NEW: Check for learned patterns first
        correction_service = CorrectionService()
        patterns = correction_service.find_similar_patterns(query)
        
        if patterns and patterns[0].success_rate > 0.9 and patterns[0].usage_count > 2:
            # Use learned pattern (high confidence)
            logger.info(f"Using learned pattern {patterns[0].id} for query: {query[:50]}...")
            
            # Parse the canonical intent
            from app.utils.query_intent import parse_intent_json
            self.intent = parse_intent_json(patterns[0].canonical_intent_json)
            
            # Mark as high confidence
            if hasattr(self.intent, 'parameters'):
                self.intent.parameters = self.intent.parameters or {}
                self.intent.parameters["confidence"] = 0.95
                self.intent.parameters["source"] = "learned_pattern"
                self.intent.parameters["pattern_id"] = patterns[0].id
            
            # Update pattern usage
            correction_service._update_pattern_usage(patterns[0].id, success=True)
            
            return self.intent
            
        elif patterns and patterns[0].success_rate > 0.7:
            # Medium confidence - use pattern but also check with LLM
            logger.info(f"Using pattern {patterns[0].id} with LLM validation for query: {query[:50]}...")
            
            pattern_intent = parse_intent_json(patterns[0].canonical_intent_json)
            llm_intent = self.get_query_intent()  # Get LLM opinion
            
            # Compare intents and use pattern if they're similar
            if self._intents_are_similar(pattern_intent, llm_intent):
                self.intent = pattern_intent
                if hasattr(self.intent, 'parameters'):
                    self.intent.parameters = self.intent.parameters or {}
                    self.intent.parameters["confidence"] = 0.85
                    self.intent.parameters["source"] = "pattern_validated"
                
                correction_service._update_pattern_usage(patterns[0].id, success=True)
                return self.intent
            
    except Exception as e:
        logger.warning(f"Pattern matching failed, falling back to LLM: {e}")
    
    # EXISTING: Fall back to normal LLM processing
    logger.info(f"Using LLM processing for query: {query[:50]}...")
    return self.get_query_intent()

def _intents_are_similar(self, intent1, intent2) -> bool:
    """Check if two intents are similar enough to trust pattern matching."""
    try:
        # Compare key fields
        if intent1.analysis_type != intent2.analysis_type:
            return False
        
        if intent1.target_field != intent2.target_field:
            return False
        
        # Compare filters (basic check)
        filters1 = getattr(intent1, 'filters', []) or []
        filters2 = getattr(intent2, 'filters', []) or []
        
        if len(filters1) != len(filters2):
            return False
        
        return True
        
    except Exception as e:
        logger.warning(f"Failed to compare intents: {e}")
        return False
```

### Performance Optimization

Add performance optimizations for pattern matching:

```python
# In correction_service.py

def _create_performance_indexes(self):
    """Create additional indexes for performance."""
    try:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Additional performance indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_intent_patterns_success_rate ON intent_patterns(success_rate DESC)",
                "CREATE INDEX IF NOT EXISTS idx_intent_patterns_last_used ON intent_patterns(last_used_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_query_similarity_cache_computed ON query_similarity_cache(computed_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_correction_sessions_created ON correction_sessions(created_at DESC)"
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
                
            logger.info("Created performance indexes")
            
    except Exception as e:
        logger.warning(f"Failed to create performance indexes: {e}")

def cleanup_old_cache_entries(self, days_old: int = 7):
    """Clean up old cache entries to maintain performance."""
    try:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM query_similarity_cache 
                WHERE computed_at < datetime('now', '-' || ? || ' days')
            """, (days_old,))
            
            deleted = cursor.rowcount
            logger.info(f"Cleaned up {deleted} old cache entries")
            
    except Exception as e:
        logger.warning(f"Failed to cleanup cache entries: {e}")

def get_learning_metrics(self, days: int = 30) -> Dict[str, Any]:
    """Get learning system performance metrics."""
    try:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Pattern usage metrics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_patterns,
                    AVG(usage_count) as avg_usage,
                    AVG(success_rate) as avg_success_rate,
                    COUNT(CASE WHEN success_rate > 0.9 THEN 1 END) as high_confidence_patterns
                FROM intent_patterns
            """)
            pattern_stats = cursor.fetchone()
            
            # Recent correction metrics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_corrections,
                    COUNT(CASE WHEN status = 'integrated' THEN 1 END) as successful_corrections,
                    COUNT(CASE WHEN created_at > datetime('now', '-' || ? || ' days') THEN 1 END) as recent_corrections
                FROM correction_sessions
            """, (days,))
            correction_stats = cursor.fetchone()
            
            # Cache performance
            cursor.execute("""
                SELECT COUNT(*) as cached_queries
                FROM query_similarity_cache
                WHERE computed_at > datetime('now', '-1 hour')
            """)
            cache_stats = cursor.fetchone()
            
            return {
                "patterns": {
                    "total": pattern_stats["total_patterns"] or 0,
                    "average_usage": pattern_stats["avg_usage"] or 0,
                    "average_success_rate": pattern_stats["avg_success_rate"] or 0,
                    "high_confidence": pattern_stats["high_confidence_patterns"] or 0
                },
                "corrections": {
                    "total": correction_stats["total_corrections"] or 0,
                    "successful": correction_stats["successful_corrections"] or 0,
                    "recent": correction_stats["recent_corrections"] or 0,
                    "success_rate": (correction_stats["successful_corrections"] or 0) / max(correction_stats["total_corrections"] or 1, 1)
                },
                "cache": {
                    "recent_entries": cache_stats["cached_queries"] or 0
                }
            }
            
    except Exception as e:
        logger.error(f"Failed to get learning metrics: {e}")
        return {}
```

## FILES TO CREATE/MODIFY

### Files to Modify
```
app/services/correction_service.py (add pattern learning and query routing)
app/engine.py (integrate pattern matching into query processing)
tests/services/test_correction_service_basic.py (expand tests)
```

### Files to Create
```
app/utils/pattern_matcher.py (optional optimization component)
tests/services/test_pattern_learning.py
tests/integration/test_query_routing.py
migrations/010_performance_indexes.sql (optional optimization)
```

## SUCCESS CRITERIA

You are done when:
- [ ] System learns patterns from successful corrections
- [ ] Similar queries are routed to learned patterns before LLM processing
- [ ] Pattern matching performance is <100ms for cached queries
- [ ] Learned patterns achieve 90%+ accuracy on repeated query types
- [ ] No degradation in normal query processing performance
- [ ] Graceful fallback when patterns are unavailable
- [ ] Cache system maintains good performance
- [ ] Learning metrics provide visibility into system effectiveness

## TESTING & GITHUB WORKFLOW

After completing implementation:

1. **Run pattern learning tests**:
   ```bash
   pytest tests/services/test_pattern_learning.py -v
   pytest tests/integration/test_query_routing.py -v
   pytest tests/ -v
   ```

2. **Test learning workflow manually**:
   ```bash
   python run.py
   # Submit queries, provide corrections, re-submit similar queries
   # Verify faster response times and improved accuracy
   ```

3. **Performance benchmarking**:
   ```bash
   python -c "
   from app.services.correction_service import CorrectionService
   import time
   cs = CorrectionService()
   start = time.time()
   patterns = cs.find_similar_patterns('average BMI of active patients')
   print(f'Pattern lookup took {(time.time() - start) * 1000:.2f}ms')
   "
   ```

4. **Commit and push changes**:
   ```bash
   git add .
   git commit -m "Sprint 4: Add pattern learning and query routing

   - Implement pattern learning from successful corrections
   - Add query routing to check learned patterns before LLM processing  
   - Enhance query processing pipeline with pattern matching
   - Add performance optimization for pattern lookup and caching
   - System now learns from corrections and provides faster, more accurate responses
   - Similar queries are handled instantly with high confidence"
   
   git push origin main
   ```

## IMPORTANT NOTES

- **Performance**: Pattern matching must be fast (<100ms) to avoid slowing down queries
- **Accuracy**: Only use high-confidence patterns (>90% success rate) for direct routing
- **Fallback**: Always gracefully fall back to LLM processing when patterns fail
- **Learning**: System should continuously improve pattern quality based on usage
- **Monitoring**: Track pattern effectiveness and system performance metrics

## DEPENDENCIES ON PREVIOUS SPRINTS

This sprint builds on all previous work:
- Uses database foundation from Sprint 1
- Leverages correction capture from Sprint 2  
- Applies learning from corrections made in Sprint 3
- Integrates with existing query processing pipeline

## WHEN YOU'RE STUCK

If you encounter issues:
1. **Start with simple pattern matching** - Exact matches before similarity scoring
2. **Focus on performance** - Cache aggressively and optimize database queries
3. **Ensure fallback works** - Never break existing LLM processing
4. **Test incrementally** - Verify each component before integration

---

**START IMPLEMENTING SPRINT 4 NOW** 