# Action Groups Quick Setup Guide

**⚠️ CRITICAL:** Without action groups, agents will hallucinate data instead of using Lambda functions!

**Time Required:** 10 minutes (5 min per agent)

---

## ✅ Current Status Check

| Agent | Action Group Status | What Happens |
|-------|-------------------|--------------|
| **Notes Agent** | ✅ Configured | Works correctly, uses Lambda |
| **Scheduling Agent** | ❌ NOT configured | Hallucinates data (Website Redesign, Mobile App, etc.) |
| **Information Agent** | ❌ NOT configured | Hallucinates data instead of using mock projects |
| **Supervisor Agent** | N/A | No action group needed (routes only) |
| **Chitchat Agent** | N/A | No action group needed (LLM only) |

---

## 🚨 Problem You're Seeing

**When you ask:** "Show me all projects for customer CUST001"

**What you get (WRONG):**
```
- Website Redesign (PROJ-001)
- Mobile App Development (PROJ-002)
- Database Migration (PROJ-003)
- Cloud Infrastructure Setup (PROJ-004)
```

**What you should get (CORRECT):**
```
- Flooring Installation (12345) - Tampa, FL
- Windows Installation (12347) - Tampa, FL
- Deck Repair (12350) - Clearwater, FL
```

**Why?** The agent doesn't have an action group, so it can't call the Lambda function. It makes up data instead.

---

## 🔧 Fix 1: Add Scheduling Agent Action Group

### Step 1: Get the Schema

```bash
cat /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/lambda/schemas/scheduling-actions-schema.json
```

**Copy the entire JSON output** - you'll paste this in Step 6.

---

### Step 2: Open Scheduling Agent

**URL:** https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/IX24FSMTQH

---

### Step 3: Click "Edit" Button

Look for the **"Edit"** button at the top right of the page.

---

### Step 4: Scroll to "Action groups" Section

Scroll down until you see **"Action groups"** section (below Instructions).

---

### Step 5: Click "Add" Button

Click the **"Add"** button in the Action groups section.

---

### Step 6: Fill in Action Group Details

| Field | Value |
|-------|-------|
| **Action group name** | `scheduling_actions` |
| **Description** | `Scheduling operations including list projects, check availability, confirm/reschedule/cancel appointments` |
| **Action group type** | `Define with API schemas` |
| **Action group invocation** | `Select existing Lambda function` |
| **Lambda function** | `scheduling-agent-scheduling-actions` |
| **API Schema** | Select: `Define with in-line OpenAPI schema editor` |

---

### Step 7: Paste OpenAPI Schema

In the schema editor box, paste the entire JSON you copied in Step 1.

Click **"Validate"** to check the schema is correct.

---

### Step 8: Save and Prepare

1. Click **"Add"** button (bottom of action group form)
2. Wait for action group to be created
3. Click **"Prepare"** button at the **TOP** of the page ⚠️ **CRITICAL!**
4. Wait 30-60 seconds for status to change from PREPARING → PREPARED

---

### Step 9: Verify

```bash
# Check agent status
aws bedrock-agent get-agent \
  --agent-id IX24FSMTQH \
  --region us-east-1 \
  --query 'agent.agentStatus' \
  --output text
```

Should return: `PREPARED`

---

## 🔧 Fix 2: Add Information Agent Action Group

### Step 1: Get the Schema

```bash
cat /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/lambda/schemas/information-actions-schema.json
```

**Copy the entire JSON output.**

---

### Step 2: Open Information Agent

**URL:** https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/C9ANXRIO8Y

---

### Step 3: Click "Edit" Button

---

### Step 4: Scroll to "Action groups" Section

---

### Step 5: Click "Add" Button

---

### Step 6: Fill in Action Group Details

| Field | Value |
|-------|-------|
| **Action group name** | `information_actions` |
| **Description** | `Information operations including project details, appointment status, working hours, weather` |
| **Action group type** | `Define with API schemas` |
| **Action group invocation** | `Select existing Lambda function` |
| **Lambda function** | `scheduling-agent-information-actions` |
| **API Schema** | Select: `Define with in-line OpenAPI schema editor` |

---

### Step 7: Paste OpenAPI Schema

Paste the JSON from Step 1.

Click **"Validate"**.

---

### Step 8: Save and Prepare

1. Click **"Add"**
2. Click **"Prepare"** at top ⚠️
3. Wait for PREPARED status

---

### Step 9: Verify

```bash
aws bedrock-agent get-agent \
  --agent-id C9ANXRIO8Y \
  --region us-east-1 \
  --query 'agent.agentStatus' \
  --output text
```

Should return: `PREPARED`

---

## ✅ Test After Configuration

### Test 1: Scheduling Agent

**URL:** https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/IX24FSMTQH

**Query:**
```
Show me all projects for customer CUST001
```

**Expected Response (CORRECT):**
```
I found 3 projects for customer CUST001:

1. Flooring Installation (12345)
   - Order: ORD-2025-001
   - Status: Scheduled
   - Store: ST-101
   - Address: 123 Main St, Tampa, FL 33601
   - Scheduled: 2025-10-15

2. Windows Installation (12347)
   - Order: ORD-2025-002
   - Status: Pending
   - Store: ST-102
   - Address: 456 Oak Ave, Tampa, FL 33602

3. Deck Repair (12350)
   - Order: ORD-2025-003
   - Status: Pending
   - Store: ST-103
   - Address: 789 Pine Dr, Clearwater, FL 33755
```

---

### Test 2: Information Agent

**URL:** https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/C9ANXRIO8Y

**Query:**
```
Tell me about project 12345 for customer CUST001
```

**Expected Response (CORRECT):**
```
Here are the details for project 12345:

Project Information:
- Project ID: 12345
- Order Number: ORD-2025-001
- Type: Installation
- Category: Flooring
- Status: Scheduled

Location:
- Address: 123 Main St, Apt 4B
- City: Tampa, FL 33601

Schedule:
- Scheduled Date: 2025-10-15
- Time: 08:00 AM - 12:00 PM
- Duration: 4 hours

Technician:
- Name: John Smith
- ID: 1001

Customer:
- Name: Sarah Johnson
- Email: sarah.johnson@email.com
- Phone: (555) 123-4567
```

---

## 🔍 Verification Commands

### Check Lambda Invocations

```bash
# Watch Scheduling Lambda logs (in real-time)
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions \
  --follow \
  --region us-east-1

# In another terminal, test the agent
# You should see logs appear showing Lambda invocation
```

### Check Action Groups Exist

```bash
# List action groups for Scheduling Agent
aws bedrock-agent list-agent-action-groups \
  --agent-id IX24FSMTQH \
  --agent-version DRAFT \
  --region us-east-1

# List action groups for Information Agent
aws bedrock-agent list-agent-action-groups \
  --agent-id C9ANXRIO8Y \
  --agent-version DRAFT \
  --region us-east-1
```

---

## 🐛 Troubleshooting

### Issue 1: "Prepare" Button Grayed Out

**Solution:** Save your changes first (scroll down and click "Save"), then the "Prepare" button will be enabled.

---

### Issue 2: Schema Validation Error

**Error:** `Invalid OpenAPI schema`

**Solution:**
- Make sure you copied the **entire** JSON (including opening `{` and closing `}`)
- No extra characters before/after the JSON
- Use the exact file content, don't modify it

---

### Issue 3: Lambda Function Not Found

**Error:** `Lambda function scheduling-agent-scheduling-actions not found`

**Solution:**
```bash
# Verify Lambda exists
aws lambda get-function \
  --function-name scheduling-agent-scheduling-actions \
  --region us-east-1

# If not found, deploy it
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
./scripts/deploy_lambda_functions.sh
```

---

### Issue 4: Still Getting Hallucinated Data

**Possible causes:**
1. **Forgot to click "Prepare"** - Most common! Click "Prepare" button at top
2. **Agent not PREPARED** - Wait 60 seconds, check status
3. **Testing old session** - Clear browser cache or use new session
4. **Action group not saved** - Go back to agent, verify action group exists

**Verify action group exists:**
```bash
aws bedrock-agent list-agent-action-groups \
  --agent-id IX24FSMTQH \
  --agent-version DRAFT \
  --region us-east-1 \
  --query 'actionGroupSummaries[*].actionGroupName'
```

Should show: `["scheduling_actions"]`

---

## ⏱️ Total Time Estimate

| Task | Time |
|------|------|
| Copy schemas | 1 min |
| Add Scheduling action group | 5 min |
| Add Information action group | 5 min |
| Test both agents | 2 min |
| **Total** | **13 min** |

---

## 📋 Checklist

Before testing:
- [ ] Scheduling Agent action group added
- [ ] Scheduling Agent status = PREPARED
- [ ] Information Agent action group added
- [ ] Information Agent status = PREPARED
- [ ] Clear browser cache / start new test session

Testing:
- [ ] "Show me all projects" returns 12345, 12347, 12350
- [ ] "Tell me about project 12345" returns Flooring Installation details
- [ ] CloudWatch logs show Lambda invocations
- [ ] No more hallucinated data (Website Redesign, Mobile App, etc.)

---

## 🎯 Success Criteria

✅ Scheduling Agent returns **3 real mock projects** (12345, 12347, 12350)
✅ Information Agent returns **real project details** from Lambda
✅ CloudWatch logs show **Lambda function invocations**
✅ **No more hallucinated data** like "Website Redesign" or "Mobile App"

---

**Once action groups are configured, the agents will use Lambda functions and return correct mock data!**

**Next:** Update agent instructions with B2B logic (docs/AGENT_INSTRUCTIONS_UPDATE_CHECKLIST.md)
