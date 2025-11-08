# Terraform Collaboration Setup Guide

## Overview

This guide shows how to set up **AWS Bedrock Multi-Agent Collaboration** using Terraform's `aws_bedrockagent_agent_collaborator` resource. This is the **proper, production-ready approach** for supervisor routing.

## Architecture

```
User Request
    ↓
Supervisor Agent (ZZNSFE74NB)
    ↓ [AWS Bedrock handles routing internally]
    ├─→ SchedulingAgent (v1 alias)  → Lambda: pf-scheduling-actions
    ├─→ InformationAgent (v1 alias) → Lambda: pf-information-actions
    └─→ ChitchatAgent (v1 alias)    → No Lambda (conversational)
```

---

## Why This Approach vs Frontend Routing

| Feature | Terraform Collaboration | Frontend Routing |
|---------|------------------------|------------------|
| **Routing** | AWS Bedrock (native) | Your code (Claude classification) |
| **Setup** | Terraform declarative | Python backend code |
| **Maintenance** | Infrastructure as code | Application code changes |
| **Scalability** | Native AWS optimization | Custom implementation |
| **Observability** | AWS CloudWatch metrics | Custom logging |
| **Cost** | Higher (supervisor + collaborator invocations) | Lower (classification + direct invocation) |

**Recommendation**: Use Terraform collaboration for production AWS-native setup.

---

## Prerequisites

✅ **You already have:**
1. All 4 agents deployed:
   - Supervisor: ZZNSFE74NB
   - SchedulingAgent: XWYHPGTXFC
   - pf-information: YPHTBWTHU8
   - pf-chitchat: 2VRYB01FGD

2. Lambda functions deployed and working:
   - pf-scheduling-actions
   - pf-information-actions

3. Terraform infrastructure in `infrastructure/terraform/`

⚠️ **What's missing:**
- Version 1 (v1) aliases for the 3 collaborator agents (must be created via Console)

---

## Step-by-Step Setup

### Step 1: Create v1 Aliases in AWS Console (One-Time, ~15 minutes)

**Why Console is Required:**
- AWS CLI has no `create-agent-version` command
- Terraform AWS provider (v6.17.0) has no `aws_bedrockagent_agent_version` resource
- This is an AWS platform limitation during preview

**Follow these steps for EACH of the 3 collaborator agents:**

#### For SchedulingAgent (XWYHPGTXFC):

1. Open: https://console.aws.amazon.com/bedrock/
2. Region: **us-east-1** (top-right)
3. Click: **Agents** (left sidebar)
4. Find and click: **SchedulingAgent** (ID: XWYHPGTXFC)

5. **Create Version:**
   - Click "Working draft" dropdown at top
   - Click "Create version" button
   - Dialog: "Create version 1?"
   - Click "Create version"
   - Wait ~30 seconds for "Version 1" status: "Available"

6. **Create Alias:**
   - Click "Aliases" tab (near top)
   - Click "Create alias" button
   - Alias name: `v1`
   - Description: `Production alias for Supervisor collaboration`
   - Agent version: Select **"1"** (the version you just created)
   - Click "Create alias"
   - **Copy the Alias ID** (10-character code like "ABC1DEF2G3")

#### Repeat for pf-information (YPHTBWTHU8):

1. Click on "pf-information"
2. Create version → Version 1
3. Create alias → Name: `v1`, Version: 1
4. Copy the Alias ID

#### Repeat for pf-chitchat (2VRYB01FGD):

1. Click on "pf-chitchat"
2. Create version → Version 1
3. Create alias → Name: `v1`, Version: 1
4. Copy the Alias ID

---

### Step 2: Find v1 Alias IDs (Automated)

Once you've created the v1 aliases in Console, run:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
./scripts/find_v1_alias_ids.sh
```

**Expected output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scheduling Agent (XWYHPGTXFC)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ v1 alias found

Alias ID:  ABC1DEF2G3
Alias ARN: arn:aws:bedrock:us-east-1:618048437522:agent-alias/XWYHPGTXFC/ABC1DEF2G3
Points to: Version 1
...
```

Save these Alias IDs - you'll need them in Step 3.

---

### Step 3: Update Terraform Configuration

Edit `infrastructure/terraform/collaboration.tf` and replace `V1_ALIAS_ID_HERE` with actual alias IDs:

**Before:**
```hcl
agent_descriptor {
  alias_arn = "arn:aws:bedrock:${local.region}:${local.account_id}:agent-alias/${local.scheduling_id}/V1_ALIAS_ID_HERE"
}
```

**After (example):**
```hcl
agent_descriptor {
  alias_arn = "arn:aws:bedrock:${local.region}:${local.account_id}:agent-alias/${local.scheduling_id}/ABC1DEF2G3"
}
```

**Update all 3 resources:**
- `aws_bedrockagent_agent_collaborator.scheduling` → Scheduling alias ID
- `aws_bedrockagent_agent_collaborator.information` → Information alias ID
- `aws_bedrockagent_agent_collaborator.chitchat` → Chitchat alias ID

---

### Step 4: Apply Terraform

```bash
cd infrastructure/terraform

# Preview changes
terraform plan

# Apply collaboration configuration
terraform apply
```

**Expected output:**
```
Plan: 3 to add, 0 to change, 0 to destroy

aws_bedrockagent_agent_collaborator.scheduling: Creating...
aws_bedrockagent_agent_collaborator.information: Creating...
aws_bedrockagent_agent_collaborator.chitchat: Creating...

aws_bedrockagent_agent_collaborator.scheduling: Creation complete
aws_bedrockagent_agent_collaborator.information: Creation complete
aws_bedrockagent_agent_collaborator.chitchat: Creation complete

Apply complete! Resources: 3 added, 0 changed, 0 destroyed.
```

---

### Step 5: Verify Collaboration

Run the verification script:

```bash
./scripts/verify_collaborators.sh
```

**Or manually:**
```bash
aws bedrock-agent list-agent-collaborators \
  --agent-id ZZNSFE74NB \
  --agent-version DRAFT \
  --region us-east-1 \
  --query 'agentCollaboratorSummaries[*].[collaboratorName,agentDescriptor.aliasArn]' \
  --output table
```

**Expected output:**
```
---------------------------------------------------------------------------
|                        ListAgentCollaborators                          |
+---------------------+--------------------------------------------------+
|  SchedulingAgent    |  arn:aws:bedrock:us-east-1:...:agent-alias/...  |
|  InformationAgent   |  arn:aws:bedrock:us-east-1:...:agent-alias/...  |
|  ChitchatAgent      |  arn:aws:bedrock:us-east-1:...:agent-alias/...  |
+---------------------+--------------------------------------------------+
```

---

### Step 6: Prepare Supervisor Agent

The Supervisor needs to be prepared after collaboration is configured:

```bash
aws bedrock-agent prepare-agent \
  --agent-id ZZNSFE74NB \
  --region us-east-1
```

Wait 30-60 seconds for preparation to complete.

---

### Step 7: Test Supervisor Routing

Test that the Supervisor correctly routes to specialist agents:

**Test 1: Routing to SchedulingAgent**
```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id ZZNSFE74NB \
  --agent-alias-id TSTALIASID \
  --session-id test-$(date +%s) \
  --session-state '{"sessionAttributes":{"customer_id":"1645869","client_id":"09PF05VD"}}' \
  --input-text "List my projects" \
  /tmp/supervisor_projects.txt

cat /tmp/supervisor_projects.txt
```

**Expected:** Should show project list from Lambda function

**Test 2: Routing to InformationAgent**
```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id ZZNSFE74NB \
  --agent-alias-id TSTALIASID \
  --session-id test-$(date +%s) \
  --input-text "What's the weather in New York?" \
  /tmp/supervisor_weather.txt

cat /tmp/supervisor_weather.txt
```

**Test 3: Routing to ChitchatAgent**
```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id ZZNSFE74NB \
  --agent-alias-id TSTALIASID \
  --session-id test-$(date +%s) \
  --input-text "Hello, how are you?" \
  /tmp/supervisor_hello.txt

cat /tmp/supervisor_hello.txt
```

---

## Troubleshooting

### "v1 aliases not found"
**Solution:** Complete Step 1 (Console setup) first

### "ValidationException: Agent cannot collaborate with TSTALIASID"
**Solution:** You're still using TSTALIASID in Terraform. Update to v1 alias ARNs.

### "Function calls not executing" (shows XML text)
**Known Issue:** AWS Bedrock platform bug with collaborator function execution
- See: `docs/ROUTING_COMPARISON.md` for details
- This is why frontend routing exists as a fallback
- May be resolved in future AWS updates

### Collaborators not routing correctly
**Check:**
1. Supervisor prepared: `aws bedrock-agent prepare-agent --agent-id ZZNSFE74NB`
2. Session attributes included: `customer_id`, `client_id`
3. Lambda permissions correct: Check CloudWatch logs

---

## Architecture After Setup

```
Supervisor Agent (ZZNSFE74NB)
├── Uses: TSTALIASID (for runtime invocation)
├── Collaborators (configured in DRAFT):
│   ├── SchedulingAgent → v1 alias → Version 1 → Lambda: pf-scheduling-actions
│   ├── InformationAgent → v1 alias → Version 1 → Lambda: pf-information-actions
│   └── ChitchatAgent → v1 alias → Version 1 → No Lambda (conversational)
└── Routes queries automatically based on intent
```

**Key Insight:**
- **TSTALIASID** → Used to INVOKE the Supervisor (points to Supervisor's DRAFT)
- **v1 aliases** → Used for COLLABORATION (point to specialist agents' Version 1)

---

## Maintenance

### To Update Agent Instructions:

1. Update instructions in `agent_instructions/*.txt`
2. Run DEPLOY.sh to update DRAFT
3. Create new version (v2) in Console
4. Update v1 alias to point to v2 (or create v2 alias)
5. Update Terraform collaboration.tf if using new alias
6. Run `terraform apply`
7. Prepare supervisor: `aws bedrock-agent prepare-agent --agent-id ZZNSFE74NB`

### To Add New Collaborator:

1. Create new agent via DEPLOY.sh or Terraform
2. Create Version 1 and v1 alias in Console
3. Add new `aws_bedrockagent_agent_collaborator` resource in collaboration.tf
4. Run `terraform apply`
5. Prepare supervisor

---

## Files Created/Modified

```
infrastructure/terraform/collaboration.tf  ← New: Terraform collaboration config
scripts/find_v1_alias_ids.sh              ← New: Helper to find alias IDs
scripts/associate_collaborators_with_v1.sh ← Existing: CLI alternative
scripts/verify_collaborators.sh            ← Existing: Verification
ENABLE_COLLABORATION.md                    ← Existing: Console instructions
TERRAFORM_COLLABORATION_GUIDE.md           ← This file
```

---

## Summary

✅ **What's Automated:**
- Agent creation (Terraform/DEPLOY.sh)
- Lambda deployment (DEPLOY.sh)
- Collaboration association (Terraform)
- Verification (scripts)

⚠️ **What Requires Console (One-Time):**
- Creating agent versions (AWS API limitation)
- Creating v1 aliases pointing to versions

Once v1 aliases exist, Terraform manages everything declaratively!

---

**Next Steps:**
1. Follow Step 1 to create v1 aliases in Console (~15 minutes)
2. Run `./scripts/find_v1_alias_ids.sh` to get alias IDs
3. Update `infrastructure/terraform/collaboration.tf` with alias IDs
4. Run `terraform apply`
5. Test supervisor routing

---

_Last Updated: November 4, 2025_
_Current Agent IDs: XWYHPGTXFC (Scheduling), YPHTBWTHU8 (Information), 2VRYB01FGD (Chitchat), ZZNSFE74NB (Supervisor)_
