# Phase 3: AWS Connect + Agentic AI - Research Report

**Date:** October 13, 2025
**Status:** ✅ Research Complete - Ready for Implementation Planning
**Focus:** IVR with Bedrock Agents, SMS Integration, Caller ID

---

## Executive Summary

AWS Connect provides a comprehensive cloud contact center solution that **fully supports** integration with Bedrock Agents for agentic AI-powered IVR systems. The platform includes:

✅ **Voice IVR with AI Agents** - Full Bedrock Agent integration via Amazon Lex
✅ **SMS Messaging** - Two-way SMS with unified agent workspace
✅ **Caller ID** - Outbound caller ID display (with limitations)
✅ **Real-Time Analytics** - Transcription, sentiment analysis, call recording
✅ **Scalability** - From 10 to thousands of concurrent calls

### Key Findings

| Feature | Status | Notes |
|---------|--------|-------|
| **Bedrock Agent + IVR** | ✅ Fully Supported | Via Amazon Lex integration |
| **SMS Messaging** | ✅ Supported | Separate phone number required |
| **Caller ID Display** | ⚠️ Partial | Number shows, name limited |
| **Voice + SMS Same Number** | ❌ Not Supported | Requires 2 separate numbers |
| **Real-Time Transcription** | ✅ Supported | Via Amazon Transcribe |
| **Sentiment Analysis** | ✅ Supported | Real-time with Contact Lens |
| **Call Recording** | ✅ Supported | With PII redaction |

---

## 1. AWS Connect Overview

### What is AWS Connect?

**Amazon Connect** is a cloud-based contact center service that enables organizations to provide omnichannel customer service at scale. It's a pay-as-you-go service with no upfront payments or long-term commitments.

### Key Capabilities

- **Voice Calling** - Inbound and outbound calls
- **SMS Messaging** - Two-way text messaging
- **Web Chat** - Website chat widget
- **Task Management** - Routing and workflow automation
- **AI-Powered Features** - Real-time transcription, sentiment analysis, call summarization
- **Agent Workspace** - Unified interface for all channels

---

## 2. Bedrock Agent Integration for IVR

### Architecture Overview

```
Customer Call
    ↓
Amazon Connect (Telephony)
    ↓
Contact Flow (IVR Logic)
    ↓
Amazon Lex (Voice Processing)
    ↓
Amazon Bedrock Agent (AI Orchestration)
    ↓
├─→ Lambda Functions (Business Logic)
├─→ DynamoDB (Data Storage)
└─→ External APIs (PF360, etc.)
```

### Integration Components

#### 1. **Amazon Connect** (Contact Center Platform)
- Handles telephony and call routing
- Manages contact flows (IVR scripts)
- Provides agent workspace
- Records and monitors calls

#### 2. **Amazon Lex** (Voice Interface)
- Processes speech-to-text
- Recognizes intents from customer voice
- Bridges Connect to Bedrock Agent
- Handles conversation context

#### 3. **Amazon Bedrock Agent** (AI Orchestration)
- Uses foundation models (Claude, Nova, etc.)
- Orchestrates multi-step conversations
- Calls action groups (Lambda functions)
- Maintains conversation memory
- Handles complex reasoning

#### 4. **AWS Lambda** (Business Logic)
- Implements scheduling operations
- Integrates with PF360 API
- Accesses DynamoDB for data
- Returns results to Bedrock Agent

#### 5. **Amazon Transcribe** (Real-Time Transcription)
- Converts speech to text in real-time
- Enables sentiment analysis
- Supports call summarization
- Redacts PII (names, credit cards, SSN)

#### 6. **Contact Lens for Amazon Connect** (Analytics)
- Real-time sentiment analysis
- Category and keyword detection
- Call quality monitoring
- Agent performance insights

### Sample Integration (AWS Reference)

**GitHub Repository:** `aws-samples/sample-amazon-connect-bedrock-agent-voice-integration`

**Features Demonstrated:**
- Voice-based booking assistant
- Search for services
- Check availability
- Create/update/cancel appointments
- Customer registration
- Natural conversation flow

**Technology Stack:**
- Amazon Connect (telephony)
- Amazon Lex (voice processing)
- Amazon Bedrock Agent (Nova-Micro model)
- AWS Lambda (actions)
- DynamoDB (data storage)
- AWS CDK (infrastructure deployment)

### Integration Workflow

1. **Customer Calls**: Dials Amazon Connect phone number
2. **IVR Greeting**: Contact flow plays welcome message
3. **Voice Processing**: Amazon Lex captures speech and recognizes intent
4. **Agent Invocation**: Lex sends request to Bedrock Agent
5. **AI Processing**: Bedrock Agent uses LLM to understand complex requests
6. **Action Execution**: Agent calls Lambda functions to perform operations
7. **Response Generation**: Agent formulates natural language response
8. **Voice Synthesis**: Response converted to speech and played to customer
9. **Loop**: Process continues until customer request is resolved

### Benefits of Bedrock Agent for IVR

| Capability | Traditional IVR | Bedrock Agent IVR |
|------------|-----------------|-------------------|
| **Intent Recognition** | Fixed keywords | Natural language understanding |
| **Context Handling** | Limited slots | Full conversation memory |
| **Complex Requests** | Single-turn only | Multi-step reasoning |
| **Personalization** | Basic variables | Context-aware responses |
| **Fallback Handling** | Transfer to agent | Intelligent clarification |
| **Scalability** | Manual updates | Self-learning capabilities |

---

## 3. SMS Integration with AWS Connect

### Overview

Amazon Connect supports **two-way SMS messaging** as of November 2023, enabling text-based customer interactions alongside voice calls.

### Key Features

✅ **Two-Way SMS** - Customers can send and receive messages
✅ **Unified Agent Workspace** - Same interface for voice, chat, and SMS
✅ **Contact Flow Integration** - Use existing flows for multiple channels
✅ **Outbound SMS** - Proactive messaging (launched October 2024)
✅ **Channel Switching** - Move customers from voice to SMS (and vice versa)

### Setup Requirements

#### Step 1: Acquire SMS-Enabled Phone Number

**Service:** AWS End User Messaging SMS (formerly Amazon Pinpoint SMS)

**Process:**
1. Open AWS End User Messaging SMS console
2. Request phone number
3. Select country and capabilities (SMS + MMS)
4. Choose number type:
   - **10DLC** (10-Digit Long Code) - Standard US numbers
   - **Toll-Free** - 1-800 numbers
   - **Short Code** - Premium option (e.g., 12345)
5. Complete registration (15-day processing for some countries)

**Important:** You **CANNOT** change SMS/voice capabilities after purchase

#### Step 2: Enable Two-Way SMS

1. Open AWS End User Messaging SMS console
2. Select phone number
3. Enable **Two-way messaging**
4. Choose destination: **Amazon Connect**
5. Select IAM role for message routing
6. Configure routing to specific Connect instance

#### Step 3: Update Contact Flows

**Add SMS Detection Logic:**

```
Check Contact Attributes Block:
  Namespace: "Segment attributes"
  Key: "Subtype"
  Condition: equals "connect:SMS"

  If true → Route to SMS flow
  If false → Route to voice flow
```

This allows the same contact flow to handle both voice and SMS.

#### Step 4: Test SMS Integration

1. Set agent status to "Available"
2. Send test SMS from mobile device to Connect number
3. Verify message appears in agent workspace
4. Reply from agent workspace
5. Confirm customer receives response

### Outbound SMS Capabilities (NEW - October 2024)

**Use Cases:**
- **Appointment Reminders** - Schedule-based proactive messages
- **Service Updates** - Status notifications
- **Post-Contact Surveys** - Feedback collection
- **Queue Deflection** - Offer SMS while customer waits on hold

**Implementation Methods:**

**1. Contact Flow Block:**
```
Send Message Block:
  Destination: Customer phone number
  Message: "Your appointment is confirmed for..."
  From: SMS-enabled phone number
```

**2. API Method:**
```
StartOutboundChatContact API:
  SourceEndpoint: +1-555-SMS-NUMBER
  DestinationEndpoint: Customer phone
  InitialMessage: "Your service is complete!"
```

### SMS with Bedrock Agent

**Yes, SMS can be routed to Bedrock Agents!**

**Architecture:**
```
Customer SMS
    ↓
AWS End User Messaging SMS
    ↓
Amazon Connect (SMS Channel)
    ↓
Contact Flow (Check Subtype = SMS)
    ↓
Amazon Lex (Text Processing)
    ↓
Amazon Bedrock Agent (AI Orchestration)
    ↓
Lambda Functions (Business Logic)
    ↓
Response → SMS Reply to Customer
```

**Benefits:**
- Same Bedrock Agent handles voice AND SMS
- Unified conversation memory across channels
- Consistent scheduling logic
- Reduced development effort

### Important Limitation: Voice + SMS on Same Number

⚠️ **CRITICAL:** AWS Connect does **NOT** support using the same phone number for both voice and SMS simultaneously.

**You must:**
- Purchase **separate phone numbers** for voice and SMS
- Example:
  - Voice: +1-555-VOICE (555-864-2300)
  - SMS: +1-555-TEXTS (555-839-8700)

**Workaround:**
- Display both numbers to customers
- "Call us at 555-VOICE or text 555-TEXTS"
- Use marketing to educate customers on separate numbers

---

## 4. Caller ID Features

### Outbound Caller ID Display

AWS Connect supports displaying **caller ID number** on outbound calls, but with significant limitations on **caller ID name** (CNAM).

### What Works ✅

#### Caller ID Number Display

**Capabilities:**
- Display your business phone number when calling customers
- Configure at queue level or dynamically in contact flows
- Use E.164 format: `+1-555-123-4567`
- Set different caller IDs per queue or campaign

**Configuration Options:**

**1. Queue-Level (Static):**
```
Navigate to: Routing → Queues → Select Queue
Settings:
  Outbound Caller ID Number: +1-555-123-4567
  Outbound Caller ID Name: "ProjectsForce 360"
```

**2. Contact Flow (Dynamic):**
```
Call Phone Number Block:
  Caller ID Number: Set dynamically from attribute
  Format: Must be E.164
  Example: $.Attributes.CustomerPreferredCallerID
```

**3. By Country (International):**
```
Check Contact Attributes:
  If Country = "UK" → Use UK number
  If Country = "US" → Use US number
  If Country = "AU" → Use AU number
```

#### Requirements

- **Phone number must be claimed** in your Amazon Connect instance
- **E.164 format required:** `+[country code][phone number]`
- **Custom caller ID requires AWS Support ticket** to activate
- **External numbers** (not owned by you) require AWS Support approval

### What Doesn't Work ❌

#### Caller ID Name Display (CNAM)

⚠️ **MAJOR LIMITATION:** As of **March 31, 2023**, Amazon Connect **NO LONGER supports CNAM** (Caller ID Name) for new configurations.

**What This Means:**
- You can configure "ProjectsForce 360" as outbound caller name
- AWS will **not guarantee** it displays to recipients
- Most mobile users will **only see the phone number**
- Landlines may show name, but not reliably

**Why AWS Discontinued CNAM:**
- Research showed CNAM displayed to **fewer than 7% of users**
- Mobile carriers moved to app-based reputation systems
- Modern alternatives are more effective (e.g., First Orion, Hiya)

**Alternatives:**

**1. First Orion (Recommended by AWS)**
- Third-party caller ID reputation service
- Displays business name and logo on mobile devices
- Integration available via AWS Marketplace
- Cost: ~$0.003 per call

**2. Branded Calling**
- Register business identity with carriers
- Displays business name, logo, and reason for call
- Better than CNAM (mobile-focused)
- Cost: ~$0.01-0.05 per call

**3. Pre-Call SMS**
- Send SMS before calling: "ProjectsForce 360 will call you in 2 minutes"
- Customer sees your number and knows who's calling
- Free if using existing SMS capability

### Caller ID Best Practices

1. **Use Local Numbers** - Match area code to customer location
2. **Keep Numbers Consistent** - Don't rotate caller IDs frequently
3. **Register with Carriers** - Improve reputation and reduce spam blocking
4. **Warn Customers** - Email/SMS them before calling with number to expect
5. **Don't Rely on Name Display** - Assume only number shows

### Inbound Caller ID

**For inbound calls**, AWS Connect **does receive** the caller's phone number and can:
- Display it to agents
- Use it for CRM lookup
- Store it in contact attributes
- Route calls based on caller ID
- Check against do-not-call lists

---

## 5. Real-Time Features

### Real-Time Call Transcription

**Service:** Amazon Transcribe + Contact Lens

**Capabilities:**
- **Live transcription** during call
- **Speech-to-text** with 90%+ accuracy
- **Multi-language support** - 20+ languages
- **Speaker identification** - Agent vs. Customer
- **Timestamps** - Word-level timing
- **PII redaction** - Auto-remove sensitive data

**Use Cases:**
- Real-time agent assist (suggest responses)
- Compliance monitoring
- Quality assurance
- Post-call analysis
- Training material generation

### Sentiment Analysis

**Service:** Contact Lens for Amazon Connect

**Real-Time Sentiment Detection:**
- **Positive** - Customer is satisfied
- **Neutral** - Normal conversation
- **Negative** - Customer is frustrated
- **Mixed** - Emotions changing

**Metrics Tracked:**
- Overall call sentiment
- Sentiment trend over time
- Agent vs. customer sentiment
- Sentiment shifts (neutral → negative)

**Agent Assist Features:**
- **Alerts** - Notify supervisor if sentiment drops
- **Recommendations** - Suggest actions to improve sentiment
- **Escalation** - Auto-escalate negative calls
- **Coaching** - Real-time tips for agents

### Enhanced Sentiment with Bedrock

**Traditional sentiment analysis** detects basic emotions.

**Bedrock-enhanced analysis** can detect:
- Sarcasm
- Ambivalence
- Urgency
- Confusion
- Satisfaction levels
- Emotional nuances

**Example:**
```
Customer: "Yeah, that's just perfect..."

Traditional Analysis: Positive
Bedrock Analysis: Negative (sarcasm detected)
```

### Call Recording

**Features:**
- **Auto-recording** - Record all calls or specific types
- **On-demand** - Agent-initiated recording
- **Secure storage** - S3 with encryption
- **Retention policies** - Auto-delete after X days
- **PII redaction** - Remove sensitive data from recordings

**Compliance:**
- **GDPR** - Right to delete customer recordings
- **PCI DSS** - Pause recording during payment card entry
- **HIPAA** - Encrypt and secure health information
- **State laws** - Two-party consent notification

### Call Summarization with Bedrock

**Generative AI-Powered Summaries:**

After call ends, Amazon Bedrock generates:
- **Call reason** - Why customer called
- **Resolution** - How issue was resolved
- **Follow-up actions** - Next steps identified
- **Customer sentiment** - Overall experience
- **Agent performance** - Key behaviors

**Example Summary:**
```
Call Reason: Schedule solar panel installation
Resolution: Appointment booked for Oct 20, 2:00 PM
Follow-up: Send confirmation email and pre-visit checklist
Customer Sentiment: Positive (satisfied with available dates)
Agent Performance: Professional, efficient (4 min call)
```

**Benefits:**
- Saves 5-10 minutes per call on after-call work
- Improves quality of notes
- Enables better trend analysis
- Faster supervisor review

---

## 6. Pricing Breakdown (2025)

### Voice Pricing

| Component | Rate | Notes |
|-----------|------|-------|
| **Amazon Connect Voice (AI included)** | $0.038/min | Inbound + outbound |
| **US Telephony (DID)** | $0.0022/min | Per-minute usage |
| **US Phone Number (DID)** | $0.030/day | Daily charge (~$1/month) |
| **Toll-Free Number** | $2.00/month | Monthly lease |
| **Outbound Campaigns** | $0.025/min | Connected calls only |

**Example - 1000 Minutes of Inbound Calls:**
```
Connect Voice: 1000 min × $0.038 = $38.00
US Telephony: 1000 min × $0.0022 = $2.20
Phone Number: 30 days × $0.03 = $0.90
────────────────────────────────────
Total: $41.10 (~$0.04 per minute all-in)
```

### SMS Pricing

| Component | Rate | Notes |
|-----------|------|-------|
| **SMS Outbound (US)** | $0.01/message | Per text sent |
| **SMS Inbound (US)** | $0.008/message | Per text received |
| **MMS (with media)** | $0.03/message | Images/videos |
| **SMS Phone Number (10DLC)** | $0.50/month | Monthly lease |

**Example - 500 SMS Conversations:**
```
Outbound: 500 × $0.01 = $5.00
Inbound: 500 × $0.008 = $4.00
Phone Number: $0.50
────────────────────────────────
Total: $9.50 (~$0.02 per conversation)
```

### Additional Service Costs

| Service | Rate | Notes |
|---------|------|-------|
| **Amazon Lex** | $0.00075/request | Voice requests |
| **Amazon Bedrock (Claude Sonnet)** | ~$0.015/1K tokens | Per conversation |
| **Amazon Transcribe** | $0.024/min | Real-time transcription |
| **Contact Lens Analytics** | $0.015/min | Sentiment + transcription |
| **Call Recording Storage** | $0.023/GB/month | S3 storage |

### Monthly Cost Example (Small Contact Center)

**Assumptions:**
- 2,000 inbound calls/month
- Average 5 minutes per call
- 500 SMS conversations/month
- All calls transcribed
- 50% of calls use Bedrock Agent

**Calculation:**
```
Voice Calls:
  Connect (2000×5×$0.038) = $380.00
  Telephony (2000×5×$0.0022) = $22.00
  Phone Numbers (2×$0.90) = $1.80

SMS:
  Outbound (500×$0.01) = $5.00
  Inbound (500×$0.008) = $4.00
  Phone Number = $0.50

AI Services:
  Lex (2000×$0.00075) = $1.50
  Bedrock (1000 calls × $0.50) = $500.00
  Transcribe (2000×5×$0.024) = $240.00
  Contact Lens (2000×5×$0.015) = $150.00

Storage:
  Call Recordings (100GB×$0.023) = $2.30

─────────────────────────────────────
Total Monthly: $1,307.10

Per-call cost: $1,307.10 ÷ 2,000 = $0.65/call
```

### Cost Optimization Tips

1. **Use Bedrock Selectively** - Only complex queries need AI
2. **Reduce Transcription** - Only transcribe flagged calls
3. **Compress Recordings** - Store at lower quality
4. **Archive Old Calls** - Move to Glacier after 90 days
5. **Optimize Lex Requests** - Cache common intents
6. **Right-Size Concurrency** - Don't over-provision
7. **Use Reserved Capacity** - If volume is predictable

---

## 7. Scalability & Capacity

### Concurrent Call Limits

**Default Quotas:**
- **New instances:** 100 concurrent active calls
- **Legacy instances:** 10 concurrent active calls (older accounts)
- **Max practical limit:** Thousands (with quota increase)

### What Counts as "Active Call"

✅ **Counted:**
- Inbound calls ringing
- Calls connected to agents
- Calls in IVR (listening to prompts)
- Calls on hold
- Calls being transferred

❌ **Not Counted:**
- Callbacks waiting in queue (until placed)
- Completed calls
- Failed connection attempts

### Quota Increase Process

**Small Increases (100 → 500 calls):**
- Request via Service Quotas console
- Approval in hours to 1-2 days
- No justification needed

**Medium Increases (500 → 2,000 calls):**
- Submit support case with business justification
- Include expected peak times
- Approval in 3-5 business days

**Large Increases (2,000+ calls):**
- Requires AWS Solutions Architect review
- Need detailed capacity plan
- May take 2-3 weeks for deployment
- Extra-large (10,000+) can take months

### Monitoring Capacity

**CloudWatch Metrics:**
```
ConcurrentCalls: Current active calls
ConcurrentCallsPercentage: % of quota used

Example:
  ConcurrentCalls = 40
  ConcurrentCallsPercentage = 80%
  → Current Quota = 40 ÷ 0.80 = 50 calls
```

**Alarms to Set:**
- Alert at 80% capacity
- Critical at 90% capacity
- Auto-scale agents at 85%

### Scalability Best Practices

1. **Plan Ahead** - Request quota increases before peak season
2. **Load Test** - Simulate peak traffic before go-live
3. **Monitor Trends** - Track weekly capacity usage
4. **Overflow Strategy** - Route to voicemail if at capacity
5. **Regional Distribution** - Use multiple regions for DR

### SMS Scalability

**SMS Quotas:**
- **Default:** 1 SMS/second
- **10DLC:** Up to 100 SMS/second (after registration)
- **Short Code:** Up to 1,000 SMS/second (premium)

**Throughput Planning:**
- Standard: 3,600 SMS/hour
- 10DLC: 360,000 SMS/hour
- Short Code: 3.6M SMS/hour

---

## 8. Implementation Considerations

### Architecture Decision: Phase 3 Design

**Recommended Architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│                        CUSTOMERS                             │
│                                                              │
│  📞 Voice Calls          📱 SMS Messages          💬 Web Chat│
│  +1-555-VOICE-NUM       +1-555-TEXT-NUM          Website    │
└─────────────┬──────────────────┬────────────────────┬───────┘
              │                  │                    │
              ↓                  ↓                    ↓
┌─────────────────────────────────────────────────────────────┐
│              AMAZON CONNECT (Contact Center)                 │
│                                                              │
│  • Telephony handling        • Contact flows                │
│  • Channel routing           • Queue management             │
│  • Agent workspace           • Call recording               │
└─────────────┬──────────────────┬────────────────────┬───────┘
              │                  │                    │
              ↓                  ↓                    ↓
┌─────────────────────────────────────────────────────────────┐
│                      AMAZON LEX                              │
│                                                              │
│  • Voice-to-text conversion  • Intent recognition           │
│  • Text normalization        • Slot filling                 │
│  • Context management        • Multi-turn conversations     │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                                  ↓
┌─────────────────────────────────────────────────────────────┐
│               AMAZON BEDROCK AGENT (Supervisor)              │
│                                                              │
│  Model: Claude Sonnet 4.5                                   │
│  • Natural language understanding                           │
│  • Multi-agent orchestration                                │
│  • Conversation memory                                      │
│  • Context-aware responses                                  │
│                                                              │
│  ┌──────────────┬───────────────┬──────────────┬─────────┐ │
│  │ Scheduling   │ Information   │ Notes        │ ChitChat│ │
│  │ Collaborator │ Collaborator  │ Collaborator │ Collab  │ │
│  └──────┬───────┴───────┬───────┴──────┬───────┴────┬────┘ │
└─────────┼───────────────┼──────────────┼────────────┼──────┘
          │               │              │            │
          ↓               ↓              ↓            ↓
┌─────────────────────────────────────────────────────────────┐
│                      AWS LAMBDA FUNCTIONS                    │
│                                                              │
│  • Scheduling operations    • Project lookup                │
│  • Availability checks      • Notes management              │
│  • Appointment booking      • Customer registration         │
│  • Bulk operations          • PF360 API integration         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                  DATA & EXTERNAL SERVICES                    │
│                                                              │
│  • DynamoDB (session data)   • PF360 API (scheduling)       │
│  • Aurora RDS (customer DB)  • Redis (caching)              │
│  • S3 (call recordings)      • Secrets Manager (creds)      │
└─────────────────────────────────────────────────────────────┘
```

### Integration Approach

**Option 1: Extend Existing Agents (Recommended)**
- ✅ Reuse existing Bedrock Agents (Supervisor + 4 Collaborators)
- ✅ Add Amazon Lex as new input channel
- ✅ Same Lambda functions for voice, SMS, and chat
- ✅ Unified conversation memory
- ⚠️ Need to handle voice-specific formatting

**Option 2: Separate Voice Agent**
- Create dedicated Bedrock Agent for voice
- Different prompts optimized for speech
- Separate Lambda functions
- ⚠️ Duplicates business logic
- ⚠️ Harder to maintain consistency

**Recommendation:** **Option 1** - Extend existing agents for omnichannel consistency.

### Voice-Specific Considerations

**1. Response Length**
- Keep responses concise (< 30 seconds of speech)
- Break long lists into chunks
- Offer to "send details via SMS"

**2. Numbers and Dates**
- Say: "October twentieth at two PM"
- Not: "2025-10-20 at 14:00"

**3. Confirmation**
- Always repeat key details back to customer
- "You're scheduled for Tuesday, October 15 at 2 PM, correct?"

**4. Error Handling**
- "I didn't catch that. Could you say it again?"
- Not: "ERROR: Speech recognition failed"

**5. Interruptions**
- Allow customers to interrupt (barge-in)
- Resume context smoothly

### Channel-Specific Flows

**Voice Channel:**
```
1. Greeting: "Thank you for calling ProjectsForce 360"
2. Identity: "May I have your phone number?"
3. Lookup: Check customer in database
4. Intent: "How can I help you today?"
5. Process: Route to Bedrock Agent
6. Confirm: Repeat details back
7. Closure: "Is there anything else?"
```

**SMS Channel:**
```
1. Welcome: "Hi! Thanks for texting ProjectsForce 360"
2. Identity: Customer phone is already known
3. Intent: "Reply with: 1) Schedule 2) Reschedule 3) Check Status"
4. Process: Route to Bedrock Agent
5. Confirm: Send confirmation with details
6. Follow-up: "Reply HELP for more options"
```

---

## 9. Limitations & Constraints

### Technical Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| **No shared voice/SMS number** | Customers need 2 numbers | Use both prominently in marketing |
| **CNAM not guaranteed** | Name may not display | Use caller ID reputation services |
| **Lex intent limit** | Max 500 intents per bot | Use Bedrock for complex intent routing |
| **Call recording storage** | Costs add up with volume | Archive to Glacier after 90 days |
| **Concurrent call quota** | Default 100 calls | Request increase proactively |
| **SMS 10-day registration** | Delay before SMS works | Start registration early |

### Bedrock Agent Limitations

| Limitation | Impact | Solution |
|------------|--------|----------|
| **Latency** | 1-3 second response time | Set expectations with "One moment..." |
| **Token limits** | Long conversations hit limit | Summarize and reset context |
| **Cost per call** | $0.50+ for AI-heavy calls | Use traditional IVR for simple tasks |
| **Cold start** | First call of the day slower | Keep warm with scheduled invocations |

### Voice-Specific Challenges

| Challenge | Issue | Mitigation |
|-----------|-------|------------|
| **Accents** | Speech recognition errors | Offer keypad alternative |
| **Background noise** | Transcription failures | Ask customer to find quiet area |
| **Speech rate** | Fast talkers misunderstood | "Could you repeat that slowly?" |
| **Ambiguous words** | "For" vs "Four" confusion | Confirm with different phrasing |

---

## 10. Best Practices

### Voice IVR Design

**Do's:**
✅ Keep prompts under 20 seconds
✅ Offer menu options ("Press 1 for scheduling")
✅ Allow interruptions (barge-in)
✅ Confirm understood details back to customer
✅ Provide agent escalation option
✅ Use professional voice actors for recordings
✅ Test with diverse accents and speech patterns

**Don'ts:**
❌ Don't nest menus more than 3 levels deep
❌ Don't play long legal disclaimers before menu
❌ Don't force customers to repeat information
❌ Don't use complex jargon or technical terms
❌ Don't make caller ID name display critical to flow

### SMS Best Practices

**Do's:**
✅ Keep messages under 160 characters
✅ Use clear call-to-action ("Reply YES to confirm")
✅ Provide opt-out instructions ("Reply STOP to unsubscribe")
✅ Include business name in first message
✅ Respond within 5 minutes
✅ Use templates for common responses

**Don'ts:**
❌ Don't send marketing without consent
❌ Don't text outside business hours (8 AM - 8 PM)
❌ Don't use URL shorteners (looks like spam)
❌ Don't send multiple messages in rapid succession

### Bedrock Agent Optimization

**Prompts:**
- Be specific about response format
- Include examples of good responses
- Set character limits for voice ("max 100 words")
- Define error handling behavior

**Action Groups:**
- Keep actions focused (one task per function)
- Return structured data, not plain text
- Include success/failure indicators
- Add timeout handling (Lambda max 60s)

**Memory:**
- Summarize long conversations periodically
- Clear context after task completion
- Preserve critical details (customer ID, appointment)
- Expire sessions after 24 hours of inactivity

### Cost Optimization

**Voice:**
- Use traditional IVR for simple routing
- Only invoke Bedrock for complex requests
- Reduce transcription to compliance calls only
- Compress recordings to reduce storage

**SMS:**
- Use templates instead of AI-generated messages
- Batch outbound campaigns during off-peak
- Monitor character count to avoid split messages
- Provide web portal link for complex interactions

**AI:**
- Cache common queries in DynamoDB
- Use smaller models (Nova Micro) for simple tasks
- Implement query classification (simple vs complex)
- Set token limits to prevent runaway costs

---

## 11. Comparison: Phase 2 (SMS) vs Phase 3 (Voice + SMS)

| Feature | Phase 2 (Current) | Phase 3 (Proposed) |
|---------|-------------------|-------------------|
| **SMS** | ✅ AWS End User Messaging | ✅ AWS Connect SMS |
| **Voice** | ❌ Not available | ✅ AWS Connect Voice |
| **IVR** | ❌ N/A | ✅ AI-powered with Bedrock |
| **Caller ID** | ✅ SMS sender name | ⚠️ Number only (name limited) |
| **Unified Agent** | ❌ No agent workspace | ✅ Single workspace for all channels |
| **Call Recording** | ❌ N/A | ✅ With transcription |
| **Sentiment Analysis** | ❌ Not available | ✅ Real-time with Contact Lens |
| **Channel Switching** | ❌ Not supported | ✅ Voice ↔ SMS seamlessly |
| **Cost per Interaction** | ~$0.02 (SMS only) | ~$0.65 (voice + AI) |
| **Setup Complexity** | Medium | High |
| **Maintenance** | Low | Medium |

**Key Differences:**

**Phase 2 (SMS Only):**
- Lower cost per interaction
- No voice support
- No human agents needed (fully automated)
- Simpler infrastructure

**Phase 3 (Voice + SMS + Agent Workspace):**
- Full contact center capabilities
- Real-time voice conversations
- Human agent option
- More complex but feature-rich

---

## 12. Recommendations

### Should You Implement Phase 3?

**YES, if:**
✅ Customers prefer calling over texting
✅ Complex scheduling requires back-and-forth conversation
✅ You want to provide phone support
✅ Budget allows for ~$0.65 per call
✅ You need human agent escalation
✅ Call recording/compliance is important

**MAYBE, if:**
⚠️ Current SMS-only system meets needs
⚠️ Customers primarily text already
⚠️ Voice call volume would be low (<100/month)
⚠️ Budget is tight

**NO, if:**
❌ All scheduling can be handled via SMS
❌ No budget for ~$1,300+/month
❌ No need for voice interactions
❌ Team can't support phone channel

### Phased Approach (Recommended)

**Phase 3A: Basic Voice IVR (Month 1-2)**
- Set up Amazon Connect instance
- Configure basic IVR (menu-driven)
- Test with internal team
- Train agents on workspace
- Launch to limited customers
- **Cost:** ~$500/month

**Phase 3B: AI-Powered IVR (Month 3-4)**
- Integrate Amazon Lex
- Connect to existing Bedrock Agents
- Enable voice-to-Bedrock routing
- Test complex conversations
- Refine prompts based on real calls
- **Additional Cost:** ~$800/month

**Phase 3C: Advanced Features (Month 5-6)**
- Add SMS integration
- Enable channel switching
- Implement sentiment analysis
- Set up call summarization
- Deploy agent assists
- **Additional Cost:** ~$300/month

**Total Phase 3 Cost at Full Deployment:** ~$1,600/month (2,000 calls + 500 SMS)

### Alternative: Hybrid Approach

**Keep Phase 2 SMS for:**
- Simple appointment reminders
- Confirmations and updates
- Customer-initiated texts

**Add Phase 3 Voice for:**
- Complex scheduling discussions
- Customer support escalations
- Sales and consultations

**Benefits:**
- Lower cost (most interactions via SMS)
- Voice available when needed
- Best of both worlds

---

## 13. Next Steps (If Proceeding with Phase 3)

### Week 1-2: Planning & Design

- [ ] Define use cases for voice vs SMS
- [ ] Design call flows (IVR scripts)
- [ ] Plan Bedrock Agent extensions
- [ ] Calculate expected call volumes
- [ ] Request AWS quota increases
- [ ] Budget approval for Phase 3

### Week 3-4: AWS Connect Setup

- [ ] Create Amazon Connect instance
- [ ] Claim phone numbers (voice + SMS)
- [ ] Set up basic IVR
- [ ] Configure queues and routing
- [ ] Test inbound calls
- [ ] Set up agent workspace

### Week 5-6: Lex Integration

- [ ] Create Amazon Lex bot
- [ ] Define intents and slots
- [ ] Connect Lex to Connect
- [ ] Test voice recognition
- [ ] Refine Lex prompts

### Week 7-8: Bedrock Agent Integration

- [ ] Extend Supervisor Agent for voice
- [ ] Update collaborator prompts for speech
- [ ] Create Lex → Bedrock integration
- [ ] Test end-to-end conversations
- [ ] Optimize for latency

### Week 9-10: SMS Integration

- [ ] Enable two-way SMS in Connect
- [ ] Import SMS phone number
- [ ] Configure SMS routing
- [ ] Test SMS-to-Bedrock flow
- [ ] Enable channel switching

### Week 11-12: Advanced Features

- [ ] Enable call recording
- [ ] Configure Contact Lens
- [ ] Set up sentiment analysis
- [ ] Implement call summarization
- [ ] Deploy agent assists

### Week 13-14: Testing & Launch

- [ ] User acceptance testing
- [ ] Load testing (simulate peak traffic)
- [ ] Train customer support team
- [ ] Update website with phone numbers
- [ ] Soft launch to beta customers
- [ ] Monitor and optimize

### Week 15+: Operations & Optimization

- [ ] Monitor CloudWatch metrics
- [ ] Review call transcripts
- [ ] Optimize Bedrock prompts
- [ ] Reduce costs where possible
- [ ] Gather customer feedback
- [ ] Iterate on IVR flows

---

## 14. Key Takeaways

### ✅ What's Possible

1. **Full Bedrock Agent Integration with Voice IVR** - AWS Connect + Lex + Bedrock Agents work seamlessly together
2. **SMS Integration** - Two-way SMS with same Bedrock Agents
3. **Unified Omnichannel** - Voice, SMS, and chat in single agent workspace
4. **Real-Time AI Features** - Transcription, sentiment, summarization
5. **Caller ID Display** - Phone number shows (name limited)
6. **Scalability** - From 10 to thousands of concurrent calls
7. **Pay-As-You-Go** - No upfront costs, scale as needed

### ⚠️ Key Limitations

1. **Separate Numbers Required** - Cannot use same number for voice + SMS
2. **CNAM Not Supported** - Caller name display discontinued by AWS
3. **Higher Cost Than SMS** - ~$0.65/call vs $0.02/SMS
4. **Latency** - 1-3 seconds for Bedrock Agent responses
5. **Setup Complexity** - More complex than SMS-only solution
6. **Quota Management** - Need to plan concurrent call capacity

### 💰 Cost Summary

**Small Scale (500 calls + 200 SMS/month):**
- Total: ~$450/month
- Per-call: ~$0.90

**Medium Scale (2,000 calls + 500 SMS/month):**
- Total: ~$1,300/month
- Per-call: ~$0.65

**Large Scale (10,000 calls + 2,000 SMS/month):**
- Total: ~$5,800/month
- Per-call: ~$0.58

### 🎯 Bottom Line

**AWS Connect + Bedrock Agents for IVR is:**
- ✅ **Technically feasible** - Full integration supported
- ✅ **Feature-rich** - Voice, SMS, AI, analytics all included
- ⚠️ **More expensive** - ~30x cost vs SMS-only
- ⚠️ **More complex** - Requires additional services and setup
- ✅ **Scalable** - Grows with your business
- ✅ **Future-proof** - Modern cloud contact center

**Recommendation:** Implement Phase 3 if your business needs justify the additional cost and complexity. The AI-powered IVR with omnichannel support will provide excellent customer experience.

---

## 15. Additional Resources

### AWS Documentation

- [Amazon Connect Admin Guide](https://docs.aws.amazon.com/connect/latest/adminguide/)
- [Amazon Lex Developer Guide](https://docs.aws.amazon.com/lex/)
- [Amazon Bedrock Agents Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Contact Lens for Amazon Connect](https://docs.aws.amazon.com/connect/latest/adminguide/analyze-conversations.html)
- [AWS End User Messaging SMS](https://docs.aws.amazon.com/sms-voice/latest/userguide/)

### AWS Samples & Workshops

- [sample-amazon-connect-bedrock-agent-voice-integration](https://github.com/aws-samples/sample-amazon-connect-bedrock-agent-voice-integration)
- [amazon-transcribe-live-call-analytics](https://github.com/aws-samples/amazon-transcribe-live-call-analytics)

### Pricing Calculators

- [AWS Connect Pricing](https://aws.amazon.com/connect/pricing/)
- [AWS End User Messaging Pricing](https://aws.amazon.com/end-user-messaging/pricing/)
- [Amazon Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [Amazon Transcribe Pricing](https://aws.amazon.com/transcribe/pricing/)

### AWS Blog Posts

- [Deploy generative AI agents in your contact center](https://aws.amazon.com/blogs/machine-learning/deploy-generative-ai-agents-in-your-contact-center-for-voice-and-chat-using-amazon-connect-amazon-lex-and-amazon-bedrock-knowledge-bases/)
- [Resolve customer issues via two-way SMS in Amazon Connect](https://aws.amazon.com/blogs/contact-center/resolve-customer-issues-via-two-way-sms-text-messaging-in-amazon-connect/)
- [Channel deflection from voice to chat](https://aws.amazon.com/blogs/architecture/channel-deflection-from-voice-to-chat-using-amazon-connect/)

---

**Research Completed:** October 13, 2025
**Next Action:** Review with stakeholders and decide on Phase 3 implementation
**Estimated Implementation Time:** 12-14 weeks (phased approach)
**Estimated Monthly Cost:** $450 - $1,600 depending on volume

---

**STATUS: ✅ Research Complete - Ready for Decision**
