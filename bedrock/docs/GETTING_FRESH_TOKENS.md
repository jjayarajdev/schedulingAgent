# How to Get Fresh ProjectForce API Tokens

## The Problem
- CURL scripts were failing because the API expects encrypted passwords
- The browser handles password encryption automatically via JavaScript
- Tokens from the browser work, but need to be refreshed periodically

## Solution: Get Token from Browser

### Step 1: Login to ProjectForce Portal
1. Open browser and go to: https://pf.dev.projectsforce.com/
2. Login with:
   - Email: `jay.jayakeerthy@syntegreti.com`
   - Password: `All0wj@y5677`

### Step 2: Extract Access Token from Browser
Once logged in, open Browser DevTools Console (F12) and run:

```javascript
// Get the access token
console.log(localStorage.getItem('access_token'));

// Copy it to clipboard (if browser supports it)
navigator.clipboard.writeText(localStorage.getItem('access_token'));
```

### Step 3: Test the Token
Save the token and test it:

```bash
# Save token to variable
TOKEN="<paste_token_here>"

# Test it
curl -X GET "https://api-cx-portal.dev.projectsforce.com/dashboard/get/09PF05VD/1645869" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | python3 -m json.tool
```

### Step 4: Update Lambda Function
Once you have a working token:

```bash
aws lambda update-function-configuration \
  --function-name pf-information-actions \
  --environment "Variables={
    USE_MOCK_API=false,
    ENVIRONMENT=dev,
    BEARER_TOKEN=<your_token_here>,
    DEFAULT_CLIENT_ID=09PF05VD,
    LOG_LEVEL=INFO,
    DYNAMODB_TABLE_PREFIX=pf
  }"
```

## Token Expiration
- Tokens expire after ~12-15 hours based on the `exp` field in localStorage
- When expired, simply login again and get a fresh token
- The `exp` value in localStorage is a Unix timestamp

To check if token is still valid:

```javascript
// In browser console
const exp = parseInt(localStorage.getItem('exp'));
const now = Math.floor(Date.now() / 1000);
const hoursLeft = (exp - now) / 3600;
console.log(`Token expires in ${hoursLeft.toFixed(1)} hours`);
```

## Alternative: Automated Token Refresh (Future Enhancement)
To automate this, we would need to:
1. Understand the OAuth2 refresh token flow
2. OR implement the browser's password encryption in our scripts
3. OR use Selenium/Puppeteer to automate browser login

For now, manual token extraction from browser is the quickest solution.

## Quick Reference

**Portal URL:** https://pf.dev.projectsforce.com/
**API URL:** https://api-cx-portal.dev.projectsforce.com
**Client ID:** 09PF05VD
**Test Customer ID:** 1645869

**Get Token from Browser:**
```javascript
localStorage.getItem('access_token')
```

**Test Token:**
```bash
curl -X GET "https://api-cx-portal.dev.projectsforce.com/dashboard/get/09PF05VD/1645869" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json"
```
