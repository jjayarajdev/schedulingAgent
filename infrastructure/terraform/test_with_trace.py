#!/usr/bin/env python3
"""
Test supervisor with trace enabled to see routing decisions
"""

import boto3
import json
import uuid

AGENT_ID = "WF1S95L7X1"
AGENT_ALIAS_ID = "TSTALIASID"
REGION = "us-east-1"

client = boto3.client('bedrock-agent-runtime', region_name=REGION)

print("="*80)
print("SUPERVISOR ROUTING TRACE TEST")
print("="*80)

session_id = str(uuid.uuid4())

response = client.invoke_agent(
    agentId=AGENT_ID,
    agentAliasId=AGENT_ALIAS_ID,
    sessionId=session_id,
    inputText="Show me my projects",
    enableTrace=True,  # Enable trace to see routing decisions
    sessionState={
        'sessionAttributes': {
            "customer_id": "1645975",
            "client_id": "09PF05VD"
        }
    }
)

print("\n📥 PROCESSING EVENTS:")
print("-" * 80)

response_text = ""
collaborator_invocations = []

for event in response['completion']:
    if 'chunk' in event:
        chunk = event['chunk']
        if 'bytes' in chunk:
            text = chunk['bytes'].decode('utf-8')
            response_text += text

    elif 'trace' in event:
        trace = event['trace']['trace']

        # Check for orchestration trace
        if 'orchestrationTrace' in trace:
            orch = trace['orchestrationTrace']

            # Check for collaborator invocation
            if 'invocationInput' in orch:
                inv_input = orch['invocationInput']
                if 'collaboratorInvocationInput' in inv_input:
                    collab = inv_input['collaboratorInvocationInput']
                    print(f"\n🔀 ROUTING TO COLLABORATOR!")
                    print(f"   Collaborator Name: {collab.get('collaboratorName', 'Unknown')}")
                    print(f"   Input: {collab.get('input', {}).get('text', 'N/A')}")
                    collaborator_invocations.append(collab)

            # Check for model invocation
            if 'modelInvocationInput' in orch:
                model_input = orch['modelInvocationInput']
                print(f"\n🤖 MODEL INVOCATION")
                if 'text' in model_input:
                    print(f"   Input text: {model_input['text'][:100]}...")

print("\n" + "-" * 80)
print("\n📥 FINAL RESPONSE:")
print("-" * 80)
print(response_text)
print("-" * 80)

print(f"\n📊 ROUTING SUMMARY:")
print(f"   Collaborator invocations: {len(collaborator_invocations)}")
if collaborator_invocations:
    for i, collab in enumerate(collaborator_invocations, 1):
        print(f"   {i}. {collab.get('collaboratorName', 'Unknown')}")
else:
    print("   ❌ No collaborators invoked - supervisor handled request itself")
