# AWS Bedrock Agent + Lambda Integration Guide

**Date:** October 13, 2025
**Purpose:** Explain how Lambda functions integrate with Bedrock Agents for seamless conversation-driven actions

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [How Bedrock Agents Work](#how-bedrock-agents-work)
3. [Lambda Integration Flow](#lambda-integration-flow)
4. [Action Groups Explained](#action-groups-explained)
5. [Complete Request-Response Flow](#complete-request-response-flow)
6. [OpenAPI Schema Integration](#openapi-schema-integration)
7. [Configuration Steps](#configuration-steps)
8. [Testing Integration](#testing-integration)
9. [Conversation Examples](#conversation-examples)

---

## 🏗️ Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USER                                        │
│                    "Schedule my appointment"                             │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     AWS BEDROCK AGENT                                    │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Foundation Model (Claude Sonnet 4.5)                             │  │
│  │ - Understands user intent                                        │  │
│  │ - Extracts parameters (project_id, date, time)                   │  │
│  │ - Decides which action to invoke                                 │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                │                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Action Groups                                                     │  │
│  │ - Scheduling Actions (6 actions)                                 │  │
│  │ - Information Actions (4 actions)                                │  │
│  │ - Notes Actions (2 actions)                                      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      AWS LAMBDA FUNCTIONS                                │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │
│  │  Scheduling      │  │  Information     │  │  Notes           │     │
│  │  Actions Lambda  │  │  Actions Lambda  │  │  Actions Lambda  │     │
│  │  (6 actions)     │  │  (4 actions)     │  │  (2 actions)     │     │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘     │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  MOCK MODE (Development)                                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ mock_data.py - Returns realistic test data                       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                OR
┌─────────────────────────────────────────────────────────────────────────┐
│                  REAL MODE (Production)                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ PF360 APIs - Makes actual API calls                              │  │
│  │ - https://api.projectsforce.com/dashboard/...                    │  │
│  │ - https://api.projectsforce.com/scheduler/...                    │  │
│  │ - https://api.projectsforce.com/project-notes/...                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🤖 How Bedrock Agents Work

### What is a Bedrock Agent?

A **Bedrock Agent** is an AWS service that:
1. Uses Foundation Models (like Claude) to understand user intent
2. Automatically orchestrates multi-step tasks
3. Invokes Lambda functions to perform actions
4. Maintains conversation context across turns
5. Returns natural language responses to users

### Key Components

#### 1. Foundation Model
- **Model Used:** Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`)
- **Purpose:** Natural language understanding and generation
- **Capabilities:**
  - Understands user requests
  - Extracts parameters from conversation
  - Decides which actions to invoke
  - Formats responses naturally

#### 2. Instructions (Agent Prompt)
- Defines the agent's personality and behavior
- Specifies how to handle different scenarios
- Guides conversation flow
- Example:
  ```
  You are a friendly scheduling assistant for ProjectsForce.
  Help customers schedule, reschedule, and manage their appointments.
  Always confirm details before making changes.
  ```

#### 3. Action Groups
- Collections of related actions the agent can perform
- Each action group connects to a Lambda function
- Defined using OpenAPI schemas
- Example: "Scheduling Actions" group with 6 scheduling-related actions

#### 4. Knowledge Bases (Optional)
- RAG (Retrieval Augmented Generation) for document search
- Can query PDFs, documents, FAQs
- Not used in our current implementation

---

## 🔄 Lambda Integration Flow

### Complete Flow: User Message → Action → Response

```
STEP 1: User Input
┌────────────────────────────────────────────────────────────────┐
│ User: "Schedule my flooring installation for October 15th"    │
└───────────────────────────┬────────────────────────────────────┘
                            │
STEP 2: Agent Processing    ▼
┌────────────────────────────────────────────────────────────────┐
│ Bedrock Agent (Claude Sonnet 4.5):                            │
│ 1. Understands intent: "Schedule appointment"                 │
│ 2. Identifies action needed: "get_available_dates"            │
│ 3. Extracts parameters:                                       │
│    - customer_id: "1645975" (from session)                    │
│    - project_type: "flooring installation"                    │
│ 4. Needs project_id → calls list_projects first               │
└───────────────────────────┬────────────────────────────────────┘
                            │
STEP 3: Invoke Lambda       ▼
┌────────────────────────────────────────────────────────────────┐
│ Bedrock → Lambda Function                                      │
│                                                                │
│ POST invoke                                                    │
│ Function: scheduling-agent-scheduling-actions                  │
│                                                                │
│ Event Payload:                                                 │
│ {                                                              │
│   "messageVersion": "1.0",                                     │
│   "agent": {                                                   │
│     "name": "scheduling-agent",                                │
│     "id": "IX24FSMTQH",                                       │
│     "alias": "TYJRF3CJ7F"                                     │
│   },                                                           │
│   "sessionId": "session-abc-123",                              │
│   "actionGroup": "scheduling",                                 │
│   "apiPath": "/list-projects",                                 │
│   "httpMethod": "POST",                                        │
│   "parameters": [                                              │
│     {"name": "customer_id", "value": "1645975"},               │
│     {"name": "client_id", "value": "09PF05VD"}                 │
│   ]                                                            │
│ }                                                              │
└───────────────────────────┬────────────────────────────────────┘
                            │
STEP 4: Lambda Processing   ▼
┌────────────────────────────────────────────────────────────────┐
│ Lambda Function (handler.py):                                  │
│                                                                │
│ 1. Extract action from apiPath: "list-projects"               │
│ 2. Extract parameters: customer_id, client_id                 │
│ 3. Route to handler: handle_list_projects()                   │
│ 4. Check USE_MOCK_API environment variable                    │
│ 5. Call appropriate function:                                 │
│    - Mock: get_mock_projects(customer_id)                     │
│    - Real: requests.get(PF360_API_URL)                        │
│ 6. Transform response to standard format                      │
│ 7. Return to Bedrock                                          │
└───────────────────────────┬────────────────────────────────────┘
                            │
STEP 5: Lambda Response     ▼
┌────────────────────────────────────────────────────────────────┐
│ Lambda → Bedrock                                               │
│                                                                │
│ Response:                                                      │
│ {                                                              │
│   "messageVersion": "1.0",                                     │
│   "response": {                                                │
│     "actionGroup": "scheduling",                               │
│     "apiPath": "/list-projects",                               │
│     "httpStatusCode": 200,                                     │
│     "responseBody": {                                          │
│       "application/json": {                                    │
│         "body": "{                                             │
│           \"action\": \"list_projects\",                       │
│           \"project_count\": 3,                                │
│           \"projects\": [                                      │
│             {                                                  │
│               \"project_id\": \"12345\",                       │
│               \"project_type\": \"Installation\",             │
│               \"category\": \"Flooring\",                      │
│               \"status\": \"Pending\",                         │
│               ...                                              │
│             }                                                  │
│           ],                                                   │
│           \"mock_mode\": true                                  │
│         }"                                                     │
│       }                                                        │
│     }                                                          │
│   }                                                            │
│ }                                                              │
└───────────────────────────┬────────────────────────────────────┘
                            │
STEP 6: Agent Synthesis     ▼
┌────────────────────────────────────────────────────────────────┐
│ Bedrock Agent:                                                 │
│ 1. Receives Lambda response                                   │
│ 2. Parses project data                                        │
│ 3. Identifies flooring project (project_id: 12345)            │
│ 4. Now calls get_available_dates for that project             │
│ 5. Receives available dates                                   │
│ 6. Synthesizes natural language response                      │
└───────────────────────────┬────────────────────────────────────┘
                            │
STEP 7: User Response       ▼
┌────────────────────────────────────────────────────────────────┐
│ Agent → User:                                                  │
│ "I found your flooring installation project (ORD-2025-001).   │
│  I have availability for October 15th. These times are        │
│  available: 8:00 AM, 9:00 AM, 10:00 AM, 1:00 PM, 2:00 PM.    │
│  What time works best for you?"                               │
└────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Action Groups Explained

### What is an Action Group?

An **Action Group** is a collection of related actions that:
- Are defined by an OpenAPI schema
- Connect to a single Lambda function
- Share common parameters (like client_id)
- Represent a logical grouping of capabilities

### Our 3 Action Groups

#### 1. Scheduling Actions
**Purpose:** Manage appointment scheduling

**Lambda Function:** `scheduling-agent-scheduling-actions`

**Actions:**
```yaml
- list_projects:
    description: List all projects for a customer
    parameters: customer_id, client_id

- get_available_dates:
    description: Get available dates for scheduling
    parameters: project_id, client_id

- get_time_slots:
    description: Get time slots for a specific date
    parameters: project_id, date, request_id, client_id

- confirm_appointment:
    description: Confirm and schedule an appointment
    parameters: project_id, date, time, request_id, client_id

- reschedule_appointment:
    description: Reschedule an existing appointment
    parameters: project_id, new_date, new_time, request_id, client_id

- cancel_appointment:
    description: Cancel an appointment
    parameters: project_id, client_id
```

#### 2. Information Actions
**Purpose:** Retrieve project and appointment information

**Lambda Function:** `scheduling-agent-information-actions`

**Actions:**
```yaml
- get_project_details:
    description: Get detailed project information
    parameters: project_id, customer_id, client_id

- get_appointment_status:
    description: Check appointment status
    parameters: project_id, client_id

- get_working_hours:
    description: Get business hours
    parameters: client_id

- get_weather:
    description: Get weather forecast for location
    parameters: location, client_id
```

#### 3. Notes Actions
**Purpose:** Manage project notes

**Lambda Function:** `scheduling-agent-notes-actions`

**Actions:**
```yaml
- add_note:
    description: Add a note to a project
    parameters: project_id, note_text, author, client_id

- list_notes:
    description: List all notes for a project
    parameters: project_id, client_id
```

---

## 🔗 OpenAPI Schema Integration

### What is OpenAPI?

OpenAPI (formerly Swagger) is a standard format for describing REST APIs. Bedrock Agents use OpenAPI schemas to understand:
- What actions are available
- What parameters each action needs
- Data types and validation rules
- Response formats

### Schema Structure

```yaml
openapi: 3.0.0
info:
  title: Scheduling Actions API
  version: 1.0.0
  description: Appointment scheduling actions for Bedrock Agent

paths:
  /list-projects:
    post:
      summary: List all projects for a customer
      description: Retrieves all projects associated with a customer ID
      operationId: listProjects
      parameters:
        - name: customer_id
          in: query
          required: true
          schema:
            type: string
          description: Customer identifier
        - name: client_id
          in: query
          required: true
          schema:
            type: string
          description: Client identifier
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: object
                properties:
                  action:
                    type: string
                  project_count:
                    type: integer
                  projects:
                    type: array
                    items:
                      type: object
```

### How Bedrock Uses OpenAPI

1. **Action Discovery:** Bedrock reads the schema to know what actions exist
2. **Parameter Extraction:** Uses parameter definitions to extract values from conversation
3. **Validation:** Validates parameters against schema types
4. **Invocation:** Calls Lambda with proper structure
5. **Response Handling:** Parses Lambda response according to schema

---

## ⚙️ Configuration Steps

### Step 1: Create Lambda Functions

```bash
# Package Lambda (example for scheduling)
cd lambda/scheduling-actions
pip install -r requirements.txt -t package/
cp handler.py config.py mock_data.py package/
cd package
zip -r ../scheduling-actions.zip .

# Deploy to AWS
aws lambda create-function \
  --function-name scheduling-agent-scheduling-actions \
  --runtime python3.11 \
  --role arn:aws:iam::618048437522:role/scheduling-agent-lambda-role \
  --handler handler.lambda_handler \
  --zip-file fileb://scheduling-actions.zip \
  --timeout 30 \
  --memory-size 256 \
  --environment Variables="{USE_MOCK_API=true,ENVIRONMENT=dev}" \
  --region us-east-1
```

### Step 2: Create OpenAPI Schemas

Create 3 OpenAPI JSON files (already done):
- `infrastructure/openapi_schemas/scheduling_actions.json`
- `infrastructure/openapi_schemas/information_actions.json`
- `infrastructure/openapi_schemas/notes_actions.json`

### Step 3: Create Bedrock Agent

```bash
# Create agent
aws bedrock-agent create-agent \
  --agent-name scheduling-agent \
  --foundation-model us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --instruction "You are a friendly scheduling assistant..." \
  --agent-resource-role-arn arn:aws:iam::618048437522:role/bedrock-agent-role \
  --region us-east-1
```

### Step 4: Add Action Groups to Agent

**Option A: AWS Console (Recommended)**

1. Go to AWS Bedrock Console
2. Navigate to Agents → Your Agent
3. Click "Add action group"
4. Configure:
   - **Action group name:** `scheduling-actions`
   - **Action group type:** "Define with API schemas"
   - **Lambda function:** Select `scheduling-agent-scheduling-actions`
   - **API schema:** Upload `scheduling_actions.json`
5. Click "Save"
6. Repeat for other 2 action groups

**Option B: AWS CLI**

```bash
# Add scheduling action group
aws bedrock-agent create-agent-action-group \
  --agent-id IX24FSMTQH \
  --agent-version DRAFT \
  --action-group-name scheduling-actions \
  --action-group-executor lambda=arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-scheduling-actions \
  --api-schema file://infrastructure/openapi_schemas/scheduling_actions.json \
  --region us-east-1
```

### Step 5: Grant Permissions

```bash
# Allow Bedrock to invoke Lambda
aws lambda add-permission \
  --function-name scheduling-agent-scheduling-actions \
  --statement-id bedrock-agent-invoke \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn arn:aws:bedrock:us-east-1:618048437522:agent/IX24FSMTQH \
  --region us-east-1
```

### Step 6: Prepare Agent

```bash
# Prepare agent (compile and validate)
aws bedrock-agent prepare-agent \
  --agent-id IX24FSMTQH \
  --region us-east-1
```

This creates a new agent version and validates all configurations.

### Step 7: Create Agent Alias

```bash
# Create alias for testing
aws bedrock-agent create-agent-alias \
  --agent-id IX24FSMTQH \
  --agent-alias-name test \
  --description "Test alias for development" \
  --region us-east-1
```

---

## 🧪 Testing Integration

### Test 1: Lambda Console

```bash
# Test Lambda directly
1. Go to Lambda console
2. Open scheduling-agent-scheduling-actions
3. Click "Test" tab
4. Create test event:
```

```json
{
  "messageVersion": "1.0",
  "agent": {
    "name": "scheduling-agent",
    "id": "IX24FSMTQH"
  },
  "sessionId": "test-session",
  "actionGroup": "scheduling",
  "apiPath": "/list-projects",
  "httpMethod": "POST",
  "parameters": [
    {"name": "customer_id", "value": "1645975"},
    {"name": "client_id", "value": "09PF05VD"}
  ]
}
```

Expected Result: ✅ 200 response with projects list

### Test 2: Bedrock Agent Console

```bash
# Test via Bedrock Agent UI
1. Go to Bedrock Agents console
2. Open your agent
3. Click "Test" button (top right)
4. In chat window, type:
   "Show me my projects"
```

**What Happens:**
1. Agent receives message
2. Understands intent → needs to call list_projects
3. Invokes Lambda function
4. Lambda returns mock data
5. Agent synthesizes response
6. You see: "You have 3 projects: ..."

Expected Result: ✅ Natural response listing projects

### Test 3: AWS CLI Invoke

```bash
# Invoke agent via CLI
aws bedrock-agent-runtime invoke-agent \
  --agent-id IX24FSMTQH \
  --agent-alias-id TYJRF3CJ7F \
  --session-id test-session-123 \
  --input-text "Schedule my appointment" \
  --region us-east-1 \
  response.txt

# View response
cat response.txt
```

---

## 💬 Conversation Examples

### Example 1: Simple Scheduling

```
User: "Hi, I need to schedule my flooring installation"

[Agent thinks: User wants to schedule → need to list projects first]

Agent → Lambda: list_projects(customer_id="1645975")
Lambda → Agent: {projects: [Flooring Project 12345, ...]}

Agent: "I see you have a flooring installation project (ORD-2025-001)
       at 123 Main St, Tampa. Would you like to schedule it?"

User: "Yes please"

[Agent thinks: Need available dates for project 12345]

Agent → Lambda: get_available_dates(project_id="12345")
Lambda → Agent: {dates: ["2025-10-14", "2025-10-15", ...]}

Agent: "I have availability starting October 14th. Available dates are:
       Oct 14, 15, 16, 17, 20. Which date works for you?"

User: "October 15th"

[Agent thinks: Need time slots for Oct 15]

Agent → Lambda: get_time_slots(project_id="12345", date="2025-10-15")
Lambda → Agent: {slots: ["08:00 AM", "09:00 AM", ...]}

Agent: "For October 15th, available times are: 8 AM, 9 AM, 10 AM,
       1 PM, 2 PM, 3 PM, 4 PM, 5 PM. What time works?"

User: "10 AM"

[Agent thinks: Confirm appointment]

Agent → Lambda: confirm_appointment(project_id="12345",
                                   date="2025-10-15",
                                   time="10:00 AM")
Lambda → Agent: {confirmation_number: "CONF-1760377790", ...}

Agent: "Perfect! Your flooring installation is scheduled for
       October 15th at 10:00 AM. Confirmation: CONF-1760377790.
       Technician John Smith will arrive at 123 Main St."
```

**Actions Used:** 4 Lambda invocations in 1 conversation
- list_projects
- get_available_dates
- get_time_slots
- confirm_appointment

### Example 2: Multi-Turn with Context

```
User: "What's the status of my project?"

Agent → Lambda: list_projects(customer_id="1645975")
Lambda → Agent: {projects: [3 projects]}

Agent: "You have 3 projects:
       1. Flooring (ORD-2025-001) - Scheduled for Oct 15
       2. Windows (ORD-2025-002) - Pending
       3. Deck Repair (ORD-2025-003) - Pending
       Which one would you like details on?"

User: "The flooring one"

[Agent remembers: project_id="12345" from previous response]

Agent → Lambda: get_project_details(project_id="12345")
Lambda → Agent: {full project details}

Agent: "Here's your flooring project:
       • Status: Scheduled
       • Date: October 15, 2025 at 8:00 AM
       • Technician: John Smith
       • Address: 123 Main St, Apt 4B, Tampa
       • Duration: 4 hours"

User: "What's the weather forecast for that day?"

[Agent remembers: date="2025-10-15", location="Tampa, FL"]

Agent → Lambda: get_weather(location="Tampa, FL")
Lambda → Agent: {weather forecast}

Agent: "Weather for Oct 15 in Tampa:
       • High: 75°F, Low: 62°F
       • Condition: Sunny
       • Perfect weather for your installation!"
```

**Key Feature:** Agent maintains context across multiple turns

---

## 🔐 Security & Best Practices

### IAM Roles Required

#### 1. Lambda Execution Role
Permissions needed:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:*:table/scheduling-agent-*"
    }
  ]
}
```

#### 2. Bedrock Agent Role
Permissions needed:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-5-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": "arn:aws:lambda:us-east-1:*:function:scheduling-agent-*"
    }
  ]
}
```

### Environment Variables Management

**Development:**
```bash
USE_MOCK_API=true
ENVIRONMENT=dev
LOG_LEVEL=DEBUG
```

**Production:**
```bash
USE_MOCK_API=false
ENVIRONMENT=prod
CUSTOMER_SCHEDULER_API_URL=https://api.projectsforce.com
LOG_LEVEL=INFO
# Use AWS Secrets Manager for tokens
```

---

## 📊 Monitoring & Debugging

### CloudWatch Logs

**Lambda Logs:**
```bash
# Tail logs
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions --follow

# Filter for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/scheduling-agent-scheduling-actions \
  --filter-pattern "ERROR"

# Filter for mock mode
aws logs filter-log-events \
  --log-group-name /aws/lambda/scheduling-agent-scheduling-actions \
  --filter-pattern "[MOCK]"
```

**Agent Logs:**
```bash
# Agent invocation logs
aws logs tail /aws/bedrock/agents/IX24FSMTQH --follow
```

### Debug Tips

1. **Check Lambda Invocation**
   - Look for "Processing action: X" in logs
   - Verify parameters received

2. **Check Mock Mode**
   - Look for "[MOCK]" or "[REAL]" tags
   - Verify mock_mode in response

3. **Check Action Routing**
   - Verify apiPath matches handler routing table
   - Check for "Unknown action" errors

4. **Check Parameter Extraction**
   - Log extracted parameters
   - Verify all required params present

---

## 🎯 Success Criteria

Your integration is working when:

✅ **Lambda Functions**
- All 3 Lambdas deployed successfully
- Environment variables set correctly
- Test invocations return 200 status

✅ **Bedrock Agent**
- Agent created and prepared
- All 3 action groups configured
- OpenAPI schemas validated

✅ **Permissions**
- Bedrock can invoke Lambda functions
- Lambda has necessary AWS permissions
- No permission errors in logs

✅ **End-to-End Testing**
- Agent responds to user messages
- Lambda functions are invoked
- Natural language responses generated
- Multi-turn conversations work

✅ **Mock Mode**
- All responses show mock_mode: true
- Mock data is realistic
- Fast response times (< 1s)

---

## 📚 Summary

### The Integration in 5 Steps

1. **User sends message** → Bedrock Agent
2. **Agent understands intent** → Decides action needed
3. **Agent invokes Lambda** → Passes parameters
4. **Lambda executes** → Returns structured data
5. **Agent synthesizes** → Natural language response

### Key Advantages

✅ **No Code Changes Required**
- Lambda handles both mock and real modes
- Switch via environment variable
- Same code for dev and prod

✅ **Automatic Orchestration**
- Agent chains multiple actions
- Maintains conversation context
- Handles parameter passing

✅ **Scalability**
- Lambda auto-scales
- Agent handles concurrent users
- Serverless architecture

✅ **Monitoring**
- CloudWatch logs for everything
- Track mock vs real usage
- Debug with detailed logs

---

## 📞 Next Steps

1. ✅ Lambda functions created and tested locally
2. ⏳ Deploy Lambda functions to AWS
3. ⏳ Configure Bedrock Agent action groups
4. ⏳ Test integration in Bedrock console
5. ⏳ Deploy to production with real APIs

**Ready to deploy!** All the pieces are in place for seamless integration. 🚀
