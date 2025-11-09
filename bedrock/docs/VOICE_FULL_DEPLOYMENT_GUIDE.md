# AWS Connect Voice Integration - Full Deployment Guide

**Date:** November 9, 2025
**Phone Number:** +1-833-877-1422
**Deployment Type:** Full (Automated)

---

## Overview

This guide covers the **full automated deployment** of AWS Connect voice integration for ProjectForce Bedrock agents. Unlike the minimal deployment, this fully automates the creation of:

- ✅ AWS Connect instance
- ✅ Amazon Lex bot (with 5 intents)
- ✅ Lambda functions (lex-fulfillment, voice-bedrock-bridge)
- ✅ Phone number configuration
- ✅ Contact flows
- ✅ DynamoDB session storage
- ✅ S3 call recordings
- ✅ IAM roles and permissions

**Phone Number:** +1-833-877-1422 (Toll-Free)

---

## Prerequisites

Before running the full deployment:

### 1. Core Agents Deployed

```bash
# Ensure core Bedrock agents are deployed
./scripts/DEPLOY.sh
```

**Required agents:**
- Supervisor
- SchedulingAgent
- pf-information
- pf-chitchat

### 2. Collaboration Setup

```bash
# Ensure agent collaboration is configured
./scripts/SETUP_COLLABORATION.sh
```

This creates v1 aliases and associates collaborator agents with the Supervisor.

### 3. AWS CLI Configured

```bash
aws sts get-caller-identity
# Should return your account: 618048437522
```

### 4. Required Permissions

Your AWS user/role needs permissions for:
- AWS Connect (create instance, claim numbers)
- Amazon Lex V2 (create bots, intents, slots)
- Lambda (create functions, add permissions)
- IAM (create roles, attach policies)
- DynamoDB (create tables)
- S3 (create buckets)
- KMS (create keys)
- CloudWatch (create log groups)

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Customer Calls                           │
│                  +1-833-877-1422                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              AWS Connect Instance                           │
│  - Receives call                                            │
│  - Plays greeting                                           │
│  - Routes to Lex bot                                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│            Amazon Lex Bot                                   │
│  - Understands speech (ASR)                                 │
│  - Detects intent                                           │
│  - Invokes Lambda fulfillment                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│        Lambda: pf-lex-fulfillment-dev                       │
│  - Routes simple intents (Welcome, Help, End)               │
│  - Hands off complex queries to voice-bridge                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│     Lambda: pf-voice-bedrock-bridge-dev                     │
│  - Invokes Bedrock Supervisor agent                         │
│  - Manages session state in DynamoDB                        │
│  - Formats response for voice (TTS)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         Bedrock Supervisor Agent                            │
│  - Routes to specialist agents:                             │
│    • SchedulingAgent (appointments)                         │
│    • pf-information (weather)                               │
│    • pf-chitchat (greetings)                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Response to Customer                           │
│  - Text-to-Speech (TTS)                                     │
│  - Call recording saved to S3                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Deployment Steps

### Step 1: Run Full Deployment Script

```bash
cd /path/to/schedulingAgent-bb/bedrock
./scripts/DEPLOY_VOICE_FULL.sh
```

**What it does:**

1. **Loads agent IDs** from `config/agent_ids.json`
2. **Packages Lambda functions** with dependencies
3. **Creates Terraform configuration** with phone number
4. **Initializes Terraform** and downloads providers
5. **Plans deployment** and shows what will be created
6. **Deploys infrastructure** (requires confirmation)
7. **Saves deployment info** to `config/voice_deployment.json`

**Expected output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  AWS Connect Voice Integration - Full Deployment
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Region: us-east-1
Account: 618048437522
Environment: dev
Phone Number: +18338771422

This deployment includes:
  ✅ AWS Connect instance
  ✅ Amazon Lex bot (with 5 intents)
  ✅ Lambda functions (lex-fulfillment, voice-bridge)
  ✅ DynamoDB table for sessions
  ✅ S3 bucket for call recordings
  ✅ IAM roles and permissions
  ✅ KMS encryption for recordings
  ✅ Contact flows

[1/7] Loading Bedrock Agent IDs...
  Supervisor Agent ID: P9VCJXPIZS
  Scheduling Agent ID: OHJRRIOVDN
  Information Agent ID: M0NRSM01QE
  ChitChat Agent ID: WB5OPLGKMF
  Supervisor v1 Alias ID: TSTALIASID
✅ Agent IDs loaded

[2/7] Packaging Lambda functions...
  Packaging: lex-fulfillment
    Installing dependencies...
    ✅ Packaged: deployment.zip (13M)
  Packaging: voice-bedrock-bridge
    Installing dependencies...
    ✅ Packaged: deployment.zip (13M)
✅ Lambda functions packaged

[3/7] Creating Terraform configuration...
✅ Terraform configuration created

[4/7] Initializing Terraform...
✅ Terraform initialized

[5/7] Planning Terraform deployment...
... (shows resources to be created)
✅ Terraform plan created

[6/7] Deploying infrastructure...
Deploy infrastructure? (yes/no): yes
... (creates resources)
✅ Infrastructure deployed

[7/7] Saving deployment information...
✅ Deployment info saved to: config/voice_deployment.json

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Deployment Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

What was deployed:
  ✅ AWS Connect Instance: abc123-def456
  ✅ Phone Number: +18338771422
  ✅ Lex Bot: xyz789
  ✅ Lambda: pf-lex-fulfillment-dev
  ✅ Lambda: pf-voice-bedrock-bridge-dev
  ✅ DynamoDB: pf-session-data-dev
  ✅ S3: pf-call-recordings-dev-618048437522
```

### Step 2: Test the Deployment

**Call the phone number:**
```
📞 +1-833-877-1422
```

**Expected conversation:**
```
System: "Thank you for calling ProjectForce. Please hold while we connect you..."
Bot: "Hello! Welcome to ProjectForce. I'm your AI scheduling assistant.
      How can I help you today?"

You: "I need to schedule an appointment"
Bot: "I can help you schedule. What's your project ID?"

You: "12345"
Bot: "Let me look that up for you..."
Bot: "I found project 12345 at 123 Main Street. When would you like to schedule?"

You: "Next Tuesday"
Bot: "I have availability on Tuesday, January 14th at 9:00 AM, 1:00 PM,
      and 3:00 PM. Which time works best for you?"

You: "1 PM"
Bot: "Perfect! I've scheduled your appointment for Tuesday, January 14th
      at 1:00 PM. You'll receive a confirmation. Is there anything else?"

You: "No, that's all"
Bot: "Great! Thanks for calling. Have a wonderful day!"
```

---

## Resources Created

### AWS Connect

**Instance:**
- Name: `pf-scheduling-assistant-dev`
- Type: Connect Managed
- Inbound calls: Enabled
- Outbound calls: Disabled
- Call recordings: Enabled
- Contact flows: Auto-created

**Console URL:**
```
https://console.aws.amazon.com/connect/v2/app/instances/<INSTANCE_ID>/admin
```

### Amazon Lex

**Bot:**
- Name: `pf-scheduling-assistant-dev`
- Locale: English (US)
- Voice: Joanna (Neural)
- Session timeout: 10 minutes

**Intents:**
1. **Welcome** - Greetings and help
2. **ProjectInquiry** - List/query projects
3. **ScheduleAppointment** - Book appointments
4. **CheckWeather** - Get weather forecast
5. **EndCall** - End conversation

**Console URL:**
```
https://console.aws.amazon.com/lexv2/home?region=us-east-1#bot/<BOT_ID>
```

### Lambda Functions

**pf-lex-fulfillment-dev:**
- Runtime: Python 3.11
- Memory: 512 MB
- Timeout: 60 seconds
- Purpose: Route intents to responses or Bedrock

**pf-voice-bedrock-bridge-dev:**
- Runtime: Python 3.11
- Memory: 512 MB
- Timeout: 120 seconds
- Purpose: Bridge to Bedrock Supervisor

### Storage

**DynamoDB Table:**
- Name: `pf-session-data-dev`
- Billing: On-demand
- TTL: Enabled (24 hours)
- Purpose: Session state management

**S3 Bucket:**
- Name: `pf-call-recordings-dev-618048437522`
- Encryption: KMS
- Versioning: Enabled
- Lifecycle: 90-day retention
- Purpose: Call recordings and transcripts

### Security

**KMS Key:**
- Purpose: Encrypt call recordings
- Rotation: Enabled
- Deletion window: 10 days

**IAM Roles:**
- `pf-lex-fulfillment-role-dev` - For Lex Lambda
- `pf-voice-bedrock-bridge-role-dev` - For bridge Lambda
- `pf-lex-bot-role-dev` - For Lex bot
- `pf-connect-role-dev` - For Connect instance

---

## Configuration Files

### voice_deployment.json

Location: `config/voice_deployment.json`

```json
{
  "deployed_at": "2025-11-09T12:00:00Z",
  "region": "us-east-1",
  "account_id": "618048437522",
  "deployment_type": "full",
  "phone_number": "+18338771422",
  "connect": {
    "instance_id": "abc123-def456",
    "instance_arn": "arn:aws:connect:us-east-1:618048437522:instance/abc123-def456",
    "phone_number": "+18338771422"
  },
  "lex": {
    "bot_id": "xyz789",
    "bot_alias_id": "TSTALIASID",
    "bot_name": "pf-scheduling-assistant-dev"
  },
  "lambda": {
    "lex_fulfillment": "pf-lex-fulfillment-dev",
    "lex_fulfillment_arn": "arn:aws:lambda:us-east-1:618048437522:function:pf-lex-fulfillment-dev",
    "voice_bridge": "pf-voice-bedrock-bridge-dev",
    "voice_bridge_arn": "arn:aws:lambda:us-east-1:618048437522:function:pf-voice-bedrock-bridge-dev"
  },
  "storage": {
    "dynamodb_table": "pf-session-data-dev",
    "call_recordings_bucket": "pf-call-recordings-dev-618048437522"
  },
  "bedrock_agents": {
    "supervisor_id": "P9VCJXPIZS",
    "supervisor_alias_id": "TSTALIASID",
    "scheduling_id": "OHJRRIOVDN",
    "information_id": "M0NRSM01QE",
    "chitchat_id": "WB5OPLGKMF"
  }
}
```

---

## Monitoring & Troubleshooting

### CloudWatch Logs

**View Lambda logs:**
```bash
# Lex fulfillment logs
aws logs tail /aws/lambda/pf-lex-fulfillment-dev --follow --region us-east-1

# Voice bridge logs
aws logs tail /aws/lambda/pf-voice-bedrock-bridge-dev --follow --region us-east-1
```

### Connect Metrics

**View real-time metrics:**
```
https://console.aws.amazon.com/connect/v2/app/instances/<INSTANCE_ID>/metrics
```

**Key metrics:**
- Calls received
- Calls handled
- Average call duration
- Error rate

### Common Issues

**Issue: "Phone number not reachable"**
- Check phone number status in Connect console
- Verify contact flow is published
- Check Lambda permissions

**Issue: "Bot not responding"**
- Check Lex bot is built and published
- Verify Lambda fulfillment is connected
- Check CloudWatch logs for errors

**Issue: "Can't invoke Bedrock agent"**
- Verify Supervisor agent is prepared
- Check IAM permissions for bedrock:InvokeAgent
- Ensure agent alias exists

---

## Cost Estimate

### Monthly Costs (Moderate Usage: 500 calls/month, 3 min avg)

**AWS Connect:**
- Usage: 500 calls × 3 min = 1,500 minutes
- Cost: 1,500 × $0.018/min = **$27.00**

**Amazon Lex:**
- Requests: 500 calls × 6 turns avg = 3,000 requests
- Cost: 3,000 × $0.00075 = **$2.25**

**Lambda:**
- Invocations: 3,000 × 2 functions = 6,000
- Cost: (minimal, within free tier) **$0.50**

**DynamoDB:**
- Requests: 6,000 reads/writes
- Storage: <1 GB
- Cost: **$0.50**

**S3:**
- Storage: 500 recordings × 5 MB = 2.5 GB
- Cost: **$0.06**

**Bedrock:**
- Invocations: 3,000
- Tokens: ~10K input, ~5K output per call
- Cost: 3,000 × ($0.03 + $0.075) = **$315.00**

**Total Monthly Cost: ~$345/month** for 500 calls

**Cost per call: ~$0.69**

---

## Cleanup

### Remove All Voice Resources

```bash
# Full cleanup (deletes everything)
./scripts/CLEANUP_VOICE_FULL.sh
```

**This will delete:**
- AWS Connect instance
- Phone number
- Lex bot
- Lambda functions
- S3 bucket (after emptying)
- DynamoDB table
- KMS keys
- IAM roles
- Contact flows

**What remains:**
- Bedrock agents (not affected)
- Core infrastructure

---

## Next Steps

### 1. Customize Contact Flows

Edit contact flows in Connect console to:
- Customize greeting message
- Add business hours routing
- Configure fallback options
- Add queue and agent routing

### 2. Add More Intents

Extend Lex bot with:
- CancelAppointment
- RescheduleAppointment
- GetProjectStatus
- RequestCallback

### 3. Enable Analytics

**Call recording analysis:**
- Enable Contact Lens
- Set up sentiment analysis
- Configure transcription

**Usage analytics:**
- CloudWatch dashboards
- Custom metrics
- Alerting

### 4. Production Hardening

- Add redundancy (multiple regions)
- Implement disaster recovery
- Set up monitoring alerts
- Configure auto-scaling
- Add security scanning

---

## Comparison: Full vs Minimal Deployment

| Feature | Full Deployment | Minimal Deployment |
|---------|----------------|-------------------|
| **AWS Connect** | ✅ Automated | ❌ Manual |
| **Lex Bot** | ✅ Automated | ❌ Manual |
| **Lambda** | ✅ Automated | ✅ Automated |
| **Contact Flows** | ✅ Auto-created | ❌ Manual |
| **Phone Config** | ✅ Configured | ❌ Manual |
| **Time to Deploy** | 10-15 min | 60-90 min |
| **Terraform** | Full | Minimal |
| **Script** | DEPLOY_VOICE_FULL.sh | DEPLOY_VOICE_MINIMAL.sh |

**Recommendation:** Use **Full Deployment** for faster, automated setup.

---

## Related Documentation

- [Minimal Deployment Guide](./AWS_CONSOLE_SETUP_GUIDE.md)
- [Voice Deployment Status](./VOICE_DEPLOYMENT_STATUS.md)
- [Deployment Scripts Reference](./DEPLOYMENT_SCRIPTS_REFERENCE.md)
- [SMS Integration Plan](./AWS_SMS_INTEGRATION_PLAN.md)

---

## Support

For issues:
1. Check CloudWatch logs
2. Verify AWS Console shows resources
3. Test Lambda functions directly
4. Review Terraform state
5. Contact AWS Support if needed
