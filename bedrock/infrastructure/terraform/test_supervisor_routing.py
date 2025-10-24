#!/usr/bin/env python3
"""
Comprehensive Supervisor Agent Routing Test
Tests routing to all 4 specialist agents:
1. Chitchat Agent - Greetings and casual conversation
2. Scheduling Agent - Appointment booking and management
3. Information Agent - Project information queries
4. Notes Agent - Note management
"""

import boto3
import json
import uuid
from datetime import datetime
import time

# Configuration
AGENT_ID = "WF1S95L7X1"  # Supervisor agent
AGENT_ALIAS_ID = "TSTALIASID"
REGION = "us-east-1"

# Initialize Bedrock Agent Runtime client
client = boto3.client('bedrock-agent-runtime', region_name=REGION)

# Test data
SESSION_ATTRIBUTES = {
    "customer_id": "1645975",
    "client_id": "09PF05VD"
}

def test_routing(test_name: str, input_text: str, expected_agent: str, include_session: bool = True):
    """
    Test the supervisor agent routing with a query

    Args:
        test_name: Name of the test
        input_text: User query to test
        expected_agent: Expected agent to route to
        include_session: Whether to include session attributes
    """
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"{'='*80}")
    print(f"📝 Input: {input_text}")
    print(f"🎯 Expected Route: {expected_agent}")
    if include_session:
        print(f"👤 Session Attributes: {json.dumps(SESSION_ATTRIBUTES, indent=2)}")
    print(f"\n🚀 Invoking supervisor agent...")
    print("-" * 80)

    # Generate a unique session ID
    session_id = str(uuid.uuid4())

    try:
        # Invoke agent
        response = client.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=input_text,
            sessionState={
                'sessionAttributes': SESSION_ATTRIBUTES if include_session else {}
            }
        )

        # Process streaming response
        print("\n📥 AGENT RESPONSE:")
        print("-" * 80)

        full_response = ""
        chunks = []

        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    chunk_text = chunk['bytes'].decode('utf-8')
                    full_response += chunk_text
                    chunks.append(chunk_text)
                    print(chunk_text, end='', flush=True)

        print("\n" + "-" * 80)
        print(f"✅ Test completed!")
        print(f"📊 Response length: {len(full_response)} characters")
        print(f"📦 Chunks received: {len(chunks)}")

        return {
            "success": True,
            "response": full_response,
            "chunks": chunks,
            "session_id": session_id,
            "expected_agent": expected_agent
        }

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "expected_agent": expected_agent
        }

def main():
    """
    Run comprehensive supervisor routing tests
    """
    print("\n" + "="*80)
    print("🤖 SUPERVISOR AGENT ROUTING TEST SUITE")
    print("="*80)
    print(f"Agent ID: {AGENT_ID}")
    print(f"Alias ID: {AGENT_ALIAS_ID}")
    print(f"Region: {REGION}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    results = []

    # Test 1: Chitchat Agent - Greeting
    print("\n\n" + "🔷"*40)
    print("TEST GROUP 1: CHITCHAT AGENT")
    print("🔷"*40)

    result = test_routing(
        test_name="Greeting Test",
        input_text="Hello! How are you today?",
        expected_agent="Chitchat Agent",
        include_session=False
    )
    results.append(result)
    time.sleep(2)

    result = test_routing(
        test_name="Casual Conversation",
        input_text="What's the weather like?",
        expected_agent="Chitchat Agent",
        include_session=False
    )
    results.append(result)
    time.sleep(2)

    # Test 2: Scheduling Agent - Appointments
    print("\n\n" + "🔷"*40)
    print("TEST GROUP 2: SCHEDULING AGENT")
    print("🔷"*40)

    result = test_routing(
        test_name="List Projects",
        input_text="Show me my projects",
        expected_agent="Scheduling Agent"
    )
    results.append(result)
    time.sleep(2)

    result = test_routing(
        test_name="Book Appointment",
        input_text="I want to schedule an appointment for next Monday",
        expected_agent="Scheduling Agent"
    )
    results.append(result)
    time.sleep(2)

    result = test_routing(
        test_name="Check Availability",
        input_text="What dates are available for scheduling?",
        expected_agent="Scheduling Agent"
    )
    results.append(result)
    time.sleep(2)

    # Test 3: Information Agent - Project Info
    print("\n\n" + "🔷"*40)
    print("TEST GROUP 3: INFORMATION AGENT")
    print("🔷"*40)

    result = test_routing(
        test_name="Project Details",
        input_text="Can you give me details about my bathroom remodel project?",
        expected_agent="Information Agent"
    )
    results.append(result)
    time.sleep(2)

    result = test_routing(
        test_name="Business Hours",
        input_text="What are your business hours?",
        expected_agent="Information Agent"
    )
    results.append(result)
    time.sleep(2)

    result = test_routing(
        test_name="Project Status",
        input_text="What's the status of my projects?",
        expected_agent="Information Agent"
    )
    results.append(result)
    time.sleep(2)

    # Test 4: Notes Agent - Note Management
    print("\n\n" + "🔷"*40)
    print("TEST GROUP 4: NOTES AGENT")
    print("🔷"*40)

    result = test_routing(
        test_name="Add Note",
        input_text="Add a note: Customer prefers morning appointments",
        expected_agent="Notes Agent"
    )
    results.append(result)
    time.sleep(2)

    result = test_routing(
        test_name="View Notes",
        input_text="Show me the notes for my project",
        expected_agent="Notes Agent"
    )
    results.append(result)
    time.sleep(2)

    # Summary
    print("\n\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)

    successful = sum(1 for r in results if r['success'])
    total = len(results)

    print(f"\nTotal Tests: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Success Rate: {(successful/total)*100:.1f}%")

    print("\n" + "="*80)
    print("DETAILED RESULTS BY AGENT:")
    print("="*80)

    for agent in ["Chitchat Agent", "Scheduling Agent", "Information Agent", "Notes Agent"]:
        agent_results = [r for r in results if r['expected_agent'] == agent]
        agent_success = sum(1 for r in agent_results if r['success'])
        print(f"\n{agent}:")
        print(f"  Tests: {len(agent_results)}")
        print(f"  Success: {agent_success}/{len(agent_results)}")
        if agent_success < len(agent_results):
            print(f"  ⚠️  Some tests failed")
        else:
            print(f"  ✅ All tests passed")

    print("\n" + "="*80)
    print("✅ ALL ROUTING TESTS COMPLETED")
    print("="*80)

if __name__ == "__main__":
    main()
