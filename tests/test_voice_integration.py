"""
Test Suite for Phase 3: Voice Integration
Tests AWS Connect, Lex, and Voice Lambda functions
"""

import boto3
import json
import time
from typing import Dict, Any, Optional

# AWS clients
lex_runtime = boto3.client('lexv2-runtime')
lambda_client = boto3.client('lambda')

# Configuration (update these with your actual values)
REGION = 'us-east-1'
PREFIX = 'pf'
ENVIRONMENT = 'dev'

LEX_BOT_ID = None  # Will be fetched dynamically
LEX_BOT_ALIAS_ID = None
LEX_LOCALE_ID = 'en_US'

TEST_SESSION_ID = f'test-session-{int(time.time())}'
TEST_CUSTOMER_ID = 'C001'


def get_lex_bot_info():
    """Get Lex bot ID and alias from AWS"""
    global LEX_BOT_ID, LEX_BOT_ALIAS_ID

    lex_models = boto3.client('lexv2-models', region_name=REGION)

    # Get bot ID
    bots = lex_models.list_bots()
    for bot in bots['botSummaries']:
        if f'{PREFIX}-scheduling-assistant-{ENVIRONMENT}' in bot['botName']:
            LEX_BOT_ID = bot['botId']
            break

    if not LEX_BOT_ID:
        print("❌ Lex bot not found. Please deploy voice infrastructure first.")
        return False

    # Get alias ID
    aliases = lex_models.list_bot_aliases(botId=LEX_BOT_ID)
    for alias in aliases['botAliasSummaries']:
        if alias['botAliasName'] == 'prod':
            LEX_BOT_ALIAS_ID = alias['botAliasId']
            break

    if not LEX_BOT_ALIAS_ID:
        print("❌ Lex bot alias 'prod' not found.")
        return False

    print(f"✅ Found Lex bot: {LEX_BOT_ID}")
    print(f"✅ Found alias: {LEX_BOT_ALIAS_ID}")
    return True


def test_lex_bot_direct(text: str, session_id: str) -> Dict[str, Any]:
    """Test Lex bot directly (without Connect)"""
    try:
        response = lex_runtime.recognize_text(
            botId=LEX_BOT_ID,
            botAliasId=LEX_BOT_ALIAS_ID,
            localeId=LEX_LOCALE_ID,
            sessionId=session_id,
            text=text,
            sessionState={
                'sessionAttributes': {
                    'customer_id': TEST_CUSTOMER_ID,
                    'channel': 'test'
                }
            }
        )

        return {
            'success': True,
            'intent': response.get('sessionState', {}).get('intent', {}).get('name'),
            'messages': [msg.get('content', '') for msg in response.get('messages', [])],
            'session_state': response.get('sessionState', {})
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def test_lex_fulfillment_lambda(event: Dict[str, Any]) -> Dict[str, Any]:
    """Test lex-fulfillment Lambda function"""
    try:
        response = lambda_client.invoke(
            FunctionName=f'{PREFIX}-lex-fulfillment-{ENVIRONMENT}',
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )

        result = json.loads(response['Payload'].read())
        return {
            'success': True,
            'result': result
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def test_voice_bedrock_bridge(input_text: str, session_id: str) -> Dict[str, Any]:
    """Test voice-bedrock-bridge Lambda function"""
    try:
        response = lambda_client.invoke(
            FunctionName=f'{PREFIX}-voice-bedrock-bridge-{ENVIRONMENT}',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'session_id': session_id,
                'customer_id': TEST_CUSTOMER_ID,
                'input_text': input_text,
                'channel': 'test'
            })
        )

        result = json.loads(response['Payload'].read())
        return {
            'success': True,
            'result': result
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def run_tests():
    """Run all voice integration tests"""

    print("\n" + "="*60)
    print("Phase 3: Voice Integration Test Suite")
    print("="*60 + "\n")

    # Test 1: Get Lex bot info
    print("TEST 1: Verify Lex Bot Deployment")
    print("-" * 60)
    if not get_lex_bot_info():
        print("\n❌ Cannot proceed without Lex bot. Exiting.\n")
        return
    print("✅ Test 1 PASSED\n")

    # Test 2: Test Lex bot with simple query
    print("TEST 2: Lex Bot - Simple Project Inquiry")
    print("-" * 60)
    result = test_lex_bot_direct("show me my projects", TEST_SESSION_ID)
    if result['success']:
        print(f"✅ Intent recognized: {result['intent']}")
        print(f"   Response: {result['messages'][0] if result['messages'] else 'No response'}")
        print("✅ Test 2 PASSED\n")
    else:
        print(f"❌ Test 2 FAILED: {result['error']}\n")

    # Test 3: Test Lex bot with urgent request
    print("TEST 3: Lex Bot - Urgent Scheduling Request")
    print("-" * 60)
    result = test_lex_bot_direct("schedule my most urgent project", TEST_SESSION_ID)
    if result['success']:
        print(f"✅ Intent recognized: {result['intent']}")
        print(f"   Response: {result['messages'][0] if result['messages'] else 'No response'}")
        print("✅ Test 3 PASSED\n")
    else:
        print(f"❌ Test 3 FAILED: {result['error']}\n")

    # Test 4: Test lex-fulfillment Lambda
    print("TEST 4: Lex Fulfillment Lambda")
    print("-" * 60)
    lex_event = {
        'sessionId': TEST_SESSION_ID,
        'sessionState': {
            'intent': {
                'name': 'Welcome',
                'state': 'Fulfilled'
            },
            'sessionAttributes': {
                'customer_id': TEST_CUSTOMER_ID
            }
        },
        'inputTranscript': 'hello'
    }
    result = test_lex_fulfillment_lambda(lex_event)
    if result['success']:
        print("✅ Lambda invoked successfully")
        print(f"   Response: {result['result']}")
        print("✅ Test 4 PASSED\n")
    else:
        print(f"❌ Test 4 FAILED: {result['error']}\n")

    # Test 5: Test voice-bedrock-bridge Lambda
    print("TEST 5: Voice-Bedrock Bridge Lambda")
    print("-" * 60)
    result = test_voice_bedrock_bridge("What projects do I have?", f"test-bridge-{int(time.time())}")
    if result['success']:
        print("✅ Lambda invoked successfully")
        response_text = result['result'].get('response', 'No response')
        print(f"   Bedrock response: {response_text[:200]}...")
        print("✅ Test 5 PASSED\n")
    else:
        print(f"❌ Test 5 FAILED: {result['error']}\n")

    # Test 6: Test conversation flow
    print("TEST 6: Multi-Turn Conversation")
    print("-" * 60)
    conv_session = f"conv-test-{int(time.time())}"

    # Turn 1
    result1 = test_lex_bot_direct("hello", conv_session)
    print(f"Turn 1 - User: 'hello'")
    print(f"Turn 1 - Bot: {result1['messages'][0] if result1.get('messages') else 'No response'}")

    time.sleep(1)

    # Turn 2
    result2 = test_lex_bot_direct("show me my projects", conv_session)
    print(f"Turn 2 - User: 'show me my projects'")
    print(f"Turn 2 - Bot: {result2['messages'][0] if result2.get('messages') else 'No response'}")

    if result1['success'] and result2['success']:
        print("✅ Test 6 PASSED\n")
    else:
        print("❌ Test 6 FAILED\n")

    # Summary
    print("="*60)
    print("Test Suite Complete")
    print("="*60)
    print("\nNext Steps:")
    print("1. Test voice calls by dialing your AWS Connect phone number")
    print("2. Monitor CloudWatch Logs for detailed execution traces")
    print("3. Review call recordings in S3")
    print("\nManual Testing Commands:")
    print(f"  aws lexv2-runtime recognize-text --bot-id {LEX_BOT_ID} \\")
    print(f"    --bot-alias-id {LEX_BOT_ALIAS_ID} --locale-id {LEX_LOCALE_ID} \\")
    print(f"    --session-id test-123 --text 'show me my projects'")
    print("")


if __name__ == "__main__":
    run_tests()
