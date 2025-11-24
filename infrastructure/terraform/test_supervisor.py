#!/usr/bin/env python3
"""
Test script for Supervisor Agent with Collaborators
Tests routing to specialist agents
"""

import boto3
import json
import uuid
from datetime import datetime

# Configuration
AGENT_ID = "WF1S95L7X1"  # Supervisor agent
AGENT_ALIAS_ID = "TSTALIASID"
REGION = "us-east-1"

# Initialize Bedrock Agent Runtime client
client = boto3.client('bedrock-agent-runtime', region_name=REGION)

def test_supervisor_agent(test_name: str, input_text: str, session_attributes: dict = None):
    """
    Test the supervisor agent with a query
    """
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"{'='*80}")
    print(f"Input: {input_text}")
    print(f"\nSession Attributes: {json.dumps(session_attributes, indent=2)}")
    print(f"\nInvoking supervisor agent {AGENT_ID} (alias: {AGENT_ALIAS_ID})...")
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
                'sessionAttributes': session_attributes or {}
            }
        )

        # Process streaming response
        print("\n📥 RESPONSE:")
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
        print(f"\n✅ Test completed successfully!")
        print(f"Response length: {len(full_response)} characters")
        print(f"Number of chunks: {len(chunks)}")

        return {
            "success": True,
            "response": full_response,
            "chunks": chunks,
            "session_id": session_id
        }

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

def main():
    """
    Run supervisor agent tests
    """
    print("\n" + "="*80)
    print("SUPERVISOR AGENT TESTING")
    print("="*80)
    print(f"Agent ID: {AGENT_ID}")
    print(f"Alias ID: {AGENT_ALIAS_ID}")
    print(f"Region: {REGION}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    # Test 1: Simple greeting (should route to Chitchat agent)
    test_supervisor_agent(
        test_name="Greeting Test (Chitchat Agent)",
        input_text="Hello! How are you today?"
    )

    print("\n\n" + "="*80)
    print("Continuing to next test...")
    print("="*80)

    # Test 2: Scheduling query (should route to Scheduling agent)
    test_supervisor_agent(
        test_name="Scheduling Test (Scheduling Agent)",
        input_text="Show me my projects",
        session_attributes={
            "customer_id": "1645975",
            "client_id": "09PF05VD"
        }
    )

    print("\n\n" + "="*80)
    print("ALL TESTS COMPLETED")
    print("="*80)

if __name__ == "__main__":
    main()
