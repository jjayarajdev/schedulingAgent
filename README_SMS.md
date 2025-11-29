# SMS Integration - Production Ready

Production-ready SMS integration using AWS Pinpoint SMS Voice v2, Lambda, and multi-agent orchestration.

## Overview

This SMS integration provides:
- Two-way SMS messaging via AWS Pinpoint SMS Voice v2
- Inbound message processing with AI-powered responses
- Session management and message history
- TCPA-compliant opt-out handling
- Event tracking and delivery status monitoring

## Architecture

```
Inbound SMS → AWS Pinpoint → SNS Topic → Lambda → Orchestrator → Response
                                          ↓
                                      DynamoDB (Sessions, Messages, Consent)
```

## Quick Start

### Prerequisites

- AWS CLI configured
- Terraform installed
- Python 3.11+
- AWS account with SMS permissions

### Deployment

1. **Deploy infrastructure**:
   ```bash
   cd infrastructure/terraform/sms
   terraform init
   terraform plan -var="environment=dev" -out=tfplan
   terraform apply tfplan
   ```

2. **Configure SMS resources**:
   ```bash
   cd ../../../
   ./scripts/deploy_sms_config_setup.sh dev
   ```

3. **Test the setup**:
   ```bash
   # Quick test (validates configuration)
   python scripts/test-sms-integration.py --environment dev --quick

   # Comprehensive test (includes Lambda execution)
   python scripts/test-sms-integration.py --environment dev
   ```

## Testing

### Quick Test (Configuration Only)

Validates environment variables, SNS topic, and DynamoDB tables without executing Lambda:

```bash
python scripts/test-sms-integration.py --environment dev --quick
```

### Comprehensive Test (Full Integration)

Tests the complete flow including Lambda execution and message processing:

```bash
# Default test
python scripts/test-sms-integration.py --environment dev

# With custom phone and message
python scripts/test-sms-integration.py \
  --environment dev \
  --phone +15555551234 \
  --message "Test appointment scheduling"

# With verbose logs
python scripts/test-sms-integration.py --environment dev --verbose
```

## Configuration

### Environment Variables

The Lambda function uses these environment variables (automatically configured by Terraform):

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Deployment environment | `dev`, `staging`, `prod` |
| `ORIGINATION_NUMBER` | SMS origination phone number | `+14255556160` |
| `ORCHESTRATOR_LAMBDA` | Multi-agent orchestrator function | `pf-orchestrator` |
| `SMS_CONFIGURATION_SET` | Pinpoint configuration set name | `scheduling-agent-sms-config-dev` |
| `CONSENT_TABLE` | DynamoDB consent tracking table | `scheduling-agent-sms-consent-dev` |
| `MESSAGES_TABLE` | DynamoDB messages table | `scheduling-agent-sms-messages-dev` |
| `SESSIONS_TABLE` | DynamoDB sessions table | `scheduling-agent-sms-sessions-dev` |
| `PF_SECRET_NAME` | Secrets Manager credential path | `projectforce/api/credentials` |
| `AWS_REGION_NAME` | AWS region | `us-east-1` |

### AWS Resources

**DynamoDB Tables**:
- `scheduling-agent-sms-consent-{env}` - Consent and opt-out tracking
- `scheduling-agent-opt-out-tracking-{env}` - Opt-out request tracking
- `scheduling-agent-sms-messages-{env}` - Message history
- `scheduling-agent-sms-sessions-{env}` - Conversation sessions

**Lambda Functions**:
- `scheduling-agent-sms-inbound-{env}` - Inbound SMS processor

**SNS Topics**:
- `scheduling-agent-sms-inbound-{env}` - Inbound message routing

**Pinpoint SMS**:
- Configuration Set: `scheduling-agent-sms-config-{env}`
- Event Destination: `sms-delivery-events-{env}`

## Production Deployment

### 1. Request SMS Production Access

AWS accounts start in SMS Sandbox mode. Request production access:

1. Go to AWS Pinpoint SMS console
2. Navigate to "SMS and voice" → "Phone numbers"
3. Request production access
4. Provide use case and compliance documentation

### 2. Deploy to Production

```bash
# Deploy infrastructure
cd infrastructure/terraform/sms
terraform workspace new prod  # or terraform workspace select prod
terraform plan -var="environment=prod" -out=tfplan
terraform apply tfplan

# Configure SMS resources
cd ../../../
./scripts/deploy_sms_config_setup.sh prod

# Test production setup
python scripts/test-sms-integration.py --environment prod --quick
```

### 3. Update Secrets

Ensure production credentials are in Secrets Manager:

```bash
aws secretsmanager create-secret \
  --name projectforce/api/credentials \
  --secret-string '{
    "bearer_token": "YOUR_PROD_TOKEN",
    "client_id": "YOUR_CLIENT_ID",
    "user_id": "YOUR_USER_ID"
  }' \
  --region us-east-1
```

## Monitoring

### CloudWatch Logs

View Lambda execution logs:

```bash
# Stream live logs
aws logs tail /aws/lambda/scheduling-agent-sms-inbound-dev --follow

# View recent logs
aws logs tail /aws/lambda/scheduling-agent-sms-inbound-dev --since 1h
```

### DynamoDB Queries

Check message history:

```bash
# Scan messages table
aws dynamodb scan \
  --table-name scheduling-agent-sms-messages-dev \
  --limit 10

# Query by phone number (requires GSI)
aws dynamodb query \
  --table-name scheduling-agent-sms-messages-dev \
  --index-name phone-index \
  --key-condition-expression "phone_number = :phone" \
  --expression-attribute-values '{":phone":{"S":"+15555551234"}}'
```

## Opt-Out Handling

### TCPA Compliance

The system automatically handles opt-out requests:

**Opt-out Keywords** (case-insensitive):
- STOP, STOPALL
- QUIT, END
- REVOKE, CANCEL
- OPT OUT, OPTOUT
- UNSUBSCRIBE

**Processing**:
1. Opt-out recorded immediately in DynamoDB
2. Confirmation sent to customer
3. 10-business-day processing window (TCPA 2025 requirement)
4. Universal opt-out (applies to SMS and voice)

**Re-subscription**:
- Reply `START` to resubscribe

## Troubleshooting

### Common Issues

**1. Lambda execution fails**

Check environment variables:
```bash
python scripts/test-sms-integration.py --environment dev --quick
```

**2. Messages not being stored**

Check DynamoDB table permissions in Lambda IAM role.

**3. Orchestrator timeouts**

Adjust `ORCHESTRATOR_TIMEOUT_SECONDS` in handler.py (default: 30s).

**4. SMS send failures in Sandbox mode**

Error: `DESTINATION_PHONE_NUMBER_NOT_VERIFIED`

Solution: Verify destination phone numbers in AWS Pinpoint console or request production access.

## Performance

### Benchmarks

- **Lambda Cold Start**: ~1s
- **Lambda Warm Execution**: ~8s (includes orchestrator call)
- **Orchestrator Response**: ~7-8s
- **DynamoDB Operations**: <100ms
- **Memory Usage**: ~90MB (18% of 512MB allocation)

### Optimization Tips

1. **Reduce orchestrator latency**: Optimize AI model and prompts
2. **Cache credentials**: Already implemented (in-memory caching)
3. **Async processing**: Consider SQS for high-volume scenarios
4. **Batch operations**: Use DynamoDB batch writes for multiple messages

## Security

### Best Practices

- ✅ Credentials stored in AWS Secrets Manager
- ✅ IAM roles with least-privilege permissions
- ✅ SNS topic policies restrict to source account
- ✅ DynamoDB encryption at rest (AWS managed)
- ✅ CloudWatch logs for audit trail
- ✅ TTL enabled on tables (automatic cleanup)

### Data Retention

- **Messages**: 4 years (TCPA compliance)
- **Sessions**: 24 hours
- **Consent records**: 4 years
- **CloudWatch logs**: 7 days (dev), 30 days (prod)

## Support

### Test Scripts

All testing is consolidated into one comprehensive script:

```bash
# Quick validation (no Lambda execution)
python scripts/test-sms-integration.py --environment dev --quick

# Full integration test
python scripts/test-sms-integration.py --environment dev

# With verbose logs
python scripts/test-sms-integration.py --environment dev --verbose
```

### Deployment Scripts

- `scripts/deploy_sms_integration.sh` - Deploy SNS, Lambda, DynamoDB
- `scripts/deploy_sms_config_setup.sh` - Configure Pinpoint SMS resources
- `scripts/test-sms-integration.py` - Comprehensive test suite

## Migration to Production

### Checklist

- [ ] Request AWS SMS production access
- [ ] Provision dedicated phone number
- [ ] Update production secrets in Secrets Manager
- [ ] Deploy production infrastructure
- [ ] Configure CloudWatch alarms
- [ ] Test with verified phone numbers
- [ ] Enable production monitoring
- [ ] Document runbook for on-call

## License

Internal use only - Proprietary
