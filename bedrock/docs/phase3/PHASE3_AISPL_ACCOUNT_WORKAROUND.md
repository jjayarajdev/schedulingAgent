# AWS Connect with AISPL Account - Workarounds

**Date:** October 17, 2025
**Issue:** Cannot create AWS Connect instance with AISPL account
**Status:** Known limitation with multiple workarounds

---

## 🚨 The Problem

### Error Message

```
An error occurred while creating scheduling-agent-us-test instance.

You're signed in with an AWS account that was provided by AISPL.
These accounts cannot create Amazon Connect instances.
Sign in using an account provided by AWS, and then try to create
an instance. Please contact support if you need further assistance.
```

### What is AISPL?

**AISPL** = **Amazon Internet Services Private Limited**

- AWS's **Indian subsidiary** that provides AWS services in India
- Required for Indian customers due to Indian tax and regulatory requirements
- Account region: India
- Billing entity: AISPL (shows on invoice as "Amazon Internet Services Pvt Ltd")
- GST compliance: Indian GST charged on invoices

### Why the Restriction?

AWS Connect is **NOT available** for AISPL accounts due to:
1. **Telecom regulations** - Indian telecom licensing requirements
2. **Data residency** - Voice data storage regulations in India
3. **Licensing complexity** - AWS hasn't obtained Indian telecom operator license for AISPL

**Impact:** You **cannot** create AWS Connect instances with AISPL account in **any region** (not even US regions)

---

## ✅ Solution: Multiple Workarounds

You have **3 options** to proceed with Phase 3 voice integration:

---

## 🎯 Option 1: Create New AWS Global Account (Recommended)

### Overview

Create a **separate AWS account** (non-AISPL, global AWS) specifically for AWS Connect, while keeping your AISPL account for other services.

### Steps

#### Step 1: Create New AWS Account

1. **Sign Out of Current AISPL Account**
   - AWS Console → Sign out

2. **Create New AWS Account**
   - Go to: https://portal.aws.amazon.com/billing/signup
   - Use **different email** address (e.g., aws-connect@yourcompany.com)
   - **Important:** Use **non-Indian billing address**
     - Use US address (company US office, or registered agent)
     - Use US credit card (if available)
     - Or use international credit card with non-India billing address

3. **Account Details**
   ```
   Email: aws-connect@yourcompany.com
   Account name: YourCompany-Connect

   Billing Address:
   - Country: United States (or other non-India country)
   - Address: [Your US office or registered agent]
   - Payment method: International credit card
   ```

4. **Verify Account**
   - Phone verification (use international number or US number)
   - Credit card verification ($1 charge)

5. **Wait 5-10 Minutes**
   - Account activation

#### Step 2: Set Up AWS Connect in New Account

1. **Sign In to New Global Account**
   - Use new email/password

2. **Create AWS Connect Instance**
   - Follow PHASE3_US_PHONE_SETUP.md
   - Region: us-east-1 or us-west-2
   - Claim US phone number (instant)

3. **Create Amazon Lex Bot**
   - Same region as Connect instance

#### Step 3: Connect to AISPL Account Resources

**Architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│               NEW GLOBAL AWS ACCOUNT                        │
│                                                             │
│  • AWS Connect (us-east-1)                                 │
│  • Amazon Lex (us-east-1)                                  │
│  • Bridge Lambda (us-east-1)                               │
│                                                             │
│  Phone number: +1 (800) XXX-XXXX                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ (Cross-account invocation)
                     ↓
┌─────────────────────────────────────────────────────────────┐
│               EXISTING AISPL ACCOUNT                        │
│                                                             │
│  • Bedrock Agents (ap-south-1)                             │
│  • Lambda Functions (ap-south-1)                           │
│  • Aurora PostgreSQL (ap-south-1)                          │
│  • DynamoDB, Redis                                         │
└─────────────────────────────────────────────────────────────┘
```

**Cross-Account Setup:**

**In AISPL Account (ap-south-1):**
1. Create IAM role for cross-account access
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Principal": {
         "AWS": "arn:aws:iam::[NEW-ACCOUNT-ID]:root"
       },
       "Action": "sts:AssumeRole"
     }]
   }
   ```

2. Attach permissions:
   - Bedrock Agent invoke permission
   - Lambda invoke permission (for your 12 actions)

**In Global Account (us-east-1):**
1. Bridge Lambda assumes role in AISPL account
2. Invokes Bedrock Agent in ap-south-1
3. Returns response to Lex → Connect

**Example Bridge Lambda Code:**
```python
import boto3

# Assume role in AISPL account
sts = boto3.client('sts')
assumed_role = sts.assume_role(
    RoleArn='arn:aws:iam::[AISPL-ACCOUNT]:role/ConnectCrossAccountRole',
    RoleSessionName='connect-bridge'
)

# Create Bedrock client in AISPL account
bedrock = boto3.client(
    'bedrock-agent-runtime',
    region_name='ap-south-1',
    aws_access_key_id=assumed_role['Credentials']['AccessKeyId'],
    aws_secret_access_key=assumed_role['Credentials']['SecretAccessKey'],
    aws_session_token=assumed_role['Credentials']['SessionToken']
)

# Invoke Bedrock Agent in AISPL account
response = bedrock.invoke_agent(
    agentId='5VTIWONUMO',  # Your existing supervisor in AISPL
    agentAliasId='HH2U7EZXMW',
    sessionId=session_id,
    inputText=user_message
)
```

### Pros & Cons

**Pros:**
✅ **Full AWS Connect features** - No limitations
✅ **US phone numbers** - Instant claiming
✅ **Reuse existing agents** - Cross-account invoke
✅ **Keep AISPL benefits** - Indian tax compliance, Bedrock in India
✅ **Clean separation** - Voice in one account, data in another

**Cons:**
❌ **Two accounts to manage** - Extra complexity
❌ **Cross-account latency** - +20-50ms (us-east-1 → ap-south-1)
❌ **Two bills** - One AISPL, one global AWS
❌ **Data transfer costs** - $0.01/GB across accounts

### Cost Impact

**Extra Costs:**
- Cross-region data transfer: ~$0.01/GB = ~$0.30/month (for 30GB voice traffic)
- Negligible compared to overall Connect costs

**Billing:**
- **Global Account:** AWS Connect, Lex, Transcribe (~$200/month)
- **AISPL Account:** Bedrock, Lambda, databases (~$150/month)
- **Total:** ~$350/month (same as single account)

---

## 🎯 Option 2: Use Twilio + AISPL Account

### Overview

Use **Twilio** for voice handling, forward to your existing Bedrock Agents in AISPL account via API.

### Architecture

```
Customer → Twilio Phone Number → Twilio Voice API
                                      ↓
                            API Gateway (AISPL account)
                                      ↓
                            Lambda (AISPL account)
                                      ↓
                            Bedrock Agent (AISPL account)
```

### Steps

1. **Sign Up for Twilio**
   - Go to: https://www.twilio.com/
   - Twilio accepts Indian companies
   - No AISPL restrictions

2. **Get Indian Phone Number**
   - Twilio Console → Phone Numbers → Buy
   - Select India (+91)
   - Approval: 1-2 days with docs

3. **Create Twilio Voice Handler**
   - TwiML bin that calls your API Gateway
   - API Gateway → Lambda → Bedrock Agent

4. **Configure Voice Flow**
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <Response>
       <Gather input="speech" action="https://your-api.execute-api.ap-south-1.amazonaws.com/prod/voice">
           <Say>Thank you for calling. How can I help you?</Say>
       </Gather>
   </Response>
   ```

### Pros & Cons

**Pros:**
✅ **Works with AISPL account** - No account change needed
✅ **Indian phone numbers** - Easier compliance
✅ **Fast setup** - 1-2 days for Indian number
✅ **Proven solution** - Many Indian companies use this

**Cons:**
❌ **No AWS Connect features** - No Contact Lens, no native analytics
❌ **More code** - Need to build voice handling logic
❌ **Twilio costs** - Extra layer of charges (~30% more expensive)
❌ **Less integration** - Not native AWS

### Cost Comparison

**Twilio + Lambda (1,000 calls/month, 3 min avg):**

| Component | Cost |
|-----------|------|
| Twilio Indian number | $1/month |
| Twilio inbound calls | $0.0085/min × 3,000 = $25.50 |
| Twilio → API forward | $0.005/min × 3,000 = $15.00 |
| API Gateway | $3.50/1M requests = $0.004 |
| Lambda (AISPL account) | $5.00 |
| Bedrock (AISPL account) | $30.00 |
| **Total** | **~$76.50/month** |

**vs AWS Connect (if allowed):** ~$213/month

**Savings:** 64% cheaper! (But less features)

---

## 🎯 Option 3: Partner with Indian Telecom Provider

### Overview

Use Indian cloud contact center providers that have proper telecom licenses, integrate with your AWS Bedrock Agents.

### Recommended Providers

**1. Exotel** (Indian company)
- Indian telecom license
- Voice API
- Integrates with external AI (your Bedrock)
- Cost: ~₹0.50/min inbound

**2. Knowlarity**
- Enterprise contact center
- Cloud telephony platform
- API-first architecture
- Cost: ~₹0.40/min inbound

**3. Ozonetel**
- Indian cloud contact center
- Omnichannel platform
- AI integration support
- Cost: ~₹0.45/min inbound

### Architecture

```
Customer → Exotel Number → Exotel Voice Platform
                                 ↓
                        Webhook to your API Gateway
                                 ↓
                        Lambda → Bedrock Agent (AISPL)
```

### Pros & Cons

**Pros:**
✅ **Fully compliant** - Indian telecom licenses
✅ **Indian phone numbers** - Easy to get
✅ **Works with AISPL** - No account issues
✅ **Local support** - Indian customer support teams
✅ **Battle-tested** - Used by major Indian companies

**Cons:**
❌ **Vendor lock-in** - Tied to their platform
❌ **Integration work** - API integration needed
❌ **Less AWS features** - Not native AWS ecosystem
❌ **Potentially expensive** - Depends on contract

---

## 📊 Decision Matrix

| Factor | New AWS Account | Twilio + AISPL | Indian Provider |
|--------|-----------------|----------------|-----------------|
| **Setup Time** | 1 day | 2-3 days | 3-5 days |
| **Compliance** | ⚠️ Need US address | ✅ Easy | ✅ Perfect |
| **AWS Integration** | ✅ Perfect | ⚠️ Manual | ⚠️ Manual |
| **Cost** | $$$ | $ | $$ |
| **Features** | ✅ All Connect | ⚠️ Limited | ⚠️ Limited |
| **Indian Number** | ⏳ Hard | ✅ Easy | ✅ Easy |
| **Maintenance** | 2 accounts | Medium | Medium |
| **Best For** | US customers | Budget/testing | Indian production |

---

## 🎯 Recommended Approach

### For Your Specific Case (Indian Customers + Bedrock in AISPL)

**Recommended: Option 2 (Twilio) + Transition to Option 3 (Indian Provider)**

**Phase 1 (Month 1-2): Twilio for Quick Launch**
- Sign up for Twilio
- Get Indian number (1-2 days)
- Build voice handler Lambda
- Integrate with Bedrock (AISPL account)
- Launch and validate

**Phase 2 (Month 3+): Migrate to Exotel/Knowlarity**
- Evaluate Indian providers
- Negotiate enterprise contract
- Migrate from Twilio to Indian provider
- Better long-term cost and compliance

**Why Not Option 1 (New AWS Account)?**
- Your Bedrock Agents are in AISPL (ap-south-1)
- Cross-account, cross-region adds latency
- Managing two accounts is complex
- Indian customers calling US number = expensive

---

## 🚀 Immediate Next Steps (Twilio Approach)

### Day 1: Set Up Twilio

1. **Create Twilio Account**
   - Go to: https://www.twilio.com/try-twilio
   - Sign up with company email
   - Verify phone + credit card

2. **Get Test Number (Instant)**
   - Twilio Console → Phone Numbers → Buy
   - Select **United States** (for testing)
   - Cost: $1/month
   - Can test immediately

3. **Request Indian Number** (Parallel)
   - Go to: Regulatory Compliance
   - Submit company docs (same as AWS Indian DID)
   - Approval: 1-2 days

### Day 2: Build Voice Handler

4. **Create API Gateway in AISPL Account**
   ```bash
   # In AISPL account (ap-south-1)
   aws apigateway create-rest-api \
     --name voice-handler \
     --region ap-south-1
   ```

5. **Create Lambda Function**
   ```python
   # voice_handler.py
   import boto3
   import json

   bedrock = boto3.client('bedrock-agent-runtime', region_name='ap-south-1')

   def lambda_handler(event, context):
       # Parse Twilio request
       speech_text = event['SpeechResult']
       caller_phone = event['From']

       # Call Bedrock Agent (existing in AISPL)
       response = bedrock.invoke_agent(
           agentId='5VTIWONUMO',
           agentAliasId='HH2U7EZXMW',
           sessionId=f"twilio-{caller_phone}",
           inputText=speech_text
       )

       # Return TwiML
       twiml = f"""
       <?xml version="1.0" encoding="UTF-8"?>
       <Response>
           <Say>{response_text}</Say>
           <Gather input="speech" action="{api_endpoint}">
               <Say>Is there anything else?</Say>
           </Gather>
       </Response>
       """
       return {
           'statusCode': 200,
           'headers': {'Content-Type': 'text/xml'},
           'body': twiml
       }
   ```

6. **Deploy Lambda**
   ```bash
   zip voice_handler.zip voice_handler.py
   aws lambda create-function \
     --function-name twilio-voice-handler \
     --runtime python3.11 \
     --role arn:aws:iam::[AISPL-ACCOUNT]:role/lambda-role \
     --handler voice_handler.lambda_handler \
     --zip-file fileb://voice_handler.zip \
     --region ap-south-1
   ```

7. **Connect API Gateway to Lambda**
   - Create POST /voice endpoint
   - Integrate with Lambda
   - Deploy to prod stage

8. **Configure Twilio Number**
   - Twilio Console → Phone Numbers → Active Numbers
   - Select your number
   - Voice & Fax → "A CALL COMES IN"
   - Webhook: `https://[YOUR-API-GW].execute-api.ap-south-1.amazonaws.com/prod/voice`
   - HTTP POST

9. **Test**
   - Call Twilio number
   - Should hear greeting
   - Say something → Should get Bedrock response

---

## 💰 Updated Cost Estimates (Twilio Approach)

### Monthly Costs (500 calls/month, 5 min avg = 2,500 minutes)

| Component | Cost |
|-----------|------|
| **Twilio Indian Number** | $1.00 |
| **Twilio Inbound** | 2,500 × $0.0085 = $21.25 |
| **Twilio Voice Minutes** | 2,500 × $0.005 = $12.50 |
| **API Gateway** | 500 requests × $3.50/1M = $0.002 |
| **Lambda (AISPL)** | $2.00 |
| **Bedrock (AISPL)** | $15.00 |
| **DynamoDB/Aurora** | $20.00 |
| **Total** | **~$71.75/month** |

**Per Call:** $0.14 (vs $0.48 with full AWS Connect + Indian DID)

**Savings:** 70% cheaper than AWS Connect approach!

---

## 🎓 Alternative: Wait for AWS Connect in AISPL

### Future Possibility

AWS **may** eventually support AWS Connect for AISPL accounts, but:

⏳ **Timeline:** Unknown (could be 6-12+ months, or never)
⏳ **Requirements:** AWS would need Indian telecom operator license
⏳ **No official announcement:** No public roadmap item

**Recommendation:** Don't wait. Use workaround above (Twilio or Indian provider)

---

## 📚 Additional Resources

### Cross-Account IAM Setup
- [AWS Cross-Account Access](https://docs.aws.amazon.com/IAM/latest/UserGuide/tutorial_cross-account-with-roles.html)

### Twilio Documentation
- [Twilio Voice API](https://www.twilio.com/docs/voice)
- [Twilio India Compliance](https://www.twilio.com/docs/phone-numbers/regulatory/getting-started/india)

### Indian Telecom Providers
- [Exotel](https://exotel.com/)
- [Knowlarity](https://www.knowlarity.com/)
- [Ozonetel](https://www.ozonetel.com/)

---

## ✅ Action Plan (Revised)

### What to Do Right Now

**✅ Accept the Reality:**
- You cannot use AWS Connect with AISPL account
- This is a permanent AWS limitation (not a bug)

**✅ Choose Your Path:**
1. **For quick launch + Indian customers:** Use Twilio (recommended)
2. **For US customers + full features:** Create new global AWS account
3. **For enterprise/long-term:** Partner with Exotel or Knowlarity

**✅ Immediate Actions (Twilio Path):**
1. Sign up for Twilio today
2. Get US test number (instant)
3. Build voice handler Lambda in AISPL account
4. Request Indian Twilio number (parallel)
5. Test with US number while waiting
6. Switch to Indian number when approved (1-2 days)

**Timeline to Launch:** 3-5 days (vs 4 weeks with AWS Connect)

**Cost:** ~$72/month (vs $238/month with AWS Connect)

---

## 🆘 Need Help?

**For Twilio Setup:**
- Twilio Support: help@twilio.com
- Documentation: https://www.twilio.com/docs

**For Cross-Account AWS:**
- AWS Support (both accounts)
- Create support case in each account

**For Indian Providers:**
- Exotel: sales@exotel.com
- Knowlarity: sales@knowlarity.com

---

**Document Version:** 1.0
**Last Updated:** October 17, 2025
**Issue:** AISPL account limitation
**Workarounds:** 3 options provided (Twilio recommended)

---

**Bottom Line:** Your AISPL account cannot use AWS Connect. Use Twilio + your existing Bedrock Agents in AISPL account for fastest, cheapest path to launch. (~$72/month, 3-5 days to launch)
