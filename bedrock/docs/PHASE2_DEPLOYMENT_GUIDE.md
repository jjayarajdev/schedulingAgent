# Phase 2 Deployment Guide: AWS SMS Integration

**Version:** 1.0
**Date:** October 13, 2025
**Status:** Ready for Deployment

---

## Overview

This guide covers deploying AWS End User Messaging SMS for Phase 2 of the Bedrock Multi-Agent System, enabling two-way SMS communication with customers.

### What's Being Deployed

| Component | Purpose | Resources |
|-----------|---------|-----------|
| **AWS End User Messaging SMS** | Two-way SMS/MMS service | Toll-free number, opt-out list, config set |
| **DynamoDB Tables** | SMS data storage | 4 tables (consent, tracking, messages, sessions) |
| **Lambda Function** | Inbound message processor | 1 function with SNS trigger |
| **SNS Topic** | Inbound message routing | 1 topic |
| **CloudWatch** | Logging and monitoring | 2 log groups |
| **IAM Roles** | Permissions | 2 roles (Lambda, CloudWatch) |

---

## Prerequisites

### 1. Phase 1 Complete ✅

Ensure Phase 1 is deployed and working:
```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock

# Verify agents are working
python3 tests/test_api_access.py
```

**Expected output:**
```
✅ PASS  Direct Model
✅ PASS  Agent
✅ PASS  Supervisor
```

### 2. AWS CLI Configured

```bash
# Verify AWS credentials
aws sts get-caller-identity

# Expected output:
# {
#   "UserId": "...",
#   "Account": "618048437522",
#   "Arn": "arn:aws:iam::618048437522:user/..."
# }
```

### 3. Terraform Installed

```bash
terraform version
# Required: >= 1.5.0
```

### 4. Python 3.11+

```bash
python3 --version
# Required: >= 3.11
```

---

## Deployment Steps

### Step 1: Build Lambda Package

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/lambda

# Build Lambda deployment package
./build_lambda.sh
```

**Expected output:**
```
================================
Lambda Deployment Package Builder
================================

Building: sms-inbound-processor
  → Installing dependencies...
  → Package created: lambda.zip (1.2M)

================================
Build Complete!
================================
```

**Verify package:**
```bash
ls -lh sms-inbound-processor/lambda.zip
# Should show ~1-2 MB file
```

---

### Step 2: Initialize Terraform SMS Module

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/terraform/sms

# Initialize Terraform
terraform init
```

**Expected output:**
```
Initializing the backend...
Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 6.0"...
- Installing hashicorp/aws v6.x.x...

Terraform has been successfully initialized!
```

---

### Step 3: Review Terraform Plan

```bash
# Generate plan
terraform plan -out=tfplan
```

**Expected resources to create (~25):**
- 1 × AWS End User Messaging phone number
- 1 × Opt-out list
- 1 × Configuration set
- 1 × SNS topic
- 4 × DynamoDB tables
- 1 × Lambda function
- 2 × CloudWatch log groups
- 2 × IAM roles
- ~10 × IAM policies and attachments

**Review plan carefully:**
```
Plan: 25 to add, 0 to change, 0 to destroy.
```

---

### Step 4: Apply Terraform Configuration

```bash
# Apply infrastructure
terraform apply tfplan
```

**Duration:** ~5-10 minutes

**Note on phone number provisioning:**
- Toll-free numbers can take **2-4 weeks** to provision
- You'll see the resource created, but it may be in "pending" state
- Check AWS Console → End User Messaging → Phone numbers

---

### Step 5: Save Outputs

```bash
# Save outputs to file
terraform output -json > ../../../phase2-outputs.json

# Display key outputs
echo "Phone Number:"
terraform output phone_number

echo "SNS Topic:"
terraform output sns_inbound_topic_arn

echo "Lambda Function:"
terraform output lambda_inbound_function_name

echo "DynamoDB Tables:"
terraform output consent_table_name
terraform output messages_table_name
```

**Example output:**
```json
{
  "phone_number": "+18005551234",
  "sns_inbound_topic_arn": "arn:aws:sns:us-east-1:618048437522:scheduling-agent-sms-inbound-dev",
  "lambda_inbound_function_name": "scheduling-agent-sms-inbound-dev",
  "consent_table_name": "scheduling-agent-sms-consent-dev"
}
```

---

### Step 6: Configure Two-Way Messaging

**IMPORTANT:** This step must be done manually in AWS Console (Terraform doesn't support this yet).

1. Open [AWS End User Messaging Console](https://console.aws.amazon.com/sms-voice/home?region=us-east-1)

2. Navigate to **Phone numbers**

3. Select your phone number

4. Click **"Two-way messaging"** tab

5. Enable two-way messaging:
   - Toggle: **Enabled**
   - SNS Topic: Select `scheduling-agent-sms-inbound-dev`
   - Click **"Save"**

**Screenshot location:**
```
Configuration → Phone numbers → [Your Number] → Two-way messaging
```

---

### Step 7: Verify Deployment

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock

# Check Lambda function
aws lambda get-function \
  --function-name scheduling-agent-sms-inbound-dev \
  --region us-east-1

# Check DynamoDB tables
aws dynamodb list-tables --region us-east-1 | grep scheduling-agent-sms

# Check SNS topic
aws sns list-topics --region us-east-1 | grep sms-inbound
```

**Expected:**
- Lambda function exists and is active
- 4 DynamoDB tables exist
- SNS topic exists

---

## Testing

### Test 1: Lambda Function (Unit Test)

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock

# Create test event
cat > /tmp/test-sms-event.json <<'EOF'
{
  "Records": [{
    "Sns": {
      "Message": "{\"originationNumber\":\"+14255551234\",\"destinationNumber\":\"+18005551234\",\"messageBody\":\"Hello\",\"inboundMessageId\":\"test-123\",\"messageKeyword\":\"NONE\"}"
    }
  }]
}
EOF

# Invoke Lambda locally (requires AWS SAM)
aws lambda invoke \
  --function-name scheduling-agent-sms-inbound-dev \
  --payload file:///tmp/test-sms-event.json \
  --region us-east-1 \
  /tmp/lambda-response.json

# View response
cat /tmp/lambda-response.json
```

**Expected:**
```json
{
  "statusCode": 200,
  "body": "{\"message\":\"SMS processed successfully\"}"
}
```

### Test 2: End-to-End SMS (Requires Verified Number)

**Prerequisites:**
- Phone number provisioned (2-4 weeks)
- Your personal number added to verified list (dev/test)

**Steps:**

1. Add your number to verified list:
```bash
aws pinpoint-sms-voice-v2 create-verified-destination-number \
  --destination-phone-number +1YOUR_NUMBER \
  --region us-east-1
```

2. Send test SMS to toll-free number:
```
From: Your phone
To: +1-800-XXX-XXXX (your toll-free number)
Message: Hello
```

3. Check CloudWatch logs:
```bash
aws logs tail /aws/lambda/scheduling-agent-sms-inbound-dev --follow --region us-east-1
```

4. Verify reply received on your phone

---

## Configuration

### Environment Variables (Already Set by Terraform)

| Variable | Value | Description |
|----------|-------|-------------|
| `ENVIRONMENT` | `dev` | Environment name |
| `SUPERVISOR_AGENT_ID` | `5VTIWONUMO` | Bedrock Agent ID |
| `SUPERVISOR_ALIAS_ID` | `HH2U7EZXMW` | Agent Alias ID |
| `ORIGINATION_NUMBER` | `+1800...` | Your toll-free number |
| `CONSENT_TABLE` | `scheduling-agent-sms-consent-dev` | DynamoDB table |
| `MESSAGES_TABLE` | `scheduling-agent-sms-messages-dev` | DynamoDB table |
| `SESSIONS_TABLE` | `scheduling-agent-sms-sessions-dev` | DynamoDB table |
| `OPT_OUT_TRACKING_TABLE` | `scheduling-agent-opt-out-tracking-dev` | DynamoDB table |

### Adjustable Settings

Edit `infrastructure/terraform/sms/terraform.tfvars`:

```hcl
environment = "dev"

# Lambda settings
lambda_memory_size = 512  # MB
lambda_timeout = 30       # seconds

# Session TTL
sms_session_ttl_hours = 24

# Message retention
sms_message_retention_days = 1460  # 4 years

# TCPA compliance
tcpa_opt_out_deadline_days = 10

# CloudWatch retention
sms_cloudwatch_retention_days = 30
```

---

## Monitoring

### CloudWatch Logs

**Lambda logs:**
```bash
# Tail Lambda logs
aws logs tail /aws/lambda/scheduling-agent-sms-inbound-dev --follow --region us-east-1

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/scheduling-agent-sms-inbound-dev \
  --filter-pattern "ERROR" \
  --region us-east-1
```

**SMS delivery logs:**
```bash
# Tail SMS events
aws logs tail /aws/sms/scheduling-agent/dev --follow --region us-east-1
```

### CloudWatch Metrics

**Lambda metrics:**
- Invocations
- Duration
- Errors
- Throttles

**Custom metrics to add:**
```python
# In Lambda code
cloudwatch = boto3.client('cloudwatch')

cloudwatch.put_metric_data(
    Namespace='SchedulingAgent/SMS',
    MetricData=[
        {
            'MetricName': 'InboundMessages',
            'Value': 1,
            'Unit': 'Count'
        }
    ]
)
```

### DynamoDB Monitoring

```bash
# Check table metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=scheduling-agent-sms-messages-dev \
  --start-time 2025-10-13T00:00:00Z \
  --end-time 2025-10-13T23:59:59Z \
  --period 3600 \
  --statistics Sum \
  --region us-east-1
```

---

## Troubleshooting

### Issue 1: Lambda Returns 500 Error

**Symptoms:**
- Lambda invocation fails
- CloudWatch shows "Error invoking Bedrock Agent"

**Solutions:**
```bash
# Check Lambda has Bedrock permissions
aws lambda get-policy \
  --function-name scheduling-agent-sms-inbound-dev \
  --region us-east-1

# Verify agent is in PREPARED state
aws bedrock-agent get-agent \
  --agent-id 5VTIWONUMO \
  --region us-east-1 \
  --query 'agent.agentStatus'

# Check Lambda IAM role
aws iam get-role-policy \
  --role-name scheduling-agent-lambda-sms-dev \
  --policy-name sms-permissions \
  --region us-east-1
```

### Issue 2: SMS Not Sending

**Symptoms:**
- Reply not received on phone
- CloudWatch shows "Error sending SMS"

**Solutions:**
```bash
# Verify phone number is active
aws pinpoint-sms-voice-v2 describe-phone-numbers \
  --region us-east-1

# Check destination number not on opt-out list
aws dynamodb get-item \
  --table-name scheduling-agent-sms-consent-dev \
  --key '{"phone_number": {"S": "+14255551234"}}' \
  --region us-east-1

# Test SendTextMessage directly
aws pinpoint-sms-voice-v2 send-text-message \
  --destination-phone-number +1YOUR_NUMBER \
  --origination-identity +1YOUR_TOLL_FREE \
  --message-body "Test from AWS CLI" \
  --region us-east-1
```

### Issue 3: Inbound Messages Not Triggering Lambda

**Symptoms:**
- Send SMS to toll-free number
- No Lambda invocation in CloudWatch

**Solutions:**
```bash
# Verify SNS subscription
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:618048437522:scheduling-agent-sms-inbound-dev \
  --region us-east-1

# Check Lambda has SNS permission
aws lambda get-policy \
  --function-name scheduling-agent-sms-inbound-dev \
  --region us-east-1 | jq '.Policy' | jq .

# Test SNS → Lambda manually
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:618048437522:scheduling-agent-sms-inbound-dev \
  --message '{"originationNumber":"+14255551234","destinationNumber":"+18005551234","messageBody":"Test","inboundMessageId":"test"}' \
  --region us-east-1
```

### Issue 4: Phone Number Stuck in "Pending"

**Symptoms:**
- Terraform created phone number resource
- Status shows "pending" for days/weeks

**This is normal:**
- Toll-free number provisioning takes 2-4 weeks
- You can proceed with other setup meanwhile
- SMS will work once provisioning completes

**Check status:**
```bash
aws pinpoint-sms-voice-v2 describe-phone-numbers \
  --region us-east-1 \
  --query 'PhoneNumbers[*].[PhoneNumber,Status,CreatedTimestamp]'
```

---

## Cost Estimates

### Monthly Costs (10,000 messages)

| Resource | Cost | Notes |
|----------|------|-------|
| **Phone Number** | $2-5/month | Toll-free reservation |
| **SMS Outbound** | $75.00 | 10K messages × $0.0075 |
| **SMS Inbound** | $5.00 | 10K messages × $0.0005 |
| **Lambda** | $0.21 | 512 MB, 5s avg |
| **DynamoDB** | $0.50 | PAY_PER_REQUEST |
| **CloudWatch** | $2.00 | Logs + metrics |
| **SNS** | $0.50 | Topic + subscriptions |
| **Total** | **~$85/month** | For 10K messages |

### Cost per Message

- SMS outbound: $0.0075
- SMS inbound: $0.0005
- Lambda: $0.000021
- DynamoDB: $0.000050
- **Total: $0.008/message**

---

## Next Steps

After successful deployment:

1. **Request Toll-Free Number Approval** (if not auto-approved)
   - May require business verification
   - Typically 2-4 weeks

2. **Set Up Monitoring**
   - Create CloudWatch dashboard
   - Set up alarms for errors
   - Monitor opt-out deadlines

3. **Test Thoroughly**
   - Test all agent routes (scheduling, info, notes, chitchat)
   - Test opt-out keywords
   - Test long messages (segmentation)
   - Test error scenarios

4. **Document Phone Number**
   - Add to documentation
   - Update customer communications
   - Train support team

5. **Phase 3: Frontend**
   - Build React chat interface
   - Integrate with SMS backend
   - Deploy to production

---

## Rollback

If you need to remove SMS infrastructure:

```bash
cd infrastructure/terraform/sms

# Destroy all resources
terraform destroy

# Confirm: yes
```

**⚠️ Warning:** This will:
- Delete all DynamoDB data
- Remove Lambda function
- Release phone number
- Cannot be undone

---

## Support

**Issues?**
- Check [Troubleshooting](#troubleshooting) section
- Review CloudWatch logs
- Verify IAM permissions
- Contact AWS Support for phone number issues

**Documentation:**
- [AWS End User Messaging Docs](https://docs.aws.amazon.com/sms-voice/)
- [Lambda Docs](https://docs.aws.amazon.com/lambda/)
- [DynamoDB Docs](https://docs.aws.amazon.com/dynamodb/)

---

**Deployment Status:** Ready
**Last Updated:** October 13, 2025
