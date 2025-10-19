# Load Testing Suite - AWS Bedrock Multi-Agent System

Comprehensive performance and load testing for the AWS Bedrock scheduling agent using Locust.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Test Files](#test-files)
5. [Running Load Tests](#running-load-tests)
6. [Test Scenarios](#test-scenarios)
7. [Distributed Testing](#distributed-testing)
8. [Monitoring](#monitoring)
9. [Analyzing Results](#analyzing-results)
10. [Performance Targets](#performance-targets)
11. [Troubleshooting](#troubleshooting)

---

## 📌 Overview

This load testing suite provides comprehensive performance testing for:
- **Bedrock Agent Routing:** Supervisor → Collaborator routing accuracy
- **Lambda Functions:** Bulk operations and scheduling actions
- **Multi-Turn Conversations:** Session management and context preservation
- **Performance Metrics:** Response times, throughput, error rates

### Why Locust?
- ✅ Python-based (matches project stack)
- ✅ Distributed load generation
- ✅ Real-time web UI monitoring
- ✅ Flexible scenario customization
- ✅ AWS service friendly

---

## 🚀 Installation

### Method 1: Using UV (Recommended)

```bash
# Navigate to backend directory
cd bedrock/backend

# Sync all dependencies including dev group (contains locust)
uv sync --group dev

# Verify installation
uv run locust --version
```

### Method 2: Using pip

```bash
# Install from requirements.txt
cd bedrock/backend
pip install -r requirements.txt

# Or install specific packages
pip install locust>=2.32.0 pyzmq>=26.2.0 gevent>=24.11.1

# Verify installation
locust --version
```

### Method 3: Install in Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r bedrock/backend/requirements.txt

# Verify
locust --version
```

---

## ⚡ Quick Start

### 1. Basic Agent Load Test (Web UI)

```bash
# Navigate to LoadTest directory
cd bedrock/tests/LoadTest

# Start Locust with web UI
locust -f locustfile.py

# Open browser to http://localhost:8089
# Set: Users=10, Spawn rate=1
# Click "Start swarming"
```

### 2. Quick Headless Test (5 minutes)

```bash
cd bedrock/tests/LoadTest

# Run 50 users for 5 minutes with HTML report
locust -f locustfile.py --headless \
  -u 50 -r 5 -t 5m \
  --html report.html
```

### 3. Lambda Function Test

```bash
cd bedrock/tests/LoadTest

# Test bulk operations Lambda
locust -f lambda_loadtest.py --headless \
  -u 20 -r 2 -t 5m \
  --html lambda_report.html
```

---

## 📂 Test Files

### Structure

```
bedrock/tests/LoadTest/
├── __init__.py                 # Package initialization
├── config.py                   # Configuration & constants
├── utils.py                    # Helper functions
├── locustfile.py              # Main agent load test
├── lambda_loadtest.py         # Lambda function load test
└── README.md                   # This file
```

### File Descriptions

**`config.py`**
- Agent IDs and aliases
- Lambda function names
- Test message templates
- Performance targets
- Load profiles

**`utils.py`**
- AWS Bedrock invoke helper
- AWS Lambda invoke helper
- CloudWatch metrics fetcher
- Response validation
- Cost estimation

**`locustfile.py`**
- Bedrock agent load tests
- Routing accuracy tests
- Multi-turn conversations
- Custom metrics tracking

**`lambda_loadtest.py`**
- Bulk operations testing
- Scheduling actions testing
- Lambda performance metrics

---

## 🏃 Running Load Tests

### Test Parameters

```bash
locust -f <file> [OPTIONS]

Options:
  -u, --users <number>         Number of concurrent users
  -r, --spawn-rate <number>    Users spawned per second
  -t, --run-time <time>        Test duration (e.g., 5m, 1h)
  --headless                   Run without web UI
  --html <file>                Generate HTML report
  --csv <prefix>               Generate CSV stats
  --only-summary               Only print summary stats
  --stop-timeout <seconds>     Wait time for graceful shutdown
```

### Common Test Scenarios

#### Scenario 1: Smoke Test (1 user, 1 minute)

```bash
cd bedrock/tests/LoadTest

locust -f locustfile.py --headless \
  -u 1 -r 1 -t 1m \
  --only-summary
```

**Purpose:** Quick validation that everything works

#### Scenario 2: Light Load (10 users, 5 minutes)

```bash
locust -f locustfile.py --headless \
  -u 10 -r 1 -t 5m \
  --html light_load_report.html \
  --csv light_load_stats
```

**Purpose:** Baseline performance measurement

#### Scenario 3: Medium Load (50 users, 10 minutes)

```bash
locust -f locustfile.py --headless \
  -u 50 -r 5 -t 10m \
  --html medium_load_report.html
```

**Purpose:** Realistic production load

#### Scenario 4: Heavy Load (100 users, 30 minutes)

```bash
locust -f locustfile.py --headless \
  -u 100 -r 10 -t 30m \
  --html heavy_load_report.html
```

**Purpose:** Peak traffic simulation

#### Scenario 5: Stress Test (500 users, 1 hour)

```bash
locust -f locustfile.py --headless \
  -u 500 -r 50 -t 1h \
  --html stress_test_report.html \
  --csv stress_test_stats
```

**Purpose:** Find breaking point and limits

#### Scenario 6: Spike Test (instant load)

```bash
locust -f locustfile.py --headless \
  -u 200 -r 200 -t 5m \
  --html spike_test_report.html
```

**Purpose:** Test recovery from sudden traffic spike

---

## 🎯 Test Scenarios

### Agent Load Tests (locustfile.py)

**1. BedrockAgentUser (General User)**
- 30% chitchat messages
- 50% scheduling requests
- 10% information queries
- 10% notes requests
- Wait 1-5 seconds between requests

**2. MultiTurnConversationUser**
- Executes complete 5-turn conversation
- Tests session persistence
- Validates routing across turns

**3. SchedulingFocusedUser**
- 80% scheduling requests
- 20% other requests
- Simulates heavy scheduling load

### Lambda Load Tests (lambda_loadtest.py)

**1. BulkOperationsUser**
- 40% route optimization
- 30% bulk team assignment
- 20% project validation
- 10% conflict detection

**2. MixedLambdaUser**
- 70% bulk operations
- 30% scheduling actions

---

## 🌐 Distributed Testing

For large-scale tests (1000+ users), use distributed mode.

### Setup Master Node

```bash
cd bedrock/tests/LoadTest

# Start master (web UI on port 8089)
locust -f locustfile.py --master
```

### Setup Worker Nodes

On each worker machine:

```bash
cd bedrock/tests/LoadTest

# Connect to master
locust -f locustfile.py --worker --master-host=<master-ip>
```

### Example: 3-Node Distributed Test

**Machine 1 (Master):**
```bash
locust -f locustfile.py --master
```

**Machine 2 (Worker):**
```bash
locust -f locustfile.py --worker --master-host=192.168.1.100
```

**Machine 3 (Worker):**
```bash
locust -f locustfile.py --worker --master-host=192.168.1.100
```

Then open http://192.168.1.100:8089 and set users=1000, spawn rate=50.

### AWS Deployment (Advanced)

Deploy Locust to AWS ECS/Fargate for massive scale:

```bash
# 1 master + 10 workers = 10,000+ concurrent users
# See AWS ECS Locust deployment guides
```

---

## 📊 Monitoring

### Real-Time Monitoring (Web UI)

When running with web UI (default), open http://localhost:8089

**Charts Available:**
- Total Requests per Second
- Response Times (median, 95th percentile)
- Number of Users
- Failures per Second

### CloudWatch Metrics

Monitor AWS services during load tests:

```bash
# Bedrock agent invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Invocations \
  --dimensions Name=AgentId,Value=5VTIWONUMO \
  --start-time 2025-10-16T10:00:00Z \
  --end-time 2025-10-16T11:00:00Z \
  --period 60 \
  --statistics Sum,Average

# Lambda concurrent executions
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name ConcurrentExecutions \
  --dimensions Name=FunctionName,Value=scheduling-agent-bulk-ops-dev \
  --start-time 2025-10-16T10:00:00Z \
  --end-time 2025-10-16T11:00:00Z \
  --period 60 \
  --statistics Maximum,Average

# Lambda duration
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=scheduling-agent-bulk-ops-dev \
  --start-time 2025-10-16T10:00:00Z \
  --end-time 2025-10-16T11:00:00Z \
  --period 60 \
  --statistics Average,p95,p99
```

### Cost Tracking During Tests

Monitor costs in real-time:

```bash
# From Python (in utils.py)
from utils import estimate_test_cost

# Estimate cost for 10,000 invocations
cost = estimate_test_cost(num_invocations=10000)
print(f"Estimated cost: ${cost['total_cost_usd']}")
```

---

## 📈 Analyzing Results

### HTML Report

After test with `--html report.html`:

```
Open: report.html in browser

Sections:
1. Statistics - Response times, RPS, failures
2. Charts - Visual graphs of performance
3. Exceptions - Error details
4. Download Data - CSV export
```

### CSV Stats

After test with `--csv stats`:

```
Generated files:
- stats_stats.csv        # Request statistics
- stats_stats_history.csv # Time-series data
- stats_failures.csv     # Failure details
```

### Command-Line Summary

With `--only-summary`:

```
 Name                          # reqs  # fails  Avg    Min    Max    Median  p95    p99   RPS
-------------------------------------------------------------------------------
 bedrock_agent:chitchat         1500      0    2145    987   5432    2100   3200   4500  5.0
 bedrock_agent:scheduling       2500      5    2567   1100   8900    2400   4100   6200  8.3
 bedrock_agent:information       500      0    1987    890   4200    1950   2800   3500  1.7
 bedrock_agent:notes             500      1    2100    950   4800    2050   3000   3900  1.7
-------------------------------------------------------------------------------
 Total                          5000      6    2300    890   8900    2200   3800   5500 16.7

Routing Accuracy: 99.4%
```

### Key Metrics to Check

**1. Response Times**
- ✅ P50 < 2s
- ✅ P95 < 5s
- ✅ P99 < 10s

**2. Error Rate**
- ✅ < 1% failures

**3. Throughput**
- ✅ > 100 RPS (for agents)
- ✅ > 500 RPS (for Lambda)

**4. Routing Accuracy**
- ✅ > 95% correct routing

**5. Lambda Metrics**
- ✅ No throttling errors
- ✅ Concurrent executions < account limit
- ✅ Duration within expectations

---

## 🎯 Performance Targets

### Bedrock Agents

| Metric | Target | Notes |
|--------|--------|-------|
| P50 latency | < 2s | Median response time |
| P95 latency | < 5s | 95th percentile |
| P99 latency | < 10s | 99th percentile |
| Error rate | < 1% | Failed requests |
| Throughput | 100 RPS | Requests per second |
| Routing accuracy | > 95% | Correct collaborator selection |

### Lambda Functions

| Metric | Target | Notes |
|--------|--------|-------|
| P50 latency | < 1s | Median execution time |
| P95 latency | < 3s | 95th percentile |
| P99 latency | < 5s | 99th percentile |
| Error rate | < 0.5% | Failed invocations |
| Throughput | 500 RPS | Invocations per second |
| Cold start | < 2s | First invocation |

### Cost Estimates

**Agent Invocations (Claude Sonnet 4.5):**
- Input: $3 per 1M tokens
- Output: $15 per 1M tokens
- Avg cost per invocation: ~$0.01 (200 input + 500 output tokens)

**10,000 invocation load test:** ~$100

---

## 🔧 Troubleshooting

### Issue 1: Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'locust'
```

**Solution:**
```bash
# Install dependencies
cd bedrock/backend
uv sync --group dev

# Or
pip install -r requirements.txt
```

### Issue 2: AWS Credentials Not Found

**Error:**
```
NoCredentialsError: Unable to locate credentials
```

**Solution:**
```bash
# Configure AWS credentials
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=<your-key>
export AWS_SECRET_ACCESS_KEY=<your-secret>
export AWS_REGION=us-east-1
```

### Issue 3: Agent Access Denied

**Error:**
```
Access denied when calling Bedrock
```

**Solution:**
```bash
# Check IAM permissions
# Ensure you have:
# - bedrock:InvokeAgent
# - bedrock:InvokeModel

# Or use a role with sufficient permissions
```

### Issue 4: Lambda Not Found

**Error:**
```
Function not found: scheduling-actions-dev
```

**Solution:**
```python
# Edit config.py and comment out non-deployed Lambda functions
LAMBDA_FUNCTIONS = {
    "bulk_ops": "scheduling-agent-bulk-ops-dev",
    # "scheduling": "scheduling-actions-dev",  # Not deployed yet
}
```

### Issue 5: High Error Rate

**Symptoms:** > 10% failures

**Solutions:**
1. Reduce spawn rate (`-r 1` instead of `-r 10`)
2. Add delays between requests (increase wait_time)
3. Check AWS service limits
4. Monitor CloudWatch for throttling

### Issue 6: Locust Web UI Not Opening

**Error:**
```
Connection refused on localhost:8089
```

**Solution:**
```bash
# Check if port is already in use
netstat -an | grep 8089

# Use different port
locust -f locustfile.py --web-port 8090
```

---

## 📚 Advanced Usage

### Custom Test Scenarios

Create custom scenario file:

```python
# custom_scenario.py

from locust import HttpUser, task, between
from utils import invoke_bedrock_agent
from config import SUPERVISOR_AGENT_ID, SUPERVISOR_ALIAS_ID

class CustomUser(HttpUser):
    wait_time = between(2, 5)

    @task
    def my_custom_test(self):
        # Your custom test logic
        pass
```

Run:
```bash
locust -f custom_scenario.py
```

### Environment Variables

```bash
# Override configuration via environment
export AWS_REGION=us-west-2
export SUPERVISOR_AGENT_ID=YOUR_AGENT_ID
export SUPERVISOR_ALIAS_ID=YOUR_ALIAS_ID

locust -f locustfile.py
```

### Integration with CI/CD

```yaml
# .github/workflows/load-test.yml

name: Load Test

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: pip install -r bedrock/backend/requirements.txt
      - name: Run load test
        run: |
          cd bedrock/tests/LoadTest
          locust -f locustfile.py --headless -u 50 -r 5 -t 5m --html report.html
      - name: Upload report
        uses: actions/upload-artifact@v3
        with:
          name: load-test-report
          path: bedrock/tests/LoadTest/report.html
```

---

## 📝 Best Practices

1. **Start Small:** Begin with 1-10 users to validate setup
2. **Gradual Ramp:** Increase load gradually (spawn rate 1-5)
3. **Monitor Costs:** Track AWS costs during tests
4. **Set Timeouts:** Use `-t` to prevent runaway tests
5. **Save Reports:** Always generate HTML reports for analysis
6. **Baseline First:** Establish baseline before optimization
7. **Test in Non-Prod:** Never run large tests in production
8. **Clean Up:** Review CloudWatch logs after tests

---

## 🔗 Related Documentation

- **Main Project README:** [bedrock/README.md](../../README.md)
- **CONTEXT.md:** [Full project context](../../../CONTEXT.md)
- **Testing Guide:** [bedrock/docs/TESTING_GUIDE.md](../../docs/TESTING_GUIDE.md)
- **Locust Official Docs:** https://docs.locust.io/

---

## 📞 Support

**Issues:**
- Check [Troubleshooting](#troubleshooting) section
- Review CloudWatch logs
- Check AWS service quotas

**Questions:**
- Refer to CONTEXT.md for project overview
- Check Locust documentation for tool-specific questions

---

**Last Updated:** October 16, 2025
**Version:** 1.0.0
**Status:** Ready for use
