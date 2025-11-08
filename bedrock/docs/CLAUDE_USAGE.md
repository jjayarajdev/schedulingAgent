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

---

# CRITICAL LESSONS LEARNED - Agent Collaboration Architecture

**Date:** November 7, 2025
**Incident:** Agent collaboration broke after updating DRAFT without creating new versions

## The Problem

When using AWS Bedrock agent collaboration, collaborations point to **versioned aliases** (e.g., v1, v2), NOT to DRAFT.

**What happened:**
1. We updated agent instructions in DRAFT
2. We ran `prepare-agent` (which only updates DRAFT)
3. The collaboration was still using v1 alias → pointing to old version 1
4. Result: Agents used old instructions, system appeared broken

## Agent Versioning Architecture

```
┌─────────────────────────────────────────────────────────┐
│ SCHEDULING AGENT                                         │
├─────────────────────────────────────────────────────────┤
│ DRAFT (Working Copy)                                     │
│   ↓ prepare-agent                                        │
│   ↓ create version (AWS Console only)                   │
│ VERSION 1 ← v1 alias points here                        │
│ VERSION 2                                                │
│ VERSION 3                                                │
└─────────────────────────────────────────────────────────┘
                    ↑
                    │
            Collaboration uses v1 alias
                    │
                    │
┌─────────────────────────────────────────────────────────┐
│ SUPERVISOR AGENT                                         │
│   - Routes to collaborators via aliases                 │
│   - Cannot use DRAFT for collaboration                  │
└─────────────────────────────────────────────────────────┘
```

## Correct Update Process

When you need to update agent instructions:

### Step 1: Update DRAFT
```bash
# Update the instruction file
vim bedrock/infrastructure/agent_instructions/scheduling_collaborator.txt

# Update the agent with new instructions
aws bedrock-agent update-agent \
  --agent-id <AGENT_ID> \
  --agent-name "SchedulingAgent" \
  --instruction file://path/to/instructions.txt \
  --region us-east-1
```

### Step 2: Prepare Agent (Updates DRAFT)
```bash
aws bedrock-agent prepare-agent \
  --agent-id <AGENT_ID> \
  --region us-east-1
```

### Step 3: Create New Version (AWS Console Required)
**THIS IS THE STEP WE MISSED**

1. Go to AWS Bedrock Console
2. Navigate to Agents → Select your agent
3. Click "Working draft" dropdown
4. Select "Create version"
5. Wait for version creation to complete (creates version 2, 3, etc.)

### Step 4: Update Alias to Point to New Version
```bash
# Option A: Via AWS Console (Recommended)
# 1. Go to agent's "Aliases" tab
# 2. Click on the alias (e.g., "v1")
# 3. Click "Edit"
# 4. Change "Agent version" from old to new version
# 5. Click "Save"

# Option B: Via CLI (if you know the version number)
aws bedrock-agent update-agent-alias \
  --agent-id <AGENT_ID> \
  --agent-alias-id <ALIAS_ID> \
  --agent-alias-name v1 \
  --routing-configuration agentVersion=2 \
  --region us-east-1
```

### Step 5: Prepare Supervisor Agent
```bash
# After updating collaborator versions, prepare supervisor
aws bedrock-agent prepare-agent \
  --agent-id <SUPERVISOR_AGENT_ID> \
  --region us-east-1
```

## What NOT to Do

❌ **DON'T** just run `prepare-agent` and assume it's live
❌ **DON'T** try to point aliases to DRAFT (not allowed)
❌ **DON'T** disassociate/re-associate collaborators without understanding the impact
❌ **DON'T** assume collaborations work like regular agent invocations

## Diagnostic Commands

Before making changes, ALWAYS check current state:

```bash
# Check which version an alias points to
aws bedrock-agent get-agent-alias \
  --agent-id <AGENT_ID> \
  --agent-alias-id <ALIAS_ID> \
  --region us-east-1 \
  --query 'agentAlias.routingConfiguration[0].agentVersion'

# List all collaborators and their aliases
aws bedrock-agent list-agent-collaborators \
  --agent-id <SUPERVISOR_ID> \
  --agent-version DRAFT \
  --region us-east-1

# Check when agent was last prepared
aws bedrock-agent get-agent \
  --agent-id <AGENT_ID> \
  --region us-east-1 \
  --query 'agent.preparedAt'
```

## Why This Matters

1. **Collaborations require stability** - They use versioned aliases to ensure consistency
2. **DRAFT is for development** - It's not meant for production collaboration
3. **Version control is intentional** - Forces you to explicitly promote changes
4. **Breaking changes are isolated** - Old versions remain accessible via their aliases

## Prevention Checklist

Before updating any collaborative agent:

- [ ] Check current alias → version mapping
- [ ] Understand which collaborators depend on this agent
- [ ] Update DRAFT with new instructions
- [ ] Prepare DRAFT
- [ ] Create new version (AWS Console)
- [ ] Update alias to new version
- [ ] Prepare supervisor agent
- [ ] Test collaboration works
- [ ] Only then consider it "deployed"

## Key Takeaway

> **When working with agent collaboration, remember:**
> "Prepare updates DRAFT. Versioning publishes it. Aliases route to it. All three are required."

This is not optional - it's the architecture. Skipping any step breaks collaboration.
