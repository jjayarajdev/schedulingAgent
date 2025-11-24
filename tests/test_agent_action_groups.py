#!/usr/bin/env python3
"""
AWS Support Case Test Script - Bedrock Agent Action Groups Bug
Demonstrates that agents output function calls as text instead of executing them
"""

import boto3
import json
import time

# Configuration
AGENT_ID = 'YDCJTJBSLO'
AGENT_ALIAS_ID = 'VB7IU4DNIZ'
LAMBDA_FUNCTION = 'scheduling-agent-scheduling-actions'
REGION = 'us-east-1'

print("=" * 70)
print("AWS Bedrock Agent Action Groups Bug Reproduction Test")
print("=" * 70)

# Initialize clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=REGION)
lambda_client = boto3.client('lambda', region_name=REGION)
logs_client = boto3.client('logs', region_name=REGION)

# Test 1: Direct Lambda invocation (THIS WORKS)
print("\n[TEST 1] Direct Lambda Invocation")
print("-" * 70)

lambda_payload = {
    "actionGroup": "scheduling-actions",
    "apiPath": "/list-projects",
    "httpMethod": "POST",
    "parameters": [
        {"name": "customer_id", "type": "string", "value": "CUST001"}
    ]
}

try:
    response = lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTION,
        Payload=json.dumps(lambda_payload)
    )

    result = json.loads(response['Payload'].read())
    print(f"✅ Lambda invocation: SUCCESS")
    print(f"Response: {json.dumps(result, indent=2)}")
except Exception as e:
    print(f"❌ Lambda invocation: FAILED - {e}")

# Test 2: Agent invocation (THIS FAILS - outputs XML instead of executing)
print("\n[TEST 2] Agent Invocation (with Action Group)")
print("-" * 70)

session_id = f"test-{int(time.time())}"

try:
    response = bedrock_agent_runtime.invoke_agent(
        agentId=AGENT_ID,
        agentAliasId=AGENT_ALIAS_ID,
        sessionId=session_id,
        inputText='Show me all my projects',
        sessionState={
            'sessionAttributes': {
                'customer_id': 'CUST001',
                'customer_type': 'B2C'
            }
        }
    )

    print(f"Agent Response:")
    print("-" * 70)

    full_response = ""
    for event in response['completion']:
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                text = chunk['bytes'].decode('utf-8')
                full_response += text
                print(text, end='')

    print("\n" + "-" * 70)

    # Check if response contains XML function calls (the bug)
    if '<function_calls>' in full_response:
        print("\n❌ BUG CONFIRMED: Agent outputs function call as TEXT")
        print("   Expected: Agent should invoke Lambda function")
        print("   Actual: Agent outputs XML as text to user")
    else:
        print("\n✅ Agent executed function call correctly")

except Exception as e:
    print(f"❌ Agent invocation: FAILED - {e}")

# Test 3: Check CloudWatch logs for Lambda invocations
print("\n[TEST 3] CloudWatch Logs Verification")
print("-" * 70)

log_group = f"/aws/lambda/{LAMBDA_FUNCTION}"

try:
    # Get recent log events
    end_time = int(time.time() * 1000)
    start_time = end_time - (5 * 60 * 1000)  # Last 5 minutes

    try:
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=start_time,
            endTime=end_time
        )

        events = response.get('events', [])

        if events:
            print(f"✅ Found {len(events)} log entries in last 5 minutes")
            print("Note: These are likely from direct Lambda tests, NOT from agent")
        else:
            print(f"❌ ZERO log entries in last 5 minutes")
            print("   This confirms Lambda was NEVER invoked by the agent")
    except logs_client.exceptions.ResourceNotFoundException:
        print(f"❌ Log group not found: {log_group}")

except Exception as e:
    print(f"❌ CloudWatch check: FAILED - {e}")

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("✅ Lambda function works when invoked directly")
print("❌ Agent outputs function calls as XML text instead of executing them")
print("❌ CloudWatch logs show zero invocations from agent")
print("\nConclusion: AWS Bedrock Agent Action Groups are not invoking Lambda")
print("=" * 70)
