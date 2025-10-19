#!/bin/bash

################################################################################
# Monitoring & Alarms Setup Script
#
# This script sets up comprehensive monitoring for the Scheduling Agent:
# - CloudWatch Log Groups
# - CloudWatch Dashboards
# - CloudWatch Alarms
# - SNS Topics for notifications
#
# Usage: ./setup_monitoring.sh
#
# Prerequisites:
# - AWS CLI configured
# - Appropriate IAM permissions
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Monitoring & Alarms Setup${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="scheduling-agent"
SNS_EMAIL="${SNS_EMAIL:-your-email@example.com}"

echo -e "${YELLOW}Configuration:${NC}"
echo "  AWS Region: $AWS_REGION"
echo "  Project: $PROJECT_NAME"
echo "  Email: $SNS_EMAIL"
echo ""

################################################################################
# Step 1: Create SNS Topic for Alarms
################################################################################

echo -e "${YELLOW}Step 1: Creating SNS Topic for Alarms...${NC}"

SNS_TOPIC_ARN=$(aws sns create-topic \
  --name "${PROJECT_NAME}-alarms" \
  --region "$AWS_REGION" \
  --output text \
  --query 'TopicArn' 2>/dev/null || echo "")

if [ -z "$SNS_TOPIC_ARN" ]; then
  # Topic might already exist, get ARN
  SNS_TOPIC_ARN=$(aws sns list-topics \
    --region "$AWS_REGION" \
    --output text \
    --query "Topics[?contains(TopicArn, '${PROJECT_NAME}-alarms')].TopicArn | [0]")
fi

echo -e "${GREEN}✓ SNS Topic: $SNS_TOPIC_ARN${NC}"

# Subscribe email to SNS topic
echo "  Subscribing email: $SNS_EMAIL"
aws sns subscribe \
  --topic-arn "$SNS_TOPIC_ARN" \
  --protocol email \
  --notification-endpoint "$SNS_EMAIL" \
  --region "$AWS_REGION" \
  > /dev/null 2>&1 || true

echo -e "${YELLOW}  ⚠ Check your email to confirm SNS subscription${NC}"
echo ""

################################################################################
# Step 2: Create Log Groups
################################################################################

echo -e "${YELLOW}Step 2: Creating CloudWatch Log Groups...${NC}"

# Log groups to create
LOG_GROUPS=(
  "/aws/${PROJECT_NAME}/backend"
  "/aws/${PROJECT_NAME}/lambda/scheduling-actions"
  "/aws/${PROJECT_NAME}/lambda/information-actions"
  "/aws/${PROJECT_NAME}/lambda/notes-actions"
  "/aws/${PROJECT_NAME}/bedrock-agent/supervisor"
  "/aws/${PROJECT_NAME}/bedrock-agent/scheduling"
  "/aws/${PROJECT_NAME}/bedrock-agent/information"
  "/aws/${PROJECT_NAME}/bedrock-agent/notes"
  "/aws/${PROJECT_NAME}/bedrock-agent/chitchat"
)

for LOG_GROUP in "${LOG_GROUPS[@]}"; do
  aws logs create-log-group \
    --log-group-name "$LOG_GROUP" \
    --region "$AWS_REGION" \
    > /dev/null 2>&1 || true

  # Set retention to 30 days
  aws logs put-retention-policy \
    --log-group-name "$LOG_GROUP" \
    --retention-in-days 30 \
    --region "$AWS_REGION" \
    > /dev/null 2>&1 || true

  echo -e "${GREEN}  ✓ $LOG_GROUP${NC}"
done

echo ""

################################################################################
# Step 3: Create CloudWatch Dashboard
################################################################################

echo -e "${YELLOW}Step 3: Creating CloudWatch Dashboard...${NC}"

# Dashboard configuration
cat > /tmp/dashboard-config.json << 'EOF'
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Bedrock", "Invocations", {"stat": "Sum"}],
          [".", "Errors", {"stat": "Sum"}],
          [".", "Throttles", {"stat": "Sum"}]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "us-east-1",
        "title": "Bedrock Agent - Invocations",
        "yAxis": {
          "left": {
            "min": 0
          }
        }
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Bedrock", "InvocationLatency", {"stat": "Average"}],
          ["...", {"stat": "p99"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Bedrock Agent - Latency",
        "yAxis": {
          "left": {
            "min": 0,
            "label": "ms"
          }
        }
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lambda", "Invocations", {"stat": "Sum"}],
          [".", "Errors", {"stat": "Sum"}],
          [".", "Throttles", {"stat": "Sum"}],
          [".", "ConcurrentExecutions", {"stat": "Maximum"}]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "us-east-1",
        "title": "Lambda Functions - Overview"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lambda", "Duration", {"stat": "Average"}],
          ["...", {"stat": "p99"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Lambda Functions - Duration"
      }
    },
    {
      "type": "log",
      "properties": {
        "query": "SOURCE '/aws/scheduling-agent/backend'\n| fields @timestamp, level, message\n| filter level = 'ERROR'\n| sort @timestamp desc\n| limit 20",
        "region": "us-east-1",
        "title": "Recent Errors",
        "stacked": false
      }
    },
    {
      "type": "log",
      "properties": {
        "query": "SOURCE '/aws/scheduling-agent/backend'\n| stats count() by level\n| sort count desc",
        "region": "us-east-1",
        "title": "Log Levels Distribution",
        "stacked": false
      }
    }
  ]
}
EOF

aws cloudwatch put-dashboard \
  --dashboard-name "${PROJECT_NAME}-dashboard" \
  --dashboard-body file:///tmp/dashboard-config.json \
  --region "$AWS_REGION" \
  > /dev/null

echo -e "${GREEN}✓ Dashboard created: ${PROJECT_NAME}-dashboard${NC}"
echo -e "${BLUE}  View at: https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#dashboards:name=${PROJECT_NAME}-dashboard${NC}"
echo ""

################################################################################
# Step 4: Create CloudWatch Alarms
################################################################################

echo -e "${YELLOW}Step 4: Creating CloudWatch Alarms...${NC}"

# Alarm 1: High error rate
echo "  Creating alarm: High Error Rate"
aws cloudwatch put-metric-alarm \
  --alarm-name "${PROJECT_NAME}-high-error-rate" \
  --alarm-description "Alert when error rate exceeds threshold" \
  --namespace "AWS/Bedrock" \
  --metric-name "Errors" \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --region "$AWS_REGION" \
  > /dev/null

echo -e "${GREEN}    ✓ High Error Rate alarm created${NC}"

# Alarm 2: High latency
echo "  Creating alarm: High Latency"
aws cloudwatch put-metric-alarm \
  --alarm-name "${PROJECT_NAME}-high-latency" \
  --alarm-description "Alert when latency exceeds 5 seconds" \
  --namespace "AWS/Bedrock" \
  --metric-name "InvocationLatency" \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 5000 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --region "$AWS_REGION" \
  > /dev/null

echo -e "${GREEN}    ✓ High Latency alarm created${NC}"

# Alarm 3: Lambda errors
echo "  Creating alarm: Lambda Errors"
aws cloudwatch put-metric-alarm \
  --alarm-name "${PROJECT_NAME}-lambda-errors" \
  --alarm-description "Alert when Lambda functions have errors" \
  --namespace "AWS/Lambda" \
  --metric-name "Errors" \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --region "$AWS_REGION" \
  > /dev/null

echo -e "${GREEN}    ✓ Lambda Errors alarm created${NC}"

# Alarm 4: Lambda throttles
echo "  Creating alarm: Lambda Throttles"
aws cloudwatch put-metric-alarm \
  --alarm-name "${PROJECT_NAME}-lambda-throttles" \
  --alarm-description "Alert when Lambda functions are throttled" \
  --namespace "AWS/Lambda" \
  --metric-name "Throttles" \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --region "$AWS_REGION" \
  > /dev/null

echo -e "${GREEN}    ✓ Lambda Throttles alarm created${NC}"

# Alarm 5: Database connections (if using RDS)
echo "  Creating alarm: Database Connection High"
aws cloudwatch put-metric-alarm \
  --alarm-name "${PROJECT_NAME}-db-connections-high" \
  --alarm-description "Alert when database connections are high" \
  --namespace "AWS/RDS" \
  --metric-name "DatabaseConnections" \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --region "$AWS_REGION" \
  > /dev/null 2>&1 || true

echo -e "${GREEN}    ✓ Database Connections alarm created${NC}"

echo ""

################################################################################
# Step 5: Create Metric Filters
################################################################################

echo -e "${YELLOW}Step 5: Creating Metric Filters...${NC}"

# Metric filter for errors
aws logs put-metric-filter \
  --log-group-name "/aws/${PROJECT_NAME}/backend" \
  --filter-name "${PROJECT_NAME}-error-count" \
  --filter-pattern '[timestamp, level=ERROR, ...]' \
  --metric-transformations \
    metricName=ErrorCount,metricNamespace=SchedulingAgent,metricValue=1 \
  --region "$AWS_REGION" \
  > /dev/null 2>&1 || true

echo -e "${GREEN}  ✓ Error count metric filter created${NC}"

# Metric filter for response time
aws logs put-metric-filter \
  --log-group-name "/aws/${PROJECT_NAME}/backend" \
  --filter-name "${PROJECT_NAME}-response-time" \
  --filter-pattern '[timestamp, level, msg, latency_ms=latency_ms*, ...]' \
  --metric-transformations \
    metricName=ResponseTime,metricNamespace=SchedulingAgent,metricValue='$latency_ms' \
  --region "$AWS_REGION" \
  > /dev/null 2>&1 || true

echo -e "${GREEN}  ✓ Response time metric filter created${NC}"

# Metric filter for successful requests
aws logs put-metric-filter \
  --log-group-name "/aws/${PROJECT_NAME}/backend" \
  --filter-name "${PROJECT_NAME}-success-count" \
  --filter-pattern '[timestamp, level=INFO, msg="chat_response_sent", ...]' \
  --metric-transformations \
    metricName=SuccessCount,metricNamespace=SchedulingAgent,metricValue=1 \
  --region "$AWS_REGION" \
  > /dev/null 2>&1 || true

echo -e "${GREEN}  ✓ Success count metric filter created${NC}"

echo ""

################################################################################
# Step 6: Create Custom Metrics Script
################################################################################

echo -e "${YELLOW}Step 6: Creating Custom Metrics Script...${NC}"

cat > "$(dirname "$0")/publish_metrics.py" << 'PYEOF'
#!/usr/bin/env python3
"""
Publish custom CloudWatch metrics for Scheduling Agent.

Usage:
    python3 publish_metrics.py
"""

import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

def publish_custom_metrics():
    """Publish custom application metrics."""

    # Example: Publish active sessions count
    # (This would be retrieved from your database in production)

    metrics = [
        {
            'MetricName': 'ActiveSessions',
            'Value': 0.0,  # Replace with actual value from database
            'Unit': 'Count',
            'Timestamp': datetime.utcnow()
        },
        {
            'MetricName': 'TotalMessages',
            'Value': 0.0,  # Replace with actual value
            'Unit': 'Count',
            'Timestamp': datetime.utcnow()
        },
        {
            'MetricName': 'AppointmentsCreated',
            'Value': 0.0,  # Replace with actual value
            'Unit': 'Count',
            'Timestamp': datetime.utcnow()
        }
    ]

    cloudwatch.put_metric_data(
        Namespace='SchedulingAgent',
        MetricData=metrics
    )

    print(f"Published {len(metrics)} metrics to CloudWatch")

if __name__ == '__main__':
    publish_custom_metrics()
PYEOF

chmod +x "$(dirname "$0")/publish_metrics.py"

echo -e "${GREEN}✓ Custom metrics script created: publish_metrics.py${NC}"
echo ""

################################################################################
# Step 7: Summary
################################################################################

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Monitoring Setup Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

echo -e "${BLUE}Resources Created:${NC}"
echo "  1. SNS Topic: $SNS_TOPIC_ARN"
echo "  2. Log Groups: ${#LOG_GROUPS[@]} created"
echo "  3. CloudWatch Dashboard: ${PROJECT_NAME}-dashboard"
echo "  4. CloudWatch Alarms: 5 alarms"
echo "  5. Metric Filters: 3 filters"
echo ""

echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Confirm SNS subscription in your email (${SNS_EMAIL})"
echo "2. View dashboard: https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#dashboards:name=${PROJECT_NAME}-dashboard"
echo "3. Test alarms by triggering errors"
echo "4. Set up custom metrics: ./publish_metrics.py"
echo "5. Configure log retention as needed"
echo ""

echo -e "${BLUE}Useful Commands:${NC}"
echo "# View logs"
echo "  aws logs tail /aws/${PROJECT_NAME}/backend --follow"
echo ""
echo "# View alarms"
echo "  aws cloudwatch describe-alarms --region ${AWS_REGION}"
echo ""
echo "# Publish test alarm"
echo "  aws cloudwatch set-alarm-state --alarm-name ${PROJECT_NAME}-high-error-rate --state-value ALARM --state-reason test"
echo ""

echo -e "${GREEN}All done! 🎉${NC}"
