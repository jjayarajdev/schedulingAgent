# Developer Handover Documentation

**Project:** AWS Bedrock Multi-Agent Scheduling System
**Created:** October 13, 2025
**Status:** Phase 1 Complete, Phase 2 Research Complete, Phase 3 Research Complete
**AWS Account:** 618048437522
**Region:** us-east-1

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [AWS Account & Credentials](#aws-account--credentials)
3. [Deployed AWS Resources](#deployed-aws-resources)
4. [Project Status by Phase](#project-status-by-phase)
5. [Quick Start Guide](#quick-start-guide)
6. [Testing & Verification](#testing--verification)
7. [Deployment Procedures](#deployment-procedures)
8. [Known Issues & Manual Steps](#known-issues--manual-steps)
9. [Cost Information](#cost-information)
10. [Documentation Index](#documentation-index)
11. [Support & Contacts](#support--contacts)

---

## Executive Summary

This project implements an AI-powered scheduling agent system using **AWS Bedrock Multi-Agent Collaboration** with a supervisor-collaborator architecture. The system uses 5 specialized agents powered by **Claude Sonnet 4.5** to handle customer scheduling requests for ProjectsForce 360.

### What's Been Completed

- ✅ **Phase 1:** 5 Bedrock Agents deployed with multi-agent collaboration (18/18 tests passing)
- ✅ **Phase 2 Research:** AWS SMS infrastructure documented
- ✅ **Bulk Operations:** Lambda function, OpenAPI schema, comprehensive Swagger documentation
- ✅ **Phase 3 Research:** AWS Connect + Bedrock Agent IVR integration analysis

### What's Pending

- ⏳ **Bulk Operations:** Manual AWS Console configuration (coordinator collaborator action group)
- ⏳ **Phase 2 Implementation:** SMS two-way messaging deployment
- ⏳ **Phase 3 Implementation:** AWS Connect IVR system (12-14 weeks estimated)
- ⏳ **Lambda Functions:** 12 action handlers for Phase 1 agents (PF360 API integration)

---

## AWS Account & Credentials

### Account Information

| Property | Value |
|----------|-------|
| **AWS Account ID** | `618048437522` |
| **Primary Region** | `us-east-1` (US East - N. Virginia) |
| **Cross-Region Profiles** | `us-east-1`, `us-east-2`, `us-west-2` |
| **Account Owner** | jjayaraj@projectsforce.com |

### AWS CLI Configuration

```bash
# Verify current AWS identity
aws sts get-caller-identity

# Expected output:
# {
#     "UserId": "...",
#     "Account": "618048437522",
#     "Arn": "arn:aws:iam::618048437522:user/..."
# }

# Configure AWS CLI (if needed)
aws configure
# Access Key ID: [Stored in 1Password/Secrets Manager]
# Secret Access Key: [Stored in 1Password/Secrets Manager]
# Default region: us-east-1
# Default output format: json
```

### Required IAM Permissions

Your IAM user/role must have permissions for:

- **Bedrock:** Full access (agents, models, inference profiles)
- **IAM:** Create/manage roles and policies
- **S3:** Create buckets, upload objects
- **Lambda:** Create/invoke functions
- **DynamoDB:** Create tables, read/write items
- **Secrets Manager:** Create/read secrets
- **CloudWatch:** Logs and metrics
- **End User Messaging:** SMS configuration

**Managed Policies:**
- `PowerUserAccess` (recommended for development)
- Or custom policy: See `AWS_SETUP_GUIDE.md` lines 76-106

### Secrets in AWS Secrets Manager

| Secret Name | Purpose | How to Retrieve |
|-------------|---------|-----------------|
| `scheduling-agent/aurora/master-password` | Aurora PostgreSQL password | `aws secretsmanager get-secret-value --secret-id scheduling-agent/aurora/master-password --query SecretString --output text` |
| `scheduling-agent/jwt/secret-key` | JWT authentication secret | `aws secretsmanager get-secret-value --secret-id scheduling-agent/jwt/secret-key --query SecretString --output text` |
| `scheduling-agent/pf360/api-credentials` | PF360 API credentials | `aws secretsmanager get-secret-value --secret-id scheduling-agent/pf360/api-credentials --query SecretString --output text` |

**⚠️ IMPORTANT:** Never commit secrets to git. Always retrieve from Secrets Manager.

### Environment Files

**Backend `.env` template:**
```bash
# Copy from example
cp backend/.env.example backend/.env

# Get secrets from AWS
AURORA_PASSWORD=$(aws secretsmanager get-secret-value --secret-id scheduling-agent/aurora/master-password --query SecretString --output text)
JWT_SECRET=$(aws secretsmanager get-secret-value --secret-id scheduling-agent/jwt/secret-key --query SecretString --output text)

# Update .env file with actual values
```

---

## Deployed AWS Resources

### Phase 1: Bedrock Agents (✅ Deployed)

#### Supervisor Agent

- **Agent ID:** `5VTIWONUMO`
- **Name:** `scheduling-agent-supervisor`
- **Model:** Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`)
- **Status:** PREPARED
- **Role:** Routes requests to appropriate specialist agents
- **Aliases:**
  - `HH2U7EZXMW` (Latest - version 6)
  - `TSTALIASID` (Test - points to DRAFT)
  - `PEXPJRXIML` (v1 - deprecated)

#### Collaborator Agents

| Agent | ID | v4 Alias | Status | Actions |
|-------|-----|----------|--------|---------|
| **Scheduling** | `IX24FSMTQH` | `TYJRF3CJ7F` | PREPARED | 6 scheduling actions |
| **Information** | `C9ANXRIO8Y` | `YVNFXEKPWO` | PREPARED | 4 information actions |
| **Notes** | `G5BVBYEPUM` | `F9QQNLZUW8` | PREPARED | 2 note actions |
| **Chitchat** | `BIUW1ARHGL` | `THIPMPJCPI` | PREPARED | Conversational only |

**Test Agent in AWS Console:**
https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/5VTIWONUMO

#### IAM Roles

Each agent has its own IAM service role:
- `scheduling-agent-supervisor-service-role`
- `scheduling-agent-scheduling-service-role`
- `scheduling-agent-information-service-role`
- `scheduling-agent-notes-service-role`
- `scheduling-agent-chitchat-service-role`

### Bulk Operations (✅ Lambda Deployed, ⏳ Action Group Pending)

#### Lambda Function

- **Function Name:** `scheduling-agent-bulk-ops-dev`
- **ARN:** `arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-bulk-ops-dev`
- **Runtime:** Python 3.11
- **Memory:** 1024 MB
- **Timeout:** 60 seconds
- **Handler:** `handler.lambda_handler`
- **Package Size:** 17.3 MB (18,181,359 bytes)
- **Status:** ✅ Active

**Environment Variables:**
```
ENVIRONMENT=dev
DYNAMODB_TABLE=scheduling-agent-bulk-ops-tracking-dev
MAX_PROJECTS=50
PF360_API_URL=https://api.pf360.com
```

**Invoke Lambda:**
```bash
aws lambda invoke \
  --function-name scheduling-agent-bulk-ops-dev \
  --region us-east-1 \
  --payload '{"body": "{\"operation\": \"optimize_route\", \"project_ids\": [\"12345\", \"12347\"], \"date\": \"2025-10-15\"}"}' \
  response.json
```

#### Coordinator Collaborator Agent (⏳ Pending Action Group)

- **Agent ID:** `QHUR9JP4GT`
- **ARN:** `arn:aws:bedrock:us-east-1:618048437522:agent/QHUR9JP4GT`
- **Name:** `scheduling-agent-coordinator-collaborator`
- **Model:** Claude Sonnet 4.5 (`anthropic.claude-sonnet-4-5-v1:0`)
- **Status:** NOT_PREPARED
- **Issue:** Action group needs to be configured manually via AWS Console

**Manual Step Required:** See "Known Issues & Manual Steps" section below

#### DynamoDB Table

- **Table Name:** `scheduling-agent-bulk-ops-tracking-dev`
- **ARN:** `arn:aws:dynamodb:us-east-1:618048437522:table/scheduling-agent-bulk-ops-tracking-dev`
- **Key Schema:** `operation_id` (String, HASH)
- **Billing Mode:** PAY_PER_REQUEST
- **TTL:** Enabled on `ttl` attribute
- **Status:** ✅ Active

**Query Table:**
```bash
aws dynamodb scan --table-name scheduling-agent-bulk-ops-tracking-dev
```

### S3 Buckets

#### Agent Schemas Bucket

- **Bucket Name:** `scheduling-agent-schemas-dev-618048437522`
- **Region:** us-east-1
- **Purpose:** Stores OpenAPI schemas for agent action groups
- **Contents:**
  - `scheduling_actions.json` (6 actions)
  - `information_actions.json` (4 actions)
  - `notes_actions.json` (2 actions)

**List Contents:**
```bash
aws s3 ls s3://scheduling-agent-schemas-dev-618048437522/ --recursive
```

#### Bulk Operations Artifacts Bucket

- **Bucket Name:** `scheduling-agent-artifacts-dev`
- **Region:** us-east-1
- **Purpose:** Stores OpenAPI schema for coordinator bulk operations
- **Contents:**
  - `openapi-schemas/coordinator_actions.json` (14.1 KB, 365 lines)

**List Contents:**
```bash
aws s3 ls s3://scheduling-agent-artifacts-dev/ --recursive
```

#### Terraform State Bucket

- **Bucket Name:** `projectsforce-terraform-state-618048437522`
- **Region:** us-east-1
- **Purpose:** Stores Terraform state files
- **Versioning:** Enabled
- **Encryption:** AES256

**⚠️ CRITICAL:** Do not delete this bucket - it contains infrastructure state

### DynamoDB Tables

| Table Name | Purpose | Key Schema | Billing Mode |
|------------|---------|------------|--------------|
| `terraform-lock` | Terraform state locking | `LockID` (HASH) | PAY_PER_REQUEST |
| `scheduling-agent-bulk-ops-tracking-dev` | Bulk operations tracking | `operation_id` (HASH) | PAY_PER_REQUEST |

### CloudWatch Log Groups

| Log Group | Retention | Purpose |
|-----------|-----------|---------|
| `/aws/ecs/scheduling-agent` | 7 days | ECS container logs |
| `/aws/lambda/scheduling-agent` | 7 days | Lambda function logs |
| `/aws/bedrock/scheduling-agent` | 7 days | Bedrock agent logs |
| `/aws/lambda/scheduling-agent-bulk-ops-dev` | 7 days | Bulk ops Lambda logs |

**Tail Logs:**
```bash
# Bulk operations Lambda logs
aws logs tail /aws/lambda/scheduling-agent-bulk-ops-dev --follow

# Bedrock agent logs
aws logs tail /aws/bedrock/scheduling-agent --follow
```

---

## Project Status by Phase

### Phase 1: Multi-Agent Bedrock Deployment (✅ COMPLETE)

**Status:** Fully deployed and tested
**Completion Date:** October 12, 2025
**Test Results:** 18/18 tests passing

**What's Working:**
- ✅ 5 Bedrock Agents deployed with Claude Sonnet 4.5
- ✅ Multi-agent collaboration enabled
- ✅ Supervisor routes to correct collaborators (chitchat, scheduling, information, notes)
- ✅ Cross-region inference profiles working (us-east-1, us-east-2, us-west-2)
- ✅ All agents in PREPARED status
- ✅ Interactive testing in AWS Console working

**What's Pending:**
- ⏳ Lambda functions for 12 action handlers (PF360 API integration)
- ⏳ Connect Lambda ARNs to agent action groups
- ⏳ End-to-end testing with real PF360 API

**Key Files:**
- `infrastructure/terraform/bedrock_agents.tf` (550 lines)
- `infrastructure/agent_instructions/*.txt` (5 files)
- `infrastructure/openapi_schemas/*.json` (3 files)

**Testing:**
- Test in AWS Console: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/5VTIWONUMO
- Or run: `python3 tests/test_agents_interactive.py`

### Phase 2: AWS SMS Integration (✅ RESEARCH COMPLETE)

**Status:** Research and documentation complete, not yet implemented
**Documentation:** `PHASE2_AWS_SMS_RESEARCH.md` (80 KB), `PHONE_NUMBER_SETUP_GUIDE.md` (30 KB)

**Key Findings:**
- ✅ AWS End User Messaging SMS (formerly Pinpoint SMS)
- ✅ Two-way messaging supported with Lambda
- ✅ TCPA 2025 compliance requirements documented
- ✅ Phone number provisioning process: 2-4 weeks
- ✅ Toll-free: $2/month, 10DLC: $8-15/month

**What's Needed for Implementation:**
1. Request phone number via AWS Console (2-4 weeks wait)
2. Deploy Lambda function for incoming SMS webhook
3. Configure two-way messaging settings
4. Set up DynamoDB tables for SMS sessions and consent management
5. Implement opt-out/opt-in flows (10 business day processing)

**Cost Estimate:** $50-100/month (phone number + usage)

### Bulk Operations (✅ DEPLOYED, ⏳ ACTION GROUP PENDING)

**Status:** Lambda function deployed, Swagger docs complete, manual configuration needed

**What's Working:**
- ✅ Lambda function: `scheduling-agent-bulk-ops-dev` (Active)
- ✅ DynamoDB tracking table (Active)
- ✅ 4 bulk operations implemented:
  - Route optimization (TSP algorithm, 2-50 projects)
  - Bulk team assignments (1-100 projects)
  - Project validation (1-100 projects)
  - Conflict detection (unlimited)
- ✅ OpenAPI 3.0.3 specification (29 KB)
- ✅ Interactive Swagger UI documentation (`BULK_OPS_API_DOCS.html`)
- ✅ Postman collection with 11 pre-configured requests
- ✅ Complete API documentation suite (9 files, 148 KB)

**What's Pending:**
- ⏳ **MANUAL STEP:** Configure action group for coordinator agent via AWS Console
  - Agent ID: `QHUR9JP4GT`
  - Needs Lambda ARN attached: `arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-bulk-ops-dev`
  - See `BULK_OPS_DEPLOYMENT.md` Section 6 for step-by-step instructions

**Documentation:**
- Design: `BULK_SCHEDULING_DESIGN.md` (612 lines)
- Deployment: `BULK_OPS_DEPLOYMENT.md` (14 KB)
- API Docs: `API_DOCUMENTATION_INDEX.md` (master index)
- Interactive: Run `./serve-docs.sh` then visit http://localhost:8080/BULK_OPS_API_DOCS.html
  - **Note:** HTML must be served via HTTP due to CORS (see `HOW_TO_VIEW_SWAGGER_UI.md`)

**Performance:**
- 10 projects: 2-3 seconds
- 25 projects: 4-5 seconds
- 50 projects: 7-10 seconds
- 100 projects: 10-15 seconds (bulk assign/validate only)

### Phase 3: AWS Connect IVR (✅ RESEARCH COMPLETE)

**Status:** Research complete, not yet implemented
**Documentation:** `PHASE3_AWS_CONNECT_RESEARCH.md` (68 KB, 1,185 lines)

**Key Findings:**
- ✅ AWS Connect + Bedrock Agent integration fully supported via Amazon Lex
- ⚠️ SMS requires SEPARATE phone number from voice (cannot share)
- ⚠️ Caller ID name (CNAM) discontinued by AWS March 2023 - only number displays
- ✅ Real-time transcription with Amazon Transcribe
- ✅ Sentiment analysis with Contact Lens
- ✅ Multi-channel support (voice, chat, SMS)

**Architecture:**
```
Customer (Voice/SMS)
    ↓
Amazon Connect (Contact Center)
    ↓
Amazon Lex (NLU + Intent Recognition)
    ↓
Amazon Bedrock Agent (AI Orchestration)
    ↓
Existing 5 Collaborator Agents
    ↓
Lambda Functions → PF360 API
```

**Cost Estimate:** $450-$1,600/month depending on volume
- Amazon Connect: $300-1,000/month
- Amazon Lex: $100-300/month
- Transcription: $50-200/month
- Sentiment Analysis: $50-100/month

**Implementation Timeline:** 12-14 weeks
- Weeks 1-2: AWS Connect setup
- Weeks 3-4: Amazon Lex integration
- Weeks 5-8: Bedrock Agent connection
- Weeks 9-10: Contact flows
- Weeks 11-12: Testing
- Weeks 13-14: Production deployment

**Next Steps:**
- Request AWS Connect instance via AWS Console
- Set up phone numbers (voice + SMS separate)
- Configure Amazon Lex bot
- Integrate with existing Bedrock agents

---

## Quick Start Guide

### Prerequisites

1. **Tools Installed:**
   - AWS CLI v2 (`aws --version`)
   - Python 3.11+ (`python3 --version`)
   - Terraform 1.5+ (if making infrastructure changes)
   - jq (for JSON parsing)

2. **AWS Access Configured:**
   ```bash
   # Verify AWS CLI is configured
   aws sts get-caller-identity

   # Should show Account: 618048437522
   ```

3. **Repository Cloned:**
   ```bash
   cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
   ```

### 5-Minute Setup

```bash
# 1. Verify AWS resources
aws bedrock-agent list-agents --region us-east-1

# 2. Check agent status
aws bedrock-agent get-agent \
  --agent-id 5VTIWONUMO \
  --region us-east-1 | grep agentStatus

# 3. List all collaborators
aws bedrock-agent list-agent-collaborators \
  --agent-id 5VTIWONUMO \
  --agent-version DRAFT \
  --region us-east-1

# 4. Test bulk operations Lambda
aws lambda invoke \
  --function-name scheduling-agent-bulk-ops-dev \
  --region us-east-1 \
  --payload '{"body": "{\"operation\": \"detect_conflicts\", \"project_ids\": [\"12345\"], \"team\": \"Team A\", \"date_range\": [\"2025-10-15\", \"2025-10-20\"]}"}' \
  response.json

# 5. View response
cat response.json
```

### Test the System

**Option 1: AWS Console (Recommended)**

1. Go to: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/5VTIWONUMO
2. Click **"Test"** button (top right)
3. Try these messages:
   - `Hello! How are you?` → Routes to chitchat
   - `I want to schedule an appointment` → Routes to scheduling
   - `What are your working hours?` → Routes to information
   - `Add a note that I prefer mornings` → Routes to notes

**Option 2: Python Test Script**

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
python3 tests/test_agents_interactive.py
```

**Option 3: Comprehensive Test Suite**

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
python3 tests/comprehensive_test.py
```

---

## Testing & Verification

### Agent Testing

#### Test 1: Verify All Agents Are Prepared

```bash
# Run verification script
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
./scripts/verify_deployment.sh
```

**Expected Output:**
```
✓ Checking Supervisor Agent...
Agent: scheduling-agent-supervisor | Status: PREPARED | Model: us.anthropic.claude-sonnet-4-5-20250929-v1:0

✓ Checking Collaborator Associations...
Found 4 collaborators associated with supervisor

✓ Checking All Agent Statuses...
  scheduling-agent-supervisor: PREPARED
  scheduling-agent-scheduling: PREPARED
  scheduling-agent-information: PREPARED
  scheduling-agent-notes: PREPARED
  scheduling-agent-chitchat: PREPARED

✅ Deployment Verification Complete!
```

#### Test 2: Interactive Agent Testing

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
python3 tests/test_agents_interactive.py
```

This script provides:
- Pre-flight checks (credentials, agent status, collaborators)
- 4 predefined test scenarios
- Interactive chat mode
- Console testing instructions

#### Test 3: Comprehensive Test Suite

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
python3 tests/comprehensive_test.py
```

**Tests:**
1. Chitchat routing
2. Scheduling routing
3. Information routing
4. Notes routing
5. Session management
6. Multi-turn conversations
7. Error handling
8. Response time validation

**Test Results:** 18/18 tests passing (as of October 13, 2025)

### Bulk Operations Testing

#### Test 1: Route Optimization

```bash
aws lambda invoke \
  --function-name scheduling-agent-bulk-ops-dev \
  --region us-east-1 \
  --payload '{"body": "{\"operation\": \"optimize_route\", \"project_ids\": [\"12345\", \"12347\", \"12350\"], \"date\": \"2025-10-15\", \"optimize_for\": \"time\"}"}' \
  response.json && cat response.json
```

#### Test 2: Bulk Assignment

```bash
aws lambda invoke \
  --function-name scheduling-agent-bulk-ops-dev \
  --region us-east-1 \
  --payload '{"body": "{\"operation\": \"bulk_assign_teams\", \"project_ids\": [\"15001\", \"15002\", \"15003\"], \"team\": \"Team A\", \"date_range\": [\"2025-10-15\", \"2025-10-20\"]}"}' \
  response.json && cat response.json
```

#### Test 3: Project Validation

```bash
aws lambda invoke \
  --function-name scheduling-agent-bulk-ops-dev \
  --region us-east-1 \
  --payload '{"body": "{\"operation\": \"validate_projects\", \"project_ids\": [\"10001\", \"10002\", \"10003\"], \"validation_checks\": [\"permit\", \"measurement\", \"access\"]}"}' \
  response.json && cat response.json
```

#### Test 4: Using Postman

1. Import collection: `docs/BULK_OPS_POSTMAN_COLLECTION.json`
2. Configure AWS authentication (Signature v4)
3. Run any of the 11 pre-configured requests

### Monitoring & Logs

**CloudWatch Logs:**
```bash
# Tail Lambda logs
aws logs tail /aws/lambda/scheduling-agent-bulk-ops-dev --follow

# Filter errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/scheduling-agent-bulk-ops-dev \
  --filter-pattern "ERROR"

# Get recent invocations
aws lambda get-function \
  --function-name scheduling-agent-bulk-ops-dev \
  --query 'Configuration.{LastModified:LastModified,Version:Version,State:State}'
```

**Lambda Metrics:**
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=scheduling-agent-bulk-ops-dev \
  --start-time 2025-10-13T00:00:00Z \
  --end-time 2025-10-14T00:00:00Z \
  --period 3600 \
  --statistics Average,Maximum
```

---

## Deployment Procedures

### Phase 1 Agents (Already Deployed)

The Phase 1 agents are fully deployed via Terraform. If you need to make changes:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/terraform

# 1. Make changes to bedrock_agents.tf or agent instructions

# 2. Plan changes
terraform plan

# 3. Apply changes
terraform apply

# 4. Prepare agents
aws bedrock-agent prepare-agent --agent-id 5VTIWONUMO --region us-east-1
aws bedrock-agent prepare-agent --agent-id IX24FSMTQH --region us-east-1
aws bedrock-agent prepare-agent --agent-id C9ANXRIO8Y --region us-east-1
aws bedrock-agent prepare-agent --agent-id G5BVBYEPUM --region us-east-1
aws bedrock-agent prepare-agent --agent-id BIUW1ARHGL --region us-east-1

# 5. Verify
./scripts/verify_deployment.sh
```

### Bulk Operations Lambda Updates

To update the bulk operations Lambda function:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/lambda/bulk-operations

# 1. Make changes to handler.py

# 2. Install dependencies
pip install -r requirements.txt -t package/

# 3. Package Lambda
cp handler.py package/
cd package
zip -r ../lambda-package.zip .
cd ..

# 4. Deploy
aws lambda update-function-code \
  --function-name scheduling-agent-bulk-ops-dev \
  --zip-file fileb://lambda-package.zip \
  --region us-east-1

# 5. Wait for update to complete
aws lambda wait function-updated \
  --function-name scheduling-agent-bulk-ops-dev

# 6. Test
aws lambda invoke \
  --function-name scheduling-agent-bulk-ops-dev \
  --region us-east-1 \
  --payload '{"body": "{\"operation\": \"detect_conflicts\", \"project_ids\": [\"12345\"], \"team\": \"Team A\", \"date_range\": [\"2025-10-15\", \"2025-10-20\"]}"}' \
  response.json
```

### Creating New Lambda Functions

For new Lambda functions (e.g., Phase 1 action handlers):

```bash
# 1. Create function directory
mkdir -p lambda/new-function

# 2. Create handler.py
cat > lambda/new-function/handler.py <<'EOF'
import json

def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Success'})
    }
EOF

# 3. Create requirements.txt
cat > lambda/new-function/requirements.txt <<'EOF'
boto3>=1.28.0
requests>=2.31.0
EOF

# 4. Package and deploy (see script above)

# 5. Grant Bedrock Agent permissions
aws lambda add-permission \
  --function-name new-function \
  --statement-id bedrock-agent-access \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn "arn:aws:bedrock:us-east-1:618048437522:agent/*"
```

---

## Known Issues & Manual Steps

### Issue 1: Coordinator Agent Action Group (⏳ URGENT)

**Status:** Lambda deployed, but action group configuration failed via AWS CLI

**Problem:** AWS CLI `create-agent-action-group` validation error when using OpenAPI schema from S3:
```
ValidationException: Failed to create OpenAPI 3 model from the JSON/YAML object
```

**Manual Fix Required:**

1. **Open AWS Bedrock Console:**
   - Go to: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents
   - Click on agent: `scheduling-agent-coordinator-collaborator`
   - Agent ID: `QHUR9JP4GT`

2. **Create Action Group:**
   - Scroll to "Action groups" section
   - Click **"Add action group"**
   - Action group name: `coordinator-bulk-operations`
   - Description: `Bulk scheduling operations for coordinators`

3. **Configure Action Group:**
   - Action group type: **"Define with API schemas"**
   - Action group invocation: **"Select Lambda function"**
   - Lambda function: **`scheduling-agent-bulk-ops-dev`**
   - API schema: **"Define via in-line schema editor"**

4. **Paste OpenAPI Schema:**
   - Copy contents from: `s3://scheduling-agent-artifacts-dev/openapi-schemas/coordinator_actions.json`
   - Or use local file: `infrastructure/openapi_schemas/coordinator_actions.json`
   - Paste into schema editor

5. **Save and Prepare:**
   - Click **"Add action group"**
   - Click **"Prepare"** at top of page
   - Wait 10-15 seconds for preparation

6. **Verify:**
   ```bash
   aws bedrock-agent get-agent \
     --agent-id QHUR9JP4GT \
     --region us-east-1 | grep agentStatus

   # Should show: "agentStatus": "PREPARED"
   ```

**Full Instructions:** See `BULK_OPS_DEPLOYMENT.md` Section 6

### Issue 2: Lambda Function Permissions for Bedrock

If you create new Lambda functions for agent action groups, you must grant Bedrock invoke permissions:

```bash
aws lambda add-permission \
  --function-name your-function-name \
  --statement-id bedrock-agent-access \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn "arn:aws:bedrock:us-east-1:618048437522:agent/*" \
  --region us-east-1
```

### Issue 3: Cross-Region Inference Profile

The system uses cross-region inference profiles to improve availability. If you see throttling errors:

```bash
# Verify inference profile
aws bedrock get-inference-profile \
  --inference-profile-identifier us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --region us-east-1

# The profile routes across us-east-1, us-east-2, us-west-2
```

**Resolution:** This was resolved by adding cross-region IAM permissions. See `403_ERROR_RESOLUTION.md` for details.

### Issue 4: API Invocation Permissions

Direct API invocation of agents (via `bedrock-agent-runtime:InvokeAgent`) may fail with 403 errors, even when console testing works.

**Workaround:** Use AWS Console testing instead of programmatic API calls for now.

**To Fix (if needed):**
1. Request on-demand API access via AWS Support
2. Or add IAM permissions:
   ```json
   {
     "Effect": "Allow",
     "Action": [
       "bedrock-agent-runtime:InvokeAgent"
     ],
     "Resource": "arn:aws:bedrock:us-east-1:618048437522:agent/*"
   }
   ```

---

## Cost Information

### Current Monthly Costs (As of October 13, 2025)

| Service | Configuration | Estimated Cost |
|---------|---------------|----------------|
| **Bedrock Agents** | AgentCore (5 agents) | **$0** (FREE until Sept 16, 2025) |
| **Bedrock Inference** | Claude Sonnet 4.5 usage | $0-50 (pay per use) |
| **Lambda** | Bulk ops function | $0-5 (pay per invocation) |
| **DynamoDB** | 2 tables (PAY_PER_REQUEST) | $0-5 |
| **S3** | 3 buckets | ~$1 |
| **Secrets Manager** | 3 secrets | $1.20 ($0.40 each) |
| **CloudWatch** | Logs (7-day retention) | $0-5 |
| **IAM** | Roles and policies | Free |
| **TOTAL** | | **$2-67/month** |

### Projected Costs After Full Implementation

#### Phase 1 Complete (Lambda Functions)
- Bedrock AgentCore: $200-300/month (after Sept 2025)
- Model invocations: $50-100/month
- Lambda: $10-20/month
- Other: $10/month
- **Total: $270-430/month**

#### Phase 2 (SMS)
- Phone number: $2-15/month
- SMS messages: $0.0079/inbound, $0.0070/outbound
- Lambda webhook: $5/month
- DynamoDB sessions: $5/month
- **Additional: $50-100/month**

#### Phase 3 (AWS Connect IVR)
- Amazon Connect: $300-1,000/month
- Amazon Lex: $100-300/month
- Transcription: $50-200/month
- Sentiment Analysis: $50-100/month
- **Additional: $500-1,600/month**

### Cost Optimization Tips

1. **AgentCore Preview Pricing:** FREE until September 16, 2025 - develop now!
2. **DynamoDB:** Use PAY_PER_REQUEST instead of provisioned capacity
3. **CloudWatch:** Set 7-day retention (already configured)
4. **Lambda:** Optimize memory and timeout settings
5. **S3:** Use lifecycle policies for old objects

### Cost Monitoring

**Set up billing alerts:**
```bash
# Create budget
aws budgets create-budget \
  --account-id 618048437522 \
  --budget file://budget.json

# Check current spend
aws ce get-cost-and-usage \
  --time-period Start=2025-10-01,End=2025-10-31 \
  --granularity MONTHLY \
  --metrics BlendedCost
```

**Billing Dashboard:**
https://console.aws.amazon.com/billing/home

**Cost Explorer:**
https://console.aws.amazon.com/cost-management/home

---

## Documentation Index

### Primary Documentation (Must Read)

| Document | Purpose | Location |
|----------|---------|----------|
| **DEVELOPER_HANDOVER.md** | This file - master handover document | `docs/` |
| **README.md** | Project overview and architecture | `docs/` |
| **DEPLOYMENT_STATUS.md** | Current deployment status and agent IDs | `docs/` |
| **API_DOCUMENTATION_INDEX.md** | Master index for all API documentation | `docs/` |

### Phase 1: Bedrock Agents

| Document | Purpose | Size |
|----------|---------|------|
| `DEPLOYMENT_GUIDE.md` | Step-by-step deployment instructions | 14 KB |
| `ARCHITECTURE_RESEARCH.md` | Bedrock vs LangGraph comparison (60 pages) | 150 KB |
| `TESTING_GUIDE.md` | Testing procedures and scripts | 10 KB |
| `403_ERROR_RESOLUTION.md` | Cross-region permission fix | 5 KB |

### Bulk Operations

| Document | Purpose | Size |
|----------|---------|------|
| `BULK_SCHEDULING_DESIGN.md` | Architecture and algorithms | 20 KB |
| `BULK_OPS_DEPLOYMENT.md` | Deployment guide with manual steps | 14 KB |
| `BULK_SCHEDULING_SUMMARY.md` | Feature summary and benchmarks | 12 KB |
| `API_DOCUMENTATION_README.md` | Complete API documentation | 10 KB |
| `API_QUICK_REFERENCE.md` | One-page API cheat sheet | 6 KB |
| `BULK_OPS_API_DOCS.html` | **Interactive Swagger UI** (open in browser) | 8 KB |
| `BULK_OPS_API_SWAGGER.yaml` | OpenAPI 3.0.3 specification | 29 KB |
| `BULK_OPS_POSTMAN_COLLECTION.json` | 11 pre-configured API requests | 21 KB |

### Phase 2: AWS SMS

| Document | Purpose | Size |
|----------|---------|------|
| `PHASE2_AWS_SMS_RESEARCH.md` | Complete SMS research and requirements | 80 KB |
| `PHONE_NUMBER_SETUP_GUIDE.md` | Step-by-step phone setup with screenshots | 30 KB |

### Phase 3: AWS Connect IVR

| Document | Purpose | Size |
|----------|---------|------|
| `PHASE3_AWS_CONNECT_RESEARCH.md` | Complete IVR research (15 sections) | 68 KB |

### AWS Setup & Configuration

| Document | Purpose | Size |
|----------|---------|------|
| `AWS_SETUP_GUIDE.md` | Comprehensive AWS setup guide | 20 KB |
| `AWS_SETUP_STEP_BY_STEP.md` | Command-by-command execution guide | 18 KB |
| `ENABLE_API_ACCESS.md` | Troubleshooting API access issues | 8 KB |

### Reference Documentation

| Document | Purpose |
|----------|---------|
| `CREATED_FILES.md` | Complete inventory of files created |
| `TERRAFORM_COMPLETE.md` | Terraform configuration details |
| `IMPLEMENTATION_PLAN.md` | Original implementation plan |
| `MIGRATION_PLAN.md` | Migration strategy from prototype |

### Deprecated/Outdated Documents

The following documents are outdated and can be ignored:
- `GETTING_STARTED.md` - Replaced by PHASE1_GETTING_STARTED.md
- `PHASE1_GETTING_STARTED.md` - Replaced by DEPLOYMENT_GUIDE.md
- Several intermediate status reports

**Recommendation:** These should be archived or deleted to avoid confusion.

---

## Support & Contacts

### Project Information

- **Project Owner:** jjayaraj@projectsforce.com
- **AWS Account:** 618048437522
- **Primary Region:** us-east-1
- **Repository:** `/Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/`

### AWS Resources

- **AWS Console:** https://console.aws.amazon.com/
- **Bedrock Agents:** https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents
- **Supervisor Agent:** https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/5VTIWONUMO
- **Lambda Functions:** https://console.aws.amazon.com/lambda/home?region=us-east-1
- **CloudWatch Logs:** https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups

### Key Commands Reference

```bash
# Verify AWS identity
aws sts get-caller-identity

# List all agents
aws bedrock-agent list-agents --region us-east-1

# Check agent status
aws bedrock-agent get-agent --agent-id 5VTIWONUMO --region us-east-1

# List collaborators
aws bedrock-agent list-agent-collaborators \
  --agent-id 5VTIWONUMO --agent-version DRAFT --region us-east-1

# Test bulk operations
aws lambda invoke \
  --function-name scheduling-agent-bulk-ops-dev \
  --region us-east-1 \
  --payload '{"body": "{\"operation\": \"detect_conflicts\", \"project_ids\": [\"12345\"]}"}' \
  response.json

# Tail logs
aws logs tail /aws/lambda/scheduling-agent-bulk-ops-dev --follow

# Run verification
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
./scripts/verify_deployment.sh

# Run tests
python3 tests/comprehensive_test.py
```

### External Resources

- **AWS Bedrock Docs:** https://docs.aws.amazon.com/bedrock/
- **AWS Lambda Docs:** https://docs.aws.amazon.com/lambda/
- **AWS Connect Docs:** https://docs.aws.amazon.com/connect/
- **Anthropic Claude Docs:** https://docs.anthropic.com/

### Troubleshooting Steps

1. **Agent not responding?**
   - Check agent status: `aws bedrock-agent get-agent --agent-id 5VTIWONUMO --region us-east-1`
   - Verify collaborators: `aws bedrock-agent list-agent-collaborators --agent-id 5VTIWONUMO --agent-version DRAFT --region us-east-1`
   - Re-prepare agent: `aws bedrock-agent prepare-agent --agent-id 5VTIWONUMO --region us-east-1`

2. **Lambda errors?**
   - Check logs: `aws logs tail /aws/lambda/scheduling-agent-bulk-ops-dev --follow`
   - Verify permissions: Check IAM role has DynamoDB and Secrets Manager access
   - Test locally: Package and test Lambda function offline

3. **Permission errors?**
   - Verify IAM user/role has required permissions
   - Check model access: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess
   - Review `ENABLE_API_ACCESS.md` for API permission issues

4. **Need help?**
   - Check documentation in `docs/` folder
   - Review CloudWatch logs for errors
   - Run `./scripts/verify_deployment.sh` for diagnostics

---

## Next Steps for New Developer

### Week 1: Onboarding & Familiarization

1. **Setup Development Environment** (Day 1)
   - Configure AWS CLI with account 618048437522
   - Verify access to all AWS resources
   - Clone repository
   - Run verification scripts

2. **Test Existing System** (Day 1-2)
   - Test all 5 agents in AWS Console
   - Run comprehensive test suite (`tests/comprehensive_test.py`)
   - Test bulk operations Lambda function
   - Review Swagger UI documentation (`BULK_OPS_API_DOCS.html`)

3. **Review Documentation** (Day 2-3)
   - Read this DEVELOPER_HANDOVER.md thoroughly
   - Review DEPLOYMENT_STATUS.md for current state
   - Read BULK_SCHEDULING_DESIGN.md for bulk ops architecture
   - Skim Phase 2 and Phase 3 research documents

4. **Understand Architecture** (Day 3-5)
   - Review agent instructions in `infrastructure/agent_instructions/`
   - Understand OpenAPI schemas in `infrastructure/openapi_schemas/`
   - Review Lambda code in `lambda/bulk-operations/handler.py`
   - Understand multi-agent routing logic

### Week 2: Manual Configuration & Quick Wins

1. **Complete Coordinator Action Group Setup** (⏳ URGENT - Day 6)
   - Follow "Known Issues & Manual Steps" section above
   - Configure action group for agent QHUR9JP4GT via AWS Console
   - Test bulk operations end-to-end
   - **This unblocks bulk operations feature**

2. **Update Documentation** (Day 7-8)
   - Mark coordinator action group as complete
   - Update DEPLOYMENT_STATUS.md
   - Add any additional notes or findings
   - Archive outdated documentation

3. **Create Lambda Functions for Phase 1 Agents** (Day 9-10)
   - Start with scheduling Lambda (6 actions)
   - Reference existing code patterns from bulk-operations Lambda
   - Follow PF360 API patterns from current system

### Week 3+: Ongoing Development

1. **Phase 1 Completion:**
   - Implement 12 Lambda action handlers
   - Connect to PF360 API
   - End-to-end testing
   - Production deployment

2. **Phase 2 SMS (if required):**
   - Request phone number (2-4 weeks wait)
   - Implement SMS webhook Lambda
   - Configure two-way messaging
   - Test opt-in/opt-out flows

3. **Phase 3 IVR (if required):**
   - Request AWS Connect instance
   - Set up Amazon Lex integration
   - Configure contact flows
   - 12-14 week implementation timeline

---

## Appendix

### Agent IDs Quick Reference

| Agent | ID | Alias | ARN |
|-------|-----|-------|-----|
| Supervisor | `5VTIWONUMO` | `HH2U7EZXMW` | `arn:aws:bedrock:us-east-1:618048437522:agent/5VTIWONUMO` |
| Scheduling | `IX24FSMTQH` | `TYJRF3CJ7F` | `arn:aws:bedrock:us-east-1:618048437522:agent/IX24FSMTQH` |
| Information | `C9ANXRIO8Y` | `YVNFXEKPWO` | `arn:aws:bedrock:us-east-1:618048437522:agent/C9ANXRIO8Y` |
| Notes | `G5BVBYEPUM` | `F9QQNLZUW8` | `arn:aws:bedrock:us-east-1:618048437522:agent/G5BVBYEPUM` |
| Chitchat | `BIUW1ARHGL` | `THIPMPJCPI` | `arn:aws:bedrock:us-east-1:618048437522:agent/BIUW1ARHGL` |
| **Coordinator** | **`QHUR9JP4GT`** | - | `arn:aws:bedrock:us-east-1:618048437522:agent/QHUR9JP4GT` |

### Lambda Functions

| Function | ARN | Purpose |
|----------|-----|---------|
| `scheduling-agent-bulk-ops-dev` | `arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-bulk-ops-dev` | Bulk operations for coordinators |

### S3 Buckets

| Bucket | Purpose | ARN |
|--------|---------|-----|
| `scheduling-agent-schemas-dev-618048437522` | Agent OpenAPI schemas | `arn:aws:s3:::scheduling-agent-schemas-dev-618048437522` |
| `scheduling-agent-artifacts-dev` | Coordinator OpenAPI schemas | `arn:aws:s3:::scheduling-agent-artifacts-dev` |
| `projectsforce-terraform-state-618048437522` | Terraform state | `arn:aws:s3:::projectsforce-terraform-state-618048437522` |

### DynamoDB Tables

| Table | ARN | Purpose |
|-------|-----|---------|
| `terraform-lock` | `arn:aws:dynamodb:us-east-1:618048437522:table/terraform-lock` | Terraform state locking |
| `scheduling-agent-bulk-ops-tracking-dev` | `arn:aws:dynamodb:us-east-1:618048437522:table/scheduling-agent-bulk-ops-tracking-dev` | Bulk operations tracking |

---

**Document Version:** 1.0
**Last Updated:** October 13, 2025
**Next Review:** After coordinator action group completion
**Maintained By:** Development Team

---

## 🎉 Welcome Aboard!

You now have complete information to continue development of the AWS Bedrock Multi-Agent Scheduling System. The system is well-documented, tested, and ready for the next phase of implementation.

**Priority Tasks:**
1. ⏳ **URGENT:** Complete coordinator action group setup (see "Known Issues" section)
2. Implement Phase 1 Lambda functions (12 action handlers)
3. Consider Phase 2 SMS or Phase 3 IVR based on business priorities

Good luck! 🚀
