#!/usr/bin/env python3
"""
Test supervisor routing with explicit scheduling request
"""

import boto3
import uuid

AGENT_ID = "WF1S95L7X1"  # Supervisor
AGENT_ALIAS_ID = "TSTALIASID"
REGION = "us-east-1"

client = boto3.client('bedrock-agent-runtime', region_name=REGION)

# Use the EXACT phrasing from supervisor's example routing decisions
test_phrase = "I want to schedule an appointment"

print("="*80)
print(f"Testing: '{test_phrase}'")
print("="*80)

session_id = str(uuid.uuid4())

response = client.invoke_agent(
    agentId=AGENT_ID,
    agentAliasId=AGENT_ALIAS_ID,
    sessionId=session_id,
    inputText=test_phrase,
    sessionState={
        'sessionAttributes': {
            "customer_id": "1645975",
            "client_id": "09PF05VD"
        }
    }
)

print("\n📥 RESPONSE:")
print("-" * 80)

for event in response['completion']:
    if 'chunk' in event:
        chunk = event['chunk']
        if 'bytes' in chunk:
            print(chunk['bytes'].decode('utf-8'), end='', flush=True)

print("\n" + "-" * 80)
