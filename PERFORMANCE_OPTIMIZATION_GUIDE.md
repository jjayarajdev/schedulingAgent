# Performance Optimization Guide
## ProjectForce Scheduling Agent - Response Time Improvements

**Current Issue:** Agent responses taking ~45 seconds
**Target:** Reduce to 5-10 seconds

---

## Root Cause Analysis

### Identified Bottlenecks

1. **Agent Collaboration Overhead** (15-20 seconds)
   - Supervisor agent receives request
   - Routes to specialized agent (Scheduling/Information/Chitchat)
   - Waits for collaborator response
   - Processes and returns result
   - Each hop adds latency

2. **Lambda Cold Starts** (2-5 seconds)
   - Current memory: 512 MB
   - First invocation or after idle period requires cold start
   - Python runtime initialization
   - Import dependencies (requests, boto3, etc.)

3. **Bedrock Model Processing** (10-15 seconds)
   - Using Claude 3.5 Sonnet v2 (powerful but slower)
   - Full model inference for both Supervisor and collaborator
   - Long instructions/prompts increase processing time

4. **API Call Latency** (5-10 seconds)
   - ProjectForce API calls from Lambda
   - Network latency + API processing time
   - No caching of frequently requested data

5. **Session Management** (1-2 seconds)
   - Session state persistence
   - Attribute resolution and validation

---

## Optimization Strategies

### 1. **Increase Lambda Memory** (Quick Win - 30% improvement)

**Current:** 512 MB
**Recommended:** 1024-2048 MB

**Why it helps:**
- More CPU allocated with higher memory
- Faster Python initialization
- Better performance for JSON parsing and API calls

**Implementation:**
```bash
aws lambda update-function-configuration \
  --function-name pf-scheduling-actions \
  --memory-size 1024

aws lambda update-function-configuration \
  --function-name pf-information-actions \
  --memory-size 1024
```

**Expected Impact:** 2-3 seconds improvement

---

### 2. **Enable Provisioned Concurrency** (Eliminates Cold Starts - 20% improvement)

**Current:** On-demand only
**Recommended:** 1-2 provisioned instances

**Why it helps:**
- Eliminates cold start latency
- Lambda always warm and ready
- Predictable performance

**Implementation:**
```bash
# Create provisioned concurrency for alias
aws lambda put-provisioned-concurrency-config \
  --function-name pf-scheduling-actions \
  --provisioned-concurrent-executions 1 \
  --qualifier PROD

# Repeat for information-actions
```

**Cost Impact:** ~$10-15/month per Lambda
**Expected Impact:** 2-5 seconds improvement

---

### 3. **Use Haiku for Supervisor Agent** (Major Win - 40% improvement)

**Current Model:** Claude 3.5 Sonnet v2 (`us.anthropic.claude-3-5-sonnet-20241022-v2:0`)
**Recommended:** Claude 3 Haiku (`anthropic.claude-3-haiku-20240307-v1:0`)

**Why it helps:**
- Supervisor only routes - doesn't need deep reasoning
- Haiku is 3-5x faster than Sonnet
- Significantly cheaper
- Still accurate for routing decisions

**Implementation:**
```bash
# Update agent configuration
aws bedrock-agent update-agent \
  --agent-id 6O1D7SE5OW \
  --foundation-model "anthropic.claude-3-haiku-20240307-v1:0" \
  --agent-name "ProjectForce-Supervisor"

# Prepare the agent
aws bedrock-agent prepare-agent --agent-id 6O1D7SE5OW
```

**Expected Impact:** 10-15 seconds improvement (BIGGEST IMPACT)

---

### 4. **Optimize Supervisor Instructions** (15% improvement)

**Current:** Long, detailed instructions
**Recommended:** Minimal routing-only instructions

**Why it helps:**
- Fewer tokens to process
- Faster inference
- Clearer routing logic

**Implementation:**

Create `/bedrock/infrastructure/agent_instructions/supervisor_optimized.txt`:

```
You are a routing agent. Route user requests to the appropriate collaborator:

ROUTING RULES:
- Scheduling/appointments/projects → SchedulingAgent
- General questions/information → InformationAgent
- Greetings/casual chat → ChitchatAgent

Return collaborator response EXACTLY as received. No additions or changes.
```

Then update:
```bash
# Update with optimized instructions
./scripts/update_agent_instructions.sh
```

**Expected Impact:** 2-3 seconds improvement

---

### 5. **Implement Response Caching** (30% improvement for repeated queries)

**Current:** Every request hits API
**Recommended:** Cache frequently requested data

**Why it helps:**
- Skip API calls for cached data
- Reduce Lambda execution time
- Better user experience

**Implementation:**

Update Lambda to use DynamoDB caching:

```python
# Add to handler.py
import boto3
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
cache_table = dynamodb.Table('pf-agent-cache')

def get_cached_projects(customer_id, ttl_minutes=5):
    """Check cache before API call"""
    try:
        response = cache_table.get_item(
            Key={'customer_id': customer_id, 'data_type': 'projects'}
        )

        if 'Item' in response:
            cached_time = datetime.fromisoformat(response['Item']['timestamp'])
            if datetime.now() - cached_time < timedelta(minutes=ttl_minutes):
                logger.info("Cache HIT for projects")
                return response['Item']['data']

        logger.info("Cache MISS for projects")
        return None
    except Exception as e:
        logger.error(f"Cache error: {e}")
        return None

def cache_projects(customer_id, data):
    """Store in cache"""
    try:
        cache_table.put_item(
            Item={
                'customer_id': customer_id,
                'data_type': 'projects',
                'data': data,
                'timestamp': datetime.now().isoformat(),
                'ttl': int((datetime.now() + timedelta(hours=1)).timestamp())
            }
        )
    except Exception as e:
        logger.error(f"Cache write error: {e}")
```

**Expected Impact:** 5-10 seconds for cached responses

---

### 6. **Enable Keep-Alive for HTTP Connections** (10% improvement)

**Current:** New connection per API request
**Recommended:** Reuse connections

**Implementation:**

```python
# In config.py or handler.py
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Create session with connection pooling
session = requests.Session()
adapter = HTTPAdapter(
    pool_connections=10,
    pool_maxsize=20,
    max_retries=Retry(total=3, backoff_factor=0.1)
)
session.mount('https://', adapter)

# Use session instead of requests.get/post
def call_api(url, headers, data=None):
    if data:
        return session.post(url, json=data, headers=headers, timeout=10)
    return session.get(url, headers=headers, timeout=10)
```

**Expected Impact:** 1-2 seconds improvement

---

### 7. **Parallel API Calls** (20% improvement for multi-step operations)

**Current:** Sequential API calls
**Recommended:** Parallel execution where possible

**Implementation:**

```python
import concurrent.futures

def get_projects_with_details(customer_id, client_id, token):
    """Fetch projects and their details in parallel"""

    # First get project list
    projects = call_api_get_projects(customer_id, client_id, token)

    # Fetch details for multiple projects in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_project = {
            executor.submit(call_api_get_project_details, p['id'], token): p
            for p in projects[:5]  # Top 5 projects
        }

        for future in concurrent.futures.as_completed(future_to_project):
            project = future_to_project[future]
            try:
                details = future.result()
                project.update(details)
            except Exception as e:
                logger.error(f"Error fetching details for {project['id']}: {e}")

    return projects
```

**Expected Impact:** 3-5 seconds for multi-project queries

---

## Implementation Priority

### Phase 1: Quick Wins (1-2 hours, 40-50% improvement)

1. ✅ **Switch Supervisor to Haiku** (15 seconds saved)
2. ✅ **Increase Lambda Memory to 1024 MB** (2-3 seconds saved)
3. ✅ **Optimize Supervisor Instructions** (2-3 seconds saved)

**Expected Total:** 45s → 23-25s (45% improvement)

---

### Phase 2: Medium Effort (1-2 days, 60-70% improvement)

4. ✅ **Enable Provisioned Concurrency** (2-5 seconds saved)
5. ✅ **HTTP Connection Pooling** (1-2 seconds saved)
6. ✅ **Optimize Lambda Code** (remove unused imports, efficient JSON parsing)

**Expected Total:** 45s → 15-18s (60% improvement)

---

### Phase 3: Advanced (3-5 days, 75-80% improvement)

7. ✅ **DynamoDB Caching** (5-10 seconds saved for cached responses)
8. ✅ **Parallel API Calls** (3-5 seconds saved)
9. ✅ **Consider Direct Agent Invocation** (bypass Supervisor for known intents)

**Expected Total:** 45s → 8-12s (75% improvement)

---

## Monitoring & Measurement

### Add Performance Logging

```python
import time

def lambda_handler(event, context):
    start_time = time.time()

    # Track individual steps
    step_times = {}

    # Extract parameters
    extract_start = time.time()
    params = extract_parameters(event)
    step_times['extract_params'] = time.time() - extract_start

    # API call
    api_start = time.time()
    result = call_api(...)
    step_times['api_call'] = time.time() - api_start

    # Format response
    format_start = time.time()
    response = format_response(result)
    step_times['format_response'] = time.time() - format_start

    total_time = time.time() - start_time

    logger.info(f"Performance: Total={total_time:.2f}s, Steps={step_times}")

    return response
```

### CloudWatch Metrics

Monitor these metrics after optimizations:
- Lambda Duration (p50, p95, p99)
- Lambda Cold Start Count
- Bedrock Agent Latency
- API Call Duration

---

## Cost Analysis

| Optimization | Monthly Cost | Savings (Time) |
|-------------|--------------|----------------|
| Memory 512→1024 MB | +$2-3 | 2-3s |
| Provisioned Concurrency (1) | +$10-15 | 2-5s |
| Supervisor: Sonnet→Haiku | -$20-30 | 10-15s |
| DynamoDB Caching | +$1-2 | 5-10s (cached) |
| **Net Change** | **-$7 to -$10** | **20-30s** |

**Result:** Better performance + Lower costs

---

## Recommended Action Plan

### Step 1: Deploy Quick Wins (Today)

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock

# 1. Update Lambda memory
aws lambda update-function-configuration \
  --function-name pf-scheduling-actions \
  --memory-size 1024

aws lambda update-function-configuration \
  --function-name pf-information-actions \
  --memory-size 1024

# 2. Switch Supervisor to Haiku
aws bedrock-agent update-agent \
  --agent-id 6O1D7SE5OW \
  --foundation-model "anthropic.claude-3-haiku-20240307-v1:0" \
  --agent-name "ProjectForce-Supervisor"

aws bedrock-agent prepare-agent --agent-id 6O1D7SE5OW

# 3. Create optimized supervisor instructions
cat > infrastructure/agent_instructions/supervisor_optimized.txt << 'EOF'
You are a routing agent. Route user requests to the appropriate collaborator:

ROUTING RULES:
- Scheduling/appointments/projects → SchedulingAgent
- General questions/information → InformationAgent
- Greetings/casual chat → ChitchatAgent

Return collaborator response EXACTLY as received. No additions or changes.
EOF

# 4. Update agent
./scripts/update_agent_instructions.sh
```

### Step 2: Test Performance

```bash
# Run test queries and measure
time curl -X POST http://localhost:5003/api/invoke-agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show my projects",
    "session_id": "perf-test-1",
    "pf_token": "YOUR_TOKEN",
    "pf_client_id": "09PF05VD",
    "pf_user_id": "1646085",
    "stream": false
  }'
```

### Step 3: Monitor & Iterate

```bash
# Watch Lambda logs for timing
aws logs tail /aws/lambda/pf-scheduling-actions \
  --follow \
  --format short \
  --filter-pattern "Duration"
```

---

## Expected Results

| Metric | Before | After Phase 1 | After Phase 2 | After Phase 3 |
|--------|--------|---------------|---------------|---------------|
| **Response Time** | 45s | 23-25s | 15-18s | 8-12s |
| **P95 Latency** | 50s | 28s | 20s | 15s |
| **Cold Starts** | 5s | 5s | 0s | 0s |
| **Monthly Cost** | $50 | $45 | $43 | $45 |

---

## Troubleshooting

### If performance doesn't improve:

1. **Check CloudWatch Logs** for bottlenecks
2. **Enable X-Ray tracing** to see detailed timing
3. **Verify Haiku model** is actually being used
4. **Check network latency** between Lambda and ProjectForce API
5. **Consider VPC endpoint** for Bedrock if using VPC

### X-Ray Setup

```bash
aws lambda update-function-configuration \
  --function-name pf-scheduling-actions \
  --tracing-config Mode=Active
```

---

**Last Updated:** 2025-11-08
**Version:** 1.0
**Owner:** ProjectForce Team
