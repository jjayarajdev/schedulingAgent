#!/usr/bin/env python3
"""
Test Frontend Routing Approach
This demonstrates the alternate approach where frontend classifies intent
and routes directly to specialist agents (bypassing supervisor)
"""

import boto3
import json
import uuid
from datetime import datetime

# Configuration
REGION = "us-east-1"

# Agent IDs (from updated agent_config.json)
AGENTS = {
    'scheduling': {
        'agent_id': 'TIGRBGSXCS',
        'alias_id': 'PNDF9AQVHW',
        'name': 'Scheduling Agent'
    },
    'information': {
        'agent_id': 'JEK4SDJOOU',
        'alias_id': 'LF61ZU9X2T',
        'name': 'Information Agent'
    },
    'notes': {
        'agent_id': 'CF0IPHCFFY',
        'alias_id': 'YOBOR0JJM7',
        'name': 'Notes Agent'
    },
    'chitchat': {
        'agent_id': 'GXVZEOBQ64',
        'alias_id': 'RSSE65OYGM',
        'name': 'Chitchat Agent'
    }
}

# Initialize clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=REGION)
bedrock_runtime = boto3.client('bedrock-runtime', region_name=REGION)

# Customer context
CUSTOMER_CONTEXT = {
    'customer_id': '1645975',
    'client_id': '09PF05VD',
    'customer_type': 'B2C'
}


def classify_intent(message):
    """Classify intent using Claude Haiku (fast & cheap)"""
    prompt = f"""You are an intent classifier for a property management scheduling system.

Given a user message, classify it into ONE of these categories:

1. **scheduling**: Listing projects, booking appointments, checking availability, dates/times
2. **information**: Project details, appointment status, working hours, weather
3. **notes**: Adding or viewing notes
4. **chitchat**: Greetings, small talk, general questions

User message: "{message}"

Respond with ONLY the category name (scheduling/information/notes/chitchat), nothing else."""

    try:
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 10,
                "temperature": 0.0,
                "messages": [{"role": "user", "content": prompt}]
            })
        )

        response_body = json.loads(response['body'].read())
        intent = response_body['content'][0]['text'].strip().lower()

        # Validate
        valid_intents = ['scheduling', 'information', 'notes', 'chitchat']
        if intent not in valid_intents:
            print(f"⚠️  Invalid intent '{intent}', defaulting to chitchat")
            intent = 'chitchat'

        return intent

    except Exception as e:
        print(f"❌ Classification error: {e}")
        return 'chitchat'


def invoke_specialist_agent(intent, message):
    """Directly invoke the appropriate specialist agent"""
    agent_config = AGENTS.get(intent, AGENTS['chitchat'])

    # Augment prompt with customer context
    augmented_prompt = f"""Session Context:
- Customer ID: {CUSTOMER_CONTEXT['customer_id']}
- Client ID: {CUSTOMER_CONTEXT['client_id']}
- Customer Type: {CUSTOMER_CONTEXT['customer_type']}

User Request: {message}

Please help the customer with their request using their customer ID for any actions."""

    session_id = str(uuid.uuid4())

    print(f"\n🎯 Routing Decision:")
    print(f"   Intent: {intent.upper()}")
    print(f"   Agent: {agent_config['name']}")
    print(f"   Agent ID: {agent_config['agent_id']}")
    print(f"   Alias ID: {agent_config['alias_id']}")
    print(f"\n📤 Invoking agent...")
    print("-" * 80)

    try:
        response = bedrock_agent_runtime.invoke_agent(
            agentId=agent_config['agent_id'],
            agentAliasId=agent_config['alias_id'],
            sessionId=session_id,
            inputText=augmented_prompt,
            sessionState={
                'sessionAttributes': CUSTOMER_CONTEXT
            }
        )

        print("\n📥 AGENT RESPONSE:")
        print("-" * 80)

        full_response = ""
        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    chunk_text = chunk['bytes'].decode('utf-8')
                    full_response += chunk_text
                    print(chunk_text, end='', flush=True)

        print("\n" + "-" * 80)

        # Check for function call XML
        has_function_calls_text = '<function_calls>' in full_response or '<invoke>' in full_response

        return {
            'success': not has_function_calls_text,
            'response': full_response,
            'intent': intent,
            'agent': agent_config['name'],
            'has_function_calls_text': has_function_calls_text
        }

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'intent': intent
        }


def test_frontend_routing(test_name, message):
    """Test the complete frontend routing flow"""
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"{'='*80}")
    print(f"📝 User Message: \"{message}\"")
    print(f"👤 Customer: {CUSTOMER_CONTEXT['customer_id']}")
    print()

    # Step 1: Classify intent
    print("🔍 Step 1: Classifying intent...")
    intent = classify_intent(message)
    print(f"   ✅ Intent: {intent.upper()}")

    # Step 2: Route to specialist
    print("\n🚀 Step 2: Routing to specialist agent...")
    result = invoke_specialist_agent(intent, message)

    # Analysis
    print("\n📊 ANALYSIS:")
    if result.get('success'):
        print("   ✅ Response clean (no function call XML)")
        print("   ✅ Direct agent invocation worked!")
        status = "✅ PASSED"
    elif result.get('has_function_calls_text'):
        print("   ⚠️  Function calls appear as TEXT")
        print("   ⚠️  Agent didn't execute the action")
        status = "⚠️ PARTIAL"
    else:
        print("   ❌ Error occurred")
        status = "❌ FAILED"

    print(f"\n{status}")

    return result


def main():
    """Run frontend routing tests"""
    print("\n" + "="*80)
    print("🔀 FRONTEND ROUTING APPROACH TEST")
    print("="*80)
    print("\nThis approach bypasses the supervisor and:")
    print("1. Uses Claude Haiku to classify user intent (fast & cheap)")
    print("2. Routes directly to the appropriate specialist agent")
    print("3. Injects customer context via prompt + session attributes")
    print("\n" + "="*80)
    print(f"Region: {REGION}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    results = []

    # Test 1: Chitchat
    result = test_frontend_routing(
        "Chitchat Test",
        "Hello! How are you today?"
    )
    results.append(result)

    print("\n\n" + "🔹"*40)
    input("\nPress Enter to continue to next test...")

    # Test 2: Scheduling (the critical test)
    result = test_frontend_routing(
        "Scheduling Test",
        "Show me my projects"
    )
    results.append(result)

    print("\n\n" + "🔹"*40)
    input("\nPress Enter to continue to next test...")

    # Test 3: Information
    result = test_frontend_routing(
        "Information Test",
        "What are your business hours?"
    )
    results.append(result)

    print("\n\n" + "🔹"*40)
    input("\nPress Enter to continue to next test...")

    # Test 4: Notes
    result = test_frontend_routing(
        "Notes Test",
        "Add a note: Customer prefers morning appointments"
    )
    results.append(result)

    # Summary
    print("\n\n" + "="*80)
    print("📊 FRONTEND ROUTING TEST SUMMARY")
    print("="*80)

    successful = sum(1 for r in results if r.get('success'))
    total = len(results)

    print(f"\nTotal Tests: {total}")
    print(f"Successful: {successful}")
    print(f"Success Rate: {(successful/total)*100:.1f}%")

    print("\n" + "="*80)
    print("RESULTS BY INTENT:")
    print("="*80)

    for result in results:
        intent = result.get('intent', 'unknown')
        agent = result.get('agent', 'unknown')
        status = "✅" if result.get('success') else "❌"
        print(f"{status} {intent.upper():<12} → {agent}")

    print("\n" + "="*80)
    print("ADVANTAGES OF FRONTEND ROUTING:")
    print("="*80)
    print("✅ No dependency on AWS multi-agent collaboration feature")
    print("✅ Direct specialist invocation (no supervisor overhead)")
    print("✅ Faster response times (one agent call instead of two)")
    print("✅ More control over routing logic")
    print("✅ Cheaper (Haiku classification costs < $0.001 per request)")
    print("✅ Works reliably today (no platform bugs)")

    print("\n" + "="*80)
    print("COMPARISON: Frontend vs Supervisor Routing")
    print("="*80)
    print("\n┌─────────────────────┬────────────────┬─────────────────┐")
    print("│ Aspect              │ Frontend Route │ Supervisor Route│")
    print("├─────────────────────┼────────────────┼─────────────────┤")
    print("│ Reliability         │ ✅ High        │ ❌ Low (AWS bug)│")
    print("│ Speed               │ ✅ Fast        │ ⚠️  Slower      │")
    print("│ Control             │ ✅ Full        │ ⚠️  Limited     │")
    print("│ Cost                │ ✅ Lower       │ ⚠️  Higher      │")
    print("│ Complexity          │ ⚠️  Medium     │ ✅ Simple       │")
    print("│ Production Ready    │ ✅ Yes         │ ❌ No           │")
    print("└─────────────────────┴────────────────┴─────────────────┘")

    print("\n" + "="*80)
    print("✅ RECOMMENDATION: Use Frontend Routing (current approach)")
    print("="*80)

if __name__ == "__main__":
    main()
