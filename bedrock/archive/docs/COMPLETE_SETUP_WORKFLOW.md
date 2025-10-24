# Complete Setup Workflow - All Scripts in Order

**Last Updated:** 2025-10-19

This guide shows you **exactly which scripts to run** and in what order to set up the entire multi-agent system.

---

## 📋 Prerequisites

Before running any scripts:

1. **AWS CLI configured**
   ```bash
   aws configure
   # Region: us-east-1
   # Access Key: Your AWS access key
   # Secret Key: Your AWS secret key
   ```

2. **Bedrock model access enabled**
   - Claude Sonnet 4.5 model access requested and approved
   - Model ID: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`

3. **Agents already created** (via Terraform or Console)
   - Supervisor Agent: `5VTIWONUMO`
   - Scheduling Agent: `IX24FSMTQH`
   - Information Agent: `C9ANXRIO8Y`
   - Notes Agent: `G5BVBYEPUM`
   - Chitchat Agent: `2SUXQSWZOV`

---

## 🚀 Complete Setup (7 Steps)

### Step 1: Deploy Lambda Functions ✅

**What it does:** Deploys 3 Lambda functions to AWS with all dependencies

**Script:** `scripts/deploy_lambda_functions.sh`

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/scripts

./deploy_lambda_functions.sh
```

**Time:** ~5 minutes

**What happens:**
- Packages Lambda code with dependencies
- Creates/updates 3 Lambda functions:
  - `scheduling-agent-scheduling-actions` (6 actions)
  - `scheduling-agent-information-actions` (4 actions)
  - `scheduling-agent-notes-actions` (2 actions)
- Sets environment variables (`USE_MOCK_API=true`)
- Grants Bedrock permissions

**Verify:**
```bash
aws lambda list-functions --region us-east-1 --query 'Functions[?contains(FunctionName, `scheduling-agent`)].FunctionName'
```

**Expected:** Should show 3 Lambda functions

---

### Step 2: Configure Action Groups ✅

**What it does:** Connects Lambda functions to Bedrock agents via action groups

**Script:** `scripts/configure_action_groups.sh`

```bash
./configure_action_groups.sh
```

**Time:** ~3 minutes

**What happens:**
- Deletes existing action groups (if any)
- Creates new action groups for each specialist agent:
  - Scheduling Agent → scheduling-actions Lambda
  - Information Agent → information-actions Lambda
  - Notes Agent → notes-actions Lambda
- Uses OpenAPI 3.0 schemas from `lambda/schemas/`
- Prepares all specialist agents

**Verify:**
```bash
aws bedrock-agent list-agent-action-groups --agent-id IX24FSMTQH --agent-version DRAFT --region us-east-1
```

**Expected:** Should show action group with Lambda ARN

---

### Step 3: Test Lambda Functions Directly 🧪

**What it does:** Tests Lambda functions directly (bypasses agents)

**Script:** `scripts/test_lambdas.sh`

```bash
./test_lambdas.sh
```

**Time:** ~1 minute

**What happens:**
- Tests all 8 Lambda actions directly
- Color-coded pass/fail output
- Summary statistics

**Expected Output:**
```
✅ list_projects - PASSED
✅ get_project_details - PASSED
✅ get_appointment_status - PASSED
✅ get_working_hours - PASSED
✅ get_available_dates - PASSED
✅ confirm_appointment - PASSED
✅ add_note - PASSED
✅ list_notes - PASSED

Total: 8/8 PASSED
```

**If any fail:** Check Lambda deployment, CloudWatch logs

---

### Step 4: Update Agent Instructions ⭐ CRITICAL

**What it does:** Updates all agent instructions to include AVAILABLE ACTIONS sections

**Script:** `scripts/update_agent_instructions.sh`

```bash
./update_agent_instructions.sh
```

**Time:** ~3 minutes

**What happens:**
- Backs up current agent instructions (timestamped)
- Updates 3 specialist agents with AVAILABLE ACTIONS sections:
  - Scheduling Agent → 6 available actions
  - Information Agent → 4 available actions
  - Notes Agent → 2 available actions
- Prepares all agents (makes instructions active)
- Verifies AVAILABLE ACTIONS sections exist

**Expected Output:**
```
✅ Scheduling Agent instructions updated
✅ Information Agent instructions updated
✅ Notes Agent instructions updated
✅ All agents prepared successfully
✅ Verification complete - All agents have AVAILABLE ACTIONS
```

**Why critical:** Without AVAILABLE ACTIONS sections, agents will hallucinate instead of calling Lambda functions!

---

### Step 5: Update Collaborator Aliases ⭐ MOST CRITICAL

**What it does:** Creates new agent versions and updates Supervisor collaborators to use them

**Script:** `scripts/update_collaborator_aliases_v2.sh`

```bash
./update_collaborator_aliases_v2.sh
```

**Time:** ~3 minutes (+ 30 second wait)

**What happens:**
1. Creates new versions from DRAFT for all specialist agents (v5, v5, v5, v5)
   - These versions include the updated instructions from Step 4
2. Creates/updates version aliases (v5) pointing to new versions
3. Deletes old Supervisor collaborators (pointing to old versions)
4. Creates new collaborators using version aliases
5. Prepares Supervisor Agent

**Expected Output:**
```
✅ Created version 5 for Scheduling Agent
✅ Created version 5 for Information Agent
✅ Created version 5 for Notes Agent
✅ Created version 5 for Chitchat Agent

✅ Updated alias v5 → version 5 (ABC123)
✅ Updated alias v5 → version 5 (DEF456)
✅ Updated alias v5 → version 5 (GHI789)
✅ Updated alias v5 → version 5 (JKL012)

✅ Deleted old collaborators
✅ Added scheduling_collaborator
✅ Added information_collaborator
✅ Added notes_collaborator
✅ Added chitchat_collaborator

✅ Supervisor Agent prepared successfully
```

**Why critical:** This is the FINAL piece to fix hallucination! Supervisor must use updated agent versions.

**Why version aliases:** AWS Bedrock doesn't allow DRAFT aliases for collaboration. See `COLLABORATOR_ALIAS_ISSUE.md`.

---

### Step 6: Test Agents with Session Context 🧪

**What it does:** Tests the complete multi-agent system with proper session context

**Script:** `tests/test_agent_with_session.py`

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock

./tests/test_agent_with_session.py
```

**Time:** ~2 minutes

**What happens:**
- Tests 5 complete workflows with session attributes
- Each test verifies:
  - ✅ Lambda function called (not hallucinated)
  - ✅ Real mock data returned (12345, 12347, 12350)
  - ❌ NO hallucinated data (Kitchen Remodel, etc.)

**Expected Output:**
```
⚠️  IMPORTANT: Run these scripts FIRST:
   1. bedrock/scripts/update_agent_instructions.sh ✅
   2. bedrock/scripts/update_collaborator_aliases_v2.sh ✅

================================================================================
Test 1: List Projects (B2C Customer)
================================================================================
Query: Show me all my projects
Session: customer_id=CUST001, customer_type=B2C

✅ Test 1 PASSED - List Projects

Expected data found: 12345, 12347, 12350, Flooring, Windows, Deck
No hallucinated data found

================================================================================
Test 2: Get Project Details
================================================================================
...

Total Tests: 5
Passed: ✅ 5
Failed: ❌ 0
Success Rate: 100.0%
```

**If tests fail:** Check CloudWatch logs (next step)

---

### Step 7: Verify CloudWatch Logs 🔍

**What it does:** Confirms Lambda functions are being invoked by agents

**Commands:**

```bash
# Watch Scheduling Lambda logs (real-time)
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions --follow --region us-east-1

# In another terminal, run the test
./tests/test_agent_with_session.py

# You should see Lambda invocations appear in the logs!
```

**Expected Logs:**
```
2025-10-19T14:30:15.123Z START RequestId: abc-123
2025-10-19T14:30:15.456Z [INFO] Action: list_projects
2025-10-19T14:30:15.789Z [INFO] Customer ID: CUST001
2025-10-19T14:30:16.012Z [INFO] Returning 3 projects
2025-10-19T14:30:16.234Z END RequestId: abc-123
```

**If no logs appear:** Agents are NOT calling Lambda functions
- Re-run Step 5 (update_collaborator_aliases_v2.sh)
- Check collaborator configuration
- See troubleshooting section below

---

## ✅ Success Checklist

After running all 7 steps, verify:

- [ ] **Step 1:** 3 Lambda functions deployed
  ```bash
  aws lambda list-functions --region us-east-1 | grep scheduling-agent
  ```

- [ ] **Step 2:** Action groups configured for 3 agents
  ```bash
  aws bedrock-agent list-agent-action-groups --agent-id IX24FSMTQH --agent-version DRAFT --region us-east-1
  ```

- [ ] **Step 3:** Lambda direct tests pass (8/8)
  ```bash
  ./scripts/test_lambdas.sh
  ```

- [ ] **Step 4:** Agents have AVAILABLE ACTIONS in instructions
  ```bash
  aws bedrock-agent get-agent --agent-id IX24FSMTQH --region us-east-1 --query 'agent.instruction' | grep "AVAILABLE ACTIONS"
  ```

- [ ] **Step 5:** Supervisor collaborators use version aliases (NOT TSTALIASID)
  ```bash
  aws bedrock-agent list-agent-collaborators --agent-id 5VTIWONUMO --agent-version DRAFT --region us-east-1
  ```

- [ ] **Step 6:** Agent tests pass (5/5)
  ```bash
  ./tests/test_agent_with_session.py
  ```

- [ ] **Step 7:** CloudWatch logs show Lambda invocations
  ```bash
  aws logs tail /aws/lambda/scheduling-agent-scheduling-actions --since 5m --region us-east-1
  ```

---

## 🔄 Quick Reference - All Commands

**Copy-paste this entire block to run everything:**

```bash
# Navigate to bedrock directory
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock

# Step 1: Deploy Lambda functions
./scripts/deploy_lambda_functions.sh

# Step 2: Configure action groups
./scripts/configure_action_groups.sh

# Step 3: Test Lambda functions
./scripts/test_lambdas.sh

# Step 4: Update agent instructions
./scripts/update_agent_instructions.sh

# Step 5: Update collaborator aliases (CRITICAL!)
./scripts/update_collaborator_aliases_v2.sh

# Step 6: Test agents
./tests/test_agent_with_session.py

# Step 7: Verify CloudWatch logs (in separate terminal)
# aws logs tail /aws/lambda/scheduling-agent-scheduling-actions --follow --region us-east-1
```

**Total Time:** ~20 minutes (including waiting for agents to prepare)

---

## 🚨 Troubleshooting

### Issue: Lambda deployment fails

**Error:** `An error occurred (AccessDeniedException)`

**Solution:**
- Check AWS credentials: `aws sts get-caller-identity`
- Verify Lambda permissions in IAM

### Issue: Action group configuration fails

**Error:** `Agent must be in PREPARED state`

**Solution:**
```bash
# Prepare agent manually
aws bedrock-agent prepare-agent --agent-id IX24FSMTQH --region us-east-1

# Wait 30 seconds, then retry
sleep 30
./scripts/configure_action_groups.sh
```

### Issue: Agent tests fail (agents hallucinate)

**Symptoms:** Tests return fake data (Kitchen Remodel, etc.) instead of real mock data (12345, 12347, 12350)

**Solution:**
1. Verify Step 4 completed:
   ```bash
   aws bedrock-agent get-agent --agent-id IX24FSMTQH --region us-east-1 --query 'agent.instruction' | grep "AVAILABLE ACTIONS"
   ```
   Should output: AVAILABLE ACTIONS section

2. Verify Step 5 completed:
   ```bash
   aws bedrock-agent list-agent-collaborators --agent-id 5VTIWONUMO --agent-version DRAFT --region us-east-1 | grep TSTALIASID
   ```
   Should output: **Nothing** (collaborators should NOT use TSTALIASID)

3. Re-run Step 5:
   ```bash
   ./scripts/update_collaborator_aliases_v2.sh
   ```

### Issue: No CloudWatch logs

**Symptoms:** Tests pass but no Lambda invocations appear in CloudWatch

**Solution:**
- Agents are NOT calling Lambda functions (hallucinating instead)
- Re-run Step 4 and Step 5
- Wait 60 seconds after Step 5 before testing

---

## 📚 Related Documentation

**Setup Guides:**
- `AWS_SETUP_GUIDE.md` - AWS account setup
- `AWS_SETUP_STEP_BY_STEP.md` - Detailed AWS setup
- `COLLABORATOR_ALIAS_ISSUE.md` - Why version aliases are needed

**Testing:**
- `tests/README.md` - Test documentation
- `docs/TESTING_COMPLETE_WORKFLOWS.md` - Complete test workflows
- `docs/MOCK_DATA_REFERENCE.md` - Mock data reference

**Troubleshooting:**
- `docs/HALLUCINATION_FIX_GUIDE.md` - Hallucination troubleshooting
- `FINAL_FIX_SUMMARY.md` - Complete fix summary
- `QUICK_FIX_GUIDE.md` - Quick reference

**Scripts:**
- `scripts/README.md` - All scripts documentation

---

## 💡 What Each Step Does (Summary)

| Step | Script | Purpose | Critical? | Time |
|------|--------|---------|-----------|------|
| 1 | `deploy_lambda_functions.sh` | Deploy Lambda functions to AWS | ✅ Yes | 5 min |
| 2 | `configure_action_groups.sh` | Connect Lambda to agents | ✅ Yes | 3 min |
| 3 | `test_lambdas.sh` | Verify Lambda works | 🧪 Test | 1 min |
| 4 | `update_agent_instructions.sh` | Add AVAILABLE ACTIONS to agents | ⭐ CRITICAL | 3 min |
| 5 | `update_collaborator_aliases_v2.sh` | Update Supervisor to use new versions | ⭐ MOST CRITICAL | 3 min |
| 6 | `test_agent_with_session.py` | Test complete system | 🧪 Test | 2 min |
| 7 | CloudWatch verification | Confirm Lambda invocations | 🔍 Verify | 1 min |

**Total:** ~20 minutes

---

## 🎯 Current Status for Your Setup

Based on your session:

| Step | Status | Notes |
|------|--------|-------|
| 1. Deploy Lambda | ✅ Done | Lambda functions already deployed |
| 2. Configure Action Groups | ✅ Done | Action groups already configured |
| 3. Test Lambda | ✅ Done | 8/8 tests pass |
| 4. Update Instructions | ✅ Done | You ran this successfully |
| 5. Update Collaborators | ⏳ **PENDING** | Need to run `update_collaborator_aliases_v2.sh` |
| 6. Test Agents | ⏳ Pending | Run after Step 5 |
| 7. Verify CloudWatch | ⏳ Pending | Run after Step 6 |

**Next Step for You:**
```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/scripts
./update_collaborator_aliases_v2.sh
```

---

**Last Updated:** 2025-10-19
**Status:** Ready to run Step 5 (update_collaborator_aliases_v2.sh)
