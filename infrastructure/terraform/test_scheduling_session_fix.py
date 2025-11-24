#!/usr/bin/env python3
"""
Test Scheduling Agent Session Attributes Fix
Verifies that the agent now uses session attributes instead of asking for them
"""

import boto3
import json
import uuid

# Configuration
REGION = "us-east-1"
SCHEDULING_AGENT_ID = "TIGRBGSXCS"
ALIAS_ID = "TSTALIASID"

# Test customer
TEST_CUSTOMER = {
    "customer_id": "1645975",
    "client_id": "09PF05VD"
}

client = boto3.client('bedrock-agent-runtime', region_name=REGION)

def invoke_agent(agent_id: str, input_text: str, session_attrs: dict) -> dict:
    """Invoke an agent and return response with traces"""
    session_id = str(uuid.uuid4())

    print(f"\n{'='*80}")
    print(f"INVOKING AGENT")
    print(f"{'='*80}")
    print(f"Agent ID: {agent_id}")
    print(f"Input: {input_text}")
    print(f"Session Attributes: {json.dumps(session_attrs, indent=2)}")
    print(f"{'='*80}\n")

    try:
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=ALIAS_ID,
            sessionId=session_id,
            inputText=input_text,
            enableTrace=True,
            sessionState={
                'sessionAttributes': session_attrs
            }
        )

        full_response = ""
        traces = []
        lambda_invoked = False

        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    full_response += chunk['bytes'].decode('utf-8')
            elif 'trace' in event:
                trace = event['trace']
                traces.append(trace)

                # Check for action group invocation
                trace_data = trace.get('trace', {})
                if 'orchestrationTrace' in trace_data:
                    orch = trace_data['orchestrationTrace']
                    if 'invocationInput' in orch:
                        inv_input = orch['invocationInput']
                        if 'actionGroupInvocationInput' in inv_input:
                            lambda_invoked = True
                            action_group = inv_input['actionGroupInvocationInput']
                            print(f"✅ LAMBDA INVOKED!")
                            print(f"Action Group: {action_group.get('actionGroupName', 'Unknown')}")
                            print(f"API Path: {action_group.get('apiPath', 'Unknown')}")
                            if 'requestBody' in action_group:
                                print(f"Request Body: {json.dumps(action_group['requestBody'], indent=2)}")

        return {
            "success": True,
            "response": full_response,
            "traces": traces,
            "lambda_invoked": lambda_invoked
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "response": "",
            "traces": [],
            "lambda_invoked": False
        }

def check_for_asking_credentials(response_text: str) -> bool:
    """Check if agent is asking for customer_id or client_id"""
    asking_phrases = [
        "customer id",
        "customer identifier",
        "client id",
        "client identifier",
        "i need",
        "could you provide",
        "please provide"
    ]

    response_lower = response_text.lower()
    for phrase in asking_phrases:
        if phrase in response_lower and ("customer" in response_lower or "client" in response_lower):
            return True
    return False

def main():
    print("\n" + "="*80)
    print("TESTING SCHEDULING AGENT SESSION ATTRIBUTES FIX")
    print("="*80)
    print("\nThis test verifies that the agent:")
    print("  1. ✅ Uses session attributes for customer_id and client_id")
    print("  2. ✅ Does NOT ask the user for these values")
    print("  3. ✅ Invokes the list_projects Lambda action")
    print("\n" + "="*80)

    # Test: List Projects
    result = invoke_agent(
        agent_id=SCHEDULING_AGENT_ID,
        input_text="Show me my projects",
        session_attrs=TEST_CUSTOMER
    )

    print("\n" + "="*80)
    print("TEST RESULTS")
    print("="*80)

    if not result['success']:
        print(f"❌ FAIL - Error invoking agent: {result['error']}")
        return

    response = result['response']
    lambda_invoked = result['lambda_invoked']
    asking_for_credentials = check_for_asking_credentials(response)

    print(f"\n📝 Agent Response:")
    print("-" * 80)
    print(response)
    print("-" * 80)

    print(f"\n📊 Analysis:")
    print(f"  Lambda Invoked: {'✅ YES' if lambda_invoked else '❌ NO'}")
    print(f"  Asking for Credentials: {'❌ YES (BAD)' if asking_for_credentials else '✅ NO (GOOD)'}")
    print(f"  Response Length: {len(response)} characters")

    print(f"\n🎯 VERDICT:")
    if lambda_invoked and not asking_for_credentials:
        print("  ✅ ✅ ✅ SUCCESS! Agent is using session attributes correctly!")
        print("  - Lambda was invoked")
        print("  - Agent did not ask for customer_id or client_id")
        return True
    elif not lambda_invoked and not asking_for_credentials:
        print("  ⚠️  PARTIAL - Agent didn't ask for credentials, but Lambda not invoked")
        print("  - This might be a Lambda error, not an agent instruction issue")
        return False
    elif asking_for_credentials:
        print("  ❌ FAIL - Agent is still asking for credentials!")
        print("  - The instruction update did not fix the issue")
        return False
    else:
        print("  ❌ FAIL - Unexpected behavior")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
