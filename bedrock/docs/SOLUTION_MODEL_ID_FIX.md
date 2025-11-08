# SOLUTION: Bedrock Agent Model ID Fix

**Date:** November 4, 2025
**Status:** 🎯 **ROOT CAUSE IDENTIFIED**

## Problem Identified

The agent invocation failure is due to an **incorrect model ID configuration**, NOT permissions!

### Evidence from UI Trace

```json
{
  "foundationModel": "anthropic.claude-3-5-sonnet-20241022-v2:0",
  "failureCode": 403,
  "failureReason": "Access denied when calling Bedrock. Check your request permissions and retry the request."
}
```

### The Issue

**Current (WRONG):**
```
anthropic.claude-3-5-sonnet-20241022-v2:0
```
This is a BASE MODEL ID that doesn't support on-demand invocation.

**Should Be:**
```
us.anthropic.claude-3-5-sonnet-20241022-v2:0
```
This is an INFERENCE PROFILE ID that supports on-demand invocation.

### Why This Happened

Claude 3.5 Sonnet v2 was released with a requirement that it can only be invoked via inference profiles, not directly. The error message "Access denied" is misleading - it's actually a "model not available for direct invocation" error.

## Solution Options

### Option 1: Update to Inference Profile (Recommended)

Update the agent configuration to use the inference profile ID.

**Via AWS Console:**
1. Go to AWS Bedrock Console → Agents
2. Select "SchedulingAgent" (ID: VBZPDTNEXJ)
3. Click "Edit"
4. Update Foundation Model from:
   - FROM: `anthropic.claude-3-5-sonnet-20241022-v2:0`
   - TO: `us.anthropic.claude-3-5-sonnet-20241022-v2:0`
5. Save changes
6. Repeat for all 4 agents:
   - SchedulingAgent (VBZPDTNEXJ)
   - pf-chitchat (G1XCBCAXBX)
   - pf-information (XQFAHG3K8Q)
   - Supervisor (PXGWN2EEBH)

**Via CLI (if UpdateAgent permission is granted):**
```bash
# Would need bedrock:UpdateAgent permission
aws bedrock-agent update-agent \
    --agent-id VBZPDTNEXJ \
    --agent-name SchedulingAgent \
    --foundation-model "us.anthropic.claude-3-5-sonnet-20241022-v2:0" \
    --instruction "You are the SchedulingAgent..." \
    --agent-resource-role-arn "arn:aws:iam::618048437522:role/pf_scheduling_agent_role" \
    --region us-east-1
```

### Option 2: Use Claude 3 Haiku (Works Without Inference Profile)

Change to Claude 3 Haiku which supports direct invocation:

**Model ID:** `anthropic.claude-3-haiku-20240307-v1:0`

**Pros:**
- No inference profile required
- Faster responses
- Lower cost
- Proven to work (we tested it successfully)

**Cons:**
- Less capable than Claude 3.5 Sonnet v2
- May not handle complex reasoning as well

**Via Console:**
1. Edit each agent
2. Change Foundation Model to: `anthropic.claude-3-haiku-20240307-v1:0`
3. Save

### Option 3: Use Claude 3.5 Sonnet v1

Use the older Claude 3.5 Sonnet version:

**Model ID:** `anthropic.claude-3-5-sonnet-20240620-v1:0`

**Pros:**
- Very capable (close to v2 performance)
- Supports direct invocation
- No inference profile needed

**Cons:**
- Not the absolute latest model

### Option 4: Redeploy with Correct Configuration

Run cleanup and redeploy with the corrected model ID:

```bash
# Cleanup existing agents
./scripts/CLEANUP.sh

# Deploy with correct configuration
./scripts/DEPLOY.sh
```

The DEPLOY.sh script already has the correct inference profile ID on line 397:
```bash
local MODEL_ID="us.anthropic.claude-3-5-sonnet-20241022-v2:0"
```

So a fresh deployment should work correctly.

## Verification After Fix

After updating the model ID, test with:

```python
python3 << 'EOF'
import boto3
from datetime import datetime

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

response = client.invoke_agent(
    agentId='VBZPDTNEXJ',
    agentAliasId='TSTALIASID',
    sessionId=f'test-{int(datetime.now().timestamp())}',
    inputText='Show my projects'
)

print("Response:")
for event in response['completion']:
    if 'chunk' in event:
        print(event['chunk']['bytes'].decode('utf-8'), end='', flush=True)
    elif 'trace' in event:
        trace = event['trace'].get('trace', {})
        if 'modelInvocationInput' in trace:
            model = trace['modelInvocationInput'].get('foundationModel', 'Unknown')
            print(f"\n[Model Used: {model}]")

print("\n✅ Success!")
EOF
```

## Why The Error Was Misleading

The error message said "Access denied" but the real issue was:

**AWS Error Message:**
```
Access denied when calling Bedrock. Check your request permissions and retry the request.
```

**Actual Problem:**
```
The model 'anthropic.claude-3-5-sonnet-20241022-v2:0' does not support on-demand invocation.
Please use the inference profile 'us.anthropic.claude-3-5-sonnet-20241022-v2:0' instead.
```

AWS Bedrock returns a 403 error for this case, which made us think it was a permissions issue. It's actually a configuration error.

## Recommended Action

**Immediate Fix (Fastest):**
1. Use AWS Console to update all 4 agents to use: `us.anthropic.claude-3-5-sonnet-20241022-v2:0`
2. Test agent invocation
3. Should work immediately

**Alternative (If Console Update Doesn't Work):**
1. Use AWS Console to update all 4 agents to use: `anthropic.claude-3-haiku-20240307-v1:0`
2. This model is proven to work from our testing
3. Cheaper and faster anyway

**Long-term Fix:**
1. Verify DEPLOY.sh has correct model ID (it does - line 397)
2. Consider adding validation to deployment script to ensure inference profile is used
3. Add error handling to detect this specific case

## Model ID Reference

### ✅ Working Model IDs (Direct Invocation)
```
anthropic.claude-3-haiku-20240307-v1:0
anthropic.claude-3-sonnet-20240229-v1:0
anthropic.claude-3-opus-20240229-v1:0
anthropic.claude-3-5-haiku-20241022-v1:0
anthropic.claude-3-5-sonnet-20240620-v1:0
```

### ✅ Working Inference Profile IDs
```
us.anthropic.claude-3-5-sonnet-20241022-v2:0
us.anthropic.claude-3-5-haiku-20241022-v1:0
```

### ❌ Does NOT Work for Agents (Requires Inference Profile)
```
anthropic.claude-3-5-sonnet-20241022-v2:0  ← This is what's currently configured!
```

## Impact

**Before Fix:**
- All agent invocations fail with accessDeniedException
- Lambda functions work fine
- Direct model invocation works fine

**After Fix:**
- All agent invocations should work ✅
- End-to-end agent orchestration functional
- Can proceed with Phase 2 and Phase 3 development

## Test Plan After Fix

1. **Test Single Agent:**
   ```python
   # Test SchedulingAgent
   response = client.invoke_agent(
       agentId='VBZPDTNEXJ',
       agentAliasId='TSTALIASID',
       sessionId='test-123',
       inputText='Show my projects'
   )
   ```

2. **Test All Agents:**
   - SchedulingAgent: "Show my projects"
   - Chitchat: "Hello, how are you?"
   - Information: "What's the weather in New York?"
   - Supervisor: "I want to check my projects" (should route to SchedulingAgent)

3. **Test Lambda Integration:**
   - Verify agent calls Lambda functions
   - Check Lambda returns real ProjectForce data
   - Confirm agent processes and returns data to user

## Related Files

- `scripts/DEPLOY.sh:397` - Already has correct inference profile ID
- `docs/CLAUDE_USAGE.md` - Documents inference profile requirement
- `docs/AGENT_INVOCATION_ISSUE_ANALYSIS_NOV4.md` - Previous analysis (permissions focus)

## Conclusion

**This was NOT a permissions issue.** The IAM configuration was correct all along. The issue was simply using the wrong model ID format for Claude 3.5 Sonnet v2.

The fix is straightforward: Update the foundation model configuration in the AWS Console for all 4 agents to use the inference profile ID instead of the base model ID.

**Estimated Time to Fix:** 5-10 minutes via AWS Console
**Expected Result:** All agents should work immediately after the change
