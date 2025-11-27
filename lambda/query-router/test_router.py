#!/usr/bin/env python3
"""
Test script for query router Lambda function
"""

import json
import sys
sys.path.insert(0, '.')

from handler import classify_query_complexity

# Test queries
test_queries = {
    "SIMPLE": [
        "Show me all my projects",
        "What's the weather tomorrow?",
        "Tell me about project PRJ-78945",
        "What are your working hours?",
        "Add a note to my appointment"
    ],
    "COMPLEX": [
        "Schedule my most urgent project for the earliest time",
        "If weather is good next week, schedule my outdoor project",
        "Check all my pending projects and schedule the urgent ones",
        "Find available slots for next week and check weather",
        "Schedule all my installation projects"
    ]
}

print("=" * 80)
print("TESTING QUERY ROUTER - Complexity Classification")
print("=" * 80)

# Test simple queries
print("\n### SIMPLE QUERIES (Expected: SIMPLE) ###\n")
for query in test_queries["SIMPLE"]:
    result = classify_query_complexity(query)
    status = "PASS" if result == "SIMPLE" else "FAIL"
    print(f"{status} '{query[:50]}...' -> {result}")

# Test complex queries
print("\n### COMPLEX QUERIES (Expected: COMPLEX) ###\n")
for query in test_queries["COMPLEX"]:
    result = classify_query_complexity(query)
    status = "PASS" if result == "COMPLEX" else "FAIL"
    print(f"{status} '{query[:50]}...' -> {result}")

print("\n" + "=" * 80)
print("Test completed!")
print("=" * 80)
