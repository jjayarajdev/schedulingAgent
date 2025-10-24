# Agent Instructions Update - AWS CLI Scripts

**Purpose:** Fix agent hallucination issue by adding AVAILABLE ACTIONS sections to agent instructions
**Date:** 2025-10-19
**Method:** AWS CLI (automated, repeatable, production-ready)

---

## 🎯 Overview

This directory contains scripts to update Bedrock agent instructions via AWS CLI to fix the hallucination issue where agents generate fake data instead of using Lambda functions.

**Problem:** Agents return hallucinated data (Kitchen Remodel, Bathroom Renovation) instead of real mock data (Flooring Installation 12345, Windows Installation 12347, Deck Repair 12350)

**Solution:** Update agent instructions to explicitly reference action groups with "AVAILABLE ACTIONS" sections

**Result:** Agents will call Lambda functions instead of generating fake responses

---

## 📁 Files Structure

```
bedrock/
├── agent-instructions/              # Instruction files
│   ├── scheduling-agent-instructions.txt    # Scheduling Agent (with AVAILABLE ACTIONS)
│   ├── information-agent-instructions.txt   # Information Agent (with AVAILABLE ACTIONS)
│   ├── notes-agent-instructions.txt         # Notes Agent (with AVAILABLE ACTIONS)
│   └── backups/                             # Auto-created backups
│       └── YYYYMMDD_HHMMSS/                 # Timestamped backup folder
│           ├── scheduling-agent-instructions-backup.txt
│           ├── information-agent-instructions-backup.txt
│           └── notes-agent-instructions-backup.txt
│
└── scripts/
    ├── update_agent_instructions.sh         # Main update script (run this!)
    ├── configure_action_groups.sh           # Action groups setup (already done)
    ├── test_lambdas.sh                      # Test Lambda functions
    └── README_AGENT_INSTRUCTIONS_UPDATE.md  # This file
```

---

## 🚀 Quick Start

### Step 1: Review Instruction Files (Optional)

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock

# Review what will be applied
cat agent-instructions/scheduling-agent-instructions.txt
cat agent-instructions/information-agent-instructions.txt
cat agent-instructions/notes-agent-instructions.txt
```

### Step 2: Run Update Script

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/scripts

# Run the update script
./update_agent_instructions.sh
```

**What it does:**
1. ✅ Verifies instruction files exist
2. ✅ Backs up current agent instructions (timestamped)
3. ✅ Updates all 3 agents with new instructions
4. ✅ Prepares all agents (wait 30s each)
5. ✅ Verifies AVAILABLE ACTIONS sections were added
6. ✅ Shows final status

**Time:** ~2-3 minutes total

### Step 3: Verify (CloudWatch Test)

```bash
# In one terminal, watch for Lambda invocations
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions --follow --region us-east-1

# In another terminal, test with Python (see Step 4)
```

**Expected:** You should see Lambda logs appear when agents are queried!

### Step 4: Test with Python API

Create a test file:

```python
# test_agent_with_session.py
import boto3
import json

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

def test_scheduling_agent():
    print("Testing Scheduling Agent...")
    print("="*80)

    response = client.invoke_agent(
        agentId='5VTIWONUMO',  # Supervisor Agent
        agentAliasId='HH2U7EZXMW',
        sessionId=f'test-{int(time.time())}',
        inputText='Show me all my projects',
        sessionState={
            'sessionAttributes': {
                'customer_id': 'CUST001',
                'customer_type': 'B2C'
            }
        }
    )

    # Process response stream
    for event in response['completion']:
        if 'chunk' in event:
            chunk = event['chunk']['bytes'].decode()
            print(chunk, end='', flush=True)

    print("\n" + "="*80)

if __name__ == '__main__':
    import time
    test_scheduling_agent()
```

Run it:

```bash
python3 test_agent_with_session.py
```

**Expected Output:**
```
I found 3 projects for you:

1. Flooring Installation (12345)
   - Order: ORD-2025-001
   - Status: Scheduled
   - Address: 123 Main St, Tampa, FL 33601
   - Scheduled: 2025-10-15

2. Windows Installation (12347)
   - Order: ORD-2025-002
   - Status: Pending
   - Address: 456 Oak Ave, Tampa, FL 33602

3. Deck Repair (12350)
   - Order: ORD-2025-003
   - Status: Pending
   - Address: 789 Pine Dr, Clearwater, FL 33755
```

**CloudWatch logs should show:**
```
START RequestId: xxx
Received event: {"actionGroup": "scheduling_actions", ...}
Extracted parameters: {'customer_id': 'CUST001'}
Returning 3 projects for customer CUST001
END RequestId: xxx
```

✅ **SUCCESS!** Agents are now using Lambda functions!

---

## 📋 What Changed

### Before (Agents Hallucinate)

**Instructions had:**
```
You are a scheduling specialist agent...

Your responsibilities:
1) Help customers view their projects
2) Check available dates and time slots for scheduling
...
```

**Problem:** No explicit instruction to USE action groups!

**Result:** Agent generates fake data from LLM knowledge

---

### After (Agents Use Actions)

**Instructions now include:**
```
AVAILABLE ACTIONS - MUST USE THESE!

1. list_projects
   When to use: User asks to see projects
   Required: customer_id (from sessionAttributes)
   CRITICAL: NEVER make up project data! ALWAYS call this action!

2. get_available_dates
   When to use: User wants to schedule, check availability
   Required: project_id only
   CRITICAL: NEVER guess dates! ALWAYS call this action!

... (for all 6 actions)

CRITICAL REMINDERS:
- NEVER generate fake data - USE AN ACTION!
- NEVER make up project IDs - Use list_projects!
- NEVER guess dates/times - Use get_available_dates!
```

**Result:** Agent explicitly knows to call actions instead of generating responses!

---

## 🔍 Script Details

### update_agent_instructions.sh

**Purpose:** Update all 3 specialist agents with new instructions that include AVAILABLE ACTIONS sections

**What it does:**

1. **Verification Phase**
   - Checks all 3 instruction files exist
   - Shows file sizes and line counts
   - Exits if any file is missing

2. **Backup Phase**
   - Creates timestamped backup directory
   - Backs up current instructions for all 3 agents
   - Preserves original instructions for rollback

3. **Update Phase**
   - Fetches current agent configuration (name, model, role)
   - Updates instructions while preserving other settings
   - Updates all 3 agents: Scheduling, Information, Notes

4. **Prepare Phase**
   - Prepares all 3 agents (AWS requirement after changes)
   - Waits 30 seconds per agent for preparation
   - Shows preparation status and timestamps

5. **Verification Phase**
   - Checks all agents are PREPARED
   - Verifies "AVAILABLE ACTIONS" sections exist
   - Shows update and preparation timestamps

**Output:**
- Color-coded console output (green=success, red=error, yellow=warning, blue=info)
- Progress indicators for each step
- Detailed status for each agent
- Backup location for rollback

**Safety Features:**
- ✅ Creates backups before any changes
- ✅ Validates files exist before starting
- ✅ Preserves existing agent configuration (model, role, etc.)
- ✅ Exits on error (won't partially update)
- ✅ Shows exactly what changed

---

## 🔄 Rollback (If Needed)

If something goes wrong, you can restore from backups:

```bash
# Find your backup
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/agent-instructions/backups
ls -la

# Latest backup is in the newest folder
cd 20251019_131800  # Use your timestamp

# Manually restore using AWS CLI
aws bedrock-agent update-agent \
  --agent-id IX24FSMTQH \
  --agent-name "scheduling-agent-scheduling" \
  --foundation-model "us.anthropic.claude-sonnet-4-5-20250929-v1:0" \
  --instruction "$(cat scheduling-agent-instructions-backup.txt)" \
  --agent-resource-role-arn "arn:aws:iam::618048437522:role/scheduling-agent-scheduling-agent-role-dev" \
  --region us-east-1

# Then prepare agent
aws bedrock-agent prepare-agent --agent-id IX24FSMTQH --region us-east-1
```

Repeat for Information Agent (C9ANXRIO8Y) and Notes Agent (G5BVBYEPUM).

---

## 🧪 Testing After Update

### 1. Test Lambda Functions Directly

```bash
# Test Scheduling Lambda
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/scripts
./test_lambdas.sh

# Should show:
# ✅ PASS - list_projects
# ✅ PASS - get_available_dates
# etc.
```

### 2. Test Agents with Python API

**See Step 4 in Quick Start above**

Key points:
- MUST include sessionAttributes with customer_id
- MUST use bedrock-agent-runtime API (not bedrock-agent)
- Use Supervisor Agent ID (5VTIWONUMO) for multi-agent routing

### 3. Monitor CloudWatch Logs

```bash
# Watch Scheduling Lambda
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions --follow --region us-east-1

# Watch Information Lambda
aws logs tail /aws/lambda/scheduling-agent-information-actions --follow --region us-east-1

# Watch Notes Lambda
aws logs tail /aws/lambda/scheduling-agent-notes-actions --follow --region us-east-1
```

**Expected:** Logs appear when agents query!

**Not expected:** No logs (agents still hallucinating)

---

## ✅ Success Criteria

After running the update script, verify:

- [ ] Script completed without errors
- [ ] All 3 agents show Status: PREPARED
- [ ] All 3 agents have recent preparedAt timestamps
- [ ] Verification shows "✅ AVAILABLE ACTIONS section found" for all 3 agents
- [ ] Backups created in agent-instructions/backups/TIMESTAMP/
- [ ] Python test returns real mock data (12345, 12347, 12350)
- [ ] CloudWatch logs show Lambda invocations
- [ ] NO hallucinated data (Kitchen Remodel, Bathroom Renovation, etc.)

---

## 🎯 Agent IDs Reference

| Agent | ID | Instruction File |
|-------|-------|------------------|
| Scheduling Agent | IX24FSMTQH | scheduling-agent-instructions.txt |
| Information Agent | C9ANXRIO8Y | information-agent-instructions.txt |
| Notes Agent | G5BVBYEPUM | notes-agent-instructions.txt |
| Supervisor Agent | 5VTIWONUMO | (No changes - routing only) |
| Chitchat Agent | 2SUXQSWZOV | (No changes - no action groups) |

---

## 📊 Deployment to Stage/Production

### For Dev → Stage → Prod:

1. **Keep instruction files in version control:**
   ```bash
   git add agent-instructions/*.txt
   git commit -m "Add AVAILABLE ACTIONS sections to fix hallucination"
   git push
   ```

2. **Update agent IDs for each environment:**

   **Option A:** Create environment-specific scripts
   ```bash
   # scripts/update_agent_instructions_dev.sh (uses dev agent IDs)
   # scripts/update_agent_instructions_stage.sh (uses stage agent IDs)
   # scripts/update_agent_instructions_prod.sh (uses prod agent IDs)
   ```

   **Option B:** Use environment variables
   ```bash
   # Set environment-specific IDs
   export SCHEDULING_AGENT_ID="STAGE_ID_HERE"
   export INFORMATION_AGENT_ID="STAGE_ID_HERE"
   export NOTES_AGENT_ID="STAGE_ID_HERE"

   # Run script (modify to use env vars)
   ./update_agent_instructions.sh
   ```

3. **Terraform/IaC approach (recommended):**
   - Store instructions in Terraform variables
   - Use `aws_bedrockagent_agent` resource
   - Apply instruction updates via Terraform

---

## 🐛 Troubleshooting

### Issue: Script says "Missing instruction files"

**Solution:**
```bash
# Check if files exist
ls -la /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/agent-instructions/

# Should show:
# scheduling-agent-instructions.txt
# information-agent-instructions.txt
# notes-agent-instructions.txt
```

---

### Issue: Agent still shows old status

**Solution:**
```bash
# Manually prepare agent
aws bedrock-agent prepare-agent --agent-id IX24FSMTQH --region us-east-1

# Wait 60 seconds, then check
aws bedrock-agent get-agent --agent-id IX24FSMTQH --region us-east-1 --query 'agent.agentStatus'
```

---

### Issue: Agents still hallucinating after update

**Check:**

1. **Verify AVAILABLE ACTIONS section exists:**
   ```bash
   aws bedrock-agent get-agent \
     --agent-id IX24FSMTQH \
     --region us-east-1 \
     --query 'agent.instruction' \
     --output text | grep "AVAILABLE ACTIONS"
   ```

2. **Check if using session attributes:**
   - Python test MUST include sessionState with sessionAttributes
   - Console tests may not populate sessionAttributes automatically

3. **Verify action groups exist:**
   ```bash
   aws bedrock-agent list-agent-action-groups \
     --agent-id IX24FSMTQH \
     --agent-version DRAFT \
     --region us-east-1

   # Should show: actionGroupState: ENABLED
   ```

4. **Check CloudWatch logs:**
   ```bash
   aws logs tail /aws/lambda/scheduling-agent-scheduling-actions --region us-east-1

   # If no logs, Lambda not being invoked!
   ```

---

## 📚 Related Documentation

- **Investigation Report:** [`../HALLUCINATION_ISSUE_SUMMARY.md`](../HALLUCINATION_ISSUE_SUMMARY.md)
- **Detailed Fix Guide:** [`../docs/HALLUCINATION_FIX_GUIDE.md`](../docs/HALLUCINATION_FIX_GUIDE.md)
- **Action Reference:** [`../docs/AGENT_INSTRUCTIONS_ACTION_REFERENCE.md`](../docs/AGENT_INSTRUCTIONS_ACTION_REFERENCE.md)
- **Testing Guide:** [`../docs/TESTING_COMPLETE_WORKFLOWS.md`](../docs/TESTING_COMPLETE_WORKFLOWS.md)
- **Mock Data Reference:** [`../docs/MOCK_DATA_REFERENCE.md`](../docs/MOCK_DATA_REFERENCE.md)

---

**Once script completes successfully, agents will use Lambda functions and stop hallucinating!** 🎉
