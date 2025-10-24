#!/usr/bin/env python3
"""
Test script for Bedrock Multi-Agent Collaboration
Tests the supervisor agent routing to various collaborators
"""

import boto3
import json
import sys
import uuid

def invoke_agent(agent_id, agent_alias_id, session_id, input_text, region='us-east-1'):
    """
    Invoke a Bedrock agent and stream the response

    Args:
        agent_id: The agent ID
        agent_alias_id: The agent alias ID
        session_id: Unique session identifier
        input_text: The user's input text
        region: AWS region (default: us-east-1)
    """
    client = boto3.client('bedrock-agent-runtime', region_name=region)

    print(f"\n{'='*80}")
    print(f"Session ID: {session_id}")
    print(f"User Input: {input_text}")
    print(f"{'='*80}\n")

    try:
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=input_text
        )

        # Process the streaming response
        event_stream = response['completion']
        full_response = ""

        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    chunk_text = chunk['bytes'].decode('utf-8')
                    full_response += chunk_text
                    print(chunk_text, end='', flush=True)

        print(f"\n\n{'='*80}")
        print(f"Response complete")
        print(f"{'='*80}\n")

        return full_response

    except Exception as e:
        print(f"\nError invoking agent: {e}")
        return None


def main():
    """Main test function"""

    # Agent configuration
    AGENT_ID = "5VTIWONUMO"  # Supervisor agent ID
    AGENT_ALIAS_ID = "PEXPJRXIML"  # Supervisor agent alias
    REGION = "us-east-1"

    # Test scenarios
    test_scenarios = [
        {
            "name": "Test 1: Chitchat (Greeting)",
            "input": "Hello! How are you?",
            "expected": "Should route to chitchat_collaborator"
        },
        {
            "name": "Test 2: Scheduling Request",
            "input": "I want to schedule an appointment",
            "expected": "Should route to scheduling_collaborator"
        },
        {
            "name": "Test 3: Information Query",
            "input": "What are your working hours?",
            "expected": "Should route to information_collaborator"
        },
        {
            "name": "Test 4: Notes Request",
            "input": "Can you add a note that I prefer morning appointments?",
            "expected": "Should route to notes_collaborator"
        }
    ]

    print("\n" + "="*80)
    print("BEDROCK MULTI-AGENT COLLABORATION TEST")
    print("="*80)
    print(f"\nSupervisor Agent ID: {AGENT_ID}")
    print(f"Agent Alias ID: {AGENT_ALIAS_ID}")
    print(f"Region: {REGION}")
    print(f"\nTesting {len(test_scenarios)} scenarios...\n")

    # Run tests
    for i, scenario in enumerate(test_scenarios, 1):
        session_id = str(uuid.uuid4())  # New session for each test

        print(f"\n{'#'*80}")
        print(f"# {scenario['name']}")
        print(f"# Expected: {scenario['expected']}")
        print(f"{'#'*80}")

        response = invoke_agent(
            agent_id=AGENT_ID,
            agent_alias_id=AGENT_ALIAS_ID,
            session_id=session_id,
            input_text=scenario['input'],
            region=REGION
        )

        if response is None:
            print(f"❌ Test {i} failed - No response received")
        else:
            print(f"✅ Test {i} completed")

        # Small delay between tests
        if i < len(test_scenarios):
            import time
            time.sleep(2)

    print(f"\n{'='*80}")
    print("ALL TESTS COMPLETED")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
