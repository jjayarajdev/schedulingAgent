#!/usr/bin/env python3
"""Prepare all agents and test"""

import boto3
import time
import uuid

client = boto3.client('bedrock-agent', region_name='us-east-1')
runtime_client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

agents = {
    'Supervisor': '5VTIWONUMO',
    'Scheduling': 'IX24FSMTQH',
    'Information': 'C9ANXRIO8Y',
    'Notes': 'G5BVBYEPUM',
    'Chitchat': 'BIUW1ARHGL'
}

print("Preparing all agents...")
print("="*60)

for name, agent_id in agents.items():
    try:
        response = client.prepare_agent(agentId=agent_id)
        status = response['agentStatus']
        print(f"✓ {name:12} ({agent_id}): {status}")
    except Exception as e:
        print(f"✗ {name:12} ({agent_id}): {e}")

print("\nWaiting 30 seconds for preparation...")
time.sleep(30)

print("\nTesting agent invocation...")
print("="*60)

try:
    response = runtime_client.invoke_agent(
        agentId='5VTIWONUMO',
        agentAliasId='PEXPJRXIML',
        sessionId=str(uuid.uuid4()),
        inputText='Hello!'
    )

    print("✅ Agent invoked!")
    print("\nResponse:")
    print("-"*60)

    event_stream = response['completion']
    for event in event_stream:
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                print(chunk['bytes'].decode('utf-8'), end='', flush=True)

    print()
    print("-"*60)
    print("\n🎉 SUCCESS!\n")

except Exception as e:
    print(f"❌ FAILED: {e}\n")
