#!/usr/bin/env python3
"""
Test script to verify Bedrock API access for agents
Run this after enabling on-demand access in AWS Console
"""

import boto3
import json
import uuid

def test_model_direct_invoke():
    """Test direct model invocation (this already works)"""
    print("\n" + "="*70)
    print("TEST 1: Direct Model Invocation")
    print("="*70)

    client = boto3.client('bedrock-runtime', region_name='us-east-1')

    try:
        response = client.invoke_model(
            modelId='us.anthropic.claude-sonnet-4-5-20250929-v1:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 50,
                'messages': [{
                    'role': 'user',
                    'content': 'Say "Hello from direct invocation!"'
                }]
            })
        )

        result = json.loads(response['body'].read())
        print(f"✅ SUCCESS")
        print(f"Response: {result['content'][0]['text']}")
        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_agent_invoke():
    """Test agent invocation (this is what's currently failing)"""
    print("\n" + "="*70)
    print("TEST 2: Agent Invocation (Chitchat Agent)")
    print("="*70)

    client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

    try:
        response = client.invoke_agent(
            agentId='BIUW1ARHGL',
            agentAliasId='TSTALIASID',
            sessionId=str(uuid.uuid4()),
            inputText='Hello!'
        )

        print("Agent Response:")
        event_stream = response['completion']
        full_response = ""

        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    text = chunk['bytes'].decode('utf-8')
                    full_response += text
                    print(text, end='', flush=True)

        print()
        print(f"\n✅ SUCCESS - Agent invocation works!")
        return True

    except Exception as e:
        error_msg = str(e)
        print(f"❌ FAILED: {error_msg}")

        if 'accessDeniedException' in error_msg or '403' in error_msg:
            print("\n⚠️  ACCESS DENIED ERROR")
            print("This means on-demand API access is NOT yet enabled.")
            print("\nNext steps:")
            print("1. Go to AWS Console Model Access page")
            print("2. Enable 'On-demand' access for Claude Sonnet 4.5")
            print("3. Wait 5-10 minutes")
            print("4. Run this script again")

        return False

def test_supervisor_agent():
    """Test supervisor agent invocation"""
    print("\n" + "="*70)
    print("TEST 3: Supervisor Agent Invocation")
    print("="*70)

    client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

    try:
        response = client.invoke_agent(
            agentId='5VTIWONUMO',
            agentAliasId='HH2U7EZXMW',  # Latest alias
            sessionId=str(uuid.uuid4()),
            inputText='Hello! How are you?'
        )

        print("Supervisor Response:")
        event_stream = response['completion']
        full_response = ""

        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    text = chunk['bytes'].decode('utf-8')
                    full_response += text
                    print(text, end='', flush=True)

        print()
        print(f"\n✅ SUCCESS - Supervisor agent works!")
        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def main():
    print("\n" + "="*70)
    print("BEDROCK API ACCESS TEST")
    print("="*70)
    print("\nThis script tests 3 things:")
    print("1. Direct model invocation (should work)")
    print("2. Collaborator agent invocation (currently fails)")
    print("3. Supervisor agent invocation (currently fails)")
    print("\nRunning tests...")

    results = []

    # Test 1: Direct model invocation
    results.append(("Direct Model", test_model_direct_invoke()))

    # Test 2: Agent invocation
    results.append(("Agent", test_agent_invoke()))

    # Test 3: Supervisor agent
    results.append(("Supervisor", test_supervisor_agent()))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}  {name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("Your agents are ready to use via API!")
    else:
        print("\n⚠️  Some tests failed.")
        print("\nIf Agent tests failed:")
        print("→ Enable 'On-demand' access in AWS Console")
        print("→ See: bedrock/ENABLE_API_ACCESS.md")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
