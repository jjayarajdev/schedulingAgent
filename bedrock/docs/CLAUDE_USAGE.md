# Anthropic Claude Model Usage Guide

**Date:** November 4, 2025
**Purpose:** Quick reference for using Claude models with AWS Bedrock

## Available Claude Models

### Claude 3 Family (Stable - Direct Access)
- `anthropic.claude-3-haiku-20240307-v1:0` - Fast, cost-effective
- `anthropic.claude-3-sonnet-20240229-v1:0` - Balanced performance
- `anthropic.claude-3-opus-20240229-v1:0` - Most capable
- `anthropic.claude-3-5-haiku-20241022-v1:0` - Latest Haiku
- `anthropic.claude-instant-v1` - Legacy, very fast

### Claude 3.5 v2 (Requires Inference Profile)
- `us.anthropic.claude-3-5-sonnet-20241022-v2:0` - Latest (inference profile)
- ❌ `anthropic.claude-3-5-sonnet-20241022-v2:0` - Won't work (needs profile)

## Correct Request Format

**Key requirement:** Must include `anthropic_version` parameter!

```json
{
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 500,
    "temperature": 0.7,
    "messages": [
        {
            "role": "user",
            "content": "Your prompt here"
        }
    ]
}
```

## Python Example (Recommended)

```python
import boto3
import json

client = boto3.client('bedrock-runtime', region_name='us-east-1')

body = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 500,
    "temperature": 0.7,
    "messages": [
        {
            "role": "user",
            "content": "Hello, how are you?"
        }
    ]
}

response = client.invoke_model(
    modelId='anthropic.claude-3-haiku-20240307-v1:0',
    body=json.dumps(body)
)

response_body = json.loads(response['body'].read())
text = response_body['content'][0]['text']
print(text)
```

## Response Format

```json
{
    "id": "msg_...",
    "type": "message",
    "role": "assistant",
    "model": "claude-3-haiku-20240307",
    "content": [
        {
            "type": "text",
            "text": "Response text here"
        }
    ],
    "stop_reason": "end_turn",
    "usage": {
        "input_tokens": 13,
        "output_tokens": 18
    }
}
```

## Common Errors

### 1. Malformed Input Request

**Error:**
```
ValidationException: Malformed input request, please reformat your input and try again.
```

**Your Original Command:**
```bash
# ❌ This doesn't work:
aws bedrock-runtime invoke-model \
    --model-id anthropic.claude-3-haiku-20240307-v1:0 \
    --body '{"messages":[{"role":"user","content":"Hello"}],"max_tokens":100}'
```

**Problem:** Missing `anthropic_version` parameter

**Fix:**
```python
body = {
    "anthropic_version": "bedrock-2023-05-31",  # Required!
    "max_tokens": 100,
    "messages": [{"role": "user", "content": "Hello"}]
}
```

### 2. On-Demand Throughput Not Supported

**Error:**
```
ValidationException: Invocation of model ID anthropic.claude-3-5-sonnet-20241022-v2:0
with on-demand throughput isn't supported. Retry your request with the ID or ARN of an
inference profile.
```

**Fix:** Use the inference profile ID:
```python
modelId='us.anthropic.claude-3-5-sonnet-20241022-v2:0'  # Note the "us." prefix
```

## Helper Script

Use the provided script for easy testing:

```bash
# Test with Haiku (fast, cheap)
./scripts/test_claude_model.sh "Your prompt here"

# Test with Sonnet (balanced)
./scripts/test_claude_model.sh "Your prompt" "anthropic.claude-3-sonnet-20240229-v1:0"

# Test with Claude 3.5 v2 (requires inference profile)
./scripts/test_claude_model.sh "Your prompt" "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
```

## Parameters

### Required
- `anthropic_version` (string) - Always use `"bedrock-2023-05-31"`
- `max_tokens` (integer) - Maximum tokens in response (1-4096)
- `messages` (array) - Conversation messages

### Optional
- `temperature` (float, 0-1) - Randomness (default: 1.0)
- `top_p` (float, 0-1) - Nucleus sampling (default: 0.999)
- `top_k` (integer) - Top-k sampling (default: 250)
- `stop_sequences` (array) - Stop generation at these strings
- `system` (string) - System prompt

## Multi-Turn Conversations

```python
body = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 500,
    "system": "You are a helpful assistant.",
    "messages": [
        {"role": "user", "content": "What is the capital of France?"},
        {"role": "assistant", "content": "The capital of France is Paris."},
        {"role": "user", "content": "What is its population?"}
    ]
}
```

## Model Comparison

| Model | Speed | Cost | Quality | Best For |
|-------|-------|------|---------|----------|
| Claude Instant | Fastest | Lowest | Good | Simple tasks, high volume |
| Claude 3 Haiku | Very Fast | Low | Great | Most tasks, cost-effective |
| Claude 3 Sonnet | Fast | Medium | Excellent | Complex reasoning |
| Claude 3 Opus | Moderate | High | Best | Critical tasks |
| Claude 3.5 Sonnet v2 | Fast | Medium | Excellent | Latest features |

## Cost Optimization Tips

1. **Start with Haiku** - It's surprisingly good and much cheaper
2. **Use lower max_tokens** - Only request what you need
3. **Cache system prompts** - Reuse system messages across requests
4. **Batch requests** - Process multiple items in one call when possible
5. **Monitor token usage** - Track actual usage vs. max_tokens

## Best Practices

1. **Always include anthropic_version** - Required for all Claude models
2. **Set reasonable max_tokens** - Default is 4096, often too much
3. **Use system prompts** - Better than including instructions in every message
4. **Handle stop_reason** - Check if response was truncated (stop_reason != "end_turn")
5. **Monitor token usage** - Response includes actual token counts

## Differences from Amazon Nova

| Feature | Claude | Amazon Nova |
|---------|--------|-------------|
| Version Required | Yes (`anthropic_version`) | No |
| Content Format | String: `"Hello"` | Array: `[{"text":"Hello"}]` |
| Max Tokens Key | `max_tokens` (snake_case) | `maxTokens` (camelCase) |
| Config Location | Top-level | `inferenceConfig` object |
| Response Path | `content[0].text` | `output.message.content[0].text` |

## Quick Reference

### Haiku (Fast & Cheap)
```bash
./scripts/test_claude_model.sh "Your prompt"
```

### Sonnet (Balanced)
```bash
./scripts/test_claude_model.sh "Your prompt" "anthropic.claude-3-sonnet-20240229-v1:0"
```

### Claude 3.5 v2 (Latest)
```bash
./scripts/test_claude_model.sh "Your prompt" "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
```

## Resources

- [Claude on AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages.html)
- [Anthropic API Reference](https://docs.anthropic.com/claude/reference/messages_post)
- [Bedrock Runtime API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_InvokeModel.html)
