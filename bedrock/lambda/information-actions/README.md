# Information Actions Lambda Function

Handles 4 information-related actions for the Bedrock Scheduling Agent.

## 🎯 Actions Implemented

| Action | Description | Mock Support |
|--------|-------------|--------------|
| `get_project_details` | Get detailed project information | ✅ Yes |
| `get_appointment_status` | Check appointment status | ✅ Yes |
| `get_working_hours` | Get business hours | ✅ Yes |
| `get_weather` | Get weather forecast | ✅ Yes |

## 🔧 Configuration

### Environment Variables

```bash
# Core Configuration
USE_MOCK_API=true                    # true = mock responses, false = real API calls
ENVIRONMENT=dev                       # dev, qa, staging, prod
CUSTOMER_SCHEDULER_API_URL=https://api.projectsforce.com

# Weather API
WEATHER_API_URL=https://wttr.in      # External weather API

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

## 📥 Request Format

Bedrock Agent sends requests in this format:

```json
{
  "messageVersion": "1.0",
  "agent": {
    "name": "scheduling-agent-information",
    "id": "IX24FSMTQH",
    "alias": "TYJRF3CJ7F",
    "version": "4"
  },
  "sessionId": "session-123",
  "sessionAttributes": {},
  "promptSessionAttributes": {},
  "actionGroup": "information",
  "apiPath": "/get-project-details",
  "httpMethod": "POST",
  "parameters": [
    {"name": "project_id", "value": "12345"},
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
    "actionGroup": "information",
    "apiPath": "/get-project-details",
    "httpMethod": "POST",
    "httpStatusCode": 200,
    "responseBody": {
      "application/json": {
        "body": "{\"action\": \"get_project_details\", \"project_details\": {...}, \"mock_mode\": true}"
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

# Test get_project_details
event = {
    "apiPath": "/get-project-details",
    "parameters": [
        {"name": "project_id", "value": "12345"},
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
zip -r ../information-actions.zip .
cd ..
```

### Deploy to AWS

```bash
# Create/update Lambda function
aws lambda update-function-code \
  --function-name scheduling-agent-information-actions \
  --zip-file fileb://information-actions.zip \
  --region us-east-1

# Update environment variables
aws lambda update-function-configuration \
  --function-name scheduling-agent-information-actions \
  --environment Variables="{USE_MOCK_API=true,ENVIRONMENT=dev}" \
  --region us-east-1
```

### Connect to Bedrock Agent

```bash
# Grant Bedrock permission to invoke Lambda
aws lambda add-permission \
  --function-name scheduling-agent-information-actions \
  --statement-id bedrock-agent-information \
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
  --function-name scheduling-agent-information-actions \
  --environment Variables="{USE_MOCK_API=false,ENVIRONMENT=prod,CUSTOMER_SCHEDULER_API_URL=https://api.projectsforce.com}" \
  --region us-east-1
```

## 📊 Monitoring

### CloudWatch Logs

```bash
# Tail logs
aws logs tail /aws/lambda/scheduling-agent-information-actions --follow

# Search for mock mode logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/scheduling-agent-information-actions \
  --filter-pattern "[MOCK]"
```

### Check Mock vs Real Usage

Logs will show:
- `[MOCK]` - When using mock data
- `[REAL]` - When making actual API calls

## ⚠️ Known Issues

1. **Appointment Status API**
   - No dedicated API found in PF360
   - Currently derived from Dashboard API data
   - Consider creating dedicated endpoint

2. **Weather API Dependency**
   - Uses external wttr.in service
   - No authentication required
   - Consider fallback if service is unavailable

3. **Customer ID Requirement**
   - `get_appointment_status` in real mode requires `customer_id`
   - Needed to fetch project data from Dashboard API
   - Consider storing in session or requiring in all requests

## 🔐 Security

- Never log full authorization tokens
- Use Secrets Manager for sensitive credentials
- Validate all input parameters
- Set appropriate IAM role permissions

## 📚 Related Documentation

- [PF360 API Analysis](../../docs/PF360_API_ANALYSIS.md)
- [Bedrock Agent Configuration](../../infrastructure/terraform/bedrock_agents.tf)
- [OpenAPI Schema](../../infrastructure/openapi_schemas/information_actions.json)
- [Lambda Mock Implementation](../../docs/LAMBDA_MOCK_IMPLEMENTATION.md)

---

**Lambda ARN:** Will be set after deployment
**Region:** us-east-1
**Runtime:** Python 3.11
**Memory:** 256 MB
**Timeout:** 30 seconds
