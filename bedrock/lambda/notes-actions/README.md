# Notes Actions Lambda Function

Handles 2 notes-related actions for the Bedrock Scheduling Agent.

## 🎯 Actions Implemented

| Action | Description | Mock Support | DynamoDB Fallback |
|--------|-------------|--------------|-------------------|
| `add_note` | Add a note to a project | ✅ Yes | ✅ Yes |
| `list_notes` | List all notes for a project | ✅ Yes | ✅ Yes |

## 🔧 Configuration

### Environment Variables

```bash
# Core Configuration
USE_MOCK_API=true                    # true = mock responses, false = real API calls
ENVIRONMENT=dev                       # dev, qa, staging, prod
CUSTOMER_SCHEDULER_API_URL=https://api.projectsforce.com

# DynamoDB Configuration (fallback storage)
DYNAMODB_TABLE=scheduling-agent-notes-dev

# Logging
LOG_LEVEL=INFO
```

### Mock Mode vs Real Mode

**Mock Mode** (`USE_MOCK_API=true`):
- Returns realistic mock responses
- In-memory note storage (resets on Lambda restart)
- Fast and consistent for development
- All responses include `"mock_mode": true`

**Real Mode** (`USE_MOCK_API=false`):
- Attempts to make PF360 API calls
- Falls back to DynamoDB if API unavailable
- Returns live data when available
- All responses include `"mock_mode": false`

### DynamoDB Fallback

**Why DynamoDB Fallback?**
- PF360 list_notes API may not exist
- Provides reliable storage for notes
- Ensures functionality even without dedicated API

**DynamoDB Table Schema:**
```
Table: scheduling-agent-notes-dev
Partition Key: project_id (String)
Sort Key: timestamp (String)

Attributes:
- project_id (String)
- timestamp (String, ISO format)
- note_text (String)
- author (String)
- created_at (String)
```

## 📥 Request Format

Bedrock Agent sends requests in this format:

```json
{
  "messageVersion": "1.0",
  "agent": {
    "name": "scheduling-agent-notes",
    "id": "IX24FSMTQH",
    "alias": "TYJRF3CJ7F",
    "version": "4"
  },
  "sessionId": "session-123",
  "sessionAttributes": {},
  "promptSessionAttributes": {},
  "actionGroup": "notes",
  "apiPath": "/add-note",
  "httpMethod": "POST",
  "parameters": [
    {"name": "project_id", "value": "12345"},
    {"name": "note_text", "value": "Customer requested morning appointment"},
    {"name": "author", "value": "Agent"},
    {"name": "client_id", "value": "09PF05VD"}
  ]
}
```

## 📤 Response Format

All responses follow this format:

```json
{
  "messageVersion": "1.0",
  "response": {
    "actionGroup": "notes",
    "apiPath": "/add-note",
    "httpMethod": "POST",
    "httpStatusCode": 200,
    "responseBody": {
      "application/json": {
        "body": "{\"action\": \"add_note\", \"project_id\": \"12345\", \"note_text\": \"...\", \"mock_mode\": true}"
      }
    }
  }
}
```

## 🧪 Testing Locally

### Test with Mock Data

```bash
# Set mock mode
export USE_MOCK_API=true

# Run handler
python3 handler.py
```

### Test Individual Actions

```python
# Test in Python
import json
from handler import lambda_handler

# Test add_note
event = {
    "apiPath": "/add-note",
    "parameters": [
        {"name": "project_id", "value": "12345"},
        {"name": "note_text", "value": "Test note"},
        {"name": "author", "value": "Test Agent"},
        {"name": "client_id", "value": "09PF05VD"}
    ]
}

response = lambda_handler(event, None)
print(json.dumps(response, indent=2))

# Test list_notes
event2 = {
    "apiPath": "/list-notes",
    "parameters": [
        {"name": "project_id", "value": "12345"},
        {"name": "client_id", "value": "09PF05VD"}
    ]
}

response2 = lambda_handler(event2, None)
print(json.dumps(response2, indent=2))
```

## 📦 Deployment

### Create DynamoDB Table

```bash
# Create DynamoDB table for notes storage
aws dynamodb create-table \
  --table-name scheduling-agent-notes-dev \
  --attribute-definitions \
    AttributeName=project_id,AttributeType=S \
    AttributeName=timestamp,AttributeType=S \
  --key-schema \
    AttributeName=project_id,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### Package Lambda

```bash
# Install dependencies
pip install -r requirements.txt -t package/

# Copy handler files
cp handler.py config.py mock_data.py package/

# Create deployment package
cd package
zip -r ../notes-actions.zip .
cd ..
```

### Deploy to AWS

```bash
# Create/update Lambda function
aws lambda update-function-code \
  --function-name scheduling-agent-notes-actions \
  --zip-file fileb://notes-actions.zip \
  --region us-east-1

# Update environment variables
aws lambda update-function-configuration \
  --function-name scheduling-agent-notes-actions \
  --environment Variables="{USE_MOCK_API=true,ENVIRONMENT=dev,DYNAMODB_TABLE=scheduling-agent-notes-dev}" \
  --region us-east-1
```

### Grant DynamoDB Permissions

Add this policy to Lambda execution role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:Query",
        "dynamodb:GetItem"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:618048437522:table/scheduling-agent-notes-dev"
    }
  ]
}
```

### Connect to Bedrock Agent

```bash
# Grant Bedrock permission to invoke Lambda
aws lambda add-permission \
  --function-name scheduling-agent-notes-actions \
  --statement-id bedrock-agent-notes \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn "arn:aws:bedrock:us-east-1:618048437522:agent/IX24FSMTQH" \
  --region us-east-1
```

Then update the agent's action group to use this Lambda ARN.

## 🔄 Switching from Mock to Real API

When you're ready to use real PF360 APIs:

### Step 1: Verify API Endpoints

```bash
# Test add note API
curl -X POST \
  "https://api.projectsforce.com/project-notes/add/09PF05VD" \
  -H "authorization: Bearer YOUR_TOKEN" \
  -H "client_id: 09PF05VD" \
  -H "Content-Type: application/json" \
  -d '{"project_id":"12345","note":"Test note","author":"Agent"}'

# Test list notes API (may not exist)
curl -X GET \
  "https://api.projectsforce.com/project-notes/list/09PF05VD?project_id=12345" \
  -H "authorization: Bearer YOUR_TOKEN" \
  -H "client_id: 09PF05VD"
```

### Step 2: Update Environment Variable

```bash
# Update Lambda to use real APIs (with DynamoDB fallback)
aws lambda update-function-configuration \
  --function-name scheduling-agent-notes-actions \
  --environment Variables="{USE_MOCK_API=false,ENVIRONMENT=prod,CUSTOMER_SCHEDULER_API_URL=https://api.projectsforce.com,DYNAMODB_TABLE=scheduling-agent-notes-prod}" \
  --region us-east-1
```

## 📊 Monitoring

### CloudWatch Logs

```bash
# Tail logs
aws logs tail /aws/lambda/scheduling-agent-notes-actions --follow

# Search for DynamoDB fallback usage
aws logs filter-log-events \
  --log-group-name /aws/lambda/scheduling-agent-notes-actions \
  --filter-pattern "DynamoDB fallback"
```

### Check Mock vs Real Usage

Logs will show:
- `[MOCK]` - When using mock data
- `[REAL]` - When making actual API calls
- `DynamoDB fallback` - When using DynamoDB instead of API

## ⚠️ Known Issues

1. **List Notes API Unknown**
   - PF360 may not have a dedicated list notes endpoint
   - Lambda automatically falls back to DynamoDB
   - Consider this the primary storage method if API doesn't exist

2. **In-Memory Mock Storage**
   - Mock notes reset on Lambda restart
   - Only affects development/testing
   - Real mode uses persistent DynamoDB

3. **DynamoDB Table Required**
   - Must create DynamoDB table before deployment
   - Lambda needs IAM permissions for DynamoDB
   - Table schema must match expected format

## 🔐 Security

- Never log full authorization tokens
- Use Secrets Manager for sensitive credentials
- Validate all input parameters
- Set appropriate IAM role permissions for DynamoDB access

## 📚 Related Documentation

- [PF360 API Analysis](../../docs/PF360_API_ANALYSIS.md)
- [Bedrock Agent Configuration](../../infrastructure/terraform/bedrock_agents.tf)
- [OpenAPI Schema](../../infrastructure/openapi_schemas/notes_actions.json)
- [Lambda Mock Implementation](../../docs/LAMBDA_MOCK_IMPLEMENTATION.md)

---

**Lambda ARN:** Will be set after deployment
**DynamoDB Table:** scheduling-agent-notes-dev
**Region:** us-east-1
**Runtime:** Python 3.11
**Memory:** 256 MB
**Timeout:** 30 seconds
