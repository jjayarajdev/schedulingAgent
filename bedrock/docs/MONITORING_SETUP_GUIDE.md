# Monitoring & Observability Setup Guide

Complete guide for setting up monitoring, logging, and alerting for the Scheduling Agent system.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [CloudWatch Components](#cloudwatch-components)
- [Metrics & Alarms](#metrics--alarms)
- [Logging](#logging)
- [Dashboards](#dashboards)
- [Alerting](#alerting)
- [Troubleshooting](#troubleshooting)

---

## Overview

The monitoring system provides visibility into:

- **Bedrock Agent Performance** - Invocations, latency, errors
- **Lambda Functions** - Execution, duration, throttles
- **Backend API** - Request/response times, error rates
- **Database** - Connection pool, query performance
- **System Health** - Overall availability and performance

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                     │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Backend    │  │   Lambda     │  │   Bedrock    │  │
│  │     API      │  │  Functions   │  │    Agent     │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                  │                  │          │
└─────────┼──────────────────┼──────────────────┼──────────┘
          │                  │                  │
          │ Structured Logs  │ CloudWatch Logs  │ X-Ray Traces
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼──────────┐
│                 CloudWatch Logs & Metrics                 │
│                                                           │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────┐ │
│  │  Log Groups    │  │  Metric Filters│  │  Custom    │ │
│  │                │  │                │  │  Metrics   │ │
│  └────────┬───────┘  └────────┬───────┘  └──────┬─────┘ │
│           │                   │                  │        │
│           └───────────────────┴──────────────────┘        │
│                              │                            │
└──────────────────────────────┼────────────────────────────┘
                               │
┌──────────────────────────────▼────────────────────────────┐
│                 CloudWatch Alarms & Dashboards            │
│                                                           │
│  ┌─────────────────┐         ┌─────────────────┐        │
│  │  Alarms         │         │  Dashboards     │        │
│  │  • Error Rate   │─────────▶│  • Real-time   │        │
│  │  • Latency      │         │  • Historical  │        │
│  │  • Throttles    │         │  • Logs Query  │        │
│  └────────┬────────┘         └─────────────────┘        │
└───────────┼──────────────────────────────────────────────┘
            │
┌───────────▼──────────────────────────────────────────────┐
│                    SNS Notifications                      │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │    Email     │  │    Slack     │  │  PagerDuty   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└───────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Automated Setup (Recommended)

Run the monitoring setup script:

```bash
cd bedrock/scripts

# Set your email for alerts
export SNS_EMAIL="your-email@example.com"
export AWS_REGION="us-east-1"

# Run setup
./setup_monitoring.sh
```

**What it creates:**
- ✅ CloudWatch Log Groups (9 groups)
- ✅ CloudWatch Dashboard
- ✅ CloudWatch Alarms (5 alarms)
- ✅ SNS Topic for notifications
- ✅ Metric Filters (3 filters)

### Manual Setup

If you prefer manual setup, follow the steps below.

---

## CloudWatch Components

### 1. Log Groups

Create log groups for each component:

```bash
# Backend API logs
aws logs create-log-group \
  --log-group-name /aws/scheduling-agent/backend \
  --region us-east-1

# Lambda function logs
aws logs create-log-group \
  --log-group-name /aws/scheduling-agent/lambda/scheduling-actions \
  --region us-east-1

aws logs create-log-group \
  --log-group-name /aws/scheduling-agent/lambda/information-actions \
  --region us-east-1

aws logs create-log-group \
  --log-group-name /aws/scheduling-agent/lambda/notes-actions \
  --region us-east-1

# Bedrock Agent logs
aws logs create-log-group \
  --log-group-name /aws/scheduling-agent/bedrock-agent/supervisor \
  --region us-east-1
```

**Set retention policy (30 days):**

```bash
aws logs put-retention-policy \
  --log-group-name /aws/scheduling-agent/backend \
  --retention-in-days 30 \
  --region us-east-1
```

### 2. Metric Filters

Extract metrics from logs:

#### Error Count Filter

```bash
aws logs put-metric-filter \
  --log-group-name /aws/scheduling-agent/backend \
  --filter-name scheduling-agent-error-count \
  --filter-pattern '[timestamp, level=ERROR, ...]' \
  --metric-transformations \
    metricName=ErrorCount,metricNamespace=SchedulingAgent,metricValue=1 \
  --region us-east-1
```

#### Response Time Filter

```bash
aws logs put-metric-filter \
  --log-group-name /aws/scheduling-agent/backend \
  --filter-name scheduling-agent-response-time \
  --filter-pattern '[timestamp, level, msg, latency_ms=latency_ms*, ...]' \
  --metric-transformations \
    metricName=ResponseTime,metricNamespace=SchedulingAgent,metricValue='$latency_ms' \
  --region us-east-1
```

#### Success Count Filter

```bash
aws logs put-metric-filter \
  --log-group-name /aws/scheduling-agent/backend \
  --filter-name scheduling-agent-success-count \
  --filter-pattern '[timestamp, level=INFO, msg="chat_response_sent", ...]' \
  --metric-transformations \
    metricName=SuccessCount,metricNamespace=SchedulingAgent,metricValue=1 \
  --region us-east-1
```

### 3. Custom Metrics

Publish custom application metrics:

**Create `publish_metrics.py`:**

```python
#!/usr/bin/env python3
import boto3
from datetime import datetime
from sqlalchemy import create_engine, text

cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
engine = create_engine('postgresql://...')  # Your DB URL

def publish_metrics():
    # Get metrics from database
    with engine.connect() as conn:
        # Active sessions
        active_sessions = conn.execute(
            text("SELECT COUNT(*) FROM sessions WHERE status='active'")
        ).scalar()

        # Total messages today
        total_messages = conn.execute(
            text("SELECT COUNT(*) FROM messages WHERE DATE(created_at) = CURRENT_DATE")
        ).scalar()

        # Appointments created today
        appointments_today = conn.execute(
            text("SELECT COUNT(*) FROM appointments WHERE DATE(created_at) = CURRENT_DATE")
        ).scalar()

    # Publish to CloudWatch
    cloudwatch.put_metric_data(
        Namespace='SchedulingAgent',
        MetricData=[
            {
                'MetricName': 'ActiveSessions',
                'Value': active_sessions,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            },
            {
                'MetricName': 'TotalMessages',
                'Value': total_messages,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            },
            {
                'MetricName': 'AppointmentsCreated',
                'Value': appointments_today,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            }
        ]
    )

if __name__ == '__main__':
    publish_metrics()
```

**Schedule with cron:**

```bash
# Run every 5 minutes
*/5 * * * * /usr/bin/python3 /path/to/publish_metrics.py
```

---

## Metrics & Alarms

### Key Metrics to Monitor

#### Bedrock Agent Metrics

| Metric | Namespace | Description | Threshold |
|--------|-----------|-------------|-----------|
| `Invocations` | AWS/Bedrock | Total agent invocations | - |
| `Errors` | AWS/Bedrock | Failed invocations | > 10 per 5min |
| `Throttles` | AWS/Bedrock | Rate limit hits | > 5 per 5min |
| `InvocationLatency` | AWS/Bedrock | Response time (ms) | > 5000ms (p99) |

#### Lambda Metrics

| Metric | Namespace | Description | Threshold |
|--------|-----------|-------------|-----------|
| `Invocations` | AWS/Lambda | Function invocations | - |
| `Errors` | AWS/Lambda | Function errors | > 5 per 5min |
| `Throttles` | AWS/Lambda | Concurrent limit hits | > 1 per 5min |
| `Duration` | AWS/Lambda | Execution time (ms) | > 25000ms |
| `ConcurrentExecutions` | AWS/Lambda | Concurrent runs | > 800 |

#### Custom Application Metrics

| Metric | Namespace | Description | Threshold |
|--------|-----------|-------------|-----------|
| `ErrorCount` | SchedulingAgent | Application errors | > 10 per 5min |
| `ResponseTime` | SchedulingAgent | API response time | > 3000ms (avg) |
| `SuccessCount` | SchedulingAgent | Successful requests | - |
| `ActiveSessions` | SchedulingAgent | Active user sessions | > 1000 |
| `AppointmentsCreated` | SchedulingAgent | Daily appointments | - |

### Creating Alarms

#### 1. High Error Rate Alarm

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name scheduling-agent-high-error-rate \
  --alarm-description "Alert when error rate exceeds threshold" \
  --namespace AWS/Bedrock \
  --metric-name Errors \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:scheduling-agent-alarms \
  --region us-east-1
```

#### 2. High Latency Alarm

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name scheduling-agent-high-latency \
  --alarm-description "Alert when latency exceeds 5 seconds" \
  --namespace AWS/Bedrock \
  --metric-name InvocationLatency \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 5000 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:scheduling-agent-alarms \
  --region us-east-1
```

#### 3. Lambda Errors Alarm

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name scheduling-agent-lambda-errors \
  --alarm-description "Alert when Lambda functions have errors" \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:scheduling-agent-alarms \
  --region us-east-1
```

#### 4. Lambda Throttles Alarm

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name scheduling-agent-lambda-throttles \
  --alarm-description "Alert when Lambda functions are throttled" \
  --namespace AWS/Lambda \
  --metric-name Throttles \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:scheduling-agent-alarms \
  --region us-east-1
```

#### 5. Database Connections Alarm

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name scheduling-agent-db-connections-high \
  --alarm-description "Alert when database connections are high" \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:scheduling-agent-alarms \
  --region us-east-1
```

---

## Logging

### Log Format

The backend uses structured JSON logging:

```json
{
  "timestamp": "2025-10-17T12:00:00.123Z",
  "level": "INFO",
  "logger": "app.api.chat",
  "message": "chat_response_sent",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "response_length": 150,
  "processing_time_ms": 850,
  "customer_id": "1645975"
}
```

### Log Queries

#### 1. Find Recent Errors

```
fields @timestamp, level, message, error
| filter level = "ERROR"
| sort @timestamp desc
| limit 100
```

#### 2. Calculate Average Response Time

```
fields latency_ms
| filter message = "chat_response_sent"
| stats avg(latency_ms) as avg_latency, max(latency_ms) as max_latency, min(latency_ms) as min_latency
```

#### 3. Count Requests by Session

```
fields session_id
| filter message = "chat_request_received"
| stats count() by session_id
| sort count desc
| limit 20
```

#### 4. Find Slow Requests

```
fields @timestamp, session_id, latency_ms
| filter message = "chat_response_sent" and latency_ms > 3000
| sort latency_ms desc
| limit 50
```

#### 5. Error Distribution by Type

```
fields error_type
| filter level = "ERROR"
| stats count() by error_type
| sort count desc
```

### Log Insights Queries

Save these as CloudWatch Insights saved queries:

```bash
# Save query
aws logs put-query-definition \
  --name "Slow Requests" \
  --query-string "fields @timestamp, session_id, latency_ms | filter message = 'chat_response_sent' and latency_ms > 3000 | sort latency_ms desc | limit 50" \
  --log-group-names /aws/scheduling-agent/backend \
  --region us-east-1
```

---

## Dashboards

### CloudWatch Dashboard

Create a comprehensive dashboard:

**Dashboard JSON:**

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "title": "Bedrock Agent - Invocations & Errors",
        "metrics": [
          ["AWS/Bedrock", "Invocations", {"stat": "Sum", "color": "#2ca02c"}],
          [".", "Errors", {"stat": "Sum", "color": "#d62728"}],
          [".", "Throttles", {"stat": "Sum", "color": "#ff7f0e"}]
        ],
        "period": 300,
        "region": "us-east-1",
        "yAxis": {
          "left": {"min": 0}
        }
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Bedrock Agent - Latency (ms)",
        "metrics": [
          ["AWS/Bedrock", "InvocationLatency", {"stat": "Average", "color": "#1f77b4"}],
          ["...", {"stat": "p99", "color": "#ff7f0e"}]
        ],
        "period": 300,
        "region": "us-east-1",
        "yAxis": {
          "left": {"min": 0, "label": "Milliseconds"}
        }
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Lambda Functions - Overview",
        "metrics": [
          ["AWS/Lambda", "Invocations", {"stat": "Sum"}],
          [".", "Errors", {"stat": "Sum"}],
          [".", "Throttles", {"stat": "Sum"}],
          [".", "ConcurrentExecutions", {"stat": "Maximum"}]
        ],
        "period": 300,
        "region": "us-east-1"
      }
    },
    {
      "type": "log",
      "properties": {
        "title": "Recent Errors",
        "query": "SOURCE '/aws/scheduling-agent/backend'\n| fields @timestamp, level, message, error\n| filter level = 'ERROR'\n| sort @timestamp desc\n| limit 20",
        "region": "us-east-1"
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Custom - Active Sessions",
        "metrics": [
          ["SchedulingAgent", "ActiveSessions", {"stat": "Average"}]
        ],
        "period": 300,
        "region": "us-east-1"
      }
    }
  ]
}
```

**Create dashboard:**

```bash
aws cloudwatch put-dashboard \
  --dashboard-name scheduling-agent-dashboard \
  --dashboard-body file://dashboard.json \
  --region us-east-1
```

**View dashboard:**
```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=scheduling-agent-dashboard
```

---

## Alerting

### SNS Topic Setup

#### 1. Create SNS Topic

```bash
aws sns create-topic \
  --name scheduling-agent-alarms \
  --region us-east-1
```

#### 2. Subscribe Email

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:scheduling-agent-alarms \
  --protocol email \
  --notification-endpoint your-email@example.com \
  --region us-east-1
```

#### 3. Subscribe Slack (via Lambda)

Create Lambda function to forward to Slack:

```python
import json
import urllib3

http = urllib3.PoolManager()

def lambda_handler(event, context):
    message = json.loads(event['Records'][0]['Sns']['Message'])

    slack_message = {
        'text': f"🚨 CloudWatch Alarm: {message['AlarmName']}",
        'attachments': [{
            'color': 'danger',
            'fields': [
                {'title': 'Description', 'value': message['AlarmDescription'], 'short': False},
                {'title': 'State', 'value': message['NewStateValue'], 'short': True},
                {'title': 'Reason', 'value': message['NewStateReason'], 'short': False}
            ]
        }]
    }

    http.request(
        'POST',
        'https://hooks.slack.com/services/YOUR/WEBHOOK/URL',
        body=json.dumps(slack_message),
        headers={'Content-Type': 'application/json'}
    )

    return {'statusCode': 200}
```

#### 4. Subscribe PagerDuty

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:scheduling-agent-alarms \
  --protocol email \
  --notification-endpoint your-integration@pagerduty.com \
  --region us-east-1
```

### Alarm Actions

Configure alarm actions for different severities:

**Critical (P1):**
- Send to PagerDuty (on-call engineer)
- Send to Slack (#alerts channel)
- Send email to ops team

**Warning (P2):**
- Send to Slack (#monitoring channel)
- Send email to dev team

**Info (P3):**
- Log only
- Daily digest email

---

## Troubleshooting

### Issue: Logs not appearing

**Cause:** Log group doesn't exist or incorrect permissions

**Solution:**

1. Check log group exists:
   ```bash
   aws logs describe-log-groups --region us-east-1
   ```

2. Verify IAM permissions:
   ```bash
   aws iam get-role-policy \
     --role-name your-lambda-role \
     --policy-name CloudWatchLogsPolicy
   ```

3. Test logging manually:
   ```bash
   aws logs create-log-stream \
     --log-group-name /aws/scheduling-agent/backend \
     --log-stream-name test-stream

   aws logs put-log-events \
     --log-group-name /aws/scheduling-agent/backend \
     --log-stream-name test-stream \
     --log-events timestamp=$(date +%s%3N),message="Test log"
   ```

### Issue: Alarms not triggering

**Cause:** Incorrect metric query or threshold

**Solution:**

1. Test metric query:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Bedrock \
     --metric-name Errors \
     --start-time 2025-10-17T00:00:00Z \
     --end-time 2025-10-17T23:59:59Z \
     --period 300 \
     --statistics Sum \
     --region us-east-1
   ```

2. Manually trigger alarm for testing:
   ```bash
   aws cloudwatch set-alarm-state \
     --alarm-name scheduling-agent-high-error-rate \
     --state-value ALARM \
     --state-reason "Testing alarm notification" \
     --region us-east-1
   ```

### Issue: High CloudWatch costs

**Cause:** Too many custom metrics or long log retention

**Solution:**

1. Reduce log retention:
   ```bash
   aws logs put-retention-policy \
     --log-group-name /aws/scheduling-agent/backend \
     --retention-in-days 7 \
     --region us-east-1
   ```

2. Use sampling for metrics:
   - Publish every 5 minutes instead of every minute
   - Use percentile statistics instead of full distributions

3. Filter logs before ingestion:
   - Don't log debug messages in production
   - Use subscription filters to route only errors to long-term storage

---

## Best Practices

1. **Use structured logging** - JSON format for easier querying
2. **Set appropriate log retention** - 7-30 days for most cases
3. **Create composite alarms** - Combine multiple metrics
4. **Use anomaly detection** - For dynamic thresholds
5. **Tag all resources** - For cost allocation and filtering
6. **Document runbooks** - Link to docs in alarm descriptions
7. **Test alarms regularly** - Monthly alarm testing schedule
8. **Review metrics weekly** - Adjust thresholds as needed

---

## Next Steps

- [ ] Set up AWS X-Ray for distributed tracing
- [ ] Configure CloudWatch Synthetics for uptime monitoring
- [ ] Implement application performance monitoring (APM)
- [ ] Create runbooks for common incidents
- [ ] Set up log archival to S3 Glacier
- [ ] Implement cost optimization for CloudWatch

---

## Resources

- [CloudWatch Logs Insights Query Syntax](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html)
- [CloudWatch Alarms Best Practices](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Best_Practice_Recommended_Alarms_AWS_Services.html)
- [AWS X-Ray Developer Guide](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html)
