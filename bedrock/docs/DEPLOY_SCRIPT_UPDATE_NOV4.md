# DEPLOY.sh IAM Policy Update

**Date:** November 4, 2025
**Purpose:** Document enhancement of Bedrock agent IAM policy in DEPLOY.sh

## Summary

Updated the IAM policy for Bedrock agent execution roles in `scripts/DEPLOY.sh` to include comprehensive permissions discovered during troubleshooting of the agent invocation access denied issue.

## Changes Made

**File:** `/Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/scripts/DEPLOY.sh`
**Lines:** 436-480 (IAM policy definition)

### Additions to IAM Policy

#### 1. Explicit Inference Profile ARN
**Added:**
```json
"arn:aws:bedrock:${REGION}::inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0"
```

**Why:** Claude 3.5 v2 requires explicit inference profile permissions. The wildcard `inference-profile/*` alone was insufficient.

#### 2. Enhanced Bedrock Agent Runtime Actions
**Added:**
```json
"bedrock:GetInferenceProfile",
"bedrock:ListInferenceProfiles"
```

**Why:** Agents need to retrieve inference profile details and list available profiles during model invocation.

#### 3. Lambda Invoke Permission Statement
**Added entire new statement:**
```json
{
  "Sid": "LambdaInvokePermission",
  "Effect": "Allow",
  "Action": [
    "lambda:InvokeFunction"
  ],
  "Resource": [
    "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-scheduling-actions",
    "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-information-actions",
    "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-chitchat-actions"
  ]
}
```

**Why:** Agent execution roles need explicit permission to invoke Lambda action groups. While Lambda resource-based policies allow the invocation, the agent role also needs the invoke permission.

## Complete Updated Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockModelAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:${REGION}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
        "arn:aws:bedrock:*::foundation-model/*",
        "arn:aws:bedrock:${REGION}::inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        "arn:aws:bedrock:*::inference-profile/*"
      ]
    },
    {
      "Sid": "BedrockAgentRuntime",
      "Effect": "Allow",
      "Action": [
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel",
        "bedrock:GetInferenceProfile",
        "bedrock:ListInferenceProfiles"
      ],
      "Resource": "*"
    },
    {
      "Sid": "LambdaInvokePermission",
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-scheduling-actions",
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-information-actions",
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-chitchat-actions"
      ]
    }
  ]
}
```

## Impact

### For New Deployments
Future deployments using `scripts/DEPLOY.sh` will automatically create agent execution roles with comprehensive permissions, potentially avoiding the agent invocation access denied issue.

### For Existing Deployments
Existing agent roles already have the enhanced policy (updated manually during troubleshooting on November 4, 2025). No redeployment needed.

## Testing Recommendations

After deploying with the updated script:

1. **Verify role policy:**
   ```bash
   aws iam get-role-policy \
       --role-name pf-chitchat-agent-role \
       --policy-name BedrockModelInvoke
   ```

2. **Test agent invocation:**
   ```bash
   aws bedrock-agent-runtime invoke-agent \
       --agent-id <AGENT_ID> \
       --agent-alias-id <ALIAS_ID> \
       --session-id test-$(date +%s) \
       --input-text "Hello"
   ```

3. **Monitor for errors:**
   ```bash
   # Should not see accessDeniedException
   # May still need IAM propagation delay (5-10 minutes)
   ```

## Related Documentation

- `docs/BEDROCK_ACCESS_DENIED_RESOLUTION.md` - Full troubleshooting process
- `docs/CLAUDE_USAGE.md` - Claude model invocation guide
- `docs/BEDROCK_QUICK_REFERENCE.md` - Model format comparison

## CLEANUP.sh Status

**No changes required** - CLEANUP.sh is already comprehensive and handles all current agents and resources correctly.

## Verification

To verify the update was successful:

```bash
# Check the IAM policy section in DEPLOY.sh
grep -A 40 "Attach comprehensive Bedrock permissions" scripts/DEPLOY.sh

# Look for:
# - inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0
# - GetInferenceProfile and ListInferenceProfiles actions
# - LambdaInvokePermission statement with 3 Lambda functions
```

## Next Steps

1. Test the updated DEPLOY.sh script in a clean environment (optional)
2. Continue monitoring agent invocation for access denied resolution
3. Document any additional findings from AWS Support or Console testing
