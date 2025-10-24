#!/usr/bin/env python3
"""
Production Test Suite for Bedrock Multi-Agent System

This script demonstrates the correct way to use the agents with customer context
from a logged-in session.

Usage:
    python3 test_production.py
"""

import boto3
import json
import time
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================================
# CONFIGURATION
# ============================================================================

def load_agent_config():
    """Load agent configuration from agent_config.json"""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'agent_config.json'
    )

    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    else:
        # Fallback to current IDs
        return {
            'supervisor_id': 'V3BW0KFBMX',
            'supervisor_alias': 'K6BWBY1RNY',
            'region': 'us-east-1'
        }

CONFIG = load_agent_config()
SUPERVISOR_ID = CONFIG['supervisor_id']
SUPERVISOR_ALIAS = CONFIG['supervisor_alias']
REGION = CONFIG.get('region', 'us-east-1')

# ============================================================================
# PRODUCTION INVOCATION PATTERN
# ============================================================================

def invoke_agent_with_customer_context(user_message, customer_id, customer_type='B2C'):
    """
    Production-ready agent invocation with customer context.

    This is how you would invoke the agent in your application after user login.

    Args:
        user_message: The user's actual question/request
        customer_id: From your login session (e.g., "CUST001")
        customer_type: B2C or B2B from your user profile

    Returns:
        tuple: (full_response, success)
    """
    client = boto3.client('bedrock-agent-runtime', region_name=REGION)

    # Generate unique session ID
    session_id = f"session-{customer_id}-{int(time.time())}"

    # CRITICAL: Inject customer context into the prompt
    # This is the pattern that makes everything work
    augmented_prompt = f"""Session Context:
- Customer ID: {customer_id}
- Customer Type: {customer_type}

User Request: {user_message}

Please help the customer with their request using their customer ID for any actions."""

    try:
        response = client.invoke_agent(
            agentId=SUPERVISOR_ID,
            agentAliasId=SUPERVISOR_ALIAS,
            sessionId=session_id,
            inputText=augmented_prompt,
            sessionState={
                'sessionAttributes': {
                    'customer_id': customer_id,
                    'customer_type': customer_type
                }
            }
        )

        # Collect response
        full_response = ""
        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    full_response += chunk['bytes'].decode('utf-8')

        return full_response, True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return str(e), False

# ============================================================================
# TEST SCENARIOS
# ============================================================================

TEST_SCENARIOS = [
    {
        'name': 'List Projects',
        'category': 'Scheduling',
        'query': 'Show me all my projects',
        'expected_data': ['12345', '12347', '12350', 'Flooring', 'Windows', 'Deck'],
        'avoid_data': ['Kitchen', 'Bathroom', 'Garage']
    },
    {
        'name': 'Get Project Details',
        'category': 'Information',
        'query': 'Tell me about project 12345',
        'expected_data': ['12345', 'Flooring', 'Tampa'],
        'avoid_data': ['Kitchen', 'Bathroom']
    },
    {
        'name': 'Check Availability',
        'category': 'Scheduling',
        'query': 'What dates are available for project 12347?',
        'expected_data': ['2025', 'available'],
        'avoid_data': []
    },
    {
        'name': 'Business Hours',
        'category': 'Information',
        'query': 'What are your business hours?',
        'expected_data': ['Monday', 'Friday'],
        'avoid_data': []
    },
    {
        'name': 'Appointment Status',
        'category': 'Information',
        'query': 'What is the status of appointment 12345?',
        'expected_data': ['12345'],
        'avoid_data': []
    }
]

# ============================================================================
# TEST EXECUTION
# ============================================================================

def verify_response(response, expected_data, avoid_data):
    """Verify response contains expected data and no hallucinations"""
    found_expected = []
    found_avoided = []

    for expected in expected_data:
        if expected in response:
            found_expected.append(expected)

    for avoid in avoid_data:
        if avoid in response:
            found_avoided.append(avoid)

    success = len(found_expected) == len(expected_data) and len(found_avoided) == 0

    return success, found_expected, found_avoided

def run_test(test, customer_id='CUST001', customer_type='B2C'):
    """Run a single test scenario"""
    print(f"\n{'='*80}")
    print(f"Test: {test['name']}")
    print(f"Category: {test['category']}")
    print(f"{'='*80}")
    print(f"User: {test['query']}")
    print(f"Customer: {customer_id} ({customer_type})")
    print(f"{'─'*80}")

    # Invoke agent
    response, success = invoke_agent_with_customer_context(
        test['query'],
        customer_id,
        customer_type
    )

    if not success:
        print(f"❌ FAILED - Agent invocation error")
        return False

    # Show response preview
    print(f"Agent Response:")
    preview = response[:300] + "..." if len(response) > 300 else response
    print(preview)
    print()

    # Verify
    success, found_expected, found_avoided = verify_response(
        response,
        test['expected_data'],
        test['avoid_data']
    )

    if success:
        print(f"✅ PASSED - All expected data found, no hallucinations")
        return True
    else:
        missing = [e for e in test['expected_data'] if e not in found_expected]
        if missing:
            print(f"⚠️  Missing expected data: {', '.join(missing)}")
        if found_avoided:
            print(f"❌ Found hallucinated data: {', '.join(found_avoided)}")
        print(f"❌ FAILED")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("PRODUCTION TEST SUITE")
    print("="*80)
    print(f"\nSupervisor Agent: {SUPERVISOR_ID}")
    print(f"Alias: {SUPERVISOR_ALIAS}")
    print(f"Region: {REGION}")
    print(f"\nSimulating user CUST001 logged in with session context")
    print(f"Total Tests: {len(TEST_SCENARIOS)}")
    print("="*80)

    passed = 0
    failed = 0
    results = []

    for test in TEST_SCENARIOS:
        result = run_test(test)
        results.append({
            'name': test['name'],
            'category': test['category'],
            'passed': result
        })

        if result:
            passed += 1
        else:
            failed += 1

        # Brief pause between tests
        time.sleep(2)

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"\nTotal Tests: {len(TEST_SCENARIOS)}")
    print(f"Passed: ✅ {passed}")
    print(f"Failed: ❌ {failed}")
    print(f"Success Rate: {(passed/len(TEST_SCENARIOS)*100):.1f}%")

    # By category
    print("\nBy Category:")
    categories = {}
    for result in results:
        cat = result['category']
        if cat not in categories:
            categories[cat] = {'passed': 0, 'total': 0}
        categories[cat]['total'] += 1
        if result['passed']:
            categories[cat]['passed'] += 1

    for cat, stats in categories.items():
        print(f"  {cat}: {stats['passed']}/{stats['total']}")

    # Detailed results
    print("\n" + "="*80)
    print("DETAILED RESULTS")
    print("="*80)
    for result in results:
        status = "✅ PASSED" if result['passed'] else "❌ FAILED"
        print(f"{status} - {result['name']}")

    print("\n" + "="*80)
    print("CloudWatch Verification")
    print("="*80)
    print("\nTo verify Lambda functions were called, check CloudWatch logs:")
    print("\nScheduling Actions:")
    print("  aws logs tail /aws/lambda/scheduling-agent-scheduling-actions \\")
    print("    --follow --region us-east-1")
    print("\nInformation Actions:")
    print("  aws logs tail /aws/lambda/scheduling-agent-information-actions \\")
    print("    --follow --region us-east-1")
    print("\nNotes Actions:")
    print("  aws logs tail /aws/lambda/scheduling-agent-notes-actions \\")
    print("    --follow --region us-east-1")

    print("\n" + "="*80)

    if passed == len(TEST_SCENARIOS):
        print("✅ ALL TESTS PASSED! System is working correctly.")
        print("="*80 + "\n")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED - Review results above")
        print("="*80 + "\n")
        return 1

if __name__ == '__main__':
    exit(main())
