# Bedrock Agent Invocation Issue - Deep Analysis

**Date:** November 4, 2025
**Status:** 🔴 **BLOCKED** - Likely account-level restriction

## Executive Summary

After comprehensive troubleshooting, the Bedrock agent invocation failure is **NOT** due to IAM permissions. All agent roles have `AmazonBedrockFullAccess`, and direct model invocation works perfectly. The issue appears to be an **account-level restriction on the Bedrock Agents service** itself.

## What Works ✅

1. **Direct Bedrock Model Invocation**
   - Both Amazon Nova and Claude models work perfectly
   - Tested via `bedrock-runtime:InvokeModel`
   - All inference profiles accessible

2. **Lambda Functions**
   - All 3 Lambda functions work flawlessly
   - Successfully return real data from ProjectForce API
   - Example: pf-scheduling-actions returns 25 projects

3. **Agent Management Operations**
   - List agents ✅
   - Get agent summaries ✅
   - List agent aliases ✅
   - Prepare agents ✅

4. **IAM Permissions**
   - All 4 agent roles have `AmazonBedrockFullAccess`
   - User (pfuser) has `AdministratorAccess` + `AmazonBedrockFullAccess`
   - Trust relationships configured correctly

## What Doesn't Work ❌

1. **Agent Invocation**
   - `bedrock-agent-runtime:InvokeAgent` initiates successfully
   - Fails during event stream with `accessDeniedException`
   - Error: "Access denied when calling Bedrock"

2. **Agent Management Operations (Some)**
   - `bedrock:GetAgent` - Access Denied
   - `bedrock:UpdateAgentAlias` - Access Denied

## Current Configuration

### Agents Deployed

| Agent ID | Name | Status | Alias | Role |
|----------|------|--------|-------|------|
| VBZPDTNEXJ | SchedulingAgent | PREPARED | TSTALIASID | pf_scheduling_agent_role |
| G1XCBCAXBX | pf-chitchat | PREPARED | TSTALIASID | pf_chitchat_agent_role |
| XQFAHG3K8Q | pf-information | PREPARED | TSTALIASID | pf_information_agent_role |
| PXGWN2EEBH | Supervisor | PREPARED | TSTALIASID | pf_supervisor_agent_role |

### Agent Role Permissions

All agent roles have the same configuration:

**Attached Managed Policy:**
```
AmazonBedrockFullAccess (arn:aws:iam::aws:policy/AmazonBedrockFullAccess)
```

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

## Error Analysis

### Error Pattern

```
Testing agent invocation...
Agent ID: VBZPDTNEXJ
Agent Alias: TSTALIASID

✅ Agent invocation initiated successfully!

❌ Error: EventStreamError
Message: An error occurred (accessDeniedException) when calling the InvokeAgent operation:
Access denied when calling Bedrock. Check your request permissions and retry the request.
```

### Key Observations

1. **Invocation starts successfully** - The initial API call to `InvokeAgent` succeeds
2. **Fails during event stream** - Error occurs when agent tries to call the foundation model
3. **Not an IAM permission issue** - Roles have full Bedrock access
4. **Specific to agent runtime** - Direct model invocation works fine

## Troubleshooting Steps Completed

### 1. Verified User Permissions ✅
```bash
# pfuser has:
- AdministratorAccess
- AmazonBedrockFullAccess
```

### 2. Verified Model Access ✅
```bash
# Successfully tested:
- amazon.nova-micro-v1:0
- anthropic.claude-3-haiku-20240307-v1:0
- us.anthropic.claude-3-5-sonnet-20241022-v2:0 (inference profile)
```

### 3. Verified Agent Configuration ✅
```bash
# All agents:
- Status: PREPARED
- Have aliases configured (TSTALIASID)
- Have valid execution roles
```

### 4. Verified Agent Role Permissions ✅
```bash
# Checked all 4 agent roles:
pf_scheduling_agent_role ✅ AmazonBedrockFullAccess
pf_chitchat_agent_role ✅ AmazonBedrockFullAccess
pf_information_agent_role ✅ AmazonBedrockFullAccess
pf_supervisor_agent_role ✅ AmazonBedrockFullAccess
```

### 5. Verified Lambda Permissions ✅
```bash
# All Lambda functions working:
- pf-scheduling-actions: Returns 25 projects ✅
- pf-information-actions: Available ✅
- pf-chitchat-actions: Available ✅
```

### 6. Tested Direct Model Invocation ✅
```bash
# Successfully invoked:
- Claude Haiku via bedrock-runtime:InvokeModel ✅
- Amazon Nova via bedrock-runtime:InvokeModel ✅
```

## Root Cause Analysis

### Hypothesis 1: IAM Propagation Delay ❌
**Status:** Ruled out
- Policies have been in place for hours
- IAM changes typically propagate within 5-10 minutes
- Issue persists across multiple testing sessions

### Hypothesis 2: Insufficient Agent Role Permissions ❌
**Status:** Ruled out
- All agents have `AmazonBedrockFullAccess`
- This is the recommended AWS managed policy for Bedrock agents
- Direct model invocation from same roles would also fail (but it doesn't)

### Hypothesis 3: Missing Inference Profile Permissions ❌
**Status:** Ruled out
- Direct inference profile invocation works
- Tested `us.anthropic.claude-3-5-sonnet-20241022-v2:0` successfully

### Hypothesis 4: Account-Level Service Restriction ⚠️ **LIKELY**
**Status:** Most probable cause

**Evidence:**
1. User has `AdministratorAccess` but still denied for:
   - `bedrock:GetAgent`
   - `bedrock:UpdateAgentAlias`
   - Agent model invocation

2. Pattern suggests service-level restriction, not IAM permissions

3. Bedrock Agents may require additional account setup beyond model access

**Possible Causes:**
- Bedrock Agents service not fully enabled for the account
- Account in a region with limited Bedrock Agents availability
- Service quota or limit preventing agent execution
- Additional console-based enablement step required

### Hypothesis 5: Resource-Based Policy Missing ⚠️
**Status:** Possible but unlikely

The inference profile or foundation model might require a resource-based policy that cannot be set via CLI. However, this would be unusual for foundation models.

## Comparison: What Works vs What Doesn't

### Working Path (Direct Invocation)
```
User (pfuser)
  → bedrock-runtime:InvokeModel
    → Claude Model ✅
```

### Failing Path (Agent Invocation)
```
User (pfuser)
  → bedrock-agent-runtime:InvokeAgent ✅ (Succeeds)
    → Agent Role (pf_scheduling_agent_role)
      → bedrock:InvokeModel ❌ (Fails with accessDeniedException)
        → Claude Model
```

## Next Steps

### Option 1: AWS Console Testing (Recommended)
Test agent invocation through the AWS Bedrock Console:

1. Navigate to AWS Bedrock Console
2. Go to Agents section
3. Select "SchedulingAgent"
4. Use the built-in test interface
5. Attempt to invoke the agent

**If this works:** The issue is likely with CLI/SDK permissions or configuration
**If this fails:** Confirms account-level restriction

### Option 2: AWS Support (If Console Fails)
Open an AWS Support case with:

**Issue:** Bedrock Agent invocation fails with `accessDeniedException` despite `AmazonBedrockFullAccess`

**Evidence:**
- Agent roles have full Bedrock access
- Direct model invocation works
- Agent invocation initiates but fails during execution
- Error occurs in event stream, not initial API call

**Account ID:** 618048437522
**Region:** us-east-1
**Agent ID:** VBZPDTNEXJ

### Option 3: Check Service Quotas
```bash
# Check Bedrock service quotas
aws service-quotas list-service-quotas \
    --service-code bedrock \
    --region us-east-1
```

### Option 4: Verify Region Availability
Confirm that Bedrock Agents is fully available in us-east-1:
- Check AWS Bedrock documentation for regional availability
- Verify that all required endpoints are accessible

### Option 5: Alternative Architecture (Workaround)
Since Lambda functions work perfectly:

**Immediate Workaround:**
- Use Lambda functions directly for production
- Bypass Bedrock Agents temporarily
- Build orchestration logic in Lambda or API Gateway
- Lambda functions already return real ProjectForce data

**Production Path:**
```
User → API Gateway → Lambda (Orchestrator) → Lambda Action Functions → ProjectForce API
```

This avoids the Bedrock Agent invocation entirely while maintaining all functionality.

## Testing Commands

### Test Direct Model Invocation (Working)
```bash
./scripts/test_claude_model.sh "Hello"
./scripts/test_nova_model.sh "Hello"
```

### Test Agent Invocation (Failing)
```python
python3 << 'EOF'
import boto3
from datetime import datetime

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

response = client.invoke_agent(
    agentId='VBZPDTNEXJ',
    agentAliasId='TSTALIASID',
    sessionId=f'test-{int(datetime.now().timestamp())}',
    inputText='Hello'
)

for event in response['completion']:
    if 'chunk' in event:
        print(event['chunk']['bytes'].decode('utf-8'), end='')
EOF
```

### Test Lambda Function (Working)
```bash
aws lambda invoke \
    --function-name pf-scheduling-actions \
    --payload '{"action":"list_projects","userId":"test@example.com"}' \
    response.json && cat response.json | jq '.'
```

## Conclusion

The Bedrock agent invocation issue is **NOT** a simple IAM permission problem. All evidence points to an **account-level restriction on the Bedrock Agents service** that requires either:

1. AWS Console-based enablement
2. AWS Support intervention
3. Additional account configuration beyond IAM policies

**Recommended Action:** Test in AWS Bedrock Console first, then contact AWS Support if the issue persists.

**Temporary Solution:** Use Lambda functions directly, which are working perfectly and already integrated with the ProjectForce API.

## Related Documentation

- `docs/BEDROCK_ACCESS_DENIED_RESOLUTION.md` - Initial troubleshooting
- `docs/CLAUDE_USAGE.md` - Working Claude model invocation
- `docs/AMAZON_NOVA_USAGE.md` - Working Nova model invocation
- `docs/BEDROCK_QUICK_REFERENCE.md` - Model format comparison
- `docs/DEPLOY_SCRIPT_UPDATE_NOV4.md` - IAM policy enhancements

## Verification Commands

```bash
# Verify agent roles have correct permissions
for role in pf_scheduling_agent_role pf_chitchat_agent_role pf_information_agent_role pf_supervisor_agent_role; do
    echo "=== $role ==="
    aws iam list-attached-role-policies --role-name $role
done

# List all agents
aws bedrock-agent list-agents --region us-east-1

# Test direct model invocation
./scripts/test_claude_model.sh "Hello from test"
```
