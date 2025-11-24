#!/usr/bin/env python3
"""
Test SchedulingAgent directly (bypassing Supervisor)
This should return JSON formatted responses
"""

import boto3
import json
import uuid

# Agent IDs from AWS
SCHEDULING_AGENT_ID = "SOILTYW7SI"
SCHEDULING_ALIAS_ID = "GIMRYJ3NCI"  # v1 alias
REGION = "us-east-1"

# Initialize Bedrock client
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=REGION)

# Test message
test_message = "show me my projects"

# Session attributes (customer context) - Real credentials
session_attributes = {
    "customer_id": "1646085",
    "client_id": "09PF05VD",
    "bearer_token": "TaDWx6r5O0WE2tb5/Lb77XuI29UR7j2NlMHbUdXd+YrYPR7ZdTrczgYigcaRHxvF4PUl7KCfKcSa/5LTVI9GZGD2xjCQuIIGifYzjbeIG4F9hljoQfRSa4yHgXV4iKYuqyrGhSMR2SSZtZYnMIprKV5SeEOzLetV5rSRAmv7Gaql+7WMxg9YyXONFcV7MJHDvSyDXZFIDx0aAvhffakC3AN86giYM7H6QGlwo7OqqkfH88MV+MyJTJqMzWJXx7lI5xPuAc0lLtoRftNZ2PQN8Q4APfRkyfsVbm0IkMidTHw4CtIbnDF7rnLdOYO4amUcvntMnR8iAFikdkbGodCW5OZQzMhQxWZIizfX4mkYqNw9jGxOfbFGMonzQZwFgrFfn2F3Zys3lNQR2TlYo78wiYlMAWafKsVYWChjCpCrFuKGIb6pNfW8s38eqDAG2ApYEVxGpEPLUxQpPR7m88ofRS9zL2e3QABL83MVSl487zpM8Epq9if0WJFQ+3KccrHKtkfIwrn3A/IGw8nYmSIXx9kLXwpdYsyRz6hUXkuaqMLnJ9hJctt4TLiMohyrqqcjXhGQoOKKu0eYH+f/mPWkf6hV9rdiKWhLwpCK0j44eDeHgoarYxZZcJGd9KK+2G6pnlvgi6sP8sZcuJTMc4kCiaFFLlXZDJppdXjIBlj9ItscnV2RRIP/I6CLrRsBmkgQpSiw88wW/XihrEVZKXTG2lRKGoZlVLreA0C1NBUbKs8="
}

# Generate session ID
session_id = f"test-direct-{uuid.uuid4().hex[:8]}"

print("=" * 70)
print("Testing SchedulingAgent Directly (Bypassing Supervisor)")
print("=" * 70)
print(f"Agent ID: {SCHEDULING_AGENT_ID}")
print(f"Alias ID: {SCHEDULING_ALIAS_ID}")
print(f"Session ID: {session_id}")
print(f"Message: {test_message}")
print("=" * 70)
print()

try:
    # Invoke agent directly
    response = bedrock_agent_runtime.invoke_agent(
        agentId=SCHEDULING_AGENT_ID,
        agentAliasId=SCHEDULING_ALIAS_ID,
        sessionId=session_id,
        inputText=test_message,
        sessionState={
            'sessionAttributes': session_attributes
        }
    )

    # Process streaming response
    full_response = ""
    event_stream = response['completion']

    for event in event_stream:
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                chunk_text = chunk['bytes'].decode('utf-8')
                full_response += chunk_text
                print(chunk_text, end='', flush=True)

    print("\n")
    print("=" * 70)
    print("Full Response:")
    print("=" * 70)
    print(full_response)
    print()

    # Check for JSON blocks
    if "```json" in full_response:
        print("✅ JSON code block detected!")
        print("The response contains structured JSON data.")
    else:
        print("⚠️  No JSON code block found.")
        print("The response is plain text.")

    print()
    print("=" * 70)
    print("Response Analysis:")
    print("=" * 70)

    # Try to extract and parse JSON
    if "```json" in full_response:
        import re
        json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', full_response)
        if json_match:
            try:
                json_data = json.loads(json_match.group(1))
                print("✅ Successfully parsed JSON:")
                print(json.dumps(json_data, indent=2))
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error: {e}")

except Exception as e:
    print(f"❌ Error invoking agent: {e}")
    import traceback
    traceback.print_exc()
