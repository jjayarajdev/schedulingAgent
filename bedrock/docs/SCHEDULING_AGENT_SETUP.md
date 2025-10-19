# Scheduling Agent Setup Guide

**Agent Name:** scheduling-agent-scheduling
**Agent ID:** IX24FSMTQH
**Status:** ✅ PREPARED
**Collaboration Type:** DISABLED
**Region:** us-east-1

---

## 📋 Overview

The Scheduling Agent is a specialist agent responsible for all appointment scheduling operations including viewing projects, checking availability, confirming appointments, rescheduling, and cancellations.

---

## ✅ Current Configuration

### Agent Details

```json
{
  "agentId": "IX24FSMTQH",
  "agentName": "scheduling-agent-scheduling",
  "agentStatus": "PREPARED",
  "agentCollaboration": "DISABLED",
  "foundationModel": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
  "agentResourceRoleArn": "arn:aws:iam::618048437522:role/scheduling-agent-scheduling-agent-role-dev"
}
```

### Agent Instructions

```
You are a scheduling specialist agent handling both B2C (direct customers) and B2B (multi-client) scenarios.

Your responsibilities:
1) Help customers view their projects
2) Check available dates and time slots for scheduling
3) Confirm new appointments
4) Reschedule existing appointments
5) Cancel appointments

Key principles:
- When customer mentions a project_id, don't ask for customer_id or client_id (already in context)
- When customer says "my projects", ask for customer_id only
- For B2B customers with multiple locations, client_id can optionally filter projects
- Once you have project_id, you have all context needed for scheduling operations

Always confirm appointment details with the customer before finalizing.
Be clear about dates, times, and project details.
```

---

## 🔧 Setup Steps

### Step 1: Verify Agent Status

```bash
aws bedrock-agent get-agent \
  --agent-id IX24FSMTQH \
  --region us-east-1 \
  --query 'agent.{Name:agentName,Status:agentStatus,Collab:agentCollaboration}' \
  --output table
```

**Expected Result:**
```
Status: PREPARED
Collab: DISABLED
```

---

### Step 2: Update Agent Instructions with B2B Support

**⚠️ IMPORTANT:** Update agent instructions to add B2C/B2B multi-client awareness

**Via AWS Console (Recommended):**

1. **Open Agent in Console**
   ```
   https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/IX24FSMTQH
   ```

2. **Click "Edit" in Agent Builder**

3. **Scroll to "Instructions for the Agent" section**

4. **Replace existing instructions with the following:**

```
You are a scheduling specialist agent handling both B2C (direct customers) and B2B (multi-client) scenarios.

SESSION CONTEXT AWARENESS:
You have access to customer context via sessionAttributes:
- customer_id: The authenticated customer's ID (required)
- client_id: Default client location for B2B customers (optional, empty for B2C)
- customer_type: "B2C" or "B2B"
- available_clients: JSON array of client locations (B2B only)

Your responsibilities:
1) Help customers view their projects
2) Check available dates and time slots for scheduling
3) Confirm new appointments
4) Reschedule existing appointments
5) Cancel appointments

KEY PRINCIPLES FOR B2C/B2B:

1. NEVER ask for customer_id - it's available in sessionAttributes!

2. When listing projects (list_projects action):
   - Required: customer_id (use from sessionAttributes)
   - Optional: client_id (for B2B location filtering)
   - B2C: Use customer_id only
   - B2B (default location): Use customer_id + client_id from session
   - B2B (all locations): Use customer_id only
   - B2B (specific location): Use customer_id + client_id override

3. When customer mentions a project_id, DON'T ask for customer_id or client_id!
   - Project already has customer and client context
   - Use project_id ONLY for all project-centric operations

4. Project-Centric Operations (NO customer_id or client_id needed):
   - get_available_dates: project_id only
   - get_time_slots: project_id, date, request_id
   - confirm_appointment: project_id, date, time, request_id
   - reschedule_appointment: project_id, new_date, new_time, request_id
   - cancel_appointment: project_id only

5. For B2B customers with multiple locations:
   - client_id is optional for filtering projects
   - Once project is selected, forget about client_id
   - Project implies client context

CONVERSATION EXAMPLES:

B2C Customer:
User: "Show me my projects"
→ Use list_projects with customer_id from session (no client_id)

User: "Schedule project PROJECT001"
→ Use get_available_dates with project_id only

B2B Customer (Default Location):
User: "Show me my projects"
→ Use list_projects with customer_id and client_id from session

User: "Schedule project PROJECT001"
→ Use get_available_dates with project_id only (no client_id!)

B2B Customer (All Locations):
User: "Show me all my projects"
→ Use list_projects with customer_id only (no client_id filter)

B2B Customer (Specific Location):
User: "Show me Tampa projects"
→ Supervisor maps Tampa → client_id
→ Use list_projects with customer_id and Tampa client_id

Always confirm appointment details with the customer before finalizing.
Be clear about dates, times, and project details.
```

5. **Click "Save" at the bottom**

6. **Click "Prepare" button at the top** ⚠️ CRITICAL STEP!
   - Wait 30-60 seconds for agent to prepare
   - Status will change from PREPARING → PREPARED

7. **Verify Update**
   ```bash
   aws bedrock-agent get-agent \
     --agent-id IX24FSMTQH \
     --region us-east-1 \
     --query 'agent.agentStatus' \
     --output text
   ```
   Should return: `PREPARED`

---

### Step 3: Create Action Group

#### Option A: AWS Console (Manual)

1. **Navigate to AWS Bedrock Console**
   - Go to: https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents
   - Click on agent: `scheduling-agent-scheduling` (IX24FSMTQH)

2. **Add Action Group**
   - Scroll to "Action groups" section
   - Click **"Add"** button

3. **Configure Action Group**
   - **Action group name:** `scheduling_actions`
   - **Description:** `Scheduling operations including list projects, check availability, confirm/reschedule/cancel appointments`
   - **Action group type:** `Define with API schemas`
   - **Action group invocation:** `Select existing Lambda function`
   - **Lambda function:** `scheduling-agent-scheduling-actions`
   - **API Schema:** `Define with in-line OpenAPI schema editor`

4. **Paste OpenAPI Schema**
   - Copy the entire content from: `bedrock/lambda/schemas/scheduling-actions-schema.json`
   - Paste into the schema editor
   - Click **"Validate"** to ensure schema is correct

5. **Save and Prepare**
   - Click **"Add"** button
   - Wait for action group to be created
   - Click **"Prepare"** button at the top of the agent page
   - Wait for status to return to `PREPARED`

#### Option B: AWS CLI (Automated - Coming Soon)

```bash
# Create action group via CLI
aws bedrock-agent create-agent-action-group \
  --agent-id IX24FSMTQH \
  --agent-version DRAFT \
  --action-group-name scheduling_actions \
  --action-group-executor '{
    "lambda": "arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-scheduling-actions"
  }' \
  --api-schema '{
    "payload": "'$(cat bedrock/lambda/schemas/scheduling-actions-schema.json | jq -c)'"
  }' \
  --region us-east-1
```

---

## 📄 OpenAPI Schema Reference

**Location:** `bedrock/lambda/schemas/scheduling-actions-schema.json`

### Actions (6 total)

| Action | Operation ID | Required Parameters | Optional Parameters | Description |
|--------|-------------|---------------------|---------------------|-------------|
| **List Projects** | `list_projects` | `customer_id` | `client_id` (B2B filter) | Get all projects for a customer |
| **Get Available Dates** | `get_available_dates` | `project_id` | None | Get available dates for scheduling |
| **Get Time Slots** | `get_time_slots` | `project_id`, `date`, `request_id` | None | Get time slots for a specific date |
| **Confirm Appointment** | `confirm_appointment` | `project_id`, `date`, `time`, `request_id` | None | Schedule a new appointment |
| **Reschedule Appointment** | `reschedule_appointment` | `project_id`, `new_date`, `new_time`, `request_id` | None | Change existing appointment |
| **Cancel Appointment** | `cancel_appointment` | `project_id` | None | Cancel an appointment |

**Note:** `client_id` has been removed from all actions except `list_projects` where it's optional for B2B filtering (updated 2025-10-17)

### Schema Preview

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Scheduling Actions API",
    "description": "API for scheduling-related actions",
    "version": "1.0.0"
  },
  "paths": {
    "/list-projects": {
      "post": {
        "summary": "List Projects",
        "operationId": "list_projects",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "customer_id": {
                    "type": "string",
                    "description": "Customer ID from PF360 system"
                  }
                },
                "required": ["customer_id"]
              }
            }
          }
        }
      }
    }
    // ... 5 more endpoints
  }
}
```

---

## 🔗 Lambda Function Integration

### Lambda Function Details

- **Function Name:** `scheduling-agent-scheduling-actions`
- **ARN:** `arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-scheduling-actions`
- **Runtime:** Python 3.11
- **Handler:** `lambda_function.lambda_handler`
- **Memory:** 512 MB
- **Timeout:** 30 seconds
- **Environment:**
  - `USE_MOCK_API=true` (set to `false` for production)

### Lambda Handler Location

**File:** `bedrock/lambda/scheduling_actions/lambda_function.py`

### Testing Lambda Directly

```bash
# Test list-projects action
aws lambda invoke \
  --function-name scheduling-agent-scheduling-actions \
  --cli-binary-format raw-in-base64-out \
  --payload '{"actionGroup":"scheduling_actions","apiPath":"/list-projects","httpMethod":"POST","parameters":[{"name":"customer_id","type":"string","value":"CUST001"}]}' \
  --region us-east-1 \
  response.json

cat response.json | jq
```

---

## 🧪 Testing the Agent

### Test in AWS Console

1. **Navigate to Agent**
   - Go to Bedrock Console → Agents → `scheduling-agent-scheduling`
   - Click **"Test"** button (right side panel)

2. **Test Queries**

**Test 1: List Projects**
```
Show me all projects for customer CUST001
```
**Expected:** Returns 3 mock projects (12345 Flooring, 12347 Windows, 12350 Deck Repair)

**Test 2: Check Availability**
```
What dates are available for project 12347?
```
**Expected:** Returns next 10 weekdays with available slots

**Test 3: Get Time Slots**
```
Show me time slots for project 12347 on [select a date from availability]
```
**Expected:** Returns time slots from 8 AM to 5 PM

**Test 4: Confirm Appointment**
```
Book project 12347 for [date] at 10:00 AM
```
**Expected:** Confirms appointment with project details

---

## 📊 Monitoring

### CloudWatch Logs

**Log Group:** `/aws/lambda/scheduling-agent-scheduling-actions`

```bash
# View recent logs
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions \
  --follow \
  --region us-east-1
```

### CloudWatch Metrics

```bash
# Check invocation count
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=scheduling-agent-scheduling-actions \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region us-east-1
```

---

## 🔍 Troubleshooting

### Issue 1: Action Group Validation Error

**Error:** `Value at 'functionSchema.functions.X.member.name' failed to satisfy constraint`

**Solution:** Ensure all operationIds in the OpenAPI schema use snake_case:
- ✅ `list_projects` (correct)
- ❌ `listProjects` (incorrect)

### Issue 2: Agent Cannot Be Prepared

**Error:** `This agent cannot be prepared. The AgentCollaboration attribute is set to SUPERVISOR_ROUTER`

**Solution:** Update agent collaboration to `DISABLED`:
```bash
aws bedrock-agent update-agent \
  --agent-id IX24FSMTQH \
  --agent-name scheduling-agent-scheduling \
  --foundation-model us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --agent-resource-role-arn arn:aws:iam::618048437522:role/scheduling-agent-scheduling-agent-role-dev \
  --agent-collaboration DISABLED \
  --instruction "You are a scheduling specialist agent..." \
  --region us-east-1

aws bedrock-agent prepare-agent --agent-id IX24FSMTQH --region us-east-1
```

### Issue 3: Lambda Function Not Found

**Error:** `Lambda function not found`

**Solution:** Verify Lambda function exists and has correct permissions:
```bash
aws lambda get-function \
  --function-name scheduling-agent-scheduling-actions \
  --region us-east-1
```

### Issue 4: Parameters Not Extracted (FIXED)

**Error:** `Missing required parameter: customer_id` (even though parameter is provided)

**Cause:** Bedrock sends parameters in `requestBody.content.application/json.properties` array format when using action groups, not as a JSON string.

**Status:** ✅ Fixed in Lambda handler (2025-10-17)

**Solution:** Lambda handler now correctly extracts parameters from both formats:
- Old format: `event['parameters']` array
- Action group format: `event['requestBody']['content']['application/json']['properties']` array

If you encounter this issue, redeploy Lambda functions:
```bash
./scripts/deploy_lambda_functions.sh
```

### Issue 5: Agent Not Responding

**Check:**
1. Agent status is `PREPARED`
2. Action group is created and linked
3. Lambda function has correct environment variables
4. CloudWatch logs for errors

---

## 🔐 IAM Permissions

### Agent Role Permissions

The agent role (`scheduling-agent-scheduling-agent-role-dev`) needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-scheduling-actions"
      ]
    }
  ]
}
```

### Lambda Execution Role Permissions

The Lambda role needs:
- CloudWatch Logs write permissions
- (Optional) Secrets Manager read for PF360 API credentials
- (Optional) DynamoDB read/write for session data

---

## 📝 Configuration Files

### Agent Configuration
- **Location:** Managed by AWS Bedrock (no local file)
- **View:** AWS Console or CLI (`aws bedrock-agent get-agent`)

### Lambda Code
- **Location:** `bedrock/lambda/scheduling_actions/`
- **Handler:** `lambda_function.py`
- **Dependencies:** `requirements.txt`

### OpenAPI Schema
- **Location:** `bedrock/lambda/schemas/scheduling-actions-schema.json`
- **Format:** OpenAPI 3.0 JSON

---

## 🚀 Next Steps

After completing this agent setup:

1. ✅ Verify agent status is `PREPARED`
2. ✅ Create action group with OpenAPI schema
3. ✅ Test in Bedrock Console
4. ✅ Verify Lambda invocations in CloudWatch
5. → Proceed to **Information Agent Setup** (`INFORMATION_AGENT_SETUP.md`)
6. → Proceed to **Notes Agent Setup** (`NOTES_AGENT_SETUP.md`)
7. → Test **Supervisor Agent** with multi-agent collaboration

---

## 📚 Related Documentation

- **[AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md](./AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md)** - Complete setup guide
- **[ACTION_GROUPS_SETUP_GUIDE.md](./ACTION_GROUPS_SETUP_GUIDE.md)** - Detailed action groups setup
- **[LAMBDA_DEPLOYMENT_GUIDE.md](./LAMBDA_DEPLOYMENT_GUIDE.md)** - Lambda deployment guide
- **[api-documentation.html](./api-documentation.html)** - Interactive API documentation

---

**Last Updated:** 2025-10-17
**Status:** Ready for action group creation
**Agent Version:** DRAFT
