# Load Testing Quick Start Guide

**Fast reference for running load tests - no manual reading required!**

---

## 🚀 Install

```bash
# Option 1: UV (recommended)
cd bedrock/backend
uv sync --group dev

# Option 2: pip
pip install -r requirements.txt
```

---

## ⚡ Run Tests

### 1. Agent Test (Web UI)
```bash
cd bedrock/tests/LoadTest
locust -f locustfile.py
# Open http://localhost:8089
```

### 2. Agent Test (Headless - 5 min)
```bash
cd bedrock/tests/LoadTest
locust -f locustfile.py --headless -u 50 -r 5 -t 5m --html report.html
```

### 3. Lambda Test
```bash
cd bedrock/tests/LoadTest
locust -f lambda_loadtest.py --headless -u 20 -r 2 -t 5m --html lambda_report.html
```

### 4. Stress Test
```bash
cd bedrock/tests/LoadTest
locust -f locustfile.py --headless -u 500 -r 50 -t 30m --html stress_report.html
```

---

## 📊 Common Commands

```bash
# Smoke test (1 user, 1 min)
locust -f locustfile.py --headless -u 1 -r 1 -t 1m --only-summary

# Light load (10 users, 5 min)
locust -f locustfile.py --headless -u 10 -r 1 -t 5m --html light.html

# Medium load (50 users, 10 min)
locust -f locustfile.py --headless -u 50 -r 5 -t 10m --html medium.html

# Heavy load (100 users, 30 min)
locust -f locustfile.py --headless -u 100 -r 10 -t 30m --html heavy.html

# Spike test (instant 200 users)
locust -f locustfile.py --headless -u 200 -r 200 -t 5m --html spike.html
```

---

## 🎯 Performance Targets

| Metric | Target |
|--------|--------|
| P50 latency | < 2s |
| P95 latency | < 5s |
| Error rate | < 1% |
| Throughput | > 100 RPS |
| Routing accuracy | > 95% |

---

## 🔧 Quick Fixes

**Import Error:**
```bash
cd bedrock/backend && uv sync --group dev
```

**AWS Credentials:**
```bash
aws configure
```

**Lambda Not Found:**
```python
# Edit config.py, comment out non-deployed functions
```

---

## 📁 Files

- `locustfile.py` - Bedrock agent load test
- `lambda_loadtest.py` - Lambda function load test
- `config.py` - Configuration
- `utils.py` - Helper functions
- `README.md` - Full documentation

---

## 📖 Full Docs

See [README.md](README.md) for complete documentation.

---

**Generated:** October 16, 2025
