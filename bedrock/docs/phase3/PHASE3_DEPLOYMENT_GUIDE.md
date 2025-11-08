# Phase 3: Voice Integration Deployment Guide

**Complete guide for deploying AWS Connect + Bedrock voice integration**

---

## Overview

Phase 3 adds voice/phone call capabilities to your Bedrock multi-agent system. Customers can call a phone number and interact with your AI scheduling assistant using natural voice conversation.

### Architecture

```
Customer Phone
    ↓
AWS Connect Instance (Contact Center)
    ↓
Amazon Lex V2 Bot (Speech-to-Text + Intent Recognition)
    ↓
Lambda: lex-fulfillment (Simple queries)
    ↓
Lambda: voice-bedrock-bridge (Complex queries)
    ↓
Bedrock Supervisor Agent (Existing from Phase 1)
    ↓
Collaborator Agents + Lambda Actions
    ↓
Backend APIs + DynamoDB
```

---

## Prerequisites

Before deploying Phase 3, ensure you have:

- [x] **Phase 1 Complete**: Bedrock agents deployed and working
- [x] **AWS CLI**: Version 2.x configured with credentials
- [x] **Terraform**: Version 1.0+ installed
- [x] **Python 3.11**: For Lambda functions
- [x] **AWS Permissions**: Access to Connect, Lex, Lambda, IAM
- [x] **Phone Number Budget**: ~$3-5/month for toll-free number
- [x] **Region**: us-east-1 (for USA customers)

---

## Deployment Steps

### Step 1: Package Lambda Functions

```bash
cd bedrock

# Package lex-fulfillment
cd lambda/lex-fulfillment
zip -r deployment.zip handler.py
cd ../..

# Package voice-bedrock-bridge
cd lambda/voice-bedrock-bridge
zip -r deployment.zip handler.py
cd ../..
```

### Step 2: Run Automated Deployment

```bash
./scripts/deploy_voice_integration.sh
```

The script will:
1. ✅ Package Lambda functions
2. ✅ Deploy Terraform infrastructure (Connect, Lex, Lambdas)
3. ⏸️ Pause for manual phone number claiming
4. ⏸️ Pause for manual contact flow import
5. ⏸️ Pause for manual phone-to-flow association
6. ✅ Complete deployment

### Step 3: Manual Steps (Required)

#### 3a. Claim Phone Number

AWS Connect phone numbers must be claimed through the console:

1. Open the link provided by the deployment script
2. Click **"Claim a number"**
3. Select **"Toll free"** (recommended for customer calls)
4. Choose DID: **United States +1**
5. Select an available toll-free number (e.g., +1-800-XXX-XXXX)
6. Click **"Claim phone number"**
7. **Note the phone number** for later

**Why toll-free?** No cost to customers, professional appearance.

#### 3b. Import Contact Flow

1. Open AWS Connect → Contact Flows (link from script)
2. Click **"Create contact flow"**
3. Name it: `pf-main-inbound-flow`
4. Click dropdown next to **"Save"** → **"Import flow (beta)"**
5. Select file: `infrastructure/voice/contact-flows/main-inbound-flow-configured.json`
6. Click **"Import"**
7. Review the flow (should show all blocks connected)
8. Click **"Publish"**
9. Note the Contact Flow ID from the URL

#### 3c. Associate Phone with Flow

1. Go back to Phone Numbers
2. Click on your claimed phone number
3. Under **"Contact flow / IVR"**, select: `pf-main-inbound-flow`
4. Click **"Save"**

---

## Configuration

### Environment Variables

The Lambda functions use these environment variables (auto-configured by Terraform):

**lex-fulfillment:**
```bash
DYNAMODB_TABLE=pf-session-data-dev
INFORMATION_LAMBDA=pf-information-actions
VOICE_BRIDGE_LAMBDA=pf-voice-bedrock-bridge-dev
AWS_REGION=us-east-1
```

**voice-bedrock-bridge:**
```bash
SUPERVISOR_AGENT_ID=[AUTO-DETECTED]
SUPERVISOR_AGENT_ALIAS_ID=TSTALIASID
DYNAMODB_TABLE=pf-session-data-dev
AWS_REGION=us-east-1
```

### Phone Number Configuration

The phone number is configurable in `infrastructure/terraform/voice/variables.tf`:

```hcl
variable "connect_phone_number" {
  description = "Phone number to associate with AWS Connect"
  type        = string
  default     = "+18005551234"  # Update with your actual number
}
```

**Update this after claiming your number.**

---

## Testing

### Test 1: Direct Lex Bot Test

Test Lex bot without making a phone call:

```bash
aws lexv2-runtime recognize-text \
  --bot-id [BOT_ID] \
  --bot-alias-id [ALIAS_ID] \
  --locale-id en_US \
  --session-id test-session-1 \
  --text "show me my projects"
```

Expected response: List of projects or prompt for customer ID.

### Test 2: Run Automated Test Suite

```bash
cd tests
python3 test_voice_integration.py
```

This tests:
- ✅ Lex bot deployment
- ✅ Intent recognition
- ✅ Lambda fulfillment
- ✅ Bedrock bridge integration
- ✅ Multi-turn conversations

### Test 3: Live Phone Call Test

**Test Scenarios:**

1. **Simple Query** (handled by Lex):
   - Call: Your phone number
   - Say: "Show me my projects"
   - Expected: List of projects read aloud

2. **Complex Query** (routed to Bedrock):
   - Call: Your phone number
   - Say: "Schedule my most urgent project"
   - Expected: Bedrock response with project details

3. **Multi-Turn Conversation**:
   - Call: Your phone number
   - Say: "What projects do I have?"
   - Bot responds with list
   - Say: "Schedule the roofing one for Monday"
   - Expected: Scheduling flow initiated

4. **Fallback Test**:
   - Call: Your phone number
   - Say: "What's the weather like for outdoor projects?"
   - Expected: Routed to Bedrock for complex handling

---

## Monitoring

### CloudWatch Logs

**Lambda Logs:**
```bash
# Lex fulfillment logs
aws logs tail /aws/lambda/pf-lex-fulfillment-dev --follow

# Voice-Bedrock bridge logs
aws logs tail /aws/lambda/pf-voice-bedrock-bridge-dev --follow
```

**Connect Logs:**
```bash
# Contact flow logs
aws logs tail /aws/connect/[INSTANCE_ID] --follow
```

### CloudWatch Metrics

Key metrics to monitor:

| Metric | What to Watch | Target |
|--------|---------------|--------|
| `IncomingCalls` | Total calls received | Monitor growth |
| `MissedCalls` | Failed to answer | < 1% |
| `LexIntentRecognition` | Intent accuracy | > 80% |
| `LexFallbackRate` | Unrecognized queries | < 20% |
| `LambdaDuration` | Response time | < 3s |
| `BedrockLatency` | Agent response time | < 5s |

### Call Recordings

Recordings are stored in S3:

```bash
# List recordings
aws s3 ls s3://pf-call-recordings-dev-[ACCOUNT_ID]/recordings/

# Download a recording
aws s3 cp s3://pf-call-recordings-dev-[ACCOUNT_ID]/recordings/2025/01/28/recording-123.wav ./
```

**Retention:** 90 days (configurable in Terraform)

---

## Troubleshooting

### Problem: Calls don't connect

**Check:**
1. Phone number is claimed and active
2. Contact flow is published
3. Phone number is associated with contact flow
4. Hours of operation include current time (24/7 by default)

**Fix:**
```bash
aws connect list-phone-numbers-v2 --target-arn [INSTANCE_ARN]
```

### Problem: Lex doesn't recognize speech

**Check:**
1. Lex bot is built and published
2. Bot alias is "prod"
3. Voice settings use "Joanna" (neural)

**Fix:**
```bash
# Rebuild Lex bot
aws lexv2-models build-bot-locale \
  --bot-id [BOT_ID] \
  --bot-version DRAFT \
  --locale-id en_US
```

### Problem: Lambda timeout errors

**Check CloudWatch Logs:**
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/pf-voice-bedrock-bridge-dev \
  --filter-pattern "Task timed out"
```

**Fix:** Increase timeout in Terraform:
```hcl
resource "aws_lambda_function" "voice_bedrock_bridge" {
  timeout = 120  # Increase from 60 to 120
}
```

### Problem: Bedrock agent not responding

**Check:**
1. Supervisor agent is deployed (Phase 1)
2. Lambda has `bedrock:InvokeAgent` permission
3. Agent alias is correct (`TSTALIASID`)

**Test Bedrock directly:**
```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id [AGENT_ID] \
  --agent-alias-id TSTALIASID \
  --session-id test-123 \
  --input-text "Show me my projects"
```

### Problem: Poor call quality / choppy audio

**Check:**
1. Lex voice is "neural" (not "standard")
2. Lambda cold starts (first call may be slow)
3. Network latency (all resources in same region?)

**Fix:** Pre-warm Lambdas with CloudWatch Events:
```bash
# Create EventBridge rule to invoke Lambda every 5 minutes
aws events put-rule --name warm-lex-fulfillment \
  --schedule-expression "rate(5 minutes)"
```

---

## Architecture Details

### Component Breakdown

**AWS Connect Instance:**
- Handles inbound phone calls
- Manages call routing and queue
- Records calls to S3
- Integrates with Lex for speech-to-text

**Amazon Lex V2 Bot:**
- Converts speech to text
- Recognizes intents (Welcome, ProjectInquiry, ScheduleAppointment, UrgentRequest)
- Extracts slots (ProjectID, dates, times)
- Routes to appropriate fulfillment

**lex-fulfillment Lambda:**
- Handles simple, fast queries
- Direct API calls (no Bedrock overhead)
- Returns responses < 3 seconds

**voice-bedrock-bridge Lambda:**
- Handles complex, conversational queries
- Invokes Bedrock Supervisor Agent
- Formats responses for voice (removes markdown, shortens text)
- Manages session state in DynamoDB

**Contact Flow:**
- Welcome message
- Customer lookup by phone number
- Lex bot invocation
- Intent routing (simple vs complex)
- Response playback
- Loop for multi-turn conversations
- Goodbye and disconnect

### Data Flow Example

**User says:** "Schedule my most urgent project"

1. AWS Connect receives call
2. Contact flow plays welcome message
3. Lex bot recognizes speech → `UrgentRequest` intent
4. Contact flow routes to `voice-bedrock-bridge` Lambda (complex query)
5. Lambda invokes Bedrock Supervisor Agent
6. Supervisor routes to Scheduling Collaborator
7. Scheduling agent triggers `schedule-urgent-project` Step Function
8. Step Function finds urgent project, returns details
9. Lambda formats response for voice
10. Contact flow reads response to customer
11. Asks "Anything else?" and loops

**Total time:** ~8 seconds

---

## Cost Estimation

Monthly costs for **1,000 calls** (5 min average):

| Service | Usage | Cost |
|---------|-------|------|
| AWS Connect | 1000 calls × 5 min | $90 |
| Phone Number (Toll-free) | 1 DID | $3 |
| Lex V2 | ~3000 requests | $2.25 |
| Lambda (lex-fulfillment) | 1000 invocations | $0.20 |
| Lambda (voice-bedrock-bridge) | 1000 invocations | $0.40 |
| Bedrock Agents | ~1000 invocations | $50 |
| S3 (recordings) | 1000 × 5min WAV | $10 |
| CloudWatch Logs | 10GB | $5 |
| **Total** | | **~$160/month** |

**Per-call cost:** ~$0.16

**Scaling:** Mostly linear with call volume.

---

## Next Steps

After successful deployment:

### 1. Optimize Lex Bot
- Add more sample utterances based on real call data
- Tune confidence threshold (default: 0.70)
- Add custom slot types for project categories

### 2. Enhance Voice Responses
- Add SSML for better speech (pauses, emphasis)
- Implement dynamic voice selection (male/female)
- Add call transfer to human agents

### 3. Analytics & Reporting
- Build CloudWatch dashboard
- Track top intents and fallback rate
- Measure customer satisfaction (post-call survey)

### 4. Production Hardening
- Enable call recording encryption
- Set up alerting for Lambda errors
- Implement rate limiting for API calls
- Add DTMF fallback (keypad input)

### 5. Advanced Features (Phase 3.1)
- Outbound calling for appointment reminders
- SMS integration with voice (multi-channel)
- Call transcription and sentiment analysis
- Real-time human agent handoff

---

## Configuration Reference

### Terraform Variables

All configurable in `infrastructure/terraform/voice/variables.tf`:

```hcl
variable "region" {
  default = "us-east-1"
}

variable "prefix" {
  default = "pf"
}

variable "environment" {
  default = "dev"
}

variable "connect_phone_number" {
  default = "+18005551234"  # UPDATE THIS
}

variable "supervisor_agent_id" {
  # Auto-detected during deployment
}
```

### Lex Bot Intents

| Intent Name | Purpose | Fulfillment |
|-------------|---------|-------------|
| `Welcome` | Greeting | lex-fulfillment |
| `ProjectInquiry` | List projects | lex-fulfillment |
| `ScheduleAppointment` | Book appointment | voice-bedrock-bridge |
| `UrgentRequest` | Urgent scheduling | voice-bedrock-bridge |
| `FallbackIntent` | Unrecognized query | voice-bedrock-bridge |

### Voice Settings

- **Voice ID:** Joanna (female, professional)
- **Engine:** Neural (better quality than standard)
- **Speech Rate:** 100% (normal speed)
- **Language:** en_US

---

## Support

For issues during deployment:

1. **Check logs first**: CloudWatch Logs for all services
2. **Review Terraform output**: Look for failed resources
3. **Test components individually**: Lex → Lambda → Bedrock
4. **Consult AWS documentation**:
   - [AWS Connect User Guide](https://docs.aws.amazon.com/connect/)
   - [Lex V2 Developer Guide](https://docs.aws.amazon.com/lexv2/)
   - [Bedrock Agents Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)

---

**Phase 3 Version:** 1.0
**Last Updated:** 2025-10-28
**Region Support:** us-east-1 (USA customers)
**Dependencies:** Phase 1 (Bedrock agents)
