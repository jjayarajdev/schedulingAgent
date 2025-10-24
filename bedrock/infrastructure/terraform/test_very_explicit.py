#!/usr/bin/env python3
"""
Test supervisor with very explicit scheduling request
"""

import boto3
import uuid

AGENT_ID = "WF1S95L7X1"
AGENT_ALIAS_ID = "TSTALIASID"
REGION = "us-east-1"

client = boto3.client('bedrock-agent-runtime', region_name=REGION)

# Very explicit request that should route to Scheduling Agent
test_phrase = "I want to schedule a new appointment. My customer ID is 1645975 and client ID is 09PF05VD. Please show me my available projects so I can pick a date and time."

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
    elif 'trace' in event:
        trace = event['trace']['trace']
        if 'orchestrationTrace' in trace:
            orch = trace['orchestrationTrace']
            if 'invocationInput' in orch:
                print(f"\n\n[TRACE] Invocation Type: {orch['invocationInput'].get('invocationType', 'N/A')}")
            if 'modelInvocationOutput' in orch:
                print(f"[TRACE] Routing decision made")

print("\n" + "-" * 80)
