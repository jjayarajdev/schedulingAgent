"""
Direct Bedrock Agent Invocation Test
Tests if we can invoke Bedrock agents with current credentials
"""
import boto3
import json
import sys

# Initialize Bedrock client
bedrock_client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

# Test with Supervisor agent
agent_id = 'SQRXPIXRFY'
agent_alias_id = 'TSTALIASID'
session_id = 'test-direct-session-123'
input_text = 'I need help scheduling an appointment'

print(f"Testing Bedrock agent invocation...")
print(f"Agent ID: {agent_id}")
print(f"Alias ID: {agent_alias_id}")
print(f"Input: {input_text}\n")

try:
    response = bedrock_client.invoke_agent(
        agentId=agent_id,
        agentAliasId=agent_alias_id,
        sessionId=session_id,
        inputText=input_text,
        sessionState={
            'sessionAttributes': {
                'customer_id': '1646085',
                'client_id': '09PF05VD'
            }
        }
    )

    print("SUCCESS! Agent invocation worked!")
    print("\nResponse stream:")

    # Process event stream
    event_stream = response['completion']
    full_response = []

    for event in event_stream:
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                text = chunk['bytes'].decode('utf-8')
                full_response.append(text)
                print(text, end='', flush=True)

    print(f"\n\nFull response: {''.join(full_response)}")

except Exception as e:
    print(f"ERROR: {str(e)}")
    print(f"Error type: {type(e).__name__}")
    sys.exit(1)
