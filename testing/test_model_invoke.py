#!/usr/bin/env python3
"""Test direct model invocation"""
import boto3
import json

session = boto3.Session(profile_name='pf-aws', region_name='us-east-1')
client = session.client('bedrock-runtime')

model_id = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

print(f"Testing model invocation: {model_id}")

try:
    response = client.invoke_model(
        modelId=model_id,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{"role": "user", "content": "Say hello"}],
            "max_tokens": 100
        })
    )

    result = json.loads(response['body'].read())
    print(f"✅ Model invocation SUCCESS!")
    print(f"Response: {result['content'][0]['text']}")

except Exception as e:
    print(f"❌ ERROR: {e}")
