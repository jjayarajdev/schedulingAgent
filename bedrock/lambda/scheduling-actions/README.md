# Scheduling Actions Lambda Function

Handles 6 scheduling-related actions for the Bedrock Scheduling Agent.

## 🎯 Actions Implemented

| Action | Description | Mock Support |
|--------|-------------|--------------|
| `list_projects` | List all projects for customer | ✅ Yes |
| `get_available_dates` | Get available dates for scheduling | ✅ Yes |
| `get_time_slots` | Get time slots for a specific date | ✅ Yes |
| `confirm_appointment` | Confirm/schedule an appointment | ✅ Yes |
| `reschedule_appointment` | Reschedule existing appointment | ✅ Yes |
| `cancel_appointment` | Cancel an appointment | ✅ Yes |

## 🔧 Configuration

### Environment Variables

```bash
# Core Configuration
USE_MOCK_API=true                    # true = mock responses, false = real API calls
ENVIRONMENT=dev                       # dev, qa, staging, prod
CUSTOMER_SCHEDULER_API_URL=https://api.projectsforce.com

# Feature Flags (gradual rollout)
ENABLE_REAL_CONFIRM=false            # Enable real API for confirm (even if USE_MOCK_API=false)
ENABLE_REAL_CANCEL=false             # Enable real API for cancel (even if USE_MOCK_API=false)

# Session Management
DYNAMODB_TABLE=scheduling-agent-sessions-dev

# Logging
LOG_LEVEL=INFO
```

### Mock Mode vs Real Mode

**Mock Mode** (`USE_MOCK_API=true`):
- Returns realistic mock responses
- No external API calls
- Fast and consistent for development
- All responses include `"mock_mode": true`

**Real Mode** (`USE_MOCK_API=false`):
- Makes actual PF360 API calls
- Requires valid authorization token
- Returns live data
- All responses include `"mock_mode": false`

### Feature Flags

Additional safety flags for production rollout:
- `ENABLE_REAL_CONFIRM`: Even if `USE_MOCK_API=false`, you can keep confirm in mock mode
- `ENABLE_REAL_CANCEL`: Even if `USE_MOCK_API=false`, you can keep cancel in mock mode

**Use Case:** Gradually enable write operations while keeping reads real.

## 📥 Request Format

Bedrock Agent sends requests in this format:

```json
{
  "messageVersion": "1.0",
  "agent": {
    "name": "scheduling-agent-scheduling",
    "id": "IX24FSMTQH",
    "alias": "TYJRF3CJ7F",
    "version": "4"
  },
  "sessionId": "session-123",
  "sessionAttributes": {},
  "promptSessionAttributes": {},
  "actionGroup": "scheduling",
  "apiPath": "/list-projects",
  "httpMethod": "POST",
  "parameters": [
    {"name": "customer_id", "value": "1645975"},
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
    "actionGroup": "scheduling",
    "apiPath": "/list-projects",
    "httpMethod": "POST",
    "httpStatusCode": 200,
    "responseBody": {
      "application/json": {
        "body": "{\"action\": \"list_projects\", \"projects\": [...], \"mock_mode\": true}"
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

# Test list_projects
event = {
    "apiPath": "/list-projects",
    "parameters": [
        {"name": "customer_id", "value": "1645975"},
        {"name": "client_id", "value": "09PF05VD"}
    ]
}

response = lambda_handler(event, None)
print(json.dumps(response, indent=2))
```

## 📦 Deployment

### Package Lambda

```bash
# Install dependencies
pip install -r requirements.txt -t package/

# Copy handler files
cp handler.py config.py mock_data.py package/

# Create deployment package
cd package
zip -r ../scheduling-actions.zip .
cd ..
```

### Deploy to AWS

```bash
# Create/update Lambda function
aws lambda update-function-code \
  --function-name scheduling-agent-scheduling-actions \
  --zip-file fileb://scheduling-actions.zip \
  --region us-east-1

# Update environment variables
aws lambda update-function-configuration \
  --function-name scheduling-agent-scheduling-actions \
  --environment Variables="{USE_MOCK_API=true,ENVIRONMENT=dev}" \
  --region us-east-1
```

### Connect to Bedrock Agent

```bash
# Grant Bedrock permission to invoke Lambda
aws lambda add-permission \
  --function-name scheduling-agent-scheduling-actions \
  --statement-id bedrock-agent-scheduling \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn "arn:aws:bedrock:us-east-1:618048437522:agent/IX24FSMTQH" \
  --region us-east-1
```

Then update the agent's action group to use this Lambda ARN.

## 🔄 Switching from Mock to Real API

When you're ready to use real PF360 APIs:

### Step 1: Verify Credentials

```bash
# Test real API access with curl
curl -X GET \
  "https://api.projectsforce.com/dashboard/get/09PF05VD/1645975" \
  -H "authorization: Bearer YOUR_TOKEN" \
  -H "client_id: 09PF05VD"
```

### Step 2: Update Environment Variable

```bash
# Update Lambda to use real APIs
aws lambda update-function-configuration \
  --function-name scheduling-agent-scheduling-actions \
  --environment Variables="{USE_MOCK_API=false,ENVIRONMENT=prod,CUSTOMER_SCHEDULER_API_URL=https://api.projectsforce.com}" \
  --region us-east-1
```

### Step 3: Gradual Rollout

```bash
# First, enable reads only
aws lambda update-function-configuration \
  --function-name scheduling-agent-scheduling-actions \
  --environment Variables="{USE_MOCK_API=false,ENABLE_REAL_CONFIRM=false,ENABLE_REAL_CANCEL=false}" \
  --region us-east-1

# After testing, enable writes
aws lambda update-function-configuration \
  --function-name scheduling-agent-scheduling-actions \
  --environment Variables="{USE_MOCK_API=false,ENABLE_REAL_CONFIRM=true,ENABLE_REAL_CANCEL=true}" \
  --region us-east-1
```

## 📊 Monitoring

### CloudWatch Logs

```bash
# Tail logs
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions --follow

# Search for mock mode logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/scheduling-agent-scheduling-actions \
  --filter-pattern "[MOCK]"
```

### Check Mock vs Real Usage

Logs will show:
- `[MOCK]` - When using mock data
- `[REAL]` - When making actual API calls

## ⚠️ Known Issues

1. **request_id Dependency**
   - `get_time_slots` requires `request_id` from `get_available_dates`
   - Agent must maintain session context

2. **Reschedule Cancel Failure**
   - Reschedule cancels first, then confirms
   - If no existing appointment, cancel fails but confirm proceeds

## 🔐 Security

- Never log full authorization tokens
- Use Secrets Manager for sensitive credentials
- Validate all input parameters
- Set appropriate IAM role permissions

## 📚 Related Documentation

- [PF360 API Analysis](../../docs/PF360_API_ANALYSIS.md)
- [Bedrock Agent Configuration](../../infrastructure/terraform/bedrock_agents.tf)
- [OpenAPI Schema](../../infrastructure/openapi_schemas/scheduling_actions.json)

---

**Lambda ARN:** Will be set after deployment
**Region:** us-east-1
**Runtime:** Python 3.11
**Memory:** 256 MB
**Timeout:** 30 seconds
