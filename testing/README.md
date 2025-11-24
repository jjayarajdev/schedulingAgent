# ProjectForce Bedrock Agent Testing Suite

Comprehensive testing suite for ProjectForce Bedrock multi-agent system with formatted output, test UI, and automated test suites.

**Last Updated**: 2025-11-15
**Status**: Production Ready with 6 Test Suites

## 📁 Files

| File | Description |
|------|-------------|
| `FORMATTED_TESTING.md` | Complete guide to formatted test results |
| `format_results.py` | Formatter for clean, color-coded test output |
| `run_test_formatted.sh` | Wrapper to run tests with formatting |
| `run_all_test_suites.sh` | Runs all 6 test suites sequentially |
| `test_suite_1_basic_workflow.sh` | Basic project workflow tests |
| `test_suite_2_context_resolution.sh` | Context tracking and reference tests |
| `test_suite_3_filtering.sh` | Advanced filtering tests |
| `test_suite_4_chitchat_mixed.sh` | Chitchat and routing tests |
| `test_suite_5_scheduling.sh` | Scheduling workflow tests |
| `test_suite_6_notes.sh` | Notes functionality tests (NEW) |
| `run_quick_tests.sh` | Quick sanity check tests |
| `test_config.sh` | Configuration file for test credentials |
| `ui/index.html` | Interactive test UI (localhost:8000) |
| `README.md` | This file - testing guide |

## 🚀 Quick Start

### Option 1: Interactive Test UI (Recommended)

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/bedrock/testing/ui
python3 -m http.server 8000
```

Open browser: http://localhost:8000

**Features**:
- Real-time chat interface
- Session persistence
- Performance metrics display
- Response visualization
- No configuration needed (uses test credentials)

### Option 2: Formatted Test Suites (Recommended for Automation)

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/bedrock/testing

# Quick sanity check
./run_test_formatted.sh run_quick_tests.sh

# Full test suites
./run_test_formatted.sh test_suite_1_basic_workflow.sh
./run_test_formatted.sh test_suite_2_context_resolution.sh
./run_test_formatted.sh test_suite_3_filtering.sh
./run_test_formatted.sh test_suite_4_chitchat_mixed.sh
./run_test_formatted.sh test_suite_5_scheduling.sh
```

**Features**:
- Color-coded output (green=direct, yellow=agent, red=error)
- Performance metrics (avg/min/max times)
- Error summaries
- Clean table format
- See `FORMATTED_TESTING.md` for details

### Option 3: Manual curl Commands

1. **Configure your credentials**:
   ```bash
   cd /Users/jjayaraj/workspaces/studios/projectsforce/bedrock/testing
   nano test_config.sh  # Edit with your credentials
   ```

2. **Load configuration**:
   ```bash
   source test_config.sh
   ```

3. **Run individual tests**:
   ```bash
   # Example: List projects
   curl -X POST "$API_ENDPOINT" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "show my projects",
       "session_id": "test-001",
       "pf_token": "'"$PF_TOKEN"'",
       "pf_client_id": "'"$PF_CLIENT_ID"'",
       "pf_user_id": '"$PF_USER_ID"'
     }'
   ```

### Option 2: Using Postman

#### Step 1: Import Environment
1. Open Postman
2. Click **Environments** (left sidebar)
3. Click **Import**
4. Select `ProjectForce_Bedrock.postman_environment.json`
5. Click the imported environment to edit it
6. **Update these values** with your credentials:
   - `base_url` - Your API Gateway endpoint
   - `pf_token` - Your ProjectForce bearer token
   - `pf_client_id` - Your client ID
   - `pf_user_id` - Your user ID
7. Click **Save**

#### Step 2: Import Collection
1. Click **Collections** (left sidebar)
2. Click **Import**
3. Select `ProjectForce_Bedrock_Tests.postman_collection.json`
4. The collection will be imported with 60+ requests

#### Step 3: Select Environment
1. In the top-right corner, select environment dropdown
2. Choose **"ProjectForce Bedrock - Production"**

#### Step 4: Run Tests
- **Single Test**: Click any request → **Send**
- **Folder**: Right-click folder → **Run**
- **All Tests**: Click collection → **Run** → **Run ProjectForce Bedrock Agent Tests**

## 🔧 Configuration Options

### For curl Tests (test_config.sh)

Edit `test_config.sh` to update:

```bash
# API Gateway Endpoint
export API_ENDPOINT="https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/dev/invoke-agent"

# Authentication
export PF_TOKEN="YOUR_BEARER_TOKEN"
export PF_CLIENT_ID="YOUR_CLIENT_ID"
export PF_USER_ID=YOUR_USER_ID
```

### For Postman Tests (Environment File)

Edit the environment in Postman UI or modify `ProjectForce_Bedrock.postman_environment.json`:

```json
{
  "key": "base_url",
  "value": "https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/dev"
},
{
  "key": "pf_token",
  "value": "YOUR_BEARER_TOKEN"
},
{
  "key": "pf_client_id",
  "value": "YOUR_CLIENT_ID"
},
{
  "key": "pf_user_id",
  "value": "YOUR_USER_ID"
}
```

## 📊 Test Suites

### Suite 1: Basic Project Workflow
**File**: `test_suite_1_basic_workflow.sh`
- Greeting (chitchat agent)
- List all projects (direct lambda ~2s)
- Filter projects by status (direct lambda ~2s)
- Get project details (direct lambda ~2s)
- Schedule project (scheduling agent ~5-25s)

### Suite 2: Context Resolution
**File**: `test_suite_2_context_resolution.sh`
- Ordinal references ("the 3rd project", "the last one")
- Pronoun references ("that project", "schedule it")
- Implicit context tracking across turns
- Location inference for weather queries

### Suite 3: Advanced Filtering
**File**: `test_suite_3_filtering.sh`
- Filter by status (Scheduled, New, Unscheduled)
- Filter by category (Decking, Roofing, etc.)
- Filter by project type (Call Back, Demo, Install)
- Combined filters
- Empty result handling

### Suite 4: Chitchat & Mixed Queries
**File**: `test_suite_4_chitchat_mixed.sh`
- Greetings and casual conversation
- Help requests
- Mixed chitchat + business queries
- Agent routing validation

### Suite 5: Scheduling Workflows
**File**: `test_suite_5_scheduling.sh`
- Schedule project workflow (multi-turn)
- Reschedule operations
- Cancel appointments
- Date/time validation
- Confirmation flows

### Suite 6: Notes Functionality
**File**: `test_suite_6_notes.sh`
- Add note with explicit project ID
- List notes for a project
- Add multiple notes to same project
- Context-aware note addition (after viewing project)
- Context-aware note listing
- Verify notes are stored in DynamoDB
- Test note author tracking

### Quick Tests
**File**: `run_quick_tests.sh`
- Fast sanity check (~30 seconds)
- Core functionality validation
- Deployment verification

## 🎯 Example Workflows

### Complete E2E Flow

Using the same `session_id` maintains conversation context:

```bash
SESSION="e2e-$(date +%s)"

# 1. Greeting
curl -X POST "$API_ENDPOINT" -H "Content-Type: application/json" \
  -d '{"message":"hi","session_id":"'$SESSION'","pf_token":"'"$PF_TOKEN"'","pf_client_id":"'"$PF_CLIENT_ID"'","pf_user_id":'"$PF_USER_ID"'}'

# 2. List projects
curl -X POST "$API_ENDPOINT" -H "Content-Type: application/json" \
  -d '{"message":"show my projects","session_id":"'$SESSION'","pf_token":"'"$PF_TOKEN"'","pf_client_id":"'"$PF_CLIENT_ID"'","pf_user_id":'"$PF_USER_ID"'}'

# 3. Get details
curl -X POST "$API_ENDPOINT" -H "Content-Type: application/json" \
  -d '{"message":"show details for the 1st project","session_id":"'$SESSION'","pf_token":"'"$PF_TOKEN"'","pf_client_id":"'"$PF_CLIENT_ID"'","pf_user_id":'"$PF_USER_ID"'}'

# 4. Schedule
curl -X POST "$API_ENDPOINT" -H "Content-Type: application/json" \
  -d '{"message":"schedule this project","session_id":"'$SESSION'","pf_token":"'"$PF_TOKEN"'","pf_client_id":"'"$PF_CLIENT_ID"'","pf_user_id":'"$PF_USER_ID"'}'

# 5. Provide date
curl -X POST "$API_ENDPOINT" -H "Content-Type: application/json" \
  -d '{"message":"November 20, 2025","session_id":"'$SESSION'","pf_token":"'"$PF_TOKEN"'","pf_client_id":"'"$PF_CLIENT_ID"'","pf_user_id":'"$PF_USER_ID"'}'

# 6. Provide time
curl -X POST "$API_ENDPOINT" -H "Content-Type: application/json" \
  -d '{"message":"9:00 AM","session_id":"'$SESSION'","pf_token":"'"$PF_TOKEN"'","pf_client_id":"'"$PF_CLIENT_ID"'","pf_user_id":'"$PF_USER_ID"'}'

# 7. Confirm
curl -X POST "$API_ENDPOINT" -H "Content-Type: application/json" \
  -d '{"message":"yes, confirm","session_id":"'$SESSION'","pf_token":"'"$PF_TOKEN"'","pf_client_id":"'"$PF_CLIENT_ID"'","pf_user_id":'"$PF_USER_ID"'}'
```

### Multi-turn Scheduling

Use Postman folder: **"5. Schedule Project (Multi-turn)"**

Run requests in sequence with the same `session_id`:
1. 5.1 Schedule - Step 1 (Initiate)
2. 5.2 Schedule - Step 2 (Date)
3. 5.3 Schedule - Step 3 (Time)
4. 5.4 Schedule - Step 4 (Confirm)

## 📈 Expected Performance

| Route Type | Expected Time | Test Categories | Example Queries |
|-----------|---------------|-----------------|-----------------|
| **Direct Lambda** | ~2 seconds | List, Filter, Details | "show my projects", "scheduled projects" |
| **Bedrock Agents** | ~5-25 seconds | Greeting, Schedule, Complex queries | "hello", "schedule project 123", "what's the weather" |
| **Classification** | ~0.1-0.2 seconds | All queries | Intent detection overhead |

### Performance by Agent
- **Chitchat Agent**: ~5-10s (simple responses)
- **Scheduling Agent**: ~10-25s (multi-turn conversations)
- **Information Agent**: ~5-15s (complex queries)
- **Direct Lambda**: ~2s (simple data retrieval)

## 🔍 Validation

### curl Tests
- Check HTTP status: `200`
- Check response has `output` field
- Check response time

### Postman Tests (Automated)
Each request includes test scripts:
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Response has output", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('output');
});

pm.test("Response time is acceptable", function () {
    pm.expect(pm.response.responseTime).to.be.below(15000);
});
```

## 🆘 Troubleshooting

### Issue: "401 Unauthorized"
**Cause**: Invalid or expired credentials
**Fix**:
- Check your `pf_token` is valid and not expired
- Verify `pf_client_id` and `pf_user_id` are correct
- Update credentials in `test_config.sh`

### Issue: "Internal server error" or "Task timed out"
**Cause**: Lambda execution error or timeout
**Fix**:
- Check CloudWatch logs:
  ```bash
  aws logs tail /aws/lambda/pf-orchestrator --follow
  ```
- Verify Lambda environment variables are set
- Check DynamoDB table exists (pf-sessions-dev)
- Verify IAM permissions for Bedrock + DynamoDB

### Issue: Slow responses (>30s or timeout)
**Cause**: Not using hybrid routing or VPC issues
**Fix**:
- Check if hybrid routing is enabled: `ALLOW_DIRECT_LAMBDA=true`
- Verify USE_SUPERVISOR=false for direct agent routing
- Ensure Lambda is NOT in VPC (serverless architecture)
- Check Lambda cold start times (should be ~2s, not ~10s)

### Issue: Session not maintained / Context lost
**Cause**: DynamoDB session storage issue
**Fix**:
- Ensure you're using the same `session_id` across requests
- Check DynamoDB table exists and is accessible
- Verify Lambda has DynamoDB permissions
- Check session TTL (default 1 hour)
- View session data:
  ```bash
  aws dynamodb get-item --table-name pf-sessions-dev \
    --key '{"session_id": {"S": "your-session-id"}}'
  ```

### Issue: "No JSON responses found" in formatted tests
**Cause**: Test returned non-JSON output or failed
**Fix**:
- Run test without formatter to see raw output:
  ```bash
  ./test_suite_1_basic_workflow.sh
  ```
- Check API endpoint is correct in test_config.sh
- Verify network connectivity to API Gateway

## 📝 Adding New Tests

### In curl (TEST_CASES.md)
Add new test case:
```bash
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "your new query",
    "session_id": "test-new-001",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
```

### In Postman
1. Right-click appropriate folder
2. Click **Add Request**
3. Name it following the pattern: `X.Y Description`
4. Use body template with variables:
   ```json
   {
     "message": "your query",
     "session_id": "{{session_id}}-test-new",
     "pf_token": "{{pf_token}}",
     "pf_client_id": "{{pf_client_id}}",
     "pf_user_id": {{pf_user_id}}
   }
   ```

## 🔐 Security Notes

- **Never commit credentials** to version control
- Use environment variables or Postman environments
- Rotate tokens regularly
- Use different tokens for dev/staging/production
- Consider using AWS Secrets Manager for production

## 📚 Additional Resources

- **API Documentation**: See `TEST_CASES.md` for detailed test documentation
- **Deployment Guide**: See `/scripts/DEPLOY.sh` and `/tmp/DEPLOYMENT_SEQUENCE.md`
- **Architecture**: Hybrid routing with direct Lambda calls and Supervisor agent
- **Troubleshooting**: Check CloudWatch logs for Lambda invocations

## ✅ Verification Checklist

After setting up, verify:

- [ ] Environment variables loaded (`source test_config.sh`)
- [ ] Postman environment imported and selected
- [ ] Test credentials are valid
- [ ] API endpoint is correct
- [ ] Simple greeting test works (Postman: 1.1 or curl test case 1.1)
- [ ] List projects test works (Postman: 2.1 or curl test case 2.1)
- [ ] Hybrid routing is working (fast responses for list/filter)

---

**Ready to test!** Start with the simple tests in section 1 (Greeting) and 2 (List Projects) to verify your setup.
