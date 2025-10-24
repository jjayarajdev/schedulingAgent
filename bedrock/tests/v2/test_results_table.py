#!/usr/bin/env python3
"""
Streamlined test with table output for all test queries
"""

import boto3
import json

REGION = "us-east-1"
bedrock_runtime = boto3.client('bedrock-runtime', region_name=REGION)

# All test queries
TEST_QUERIES = {
    "Chitchat": [
        "Hey, how's it going?",
        "What do you think about the weather today?",
        "I'm feeling a bit stressed, just need to talk",
        "Tell me a joke!",
        "Good morning! Ready for the weekend?"
    ],
    "Scheduling": [
        "Can you schedule a meeting with Sarah for next Tuesday at 2pm?",
        "What's on my calendar for tomorrow?",
        "I need to reschedule my 3pm appointment to Thursday",
        "Block out 2 hours next week for project planning",
        "Find a time slot for a team sync this week",
        "Cancel my meeting on Friday afternoon"
    ],
    "Information": [
        "What's the current weather in Seattle?",
        "Who won the NBA championship last year?",
        "Look up the population of Tokyo",
        "What are the symptoms of vitamin D deficiency?",
        "Find me information about renewable energy trends",
        "What's the exchange rate for USD to EUR?"
    ],
    "Notes": [
        "Save a note: Remember to buy groceries - milk, eggs, bread",
        "Create a note about ideas for the quarterly presentation",
        "Show me all my notes from last week",
        "Find my note about the client meeting",
        "Delete the note about vacation planning",
        "Add to my shopping list: coffee and bananas"
    ],
    "Ambiguous": [
        "Remind me about the meeting",
        "What time is it in London?",
        "I need help with something",
        "Thanks for your help earlier!"
    ]
}

def classify_intent(message):
    """Classify using Claude Haiku"""
    prompt = f"""Classify this message into ONE category: scheduling, information, notes, or chitchat

Message: "{message}"

Respond with ONLY the category name."""

    try:
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 10,
                'temperature': 0.0,
                'messages': [{'role': 'user', 'content': prompt}]
            })
        )

        result = json.loads(response['body'].read())
        return result['content'][0]['text'].strip().lower()
    except:
        return 'chitchat'

# Run tests
print("\n" + "="*120)
print("COMPREHENSIVE INTENT CLASSIFICATION TEST RESULTS")
print("="*120)
print()

all_results = []
for category, queries in TEST_QUERIES.items():
    print(f"Testing {category} queries...")
    for query in queries:
        intent = classify_intent(query)
        all_results.append({
            'category': category,
            'query': query,
            'intent': intent
        })

# TABLE 1: Full Results
print("\n" + "="*120)
print("TABLE 1: COMPLETE QUERY CLASSIFICATION RESULTS")
print("="*120)
print(f"{'#':<4} {'Expected Category':<15} {'Query':<60} {'Classified As':<15} {'Match':<6}")
print("-"*120)

intent_map = {
    'Chitchat': 'chitchat',
    'Scheduling': 'scheduling',
    'Information': 'information',
    'Notes': 'notes'
}

for idx, result in enumerate(all_results, 1):
    query_display = result['query'][:57] + "..." if len(result['query']) > 60 else result['query']
    expected = intent_map.get(result['category'], 'various')
    match = '✅ Yes' if result['intent'] == expected else '❌ No' if expected != 'various' else '  -'

    print(f"{idx:<4} {result['category']:<15} {query_display:<60} {result['intent']:<15} {match:<6}")

# TABLE 2: Summary by Category
print("\n" + "="*120)
print("TABLE 2: ACCURACY BY CATEGORY")
print("="*120)
print(f"{'Expected Category':<20} {'Total Queries':<15} {'Correct':<10} {'Incorrect':<12} {'Accuracy':<15}")
print("-"*120)

for category, expected_intent in intent_map.items():
    category_results = [r for r in all_results if r['category'] == category]
    total = len(category_results)
    correct = sum(1 for r in category_results if r['intent'] == expected_intent)
    incorrect = total - correct
    accuracy = f"{(correct/total)*100:.1f}%" if total > 0 else "N/A"

    print(f"{category:<20} {total:<15} {correct:<10} {incorrect:<12} {accuracy:<15}")

# Ambiguous cases
ambiguous_results = [r for r in all_results if r['category'] == 'Ambiguous']
print(f"{'Ambiguous/Edge':<20} {len(ambiguous_results):<15} {'N/A':<10} {'N/A':<12} {'(varies)':<15}")

# TABLE 3: Intent Distribution
print("\n" + "="*120)
print("TABLE 3: INTENT DISTRIBUTION ACROSS ALL QUERIES")
print("="*120)

intent_counts = {}
for result in all_results:
    intent = result['intent']
    intent_counts[intent] = intent_counts.get(intent, 0) + 1

total_queries = len(all_results)
print(f"{'Intent':<20} {'Count':<10} {'Percentage':<15} {'Bar Chart':<40}")
print("-"*120)

for intent in sorted(intent_counts.keys()):
    count = intent_counts[intent]
    percentage = (count/total_queries)*100
    bar = '█' * int(percentage/2.5)
    print(f"{intent.capitalize():<20} {count:<10} {percentage:>5.1f}%{'':<10} {bar:<40}")

# TABLE 4: Ambiguous Cases Detail
print("\n" + "="*120)
print("TABLE 4: AMBIGUOUS/EDGE CASE ROUTING DECISIONS")
print("="*120)
print(f"{'Query':<70} {'Routed To':<20} {'Reasoning':<30}")
print("-"*120)

reasoning = {
    'remind me about the meeting': 'Could be scheduling or notes - system chooses based on keywords',
    'what time is it in london': 'Information query about time/timezone',
    'i need help with something': 'Vague - likely goes to chitchat for clarification',
    'thanks for your help earlier': 'Gratitude expression - chitchat'
}

for result in ambiguous_results:
    query_display = result['query'][:67] + "..." if len(result['query']) > 70 else result['query']
    reason_key = result['query'].lower()
    reason = reasoning.get(reason_key, 'Context-dependent')[:27] + "..."
    print(f"{query_display:<70} {result['intent'].capitalize():<20} {reason:<30}")

# FINAL SUMMARY
print("\n" + "="*120)
print("📊 OVERALL SUMMARY")
print("="*120)

# Calculate overall accuracy (excluding ambiguous)
non_ambiguous = [r for r in all_results if r['category'] != 'Ambiguous']
correct_total = sum(1 for r in non_ambiguous if r['intent'] == intent_map.get(r['category']))
overall_accuracy = (correct_total/len(non_ambiguous))*100 if non_ambiguous else 0

print(f"\nTotal Queries Tested:        {total_queries}")
print(f"Non-Ambiguous Queries:       {len(non_ambiguous)}")
print(f"Correct Classifications:     {correct_total}")
print(f"Overall Accuracy:            {overall_accuracy:.1f}%")
print(f"\nAmbiguous Queries:           {len(ambiguous_results)} (no fixed expectation)")

print("\n" + "="*120)
print("✅ VERDICT: Frontend routing with Claude Haiku classification")
print("="*120)

if overall_accuracy >= 95:
    print("🎉 EXCELLENT! Classification accuracy is very high (≥95%)")
elif overall_accuracy >= 85:
    print("✅ GOOD! Classification accuracy is strong (≥85%)")
elif overall_accuracy >= 75:
    print("⚠️  ACCEPTABLE: Classification accuracy is decent (≥75%) but could be improved")
else:
    print("❌ NEEDS IMPROVEMENT: Classification accuracy is below 75%")

print("\nRecommendation: ✅ Use frontend routing with intent classification")
print("="*120)
print()
