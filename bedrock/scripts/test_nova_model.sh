#!/bin/bash

# Test Amazon Nova Model
# Usage: ./test_nova_model.sh "Your prompt here"

PROMPT="${1:-Hello, how are you?}"
MODEL_ID="amazon.nova-micro-v1:0"
REGION="us-east-1"

echo "Testing Amazon Nova model..."
echo "Prompt: $PROMPT"
echo ""

python3 << EOFPYTHON
import boto3
import json
import sys

client = boto3.client('bedrock-runtime', region_name='$REGION')

body = {
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "text": "$PROMPT"
                }
            ]
        }
    ],
    "inferenceConfig": {
        "maxTokens": 500,
        "temperature": 0.7
    }
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
    if 'output' in response_body and 'message' in response_body['output']:
        content = response_body['output']['message']['content']
        for item in content:
            if 'text' in item:
                print("Response:")
                print("─" * 80)
                print(item['text'])
                print("─" * 80)
    
    # Print usage statistics
    if 'usage' in response_body:
        usage = response_body['usage']
        print(f"\nTokens: Input={usage.get('inputTokens', 0)}, Output={usage.get('outputTokens', 0)}, Total={usage.get('totalTokens', 0)}")
    
except Exception as e:
    print(f"❌ Error: {type(e).__name__}")
    print(f"Message: {str(e)}")
    sys.exit(1)

EOFPYTHON
