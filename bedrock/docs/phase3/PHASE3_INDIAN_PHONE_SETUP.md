# Getting an Indian Phone Number for AWS Connect

**Date:** October 17, 2025
**Purpose:** Step-by-step guide to claim an Indian phone number for voice calls
**Estimated Time:** 7-15 business days

---

## 📋 Overview

This guide walks you through the process of obtaining an **Indian phone number** (+91) for use with AWS Connect. The process is more complex than US/EU numbers due to Indian telecom regulations.

### What You'll Get

✅ **Indian Direct Inward Dialing (DID)** number: +91 XXXX XXXXXX
✅ **Inbound call capability** for customers in India
✅ **Low-latency routing** via Mumbai (ap-south-1) region
✅ **Full AWS Connect integration** (IVR, recording, analytics)

---

## 🎯 Prerequisites

### 1. Business Requirements

You MUST have **ONE** of the following:

#### Option A: Indian Registered Business ✅ (Recommended)
- Company registered in India (Pvt Ltd, LLP, Partnership, Proprietorship)
- Valid GST registration
- Indian business address

#### Option B: International Business with Indian Presence
- Parent company registered outside India
- Subsidiary/branch office in India
- Indian business address
- Agent/representative in India

#### Option C: Third-Party Telecom Provider ⚠️ (Alternative)
- Use services like Twilio, Exotel, Knowlarity
- Forward calls to AWS Connect
- Faster approval but extra costs

**Important:** If you don't have Option A or B, use **Option C** (detailed below)

---

### 2. Required Documents Checklist

Prepare these documents **before** starting:

#### For Indian Companies:
- [ ] **Certificate of Incorporation** (scanned copy)
- [ ] **GST Registration Certificate** (GSTIN)
- [ ] **PAN Card** (company PAN)
- [ ] **Address Proof:**
  - [ ] Electricity bill (< 3 months old)
  - [ ] Water bill (< 3 months old)
  - [ ] Lease agreement with notarization
- [ ] **Authorized Signatory Proof:**
  - [ ] Director/Partner Aadhaar card OR Passport
  - [ ] Board resolution (for Pvt Ltd companies)
- [ ] **Letter of Authorization (LOA)** - Template provided below

#### For International Companies with Indian Presence:
- [ ] Parent company incorporation certificate
- [ ] Indian branch office registration
- [ ] FEMA approval (if applicable)
- [ ] Indian address proof (lease, utility bill)
- [ ] Authorized representative ID (Indian resident)
- [ ] LOA on parent company letterhead

---

## 🚀 Method 1: Direct AWS Connect DID (7-15 Days)

### Step 1: Prepare Letter of Authorization (LOA)

**Download template:** Create this document on your company letterhead

```
[Company Letterhead]

Date: [Today's Date]

To: Amazon Web Services India Pvt Ltd
Block E, 14th Floor
International Trade Tower
Nehru Place
New Delhi - 110019
India

Subject: Letter of Authorization for Telecom Services

Dear Sir/Madam,

We, [COMPANY NAME], a company registered under the Companies Act with
Corporate Identity Number [CIN NUMBER], having our registered office at
[FULL ADDRESS], hereby authorize Amazon Web Services India Pvt Ltd (AWS)
to:

1. Acquire telephone number(s) on our behalf from licensed telecom operators
   in India for the purpose of establishing a cloud-based contact center.

2. Use said telephone number(s) exclusively for:
   - Inbound customer service calls
   - Customer appointment scheduling
   - Project information queries
   - Outbound customer callbacks (optional)

3. Route all telephony traffic through AWS infrastructure located in the
   Asia Pacific (Mumbai) region.

Company Details:
- Company Name: [FULL LEGAL NAME]
- CIN: [CIN NUMBER]
- GST: [GSTIN]
- PAN: [PAN NUMBER]
- Registered Address: [FULL ADDRESS]
- Contact Person: [NAME], [DESIGNATION]
- Contact Phone: [PHONE]
- Contact Email: [EMAIL]

We confirm that we shall use these services in compliance with:
- The Indian Telegraph Act, 1885
- Telecom Regulatory Authority of India (TRAI) regulations
- All applicable Indian telecommunications laws

This authorization is valid for a period of [1 year / until revoked].

Authorized Signatory:

_______________________
[Name]
[Designation]
[Company Stamp]

Place: [City]
Date: [Date]
```

**Important:** Must be on **company letterhead** with **official stamp**

---

### Step 2: Submit Documents via AWS Support

**Process:**

1. **Open AWS Console**
   - Go to: https://console.aws.amazon.com/support/
   - Sign in with account that has AWS Connect access

2. **Create Support Case**
   - Click **Create case**
   - Case type: **Service limit increase**
   - Service: **Amazon Connect**

3. **Fill Case Details**
   ```
   Subject: Request for Indian DID Number - Amazon Connect

   Description:
   Dear AWS Support,

   We request approval to claim an Indian Direct Inward Dialing (DID) number
   for our Amazon Connect instance.

   Details:
   - AWS Account ID: [YOUR ACCOUNT ID]
   - AWS Connect Instance: scheduling-agent-india
   - Region: ap-south-1 (Mumbai)
   - Phone Number Type: Geographic DID (local number)
   - Preferred City: [Mumbai / Delhi / Bangalore / etc.]
   - Expected Call Volume: [500 calls/month initially]
   - Use Case: Customer service IVR for appointment scheduling

   We have attached all required compliance documents:
   1. Certificate of Incorporation
   2. GST Registration Certificate
   3. Company PAN Card
   4. Address Proof (Electricity Bill)
   5. Authorized Signatory ID (Aadhaar/Passport)
   6. Board Resolution
   7. Letter of Authorization (LOA)

   Please let us know if any additional information is required.

   Thank you.
   ```

4. **Attach All Documents**
   - Upload all 7 documents listed above
   - Ensure files are PDF format, <5MB each
   - Name files clearly: `LOA.pdf`, `GST_Certificate.pdf`, etc.

5. **Submit Case**
   - Priority: Normal
   - Contact method: Email (faster than phone)

---

### Step 3: AWS Review Process

**What Happens:**

**Week 1:**
- AWS support acknowledges case (1-2 hours)
- Reviews documents for completeness
- May request additional info or clarifications

**Week 2:**
- AWS forwards request to Indian telecom carrier partner
- Carrier validates business registration
- Carrier checks address proof
- Carrier may contact you directly for verification

**Week 2-3:**
- Carrier approves request
- AWS provisions number in your region
- You receive approval notification email

**Timeline:**
- **Fastest:** 7 business days (if all docs perfect)
- **Average:** 10-12 business days
- **Slowest:** 15 business days (if issues with docs)

---

### Step 4: Claim Number in AWS Connect

Once approved, AWS will notify you. Then:

1. **Open AWS Connect Console**
   - Go to: https://ap-south-1.console.aws.amazon.com/connect/

2. **Select Your Instance**
   - Click `scheduling-agent-india`

3. **Go to Phone Numbers**
   - Left menu → **Channels** → **Phone numbers**
   - Click **Claim a number**

4. **Select Your Number**
   - Country: **India (+91)**
   - Type: **DID**
   - You should now see available numbers
   - Select number with desired city code:
     - Mumbai: +91 22 XXXX XXXX
     - Delhi: +91 11 XXXX XXXX
     - Bangalore: +91 80 XXXX XXXX
     - Chennai: +91 44 XXXX XXXX

5. **Assign to Contact Flow**
   - Flow: Select `SchedulingAgentMainFlow` (created in Phase 3.3)
   - Description: "Main IVR for customer calls"
   - Click **Save**

6. **Test Immediately**
   - Call the number from your mobile
   - Should hear IVR greeting
   - Test full conversation flow

---

## 🏃 Method 2: Fast Alternative - Twilio → AWS Connect (1-2 Days)

If you need to launch **immediately** while waiting for AWS DID approval:

### Why Twilio?

✅ **Much faster approval** - 1-2 days vs 2 weeks
✅ **Easier compliance** - Twilio handles Indian telecom regulations
✅ **Same functionality** - Calls forward seamlessly to AWS Connect
✅ **Migration path** - Switch to native AWS DID later

❌ **Extra cost** - ~$0.01/min forwarding fee
❌ **Slight latency** - +50-100ms call routing delay

---

### Twilio Setup Process

#### Step 1: Get Twilio Indian Number

1. **Sign up for Twilio**
   - Go to: https://www.twilio.com/
   - Create account (free trial available)

2. **Complete Indian Compliance**
   - Go to: Twilio Console → Regulatory Compliance
   - Submit same documents as AWS (faster review)
   - Approval: 1-2 business days

3. **Buy Indian Number**
   - Go to: Phone Numbers → Buy a Number
   - Country: India
   - Capabilities: ✅ Voice
   - Select number, purchase (~$1/month)

#### Step 2: Configure SIP Trunk to AWS Connect

**In Twilio Console:**

1. **Create TwiML App**
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <Response>
       <Dial>
           <Sip>
               sip:@[YOUR-CONNECT-INSTANCE].awsapps.com
           </Sip>
       </Dial>
   </Response>
   ```

2. **Assign to Phone Number**
   - Phone Numbers → Active Numbers
   - Select your Indian number
   - Voice → TwiML App → [Your App]

**In AWS Connect:**

1. **Enable SIP Trunk**
   - Connect Console → Channels → Phone numbers
   - Allow external SIP connections

2. **Whitelist Twilio IPs**
   - Add Twilio's SIP IPs to allowed list

3. **Test Call Forwarding**
   - Call Twilio number
   - Should forward to AWS Connect
   - IVR should play

---

### Twilio Cost Analysis

| Component | Cost |
|-----------|------|
| **Twilio Indian Number** | $1.00/month |
| **Inbound to Twilio** | $0.0085/min |
| **Twilio → AWS Connect Forward** | $0.012/min |
| **AWS Connect Processing** | $0.038/min |
| **Total per Minute** | $0.0585/min |

**Comparison:**
- Native AWS DID: $0.044/min
- Twilio + AWS: $0.0585/min
- **Extra cost:** ~$0.015/min (+30%)

**For 500 calls/month (5 min avg):**
- Native AWS: $110/month
- Twilio + AWS: $146/month
- **Difference:** $36/month

**Recommendation:** Use Twilio for **first 1-2 months** while AWS DID is being approved, then migrate.

---

## 🔄 Migration from Twilio to Native AWS DID

When your AWS DID is approved:

### Step 1: Parallel Testing (Week 1)
- Keep Twilio number active
- Test AWS DID with internal team
- Verify all features work

### Step 2: Gradual Migration (Week 2)
- Publish AWS DID on website (new number)
- Keep Twilio active for existing customers
- Forward Twilio to AWS DID (number porting info)

### Step 3: Full Cutover (Week 3-4)
- All customers use AWS DID
- Twilio number redirects to AWS DID
- After 30 days: Cancel Twilio

---

## 💰 Cost Comparison

### Monthly Costs (500 calls, 5 min avg = 2,500 minutes)

| Method | Setup | Monthly | Per-Minute | Notes |
|--------|-------|---------|------------|-------|
| **AWS Connect DID** | 2 weeks wait | $110 | $0.044 | Lowest cost, longer setup |
| **Twilio + AWS** | 1-2 days | $146 | $0.058 | Fastest, 30% more expensive |
| **Exotel + AWS** | 3-5 days | $135 | $0.054 | Indian company, good support |

**Recommended Strategy:**
1. **Month 1-2:** Twilio (fast launch)
2. **Month 3+:** Native AWS DID (cost optimization)

---

## 📞 Alternative Indian Telecom Providers

### Option: Exotel (Indian Company)

**Pros:**
✅ Indian company, easier compliance
✅ Better India-specific support
✅ 3-5 day approval
✅ Good for Indian market

**Cons:**
❌ More expensive than AWS native
❌ Extra integration layer

**Setup:** Similar to Twilio, use SIP forwarding to AWS Connect

**Pricing:** ~$0.012/min + AWS Connect fees

---

### Option: Knowlarity

**Pros:**
✅ Enterprise-grade reliability
✅ Strong in India market
✅ Faster approval (3-5 days)

**Cons:**
❌ Higher minimum commitment
❌ More complex pricing

---

## 🛠️ Troubleshooting

### Issue: Document Rejection

**Common Reasons:**
- Address proof >3 months old
- LOA not on letterhead
- Missing company stamp
- Unclear scans (photos instead of scans)

**Solution:**
- Use scanner, not phone camera
- Ensure all text is readable
- Get fresh utility bill if needed
- Have LOA notarized if possible

---

### Issue: Long Approval Time (>15 Days)

**Actions:**
1. Reply to AWS support case asking for status update
2. Check if carrier contacted you directly (check spam folder)
3. Escalate via AWS account manager if available
4. Use Twilio as interim solution

---

### Issue: Number Not Available in Desired City

**Solution:**
- Most flexible: Choose Mumbai (largest pool)
- Alternative: Delhi, Bangalore
- Toll-free: Available nationally but longer approval

---

## ✅ Pre-Launch Checklist

Before going live with Indian number:

- [ ] Phone number claimed and active
- [ ] Assigned to main contact flow
- [ ] Test call from Indian mobile network (Airtel/Jio/Vodafone)
- [ ] Test call from landline
- [ ] Verify caller ID shows correctly
- [ ] Verify call quality (audio clear both ways)
- [ ] Test IVR menu navigation
- [ ] Test Lex intent recognition
- [ ] Test Bedrock Agent responses
- [ ] Verify call recording works
- [ ] Check CloudWatch logs
- [ ] Confirm billing is working
- [ ] Load test with 10 concurrent calls
- [ ] Update website with new number
- [ ] Train customer service team
- [ ] Prepare customer communication

---

## 📊 Regional Coverage in India

### AWS Connect Regions

**Primary:** `ap-south-1` (Mumbai) ✅ Recommended
- Lowest latency for Indian customers
- Full feature support
- Indian DID numbers available

**Backup:** `ap-southeast-1` (Singapore)
- Fallback for disaster recovery
- Higher latency (~50ms)
- Can claim Indian numbers but slower

---

### Indian Mobile Carriers Supported

AWS Connect works with **all major Indian carriers:**

✅ Reliance Jio
✅ Bharti Airtel
✅ Vodafone Idea (Vi)
✅ BSNL/MTNL
✅ All MVNO operators

**Call Quality:** Excellent (HD voice where supported)

---

## 🎓 Best Practices

### 1. Start Early
Submit DID request **before** building Lex/Connect flows. Parallel work saves time.

### 2. Have Backup Plan
Always have Twilio as fallback in case of AWS DID delays.

### 3. Test Thoroughly
Test from multiple carriers (Jio, Airtel, Vi) before public launch.

### 4. Monitor Closely
First week: Check CloudWatch hourly. Week 2-4: Daily monitoring.

### 5. Gather Feedback
First 100 calls: Survey customers on call quality and experience.

---

## 📞 Support Contacts

### AWS Support
- **Indian Support:** Available 24/7 in English/Hindi
- **Phone:** 1800-212-2354 (toll-free from India)
- **Email:** Via AWS Support Console

### Twilio Support
- **India Support:** Business hours IST
- **Email:** help@twilio.com
- **Docs:** https://www.twilio.com/docs/voice/india

---

## 📚 Additional Resources

### Official Documentation
- [AWS Connect in India](https://aws.amazon.com/connect/resources/)
- [TRAI Regulations](https://www.trai.gov.in/)
- [Indian Telecom Guidelines](https://dot.gov.in/)

### Community Resources
- [AWS India Slack Community](https://aws-india.slack.com/)
- [AWS re:Post for Connect](https://repost.aws/tags/TAqDXD5uy2R_mrXTdWykfmVQ/amazon-connect)

---

## 🎯 Success Criteria

You'll know setup is successful when:

✅ Indian number shows in AWS Connect console
✅ Test call connects and plays IVR
✅ Lex recognizes voice input correctly
✅ Bedrock Agent responds appropriately
✅ Call recording appears in S3
✅ CloudWatch shows successful flow
✅ No audio quality issues
✅ Latency <200ms end-to-end

---

## ⏭️ Next Steps

After getting your Indian phone number:

1. **Configure Lex Bot** - See PHASE3_IMPLEMENTATION_PLAN.md (Step 4)
2. **Build Contact Flows** - See PHASE3_IMPLEMENTATION_PLAN.md (Step 6)
3. **Test End-to-End** - See PHASE3_IMPLEMENTATION_PLAN.md (Step 7)
4. **Launch** - See PHASE3_IMPLEMENTATION_PLAN.md (Step 8)

---

**Document Version:** 1.0
**Last Updated:** October 17, 2025
**Estimated Setup Time:** 7-15 business days (AWS native) or 1-2 days (Twilio)

**Related Documents:**
- [PHASE3_IMPLEMENTATION_PLAN.md](PHASE3_IMPLEMENTATION_PLAN.md) - Main implementation guide
- [PHASE3_AWS_CONNECT_RESEARCH.md](PHASE3_AWS_CONNECT_RESEARCH.md) - Technical research

---

**Need Help?** Open an AWS Support case or check the troubleshooting section above.
