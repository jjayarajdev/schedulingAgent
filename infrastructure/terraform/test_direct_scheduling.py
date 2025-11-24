#!/usr/bin/env python3
"""
Test direct invocation of Scheduling Agent (bypassing supervisor)
"""

import boto3
import json
import uuid

# Configuration
AGENT_ID = "TIGRBGSXCS"  # Scheduling agent directly
AGENT_ALIAS_ID = "TSTALIASID"
REGION = "us-east-1"

client = boto3.client('bedrock-agent-runtime', region_name=REGION)

print("="*80)
print("DIRECT SCHEDULING AGENT TEST")
print("="*80)
print(f"Agent ID: {AGENT_ID}")
print(f"Alias ID: {AGENT_ALIAS_ID}")
print("="*80)

session_id = str(uuid.uuid4())

response = client.invoke_agent(
    agentId=AGENT_ID,
    agentAliasId=AGENT_ALIAS_ID,
    sessionId=session_id,
    inputText="Show me my projects",
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
print("✅ Test completed")
