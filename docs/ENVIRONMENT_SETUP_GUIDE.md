# Environment Setup Guide - ProjectForce Scheduling Agent

> Step-by-step guide to deploy the ProjectForce Scheduling Agent to a new AWS environment.

## Table of Contents

1. [Quick Reference - Deployment Command](#1-quick-reference---deployment-command)
2. [Configuration Parameters](#2-configuration-parameters)
3. [Manual Steps Required (MUST DO FIRST)](#3-manual-steps-required-must-do-first)
4. [Prerequisites](#4-prerequisites)
5. [Automated Deployment](#5-automated-deployment)
6. [Manual Setup (Step-by-Step)](#6-manual-setup-step-by-step)
7. [Verification & Testing](#7-verification--testing)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Quick Reference - Deployment Command

```bash
# Full syntax with all configurable parameters
AWS_PROFILE=<profile> ./scripts/pf-manage.sh deploy --all \
  --prefix <resource-prefix> \
  --env <environment>

# Example: Deploy to dev with prefix "pf-syn"
AWS_PROFILE=pf-aws ./scripts/pf-manage.sh deploy --all --prefix pf-syn --env dev

# Example: Deploy to QA with custom prefix
AWS_PROFILE=pf-aws ./scripts/pf-manage.sh deploy --all --prefix myproject --env qa

# Example: Deploy to production
AWS_PROFILE=pf-aws ./scripts/pf-manage.sh deploy --all --prefix pf-syn --env prod
```

---

## 2. Configuration Parameters

### 2.1 Naming Convention

Resources are named using the pattern: `{PREFIX}-{resource}-{ENVIRONMENT}`

| Parameter | Description | Default | Examples |
|-----------|-------------|---------|----------|
| `--prefix` | Resource name prefix | `pf-syn` | `pf-syn`, `myproject`, `acme` |
| `--env` | Environment suffix | `dev` | `dev`, `qa`, `staging`, `prod` |

**Examples of generated resource names:**

| Prefix | Environment | Lambda Name | DynamoDB Table |
|--------|-------------|-------------|----------------|
| `pf-syn` | `dev` | `pf-syn-orchestrator-dev` | `pf-syn-sessions-dev` |
| `pf-syn` | `qa` | `pf-syn-orchestrator-qa` | `pf-syn-sessions-qa` |
| `pf-syn` | `prod` | `pf-syn-orchestrator-prod` | `pf-syn-sessions-prod` |
| `acme` | `dev` | `acme-orchestrator-dev` | `acme-sessions-dev` |

### 2.2 Command Options

| Option | Description |
|--------|-------------|
| `--all` | Deploy all components (lambda, voice, sms) |
| `--lambda` | Deploy Lambda functions and API Gateway only |
| `--voice` | Deploy Voice integration (Lex bot, fulfillment Lambda) only |
| `--sms` | Deploy SMS integration only |
| `--dry-run` | Show what would be done without executing |
| `--force` | Skip confirmation prompts |
| `--debug` | Enable verbose debug output |

### 2.3 Environment Variables

You can also set these via environment variables:

```bash
export AWS_PROFILE=pf-aws           # AWS credentials profile
export AWS_REGION=us-east-1         # AWS region (must be us-east-1 for Connect/Lex)
export RESOURCE_PREFIX=pf-syn       # Resource prefix
export ENVIRONMENT=dev              # Environment suffix
```

---

## 3. Manual Steps Required (MUST DO FIRST)

**These steps CANNOT be automated and must be completed in AWS Console before running deployment scripts.**

### 3.1 Enable Amazon Bedrock Model Access

**Console Location:** AWS Console → Amazon Bedrock → Model access

1. Navigate to Amazon Bedrock in the AWS Console
2. Click "Model access" in the left sidebar
3. Click "Modify model access"
4. Enable `Claude 3.5 Sonnet` (anthropic.claude-3-5-sonnet-20241022-v2:0)
5. Submit request and wait for access (usually immediate)

**Verification:**
```bash
AWS_PROFILE=pf-aws aws bedrock list-foundation-models \
  --query "modelSummaries[?contains(modelId, 'claude')].modelId" \
  --output table
```

### 3.2 Create Amazon Connect Instance

**Console Location:** AWS Console → Amazon Connect → Create instance

1. Navigate to Amazon Connect in the AWS Console
2. Click "Create instance"
3. Configure:
   - Identity management: Store users in Connect
   - Instance alias: `{prefix}-schedule-voice-{env}` (e.g., `pf-syn-schedule-voice-dev`)
   - Admin username/password
   - Data storage: Accept defaults
   - Telephony: Enable both inbound and outbound
4. Wait for instance creation (5-10 minutes)
5. **Record the Instance ID** (format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

**Verification:**
```bash
AWS_PROFILE=pf-aws aws connect list-instances --query 'InstanceSummaryList[*].[Id,InstanceAlias]' --output table
```

### 3.3 Claim Phone Number in Connect

**Console Location:** Amazon Connect Admin → Channels → Phone numbers

1. Open Connect instance admin console
2. Go to Channels → Phone numbers → Claim a phone number
3. Select country and type (DID recommended for voice quality)
4. **Record the phone number** (format: `+1XXXXXXXXXX`)

### 3.4 Create Contact Flow (Semi-Automated)

**The Contact Flow routes voice calls to your Lex bot. There are two approaches:**

#### Option A: Automated via Script (Recommended)

If you already have a template Contact Flow JSON file, the deployment script will create/update it:

```bash
# Contact Flow JSON files are stored in:
scripts/config/connect/pf-main-inbound-voice.json
scripts/config/connect/pf-main-inbound-voice-dev.json  # Environment-specific

# The deploy command handles Contact Flow deployment:
AWS_PROFILE=pf-aws ./scripts/pf-manage.sh deploy --voice --prefix pf-syn --env dev
```

The `lib/voice.sh` script:
- Reads Contact Flow JSON from `scripts/config/connect/`
- Creates new flows or updates existing ones via `aws connect update-contact-flow-content`
- Automatically associates phone numbers with the flow

#### Option B: Manual Console Setup (First Time Only)

If no template exists, create the initial Contact Flow via Console:

**Console Location:** Amazon Connect Admin → Routing → Contact flows

1. Go to Routing → Contact flows → Create contact flow
2. Name: `{prefix}-main-inbound-voice-{env}` (e.g., `pf-syn-main-inbound-voice-dev`)
3. Add blocks in order:

```
[Entry Point]
      ↓
[Set Voice] → Configure Polly voice (e.g., "Joanna", Neural)
      ↓
[Get customer input] → Configure Lex bot:
    - Bot: {prefix}-scheduling-assistant-{env}
    - Alias: TestBotAlias
    - Session attributes (see below)
      ↓
[Handle response]
    ├── Intent: Goodbye → [Play prompt: "Goodbye!"] → [Disconnect]
    ├── Error → [Play prompt: "Sorry, error occurred"] → [Disconnect]
    └── Default → Loop back to [Get customer input]
```

4. Save and Publish

#### Lex Session Attributes Configuration

The "Get customer input" block must pass phone numbers to Lex for authentication:

| Attribute | Value | Purpose |
|-----------|-------|---------|
| `CustomerNumber` | `$.CustomerEndpoint.Address` | Caller's phone number |
| `SystemNumber` | `$.SystemEndpoint.Address` | System phone number called |

#### Update Contact Flow via Script (After Manual Creation)

Once a Contact Flow exists, you can update it via Python script:

```bash
# Update Lex session attributes to pass phone numbers
AWS_PROFILE=pf-aws python3 scripts/update_connect_flow_lex_v4.py
```

This script:
- Fetches the existing Contact Flow JSON
- Updates `LexSessionAttributes` to pass `$.CustomerEndpoint.Address` and `$.SystemEndpoint.Address`
- Saves changes back via `update_contact_flow_content` API

#### Export Contact Flow as Template

To create a reusable template for other environments:

```bash
# Export existing Contact Flow to JSON
source scripts/lib/voice.sh
export RESOURCE_PREFIX=pf-syn
export ENVIRONMENT=dev

# Get instance ID and export
INSTANCE_ID=$(get_connect_instance_id "$(connect_instance_alias)")
export_contact_flow "pf-syn-main-inbound-voice-dev" "$INSTANCE_ID" \
  "scripts/config/connect/pf-main-inbound-voice-dev.json"
```

#### Assign Phone Number to Contact Flow

**Manual (Console):**
1. Go to Channels → Phone numbers
2. Click on your phone number
3. Set "Contact flow / IVR" to your contact flow
4. Save

**Automated (Script):**
```bash
# The deploy script handles this automatically:
AWS_PROFILE=pf-aws ./scripts/pf-manage.sh deploy --voice --prefix pf-syn --env dev
```

### 3.5 Associate Lex Bot with Connect Instance

**Console Location:** Amazon Connect Admin → Contact flows → Amazon Lex

1. Go to Contact flows → Amazon Lex
2. Click "Add Lex bot"
3. Select region: `us-east-1`
4. Select bot: `{prefix}-scheduling-assistant-{env}`
5. Select alias: `TestBotAlias`
6. Click "Add"

**Verification:**
```bash
# List bots associated with Connect instance
AWS_PROFILE=pf-aws aws connect list-bots \
  --instance-id <YOUR_INSTANCE_ID> \
  --lex-version V2 \
  --query 'LexBots[*].[Name,LexRegion]' --output table
```

### 3.6 Request SMS Phone Number

**Console Location:** AWS Console → Amazon Pinpoint → SMS and voice → Phone numbers

1. Navigate to Pinpoint SMS and Voice
2. Request origination identity → Phone number
3. Select:
   - Country: United States
   - Type: Long code or Toll-free
   - Capabilities: SMS (and Voice if needed)
4. Complete registration requirements
5. **Record the phone number** (format: `+1XXXXXXXXXX`)

### 3.7 Configure SMS Two-Way Messaging

**Console Location:** Pinpoint SMS → Phone numbers → Your number → Two-way SMS

1. Click on your SMS phone number
2. Enable "Two-way SMS"
3. Set destination type: SNS topic
4. Set destination: `arn:aws:sns:us-east-1:{ACCOUNT_ID}:{prefix}-sms-inbound-{env}`
5. Save

---

## 4. Prerequisites

### 4.1 AWS Account Requirements

| Requirement | Details |
|-------------|---------|
| AWS Account | With admin access or appropriate IAM permissions |
| Region | `us-east-1` (required for Connect and Lex) |
| Service Quotas | Ensure Lambda, DynamoDB, Connect limits are sufficient |

### 4.2 Local Development Setup

```bash
# Required tools
aws --version          # AWS CLI v2.x required
jq --version           # JSON processor
zip --version          # For Lambda packaging
bash --version         # Bash 4.x+ recommended

# Configure AWS credentials
aws configure --profile pf-aws
# Enter: Access Key, Secret Key, Region (us-east-1), Output (json)

# Verify access
AWS_PROFILE=pf-aws aws sts get-caller-identity
```

### 4.3 Clone Repository

```bash
git clone <repository-url>
cd schedulingAgent
```

---

## 5. Automated Deployment

After completing all manual steps in Section 3, run the automated deployment:

### 5.1 Full Deployment

```bash
# Deploy everything to dev
AWS_PROFILE=pf-aws ./scripts/pf-manage.sh deploy --all --prefix pf-syn --env dev

# Deploy to QA
AWS_PROFILE=pf-aws ./scripts/pf-manage.sh deploy --all --prefix pf-syn --env qa

# Deploy to Production
AWS_PROFILE=pf-aws ./scripts/pf-manage.sh deploy --all --prefix pf-syn --env prod
```

### 5.2 Component-Specific Deployment

```bash
# Deploy Lambda functions only
AWS_PROFILE=pf-aws ./scripts/pf-manage.sh deploy --lambda --prefix pf-syn --env dev

# Deploy Voice (Lex bot) only
AWS_PROFILE=pf-aws ./scripts/pf-manage.sh deploy --voice --prefix pf-syn --env dev

# Deploy SMS integration only
AWS_PROFILE=pf-aws ./scripts/pf-manage.sh deploy --sms --prefix pf-syn --env dev
```

### 5.3 Update Existing Deployment

```bash
# Update Lambda code only (faster for code changes)
AWS_PROFILE=pf-aws ./scripts/pf-manage.sh deploy --lambda --prefix pf-syn --env dev

# Validate current deployment
AWS_PROFILE=pf-aws ./scripts/pf-manage.sh validate --all --prefix pf-syn --env dev

# Show resource status
AWS_PROFILE=pf-aws ./scripts/pf-manage.sh status --prefix pf-syn --env dev
```

### 5.4 Cleanup Resources

```bash
# Remove all resources (with confirmation prompt)
AWS_PROFILE=pf-aws ./scripts/pf-manage.sh cleanup --all --prefix pf-syn --env dev

# Force cleanup without confirmation
AWS_PROFILE=pf-aws ./scripts/pf-manage.sh cleanup --all --prefix pf-syn --env dev --force
```

---

## 6. Manual Setup (Step-by-Step)

If automated scripts fail or for more control, follow these manual steps.

### Phase 1: Foundation (IAM & Secrets)

#### Step 1.1: Create IAM Roles

```bash
# Set configuration
export AWS_PROFILE=pf-aws
export RESOURCE_PREFIX=pf-syn
export ENVIRONMENT=dev

# Source library and create roles
source scripts/lib/common.sh
source scripts/lib/iam.sh

configure_orchestrator_role
configure_scheduling_actions_role
configure_information_actions_role
configure_chitchat_actions_role
configure_notes_actions_role
configure_customer_lookup_role
configure_lex_fulfillment_role
configure_voice_bedrock_bridge_role
configure_sms_inbound_role
```

**Roles Created:**

| Role Name | Purpose |
|-----------|---------|
| `{prefix}-orchestrator-role-{env}` | Main orchestrator Lambda |
| `{prefix}-scheduling-actions-role-{env}` | Scheduling Lambda |
| `{prefix}-information-actions-role-{env}` | Information Lambda |
| `{prefix}-chitchat-actions-role-{env}` | Chitchat Lambda |
| `{prefix}-notes-actions-role-{env}` | Notes Lambda |
| `{prefix}-customer-lookup-role-{env}` | Customer lookup Lambda |
| `{prefix}-lex-fulfillment-role-{env}` | Lex fulfillment Lambda |
| `{prefix}-voice-bedrock-bridge-role-{env}` | Voice bridge Lambda |
| `{prefix}-sms-inbound-role-{env}` | SMS inbound Lambda |

#### Step 1.2: Create Secrets

```bash
AWS_PROFILE=pf-aws aws secretsmanager create-secret \
  --name "projectforce/api/credentials" \
  --secret-string '{"bearer_token":"","refresh_token":"","client_id":"09PF05VD","user_id":"","user_phone":"","exp":0}'
```

### Phase 2: Data Layer (DynamoDB)

```bash
source scripts/lib/dynamodb.sh

export RESOURCE_PREFIX=pf-syn
export ENVIRONMENT=dev

create_core_dynamodb_tables
create_sms_dynamodb_tables
```

**Tables Created:**

| Table Name | Key Schema | Purpose |
|------------|------------|---------|
| `{prefix}-sessions-{env}` | session_id (HASH) | Session state |
| `{prefix}-workflow-states-{env}` | session_id (HASH) | Workflow state |
| `{prefix}-customers-{env}` | phone_number (HASH) | Customer lookup |
| `{prefix}-notes-{env}` | note_id (HASH) | Notes storage |
| `{prefix}-project-notes-{env}` | project_id (HASH), timestamp (RANGE) | Project notes |
| `{prefix}-sms-sessions-{env}` | phone_number (HASH) | SMS sessions |
| `{prefix}-sms-messages-{env}` | message_id (HASH) | SMS messages |
| `{prefix}-sms-consent-{env}` | phone_number (HASH) | SMS consent |
| `{prefix}-opt-out-tracking-{env}` | phone_number (HASH) | Opt-out tracking |

### Phase 3: Compute Layer (Lambda Functions)

```bash
source scripts/lib/lambda.sh

export RESOURCE_PREFIX=pf-syn
export ENVIRONMENT=dev

deploy_all_lambdas
```

### Phase 4: API Layer (API Gateway)

```bash
source scripts/lib/api.sh

export RESOURCE_PREFIX=pf-syn
export ENVIRONMENT=dev

deploy_api_gateway
```

### Phase 5: Voice Integration (Lex Bot)

```bash
source scripts/lib/voice.sh

export RESOURCE_PREFIX=pf-syn
export ENVIRONMENT=dev

deploy_voice
```

**Note:** After deploying the Lex bot, you must manually associate it with Connect (see Section 3.5).

### Phase 6: SMS Integration

```bash
source scripts/lib/sms.sh

export RESOURCE_PREFIX=pf-syn
export ENVIRONMENT=dev

deploy_sms
```

**Note:** After deploying SMS, you must manually configure two-way SMS (see Section 3.7).

---

## 7. Verification & Testing

### 7.1 Validate Deployment

```bash
AWS_PROFILE=pf-aws ./scripts/pf-manage.sh validate --all --prefix pf-syn --env dev
```

### 7.2 Test Lambda Functions

```bash
# Test orchestrator directly
AWS_PROFILE=pf-aws aws lambda invoke \
  --function-name pf-syn-orchestrator-dev \
  --payload '{"body": "{\"message\": \"hello\", \"session_id\": \"test-123\", \"pf_client_id\": \"09PF05VD\", \"pf_user_id\": \"1646085\", \"channel\": \"chat\"}"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/response.json && cat /tmp/response.json
```

### 7.3 Test API Gateway

```bash
# Replace API_ID with your actual API Gateway ID
curl -X POST https://<API_ID>.execute-api.us-east-1.amazonaws.com/dev/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "hello", "session_id": "test-123", "pf_client_id": "09PF05VD", "pf_user_id": "1646085", "channel": "chat"}'
```

### 7.4 Test Voice

1. Call your claimed phone number
2. Speak: "I want to schedule an appointment"
3. Monitor logs:
   ```bash
   AWS_PROFILE=pf-aws aws logs tail /aws/lambda/pf-syn-lex-fulfillment-dev --since 5m --follow
   ```

### 7.5 Test SMS

1. Send SMS to your SMS phone number
2. Text: "Hello"
3. Monitor logs:
   ```bash
   AWS_PROFILE=pf-aws aws logs tail /aws/lambda/pf-syn-sms-inbound-dev --since 5m --follow
   ```

---

## 8. Troubleshooting

### 8.1 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Lambda timeout | Cold start or slow API | Increase timeout to 120s |
| 403 Forbidden | Token expired | Token auto-refreshes; check logs |
| Lex not responding | Bot not built | Build bot in Lex console |
| SMS not received | Two-way SMS not configured | Check Pinpoint console (Section 3.7) |
| Connect call drops | Contact flow misconfigured | Check flow in Connect console (Section 3.4) |
| Voice call gets no response | Lex bot not associated with Connect | Associate bot (Section 3.5) |
| "Bot not found" error | Wrong bot name in contact flow | Verify bot name matches prefix/env |

### 8.2 Check Logs

```bash
# Orchestrator logs
AWS_PROFILE=pf-aws aws logs tail /aws/lambda/{prefix}-orchestrator-{env} --since 10m --follow

# Lex fulfillment logs (voice)
AWS_PROFILE=pf-aws aws logs tail /aws/lambda/{prefix}-lex-fulfillment-{env} --since 10m --follow

# SMS inbound logs
AWS_PROFILE=pf-aws aws logs tail /aws/lambda/{prefix}-sms-inbound-{env} --since 10m --follow
```

### 8.3 Check Secret Status

```bash
AWS_PROFILE=pf-aws aws secretsmanager get-secret-value \
  --secret-id projectforce/api/credentials \
  --query SecretString --output text | jq '{user_id, user_phone, exp}'
```

### 8.4 Reset Session

```bash
AWS_PROFILE=pf-aws aws dynamodb delete-item \
  --table-name {prefix}-sessions-{env} \
  --key '{"session_id": {"S": "your-session-id"}}'
```

---

## Script Library Reference

| Script | Purpose |
|--------|---------|
| `pf-manage.sh` | Main entry point - deploy, cleanup, validate |
| `lib/common.sh` | Shared utilities, logging, validation |
| `lib/iam.sh` | IAM role creation and configuration |
| `lib/lambda.sh` | Lambda deployment and updates |
| `lib/dynamodb.sh` | DynamoDB table creation |
| `lib/voice.sh` | Lex bot and Connect integration |
| `lib/sms.sh` | SMS/SNS configuration |
| `lib/api.sh` | API Gateway setup |
| `lib/secrets.sh` | Secrets Manager operations |
| `lib/cloudwatch.sh` | CloudWatch log configuration |
| `lib/validate.sh` | Resource validation |

---

## Deployment Checklist

Use this checklist for new environment setup:

### Manual Steps (AWS Console)
- [ ] Enable Bedrock Claude 3.5 Sonnet model access
- [ ] Create Amazon Connect instance
- [ ] Claim phone number in Connect
- [ ] Create Contact Flow with Lex bot integration
- [ ] Configure Contact Flow blocks (Set Voice, Get Customer Input, etc.)
- [ ] Assign phone number to Contact Flow
- [ ] Request SMS phone number (Pinpoint)
- [ ] Configure SMS two-way messaging to SNS topic

### Automated Steps (Scripts)
- [ ] Run: `./pf-manage.sh deploy --all --prefix <prefix> --env <env>`
- [ ] Associate Lex bot with Connect instance (Console)
- [ ] Run: `./pf-manage.sh validate --all --prefix <prefix> --env <env>`

### Testing
- [ ] Test API Gateway endpoint
- [ ] Test voice call
- [ ] Test SMS
- [ ] Verify logs in CloudWatch

---

*Last Updated: December 12, 2024*
