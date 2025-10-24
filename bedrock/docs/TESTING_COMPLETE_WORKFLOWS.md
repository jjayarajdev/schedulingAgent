# Complete Workflow Testing Guide

**Purpose:** Test multi-agent collaboration and complete workflows
**Environment:** Mock API mode (USE_MOCK_API=true)
**Last Updated:** 2025-10-19

---

## 📋 Table of Contents

1. [AWS CLI Testing](#aws-cli-testing)
2. [AWS Bedrock Console Testing](#aws-bedrock-console-testing)
3. [Complete Workflows](#complete-workflows)
4. [Troubleshooting](#troubleshooting)

---

## 🖥️ AWS CLI Testing

### Test Individual Lambda Functions

#### 1. Test Scheduling Lambda

```bash
# List Projects
aws lambda invoke \
  --function-name scheduling-agent-scheduling-actions \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "actionGroup": "scheduling_actions",
    "apiPath": "/list-projects",
    "httpMethod": "POST",
    "requestBody": {
      "content": {
        "application/json": {
          "properties": [
            {"name": "customer_id", "type": "string", "value": "CUST001"}
          ]
        }
      }
    }
  }' \
  --region us-east-1 \
  response.json && cat response.json | jq
```

**Expected:** Returns 3 mock projects (12345, 12347, 12350)

```bash
# Get Available Dates
aws lambda invoke \
  --function-name scheduling-agent-scheduling-actions \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "actionGroup": "scheduling_actions",
    "apiPath": "/get-available-dates",
    "httpMethod": "POST",
    "requestBody": {
      "content": {
        "application/json": {
          "properties": [
            {"name": "project_id", "type": "string", "value": "12347"}
          ]
        }
      }
    }
  }' \
  --region us-east-1 \
  response.json && cat response.json | jq
```

**Expected:** Returns next 10 weekdays with available dates

---

#### 2. Test Information Lambda

```bash
# Get Project Details
aws lambda invoke \
  --function-name scheduling-agent-information-actions \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "actionGroup": "information_actions",
    "apiPath": "/get-project-details",
    "httpMethod": "POST",
    "requestBody": {
      "content": {
        "application/json": {
          "properties": [
            {"name": "project_id", "type": "string", "value": "12345"},
            {"name": "customer_id", "type": "string", "value": "CUST001"}
          ]
        }
      }
    }
  }' \
  --region us-east-1 \
  response.json && cat response.json | jq
```

**Expected:** Returns Flooring Installation project details (Tampa, FL)

```bash
# Get Working Hours
aws lambda invoke \
  --function-name scheduling-agent-information-actions \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "actionGroup": "information_actions",
    "apiPath": "/get-working-hours",
    "httpMethod": "POST",
    "requestBody": {
      "content": {
        "application/json": {
          "properties": []
        }
      }
    }
  }' \
  --region us-east-1 \
  response.json && cat response.json | jq
```

**Expected:** Returns Mon-Fri 8AM-6PM, Sat 9AM-4PM, Sun Closed

---

#### 3. Test Notes Lambda

```bash
# Add Note
aws lambda invoke \
  --function-name scheduling-agent-notes-actions \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "actionGroup": "notes_actions",
    "apiPath": "/add-note",
    "httpMethod": "POST",
    "requestBody": {
      "content": {
        "application/json": {
          "properties": [
            {"name": "project_id", "type": "string", "value": "12345"},
            {"name": "note_text", "type": "string", "value": "Customer prefers morning appointments"},
            {"name": "author", "type": "string", "value": "Test Agent"}
          ]
        }
      }
    }
  }' \
  --region us-east-1 \
  response.json && cat response.json | jq
```

**Expected:** Confirms note added with note_id and timestamp

```bash
# List Notes
aws lambda invoke \
  --function-name scheduling-agent-notes-actions \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "actionGroup": "notes_actions",
    "apiPath": "/list-notes",
    "httpMethod": "POST",
    "requestBody": {
      "content": {
        "application/json": {
          "properties": [
            {"name": "project_id", "type": "string", "value": "12345"}
          ]
        }
      }
    }
  }' \
  --region us-east-1 \
  response.json && cat response.json | jq
```

**Expected:** Returns all notes for project 12345

---

### Test Bedrock Agents via CLI

#### Test Supervisor Agent

```bash
# Invoke Supervisor Agent
aws bedrock-agent-runtime invoke-agent \
  --agent-id 5VTIWONUMO \
  --agent-alias-id TSTALIASID \
  --session-id test-session-$(date +%s) \
  --input-text "Show me all projects for customer CUST001" \
  --region us-east-1 \
  response.txt

# View response (streaming format)
cat response.txt
```

**Note:** The response is in event stream format. For easier reading, use the Bedrock Console.

---

## 🌐 AWS Bedrock Console Testing

### Test Individual Agents

#### 1. Test Supervisor Agent (Orchestrator)

**URL:** https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/5VTIWONUMO

**Steps:**
1. Click **"Test"** button (right side panel)
2. Enter test query
3. View response and trace

**Test Queries:**

```
Query 1: Show me all projects for customer CUST001
Expected: Routes to Scheduling Agent, returns 3 projects

Query 2: Tell me about project 12345 for customer CUST001
Expected: Routes to Information Agent, returns project details

Query 3: Add a note to project 12345: Customer prefers mornings
Expected: Routes to Notes Agent, confirms note added

Query 4: What are your business hours?
Expected: Routes to Information Agent, returns working hours

Query 5: Hello!
Expected: Routes to Chitchat Agent, friendly greeting
```

---

#### 2. Test Scheduling Agent

**URL:** https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/IX24FSMTQH

**Test Queries:**

```
Query 1: Show me all projects for customer CUST001
Expected: Returns 3 projects (12345 Flooring, 12347 Windows, 12350 Deck)

Query 2: What dates are available for project 12347?
Expected: Returns next 10 weekdays

Query 3: Show me time slots for project 12347 on [pick a date]
Expected: Returns time slots from 8 AM to 5 PM

Query 4: Book project 12347 for [date] at 10:00 AM
Expected: Confirms appointment (requires request_id from previous query)
```

---

#### 3. Test Information Agent

**URL:** https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/C9ANXRIO8Y

**Test Queries:**

```
Query 1: Tell me about project 12345 for customer CUST001
Expected: Returns Flooring Installation details (Tampa, 4 hours)

Query 2: What's the appointment status for project 12345?
Expected: Returns Scheduled status, Oct 15, 8 AM - 12 PM

Query 3: What are your business hours?
Expected: Returns Mon-Fri 8 AM - 6 PM, Sat 9 AM - 4 PM

Query 4: What's the weather like in Tampa?
Expected: Returns mock weather (Partly Cloudy, 75°F)
```

---

#### 4. Test Notes Agent

**URL:** https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/G5BVBYEPUM

**Test Queries:**

```
Query 1: Add a note to project 12345: Customer prefers morning appointments
Expected: Confirms note added with timestamp

Query 2: Show me all notes for project 12345
Expected: Returns all notes (includes previously added note)

Query 3: Add a note to project 12347: Gate code is 1234
Expected: Confirms note added to different project
```

---

#### 5. Test Chitchat Agent

**URL:** https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/2SUXQSWZOV

**Test Queries:**

```
Query 1: Hello! How are you?
Expected: Friendly greeting, offers to help

Query 2: What services do you offer?
Expected: Describes scheduling services

Query 3: Can you schedule an appointment?
Expected: Redirects to Scheduling specialist
```

---

## 🔄 Complete Workflows

### Workflow 1: Complete Scheduling Process

**Test in Supervisor Agent Console:**

```
Step 1: "Show me all projects for customer CUST001"
→ Expected: Returns 3 projects

Step 2: "Tell me about project 12347"
→ Expected: Windows Installation, Tampa, Pending status

Step 3: "What dates are available for project 12347?"
→ Expected: Returns next 10 weekdays

Step 4: "Show me time slots for project 12347 on [select a date from step 3]"
→ Expected: Returns 8 AM - 5 PM time slots

Step 5: "Book project 12347 for [date] at 10:00 AM"
→ Expected: Confirms appointment scheduled

Step 6: "Add a note to project 12347: Customer requested morning slot"
→ Expected: Confirms note added

Step 7: "What's the appointment status for project 12347?"
→ Expected: Shows newly scheduled appointment
```

**What This Tests:**
- ✅ Multi-agent collaboration (Supervisor → Scheduling, Information, Notes)
- ✅ Context retention across multiple steps
- ✅ Parameter passing between agents
- ✅ Mock data consistency

---

### Workflow 2: Project Information Gathering

**Test in Supervisor Agent Console:**

```
Step 1: "Show me details for project 12345"
→ Expected: Flooring Installation, Tampa, Scheduled Oct 15

Step 2: "What's the appointment status?"
→ Expected: Scheduled, 8 AM - 12 PM, technician John Smith

Step 3: "Show me all notes for this project"
→ Expected: Returns any existing notes

Step 4: "What's the weather like in Tampa?"
→ Expected: Partly Cloudy, 75°F

Step 5: "Add a note: Customer confirmed appointment time"
→ Expected: Note added successfully
```

**What This Tests:**
- ✅ Information Agent actions (project details, status, weather)
- ✅ Notes Agent integration
- ✅ Context awareness (remembers project_id from Step 1)

---

### Workflow 3: B2B Multi-Client Scenario

**Test in Supervisor Agent Console:**

```
Step 1: "Show me all projects for customer CUST_BIGCORP"
→ Expected: Returns all projects across all locations

Step 2: "Show me Tampa projects only"
→ Expected: Filters to Tampa location (if supervisor maps Tampa → client_id)

Step 3: "What are Tampa office hours?"
→ Expected: Returns location-specific hours (if implemented)

Step 4: "Schedule a Tampa project"
→ Expected: Shows Tampa projects for scheduling
```

**What This Tests:**
- ✅ B2B customer handling
- ✅ Location filtering with client_id
- ✅ Session attributes usage
- ✅ Natural language location mapping

---

### Workflow 4: Chitchat + Task Workflow

**Test in Supervisor Agent Console:**

```
Step 1: "Hello! How are you?"
→ Expected: Routes to Chitchat, friendly greeting

Step 2: "I need to schedule an appointment"
→ Expected: Routes to Scheduling, asks for customer ID or shows projects

Step 3: "Show me my projects for customer CUST001"
→ Expected: Returns 3 projects

Step 4: "Thanks for your help!"
→ Expected: Routes to Chitchat, warm farewell
```

**What This Tests:**
- ✅ Dynamic routing between Chitchat and task agents
- ✅ Context switching
- ✅ Supervisor orchestration

---

## 🔍 Viewing Agent Traces

### Enable Trace in Bedrock Console

1. In the test panel, check **"Show trace"** checkbox
2. Run a query
3. View the trace to see:
   - Which agents were invoked
   - What parameters were passed
   - Lambda function responses
   - Agent reasoning and decisions

### Example Trace Analysis

```
User Query: "Show me all projects for customer CUST001"

Trace:
1. Supervisor Agent receives query
2. Supervisor identifies intent: list_projects
3. Supervisor routes to Scheduling Agent (IX24FSMTQH)
4. Scheduling Agent extracts parameter: customer_id = CUST001
5. Scheduling Agent invokes Lambda: scheduling-agent-scheduling-actions
6. Lambda action: list-projects
7. Lambda returns: 3 projects
8. Scheduling Agent formats response
9. Supervisor returns final response to user
```

---

## 📊 Monitoring with CloudWatch

### View Real-Time Lambda Logs

```bash
# Watch Scheduling Lambda logs
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions \
  --follow \
  --region us-east-1

# Watch Information Lambda logs
aws logs tail /aws/lambda/scheduling-agent-information-actions \
  --follow \
  --region us-east-1

# Watch Notes Lambda logs
aws logs tail /aws/lambda/scheduling-agent-notes-actions \
  --follow \
  --region us-east-1
```

### View Agent Logs

```bash
# Supervisor Agent logs
aws logs tail /aws/bedrock/agents/5VTIWONUMO \
  --follow \
  --region us-east-1

# Scheduling Agent logs
aws logs tail /aws/bedrock/agents/IX24FSMTQH \
  --follow \
  --region us-east-1
```

### Search for Errors

```bash
# Find errors in last hour
aws logs filter-log-events \
  --log-group-name /aws/lambda/scheduling-agent-notes-actions \
  --start-time $(($(date +%s) - 3600))000 \
  --filter-pattern "ERROR" \
  --region us-east-1
```

---

## 🐛 Troubleshooting

### Issue 1: Agent Returns "Validation Error"

**Symptom:** Lambda receives empty parameters `{}`

**Check:**
```bash
# View recent Lambda logs to see what parameters were received
aws logs tail /aws/lambda/scheduling-agent-notes-actions \
  --since 5m \
  --region us-east-1 | grep "Extracted parameters"
```

**Solution:**
- Verify agent has action group configured
- Check OpenAPI schema matches Lambda expectations
- Ensure Lambda parameter extraction handles `properties` array

---

### Issue 2: Agent Not Routing to Collaborators

**Symptom:** Supervisor tries to handle request directly instead of routing

**Check:**
```bash
# Verify collaborators are configured
aws bedrock-agent list-agent-collaborators \
  --agent-id 5VTIWONUMO \
  --agent-version DRAFT \
  --region us-east-1
```

**Solution:**
- Update Supervisor instructions to emphasize routing
- Verify all collaborator agents are PREPARED
- Check agent instructions don't conflict with routing logic

---

### Issue 3: "Agent Not Found" Error

**Symptom:** Supervisor cannot find collaborator agent

**Check:**
```bash
# Check all agent statuses
aws bedrock-agent get-agent --agent-id 5VTIWONUMO --region us-east-1 --query 'agent.agentStatus'
aws bedrock-agent get-agent --agent-id IX24FSMTQH --region us-east-1 --query 'agent.agentStatus'
aws bedrock-agent get-agent --agent-id C9ANXRIO8Y --region us-east-1 --query 'agent.agentStatus'
aws bedrock-agent get-agent --agent-id G5BVBYEPUM --region us-east-1 --query 'agent.agentStatus'
```

**Solution:**
- Ensure all agents show status: PREPARED
- Click "Prepare" button for each agent
- Verify agent IDs in collaborator configuration

---

### Issue 4: Mock Data Not Returning

**Symptom:** Lambda returns errors or empty data

**Check:**
```bash
# Verify mock mode is enabled
aws lambda get-function-configuration \
  --function-name scheduling-agent-scheduling-actions \
  --region us-east-1 \
  --query 'Environment.Variables.USE_MOCK_API'
```

**Solution:**
- Should return: "true"
- If not, enable mock mode:
```bash
aws lambda update-function-configuration \
  --function-name scheduling-agent-scheduling-actions \
  --environment Variables={USE_MOCK_API=true} \
  --region us-east-1
```

---

## ✅ Success Criteria

### Individual Lambda Functions
- ✅ All 3 Lambda functions return 200 status
- ✅ Mock data is returned correctly
- ✅ Parameters are extracted properly
- ✅ No validation errors

### Individual Agents
- ✅ Each agent responds to test queries
- ✅ Agents invoke correct Lambda functions
- ✅ Responses are formatted correctly
- ✅ No timeout errors

### Multi-Agent Workflows
- ✅ Supervisor routes to correct specialist agents
- ✅ Context is maintained across multiple steps
- ✅ Complete workflows execute successfully
- ✅ All agents collaborate smoothly

### Traces
- ✅ Trace shows agent invocation sequence
- ✅ Parameters passed correctly between agents
- ✅ Lambda responses visible in trace
- ✅ No errors in trace logs

---

## 📚 Related Documentation

- **[MOCK_DATA_REFERENCE.md](./MOCK_DATA_REFERENCE.md)** - Valid mock data and test queries
- **[SUPERVISOR_AGENT_SETUP.md](./SUPERVISOR_AGENT_SETUP.md)** - Supervisor agent configuration
- **[B2B_MULTI_CLIENT_INTEGRATION_GUIDE.md](./B2B_MULTI_CLIENT_INTEGRATION_GUIDE.md)** - B2B testing scenarios
- **[AGENT_INSTRUCTIONS_UPDATE_CHECKLIST.md](./AGENT_INSTRUCTIONS_UPDATE_CHECKLIST.md)** - Post-update testing

---

## 🚀 Quick Test Script

Copy-paste this entire script to test all Lambda functions:

```bash
#!/bin/bash

echo "=== Testing All Lambda Functions ==="
echo ""

# Test Scheduling Lambda
echo "1. Testing Scheduling Lambda - List Projects"
aws lambda invoke \
  --function-name scheduling-agent-scheduling-actions \
  --cli-binary-format raw-in-base64-out \
  --payload '{"actionGroup":"scheduling_actions","apiPath":"/list-projects","httpMethod":"POST","requestBody":{"content":{"application/json":{"properties":[{"name":"customer_id","type":"string","value":"CUST001"}]}}}}' \
  --region us-east-1 \
  response.json && cat response.json | jq -r '.response.httpStatusCode'
echo ""

# Test Information Lambda
echo "2. Testing Information Lambda - Get Project Details"
aws lambda invoke \
  --function-name scheduling-agent-information-actions \
  --cli-binary-format raw-in-base64-out \
  --payload '{"actionGroup":"information_actions","apiPath":"/get-project-details","httpMethod":"POST","requestBody":{"content":{"application/json":{"properties":[{"name":"project_id","type":"string","value":"12345"},{"name":"customer_id","type":"string","value":"CUST001"}]}}}}' \
  --region us-east-1 \
  response.json && cat response.json | jq -r '.response.httpStatusCode'
echo ""

# Test Notes Lambda
echo "3. Testing Notes Lambda - Add Note"
aws lambda invoke \
  --function-name scheduling-agent-notes-actions \
  --cli-binary-format raw-in-base64-out \
  --payload '{"actionGroup":"notes_actions","apiPath":"/add-note","httpMethod":"POST","requestBody":{"content":{"application/json":{"properties":[{"name":"project_id","type":"string","value":"12345"},{"name":"note_text","type":"string","value":"Test note"}]}}}}' \
  --region us-east-1 \
  response.json && cat response.json | jq -r '.response.httpStatusCode'
echo ""

echo "=== All Tests Complete ==="
echo "✅ All Lambda functions should return 200"
```

**Save as:** `test_lambdas.sh`

**Run:**
```bash
chmod +x test_lambdas.sh
./test_lambdas.sh
```

---

**Last Updated:** 2025-10-19
**Status:** Ready for testing
**Mock Mode:** Enabled (USE_MOCK_API=true)
