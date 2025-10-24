# Agent Instructions Update Checklist - B2B Multi-Client Support

**Date:** 2025-10-17
**Purpose:** Update all agent instructions to support B2C/B2B multi-client scenarios
**Estimated Time:** 20-30 minutes (4 agents × 5 minutes each)

---

## ✅ Pre-Update Checklist

Before updating agent instructions:

- [ ] Backend API updated with B2B support ✅ Complete
- [ ] Lambda functions deployed with session fallback ⏳ Run `./scripts/deploy_lambda_functions.sh`
- [ ] OpenAPI schemas updated (snake_case, optional client_id) ✅ Complete
- [ ] Documentation reviewed (B2B_MULTI_CLIENT_INTEGRATION_GUIDE.md) ✅ Complete

---

## 🎯 Agent Update Order

**Update in this order:**

1. **Supervisor Agent** (5VTIWONUMO) - Most important, routes all requests
2. **Scheduling Agent** (IX24FSMTQH) - Handles customer_id and client_id
3. **Information Agent** (C9ANXRIO8Y) - Handles optional client_id
4. **Notes Agent** (G5BVBYEPUM) - Simplest, project-centric only
5. **Chitchat Agent** (2SUXQSWZOV) - No changes needed

---

## 📋 Update Steps (For Each Agent)

### General Process

1. **Open Agent in AWS Console**
   ```
   https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents
   ```

2. **Click on agent name**
   - Opens agent details page

3. **Click "Edit" button** (top right)
   - Opens agent builder

4. **Scroll to "Instructions for the Agent" section**

5. **Copy new instructions from setup guide**
   - See specific instructions below for each agent

6. **Replace existing instructions**
   - Select all (Cmd+A / Ctrl+A)
   - Paste new instructions

7. **Click "Save"** (bottom of page)

8. **Click "Prepare"** (top of page) ⚠️ CRITICAL!
   - Wait 30-60 seconds
   - Status changes: PREPARING → PREPARED

9. **Verify status**
   ```bash
   aws bedrock-agent get-agent \
     --agent-id <AGENT_ID> \
     --region us-east-1 \
     --query 'agent.agentStatus' \
     --output text
   ```
   Should return: `PREPARED`

---

## 1️⃣ Supervisor Agent (5VTIWONUMO)

**Priority:** 🔴 HIGHEST - Update this first!

**Console URL:**
```
https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/5VTIWONUMO
```

**New Instructions:** See `SUPERVISOR_AGENT_SETUP.md` → Step 2

**Key Changes:**
- ✅ Session attributes awareness (customer_id, client_id, customer_type)
- ✅ B2C vs B2B routing logic
- ✅ Location filtering principles
- ✅ Natural language location mapping
- ✅ Never ask for customer_id (already in session)

**Verification:**
```bash
aws bedrock-agent get-agent --agent-id 5VTIWONUMO --region us-east-1 --query 'agent.agentStatus' --output text
```

**Status:** [ ] Not Started  [ ] In Progress  [ ] ✅ Complete

---

## 2️⃣ Scheduling Agent (IX24FSMTQH)

**Priority:** 🟠 HIGH

**Console URL:**
```
https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/IX24FSMTQH
```

**New Instructions:** See `SCHEDULING_AGENT_SETUP.md` → Step 2

**Key Changes:**
- ✅ Session attributes usage
- ✅ When to use customer_id (listing projects)
- ✅ When to use client_id (B2B filtering)
- ✅ When NOT to ask for parameters (project-centric ops)
- ✅ Conversation examples for B2C and B2B

**Verification:**
```bash
aws bedrock-agent get-agent --agent-id IX24FSMTQH --region us-east-1 --query 'agent.agentStatus' --output text
```

**Status:** [ ] Not Started  [ ] In Progress  [ ] ✅ Complete

---

## 3️⃣ Information Agent (C9ANXRIO8Y)

**Priority:** 🟡 MEDIUM

**Console URL:**
```
https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/C9ANXRIO8Y
```

**New Instructions:** See `INFORMATION_AGENT_SETUP.md` → Step 2

**Key Changes:**
- ✅ Most operations are project-centric
- ✅ get_working_hours can work without parameters
- ✅ client_id optional for location-specific hours
- ✅ Conversation examples for default vs location-specific hours

**Verification:**
```bash
aws bedrock-agent get-agent --agent-id C9ANXRIO8Y --region us-east-1 --query 'agent.agentStatus' --output text
```

**Status:** [ ] Not Started  [ ] In Progress  [ ] ✅ Complete

---

## 4️⃣ Notes Agent (G5BVBYEPUM)

**Priority:** 🟢 LOW

**Console URL:**
```
https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/G5BVBYEPUM
```

**New Instructions:** See `NOTES_AGENT_SETUP.md` → Step 2

**Key Changes:**
- ✅ Notes are project-centric
- ✅ Only project_id needed
- ✅ No customer or client context required
- ✅ Same behavior for B2C and B2B

**Verification:**
```bash
aws bedrock-agent get-agent --agent-id G5BVBYEPUM --region us-east-1 --query 'agent.agentStatus' --output text
```

**Status:** [ ] Not Started  [ ] In Progress  [ ] ✅ Complete

---

## 5️⃣ Chitchat Agent (2SUXQSWZOV)

**Priority:** ⚪ NONE - No updates needed

**Console URL:**
```
https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/2SUXQSWZOV
```

**Action:** ✅ Skip - No B2B updates needed

**Reason:**
- Handles casual conversation only
- No data operations or business logic
- Same behavior for all customer types

**Status:** [ ] ✅ Not Applicable (Skip)

---

## 🧪 Post-Update Testing

After updating all agent instructions:

### Test 1: B2C Customer Flow

**Test in Supervisor Agent Console:**

```
User: Show me my projects for customer CUST001
```

**Expected:**
- ✅ Supervisor → Scheduling Agent (with customer_id from session)
- ✅ NO asking for customer_id again
- ✅ Returns projects

```
User: Schedule project PROJECT001
```

**Expected:**
- ✅ Supervisor → Scheduling Agent
- ✅ NO asking for customer_id or client_id
- ✅ Shows available dates

---

### Test 2: B2B Customer Flow

**Test in Supervisor Agent Console:**

```
User: Show me all projects for customer CUST_BIGCORP
```

**Expected:**
- ✅ Uses customer_id only (no client_id filter)
- ✅ Returns projects from all locations
- ✅ Groups by location if many projects

```
User: Show me Tampa projects
```

**Expected:**
- ✅ Supervisor maps "Tampa" to client_id
- ✅ Uses customer_id + client_id
- ✅ Returns Tampa projects only

---

### Test 3: Working Hours

```
User: What are your business hours?
```

**Expected:**
- ✅ Information Agent returns default hours
- ✅ NO parameters needed

```
User: What are Tampa office hours?
```

**Expected:**
- ✅ Supervisor maps Tampa to client_id
- ✅ Information Agent gets location-specific hours
- ✅ Returns Tampa hours

---

### Test 4: Notes (Project-Centric)

```
User: Add a note to project PROJECT001: Customer prefers mornings
```

**Expected:**
- ✅ Notes Agent uses project_id only
- ✅ NO asking for customer_id or client_id
- ✅ Confirms note added

---

## 🔍 Troubleshooting

### Issue 1: Agent Not Prepared After Update

**Symptom:** Agent status stuck in "PREPARING" or "FAILED"

**Solution:**
1. Wait 2-3 minutes (sometimes takes longer)
2. Refresh AWS Console page
3. Check if there are validation errors in the instructions
4. Try clicking "Prepare" again

### Issue 2: Agent Still Asking for customer_id

**Symptom:** Agent asks for customer_id even though user is authenticated

**Possible Causes:**
1. Backend not passing session attributes
2. Agent instructions not updated correctly
3. Agent not prepared after update

**Solution:**
1. Verify backend is passing `sessionAttributes`
2. Re-check agent instructions (copy-paste again)
3. Click "Prepare" button again
4. Test in Bedrock Console with explicit session attributes

### Issue 3: B2B Filtering Not Working

**Symptom:** Agent shows all projects when should show filtered by location

**Possible Causes:**
1. Supervisor not mapping location names to client_id
2. Scheduling Agent not using client_id parameter

**Solution:**
1. Check Supervisor instructions include location mapping logic
2. Verify Scheduling Agent instructions mention client_id usage
3. Check Lambda function handles optional client_id
4. Enable trace in Bedrock Console to see parameters passed

---

## 📊 Progress Tracking

**Update Progress:**

- [ ] Supervisor Agent (5VTIWONUMO)
- [ ] Scheduling Agent (IX24FSMTQH)
- [ ] Information Agent (C9ANXRIO8Y)
- [ ] Notes Agent (G5BVBYEPUM)
- [ ] Chitchat Agent (2SUXQSWZOV) - Skip

**Testing Progress:**

- [ ] B2C customer flow
- [ ] B2B all locations
- [ ] B2B filtered by location
- [ ] Working hours (default vs location)
- [ ] Notes (project-centric)

**Overall Status:**

- [ ] All agents updated
- [ ] All agents prepared
- [ ] All tests passed
- [ ] ✅ Ready for production

---

## 📚 Related Documentation

**For detailed instructions:**
- `SUPERVISOR_AGENT_SETUP.md` - Step 2: Update Agent Instructions
- `SCHEDULING_AGENT_SETUP.md` - Step 2: Update Agent Instructions
- `INFORMATION_AGENT_SETUP.md` - Step 2: Update Agent Instructions
- `NOTES_AGENT_SETUP.md` - Step 2: Update Agent Instructions
- `CHITCHAT_AGENT_SETUP.md` - Step 2: No updates needed

**For integration:**
- `B2B_MULTI_CLIENT_INTEGRATION_GUIDE.md` - Complete portal integration guide
- `B2B_IMPLEMENTATION_SUMMARY.md` - Quick reference

**For testing:**
- `B2B_MULTI_CLIENT_INTEGRATION_GUIDE.md` → Testing Scenarios

---

## ⏱️ Estimated Timeline

| Task | Time | Status |
|------|------|--------|
| Deploy Lambda functions | 5 min | ⏳ Pending |
| Update Supervisor Agent | 5 min | ⏳ Pending |
| Update Scheduling Agent | 5 min | ⏳ Pending |
| Update Information Agent | 5 min | ⏳ Pending |
| Update Notes Agent | 5 min | ⏳ Pending |
| Test all scenarios | 10 min | ⏳ Pending |
| **Total** | **35 min** | **⏳ Pending** |

---

**Last Updated:** 2025-10-17
**Status:** Ready for agent instruction updates
**Next Action:** Deploy Lambda functions, then update agents in order listed above
