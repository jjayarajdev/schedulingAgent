# Notes Agent Setup Guide

**Agent Name:** scheduling-agent-notes
**Agent ID:** G5BVBYEPUM
**Status:** ✅ PREPARED
**Collaboration Type:** DISABLED
**Region:** us-east-1

---

## 📋 Overview

The Notes Agent is a specialist agent responsible for managing project notes, including adding notes to projects and retrieving notes for customer reference and context.

---

## ✅ Current Configuration

### Agent Details

```json
{
  "agentId": "G5BVBYEPUM",
  "agentName": "scheduling-agent-notes",
  "agentStatus": "PREPARED",
  "agentCollaboration": "DISABLED",
  "foundationModel": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
  "agentResourceRoleArn": "arn:aws:iam::618048437522:role/scheduling-agent-notes-agent-role-dev"
}
```

### Agent Instructions

```
You are a notes specialist agent handling both B2C (direct customers) and B2B (multi-client) scenarios.

Your responsibilities:
1) Add notes to projects
2) Retrieve and display notes for projects
3) Help organize customer preferences and special instructions

Key principles:
- Notes are attached to projects - only project_id is needed
- Don't ask for client_id or customer_id when you have project_id
- Author field is optional (defaults to 'Agent' if not provided)

Always confirm the note content with the customer before saving.
Be clear about which project the note belongs to.
```

---

## 🔧 Setup Steps

### Step 1: Verify Agent Status

```bash
aws bedrock-agent get-agent \
  --agent-id G5BVBYEPUM \
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
   https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/G5BVBYEPUM
   ```

2. **Click "Edit" in Agent Builder**

3. **Scroll to "Instructions for the Agent" section**

4. **Replace existing instructions with the following:**

```
You are a notes specialist agent handling both B2C (direct customers) and B2B (multi-client) scenarios.

SESSION CONTEXT AWARENESS:
You have access to customer context via sessionAttributes:
- customer_id: The authenticated customer's ID
- client_id: Default client location for B2B customers (optional)
- customer_type: "B2C" or "B2B"

Your responsibilities:
1) Add notes to projects
2) Retrieve and display notes for projects
3) Help organize customer preferences and special instructions

KEY PRINCIPLES FOR B2C/B2B:

1. Notes are attached to projects - project_id is the only required identifier

2. add_note action:
   - Required: project_id, note_text
   - Optional: author (defaults to 'Agent' if not provided)
   - NO customer_id or client_id needed
   - Notes are project-centric, not customer-centric

3. list_notes action:
   - Required: project_id ONLY
   - NO customer_id or client_id needed
   - Project has all context needed

4. NEVER ask for customer_id or client_id when you have project_id
   - Project already has customer and client relationships
   - Notes belong to projects, not customers or clients

CONVERSATION EXAMPLES:

User: "Add a note to project PROJECT001: Customer prefers morning appointments"
→ Use add_note with:
   - project_id: "PROJECT001"
   - note_text: "Customer prefers morning appointments"
   - author: "Agent" (default)
→ NO customer_id or client_id needed

User: "Show me all notes for project PROJECT001"
→ Use list_notes with project_id: "PROJECT001"
→ NO customer_id or client_id needed

User: "Add a note that the customer has a dog"
→ If project_id is in conversation context, use it
→ If not, ask: "Which project would you like to add this note to?"
→ Then use add_note with project_id only

B2C vs B2B - NO DIFFERENCE:
- Notes work the same way for both
- Project is the only identifier needed
- Customer and client context is implicit in the project

Always confirm the note content with the customer before saving.
Be clear about which project the note belongs to.
```

5. **Click "Save" at the bottom**

6. **Click "Prepare" button at the top** ⚠️ CRITICAL STEP!
   - Wait 30-60 seconds for agent to prepare
   - Status will change from PREPARING → PREPARED

7. **Verify Update**
   ```bash
   aws bedrock-agent get-agent \
     --agent-id G5BVBYEPUM \
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
   - Click on agent: `scheduling-agent-notes` (G5BVBYEPUM)

2. **Add Action Group**
   - Scroll to "Action groups" section
   - Click **"Add"** button

3. **Configure Action Group**
   - **Action group name:** `notes_actions`
   - **Description:** `Notes management including adding and listing notes for projects`
   - **Action group type:** `Define with API schemas`
   - **Action group invocation:** `Select existing Lambda function`
   - **Lambda function:** `scheduling-agent-notes-actions`
   - **API Schema:** `Define with in-line OpenAPI schema editor`

4. **Paste OpenAPI Schema**
   - Copy the entire content from: `bedrock/lambda/schemas/notes-actions-schema.json`
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
  --agent-id G5BVBYEPUM \
  --agent-version DRAFT \
  --action-group-name notes_actions \
  --action-group-executor '{
    "lambda": "arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-notes-actions"
  }' \
  --api-schema '{
    "payload": "'$(cat bedrock/lambda/schemas/notes-actions-schema.json | jq -c)'"
  }' \
  --region us-east-1
```

---

## 📄 OpenAPI Schema Reference

**Location:** `bedrock/lambda/schemas/notes-actions-schema.json`

### Actions (2 total)

| Action | Operation ID | Required Parameters | Optional Parameters | Description |
|--------|-------------|---------------------|---------------------|-------------|
| **Add Note** | `add_note` | `project_id`, `note_text` | `author` (defaults to 'Agent') | Add a note to a project |
| **List Notes** | `list_notes` | `project_id` | None | List all notes for a project |

**Note:** `client_id` has been removed from both actions - notes are project-centric (updated 2025-10-17)

### Schema Preview

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Notes Actions API",
    "description": "API for notes-related actions",
    "version": "1.0.0"
  },
  "paths": {
    "/add-note": {
      "post": {
        "summary": "Add Note",
        "operationId": "add_note",
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
                  "note_text": {
                    "type": "string",
                    "description": "The note content to add"
                  },
                  "author": {
                    "type": "string",
                    "description": "Author of the note (defaults to 'Agent')"
                  }
                },
                "required": ["project_id", "note_text"]
              }
            }
          }
        }
      }
    },
    "/list-notes": {
      "post": {
        "summary": "List Notes",
        "operationId": "list_notes",
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
                  }
                },
                "required": ["project_id"]
              }
            }
          }
        }
      }
    }
  }
}
```

---

## 🔗 Lambda Function Integration

### Lambda Function Details

- **Function Name:** `scheduling-agent-notes-actions`
- **ARN:** `arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-notes-actions`
- **Runtime:** Python 3.11
- **Handler:** `lambda_function.lambda_handler`
- **Memory:** 512 MB
- **Timeout:** 30 seconds
- **Environment:**
  - `USE_MOCK_API=true` (set to `false` for production)

### Lambda Handler Location

**File:** `bedrock/lambda/notes_actions/lambda_function.py`

### Testing Lambda Directly

```bash
# Test add-note action
aws lambda invoke \
  --function-name scheduling-agent-notes-actions \
  --cli-binary-format raw-in-base64-out \
  --payload '{"actionGroup":"notes_actions","apiPath":"/add-note","httpMethod":"POST","parameters":[{"name":"project_id","type":"string","value":"PROJECT001"},{"name":"note_text","type":"string","value":"Customer prefers morning appointments"},{"name":"author","type":"string","value":"Agent"}]}' \
  --region us-east-1 \
  response.json

cat response.json | jq
```

---

## 🧪 Testing the Agent

### Test in AWS Console

1. **Navigate to Agent**
   - Go to Bedrock Console → Agents → `scheduling-agent-notes`
   - Click **"Test"** button (right side panel)

2. **Test Queries**

**Test 1: Add Note**
```
Add a note to project 12345: Customer prefers morning appointments
```
**Expected:** Confirms note added with timestamp and author "Agent"

**Test 2: List Notes**
```
Show me all notes for project 12345
```
**Expected:** Returns all notes stored for project 12345 (mock mode stores notes in memory)

**Test 3: Add with Custom Author**
```
Add a note to project 12347: Gate code is 1234 (author: John Smith)
```
**Expected:** Confirms note added with author "John Smith"

---

## 📊 Monitoring

### CloudWatch Logs

**Log Group:** `/aws/lambda/scheduling-agent-notes-actions`

```bash
# View recent logs
aws logs tail /aws/lambda/scheduling-agent-notes-actions \
  --follow \
  --region us-east-1
```

### CloudWatch Metrics

```bash
# Check invocation count
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=scheduling-agent-notes-actions \
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
- ✅ `add_note` (correct)
- ❌ `addNote` (incorrect)

### Issue 2: Agent Cannot Be Prepared

**Error:** `This agent cannot be prepared. The AgentCollaboration attribute is set to SUPERVISOR_ROUTER`

**Solution:** Update agent collaboration to `DISABLED`:
```bash
aws bedrock-agent update-agent \
  --agent-id G5BVBYEPUM \
  --agent-name scheduling-agent-notes \
  --foundation-model us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --agent-resource-role-arn arn:aws:iam::618048437522:role/scheduling-agent-notes-agent-role-dev \
  --agent-collaboration DISABLED \
  --instruction "You are a notes specialist agent..." \
  --region us-east-1

aws bedrock-agent prepare-agent --agent-id G5BVBYEPUM --region us-east-1
```

### Issue 3: Note Not Saved

**Error:** `Failed to save note`

**Solution:**
- Verify project_id is correct
- In mock mode, notes are stored in memory (lost on Lambda restart)
- In real mode, notes are stored in DynamoDB (persistent)

### Issue 4: Parameters Not Extracted (FIXED)

**Error:** `Missing required parameter` (even though parameter is provided)

**Cause:** Bedrock sends parameters in `requestBody.content.application/json.properties` array format when using action groups.

**Status:** ✅ Fixed in Lambda handler (2025-10-17)

**Solution:** If you encounter this issue, redeploy Lambda functions:
```bash
./scripts/deploy_lambda_functions.sh
```

### Issue 5: Notes List Empty

**Error:** `No notes found for this project`

**Solution:**
- Verify project has notes added
- In mock mode, add sample notes first
- Check CloudWatch logs for errors

---

## 🔐 IAM Permissions

### Agent Role Permissions

The agent role (`scheduling-agent-notes-agent-role-dev`) needs:

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
        "arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-notes-actions"
      ]
    }
  ]
}
```

### Lambda Execution Role Permissions

The Lambda role needs:
- CloudWatch Logs write permissions
- (Optional) DynamoDB read/write for persistent notes storage
- (Optional) S3 write for note attachments (future feature)

---

## 📝 Configuration Files

### Agent Configuration
- **Location:** Managed by AWS Bedrock (no local file)
- **View:** AWS Console or CLI (`aws bedrock-agent get-agent`)

### Lambda Code
- **Location:** `bedrock/lambda/notes_actions/`
- **Handler:** `lambda_function.py`
- **Dependencies:** `requirements.txt`

### OpenAPI Schema
- **Location:** `bedrock/lambda/schemas/notes-actions-schema.json`
- **Format:** OpenAPI 3.0 JSON

---

## 🚀 Next Steps

After completing this agent setup:

1. ✅ Verify agent status is `PREPARED`
2. ✅ Create action group with OpenAPI schema
3. ✅ Test in Bedrock Console
4. ✅ Verify Lambda invocations in CloudWatch
5. → Test **Supervisor Agent** with multi-agent collaboration
6. → Test complete workflows (scheduling with notes)

---

## 🎯 Multi-Agent Workflow Examples

Once all agents are configured, test these workflows through the Supervisor Agent:

**Workflow 1: Schedule with Notes**
```
I want to schedule an appointment for customer CUST001's kitchen remodel project.
The customer prefers morning appointments and has a dog.
```

**Expected Flow:**
1. Supervisor → Scheduling Agent: List projects for CUST001
2. Supervisor → Notes Agent: Add note about morning preference
3. Supervisor → Notes Agent: Add note about dog
4. Supervisor → Scheduling Agent: Check available dates
5. Supervisor → Scheduling Agent: Confirm morning slot
6. Response to customer with confirmation

**Workflow 2: Get Context Before Scheduling**
```
Show me all the notes for project PROJECT001 before I schedule
```

**Expected Flow:**
1. Supervisor → Notes Agent: List notes for PROJECT001
2. Supervisor → Information Agent: Get project details
3. Response with complete context

---

## 📚 Related Documentation

- **[AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md](./AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md)** - Complete setup guide
- **[SCHEDULING_AGENT_SETUP.md](./SCHEDULING_AGENT_SETUP.md)** - Scheduling agent setup
- **[INFORMATION_AGENT_SETUP.md](./INFORMATION_AGENT_SETUP.md)** - Information agent setup
- **[ACTION_GROUPS_SETUP_GUIDE.md](./ACTION_GROUPS_SETUP_GUIDE.md)** - Detailed action groups setup
- **[LAMBDA_DEPLOYMENT_GUIDE.md](./LAMBDA_DEPLOYMENT_GUIDE.md)** - Lambda deployment guide
- **[api-documentation.html](./api-documentation.html)** - Interactive API documentation

---

**Last Updated:** 2025-10-17
**Status:** Ready for action group creation
**Agent Version:** DRAFT
