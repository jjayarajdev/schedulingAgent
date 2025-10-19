# Tests Directory

**Purpose:** Test scripts for Bedrock Multi-Agent System

**Last Updated:** 2025-10-19

---

## 📋 Available Tests

### test_agent_with_session.py ⭐
**Purpose:** Complete test suite with proper session context

**What it tests:**
1. List Projects - Returns real mock data (12345, 12347, 12350)
2. Get Project Details - Returns Flooring Installation details
3. Get Appointment Status - Returns scheduled date/time
4. Get Working Hours - Returns business hours
5. Check Availability - Returns available dates

**Key Features:**
- ✅ Includes sessionAttributes (customer_id, customer_type)
- ✅ Tests B2C customer scenarios
- ✅ Verifies real mock data returned
- ✅ Checks for NO hallucinated data
- ✅ Color-coded pass/fail results
- ✅ CloudWatch verification instructions

**Usage:**
```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock

./tests/test_agent_with_session.py
```

**Prerequisites:**
1. Run `scripts/update_agent_instructions.sh` ✅
2. Run `scripts/update_collaborator_aliases.sh` ⏳ **MUST DO**

**Expected Output:**
```
Total Tests: 5
Passed: ✅ 5
Failed: ❌ 0
Success Rate: 100.0%
```

---

## 🎯 Testing Workflow

### Step 1: Lambda Functions (Direct Test)
```bash
cd ../scripts
./test_lambdas.sh
```
This tests Lambda functions directly, bypassing agents.

**Expected:** 8/8 tests pass

---

### Step 2: Agents with Session Context (Integration Test)
```bash
cd ../tests
./test_agent_with_session.py
```
This tests the complete multi-agent flow with proper session context.

**Expected:** 5/5 tests pass

---

### Step 3: CloudWatch Verification
```bash
# In another terminal, watch for Lambda invocations
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions --follow --region us-east-1

# Then run the test
./test_agent_with_session.py
```

**Expected:** CloudWatch logs appear showing Lambda invocations!

---

## 🔍 What Each Test Verifies

### Test 1: List Projects
**Query:** "Show me all my projects"
**Session:** `{customer_id: "CUST001", customer_type: "B2C"}`

**Expected Response:**
- Project 12345 - Flooring Installation, Tampa
- Project 12347 - Windows Installation, Tampa
- Project 12350 - Deck Repair, Clearwater

**Verifies:**
- ✅ Lambda function `list_projects` called
- ✅ Real mock data returned
- ❌ NO hallucinated data (Kitchen Remodel, etc.)

---

### Test 2: Get Project Details
**Query:** "Tell me about project 12345"
**Session:** `{customer_id: "CUST001", customer_type: "B2C"}`

**Expected Response:**
- Project ID: 12345
- Type: Flooring Installation
- Location: 123 Main St, Tampa, FL
- Order: ORD-2025-001
- Technician: John Smith

**Verifies:**
- ✅ Lambda function `get_project_details` called
- ✅ Complete project information returned

---

### Test 3: Get Appointment Status
**Query:** "What's the appointment status for project 12345?"
**Session:** `{customer_id: "CUST001", customer_type: "B2C"}`

**Expected Response:**
- Status: Scheduled
- Date: 2025-10-15
- Time: 8:00 AM - 12:00 PM
- Technician: John Smith
- Duration: 4 hours

**Verifies:**
- ✅ Lambda function `get_appointment_status` called
- ✅ Appointment details returned

---

### Test 4: Get Working Hours
**Query:** "What are your business hours?"
**Session:** `{customer_id: "CUST001", customer_type: "B2C"}`

**Expected Response:**
- Monday - Friday: 9:00 AM - 6:00 PM
- Saturday: 10:00 AM - 3:00 PM
- Sunday: Closed

**Verifies:**
- ✅ Lambda function `get_working_hours` called
- ✅ Business hours returned

---

### Test 5: Check Availability
**Query:** "What dates are available for project 12347?"
**Session:** `{customer_id: "CUST001", customer_type: "B2C"}`

**Expected Response:**
- List of available dates (next 10 weekdays)
- 2025 dates

**Verifies:**
- ✅ Lambda function `get_available_dates` called
- ✅ Available dates returned

---

## 🐛 Troubleshooting

### Tests Failing?

**Check:**

1. **Agent instructions updated?**
   ```bash
   aws bedrock-agent get-agent --agent-id IX24FSMTQH --region us-east-1 \
     --query 'agent.instruction' --output text | grep "AVAILABLE ACTIONS"
   ```
   Should show: AVAILABLE ACTIONS section

2. **Collaborators using DRAFT aliases?**
   ```bash
   aws bedrock-agent list-agent-collaborators --agent-id 5VTIWONUMO \
     --agent-version DRAFT --region us-east-1 | grep TSTALIASID
   ```
   Should show: Multiple TSTALIASID matches

3. **Agents prepared?**
   ```bash
   aws bedrock-agent get-agent --agent-id IX24FSMTQH --region us-east-1 \
     --query 'agent.agentStatus'
   ```
   Should return: "PREPARED"

4. **CloudWatch logs showing Lambda invocations?**
   ```bash
   aws logs tail /aws/lambda/scheduling-agent-scheduling-actions \
     --since 5m --region us-east-1
   ```
   Should show: Recent Lambda logs

---

### Common Issues

**Issue:** Tests pass but no CloudWatch logs
**Solution:** Lambda not being invoked, run `scripts/update_collaborator_aliases.sh`

**Issue:** Tests return hallucinated data
**Solution:** Collaborators using old agent versions, run `scripts/update_collaborator_aliases.sh`

**Issue:** Tests timeout or hang
**Solution:** Check AWS credentials and region configuration

---

## 📊 Test Data Reference

For complete mock data reference, see:
- `../docs/MOCK_DATA_REFERENCE.md`

**Valid Project IDs:**
- 12345 - Flooring Installation (Scheduled)
- 12347 - Windows Installation (Pending)
- 12350 - Deck Repair (Pending)

**Valid Customer ID:**
- CUST001 (B2C customer with 3 projects)

---

## 📚 Related Documentation

- **Testing Guide:** `../docs/TESTING_COMPLETE_WORKFLOWS.md`
- **Mock Data:** `../docs/MOCK_DATA_REFERENCE.md`
- **Hallucination Fix:** `../COMPLETE_FIX_DEPLOYMENT.md`
- **Scripts:** `../scripts/README.md`

---

**Last Updated:** 2025-10-19
**Test Suite:** test_agent_with_session.py
**Status:** ✅ Working (requires collaborator alias update)
