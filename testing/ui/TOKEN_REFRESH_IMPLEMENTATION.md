# Token Refresh Implementation - Fix for Token Expiration Issue

## Problem Statement

The ProjectForce API tokens expire very quickly (within minutes). Previously:
- UI stored token in localStorage on initial login
- When token expired, UI kept sending the expired token
- Lambda would get 403 Forbidden errors from ProjectForce API
- User would see "You have no projects matching your criteria" error
- Even though AWS Secrets Manager had fresh tokens, UI didn't use them

## Root Cause

**Two separate token sources:**
1. **UI Token**: Stored in localStorage, sent to Lambda via `pf_token` parameter
2. **Secrets Manager Token**: Stored in AWS Secrets Manager, used by Lambda as fallback

The UI was sending its own expired token, and Lambda was using that instead of fetching from Secrets Manager.

## Solution Implemented

### 1. Automatic Token Refresh on Page Load
**File**: `index.local.html` - Lines 452-518

When the page loads:
1. If credentials exist in localStorage, load them
2. **Immediately refresh the token** by calling the login endpoint
3. Save the fresh token to both:
   - localStorage (for UI use)
   - AWS Secrets Manager (for Lambda use)
4. Update user display to show "refreshed" status

**Code Flow**:
```javascript
async function autoLogin() {
    if (loadSavedCredentials()) {
        // Proactively refresh token on startup
        const refreshed = await refreshToken();
        if (refreshed) {
            console.log('✅ Token refreshed on startup');
        }
    } else {
        // First-time login
        await performLogin();
        await saveToSecretsManager();
    }
}
```

### 2. Automatic Token Refresh on 403 Errors
**File**: `index.local.html` - Lines 587-728

When sending chat messages:
1. Detect 403 errors or authentication failures
2. **Automatically refresh the token** without user intervention
3. **Retry the original request** with the fresh token
4. Save fresh token to both localStorage and Secrets Manager

**Code Flow**:
```javascript
async function sendMessage(isRetry = false) {
    try {
        const response = await fetch('/invoke-agent', { ... });
        const data = await response.json();

        // Detect token expiration
        if (response.status === 403 || data.error.includes('token')) {
            if (!isRetry) {
                // Refresh token
                const refreshed = await refreshToken();
                if (refreshed) {
                    // Retry with fresh token
                    return await sendMessage(true);
                }
            }
        }
    } catch (error) { ... }
}
```

### 3. Refresh Token Function
**File**: `index.local.html` - Lines 587-635

Centralized function to refresh tokens:
1. Call `/api/login` endpoint with credentials
2. Extract new `accesstoken`, `client_id`, and `customer_id`
3. Save to localStorage via `saveCredentials()`
4. Save to AWS Secrets Manager via `/api/save-token-to-secrets`
5. Return success/failure status

**Code**:
```javascript
async function refreshToken() {
    const response = await fetch('/api/login', {
        method: 'POST',
        body: JSON.stringify({
            email: 'jay@mailinator.com',
            password: 'U2FsdGVkX197AQMdkqthasfRGWLh41rhHVaw9Q9Q8cE=',
            device_type: 1
        })
    });

    const data = await response.json();
    if (data.accesstoken) {
        accessToken = data.accesstoken;
        saveCredentials();

        // Save to AWS Secrets Manager
        await fetch('/api/save-token-to-secrets', {
            method: 'POST',
            body: JSON.stringify({
                access_token: accessToken,
                client_id: clientId,
                customer_id: userId
            })
        });

        return true;
    }
    return false;
}
```

## Benefits

### User Experience
- ✅ **No manual token refresh required** - fully automatic
- ✅ **Seamless error recovery** - 403 errors handled transparently
- ✅ **No page reloads needed** - tokens refresh in the background
- ✅ **Fresh token on every page load** - proactive refresh strategy

### System Reliability
- ✅ **UI and Lambda stay in sync** - both use the same fresh token
- ✅ **Reduced 403 errors** - tokens refreshed before expiration
- ✅ **Better error handling** - automatic retry on authentication failures
- ✅ **Dual storage** - localStorage for UI, Secrets Manager for Lambda

## Testing

### Test Scenario 1: Page Load with Expired Token
**Steps**:
1. Load page with expired token in localStorage
2. UI automatically detects and refreshes token
3. User sees "User: 1646085 (refreshed)" in header

**Expected Result**: Fresh token loaded, no errors

### Test Scenario 2: Token Expires During Chat Session
**Steps**:
1. Open UI with fresh token
2. Wait for token to expire (a few minutes)
3. Send message "list my projects"
4. UI detects 403, refreshes token, retries request

**Expected Result**: Message succeeds after automatic refresh

### Test Scenario 3: Verify Secrets Manager Sync
**Steps**:
1. Refresh token in UI
2. Check AWS Secrets Manager for updated token
```bash
aws secretsmanager get-secret-value \
  --secret-id scheduling-agent/pf360/api-credentials \
  --query 'SecretString' --output text | jq '.pf_token' -r | wc -c
```

**Expected Result**: Token length ~748 characters, updated timestamp

## Architecture Diagram

```
┌─────────────────┐
│   User Opens    │
│   index.local   │
│     .html       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  autoLogin()    │
│  - Load cached  │
│  - Refresh token│
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│         refreshToken()              │
│  1. Call /api/login                 │
│  2. Get fresh accesstoken           │
│  3. Save to localStorage            │
│  4. Save to AWS Secrets Manager     │
└────────┬────────────────────────────┘
         │
         ├──────────────────┬──────────────────┐
         ▼                  ▼                  ▼
┌─────────────────┐  ┌──────────────┐  ┌─────────────────┐
│   localStorage  │  │ AWS Secrets  │  │ UI updates to   │
│   Updated       │  │ Manager      │  │ "refreshed"     │
│                 │  │ Updated      │  │                 │
└─────────────────┘  └──────────────┘  └─────────────────┘

User sends message "list my projects"
         │
         ▼
┌─────────────────┐
│ sendMessage()   │
│ with pf_token   │
└────────┬────────┘
         │
         ▼
  ┌─────────────┐
  │ Response OK?│
  └──────┬──────┘
         │
    No (403) │
         │
         ▼
┌─────────────────┐
│ refreshToken()  │
│ Retry request   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Success!        │
│ Projects shown  │
└─────────────────┘
```

## Files Modified

1. **`index.local.html`**
   - Added `refreshToken()` function (lines 587-635)
   - Modified `sendMessage()` to handle 403 errors (lines 637-728)
   - Modified `autoLogin()` to refresh on startup (lines 452-518)

2. **`pf_proxy.py`** (previously added)
   - Already has `/api/save-token-to-secrets` endpoint
   - Already has `/api/login` endpoint

## Monitoring

### Success Indicators
- Console logs show "✅ Token refreshed on startup"
- Console logs show "✅ Token refreshed and saved to Secrets Manager"
- User display shows "(refreshed)" after page load
- Chat messages succeed after 403 errors

### Failure Indicators
- Console errors: "❌ Token refresh failed"
- Console warnings: "⚠️ Failed to save token to Secrets Manager"
- User sees error: "Token refresh failed. Please reload the page."

## Future Improvements

1. **Proactive Refresh**: Refresh token every N minutes instead of waiting for 403
2. **Token Expiration Tracking**: Store token timestamp and refresh before expiration
3. **Retry Logic**: Add exponential backoff for failed refresh attempts
4. **User Notifications**: Show toast message when token is refreshed
5. **Error Logging**: Send token refresh failures to CloudWatch

## Summary

This implementation solves the token expiration issue by:
1. ✅ **Proactively refreshing tokens** on page load
2. ✅ **Automatically retrying** failed requests after token refresh
3. ✅ **Keeping UI and Lambda in sync** via dual storage
4. ✅ **Providing seamless UX** with no manual intervention required

The user no longer needs to manually refresh tokens or reload the page when tokens expire. The system handles it all automatically in the background.
