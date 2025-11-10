# Troubleshooting Guide - Phase 1 Optimizations

## Issue: Access Denied After Model Switch

### Symptom
```json
{
  "error": "An error occurred (accessDeniedException) when calling the InvokeAgent operation: Access denied when calling Bedrock. Check your request permissions and retry the request."
}
```

### Root Cause
After switching agent models from Sonnet to Haiku, there may be a brief period (5-15 seconds) where:
1. Agent is in "PREPARING" status
2. IAM permissions are propagating
3. Inference profile is being initialized

### Solution
**Wait 15-30 seconds after agent preparation completes**, then retry.

```bash
# Re-prepare the agent
aws bedrock-agent prepare-agent --agent-id P9VCJXPIZS --region us-east-1

# Wait for preparation to complete
sleep 15

# Verify status is PREPARED
aws bedrock-agent get-agent --agent-id P9VCJXPIZS --region us-east-1 \
  --query 'agent.{Status:agentStatus}' \
  --output text

# Should output: PREPARED
```

### Verification
Test with a simple invocation:
```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id P9VCJXPIZS \
  --agent-alias-id TSTALIASID \
  --session-id "test-$(date +%s)" \
  --input-text "Hello" \
  --region us-east-1 \
  --output-file /tmp/response.txt

# Check response
cat /tmp/response.txt
```

### IAM Permissions Required
The agent role must have these permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/*",
                "arn:aws:bedrock:*::inference-profile/*"
            ]
        }
    ]
}
```

**Note:** Wildcards (`*`) are necessary to support all model versions and cross-region inference profiles.

---

## Issue: Performance Not Improved

### Symptom
Response times still around 30 seconds after applying Phase 1 optimizations.

### Possible Causes

#### 1. Using Cached Session
Old sessions may have cached the old agent behavior.

**Solution:** Use a **new session ID**:
```javascript
// Bad: Reusing old session
const sessionId = "session-12345";

// Good: New session for each test
const sessionId = `session-${Date.now()}`;
```

#### 2. Lambda Memory Not Updated
Verify Lambda memory was increased:

```bash
aws lambda get-function-configuration \
  --function-name pf-scheduling-actions \
  --query 'MemorySize' \
  --output text

# Should output: 3008
```

If not 3008:
```bash
aws lambda update-function-configuration \
  --function-name pf-scheduling-actions \
  --memory-size 3008 \
  --region us-east-1
```

#### 3. Agents Not Using Haiku
Verify agents switched to Haiku:

```bash
for agent_id in P9VCJXPIZS M0NRSM01QE WB5OPLGKMF; do
  echo "Agent: $agent_id"
  aws bedrock-agent get-agent --agent-id $agent_id --region us-east-1 \
    --query 'agent.{Model:foundationModel}' \
    --output text
done

# Should output haiku for all three:
# us.anthropic.claude-3-5-haiku-20241022-v1:0
```

#### 4. Cold Lambda Start
First request after deployment may be slower due to cold start.

**Solution:** Test with 2-3 consecutive requests:
```bash
# Request 1 (may be slow - cold start)
time invoke_agent "show my projects"

# Request 2 (should be faster - warm Lambda)
time invoke_agent "show my projects"

# Request 3 (should be fast - full optimization)
time invoke_agent "show my projects"
```

---

## Issue: Higher Costs Than Expected

### Symptom
AWS bill increased after Lambda memory upgrade.

### Explanation
Lambda costs increased by 70%, but should be offset by:
1. Model cost savings (80% cheaper)
2. Faster execution (50% less runtime)

### Cost Breakdown

**Before Phase 1 (10K requests/month):**
- Sonnet models: $180/month
- Lambda (1769 MB): $25.80/month
- **Total: $205.80/month**

**After Phase 1 (10K requests/month):**
- Haiku models: $15/month (Supervisor, Info, Chitchat)
- Sonnet model: $15/month (Scheduling only)
- Lambda (3008 MB): $37.13/month
- **Total: $67.13/month**

**Net Savings: $138.67/month (67% reduction)**

### Verify Costs
```bash
# Check Bedrock model invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Invocations \
  --dimensions Name=ModelId,Value=haiku-3-5 \
  --start-time 2025-11-10T00:00:00Z \
  --end-time 2025-11-10T23:59:59Z \
  --period 86400 \
  --statistics Sum \
  --region us-east-1
```

---

## Issue: Agent Responses Are Wrong

### Symptom
Agent is not returning the expected JSON format or adding commentary.

### Root Cause
Agent instructions may not have been updated or session is cached.

### Solution

#### 1. Verify Instructions
```bash
aws bedrock-agent get-agent --agent-id P9VCJXPIZS --region us-east-1 \
  --query 'agent.instruction' \
  --output text | head -20

# Should start with:
# "# Supervisor Agent (Optimized for Performance)"
# "You route requests to specialist agents..."
```

#### 2. Use New Session
Always use a fresh session ID when testing changes:
```python
import time
session_id = f"session-{int(time.time())}"
```

#### 3. Re-prepare Agent
```bash
aws bedrock-agent prepare-agent --agent-id P9VCJXPIZS --region us-east-1
sleep 15
```

---

## Issue: Lambda Timeout

### Symptom
```
Task timed out after 45.00 seconds
```

### Possible Causes
1. External API is slow
2. Connection pooling not working
3. Network issues

### Solution

#### 1. Check Lambda Logs
```bash
aws logs tail /aws/lambda/pf-scheduling-actions \
  --follow \
  --format short \
  --since 1m
```

Look for:
- API call timings
- Connection errors
- Timeout warnings

#### 2. Verify Connection Pooling
Check Lambda code has module-level session:
```python
# At module level (GOOD)
session = requests.Session()

# Inside handler (BAD)
def lambda_handler(event, context):
    session = requests.Session()  # ❌ Creates new connection each time
```

#### 3. Increase Timeout (if needed)
```bash
aws lambda update-function-configuration \
  --function-name pf-scheduling-actions \
  --timeout 60 \
  --region us-east-1
```

---

## Rollback Procedures

### Rollback Agent Models

```bash
#!/bin/bash
# Rollback to Sonnet 3.5

agents=("P9VCJXPIZS" "M0NRSM01QE" "WB5OPLGKMF")

for agent_id in "${agents[@]}"; do
  echo "Rolling back agent: $agent_id"

  aws bedrock-agent update-agent \
    --agent-id $agent_id \
    --foundation-model "us.anthropic.claude-3-5-sonnet-20241022-v2:0" \
    --region us-east-1

  aws bedrock-agent prepare-agent --agent-id $agent_id --region us-east-1

  sleep 5
done

echo "✅ All agents rolled back to Sonnet 3.5"
```

### Rollback Lambda Memory

```bash
#!/bin/bash
# Rollback Lambda memory to 1769 MB

aws lambda update-function-configuration \
  --function-name pf-scheduling-actions \
  --memory-size 1769 \
  --region us-east-1

aws lambda update-function-configuration \
  --function-name pf-information-actions \
  --memory-size 1769 \
  --region us-east-1

echo "✅ Lambda memory rolled back to 1769 MB"
```

---

## Performance Testing

### Baseline Test Script

```bash
#!/bin/bash
# Test Phase 1 Performance

echo "Testing Phase 1 Optimizations"
echo "=============================="

# Generate unique session ID
SESSION_ID="test-$(date +%s)"

# Test 1: Simple greeting (Chitchat Agent)
echo "Test 1: Chitchat (Haiku)"
START=$(date +%s.%N)
aws bedrock-agent-runtime invoke-agent \
  --agent-id P9VCJXPIZS \
  --agent-alias-id TSTALIASID \
  --session-id "$SESSION_ID-1" \
  --input-text "Hello" \
  --region us-east-1 \
  --output-file /tmp/test1.txt > /dev/null 2>&1
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "Duration: ${DIFF}s"
echo ""

# Test 2: Weather query (Information Agent)
echo "Test 2: Weather (Haiku)"
START=$(date +%s.%N)
aws bedrock-agent-runtime invoke-agent \
  --agent-id P9VCJXPIZS \
  --agent-alias-id TSTALIASID \
  --session-id "$SESSION_ID-2" \
  --input-text "What's the weather in Tampa?" \
  --region us-east-1 \
  --output-file /tmp/test2.txt > /dev/null 2>&1
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "Duration: ${DIFF}s"
echo ""

# Test 3: Project list (Scheduling Agent - Sonnet)
echo "Test 3: List Projects (Sonnet)"
START=$(date +%s.%N)
# This requires actual customer ID and session attributes
# Run from your backend with proper auth
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "Duration: ${DIFF}s"
echo ""

echo "✅ Testing complete"
echo "Expected: 40-50% faster than baseline (30s → 15-18s)"
```

---

## Getting Help

### Check Agent Status
```bash
aws bedrock-agent get-agent --agent-id P9VCJXPIZS --region us-east-1 \
  --query 'agent.{Name:agentName,Model:foundationModel,Status:agentStatus}' \
  --output json
```

### Check Lambda Status
```bash
aws lambda get-function --function-name pf-scheduling-actions --region us-east-1 \
  --query 'Configuration.{Memory:MemorySize,Status:LastUpdateStatus,Runtime:Runtime}' \
  --output json
```

### View Recent Logs
```bash
# Lambda logs
aws logs tail /aws/lambda/pf-scheduling-actions --follow --since 5m

# CloudWatch Insights query
aws logs start-query \
  --log-group-name /aws/lambda/pf-scheduling-actions \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20'
```

---

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `accessDeniedException` | Agent preparing or IAM propagating | Wait 15s, retry |
| `ModelNotFoundException` | Wrong model ID | Check `foundationModel` in agent config |
| `ThrottlingException` | Too many requests | Implement exponential backoff |
| `ResourceNotFoundException` | Agent not found | Verify agent ID is correct |
| `ValidationException` | Invalid parameters | Check agent collaboration mode |

---

## Contact & Support

If issues persist:
1. Check [PERFORMANCE_OPTIMIZATIONS_PHASE1.md](./PERFORMANCE_OPTIMIZATIONS_PHASE1.md) for implementation details
2. Review [BEDROCK_SDK_OPTIMIZATION.md](./BEDROCK_SDK_OPTIMIZATION.md) for backend setup
3. Check AWS Service Health Dashboard for regional issues
4. Review CloudWatch logs for detailed error messages
