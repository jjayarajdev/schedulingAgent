# 🔐 ProjectForce Token Manager

A beautiful web-based UI tool to manage Bearer tokens and update AWS Lambda functions.

## Features

- 🔑 **Authenticate** - Log in with your ProjectForce credentials to retrieve Bearer tokens
- 📋 **Manual Token Entry** - Paste tokens retrieved manually from the browser
- ☁️ **AWS CLI Commands** - Auto-generate AWS CLI commands to update Lambda functions
- 📊 **Token Information** - View detailed token and user information
- 📋 **Copy to Clipboard** - One-click copy for tokens and commands

## Quick Start

### Option 1: Use the Web UI

1. **Launch the Token Manager:**
   ```bash
   cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
   ./launch_token_manager.sh
   ```

2. **Open in Browser:**
   - Navigate to: `http://localhost:8080/token_manager.html`

3. **Authenticate:**
   - Enter your credentials:
     - Email: `jay@mailinator.com`
     - Password: `Jay@123456`
     - Identifier: `projectsforce-validation`
   - Click "🚀 Authenticate & Update Lambdas"

4. **Copy AWS Commands:**
   - Switch to the "AWS Commands" tab
   - Copy and run the commands in your terminal

### Option 2: Command Line Script

If you prefer command-line tools, use the existing script:

```bash
./update_lambdas_with_token.sh
```

## UI Tabs

### 🔑 Authenticate Tab
- Enter ProjectForce credentials
- Automatically retrieves Bearer token
- Displays user and token information
- Shows token validity and length

### 📋 Manual Token Tab
- Paste tokens retrieved from browser
- Useful if authentication fails
- Generates AWS CLI commands

**How to get token manually:**
1. Open: `https://projectsforce-validation.cx-portal.dev.projectsforce.com`
2. Log in with your credentials
3. Open DevTools (F12) → Application → Local Storage
4. Copy the token value

### ☁️ AWS Commands Tab
- Pre-generated AWS CLI commands
- Ready to copy and paste
- Updates all Lambda functions:
  - `pf-information-actions`
  - `pf-scheduling-actions`
  - `pf-notes-actions`

## API Endpoints

### Authentication Endpoint
```
POST https://api-cx-portal.dev.projectsforce.com/authentication/login?identifier=projectsforce-validation
```

**Request Body:**
```json
{
  "email": "jay@mailinator.com",
  "password": "U2FsdGVkX18ZMNPJeL3WQFI5mPk1WSwc4rWWzQLo4CE=",
  "device_type": 1
}
```

**Response:**
```json
{
  "accesstoken": "<748-character-token>",
  "refrestoken": "<refresh-token>",
  "exp": 1762173485,
  "user": {
    "customer_id": 1646085,
    "client_id": "09PF05VD",
    "email": "jay@mailinator.com",
    ...
  }
}
```

## Lambda Configuration

All Lambda functions will be updated with:

```json
{
  "USE_MOCK_API": "false",
  "ENVIRONMENT": "dev",
  "BEARER_TOKEN": "<your-token>",
  "DEFAULT_CLIENT_ID": "09PF05VD",
  "LOG_LEVEL": "INFO"
}
```

## Environment-Specific URLs

The system uses environment-aware API URLs:

| Environment | API URL |
|------------|---------|
| **dev** | `https://api-cx-portal.dev.projectsforce.com` |
| **staging** | `https://api-cx-portal.staging.projectsforce.com` |
| **prod** | `https://api-cx-portal.projectsforce.com` |

## Token Security

⚠️ **Important Security Notes:**

1. **Never commit tokens** to version control
2. **Token expiry** - Tokens expire after a certain period (check `exp` field)
3. **Rotate tokens regularly** - Use this tool to update tokens when needed
4. **Encrypted passwords** - Passwords must be encrypted before sending to API

## Troubleshooting

### Authentication Fails

**Error:** "Invalid credentials"

**Solution:**
- Verify email and password are correct
- Check if account is active
- Try manual token retrieval from browser

### Lambda Update Fails

**Error:** "Access Denied" or "Function not found"

**Solution:**
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check Lambda function exists
aws lambda list-functions --query 'Functions[?contains(FunctionName, `pf-`)].FunctionName'

# Verify region
export AWS_REGION=us-east-1
```

### Token Expired

**Error:** API returns 401 Unauthorized

**Solution:**
- Re-authenticate using the Token Manager
- Update Lambda functions with fresh token

## Files

- `token_manager.html` - Web UI interface
- `launch_token_manager.sh` - Launch script for web server
- `update_lambdas_with_token.sh` - Command-line update script
- `/tmp/bearer_token.txt` - Saved token (temporary)
- `/tmp/cx_portal_token.json` - Full auth response (temporary)

## Additional Commands

### Verify Lambda Configuration

```bash
# Check information-actions
aws lambda get-function-configuration \
  --function-name pf-information-actions \
  --query 'Environment.Variables' \
  --output json

# Check scheduling-actions
aws lambda get-function-configuration \
  --function-name pf-scheduling-actions \
  --query 'Environment.Variables.BEARER_TOKEN' \
  --output text
```

### Test API with Token

```bash
TOKEN=$(cat /tmp/bearer_token.txt)
CLIENT_ID="09PF05VD"
CUSTOMER_ID="1646085"

curl -X GET \
  "https://api-cx-portal.dev.projectsforce.com/dashboard/get/${CLIENT_ID}/${CUSTOMER_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json"
```

## Support

For issues or questions:
1. Check CloudWatch Logs for Lambda function errors
2. Verify token is not expired
3. Ensure AWS credentials have Lambda update permissions
4. Check API endpoint is accessible

## Version History

- **v1.0** - Initial release with authentication and manual token entry
- **Current** - Added AWS CLI command generation and improved UI

---

**Last Updated:** 2025-11-03
**Maintained by:** Jay Jayakeerthy
