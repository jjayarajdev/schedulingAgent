#!/usr/bin/env python3
"""
Direct Lambda test with mock sessionAttributes
Tests if Lambda can process token and call real API
"""
import json
import sys
import os

# Add lambda directory to path
sys.path.insert(0, 'lambda/scheduling-actions')

# Set environment variables for REAL API mode
os.environ['USE_MOCK_API'] = 'false'
os.environ['ENVIRONMENT'] = 'dev'

# Import the lambda handler
from handler import lambda_handler

# Create a test event with sessionAttributes
test_event = {
    "messageVersion": "1.0",
    "agent": {
        "name": "SchedulingAgent",
        "id": "TIGRBGSXCS",
        "alias": "TSTALIASID",
        "version": "DRAFT"
    },
    "inputText": "Show me all my projects",
    "sessionId": "test-session-123",
    "actionGroup": "scheduling-actions",
    "apiPath": "/list-projects",
    "httpMethod": "POST",
    "parameters": [],
    "requestBody": {
        "content": {
            "application/json": {
                "properties": []
            }
        }
    },
    "sessionAttributes": {
        "pf_bearer_token": "TEST_TOKEN_PLACEHOLDER",  # Will replace with real token
        "pf_api_base": "https://api.dev.projectsforce.com",
        "customer_id": "6f72bffa-c323-4058-a01c-9d495d696364",
        "client_id": "09PF05VD",
        "customer_type": "B2C"
    }
}

# Try to get real token from command line or use test token
if len(sys.argv) > 1:
    real_token = sys.argv[1]
    test_event["sessionAttributes"]["pf_bearer_token"] = real_token
    print(f"✅ Using provided Bearer token: {real_token[:20]}...")
else:
    print("⚠️  No token provided - using TEST_TOKEN_PLACEHOLDER")
    print("   Usage: python3 test_lambda_direct.py <bearer_token>")

print("\n" + "="*60)
print("Testing Lambda Handler Directly")
print("="*60)
print(f"API Path: {test_event['apiPath']}")
print(f"USE_MOCK_API: {os.environ['USE_MOCK_API']}")
print(f"Session Attributes:")
for key, value in test_event["sessionAttributes"].items():
    if key == "pf_bearer_token":
        print(f"  {key}: {value[:20]}..." if len(value) > 20 else f"  {key}: {value}")
    else:
        print(f"  {key}: {value}")

print("\n" + "-"*60)
print("Invoking Lambda Handler...")
print("-"*60 + "\n")

try:
    response = lambda_handler(test_event, None)

    print("Response:")
    print(json.dumps(response, indent=2))

    # Check if we got real data or mock data
    if response.get('response', {}).get('httpStatusCode') == 200:
        body_str = response['response']['responseBody']['application/json']['body']
        body = json.loads(body_str)

        print("\n" + "="*60)
        if body.get('mock_mode') == False:
            print("✅ SUCCESS: Real API data received!")
            print(f"   Project count: {body.get('project_count', 0)}")
            if body.get('projects'):
                print("\n   Projects:")
                for proj in body['projects'][:3]:  # Show first 3
                    print(f"     - {proj.get('project_type')} at {proj.get('address', 'N/A')}")
        else:
            print("⚠️  WARNING: Still getting MOCK data")
            print(f"   mock_mode: {body.get('mock_mode')}")
    else:
        print(f"\n❌ ERROR: HTTP Status {response.get('response', {}).get('httpStatusCode')}")

except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
