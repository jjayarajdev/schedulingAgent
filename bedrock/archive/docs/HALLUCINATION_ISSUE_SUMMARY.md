# Agent Hallucination Issue - Investigation Summary

**Date:** 2025-10-19
**Issue:** Agents returning fake/hallucinated data instead of calling Lambda functions
**Status:** ✅ ROOT CAUSE IDENTIFIED

---

## 🔍 Investigation Results

### What's Working ✅

1. **Lambda Functions (100% Working)**
   ```bash
   # Direct Lambda test with customer CUST001
   aws lambda invoke \
     --function-name scheduling-agent-scheduling-actions \
     --payload '{"actionGroup":"scheduling_actions","apiPath":"/list-projects",...}' \
     response.json

   # Returns CORRECT mock data:
   {
     "projects": [
       {"project_id": "12345", "category": "Flooring", "address": "123 Main St, Tampa, FL"},
       {"project_id": "12347", "category": "Windows", "address": "456 Oak Ave, Tampa, FL"},
       {"project_id": "12350", "category": "Deck Repair", "address": "789 Pine Dr, Clearwater, FL"}
     ]
   }
   ```
   ✅ All 3 Lambda functions tested and working

2. **Action Groups (Configured Correctly)**
   ```bash
   # Scheduling Agent action group status
   {
     "actionGroupName": "scheduling_actions",
     "actionGroupState": "ENABLED",
     "actionGroupExecutor": {
       "lambda": "arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-scheduling-actions"
     }
   }
   ```
   ✅ Action groups exist, ENABLED, linked to Lambda functions

3. **Agent Status (PREPARED)**
   ```bash
   # All agents status
   Scheduling Agent: PREPARED (last prepared 2025-10-19 07:26:15)
   Information Agent: PREPARED
   Notes Agent: PREPARED
   Supervisor Agent: PREPARED
   ```
   ✅ All agents successfully prepared

4. **Comprehensive Tests (100% Pass Rate)**
   ```
   Total Tests: 18
   Passed: ✅ 18 (100.0%)
   Failed: ❌ 0
   ```
   ✅ All automated tests passed

### What's NOT Working ❌

**CloudWatch Logs:**
```bash
# When user queries agents in console
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions --follow

# Result: NO LOG ENTRIES
# ❌ Lambda is NEVER invoked!
```

**Agent Behavior:**
```
User query: "Show me all projects for customer CUST001"

Agent response (WRONG):
- Kitchen Remodel (Building A)
- Bathroom Renovation (Building B)
- Exterior Painting (Building A)
- HVAC System Upgrade (Building C)

Expected response (CORRECT):
- Flooring Installation (12345) - Tampa, FL
- Windows Installation (12347) - Tampa, FL
- Deck Repair (12350) - Clearwater, FL
```

**❌ Agents are generating fake responses instead of calling Lambda functions!**

---

## 🎯 Root Cause

### Issue #1: Agent Instructions Don't Explicitly Reference Actions

**Current Scheduling Agent instructions:**
```
You are a scheduling specialist agent...

Your responsibilities:
1) Help customers view their projects
2) Check available dates and time slots for scheduling
3) Confirm new appointments
...

SESSION CONTEXT AWARENESS:
You have access to customer context via sessionAttributes...
```

**Problem:**
- Instructions describe WHAT the agent should do
- But they don't say HOW to do it (using action groups!)
- Agent assumes it should generate responses using LLM knowledge
- **Action groups are never triggered!**

**What's Missing:**
```
AVAILABLE ACTIONS (MUST USE THESE!):

1. list_projects - Get all projects for a customer
   USE THIS ACTION when user asks about projects
   DO NOT make up project data!

2. get_available_dates - Check availability
   USE THIS ACTION when user asks about dates
   DO NOT guess dates!

... (for all 6 actions)

CRITICAL: ALWAYS use these actions instead of generating responses!
```

### Issue #2: Console Testing Without Session Context

**Expected workflow:**
```
1. User logs into portal
2. Portal authenticates user
3. Portal sets sessionAttributes: {customer_id: "CUST001", customer_type: "B2C"}
4. User asks: "Show me my projects"
5. Agent sees customer_id in session
6. Agent calls list_projects action with customer_id
7. Lambda returns real projects
```

**What's happening in console:**
```
1. User types in console: "Show me all projects for customer CUST001"
2. No sessionAttributes set (console doesn't auto-populate them)
3. Agent sees customer_id in the query text
4. Agent instructions say "use sessionAttributes"
5. Agent is confused - should it parse query or use session?
6. Agent falls back to LLM knowledge and generates fake data
7. Lambda is never called
```

### Issue #3: Notes Agent Works, Others Don't

**Why Notes Agent works:**
- You manually tested it with proper event format
- You verified Lambda invocation in CloudWatch
- Parameters were correctly extracted after bugfix

**Why Scheduling/Information Agents don't work:**
- Testing via console without proper session setup
- Agent instructions don't explicitly trigger actions
- No Lambda invocations ever occur

---

## 📋 Solution (Step-by-Step)

### Step 1: Update Agent Instructions

**For each agent (Scheduling, Information, Notes):**

1. Open agent in AWS Console
2. Click "Edit"
3. Add "AVAILABLE ACTIONS" section to instructions
4. Explicitly list each action and when to use it
5. Add: "CRITICAL: USE THESE ACTIONS instead of generating responses!"
6. Save changes
7. **Click "Prepare"** ⚠️ MUST DO THIS!
8. Wait for PREPARED status

**See detailed instructions in:** [`HALLUCINATION_FIX_GUIDE.md`](./docs/HALLUCINATION_FIX_GUIDE.md)

### Step 2: Test with Proper Session Context

**Option A: Python API (Recommended)**
```python
import boto3

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

response = client.invoke_agent(
    agentId='5VTIWONUMO',  # Supervisor
    agentAliasId='HH2U7EZXMW',
    sessionId='test-123',
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

**Option B: Update Console Test Session**
- Some console versions allow setting session state
- Look for "Session attributes" or "Session state" section
- Add customer_id and customer_type

### Step 3: Verify in CloudWatch

```bash
# In one terminal, watch logs
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions \
  --follow \
  --region us-east-1

# In another terminal, run test
# You should see:
# "Received event: {...}"
# "Extracted parameters: {'customer_id': 'CUST001'}"
# "Returning 3 projects for customer CUST001"
```

**If you see logs appear:**
✅ **SUCCESS! Agent is now using Lambda functions!**

**If no logs appear:**
❌ Agent still not triggering actions - review instructions again

---

## 📊 Verification Checklist

Before marking this issue as resolved:

- [ ] Scheduling Agent instructions updated with AVAILABLE ACTIONS section
- [ ] Information Agent instructions updated with AVAILABLE ACTIONS section
- [ ] Notes Agent instructions updated with AVAILABLE ACTIONS section
- [ ] All agents prepared (status = PREPARED)
- [ ] Test query sent with proper sessionAttributes
- [ ] CloudWatch logs show Lambda invocation
- [ ] Agent returns real mock data (12345, 12347, 12350)
- [ ] NO hallucinated data (Kitchen Remodel, Website Redesign, etc.)

---

## 🎓 Key Takeaways

1. **Configuration ≠ Usage**
   - Having action groups configured doesn't mean agents use them
   - Instructions must explicitly tell agents WHEN and HOW to use actions

2. **Session Context is Critical**
   - sessionAttributes are how agents get customer_id
   - Console testing may not populate session correctly
   - Always test with Python API for proper session context

3. **CloudWatch Confirms Action Usage**
   - If Lambda logs appear → actions are being used ✅
   - If no logs appear → actions are NOT being used ❌
   - Use this to verify fixes worked

4. **Explicit > Implicit**
   - "You are responsible for scheduling" is too vague
   - "USE list_projects action to show projects" is clear
   - Agents need explicit guidance on action usage

---

## 📁 Related Documentation

- **Fix Guide:** [`docs/HALLUCINATION_FIX_GUIDE.md`](./docs/HALLUCINATION_FIX_GUIDE.md)
- **Mock Data Reference:** [`docs/MOCK_DATA_REFERENCE.md`](./docs/MOCK_DATA_REFERENCE.md)
- **Testing Guide:** [`docs/TESTING_COMPLETE_WORKFLOWS.md`](./docs/TESTING_COMPLETE_WORKFLOWS.md)
- **Agent Setup:**
  - [`docs/SCHEDULING_AGENT_SETUP.md`](./docs/SCHEDULING_AGENT_SETUP.md)
  - [`docs/INFORMATION_AGENT_SETUP.md`](./docs/INFORMATION_AGENT_SETUP.md)
  - [`docs/NOTES_AGENT_SETUP.md`](./docs/NOTES_AGENT_SETUP.md)

---

## 📞 Next Actions

**High Priority:**
1. Update all agent instructions with AVAILABLE ACTIONS sections
2. Prepare all agents
3. Test with Python API (include sessionAttributes)
4. Verify CloudWatch logs show Lambda invocations

**Medium Priority:**
5. Update web portal to properly set sessionAttributes
6. Add session context to all API calls
7. Update testing documentation with session examples

**Low Priority:**
8. Create automated tests with session context
9. Document console testing limitations
10. Add session validation to agents

---

**Date Completed:** (Pending)
**Fixed By:** (Pending)
**Verification:** (Pending)

---

**Once instructions are updated and agents prepared, hallucination should stop!** 🎉
