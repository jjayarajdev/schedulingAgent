# Bedrock Models - Quick Reference Card

**Date:** November 4, 2025

## Test Scripts

```bash
# Amazon Nova
./scripts/test_nova_model.sh "Your prompt here"

# Claude
./scripts/test_claude_model.sh "Your prompt here"
```

## Request Formats Comparison

### Amazon Nova

```json
{
    "messages": [{
        "role": "user",
        "content": [{"text": "Hello"}]
    }],
    "inferenceConfig": {
        "maxTokens": 500,
        "temperature": 0.7
    }
}
```

### Anthropic Claude

```json
{
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 500,
    "temperature": 0.7,
    "messages": [{
        "role": "user",
        "content": "Hello"
    }]
}
```

## Key Differences

| Feature | Nova | Claude |
|---------|------|--------|
| Version | Not required | **Required**: `anthropic_version` |
| Content | Array: `[{"text":"..."}]` | String: `"..."` |
| Config | `inferenceConfig` object | Top-level params |
| Max Tokens | `maxTokens` (camelCase) | `max_tokens` (snake_case) |

## Common Errors & Fixes

### Amazon Nova: "Malformed input request"

**Your command:**
```bash
--body '{"messages":[{"role":"user","content":"Hello"}],"max_tokens":100}'
```

**Fix:**
1. Content must be array: `"content": [{"text": "Hello"}]`
2. Use `inferenceConfig`: `"inferenceConfig": {"maxTokens": 100}`
3. Use camelCase: `maxTokens` not `max_tokens`

### Claude: "Malformed input request"

**Your command:**
```bash
--body '{"messages":[{"role":"user","content":"Hello"}],"max_tokens":100}'
```

**Fix:**
Add `anthropic_version`:
```json
{
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 100,
    "messages": [{"role": "user", "content": "Hello"}]
}
```

## Model Selection Guide

### Amazon Nova
- **nova-micro** - Cheapest, fastest for simple tasks
- **nova-lite** - Balanced, good for most tasks
- **nova-pro** - Most capable, expensive

### Anthropic Claude
- **haiku** - Fast & cheap, great for most tasks
- **sonnet** - Balanced, best value
- **opus** - Most capable, highest cost
- **3.5 v2** - Latest (needs inference profile: `us.anthropic.*`)

## Cost-Performance Tips

1. **Start cheap**: Try nova-micro or claude-haiku first
2. **Test thoroughly**: Cheapest model often good enough
3. **Monitor tokens**: Actual usage vs max_tokens
4. **Batch requests**: Process multiple items together
5. **Cache prompts**: Reuse system messages

## Response Paths

### Amazon Nova
```python
text = response_body['output']['message']['content'][0]['text']
```

### Claude
```python
text = response_body['content'][0]['text']
```

## Full Documentation

- **Amazon Nova**: `docs/AMAZON_NOVA_USAGE.md`
- **Claude**: `docs/CLAUDE_USAGE.md`
- **Troubleshooting**: `docs/BEDROCK_ACCESS_DENIED_RESOLUTION.md`
