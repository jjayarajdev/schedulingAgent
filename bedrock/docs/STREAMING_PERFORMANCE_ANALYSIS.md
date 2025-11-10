# Streaming Performance Analysis

## Current Problem

**Symptom:** Simple "Hi" message takes 10.7 seconds total
- Agent processing: 1.06s (GOOD ✅)
- Stream processing: 9.65s (BAD ❌)

**Expected:** Should be 2-3 seconds total for a simple greeting

---

## Root Cause Analysis

The 9.6-second streaming delay is NOT the agent - it's your **backend processing the streaming response**.

### Likely Issues

1. **No Bedrock SDK Connection Pooling**
   - Backend creates new connection each request
   - TCP handshake: ~100-300ms
   - TLS negotiation: ~200-500ms
   - **Total overhead: 300-800ms per request**

2. **Inefficient Event Stream Processing**
   - Processing events one-by-one instead of batching
   - Not buffering chunks before sending to client
   - Excessive logging/processing per chunk

3. **Network Latency**
   - Backend → AWS Bedrock: ~50-100ms RTT
   - If processing chunks individually: N chunks × 50ms = seconds of delay

4. **Backend Framework Overhead**
   - FastAPI/Flask streaming not optimized
   - Middleware adding latency
   - No HTTP/2 for multiplexing

---

## Diagnostic Steps

### 1. Measure Backend Bedrock Client Performance

Add this to your backend code:

```python
import time
import logging

logger = logging.getLogger(__name__)

def invoke_agent_with_metrics(message, customer_id):
    """Invoke agent and measure each phase"""

    metrics = {}

    # Phase 1: Initialize client
    start = time.time()
    # Your bedrock client initialization here
    metrics['client_init'] = time.time() - start

    # Phase 2: Invoke agent
    start = time.time()
    response = bedrock_client.invoke_agent(
        agentId=SUPERVISOR_ID,
        agentAliasId=SUPERVISOR_ALIAS,
        sessionId=session_id,
        inputText=message,
        enableTrace=False
    )
    metrics['invoke_call'] = time.time() - start

    # Phase 3: Stream processing
    start = time.time()
    chunks = []
    chunk_count = 0

    for event in response['completion']:
        chunk_count += 1
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                chunks.append(chunk['bytes'].decode('utf-8'))

    metrics['stream_read'] = time.time() - start
    metrics['chunk_count'] = chunk_count

    # Phase 4: Send to client
    start = time.time()
    full_response = ''.join(chunks)
    # Your client sending logic here
    metrics['client_send'] = time.time() - start

    logger.info(f"Performance Metrics: {metrics}")

    return full_response
```

**Run this and look for:**
- If `client_init` > 100ms → Need connection pooling
- If `stream_read` > 2s → Bedrock API is slow (unlikely)
- If `client_send` > 5s → Frontend/network issue

---

### 2. Check if Backend Has Connection Pooling

Look for module-level Bedrock client:

**❌ BAD (creates new connection each time):**
```python
def invoke_agent(message):
    bedrock = boto3.client('bedrock-agent-runtime')  # NEW CONNECTION
    response = bedrock.invoke_agent(...)
```

**✅ GOOD (reuses connection):**
```python
# Module level (outside function)
bedrock_config = Config(
    max_pool_connections=50,
    tcp_keepalive=True
)
bedrock = boto3.client('bedrock-agent-runtime', config=bedrock_config)

def invoke_agent(message):
    # Reuses existing connection
    response = bedrock.invoke_agent(...)
```

---

### 3. Optimize Streaming Response

**Current (Inefficient):**
```python
async def stream_response():
    for event in response['completion']:
        if 'chunk' in event:
            chunk_text = event['chunk']['bytes'].decode('utf-8')
            yield chunk_text  # Sends each tiny chunk individually
```

**Optimized (Batched):**
```python
async def stream_response():
    buffer = []
    buffer_size = 0
    BATCH_SIZE = 500  # bytes

    for event in response['completion']:
        if 'chunk' in event:
            chunk_text = event['chunk']['bytes'].decode('utf-8')
            buffer.append(chunk_text)
            buffer_size += len(chunk_text)

            # Send batch when threshold reached
            if buffer_size >= BATCH_SIZE:
                yield ''.join(buffer)
                buffer = []
                buffer_size = 0

    # Send remaining
    if buffer:
        yield ''.join(buffer)
```

---

### 4. Enable HTTP/2 for Backend → Bedrock

If your backend supports HTTP/2:

```python
from botocore.config import Config
import urllib3

# Enable HTTP/2
bedrock_config = Config(
    region_name='us-east-1',
    max_pool_connections=50,
    tcp_keepalive=True,
    # HTTP/2 is automatic with newer boto3/botocore
)

bedrock = boto3.client(
    'bedrock-agent-runtime',
    config=bedrock_config
)
```

---

## Quick Fix Implementation

### Option 1: Add Connection Pooling (5 minutes)

**File: your_backend.py**

```python
import boto3
from botocore.config import Config

# ============================================================================
# OPTIMIZATION: Module-level client with connection pooling
# ============================================================================

# Create ONCE at module level (reused across all requests)
bedrock_config = Config(
    region_name='us-east-1',
    retries={'max_attempts': 2, 'mode': 'adaptive'},
    max_pool_connections=50,
    tcp_keepalive=True,
    connect_timeout=5,
    read_timeout=60
)

bedrock_client = boto3.client(
    'bedrock-agent-runtime',
    config=bedrock_config
)

# Now use bedrock_client in all your functions
def invoke_supervisor(message, customer_id):
    response = bedrock_client.invoke_agent(
        agentId="P9VCJXPIZS",
        agentAliasId="TSTALIASID",
        sessionId=f"session-{customer_id}-{int(time.time())}",
        inputText=message,
        enableTrace=False
    )
    return response
```

**Expected improvement: 300-800ms saved per request**

---

### Option 2: Optimize Streaming (10 minutes)

```python
def stream_agent_response(response):
    """Optimized streaming with buffering"""
    buffer = []
    buffer_size = 0
    BATCH_SIZE = 500  # Send every 500 bytes or 3 chunks
    CHUNK_COUNT = 3

    for event in response['completion']:
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                chunk_text = chunk['bytes'].decode('utf-8')
                buffer.append(chunk_text)
                buffer_size += len(chunk_text)

                # Send batch when threshold reached
                if len(buffer) >= CHUNK_COUNT or buffer_size >= BATCH_SIZE:
                    batch = ''.join(buffer)
                    yield batch
                    buffer = []
                    buffer_size = 0

    # Send remaining
    if buffer:
        yield ''.join(buffer)
```

**Expected improvement: 2-4 seconds saved**

---

### Option 3: Reduce Backend Middleware Overhead

If using FastAPI/Flask, check for expensive middleware:

```python
# BAD: Logging every event
@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"Request: {request.url}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")  # Adds latency
    return response

# GOOD: Minimal middleware
@app.middleware("http")
async def log_requests(request, call_next):
    # Only log errors
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"Request failed: {e}")
        raise
```

---

## Expected Performance After Fixes

| Component | Current | After Fix | Improvement |
|-----------|---------|-----------|-------------|
| Agent Processing | 1.06s | 1.06s | No change |
| Backend Init | ~0.5s | ~0.05s | **90% faster** |
| Stream Processing | 9.65s | 2-3s | **70% faster** |
| **Total** | **10.7s** | **3-4s** | **65% faster** |

---

## Testing After Implementation

1. **Add metrics to your backend**
2. **Test with "Hi" message**
3. **Check logs for timing breakdown**
4. **Expected result: 3-4 seconds total**

---

## If Still Slow After Fixes

Check these:

1. **Network latency**: `ping api.bedrock.us-east-1.amazonaws.com`
2. **Backend location**: Is it far from us-east-1?
3. **VPC configuration**: Using PrivateLink or public internet?
4. **Lambda cold starts**: If backend is Lambda, first request will be slow

---

## Next Steps

1. ✅ Add connection pooling (CRITICAL - 5 min)
2. ✅ Optimize streaming buffering (HIGH - 10 min)
3. ✅ Add performance metrics (DIAGNOSTIC - 5 min)
4. ✅ Test with "Hi" message
5. ✅ Verify < 4 seconds total

Once these are done, a simple "Hi" should respond in **3-4 seconds** instead of 10+ seconds.
