# 403 Access Denied Error - Resolution

**Issue:** Agent API invocation failing with 403 access denied
**Date Reported:** October 12, 2025
**Date Resolved:** October 13, 2025
**Status:** ✅ RESOLVED

---

## Problem Summary

Bedrock Agents were successfully working in the AWS Console UI, but API invocations via `bedrock-agent-runtime` API were failing with:

```
Access denied when calling Bedrock. Check your request permissions
HTTP Status: 403 (accessDeniedException)
```

### What Was Working

- ✅ Direct model invocation via `bedrock-runtime` API (using inference profile)
- ✅ Agent testing in AWS Console UI
- ✅ Cross-region inference profile access enabled
- ✅ Agent roles had wildcard access to `inference-profile/*` and `foundation-model/*`

### What Was Failing

- ❌ Agent invocation via `bedrock-agent-runtime` API
- ❌ Supervisor agent invocation via API
- ❌ Programmatic agent testing

---

## Root Cause Analysis

AWS Support identified the issue by examining CloudTrail logs. The error message revealed:

```
errorMessage: User: arn:aws:sts::618048437522:assumed-role/scheduling-agent-supervisor-agent-role-dev/BedrockAgents-5VTIWONUMO-1f4c33b8-3a69-42be-bae0-c3e8d43a231a
is not authorized to perform: bedrock:InvokeModel
on resource: arn:aws:bedrock:us-east-2::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0
because no identity-based policy allows the bedrock:InvokeModel action
```

**Key Insight:** Notice the region in the error - `us-east-2`, not `us-east-1`.

### Cross-Region Inference Behavior

According to AWS documentation: https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html

The "US Anthropic Claude Sonnet 4.5" inference profile in `us-east-1` can route requests to **any of these regions**:
- us-east-1
- us-east-2
- us-west-2

### The Problem

Our IAM policies only granted permissions to resources in `us-east-1`:

```hcl
resources = [
  "arn:aws:bedrock:us-east-1::foundation-model/*",
  "arn:aws:bedrock:us-east-1:${account_id}:inference-profile/*"
]
```

When cross-region inference routed a request to `us-east-2` or `us-west-2`, the agent's IAM role **did not have permission** to invoke the model in those regions → 403 error.

### Why Console Worked

The AWS Console test interface likely uses different execution paths or has additional permissions that handle cross-region inference transparently.

---

## Solution

Update IAM policies for all agent roles to include foundation model permissions in **all three US regions** where cross-region inference can route:

```hcl
resources = [
  # us-east-1 (primary)
  "arn:aws:bedrock:us-east-1::foundation-model/*",
  "arn:aws:bedrock:us-east-1:${account_id}:inference-profile/*",

  # us-east-2 (cross-region)
  "arn:aws:bedrock:us-east-2::foundation-model/*",

  # us-west-2 (cross-region)
  "arn:aws:bedrock:us-west-2::foundation-model/*"
]
```

---

## Implementation

### Files Changed

**`infrastructure/terraform/bedrock_agents.tf`**

#### 1. Supervisor Agent Policy (Lines 139-158)

```hcl
# Policy for supervisor agent to invoke foundation model
data "aws_iam_policy_document" "supervisor_agent_permissions" {
  statement {
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream"
    ]
    resources = [
      # Allow access to the specific inference profile in us-east-1
      "arn:aws:bedrock:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:inference-profile/${var.foundation_model}",
      # Also allow access to all inference profiles (needed for cross-region inference)
      "arn:aws:bedrock:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:inference-profile/*",
      # Allow access to foundation models in ALL US regions (cross-region inference requirement)
      # Cross-region inference for US Anthropic Claude Sonnet 4.5 can route to: us-east-1, us-east-2, us-west-2
      "arn:aws:bedrock:us-east-1::foundation-model/*",
      "arn:aws:bedrock:us-east-2::foundation-model/*",
      "arn:aws:bedrock:us-west-2::foundation-model/*"
    ]
  }
  # ... additional statements ...
}
```

#### 2. Collaborator Agent Policy (Lines 228-247)

```hcl
# Policy for collaborator agents to invoke foundation model
data "aws_iam_policy_document" "collaborator_agent_permissions" {
  statement {
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream"
    ]
    resources = [
      # Allow access to the specific inference profile in us-east-1
      "arn:aws:bedrock:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:inference-profile/${var.foundation_model}",
      # Also allow access to all inference profiles (needed for cross-region inference)
      "arn:aws:bedrock:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:inference-profile/*",
      # Allow access to foundation models in ALL US regions (cross-region inference requirement)
      # Cross-region inference for US Anthropic Claude Sonnet 4.5 can route to: us-east-1, us-east-2, us-west-2
      "arn:aws:bedrock:us-east-1::foundation-model/*",
      "arn:aws:bedrock:us-east-2::foundation-model/*",
      "arn:aws:bedrock:us-west-2::foundation-model/*"
    ]
  }
  # ... additional statements ...
}
```

### Terraform Apply

```bash
cd infrastructure/terraform
terraform plan -out=tfplan
terraform apply tfplan
```

**Result:** All 5 agent IAM role policies updated successfully:
- ✅ supervisor_agent_permissions
- ✅ scheduling_agent_permissions
- ✅ information_agent_permissions
- ✅ notes_agent_permissions
- ✅ chitchat_agent_permissions

---

## Testing

### Test Script

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
python3 tests/test_api_access.py
```

### Results (After Fix)

```
======================================================================
TEST SUMMARY
======================================================================
✅ PASS  Direct Model
✅ PASS  Agent
✅ PASS  Supervisor

🎉 ALL TESTS PASSED!
Your agents are ready to use via API!
```

### Individual Test Results

**Test 1: Direct Model Invocation**
```
✅ SUCCESS
Response: Hello from direct invocation!
```

**Test 2: Agent Invocation (Chitchat Agent)**
```
✅ SUCCESS - Agent invocation works!
Agent Response: Hello! I'm here to help you schedule appointments...
```

**Test 3: Supervisor Agent Invocation**
```
✅ SUCCESS - Supervisor agent works!
Supervisor Response: Hello! I'm doing great, thanks for asking!...
```

---

## Lessons Learned

### 1. Cross-Region Inference is Not Obvious

When using inference profiles, AWS automatically routes requests to different regions for load balancing and availability. This is great for resilience but requires IAM permissions in **all potential target regions**, not just the primary region.

### 2. Console UI Hides Complexity

The AWS Console test interface "just works" because it likely has broader permissions or handles cross-region routing differently. API invocations require explicit IAM permissions.

### 3. CloudTrail is Essential for Debugging

Without CloudTrail logs, we would not have discovered that the failure was occurring in `us-east-2` rather than `us-east-1`. The error message from the API was too generic.

### 4. Documentation is Region-Specific

AWS Bedrock inference profile documentation clearly states which regions are used for cross-region inference. Always check:
https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html

---

## Prevention for Future Models

When adding new models or inference profiles, always:

1. **Check the inference profile documentation** to see which regions are used for cross-region routing
2. **Update IAM policies** to include all potential target regions
3. **Test via API** (not just console) to verify permissions are correct

### Recommended IAM Policy Pattern

For any US-based inference profile, use this pattern:

```hcl
resources = [
  # Primary region inference profiles
  "arn:aws:bedrock:${local.region}:${local.account_id}:inference-profile/*",

  # Foundation models in ALL US regions (for cross-region inference)
  "arn:aws:bedrock:us-east-1::foundation-model/*",
  "arn:aws:bedrock:us-east-2::foundation-model/*",
  "arn:aws:bedrock:us-west-2::foundation-model/*"
]
```

For **global** or **EU-based** inference profiles, adjust regions accordingly:
- EU: `eu-west-1`, `eu-west-2`, `eu-central-1`
- Asia: `ap-northeast-1`, `ap-southeast-1`, `ap-southeast-2`

---

## AWS Support Case Details

**Case ID:** [Not provided in message]
**AWS Support Engineer:** Santosh S.
**Date:** October 13, 2025
**Response Time:** ~24 hours

### AWS Support Findings

1. Identified the exact IAM error from CloudTrail logs
2. Noted the request was routed to `us-east-2` (not `us-east-1`)
3. Recommended adding permissions for us-east-2 and us-west-2
4. Provided specific resource ARNs to add

### Recommended Solution from AWS

```
Edit the policy attached to IAM role "scheduling-agent-supervisor-agent-role-dev"
Add permissions to InvokeModel in us-east-2 and us-west-2 region similar to
the existing us-east-1 model permission.

Optionally restrict to specific models:
  * arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0
  * arn:aws:bedrock:us-east-2::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0
  * arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0
```

---

## References

### AWS Documentation

- **Inference Profiles**: https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html
- **Cross-Region Inference**: https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html
- **IAM for Bedrock**: https://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html

### Related Documents

- **[ENABLE_API_ACCESS.md](./ENABLE_API_ACCESS.md)** - Original troubleshooting document
- **[AWS_SUPPORT_TICKET.md](./AWS_SUPPORT_TICKET.md)** - Support ticket template used
- **[DEPLOYMENT_STATUS.md](../DEPLOYMENT_STATUS.md)** - Current deployment status

### CloudTrail Query

To view the error logs:
```
https://us-east-1.console.aws.amazon.com/cloudtrail/home?region=us-east-1#/events?StartTime=2025-10-12T09:01:50.103Z&EndTime=2025-10-13T09:01:50.103Z&EventName=Converse
```

Filter by:
- Event name: `Converse`
- Error code: `AccessDeniedException`
- User: `scheduling-agent-supervisor-agent-role-dev`

---

## Timeline

| Date | Event |
|------|-------|
| **Oct 12, 2025** | Issue reported - 403 errors on agent API invocations |
| **Oct 12, 2025** | AWS Support case opened |
| **Oct 12, 2025** | Created `ENABLE_API_ACCESS.md` and `AWS_SUPPORT_TICKET.md` |
| **Oct 13, 2025** | AWS Support response received with root cause analysis |
| **Oct 13, 2025** | Terraform IAM policies updated with cross-region permissions |
| **Oct 13, 2025** | Terraform apply completed successfully |
| **Oct 13, 2025** | All API tests passing ✅ |
| **Oct 13, 2025** | Issue documented in this file |

---

## Verification Checklist

Before closing this issue, verify:

- [x] CloudTrail shows no more `AccessDeniedException` errors for Converse API
- [x] All 5 agent IAM policies updated with cross-region permissions
- [x] test_api_access.py passes all 3 tests
- [x] Direct model invocation works
- [x] Collaborator agent invocation works
- [x] Supervisor agent invocation works
- [x] Documentation updated
- [x] Terraform state reflects changes

---

**Status:** ✅ RESOLVED
**Final Verification:** October 13, 2025
**Verified By:** Development Team

All agent API invocations are now working correctly via `bedrock-agent-runtime` API.
