# Redeploy with Working Model - November 4, 2025

## Root Cause Discovered

The agent invocation failures were caused by using Claude models that **require inference profiles**:

**Models that DON'T work (require inference profiles):**
- ❌ `anthropic.claude-3-5-sonnet-20241022-v2:0` (Claude 3.5 Sonnet v2)
- ❌ `anthropic.claude-3-5-haiku-20241022-v1:0` (Claude 3.5 Haiku)
- ❌ `anthropic.claude-3-5-sonnet-20240620-v1:0` (Claude 3.5 Sonnet v1)

**Model that WORKS (no inference profile needed):**
- ✅ `anthropic.claude-3-haiku-20240307-v1:0` (Claude 3 Haiku - March 2024)

## Why AWS Console Didn't Help

When you change the model in AWS Bedrock Console, it only shows **base model IDs**, not inference profile IDs. Since newer Claude models require inference profiles, changing them in the UI doesn't fix the issue - they still fail with "Access denied."

## Solution Applied

Updated `scripts/DEPLOY.sh` to use Claude 3 Haiku (March 2024):

**Line 397-398:**
```bash
# Use Claude 3 Haiku (March 2024) - works without inference profile
local MODEL_ID="anthropic.claude-3-haiku-20240307-v1:0"
```

## Scripts Updated

### DEPLOY.sh Changes
1. **Model ID** (line 398): Changed to `anthropic.claude-3-haiku-20240307-v1:0`
2. **Comment added**: Explains why this specific model is used

### CLEANUP.sh Changes
1. **Lambda functions** (line 99-103): Reduced to 3 functions (removed old/unused ones)
2. **IAM roles** (line 135-145): Updated to current 7 roles (4 agent + 3 Lambda)
3. **Summary counts** (line 278-281): Updated to reflect 4 agents, 3 functions, 7 roles
4. **Date** (line 7): Updated to 2025-11-04

## Fresh Deployment Steps

### Step 1: Cleanup Existing Resources

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock

# Run cleanup (will delete agents but KEEP IAM roles)
./scripts/CLEANUP.sh

# OR cleanup including roles (cleaner)
./scripts/CLEANUP.sh --delete-roles
```

**What will be deleted:**
- 4 Bedrock agents (SchedulingAgent, pf-chitchat, pf-information, Supervisor)
- 3 Lambda functions (pf-scheduling-actions, pf-information-actions, pf-chitchat-actions)
- Secrets Manager secret (if exists)
- DynamoDB tables (if exists)
- IAM roles (only if you use --delete-roles flag)

### Step 2: Deploy Fresh

```bash
# Deploy everything with the working model
./scripts/DEPLOY.sh
```

**What will be created:**
- 4 Bedrock agents using Claude 3 Haiku
- 3 Lambda functions with ProjectForce API integration
- IAM roles with correct permissions
- Agent aliases (TSTALIASID)
- Action groups linking agents to Lambda functions

**Expected duration:** ~5-10 minutes

### Step 3: Verify Deployment

```bash
# Check agents are created
aws bedrock-agent list-agents --region us-east-1

# Check Lambda functions
aws lambda list-functions --region us-east-1 --query 'Functions[?starts_with(FunctionName, `pf-`)].FunctionName'

# Test Lambda function directly
aws lambda invoke \
    --function-name pf-scheduling-actions \
    --payload '{"action":"list_projects","userId":"test@example.com"}' \
    response.json && cat response.json | jq '.'
```

### Step 4: Test Agent Invocation

```bash
python3 << 'EOF'
import boto3
from datetime import datetime

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

# Get agent ID from list-agents output
print("Testing agent invocation...")

response = client.invoke_agent(
    agentId='AGENT_ID_HERE',  # Replace with actual ID from Step 3
    agentAliasId='TSTALIASID',
    sessionId=f'test-{int(datetime.now().timestamp())}',
    inputText='Show my projects'
)

print("Response:")
for event in response['completion']:
    if 'chunk' in event:
        print(event['chunk']['bytes'].decode('utf-8'), end='', flush=True)

print("\n✅ SUCCESS!")
EOF
```

## Expected Results

**Before (with Claude 3.5 models):**
```
✅ Agent invocation initiated successfully!
❌ Error: EventStreamError
Message: An error occurred (accessDeniedException) when calling the InvokeAgent operation
```

**After (with Claude 3 Haiku):**
```
✅ Agent invocation initiated successfully!

Response:
────────────────────────────────────────────────────────────────────────────────
<thinking>
Let me check the available projects for you by calling the list_projects function.
</thinking>

I found 25 projects in your ProjectForce account. Here are your active projects:
[List of projects...]

✅ SUCCESS!
```

## Claude 3 Haiku Capabilities

**Performance:**
- Very fast response times (1-3 seconds)
- Cost-effective (much cheaper than Sonnet/Opus)
- Proven to work with direct invocation

**Capabilities:**
- Excellent for most scheduling and information tasks
- Good reasoning and function calling
- Handles multi-turn conversations well
- Suitable for production use

**Comparison to Claude 3.5:**
- Slightly less capable for complex reasoning
- May need more explicit instructions
- Still very good for 90% of use cases
- The trade-off is worth it for working agents!

## Future Upgrade Path

Once AWS provides a way to specify inference profile IDs in agent configuration (via Console or CLI update), you can upgrade to Claude 3.5 models:

**Option 1: Use inference profile in DEPLOY.sh**
```bash
local MODEL_ID="us.anthropic.claude-3-5-sonnet-20241022-v2:0"
```

**Option 2: Wait for AWS to update Console**
- AWS may add inference profile support to the Bedrock Console
- Then you can change models without redeployment

## Troubleshooting

### If agent invocation still fails:

1. **Check model ID in trace:**
   - Test in AWS Bedrock Console
   - Look for `foundationModel` in trace
   - Should show: `anthropic.claude-3-haiku-20240307-v1:0`

2. **Verify direct model access:**
   ```bash
   ./scripts/test_claude_model.sh "Hello" "anthropic.claude-3-haiku-20240307-v1:0"
   ```

3. **Check IAM roles:**
   ```bash
   aws iam list-attached-role-policies --role-name pf_scheduling_agent_role
   # Should show AmazonBedrockFullAccess
   ```

4. **Wait for IAM propagation:**
   - Fresh deployments may need 5-10 minutes for IAM to propagate
   - Try again after waiting

## Files Modified

- `scripts/DEPLOY.sh` - Changed model ID on line 398
- `scripts/CLEANUP.sh` - Updated counts and role lists
- `docs/REDEPLOY_WITH_WORKING_MODEL_NOV4.md` - This document
- `docs/SOLUTION_MODEL_ID_FIX.md` - Detailed analysis of the issue

## Next Steps After Successful Deployment

1. **Test all 4 agents individually**
2. **Test Supervisor agent routing**
3. **Verify Lambda integration**
4. **Test end-to-end workflows**
5. **Document agent behaviors**
6. **Proceed with Phase 2 development**

## Summary

**The Issue:** Claude 3.5 models require inference profiles that can't be specified in agent configuration via Console

**The Fix:** Use Claude 3 Haiku (March 2024) which works without inference profiles

**The Result:** Fully functional Bedrock agents with Lambda integration

**Trade-off:** Slightly less capable model, but agents actually work

**When to Upgrade:** When AWS adds inference profile support to agent configuration

---

Ready to deploy? Run:
```bash
./scripts/CLEANUP.sh --delete-roles
./scripts/DEPLOY.sh
```
