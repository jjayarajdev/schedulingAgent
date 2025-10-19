# Bedrock Action Groups Setup Guide

**Version:** 1.0
**Last Updated:** 2025-10-17
**Prerequisites:** Lambda functions deployed (see LAMBDA_DEPLOYMENT_GUIDE.md)

---

## Overview

This guide explains how to create and configure **Action Groups** for your Bedrock agents. Action groups connect agents to Lambda functions through OpenAPI schemas.

**IMPORTANT:** This is a manual AWS Console process (~15 minutes per agent).

---

## Quick Reference

| Agent | Agent ID | Lambda Function | Schema File |
|-------|----------|----------------|-------------|
| **Scheduling Agent** | IX24FSMTQH | `scheduling-agent-scheduling-actions` | `scheduling-actions-schema.json` |
| **Information Agent** | C9ANXRIO8Y | `scheduling-agent-information-actions` | `information-actions-schema.json` |
| **Notes Agent** | G5BVBYEPUM | `scheduling-agent-notes-actions` | `notes-actions-schema.json` |

**Lambda ARNs:**
```bash
# Get Lambda ARNs
aws lambda list-functions \
  --region us-east-1 \
  --query "Functions[?starts_with(FunctionName, 'scheduling-agent-')].{Name:FunctionName,ARN:FunctionArn}" \
  --output table
```

Expected output:
```
Scheduling Actions: arn:aws:lambda:us-east-1:YOUR_ACCOUNT:function:scheduling-agent-scheduling-actions
Information Actions: arn:aws:lambda:us-east-1:YOUR_ACCOUNT:function:scheduling-agent-information-actions
Notes Actions: arn:aws:lambda:us-east-1:YOUR_ACCOUNT:function:scheduling-agent-notes-actions
```

---

## Table of Contents

1. [Understanding Action Groups](#understanding-action-groups)
2. [Setup Process Overview](#setup-process-overview)
3. [Step-by-Step Instructions](#step-by-step-instructions)
   - [Option A: Inline Schema (Recommended)](#option-a-inline-schema-recommended)
   - [Option B: S3-Hosted Schema](#option-b-s3-hosted-schema)
4. [Agent-Specific Configuration](#agent-specific-configuration)
5. [Testing](#testing)
6. [Troubleshooting](#troubleshooting)

---

## Understanding Action Groups

### What is an Action Group?

An **action group** is a collection of API operations that a Bedrock agent can invoke. It acts as the bridge between:
- **Bedrock Agent** (natural language interface)
- **Lambda Function** (business logic)
- **OpenAPI Schema** (API contract defining operations)

### Architecture

```
User Input
   ↓
Bedrock Agent (interprets intent)
   ↓
Action Group (defines available operations)
   ↓
OpenAPI Schema (maps operations to Lambda invocations)
   ↓
Lambda Function (executes business logic)
   ↓
Response back to Agent
```

### Why You Need Action Groups

Without action groups:
- ❌ Agent can only respond with text
- ❌ Cannot invoke APIs or Lambda functions
- ❌ No access to external data or services

With action groups:
- ✅ Agent can execute actions (schedule, query, update)
- ✅ Access to real-time data via Lambda → PF360 API
- ✅ Multi-step workflows (list projects → check dates → confirm)

---

## Setup Process Overview

### High-Level Steps

1. **Choose Schema Hosting Method** (Inline or S3)
2. **For Each Agent:**
   - Navigate to agent in AWS Console
   - Create new action group
   - Upload/link OpenAPI schema
   - Configure Lambda function
   - Save configuration
3. **Prepare Agents** (rebuild with new action groups)
4. **Test in Bedrock Console**

### Time Estimates

- **Inline Schema Method:** ~10 minutes per agent (~30 minutes total)
- **S3 Schema Method:** ~15 minutes per agent (~45 minutes total)

---

## Step-by-Step Instructions

### Option A: Inline Schema (Recommended)

**Pros:** Faster, no S3 setup required
**Cons:** Cannot edit schema without console access

#### Step 1: Open AWS Bedrock Console

1. Go to: https://console.aws.amazon.com/bedrock/
2. Verify region: **US East (N. Virginia) - us-east-1**
3. Navigate to: **Agents** → **Agents** (left sidebar)

#### Step 2: Select Agent

Choose the agent you want to configure:

**Option 1: Scheduling Agent**
- Agent ID: `IX24FSMTQH`
- Agent Name: `scheduling-agent-scheduling`

**Option 2: Information Agent**
- Agent ID: `C9ANXRIO8Y`
- Agent Name: `scheduling-agent-information`

**Option 3: Notes Agent**
- Agent ID: `G5BVBYEPUM`
- Agent Name: `scheduling-agent-notes`

Click on the agent name to open it.

#### Step 3: Create Action Group

1. Scroll to **Action Groups** section
2. Click **"Add" button** (top right of Action Groups section)
3. You'll see the "Add action group" form

#### Step 4: Configure Action Group - Basic Settings

**Action group name:**
```
scheduling-actions     (for Scheduling Agent)
information-actions    (for Information Agent)
notes-actions          (for Notes Agent)
```

**Description:**
```
Scheduling-related API operations (list projects, check availability, confirm appointments)    (Scheduling Agent)
Information-related API operations (project details, appointment status, working hours)         (Information Agent)
Notes-related API operations (add notes, list notes)                                            (Notes Agent)
```

**Action group type:**
- Select: **"Define with API schemas"**

#### Step 5: Configure API Schema - Inline

**API schema:**
- Select: **"Define with in-line schema editor"**

**Schema editor:**

Copy the contents of the appropriate schema file:

**For Scheduling Agent:**
```bash
cat bedrock/lambda/schemas/scheduling-actions-schema.json
```

**For Information Agent:**
```bash
cat bedrock/lambda/schemas/information-actions-schema.json
```

**For Notes Agent:**
```bash
cat bedrock/lambda/schemas/notes-actions-schema.json
```

Paste the entire JSON content into the inline schema editor.

#### Step 6: Configure Lambda Function

**Action group executor:**
- Select: **"Use existing Lambda function"**

**Lambda function:**
- Select from dropdown:
  - `scheduling-agent-scheduling-actions` (for Scheduling Agent)
  - `scheduling-agent-information-actions` (for Information Agent)
  - `scheduling-agent-notes-actions` (for Notes Agent)

**Lambda version or alias:**
- Select: **"$LATEST"** (or specific version if you've created one)

#### Step 7: Review and Create

1. Review all settings
2. Click **"Add" button** at the bottom
3. You'll see: "Action group created successfully"

#### Step 8: Prepare Agent (Rebuild)

**CRITICAL:** After adding the action group, you MUST prepare (rebuild) the agent.

1. At the top of the agent page, click **"Prepare" button**
2. Wait 30-60 seconds
3. Status will change to: "Prepared"

**Without this step, the action group will not be active!**

#### Step 9: Repeat for Other Agents

Repeat Steps 2-8 for the remaining two agents.

---

### Option B: S3-Hosted Schema

**Pros:** Schemas can be versioned, easier to update
**Cons:** Requires S3 bucket setup, more complex

#### Step 1: Create S3 Bucket (One-Time)

```bash
# Create S3 bucket for schemas
BUCKET_NAME="bedrock-agent-schemas-$(aws sts get-caller-identity --query Account --output text)"

aws s3 mb s3://${BUCKET_NAME} --region us-east-1

# Enable versioning (optional but recommended)
aws s3api put-bucket-versioning \
  --bucket ${BUCKET_NAME} \
  --versioning-configuration Status=Enabled \
  --region us-east-1
```

#### Step 2: Upload Schemas to S3

```bash
# Upload all three schemas
aws s3 cp bedrock/lambda/schemas/scheduling-actions-schema.json \
  s3://${BUCKET_NAME}/schemas/scheduling-actions-schema.json \
  --region us-east-1

aws s3 cp bedrock/lambda/schemas/information-actions-schema.json \
  s3://${BUCKET_NAME}/schemas/information-actions-schema.json \
  --region us-east-1

aws s3 cp bedrock/lambda/schemas/notes-actions-schema.json \
  s3://${BUCKET_NAME}/schemas/notes-actions-schema.json \
  --region us-east-1

# Verify upload
aws s3 ls s3://${BUCKET_NAME}/schemas/ --region us-east-1
```

#### Step 3: Get S3 URIs

```bash
# Print S3 URIs (you'll need these in the console)
echo "Scheduling Actions Schema: s3://${BUCKET_NAME}/schemas/scheduling-actions-schema.json"
echo "Information Actions Schema: s3://${BUCKET_NAME}/schemas/information-actions-schema.json"
echo "Notes Actions Schema: s3://${BUCKET_NAME}/schemas/notes-actions-schema.json"
```

#### Step 4: Configure Action Group in Console

Follow the same steps as Option A, but at **Step 5**:

**API schema:**
- Select: **"Select an existing S3 object"**

**S3 URI:**
- Enter the S3 URI from Step 3 (e.g., `s3://bedrock-agent-schemas-123456789012/schemas/scheduling-actions-schema.json`)

Continue with Steps 6-9 from Option A.

---

## Agent-Specific Configuration

### Scheduling Agent (IX24FSMTQH)

**Purpose:** Handles all scheduling operations

**Actions Exposed (6):**
1. `list-projects` - Show available projects for customer
2. `get-available-dates` - Get available dates for scheduling
3. `get-time-slots` - Get available time slots for a date
4. `confirm-appointment` - Confirm/schedule an appointment
5. `reschedule-appointment` - Reschedule an existing appointment
6. `cancel-appointment` - Cancel an appointment

**Lambda Function:** `scheduling-agent-scheduling-actions`

**Schema File:** `bedrock/lambda/schemas/scheduling-actions-schema.json`

**Test Prompts:**
- "Show me my projects"
- "When can I schedule project 12345?"
- "What time slots are available on October 25th?"

---

### Information Agent (C9ANXRIO8Y)

**Purpose:** Provides information about projects, appointments, and business details

**Actions Exposed (4):**
1. `get-project-details` - Show detailed project information
2. `get-appointment-status` - Check appointment status
3. `get-working-hours` - Get business hours
4. `get-weather` - Get weather forecast

**Lambda Function:** `scheduling-agent-information-actions`

**Schema File:** `bedrock/lambda/schemas/information-actions-schema.json`

**Test Prompts:**
- "Tell me about project 12345"
- "What's the status of my appointment?"
- "What are your business hours?"
- "What's the weather like in Tampa?"

---

### Notes Agent (G5BVBYEPUM)

**Purpose:** Manages notes and comments on projects

**Actions Exposed (2):**
1. `add-note` - Add a note to a project
2. `list-notes` - List all notes for a project

**Lambda Function:** `scheduling-agent-notes-actions`

**Schema File:** `bedrock/lambda/schemas/notes-actions-schema.json`

**Test Prompts:**
- "Add a note to project 12345: Customer prefers morning appointments"
- "Show me all notes for project 12345"

---

## Testing

### Step 1: Verify Action Groups Are Created

For each agent:

1. Open agent in AWS Console
2. Scroll to **Action Groups** section
3. Verify you see:
   - Action group name (e.g., "scheduling-actions")
   - Lambda function ARN
   - Status: "Enabled"

### Step 2: Test Individual Action via Lambda

Before testing in Bedrock, verify Lambda functions work:

```bash
# Test Scheduling Agent
aws lambda invoke \
  --function-name scheduling-agent-scheduling-actions \
  --cli-binary-format raw-in-base64-out \
  --payload '{"apiPath":"/list-projects","httpMethod":"POST","parameters":[{"name":"customer_id","value":"1645975"}]}' \
  --region us-east-1 \
  /tmp/scheduling-test.json && cat /tmp/scheduling-test.json

# Test Information Agent
aws lambda invoke \
  --function-name scheduling-agent-information-actions \
  --cli-binary-format raw-in-base64-out \
  --payload '{"apiPath":"/get-working-hours","httpMethod":"POST","parameters":[{"name":"client_id","value":"09PF05VD"}]}' \
  --region us-east-1 \
  /tmp/information-test.json && cat /tmp/information-test.json

# Test Notes Agent
aws lambda invoke \
  --function-name scheduling-agent-notes-actions \
  --cli-binary-format raw-in-base64-out \
  --payload '{"apiPath":"/list-notes","httpMethod":"POST","parameters":[{"name":"project_id","value":"12345"}]}' \
  --region us-east-1 \
  /tmp/notes-test.json && cat /tmp/notes-test.json
```

Expected: `"httpStatusCode": 200` and valid response data

### Step 3: Test in Bedrock Console

1. Go to Bedrock Console
2. Navigate to: **Agents** → **Agents**
3. Click on **Supervisor Agent** (not the collaborator agents)
4. Click **"Test" button** (top right)
5. In test panel, try these prompts:

**Basic Scheduling Test:**
```
I want to schedule an appointment for my project
```

**Expected Flow:**
1. Supervisor invokes Scheduling Agent
2. Scheduling Agent invokes `list-projects` action
3. Agent responds with project list
4. Agent asks which project to schedule

**Full Workflow Test:**
```
I want to schedule an appointment for customer 1645975 project 12345
```

**Expected Multi-Step Flow:**
1. List projects for customer
2. Get available dates for project
3. Show available time slots
4. Confirm appointment (when user selects date/time)

### Step 4: Check CloudWatch Logs

Monitor Lambda executions:

```bash
# Tail logs for Scheduling Agent
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions \
  --follow \
  --region us-east-1

# Check recent invocations (last 10 minutes)
aws logs filter-log-events \
  --log-group-name /aws/lambda/scheduling-agent-scheduling-actions \
  --start-time $(date -u -d '10 minutes ago' +%s)000 \
  --region us-east-1
```

Look for:
- `"Processing action: list-projects"`
- `"[MOCK] Fetching projects for customer..."`
- `"httpStatusCode": 200`

---

## Troubleshooting

### Issue 1: Action Group Not Appearing in Agent

**Symptoms:**
- Created action group but don't see it in agent
- Agent test doesn't invoke Lambda

**Solution:**
1. **Prepare Agent** - You MUST click "Prepare" after adding action group
2. Wait 30-60 seconds
3. Refresh page and verify status is "Prepared"

---

### Issue 2: "Unable to invoke Lambda function"

**Symptoms:**
```
Error: Unable to invoke Lambda function. Check function permissions.
```

**Solution:**
Verify Lambda has Bedrock invoke permission:

```bash
# Check permission
aws lambda get-policy \
  --function-name scheduling-agent-scheduling-actions \
  --region us-east-1

# Re-add permission if missing
aws lambda add-permission \
  --function-name scheduling-agent-scheduling-actions \
  --statement-id bedrock-invoke-scheduling \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn "arn:aws:bedrock:us-east-1:YOUR_ACCOUNT:agent/IX24FSMTQH" \
  --region us-east-1
```

---

### Issue 3: Schema Validation Error

**Symptoms:**
```
Invalid OpenAPI schema. [Error details...]
```

**Solutions:**

**A. Missing Required Fields**
- Ensure all paths have `operationId`
- Ensure all operations have `requestBody` and `responses`

**B. Invalid JSON**
- Validate JSON syntax: https://jsonlint.com/
- Check for missing commas, brackets, quotes

**C. Unsupported OpenAPI Version**
- Bedrock supports OpenAPI 3.0.x only
- Change version to: `"openapi": "3.0.0"`

**D. Fix and Re-upload**
```bash
# Edit schema file
vim bedrock/lambda/schemas/scheduling-actions-schema.json

# Re-upload to S3 (if using S3 method)
aws s3 cp bedrock/lambda/schemas/scheduling-actions-schema.json \
  s3://${BUCKET_NAME}/schemas/scheduling-actions-schema.json \
  --region us-east-1

# In console: Delete action group and recreate with fixed schema
```

---

### Issue 4: Lambda Returns Error in Bedrock Test

**Symptoms:**
- Action group configured correctly
- Lambda invokes but returns error
- Agent shows: "Action failed"

**Debugging Steps:**

**A. Check CloudWatch Logs**
```bash
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions \
  --follow \
  --region us-east-1
```

**B. Test Lambda Directly**
```bash
# Get exact event format from CloudWatch logs, then test
aws lambda invoke \
  --function-name scheduling-agent-scheduling-actions \
  --cli-binary-format raw-in-base64-out \
  --payload '{"apiPath":"/list-projects","httpMethod":"POST","parameters":[{"name":"customer_id","value":"1645975"}]}' \
  --region us-east-1 \
  /tmp/test-output.json

cat /tmp/test-output.json
```

**C. Common Lambda Errors**

| Error | Cause | Fix |
|-------|-------|-----|
| `"Missing required parameter: customer_id"` | Parameter not passed correctly | Check OpenAPI schema parameter definition |
| `"Unknown action: list_projects"` | apiPath not matching handler routing | Ensure apiPath uses hyphens: `/list-projects` |
| `"API request failed"` | PF360 API call failed (real mode) | Check USE_MOCK_API=true, or verify API credentials |
| `"Task timed out after 30.00 seconds"` | Lambda timeout | Increase timeout in Lambda configuration |

---

### Issue 5: Agent Uses Action Group But Response Is Empty

**Symptoms:**
- Lambda executes successfully (200 status)
- CloudWatch shows correct data returned
- But agent response is empty or says "I couldn't complete that"

**Solution:**
Check response format. Bedrock expects specific structure:

```json
{
  "messageVersion": "1.0",
  "response": {
    "actionGroup": "scheduling",
    "apiPath": "/list-projects",
    "httpMethod": "POST",
    "httpStatusCode": 200,
    "responseBody": {
      "application/json": {
        "body": "{\"action\":\"list_projects\",\"projects\":[...]}"
      }
    }
  }
}
```

**Key points:**
- `body` must be a JSON **string** (not an object)
- Must include `httpStatusCode: 200`
- Must include `messageVersion: "1.0"`

---

### Issue 6: "Cannot Read S3 Object" (S3 Method Only)

**Symptoms:**
```
Unable to read API schema from S3. Check bucket permissions.
```

**Solution:**

**A. Verify S3 URI is correct**
```bash
aws s3 ls s3://YOUR-BUCKET-NAME/schemas/
```

**B. Add S3 Read Permission to Bedrock Agent Role**

1. Go to IAM Console
2. Find role: `AmazonBedrockExecutionRoleForAgents_*`
3. Add inline policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::YOUR-BUCKET-NAME",
        "arn:aws:s3:::YOUR-BUCKET-NAME/*"
      ]
    }
  ]
}
```

4. Save policy
5. Wait 1-2 minutes for propagation
6. Try creating action group again

---

## Next Steps

After successfully creating all action groups:

1. ✅ **Test Individual Actions** - Verify each action works via Lambda
2. ✅ **Test via Supervisor Agent** - Test full multi-agent flows
3. ✅ **Enable Logging** - Set up CloudWatch monitoring (see MONITORING_SETUP_GUIDE.md)
4. ✅ **Switch to Real API** - Change `USE_MOCK_API=false` when ready
5. ✅ **Deploy Web Chat** - Set up frontend interface (see WEB_CHAT_DEPLOYMENT_GUIDE.md)
6. ✅ **Deploy SMS Channel** - Set up Twilio integration (see Phase 2 docs)
7. ✅ **Deploy Voice Channel** - Set up AWS Connect/Twilio (see Phase 3 docs)

---

## Summary

### What You Created

- **3 Action Groups** (one per agent)
- **12 Actions Total:**
  - 6 Scheduling Actions
  - 4 Information Actions
  - 2 Notes Actions
- **3 Lambda Integrations** (agent → Lambda via OpenAPI)

### Architecture Flow

```
User: "I want to schedule an appointment"
    ↓
Supervisor Agent (IX24FSMTQH)
    ↓
Scheduling Agent (IX24FSMTQH) [Action Group: scheduling-actions]
    ↓
Lambda: scheduling-agent-scheduling-actions
    ↓
Action: list-projects (via OpenAPI schema)
    ↓
PF360 API (or mock data)
    ↓
Response back to user
```

### Time Investment

- **Setup Time:** ~30-45 minutes (one-time)
- **Testing Time:** ~15-30 minutes
- **Total:** ~1 hour

---

## Resources

- **Lambda Deployment:** [LAMBDA_DEPLOYMENT_GUIDE.md](./LAMBDA_DEPLOYMENT_GUIDE.md)
- **Monitoring Setup:** [MONITORING_SETUP_GUIDE.md](./MONITORING_SETUP_GUIDE.md)
- **Web Chat Deployment:** [WEB_CHAT_DEPLOYMENT_GUIDE.md](./WEB_CHAT_DEPLOYMENT_GUIDE.md)
- **AWS Bedrock Agents Docs:** https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html
- **OpenAPI 3.0 Spec:** https://swagger.io/specification/

---

**Document Version:** 1.0
**Last Updated:** 2025-10-17
**Contact:** Project Team
