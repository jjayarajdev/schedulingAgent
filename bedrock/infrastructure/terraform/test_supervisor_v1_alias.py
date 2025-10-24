#!/usr/bin/env python3
"""
Test Supervisor Agent Routing using v1 alias instead of TSTALIASID
This test checks if using a versioned alias fixes the execution issue
"""

import boto3
import json
import uuid
from datetime import datetime

# Configuration - Using v1 alias instead of TSTALIASID
AGENT_ID = "WF1S95L7X1"  # Supervisor agent
AGENT_ALIAS_ID = "2VOPSV9O88"  # v1 alias (instead of TSTALIASID)
REGION = "us-east-1"

# Initialize Bedrock Agent Runtime client
client = boto3.client('bedrock-agent-runtime', region_name=REGION)

# Test data
SESSION_ATTRIBUTES = {
    "customer_id": "1645975",
    "client_id": "09PF05VD"
}

def test_with_v1_alias(test_name: str, input_text: str, expected_behavior: str):
    """Test supervisor with v1 alias"""
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"{'='*80}")
    print(f"📝 Input: {input_text}")
    print(f"🎯 Expected: {expected_behavior}")
    print(f"🏷️  Using Alias: v1 ({AGENT_ALIAS_ID})")
    print(f"👤 Session Attributes: {json.dumps(SESSION_ATTRIBUTES, indent=2)}")
    print(f"\n🚀 Invoking supervisor agent...")
    print("-" * 80)

    session_id = str(uuid.uuid4())

    try:
        response = client.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=input_text,
            sessionState={
                'sessionAttributes': SESSION_ATTRIBUTES
            }
        )

        print("\n📥 AGENT RESPONSE:")
        print("-" * 80)

        full_response = ""
        has_function_calls_text = False

        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    chunk_text = chunk['bytes'].decode('utf-8')
                    full_response += chunk_text
                    print(chunk_text, end='', flush=True)

                    # Check if response contains function call XML (bad sign)
                    if '<function_calls>' in chunk_text or '<invoke>' in chunk_text:
                        has_function_calls_text = True

        print("\n" + "-" * 80)

        # Analysis
        print("\n📊 ANALYSIS:")
        print(f"Response length: {len(full_response)} characters")

        if has_function_calls_text:
            print("⚠️  WARNING: Function calls appear as TEXT (not executed)")
            print("   This indicates routing is still not executing collaborators")
            result_status = "❌ FAILED - Execution not working"
        else:
            print("✅ No function call XML in response")
            print("   Either routing worked OR agent handled it directly")
            result_status = "✅ PASSED - Clean response"

        print(f"\n{result_status}")

        return {
            "success": not has_function_calls_text,
            "response": full_response,
            "has_function_calls_text": has_function_calls_text
        }

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

def main():
    """Run v1 alias routing tests"""
    print("\n" + "="*80)
    print("🤖 SUPERVISOR V1 ALIAS ROUTING TEST")
    print("="*80)
    print(f"Agent ID: {AGENT_ID}")
    print(f"Alias ID: {AGENT_ALIAS_ID} (v1 - NOT TSTALIASID)")
    print(f"Region: {REGION}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print("\n🔬 Testing if v1 alias fixes the execution issue...")

    results = []

    # Test 1: Simple greeting (should work with either alias)
    result = test_with_v1_alias(
        test_name="Chitchat Test - Greeting",
        input_text="Hello! How are you?",
        expected_behavior="Friendly greeting response"
    )
    results.append(("Chitchat", result))

    print("\n\n" + "🔹"*40)
    input("Press Enter to continue to next test...")

    # Test 2: Scheduling request (the critical test)
    result = test_with_v1_alias(
        test_name="Scheduling Test - Book Appointment",
        input_text="I want to schedule an appointment for next Monday",
        expected_behavior="Should invoke list_projects action (NOT show XML)"
    )
    results.append(("Scheduling", result))

    print("\n\n" + "🔹"*40)
    input("Press Enter to continue to next test...")

    # Test 3: Information request
    result = test_with_v1_alias(
        test_name="Information Test - Business Hours",
        input_text="What are your business hours?",
        expected_behavior="Should route to Information Agent"
    )
    results.append(("Information", result))

    # Summary
    print("\n\n" + "="*80)
    print("📊 V1 ALIAS TEST SUMMARY")
    print("="*80)

    successful = sum(1 for _, r in results if r.get('success'))
    total = len(results)

    print(f"\nTotal Tests: {total}")
    print(f"Clean Responses: {successful}")
    print(f"Function Call XML Found: {total - successful}")

    print("\n" + "="*80)
    print("COMPARISON ANALYSIS:")
    print("="*80)
    print("\n🔍 Key Question: Did using v1 alias fix the execution issue?")

    if successful == total:
        print("\n✅ YES! All tests showed clean execution")
        print("   The v1 alias resolved the routing execution problem!")
    elif successful > 0:
        print(f"\n⚠️  PARTIAL: {successful}/{total} tests passed")
        print("   Some improvement, but not fully resolved")
    else:
        print("\n❌ NO: All tests still show function call XML in responses")
        print("   The v1 alias did not fix the execution issue")
        print("   This suggests a deeper platform limitation")

    print("\n" + "="*80)
    print("RECOMMENDATION:")
    print("="*80)
    if successful == total:
        print("✅ Use v1 alias (2VOPSV9O88) instead of TSTALIASID for production")
        print("✅ Update frontend/backend to use v1 alias")
    else:
        print("⚠️  Continue using frontend routing (bypass supervisor)")
        print("⚠️  AWS multi-agent collaboration may have platform limitations")

    print("\n" + "="*80)

if __name__ == "__main__":
    main()
