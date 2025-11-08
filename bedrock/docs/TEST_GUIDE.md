# Testing Guide: Bedrock Agents & Lambda Functions

## Quick Test Commands

### 1. Test Supervisor Agent (Query Routing)
```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id CJ0EHPZGBU \
  --agent-alias-id TSTALIASID \
  --session-id "test-$(date +%s)" \
  --input-text "Hello, I need help scheduling an appointment" \
  --region us-east-1 \
  /tmp/supervisor_response.txt && cat /tmp/supervisor_response.txt
```

### 2. Test SchedulingAgent with Action Group
```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id ILSZT5EWND \
  --agent-alias-id TSTALIASID \
  --session-id "test-$(date +%s)" \
  --input-text "List all my projects" \
  --session-state '{
    "sessionAttributes": {
      "customer_id": "12345",
      "client_id": "09PF05VD",
      "user_name": "Test User"
    }
  }' \
  --region us-east-1 \
  /tmp/scheduling_response.txt && cat /tmp/scheduling_response.txt
```

### 3. Test Direct Lambda Invocation
```bash
aws lambda invoke \
  --function-name pf-scheduling-actions \
  --payload '{
    "actionGroup": "scheduling-actions",
    "function": "list_projects",
    "parameters": [
      {"name": "customer_id", "type": "string", "value": "12345"}
    ],
    "sessionAttributes": {
      "customer_id": "12345",
      "client_id": "09PF05VD",
      "user_name": "Test User"
    }
  }' \
  --region us-east-1 \
  /tmp/lambda_test.json && cat /tmp/lambda_test.json | python3 -m json.tool
```

### 4. Check Lambda Logs
```bash
aws logs tail /aws/lambda/pf-scheduling-actions --since 5m --format short --region us-east-1
```

### 5. Run Complete Test Suite
```bash
./scripts/test_agents.sh
```

---

## Testing Flow

### Architecture Overview
```
User Query
    ↓
Supervisor Agent (CJ0EHPZGBU)
    ↓
┌─────────────┬──────────────────┬─────────────┐
│             │                  │             │
Scheduling    Information    Chitchat      (routing based on intent)
(ILSZT5EWND)  (Z9OJEMMFND)  (NOLG2YV3HJ)
    ↓              ↓
Lambda         Lambda
pf-scheduling  pf-information
    ↓              ↓
ProjectForce API
```

### Test Scenarios

#### Scenario 1: Scheduling Flow
```bash
# 1. User asks Supervisor with session attributes
Query: "I want to schedule an appointment for my project"
Session Attributes: {
  "customer_id": "12345",
  "client_id": "09PF05VD",
  "user_name": "John Doe"
}

# 2. Supervisor routes to SchedulingAgent
# 3. SchedulingAgent uses action group → Lambda (passes session attributes)
# 4. Lambda extracts customer_id and client_id from session
# 5. Lambda retrieves Bearer token from Secrets Manager
# 6. Lambda calls ProjectForce API with auth headers
# 7. Response flows back
```

#### Scenario 2: Weather Query
```bash
# 1. User asks Supervisor
Query: "What's the weather in San Francisco?"

# 2. Supervisor routes to Information Agent
# 3. Information Agent uses action group → Lambda
# 4. Lambda calls weather API
# 5. Response flows back
```

#### Scenario 3: Conversational
```bash
# 1. User asks Supervisor
Query: "Hello! How are you?"

# 2. Supervisor routes to Chitchat Agent
# 3. Chitchat responds directly (no Lambda)
```

---

## Debugging

### Check Agent Status
```bash
aws bedrock-agent list-agents --region us-east-1 \
  --query 'agentSummaries[*].[agentName,agentId,agentStatus]' --output table
```

### Check Action Groups
```bash
# SchedulingAgent
aws bedrock-agent list-agent-action-groups \
  --agent-id ILSZT5EWND --agent-version DRAFT --region us-east-1

# Information Agent
aws bedrock-agent list-agent-action-groups \
  --agent-id Z9OJEMMFND --agent-version DRAFT --region us-east-1
```

### Check Lambda Functions
```bash
aws lambda list-functions --region us-east-1 \
  --query 'Functions[?starts_with(FunctionName, `pf-`)].FunctionName'
```

### View Lambda Code
```bash
aws lambda get-function --function-name pf-scheduling-actions --region us-east-1
```

### Monitor Real-Time Logs
```bash
# SchedulingAgent Lambda
aws logs tail /aws/lambda/pf-scheduling-actions --follow --region us-east-1

# Information Lambda
aws logs tail /aws/lambda/pf-information-actions --follow --region us-east-1
```

---

## Expected Responses

### Successful Lambda Response
```json
{
  "action": "list_projects",
  "customer_id": "12345",
  "projects": [...],
  "project_count": 5,
  "mock_mode": false
}
```

### Error Response
```json
{
  "error": "Failed to authenticate with API",
  "status_code": 401
}
```

---

## Common Issues

### Issue 1: Agent Not Responding
**Check:** Agent status must be "PREPARED"
```bash
aws bedrock-agent get-agent --agent-id ILSZT5EWND --region us-east-1
```

**Fix:** Re-prepare the agent
```bash
aws bedrock-agent prepare-agent --agent-id ILSZT5EWND --region us-east-1
```

### Issue 2: Lambda Not Invoked
**Check:** Action group must be ENABLED
```bash
aws bedrock-agent list-agent-action-groups --agent-id ILSZT5EWND --agent-version DRAFT --region us-east-1
```

**Fix:** Run deployment script
```bash
./scripts/DEPLOY.sh
```

### Issue 3: API Authentication Failures
**Check:** Secrets Manager has valid token
```bash
aws secretsmanager get-secret-value \
  --secret-id projectforce/api/dev/credentials --region us-east-1
```

**Fix:** Update with valid token
```bash
export PF_API_TOKEN="your-token-here"
./scripts/DEPLOY.sh
```

---

## Advanced Testing

### Test with Custom Session Attributes
```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id ILSZT5EWND \
  --agent-alias-id TSTALIASID \
  --session-id "test-session-123" \
  --input-text "List my projects" \
  --session-state '{
    "sessionAttributes": {
      "customer_id": "12345",
      "user_name": "John Doe"
    }
  }' \
  --region us-east-1 \
  /tmp/response.txt
```

### Test Lambda with Real API Call
```bash
# First, ensure token is in Secrets Manager
aws lambda invoke \
  --function-name pf-scheduling-actions \
  --payload '{
    "actionGroup": "scheduling-actions",
    "function": "list_projects",
    "parameters": [
      {"name": "customer_id", "type": "string", "value": "real-customer-id"}
    ],
    "messageVersion": "1.0",
    "sessionAttributes": {},
    "promptSessionAttributes": {}
  }' \
  --region us-east-1 \
  /tmp/real_api_test.json

cat /tmp/real_api_test.json | python3 -m json.tool
```

---

## Next Steps

1. **Run Initial Tests**: `./scripts/test_agents.sh`
2. **Verify Action Groups Work**: Check Lambda logs for invocations
3. **Test End-to-End**: Query through Supervisor → SchedulingAgent → Lambda → API
4. **Update API Token**: Replace PLACEHOLDER with real token in Secrets Manager
5. **Integration Testing**: Connect to your backend/UI

---

## Useful Commands Reference

### Agent IDs
- **Supervisor**: `CJ0EHPZGBU`
- **SchedulingAgent**: `ILSZT5EWND`
- **Information Agent**: `Z9OJEMMFND`
- **Chitchat Agent**: `NOLG2YV3HJ`

### Lambda Functions
- **pf-scheduling-actions**: Handles scheduling operations
- **pf-information-actions**: Handles weather/info queries
- **pf-query-router**: Routes queries (used by Supervisor)

### Test Alias ID
- **TSTALIASID**: Default test alias for all agents
