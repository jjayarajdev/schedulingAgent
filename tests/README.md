# Tests Directory

**Purpose:** Test scripts for Bedrock Multi-Agent System

**Version:** 2.0
**Last Updated:** 2025-10-24

---

## 📁 Directory Structure

```
tests/
├── v2/                              # v2.0 Classification Tests (NEW)
│   ├── test_improved_classification.py  - Tests v2.0 prompt improvements
│   └── test_results_table.py           - Full 27-query regression test
├── integration/                     # Integration tests
├── unit/                           # Unit tests
├── LoadTest/                       # Load testing materials
├── test_production.py              # Production test suite
├── test_agent_action_groups.py     # Action group tests
└── run_tests.sh                    # Test runner script
```

---

## 🆕 v2.0 Classification Tests

### v2/test_improved_classification.py ⭐ **NEW**
**Purpose:** Validates v2.0 classification prompt improvements

**What it tests:**
- ✅ Previously misclassified queries (2 edge cases)
- ✅ Edge case validation (emotional expressions, shopping lists)
- ✅ 100% classification accuracy

**Fixed Queries:**
1. "I'm feeling stressed, just need to talk" → chitchat (was: notes)
2. "Add to my shopping list: coffee" → notes (was: information)

**Usage:**
```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
python3 tests/v2/test_improved_classification.py
```

**Expected Output:**
```
Total Queries:            6
Correct Classifications:  6
Accuracy:                 100.0%
Previously Wrong, Now Fixed: 2

✅ NO FAILURES - All queries correctly classified!
```

---

### v2/test_results_table.py ⭐ **NEW**
**Purpose:** Full regression test with 27 user queries

**What it tests:**
- ✅ 6 Chitchat queries
- ✅ 8 Scheduling queries
- ✅ 5 Information queries
- ✅ 4 Notes queries
- ✅ 4 Ambiguous edge cases

**Usage:**
```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
python3 tests/v2/test_results_table.py
```

**Expected Output:**
```
CLASSIFICATION ACCURACY: 100.0% (23/23 non-ambiguous queries)

📊 RESULTS BY CATEGORY:
Chitchat:    ✅ 6/6  (100.0%)
Scheduling:  ✅ 8/8  (100.0%)
Information: ✅ 5/5  (100.0%)
Notes:       ✅ 4/4  (100.0%)
```

**Key Features:**
- Color-coded results table
- Category-wise accuracy breakdown
- Performance timing
- Edge case analysis

---

## 📋 Production Tests

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

### v2.0 Documentation
- **v2.0 Improvements:** `../docs/IMPROVEMENTS_V2.md`
- **Routing Comparison:** `../docs/ROUTING_COMPARISON.md`
- **Quick Reference:** `../docs/ROUTING_QUICK_REFERENCE.md`
- **Summary:** `../IMPROVEMENTS_SUMMARY.md`

### General Documentation
- **Testing Guide:** `../docs/TESTING_COMPLETE_WORKFLOWS.md`
- **Mock Data:** `../docs/MOCK_DATA_REFERENCE.md`
- **Production Implementation:** `../docs/PRODUCTION_IMPLEMENTATION.md`
- **Scripts:** `../scripts/README.md`

---

## 🚀 Quick Test Commands

### Run v2.0 Classification Tests
```bash
# Test v2.0 improvements (6 queries)
python3 tests/v2/test_improved_classification.py

# Full regression test (27 queries)
python3 tests/v2/test_results_table.py
```

### Run Production Tests
```bash
# Production integration test
python3 tests/test_production.py

# Action group tests
python3 tests/test_agent_action_groups.py

# All tests
./tests/run_tests.sh
```

### Run Frontend Routing Tests
```bash
# Frontend routing validation
python3 frontend/backend/test_frontend_routing.py

# Comprehensive routing comparison
python3 frontend/backend/test_comprehensive_routing.py
```

### Run Infrastructure Tests
```bash
# Supervisor routing test (shows platform issues)
python3 infrastructure/terraform/test_supervisor_routing.py

# All agent tests
python3 infrastructure/terraform/run_all_agent_tests.py
```

---

**Version:** 2.0
**Last Updated:** 2025-10-24
**Classification Accuracy:** 100%
**Status:** ✅ Production Ready
