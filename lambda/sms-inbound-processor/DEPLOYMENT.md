# SMS Inbound Processor - Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Deployment Steps](#deployment-steps)
4. [Validation](#validation)
5. [Rollback Procedure](#rollback-procedure)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### AWS Permissions Required
- Lambda: CreateFunction, UpdateFunctionCode, UpdateFunctionConfiguration
- IAM: CreateRole, AttachRolePolicy
- DynamoDB: CreateTable, DescribeTable
- SNS: CreateTopic, Subscribe
- Secrets Manager: GetSecretValue
- CloudWatch: PutMetricData, CreateLogGroup

### Tools Required
- AWS CLI v2+
- Terraform v1.0+
- Python 3.11
- Git

### Secrets Manager Setup
Ensure PF credentials exist in Secrets Manager:

```bash
aws secretsmanager get-secret-value \
  --secret-id projectforce/api/credentials \
  --region us-east-1
```

Expected secret format:
```json
{
  "bearer_token": "...",
  "client_id": "09PF05VD",
  "user_id": "1646085",
  "api_base_url": "https://api-cx-portal.dev.projectsforce.com"
}
```

---

## Environment Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd schedulingAgent
git checkout feature/feature_sms_processor
```

### 2. Install Dependencies
```bash
cd lambda/sms-inbound-processor
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create `.env` file (for local testing):
```bash
ENVIRONMENT=dev
ORCHESTRATOR_LAMBDA=pf-orchestrator
ORIGINATION_NUMBER=+18005551234
CONSENT_TABLE=scheduling-agent-sms-consent-dev
OPT_OUT_TRACKING_TABLE=scheduling-agent-opt-out-tracking-dev
MESSAGES_TABLE=scheduling-agent-sms-messages-dev
SESSIONS_TABLE=scheduling-agent-sms-sessions-dev
AWS_REGION_NAME=us-east-1
PF_SECRET_NAME=projectforce/api/credentials
LOG_LEVEL=INFO
```

---

## Deployment Steps

### Step 1: Build Lambda Package

```bash
cd lambda/sms-inbound-processor
python build.py
```

Or manual build:
```bash
rm -rf package lambda.zip
mkdir package
pip install -r requirements.txt -t package/
cp handler.py package/
cd package && zip -r ../lambda.zip . && cd ..
```

Verify package:
```bash
ls -lh lambda.zip
unzip -l lambda.zip | grep handler.py
```

### Step 2: Deploy Infrastructure with Terraform

#### Initialize Terraform
```bash
cd infrastructure/terraform/sms
terraform init
```

#### Plan Deployment
```bash
terraform plan \
  -var="environment=dev" \
  -out=tfplan
```

Review the plan carefully!

#### Apply Infrastructure
```bash
terraform apply tfplan
```

Expected resources:
- 4 DynamoDB tables
- 1 SNS topic
- 1 Lambda function
- IAM role and policies
- CloudWatch log groups

#### Save Outputs
```bash
terraform output -json > outputs.json
```

### Step 3: Update Lambda Function Code

If infrastructure already exists, update code only:

```bash
# Build package
cd lambda/sms-inbound-processor
python build.py

# Update Lambda
aws lambda update-function-code \
  --function-name scheduling-agent-sms-inbound-dev \
  --zip-file fileb://lambda.zip \
  --region us-east-1
```

Wait for update to complete:
```bash
aws lambda wait function-updated \
  --function-name scheduling-agent-sms-inbound-dev \
  --region us-east-1
```

### Step 4: Update Environment Variables (if needed)

```bash
aws lambda update-function-configuration \
  --function-name scheduling-agent-sms-inbound-dev \
  --environment "Variables={
    ENVIRONMENT=dev,
    ORCHESTRATOR_LAMBDA=pf-orchestrator,
    ORIGINATION_NUMBER=+18005551234,
    CONSENT_TABLE=scheduling-agent-sms-consent-dev,
    OPT_OUT_TRACKING_TABLE=scheduling-agent-opt-out-tracking-dev,
    MESSAGES_TABLE=scheduling-agent-sms-messages-dev,
    SESSIONS_TABLE=scheduling-agent-sms-sessions-dev,
    AWS_REGION_NAME=us-east-1,
    PF_SECRET_NAME=projectforce/api/credentials,
    LOG_LEVEL=INFO
  }" \
  --region us-east-1
```

### Step 5: Verify Deployment

```bash
# Check Lambda status
aws lambda get-function \
  --function-name scheduling-agent-sms-inbound-dev \
  --region us-east-1

# Check SNS subscription
aws sns list-subscriptions-by-topic \
  --topic-arn $(terraform output -raw sns_topic_arn) \
  --region us-east-1
```

---

## Validation

### 1. Run Test Script

```bash
cd scripts
python test-sms-simple.py \
  --environment dev \
  --phone "+15559998888" \
  --message "Hello, test deployment"
```

Expected output:
```
✓ SNS topic accessible
✓ Lambda function exists
✓ Message published to SNS
✓ Lambda processed message
✓ Data stored in DynamoDB
```

### 2. Check CloudWatch Logs

```bash
aws logs tail /aws/lambda/scheduling-agent-sms-inbound-dev \
  --follow \
  --region us-east-1
```

Look for:
- `[INFO] Processing SMS from...`
- `[INFO] PF credentials loaded successfully`
- `[INFO] Orchestrator response status: 200`

### 3. Verify DynamoDB Records

```bash
aws dynamodb scan \
  --table-name scheduling-agent-sms-messages-dev \
  --limit 5 \
  --region us-east-1
```

### 4. Test Conversation Flow

```bash
# First message
python test-sms-simple.py --phone "+15551234567" --message "Show me my projects"

# Follow-up message
python test-sms-simple.py --phone "+15551234567" --message "Tell me about the first one"
```

Verify session_id is consistent in DynamoDB.

### 5. Run Comprehensive Test Suite

```bash
python scripts/test-sms-integration.py
```

Review test results for any failures.

---

## Rollback Procedure

### Rollback Lambda Code

```bash
# List previous versions
aws lambda list-versions-by-function \
  --function-name scheduling-agent-sms-inbound-dev \
  --region us-east-1

# Update alias to previous version
aws lambda update-alias \
  --function-name scheduling-agent-sms-inbound-dev \
  --name LIVE \
  --function-version <PREVIOUS_VERSION> \
  --region us-east-1
```

### Rollback Infrastructure

```bash
cd infrastructure/terraform/sms

# Revert to previous state
terraform state pull > backup.tfstate
terraform apply -target=aws_lambda_function.sms_inbound_processor
```

### Emergency Disable

Disconnect SNS subscription to stop processing:

```bash
aws sns unsubscribe \
  --subscription-arn <SUBSCRIPTION_ARN> \
  --region us-east-1
```

---

## Troubleshooting

### Issue: Lambda Timeout

**Symptoms**: Lambda execution exceeds 30 seconds

**Solution**:
```bash
aws lambda update-function-configuration \
  --function-name scheduling-agent-sms-inbound-dev \
  --timeout 60 \
  --region us-east-1
```

### Issue: Secrets Manager Access Denied

**Symptoms**: `Failed to get PF credentials` in logs

**Solution**:
1. Verify IAM role has `secretsmanager:GetSecretValue` permission
2. Check secret ARN in IAM policy matches actual secret
3. Verify secret exists:
```bash
aws secretsmanager describe-secret \
  --secret-id projectforce/api/credentials \
  --region us-east-1
```

### Issue: DynamoDB Throttling

**Symptoms**: `ProvisionedThroughputExceededException`

**Solution**:
1. Enable auto-scaling on DynamoDB tables
2. Increase provisioned capacity temporarily
3. Add exponential backoff retry logic

### Issue: Orchestrator Returns 500

**Symptoms**: `Orchestrator response status: 500`

**Solution**:
1. Check bearer token expiration:
```bash
python scripts/token-management/get_and_update_token.py
```

2. Verify orchestrator lambda exists and is healthy:
```bash
aws lambda get-function \
  --function-name pf-orchestrator \
  --region us-east-1
```

### Issue: Messages Not Stored

**Symptoms**: No records in DynamoDB after sending SMS

**Solution**:
1. Check CloudWatch logs for errors
2. Verify DynamoDB table permissions
3. Check table write capacity

### Debug Mode

Enable debug logging:
```bash
aws lambda update-function-configuration \
  --function-name scheduling-agent-sms-inbound-dev \
  --environment "Variables={...,LOG_LEVEL=DEBUG}" \
  --region us-east-1
```

---

## Post-Deployment Checklist

- [ ] All tests passing
- [ ] CloudWatch logs show successful processing
- [ ] DynamoDB tables populated correctly
- [ ] Secrets Manager credentials valid
- [ ] Orchestrator responding with 200
- [ ] Session management working
- [ ] No errors in last 100 log entries
- [ ] Deployment documented in changelog
- [ ] Team notified of deployment
- [ ] Monitoring alerts configured

---

## Monitoring

### Key Metrics to Watch

1. **Lambda Metrics**
   - Invocations
   - Errors
   - Duration (avg, p99)
   - Concurrent executions
   - Throttles

2. **DynamoDB Metrics**
   - ConsumedReadCapacityUnits
   - ConsumedWriteCapacityUnits
   - UserErrors
   - SystemErrors

3. **Custom Metrics**
   - Messages processed per minute
   - Orchestrator success rate
   - Average response time
   - Opt-out rate

### CloudWatch Alarms

Create alarms for:
- Error rate > 1%
- Duration > 25s (approaching timeout)
- Throttles > 0
- DynamoDB capacity > 80%

---

## Support

### Team Contacts
- **On-Call**: [Your on-call rotation]
- **Slack**: #sms-integration
- **Email**: sms-support@example.com

### Escalation
1. Check runbook
2. Review CloudWatch logs
3. Contact on-call engineer
4. Page team lead if critical

---

**Last Updated**: 2025-11-20
**Version**: 1.0.0
**Maintained By**: SMS Integration Team
