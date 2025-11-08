# DEPLOY.sh Credential Prompt Example

## Interactive Prompt Flow

When you run `./scripts/DEPLOY.sh`, you'll see:

```
==========================================
ProjectForce 4-Agent Deployment
==========================================

Region: us-east-1
Account: 618048437522
Environment: dev

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ProjectForce API Credentials
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The Lambda functions need API credentials to connect to ProjectForce.

Please provide your ProjectForce API credentials:

Client ID (e.g., 09PF05VD): _
```

You enter: `09PF05VD`

```
User ID (e.g., 1645869): _
```

You enter: `1645869`

```
Bearer Token (starts with 'eyJ...'):
> _
```

You paste your token: `eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiM...`

```
✓ Credentials captured

Optional: Refresh Token (press Enter to skip):
> _
```

You can press Enter to skip or paste your refresh token.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

==========================================
Step 0: Creating Secrets Manager Secret
==========================================

Checking secret: projectforce/api/credentials
  ✅ Using provided Bearer token
  ℹ️  Secret already exists
  → Updating secret with provided credentials...
  ✅ Secret updated with provided credentials

...deployment continues...
```

## Using Environment Variables Instead

If you prefer not to be prompted, set environment variables before running:

```bash
export PF_CLIENT_ID="09PF05VD"
export PF_USER_ID="1645869"
export PF_BEARER_TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
export PF_REFRESH_TOKEN="AWldtvQhQ+wt4HhRcU/2m..."  # optional

./scripts/DEPLOY.sh
```

The script will detect these and show:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ProjectForce API Credentials
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The Lambda functions need API credentials to connect to ProjectForce.

✓ Using credentials from environment variables

  Client ID: 09PF05VD
  User ID:   1645869
  Token:     eyJhbGciOiJSUzI1NiIsI...

Press Enter to continue or Ctrl+C to cancel and re-enter credentials... _
```

Press Enter to continue with the detected credentials.

## What Happens With Your Credentials

The script stores them in AWS Secrets Manager as:

```json
{
  "bearer_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "client_id": "09PF05VD",
  "user_id": "1645869",
  "refresh_token": "AWldtvQhQ+wt4HhRcU/2m...",
  "api_base_url": "https://api-cx-portal.dev.projectsforce.com"
}
```

Lambda functions will read these credentials from Secrets Manager at runtime.

## Getting Your Bearer Token

You can get a valid bearer token from:

1. **ProjectForce Login**: After logging in to https://cx-portal.dev.projectsforce.com
2. **Browser DevTools**:
   - Open DevTools (F12)
   - Go to Application → Local Storage or Session Storage
   - Look for `access_token` or `bearer_token`
3. **API Authentication Script**: Use the authentication scripts in `testing/` directory

## Token Expiration

Bearer tokens typically expire after a few hours. If your Lambda functions start getting 401/403 errors:

1. Get a fresh token
2. Re-run `./scripts/DEPLOY.sh` with the new token
3. The script will update the Secrets Manager secret automatically

## Security Notes

- Credentials are stored securely in AWS Secrets Manager
- Never commit bearer tokens to git
- The script masks part of the token when displaying (shows first 20 chars only)
- Refresh tokens (if provided) allow automatic token renewal

---

**Last Updated**: November 4, 2025
