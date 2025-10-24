# Phase 3: Voice Integration - Quick Start Guide

**Purpose:** 5-minute overview of Phase 3 approach
**For:** Quick reference before diving into detailed implementation

---

## 🎯 What We're Building

**Enable customers to call an Indian phone number (+91 XXXX XXXXXX) and interact with your existing Bedrock Agents via voice.**

### Flow

```
Customer dials +91 XXXX XXXXXX
         ↓
AWS Connect answers call
         ↓
Amazon Lex converts speech to text
         ↓
Your existing Bedrock Supervisor Agent (5VTIWONUMO)
         ↓
Same 12 Lambda functions you already built
         ↓
Voice response back to customer
```

---

## ✅ What You Already Have (No Changes Needed!)

✅ **5 Bedrock Agents** - Supervisor + 4 collaborators (reuse 100%)
✅ **12 Lambda functions** - scheduling, information, notes (reuse 100%)
✅ **OpenAPI schemas** - Action groups already defined (reuse 100%)
✅ **Databases** - Aurora, DynamoDB, Redis (reuse 100%)

**You only need to add:**
- Amazon Connect instance (contact center)
- Amazon Lex bot (voice interface)
- 1 new Lambda (Lex ↔ Bedrock bridge)
- Indian phone number

---

## 📝 3-Step Approach

### Step 1: Get Indian Phone Number (Start Immediately)

**Fast Option (1-2 days):** Twilio
- Sign up at Twilio.com
- Submit Indian business docs
- Get approved in 1-2 days
- Forward calls to AWS Connect

**Proper Option (7-15 days):** Native AWS Connect DID
- Submit documents via AWS Support case
- Wait for telecom carrier approval
- Claim number in AWS Connect console

**Documents Needed:**
1. Company registration certificate
2. GST certificate
3. Address proof (utility bill)
4. Director ID proof (Aadhaar/Passport)
5. Letter of Authorization (template provided)

👉 **See:** [PHASE3_INDIAN_PHONE_SETUP.md](PHASE3_INDIAN_PHONE_SETUP.md)

---

### Step 2: Set Up Voice Infrastructure (Week 1-2)

**2.1 Create AWS Connect Instance**
- Console → AWS Connect → Create instance
- Region: `ap-south-1` (Mumbai)
- Name: `scheduling-agent-india`
- Enable call recording

**2.2 Create Amazon Lex Bot**
- Console → Amazon Lex → Create bot
- Name: `SchedulingAgentVoice`
- Language: English (India)
- Intents: ScheduleAppointment, CheckStatus, Reschedule, etc.

**2.3 Build Lex-to-Bedrock Bridge Lambda**
```python
# New Lambda function
def lambda_handler(event, context):
    # 1. Get voice input from Lex
    user_message = event['inputTranscript']

    # 2. Call your existing Bedrock Supervisor Agent
    response = bedrock_agent_runtime.invoke_agent(
        agentId='5VTIWONUMO',  # Your existing supervisor
        sessionId=f"voice-{phone}",
        inputText=user_message
    )

    # 3. Format for voice (convert dates, times, etc.)
    voice_response = format_for_voice(response)

    # 4. Return to Lex → Connect → Customer
    return voice_response
```

**2.4 Create Contact Flow (IVR)**
- AWS Connect console → Contact flows
- Greeting → Get input (Lex) → Play response → Loop

👉 **See:** [PHASE3_IMPLEMENTATION_PLAN.md](PHASE3_IMPLEMENTATION_PLAN.md) Steps 4-6

---

### Step 3: Test & Launch (Week 3-4)

**3.1 Test Scenarios**
- Call from Indian mobile
- Test: "Schedule flooring installation for next Tuesday at 10 AM"
- Test: "What's my project status?"
- Test: "Reschedule to next Friday"

**3.2 Launch**
- Publish number on website
- Monitor CloudWatch for errors
- Track call quality metrics

👉 **See:** [PHASE3_IMPLEMENTATION_PLAN.md](PHASE3_IMPLEMENTATION_PLAN.md) Steps 7-8

---

## 💡 Key Design Decisions

### ✅ Extend Existing Agents (Not Create New Ones)

**Why:**
- Same Bedrock Agent for voice, SMS, and chat
- Same Lambda functions (12 actions)
- Same databases
- Same business logic
- Easier to maintain

**What Changes:**
- Input channel: Add voice (via Lex)
- Output format: Add voice-friendly formatting (dates, times)

---

### ✅ Reuse Phase 1 & 2 Work (100%)

| Component | Phase 1/2 | Phase 3 | Reuse |
|-----------|-----------|---------|-------|
| Bedrock Supervisor | ✅ Built | Use as-is | 100% |
| 4 Collaborators | ✅ Built | Use as-is | 100% |
| 12 Lambda functions | ✅ Built | Use as-is | 100% |
| Aurora PostgreSQL | ✅ Ready | Use as-is | 100% |
| DynamoDB tables | ✅ Ready | Use as-is | 100% |
| Redis cache | ✅ Ready | Use as-is | 100% |
| **New:** AWS Connect | — | ✅ Add | 0% |
| **New:** Amazon Lex | — | ✅ Add | 0% |
| **New:** Bridge Lambda | — | ✅ Add | 0% |

**Total Reuse:** ~85% (only add voice layer)

---

## 💰 Cost Estimate

### Monthly Cost (500 calls/month, 5 min avg)

| Component | Cost |
|-----------|------|
| AWS Connect | $95 |
| Indian phone number | $10 |
| Telephony (India inbound) | $15 |
| Amazon Lex | $0.40 |
| Bedrock (same as before) | $15 |
| Transcription | $60 |
| Analytics | $38 |
| Storage/logs | $5 |
| **Total** | **~$238/month** |

**Per Call:** $0.48
**Per Minute:** $0.095

**Scaling:**
- 2,000 calls/month: ~$850/month
- 10,000 calls/month: ~$3,800/month

---

## ⏱️ Timeline

### Recommended Approach (Parallel Work)

**Week 0 (Now):**
- ✅ Submit Indian phone number application (start 7-15 day clock)
- ✅ While waiting, build Lex + Lambda + Flows

**Week 1:**
- Create AWS Connect instance
- Build Amazon Lex bot
- Define intents and slots

**Week 2:**
- Build Lex-to-Bedrock bridge Lambda
- Create contact flows
- Test with US test number

**Week 3:**
- Indian number approved (hopefully!)
- Claim number in AWS Connect
- Test end-to-end with real number

**Week 4:**
- UAT testing
- Soft launch (internal)
- Public launch
- Monitor and optimize

**Total:** 4 weeks (assuming phone approval in 2 weeks)

---

## 🚨 Common Pitfalls to Avoid

### ❌ Don't: Create New Bedrock Agents for Voice

**Why:** Duplicates business logic, harder to maintain

**✅ Do:** Reuse existing supervisor agent (5VTIWONUMO)

---

### ❌ Don't: Wait for Phone Number Before Starting

**Why:** Wastes 2 weeks

**✅ Do:** Build Lex/Lambda/Flows in parallel, test with US number

---

### ❌ Don't: Forget Voice-Specific Formatting

**Why:** Responses like "2025-10-20" sound robotic

**✅ Do:** Format dates/times for speech: "October twentieth"

---

### ❌ Don't: Skip Load Testing

**Why:** First call surge can overwhelm system

**✅ Do:** Test with 100 concurrent calls before launch

---

## 📊 Success Metrics

Track these from Day 1:

| Metric | Target | How to Track |
|--------|--------|--------------|
| **Call Success Rate** | >85% | CloudWatch: ContactFlowSuccess |
| **Speech Recognition** | >90% | CloudWatch: LexIntentMatches |
| **Avg Call Duration** | <4 min | CloudWatch: AverageHandleTime |
| **Customer Satisfaction** | >4.0/5 | Post-call survey |
| **Booking Rate** | >70% | Lambda: confirm_appointment calls |
| **Cost per Call** | <$0.50 | AWS Cost Explorer |

---

## 🆘 Need Help?

### Read These Docs (In Order)

1. **This file** (PHASE3_QUICK_START.md) - You are here!
2. [PHASE3_INDIAN_PHONE_SETUP.md](PHASE3_INDIAN_PHONE_SETUP.md) - Get your phone number
3. [PHASE3_IMPLEMENTATION_PLAN.md](PHASE3_IMPLEMENTATION_PLAN.md) - Detailed build guide
4. [PHASE3_AWS_CONNECT_RESEARCH.md](PHASE3_AWS_CONNECT_RESEARCH.md) - Deep technical dive

### Ask Questions

- **AWS Support:** Open case in AWS Console
- **Internal:** Check existing docs in `bedrock/docs/`
- **Community:** AWS re:Post, Stack Overflow

---

## ✅ Immediate Next Steps (Do Today!)

### 1. Gather Documents (30 minutes)
- [ ] Find company registration certificate
- [ ] Get latest GST certificate
- [ ] Get utility bill (<3 months old)
- [ ] Get director Aadhaar/Passport copy
- [ ] Draft Letter of Authorization (template in docs)

### 2. Submit Phone Number Request (15 minutes)
- [ ] Open AWS Support case
- [ ] Upload all 5 documents
- [ ] Request Indian DID in ap-south-1

### 3. Start Building (While Waiting)
- [ ] Create AWS Connect instance
- [ ] Start designing Lex bot intents
- [ ] Read detailed implementation plan

**Time to Start:** 45 minutes
**Time to Launch:** 3-4 weeks

---

## 🎯 End State (What Success Looks Like)

**Customer Experience:**
```
Customer: [Dials +91 XXXX XXXXXX]
IVR: "Thank you for calling ProjectsForce 360. How can I help you?"
Customer: "I want to schedule my flooring installation for next Monday at 2 PM"
IVR: "Let me check availability... I have Monday, October 21st at 2 PM
      available for your flooring project. Shall I book it?"
Customer: "Yes"
IVR: "Perfect! You're confirmed for Monday, October 21st at 2 PM.
      You'll receive an SMS confirmation shortly. Is there anything else?"
Customer: "No, thank you"
IVR: "Thank you for calling. Goodbye!"
[Call ends - SMS sent - Calendar updated - All logged]
```

**Your Backend:**
- ✅ Same Bedrock Agents (no duplication)
- ✅ Same Lambda functions (unified backend)
- ✅ Same databases (single source of truth)
- ✅ Voice, SMS, and Chat all work the same way
- ✅ Complete audit trail and analytics
- ✅ Scales to thousands of calls

---

**Ready to start? → Open [PHASE3_INDIAN_PHONE_SETUP.md](PHASE3_INDIAN_PHONE_SETUP.md) and submit your phone number request today!**

---

**Document Version:** 1.0
**Last Updated:** October 17, 2025
**Estimated Reading Time:** 5 minutes
