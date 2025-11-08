# Enable Agent Collaboration - Step-by-Step Guide

## Current Status

✅ **All infrastructure deployed successfully:**
- 4 Bedrock agents created and prepared
- 2 Lambda functions with correct permissions
- DEPLOY.sh includes collaboration configuration code
- CLI script ready: `scripts/associate_collaborators_with_v1.sh`

⚠️ **Collaboration blocked - Requires AWS Console:**
- TSTALIASID cannot be used for collaboration (AWS restriction)
- No CLI/Terraform command exists to create agent versions
- Must use AWS Bedrock Console (one-time setup, ~15 minutes)

---

## Why Console is Required

AWS Bedrock has three ways to create resources:
1. **AWS CLI** - ❌ No `create-agent-version` command exists
2. **Terraform** - ❌ No `aws_bedrockagent_agent_version` resource type
3. **AWS Console** - ✅ Only method that can create agent versions

**This is an AWS platform limitation, not a configuration issue.**

---

## Step-by-Step Instructions

### Prerequisites
- AWS Console access to account `618048437522`
- Region: `us-east-1`
- Permissions: `bedrock:*` or `BedrockFullAccess`

### Step 1: Open AWS Bedrock Console

Navigate to: https://console.aws.amazon.com/bedrock/

1. **Select region:** us-east-1 (top-right corner)
2. **Click:** "Agents" in the left sidebar
3. You should see 4 agents:
   - SchedulingAgent (XWYHPGTXFC)
   - pf-information (YPHTBWTHU8)
   - pf-chitchat (2VRYB01FGD)
   - Supervisor (ZZNSFE74NB)

### Step 2: Create Version & Alias for SchedulingAgent

1. **Click** on "SchedulingAgent" to open agent details
2. **Click** the "Working draft" dropdown at the top
3. **Click** "Create version" button
   - A dialog appears: "Create version 1?"
   - **Click** "Create version"
   - Wait ~30 seconds for version creation to complete
   - You'll see "Version 1" created with status "Available"

4. **Click** "Aliases" tab (near the top)
5. **Click** "Create alias" button
   - Alias name: `v1`
   - Description: `Production alias for Supervisor collaboration`
   - Agent version: Select **"1"** (the version you just created)
   - **Click** "Create alias"
6. **Copy the Alias ID** (10-character code, e.g., "A1B2C3D4E5")
   - You'll need this, but the script can also find it automatically

### Step 3: Create Version & Alias for pf-information

Repeat Step 2 for **pf-information** (YPHTBWTHU8):
1. Click on "pf-information"
2. Create version →  Version 1
3. Create alias → Name: `v1`, Version: 1
4. Copy the Alias ID

### Step 4: Create Version & Alias for pf-chitchat

Repeat Step 2 for **pf-chitchat** (2VRYB01FGD):
1. Click on "pf-chitchat"
2. Create version → Version 1
3. Create alias → Name: `v1`, Version: 1
4. Copy the Alias ID

### Step 5: Run CLI Script to Associate Collaborators

Now that v1 aliases exist, run the automated script:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock

# Run the collaboration setup script
./scripts/associate_collaborators_with_v1.sh
```

**Expected output:**
```
═══════════════════════════════════════════════════════════════
Associate Collaborators with Supervisor Agent
═══════════════════════════════════════════════════════════════

Fetching v1 alias IDs...
✅ Found v1 aliases:
  Scheduling:  <ALIAS_ID>
  Information: <ALIAS_ID>
  Chitchat:    <ALIAS_ID>

═══════════════════════════════════════════════════════════════
Associating Collaborators...
═══════════════════════════════════════════════════════════════

📋 Associating SchedulingAgent...
✅ SchedulingAgent associated

📋 Associating InformationAgent...
✅ InformationAgent associated

📋 Associating ChitchatAgent...
✅ ChitchatAgent associated

═══════════════════════════════════════════════════════════════
Preparing Supervisor Agent...
═══════════════════════════════════════════════════════════════

✅ Supervisor Agent prepared with collaborators!

═══════════════════════════════════════════════════════════════
Verification
═══════════════════════════════════════════════════════════════

---------------------------------------------------------------------------
|                        ListAgentCollaborators                          |
+---------------------+--------------------------------------------------+
|  SchedulingAgent    |  arn:aws:bedrock:us-east-1:...:agent-alias/...  |
|  InformationAgent   |  arn:aws:bedrock:us-east-1:...:agent-alias/...  |
|  ChitchatAgent      |  arn:aws:bedrock:us-east-1:...:agent-alias/...  |
+---------------------+--------------------------------------------------+

✅ Collaboration configured successfully!
```

---

## Testing

### Test 1: Supervisor Routes to SchedulingAgent

```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id ZZNSFE74NB \
  --agent-alias-id TSTALIASID \
  --session-id test-$(date +%s) \
  --session-state '{"sessionAttributes":{"customer_id":"1645869","client_id":"09PF05VD"}}' \
  --input-text "List my projects" \
  /tmp/supervisor_projects.txt

# Check the output
cat /tmp/supervisor_projects.txt
```

### Test 2: Supervisor Routes to InformationAgent

```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id ZZNSFE74NB \
  --agent-alias-id TSTALIASID \
  --session-id test-$(date +%s) \
  --input-text "What's the weather in New York?" \
  /tmp/supervisor_weather.txt

cat /tmp/supervisor_weather.txt
```

### Test 3: Supervisor Routes to ChitchatAgent

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

### "v1 aliases not found" error

**Problem:** Script says v1 aliases don't exist

**Solution:** Complete Steps 2-4 in AWS Console first. The script needs v1 aliases to exist.

### "ValidationException: Agent cannot collaborate with TSTALIASID"

**Problem:** Trying to use TSTALIASID for collaboration

**Solution:** This is expected. TSTALIASID is AWS-managed and cannot be used for collaboration. You MUST create v1 aliases.

### "ResourceNotFoundException: Agent Version doesn't exist"

**Problem:** Trying to create alias before creating version

**Solution:** Always create version FIRST, then create alias pointing to that version.

### Collaborators not routing correctly

**Problem:** Supervisor responds but doesn't invoke specialist agents

**Possible causes:**
1. Collaborators not prepared - Run: `aws bedrock-agent prepare-agent --agent-id ZZNSFE74NB --region us-east-1`
2. Session attributes missing - Include `customer_id` and `client_id` in session state
3. Lambda permissions - Check CloudWatch logs for Lambda errors

---

## What Gets Created

### In AWS Console (Manual - One Time):
1. **SchedulingAgent Version 1** - Immutable snapshot of agent
2. **SchedulingAgent v1 alias** - Points to Version 1, used for collaboration
3. **pf-information Version 1** - Immutable snapshot
4. **pf-information v1 alias** - Points to Version 1
5. **pf-chitchat Version 1** - Immutable snapshot
6. **pf-chitchat v1 alias** - Points to Version 1

### Via CLI Script (Automated):
1. **Supervisor → SchedulingAgent collaboration** - Associates v1 alias as collaborator
2. **Supervisor → InformationAgent collaboration** - Associates v1 alias as collaborator
3. **Supervisor → ChitchatAgent collaboration** - Associates v1 alias as collaborator
4. **Prepared Supervisor** - Activates collaboration configuration

---

## Architecture After Setup

```
Supervisor Agent (ZZNSFE74NB)
├── Uses: TSTALIASID (for invocation)
├── Collaborators:
│   ├── SchedulingAgent → v1 alias → Version 1 → Lambda: pf-scheduling-actions
│   ├── InformationAgent → v1 alias → Version 1 → Lambda: pf-information-actions
│   └── ChitchatAgent → v1 alias → Version 1 → No Lambda (conversational)
└── Routes queries automatically based on intent
```

**Key Insight:**
- **TSTALIASID** → Used to INVOKE the Supervisor (points to Supervisor's DRAFT)
- **v1 aliases** → Used for COLLABORATION (point to specialist agents' Version 1)

---

## Alias Strategy Summary

| Agent | TSTALIASID | v1 Alias | Purpose |
|-------|------------|----------|---------|
| **Supervisor** | ✅ Used for invocation | ❌ Not needed | Entry point for users |
| **SchedulingAgent** | ✅ For individual testing | ✅ For collaboration | Specialist routing |
| **pf-information** | ✅ For individual testing | ✅ For collaboration | Specialist routing |
| **pf-chitchat** | ✅ For individual testing | ✅ For collaboration | Specialist routing |

---

## Time Estimate

- **AWS Console steps:** 15-20 minutes (one-time setup)
- **CLI script execution:** 30 seconds (automated)
- **Total:** ~20 minutes to fully enable collaboration

---

## Future Automation

If AWS adds CLI/Terraform support for creating versions in the future, update:
1. `scripts/DEPLOY.sh` - Add version creation after agent creation
2. `infrastructure/terraform/agent_versions_and_aliases.tf` - Uncomment when supported

**Track AWS provider updates:** https://github.com/hashicorp/terraform-provider-aws/releases

---

## Summary

✅ **What's Automated:**
- Agent creation
- Lambda deployment
- Role and permission setup
- Collaboration association (via `associate_collaborators_with_v1.sh`)

⚠️ **What Requires Console (One-Time):**
- Creating agent versions (AWS API limitation)
- Creating v1 aliases pointing to versions

Once v1 aliases exist, everything else is automated and the system will work perfectly!

---

_Last Updated: November 4, 2025_
_Current Agent IDs: XWYHPGTXFC (Scheduling), YPHTBWTHU8 (Information), 2VRYB01FGD (Chitchat), ZZNSFE74NB (Supervisor)_
