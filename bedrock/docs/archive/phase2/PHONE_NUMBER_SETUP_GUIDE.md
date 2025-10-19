# Phone Number Setup & Two-Way Messaging Configuration

**Purpose:** Step-by-step guide for configuring AWS End User Messaging SMS phone number and two-way messaging
**Audience:** DevOps, Backend Engineers
**Duration:** 15 minutes setup + 2-4 weeks provisioning wait time

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Step 1: Request Phone Number](#step-1-request-phone-number)
4. [Step 2: Monitor Provisioning Status](#step-2-monitor-provisioning-status)
5. [Step 3: Configure Two-Way Messaging](#step-3-configure-two-way-messaging)
6. [Step 4: Testing](#step-4-testing)
7. [Troubleshooting](#troubleshooting)
8. [FAQ](#faq)

---

## Overview

AWS End User Messaging SMS requires manual phone number provisioning and two-way messaging configuration through the AWS Console. This guide covers the complete process from request to production.

### Timeline

| Phase | Duration | What Happens |
|-------|----------|--------------|
| **Request Submission** | 5 minutes | You submit phone number request |
| **AWS Review** | 1-3 days | AWS reviews your account/use case |
| **Provisioning** | 2-4 weeks | Carrier provisions toll-free number |
| **Configuration** | 10 minutes | You configure two-way messaging |
| **Testing** | 30 minutes | Verify SMS flow works |

**Total:** 2-4 weeks (mostly waiting)

---

## Prerequisites

### 1. Terraform Deployment Complete

Ensure Phase 2 infrastructure is deployed:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/terraform/sms

# Check if resources exist
terraform show | grep "aws_pinpointsmsvoicev2_phone_number"
terraform show | grep "aws_sns_topic"
```

**Expected output:**
```
resource "aws_pinpointsmsvoicev2_phone_number" "main" {
    ...
}
```

### 2. AWS Console Access

Ensure you have access to:
- [AWS End User Messaging Console](https://console.aws.amazon.com/sms-voice/home?region=us-east-1)
- Permissions: `sms-voice:*` or specific permissions

### 3. SNS Topic ARN

Get your SNS topic ARN:
```bash
cd infrastructure/terraform/sms
terraform output sns_inbound_topic_arn
```

**Example output:**
```
arn:aws:sns:us-east-1:618048437522:scheduling-agent-sms-inbound-dev
```

**Save this ARN** - you'll need it in Step 3.

---

## Step 1: Request Phone Number

### Option A: Terraform Already Created It ✅

If you've already run `terraform apply`, the phone number resource is created but may be in "pending" status.

**Check status:**
```bash
aws pinpoint-sms-voice-v2 describe-phone-numbers \
  --region us-east-1 \
  --query 'PhoneNumbers[*].[PhoneNumber,Status,CreatedTimestamp]' \
  --output table
```

**Expected output:**
```
----------------------------------------
|      DescribePhoneNumbers           |
+------------------+-------------------+
|  +18005551234    |  PENDING          |
|  2025-10-13      |                   |
+------------------+-------------------+
```

**If status is `PENDING`:** Skip to [Step 2: Monitor Provisioning Status](#step-2-monitor-provisioning-status)

**If no phone number exists:** Continue to Option B below.

### Option B: Manual Request via AWS Console

If phone number wasn't created by Terraform, request it manually:

1. **Navigate to AWS End User Messaging Console**
   ```
   https://console.aws.amazon.com/sms-voice/home?region=us-east-1#/phone-numbers
   ```

2. **Click "Request phone number"**

   Location: Top-right corner of Phone numbers page

3. **Select number type**

   | Setting | Value | Why |
   |---------|-------|-----|
   | **Country** | United States | Primary market |
   | **Number type** | Toll-free | ✅ Recommended - no per-minute charges |
   | **Capabilities** | SMS, MMS, Voice | Enable all for flexibility |
   | **Message type** | Transactional | For appointment notifications |

   **Alternative:** Long code (10-digit) if toll-free unavailable
   - Pros: Faster provisioning (days vs weeks)
   - Cons: Limited throughput (1 MPS vs 3 MPS)

4. **Review registration requirements**

   You may need to submit:
   - **Company name:** Your business name
   - **Business address:** Physical address
   - **Use case description:** "Customer appointment scheduling and notifications"
   - **Sample messages:**
     - "Your appointment is confirmed for tomorrow at 2pm"
     - "Reminder: Your appointment is in 1 hour"

   **Note:** Requirements vary by account age and history.

5. **Confirm and submit**

   - Review monthly costs: ~$2-5/month for toll-free
   - Click **"Request phone number"**

6. **Save confirmation**

   You'll see:
   ```
   Phone number request submitted
   Phone number: +1-800-XXX-XXXX
   Status: Pending
   ```

   **Copy this phone number** - you'll need it for configuration.

---

## Step 2: Monitor Provisioning Status

### What Happens During Provisioning?

| Day | Status | Action |
|-----|--------|--------|
| **Day 0** | Request submitted | AWS reviews your account |
| **Day 1-3** | Under review | AWS validates use case and compliance |
| **Day 4-7** | Approved | Carrier begins provisioning |
| **Day 8-28** | Provisioning | Carrier assigns toll-free number |
| **Day 14-28** | Active | Number ready for use |

### Check Status via AWS Console

1. **Navigate to Phone numbers**
   ```
   https://console.aws.amazon.com/sms-voice/home?region=us-east-1#/phone-numbers
   ```

2. **View status**

   | Status | Meaning | Action |
   |--------|---------|--------|
   | **Pending** | Initial state | Wait - no action needed |
   | **Verifying** | AWS reviewing | Wait - checking compliance |
   | **Provisioning** | Carrier assigning | Wait - number being set up |
   | **Active** | Ready to use | ✅ Proceed to Step 3 |
   | **Failed** | Request rejected | Contact AWS Support |

3. **Status will show:**
   ```
   Phone Number      Status        Created
   +18005551234      PROVISIONING  2025-10-13
   ```

### Check Status via CLI

```bash
# Check current status
aws pinpoint-sms-voice-v2 describe-phone-numbers \
  --region us-east-1 \
  --query 'PhoneNumbers[*].[PhoneNumber,Status,CreatedTimestamp]' \
  --output table

# Set up monitoring (optional)
watch -n 3600 'aws pinpoint-sms-voice-v2 describe-phone-numbers --region us-east-1 --query "PhoneNumbers[*].[PhoneNumber,Status]" --output table'
```

**This command checks status every hour.**

### Email Notifications

AWS will email you when:
- ✅ Request approved
- ✅ Number provisioned and active
- ❌ Request rejected (rare)

**Check your registered AWS account email** (including spam folder).

### What to Do While Waiting

You can continue development without the phone number:

#### 1. Test Lambda with Mock Events

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock

# Create test event
cat > /tmp/test-sms-event.json <<'EOF'
{
  "Records": [{
    "Sns": {
      "Message": "{\"originationNumber\":\"+14255551234\",\"destinationNumber\":\"+18005551234\",\"messageBody\":\"Hello\",\"inboundMessageId\":\"test-123\"}"
    }
  }]
}
EOF

# Test Lambda
aws lambda invoke \
  --function-name scheduling-agent-sms-inbound-dev \
  --payload file:///tmp/test-sms-event.json \
  --region us-east-1 \
  /tmp/response.json

# View response
cat /tmp/response.json
```

#### 2. Add Verified Numbers for Testing

Once phone is provisioned, you'll need verified numbers for testing:

```bash
# Add your personal number for testing
aws pinpoint-sms-voice-v2 create-verified-destination-number \
  --destination-phone-number +1YOUR_PHONE_NUMBER \
  --region us-east-1
```

**You'll receive a verification code via SMS.**

```bash
# Verify with code
aws pinpoint-sms-voice-v2 verify-destination-number \
  --verified-destination-number-id <id-from-previous-command> \
  --verification-code 123456 \
  --region us-east-1
```

#### 3. Set Up Monitoring

While waiting, configure CloudWatch dashboards:

```bash
# Create dashboard (do this now)
aws cloudwatch put-dashboard \
  --dashboard-name SchedulingAgentSMS \
  --dashboard-body file://cloudwatch-dashboard.json \
  --region us-east-1
```

#### 4. Test Other Components

- ✅ Test Bedrock Agent responses (Phase 1)
- ✅ Test DynamoDB consent table writes
- ✅ Test Lambda error handling
- ✅ Review CloudWatch logs structure

#### 5. Document Your Phone Number

Prepare documentation for when number is provisioned:
- Customer communication templates
- Support team training materials
- Phone number usage policies

---

## Step 3: Configure Two-Way Messaging

⚠️ **IMPORTANT:** Only do this step after phone number status is **ACTIVE**.

### Why Manual Configuration?

Terraform/CloudFormation don't yet support configuring two-way messaging for phone numbers. This must be done via AWS Console.

### Configuration Steps

#### 3.1: Open AWS Console

1. Navigate to:
   ```
   https://console.aws.amazon.com/sms-voice/home?region=us-east-1#/phone-numbers
   ```

2. You should see your phone number with status **ACTIVE**:
   ```
   Phone Number      Status    Capabilities
   +18005551234      ACTIVE    SMS, MMS, Voice
   ```

#### 3.2: Access Phone Number Settings

1. **Click on your phone number** (e.g., +18005551234)

2. You'll see the phone number details page with tabs:
   ```
   [General] [Two-way messaging] [Opt-out lists] [Event destinations]
   ```

#### 3.3: Configure Two-Way Messaging

1. **Click the "Two-way messaging" tab**

2. You'll see:
   ```
   Two-way messaging: Disabled

   [Enable two-way messaging button]
   ```

3. **Click "Enable two-way messaging"**

4. **Configure settings:**

   | Setting | Value | Notes |
   |---------|-------|-------|
   | **Status** | Enabled | Toggle to ON |
   | **Destination type** | SNS Topic | ✅ Select this |
   | **SNS Topic ARN** | `arn:aws:sns:us-east-1:618048437522:scheduling-agent-sms-inbound-dev` | Get from Terraform output |
   | **Keyword filter** | None (blank) | Route ALL messages to Lambda |
   | **Self-managed opt-outs** | Disabled | We handle opt-outs in Lambda |

   **Screenshot description:**
   ```
   ┌─────────────────────────────────────────────┐
   │ Two-way messaging configuration             │
   ├─────────────────────────────────────────────┤
   │ Status: [●] Enabled  [ ] Disabled           │
   │                                              │
   │ Destination type:                           │
   │   (●) SNS Topic                             │
   │   ( ) Amazon Lex bot                        │
   │                                              │
   │ SNS Topic ARN: *                            │
   │ ┌──────────────────────────────────────────┐│
   │ │arn:aws:sns:us-east-1:618048437522:...   ││
   │ └──────────────────────────────────────────┘│
   │                                              │
   │ Keyword filter: (optional)                  │
   │ ┌──────────────────────────────────────────┐│
   │ │                                          ││
   │ └──────────────────────────────────────────┘│
   │                                              │
   │ Self-managed opt-outs:                      │
   │   [ ] Enable                                │
   │                                              │
   │         [Cancel]  [Save changes]            │
   └─────────────────────────────────────────────┘
   ```

5. **Get SNS Topic ARN** (if you don't have it):
   ```bash
   cd infrastructure/terraform/sms
   terraform output sns_inbound_topic_arn
   ```

   Copy the ARN (looks like):
   ```
   arn:aws:sns:us-east-1:618048437522:scheduling-agent-sms-inbound-dev
   ```

6. **Paste ARN** into "SNS Topic ARN" field

7. **Leave "Keyword filter" blank**
   - This ensures ALL inbound messages are routed to Lambda
   - We'll handle keywords (STOP, START, etc.) in Lambda code

8. **Keep "Self-managed opt-outs" DISABLED**
   - We have custom TCPA compliance logic in Lambda
   - AWS auto-opt-out would conflict with our 10-day processing

9. **Click "Save changes"**

#### 3.4: Verify Configuration

1. **Refresh the page**

2. **Verify settings show:**
   ```
   Two-way messaging: Enabled
   Destination: SNS Topic (arn:aws:sns:us-east-1:...)
   Keyword filter: None
   Self-managed opt-outs: Disabled
   ```

3. **Check SNS Topic subscription:**
   ```bash
   aws sns list-subscriptions-by-topic \
     --topic-arn arn:aws:sns:us-east-1:618048437522:scheduling-agent-sms-inbound-dev \
     --region us-east-1
   ```

   **Expected output:**
   ```json
   {
     "Subscriptions": [
       {
         "SubscriptionArn": "arn:aws:sns:...:subscription/...",
         "Protocol": "lambda",
         "Endpoint": "arn:aws:lambda:us-east-1:...:function:scheduling-agent-sms-inbound-dev"
       }
     ]
   }
   ```

   ✅ **Confirms Lambda is subscribed to SNS topic**

---

## Step 4: Testing

### 4.1: Test with Verified Number

**Prerequisites:**
- Phone number is ACTIVE
- Two-way messaging configured
- Your personal number added to verified list

**Test flow:**

1. **Send test SMS from your phone:**
   ```
   To: +1-800-XXX-XXXX (your toll-free number)
   Message: Hello
   ```

2. **Check CloudWatch logs:**
   ```bash
   aws logs tail /aws/lambda/scheduling-agent-sms-inbound-dev \
     --follow \
     --region us-east-1
   ```

   **Expected log output:**
   ```
   Processing SMS from +1YOUR_NUMBER: Hello
   Invoking Bedrock Agent 5VTIWONUMO
   Agent response: Hello! I'm here to help you schedule appointments...
   Sending SMS to +1YOUR_NUMBER
   SMS sent successfully: msg-12345
   ```

3. **Verify reply received on your phone:**
   ```
   From: +1-800-XXX-XXXX
   Message: Hello! I'm here to help you schedule appointments with our property management team. What would you like to do today?
   ```

   ✅ **Success! Two-way SMS is working**

### 4.2: Test All Agent Routes

Test each agent type:

| Test | Message | Expected Route | Expected Response |
|------|---------|----------------|-------------------|
| **Chitchat** | "Hello" | chitchat_collaborator | Greeting |
| **Scheduling** | "Schedule appointment" | scheduling_collaborator | Ask for project |
| **Information** | "What are your hours?" | information_collaborator | Business hours |
| **Notes** | "Add note: prefer mornings" | notes_collaborator | Ask for appointment ID |
| **Opt-out** | "STOP" | Opt-out handler | Confirmation message |

### 4.3: Test Opt-Out Flow

1. **Send opt-out:**
   ```
   To: +1-800-XXX-XXXX
   Message: STOP
   ```

2. **Expected reply:**
   ```
   You have been unsubscribed from SMS messages. Your request will be processed within 10 business days. Reply START to resubscribe.
   ```

3. **Verify DynamoDB consent table:**
   ```bash
   aws dynamodb get-item \
     --table-name scheduling-agent-sms-consent-dev \
     --key '{"phone_number": {"S": "+1YOUR_NUMBER"}}' \
     --region us-east-1
   ```

   **Expected:**
   ```json
   {
     "Item": {
       "phone_number": {"S": "+1YOUR_NUMBER"},
       "consent_status": {"S": "opted_out"},
       "opt_out_method": {"S": "sms"},
       "opt_out_requested_at": {"S": "2025-10-13T20:15:30Z"},
       "opt_out_deadline": {"S": "2025-10-27T20:15:30Z"}
     }
   }
   ```

4. **Test that messages are blocked:**
   ```
   Try sending another message - it should not trigger Lambda
   ```

5. **Test opt-in:**
   ```
   To: +1-800-XXX-XXXX
   Message: START
   ```

   **Expected reply:**
   ```
   You have been resubscribed to SMS messages. Welcome back!
   ```

---

## Troubleshooting

### Issue 1: Phone Number Stuck in "Pending" for > 4 Weeks

**Symptoms:**
- Status shows "Pending" or "Provisioning"
- No email from AWS
- Been waiting > 4 weeks

**Solutions:**

1. **Check AWS Health Dashboard:**
   ```
   https://health.aws.amazon.com/health/home
   ```
   Look for SMS service issues

2. **Contact AWS Support:**
   ```
   AWS Console → Support → Create case
   Type: Technical
   Service: End User Messaging SMS
   Category: Phone number provisioning
   Severity: General guidance

   Description:
   "Phone number +18005551234 has been in 'Pending' status for X weeks.
   Request submitted on: 2025-10-13
   Account ID: 618048437522
   Region: us-east-1

   Please advise on expected provisioning timeline."
   ```

3. **Try requesting a different number type:**
   - If toll-free is delayed, try 10DLC (faster)
   - 10DLC: 3-7 days provisioning
   - Toll-free: 2-4 weeks (can be longer)

### Issue 2: Two-Way Messaging Config Not Saving

**Symptoms:**
- Click "Save changes"
- Returns to Disabled state
- No error message shown

**Solutions:**

1. **Verify SNS Topic permissions:**
   ```bash
   aws sns get-topic-attributes \
     --topic-arn arn:aws:sns:us-east-1:618048437522:scheduling-agent-sms-inbound-dev \
     --region us-east-1
   ```

   Check for policy allowing `sms-voice.amazonaws.com` to publish

2. **Verify topic exists:**
   ```bash
   aws sns list-topics --region us-east-1 | grep sms-inbound
   ```

3. **Check browser console for errors:**
   - Open browser DevTools (F12)
   - Look for API errors
   - May show permission issues

4. **Try different browser:**
   - Chrome/Firefox sometimes have different behavior
   - Clear cache and try again

### Issue 3: Inbound Messages Not Triggering Lambda

**Symptoms:**
- Send SMS to phone number
- No Lambda invocation in CloudWatch
- No error, just silence

**Debug steps:**

1. **Verify SNS subscription:**
   ```bash
   aws sns list-subscriptions-by-topic \
     --topic-arn arn:aws:sns:us-east-1:618048437522:scheduling-agent-sms-inbound-dev \
     --region us-east-1
   ```

   Should show Lambda subscription

2. **Check SNS topic metrics:**
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/SNS \
     --metric-name NumberOfMessagesPublished \
     --dimensions Name=TopicName,Value=scheduling-agent-sms-inbound-dev \
     --start-time 2025-10-13T00:00:00Z \
     --end-time 2025-10-13T23:59:59Z \
     --period 3600 \
     --statistics Sum \
     --region us-east-1
   ```

   If Sum = 0, SNS isn't receiving messages

3. **Verify phone number → SNS association:**
   ```bash
   aws pinpoint-sms-voice-v2 describe-phone-numbers \
     --region us-east-1 \
     --query 'PhoneNumbers[*].[PhoneNumber,TwoWayEnabled,TwoWayChannelArn]'
   ```

   Should show: `["+18005551234", true, "arn:aws:sns:..."]`

4. **Test SNS → Lambda manually:**
   ```bash
   aws sns publish \
     --topic-arn arn:aws:sns:us-east-1:618048437522:scheduling-agent-sms-inbound-dev \
     --message '{"originationNumber":"+14255551234","destinationNumber":"+18005551234","messageBody":"Test","inboundMessageId":"test-123"}' \
     --region us-east-1
   ```

   Check if Lambda is invoked

### Issue 4: Reply Not Sending

**Symptoms:**
- Lambda invocation succeeds
- CloudWatch shows "SMS sent successfully"
- But no reply received on phone

**Debug steps:**

1. **Check SMS delivery logs:**
   ```bash
   aws logs tail /aws/sms/scheduling-agent/dev --follow --region us-east-1
   ```

   Look for delivery events

2. **Check destination number not on opt-out list:**
   ```bash
   aws dynamodb get-item \
     --table-name scheduling-agent-sms-consent-dev \
     --key '{"phone_number": {"S": "+1YOUR_NUMBER"}}' \
     --region us-east-1
   ```

3. **Test SendTextMessage directly:**
   ```bash
   aws pinpoint-sms-voice-v2 send-text-message \
     --destination-phone-number +1YOUR_NUMBER \
     --origination-identity +18005551234 \
     --message-body "Test from AWS CLI" \
     --region us-east-1
   ```

4. **Check phone number capabilities:**
   ```bash
   aws pinpoint-sms-voice-v2 describe-phone-numbers \
     --region us-east-1 \
     --query 'PhoneNumbers[*].[PhoneNumber,Status,MessageType]'
   ```

   Should show: `["ACTIVE", "TRANSACTIONAL"]`

---

## FAQ

### Q1: How long does phone number provisioning take?

**A:** Typically 2-4 weeks for toll-free numbers. Can vary by:
- Account age (new accounts may be slower)
- Use case (some require additional review)
- Carrier availability

**Faster alternatives:**
- 10DLC (long code): 3-7 days
- Short code: 8-12 weeks (expensive, high throughput)

### Q2: Can I use my existing phone number?

**A:** Yes! If you have an existing number with another provider (Twilio, etc.), you can port it to AWS:

```bash
aws pinpoint-sms-voice-v2 request-phone-number \
  --phone-number-type LONG_CODE \
  --existing-phone-number +18005551234 \
  --region us-east-1
```

**Note:** Porting takes 7-10 days and requires proof of ownership.

### Q3: What if I need the system to work NOW?

**Options:**

1. **Use Twilio temporarily** (can switch to AWS later)
2. **Request 10DLC instead** (3-7 days vs 2-4 weeks)
3. **Use AWS SNS for one-way SMS** (outbound only, no replies)

### Q4: Can I have multiple phone numbers?

**A:** Yes! Terraform supports multiple phone numbers:

```hcl
# Add to main.tf
resource "aws_pinpointsmsvoicev2_phone_number" "backup" {
  iso_country_code = "US"
  message_type    = "TRANSACTIONAL"
  number_type     = "TOLL_FREE"
  ...
}
```

**Use cases:**
- Different numbers per region
- Separate dev/staging/prod numbers
- Backup number for failover

### Q5: How do I change the SNS topic after configuration?

**A:** Repeat Step 3:
1. Go to phone number settings
2. Click "Two-way messaging" tab
3. Update SNS Topic ARN
4. Click "Save changes"

**Note:** Changes take effect immediately.

### Q6: What happens during provisioning? Can I cancel?

**A:** During provisioning:
- Your account is NOT charged yet
- Number is reserved but not active
- You can cancel anytime before activation

**To cancel:**
```bash
aws pinpoint-sms-voice-v2 release-phone-number \
  --phone-number-id <phone-number-id> \
  --region us-east-1
```

### Q7: Can I test with a sandbox number?

**A:** Yes! AWS provides sandbox mode:

1. Enable sandbox in AWS Console:
   ```
   End User Messaging → Settings → Sandbox mode
   ```

2. Add verified numbers (up to 10):
   ```bash
   aws pinpoint-sms-voice-v2 create-verified-destination-number \
     --destination-phone-number +1YOUR_NUMBER \
     --region us-east-1
   ```

3. Test full flow with verified numbers
4. Move to production when phone provisioned

---

## Next Steps After Configuration

Once two-way messaging is configured and tested:

1. **✅ Update documentation** with final phone number
2. **✅ Train support team** on SMS interactions
3. **✅ Set up monitoring** (CloudWatch alarms)
4. **✅ Document customer-facing** phone number
5. **✅ Test error scenarios** (invalid messages, long messages)
6. **✅ Load test** (if expecting high volume)
7. **✅ Plan Phase 3** (frontend integration)

---

## Additional Resources

### AWS Documentation
- [End User Messaging SMS](https://docs.aws.amazon.com/sms-voice/)
- [Phone number types](https://docs.aws.amazon.com/sms-voice/latest/userguide/phone-numbers.html)
- [Two-way messaging](https://docs.aws.amazon.com/sms-voice/latest/userguide/two-way-sms.html)

### Internal Documentation
- [PHASE2_DEPLOYMENT_GUIDE.md](./PHASE2_DEPLOYMENT_GUIDE.md)
- [PHASE2_IMPLEMENTATION_SUMMARY.md](./PHASE2_IMPLEMENTATION_SUMMARY.md)
- [PHASE2_AWS_SMS_RESEARCH.md](./PHASE2_AWS_SMS_RESEARCH.md)

### Support
- **AWS Support:** Create case in AWS Console
- **Phone provisioning issues:** Priority: Normal, Category: Phone number provisioning
- **Technical issues:** Priority: High if production, Normal if dev

---

**Last Updated:** October 13, 2025
**Status:** Ready for use
**Version:** 1.0.0
