# AWS Support Ticket - Enable On-Demand API Access for Claude Sonnet 4.5

## How to Submit This Ticket

1. Go to: https://console.aws.amazon.com/support/home
2. Click **"Create case"**
3. Select **"Technical Support"**
4. Fill in the details below

---

## Case Details

### Subject
```
Enable On-Demand API Access for Claude Sonnet 4.5 - Agent API Invocation Failing with 403
```

### Service
```
Amazon Bedrock
```

### Category
```
Model Access / Permissions
```

### Severity
```
System impaired (or appropriate severity for your use case)
```

---

## Case Description

Copy and paste this (update placeholders if needed):

```
Hello AWS Support Team,

I need assistance enabling full API access (on-demand throughput) for Claude Sonnet 4.5
in my AWS account. I currently have cross-region inference access enabled, but Bedrock
Agent API invocations are failing with 403 Access Denied errors.

ACCOUNT INFORMATION:
- Account ID: 618048437522
- Region: us-east-1
- IAM User: pfuser (has AdministratorAccess policy)

MODEL INFORMATION:
- Model Name: Claude Sonnet 4.5
- Model ID: anthropic.claude-sonnet-4-5-20250929-v1:0
- Inference Profile: us.anthropic.claude-sonnet-4-5-20250929-v1:0
- Current Access: Cross-region inference (enabled ✓)
- Needed Access: On-demand throughput / Base model API access

ISSUE DESCRIPTION:
I have deployed Bedrock Agents (multi-agent collaboration system) that use Claude Sonnet 4.5.

What WORKS:
✅ Direct model invocation via bedrock-runtime API (using inference profile)
✅ Agent testing in AWS Console UI
✅ Cross-region inference profile access is enabled

What FAILS:
❌ Agent invocation via bedrock-agent-runtime API
❌ Error: "Access denied when calling Bedrock. Check your request permissions"
❌ HTTP Status: 403 (accessDeniedException)

AGENT DETAILS:
- Supervisor Agent ID: 5VTIWONUMO
- Collaborator Agent IDs: IX24FSMTQH, C9ANXRIO8Y, G5BVBYEPUM, BIUW1ARHGL
- All agents configured with Claude Sonnet 4.5 (us.anthropic.claude-sonnet-4-5-20250929-v1:0)
- IAM roles have correct permissions (bedrock:InvokeModel, bedrock:InvokeModelWithResponseStream)

IAM PERMISSIONS VERIFIED:
- Agent roles have wildcard access to inference-profile/* and foundation-model/*
- Trust policies correctly configured for bedrock.amazonaws.com
- User has AdministratorAccess

INVESTIGATION COMPLETED:
1. Verified model invocation works directly:
   ✅ aws bedrock-runtime invoke-model --model-id us.anthropic.claude-sonnet-4-5-20250929-v1:0

2. Verified IAM permissions are correct for all agent roles

3. Checked Model Access page:
   - UI shows "Cross-region inference: Access granted" only
   - No option visible to enable "On-demand throughput"
   - Yellow banner indicates "Model access page retiring soon"
   - Account appears to be in transition to new auto-enable system

4. Tested multiple agent aliases and versions - all fail with same 403 error

ROOT CAUSE (Suspected):
The Model Access page shows only "Cross-region inference" access for all Anthropic models
in the Base models section. There is no UI option to enable "On-demand" access separately.

I believe my account is in a transition state between the old and new model access systems,
and I need manual enablement of on-demand/base model API access for agent use cases.

REQUEST:
Please enable full API access (on-demand throughput) for Claude Sonnet 4.5
(anthropic.claude-sonnet-4-5-20250929-v1:0) in us-east-1 region for account 618048437522.

This will allow my Bedrock Agents to invoke the model programmatically via the
bedrock-agent-runtime API.

BUSINESS IMPACT:
I am developing a multi-agent scheduling system for a property management company.
Console testing works fine for development, but I need programmatic API access for:
- Automated testing scripts
- Integration with backend systems
- Production deployment

ADDITIONAL NOTES:
- I have already updated all agent configurations to use Claude Sonnet 4.5
- All Terraform infrastructure is deployed correctly
- This is blocking transition from development (console) to production (API)

Please let me know if you need any additional information or diagnostics.

Thank you for your assistance!

Best regards,
[Your Name]
```

---

## Attachments (Optional but Helpful)

If you want to attach additional evidence, create these files:

### 1. Test Output
Run this and save output:
```bash
python3 /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/test_api_access.py > /tmp/api_test_output.txt 2>&1
```

### 2. IAM Policy Export
```bash
aws iam get-role-policy \
  --role-name scheduling-agent-supervisor-agent-role-dev \
  --policy-name scheduling-agent-supervisor-agent-policy \
  --output json > /tmp/supervisor_iam_policy.json
```

### 3. Agent Configuration
```bash
aws bedrock-agent get-agent \
  --agent-id 5VTIWONUMO \
  --region us-east-1 \
  --output json > /tmp/supervisor_agent_config.json
```

---

## Expected Response Time

- **General guidance**: 12-24 hours
- **System impaired**: 4-12 hours
- **Production system down**: 1-4 hours

---

## Follow-up Actions After Resolution

Once AWS Support enables access, run:

```bash
# Wait 5-10 minutes after confirmation, then test:
python3 /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/test_api_access.py
```

You should see:
```
✅ PASS  Direct Model
✅ PASS  Agent
✅ PASS  Supervisor

🎉 ALL TESTS PASSED!
Your agents are ready to use via API!
```

---

## Alternative: Escalation Path

If the first support engineer doesn't resolve it, ask to:

1. **Escalate to Bedrock Specialist**: "Can this be escalated to someone with Bedrock model access expertise?"

2. **Reference AWS Documentation**: The AWS docs mention needing "model access" for agents - you have it for console but not API

3. **Request Account Configuration Audit**: "Can you verify my account's model entitlements match what's required for bedrock-agent-runtime API calls?"

---

## Questions Support Might Ask

**Q: Have you checked IAM permissions?**
A: Yes, verified. Agent roles have bedrock:InvokeModel with wildcard resources. Direct model invocation works.

**Q: Can you test in console?**
A: Yes, console testing works perfectly. Only API invocation fails.

**Q: What error do you see?**
A: "accessDeniedException: Access denied when calling Bedrock" (HTTP 403)

**Q: Have you enabled model access?**
A: Yes, for cross-region inference profiles. But base model on-demand access is not available in the UI to enable.

**Q: Can you provide agent ID?**
A: Supervisor: 5VTIWONUMO, collaborators in case description above.

---

**Status**: Ready to submit
**Priority**: Medium to High (blocking production deployment)
**Estimated Resolution**: 4-24 hours depending on severity level chosen

---

Good luck! Let me know if you need any clarification on the ticket details.
