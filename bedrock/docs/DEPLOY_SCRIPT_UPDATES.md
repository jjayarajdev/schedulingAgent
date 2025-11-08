# DEPLOY.sh Script Updates - November 4, 2025

## Summary
Updated DEPLOY.sh to use the correct Claude 3.5 Sonnet V2 inference profile and proper IAM permissions.

---

## Changes Made

### 1. Model ID Configuration (Line 397)

**BEFORE:**
```bash
local MODEL_ID="anthropic.claude-3-5-sonnet-20241022-v2:0"
```

**AFTER:**
```bash
local MODEL_ID="us.anthropic.claude-3-5-sonnet-20241022-v2:0"
```

**Why:**
- The direct model ID `anthropic.claude-3-5-sonnet-20241022-v2:0` does NOT support on-demand invocation
- Must use cross-region inference profile: `us.anthropic.claude-3-5-sonnet-20241022-v2:0`
- This allows the agent to invoke the model without pre-provisioned throughput

**Error Before Fix:**
```
validationException: Invocation of model ID anthropic.claude-3-5-sonnet-20241022-v2:0
with on-demand throughput isn't supported. Retry your request with the ID or ARN of
an inference profile that contains this model.
```

---

### 2. IAM Policy for Agent Roles (Lines 436-451)

**BEFORE:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": "arn:aws:bedrock:${REGION}::foundation-model/${MODEL_ID}"
    }
  ]
}
```

**AFTER:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": [
        "arn:aws:bedrock:${REGION}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
        "arn:aws:bedrock:*::foundation-model/*"
      ]
    }
  ]
}
```

**Why:**
- Single resource ARN only allowed the specific model ID
- Inference profiles have different ARN patterns
- Wildcard `arn:aws:bedrock:*::foundation-model/*` allows:
  - Direct model invocations
  - Cross-region inference profiles
  - Future model versions without policy updates

**Error Before Fix:**
```
accessDeniedException: Access denied when calling Bedrock.
Check your request permissions and retry the request.
```

---

## Impact

### Agents Created
All 4 agents will now be created with:
- ✅ Correct inference profile model ID
- ✅ Proper IAM permissions for model invocation
- ✅ Support for both direct and inference profile access

### Affected Agents
1. **SchedulingAgent** - Primary agent for scheduling
2. **pf-information** - Weather information agent
3. **pf-chitchat** - Conversational agent
4. **Supervisor** - Orchestrator agent

---

## Testing

After running the updated DEPLOY.sh:

1. **Verify Model ID:**
   ```bash
   aws bedrock-agent get-agent \
     --agent-id <AGENT_ID> \
     --region us-east-1 \
     --query 'agent.foundationModel' \
     --output text
   ```
   Should return: `us.anthropic.claude-3-5-sonnet-20241022-v2:0`

2. **Verify IAM Policy:**
   ```bash
   aws iam get-role-policy \
     --role-name AmazonBedrockExecutionRoleForAgents_SchedulingAgent \
     --policy-name BedrockModelInvoke \
     --output json
   ```
   Should show wildcard resource permission.

3. **Test Agent Invocation:**
   ```bash
   ./scripts/TEST_AGENTS.sh
   ```
   Should successfully invoke agents without permission errors.

---

## Cleanup Before Redeployment

Before running the updated DEPLOY.sh, clean up existing resources:

```bash
# Run cleanup script
./scripts/CLEANUP.sh

# Wait for all resources to be deleted (check AWS Console)

# Then deploy with fresh configuration
export PF_BEARER_TOKEN="your-bearer-token-here"
./scripts/DEPLOY.sh
```

---

## Additional Fixes Applied

Also fixed in this session (but not in DEPLOY.sh):

1. **pfuser IAM Permissions** - Added bedrock-agent-runtime:InvokeAgent permission
   ```bash
   aws iam put-user-policy \
     --user-name pfuser \
     --policy-name BedrockAgentInvoke \
     --policy-document file:///tmp/bedrock-full-policy.json
   ```

2. **TEST_AGENTS.sh** - Updated to use boto3 instead of AWS CLI
   - AWS CLI no longer supports `aws bedrock-agent-runtime invoke-agent`
   - Now uses Python SDK with `client.invoke_agent()`

---

## Files Modified

1. `/Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/scripts/DEPLOY.sh`
   - Line 397: Model ID
   - Lines 436-451: IAM policy

2. `/Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/scripts/TEST_AGENTS.sh`
   - Lines 118-174: boto3 invocation instead of AWS CLI

---

## Status: ✅ READY FOR CLEAN DEPLOYMENT

The DEPLOY.sh script is now updated and ready for a clean deployment with:
- ✅ Correct inference profile model ID
- ✅ Proper IAM permissions
- ✅ Bearer token support
- ✅ All previous fixes integrated
