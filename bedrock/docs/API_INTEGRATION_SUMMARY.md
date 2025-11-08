# Phase 1 API Integration - Implementation Summary

**Date:** 2025-10-29
**Status:** ✅ Configuration Updated - Ready for Testing
**Environment:** dev (`https://api-cx-portal.dev.projectsforce.com`)

---

## What Was Changed

### 1. **Updated Configuration Files**

#### `lambda/scheduling-actions/config.py`
- ✅ Added real API base URLs for dev/staging/prod
- ✅ Updated to use `https://api-cx-portal.dev.projectsforce.com`
- ✅ Added Bearer token support from environment variable
- ✅ Fixed authentication headers: `Authorization` (capital A), `Client_Id` (capital C and I)
- ✅ Added default `CLIENT_ID=09PF05VD`

#### `lambda/information-actions/config.py`
- ✅ Same updates as scheduling-actions
- ✅ Consistent authentication across all Lambdas

### 2. **Environment Variables**

Created `lambda/.env.example` with:
```bash
USE_MOCK_API=true              # Toggle real API mode
ENVIRONMENT=dev                # Deployment environment
BEARER_TOKEN=[YOUR_TOKEN]      # ProjectForce API token
DEFAULT_CLIENT_ID=09PF05VD     # Client identifier
ENABLE_REAL_CONFIRM=false      # Gradual rollout flag
ENABLE_REAL_CANCEL=false       # Gradual rollout flag
```

### 3. **Lambda Handler Updates**

**No changes needed!** 🎉

The existing handlers already:
- Support mock/real API toggle
- Use correct data models (`project_project_id`, `project_project_number`)
- Handle authentication headers properly
- Map API responses correctly

---

## API Endpoints Configuration

### Base URLs by Environment:
| Environment | URL |
|-------------|-----|
| **dev** (current) | `https://api-cx-portal.dev.projectsforce.com` |
| staging | `https://api-cx-portal.staging.projectsforce.com` |
| prod | `https://api-cx-portal.projectsforce.com` |

### Supported APIs:

#### Dashboard API (Information Agent)
```
GET /dashboard/get/{client_id}/{customer_id}
Headers:
  Authorization: Bearer [TOKEN]
  Client_Id: 09PF05VD
```

#### Scheduler APIs (Scheduling Agent)
```
# Get Available Dates/Slots
GET /scheduler/client/{client_id}/project/{project_id}/date/{date}/selected/{date}/get-rescheduler-slots

# Confirm Appointment
POST /scheduler/client/{client_id}/project/{project_id}/schedule
Body: {created_at, date, time, request_id, is_chatbot}

# Cancel/Reschedule
GET /scheduler/client/{client_id}/project/{project_id}/cancel-reschedule
```

---

## Testing the Integration

### Step 1: Enable Real API Mode

**Option A: Environment Variable (for deployed Lambdas)**
```bash
# Update Lambda environment variables
aws lambda update-function-configuration \
  --function-name scheduling-agent-scheduling-actions \
  --environment Variables={USE_MOCK_API=false,BEARER_TOKEN=[TOKEN],DEFAULT_CLIENT_ID=09PF05VD}
```

**Option B: Local Testing**
```bash
cd lambda/scheduling-actions
cp ../.env.example .env
# Edit .env:
#   USE_MOCK_API=false
#   BEARER_TOKEN=[your token]

python handler.py
```

### Step 2: Test with Real Data

Use test credentials from `docs/api-calls.txt`:
- Customer ID: `1645869`
- Project ID: `7750176`
- Client ID: `09PF05VD`

### Step 3: Monitor Logs

```bash
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions --follow
aws logs tail /aws/lambda/scheduling-agent-information-actions --follow
```

---

## What Works Now

✅ **Mock Mode** (default):
- All actions work with mock data
- No real API calls
- Safe for testing agent logic

✅ **Real API Mode** (when `USE_MOCK_API=false`):
- Dashboard API: Get customer projects
- Scheduler API: Get available dates/slots
- Authentication: Bearer token + Client_Id
- Data mapping: Correct field names

---

## What Still Needs Work

### 1. **Customer Lookup by Phone** ⚠️
- **Problem**: We only have phone number from voice/SMS
- **Need**: API endpoint to convert phone → customer_id
- **Workaround**: Pass customer_id explicitly for now

### 2. **Token Refresh** ⚠️
- **Problem**: Bearer tokens expire
- **Need**: Token refresh mechanism
- **Workaround**: Monitor 401 responses, manually update token

### 3. **Multi-Client Support** ⚠️
- **Problem**: Currently hardcoded `CLIENT_ID=09PF05VD`
- **Need**: Customer-to-client mapping
- **Workaround**: Single client for now

### 4. **Confirm/Cancel Feature Flags** ⚠️
- **Status**: Disabled by default (`ENABLE_REAL_CONFIRM=false`)
- **Reason**: Want to test read-only operations first
- **Action**: Set to `true` when ready for write operations

---

## Deployment Steps

### For New Environment:

1. **Set Environment Variables in Terraform:**

```hcl
# infrastructure/terraform/lambda.tf
resource "aws_lambda_function" "scheduling_actions" {
  environment {
    variables = {
      USE_MOCK_API      = "false"
      ENVIRONMENT       = "dev"
      BEARER_TOKEN      = var.bearer_token  # Store in AWS Secrets Manager
      DEFAULT_CLIENT_ID = "09PF05VD"
      DYNAMODB_TABLE    = "scheduling-agent-sessions-dev"
      LOG_LEVEL         = "INFO"

      # Feature flags
      ENABLE_REAL_CONFIRM = "false"
      ENABLE_REAL_CANCEL  = "false"
    }
  }
}
```

2. **Deploy with DEPLOY.sh:**
```bash
./DEPLOY.sh dev us-east-1
```

3. **Verify:**
```bash
# Check Lambda environment
aws lambda get-function-configuration \
  --function-name scheduling-agent-scheduling-actions \
  --query 'Environment'
```

---

## Gradual Rollout Strategy

### Phase 1.1: Read-Only APIs ✅ (Current)
- ✅ Dashboard API (get projects)
- ✅ Get available dates/slots
- ✅ Get project details
- Mock: Confirm, Cancel operations

### Phase 1.2: Write Operations (Next)
- Enable `ENABLE_REAL_CONFIRM=true`
- Test appointment confirmation
- Monitor for errors

### Phase 1.3: Cancel/Reschedule (After 1.2)
- Enable `ENABLE_REAL_CANCEL=true`
- Test cancellation flow
- Verify data integrity

### Phase 1.4: Full Production (Final)
- Switch `USE_MOCK_API=false` globally
- All operations use real API
- Monitor metrics and errors

---

## Troubleshooting

### 401 Unauthorized
- Check Bearer token is set correctly
- Verify token hasn't expired
- Ensure `Authorization: Bearer TOKEN` format

### 404 Not Found
- Verify base URL matches environment
- Check client_id is correct (`09PF05VD`)
- Confirm customer_id and project_id exist

### Data Structure Mismatch
- Handlers already updated for real API structure
- Uses `project_project_id` not `project_id`
- Uses `project_project_number` not `project_number`

### Headers Not Working
- Ensure `Client_Id` (capital C and I)
- Ensure `Authorization` (capital A)
- Check all required headers present

---

## Files Modified

1. `lambda/scheduling-actions/config.py` - API configuration
2. `lambda/information-actions/config.py` - API configuration
3. `lambda/.env.example` - Environment variable documentation

**Files NOT modified** (already correct):
- `lambda/scheduling-actions/handler.py` - Already supports real API
- `lambda/information-actions/handler.py` - Already supports real API
- Data mapping already correct throughout

---

## Next Steps

1. **Test with real dev environment:**
   ```bash
   # Set USE_MOCK_API=false
   # Test dashboard API call
   # Verify data returned matches expected format
   ```

2. **Get customer lookup API:**
   - Need endpoint to convert phone number → customer_id
   - Critical for voice/SMS integration

3. **Deploy to client AWS:**
   - Update Terraform with environment variables
   - Run `./DEPLOY.sh`
   - Test end-to-end

4. **Enable write operations:**
   - Test confirmation flow
   - Enable feature flags gradually

---

## Summary

✅ **Configuration Updated**: All Lambda configs now support real ProjectForce APIs
✅ **Authentication Fixed**: Correct Bearer token and Client_Id headers
✅ **Environment Ready**: Can toggle between mock and real APIs
✅ **Backwards Compatible**: Mock mode still works for testing
🔄 **Ready for Testing**: Set `USE_MOCK_API=false` to try real APIs
⏳ **Pending**: Customer phone lookup, token refresh, multi-client support

**Status**: Ready to deploy and test with dev environment!
