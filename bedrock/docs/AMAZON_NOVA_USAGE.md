# Amazon Nova Model Usage Guide

**Date:** November 4, 2025
**Purpose:** Quick reference for using Amazon Nova models with AWS Bedrock

## Amazon Nova Models

### Available Models
- `amazon.nova-micro-v1:0` - Smallest, fastest, most cost-effective
- `amazon.nova-lite-v1:0` - Balanced performance and cost
- `amazon.nova-pro-v1:0` - Most capable

## Correct Request Format

The key difference from Claude models is that Nova uses a nested content structure:

```json
{
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "text": "Your prompt here"
                }
            ]
        }
    ],
    "inferenceConfig": {
        "maxTokens": 500,
        "temperature": 0.7
    }
}
```

## Python Example (Recommended)

```python
import boto3
import json

client = boto3.client('bedrock-runtime', region_name='us-east-1')

body = {
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "text": "Hello, how are you?"
                }
            ]
        }
    ],
    "inferenceConfig": {
        "maxTokens": 500,
        "temperature": 0.7
    }
}

response = client.invoke_model(
    modelId='amazon.nova-micro-v1:0',
    body=json.dumps(body)
)

response_body = json.loads(response['body'].read())
text = response_body['output']['message']['content'][0]['text']
print(text)
```

## Response Format

```json
{
    "output": {
        "message": {
            "content": [
                {
                    "text": "Response text here"
                }
            ],
            "role": "assistant"
        }
    },
    "stopReason": "end_turn",
    "usage": {
        "inputTokens": 6,
        "outputTokens": 26,
        "totalTokens": 32
    }
}
```

## Common Error

### Malformed Input Request

**Error:**
```
ValidationException: Malformed input request, please reformat your input and try again.
```

**Cause:** Using incorrect format (e.g., Claude format)

**Your Original Command:**
```bash
# This doesn't work for Nova:
aws bedrock-runtime invoke-model \
    --model-id amazon.nova-micro-v1:0 \
    --body '{"messages":[{"role":"user","content":"Hello"}],"max_tokens":100}'
```

**Problem:**
1. `content` should be an array of objects with `text` key: `[{"text":"Hello"}]`
2. Parameters should be in `inferenceConfig` object, not top-level
3. Use `maxTokens` (camelCase) not `max_tokens`

## Helper Script

Use the provided script for easy testing:

```bash
./scripts/test_nova_model.sh "Your prompt here"
```

## Key Differences from Claude

| Feature | Amazon Nova | Anthropic Claude |
|---------|-------------|------------------|
| Content Format | Array: `[{"text": "..."}]` | String: `"..."` |
| Config Location | `inferenceConfig` | Top-level |
| Max Tokens | `maxTokens` | `max_tokens` |
| Version Required | No | Yes (`anthropic_version`) |

## Parameters

### inferenceConfig Options
- `maxTokens` (integer, required) - Maximum tokens in response
- `temperature` (float, 0-1) - Randomness (default: 0.7)
- `topP` (float, 0-1) - Nucleus sampling (default: 0.9)
- `stopSequences` (array) - Stop generation at these strings

## Best Practices

1. **Use Python boto3** instead of AWS CLI for easier testing
2. **Start with low maxTokens** (100-200) for testing
3. **Monitor token usage** in response for cost tracking
4. **Use nova-micro** for simple tasks (much cheaper)
5. **Use nova-pro** only when you need advanced reasoning

## Cost Comparison (Approximate)

- nova-micro: Lowest cost, fast responses
- nova-lite: 3-4x micro cost, better quality
- nova-pro: 10-12x micro cost, best quality

Choose the smallest model that meets your needs!
