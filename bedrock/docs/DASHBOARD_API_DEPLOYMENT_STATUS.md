# Dashboard API - AWS Deployment Status
**Date**: 2025-10-29  
**Status**: ✅ DEPLOYED - Ready for Testing

---

## What Was Deployed

### Lambda Function: `pf-information-actions`

**Configuration**:
- Runtime: Python 3.11
- Handler: handler.lambda_handler
- Timeout: 30 seconds
- Memory: 512 MB

**Environment Variables** (CONFIGURED):
```bash
USE_MOCK_API=false          # ✅ Real API enabled
ENVIRONMENT=dev              # ✅ Dev environment
BEARER_TOKEN=[CONFIGURED]    # ✅ Token from 2025-10-29
DEFAULT_CLIENT_ID=09PF05VD   # ✅ Client ID set
LOG_LEVEL=INFO               # ✅ Logging enabled
DYNAMODB_TABLE_PREFIX=pf     # ✅ Table prefix set
```

**Code Deployed**:
- Latest `lambda/information-actions/` code
- Updated `config.py` with real API URLs
- Bearer token authentication configured
- All dependencies included (requests, boto3, etc.)

---

## Deployment Script

**File**: `deploy_dashboard_api_test.sh`

Deployment completed successfully in 5 steps:
1. ✅ Lambda package created
2. ✅ Lambda code updated
3. ✅ Lambda ready (waited for update)
4. ✅ Environment variables updated
5. ✅ Configuration ready

---

## Next Steps to Test "Show Me My Projects"

### Option 1: Test Lambda Directly

```bash
# Create test event
cat > test-event.json << 'EVENTEOF'
{
  "apiPath": "/get-projects",
  "httpMethod": "POST",
  "actionGroup": "information",
  "parameters": [
    {"name": "customer_id", "value": "1645869"},
    {"name": "client_id", "value": "09PF05VD"}
  ]
}
EVENTEOF

# Invoke Lambda
aws lambda invoke \
  --function-name pf-information-actions \
  --payload file://test-event.json \
  response.json

# View response
cat response.json | jq .
```

### Option 2: Test via Bedrock Agent (RECOMMENDED)

The `pf-information-agent` should already exist in AWS. To test:

1. **Get the Agent ID**:
```bash
aws bedrock-agent list-agents \
  --query 'agentSummaries[?contains(agentName, `information`)].{Name:agentName,ID:agentId,Status:agentStatus}' \
  --output table
```

2. **Get the Agent Alias ID**:
```bash
AGENT_ID="[from above]"
aws bedrock-agent list-agent-aliases \
  --agent-id $AGENT_ID \
  --output table
```

3. **Test with Bedrock Console**:
   - Go to AWS Bedrock Console
   - Navigate to Agents
   - Find "pf-information-agent"
   - Use the test interface
   - Ask: "Show me my projects for customer 1645869"

### Option 3: Test via API Gateway (if configured)

If you have API Gateway set up:
```bash
curl -X POST https://[YOUR-API-GATEWAY]/prod/projects \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "1645869", "client_id": "09PF05VD"}'
```

---

## Expected Response

When working correctly, the Lambda should return:

```json
{
  "response": {
    "httpStatusCode": 200,
    "responseBody": {
      "application/json": {
        "body": "{\"customer_id\":\"1645869\",\"total_projects\":25,\"projects\":[...],\"mock_mode\":false}"
      }
    }
  }
}
```

**Key Data Returned**:
- 25 projects for customer 1645869
- Real project data (not mock)
- Project details including:
  - Project ID, order number, category
  - Status and dates
  - Technician assignments
  - Store information
  - Customer address

---

## Troubleshooting

### Issue: Bearer Token Expired

**Symptoms**:
- 403 Forbidden errors
- "Failed to authenticate token" message

**Solution**:
1. Get fresh Bearer token from ProjectForce portal:
   - Visit: https://projectsforce-validation.cx-portal.dev.projectsforce.com
   - Login and capture new token from network tab

2. Update Lambda environment variable:
```bash
aws lambda update-function-configuration \
  --function-name pf-information-actions \
  --environment "Variables={
    USE_MOCK_API=false,
    ENVIRONMENT=dev,
    BEARER_TOKEN=[NEW_TOKEN_HERE],
    DEFAULT_CLIENT_ID=09PF05VD,
    LOG_LEVEL=INFO,
    DYNAMODB_TABLE_PREFIX=pf
  }"
```

### Issue: Lambda Timeout

**Symptoms**:
- Lambda times out after 30 seconds

**Solution**:
```bash
aws lambda update-function-configuration \
  --function-name pf-information-actions \
  --timeout 60
```

### Issue: Check Lambda Logs

```bash
# Tail live logs
aws logs tail /aws/lambda/pf-information-actions --follow

# View recent logs
aws logs tail /aws/lambda/pf-information-actions --since 1h
```

---

## API Endpoints Configured

The Lambda is configured to call these ProjectForce APIs:

### 1. Dashboard API - Get Customer Projects
- **URL**: `https://api-cx-portal.dev.projectsforce.com/dashboard/get/09PF05VD/1645869`
- **Method**: GET
- **Returns**: 25 projects with full details

### 2. Get Project Details
- **URL**: `https://api-cx-portal.dev.projectsforce.com/dashboard/get/09PF05VD/[CUSTOMER_ID]`
- **Method**: GET
- **Returns**: Filtered project information

### 3. Get Business Hours
- **URL**: `https://api-cx-portal.dev.projectsforce.com/business-hours/09PF05VD`
- **Method**: GET
- **Returns**: Business hours configuration

---

## Files Created/Modified

### Deployed to AWS:
- `lambda/information-actions/handler.py` (updated)
- `lambda/information-actions/config.py` (updated with real API)
- All dependencies packaged

### Documentation:
- `deploy_dashboard_api_test.sh` - Deployment script
- `docs/DASHBOARD_API_RECORDS.md` - Complete API documentation
- `lambda/API_TEST_RESULTS.md` - Test results
- `lambda/curl_commands.txt` - Working CURL commands

### Test Scripts:
- `lambda/test_api_integration.py` - Python test suite
- `lambda/show_request.py` - Request viewer

---

## Verification Checklist

- [x] Lambda function deployed
- [x] Environment variables configured
- [x] Bearer token added
- [x] Real API mode enabled (USE_MOCK_API=false)
- [ ] Lambda tested directly
- [ ] Bedrock Agent tested
- [ ] End-to-end "show me my projects" working

---

## Test Customer Data

**Customer ID**: 1645869  
**Client ID**: 09PF05VD  
**Known Projects**: 25 total

**Sample Project**:
- Project ID: 2109511
- Order Number: 658514656
- Category: MWORK - INT/EXT/PATIO DOOR
- Status: Scheduled
- Technician: Brian Garavuso

---

## Quick Test Commands

```bash
# 1. Check Lambda exists
aws lambda get-function --function-name pf-information-actions

# 2. Check environment variables
aws lambda get-function-configuration \
  --function-name pf-information-actions \
  --query 'Environment.Variables'

# 3. View recent logs
aws logs tail /aws/lambda/pf-information-actions --since 10m

# 4. Test Lambda
echo '{"apiPath":"/get-projects","httpMethod":"POST","actionGroup":"information","parameters":[{"name":"customer_id","value":"1645869"}]}' | \
  aws lambda invoke --function-name pf-information-actions --payload file:///dev/stdin /dev/stdout

# 5. Check Bedrock Agents
aws bedrock-agent list-agents
```

---

## Success Criteria

The deployment is successful when:

1. ✅ Lambda invokes without errors
2. ✅ Returns 200 status code
3. ✅ `mock_mode: false` in response
4. ✅ Returns 25 projects for customer 1645869
5. ✅ Project data includes real IDs, names, addresses
6. ✅ Response time < 5 seconds

---

## Git Commits

All changes committed and pushed:

- **Commit 4e64a18**: API integration with working Bearer token
- **Commit f4de210**: Dashboard API records documentation  
- **Branch**: 24Oct
- **Remotes**: origin (GitHub), bitbucket (Bitbucket)

---

## Contact & Support

**Token Refresh**: Get from https://projectsforce-validation.cx-portal.dev.projectsforce.com  
**AWS Region**: us-east-1 (verify with `aws configure get region`)  
**CloudWatch Logs**: `/aws/lambda/pf-information-actions`

---

**Status**: ✅ READY FOR TESTING

The Lambda is deployed and configured. Test it with the commands above!
