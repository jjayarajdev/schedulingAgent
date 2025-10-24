# Getting a US Phone Number for AWS Connect

**Date:** October 17, 2025
**Purpose:** Step-by-step guide to claim US phone number for voice calls
**Estimated Time:** 5-10 minutes (instant approval!)

---

## 📋 Overview

Getting a **US phone number** for AWS Connect is **dramatically simpler and faster** than Indian numbers. No document submission, no approval process - just click and claim!

### What You'll Get

✅ **US Direct Inward Dialing (DID)**: +1 (XXX) XXX-XXXX
✅ **OR Toll-Free**: +1 (800/888/877/866/855/844/833) XXX-XXXX
✅ **Instant availability** - claim in seconds
✅ **Full AWS Connect integration** - IVR, recording, analytics
✅ **Ideal for testing** - before Indian number approval

### Time Comparison

| Region | Approval Time | Documents Required |
|--------|---------------|-------------------|
| **US** | **Instant** ✅ | None |
| India | 7-15 days | 5 documents |
| EU | 1-3 days | 1-2 documents |
| Australia | 3-7 days | 2-3 documents |

---

## 🎯 When to Use US Numbers

### ✅ Use US Number For:

1. **Testing Phase 3 Implementation**
   - Test while waiting for Indian DID approval
   - Validate Lex bot, contact flows, Bedrock integration
   - No cost/time barrier

2. **US Customer Base**
   - If you have customers in United States
   - Provides local presence for US market
   - Lower call rates for US customers

3. **International Business**
   - Toll-free number for global customers
   - English-speaking markets (US, Canada, UK)
   - Professional presence

4. **Development & QA**
   - Developers can test without waiting
   - QA team can validate features quickly
   - Staging environment testing

### ⚠️ Don't Use US Number For:

- Primary number for Indian customers (high international call rates)
- Replacing Indian DID (customers prefer local numbers)
- Final production (unless you have US customer base)

---

## 🚀 Quick Start: Claim US Number (5 Minutes)

### Step 1: Create/Access AWS Connect Instance

**If you already have an instance (from Indian setup):**
- Skip to Step 2

**If you need to create one:**

1. **Open AWS Console**
   - Go to: https://console.aws.amazon.com/connect/
   - Select region: `us-east-1` (N. Virginia) or `us-west-2` (Oregon)

2. **Click "Create instance"**

3. **Configure Settings**
   ```
   Identity management: Store users in Amazon Connect
   Instance alias: scheduling-agent-us-test
   Administrator: Create first admin user
     - First name: Admin
     - Last name: User
     - Username: admin
     - Password: [Create strong password]
     - Email: your-email@company.com
   ```

4. **Telephony Options**
   - ✅ Enable inbound calls
   - ✅ Enable outbound calls

5. **Data Storage**
   - ✅ Call recordings (S3)
   - ✅ Exported reports (S3)
   - Default encryption (AWS managed keys)

6. **Click "Create instance"**
   - Wait 2-3 minutes for provisioning

---

### Step 2: Claim US Phone Number (Instant!)

1. **Access Your Instance**
   - AWS Connect console → Select your instance
   - Click "Access URL" → Login with admin credentials

2. **Navigate to Phone Numbers**
   - Left sidebar → **Channels** → **Phone numbers**
   - Click **"Claim a number"** button

3. **Select Country & Type**

   **Option A: US Local Number (DID)**
   ```
   Country/Region: United States (+1)
   Type: DID (Direct Inward Dialing)

   Numbers appear instantly! Examples:
   +1 (202) XXX-XXXX (Washington DC)
   +1 (415) XXX-XXXX (San Francisco)
   +1 (212) XXX-XXXX (New York)
   +1 (312) XXX-XXXX (Chicago)
   +1 (404) XXX-XXXX (Atlanta)
   ```

   **Option B: US Toll-Free Number**
   ```
   Country/Region: United States (+1)
   Type: Toll-Free

   Prefixes available:
   +1 (800) XXX-XXXX (most popular)
   +1 (888) XXX-XXXX
   +1 (877) XXX-XXXX
   +1 (866) XXX-XXXX
   +1 (855) XXX-XXXX
   +1 (844) XXX-XXXX
   +1 (833) XXX-XXXX (newest)
   ```

4. **Choose Your Number**
   - Browse available numbers
   - Select one that's easy to remember
   - Optional: Choose area code for local presence

5. **Set Description** (Optional but recommended)
   ```
   Description: Test IVR for Bedrock Agent Integration
   ```

6. **Assign to Contact Flow**
   - Flow/IVR: Select your contact flow (or set later)
   - If testing: Choose "Sample inbound flow" for now

7. **Click "Save"**
   - Number is **immediately active**!
   - Can receive calls in ~30 seconds

---

### Step 3: Test Your Number (Instant Validation)

1. **Call from Your Mobile Phone**
   - Dial the number you just claimed
   - Should connect immediately

2. **What You'll Hear**
   - Sample greeting (if using default flow)
   - Or your custom IVR (if you set one up)

3. **Verify in Console**
   - AWS Connect → **Metrics and quality** → **Real-time metrics** → **Queues**
   - Should see incoming call activity

**🎉 Success! Your US number is live!**

---

## 📞 US Number Types Comparison

### DID (Direct Inward Dialing) - Local Numbers

**Format:** +1 (XXX) XXX-XXXX

**Pros:**
✅ **Instant availability** - claim in seconds
✅ **Local presence** - choose area code (NY, SF, Chicago, etc.)
✅ **Lower cost** - $0.03/month, $0.022/min inbound
✅ **Familiar format** - standard US phone number
✅ **Better for SMS** - can send/receive SMS (additional setup)

**Cons:**
❌ Customers pay for call (not toll-free)
❌ Area code may not match business location
❌ Less "professional" perception vs toll-free

**Best For:**
- Testing and development
- Local market presence (e.g., SF Bay Area business)
- Cost-sensitive applications
- SMS integration

**Popular Area Codes:**
```
New York:        +1 (212), (646), (917)
Los Angeles:     +1 (213), (310), (323)
San Francisco:   +1 (415), (650)
Chicago:         +1 (312), (773)
Washington DC:   +1 (202)
Miami:           +1 (305), (786)
Atlanta:         +1 (404), (678)
```

---

### Toll-Free Numbers

**Format:** +1 (8XX) XXX-XXXX

**Pros:**
✅ **Professional image** - perceived as established business
✅ **Free for callers** - no cost to customer
✅ **National presence** - not tied to location
✅ **Better recall** - customers remember 1-800 numbers
✅ **Porting supported** - can move from carrier to carrier

**Cons:**
❌ **Higher cost** - $0.06/month + $0.042/min (nearly 2x DID)
❌ **Limited SMS support** - harder to use for texting
❌ **May seem less personal** - less "local" feel

**Best For:**
- Customer service lines
- National businesses
- Professional appearance
- When you want callers to dial for free

**Prefix Meanings:**
```
800: Original (1966) - most recognizable
888: Added 1996 - still very popular
877: Added 1998 - good availability
866: Added 2000 - decent availability
855: Added 2010 - good availability
844: Added 2013 - lots available
833: Added 2017 - newest, most available
```

**Recommendation:** Use **800** if available (most trusted), else **888** or **877**

---

## 💰 US Pricing (2025)

### DID (Local Number)

| Component | Rate | Notes |
|-----------|------|-------|
| **Monthly fee** | $0.03/month | Per number |
| **Inbound calls** | $0.0022/min | Per minute connected |
| **Outbound calls** | $0.0022/min | Per minute connected |
| **AWS Connect service** | $0.018/min | Base platform fee |
| **Total per inbound minute** | **$0.0202/min** | = $0.03/mo + $0.0022/min + $0.018/min |

**Example: 1,000 calls/month, 3 min avg = 3,000 minutes**
```
Phone number:    1 × $0.03     = $0.03
Inbound calls:   3,000 × $0.0022 = $6.60
Connect service: 3,000 × $0.018  = $54.00
─────────────────────────────────────
Total:                           $60.63/month
Per call:                        $0.06
```

---

### Toll-Free Number

| Component | Rate | Notes |
|-----------|------|-------|
| **Monthly fee** | $0.06/month | Per number |
| **Inbound calls** | $0.042/min | Per minute (includes telephony) |
| **Outbound calls** | $0.042/min | Per minute |
| **AWS Connect service** | $0.018/min | Base platform fee |
| **Total per inbound minute** | **$0.060/min** | = $0.06/mo + $0.042/min + $0.018/min |

**Example: 1,000 calls/month, 3 min avg = 3,000 minutes**
```
Phone number:    1 × $0.06     = $0.06
Inbound calls:   3,000 × $0.042  = $126.00
Connect service: 3,000 × $0.018  = $54.00
─────────────────────────────────────
Total:                           $180.06/month
Per call:                        $0.18
```

---

### Full Stack Costs (with AI services)

**Complete System: 1,000 calls/month, 3 min avg**

| Service | DID Cost | Toll-Free Cost |
|---------|----------|----------------|
| Phone number | $0.03 | $0.06 |
| Telephony | $6.60 | $126.00 |
| AWS Connect | $54.00 | $54.00 |
| **Amazon Lex** | $0.75 | $0.75 |
| **Bedrock (Claude Sonnet 4.5)** | $30.00 | $30.00 |
| **Amazon Transcribe** | $72.00 | $72.00 |
| **Contact Lens Analytics** | $45.00 | $45.00 |
| CloudWatch/S3 | $5.00 | $5.00 |
| **TOTAL** | **$213.38** | **$332.81** |
| **Per Call** | **$0.21** | **$0.33** |

**Key Takeaway:** Toll-free costs **56% more** than DID for US calls

---

### Cost Comparison: US vs India

**1,000 calls/month, 3 min avg**

| Region | Phone Type | Monthly Cost | Per Call |
|--------|------------|--------------|----------|
| **US** | DID | $213 | $0.21 |
| **US** | Toll-Free | $333 | $0.33 |
| **India** | DID | $475 | $0.48 |

**Why India costs more:**
- Higher telephony rates in India (~$0.006/min vs $0.0022/min US)
- More expensive transcription/analytics for non-US regions

---

## 🌎 US Number Capabilities

### What You Can Do

✅ **Inbound Voice Calls**
- Receive calls from US/Canada for free (local rates)
- International calls work (caller pays international rates)

✅ **Outbound Voice Calls**
- Call customers back
- Proactive appointment reminders
- Follow-up calls

✅ **SMS Messaging** (DID only)
- Two-way SMS (requires additional setup)
- Appointment confirmations
- Reminders and notifications
- Not available on toll-free (different setup)

✅ **MMS** (Multimedia Messaging)
- Send images, PDFs
- Appointment details with map
- Requires SMS-enabled DID

✅ **Call Recording**
- All calls recorded to S3
- Compliance and quality monitoring

✅ **Real-Time Transcription**
- Amazon Transcribe integration
- Live captions for agents
- Post-call analytics

✅ **Contact Lens Analytics**
- Sentiment analysis
- Category detection
- Supervisor escalation triggers

---

### Geographic Coverage

**US DID Numbers Work From:**
- ✅ All 50 US states
- ✅ Canada (most carriers)
- ✅ International (caller pays international rates)

**Toll-Free Numbers Work From:**
- ✅ United States (100% coverage)
- ✅ Canada (most carriers)
- ⚠️ Mexico (some carriers)
- ⚠️ International (limited support, caller may not reach)

**Best Practice:** If you need international reach, use **DID + virtual number service** (e.g., Twilio global routing)

---

## 🔧 Setup for Testing (While Waiting for Indian Number)

### Recommended Approach

**Use US number for Phase 3 development:**

1. **Week 1: Set Up with US Number**
   - Claim US DID (instant)
   - Build Lex bot, contact flows, bridge Lambda
   - Test end-to-end with US number

2. **Week 2-3: Continue Testing**
   - Test all conversation scenarios
   - Validate Bedrock integration
   - Load test with 100+ concurrent calls
   - QA and bug fixes

3. **Week 3-4: Indian Number Ready**
   - Claim Indian DID (when approved)
   - Reassign flows to Indian number
   - Test with Indian number
   - Switch DNS/website to Indian number

**Benefits:**
- ✅ Don't waste 2-3 weeks waiting for Indian approval
- ✅ Find bugs early with US number
- ✅ Team can test from anywhere
- ✅ No cost penalty (minimal usage during testing)

---

## 🚀 Quick Setup Script (US Number in 5 Minutes)

### Step-by-Step Checklist

**Minute 0-2: Create Instance**
- [ ] Open https://console.aws.amazon.com/connect/
- [ ] Region: us-east-1 or us-west-2
- [ ] Create instance: `scheduling-agent-us-test`
- [ ] Enable inbound + outbound calls
- [ ] Create admin user

**Minute 2-3: Claim Number**
- [ ] Login to instance
- [ ] Channels → Phone numbers → Claim number
- [ ] Select US (+1)
- [ ] Choose DID (local) or Toll-Free
- [ ] Pick a number
- [ ] Save

**Minute 3-4: Assign to Flow**
- [ ] Select your contact flow (or sample flow for testing)
- [ ] Save configuration

**Minute 4-5: Test**
- [ ] Call from your mobile
- [ ] Verify IVR answers
- [ ] Check real-time metrics

**✅ Done! US number is live!**

---

## 🌟 Best Practices for US Numbers

### 1. Choose Memorable Numbers

**Good:**
- +1 (800) 555-BOOK (2665)
- +1 (888) 123-4567
- +1 (877) PROJECT (776-5328)

**Avoid:**
- +1 (844) 927-8341 (hard to remember)

### 2. Use Vanity Numbers (If Possible)

**Examples:**
- 1-800-FLOORING
- 1-888-SCHEDULE
- 1-877-PROJECT-360

**How to Get:**
- AWS Connect may have limited vanity numbers available
- Or port existing vanity number from carrier

### 3. Test Before Going Live

**Checklist:**
- [ ] Call from US mobile (AT&T, Verizon, T-Mobile)
- [ ] Call from landline
- [ ] Test during business hours
- [ ] Test after hours (should play closed message)
- [ ] Test with background noise
- [ ] Test with strong accents
- [ ] Load test with 50+ concurrent calls

### 4. Set Up Call Recording

**Configuration:**
- Enable recording for all calls
- Store in S3 with 90-day retention
- Enable encryption (AWS KMS)
- Set up lifecycle policy (archive to Glacier after 90 days)

### 5. Monitor Metrics

**Key CloudWatch Metrics:**
```
ConcurrentCalls
MissedCalls
CallsPerInterval
AverageHandleTime
ContactFlowErrors
LexIntentMatches
```

**Set Alarms:**
- Alert at 80% capacity
- Alert on >5 errors/hour
- Alert on AHT >5 minutes

---

## 📊 US vs Indian Number: When to Use Each

| Use Case | US DID | Indian DID | Notes |
|----------|--------|------------|-------|
| **Testing & Development** | ✅ Best | ⏳ Wait | US is instant |
| **US Customers** | ✅ Required | ❌ No | Local presence |
| **Indian Customers** | ⚠️ Expensive | ✅ Required | International rates |
| **Global Customers** | ✅ Toll-free | ⚠️ Limited | Use both |
| **SMS Integration** | ✅ Easy | ⚠️ Complex | US SMS simpler |
| **Cost Optimization** | ✅ Cheaper | ❌ 2x cost | For US calls |
| **Professional Image** | ✅ Toll-free | ✅ Local DID | Both work |

---

## 🔄 Using Both US and Indian Numbers

### Multi-Region Strategy

**Recommended Setup:**

```
┌─────────────────────────────────────────────────────────────┐
│                        CUSTOMERS                            │
├─────────────────────────────────────────────────────────────┤
│  US Customers          Indian Customers      International  │
│  Call: +1 (800) XXX    Call: +91 XX XXXX   Call: Either    │
└───────┬────────────────────────┬──────────────────┬─────────┘
        │                        │                  │
        ↓                        ↓                  ↓
┌───────────────────┐   ┌───────────────────┐   ┌──────────┐
│ AWS Connect       │   │ AWS Connect       │   │  Choose  │
│ US Instance       │   │ India Instance    │   │  Closest │
│ (us-east-1)       │   │ (ap-south-1)      │   └──────────┘
└───────┬───────────┘   └────────┬──────────┘
        │                        │
        └────────────┬───────────┘
                     ↓
        ┌────────────────────────┐
        │   Amazon Lex (Global)  │
        └────────────┬───────────┘
                     ↓
        ┌────────────────────────┐
        │ Same Bedrock Agents    │
        │ (Supervisor + 4 Collab)│
        └────────────┬───────────┘
                     ↓
        ┌────────────────────────┐
        │ Same Lambda Functions  │
        │ (12 actions)           │
        └────────────────────────┘
```

**Benefits:**
- ✅ Lowest latency for each region
- ✅ Local phone numbers for each market
- ✅ Single backend (same agents/lambdas)
- ✅ Region-specific optimizations

**Setup:**
1. US instance: `us-east-1` with US DID
2. India instance: `ap-south-1` with Indian DID
3. Both instances call same Bedrock Supervisor
4. Same Lambda functions (cross-region invoke)

---

## 🆘 Troubleshooting US Numbers

### Issue: Number Not Available

**Symptoms:** Desired area code shows "No numbers available"

**Solutions:**
1. Try different area code in same city (e.g., NYC has 212, 646, 917)
2. Refresh after 5 minutes (numbers get released)
3. Use toll-free instead (always available)
4. Contact AWS Support to reserve specific number

---

### Issue: Calls Not Connecting

**Symptoms:** Number rings but doesn't connect

**Checklist:**
- [ ] Contact flow assigned to number?
- [ ] Contact flow published (not draft)?
- [ ] Hours of operation configured?
- [ ] Queue capacity not exceeded?
- [ ] CloudWatch logs show errors?

**Common Fix:** Assign contact flow to phone number (often forgotten!)

---

### Issue: Poor Call Quality

**Symptoms:** Audio choppy, robotic voice, delays

**Debugging:**
1. Check caller's network (WiFi vs cellular)
2. Test from different location
3. Review CloudWatch metrics: `CallQuality`
4. Check Transcribe accuracy (should be >90%)
5. Test with different TTS voice (Lex settings)

**Solutions:**
- Use neural TTS voices (better quality)
- Increase Lex timeout to 3-4 seconds
- Add `<break>` SSML tags for natural pauses

---

### Issue: High Costs

**Symptoms:** Bill higher than expected

**Cost Audit:**
```bash
# Check usage
aws ce get-cost-and-usage \
  --time-period Start=2025-10-01,End=2025-10-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE

# Focus on:
- Amazon Connect (should be ~$54/3000 min)
- Amazon Lex (~$0.75/1000 requests)
- Amazon Transcribe (~$72/3000 min)
```

**Optimization:**
- Use DID instead of toll-free (50% savings)
- Disable Contact Lens if not needed ($45/3000 min savings)
- Reduce transcription to calls needing it only
- Set call timeout to 5 minutes (prevent runaway costs)

---

## ✅ Pre-Launch Checklist (US Number)

### Before Going Live

**Infrastructure:**
- [ ] AWS Connect instance created
- [ ] US phone number claimed and active
- [ ] Contact flow designed and published
- [ ] Amazon Lex bot configured
- [ ] Bridge Lambda deployed
- [ ] Bedrock Agent integration tested

**Testing:**
- [ ] Called from AT&T mobile - works
- [ ] Called from Verizon mobile - works
- [ ] Called from T-Mobile mobile - works
- [ ] Called from landline - works
- [ ] Tested 10+ conversation scenarios
- [ ] Load tested 50 concurrent calls
- [ ] Verified call recordings saved to S3
- [ ] Verified transcriptions accurate (>90%)

**Monitoring:**
- [ ] CloudWatch dashboard configured
- [ ] Alarms set up (capacity, errors, AHT)
- [ ] SNS notifications configured
- [ ] Cost alerts enabled ($100, $200 thresholds)

**Documentation:**
- [ ] Internal runbook created
- [ ] Customer-facing scripts reviewed
- [ ] Escalation process documented

**Launch:**
- [ ] Soft launch (internal team only) - 1 week
- [ ] Beta launch (select customers) - 1 week
- [ ] Public launch
- [ ] Website updated with phone number
- [ ] Email blast to customers

---

## 📚 Additional Resources

### Official AWS Documentation
- [AWS Connect Admin Guide](https://docs.aws.amazon.com/connect/latest/adminguide/)
- [Claiming Phone Numbers](https://docs.aws.amazon.com/connect/latest/adminguide/contact-center-phone-number.html)
- [US Telephony Pricing](https://aws.amazon.com/connect/pricing/)

### Community Resources
- [AWS Connect Reddit](https://www.reddit.com/r/amazonconnect/)
- [AWS re:Post](https://repost.aws/tags/TAqDXD5uy2R_mrXTdWykfmVQ/amazon-connect)

---

## 🎯 Summary: US vs India Decision Tree

```
START: Which number should I use?

├─ Do you have US customers?
│  └─ YES → Claim US DID ($0.21/call)
│     └─ Want toll-free? → Claim toll-free ($0.33/call)
│
├─ Do you have Indian customers?
│  └─ YES → Submit Indian DID request (7-15 days)
│     └─ Need faster? → Use Twilio (1-2 days)
│
├─ Testing Phase 3 implementation?
│  └─ YES → Claim US DID (instant testing)
│     └─ Later switch to Indian DID when approved
│
├─ Global customers (US + India + others)?
│  └─ YES → Claim both US + Indian DIDs
│     └─ Route by caller geography
│
└─ Just need any number to test?
   └─ YES → Claim US DID (fastest, easiest)
```

---

## ⏭️ Next Steps

After claiming your US number:

1. **Integrate with Lex Bot**
   - See: PHASE3_IMPLEMENTATION_PLAN.md (Step 4)

2. **Create Contact Flows**
   - See: PHASE3_IMPLEMENTATION_PLAN.md (Step 6)

3. **Test End-to-End**
   - See: PHASE3_IMPLEMENTATION_PLAN.md (Step 7)

4. **Launch**
   - See: PHASE3_IMPLEMENTATION_PLAN.md (Step 8)

---

**Document Version:** 1.0
**Last Updated:** October 17, 2025
**Setup Time:** 5-10 minutes (instant!)

**Related Documents:**
- [PHASE3_QUICK_START.md](PHASE3_QUICK_START.md) - Overview
- [PHASE3_INDIAN_PHONE_SETUP.md](PHASE3_INDIAN_PHONE_SETUP.md) - Indian number guide
- [PHASE3_IMPLEMENTATION_PLAN.md](PHASE3_IMPLEMENTATION_PLAN.md) - Full implementation

---

**🚀 Ready to claim? Log into AWS Console and get your US number in 5 minutes!**
