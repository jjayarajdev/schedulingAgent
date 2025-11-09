# Voice Integration Scripts - Quick Reference

**Date:** November 9, 2025
**Purpose:** Quick reference for AWS Connect voice integration scripts

---

## Available Scripts

All scripts are located in: `/bedrock/scripts/`

| Script | Purpose | Duration |
|--------|---------|----------|
| **DEPLOY_VOICE.sh** | Deploy complete voice infrastructure | 10-15 min |
| **test_voice_integration.sh** | Test all deployed components | 2-3 min |
| **claim_phone_number.sh** | Claim phone number only | 2 min |
| **CLEANUP_VOICE.sh** | Remove all voice resources | 5-10 min |

---

## 1. DEPLOY_VOICE.sh

### Purpose
Complete deployment of AWS Connect voice integration with dynamic agent ID loading.

### What It Does

1. ✅ Loads Bedrock agent IDs from `config/agent_ids.json`
2. ✅ Auto-discovers Supervisor v1 alias ID
3. ✅ Creates/verifies DynamoDB table for sessions
4. ✅ Packages both Lambda functions with dependencies
5. ✅ Generates Terraform variables dynamically
6. ✅ Deploys full infrastructure (Connect, Lex, Lambda, S3, IAM)
7. ✅ Optionally claims phone number
8. ✅ Saves deployment info to `config/voice_deployment.json`

### Usage

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock

# Run deployment
./scripts/DEPLOY_VOICE.sh
```

### Interactive Prompts

The script will ask:

1. **Confirm Terraform plan** (yes/no)
2. **Claim phone number?** (yes/no)
3. If claiming:
   - **Number type:** Toll-Free (1) or DID (2)
   - **Area code** (if DID selected)
   - **Choose number** from available list

### What Gets Created

**AWS Resources:**
- AWS Connect instance: `pf-voice-dev`
- Amazon Lex bot with 5 intents
- 2 Lambda functions:
  - `pf-lex-fulfillment-dev`
  - `pf-voice-bedrock-bridge-dev`
- DynamoDB table: `pf-session-data-dev`
- S3 bucket: `pf-call-recordings-dev-{account-id}`
- IAM roles and policies
- CloudWatch log groups
- KMS encryption keys

**Local Files:**
- `config/voice_deployment.json` - Deployment metadata
- `infrastructure/terraform/voice/terraform.tfvars` - Generated config
- `infrastructure/terraform/voice/terraform.tfstate` - Terraform state
- `lambda/*/deployment.zip` - Lambda packages

### Example Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  AWS Connect Voice Integration Deployment
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Region: us-east-1
Account: 618048437522
Environment: dev

[1/9] Loading Bedrock Agent IDs...
  Supervisor Agent ID: YEMXAMMRVC
  Supervisor v1 Alias ID: XXXXXXXXXX
✅ Agent IDs loaded

[2/9] Checking DynamoDB table...
✅ DynamoDB table exists: pf-session-data-dev

[3/9] Packaging Lambda functions...
  Packaging: lex-fulfillment
    ✅ Packaged: deployment.zip (2.4K)
  Packaging: voice-bedrock-bridge
    ✅ Packaged: deployment.zip (3.1K)
✅ Lambda functions packaged

[4/9] Creating Terraform configuration...
✅ Terraform variables created

[5/9] Initializing Terraform...
✅ Terraform initialized

[6/9] Planning Terraform deployment...
Plan: 23 to add, 0 to change, 0 to destroy.

Do you want to apply this plan? (yes/no): yes

[7/9] Deploying infrastructure...
✅ Infrastructure deployed

[8/9] Retrieving deployment information...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Deployment Outputs:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AWS Connect:
  Instance ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  Console URL: https://pf-voice-dev.my.connect.aws

Amazon Lex:
  Bot ID: XXXXXXXXXX
  Alias ID: XXXXXXXXXX

Lambda Functions:
  Lex Fulfillment: pf-lex-fulfillment-dev
  Voice Bridge: pf-voice-bedrock-bridge-dev

Storage:
  Call Recordings: s3://pf-call-recordings-dev-618048437522

[9/9] Phone Number Setup
Would you like to claim a phone number now? (yes/no): yes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Deployment Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Next Steps After Deployment

The script outputs specific next steps:

1. **Build Lex bot locale**
2. **Test Lambda functions**
3. **Create contact flow** in AWS Console
4. **Associate phone number** with flow
5. **Test by calling** the number

---

## 2. test_voice_integration.sh

### Purpose
Comprehensive testing of all voice integration components.

### What It Tests

| Test # | Component | What It Checks |
|--------|-----------|----------------|
| 1 | Lex Fulfillment - Welcome | Welcome intent handler works |
| 2 | Lex Fulfillment - Fallback | Bedrock handoff working |
| 3 | Voice-Bedrock Bridge | Lambda → Bedrock Supervisor |
| 4 | Bedrock Supervisor | Direct agent invocation |
| 5 | Lex Bot Recognition | Intent recognition (if built) |
| 6 | DynamoDB Sessions | Session data persistence |

### Usage

```bash
# Run all tests
./scripts/test_voice_integration.sh
```

### Example Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Voice Integration Test Suite
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Configuration:
  Lex Fulfillment: pf-lex-fulfillment-dev
  Voice Bridge: pf-voice-bedrock-bridge-dev
  Supervisor Agent: YEMXAMMRVC

Test 1: Lex Fulfillment - Welcome Intent
✅ PASSED: Welcome intent working
   Response: Hello! Welcome to ProjectForce...

Test 2: Lex Fulfillment - Fallback Intent
✅ PASSED: Fallback intent triggers Bedrock bridge
   Response: Let me help you with that...

Test 3: Voice-Bedrock Bridge
✅ PASSED: Bedrock bridge invoked successfully
   Response: You have 3 projects...

Test 4: Bedrock Supervisor Agent
✅ PASSED: Supervisor agent responding
   Response saved to: /tmp/bedrock-output.txt

Test 5: Lex Bot Recognition
⚠️  SKIPPED: Lex bot not built yet

Test 6: DynamoDB Session Storage
✅ PASSED: DynamoDB storing session data

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Test Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Tests: 5
Passed: 5
Failed: 0

✅ All tests passed!
```

### Troubleshooting

If tests fail, check CloudWatch Logs:

```bash
# Lex Fulfillment logs
aws logs tail /aws/lambda/pf-lex-fulfillment-dev --follow --region us-east-1

# Voice Bridge logs
aws logs tail /aws/lambda/pf-voice-bedrock-bridge-dev --follow --region us-east-1
```

---

## 3. claim_phone_number.sh

### Purpose
Standalone script to claim a phone number for existing Connect instance.

### Usage

```bash
# Interactive mode
./scripts/claim_phone_number.sh
```

### Interactive Flow

```
=== AWS Connect Phone Number Claim Tool ===

Fetching Connect instance...
✅ Found instance: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

What type of number do you want?
1) Toll-Free (1-800 number) - Recommended for business
   Cost: $2.00/month + $0.022/min inbound

2) DID (Local area code number)
   Cost: $0.90/month + $0.0022/min inbound

Enter choice (1 or 2): 1

Searching for available toll-free numbers...

 1. +18005551234
 2. +18005555678
 3. +18005559012
 ...

Enter the phone number you want to claim (format: +18005551234): +18005551234

Claiming +18005551234...

✅ Success! Phone number claimed: +18005551234
   Phone Number ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

Next Steps:
1. Update Terraform variables...
2. Create a contact flow...
3. Associate number with contact flow...
4. Test by calling: +18005551234
```

### Options

**Toll-Free (Recommended):**
- Format: +1-800-XXX-XXXX
- Cost: $2.00/month + $0.022/min inbound
- Best for: Business, customer service
- No area code needed

**DID (Local):**
- Format: +1-XXX-XXX-XXXX (area code based)
- Cost: $0.90/month + $0.0022/min inbound
- Best for: Local presence
- Requires area code (813, 212, etc.)

---

## 4. CLEANUP_VOICE.sh

### Purpose
Complete removal of all voice integration resources.

### ⚠️ WARNING

**This is destructive and irreversible!**

Deletes:
- AWS Connect instance
- Claimed phone numbers (released back to AWS)
- Lex bot
- Lambda functions
- S3 bucket and all recordings
- DynamoDB table and all session data
- IAM roles and policies

Does NOT delete:
- Bedrock agents (unchanged)
- Action groups (unchanged)
- Other infrastructure

### Usage

```bash
./scripts/CLEANUP_VOICE.sh
```

### Safety Checks

The script requires **two confirmations**:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  AWS Connect Voice Integration Cleanup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WARNING: This will delete:
  - AWS Connect instance
  - Claimed phone numbers
  - Lex bot
  - Lambda functions
  - S3 bucket (call recordings)
  - DynamoDB table (session data)
  - All IAM roles and policies

This action cannot be undone!

Are you sure you want to continue? (type 'yes' to confirm): yes

Type 'DELETE' to confirm deletion: DELETE

Starting cleanup...
```

### What It Does

1. Releases claimed phone number
2. Empties S3 bucket (required before deletion)
3. Deletes DynamoDB table
4. Runs `terraform destroy`
5. Cleans up local files (deployment packages, configs)

### Example Output

```
[1/6] Loading deployment information...
  Connect Instance: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  Phone Number: +18005551234
  S3 Bucket: pf-call-recordings-dev-618048437522

[2/6] Releasing phone number...
  Releasing: +18005551234
  ✅ Phone number released

[3/6] Emptying S3 bucket...
  Emptying bucket: pf-call-recordings-dev-618048437522
  ✅ S3 bucket emptied

[4/6] Deleting DynamoDB table...
  Deleting table: pf-session-data-dev
  ✅ DynamoDB table deleted

[5/6] Destroying Terraform infrastructure...
  Running terraform destroy...
  ✅ Terraform resources destroyed

[6/6] Cleaning up local files...
  Removed: config/voice_deployment.json
  Removed: Terraform state backups
  Removed: Lambda deployment packages
  ✅ Local files cleaned

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Cleanup Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Voice integration completely removed.

To redeploy, run: ./scripts/DEPLOY_VOICE.sh
```

---

## Common Workflows

### First-Time Deployment

```bash
# 1. Deploy everything
./scripts/DEPLOY_VOICE.sh
# Answer 'yes' to claim phone number

# 2. Test deployment
./scripts/test_voice_integration.sh

# 3. Build Lex bot (required before testing voice)
LEX_BOT_ID=$(jq -r '.lex.bot_id' config/voice_deployment.json)
aws lexv2-models build-bot-locale \
  --bot-id "$LEX_BOT_ID" \
  --bot-version DRAFT \
  --locale-id en_US \
  --region us-east-1

# 4. Create contact flow in AWS Console
# Go to: https://console.aws.amazon.com/connect/
# Navigate to: Routing → Contact flows
# Create: pf-main-inbound

# 5. Test by calling your number
```

### Claim Number Later

```bash
# If you skipped phone number during deployment
./scripts/claim_phone_number.sh
```

### Redeploy After Changes

```bash
# Make changes to Lambda code or Terraform config
./scripts/DEPLOY_VOICE.sh
# Will update existing resources
```

### Complete Cleanup and Redeploy

```bash
# Remove everything
./scripts/CLEANUP_VOICE.sh

# Fresh deployment
./scripts/DEPLOY_VOICE.sh
```

---

## Configuration Files

### Generated by Scripts

| File | Purpose | Created By |
|------|---------|------------|
| `config/voice_deployment.json` | Deployment metadata | DEPLOY_VOICE.sh |
| `infrastructure/terraform/voice/terraform.tfvars` | Terraform variables | DEPLOY_VOICE.sh |
| `infrastructure/terraform/voice/terraform.tfstate` | Terraform state | Terraform |
| `lambda/*/deployment.zip` | Lambda packages | DEPLOY_VOICE.sh |

### Used by Scripts

| File | Purpose | Read By |
|------|---------|---------|
| `config/agent_ids.json` | Bedrock agent IDs | DEPLOY_VOICE.sh |
| `lambda/*/requirements.txt` | Python dependencies | DEPLOY_VOICE.sh |
| `lambda/*/handler.py` | Lambda code | Terraform |

---

## Troubleshooting

### Issue: "No Connect instance found"

**Solution:**
```bash
# Deploy creates the instance
./scripts/DEPLOY_VOICE.sh
```

### Issue: "Terraform init fails"

**Solution:**
```bash
cd infrastructure/terraform/voice
rm -rf .terraform
terraform init
cd ../../..
./scripts/DEPLOY_VOICE.sh
```

### Issue: "Lambda packaging fails"

**Solution:**
```bash
# Ensure pip3 is installed
pip3 --version

# Manually package
cd lambda/lex-fulfillment
pip3 install -r requirements.txt -t package/
cd package && zip -r ../deployment.zip .
cd .. && zip -g deployment.zip handler.py
```

### Issue: "Phone number not available"

**Solution:**
```bash
# Try different area code or use toll-free
./scripts/claim_phone_number.sh
# Choose option 1 (toll-free)
```

### Issue: "Tests failing"

**Solution:**
```bash
# Check Lambda logs
LEX_LAMBDA=$(jq -r '.lambda.lex_fulfillment' config/voice_deployment.json)
aws logs tail /aws/lambda/$LEX_LAMBDA --follow --region us-east-1

# Verify agent IDs
jq . config/agent_ids.json

# Re-prepare agents
aws bedrock-agent prepare-agent --agent-id YEMXAMMRVC --region us-east-1
```

---

## Monitoring Commands

### Real-time Log Monitoring

```bash
# Terminal 1: Lex Fulfillment
aws logs tail /aws/lambda/pf-lex-fulfillment-dev --follow --region us-east-1

# Terminal 2: Voice Bridge
aws logs tail /aws/lambda/pf-voice-bedrock-bridge-dev --follow --region us-east-1

# Terminal 3: Connect Flow Logs
# (View in Connect Console → Contact flows → Flow logs)
```

### Check Deployment Status

```bash
# View all resources
cat config/voice_deployment.json | jq .

# Check Connect instance
INSTANCE_ID=$(jq -r '.connect.instance_id' config/voice_deployment.json)
aws connect describe-instance --instance-id "$INSTANCE_ID" --region us-east-1

# Check Lex bot
LEX_BOT_ID=$(jq -r '.lex.bot_id' config/voice_deployment.json)
aws lexv2-models describe-bot --bot-id "$LEX_BOT_ID" --region us-east-1
```

---

## Script Comparison with Agent Deployment

| Feature | DEPLOY.sh (Agents) | DEPLOY_VOICE.sh |
|---------|-------------------|-----------------|
| **Auto-load config** | ✅ agent_ids.json | ✅ agent_ids.json |
| **Dynamic IDs** | ✅ Yes | ✅ Yes + auto-discover alias |
| **Package Lambda** | ✅ Yes | ✅ Yes (2 functions) |
| **Deploy infrastructure** | ✅ Bedrock agents | ✅ Connect, Lex, Lambda |
| **Interactive prompts** | ✅ Yes | ✅ Yes + phone number |
| **Save deployment info** | ✅ Yes | ✅ voice_deployment.json |
| **Test script** | ❌ No | ✅ test_voice_integration.sh |
| **Cleanup script** | ✅ CLEANUP.sh | ✅ CLEANUP_VOICE.sh |

---

**Quick Reference Card:**

```bash
# Deploy voice integration
./scripts/DEPLOY_VOICE.sh

# Test deployment
./scripts/test_voice_integration.sh

# Claim phone number
./scripts/claim_phone_number.sh

# Remove everything
./scripts/CLEANUP_VOICE.sh

# Monitor logs
aws logs tail /aws/lambda/pf-lex-fulfillment-dev --follow
aws logs tail /aws/lambda/pf-voice-bedrock-bridge-dev --follow
```
