# ProjectForce API Authentication Guide

**Date**: 2025-10-30
**Status**: ✅ WORKING SOLUTION DOCUMENTED

---

## Authentication System Overview

The ProjectForce API uses a token-based authentication system with the following architecture:

### Endpoints

- **Authentication Server**: `https://auth.dev.projectsforce.com`
- **API Server**: `https://api-cx-portal.dev.projectsforce.com`
- **Web Portal**: `https://pf.dev.projectsforce.com`

### Authentication Flow

```
1. User logs in via Web Portal (SPA)
   ↓
2. Portal calls auth.dev.projectsforce.com/check.v1
   with encrypted password
   ↓
3. Auth server validates credentials
   ↓
4. Portal calls auth.dev.projectsforce.com/token
   to get access_token
   ↓
5. Access token used for API calls with
   "Authorization: Bearer <token>" header
```

---

## Key Findings

### 1. Password Encryption

The authentication system **requires encrypted passwords**. Plain text passwords are rejected.

**Example from browser:**
```json
{
  "username": "jay.jayakeerthy@syntegreti.com",
  "password": "gwKa8vUF8gSW8lC28lAJmg==",
  "reCaptcha": "",
  "method": "POST"
}
```

**Note**: The password `"All0wj@y5677"` is encrypted to `"gwKa8vUF8gSW8lC28lAJmg=="` by the frontend before sending.

### 2. Token Structure

Successful authentication returns:

```json
{
  "access_token": "TaDWx6r5O0WE2tb5/Lb77XuI29UR7j2NlMHbUdXd+YrY...",
  "token_type": "Bearer",
  "expires_in": 43599,
  "refresh_token": "jCkEAoO8sB+Z8Lc3jqM9WmteOZoyShu+asSiBGHXMVXhzL...",
  "user_id": "6f72bffa-c323-4058-a01c-9d495d696364",
  "client_id": "11MT97PY",
  "exp": 1761870323
}
```

**Token Lifetime**: ~12 hours (43,599 seconds)

### 3. Client ID vs Customer ID

- **Client ID**: Identifies the organization (e.g., `11MT97PY`, `09PF05VD`)
- **Customer ID**: Identifies specific customer within organization (e.g., `1645869`)

Both are required for API calls like:
```
GET /dashboard/get/{CLIENT_ID}/{CUSTOMER_ID}
```

---

## How to Get a Fresh Token

Since programmatic authentication requires password encryption (method unknown), **tokens must be obtained manually via browser**.

### Method: Browser Developer Tools

1. **Open the Web Portal**
   ```
   https://pf.dev.projectsforce.com/
   ```

2. **Open Browser DevTools**
   - Press `F12` or right-click → Inspect
   - Go to **Network** tab
   - Check "Preserve log"

3. **Log In**
   - Email: `jay.jayakeerthy@syntegreti.com`
   - Password: `All0wj@y5677`

4. **Find the Token Request**
   - Look for a request to `token` (filter by "token")
   - URL will be: `https://auth.dev.projectsforce.com/token`
   - Click on the request

5. **Extract Token Data**
   - Go to **Response** tab
   - Copy the entire JSON response
   - You need:
     - `access_token` - The Bearer token
     - `client_id` - Your client identifier
     - `expires_in` - Token validity period

6. **Save the Token**
   ```bash
   echo '{"access_token":"...","client_id":"..."}' > token_data.json
   ```

---

## Testing the API with Token

### Script: `test_api_with_token.sh`

```bash
#!/bin/bash

# Usage: ./test_api_with_token.sh <ACCESS_TOKEN> <CLIENT_ID> [CUSTOMER_ID]

ACCESS_TOKEN="$1"
CLIENT_ID="${2:-11MT97PY}"
CUSTOMER_ID="${3:-1645869}"

if [ -z "$ACCESS_TOKEN" ]; then
  echo "Usage: $0 <ACCESS_TOKEN> <CLIENT_ID> [CUSTOMER_ID]"
  exit 1
fi

echo "Testing ProjectForce API..."
echo "Client ID: $CLIENT_ID"
echo "Customer ID: $CUSTOMER_ID"
echo ""

# Test Dashboard API
curl -s -X GET \
  "https://api-cx-portal.dev.projectsforce.com/dashboard/get/$CLIENT_ID/$CUSTOMER_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  | python3 -m json.tool
```

### Quick Test Command

```bash
# Replace YOUR_TOKEN and YOUR_CLIENT_ID
curl -s -X GET \
  "https://api-cx-portal.dev.projectsforce.com/dashboard/get/11MT97PY/1645869" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  | python3 -m json.tool | head -50
```

---

## Updating Lambda Function

### Option 1: Using AWS CLI

```bash
aws lambda update-function-configuration \
  --function-name pf-information-actions \
  --environment "Variables={
    USE_MOCK_API=false,
    ENVIRONMENT=dev,
    BEARER_TOKEN=<YOUR_ACCESS_TOKEN>,
    DEFAULT_CLIENT_ID=<YOUR_CLIENT_ID>,
    LOG_LEVEL=INFO,
    DYNAMODB_TABLE_PREFIX=pf
  }"
```

### Option 2: Using Helper Script

Create `update_lambda_token.sh`:

```bash
#!/bin/bash
# Update Lambda with new token

if [ -z "$1" ]; then
  echo "Usage: $0 <ACCESS_TOKEN> [CLIENT_ID]"
  echo ""
  echo "Example:"
  echo "  $0 'TaDWx6r5O0WE2tb5...' 11MT97PY"
  exit 1
fi

ACCESS_TOKEN="$1"
CLIENT_ID="${2:-11MT97PY}"

echo "Updating Lambda function: pf-information-actions"
echo "Client ID: $CLIENT_ID"
echo "Token: ${ACCESS_TOKEN:0:40}..."
echo ""

aws lambda update-function-configuration \
  --function-name pf-information-actions \
  --environment "Variables={
    USE_MOCK_API=false,
    ENVIRONMENT=dev,
    BEARER_TOKEN=$ACCESS_TOKEN,
    DEFAULT_CLIENT_ID=$CLIENT_ID,
    LOG_LEVEL=INFO,
    DYNAMODB_TABLE_PREFIX=pf
  }"

echo ""
echo "✓ Lambda function updated!"
echo "✓ Token expires in: ~12 hours"
```

**Usage:**
```bash
chmod +x update_lambda_token.sh
./update_lambda_token.sh "YOUR_ACCESS_TOKEN_HERE" "11MT97PY"
```

---

## Available API Endpoints

Based on testing, these endpoints are confirmed to work:

### 1. Dashboard - Get Customer Projects

**Endpoint:** `GET /dashboard/get/{CLIENT_ID}/{CUSTOMER_ID}`

**Example:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  https://api-cx-portal.dev.projectsforce.com/dashboard/get/11MT97PY/1645869
```

**Response:**
```json
{
  "data": [
    {
      "id": 2109511,
      "order_number": "658514656",
      "category": "MWORK - INT/EXT/PATIO DOOR",
      "status": "Scheduled",
      "technician": "Brian Garavuso",
      ...
    }
  ]
}
```

### 2. Business Hours ❌ (Endpoint Not Found)

**Endpoint:** `GET /business-hours/{CLIENT_ID}`

**Status:** Returns 404 - endpoint may have changed or been removed

---

## Token Expiration Handling

### Symptoms of Expired Token

1. **HTTP 403**: `{"message":"Failed to authenticate token"}`
2. **HTTP 406**: `{"message":{"title":"Session Expired","message":"Your session has expired. Please log in again."}}`

### When to Refresh Token

- Tokens last **~12 hours** (43,599 seconds)
- Set up a reminder to refresh token every **10-11 hours**
- Consider implementing automatic refresh in production

### Refresh Process

**Option A:** Get new token manually (see "How to Get a Fresh Token" above)

**Option B:** Use refresh_token (if API supports it):
```bash
curl -X POST https://auth.dev.projectsforce.com/token \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"YOUR_REFRESH_TOKEN"}'
```

---

## Troubleshooting

### Issue: "Invalid credentials" (HTTP 401)

**Cause:** Plain text password sent to auth endpoint

**Solution:** Password must be encrypted by frontend. Use browser method to obtain token.

### Issue: "Failed to authenticate token" (HTTP 403)

**Cause:** Token expired or invalid

**Solution:** Obtain fresh token from browser

### Issue: "Session Expired" (HTTP 406)

**Cause:** Token session has expired

**Solution:** Get new token and update Lambda

### Issue: Wrong Client ID

**Symptom:** HTTP 406 or empty results

**Solution:** Use correct Client ID from token response (`11MT97PY` for jay.jayakeerthy)

### Issue: Lambda Times Out

**Solution:**
```bash
aws lambda update-function-configuration \
  --function-name pf-information-actions \
  --timeout 60
```

---

## Security Considerations

### 1. Token Storage

- **Never commit tokens to Git**
- Store in environment variables or AWS Secrets Manager
- Rotate tokens regularly

### 2. Access Control

- Tokens provide full access to user's data
- Treat tokens like passwords
- Use AWS IAM roles to restrict Lambda access

### 3. Logging

- Do not log full tokens
- Log only first 20 characters: `${TOKEN:0:20}...`
- Mask tokens in CloudWatch Logs

---

## Scripts Created

All scripts are in the `/bedrock` directory:

1. **`test_api_live.sh`** - Original test script
2. **`find_auth_endpoint.sh`** - Endpoint discovery
3. **`test_with_existing_token.sh`** - Test with Lambda token
4. **`test_auth_complete.sh`** - Complete auth flow
5. **`test_with_provided_token.sh`** - Test with browser token
6. **`get_fresh_token.py`** - Python auth script (shows manual steps)
7. **`update_lambda_token.sh`** - Helper to update Lambda (auto-generated)

---

## Quick Reference

### Get Token (Manual - Browser)
```
1. Go to: https://pf.dev.projectsforce.com/
2. Login with credentials
3. F12 → Network → Find 'token' request
4. Copy access_token from Response
```

### Test Token
```bash
curl -H "Authorization: Bearer $TOKEN" \
  https://api-cx-portal.dev.projectsforce.com/dashboard/get/11MT97PY/1645869 \
  | python3 -m json.tool | head -50
```

### Update Lambda
```bash
aws lambda update-function-configuration \
  --function-name pf-information-actions \
  --environment Variables="{BEARER_TOKEN=$TOKEN,DEFAULT_CLIENT_ID=11MT97PY}"
```

### Check Lambda Logs
```bash
aws logs tail /aws/lambda/pf-information-actions --follow
```

---

## Next Steps

1. **Get Fresh Token**
   - Log into https://pf.dev.projectsforce.com/
   - Extract token from browser DevTools

2. **Test Token**
   - Run: `./test_api_live.sh` (after adding token)
   - Verify API responses

3. **Update Lambda**
   - Run: `./update_lambda_token.sh <TOKEN> 11MT97PY`
   - Verify Lambda configuration

4. **Test End-to-End**
   - Invoke Lambda directly
   - Test via Bedrock Agent
   - Verify "show me my projects" query works

5. **Setup Token Refresh Reminder**
   - Calendar reminder every 10 hours
   - Or implement automated refresh

---

## Contact Information

**Test Account:**
- Email: jay.jayakeerthy@syntegreti.com
- Client ID: 11MT97PY
- Test Customer ID: 1645869

**AWS Resources:**
- Lambda: pf-information-actions
- Region: us-east-1
- CloudWatch: /aws/lambda/pf-information-actions

---

**Last Updated**: 2025-10-30
**Status**: ✅ Solution documented and ready for use
