# Phase 3: AWS Connect Voice Integration - Implementation Plan

**Date:** October 17, 2025
**Status:** 📋 Planning Phase
**Goal:** Enable voice calls with Indian phone number using Bedrock Agents

---

## 📋 Executive Summary

This document outlines the implementation plan for Phase 3: integrating AWS Connect with your existing Bedrock multi-agent system to enable **voice calling with an Indian phone number**.

### What You'll Get

✅ **Indian phone number** for inbound customer calls
✅ **AI-powered IVR** using existing Bedrock Agents
✅ **Natural conversation** handling (no rigid menu trees)
✅ **Multi-step scheduling** over phone
✅ **Same backend** as SMS and chat (unified)
✅ **Call recording & analytics** built-in

---

## 🎯 Objectives

1. **Claim Indian Phone Number** - Get DID (Direct Inward Dialing) number in India
2. **Set Up AWS Connect** - Contact center instance in AWS
3. **Integrate Amazon Lex** - Voice-to-text processing
4. **Connect Bedrock Agents** - Reuse existing supervisor + collaborators
5. **Create Contact Flows** - IVR call routing logic
6. **Test End-to-End** - Validate voice scheduling works
7. **Go Live** - Launch with monitoring

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CUSTOMER                                │
│                   📞 +91 XXXX XXXXXX                            │
│                    (Indian Number)                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ (Voice Call)
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                    AWS CONNECT INSTANCE                         │
│                                                                 │
│  • Telephony handling          • Call routing                  │
│  • IVR/Contact flows           • Call recording                │
│  • Queue management            • Real-time analytics           │
│                                                                 │
│  Region: ap-south-1 (Mumbai)                                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ (Speech Audio)
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                      AMAZON LEX V2                              │
│                                                                 │
│  • Speech-to-text (ASR)        • Intent recognition            │
│  • Natural language processing  • Slot filling                 │
│  • Context management          • SSML voice synthesis          │
│                                                                 │
│  Language: English (India) / Hindi (optional)                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ (Structured Intent + Text)
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│              BEDROCK SUPERVISOR AGENT (Existing)                │
│                                                                 │
│  ID: 5VTIWONUMO  |  Model: Claude Sonnet 4.5                   │
│                                                                 │
│  Routes to → Scheduling | Information | Notes | Chitchat       │
│                                                                 │
│  ✅ NO CHANGES NEEDED - Same agent as SMS/Chat                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                   LAMBDA FUNCTIONS (Existing)                   │
│                                                                 │
│  • scheduling-actions (6 actions)                              │
│  • information-actions (4 actions)                             │
│  • notes-actions (2 actions)                                   │
│                                                                 │
│  ✅ NO CHANGES NEEDED - Same Lambda as SMS/Chat                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                   PF360 API / DATABASES                         │
│                                                                 │
│  • Aurora PostgreSQL       • Redis Cache                       │
│  • DynamoDB (sessions)     • PF360 APIs                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Implementation Approach

### Strategy: Extend Existing System (Recommended)

**Why This Approach:**
✅ **Reuse 100% of existing Bedrock Agents** - No duplication
✅ **Same Lambda functions** - Voice, SMS, chat use identical backend
✅ **Unified conversation memory** - Customer can switch channels mid-conversation
✅ **Consistent responses** - Same AI model and prompts
✅ **Faster implementation** - Only add Amazon Connect + Lex layer

**What's New:**
- Amazon Connect instance (contact center)
- Amazon Lex bot (voice interface to Bedrock)
- Contact flows (IVR call routing)
- Indian phone number

**What Stays the Same:**
- All 5 Bedrock Agents (supervisor + 4 collaborators)
- All 12 Lambda actions
- All databases (Aurora, DynamoDB, Redis)
- PF360 API integrations

---

## 📝 Implementation Steps

### Phase 3.1: AWS Connect Setup (Week 1)

#### Step 1: Create AWS Connect Instance

**Region:** `ap-south-1` (Mumbai, India) - for lowest latency to Indian customers

**Process:**
1. Open AWS Connect console: https://console.aws.amazon.com/connect/
2. Click **Create instance**
3. Configure:
   - **Identity management:** Store users in Amazon Connect
   - **Instance alias:** `scheduling-agent-india`
   - **Administrator:** Create new admin user
   - **Telephony:** ✅ Enable both inbound and outbound calls
   - **Data storage:**
     - ✅ Call recordings (S3)
     - ✅ Exported reports (S3)
     - Retention: 90 days
4. Click **Create instance**

**Time:** 5-10 minutes
**Cost:** $0 (pay-as-you-go, no upfront)

---

#### Step 2: Claim Indian Phone Number

⚠️ **IMPORTANT:** Indian phone numbers in AWS Connect require special approval process

**Prerequisites:**
1. **Business registration in India** OR international company with Indian business presence
2. **Address verification** - Indian business address
3. **Letter of Authorization (LOA)** - Document authorizing phone number use
4. **Compliance documentation** - Varies by carrier

**Process:**

**Option A: Indian Local Number (DID)**
- Format: +91 XXXX XXXXXX (10 digits)
- Type: Geographic (city-specific) or National
- Best for: Local presence
- Approval time: 7-15 business days
- Cost: ~₹500-1000/month + usage

**Option B: Toll-Free Number**
- Format: +91 1800 XXX XXXX
- Type: National toll-free
- Best for: Customer service
- Approval time: 15-30 business days
- Cost: ~₹2000-3000/month + usage

**Recommended:** Start with **Local DID** (faster approval)

**Steps:**
1. In AWS Connect console → **Channels** → **Phone numbers**
2. Click **Claim a number**
3. Select:
   - **Country:** India (+91)
   - **Type:** DID (Direct Inward Dialing)
   - **Number:** Select from available
4. Submit **compliance documents:**
   - Business registration certificate
   - Address proof
   - Authorized signatory details
   - Use case description
5. Wait for approval (7-15 days)

**Alternative (Faster):** Use **Twilio + AWS Connect integration** for immediate Indian number access (see alternative approach below)

---

#### Step 3: Configure AWS Connect Instance

**Enable Required Features:**

1. **Contact Lens** (Analytics)
   - Real-time call transcription
   - Sentiment analysis
   - Keyword detection

2. **Flow Logging**
   - CloudWatch logs for debugging

3. **Contact Attributes**
   - Pass customer phone number to Lex
   - Session data to Bedrock

4. **Hours of Operation**
   - Set business hours (e.g., 9 AM - 6 PM IST)
   - After-hours routing

---

### Phase 3.2: Amazon Lex Integration (Week 2)

#### Step 4: Create Lex Bot for Voice

**Purpose:** Acts as bridge between Connect (voice) and Bedrock (AI)

**Bot Configuration:**
```yaml
Bot Name: SchedulingAgentVoice
Bot Type: Lex V2
Language: English (India) en_IN
Voice: Aditi (Indian English, Female) or Raveena (Hindi-accented English)
Session Timeout: 5 minutes
```

**Intents to Create:**

1. **ScheduleAppointment**
   - Sample utterances:
     - "I want to schedule an appointment"
     - "Book a flooring installation"
     - "Schedule me for next Tuesday"
   - Slots: project_type, date, time

2. **CheckAppointment**
   - "What's my appointment status?"
   - "When is my next appointment?"

3. **Reschedule**
   - "I need to reschedule"
   - "Change my appointment date"

4. **GetInformation**
   - "What are your working hours?"
   - "Tell me about my flooring project"

5. **AddNote**
   - "Add a note"
   - "I have a special request"

6. **FallbackIntent**
   - Routes everything to Bedrock Agent for complex queries

**Key Configuration:**

```
Fulfillment:
  Type: AWS Lambda
  Function: arn:aws:lambda:ap-south-1:xxxx:function:lex-bedrock-bridge

This Lambda will:
1. Receive intent + slots from Lex
2. Format as Bedrock Agent input
3. Invoke Bedrock Supervisor Agent
4. Format Bedrock response for voice
5. Return to Lex → Connect → Customer
```

---

#### Step 5: Create Lex-to-Bedrock Bridge Lambda

**Purpose:** Translates Lex requests to Bedrock Agent invocations

**New Lambda Function:** `lex-bedrock-bridge`

**Functionality:**
```python
def lambda_handler(event, context):
    # 1. Extract from Lex
    intent_name = event['sessionState']['intent']['name']
    slots = event['sessionState']['intent']['slots']
    user_message = event['inputTranscript']
    phone_number = event['sessionAttributes'].get('phone_number')

    # 2. Invoke Bedrock Supervisor Agent
    response = bedrock_agent_runtime.invoke_agent(
        agentId='5VTIWONUMO',
        agentAliasId='HH2U7EZXMW',
        sessionId=f"voice-{phone_number}",
        inputText=user_message
    )

    # 3. Format for voice (SSML)
    voice_response = format_for_voice(response)

    # 4. Return to Lex
    return {
        'sessionState': {
            'dialogAction': {'type': 'Close'},
            'intent': {'state': 'Fulfilled'}
        },
        'messages': [{
            'contentType': 'SSML',
            'content': voice_response
        }]
    }
```

**Voice-Specific Formatting:**
- Remove markdown formatting
- Convert dates: "2025-10-20" → "October twentieth"
- Convert times: "14:00" → "two PM"
- Add pauses: `<break time="500ms"/>`
- Emphasize key info: `<emphasis>confirmed</emphasis>`

---

### Phase 3.3: Connect Contact Flows (Week 2)

#### Step 6: Create Main IVR Contact Flow

**Flow Name:** `SchedulingAgentMainFlow`

**Flow Logic:**

```
START
  ↓
Set logging and recording behavior
  ↓
Play prompt: "Thank you for calling ProjectsForce 360"
  ↓
Get customer phone number
  → Option 1: Use caller ID (ANI)
  → Option 2: Ask customer to say their number
  ↓
Store phone_number in contact attributes
  ↓
Check business hours
  ├─ During hours → Continue
  └─ After hours → Play message, offer to schedule callback, END
  ↓
Get customer input (Lex bot)
  ↓
Lex processes voice → Invokes Bedrock via Lambda
  ↓
Play Bedrock response (TTS)
  ↓
Loop back to "Get customer input" until:
  • Customer says "goodbye"
  • Conversation completes
  • Timeout (5 minutes)
  ↓
Play prompt: "Thank you for calling. Goodbye!"
  ↓
END
```

**Contact Flow Components:**

1. **Set Recording Behavior**
   - Enable call recording
   - Store in S3
   - Enable Contact Lens

2. **Play Prompt Block**
   - Audio: Pre-recorded greeting (better quality)
   - Or TTS: "Welcome to ProjectsForce 360"

3. **Get Customer Input**
   - Type: Amazon Lex
   - Bot: SchedulingAgentVoice
   - Intent: (All)
   - Session attributes: phone_number, call_id

4. **Check Hours of Operation**
   - If closed: Route to voicemail or callback queue

5. **Loop Logic**
   - After each Lex interaction, check for:
     - "complete" intent
     - Customer hangup
     - Timeout

---

### Phase 3.4: Testing & Validation (Week 3)

#### Step 7: Test Scenarios

**Test Case 1: Simple Scheduling**
```
Call flow:
1. Customer: "I want to schedule an appointment"
2. Agent: "I'd be happy to help. What type of service?"
3. Customer: "Flooring installation"
4. Agent: "What date works for you?"
5. Customer: "Next Monday"
6. Agent: "What time?"
7. Customer: "10 AM"
8. Agent: "Perfect! You're scheduled for Monday, October 21st at 10 AM"
```

**Expected:**
- ✅ Lex recognizes "schedule appointment" intent
- ✅ Bedrock asks clarifying questions
- ✅ Lambda confirms appointment
- ✅ Voice response is natural

**Test Case 2: Complex Query**
```
Customer: "I need to reschedule my flooring installation from next week
           to the following week, and also what's the weather forecast?"
```

**Expected:**
- ✅ Bedrock breaks down multi-intent request
- ✅ Routes to scheduling collaborator for reschedule
- ✅ Routes to information collaborator for weather
- ✅ Coordinates responses naturally

**Test Case 3: Interruption/Barge-In**
```
Agent: "Let me check available dates for you. I have October—"
Customer: "Actually, I need to cancel"
```

**Expected:**
- ✅ Lex allows barge-in
- ✅ Bedrock switches context to cancellation
- ✅ Previous context is abandoned

---

### Phase 3.5: Production Launch (Week 4)

#### Step 8: Pre-Launch Checklist

- [ ] Indian phone number approved and claimed
- [ ] AWS Connect instance configured
- [ ] Lex bot tested with 20+ sample conversations
- [ ] Bedrock Agent integration verified
- [ ] Lambda bridge function deployed
- [ ] Contact flows published
- [ ] Call recording enabled
- [ ] CloudWatch alarms configured
- [ ] Load testing completed (100 concurrent calls)
- [ ] Disaster recovery plan documented
- [ ] Customer-facing phone number publicized

---

## 🌏 Indian Phone Number: Detailed Setup

### Compliance Requirements for India

**Mandatory Documents:**
1. **Business Registration**
   - Certificate of Incorporation
   - GST Registration Certificate
   - PAN Card (company)

2. **Address Proof**
   - Utility bill (electricity/water)
   - Lease agreement
   - Rent receipt

3. **Authorized Signatory**
   - Director/partner ID proof (Aadhaar/Passport)
   - Board resolution (for companies)

4. **Use Case Declaration**
   - Letter describing call center purpose
   - Customer service use case
   - Expected call volume

5. **Letter of Authorization (LOA)**
   - Letterhead document authorizing AWS/carrier
   - Signed by director/authorized signatory

### Submission Process

1. **Prepare Documents**
   - Scan all documents
   - Sign LOA on company letterhead
   - Prepare use case description

2. **Submit via AWS Support**
   - Open support case: "Request Indian DID Number"
   - Attach all documents
   - Specify:
     - Region: ap-south-1
     - City: [Your city]
     - Number type: Geographic DID
     - Expected usage: Customer service IVR

3. **Carrier Review**
   - AWS forwards to Indian telecom carrier
   - Carrier validates documents
   - May request additional info

4. **Approval & Activation**
   - Approval notification (7-15 days)
   - Number appears in AWS Connect console
   - Claim and assign to instance

### Alternative: Twilio → AWS Connect (Faster)

If you need to launch quickly before Indian DID approval:

**Option:** Use Twilio Indian number → forward to AWS Connect

**Setup:**
1. Get Indian number from Twilio (instant, easier approval)
2. Configure Twilio to forward calls to AWS Connect
3. AWS Connect SIP trunk integration
4. Later migrate to native AWS Connect number

**Pros:**
- ✅ Much faster (1-2 days vs 2 weeks)
- ✅ Easier compliance
- ✅ Same functionality

**Cons:**
- ❌ Extra cost (~$0.01/min forwarding fee)
- ❌ Slightly higher latency
- ❌ One more service to manage

---

## 💰 Cost Estimates (India Region)

### Monthly Costs (500 calls/month, 5 min avg)

| Component | Usage | Rate | Cost |
|-----------|-------|------|------|
| **AWS Connect** | 2,500 min | $0.038/min | $95.00 |
| **Indian DID Number** | 1 number | ₹800/month | $9.60 |
| **Inbound Telephony (India)** | 2,500 min | $0.006/min | $15.00 |
| **Amazon Lex** | 500 requests | $0.00075/req | $0.38 |
| **Bedrock (Claude Sonnet 4.5)** | 500 convos × 2K tokens | $0.015/1K tokens | $15.00 |
| **Amazon Transcribe** | 2,500 min | $0.024/min | $60.00 |
| **Contact Lens** | 2,500 min | $0.015/min | $37.50 |
| **S3 Call Recording** | 5 GB | $0.025/GB | $0.13 |
| **Lambda (Bridge)** | 500 invokes | $0.20/1M | $0.10 |
| **CloudWatch Logs** | 10 GB | $0.50/GB | $5.00 |
| **Total** | | | **$237.71/month** |

**Per Call Cost:** $0.48

**Annual Cost (6,000 calls):** ~$2,900

### Scaling Costs

| Scale | Calls/Month | Est. Cost/Month |
|-------|-------------|-----------------|
| Small | 500 | $240 |
| Medium | 2,000 | $850 |
| Large | 10,000 | $3,800 |
| Enterprise | 50,000 | $17,500 |

---

## ⚠️ Key Challenges & Solutions

### Challenge 1: Indian Phone Number Approval Time

**Problem:** 7-15 day approval process
**Solutions:**
1. Submit documents early (before coding)
2. Use Twilio as interim solution
3. Start with US number for testing

### Challenge 2: Voice Response Formatting

**Problem:** Bedrock returns markdown/structured text, not voice-friendly
**Solution:** Lex-to-Bedrock bridge Lambda formats responses:
- Strip markdown
- Convert dates/times to spoken format
- Add SSML pauses
- Limit response length

### Challenge 3: Multi-Step Conversations

**Problem:** Voice timeouts (5 sec silence → hang up)
**Solution:**
- Bedrock prompt: "Keep responses concise"
- Lex barge-in enabled
- Explicit prompts: "Would you like to continue?"

### Challenge 4: Accents & Speech Recognition

**Problem:** Indian English accents may not be recognized well
**Solution:**
- Use Lex `en_IN` (English India) language model
- Train Lex with Indian accent samples
- Add clarification prompts: "Did you say Monday or Sunday?"

---

## 📊 Success Metrics

### KPIs to Track

1. **Call Success Rate**
   - Target: >85% of calls complete without escalation

2. **Speech Recognition Accuracy**
   - Target: >90% intent recognition

3. **Average Handle Time (AHT)**
   - Target: <4 minutes per call

4. **Customer Satisfaction (CSAT)**
   - Target: >4.0/5.0

5. **Appointment Booking Rate**
   - Target: >70% of calls result in confirmed appointment

6. **Cost per Call**
   - Target: <$0.50/call

### Monitoring Dashboard

**CloudWatch Metrics:**
- ConcurrentCalls
- CallsPerInterval
- ContactFlowErrors
- LexIntentMatches
- BedrockAgentInvocations
- AverageCallDuration

**Alarms to Set:**
- ConcurrentCalls >80% of quota
- ContactFlowErrors >5/hour
- LexIntentMatches <70%
- AverageCallDuration >6 minutes

---

## 🗓️ Implementation Timeline

### Week 1: AWS Connect Setup
- **Day 1-2:** Create Connect instance, configure settings
- **Day 3:** Submit Indian phone number application
- **Day 4-5:** Set up S3, IAM roles, CloudWatch

### Week 2: Lex & Lambda Integration
- **Day 1-2:** Create Lex bot, configure intents
- **Day 3-4:** Build Lex-to-Bedrock bridge Lambda
- **Day 5:** Test Lex ↔ Bedrock integration

### Week 3: Contact Flows & Testing
- **Day 1-2:** Build main IVR contact flow
- **Day 3-4:** Test with 20+ scenarios
- **Day 5:** User acceptance testing (UAT)

### Week 4: Launch
- **Day 1:** Indian number approval (if ready)
- **Day 2:** Production configuration
- **Day 3:** Soft launch (internal testing)
- **Day 4:** Public launch
- **Day 5:** Monitor & optimize

**Total Time:** 4 weeks (parallel to phone number approval)

---

## 🎓 Team Requirements

### Skills Needed

1. **AWS Architect** (20 hours)
   - AWS Connect configuration
   - Lex bot design
   - Contact flow creation

2. **Backend Developer** (15 hours)
   - Lex-to-Bedrock bridge Lambda
   - Voice response formatting
   - Integration testing

3. **DevOps Engineer** (10 hours)
   - Infrastructure setup
   - Monitoring & alarms
   - Deployment automation

4. **QA Engineer** (15 hours)
   - Test scenario creation
   - Voice testing
   - Load testing

**Total Effort:** ~60 hours (1.5 engineer-months)

---

## 📚 Resources & Documentation

### AWS Documentation
- [AWS Connect Documentation](https://docs.aws.amazon.com/connect/)
- [Amazon Lex V2 Guide](https://docs.aws.amazon.com/lexv2/)
- [Bedrock Agent Runtime API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_InvokeAgent.html)
- [Connect + Lex Integration](https://docs.aws.amazon.com/connect/latest/adminguide/amazon-lex.html)

### Sample Code
- [AWS Connect + Bedrock Voice Integration](https://github.com/aws-samples/sample-amazon-connect-bedrock-agent-voice-integration)
- [Lex Lambda Fulfillment](https://docs.aws.amazon.com/lexv2/latest/dg/lambda.html)

### Indian Telecom Regulations
- [TRAI Guidelines](https://www.trai.gov.in/)
- [DID Number Allocation](https://dot.gov.in/)

---

## ✅ Next Steps (Start Here!)

### Immediate Actions (This Week)

1. **Read:** Phase 3 research document (`PHASE3_AWS_CONNECT_RESEARCH.md`)
2. **Read:** Indian phone setup guide (`PHASE3_INDIAN_PHONE_SETUP.md`)
3. **Gather:** Business documents for phone number application
4. **Create:** AWS Connect instance in `ap-south-1` region
5. **Submit:** Indian DID number request with documents

### Parallel Work (While Waiting for Phone Approval)

1. **Build:** Lex bot with intents
2. **Develop:** Lex-to-Bedrock bridge Lambda
3. **Create:** Contact flows
4. **Test:** Using US test number

### After Phone Number Approved

1. **Claim:** Indian number in AWS Connect
2. **Assign:** Number to main contact flow
3. **Test:** End-to-end with real Indian number
4. **Launch:** Publicize number to customers

---

## 🆘 Support & Escalation

### AWS Support Cases
- For phone number issues: "Telephony & Connect"
- For Lex issues: "Machine Learning & AI"
- For Bedrock issues: "Bedrock Agents"

### Internal Support
- Check `docs/` directory for guides
- Review `PHASE3_AWS_CONNECT_RESEARCH.md` for deep dive
- Test with AWS sample code first

---

**Document Version:** 1.0
**Last Updated:** October 17, 2025
**Status:** Ready for Implementation

**Next Document:** [PHASE3_INDIAN_PHONE_SETUP.md](PHASE3_INDIAN_PHONE_SETUP.md) - Detailed Indian phone number guide
