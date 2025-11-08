# API Mode Management Scripts

This directory contains scripts to manage the API mode configuration for all Lambda functions in the ProjectForce scheduling agent system.

## Overview

The Lambda functions can operate in two modes:
- **Mock API Mode**: Uses mock/simulated data for testing and development
- **Real API Mode**: Makes actual API calls to the ProjectForce CX Portal API

## Current Status

As of the last check, the Lambda functions are configured as follows:

| Lambda Function | USE_MOCK_API | Bearer Token | Status |
|----------------|--------------|--------------|--------|
| pf-scheduling-actions | `false` | ✓ Configured | **Real API Mode ENABLED** |
| pf-information-actions | `false` | ✓ Configured | **Real API Mode ENABLED** |
| pf-notes-actions | N/A | N/A | Function not yet deployed |

## Available Scripts

### 1. check_api_mode.sh

**Purpose**: Check the current API mode configuration for all Lambda functions

**Usage**:
```bash
cd bedrock/scripts
./check_api_mode.sh
```

**Output**: Displays the current configuration for each Lambda function including:
- USE_MOCK_API status
- ENABLE_REAL_CONFIRM status
- ENABLE_REAL_CANCEL status
- ENVIRONMENT setting
- Bearer token configuration status

**When to use**:
- Before making changes to verify current state
- After updates to confirm changes were applied
- During troubleshooting to understand Lambda configuration

### 2. enable_real_api.sh

**Purpose**: Switch all Lambda functions from mock to real API mode

**Usage**:
```bash
cd bedrock/scripts
./enable_real_api.sh
```

**What it does**:
- Sets `USE_MOCK_API=false` for all Lambda functions
- Sets `ENABLE_REAL_CONFIRM=true`
- Sets `ENABLE_REAL_CANCEL=true`
- Sets `ENVIRONMENT=dev` (or your specified environment)
- Verifies changes were applied successfully

**Requirements**:
- AWS CLI configured with appropriate credentials
- IAM permissions to update Lambda function configurations
- Valid bearer token configured in Lambda environment variables

**When to use**:
- When you want to test with real ProjectForce API data
- After deploying to production or staging environments
- When mock data is no longer sufficient for your testing needs

**Warning**: This enables REAL API calls that will affect actual ProjectForce data. Ensure you have:
1. A valid bearer token configured
2. Appropriate permissions for the API endpoints
3. Confirmed you want to make real changes to the system

### 3. disable_real_api.sh

**Purpose**: Switch all Lambda functions back to mock API mode

**Usage**:
```bash
cd bedrock/scripts
./disable_real_api.sh
```

**What it does**:
- Sets `USE_MOCK_API=true` for all Lambda functions
- Sets `ENABLE_REAL_CONFIRM=false`
- Sets `ENABLE_REAL_CANCEL=false`
- Verifies changes were applied successfully

**When to use**:
- When you want to revert to mock data for testing
- During development when you don't need real API calls
- To avoid hitting API rate limits or affecting production data
- When troubleshooting issues without making real changes

## Lambda Functions Managed

These scripts manage the following Lambda functions:

1. **pf-scheduling-actions**
   - Handles scheduling operations (list projects, get dates/slots, confirm/cancel appointments)
   - Location: `bedrock/lambda/scheduling-actions/`
   - APIs: `/dashboard/get`, `/scheduler/*/business-hours`, `/scheduler/*/slots`, `/scheduler/*/schedule`

2. **pf-information-actions**
   - Handles information retrieval and customer queries
   - Location: `bedrock/lambda/information-actions/`

3. **pf-notes-actions** (Not yet deployed)
   - Will handle notes operations for projects
   - Location: `bedrock/lambda/notes-actions/`

## Environment Variables

The scripts manage the following Lambda environment variables:

### Primary Configuration
- **USE_MOCK_API**: `true` or `false`
  - Controls whether Lambda uses mock data or makes real API calls
  - Default in code: `true`
  - Recommended for dev: `false` (if bearer token is available)

### Feature Flags
- **ENABLE_REAL_CONFIRM**: `true` or `false`
  - Enables real appointment confirmation API calls
  - Default: `false`
  - Set to `true` when USE_MOCK_API=false

- **ENABLE_REAL_CANCEL**: `true` or `false`
  - Enables real appointment cancellation API calls
  - Default: `false`
  - Set to `true` when USE_MOCK_API=false

### Environment Settings
- **ENVIRONMENT**: `dev`, `staging`, or `prod`
  - Determines which API base URL to use
  - Default: `dev`

- **BEARER_TOKEN**: String
  - Authentication token for ProjectForce CX Portal API
  - Must be valid and current
  - Use `scripts/test/update_lambda_env_token.sh` to update

## API Endpoints

The real API mode connects to ProjectForce CX Portal API:

### Base URLs (by environment)
- **dev**: `https://api-cx-portal.dev.projectsforce.com`
- **staging**: `https://api-cx-portal.staging.projectsforce.com`
- **prod**: `https://api-cx-portal.projectsforce.com`

### Endpoints Used
- `GET /dashboard/get/{client_id}/{customer_id}` - List customer projects
- `GET /scheduler/client/{client_id}/business-hours` - Get business hours
- `GET /scheduler/client/{client_id}/project/{project_id}/date/{date}/selected/{date}/slots` - Get available dates and time slots
- `POST /scheduler/client/{client_id}/project/{project_id}/schedule` - Confirm appointment
- `POST /scheduler/client/{client_id}/project/{project_id}/cancel` - Cancel appointment

## Testing After Changes

After enabling real API mode, test the system:

### 1. Launch the Test UI
```bash
cd bedrock/testing/ui
./launch_webapp.sh
```

### 2. Monitor Lambda Logs
```bash
# For scheduling actions
aws logs tail /aws/lambda/pf-scheduling-actions --follow

# For information actions
aws logs tail /aws/lambda/pf-information-actions --follow
```

### 3. Test Scheduling Flow
1. Open http://localhost:8000/pf_auth_demo.html
2. Enter customer_id and client_id
3. Ask the agent to schedule an appointment
4. Verify the agent:
   - Lists real projects from the API
   - Shows real available dates
   - Displays real time slots
   - Successfully confirms appointment with real API
   - Returns proper confirmation details

### 4. Verify API Calls
Check Lambda logs for:
```
✓ Making API call to: https://api-cx-portal.dev.projectsforce.com/dashboard/get/...
✓ API Response (200): {...}
```

If you see mock responses instead:
```
⚠️ Using MOCK response for [endpoint] (USE_MOCK_API=true)
```
...then the configuration didn't take effect. Re-run `enable_real_api.sh`.

## Troubleshooting

### Issue: "Function not found" error
**Cause**: Lambda function hasn't been deployed yet
**Solution**: Deploy the Lambda function first using Terraform or deployment scripts

### Issue: "401 Unauthorized" API errors
**Cause**: Bearer token is invalid or expired
**Solution**: Update the bearer token:
```bash
cd bedrock/scripts/test
./update_lambda_env_token.sh
```

### Issue: Lambda still using mock data after enabling real API
**Cause**: Environment variable update didn't take effect
**Solution**:
1. Run `check_api_mode.sh` to verify configuration
2. Re-run `enable_real_api.sh`
3. Wait 30 seconds for Lambda to pick up new configuration
4. Test again

### Issue: "No technician found" errors when scheduling
**Cause**: This is a known issue where the slots API returns times without technician availability
**Solution**:
- The agent now handles this gracefully (see `scheduling_collaborator.txt`)
- Agent will offer alternatives when a slot is unavailable
- Consider investigating backend slots API filtering logic

## Best Practices

1. **Always check current status first**
   ```bash
   ./check_api_mode.sh
   ```

2. **Use mock mode for rapid development**
   - Mock mode is faster and doesn't require valid tokens
   - Use when developing agent instructions or UI changes

3. **Use real mode for integration testing**
   - Test with real API before deploying to production
   - Verify bearer token is current
   - Monitor logs during testing

4. **Keep bearer tokens up to date**
   - Tokens expire regularly
   - Use `get_fresh_token.sh` to obtain new tokens
   - Update Lambda environment variables with new tokens

5. **Monitor API usage**
   - Real API calls count against rate limits
   - Consider using mock mode if hitting rate limits
   - Check CloudWatch for Lambda invocation metrics

## Related Files

- `bedrock/lambda/scheduling-actions/config.py` - Configuration for scheduling Lambda
- `bedrock/lambda/information-actions/config.py` - Configuration for information Lambda
- `bedrock/lambda/notes-actions/config.py` - Configuration for notes Lambda
- `bedrock/lambda/.env.example` - Template for environment variables
- `bedrock/scripts/test/update_lambda_env_token.sh` - Script to update bearer tokens
- `bedrock/scripts/get_fresh_token.sh` - Script to get new bearer token

## See Also

- [API_AUTHENTICATION_GUIDE.md](../../API_AUTHENTICATION_GUIDE.md) - Guide for obtaining and using bearer tokens
- [DASHBOARD_API_DEPLOYMENT_STATUS.md](../../DASHBOARD_API_DEPLOYMENT_STATUS.md) - Status of API integration
- [scheduling_collaborator.txt](../infrastructure/agent_instructions/scheduling_collaborator.txt) - Agent instructions including error handling
