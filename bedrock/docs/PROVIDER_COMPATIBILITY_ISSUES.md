# AWS Provider Compatibility Issues - Resolution

**Date:** November 9, 2025
**Terraform Version:** v1.5.7
**Issue:** AWS provider version incompatibility with Terraform and Lex V2 resources

---

## Problem Summary

We encountered multiple AWS provider compatibility issues:

1. **AWS Provider v5.100.0** - Latest version incompatible with Terraform v1.5.7
   - Error: "Unrecognized remote plugin message"
   - Cause: Provider binary protocol mismatch

2. **AWS Provider v5.60.0** - Lex syntax incompatible
   - Error: Unsupported `sample_value` blocks in `slot_type_values`
   - Error: Unsupported `tags` on `aws_connect_instance`

3. **AWS Provider v5.50.0** - Different Lex syntax
   - Error: Unsupported `sample_value` blocks (same issue)

4. **AWS Provider v5.31.0** - Too old
   - Error: `aws_lexv2models_*` resources don't exist

---

## Root Cause

The AWS Terraform provider's Lex V2 resources have undergone significant API changes between versions:
- v5.31 and earlier: No Lex V2 support
- v5.40-v5.60: Lex V2 added but syntax keeps changing
- v5.70+: Different slot_type_values structure
- v5.100: Binary protocol incompatible with Terraform v1.5.7

---

## Errors Fixed So Far

### ✅ 1. Lambda AWS_REGION Environment Variable
**Files:** `infrastructure/terraform/voice/lambda_functions.tf`
**Fix:** Removed `AWS_REGION` from both Lambda functions (lines 26, 129)
**Reason:** AWS Lambda automatically provides this as a built-in variable

### ✅ 2. Contact Trace Records Storage
**File:** `infrastructure/terraform/voice/aws_connect.tf:118-136`
**Fix:** Commented out `contact_trace_records` storage config
**Reason:** Storage type not supported in all regions

### ✅ 3. FallbackIntent Conflict
**File:** `infrastructure/terraform/voice/lex_bot.tf:183-197`
**Fix:** Removed custom FallbackIntent resource
**Reason:** Built-in intent, cannot be created

### ✅ 4. Instance Name
**File:** `scripts/DEPLOY_VOICE_FULL.sh:160`
**Fix:** Changed `scheduling-assistant` to `voice-dev`
**Reason:** Match existing manually-created instance

---

## Recommended Solution

Given the complexity of Lex V2 Terraform resources and constant API changes, I recommend a **hybrid approach**:

### Option A: Minimal Terraform + Manual Lex Configuration ⭐ RECOMMENDED

**What Terraform Manages:**
- ✅ AWS Connect instance (`pf-voice-dev`)
- ✅ Lambda functions (lex-fulfillment, voice-bridge)
- ✅ S3 bucket for call recordings
- ✅ DynamoDB table for sessions
- ✅ IAM roles and permissions
- ✅ KMS keys

**What You Configure Manually (AWS Console):**
- Lex bot (already exists: `pf-scheduling-assistant-dev`)
- Lex intents (Welcome, ProjectInquiry, ScheduleAppointment, etc.)
- Lex slot types (ProjectID, ProjectCategory)
- Connect contact flows

**Advantages:**
- ✅ Avoids Terraform provider compatibility issues
- ✅ Faster deployment (5-10 min vs 30-60 min debugging)
- ✅ More flexibility for Lex bot iteration
- ✅ Terraform manages infrastructure, not configuration

**Implementation:**
```bash
# 1. Comment out Lex resources in lex_bot.tf
# 2. Deploy infrastructure only
./DEPLOY_VOICE_FULL.sh

# 3. Configure Lex bot via AWS Console
# https://console.aws.amazon.com/lexv2/home?region=us-east-1

# 4. Connect Lex to Lambda via Console
# 5. Test phone number
```

---

### Option B: Upgrade Terraform (Advanced)

**Current:** Terraform v1.5.7
**Upgrade to:** Terraform v1.9+ or v1.10+

This would allow using AWS provider v5.100+ which may have more stable Lex V2 resources.

**Steps:**
```bash
# Install latest Terraform
brew upgrade terraform

# Or download from terraform.io
# Then reinitialize
terraform init -upgrade
```

**Risks:**
- May require syntax updates in other Terraform files
- Lex V2 resources still unstable even in latest provider
- Time investment: 1-2 hours

---

### Option C: Skip Lex Terraform Entirely

Remove all Lex resources from Terraform and manage entirely through:
1. AWS Console (manual configuration)
2. AWS CLI scripts (automated but not Terraform)
3. CloudFormation (if you prefer IaC)

---

## Current State

**Terraform Configuration:**
- Provider pinned to v5.50.0
- Connect instance: Fixed (tags removed)
- Lambda functions: Fixed (AWS_REGION removed)
- Lex resources: Still broken (slot_type_values syntax)

**AWS Resources (Existing):**
- Connect instance: `pf-voice-dev` (ID: 0bfaecaa-0c5e-470f-803d-ccc0300c9353)
- Lex bot: `pf-scheduling-assistant-dev` (ID: 6MCLBY66OV)
- Phone: +1-833-877-1422 (claimed)

---

## Next Steps - Recommended Approach

### 1. Simplify Terraform Configuration

Comment out all Lex resources and focus on infrastructure:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/terraform/voice

# Edit lex_bot.tf - comment out lines 1-300 (all Lex resources)
# Keep only outputs if needed
```

### 2. Deploy Infrastructure Only

```bash
cd ../../../scripts
./DEPLOY_VOICE_FULL.sh
```

This will deploy:
- Lambda functions
- S3 bucket
- DynamoDB table
- IAM roles
- (Skip Connect if using existing pf-voice-dev)

### 3. Configure Lex Bot Manually

**AWS Console Steps:**
1. Go to Amazon Lex: https://console.aws.amazon.com/lexv2/home?region=us-east-1
2. Open bot: `pf-scheduling-assistant-dev`
3. Create intents:
   - Welcome
   - ProjectInquiry
   - ScheduleAppointment
   - UrgentRequest
4. Configure Lambda fulfillment:
   - Point to: `pf-lex-fulfillment-dev`
5. Build bot
6. Test in Lex console

### 4. Connect to AWS Connect

**Connect Console Steps:**
1. Go to AWS Connect: https://pf-voice-dev.my.connect.aws
2. Routing → Contact flows → Create
3. Add "Get customer input" block
4. Select Lex bot: `pf-scheduling-assistant-dev`
5. Assign to phone number: +1-833-877-1422
6. Publish

### 5. Test End-to-End

```bash
# Call the number
📞 +1-833-877-1422

# Monitor logs
aws logs tail /aws/lambda/pf-lex-fulfillment-dev --follow --region us-east-1
```

---

## Long-Term Recommendation

For production deployments:

1. **Infrastructure** → Terraform
   - Connect instance
   - Lambda functions
   - Storage (S3, DynamoDB)
   - IAM roles
   - Networking

2. **Configuration** → AWS Console or CLI
   - Lex bots and intents
   - Connect contact flows
   - Phone number routing
   - Quick iterations

3. **State Management** → Version Control
   - Export Lex bot definitions as JSON
   - Store contact flows as JSON in Git
   - Document manual steps in runbooks

This hybrid approach provides:
- ✅ Infrastructure as Code benefits
- ✅ Configuration flexibility
- ✅ Avoids Terraform provider instability
- ✅ Faster development cycle

---

## Files Modified

1. **provider.tf** - Tried v5.100, v5.60, v5.50, v5.31
2. **lambda_functions.tf** - Removed AWS_REGION
3. **aws_connect.tf** - Removed tags, commented out contact_trace_records
4. **lex_bot.tf** - Removed FallbackIntent, attempted various slot syntax fixes
5. **DEPLOY_VOICE_FULL.sh** - Changed instance alias to voice-dev

---

## Conclusion

The AWS Terraform provider's Lex V2 resources are experiencing rapid API changes, making them unstable for production use.

**Recommended Path Forward:**
Use Terraform for infrastructure, AWS Console for Lex/Connect configuration. This provides the best balance of automation, stability, and development speed.
