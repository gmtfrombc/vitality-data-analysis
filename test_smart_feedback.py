#!/usr/bin/env python3
"""
Test script to verify smart feedback system works correctly.
"""

from app.services.correction_service import CorrectionService
from app.utils.feedback_db import insert_feedback
from app.utils.smart_feedback import (
    should_request_feedback,
    get_feedback_priority,
    get_feedback_message,
    has_recent_similar_feedback,
    calculate_confidence_score,
    calculate_novelty_score,
    is_novel_query_pattern,
)
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_smart_feedback_system():
    """Test the smart feedback system logic."""
    print("=== Testing Smart Feedback System ===")

    # Test with a fresh query
    test_query = "What is the average triglyceride level?"

    print("\n--- Test 1: Fresh Query ---")
    print(f"Query: '{test_query}'")
    should_request = should_request_feedback(test_query)
    priority = get_feedback_priority(test_query)
    message = get_feedback_message(priority)
    print(f"Should request feedback: {should_request}")
    print(f"Priority: {priority}")
    print(f"Message: {message}")

    # Add feedback for the query
    print("\n--- Test 2: Adding Feedback ---")
    success = insert_feedback(question=test_query, rating="up")
    print(f"Feedback inserted: {success}")

    # Test exact match
    print("\n--- Test 3: Exact Match ---")
    should_request_2 = should_request_feedback(test_query)
    priority_2 = get_feedback_priority(test_query)
    print(f"Should request feedback: {should_request_2}")
    print(f"Priority: {priority_2}")

    # Test very similar queries to find the threshold
    cs = CorrectionService()

    similar_queries = [
        "What is the average triglyceride level",  # Remove question mark
        "What is average triglyceride level?",  # Remove "the"
        "What's the average triglyceride level?",  # Contraction
        "What is the avg triglyceride level?",  # Abbreviation
        "average triglyceride level",  # Remove question words
    ]

    print("\n--- Test 4: Similarity Testing ---")
    for i, similar_query in enumerate(similar_queries):
        similarity = cs._calculate_query_similarity(test_query, similar_query)
        has_similar = has_recent_similar_feedback(similar_query)
        should_request = should_request_feedback(similar_query)

        print(f"\n{i+1}. '{similar_query}'")
        print(f"   Similarity: {similarity:.3f}")
        print(f"   Has similar feedback: {has_similar}")
        print(f"   Should request: {should_request}")

        if similarity >= 0.85:
            print("   ✅ Above threshold (0.85) - should be skipped!")
        else:
            print("   ⚪ Below threshold (0.85) - treated as new query")

    print("\n=== Smart Feedback Test Complete ===")


def test_enhanced_priority_with_confidence_and_novelty():
    """Test enhanced priority calculation with confidence and novelty."""
    print("\n=== Testing Enhanced Priority Logic ===")

    # Test high confidence, low novelty query (should be low priority)
    simple_query = "What is the average BMI?"
    print("\n--- Test 1: Simple Query ---")
    print(f"Query: '{simple_query}'")

    confidence = calculate_confidence_score(
        simple_query,
        {
            "data": [{"bmi": 25.0}, {"bmi": 27.0}],
            "summary": "Average BMI calculated",
            "execution_time": 1.0,
        },
    )
    novelty = calculate_novelty_score(simple_query)
    priority = get_feedback_priority(
        simple_query,
        {"data": [{"bmi": 25.0}, {"bmi": 27.0}], "summary": "Average BMI calculated"},
    )

    print(f"Confidence score: {confidence:.3f}")
    print(f"Novelty score: {novelty:.3f}")
    print(f"Priority: {priority}")

    # Test low confidence, high novelty query (should be high priority)
    complex_query = (
        "What is the correlation between xyz_metric and cardiovascular_risk_index?"
    )
    print("\n--- Test 2: Complex/Novel Query ---")
    print(f"Query: '{complex_query}'")

    confidence = calculate_confidence_score(
        complex_query, {"error": "Unknown field xyz_metric", "execution_time": 8.0}
    )
    novelty = calculate_novelty_score(complex_query)
    is_novel = is_novel_query_pattern(complex_query)
    priority = get_feedback_priority(
        complex_query, {"error": "Unknown field xyz_metric"}
    )

    print(f"Confidence score: {confidence:.3f}")
    print(f"Novelty score: {novelty:.3f}")
    print(f"Is novel pattern: {is_novel}")
    print(f"Priority: {priority}")

    # Test moderate query
    moderate_query = "Show me the distribution of glucose levels"
    print("\n--- Test 3: Moderate Query ---")
    print(f"Query: '{moderate_query}'")

    confidence = calculate_confidence_score(
        moderate_query,
        {
            "data": [{"glucose": i} for i in range(10)],
            "summary": "Distribution analysis",
            "visualization": {"type": "histogram"},
        },
    )
    novelty = calculate_novelty_score(moderate_query)
    priority = get_feedback_priority(
        moderate_query,
        {
            "data": [{"glucose": i} for i in range(10)],
            "summary": "Distribution analysis",
        },
    )

    print(f"Confidence score: {confidence:.3f}")
    print(f"Novelty score: {novelty:.3f}")
    print(f"Priority: {priority}")

    print("\n=== Enhanced Priority Test Complete ===")


def test_confidence_scoring_integration():
    """Test confidence scoring integration."""
    print("\n=== Testing Confidence Scoring ===")

    # Test with good results
    good_results = {
        "data": [{"bmi": i} for i in range(20)],
        "summary": "Comprehensive analysis of BMI data showing clear patterns.",
        "visualization": {"type": "histogram"},
        "execution_time": 2.0,
    }

    confidence = calculate_confidence_score("average BMI", good_results)
    print(f"Good results confidence: {confidence:.3f}")

    # Test with poor results
    poor_results = {
        "error": "Database connection failed",
        "data": None,
        "execution_time": 15.0,
    }

    confidence = calculate_confidence_score("average BMI", poor_results)
    print(f"Poor results confidence: {confidence:.3f}")

    # Test with no results
    confidence = calculate_confidence_score("average BMI", {})
    print(f"No results confidence: {confidence:.3f}")

    print("=== Confidence Scoring Test Complete ===")


def test_novelty_detection_integration():
    """Test novelty detection integration."""
    print("\n=== Testing Novelty Detection ===")

    # Test common queries (should have low novelty)
    common_queries = ["average BMI", "count of patients", "total weight"]

    print("Common queries (should have low novelty):")
    for query in common_queries:
        novelty = calculate_novelty_score(query)
        is_novel = is_novel_query_pattern(query)
        print(f"  '{query}': novelty={novelty:.3f}, is_novel={is_novel}")

    # Test novel queries (should have high novelty)
    novel_queries = [
        "correlation between xyz_metric and abc_level",
        "predict future BMI trends",
        "variance in new_biomarker_xyz",
    ]

    print("\nNovel queries (should have high novelty):")
    for query in novel_queries:
        novelty = calculate_novelty_score(query)
        is_novel = is_novel_query_pattern(query)
        print(f"  '{query}': novelty={novelty:.3f}, is_novel={is_novel}")

    print("=== Novelty Detection Test Complete ===")


if __name__ == "__main__":
    test_smart_feedback_system()
    test_enhanced_priority_with_confidence_and_novelty()
    test_confidence_scoring_integration()
    test_novelty_detection_integration()
