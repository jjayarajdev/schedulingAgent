# Test Scripts - Token Management & API Testing

This folder contains utility scripts for managing API tokens and testing the ProjectForce API integration.

## 📋 Available Scripts

### 1. get_accessible_projects.sh ⭐
**Purpose:** Fetch all projects accessible with your credentials

**Usage:**
```bash
./get_accessible_projects.sh [CLIENT_ID] [USER_ID]

# With defaults
./get_accessible_projects.sh

# With custom credentials
./get_accessible_projects.sh 09PF05VD 1646085
```

**What it does:**
- Tests your bearer token against ProjectForce API
- Lists all accessible projects with IDs and names
- Identifies which project IDs you can use for testing
- Validates token expiration

**Output:**
```
Found 15 projects
Available Projects:
  7751741 - Project Alpha
  7751742 - Project Beta
  ...

Project IDs you can use:
7751741, 7751742, 7751743, ...
```

---

### 2. update_secrets_manager_token.sh ⭐
**Purpose:** Update the bearer token in AWS Secrets Manager

**Usage:**
```bash
./update_secrets_manager_token.sh
```

**What it does:**
1. Shows current token (masked)
2. Prompts for new bearer token
3. Updates AWS Secrets Manager (`projectforce/api/credentials`)
4. Tests the token immediately against ProjectForce API
5. Validates HTTP response (200, 403, 401)

**Interactive Flow:**
```
Enter new bearer token: [paste token]
Update Secrets Manager? (y/n) y
✅ Secret updated successfully!
🧪 Testing token...
✅ Token is valid! (HTTP 200)
```

**Important:**
- Lambda functions use this token
- Changes take effect on next Lambda invocation
- Always test the token after updating

---

### 3. update_lambda_env_token.sh
**Purpose:** Update bearer token in Lambda environment variables

**Usage:**
```bash
./update_lambda_env_token.sh
```

**What it does:**
- Updates `BEARER_TOKEN` environment variable
- Affects both `pf-scheduling-actions` and `pf-information-actions`
- Preserves all other environment variables

**When to use:**
- When you want to use environment variables instead of Secrets Manager
- For temporary token overrides
- During testing/debugging

---

### 4. test_token_direct.sh
**Purpose:** Test a bearer token directly against ProjectForce API

**Usage:**
```bash
./test_token_direct.sh <bearer_token> [client_id] [user_id]

# Example
./test_token_direct.sh "TaDWx6r5O0WE2tb5..." 09PF05VD 1646085
```

**What it does:**
- Tests dashboard API endpoint
- Tests token validation endpoint
- Shows HTTP status codes
- Displays response preview

---

## 🔧 Common Workflows

### Workflow 1: Fix "403 Forbidden" Error

**Problem:** Lambda logs show `403 Client Error: Forbidden`

**Solution:**
```bash
cd /path/to/bedrock/scripts/test

# Step 1: Get a fresh token (use your existing script)
# Copy the token

# Step 2: Update Secrets Manager
./update_secrets_manager_token.sh
# Paste the fresh token when prompted

# Step 3: Test
cd ..
./test_agent_flow.py
```

---

### Workflow 2: Find Valid Project IDs

**Problem:** Getting "Access denied" for project IDs

**Solution:**
```bash
cd /path/to/bedrock/scripts/test

# Get list of accessible projects
./get_accessible_projects.sh

# Copy one of the project IDs from output
# Use it when running test_agent_flow.py
```

---

### Workflow 3: Test New Token Before Updating

**Problem:** Want to verify token works before deploying

**Solution:**
```bash
cd /path/to/bedrock/scripts/test

# Test the token first
./test_token_direct.sh "YOUR_TOKEN_HERE"

# If HTTP 200, update Secrets Manager
./update_secrets_manager_token.sh
```

---

### Workflow 4: Complete Token Refresh

**When:** Token is expired, need to refresh everything

**Steps:**
```bash
cd /path/to/bedrock/scripts/test

# 1. Get fresh token (use your login script)
# TOKEN="..."

# 2. Test it first
./test_token_direct.sh "$TOKEN"

# 3. Update Secrets Manager (used by Lambda)
./update_secrets_manager_token.sh
# Paste token when prompted

# 4. (Optional) Update Lambda env vars
./update_lambda_env_token.sh
# Paste token when prompted

# 5. Verify accessible projects
./get_accessible_projects.sh

# 6. Test end-to-end
cd ..
./test_agent_flow.py
# Use a project ID from step 5
```

---

## 🔍 Troubleshooting

### Error: "403 Forbidden"
**Cause:** Token is expired or invalid

**Fix:**
1. Get a fresh token from your auth system
2. Run `./update_secrets_manager_token.sh`
3. Paste the fresh token

---

### Error: "Access denied - insufficient permissions"
**Cause:** Project ID doesn't exist or you don't have access

**Fix:**
1. Run `./get_accessible_projects.sh`
2. Use one of the project IDs from the output

---

### Error: "Token validation failed"
**Cause:** Token format is incorrect or corrupted

**Fix:**
1. Ensure token is complete (no truncation)
2. Check for extra spaces or line breaks
3. Get a fresh token

---

## 📝 Token Sources

### Where Lambda Gets Tokens (Priority Order):
1. **Session Attributes** (`pf_bearer_token` or `bearer_token`)
   - Passed from agent invocation
   - Highest priority
   - Used when available

2. **AWS Secrets Manager** (`projectforce/api/credentials`)
   - Fallback when session doesn't have token
   - Updated by `update_secrets_manager_token.sh`
   - Recommended for production

3. **Lambda Environment Variables** (`BEARER_TOKEN`)
   - Last resort fallback
   - Updated by `update_lambda_env_token.sh`
   - Useful for testing

---

## 🎯 Best Practices

1. **Always Test Tokens First**
   ```bash
   ./test_token_direct.sh "TOKEN"
   ```

2. **Update Secrets Manager (Not Env Vars)**
   - Secrets Manager is more secure
   - Supports automatic rotation
   - Env vars are visible in Lambda console

3. **Check Accessible Projects Regularly**
   ```bash
   ./get_accessible_projects.sh > /tmp/projects.txt
   ```

4. **Verify After Updates**
   ```bash
   cd ..
   ./test_agent_flow.py
   ```

---

## 📚 Related Documentation

- **Agent Configuration:** `../config/agent_config.dev.json`
- **Lambda Functions:** `../../lambda/pf_scheduling_actions/`
- **Testing Flow:** `../test_agent_flow.py`
- **Deployment:** `../DEPLOY.sh`

---

## 🆘 Getting Help

If scripts fail:
1. Check AWS credentials: `aws sts get-caller-identity`
2. Check region: `echo $AWS_REGION` (should be us-east-1)
3. Check token format (should be 500+ characters)
4. Check Lambda logs: `aws logs tail /aws/lambda/pf-scheduling-actions --follow`

---

**Last Updated:** 2025-11-06
**Location:** `bedrock/scripts/test/`
**Scripts:** 4 total (all executable)
