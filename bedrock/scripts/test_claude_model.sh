#!/bin/bash

# Test Anthropic Claude Model
# Usage: ./test_claude_model.sh "Your prompt here" [model_id]

PROMPT="${1:-Hello, how are you?}"
MODEL_ID="${2:-anthropic.claude-3-haiku-20240307-v1:0}"
REGION="us-east-1"

echo "Testing Claude model..."
echo "Model: $MODEL_ID"
echo "Prompt: $PROMPT"
echo ""

python3 << EOFPYTHON
import boto3
import json
import sys

client = boto3.client('bedrock-runtime', region_name='$REGION')

body = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 500,
    "temperature": 0.7,
    "messages": [
        {
            "role": "user",
            "content": "$PROMPT"
        }
    ]
}

try:
    response = client.invoke_model(
        modelId='$MODEL_ID',
        body=json.dumps(body)
    )
    
    response_body = json.loads(response['body'].read())
    
    print("✅ Success!")
    print("")
    
    # Extract and print the response text
    if 'content' in response_body:
        for item in response_body['content']:
            if 'text' in item:
                print("Response:")
                print("─" * 80)
                print(item['text'])
                print("─" * 80)
    
    # Print usage statistics
    if 'usage' in response_body:
        usage = response_body['usage']
        print(f"\nTokens: Input={usage.get('input_tokens', 0)}, Output={usage.get('output_tokens', 0)}")
    
except Exception as e:
    print(f"❌ Error: {type(e).__name__}")
    print(f"Message: {str(e)}")
    sys.exit(1)

EOFPYTHON
