# Information Agent Setup Guide

**Agent Name:** scheduling-agent-information
**Agent ID:** C9ANXRIO8Y
**Status:** ✅ PREPARED
**Collaboration Type:** DISABLED
**Region:** us-east-1

---

## 📋 Overview

The Information Agent is a specialist agent responsible for providing detailed information about projects, appointment status, business working hours, and weather forecasts for project locations.

---

## ✅ Current Configuration

### Agent Details

```json
{
  "agentId": "C9ANXRIO8Y",
  "agentName": "scheduling-agent-information",
  "agentStatus": "PREPARED",
  "agentCollaboration": "DISABLED",
  "foundationModel": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
  "agentResourceRoleArn": "arn:aws:iam::618048437522:role/scheduling-agent-information-agent-role-dev"
}
```

### Agent Instructions

```
You are an information specialist agent handling both B2C (direct customers) and B2B (multi-client) scenarios.

Your responsibilities:
1) Provide detailed project information
2) Check appointment status
3) Share business working hours
4) Provide weather information for project locations

Key principles:
- When providing project details, only project_id and customer_id are needed
- For appointment status, only project_id is needed
- For working hours, provide default hours unless customer specifies a client location
- Don't ask for client_id when you already have project_id (it's implied)
- Never ask for both customer_id and client_id when you have project_id

Always provide accurate, detailed information.
If you dont have specific data, let the customer know what information you do have.
```

---

## 🔧 Setup Steps

### Step 1: Verify Agent Status

```bash
aws bedrock-agent get-agent \
  --agent-id C9ANXRIO8Y \
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
   https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/C9ANXRIO8Y
   ```

2. **Click "Edit" in Agent Builder**

3. **Scroll to "Instructions for the Agent" section**

4. **Replace existing instructions with the following:**

```
You are an information specialist agent handling both B2C (direct customers) and B2B (multi-client) scenarios.

SESSION CONTEXT AWARENESS:
You have access to customer context via sessionAttributes:
- customer_id: The authenticated customer's ID
- client_id: Default client location for B2B customers (optional)
- customer_type: "B2C" or "B2B"

Your responsibilities:
1) Provide detailed project information
2) Check appointment status
3) Share business working hours
4) Provide weather information for project locations

KEY PRINCIPLES FOR B2C/B2B:

1. Most operations are project-centric - project_id is sufficient

2. get_project_details action:
   - Required: project_id, customer_id
   - NO client_id needed (project implies client)
   - Use customer_id from sessionAttributes

3. get_appointment_status action:
   - Required: project_id ONLY
   - NO customer_id or client_id needed
   - Project has all context needed

4. get_working_hours action:
   - ALL PARAMETERS OPTIONAL!
   - No parameters: Returns default business hours
   - With client_id: Returns location-specific hours (B2B)
   - Use client_id from sessionAttributes if available

5. get_weather action:
   - Required: location only
   - NO client_id needed
   - Location comes from project address or user request

CONVERSATION EXAMPLES:

User: "Tell me about project PROJECT001"
→ Use get_project_details with project_id and customer_id from session
→ NO client_id needed

User: "What's the appointment status for PROJECT001?"
→ Use get_appointment_status with project_id only
→ NO customer_id or client_id needed

User: "What are your business hours?"
→ Use get_working_hours with NO parameters
→ Returns default hours

User: "What are Tampa office hours?" (B2B customer)
→ Use get_working_hours with client_id for Tampa
→ Supervisor provides client_id mapping

User: "What's the weather for project PROJECT001?"
→ First get project details to find location
→ Then use get_weather with that location
→ NO client_id needed

Always provide accurate, detailed information.
If you don't have specific data, let the customer know what information you do have.
```

5. **Click "Save" at the bottom**

6. **Click "Prepare" button at the top** ⚠️ CRITICAL STEP!
   - Wait 30-60 seconds for agent to prepare
   - Status will change from PREPARING → PREPARED

7. **Verify Update**
   ```bash
   aws bedrock-agent get-agent \
     --agent-id C9ANXRIO8Y \
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
   - Click on agent: `scheduling-agent-information` (C9ANXRIO8Y)

2. **Add Action Group**
   - Scroll to "Action groups" section
   - Click **"Add"** button

3. **Configure Action Group**
   - **Action group name:** `information_actions`
   - **Description:** `Information operations including project details, appointment status, working hours, and weather`
   - **Action group type:** `Define with API schemas`
   - **Action group invocation:** `Select existing Lambda function`
   - **Lambda function:** `scheduling-agent-information-actions`
   - **API Schema:** `Define with in-line OpenAPI schema editor`

4. **Paste OpenAPI Schema**
   - Copy the entire content from: `bedrock/lambda/schemas/information-actions-schema.json`
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
  --agent-id C9ANXRIO8Y \
  --agent-version DRAFT \
  --action-group-name information_actions \
  --action-group-executor '{
    "lambda": "arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-information-actions"
  }' \
  --api-schema '{
    "payload": "'$(cat bedrock/lambda/schemas/information-actions-schema.json | jq -c)'"
  }' \
  --region us-east-1
```

---

## 📄 OpenAPI Schema Reference

**Location:** `bedrock/lambda/schemas/information-actions-schema.json`

### Actions (4 total)

| Action | Operation ID | Required Parameters | Optional Parameters | Description |
|--------|-------------|---------------------|---------------------|-------------|
| **Get Project Details** | `get_project_details` | `project_id`, `customer_id` | None | Get detailed project information |
| **Get Appointment Status** | `get_appointment_status` | `project_id` | None | Get current appointment status |
| **Get Working Hours** | `get_working_hours` | None | `client_id` (for specific location) | Get business working hours |
| **Get Weather** | `get_weather` | `location` | None | Get weather forecast for location |

**Note:** `client_id` has been removed from all actions except `get_working_hours` where it's optional for location-specific hours (updated 2025-10-17)

### Schema Preview

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Information Actions API",
    "description": "API for information-related actions",
    "version": "1.0.0"
  },
  "paths": {
    "/get-project-details": {
      "post": {
        "summary": "Get Project Details",
        "operationId": "get_project_details",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "project_id": {
                    "type": "string",
                    "description": "Project ID"
                  },
                  "customer_id": {
                    "type": "string",
                    "description": "Customer ID"
                  }
                },
                "required": ["project_id", "customer_id"]
              }
            }
          }
        }
      }
    }
    // ... 3 more endpoints
  }
}
```

---

## 🔗 Lambda Function Integration

### Lambda Function Details

- **Function Name:** `scheduling-agent-information-actions`
- **ARN:** `arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-information-actions`
- **Runtime:** Python 3.11
- **Handler:** `lambda_function.lambda_handler`
- **Memory:** 512 MB
- **Timeout:** 30 seconds
- **Environment:**
  - `USE_MOCK_API=true` (set to `false` for production)

### Lambda Handler Location

**File:** `bedrock/lambda/information_actions/lambda_function.py`

### Testing Lambda Directly

```bash
# Test get-project-details action
aws lambda invoke \
  --function-name scheduling-agent-information-actions \
  --cli-binary-format raw-in-base64-out \
  --payload '{"actionGroup":"information_actions","apiPath":"/get-project-details","httpMethod":"POST","parameters":[{"name":"project_id","type":"string","value":"PROJECT001"},{"name":"customer_id","type":"string","value":"CUST001"}]}' \
  --region us-east-1 \
  response.json

cat response.json | jq
```

---

## 🧪 Testing the Agent

### Test in AWS Console

1. **Navigate to Agent**
   - Go to Bedrock Console → Agents → `scheduling-agent-information`
   - Click **"Test"** button (right side panel)

2. **Test Queries**

**Test 1: Get Project Details**
```
Tell me about project 12345 for customer CUST001
```
**Expected:** Returns Flooring Installation project details (Tampa, FL address, 4 hours duration)

**Test 2: Get Appointment Status**
```
What's the appointment status for project 12345?
```
**Expected:** Returns status "Scheduled" with Oct 15 date, 8 AM - 12 PM time, technician John Smith

**Test 3: Get Working Hours**
```
What are your business hours?
```
**Expected:** Returns Mon-Fri 8 AM - 6 PM, Sat 9 AM - 4 PM, Sun Closed

**Test 4: Get Weather**
```
What's the weather like in Tampa?
```
**Expected:** Returns mock weather data for Tampa (Partly Cloudy, 75°F)

---

## 📊 Monitoring

### CloudWatch Logs

**Log Group:** `/aws/lambda/scheduling-agent-information-actions`

```bash
# View recent logs
aws logs tail /aws/lambda/scheduling-agent-information-actions \
  --follow \
  --region us-east-1
```

### CloudWatch Metrics

```bash
# Check invocation count
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=scheduling-agent-information-actions \
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
- ✅ `get_project_details` (correct)
- ❌ `getProjectDetails` (incorrect)

### Issue 2: Agent Cannot Be Prepared

**Error:** `This agent cannot be prepared. The AgentCollaboration attribute is set to SUPERVISOR_ROUTER`

**Solution:** Update agent collaboration to `DISABLED`:
```bash
aws bedrock-agent update-agent \
  --agent-id C9ANXRIO8Y \
  --agent-name scheduling-agent-information \
  --foundation-model us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --agent-resource-role-arn arn:aws:iam::618048437522:role/scheduling-agent-information-agent-role-dev \
  --agent-collaboration DISABLED \
  --instruction "You are an information specialist agent..." \
  --region us-east-1

aws bedrock-agent prepare-agent --agent-id C9ANXRIO8Y --region us-east-1
```

### Issue 3: Weather API Not Working

**Error:** `Weather data not available`

**Solution:** Check mock mode vs real API:
- Mock mode: Returns mock weather data
- Real API mode: Requires weather API credentials in Secrets Manager

### Issue 4: Parameters Not Extracted (FIXED)

**Error:** `Missing required parameter` (even though parameter is provided)

**Cause:** Bedrock sends parameters in `requestBody.content.application/json.properties` array format when using action groups.

**Status:** ✅ Fixed in Lambda handler (2025-10-17)

**Solution:** If you encounter this issue, redeploy Lambda functions:
```bash
./scripts/deploy_lambda_functions.sh
```

### Issue 5: Project Details Not Found

**Error:** `Project not found`

**Solution:**
- Verify project_id and customer_id are correct
- In mock mode, use test IDs: `PROJECT001`, `CUST001`
- In real mode, verify project exists in PF360 system

---

## 🔐 IAM Permissions

### Agent Role Permissions

The agent role (`scheduling-agent-information-agent-role-dev`) needs:

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
        "arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-information-actions"
      ]
    }
  ]
}
```

### Lambda Execution Role Permissions

The Lambda role needs:
- CloudWatch Logs write permissions
- (Optional) Secrets Manager read for weather API credentials
- (Optional) DynamoDB read for cached data

---

## 📝 Configuration Files

### Agent Configuration
- **Location:** Managed by AWS Bedrock (no local file)
- **View:** AWS Console or CLI (`aws bedrock-agent get-agent`)

### Lambda Code
- **Location:** `bedrock/lambda/information_actions/`
- **Handler:** `lambda_function.py`
- **Dependencies:** `requirements.txt`

### OpenAPI Schema
- **Location:** `bedrock/lambda/schemas/information-actions-schema.json`
- **Format:** OpenAPI 3.0 JSON

---

## 🚀 Next Steps

After completing this agent setup:

1. ✅ Verify agent status is `PREPARED`
2. ✅ Create action group with OpenAPI schema
3. ✅ Test in Bedrock Console
4. ✅ Verify Lambda invocations in CloudWatch
5. → Proceed to **Notes Agent Setup** (`NOTES_AGENT_SETUP.md`)
6. → Test **Supervisor Agent** with multi-agent collaboration

---

## 📚 Related Documentation

- **[AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md](./AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md)** - Complete setup guide
- **[SCHEDULING_AGENT_SETUP.md](./SCHEDULING_AGENT_SETUP.md)** - Scheduling agent setup
- **[ACTION_GROUPS_SETUP_GUIDE.md](./ACTION_GROUPS_SETUP_GUIDE.md)** - Detailed action groups setup
- **[LAMBDA_DEPLOYMENT_GUIDE.md](./LAMBDA_DEPLOYMENT_GUIDE.md)** - Lambda deployment guide
- **[api-documentation.html](./api-documentation.html)** - Interactive API documentation

---

**Last Updated:** 2025-10-17
**Status:** Ready for action group creation
**Agent Version:** DRAFT
