#!/usr/bin/env python3
"""
Comprehensive Routing Test Suite
Tests all agent types with various query patterns
"""

import boto3
import json
import uuid
from datetime import datetime
from typing import List, Dict

# Configuration
REGION = "us-east-1"

AGENTS = {
    'scheduling': {'agent_id': 'TIGRBGSXCS', 'alias_id': 'PNDF9AQVHW', 'name': 'Scheduling Agent'},
    'information': {'agent_id': 'JEK4SDJOOU', 'alias_id': 'LF61ZU9X2T', 'name': 'Information Agent'},
    'notes': {'agent_id': 'CF0IPHCFFY', 'alias_id': 'YOBOR0JJM7', 'name': 'Notes Agent'},
    'chitchat': {'agent_id': 'GXVZEOBQ64', 'alias_id': 'RSSE65OYGM', 'name': 'Chitchat Agent'}
}

# Initialize clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=REGION)
bedrock_runtime = boto3.client('bedrock-runtime', region_name=REGION)

CUSTOMER_CONTEXT = {
    'customer_id': '1645975',
    'client_id': '09PF05VD',
    'customer_type': 'B2C'
}

# Test queries organized by expected intent
TEST_QUERIES = {
    "Chitchat Agent": [
        "Hey, how's it going?",
        "What do you think about the weather today?",
        "I'm feeling a bit stressed, just need to talk",
        "Tell me a joke!",
        "Good morning! Ready for the weekend?"
    ],
    "Scheduling Agent": [
        "Can you schedule a meeting with Sarah for next Tuesday at 2pm?",
        "What's on my calendar for tomorrow?",
        "I need to reschedule my 3pm appointment to Thursday",
        "Block out 2 hours next week for project planning",
        "Find a time slot for a team sync this week",
        "Cancel my meeting on Friday afternoon"
    ],
    "Information Agent": [
        "What's the current weather in Seattle?",
        "Who won the NBA championship last year?",
        "Look up the population of Tokyo",
        "What are the symptoms of vitamin D deficiency?",
        "Find me information about renewable energy trends",
        "What's the exchange rate for USD to EUR?"
    ],
    "Notes Agent": [
        "Save a note: Remember to buy groceries - milk, eggs, bread",
        "Create a note about ideas for the quarterly presentation",
        "Show me all my notes from last week",
        "Find my note about the client meeting",
        "Delete the note about vacation planning",
        "Add to my shopping list: coffee and bananas"
    ],
    "Ambiguous/Edge Cases": [
        "Remind me about the meeting",
        "What time is it in London?",
        "I need help with something",
        "Thanks for your help earlier!"
    ]
}


def classify_intent(message: str) -> str:
    """Classify intent using Claude Haiku"""
    prompt = f"""You are an intent classifier for a property management scheduling system.

Given a user message, classify it into ONE of these categories:

1. **scheduling**: Listing projects, booking appointments, checking availability, dates/times, calendar operations
2. **information**: Project details, appointment status, working hours, weather, general knowledge queries
3. **notes**: Adding, viewing, deleting, or managing notes
4. **chitchat**: Greetings, small talk, general questions, emotional support

User message: "{message}"

Respond with ONLY the category name (scheduling/information/notes/chitchat), nothing else."""

    try:
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 10,
                "temperature": 0.0,
                "messages": [{"role": "user", "content": prompt}]
            })
        )

        response_body = json.loads(response['body'].read())
        intent = response_body['content'][0]['text'].strip().lower()

        valid_intents = ['scheduling', 'information', 'notes', 'chitchat']
        if intent not in valid_intents:
            intent = 'chitchat'

        return intent

    except Exception as e:
        print(f"Classification error: {e}")
        return 'chitchat'


def invoke_agent(intent: str, message: str) -> Dict:
    """Invoke appropriate agent based on intent"""
    agent_config = AGENTS.get(intent, AGENTS['chitchat'])

    augmented_prompt = f"""Session Context:
- Customer ID: {CUSTOMER_CONTEXT['customer_id']}
- Client ID: {CUSTOMER_CONTEXT['client_id']}
- Customer Type: {CUSTOMER_CONTEXT['customer_type']}

User Request: {message}

Please help the customer with their request."""

    session_id = str(uuid.uuid4())

    try:
        response = bedrock_agent_runtime.invoke_agent(
            agentId=agent_config['agent_id'],
            agentAliasId=agent_config['alias_id'],
            sessionId=session_id,
            inputText=augmented_prompt,
            sessionState={'sessionAttributes': CUSTOMER_CONTEXT}
        )

        full_response = ""
        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    full_response += chunk['bytes'].decode('utf-8')

        # Truncate for display
        display_response = full_response[:150] + "..." if len(full_response) > 150 else full_response

        return {
            'success': True,
            'response': display_response,
            'full_response': full_response,
            'agent': agent_config['name']
        }

    except Exception as e:
        return {
            'success': False,
            'response': f"ERROR: {str(e)[:100]}",
            'agent': agent_config['name']
        }


def test_query(category: str, query: str, index: int) -> Dict:
    """Test a single query"""
    print(f"  [{index}] Testing: {query[:50]}...")

    # Classify
    intent = classify_intent(query)

    # Route
    result = invoke_agent(intent, query)

    return {
        'category': category,
        'query': query,
        'classified_as': intent,
        'routed_to': result['agent'],
        'status': '✅' if result['success'] else '❌',
        'response': result['response']
    }


def main():
    """Run comprehensive test suite"""
    print("\n" + "="*100)
    print("🧪 COMPREHENSIVE ROUTING TEST SUITE")
    print("="*100)
    print(f"Region: {REGION}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Queries: {sum(len(queries) for queries in TEST_QUERIES.values())}")
    print("="*100)

    all_results = []

    for category, queries in TEST_QUERIES.items():
        print(f"\n{'='*100}")
        print(f"📋 Testing: {category}")
        print(f"{'='*100}")
        print(f"Queries: {len(queries)}")

        for idx, query in enumerate(queries, 1):
            result = test_query(category, query, idx)
            all_results.append(result)
            print(f"  {result['status']} {result['classified_as']:12} → {result['routed_to']}")

    # Generate summary tables
    print("\n\n" + "="*100)
    print("📊 COMPREHENSIVE TEST RESULTS")
    print("="*100)

    # Table 1: Overview by Category
    print("\n" + "="*100)
    print("TABLE 1: RESULTS BY EXPECTED CATEGORY")
    print("="*100)
    print(f"{'Category':<25} {'Queries':<10} {'Success':<10} {'Success Rate':<15}")
    print("-"*100)

    for category in TEST_QUERIES.keys():
        category_results = [r for r in all_results if r['category'] == category]
        total = len(category_results)
        successful = sum(1 for r in category_results if r['status'] == '✅')
        rate = f"{(successful/total)*100:.0f}%" if total > 0 else "N/A"
        print(f"{category:<25} {total:<10} {successful:<10} {rate:<15}")

    # Table 2: Detailed Results
    print("\n" + "="*100)
    print("TABLE 2: DETAILED QUERY RESULTS")
    print("="*100)
    print(f"{'#':<4} {'Query':<50} {'Intent':<12} {'Routed To':<20} {'Status':<8}")
    print("-"*100)

    for idx, result in enumerate(all_results, 1):
        query_short = result['query'][:47] + "..." if len(result['query']) > 50 else result['query']
        print(f"{idx:<4} {query_short:<50} {result['classified_as']:<12} {result['routed_to']:<20} {result['status']:<8}")

    # Table 3: Intent Classification Accuracy
    print("\n" + "="*100)
    print("TABLE 3: INTENT CLASSIFICATION ACCURACY")
    print("="*100)

    intent_map = {
        "Chitchat Agent": "chitchat",
        "Scheduling Agent": "scheduling",
        "Information Agent": "information",
        "Notes Agent": "notes"
    }

    print(f"{'Expected Category':<25} {'Correct':<10} {'Incorrect':<10} {'Accuracy':<15}")
    print("-"*100)

    for category, expected_intent in intent_map.items():
        category_results = [r for r in all_results if r['category'] == category]
        correct = sum(1 for r in category_results if r['classified_as'] == expected_intent)
        total = len(category_results)
        incorrect = total - correct
        accuracy = f"{(correct/total)*100:.0f}%" if total > 0 else "N/A"
        print(f"{category:<25} {correct:<10} {incorrect:<10} {accuracy:<15}")

    # Edge cases separate
    edge_results = [r for r in all_results if r['category'] == "Ambiguous/Edge Cases"]
    if edge_results:
        print(f"{'Ambiguous/Edge Cases':<25} {'N/A':<10} {'N/A':<10} {'(varies)':<15}")

    # Table 4: Sample Responses
    print("\n" + "="*100)
    print("TABLE 4: SAMPLE AGENT RESPONSES (First 3 from each category)")
    print("="*100)

    for category in TEST_QUERIES.keys():
        print(f"\n🔹 {category}:")
        print("-"*100)
        category_results = [r for r in all_results if r['category'] == category][:3]

        for result in category_results:
            print(f"\nQuery: {result['query']}")
            print(f"Intent: {result['classified_as']} → Agent: {result['routed_to']}")
            print(f"Response: {result['response']}")
            print()

    # Summary Statistics
    print("\n" + "="*100)
    print("📈 SUMMARY STATISTICS")
    print("="*100)

    total_queries = len(all_results)
    successful = sum(1 for r in all_results if r['status'] == '✅')
    failed = total_queries - successful

    print(f"\nTotal Queries Tested:     {total_queries}")
    print(f"Successful Invocations:   {successful} ({(successful/total_queries)*100:.1f}%)")
    print(f"Failed Invocations:       {failed} ({(failed/total_queries)*100:.1f}%)")

    # Intent distribution
    intent_counts = {}
    for result in all_results:
        intent = result['classified_as']
        intent_counts[intent] = intent_counts.get(intent, 0) + 1

    print(f"\nIntent Distribution:")
    for intent, count in sorted(intent_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count/total_queries)*100
        print(f"  {intent.capitalize():<15} {count:>3} queries ({percentage:>5.1f}%)")

    # Agent utilization
    agent_counts = {}
    for result in all_results:
        agent = result['routed_to']
        agent_counts[agent] = agent_counts.get(agent, 0) + 1

    print(f"\nAgent Utilization:")
    for agent, count in sorted(agent_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count/total_queries)*100
        print(f"  {agent:<20} {count:>3} queries ({percentage:>5.1f}%)")

    # Final verdict
    print("\n" + "="*100)
    print("✅ FINAL VERDICT")
    print("="*100)

    if successful == total_queries:
        print("🎉 ALL TESTS PASSED! Frontend routing is working perfectly.")
    elif successful >= total_queries * 0.9:
        print(f"✅ EXCELLENT! {(successful/total_queries)*100:.1f}% success rate.")
    elif successful >= total_queries * 0.75:
        print(f"⚠️  GOOD: {(successful/total_queries)*100:.1f}% success rate, but some failures.")
    else:
        print(f"❌ ISSUES DETECTED: Only {(successful/total_queries)*100:.1f}% success rate.")

    print("\n" + "="*100)


if __name__ == "__main__":
    main()
