#!/usr/bin/env python3
"""
Test Improved Classification Prompt (Version 2.0)
Tests the two previously misclassified queries
"""

import boto3
import json

REGION = "us-east-1"
bedrock_runtime = boto3.client('bedrock-runtime', region_name=REGION)

# Improved prompt (Version 2.0)
IMPROVED_PROMPT_TEMPLATE = """You are an intent classifier for a property management scheduling system.

Given a user message, classify it into ONE of these categories:

1. **scheduling**:
   - Listing/showing projects ("show me my projects", "what projects do I have", "list projects")
   - Booking appointments ("schedule an appointment", "book a time")
   - Checking availability ("what dates are available", "when can I schedule")
   - Getting dates/times ("available times", "open slots")
   - Confirming, rescheduling, or canceling appointments
   - Calendar operations ("what's on my calendar", "block out time")

2. **information**:
   - Specific project details ("tell me about project X", "details for project 123")
   - Appointment status ("is my appointment confirmed")
   - Working hours ("what time do you open")
   - Weather forecasts, general knowledge queries
   - Factual information lookups ("population of", "exchange rate")
   - EXCLUDE: Personal reminders and lists (those are notes)

3. **notes**:
   - Adding notes ("add a note", "write a note", "remember this", "save a note")
   - Creating lists ("shopping list", "to-do list", "add to my list")
   - Viewing notes ("show notes", "what notes do I have", "find my note")
   - Deleting notes ("delete note", "remove note")
   - Personal reminders and memory aids

4. **chitchat**:
   - Greetings ("hi", "hello", "good morning", "thanks", "goodbye")
   - Small talk, jokes, casual conversation
   - Emotional expressions ("I'm feeling stressed", "need to talk", "how are you")
   - Gratitude and acknowledgments
   - General help requests without specific intent

User message: "{message}"

Respond with ONLY the category name (scheduling/information/notes/chitchat), nothing else."""

def classify_with_prompt(message, prompt_version="v2"):
    """Classify using specified prompt version"""
    prompt = IMPROVED_PROMPT_TEMPLATE.format(message=message)

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

# Test cases - focus on previously misclassified queries
TEST_CASES = [
    {
        'category': 'PREVIOUS MISCLASSIFICATIONS',
        'queries': [
            {
                'text': "I'm feeling a bit stressed, just need to talk",
                'expected': 'chitchat',
                'previous': 'notes',  # Was wrong
                'reason': 'Emotional support request'
            },
            {
                'text': "Add to my shopping list: coffee and bananas",
                'expected': 'notes',
                'previous': 'information',  # Was wrong
                'reason': 'Shopping list management'
            }
        ]
    },
    {
        'category': 'EDGE CASE VALIDATION',
        'queries': [
            {
                'text': "I need someone to talk to",
                'expected': 'chitchat',
                'previous': 'unknown',
                'reason': 'Emotional expression'
            },
            {
                'text': "Create a to-do list for groceries",
                'expected': 'notes',
                'previous': 'unknown',
                'reason': 'List creation'
            },
            {
                'text': "Remember to call the contractor",
                'expected': 'notes',
                'previous': 'unknown',
                'reason': 'Personal reminder'
            },
            {
                'text': "How are you doing today?",
                'expected': 'chitchat',
                'previous': 'unknown',
                'reason': 'Casual greeting'
            }
        ]
    }
]

print("\n" + "="*90)
print("🧪 IMPROVED CLASSIFICATION PROMPT TEST (Version 2.0)")
print("="*90)
print("\nFocusing on previously misclassified queries and edge cases")
print("="*90)

all_results = []

for test_group in TEST_CASES:
    print(f"\n{'='*90}")
    print(f"📋 {test_group['category']}")
    print(f"{'='*90}")

    for query_data in test_group['queries']:
        query = query_data['text']
        expected = query_data['expected']
        previous = query_data['previous']
        reason = query_data['reason']

        # Classify with improved prompt
        result = classify_with_prompt(query, "v2")

        is_correct = result == expected
        is_fixed = previous != 'unknown' and result != previous and is_correct

        status = '✅ CORRECT' if is_correct else '❌ WRONG'
        fix_status = ' (🎉 FIXED!)' if is_fixed else ''

        print(f"\nQuery: {query}")
        print(f"  Expected:  {expected}")
        if previous != 'unknown':
            print(f"  Previous:  {previous}")
        print(f"  Result:    {result} {status}{fix_status}")
        print(f"  Reason:    {reason}")

        all_results.append({
            'query': query,
            'expected': expected,
            'result': result,
            'correct': is_correct,
            'fixed': is_fixed
        })

# Summary
print("\n" + "="*90)
print("📊 TEST SUMMARY")
print("="*90)

total = len(all_results)
correct = sum(1 for r in all_results if r['correct'])
fixed = sum(1 for r in all_results if r['fixed'])

print(f"\nTotal Queries:            {total}")
print(f"Correct Classifications:  {correct}")
print(f"Accuracy:                 {(correct/total)*100:.1f}%")
print(f"Previously Wrong, Now Fixed: {fixed}")

# Show any remaining failures
failures = [r for r in all_results if not r['correct']]
if failures:
    print(f"\n⚠️  REMAINING FAILURES:")
    for f in failures:
        print(f"  - \"{f['query']}\"")
        print(f"    Expected: {f['expected']}, Got: {f['result']}")
else:
    print("\n✅ NO FAILURES - All queries correctly classified!")

print("\n" + "="*90)
print("🎯 VERDICT")
print("="*90)

if correct == total:
    print("🎉 PERFECT! All queries correctly classified.")
    print("✅ The improved prompt (v2.0) successfully fixes previous misclassifications.")
elif correct >= total * 0.9:
    print(f"✅ EXCELLENT: {(correct/total)*100:.1f}% accuracy")
    print("The improved prompt significantly improves classification.")
elif fixed >= 2:
    print(f"✅ IMPROVED: Fixed {fixed} previously misclassified queries")
    print(f"Overall accuracy: {(correct/total)*100:.1f}%")
else:
    print(f"⚠️  NEEDS MORE WORK: Only {(correct/total)*100:.1f}% accuracy")

print("\n" + "="*90)
print()
