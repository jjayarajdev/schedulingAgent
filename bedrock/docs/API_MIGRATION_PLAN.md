# API Migration Plan - LangGraph to AWS Bedrock

**Date:** October 19, 2025
**Purpose:** Migrate real PF360 API calls from archived LangGraph backend to current AWS Bedrock implementation
**Status:** Planning Phase

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current vs Target Architecture](#current-vs-target-architecture)
3. [API Inventory](#api-inventory)
4. [Key Challenges](#key-challenges)
5. [Migration Strategy](#migration-strategy)
6. [Implementation Phases](#implementation-phases)
7. [Testing Strategy](#testing-strategy)
8. [Rollback Plan](#rollback-plan)
9. [Success Criteria](#success-criteria)

---

## Executive Summary

### Current State
- **AWS Bedrock Agents:** 5 agents (1 supervisor + 4 specialists)
- **Lambda Functions:** 3 functions with 12 mock actions
- **Data Source:** Mock data (hardcoded JSON)
- **Frontend:** React + Flask backend with sample user CUST001

### Target State
- **Same architecture** but with real PF360 API integration
- **Replace mock data** with live customer data
- **Handle authentication** and multi-tenant routing
- **Manage stateful flows** (request_id, session tracking)

### Timeline Estimate
- **Phase 1 (Preparation):** 2-3 days
- **Phase 2 (Lambda Updates):** 3-5 days
- **Phase 3 (Agent Updates):** 2-3 days
- **Phase 4 (Frontend Updates):** 2-3 days
- **Phase 5 (Testing):** 3-5 days
- **Total:** 12-19 days (2.5-4 weeks)

---

## Current vs Target Architecture

### Current Architecture (Mock Data)
```
User Request
    ↓
React Frontend
    ↓
Flask Backend (port 5001)
    ↓
AWS Bedrock Supervisor Agent
    ↓
Specialist Agent (scheduling/information/notes)
    ↓
Lambda Function
    ↓
Returns MOCK_DATA (hardcoded)
    ↓
Response to User
```

### Target Architecture (Real API)
```
User Request (with auth token)
    ↓
React Frontend (sends: customer_id, client_id, authorization)
    ↓
Flask Backend (validates token, adds to prompt context)
    ↓
AWS Bedrock Supervisor Agent
    ↓
Specialist Agent
    ↓
Lambda Function (receives: customer_id, client_id, auth_header)
    ↓
PF360 API (Customer Scheduler)
    ↓
Real customer data
    ↓
Response to User
```

### Key Differences

| Aspect | Current (Mock) | Target (Real API) |
|--------|----------------|-------------------|
| **Authentication** | None | JWT/Bearer token required |
| **Customer Context** | Hardcoded CUST001 | Dynamic from auth session |
| **Data Source** | `mock_data.py` | PF360 Customer Scheduler API |
| **State Management** | Stateless | Request ID tracking for scheduling |
| **Environment** | Single environment | Multi-env (dev/qa/staging/prod) |
| **Client Routing** | N/A | Multi-tenant (client_id based routing) |

---

## API Inventory

### APIs from LangGraph Code to Migrate

#### 1. Customer Dashboard API
**Purpose:** Load all customer projects

**Endpoint:**
```
GET {CUSTOMER_SCHEDULER_BASE_API_URL}/dashboard/get/{client_id}/{customer_id}
```

**Headers:**
```json
{
  "authorization": "Bearer <token>",
  "client_id": "<client_id>",
  "Content-Type": "application/json"
}
```

**Response Example:**
```json
{
  "data": [
    {
      "project_project_id": "12345",
      "project_project_number": "ORD-2025-001",
      "project_type_project_type": "Installation",
      "project_category_category": "Flooring",
      "status_info_status": "Scheduled",
      "installation_address_full_address": "123 Main St, Tampa, FL 33601",
      "project_date_scheduled_date": "2025-10-15",
      "convertedProjectStartScheduledDate": "2025-10-15 08:00:00",
      "convertedProjectEndScheduledDate": "2025-10-15 12:00:00",
      ...
    }
  ]
}
```

**Maps to Current Lambda Action:** `list_projects`

---

#### 2. Business Hours API
**Purpose:** Get working days for scheduling

**Endpoint:**
```
GET {CUSTOMER_SCHEDULER_BASE_API_URL}/scheduler/client/{client_id}/business-hours
```

**Headers:** Same as above

**Response Example:**
```json
{
  "data": {
    "workHours": [
      {"day": "Monday", "is_working": true},
      {"day": "Tuesday", "is_working": true},
      {"day": "Wednesday", "is_working": true},
      {"day": "Thursday", "is_working": true},
      {"day": "Friday", "is_working": true},
      {"day": "Saturday", "is_working": false},
      {"day": "Sunday", "is_working": false}
    ]
  }
}
```

**Maps to Current Lambda Action:** `get_business_hours`

---

#### 3. Available Dates API (Rescheduler Slots)
**Purpose:** Get available dates for a project (initiates scheduling session)

**Endpoint:**
```
GET {CUSTOMER_SCHEDULER_BASE_API_URL}/scheduler/client/{client_id}/project/{project_id}/date/{today}/selected/{today}/get-rescheduler-slots
```

**Parameters:**
- `{today}`: Current date in `YYYY-MM-DD` format

**Response Example:**
```json
{
  "data": {
    "dates": ["2025-10-20", "2025-10-21", "2025-10-22", ...],
    "request_id": "req_abc123xyz"
  }
}
```

**Important:** Returns `request_id` which MUST be used in subsequent slot queries

**Maps to Current Lambda Action:** `get_available_dates`

---

#### 4. Time Slots API
**Purpose:** Get available time slots for a specific date

**Endpoint:**
```
GET {CUSTOMER_SCHEDULER_BASE_API_URL}/scheduler/client/{client_id}/project/{project_id}/date/{date}/selected/{date}/get-rescheduler-slots?request_id={request_id}
```

**Parameters:**
- `{date}`: Selected date in `YYYY-MM-DD` format
- `request_id`: From previous API call (query parameter)

**Response Example:**
```json
{
  "data": {
    "slots": ["08:00", "09:00", "10:00", "11:00", "13:00", "14:00", ...]
  }
}
```

**Maps to Current Lambda Action:** `get_time_slots`

---

#### 5. Confirm Schedule API
**Purpose:** Book an appointment

**Endpoint:**
```
POST {CUSTOMER_SCHEDULER_BASE_API_URL}/scheduler/client/{client_id}/project/{project_id}/schedule
```

**Request Body:**
```json
{
  "created_at": "10-20-2025 14:30:00",
  "date": "2025-10-21",
  "time": "10:00",
  "request_id": "req_abc123xyz",
  "is_chatbot": "true"
}
```

**Important:**
- `created_at`: Timezone is Asia/Kolkata (IST) - format: `MM-DD-YYYY HH:MM:SS`
- `request_id`: From get-available-dates call
- `is_chatbot`: Always "true" (string, not boolean)

**Response Example:**
```json
{
  "message": "Appointment scheduled successfully",
  "status": "success"
}
```

**Maps to Current Lambda Action:** `confirm_appointment`

---

#### 6. Cancel Schedule API
**Purpose:** Cancel an existing appointment

**Endpoint:**
```
GET {CUSTOMER_SCHEDULER_BASE_API_URL}/scheduler/client/{client_id}/project/{project_id}/cancel-reschedule
```

**Response Example:**
```json
{
  "message": "Appointment cancelled successfully"
}
```

**Maps to Current Lambda Action:** `cancel_appointment`

---

#### 7. Add Project Note API
**Purpose:** Add customer notes to a project

**Endpoint:**
```
POST {CUSTOMER_SCHEDULER_BASE_API_URL}/project-notes/add/{client_id}/{project_id}
```

**Request Body:**
```json
{
  "note_text": "Customer prefers morning appointments"
}
```

**Response Example:**
```json
{
  "message": "Note added successfully",
  "note_id": "note_123"
}
```

**Maps to Current Lambda Action:** `add_note`

---

#### 8. Project Detail URL (Frontend Only)
**Purpose:** Generate clickable link to project details page

**Format:**
```
https://{client_name}.cx-portal.{environment}.projectsforce.com/details/{project_id}
```

**Environment Mapping:**
- `dev` → `dev.projectsforce.com`
- `qa` → `qa.projectsforce.com`
- `staging` → `staging.projectsforce.com`
- `prod` → `apps.projectsforce.com`

**Example:**
```
https://acme-corp.cx-portal.dev.projectsforce.com/details/12345
```

---

## Key Challenges

### Challenge 1: State Management (Request ID Tracking)

**Problem:**
- Scheduling flow requires `request_id` from `get_available_dates` call
- Must be passed to `get_time_slots` and `confirm_schedule`
- AWS Bedrock agents are stateless by design

**Current LangGraph Solution:**
```python
# Step 1: Get dates, store request_id in session
session_context[session_id]["request_id"] = response["request_id"]

# Step 2: Use stored request_id
req_id = session_context[session_id]["request_id"]
```

**Bedrock Solution Options:**

**Option A: Session Attributes (Attempted, Doesn't Work)**
- Session attributes don't auto-propagate through collaboration
- Not reliable for multi-step flows

**Option B: Prompt Injection (Current Working Pattern) ✅**
- Store state in conversation history
- Extract from agent's previous response
- Pass explicitly in next request

**Option C: DynamoDB State Store (Recommended)**
- Lambda writes request_id to DynamoDB with session_id key
- Lambda reads from DynamoDB on next call
- TTL of 30 minutes (auto-cleanup)

**Option D: Return request_id to user, have them pass it back**
- Include request_id in response: "Your session ID is req_123. What date?"
- Extract from user's next message
- Fragile, user-dependent

**Recommendation:** Option C (DynamoDB) - Most reliable for production

---

### Challenge 2: Authentication & Authorization

**Problem:**
- APIs require JWT/Bearer token in headers
- Token contains: customer_id, client_id, permissions
- Must flow from frontend → Flask → Bedrock → Lambda

**Current Mock Implementation:**
```python
# No auth required
MOCK_DATA = {...}
return MOCK_DATA
```

**Target Implementation:**
```python
# Lambda must receive and use auth token
def handler(event, context):
    auth_header = event.get("authorization")  # How do we get this?
    client_id = event.get("client_id")

    headers = {
        "authorization": auth_header,
        "client_id": client_id,
        "Content-Type": "application/json"
    }

    response = requests.get(api_url, headers=headers)
```

**Flow Required:**

```
1. Frontend: User logs in
   → Gets JWT token from auth service
   → Stores in localStorage/sessionStorage

2. Frontend: User sends message
   → Includes token in request to Flask backend
   POST /api/chat/simple
   Headers: { "Authorization": "Bearer <token>" }

3. Flask Backend: Validates token
   → Extracts customer_id, client_id from token
   → Injects into Bedrock prompt context

   augmented_prompt = f"""
   Session Context:
   - Customer ID: {customer_id}
   - Client ID: {client_id}
   - Authorization: {token}

   User Request: {message}
   """

4. Bedrock Agent: Extracts from prompt
   → Passes to Lambda via action parameters

5. Lambda: Receives as action parameters
   → Uses in API headers
```

**Challenge:** How to pass auth token to Lambda?

**Bedrock Agent Action Groups Limitation:**
- Parameters must be defined in OpenAPI schema
- Can't dynamically add headers to Lambda invocation
- Session attributes don't work reliably

**Solutions:**

**Option A: Include in every action parameter** ❌
```json
{
  "customer_id": "CUST001",
  "authorization": "Bearer xyz123...",  // Too long, cumbersome
  "client_id": "acme-corp"
}
```
- Pros: Explicit
- Cons: Verbose, token in logs, schema pollution

**Option B: Lambda environment variables** ❌
```python
# Set env var: AUTH_TOKEN=<service-account-token>
AUTH_HEADER = {"authorization": os.getenv("AUTH_TOKEN")}
```
- Pros: Simple
- Cons: Single token for all customers (security risk), can't be user-specific

**Option C: AWS Secrets Manager + Customer ID lookup** ⚠️
```python
# Lambda fetches token based on customer_id
token = get_customer_token(customer_id)  # From Secrets Manager
```
- Pros: Secure
- Cons: Complex, requires token management per customer

**Option D: API Gateway + Lambda Authorizer** ✅ **RECOMMENDED**
```
API Gateway → Lambda Authorizer (validates JWT)
    ↓
Sets context variables (customer_id, client_id)
    ↓
Lambda receives in event.requestContext
```
- Pros: Standard AWS pattern, secure, scalable
- Cons: Requires API Gateway setup

**Option E: Bedrock Agent passes session_id, Lambda looks up token in DynamoDB** ✅ **SIMPLE**
```python
# Flask stores token in DynamoDB when session starts
dynamodb.put_item({
    "session_id": session_id,
    "auth_token": token,
    "customer_id": customer_id,
    "ttl": now + 30min
})

# Lambda retrieves token
def handler(event, context):
    session_id = event["parameters"]["session_id"]
    session = dynamodb.get_item(Key={"session_id": session_id})
    auth_token = session["auth_token"]

    headers = {"authorization": auth_token, ...}
    response = requests.get(api_url, headers=headers)
```
- Pros: Clean separation, no token in Bedrock, session-scoped
- Cons: DynamoDB dependency

**Recommendation:** Option E (DynamoDB session store) for Phase 1, migrate to Option D (API Gateway) for production

---

### Challenge 3: Multi-Tenant Routing (client_id)

**Problem:**
- Different clients have different domains: `{client_name}.cx-portal.{env}.projectsforce.com`
- URLs must be built dynamically
- Client-specific configurations may differ

**Current Mock:**
```python
# Single hardcoded client
BASE_PROJECT_URL = "https://acme.cx-portal.dev.projectsforce.com/details"
```

**Target:**
```python
# Dynamic per client
def get_project_url(client_name, env, project_id):
    env_domain = {
        "dev": "dev",
        "qa": "qa",
        "staging": "staging",
        "prod": "apps"
    }[env]

    return f"https://{client_name}.cx-portal.{env_domain}.projectsforce.com/details/{project_id}"
```

**Solution:**
- Pass `client_name` and `environment` as Lambda parameters
- Lambda builds URLs dynamically
- Store in DynamoDB session if needed frequently

---

### Challenge 4: Environment Configuration

**Current:**
```python
# Lambda has USE_MOCK_API flag
if USE_MOCK_API:
    return MOCK_DATA
else:
    # call real API
```

**Target:**
- Environment-specific API base URLs
- Different credentials per environment
- Feature flags for gradual rollout

**Configuration Strategy:**

**Lambda Environment Variables:**
```bash
CUSTOMER_SCHEDULER_BASE_API_URL=https://api.dev.projectsforce.com
ENVIRONMENT=dev
CONFIRM_SCHEDULE_FLAG=0  # 0=test mode, 1=real booking
CANCEL_SCHEDULE_FLAG=0
AWS_REGION=us-east-1
DYNAMODB_SESSION_TABLE=bedrock-sessions-dev
```

**Per-Environment Terraform:**
```hcl
# infrastructure/terraform/environments/dev/lambda.tf
environment {
  variables = {
    CUSTOMER_SCHEDULER_BASE_API_URL = "https://api.dev.projectsforce.com"
    ENVIRONMENT = "dev"
    CONFIRM_SCHEDULE_FLAG = "0"  # Test mode
  }
}

# infrastructure/terraform/environments/prod/lambda.tf
environment {
  variables = {
    CUSTOMER_SCHEDULER_BASE_API_URL = "https://api.projectsforce.com"
    ENVIRONMENT = "prod"
    CONFIRM_SCHEDULE_FLAG = "1"  # Real bookings
  }
}
```

---

### Challenge 5: Error Handling & Timeouts

**LangGraph Approach:**
```python
try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()
except Exception as e:
    logger.error(f"API error: {str(e)}")
    return "❌ Error fetching data"
```

**Bedrock Considerations:**
- Lambda timeout: 15 minutes max (configure to 30-60 seconds)
- API timeout: Set requests timeout (e.g., 20 seconds)
- Bedrock timeout: 25 seconds default
- Must handle gracefully to avoid user-facing errors

**Best Practices:**
```python
def call_api(url, headers, timeout=20):
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.Timeout:
        return {"success": False, "error": "API timeout - please try again"}
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            return {"success": False, "error": "Authentication failed"}
        elif e.response.status_code == 404:
            return {"success": False, "error": "Resource not found"}
        else:
            return {"success": False, "error": f"API error: {e.response.status_code}"}
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {"success": False, "error": "Unexpected error occurred"}
```

---

## Migration Strategy

### Approach: Phased Migration with Feature Flags

**Why Phased?**
- Minimize risk
- Test incrementally
- Easy rollback
- Parallel testing (mock vs real)

**Feature Flag Strategy:**

**Lambda Environment Variable:**
```bash
USE_REAL_API=false  # Start with false (mock data)
```

**Lambda Code:**
```python
def handler(event, context):
    use_real_api = os.getenv("USE_REAL_API", "false") == "true"

    if use_real_api:
        # Call real PF360 API
        return call_real_api(event)
    else:
        # Return mock data (current behavior)
        return get_mock_data(event)
```

**Gradual Rollout:**
1. Phase 1: Deploy with `USE_REAL_API=false` (no change)
2. Phase 2: Test with `USE_REAL_API=true` in dev environment
3. Phase 3: Enable for specific test users in prod
4. Phase 4: Enable for all users
5. Phase 5: Remove mock code

---

## Implementation Phases

### Phase 1: Preparation & Infrastructure (2-3 days)

#### 1.1 DynamoDB Session Table Setup
**Task:** Create DynamoDB table for session state storage

**Table Schema:**
```
Table Name: bedrock-sessions-{env}
Partition Key: session_id (String)
TTL Attribute: ttl (Number, Unix timestamp)

Attributes:
- session_id: "sess_abc123"
- customer_id: "CUST001"
- client_id: "acme-corp"
- client_name: "acme-corp"
- auth_token: "Bearer xyz123..."
- request_id: "req_abc123" (for scheduling session)
- selected_project_id: "12345"
- environment: "dev"
- ttl: 1729543200 (auto-delete after 30 min)
```

**Terraform:**
```hcl
# infrastructure/terraform/dynamodb.tf
resource "aws_dynamodb_table" "bedrock_sessions" {
  name           = "bedrock-sessions-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "session_id"

  attribute {
    name = "session_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Environment = var.environment
    Project     = "bedrock-agents"
  }
}
```

**Actions:**
- [ ] Create Terraform config
- [ ] Deploy to dev environment
- [ ] Test TTL auto-deletion (set 1-minute TTL)
- [ ] Deploy to qa/staging/prod

---

#### 1.2 Lambda IAM Permissions
**Task:** Grant Lambda functions DynamoDB access

**IAM Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:*:table/bedrock-sessions-*"
    }
  ]
}
```

**Terraform:**
```hcl
# infrastructure/terraform/iam.tf
resource "aws_iam_role_policy_attachment" "lambda_dynamodb" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_dynamodb_policy.arn
}
```

**Actions:**
- [ ] Add DynamoDB permissions to Lambda role
- [ ] Test Lambda can read/write DynamoDB
- [ ] Verify in all environments

---

#### 1.3 Environment Configuration
**Task:** Set up environment variables for all Lambda functions

**Variables to Add:**
```bash
# API Configuration
CUSTOMER_SCHEDULER_BASE_API_URL=https://api.dev.projectsforce.com
ENVIRONMENT=dev

# Feature Flags
USE_REAL_API=false          # Start false, enable per phase
CONFIRM_SCHEDULE_FLAG=0     # 0=test mode, 1=real booking
CANCEL_SCHEDULE_FLAG=0      # 0=test mode, 1=real cancellation

# DynamoDB
DYNAMODB_SESSION_TABLE=bedrock-sessions-dev
AWS_REGION=us-east-1

# Timeouts
API_TIMEOUT=20              # Seconds
```

**Update Terraform:**
```hcl
# infrastructure/terraform/lambda.tf
environment {
  variables = {
    CUSTOMER_SCHEDULER_BASE_API_URL = var.api_base_url
    ENVIRONMENT                     = var.environment
    USE_REAL_API                    = var.use_real_api
    CONFIRM_SCHEDULE_FLAG           = var.confirm_schedule_flag
    CANCEL_SCHEDULE_FLAG            = var.cancel_schedule_flag
    DYNAMODB_SESSION_TABLE          = aws_dynamodb_table.bedrock_sessions.name
    AWS_REGION                      = var.aws_region
    API_TIMEOUT                     = 20
  }
}
```

**Actions:**
- [ ] Update terraform variables
- [ ] Apply to dev environment
- [ ] Verify environment variables in Lambda console
- [ ] Document variable purposes in README

---

#### 1.4 Create Shared Lambda Layer
**Task:** Create Python layer with common dependencies

**Dependencies:**
```
requests==2.31.0
boto3==1.34.0
python-dateutil==2.8.2
pytz==2023.3
```

**Layer Structure:**
```
lambda-layer/
├── python/
│   ├── lib/
│   │   ├── api_client.py      # Shared API client
│   │   ├── session_manager.py # DynamoDB session helper
│   │   ├── auth_helper.py     # Auth utilities
│   │   └── utils.py           # Common utilities
│   └── requirements.txt
└── build.sh
```

**Shared API Client (`api_client.py`):**
```python
import requests
import os
import logging

logger = logging.getLogger()

class PF360APIClient:
    def __init__(self, session_data):
        self.base_url = os.getenv("CUSTOMER_SCHEDULER_BASE_API_URL")
        self.client_id = session_data["client_id"]
        self.auth_token = session_data["auth_token"]
        self.timeout = int(os.getenv("API_TIMEOUT", 20))

    def _headers(self):
        return {
            "authorization": self.auth_token,
            "client_id": self.client_id,
            "Content-Type": "application/json",
            "charset": "utf-8"
        }

    def get(self, endpoint):
        """Make GET request with error handling"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, headers=self._headers(), timeout=self.timeout)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.Timeout:
            logger.error(f"Timeout calling {url}")
            return {"success": False, "error": "API timeout"}
        except requests.HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code}: {url}")
            return {"success": False, "error": f"API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return {"success": False, "error": "Unexpected error"}

    def post(self, endpoint, data):
        """Make POST request with error handling"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.post(url, headers=self._headers(), json=data, timeout=self.timeout)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            logger.error(f"POST error: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
```

**Session Manager (`session_manager.py`):**
```python
import boto3
import os
import time

class SessionManager:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(os.getenv('DYNAMODB_SESSION_TABLE'))

    def get_session(self, session_id):
        """Retrieve session data from DynamoDB"""
        response = self.table.get_item(Key={'session_id': session_id})
        return response.get('Item')

    def update_session(self, session_id, updates):
        """Update session data"""
        # Add 30-minute TTL
        updates['ttl'] = int(time.time()) + 1800

        self.table.put_item(Item={
            'session_id': session_id,
            **updates
        })

    def set_request_id(self, session_id, request_id):
        """Store request_id for scheduling flow"""
        self.table.update_item(
            Key={'session_id': session_id},
            UpdateExpression='SET request_id = :rid, #ttl = :ttl',
            ExpressionAttributeNames={'#ttl': 'ttl'},
            ExpressionAttributeValues={
                ':rid': request_id,
                ':ttl': int(time.time()) + 1800
            }
        )

    def get_request_id(self, session_id):
        """Retrieve request_id for scheduling flow"""
        session = self.get_session(session_id)
        return session.get('request_id') if session else None
```

**Actions:**
- [ ] Create lambda-layer directory
- [ ] Write shared modules
- [ ] Create build script
- [ ] Deploy layer to AWS
- [ ] Attach to all 3 Lambda functions

---

### Phase 2: Lambda Function Updates (3-5 days)

#### 2.1 Update `scheduling-actions` Lambda

**Current Actions (Mock):**
1. `list_projects` - Returns mock projects
2. `get_available_dates` - Returns mock dates
3. `get_time_slots` - Returns mock time slots
4. `confirm_appointment` - Mock confirmation
5. `cancel_appointment` - Mock cancellation
6. `get_business_hours` - Mock business hours

**Updates Required:**

**Action 1: `list_projects`**

**Current (Mock):**
```python
def list_projects(customer_id):
    return MOCK_DATA["projects"]
```

**Updated (Real API):**
```python
def list_projects(session_id, customer_id):
    # Get session with auth token
    session_mgr = SessionManager()
    session = session_mgr.get_session(session_id)

    if not session:
        return {"error": "Invalid session"}

    # Call real API
    api_client = PF360APIClient(session)
    result = api_client.get(f"/dashboard/get/{session['client_id']}/{customer_id}")

    if not result["success"]:
        return {"error": result["error"]}

    # Transform flattened data to clean format
    projects = extract_projects(result["data"])

    # Build project URLs
    for project in projects:
        project["project_url"] = build_project_url(
            session["client_name"],
            session["environment"],
            project["project_id"]
        )

    return {"projects": projects}

def extract_projects(raw_data):
    """Transform API response to clean project list"""
    projects = []
    for i, item in enumerate(raw_data.get("data", [])):
        projects.append({
            "project_number": i + 1,
            "project_id": item.get("project_project_id"),
            "order_number": item.get("project_project_number"),
            "project_type": item.get("project_type_project_type"),
            "category": item.get("project_category_category"),
            "status": item.get("status_info_status"),
            # ... (same transformation as LangGraph code)
        })
    return projects

def build_project_url(client_name, env, project_id):
    """Build clickable project URL"""
    env_map = {"dev": "dev", "qa": "qa", "staging": "staging", "prod": "apps"}
    domain = env_map.get(env, "dev")
    return f"https://{client_name}.cx-portal.{domain}.projectsforce.com/details/{project_id}"
```

**Schema Update (OpenAPI):**
```json
{
  "list_projects": {
    "parameters": {
      "session_id": {"type": "string", "required": true},
      "customer_id": {"type": "string", "required": true}
    }
  }
}
```

---

**Action 2: `get_available_dates`**

**Current (Mock):**
```python
def get_available_dates(customer_id, project_id):
    return MOCK_DATA["available_dates"]
```

**Updated (Real API):**
```python
def get_available_dates(session_id, customer_id, project_id):
    session_mgr = SessionManager()
    session = session_mgr.get_session(session_id)

    api_client = PF360APIClient(session)

    # Get today's date
    today = datetime.now().strftime("%Y-%m-%d")

    # Call API
    endpoint = f"/scheduler/client/{session['client_id']}/project/{project_id}/date/{today}/selected/{today}/get-rescheduler-slots"
    result = api_client.get(endpoint)

    if not result["success"]:
        return {"error": result["error"]}

    data = result["data"]["data"]
    dates = data["dates"]
    request_id = data["request_id"]

    # CRITICAL: Store request_id for next steps
    session_mgr.set_request_id(session_id, request_id)

    return {
        "available_dates": dates,
        "request_id": request_id  # Return to user for transparency
    }
```

**Key Point:** `request_id` is stored in DynamoDB for subsequent calls

---

**Action 3: `get_time_slots`**

**Current (Mock):**
```python
def get_time_slots(customer_id, project_id, date):
    return MOCK_DATA["time_slots"]
```

**Updated (Real API):**
```python
def get_time_slots(session_id, customer_id, project_id, date):
    session_mgr = SessionManager()
    session = session_mgr.get_session(session_id)

    # CRITICAL: Retrieve request_id from DynamoDB
    request_id = session_mgr.get_request_id(session_id)

    if not request_id:
        return {"error": "No active scheduling session. Please get available dates first."}

    api_client = PF360APIClient(session)

    # Call API with request_id
    endpoint = f"/scheduler/client/{session['client_id']}/project/{project_id}/date/{date}/selected/{date}/get-rescheduler-slots?request_id={request_id}"
    result = api_client.get(endpoint)

    if not result["success"]:
        return {"error": result["error"]}

    slots = result["data"]["data"]["slots"]

    return {"time_slots": slots}
```

**Key Point:** Uses stored `request_id` from previous call

---

**Action 4: `confirm_appointment`**

**Current (Mock):**
```python
def confirm_appointment(customer_id, project_id, date, time):
    return {"message": "Mock appointment confirmed"}
```

**Updated (Real API):**
```python
def confirm_appointment(session_id, customer_id, project_id, date, time):
    session_mgr = SessionManager()
    session = session_mgr.get_session(session_id)

    # Get request_id
    request_id = session_mgr.get_request_id(session_id)

    if not request_id:
        return {"error": "No active scheduling session"}

    # Check feature flag
    confirm_flag = int(os.getenv("CONFIRM_SCHEDULE_FLAG", 0))

    if confirm_flag == 0:
        # Test mode: Don't actually book
        return {
            "message": "TEST MODE: Appointment would be confirmed",
            "date": date,
            "time": time,
            "test_mode": True
        }

    # Real booking
    api_client = PF360APIClient(session)

    # Format timestamp for IST timezone
    created_at = datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%m-%d-%Y %H:%M:%S")

    payload = {
        "created_at": created_at,
        "date": date,
        "time": time,
        "request_id": request_id,
        "is_chatbot": "true"  # String, not boolean
    }

    endpoint = f"/scheduler/client/{session['client_id']}/project/{project_id}/schedule"
    result = api_client.post(endpoint, payload)

    if not result["success"]:
        return {"error": result["error"]}

    # Clear request_id after successful booking
    session_mgr.update_session(session_id, {"request_id": None})

    return {
        "message": result["data"].get("message", "Appointment confirmed"),
        "date": date,
        "time": time
    }
```

**Key Points:**
- Uses `request_id` from DynamoDB
- Respects `CONFIRM_SCHEDULE_FLAG` for testing
- Timezone: Asia/Kolkata (hardcoded, should be configurable)
- Clears `request_id` after successful booking

---

**Action 5: `cancel_appointment`**

**Current (Mock):**
```python
def cancel_appointment(customer_id, project_id):
    return {"message": "Mock appointment cancelled"}
```

**Updated (Real API):**
```python
def cancel_appointment(session_id, customer_id, project_id):
    session_mgr = SessionManager()
    session = session_mgr.get_session(session_id)

    # Check feature flag
    cancel_flag = int(os.getenv("CANCEL_SCHEDULE_FLAG", 0))

    if cancel_flag == 0:
        return {
            "message": "TEST MODE: Appointment would be cancelled",
            "test_mode": True
        }

    # Real cancellation
    api_client = PF360APIClient(session)
    endpoint = f"/scheduler/client/{session['client_id']}/project/{project_id}/cancel-reschedule"
    result = api_client.get(endpoint)

    if not result["success"]:
        return {"error": result["error"]}

    return {"message": result["data"].get("message", "Appointment cancelled")}
```

---

**Action 6: `get_business_hours`**

**Updated (Real API):**
```python
def get_business_hours(session_id, client_id):
    session_mgr = SessionManager()
    session = session_mgr.get_session(session_id)

    api_client = PF360APIClient(session)
    endpoint = f"/scheduler/client/{client_id}/business-hours"
    result = api_client.get(endpoint)

    if not result["success"]:
        return {"error": result["error"]}

    work_hours = result["data"]["data"]["workHours"]
    working_days = [day["day"] for day in work_hours if day["is_working"]]

    return {
        "working_days": working_days,
        "details": work_hours
    }
```

---

**Actions:**
- [ ] Update handler.py with real API code
- [ ] Add shared layer (api_client, session_manager)
- [ ] Update OpenAPI schema (add session_id parameter)
- [ ] Deploy to dev
- [ ] Test with `USE_REAL_API=false` (should still work)
- [ ] Test with `USE_REAL_API=true` in dev

---

#### 2.2 Update `information-actions` Lambda

**Actions to Update:**
1. `get_project_details` - Currently mock
2. `get_project_status` - Currently mock
3. `get_technician_info` - Currently mock
4. `list_all_projects` - Duplicate of scheduling action

**Update Pattern (Same as Scheduling):**
```python
def get_project_details(session_id, customer_id, project_id):
    session_mgr = SessionManager()
    session = session_mgr.get_session(session_id)

    # Get all projects
    api_client = PF360APIClient(session)
    result = api_client.get(f"/dashboard/get/{session['client_id']}/{customer_id}")

    if not result["success"]:
        return {"error": result["error"]}

    # Find specific project
    projects = extract_projects(result["data"])
    project = next((p for p in projects if p["project_id"] == project_id), None)

    if not project:
        return {"error": f"Project {project_id} not found"}

    return {"project": project}
```

**Actions:**
- [ ] Update all 4 actions with real API calls
- [ ] Deploy to dev
- [ ] Test

---

#### 2.3 Update `notes-actions` Lambda

**Actions to Update:**
1. `add_note` - Mock
2. `get_notes` - Mock (API doesn't have GET endpoint)

**Update `add_note`:**
```python
def add_note(session_id, customer_id, project_id, note_text):
    session_mgr = SessionManager()
    session = session_mgr.get_session(session_id)

    api_client = PF360APIClient(session)

    payload = {"note_text": note_text}
    endpoint = f"/project-notes/add/{session['client_id']}/{project_id}"

    result = api_client.post(endpoint, payload)

    if not result["success"]:
        return {"error": result["error"]}

    return {
        "message": "Note added successfully",
        "note_text": note_text
    }
```

**`get_notes` Challenge:**
- LangGraph code stores notes locally: `session_context[session_id]["notes"]`
- No API endpoint to retrieve notes from PF360
- Options:
  1. Store in DynamoDB when added (local cache)
  2. Remove get_notes action (not supported by API)
  3. Ask backend team to add GET endpoint

**Recommendation:** Option 1 (DynamoDB cache) + note in docs that it only shows notes added via chatbot

**Actions:**
- [ ] Update add_note with real API
- [ ] Implement DynamoDB note caching for get_notes
- [ ] Document limitation
- [ ] Deploy and test

---

### Phase 3: Agent Instruction Updates (2-3 days)

#### 3.1 Update Action Schemas (OpenAPI)

**Add `session_id` to all actions**

**Example (scheduling-actions-schema.json):**
```json
{
  "openapi": "3.0.0",
  "paths": {
    "/list_projects": {
      "post": {
        "parameters": [
          {
            "name": "session_id",
            "in": "query",
            "required": true,
            "schema": {"type": "string"},
            "description": "Session ID for authentication and state tracking"
          },
          {
            "name": "customer_id",
            "in": "query",
            "required": true,
            "schema": {"type": "string"}
          }
        ]
      }
    }
  }
}
```

**Actions:**
- [ ] Update all 3 OpenAPI schemas
- [ ] Deploy schemas to S3
- [ ] Update action group configurations
- [ ] Re-prepare agents

---

#### 3.2 Update Agent Instructions

**Add Session Context Extraction**

**Scheduling Agent Instructions:**
```
You are a scheduling specialist.

CRITICAL CONTEXT EXTRACTION:
The supervisor will provide session context in their message:
- Session ID: Extract from "Session ID: <value>"
- Customer ID: Extract from "Customer ID: <value>"

ALWAYS include session_id in EVERY action call.

Example:
Supervisor says: "Help customer schedule. Session ID: sess_123, Customer ID: CUST001"
You call: list_projects(session_id="sess_123", customer_id="CUST001")

SCHEDULING FLOW (Multi-Step):
1. list_projects → User picks project
2. get_available_dates → Returns dates AND request_id
3. User picks date
4. get_time_slots → Uses stored request_id
5. User picks time
6. confirm_appointment → Books appointment

IMPORTANT:
- request_id is managed automatically (stored in backend)
- Always pass session_id for state tracking
- If API returns error, inform user clearly
```

**Actions:**
- [ ] Update all 4 specialist agent instructions
- [ ] Update supervisor instructions to pass session_id
- [ ] Deploy via `scripts/complete_setup.py`
- [ ] Test context extraction

---

### Phase 4: Frontend Updates (2-3 days)

#### 4.1 Add Authentication to Frontend

**Update Frontend to Send Auth Token**

**Current (frontend/backend/app.py):**
```python
SAMPLE_USER = {
    'customer_id': 'CUST001',
    'customer_type': 'B2C',
    # No auth token
}
```

**Updated:**
```python
@app.route('/api/chat/simple', methods=['POST'])
def chat_simple():
    data = request.json
    message = data.get('message')

    # NEW: Get auth token from request headers
    auth_token = request.headers.get('Authorization')

    if not auth_token:
        return jsonify({'error': 'Authentication required'}), 401

    # TODO: Validate token (JWT decode, check expiry, etc.)
    # For now, extract customer info from token or database

    customer_id = extract_customer_id(auth_token)  # Implement this
    client_id = extract_client_id(auth_token)
    client_name = extract_client_name(auth_token)

    # Generate session ID
    session_id = f"sess_{customer_id}_{int(time.time())}"

    # Store in DynamoDB
    store_session(session_id, {
        'customer_id': customer_id,
        'client_id': client_id,
        'client_name': client_name,
        'auth_token': auth_token,
        'environment': os.getenv('ENVIRONMENT', 'dev')
    })

    # Augment prompt with session context
    augmented_prompt = f"""Session Context:
- Session ID: {session_id}
- Customer ID: {customer_id}
- Client ID: {client_id}

User Request: {message}

Please help the customer with their request."""

    # Call Bedrock
    full_response = ""
    for chunk in invoke_agent_with_context(augmented_prompt, customer_id):
        full_response += chunk

    return jsonify({
        'response': full_response,
        'session_id': session_id,
        'timestamp': time.time()
    })
```

**Frontend (React):**
```typescript
// src/App.tsx
const sendMessage = async (text: string) => {
  // Get auth token (from login, localStorage, etc.)
  const authToken = localStorage.getItem('auth_token');

  const response = await axios.post('/api/chat/simple', {
    message: text
  }, {
    headers: {
      'Authorization': authToken
    }
  });

  // Display response
  setMessages([...messages, {
    text: response.data.response,
    sender: 'ai',
    timestamp: new Date()
  }]);
};
```

**Actions:**
- [ ] Add auth token to Flask backend
- [ ] Implement DynamoDB session storage in Flask
- [ ] Update frontend to send auth token
- [ ] Add login flow (if needed)
- [ ] Test end-to-end with real auth

---

#### 4.2 Update Sample User (Optional)

**For Testing Without Real Auth:**
```python
# backend/app.py - Development mode
if os.getenv('ENVIRONMENT') == 'dev':
    # Use hardcoded test token
    TEST_AUTH_TOKEN = os.getenv('TEST_AUTH_TOKEN', 'Bearer test_token_dev')
    TEST_CUSTOMER_ID = 'CUST001'
    TEST_CLIENT_ID = 'acme-corp'
    TEST_CLIENT_NAME = 'acme-corp'
else:
    # Production: Require real auth
    pass
```

---

### Phase 5: Testing & Validation (3-5 days)

#### 5.1 Unit Testing

**Test Each Lambda Action Independently**

**Test Script Template:**
```python
# tests/test_scheduling_lambda.py
import json
import boto3

def test_list_projects():
    # Setup: Create test session in DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('bedrock-sessions-dev')
    table.put_item(Item={
        'session_id': 'test_sess_123',
        'customer_id': 'CUST001',
        'client_id': 'acme-corp',
        'client_name': 'acme-corp',
        'auth_token': 'Bearer <real_test_token>',
        'environment': 'dev',
        'ttl': int(time.time()) + 1800
    })

    # Invoke Lambda
    lambda_client = boto3.client('lambda')
    response = lambda_client.invoke(
        FunctionName='scheduling-actions',
        Payload=json.dumps({
            'actionGroup': 'scheduling-actions',
            'action': 'list_projects',
            'parameters': [
                {'name': 'session_id', 'value': 'test_sess_123'},
                {'name': 'customer_id', 'value': 'CUST001'}
            ]
        })
    )

    result = json.loads(response['Payload'].read())

    # Assertions
    assert 'projects' in result
    assert len(result['projects']) > 0
    assert 'project_id' in result['projects'][0]
```

**Test Cases:**
- [ ] Test with `USE_REAL_API=false` (mock mode)
- [ ] Test with `USE_REAL_API=true` (real API in dev)
- [ ] Test invalid session_id (should error gracefully)
- [ ] Test expired session (DynamoDB TTL)
- [ ] Test invalid auth token (401 error)
- [ ] Test API timeout handling
- [ ] Test multi-step flow (dates → slots → confirm)

---

#### 5.2 Integration Testing

**End-to-End Flow Tests**

**Test Scenario 1: List and View Projects**
```
User: "Show me all my projects"
Expected:
  1. Bedrock calls list_projects(session_id, customer_id)
  2. Lambda retrieves session from DynamoDB
  3. Lambda calls PF360 API
  4. Returns real project list
  5. User sees projects with clickable URLs
```

**Test Scenario 2: Schedule Appointment (Full Flow)**
```
User: "I want to schedule my flooring project"
Step 1: Agent matches project, calls get_available_dates
  → Lambda stores request_id in DynamoDB
  → Returns dates to user

User: "October 21st works"
Step 2: Agent calls get_time_slots(date="2025-10-21")
  → Lambda retrieves request_id from DynamoDB
  → Returns slots

User: "10:00 AM please"
Step 3: Agent calls confirm_appointment(date, time)
  → Lambda retrieves request_id
  → Books appointment
  → Returns confirmation
```

**Test Matrix:**

| Test Case | Environment | USE_REAL_API | Expected Result |
|-----------|-------------|--------------|-----------------|
| Mock data baseline | dev | false | Mock data returned |
| Real API - list projects | dev | true | Real projects from dev API |
| Real API - full scheduling | dev | true + CONFIRM=0 | Test mode (no real booking) |
| Real API - full scheduling | qa | true + CONFIRM=1 | Real booking in QA |
| Auth failure | dev | true | 401 error, graceful message |
| API timeout | dev | true | Timeout error, retry prompt |
| Invalid session | dev | true | Error: "Invalid session" |

**Actions:**
- [ ] Run all test scenarios in dev
- [ ] Document test results
- [ ] Fix any issues found
- [ ] Repeat in QA environment

---

#### 5.3 Load Testing

**Use Existing Load Test Setup**

**Files:** `tests/LoadTest/`

**Update for Real API:**
```python
# tests/LoadTest/locustfile.py
class BedrockUser(HttpUser):
    def on_start(self):
        # Get real auth token
        self.auth_token = get_test_auth_token()

    @task
    def list_projects(self):
        self.client.post("/api/chat/simple",
            json={"message": "Show me all my projects"},
            headers={"Authorization": self.auth_token}
        )
```

**Load Test Scenarios:**
- [ ] 10 concurrent users
- [ ] 50 concurrent users
- [ ] 100 concurrent users
- [ ] Sustained load (30 min)
- [ ] Spike test (sudden traffic increase)

**Metrics to Track:**
- API response time (P50, P95, P99)
- DynamoDB read/write latency
- Lambda cold start frequency
- Error rate
- API timeout rate

---

## Rollback Plan

### Quick Rollback (Feature Flag)

**If Issues Found in Production:**

**Step 1: Disable Real API (Immediate - 1 minute)**
```bash
# Update Lambda environment variable
aws lambda update-function-configuration \
  --function-name scheduling-actions \
  --environment Variables={USE_REAL_API=false}

# Repeat for other Lambdas
```
**Result:** Immediately reverts to mock data

---

**Step 2: Drain Sessions (5 minutes)**
- DynamoDB sessions auto-expire (30 min TTL)
- Active users may see "Invalid session" temporarily
- New users get mock data immediately

---

**Step 3: Investigate (Offline)**
- Check CloudWatch logs
- Identify root cause
- Fix issue
- Re-test in dev

---

### Full Rollback (Code Deployment)

**If Feature Flag Rollback Not Sufficient:**

**Option A: Redeploy Previous Lambda Version**
```bash
# Lambda keeps previous versions
aws lambda update-alias \
  --function-name scheduling-actions \
  --name PROD \
  --function-version <previous_version>
```

**Option B: Terraform Rollback**
```bash
cd infrastructure/terraform
git checkout <previous_commit>
terraform apply
```

---

### Communication Plan

**If Rollback Required:**

1. **Internal Notification** (Slack, Email)
   - "Real API integration temporarily disabled"
   - "Users will see sample data until issue resolved"
   - ETA for fix

2. **User Communication** (If applicable)
   - Display banner: "Scheduling temporarily unavailable"
   - Provide alternative contact method

3. **Post-Mortem** (After resolution)
   - Root cause analysis
   - Prevention measures
   - Updated testing procedures

---

## Success Criteria

### Phase 1 Success (Infrastructure)
- [ ] DynamoDB table created in all environments
- [ ] Lambda IAM permissions verified
- [ ] Environment variables set correctly
- [ ] Shared Lambda layer deployed
- [ ] Feature flags working (toggle real API on/off)

### Phase 2 Success (Lambda Updates)
- [ ] All 12 actions updated with real API code
- [ ] Mock mode still works (`USE_REAL_API=false`)
- [ ] Real API mode works in dev (`USE_REAL_API=true`)
- [ ] Error handling tested (timeouts, 401, 404, 500)
- [ ] Session state tracking working (request_id)

### Phase 3 Success (Agent Updates)
- [ ] OpenAPI schemas updated with session_id
- [ ] Agent instructions updated
- [ ] Agents extract session_id correctly
- [ ] Multi-step flows work (dates → slots → confirm)

### Phase 4 Success (Frontend)
- [ ] Auth token flow implemented
- [ ] Session creation working
- [ ] End-to-end conversation flow working
- [ ] Project URLs clickable and correct

### Phase 5 Success (Testing)
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Load tests meet performance targets
- [ ] No errors in CloudWatch logs
- [ ] DynamoDB auto-cleanup (TTL) working

### Production Readiness
- [ ] Deployed to QA environment
- [ ] Tested by QA team
- [ ] Performance metrics acceptable
- [ ] Error rate < 1%
- [ ] Rollback plan tested
- [ ] Documentation updated
- [ ] Team trained on new system

---

## Appendices

### Appendix A: API Endpoint Reference

**Base URL:**
```
Dev:     https://api.dev.projectsforce.com
QA:      https://api.qa.projectsforce.com
Staging: https://api.staging.projectsforce.com
Prod:    https://api.projectsforce.com
```

**Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/dashboard/get/{client_id}/{customer_id}` | GET | List projects |
| `/scheduler/client/{client_id}/business-hours` | GET | Business hours |
| `/scheduler/client/{client_id}/project/{id}/date/{d1}/selected/{d2}/get-rescheduler-slots` | GET | Dates (returns request_id) |
| `/scheduler/client/{client_id}/project/{id}/date/{d1}/selected/{d2}/get-rescheduler-slots?request_id={rid}` | GET | Time slots |
| `/scheduler/client/{client_id}/project/{id}/schedule` | POST | Confirm appointment |
| `/scheduler/client/{client_id}/project/{id}/cancel-reschedule` | GET | Cancel appointment |
| `/project-notes/add/{client_id}/{project_id}` | POST | Add note |

---

### Appendix B: DynamoDB Schema

**Table:** `bedrock-sessions-{env}`

**Sample Item:**
```json
{
  "session_id": "sess_CUST001_1729543200",
  "customer_id": "CUST001",
  "client_id": "acme-corp",
  "client_name": "acme-corp",
  "auth_token": "Bearer eyJhbGc...",
  "environment": "dev",
  "request_id": "req_abc123xyz",
  "selected_project_id": "12345",
  "ttl": 1729545000
}
```

**Indexes:** None (single partition key)

**TTL:** 30 minutes (1800 seconds)

---

### Appendix C: Environment Variables

**Lambda Environment Variables:**
```bash
# API Configuration
CUSTOMER_SCHEDULER_BASE_API_URL=https://api.dev.projectsforce.com
ENVIRONMENT=dev

# Feature Flags
USE_REAL_API=false
CONFIRM_SCHEDULE_FLAG=0
CANCEL_SCHEDULE_FLAG=0

# DynamoDB
DYNAMODB_SESSION_TABLE=bedrock-sessions-dev
AWS_REGION=us-east-1

# Timeouts
API_TIMEOUT=20
```

---

### Appendix D: Testing Checklist

**Pre-Deployment:**
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Load tests pass
- [ ] Code reviewed
- [ ] Documentation updated

**Post-Deployment:**
- [ ] Smoke tests in dev
- [ ] Smoke tests in QA
- [ ] Performance monitoring
- [ ] Error rate monitoring
- [ ] User acceptance testing

**Rollback Readiness:**
- [ ] Feature flags tested
- [ ] Previous version tagged
- [ ] Rollback procedure documented
- [ ] Team briefed on rollback

---

## Next Steps

1. **Review this plan** with team
2. **Assign owners** for each phase
3. **Set timeline** for each phase
4. **Create JIRA tickets** (or equivalent)
5. **Begin Phase 1** (Infrastructure setup)

---

**Questions? Concerns? Clarifications needed?**

Please review and provide feedback before beginning implementation.

---

**Document Owner:** Claude Code
**Last Updated:** October 19, 2025
**Version:** 1.0
**Status:** Draft - Awaiting Approval
