# Using Existing pf-voice-dev Instance - Setup Guide

**Date:** November 9, 2025
**Existing Instance:** `pf-voice-dev`
**Instance ID:** `0bfaecaa-0c5e-470f-803d-ccc0300c9353`
**Phone Number:** +1-833-877-1422
**Account:** 772634497954

---

## Current Situation

You have **TWO** AWS Connect instances:

### 1. **pf-voice-dev** (Manually Created) ✅
- **Instance ID:** `0bfaecaa-0c5e-470f-803d-ccc0300c9353`
- **Status:** ACTIVE
- **Access URL:** https://pf-voice-dev.my.connect.aws
- **Phone:** +1-833-877-1422 (already claimed)
- **Created:** 2025-11-09 17:22:53
- **This is the one we want to use!**

### 2. **pf-scheduling-assistant** (Accidentally Created by Terraform) ❌
- **Instance ID:** `b8f4f3cf-c4bf-4b2a-943b-8e6b08a4e705`
- **Status:** ACTIVE (partially configured)
- **Access URL:** https://pf-scheduling-assistant.my.connect.aws
- **Phone:** None
- **Created:** 2025-11-09 18:58:07
- **This needs to be deleted!**

---

## Existing Resources Found

### Lex Bot ✅
- **Bot Name:** `pf-scheduling-assistant-dev`
- **Bot ID:** `6MCLBY66OV`
- **Status:** Available
- **Last Updated:** 2025-11-09 18:57:41

### Lambda Functions ✅
- **pf-scheduling-actions** - Exists (from core deployment)
- **pf-scheduler-agent-ms** - Exists

### Phone Number ✅
- **Number:** +1-833-877-1422
- **Type:** TOLL_FREE
- **Country:** US
- **Status:** Claimed (likely attached to pf-voice-dev)

---

## Terraform Errors Fixed

### 1. ✅ Lambda AWS_REGION Environment Variable
**Error:**
```
InvalidParameterValueException: Lambda was unable to configure your environment variables
because the environment variables you have provided contains reserved keys: AWS_REGION
```

**Fix:** Removed `AWS_REGION` from both Lambda functions:
- `pf-lex-fulfillment-dev` (lambda_functions.tf:26)
- `pf-voice-bedrock-bridge-dev` (lambda_functions.tf:129)

**Why:** AWS Lambda automatically provides `AWS_REGION` as a built-in environment variable. You cannot override it.

---

### 2. ✅ Contact Trace Records Storage
**Error:**
```
InvalidRequestException: Storage Type Not Supported
aws_connect_instance_storage_config.contact_trace_records
```

**Fix:** Commented out the `contact_trace_records` storage config (aws_connect.tf:118-136)

**Why:** CONTACT_TRACE_RECORDS storage type is not supported in all AWS regions or may require specific Connect instance configuration.

---

### 3. ✅ FallbackIntent Already Exists
**Error:**
```
ValidationException: Intent with name FallbackIntent already exists. Use another name.
```

**Fix:** Removed the custom FallbackIntent resource (lex_bot.tf:183-197)

**Why:** `FallbackIntent` is a built-in intent in Amazon Lex. AWS automatically creates `AMAZON.FallbackIntent` for every bot, and you cannot create a custom intent with the same name.

---

## Steps to Fix Everything

### Option A: Clean Slate (Recommended)

This will delete the duplicate instance and start fresh with pf-voice-dev:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock

# Step 1: Delete the accidentally created instance
aws connect delete-instance \
  --instance-id b8f4f3cf-c4bf-4b2a-943b-8e6b08a4e705 \
  --region us-east-1

# Step 2: Destroy existing Terraform state
cd infrastructure/terraform/voice
terraform destroy -auto-approve

# Step 3: Clean up Terraform state files
rm -f terraform.tfstate*
rm -f .terraform.lock.hcl
rm -rf .terraform

# Step 4: Redeploy with corrected configuration
cd ../../../scripts
./DEPLOY_VOICE_FULL.sh
```

**Result:** Fresh deployment using `pf-voice-dev` instance name

---

### Option B: Import Existing Instance (Advanced)

This imports your existing `pf-voice-dev` instance into Terraform:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/terraform/voice

# Import the existing Connect instance
terraform import aws_connect_instance.main 0bfaecaa-0c5e-470f-803d-ccc0300c9353

# Import existing S3 bucket (if it exists)
terraform import aws_s3_bucket.call_recordings pf-call-recordings-dev-772634497954

# Import existing DynamoDB table (if it exists)
terraform import aws_dynamodb_table.session_data pf-session-data-dev

# Verify state
terraform plan
```

**Result:** Terraform manages your existing resources

---

## What's Been Updated

### 1. **DEPLOY_VOICE_FULL.sh**
Changed:
```bash
# OLD:
connect_instance_alias = "scheduling-assistant"

# NEW:
connect_instance_alias = "voice-dev"
```

Now creates instance named `pf-voice-dev` instead of `pf-scheduling-assistant`.

### 2. **lambda_functions.tf**
Removed `AWS_REGION` from environment variables in both Lambda functions.

### 3. **aws_connect.tf**
Commented out unsupported `contact_trace_records` storage config.

### 4. **lex_bot.tf**
Removed custom `FallbackIntent` resource (uses built-in Amazon.FallbackIntent instead).

---

## Recommended Next Steps

### 1. Clean Up Duplicate Instance

```bash
# Delete the accidentally created instance
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock

aws connect delete-instance \
  --instance-id b8f4f3cf-c4bf-4b2a-943b-8e6b08a4e705 \
  --region us-east-1
```

### 2. Clean Up Lex Bot (if needed)

If the Lex bot was partially created with errors:

```bash
# Delete the bot
aws lexv2-models delete-bot \
  --bot-id 6MCLBY66OV \
  --region us-east-1

# Wait for deletion (takes ~1 minute)
aws lexv2-models list-bots --region us-east-1
```

### 3. Destroy Current Terraform State

```bash
cd infrastructure/terraform/voice
terraform destroy -auto-approve
```

### 4. Redeploy Clean

```bash
cd ../../../scripts
./DEPLOY_VOICE_FULL.sh
```

---

## Configuration Summary

### Terraform will create:

**Connect Instance:**
- Name: `pf-voice-dev`
- Inbound calls: Enabled
- Outbound calls: Disabled
- Phone: +1-833-877-1422

**Lex Bot:**
- Name: `pf-scheduling-assistant-dev`
- Voice: Joanna (Neural)
- Intents:
  - Welcome
  - ProjectInquiry
  - ScheduleAppointment
  - UrgentRequest
  - AMAZON.FallbackIntent (built-in)

**Lambda Functions:**
- `pf-lex-fulfillment-dev` - Routes intents
- `pf-voice-bedrock-bridge-dev` - Bridges to Bedrock Supervisor

**Storage:**
- S3: `pf-call-recordings-dev-772634497954`
- DynamoDB: `pf-session-data-dev`

**Security:**
- KMS key for call recording encryption
- IAM roles for Lambda, Lex, and Connect

---

## Phone Number Configuration

Your phone number +1-833-877-1422 is already claimed. Terraform needs to:

1. **Either:** Claim it fresh (if not attached to any instance)
2. **Or:** Import it if already attached to `pf-voice-dev`

Check current attachment:

```bash
aws connect list-phone-numbers-v2 \
  --target-arn "arn:aws:connect:us-east-1:772634497954:instance/0bfaecaa-0c5e-470f-803d-ccc0300c9353" \
  --region us-east-1
```

If attached to `pf-voice-dev`, you may need to:
- Release it first
- Let Terraform claim it
- Or import it into Terraform state

---

## Testing After Deployment

```bash
# Call the phone number
# 📞 +1-833-877-1422

# Expected: Hear greeting and be connected to Lex bot

# Monitor logs
aws logs tail /aws/lambda/pf-lex-fulfillment-dev --follow --region us-east-1
aws logs tail /aws/lambda/pf-voice-bedrock-bridge-dev --follow --region us-east-1

# Check Connect metrics
# https://pf-voice-dev.my.connect.aws
```

---

## Troubleshooting

### Issue: Phone number already claimed

```bash
# Release from old instance
aws connect release-phone-number \
  --phone-number-id <PHONE_NUMBER_ID> \
  --region us-east-1

# Then redeploy
./DEPLOY_VOICE_FULL.sh
```

### Issue: Lex bot conflicts

```bash
# Delete existing bot
aws lexv2-models delete-bot \
  --bot-id 6MCLBY66OV \
  --skip-resource-in-use-check \
  --region us-east-1
```

### Issue: Lambda deployment package missing

```bash
# Repackage Lambda functions
cd lambda/lex-fulfillment
pip3 install -r requirements.txt -t package/
cd package && zip -r ../deployment.zip . && cd ..
zip -g deployment.zip handler.py

cd ../voice-bedrock-bridge
pip3 install -r requirements.txt -t package/
cd package && zip -r ../deployment.zip . && cd ..
zip -g deployment.zip handler.py
```

---

## Related Documentation

- [Full Deployment Guide](./VOICE_FULL_DEPLOYMENT_GUIDE.md)
- [Terraform Fixes Summary](./TERRAFORM_FIXES_SUMMARY.md)
- [Deployment Scripts Reference](./DEPLOYMENT_SCRIPTS_REFERENCE.md)
