# Phase 3: Voice Integration

**Add voice/phone call capabilities to your Bedrock multi-agent system**

---

## Quick Start

```bash
cd bedrock

# Deploy everything
./scripts/deploy_voice_integration.sh

# Test deployment
python3 tests/test_voice_integration.py

# Call your phone number and say:
"Show me my projects"
```

---

## What Gets Deployed

- **AWS Connect Instance** - Contact center for handling calls
- **Amazon Lex V2 Bot** - Speech-to-text + intent recognition
- **2 Lambda Functions** - lex-fulfillment, voice-bedrock-bridge
- **Contact Flow** - Call routing logic (IVR)
- **S3 Bucket** - Call recordings (90-day retention)
- **IAM Roles** - Permissions for all services

---

## Architecture

```
Customer calls phone number
    ↓
AWS Connect answers call
    ↓
Lex bot listens and recognizes intent
    ↓
Simple queries → lex-fulfillment Lambda
Complex queries → voice-bedrock-bridge Lambda → Bedrock Supervisor Agent
    ↓
Response read to customer
```

---

## Configuration

All configuration is in Terraform variables:

**Location:** `infrastructure/terraform/voice/variables.tf`

**Key variables:**
- `connect_phone_number` - Your toll-free number (+1-800-XXX-XXXX)
- `supervisor_agent_id` - Auto-detected from Phase 1
- `region` - us-east-1 (for USA customers)

---

## Manual Steps Required

AWS requires 3 manual steps during deployment:

1. **Claim phone number** (AWS Console → Connect → Phone Numbers)
2. **Import contact flow** (AWS Console → Connect → Contact Flows)
3. **Associate phone with flow** (AWS Console → Phone Numbers → Edit)

The deployment script will pause and provide exact instructions.

---

## Testing

### Test 1: Automated Tests
```bash
python3 tests/test_voice_integration.py
```

### Test 2: Live Phone Call
Call your phone number and try:
- "Show me my projects"
- "Schedule my most urgent project"
- "What's the weather like?"

### Test 3: Monitor Logs
```bash
# Watch Lex fulfillment
aws logs tail /aws/lambda/pf-lex-fulfillment-dev --follow

# Watch Bedrock bridge
aws logs tail /aws/lambda/pf-voice-bedrock-bridge-dev --follow
```

---

## Supported Queries

### Simple (handled by Lex directly, <3s response):
- "Show me my projects"
- "List my projects"
- "What projects do I have?"
- "Hello" / "Help"

### Complex (routed to Bedrock, <8s response):
- "Schedule my most urgent project"
- "What's the weather like for outdoor projects?"
- "Book an appointment for Monday"
- "Reschedule project 12345"

---

## Cost

**Monthly cost for 1,000 calls (5 min avg):** ~$160

Breakdown:
- AWS Connect: $90
- Phone number: $3
- Lex: $2
- Lambda: $1
- Bedrock: $50
- S3: $10
- Logs: $5

**Per-call cost:** ~$0.16

---

## Files

```
infrastructure/
├── terraform/voice/
│   ├── aws_connect.tf          # Connect instance, S3, phone
│   ├── lex_bot.tf              # Lex bot, intents, slots
│   ├── lambda_functions.tf     # Lambda configs
│   ├── variables.tf            # Configuration
│   └── provider.tf             # Terraform setup
├── voice/
│   └── contact-flows/
│       └── main-inbound-flow.json  # IVR logic
lambda/
├── lex-fulfillment/
│   └── handler.py              # Simple query handler
└── voice-bedrock-bridge/
    └── handler.py              # Bedrock integration
scripts/
└── deploy_voice_integration.sh # Automated deployment
tests/
└── test_voice_integration.py   # Test suite
docs/phase3/
├── README.md                   # This file
└── PHASE3_DEPLOYMENT_GUIDE.md  # Complete guide
```

---

## Troubleshooting

### Calls don't connect
- Verify phone number is associated with contact flow
- Check contact flow is published
- Verify hours of operation (24/7 by default)

### Lex doesn't understand
- Check bot is built and published
- Verify alias is "prod"
- Test bot in Lex console first

### Lambda errors
- Check CloudWatch Logs
- Verify IAM permissions
- Test Lambda directly with test events

### Bedrock not responding
- Verify Supervisor agent is deployed (Phase 1)
- Check Lambda has `bedrock:InvokeAgent` permission
- Test Bedrock agent directly

---

## Next Steps

After successful deployment:

1. **Test thoroughly** - Try all query types
2. **Monitor metrics** - Set up CloudWatch dashboards
3. **Optimize Lex** - Add more sample utterances
4. **Enhance responses** - Add SSML for better speech
5. **Plan Phase 3.1** - Outbound calls, SMS integration

---

## Documentation

- **Full Guide:** [PHASE3_DEPLOYMENT_GUIDE.md](./PHASE3_DEPLOYMENT_GUIDE.md)
- **Phase 1 (Prerequisite):** [Phase 1 Docs](../README.md)
- **AWS Connect Docs:** https://docs.aws.amazon.com/connect/
- **Lex V2 Docs:** https://docs.aws.amazon.com/lexv2/

---

## Support

For deployment issues:

1. Check CloudWatch Logs (all services)
2. Review Terraform output
3. Test components individually
4. Consult full deployment guide

---

**Phase:** 3 - Voice Integration
**Status:** Production Ready
**Region:** us-east-1 (USA)
**Prerequisites:** Phase 1 (Bedrock Agents)
**Deployment Time:** ~30 minutes (including manual steps)
