# Agent Hallucination Issue - Root Cause Analysis & Fix

**Date:** 2025-10-19
**Status:** 🔴 CRITICAL ISSUE
**Impact:** Agents generating fake data instead of using Lambda functions

---

## 🚨 Problem Summary

**What you're seeing:**
```
User query: "Show me all projects for customer CUST001"

WRONG (Hallucinated):
- Kitchen Remodel (Building A)
- Bathroom Renovation (Building B)
- Exterior Painting (Building A)
- HVAC System Upgrade (Building C)
```

**What you should see:**
```
CORRECT (From Lambda):
- Flooring Installation (12345) - Tampa, FL
- Windows Installation (12347) - Tampa, FL
- Deck Repair (12350) - Clearwater, FL
```

---

## ✅ Verified Working Components

### Lambda Functions ✅
```bash
# Direct Lambda test WORKS:
aws lambda invoke \
  --function-name scheduling-agent-scheduling-actions \
  --payload '{"actionGroup":"scheduling_actions","apiPath":"/list-projects",...}' \
  response.json

# Returns:
{
  "projects": [
    {"project_id": "12345", "category": "Flooring", "address": "Tampa, FL"},
    {"project_id": "12347", "category": "Windows", "address": "Tampa, FL"},
    {"project_id": "12350", "category": "Deck Repair", "address": "Clearwater, FL"}
  ]
}
```
✅ Lambda works correctly!

### Action Groups ✅
```bash
# Check action group configuration
aws bedrock-agent list-agent-action-groups \
  --agent-id IX24FSMTQH \
  --agent-version DRAFT \
  --region us-east-1

# Result:
{
  "actionGroupName": "scheduling_actions",
  "actionGroupState": "ENABLED",
  "actionGroupExecutor": {
    "lambda": "arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-scheduling-actions"
  }
}
```
✅ Action group is ENABLED and linked to Lambda!

### Agent Status ✅
```bash
# Check agent preparation status
aws bedrock-agent get-agent \
  --agent-id IX24FSMTQH \
  --region us-east-1 \
  --query 'agent.agentStatus'

# Result: "PREPARED"
```
✅ Agent is PREPARED!

---

## 🔍 Root Cause Analysis

Despite all components being configured correctly, agents are NOT invoking Lambda functions. Here's why:

### Issue 1: Console Testing Without Session Context

**When you test in the Bedrock Console:**
- You type: "Show me all projects for customer CUST001"
- The agent should extract customer_id from the query
- BUT the agent instructions expect customer_id in **sessionAttributes**

**From Scheduling Agent instructions:**
```
SESSION CONTEXT AWARENESS:
You have access to customer context via sessionAttributes:
- customer_id: The authenticated customer's ID (required)

KEY PRINCIPLES:
1. NEVER ask for customer_id - it's available in sessionAttributes!
```

**The Problem:**
- Console tests don't automatically populate sessionAttributes
- Agent sees no customer_id in session
- Agent asks user for customer_id OR hallucinates data
- **Agent never calls the Lambda function!**

### Issue 2: Action Group Not Explicitly Referenced

The agent instructions tell it to use sessionAttributes, but they don't explicitly tell it:
> "When you need to list projects, USE the list_projects action from your action group"

The agent might not realize it has actions available!

---

## 🛠️ Solution Options

### Option 1: Update Agent Instructions (RECOMMENDED)

**Update Scheduling Agent instructions to explicitly reference action groups:**

Add this section to the instructions:

```
AVAILABLE ACTIONS (use these instead of guessing!):

1. list_projects - Get all projects for a customer
   - When to use: User asks "show me my projects" or mentions customer_id
   - Required: customer_id (from sessionAttributes OR parsed from user query)
   - Optional: client_id (for B2B filtering)
   - ALWAYS use this action instead of making up project data!

2. get_available_dates - Check availability for a project
   - When to use: User wants to schedule/check dates for a project
   - Required: project_id ONLY
   - Returns: Available dates and request_id

3. get_time_slots - Get time slots for a specific date
   - When to use: After user selects a date from available dates
   - Required: project_id, date, request_id

4. confirm_appointment - Schedule the appointment
   - When to use: User confirms date and time selection
   - Required: project_id, date, time, request_id

5. reschedule_appointment - Change existing appointment
   - When to use: User wants to change scheduled appointment
   - Required: project_id, new_date, new_time, request_id

6. cancel_appointment - Cancel appointment
   - When to use: User wants to cancel
   - Required: project_id ONLY

CRITICAL: ALWAYS use these actions instead of generating responses from your knowledge!
If a user asks about projects, dates, or appointments, USE THE ACTIONS!
```

### Option 2: Provide Session Context in Console Tests

**When testing in Bedrock Console, include session attributes:**

Instead of just:
```
Show me all projects for customer CUST001
```

The console should have been initialized with session state (but this varies by console version).

### Option 3: Test with Python API (Proper Session Context)

Create a test script that includes sessionAttributes:

```python
import boto3

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

response = client.invoke_agent(
    agentId='IX24FSMTQH',
    agentAliasId='TSTALIASID',
    sessionId='test-session-123',
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
        print(event['chunk']['bytes'].decode())
```

This way, sessionAttributes are provided and the agent should use them!

---

## 📋 Step-by-Step Fix (RECOMMENDED PATH)

### Step 1: Update Scheduling Agent Instructions

1. **Go to:** https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/IX24FSMTQH

2. **Click "Edit"** button

3. **Scroll to "Advanced prompts"** section

4. **Enable "Override agent orchestration"** (if available) OR update the main instruction field

5. **Add** the "AVAILABLE ACTIONS" section from Option 1 above to the existing instructions

6. **Save** the changes

7. **Click "Prepare"** button ⚠️ CRITICAL!

8. **Wait** for status to become PREPARED (30-60 seconds)

### Step 2: Update Information Agent Instructions

Repeat the same process for Information Agent (C9ANXRIO8Y) with these actions:

```
AVAILABLE ACTIONS:

1. get_project_details - Get complete project information
   - When to use: User asks about a specific project
   - Required: project_id, customer_id
   - USE THIS instead of making up project details!

2. get_appointment_status - Get appointment status
   - When to use: User asks about appointment status
   - Required: project_id ONLY
   - USE THIS instead of guessing status!

3. get_working_hours - Get business hours
   - When to use: User asks about working hours
   - Optional: client_id (for location-specific hours)
   - USE THIS instead of assuming hours!

4. get_weather - Get weather forecast
   - When to use: User asks about weather
   - Required: location
   - USE THIS instead of making up weather!
```

### Step 3: Test with Session Context

Create a Python test script (see Option 3 above) that includes sessionAttributes.

### Step 4: Verify in CloudWatch

After testing, check CloudWatch logs to confirm Lambda was invoked:

```bash
# Watch Scheduling Lambda logs
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions \
  --follow \
  --region us-east-1

# In another terminal, run your test

# You should see logs showing:
# "Received event: {...}"
# "Extracted parameters: {'customer_id': 'CUST001'}"
# "Returning 3 projects for customer CUST001"
```

---

## 🎯 Expected Outcome After Fix

**Before fix:**
```
User: Show me all projects for customer CUST001
Agent: [Makes up fake data]
- Kitchen Remodel
- Bathroom Renovation
- etc.
```

**After fix:**
```
User: Show me all my projects
[sessionAttributes: {customer_id: 'CUST001'}]
Agent: [Calls list_projects action with CUST001]
Agent: I found 3 projects for you:

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

---

## 🧪 Quick Verification Test

After making the changes, test with this query:

**In Python API (with session context):**
```python
# Query: "Show me all my projects"
# sessionAttributes: {"customer_id": "CUST001", "customer_type": "B2C"}
# Expected: Lambda invocation, 3 real projects returned
```

**In Bedrock Console (if session context is available):**
```
Query: "Show me all my projects"
Setup session state with customer_id: CUST001
Expected: Lambda invocation, 3 real projects (12345, 12347, 12350)
```

**CloudWatch Verification:**
```bash
# If you see Lambda logs appear, the fix worked!
# If no logs appear, agent is still not using actions
```

---

## 📊 Current Status

| Component | Status | Issue |
|-----------|--------|-------|
| Lambda Functions | ✅ Working | None - returns correct mock data |
| Action Groups | ✅ Configured | ENABLED, linked to Lambda |
| Agent Status | ✅ PREPARED | None - agent prepared successfully |
| **Agent Instructions** | ⚠️ **ISSUE** | **Don't explicitly reference actions** |
| **Session Context** | ⚠️ **ISSUE** | **Console tests lack sessionAttributes** |
| **Lambda Invocations** | ❌ **FAILING** | **Agents not calling Lambda functions** |

---

## 🎓 Key Learnings

1. **Having action groups configured ≠ agents using them**
   - Action groups must be explicitly referenced in instructions
   - Agents need clear guidance on WHEN to use each action

2. **Session context is critical**
   - Console tests may not include sessionAttributes
   - Always test with proper session context via Python API

3. **CloudWatch is your friend**
   - If you don't see Lambda invocations, the action wasn't called
   - Check logs to verify agent behavior

4. **Agent instructions must be explicit**
   - "You have access to these actions" is NOT enough
   - Must say "USE THIS ACTION instead of generating a response"

---

## 📞 Next Steps

1. ✅ Read this guide
2. ⬜ Update Scheduling Agent instructions (add AVAILABLE ACTIONS section)
3. ⬜ Update Information Agent instructions (add AVAILABLE ACTIONS section)
4. ⬜ Update Notes Agent instructions (add AVAILABLE ACTIONS section)
5. ⬜ Prepare all agents
6. ⬜ Test with Python API (include sessionAttributes)
7. ⬜ Verify CloudWatch logs show Lambda invocations
8. ⬜ Confirm agents return real mock data (12345, 12347, 12350)

---

**Once complete, the agents will use Lambda functions and stop hallucinating!** 🎉
