# SMS Inbound Processor Lambda Function

Processes inbound SMS messages from AWS End User Messaging via SNS and invokes Bedrock Agent.

## Functionality

1. **Receives SMS via SNS**: Triggered by SNS topic when customer sends SMS
2. **Opt-Out Detection**: Automatically detects and processes opt-out keywords
3. **Consent Check**: Verifies customer hasn't opted out before processing
4. **Message Storage**: Stores all messages in DynamoDB for audit trail
5. **Session Management**: Maintains conversation sessions with 24-hour TTL
6. **Agent Invocation**: Calls Bedrock Supervisor Agent with customer message
7. **Reply Sending**: Sends agent response back to customer via SMS

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment name | `dev` |
| `SUPERVISOR_AGENT_ID` | Bedrock Agent ID | `5VTIWONUMO` |
| `SUPERVISOR_ALIAS_ID` | Agent Alias ID | `HH2U7EZXMW` |
| `ORIGINATION_NUMBER` | SMS phone number | `+18005551234` |
| `CONSENT_TABLE` | DynamoDB consent table | `scheduling-agent-sms-consent-dev` |
| `OPT_OUT_TRACKING_TABLE` | DynamoDB opt-out tracking | `scheduling-agent-opt-out-tracking-dev` |
| `MESSAGES_TABLE` | DynamoDB messages table | `scheduling-agent-sms-messages-dev` |
| `SESSIONS_TABLE` | DynamoDB sessions table | `scheduling-agent-sms-sessions-dev` |
| `AWS_REGION_NAME` | AWS region | `us-east-1` |

## IAM Permissions Required

- `sms-voice:SendTextMessage` - Send SMS replies
- `sms-voice:DescribePhoneNumbers` - Get phone number details
- `dynamodb:GetItem` - Read consent status
- `dynamodb:PutItem` - Store messages and sessions
- `dynamodb:Query` - Query sessions by phone number
- `bedrock-agent-runtime:InvokeAgent` - Call Bedrock Agent
- `logs:CreateLogStream` - CloudWatch logging
- `logs:PutLogEvents` - CloudWatch logging

## SNS Event Format

```json
{
  "Records": [
    {
      "Sns": {
        "Message": "{\"originationNumber\":\"+14255551234\",\"destinationNumber\":\"+18005551234\",\"messageBody\":\"I want to schedule an appointment\",\"inboundMessageId\":\"msg-12345\",\"messageKeyword\":\"NONE\",\"previousPublishedMessageId\":\"null\"}"
      }
    }
  ]
}
```

## Response Format

```json
{
  "statusCode": 200,
  "body": "{\"message\":\"SMS processed successfully\"}"
}
```

## Deployment

### Build Lambda Package

```bash
cd lambda/sms-inbound-processor

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create deployment package
mkdir package
pip install -r requirements.txt --target package/
cd package
zip -r ../lambda.zip .
cd ..
zip -g lambda.zip handler.py

# Clean up
deactivate
rm -rf package venv
```

### Deploy with Terraform

```bash
cd infrastructure/terraform/sms
terraform init
terraform plan
terraform apply
```

## Testing

### Local Testing

```python
import json
from handler import lambda_handler

# Mock SNS event
event = {
    "Records": [{
        "Sns": {
            "Message": json.dumps({
                "originationNumber": "+14255551234",
                "destinationNumber": "+18005551234",
                "messageBody": "Hello",
                "inboundMessageId": "test-123"
            })
        }
    }]
}

# Invoke handler
response = lambda_handler(event, None)
print(response)
```

### AWS Console Testing

1. Navigate to Lambda console
2. Select `scheduling-agent-sms-inbound-dev`
3. Click "Test" tab
4. Create test event with SNS payload
5. Click "Test" button

## Monitoring

### CloudWatch Logs

```bash
# View recent logs
aws logs tail /aws/lambda/scheduling-agent-sms-inbound-dev --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/scheduling-agent-sms-inbound-dev \
  --filter-pattern "ERROR"
```

### CloudWatch Metrics

- **Invocations**: Total number of SMS processed
- **Duration**: Processing time per message
- **Errors**: Failed invocations
- **Throttles**: Rate limit hits

## Troubleshooting

### Common Issues

**1. Agent returns generic error**
- Check Bedrock Agent is in PREPARED state
- Verify IAM permissions for `bedrock-agent-runtime:InvokeAgent`
- Check agent ID and alias ID are correct

**2. SMS not sending**
- Verify phone number is provisioned
- Check IAM permissions for `sms-voice:SendTextMessage`
- Verify destination number is not on opt-out list

**3. Opt-out not working**
- Check DynamoDB consent table has item
- Verify keyword detection is working
- Check confirmation SMS was sent

**4. Session not persisting**
- Verify TTL is set correctly (24 hours)
- Check DynamoDB sessions table
- Review session ID generation logic

## TCPA Compliance Notes

- **Opt-Out Processing**: Must honor within 10 business days (TCPA 2025)
- **Multi-Channel**: SMS opt-out applies to voice calls too
- **Confirmation**: Must send confirmation of opt-out
- **Audit Trail**: All opt-outs stored with 4-year retention
- **Resubscribe**: "START" keyword allows resubscription

## Cost Estimate

- **Lambda Invocations**: 10,000/month @ $0.20/million = **$0.002**
- **Lambda Duration**: 512 MB, 5s avg @ $0.0000083/GB-second = **$0.21**
- **DynamoDB**: PAY_PER_REQUEST for 40,000 writes = **$0.50**
- **SMS Sending**: 10,000 messages @ $0.0075 = **$75.00**

**Total**: ~$75.71/month for 10K messages

## Version History

- **v1.0.0** (2025-10-13): Initial implementation with Bedrock Agent integration
