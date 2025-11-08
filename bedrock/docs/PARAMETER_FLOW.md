# Parameter Flow: Authentication & Data Through the System

## Overview

This document explains how authentication tokens (Bearer), client IDs, customer IDs, and other parameters flow from user queries through Bedrock Agents to Lambda functions and finally to the ProjectForce API.

---

## Complete Flow Diagram

```
User Query: "List my projects for customer 12345"
    ↓
┌─────────────────────────────────────────────────────────┐
│ Bedrock Agent (SchedulingAgent)                         │
│ - Extracts: customer_id = "12345"                       │
│ - Session Attributes: {client_id: "09PF05VD"}           │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ Lambda Event Payload                                     │
│ {                                                        │
│   "actionGroup": "scheduling-actions",                   │
│   "function": "list_projects",                           │
│   "parameters": [                                        │
│     {"name": "customer_id", "value": "12345"}            │
│   ],                                                     │
│   "sessionAttributes": {                                 │
│     "client_id": "09PF05VD"                              │
│   }                                                      │
│ }                                                        │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ Lambda: handler.py                                       │
│ 1. extract_parameters(event)                             │
│    → customer_id = "12345"                               │
│                                                          │
│ 2. get_auth_headers()                                    │
│    → Calls TokenManager.get_bearer_token()               │
│    → Retrieves from AWS Secrets Manager                  │
│    → Returns Bearer token                                │
│                                                          │
│ 3. Build headers:                                        │
│    {                                                     │
│      "Authorization": "Bearer <token_from_secrets>",     │
│      "Client_Id": "09PF05VD",                            │
│      "Content-Type": "application/json"                  │
│    }                                                     │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ HTTP Request to ProjectForce API                         │
│ GET https://api.dev.projectsforce.com/projects           │
│                                                          │
│ Headers:                                                 │
│   Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI...   │
│   Client_Id: 09PF05VD                                    │
│   Content-Type: application/json                         │
│                                                          │
│ Query Params:                                            │
│   customer_id=12345                                      │
└─────────────────────────────────────────────────────────┘
    ↓
API Response → Lambda → Bedrock Agent → User
```

---

## 1. Bearer Token (Authentication)

### Where It Comes From

The Bearer token is stored in **AWS Secrets Manager** and retrieved dynamically by Lambda functions.

### Storage Location
```
Secret Name: projectforce/api/dev/credentials
Secret Value: {
  "bearer_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "client_id": "09PF05VD",
  "refresh_token": "refresh_token_value_here"
}
```

### Retrieval Flow

**Step 1: TokenManager (token_manager.py)**
```python
def get_bearer_token() -> str:
    """
    Retrieves bearer token from AWS Secrets Manager
    Uses caching to minimize API calls
    """
    secret_name = "projectforce/api/dev/credentials"

    # Get secret from AWS Secrets Manager
    secret_value = secretsmanager.get_secret_value(SecretId=secret_name)
    secret_dict = json.loads(secret_value['SecretString'])

    return secret_dict['bearer_token']
```

**Step 2: Lambda Config (config.py)**
```python
def get_auth_headers(authorization: str = None, client_id: str = None):
    """
    Generate authentication headers for ProjectForce API
    """
    if not authorization:
        if TOKEN_MANAGER_AVAILABLE:
            token = get_bearer_token()
            authorization = f"Bearer {token}"
        else:
            # Fallback to environment variable
            authorization = f"Bearer {BEARER_TOKEN}"

    return {
        "Authorization": authorization,
        "Client_Id": client_id or DEFAULT_CLIENT_ID
    }
```

### Fallback Chain

1. **TokenManager** (Secrets Manager) - PRIMARY
2. **Environment Variable** `BEARER_TOKEN` - FALLBACK
3. **PLACEHOLDER** - Used during development

### Token Lifecycle

```
1. User authenticates → OAuth2 server
2. Server returns access_token + refresh_token
3. Tokens stored in Secrets Manager
4. Lambda retrieves token on-demand
5. Token cached for 3600 seconds
6. When expired, TokenManager auto-refreshes using refresh_token
```

---

## 2. Client ID

### What It Is

`Client_Id` is a ProjectForce API identifier that distinguishes between different clients/customers in a B2B context.

### Default Value
```python
DEFAULT_CLIENT_ID = "09PF05VD"
```

### Where It Comes From

**Option 1: Session Attributes (from Bedrock Agent)**
```python
client_id = event.get('sessionAttributes', {}).get('client_id')
```

**Option 2: Function Parameters**
```python
# For functions that accept client_id explicitly
parameters = extract_parameters(event)
client_id = parameters.get('client_id')
```

**Option 3: Secrets Manager**
```python
secret_dict = json.loads(secret_value['SecretString'])
client_id = secret_dict.get('client_id', DEFAULT_CLIENT_ID)
```

**Option 4: Default Fallback**
```python
client_id = client_id or DEFAULT_CLIENT_ID
```

### Usage in API Headers
```python
headers = {
    "Client_Id": "09PF05VD"  # Note: Capital C and I
}
```

---

## 3. Customer ID

### What It Is

`customer_id` identifies the specific customer whose data is being accessed (projects, appointments, etc.)

### Where It Comes From

**Extracted from Bedrock Agent parameters:**

```python
def extract_parameters(event: Dict) -> Dict[str, Any]:
    """
    Bedrock Agent passes parameters in the event
    """
    if 'parameters' in event and event['parameters']:
        # Format: [{"name": "customer_id", "type": "string", "value": "12345"}]
        params = {p['name']: p['value'] for p in event['parameters']}
        return params
```

**Example Bedrock Event:**
```json
{
  "actionGroup": "scheduling-actions",
  "function": "list_projects",
  "parameters": [
    {
      "name": "customer_id",
      "type": "string",
      "value": "12345"
    }
  ]
}
```

### Usage in Lambda Functions

**handler.py (list_projects):**
```python
def list_projects(customer_id: str, client_id: str = None):
    """List all projects for a customer"""

    # Build API request
    url = f"{API_BASE_URL}/projects"
    params = {"customer_id": customer_id}

    if client_id:
        params["client_id"] = client_id

    headers = get_auth_headers(client_id=client_id)

    response = requests.get(url, headers=headers, params=params)
    return response.json()
```

---

## 4. Complete Parameter Flow Examples

### Example 1: List Projects

**User Query:**
```
"Show me all my projects"
```

**Bedrock Agent Invocation:**
```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id ILSZT5EWND \
  --agent-alias-id TSTALIASID \
  --session-id "session-123" \
  --input-text "List all my projects" \
  --session-state '{
    "sessionAttributes": {
      "customer_id": "6f72bffa-c323-4058-a01c-9d495d696364",
      "client_id": "09PF05VD",
      "customer_type": "B2C",
      "pf_api_base": "https://api.dev.projectsforce.com"
    }
  }'
```

**Lambda Event Received:**
```json
{
  "messageVersion": "1.0",
  "agent": {
    "name": "SchedulingAgent",
    "id": "ILSZT5EWND",
    "alias": "TSTALIASID",
    "version": "DRAFT"
  },
  "actionGroup": "scheduling-actions",
  "function": "list_projects",
  "parameters": [
    {"name": "customer_id", "type": "string", "value": "6f72bffa-c323-4058-a01c-9d495d696364"}
  ],
  "sessionAttributes": {
    "customer_id": "6f72bffa-c323-4058-a01c-9d495d696364",
    "client_id": "09PF05VD",
    "customer_type": "B2C",
    "pf_api_base": "https://api.dev.projectsforce.com"
  },
  "sessionId": "session-123"
}
```

**Lambda Processing:**
```python
# 1. Extract parameters
params = extract_parameters(event)
customer_id = params.get('customer_id') or \
              event.get('sessionAttributes', {}).get('customer_id')
# Result: "6f72bffa-c323-4058-a01c-9d495d696364"

# 2. Get client_id from session attributes
client_id = event.get('sessionAttributes', {}).get('client_id')  # "09PF05VD"

# 3. Get API base URL
api_base = event.get('sessionAttributes', {}).get('pf_api_base', API_BASE_URL)
# Result: "https://api.dev.projectsforce.com"

# 4. Get auth headers (with Bearer token from Secrets Manager)
headers = get_auth_headers(client_id=client_id)
# {
#   "Authorization": "Bearer eyJhbGci...",
#   "Client_Id": "09PF05VD"
# }

# 5. Call API (NEW endpoint)
url = f"{api_base}/cx-scheduled/projects/{customer_id}"
response = requests.get(url, headers=headers)
```

**HTTP Request to ProjectForce API:**
```http
GET https://api.dev.projectsforce.com/cx-scheduled/projects/6f72bffa-c323-4058-a01c-9d495d696364 HTTP/1.1
Host: api.dev.projectsforce.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Client_Id: 09PF05VD
Content-Type: application/json
Accept: application/json
```

### Example 2: Book Appointment with All Parameters

**User Query:**
```
"Book an appointment for project proj-789 on 2024-01-15 at 10:00 AM"
```

**Lambda Event:**
```json
{
  "function": "book_appointment",
  "parameters": [
    {"name": "project_id", "value": "proj-789"},
    {"name": "appointment_date", "value": "2024-01-15"},
    {"name": "appointment_time", "value": "10:00"},
    {"name": "customer_id", "value": "12345"}
  ],
  "sessionAttributes": {
    "client_id": "09PF05VD",
    "user_name": "John Doe"
  }
}
```

**Lambda Processing:**
```python
# Extract all parameters
params = extract_parameters(event)
project_id = params['project_id']
appointment_date = params['appointment_date']
appointment_time = params['appointment_time']
customer_id = params['customer_id']

# Get auth
headers = get_auth_headers(client_id="09PF05VD")

# Build payload
payload = {
    "project_id": project_id,
    "appointment_date": appointment_date,
    "appointment_time": appointment_time,
    "customer_id": customer_id,
    "booked_by": "John Doe"  # from sessionAttributes
}

# Call API
response = requests.post(
    f"{API_BASE_URL}/appointments",
    headers=headers,
    json=payload
)
```

---

## 5. Authentication Architecture

### Components

1. **AWS Secrets Manager**
   - Stores: bearer_token, refresh_token, client_id
   - Updated by: Deployment scripts or manual updates
   - Accessed by: Lambda functions via TokenManager

2. **TokenManager (token_manager.py)**
   - Retrieves tokens from Secrets Manager
   - Caches tokens (3600s TTL)
   - Auto-refreshes expired tokens
   - Provides thread-safe access

3. **Lambda IAM Role**
   - Permissions:
     - `secretsmanager:GetSecretValue` on projectforce/api/dev/credentials
     - `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`
     - `bedrock:InvokeAgent` (for agent collaboration)

4. **OAuth2 Flow (External)**
   - Auth Server: `https://auth.dev.projectsforce.com`
   - Endpoints:
     - `/oauth2/token` - Get access_token with refresh_token
     - `/oauth2/authorize` - Initial authorization

### Token Refresh Flow

```
1. Lambda calls get_bearer_token()
2. TokenManager checks cache
3. If expired:
   a. Retrieve refresh_token from Secrets Manager
   b. POST to auth.dev.projectsforce.com/oauth2/token
   c. Receive new access_token
   d. Update Secrets Manager
   e. Update cache
4. Return valid bearer_token
```

---

## 6. Security Best Practices

### Current Implementation

✅ **Good:**
- Tokens stored in AWS Secrets Manager (encrypted at rest)
- Lambda IAM roles limit access to specific secrets
- Tokens cached in-memory (not logged)
- Bearer tokens never hardcoded in Lambda code

⚠️ **To Improve:**
- Implement token rotation policy
- Add CloudWatch alarms for authentication failures
- Use VPC endpoints for Secrets Manager access
- Implement rate limiting on token refresh

### Never Do This

❌ **DON'T hardcode tokens in code:**
```python
# BAD - Never do this
BEARER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

❌ **DON'T log tokens:**
```python
# BAD - Never log sensitive data
logger.info(f"Using token: {bearer_token}")
```

❌ **DON'T pass tokens as query parameters:**
```python
# BAD - Tokens in URLs are logged
url = f"{API_BASE_URL}/projects?token={bearer_token}"
```

---

## 7. Testing Parameter Flow

### Test 1: Direct Lambda with Parameters

```bash
aws lambda invoke \
  --function-name pf-scheduling-actions \
  --payload '{
    "actionGroup": "scheduling-actions",
    "function": "list_projects",
    "parameters": [
      {"name": "customer_id", "type": "string", "value": "12345"}
    ],
    "sessionAttributes": {
      "client_id": "09PF05VD"
    }
  }' \
  /tmp/test_response.json

cat /tmp/test_response.json | python3 -m json.tool
```

### Test 2: Agent with Session Attributes

```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id ILSZT5EWND \
  --agent-alias-id TSTALIASID \
  --session-id "test-$(date +%s)" \
  --input-text "List projects for customer 12345" \
  --session-state '{
    "sessionAttributes": {
      "client_id": "09PF05VD",
      "user_name": "Test User"
    }
  }' \
  --region us-east-1 \
  /tmp/agent_response.txt
```

### Test 3: Check Token Retrieval

```bash
# View current token in Secrets Manager
aws secretsmanager get-secret-value \
  --secret-id projectforce/api/dev/credentials \
  --region us-east-1 \
  --query SecretString \
  --output text | python3 -m json.tool
```

### Test 4: Monitor Lambda Logs for Auth

```bash
# Watch logs for authentication flow
aws logs tail /aws/lambda/pf-scheduling-actions \
  --follow \
  --format short \
  --filter-pattern "Bearer" \
  --region us-east-1
```

---

## 8. Debugging Authentication Issues

### Issue 1: "401 Unauthorized"

**Possible Causes:**
- Expired Bearer token in Secrets Manager
- Invalid Client_Id
- Missing Authorization header

**Debug Steps:**
```bash
# 1. Check token in Secrets Manager
aws secretsmanager get-secret-value \
  --secret-id projectforce/api/dev/credentials

# 2. Test token directly with curl
export TOKEN="<token_from_secrets>"
curl -H "Authorization: Bearer $TOKEN" \
     -H "Client_Id: 09PF05VD" \
     https://api.dev.projectsforce.com/projects?customer_id=12345

# 3. Check Lambda logs
aws logs tail /aws/lambda/pf-scheduling-actions --since 10m
```

### Issue 2: "Missing customer_id parameter"

**Possible Causes:**
- Parameter not extracted from Bedrock event
- Wrong parameter name in function schema

**Debug Steps:**
```bash
# 1. Check action group schema
aws bedrock-agent list-agent-action-groups \
  --agent-id ILSZT5EWND \
  --agent-version DRAFT \
  --region us-east-1

# 2. Test direct Lambda invocation
aws lambda invoke \
  --function-name pf-scheduling-actions \
  --payload '{"function": "list_projects", "parameters": [{"name": "customer_id", "value": "test"}]}' \
  /tmp/test.json

# 3. Check Lambda logs for parameter extraction
aws logs tail /aws/lambda/pf-scheduling-actions \
  --since 5m \
  --filter-pattern "Extracted parameters"
```

### Issue 3: "Failed to retrieve token from Secrets Manager"

**Possible Causes:**
- Lambda IAM role missing `secretsmanager:GetSecretValue` permission
- Secret name mismatch
- Region mismatch

**Debug Steps:**
```bash
# 1. Check Lambda IAM role
aws lambda get-function \
  --function-name pf-scheduling-actions \
  --query 'Configuration.Role'

# 2. Check IAM role permissions
aws iam get-role-policy \
  --role-name <role_name_from_step_1> \
  --policy-name lambda-secrets-policy

# 3. Verify secret exists
aws secretsmanager list-secrets \
  --filters Key=name,Values=projectforce/api/dev/credentials
```

---

## 9. Summary

### Key Takeaways

1. **Bearer Token** comes from AWS Secrets Manager via TokenManager
2. **Client_Id** comes from session attributes or defaults to "09PF05VD"
3. **Customer_Id** comes from Bedrock Agent parameters extracted from user query
4. **All parameters** flow through a consistent path: User → Bedrock → Lambda → API
5. **Authentication** is handled transparently by TokenManager with automatic refresh

### Parameter Sources Quick Reference

| Parameter | Source | Example |
|-----------|--------|---------|
| Bearer Token | Secrets Manager via TokenManager | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |
| Client_Id | Session attributes or default | `09PF05VD` |
| Customer_Id | Bedrock Agent parameters | `12345` |
| Project_Id | Bedrock Agent parameters | `proj-789` |
| Appointment_Date | Bedrock Agent parameters | `2024-01-15` |

### File Reference

- **Token Management:** `lambda/scheduling-actions/token_manager.py`
- **Config & Headers:** `lambda/scheduling-actions/config.py`
- **Parameter Extraction:** `lambda/scheduling-actions/handler.py`
- **Secret Management:** AWS Secrets Manager `projectforce/api/dev/credentials`
- **Deployment:** `scripts/DEPLOY.sh` (lines 65-125 for secret creation)

---

## 10. Next Steps

1. **Update Token:** Run `./scripts/get_fresh_token.sh` to get a valid Bearer token
2. **Test Flow:** Run `./scripts/test_agents.sh` to verify end-to-end parameter flow
3. **Monitor Logs:** Watch Lambda logs during testing to see parameter extraction
4. **Verify API:** Test API endpoints directly with curl to confirm authentication
