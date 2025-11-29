# SMS Inbound Processor Lambda

This Lambda function processes inbound SMS messages from AWS End User Messaging (Pinpoint SMS Voice v2) via SNS topic subscription and uses the multi-agent orchestration system for intelligent responses.

## Overview

The function:
1. Receives inbound SMS messages via SNS topic
2. Handles opt-out requests (STOP, CANCEL, etc.) per TCPA 2025 requirements
3. Checks customer consent status
4. Stores messages in DynamoDB for audit trail
5. Invokes the **multi-agent orchestrator lambda** for intelligent conversation processing
6. Formats responses for SMS (removes markdown, limits length)
7. Sends SMS replies back to customers

## Architecture

```
SMS Inbound → SNS Topic → SMS Processor Lambda
                               ↓
                          DynamoDB Tables
                               ↓
                     Multi-Agent Orchestrator Lambda
                          (Parallel/Sequential)
                               ↓
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
              Scheduling  Information  Notes
                Agent       Agent      Agent
                    └──────────┼──────────┘
                               ▼
                      Combined Response
                               ↓
                       SMS Reply to Customer
```

## Differences from Bedrock Supervisor

This implementation uses the **multi-agent orchestration system** instead of directly calling a Bedrock supervisor agent:

- **Orchestrator Lambda**: Invokes `orchestrator` lambda function
- **Multi-Agent Support**: Supports parallel and sequential agent execution
- **Better Performance**: Optimized routing with fast paths
- **Contextual Awareness**: Uses conversation history and context resolution
- **Channel-Aware**: Formats responses appropriately for SMS

## Environment Variables

Required environment variables (configured via Terraform):

- `ENVIRONMENT` - Deployment environment (dev/staging/prod)
- `ORCHESTRATOR_LAMBDA` - Name of orchestrator lambda function
- `ORIGINATION_NUMBER` - Phone number for sending SMS
- `CONSENT_TABLE` - DynamoDB consent tracking table name
- `OPT_OUT_TRACKING_TABLE` - DynamoDB opt-out tracking table name
- `MESSAGES_TABLE` - DynamoDB messages audit table name
- `SESSIONS_TABLE` - DynamoDB sessions table name
- `AWS_REGION_NAME` - AWS region

## DynamoDB Tables

### Consent Table
- **Hash Key**: `phone_number`
- Tracks customer consent and opt-out status
- Includes TCPA 2025 compliance fields
- 4-year TTL for retention

### Opt-Out Tracking Table
- **Hash Key**: `tracking_id`
- **Range Key**: `timestamp`
- Tracks all opt-out requests for compliance
- 10-day processing deadline

### Messages Table
- **Hash Key**: `message_id`
- **Range Key**: `timestamp`
- Audit trail of all SMS messages
- 4-year retention via TTL

### Sessions Table
- **Hash Key**: `session_id`
- Manages conversation sessions
- 24-hour TTL for active sessions

## SMS to Orchestrator Integration

When forwarding messages to the orchestrator, this lambda:

1. **Session Management**: Uses phone number to create/retrieve session ID
2. **Placeholder Credentials**: Uses `SMS_CHANNEL` as token since no real PF auth
3. **Phone as User ID**: Uses phone number as `pf_user_id`
4. **Channel Indicator**: Passes `channel: 'sms'` to orchestrator
5. **Response Formatting**: Strips markdown and truncates for SMS limits

The orchestrator should be configured to handle the SMS channel appropriately:
- Accept placeholder authentication for SMS channel
- Use phone number as customer identifier
- Format responses concisely for SMS

## Deployment

### Build Lambda Package

```bash
cd lambda/sms-inbound-processor

# Install dependencies
pip install -r requirements.txt -t .

# Create deployment package
zip -r lambda.zip . -x "*.pyc" -x "__pycache__/*" -x "*.md" -x "README.md"
```

### Deploy with Terraform

```bash
cd infrastructure/terraform/sms

terraform plan -var="environment=dev" \
  -var="orchestrator_lambda_name=scheduling-agent-orchestrator-dev"

terraform apply
```

## Testing Without Real Phone Number

Since we don't have a real phone number for testing, use the SNS validation script:

```bash
cd scripts

# Test by directly publishing to SNS topic
python test-sms-sns-trigger.py --environment dev \
  --phone "+15555551234" \
  --message "Hello, I need help scheduling"
```

This script will:
1. Publish a test message to the SNS topic (simulating inbound SMS)
2. Trigger the lambda function
3. Monitor CloudWatch logs for execution
4. Check DynamoDB for stored messages
5. Verify orchestrator was invoked

## IAM Permissions Required

Beyond the standard DynamoDB and SMS permissions, this lambda needs:

```json
{
  "Effect": "Allow",
  "Action": [
    "lambda:InvokeFunction"
  ],
  "Resource": "arn:aws:lambda:*:*:function:*-orchestrator-*"
}
```

## Monitoring

### CloudWatch Logs
- **Log Group**: `/aws/lambda/scheduling-agent-sms-inbound-{env}`
- **Key Searches**:
  - `"Invoking orchestrator lambda"` - Orchestrator invocations
  - `"Processing opt-out"` - Opt-out requests
  - `"SMS sent successfully"` - Outbound messages
  - `"Error"` - Any errors

### Metrics to Monitor
1. Lambda invocations (inbound messages)
2. Orchestrator invocation errors
3. DynamoDB throttles
4. SMS send failures
5. Opt-out rate

## Features

### Opt-Out Handling (TCPA 2025 Compliant)
- Keywords: STOP, QUIT, END, REVOKE, OPT OUT, CANCEL, UNSUBSCRIBE
- 10-business-day processing deadline
- Universal opt-out (SMS + voice)
- Confirmation message sent immediately
- 4-year audit retention

### SMS Formatting
- Removes markdown (`**bold**`, `_italic_`, etc.)
- Converts bullet points to `•`
- Collapses excessive newlines
- Truncates at 1600 chars (10 SMS segments)

### Session Management
- 24-hour session lifetime
- Phone number-based lookup
- Maintains conversation context for orchestrator

## Error Handling

Graceful handling of:
- Orchestrator lambda failures (fallback message)
- DynamoDB errors (logged, don't block)
- SMS send failures (logged, stored as failed)
- Invalid SNS message format
- Session management errors (generates new session)

## Compliance

- ✅ TCPA 2025 opt-out requirements
- ✅ 4-year message retention
- ✅ Universal opt-out across channels
- ✅ Audit trail for all communications
- ✅ Immediate opt-out confirmation

## Troubleshooting

### Lambda Not Triggered
1. Check SNS subscription exists
2. Verify Lambda permission for SNS
3. Test SNS topic with validation script

### Orchestrator Not Responding
1. Check orchestrator lambda name in env vars
2. Verify IAM permissions for lambda:InvokeFunction
3. Review orchestrator logs for errors
4. Check if orchestrator handles SMS channel

### SMS Not Sending
1. Verify phone number is provisioned and active
2. Check IAM permissions for SMS
3. Review outbound message in DynamoDB (should show 'sent' status)
4. Check CloudWatch logs for send errors

## See Also

- [Multi-Agent Orchestrator Documentation](../orchestrator/README_MULTI_AGENT.md)
- [Infrastructure Configuration](../../infrastructure/terraform/sms/main.tf)
- [Validation Script](../../scripts/test-sms-sns-trigger.py)
