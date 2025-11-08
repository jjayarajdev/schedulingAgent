# Bedrock Agent Access Denied - Resolution Attempt

**Date:** November 4, 2025  
**Issue:** `accessDeniedException` when calling Bedrock through agents  
**Status:** Partially Resolved - IAM policies updated, still investigating

## Problem Statement

When invoking Bedrock agents, we get:
```
An error occurred (accessDeniedException) when calling the InvokeAgent operation: 
Access denied when calling Bedrock. Check your request permissions and retry the request.
```

## Investigation Steps

### 1. User Permissions ✅
**User:** pfuser (arn:aws:iam::618048437522:user/pfuser)

**Attached Policies:**
- AdministratorAccess
- AmazonBedrockFullAccess
- PowerUserAccess
- IAMUserChangePassword
- BedrockAgentInvoke (inline)

**Result:** User has full permissions - NOT the issue

### 2. Model Access ✅
**Models Available:** All Claude models including Claude 3.5 Sonnet v2  
**Model ID Used:** `us.anthropic.claude-3-5-sonnet-20241022-v2:0`  
**Direct Invocation Test:** ✅ SUCCESS

**Result:** Model access granted - NOT the issue

### 3. Agent Configuration ✅
**Agents Deployed:**
- Supervisor (PXGWN2EEBH) - PREPARED
- SchedulingAgent (VBZPDTNEXJ) - PREPARED  
- pf-information (XQFAHG3K8Q) - PREPARED
- pf-chitchat (G1XCBCAXBX) - PREPARED

**Result:** All agents properly configured - NOT the issue

### 4. Agent IAM Roles - UPDATED ✅

**Problem Found:** Agent execution roles had insufficient permissions for inference profiles

**Original Policy:**
```json
{
    "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
        "arn:aws:bedrock:*::foundation-model/*",
        "arn:aws:bedrock:us-east-1::inference-profile/*"
    ]
}
```

**Updated Policy (Added):**
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
                "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
                "arn:aws:bedrock:*::foundation-model/*",
                "arn:aws:bedrock:us-east-1::inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0",
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
                "arn:aws:lambda:us-east-1:618048437522:function:pf-scheduling-actions",
                "arn:aws:lambda:us-east-1:618048437522:function:pf-information-actions",
                "arn:aws:lambda:us-east-1:618048437522:function:pf-chitchat-actions"
            ]
        }
    ]
}
```

**Roles Updated:**
- AmazonBedrockExecutionRoleForAgents_Supervisor
- AmazonBedrockExecutionRoleForAgents_SchedulingAgent
- AmazonBedrockExecutionRoleForAgents_pf-information
- AmazonBedrockExecutionRoleForAgents_pf-chitchat

**Agents Re-prepared:** ✅ All agents prepared after policy update

### 5. Trust Relationships ✅

**Checked:** Supervisor role trust relationship
```json
{
    "Principal": {
        "Service": "bedrock.amazonaws.com"
    },
    "Condition": {
        "StringEquals": {
            "aws:SourceAccount": "618048437522"
        },
        "ArnLike": {
            "aws:SourceArn": "arn:aws:bedrock:us-east-1:618048437522:agent/*"
        }
    }
}
```

**Result:** Trust relationship correct - NOT the issue

### 6. Inference Profile Testing ✅

**Test 1:** Direct invocation with inference profile  
**Model ID:** `us.anthropic.claude-3-5-sonnet-20241022-v2:0`  
**Result:** ✅ SUCCESS

**Test 2:** Direct invocation with base model ID  
**Model ID:** `anthropic.claude-3-5-sonnet-20241022-v2:0`  
**Result:** ❌ FAILED - "Invocation of model ID ... with on-demand throughput isn't supported. Retry your request with the ID or ARN of an inference profile."

**Conclusion:** Must use inference profile (which we are)

## Current Status

### What Works ✅
- Direct Bedrock model invocation (bedrock-runtime:InvokeModel)
- Lambda function invocations (returns real project data)
- Agent list/get operations (bedrock-agent:GetAgent)
- Agent preparation (bedrock-agent:PrepareAgent)

### What Doesn't Work ❌
- Agent invocation (bedrock-agent-runtime:InvokeAgent)
- Error occurs when agent tries to call the foundation model
- Error is in the event stream response, not the initial invocation

## Possible Remaining Issues

### 1. Service-Linked Role
Bedrock Agents might require a service-linked role that hasn't been created:
```bash
aws iam create-service-linked-role --aws-service-name bedrock.amazonaws.com
```

### 2. Resource-Based Policy
The inference profile might need a resource-based policy allowing the agent role:
- This cannot be set via CLI/API
- May require AWS Console or AWS Support

### 3. IAM Policy Propagation Delay
- IAM changes can take up to 5-10 minutes to propagate
- Agent preparation might need to be done after delay

### 4. Regional Inference Profile Issue
- The inference profile `us.anthropic.claude-3-5-sonnet-20241022-v2:0` might not be fully enabled
- Try switching to a different model (Claude 3 Haiku or Claude 3 Sonnet)

### 5. Bedrock Agents Service Quota
- Account might have Bedrock Agents disabled or restricted
- Requires AWS Support ticket to enable

## Next Steps

1. **Wait for IAM propagation** (5-10 minutes) and retry
2. **Try different model:** Update agents to use `anthropic.claude-3-haiku-20240307-v1:0` (older, stable model)
3. **Check service-linked role:** Create if missing
4. **Enable CloudTrail:** Check detailed error logs for agent invocations
5. **AWS Support:** Open ticket if issue persists

## Commands to Retry

### Test Agent After Waiting
```bash
python3 << 'EOFPYTHON'
import boto3
import time

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
response = client.invoke_agent(
    agentId='PXGWN2EEBH',
    agentAliasId='TSTALIASID',
    sessionId=f'test-{int(time.time())}',
    inputText='hello',
    sessionState={'sessionAttributes': {'customer_id': '1645869', 'client_id': '09PF05VD'}}
)

for event in response['completion']:
    if 'chunk' in event and 'bytes' in event['chunk']:
        print(event['chunk']['bytes'].decode('utf-8'), end='')
EOFPYTHON
```

### Check Service-Linked Role
```bash
aws iam get-role --role-name AWSServiceRoleForBedrock 2>&1
```

### Create Service-Linked Role
```bash
aws iam create-service-linked-role --aws-service-name bedrock.amazonaws.com
```

## Files Updated

- `/tmp/bedrock-agent-policy-updated.json` - New policy with inference profile permissions
- All 4 agent IAM role policies updated
- All 4 agents re-prepared

## Verification Commands

```bash
# Check updated policy
aws iam get-role-policy --role-name "AmazonBedrockExecutionRoleForAgents_Supervisor" --policy-name "BedrockModelInvoke"

# Check agent status
aws bedrock-agent list-agents --region us-east-1 --query 'agentSummaries[].{Name:agentName,Status:agentStatus}'

# Test direct model invocation
python3 -c "import boto3; boto3.client('bedrock-runtime', region_name='us-east-1').invoke_model(modelId='us.anthropic.claude-3-5-sonnet-20241022-v2:0', body='{\"anthropic_version\":\"bedrock-2023-05-31\",\"max_tokens\":10,\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}')"
```

## Resolution Status

🟡 **In Progress** - IAM policies updated, agents re-prepared, awaiting propagation or further investigation
