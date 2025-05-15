# ICD-10 Clinical Condition Mapping

## Overview

This document outlines the hybrid clinical condition mapping system that translates unstructured clinical language from user queries to standardized ICD-10 diagnostic codes. The system enables natural language queries about conditions while ensuring accurate retrieval of data from the database.

## Implementation Architecture

The system uses a hybrid approach with three layers:

1. **Core Conditions Dictionary**: A curated YAML file containing mappings for the most common conditions in the program
2. **Synonym Matching**: Handles variations in terminology for known conditions
3. **AI-Powered Fallback**: Uses OpenAI function calls to look up ICD-10 codes for conditions not in our core dictionary

## Components

### 1. Condition Mapper (`app/utils/condition_mapper.py`)

The central component that:
- Loads condition mappings from a YAML file
- Maps condition terms to canonical names
- Maps canonical names to ICD-10 codes
- Handles AI-powered lookups for unknown conditions
- Determines if clarification is needed

Key methods:
- `get_canonical_condition(term)`: Get standardized condition name
- `get_icd_codes(condition)`: Get ICD-10 codes for a condition
- `lookup_icd_codes_with_ai(condition)`: Use OpenAI to get codes for unknown conditions
- `should_ask_clarifying_question(condition)`: Determine if clarification is needed

### 2. Condition Mappings (`app/utils/condition_mappings.yaml`)

YAML file containing the core condition dictionary with:
- Canonical condition names
- Associated ICD-10 codes
- Common synonyms and variations
- Brief descriptions

Each condition entry includes:
```yaml
- canonical: "type_2_diabetes"
  description: "Type 2 diabetes mellitus"
  codes: 
    - "E11.9"  # Type 2 diabetes mellitus without complications
    - "E11.8"  # Type 2 diabetes mellitus with unspecified complications
  synonyms:
    - "type 2 diabetes"
    - "t2dm"
    - "type ii diabetes"
```

### 3. Query Intent Integration (`app/utils/query_intent.py`)

Functions that integrate condition mapping with the query intent system:
- `get_condition_filter_sql(condition)`: Generate SQL filter for a condition
- `get_canonical_condition(term)`: Get the canonical name from the condition mapper

### 4. Intent Clarification (`app/utils/intent_clarification.py`)

Enhancements to the clarification system to handle condition-related queries:
- New `CONDITION_UNCLEAR` slot type
- Identification of missing or ambiguous condition information
- Generation of clarifying questions for unknown conditions

## AI-Powered Fallback

The OpenAI function call structure:
```python
{
  "name": "provide_icd10_codes",
  "parameters": {
    "condition_name": "string",
    "icd10_codes": ["string"],
    "description": "string",
    "confidence": "number"
  }
}
```

Key aspects:
- Only uses AI results when confidence score is high enough (>=0.6)
- Provides graceful fallback when an unknown condition is encountered
- Returns structured data suitable for SQL queries
- Includes error handling and logging

## Usage Flow

1. User asks a condition-related question (e.g., "How many patients have type 2 diabetes?")
2. The query intent parser identifies a condition-related query
3. The system looks up the condition in the core mappings
4. If found, it uses the pre-defined ICD-10 codes for the SQL query
5. If not found, it attempts an AI-powered lookup
6. If the AI lookup is successful and confident, it uses those codes
7. If the AI lookup fails or has low confidence, it triggers a clarifying question

## Future Enhancements

Potential improvements:
- Expand the core condition dictionary with more conditions
- Implement condition normalization in the ETL process
- Add support for multi-condition queries (AND/OR logic)
- Cache AI-powered lookups to improve performance
- Implement fuzzy matching for condition terms 