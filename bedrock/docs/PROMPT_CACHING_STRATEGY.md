# Prompt Caching Strategy for Bedrock Agents

## Current Situation

**Problem:** Agent response times are 25-50 seconds
**Goal:** Reduce latency and costs using prompt caching
**Challenge:** AWS Bedrock Agents don't support prompt caching yet (only InvokeModel/Converse APIs do)

---

## What is Prompt Caching?

Prompt caching allows you to cache static parts of prompts (like agent instructions) so they don't need to be reprocessed on every request.

**Benefits:**
- **90% cost reduction** on cached tokens
- **Up to 85% latency reduction**
- **5-minute TTL** (resets on each cache hit)

**Requirements for Claude models:**
- Minimum **1,024 tokens** per cache checkpoint
- Maximum **4 cache checkpoints** per request
- Available regions: us-east-1, us-west-2

---

## Current Agent Analysis

### Supervisor Agent
- Model: `us.anthropic.claude-3-5-sonnet-20241022-v2:0` ✅ Supports caching
- Instructions: ~445 words (~600 tokens) ❌ Below 1,024 minimum
- Region: us-east-1 ✅ Supports caching

### Sub-Agents (Scheduling, Information, ChitChat)
- Need to check instruction sizes
- Likely also below 1,024 token minimum

---

## The Problem: Bedrock Agents Don't Support Caching (Yet)

**Bedrock Agent API (`InvokeAgent`):**
❌ Does NOT support prompt caching parameters
❌ Cannot add `cache_control` blocks
❌ No way to enable caching directly

**Direct Claude API (`Converse` / `InvokeModel`):**
✅ Supports prompt caching
✅ Can add cache checkpoints
✅ Works with same Claude models

---

## Solution Options

### Option 1: Hybrid Approach (Recommended)
**Use caching where possible, prepare agents for future support**

#### 1A. Add Caching to Existing Lambda Functions
If any Lambda functions make direct Claude API calls (not through agents), add caching:

```python
import boto3
import json

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

response = bedrock.converse(
    modelId='us.anthropic.claude-3-5-sonnet-20241022-v2:0',
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "text": "Static system prompt here (>1024 tokens)",
                    "cache_control": {"type": "ephemeral"}  # Cache this block
                },
                {
                    "text": f"User query: {user_message}"  # Not cached
                }
            ]
        }
    ],
    inferenceConfig={
        "maxTokens": 512,
        "temperature": 0.7
    }
)

# Check cache performance
cache_read = response['usage']['cacheReadInputTokens']
cache_write = response['usage']['cacheWriteInputTokens']
print(f"Cache hits: {cache_read}, Cache writes: {cache_write}")
```

#### 1B. Expand Agent Instructions to >1,024 Tokens
Make agent instructions cache-ready for when AWS adds support:

**Current Supervisor: ~600 tokens**
**Target: >1,024 tokens**

Add static reference content:
- Detailed examples (10-15 more)
- Error handling scenarios
- Edge case documentation
- API response format specifications

This won't help NOW but prepares for future caching support.

#### 1C. Create Cached Classification Layer
Add a caching layer BEFORE calling agents:

```
User Request
  → Cached Claude Call (classify intent) ← 90% cheaper, 85% faster
  → Route to appropriate agent
  → Agent processes (no caching yet)
  → Return response
```

### Option 2: Wait for AWS to Add Agent Caching Support
AWS is actively working on this. Monitor:
- AWS Bedrock release notes
- Re:Invent announcements
- Preview features

### Option 3: Replace Agents with Direct Claude API Calls + Caching
**Most aggressive approach:**

Convert agent architecture to:
```
User Request
  → Cached Claude call with full context
  → Direct Lambda function calls
  → Format response
  → Return
```

**Pros:**
- Full caching support NOW
- Complete control over prompts
- Potentially faster

**Cons:**
- Loses agent orchestration
- More code to maintain
- Loses agent-specific features (knowledge bases, action groups)

---

## Recommended Implementation Plan

### Phase 1: Quick Wins (This Week)

**1. Analyze Current Token Usage**
```bash
# Check agent instruction sizes
for agent in supervisor scheduling information chitchat; do
  echo "$agent:"
  wc -w infrastructure/agent_instructions/${agent}_collaborator.txt 2>/dev/null || \
  wc -w infrastructure/agent_instructions/${agent}.txt
done
```

**2. Identify Direct Claude API Calls**
Find any Lambda functions that call Claude directly (not through agents):
```bash
grep -r "bedrock.*invoke" lambda/*/handler.py
grep -r "converse\|invokeModel" lambda/*/handler.py
```

**3. Add Caching to Direct Calls (If Found)**
Implement prompt caching on any direct Claude API calls found.

**Result:** 5-15% latency reduction (estimated)

### Phase 2: Prepare for Future (Next 2 Weeks)

**4. Expand Agent Instructions to >1,024 Tokens**
Target all agents to have cacheable instruction sizes:

```
Supervisor: 600 → 1,200 tokens
Scheduling: ??? → 1,200 tokens
Information: ??? → 1,200 tokens
ChitChat: ??? → 1,200 tokens
```

Add:
- More examples (50+ realistic user queries)
- Detailed error scenarios
- API format specifications
- ProjectForce domain knowledge

**5. Restructure Instructions for Caching**
Organize as:
```
[STATIC CONTENT - 1,200+ tokens - CACHEABLE]
- Core instructions
- Examples
- Rules
- Error handling

[DYNAMIC CONTENT - Variable - NOT CACHED]
- Customer context
- Session data
- Recent conversation
```

**Result:** Ready for caching when AWS adds support

### Phase 3: Architecture Decision (Next Month)

**6. Evaluate Performance After Phases 1-2**

If still too slow (>10s), consider:

**Option A:** Hybrid approach
- Simple queries → Direct Claude API with caching
- Complex queries → Bedrock Agents (no caching yet)

**Option B:** Full migration to cached Claude API
- Replace agents with direct API calls
- Implement custom orchestration
- Add comprehensive caching

---

## Performance Projections

### Current State (No Caching)
```
Agent call: 25-50 seconds
- Bedrock Agent processing: 20-45s
- Lambda execution: 2-3s
- API calls: 2-3s
```

### With Phase 1 (Direct API Caching)
```
Estimated improvement: 5-15%
New time: 21-42 seconds
- Savings on cached classification: ~2-5s
```

### With Full Agent Caching (When Available)
```
Estimated improvement: 40-60%
New time: 10-20 seconds
- Cached agent instructions: 15-30s savings
```

### With Hybrid Approach (Direct API)
```
Estimated improvement: 88%
New time: 3-4 seconds
- Direct Lambda calls with caching
- Skip agent orchestration overhead
```

---

## Cost Analysis

### Current Costs (No Caching)
Assuming 1,000 requests/day:

```
Input tokens: ~2,000 per request × 1,000 = 2M tokens/day
Claude 3.5 Sonnet: $3.00 per 1M input tokens
Cost: $6.00/day = $180/month
```

### With Prompt Caching
Assuming 80% cache hit rate after warmup:

```
Cached tokens: 1,600 × 1,000 = 1.6M tokens/day
Cache read cost: $0.30 per 1M tokens = $0.48/day

Non-cached tokens: 400 × 1,000 = 400K tokens/day
Normal cost: $3.00 per 1M = $1.20/day

Total: $1.68/day = $50.40/month
Savings: $129.60/month (72% reduction)
```

---

## Monitoring & Measurement

### Metrics to Track

**Before Caching:**
```bash
# Log agent invocation latency
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name AgentInvocationLatency \
  --start-time 2025-01-01T00:00:00Z \
  --end-time 2025-01-02T00:00:00Z \
  --period 3600 \
  --statistics Average
```

**After Caching:**
```python
# In Lambda code
import time

start = time.time()
response = bedrock.converse(...)
duration = time.time() - start

cache_hit_rate = response['usage'].get('cacheReadInputTokens', 0) / total_input_tokens

logger.info(f"Request duration: {duration}s")
logger.info(f"Cache hit rate: {cache_hit_rate:.2%}")
logger.info(f"Cache read tokens: {response['usage'].get('cacheReadInputTokens', 0)}")
logger.info(f"Cache write tokens: {response['usage'].get('cacheWriteInputTokens', 0)}")
```

---

## Next Steps

1. **Run the analysis script** (see Phase 1)
2. **Check if any Lambda functions call Claude directly**
3. **Decide on approach:**
   - Conservative: Wait for AWS agent caching + prepare instructions
   - Moderate: Add caching to direct calls + expand instructions
   - Aggressive: Migrate to direct Claude API with full caching

Which approach do you want to take?
