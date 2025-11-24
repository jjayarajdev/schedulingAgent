# Complete Deployment Guide for New AWS Environment

**Version 4.0 - Complete System Rewrite**
**Last Updated**: 2025-11-15

This guide provides step-by-step instructions to deploy the v4.0 scheduling agent system in a new AWS environment from scratch. The v4.0 system represents a complete architectural redesign focused on simplicity, cost efficiency, and automated deployment.

## Table of Contents
1. [What's New in v4.0](#whats-new-in-v40)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Detailed Deployment](#detailed-deployment)
5. [Testing](#testing)
6. [Verification](#verification)
7. [Configuration](#configuration)
8. [Troubleshooting](#troubleshooting)
9. [Cleanup](#cleanup)

---

## What's New in v4.0

### Major Changes from v3.x

**Removed Components:**
- **NO Terraform** - All infrastructure managed via AWS CLI
- **NO Step Functions** - Simplified to direct Lambda routing
- **NO React Frontend** - Replaced with lightweight HTML test UI
- **NO VPC** - Fully serverless architecture
- **NO Redis** - Session storage in DynamoDB

**New Architecture:**
- **4 Bedrock Agents** (down from 5):
  - Supervisor: GEMYQNPYB4
  - Scheduling: LMJI2V9E8Y
  - Information: VDWEVR6DJD
  - Chitchat: DIT6BVFDYW
- **3 Lambda Functions** (down from 7+):
  - pf-orchestrator (512MB) - Routing + session management
  - pf-scheduling-actions (1769MB) - 7 scheduling operations
  - pf-information-actions (1769MB) - Weather API integration
- **DynamoDB** - Session storage (pf-sessions-dev)
- **Hybrid Routing** - Direct agent calls + optional supervisor
- **Cost Optimized** - 94% reduction in operational costs

**Deployment Method:**
- **PRIMARY**: `./scripts/DEPLOY.sh` - Fully automated deployment (15-20 min)
- **CLEANUP**: `./scripts/CLEANUP.sh` - Complete resource removal (5 min)
- **VALIDATION**: `./scripts/VALIDATE.sh` - Deployment verification

### Cost Comparison

| Metric | v3.x | v4.0 | Savings |
|--------|------|------|---------|
| Monthly Cost (5K requests) | ~$150 | ~$8-11 | 94% |
| Per Request Cost | ~$0.03 | ~$0.0021 | 93% |
| Deployment Time | 45-60 min | 15-20 min | 67% |
| Components | 15+ | 8 | 47% |

---

## Prerequisites

### Required Tools

- **AWS CLI v2+** - For all AWS operations
- **Python 3.11** - For Lambda functions and testing
- **Bash shell** - For deployment scripts (Linux/macOS/WSL)
- **jq** - JSON processor (optional, for formatted output)

### AWS Account Requirements

- AWS Account with administrative access
- AWS Region: `us-east-1` (recommended)
- **Bedrock Model Access Required**:
  - Claude 3.5 Sonnet V2: `us.anthropic.claude-3-5-sonnet-20241022-v2:0`
  - Request access via AWS Console → Bedrock → Model Access

### Service Quotas

Verify sufficient quotas for:
- Bedrock Agents: 4+
- Lambda Functions: 3+
- Lambda Memory: 4GB+ total
- DynamoDB Tables: 1+
- IAM Roles: 5+
- API Gateway REST APIs: 1+

### ProjectForce API Credentials

You'll need:
- **Bearer Token** - API authentication token
- **Client ID** - ProjectForce client identifier
- **User ID** - ProjectForce user identifier

These will be stored securely in AWS Secrets Manager during deployment.

### Install Required Tools

#### AWS CLI v2
```bash
# Linux/macOS
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify installation
aws --version  # Should show aws-cli/2.x.x
```

#### Python 3.11
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3.11 python3.11-venv

# macOS (using Homebrew)
brew install python@3.11

# Verify installation
python3.11 --version
```

#### jq (Optional but Recommended)
```bash
# Ubuntu/Debian
sudo apt install jq

# macOS
brew install jq
```

### Configure AWS Credentials

```bash
# Configure AWS CLI with your credentials
aws configure

# Enter when prompted:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region: us-east-1
# - Default output format: json

# Verify configuration
aws sts get-caller-identity

# Expected output:
# {
#   "UserId": "...",
#   "Account": "123456789012",
#   "Arn": "arn:aws:iam::123456789012:user/your-user"
# }
```

### Enable Bedrock Model Access

1. Go to AWS Console → Bedrock → Model Access
2. Click "Modify model access" or "Request access"
3. Select: **Claude 3.5 Sonnet v2**
4. Submit request
5. Wait for approval (usually immediate to 5 minutes)
6. Verify access:

```bash
aws bedrock list-foundation-models --region us-east-1 \
  --by-provider anthropic \
  --query 'modelSummaries[?contains(modelId, `claude-3-5-sonnet-20241022-v2`)]'

# Should return model details if access is granted
```

---

## Quick Start

For experienced users who want to deploy immediately:

```bash
# 1. Clone repository
git clone https://github.com/your-org/projectsforce.git
cd projectsforce/bedrock

# 2. Run deployment script
./scripts/DEPLOY.sh

# 3. Follow prompts to enter:
#    - ProjectForce Bearer Token
#    - ProjectForce Client ID
#    - ProjectForce User ID

# 4. Wait 15-20 minutes for deployment to complete

# 5. Test the deployment
./scripts/VALIDATE.sh

# 6. Start test UI
cd testing/ui
python3 -m http.server 8000
# Open http://localhost:8000 in browser
```

That's it! For detailed step-by-step instructions, continue reading.

---

## Detailed Deployment

### Step 1: Clone Repository

```bash
# Navigate to your workspace directory
cd ~/workspaces

# Clone the repository
git clone https://github.com/your-org/projectsforce.git

# Navigate to bedrock directory
cd projectsforce/bedrock

# Verify you're in the correct directory
pwd
# Should show: /path/to/projectsforce/bedrock

# Check deployment script exists
ls -l scripts/DEPLOY.sh
```

### Step 2: Prepare Credentials

Before running deployment, gather your ProjectForce API credentials:

1. **Bearer Token**: Your ProjectForce API authentication token
2. **Client ID**: Your ProjectForce client identifier
3. **User ID**: Your ProjectForce user identifier

These will be requested interactively during deployment and stored securely in AWS Secrets Manager.

**Important**: Never commit these credentials to version control!

### Step 3: Run Deployment Script

```bash
# Make script executable (if needed)
chmod +x scripts/DEPLOY.sh

# Run deployment
./scripts/DEPLOY.sh

# The script will:
# 1. Verify AWS credentials and permissions
# 2. Check Bedrock model access
# 3. Request ProjectForce credentials (interactive)
# 4. Create AWS Secrets Manager secret
# 5. Deploy 3 Lambda functions
# 6. Deploy 4 Bedrock agents
# 7. Create DynamoDB table
# 8. Set up API Gateway
# 9. Configure IAM roles and permissions
# 10. Validate deployment
```

### Step 4: Deployment Progress

The deployment script provides real-time progress updates:

```
========================================
ProjectForce Bedrock v4.0 Deployment
========================================

[1/10] Verifying AWS credentials...
✓ AWS credentials valid (Account: 123456789012)

[2/10] Checking Bedrock model access...
✓ Claude 3.5 Sonnet V2 access confirmed

[3/10] Configuring ProjectForce credentials...
Enter ProjectForce Bearer Token: ****
Enter ProjectForce Client ID: ****
Enter ProjectForce User ID: ****
✓ Credentials stored in Secrets Manager

[4/10] Creating DynamoDB table...
✓ Table 'pf-sessions-dev' created

[5/10] Deploying Lambda functions...
✓ pf-orchestrator deployed (512MB)
✓ pf-scheduling-actions deployed (1769MB)
✓ pf-information-actions deployed (1769MB)

[6/10] Creating IAM roles...
✓ Lambda execution roles created
✓ Bedrock agent roles created

[7/10] Deploying Bedrock agents...
✓ Supervisor agent created (GEMYQNPYB4)
✓ Scheduling agent created (LMJI2V9E8Y)
✓ Information agent created (VDWEVR6DJD)
✓ Chitchat agent created (DIT6BVFDYW)

[8/10] Configuring agent action groups...
✓ All action groups configured

[9/10] Creating API Gateway...
✓ REST API endpoint created
✓ URL: https://abc123.execute-api.us-east-1.amazonaws.com/dev

[10/10] Validating deployment...
✓ All components validated

========================================
Deployment Complete!
Duration: 18 minutes
========================================

Next steps:
1. Run validation: ./scripts/VALIDATE.sh
2. Test UI: cd testing/ui && python3 -m http.server 8000
3. Run tests: ./testing/run_test_formatted.sh test_suite_1_basic_workflow.sh
```

**Expected Duration**: 15-20 minutes

### Step 5: Post-Deployment Validation

After deployment completes, run the validation script:

```bash
# Run comprehensive validation
./scripts/VALIDATE.sh

# Expected output:
# ✓ DynamoDB table exists and accessible
# ✓ All 3 Lambda functions deployed
# ✓ All 4 Bedrock agents created
# ✓ API Gateway endpoint responding
# ✓ IAM roles configured correctly
# ✓ Secrets Manager secret exists
#
# All validation checks passed!
```

---

## Testing

### Test UI (Simple HTML Interface)

The v4.0 system includes a simple HTML test interface:

```bash
# Navigate to test UI directory
cd testing/ui

# Start local web server
python3 -m http.server 8000

# Expected output:
# Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...

# Open in browser:
# http://localhost:8000
```

**UI Features:**
- Simple chat interface
- Session ID management
- Real-time response display
- Request/response logging
- Agent routing visualization

**Test Queries:**
```
1. "Show me all my projects"
   → Information agent

2. "Schedule project PRJ-78945 for Monday at 10 AM"
   → Scheduling agent

3. "What's the weather like today?"
   → Information agent (weather API)

4. "Hello, how are you?"
   → Chitchat agent

5. "What projects do I have in progress?"
   → Information agent (filtered query)
```

### Formatted Test Suites

The v4.0 system includes 5 comprehensive test suites with formatted output:

```bash
# Navigate to testing directory
cd testing

# Run basic workflow tests
./run_test_formatted.sh test_suite_1_basic_workflow.sh

# Expected output:
# ========================================
# Test Suite 1: Basic Workflow
# ========================================
#
# [1/5] Information Query - List Projects
# ✓ PASSED (2.3s)
# Response: Found 12 active projects
#
# [2/5] Scheduling Query - Schedule Project
# ✓ PASSED (3.1s)
# Response: Project PRJ-78945 scheduled for Monday 10:00 AM
#
# [3/5] Session Continuity
# ✓ PASSED (1.8s)
# Response: Session context preserved
#
# [4/5] Error Handling
# ✓ PASSED (1.2s)
# Response: Invalid project ID handled gracefully
#
# [5/5] Agent Routing
# ✓ PASSED (2.5s)
# Response: Correct agent selected
#
# ========================================
# Results: 5/5 PASSED (100%)
# Duration: 11.2 seconds
# ========================================
```

**Available Test Suites:**

1. **test_suite_1_basic_workflow.sh** - Core functionality
2. **test_suite_2_context_resolution.sh** - Session management
3. **test_suite_3_filtering.sh** - Project filtering operations
4. **test_suite_4_chitchat.sh** - Conversational interactions
5. **test_suite_5_scheduling.sh** - Complex scheduling scenarios

**Run All Suites:**
```bash
# Run all test suites sequentially
for suite in test_suite_*.sh; do
  ./run_test_formatted.sh "$suite"
done

# Or use the convenience script
./run_all_tests.sh
```

### Manual Testing with curl

```bash
# Get API Gateway endpoint
ENDPOINT=$(aws apigateway get-rest-apis \
  --query 'items[?name==`pf-api-dev`].id' \
  --output text)
API_URL="https://${ENDPOINT}.execute-api.us-east-1.amazonaws.com/dev"

# Test orchestrator endpoint
curl -X POST "${API_URL}/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me all my projects",
    "sessionId": "test-session-123"
  }' | jq .

# Expected response:
# {
#   "response": "I found 12 active projects in your account...",
#   "agent": "information",
#   "sessionId": "test-session-123",
#   "timestamp": "2025-11-15T10:30:45Z"
# }
```

---

## Verification

### 1. AWS Console Verification

#### Bedrock Agents
```
Console → Bedrock → Agents
Expected: 4 agents in "Prepared" status
- pf-supervisor-agent-dev (GEMYQNPYB4)
- pf-scheduling-agent-dev (LMJI2V9E8Y)
- pf-information-agent-dev (VDWEVR6DJD)
- pf-chitchat-agent-dev (DIT6BVFDYW)
```

#### Lambda Functions
```
Console → Lambda → Functions
Expected: 3 functions
- pf-orchestrator (512 MB, Runtime: Python 3.11)
- pf-scheduling-actions (1769 MB, Runtime: Python 3.11)
- pf-information-actions (1769 MB, Runtime: Python 3.11)
```

#### DynamoDB
```
Console → DynamoDB → Tables
Expected: 1 table
- pf-sessions-dev
  - Partition key: sessionId (String)
  - Sort key: timestamp (Number)
  - Billing mode: PAY_PER_REQUEST
```

#### API Gateway
```
Console → API Gateway → APIs
Expected: 1 REST API
- pf-api-dev
  - Stage: dev
  - Endpoint: Regional
  - Resources: /chat (POST)
```

#### Secrets Manager
```
Console → Secrets Manager → Secrets
Expected: 1 secret
- projectforce/api/credentials
  - Contains: bearerToken, clientId, userId
```

### 2. CLI Verification

```bash
# Verify all components at once
./scripts/VALIDATE.sh

# Or verify individually:

# Check Lambda functions
aws lambda list-functions \
  --query 'Functions[?starts_with(FunctionName, `pf-`)].FunctionName' \
  --output table

# Check Bedrock agents
aws bedrock-agent list-agents \
  --query 'agentSummaries[?starts_with(agentName, `pf-`)].{Name:agentName,ID:agentId,Status:agentStatus}' \
  --output table

# Check DynamoDB table
aws dynamodb describe-table \
  --table-name pf-sessions-dev \
  --query 'Table.{Name:TableName,Status:TableStatus,ItemCount:ItemCount}' \
  --output table

# Check API Gateway
aws apigateway get-rest-apis \
  --query 'items[?name==`pf-api-dev`].{Name:name,ID:id,Created:createdDate}' \
  --output table
```

### 3. End-to-End Test

```bash
# Navigate to testing directory
cd testing

# Run comprehensive end-to-end test
./run_test_formatted.sh test_suite_1_basic_workflow.sh

# Should show 100% pass rate
```

### 4. CloudWatch Logs Check

```bash
# Check orchestrator logs
aws logs tail /aws/lambda/pf-orchestrator --follow

# Check scheduling actions logs
aws logs tail /aws/lambda/pf-scheduling-actions --follow

# Check information actions logs
aws logs tail /aws/lambda/pf-information-actions --follow

# Look for:
# - No ERROR level messages
# - Successful agent invocations
# - Proper request/response flow
```

---

## Configuration

### Environment Variables

The deployment uses these configurations:

```bash
# Region
AWS_REGION=us-east-1

# Project prefix
PROJECT_PREFIX=pf

# Environment
ENVIRONMENT=dev

# Bedrock model
BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0

# DynamoDB table
DYNAMODB_TABLE=pf-sessions-dev

# Agent alias (for all agents)
AGENT_ALIAS_ID=TSTALIASID
```

### Routing Configuration

The v4.0 system supports two routing modes:

#### 1. Direct Agent Routing (Default)
```bash
USE_SUPERVISOR=false
ALLOW_DIRECT_LAMBDA=true
```

**Behavior:**
- Orchestrator analyzes query intent
- Routes directly to appropriate agent
- Faster response time
- Lower cost per request

#### 2. Supervisor Mode (Optional)
```bash
USE_SUPERVISOR=true
ALLOW_DIRECT_LAMBDA=false
```

**Behavior:**
- All queries go through Supervisor agent
- Supervisor delegates to collaborators
- Better for complex multi-turn conversations
- Slightly higher latency

**Switch Modes:**
```bash
# Enable supervisor mode
./scripts/SETUP_COLLABORATION.sh

# This will:
# - Configure supervisor agent collaboration settings
# - Update orchestrator to use supervisor routing
# - Validate configuration
```

### Session Management

Sessions are stored in DynamoDB with automatic expiration:

```bash
# Session TTL: 24 hours
# Auto-cleanup: 48 hours (DynamoDB TTL)

# View active sessions
aws dynamodb scan \
  --table-name pf-sessions-dev \
  --projection-expression "sessionId,userId,lastActivity" \
  --output table

# Clear specific session
aws dynamodb delete-item \
  --table-name pf-sessions-dev \
  --key '{"sessionId": {"S": "your-session-id"}}'
```

### Lambda Configuration

Each Lambda function has specific memory and timeout settings:

```bash
# pf-orchestrator
Memory: 512 MB
Timeout: 60 seconds
Purpose: Request routing + session management

# pf-scheduling-actions
Memory: 1769 MB
Timeout: 300 seconds
Purpose: 7 scheduling operations (list, create, update, delete, etc.)

# pf-information-actions
Memory: 1769 MB
Timeout: 300 seconds
Purpose: Weather API integration + information retrieval
```

**Update Configuration:**
```bash
# Increase orchestrator memory (if needed)
aws lambda update-function-configuration \
  --function-name pf-orchestrator \
  --memory-size 1024 \
  --region us-east-1

# Increase timeout (if needed)
aws lambda update-function-configuration \
  --function-name pf-scheduling-actions \
  --timeout 600 \
  --region us-east-1
```

### Agent Configuration

All agents use the TSTALIASID alias, which points to the latest DRAFT version:

```bash
# View agent details
aws bedrock-agent get-agent \
  --agent-id GEMYQNPYB4 \
  --region us-east-1

# View agent alias
aws bedrock-agent get-agent-alias \
  --agent-id GEMYQNPYB4 \
  --agent-alias-id TSTALIASID \
  --region us-east-1

# Update agent instructions (then prepare)
aws bedrock-agent update-agent \
  --agent-id GEMYQNPYB4 \
  --agent-name pf-supervisor-agent-dev \
  --instruction "$(cat new_instructions.txt)" \
  --region us-east-1

aws bedrock-agent prepare-agent \
  --agent-id GEMYQNPYB4 \
  --region us-east-1
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: Deployment Script Fails - AWS Credentials

**Error:**
```
Unable to locate credentials. You can configure credentials by running "aws configure".
```

**Solution:**
```bash
# Configure AWS CLI
aws configure

# Enter your credentials when prompted
# Verify configuration
aws sts get-caller-identity
```

#### Issue 2: Bedrock Model Access Denied

**Error:**
```
AccessDeniedException: You don't have access to the model with the specified model ID.
```

**Solution:**
```bash
# 1. Go to AWS Console → Bedrock → Model Access
# 2. Click "Modify model access"
# 3. Select Claude 3.5 Sonnet v2
# 4. Submit request
# 5. Wait for approval (5-10 minutes)

# Verify access
aws bedrock list-foundation-models \
  --region us-east-1 \
  --by-provider anthropic \
  --query 'modelSummaries[?contains(modelId, `claude-3-5-sonnet-20241022-v2`)]'
```

#### Issue 3: Lambda Deployment Timeout

**Error:**
```
Error: Function deployment timed out after 5 minutes
```

**Solution:**
```bash
# Check Lambda creation status
aws lambda get-function \
  --function-name pf-orchestrator \
  --region us-east-1

# If function exists but deployment incomplete, update code
cd lambda/orchestrator
zip -r ../orchestrator.zip .
cd ..

aws lambda update-function-code \
  --function-name pf-orchestrator \
  --zip-file fileb://orchestrator.zip \
  --region us-east-1
```

#### Issue 4: Agent Creation Fails

**Error:**
```
Error: Agent creation failed - resource limit exceeded
```

**Solution:**
```bash
# Check existing agents
aws bedrock-agent list-agents --region us-east-1

# If you have old agents, delete them
aws bedrock-agent delete-agent \
  --agent-id OLD_AGENT_ID \
  --skip-resource-in-use-check \
  --region us-east-1

# Retry deployment
./scripts/DEPLOY.sh
```

#### Issue 5: DynamoDB Permission Denied

**Error:**
```
AccessDeniedException: User is not authorized to perform: dynamodb:PutItem
```

**Solution:**
```bash
# Check IAM role permissions
aws iam get-role-policy \
  --role-name pf-orchestrator-role \
  --policy-name pf-orchestrator-policy

# If missing DynamoDB permissions, update policy
aws iam put-role-policy \
  --role-name pf-orchestrator-role \
  --policy-name pf-orchestrator-policy \
  --policy-document file://policies/orchestrator-policy.json
```

#### Issue 6: API Gateway 403 Forbidden

**Error:**
```
{"message":"Forbidden"}
```

**Solution:**
```bash
# Check API Gateway resource policy
aws apigateway get-rest-api \
  --rest-api-id YOUR_API_ID \
  --region us-east-1

# Verify Lambda integration
aws apigateway get-integration \
  --rest-api-id YOUR_API_ID \
  --resource-id YOUR_RESOURCE_ID \
  --http-method POST \
  --region us-east-1

# Re-deploy API
aws apigateway create-deployment \
  --rest-api-id YOUR_API_ID \
  --stage-name dev \
  --region us-east-1
```

#### Issue 7: Session Not Persisting

**Error:**
Context not maintained between requests

**Solution:**
```bash
# Check DynamoDB table
aws dynamodb describe-table \
  --table-name pf-sessions-dev \
  --region us-east-1

# Test session write
aws dynamodb put-item \
  --table-name pf-sessions-dev \
  --item '{
    "sessionId": {"S": "test-123"},
    "userId": {"S": "test-user"},
    "context": {"S": "{}"},
    "timestamp": {"N": "'$(date +%s)'"}
  }' \
  --region us-east-1

# Test session read
aws dynamodb get-item \
  --table-name pf-sessions-dev \
  --key '{"sessionId": {"S": "test-123"}}' \
  --region us-east-1
```

#### Issue 8: High Lambda Costs

**Symptom:**
Unexpected AWS charges from Lambda

**Solution:**
```bash
# Check Lambda invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=pf-orchestrator \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum \
  --region us-east-1

# Check for error loops
aws logs filter-log-events \
  --log-group-name /aws/lambda/pf-orchestrator \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '1 day ago' +%s)000 \
  --region us-east-1

# If found, fix errors and redeploy
```

### Getting Help

1. **Check CloudWatch Logs**
   ```bash
   aws logs tail /aws/lambda/pf-orchestrator --follow
   ```

2. **Run Validation Script**
   ```bash
   ./scripts/VALIDATE.sh
   ```

3. **Review Deployment Logs**
   ```bash
   cat deployment.log  # Created by DEPLOY.sh
   ```

4. **Test Individual Components**
   ```bash
   # Test Lambda directly
   aws lambda invoke \
     --function-name pf-orchestrator \
     --payload '{"test": true}' \
     response.json

   cat response.json
   ```

---

## Cleanup

### Complete Resource Removal

To remove all deployed resources:

```bash
# Run cleanup script
./scripts/CLEANUP.sh

# The script will:
# 1. Delete API Gateway
# 2. Delete Lambda functions
# 3. Delete Bedrock agents
# 4. Delete DynamoDB table
# 5. Delete IAM roles
# 6. Delete Secrets Manager secret
# 7. Delete CloudWatch log groups

# Expected duration: 5 minutes
```

**Output:**
```
========================================
ProjectForce Bedrock v4.0 Cleanup
========================================

[1/7] Deleting API Gateway...
✓ API Gateway deleted

[2/7] Deleting Lambda functions...
✓ pf-orchestrator deleted
✓ pf-scheduling-actions deleted
✓ pf-information-actions deleted

[3/7] Deleting Bedrock agents...
✓ Supervisor agent deleted
✓ Scheduling agent deleted
✓ Information agent deleted
✓ Chitchat agent deleted

[4/7] Deleting DynamoDB table...
✓ pf-sessions-dev deleted

[5/7] Deleting IAM roles...
✓ All IAM roles deleted

[6/7] Deleting Secrets Manager secret...
✓ projectforce/api/credentials deleted

[7/7] Deleting CloudWatch log groups...
✓ All log groups deleted

========================================
Cleanup Complete!
All resources removed.
========================================
```

### Partial Cleanup

If you want to remove specific components only:

```bash
# Delete only Lambda functions
aws lambda delete-function --function-name pf-orchestrator
aws lambda delete-function --function-name pf-scheduling-actions
aws lambda delete-function --function-name pf-information-actions

# Delete only Bedrock agents
aws bedrock-agent delete-agent --agent-id GEMYQNPYB4 --skip-resource-in-use-check
aws bedrock-agent delete-agent --agent-id LMJI2V9E8Y --skip-resource-in-use-check
aws bedrock-agent delete-agent --agent-id VDWEVR6DJD --skip-resource-in-use-check
aws bedrock-agent delete-agent --agent-id DIT6BVFDYW --skip-resource-in-use-check

# Delete only DynamoDB table
aws dynamodb delete-table --table-name pf-sessions-dev
```

### Verify Cleanup

```bash
# Check no Lambda functions remain
aws lambda list-functions \
  --query 'Functions[?starts_with(FunctionName, `pf-`)]' \
  --output table

# Check no Bedrock agents remain
aws bedrock-agent list-agents \
  --query 'agentSummaries[?starts_with(agentName, `pf-`)]' \
  --output table

# Check no DynamoDB tables remain
aws dynamodb list-tables \
  --query 'TableNames[?starts_with(@, `pf-`)]' \
  --output table

# All should return empty results
```

---

## Production Considerations

### Security Hardening

1. **API Gateway Authentication**
   ```bash
   # Add API key requirement
   aws apigateway create-api-key \
     --name pf-api-key-prod \
     --enabled

   # Create usage plan
   aws apigateway create-usage-plan \
     --name pf-usage-plan-prod \
     --throttle burstLimit=100,rateLimit=50
   ```

2. **Secrets Rotation**
   ```bash
   # Enable automatic rotation for ProjectForce credentials
   aws secretsmanager rotate-secret \
     --secret-id projectforce/api/credentials \
     --rotation-lambda-arn arn:aws:lambda:us-east-1:ACCOUNT:function:rotate-secret
   ```

3. **Encryption at Rest**
   ```bash
   # Enable DynamoDB encryption
   aws dynamodb update-table \
     --table-name pf-sessions-prod \
     --sse-specification Enabled=true,SSEType=KMS
   ```

### Monitoring and Alerts

1. **CloudWatch Dashboards**
   ```bash
   # Create dashboard for key metrics
   aws cloudwatch put-dashboard \
     --dashboard-name pf-monitoring-prod \
     --dashboard-body file://monitoring/dashboard.json
   ```

2. **Alarms**
   ```bash
   # Alert on Lambda errors
   aws cloudwatch put-metric-alarm \
     --alarm-name pf-orchestrator-errors \
     --alarm-description "Alert on orchestrator errors" \
     --metric-name Errors \
     --namespace AWS/Lambda \
     --statistic Sum \
     --period 300 \
     --threshold 10 \
     --comparison-operator GreaterThanThreshold \
     --dimensions Name=FunctionName,Value=pf-orchestrator
   ```

3. **Cost Alerts**
   ```bash
   # Set budget alert
   aws budgets create-budget \
     --account-id ACCOUNT_ID \
     --budget file://monitoring/budget.json \
     --notifications-with-subscribers file://monitoring/notifications.json
   ```

### Scalability

1. **Lambda Concurrency**
   ```bash
   # Reserve concurrency for critical functions
   aws lambda put-function-concurrency \
     --function-name pf-orchestrator \
     --reserved-concurrent-executions 100
   ```

2. **DynamoDB Capacity**
   ```bash
   # Enable auto-scaling (if switching from on-demand)
   aws application-autoscaling register-scalable-target \
     --service-namespace dynamodb \
     --resource-id table/pf-sessions-prod \
     --scalable-dimension dynamodb:table:ReadCapacityUnits \
     --min-capacity 5 \
     --max-capacity 100
   ```

3. **API Gateway Rate Limiting**
   ```bash
   # Configure throttling
   aws apigateway update-stage \
     --rest-api-id API_ID \
     --stage-name prod \
     --patch-operations \
       op=replace,path=/throttle/rateLimit,value=1000 \
       op=replace,path=/throttle/burstLimit,value=2000
   ```

### Backup and Recovery

1. **DynamoDB Backups**
   ```bash
   # Enable point-in-time recovery
   aws dynamodb update-continuous-backups \
     --table-name pf-sessions-prod \
     --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true

   # Create on-demand backup
   aws dynamodb create-backup \
     --table-name pf-sessions-prod \
     --backup-name pf-sessions-prod-$(date +%Y%m%d)
   ```

2. **Lambda Versioning**
   ```bash
   # Publish function version
   aws lambda publish-version \
     --function-name pf-orchestrator \
     --description "Production release v4.0"

   # Create alias pointing to version
   aws lambda create-alias \
     --function-name pf-orchestrator \
     --name PROD \
     --function-version 1
   ```

3. **Configuration Backups**
   ```bash
   # Export all resource configurations
   ./scripts/export_configuration.sh > config_backup_$(date +%Y%m%d).json
   ```

### Multi-Region Deployment

For high availability, deploy to multiple regions:

```bash
# Deploy to us-west-2
export AWS_REGION=us-west-2
./scripts/DEPLOY.sh

# Update Route 53 for failover
aws route53 create-health-check \
  --caller-reference $(date +%s) \
  --health-check-config file://route53/health-check.json

# Configure failover routing
aws route53 change-resource-record-sets \
  --hosted-zone-id ZONE_ID \
  --change-batch file://route53/failover-routing.json
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client (Browser/API)                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway (REST)                          │
│                  /chat POST endpoint                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           Lambda: pf-orchestrator (512MB)                        │
│           - Request routing                                      │
│           - Session management                                   │
│           - Intent classification                                │
└──────────┬──────────────────────────────────────┬───────────────┘
           │                                       │
           ▼                                       ▼
┌──────────────────────┐              ┌──────────────────────────┐
│   DynamoDB           │              │   Bedrock Agents (4)     │
│   pf-sessions-dev    │              │   - Supervisor           │
│   - Session storage  │              │   - Scheduling           │
│   - Context mgmt     │              │   - Information          │
└──────────────────────┘              │   - Chitchat             │
                                      └──────────┬───────────────┘
                                                 │
                         ┌───────────────────────┼───────────────┐
                         │                       │               │
                         ▼                       ▼               ▼
              ┌──────────────────┐   ┌─────────────────┐   ┌────────┐
              │ Lambda:          │   │ Lambda:         │   │Secrets │
              │ pf-scheduling    │   │ pf-information  │   │Manager │
              │ -actions         │   │ -actions        │   │        │
              │ (1769MB)         │   │ (1769MB)        │   │API     │
              │                  │   │                 │   │Creds   │
              │ 7 operations:    │   │ - Weather API   │   └────────┘
              │ - list           │   │ - Project info  │
              │ - create         │   │ - Filtering     │
              │ - update         │   └─────────────────┘
              │ - delete         │
              │ - check          │
              │ - available      │
              │ - conflict       │
              └──────────────────┘
```

---

## Cost Breakdown

### Monthly Cost Estimate (5,000 requests/month)

| Service | Usage | Cost |
|---------|-------|------|
| Bedrock Agents (4) | 5K invocations | $4.00 |
| Lambda - Orchestrator | 5K invocations, 512MB | $0.50 |
| Lambda - Scheduling | 2K invocations, 1769MB | $1.50 |
| Lambda - Information | 3K invocations, 1769MB | $2.00 |
| DynamoDB | 10K writes, 10K reads | $0.50 |
| API Gateway | 5K requests | $0.02 |
| CloudWatch Logs | 1GB/month | $0.50 |
| Secrets Manager | 1 secret | $0.40 |
| **Total** | | **~$9.42/month** |

### Per Request Cost

```
Average cost per request: $0.0021
Breakdown:
- Bedrock agent: $0.0008
- Lambda execution: $0.0009
- DynamoDB ops: $0.0002
- Other services: $0.0002
```

### Cost Optimization Tips

1. **Use reserved concurrency** for predictable workloads
2. **Enable DynamoDB auto-scaling** for variable traffic
3. **Implement caching** to reduce Lambda invocations
4. **Archive old CloudWatch logs** to S3 Glacier
5. **Use Lambda ARM architecture** for 20% cost reduction

---

## Deployment Checklist

Use this checklist to track deployment progress:

### Pre-Deployment
- [ ] AWS CLI v2+ installed
- [ ] Python 3.11 installed
- [ ] AWS credentials configured
- [ ] Bedrock model access granted (Claude 3.5 Sonnet V2)
- [ ] ProjectForce API credentials ready
- [ ] Git repository cloned

### Deployment
- [ ] Ran `./scripts/DEPLOY.sh`
- [ ] Entered ProjectForce credentials
- [ ] Deployment completed without errors
- [ ] Received API Gateway endpoint URL

### Validation
- [ ] Ran `./scripts/VALIDATE.sh`
- [ ] All 4 Bedrock agents created
- [ ] All 3 Lambda functions deployed
- [ ] DynamoDB table exists
- [ ] API Gateway responding
- [ ] Secrets Manager secret created

### Testing
- [ ] Test UI accessible (http://localhost:8000)
- [ ] Basic workflow test passed
- [ ] Context resolution test passed
- [ ] Filtering test passed
- [ ] Chitchat test passed
- [ ] Scheduling test passed

### Verification
- [ ] Checked CloudWatch logs (no errors)
- [ ] Verified session persistence
- [ ] Tested all 4 agent types
- [ ] Confirmed hybrid routing works
- [ ] API Gateway endpoint responding

### Optional
- [ ] Set up CloudWatch dashboards
- [ ] Configured alarms
- [ ] Enabled DynamoDB backups
- [ ] Set up cost alerts
- [ ] Documented custom configurations

---

## Support and Resources

### Documentation

- [DEPLOY.sh Script](../scripts/DEPLOY.sh) - Main deployment script
- [CLEANUP.sh Script](../scripts/CLEANUP.sh) - Resource cleanup script
- [VALIDATE.sh Script](../scripts/VALIDATE.sh) - Deployment validation
- [Test Suites](../testing/) - Comprehensive test coverage
- [Lambda Functions](../lambda/) - Function source code
- [Agent Instructions](../agents/) - Bedrock agent configurations

### AWS Console Links (us-east-1)

- [Bedrock Agents](https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents)
- [Lambda Functions](https://console.aws.amazon.com/lambda/home?region=us-east-1#/functions)
- [DynamoDB Tables](https://console.aws.amazon.com/dynamodbv2/home?region=us-east-1#tables)
- [API Gateway](https://console.aws.amazon.com/apigateway/home?region=us-east-1#/apis)
- [Secrets Manager](https://console.aws.amazon.com/secretsmanager/home?region=us-east-1#!/listSecrets)
- [CloudWatch Logs](https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups)

### CLI Commands Quick Reference

```bash
# Deploy
./scripts/DEPLOY.sh

# Validate
./scripts/VALIDATE.sh

# Test
cd testing/ui && python3 -m http.server 8000

# Test suites
./testing/run_test_formatted.sh test_suite_1_basic_workflow.sh

# Cleanup
./scripts/CLEANUP.sh

# View logs
aws logs tail /aws/lambda/pf-orchestrator --follow

# Check agents
aws bedrock-agent list-agents --region us-east-1

# Check Lambda
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `pf-`)]'
```

---

## Deployment Time Estimates

| Phase | Duration | Notes |
|-------|----------|-------|
| Prerequisites | One-time | AWS CLI, Python, credentials |
| Main Deployment | 15-20 min | Automated via DEPLOY.sh |
| Validation | 2-3 min | Automated via VALIDATE.sh |
| Testing | 5-10 min | All test suites |
| **Total** | **~20-25 min** | Excluding prerequisites |

---

## Success Criteria

Deployment is successful when:

1. ✓ All AWS credentials validated
2. ✓ Bedrock model access confirmed
3. ✓ All 4 Bedrock agents created and prepared
4. ✓ All 3 Lambda functions deployed
5. ✓ DynamoDB table created and accessible
6. ✓ API Gateway endpoint responding
7. ✓ Secrets Manager secret created
8. ✓ All IAM roles configured
9. ✓ VALIDATE.sh passes 100%
10. ✓ Test UI accessible and functional
11. ✓ All test suites pass
12. ✓ No errors in CloudWatch logs

---

## Version Information

- **Version**: 4.0
- **Last Updated**: 2025-11-15
- **AWS CLI Version**: 2.x+
- **Python Version**: 3.11
- **Bedrock Model**: Claude 3.5 Sonnet V2 (us.anthropic.claude-3-5-sonnet-20241022-v2:0)
- **AWS Region**: us-east-1 (primary)
- **Deployment Method**: Automated bash scripts (NO Terraform)
- **Architecture**: Serverless (NO VPC)
- **Frontend**: Simple HTML UI (NO React)
- **Session Storage**: DynamoDB (NO Redis)

---

## What's Removed from v3.x

For reference, here's what was removed in the v4.0 rewrite:

### Removed Infrastructure
- ❌ Terraform - Replaced with AWS CLI scripts
- ❌ Step Functions - Simplified to direct routing
- ❌ VPC deployment - Now fully serverless
- ❌ Redis/ElastiCache - Using DynamoDB instead
- ❌ 5th agent (Notes) - Consolidated to 4 agents

### Removed Frontend
- ❌ React application - Replaced with simple HTML UI
- ❌ Node.js server - Using Python SimpleHTTPServer
- ❌ Complex build process - No build step needed

### Removed Complexity
- ❌ Multi-step state machines - Direct Lambda calls
- ❌ Query router Lambda - Integrated into orchestrator
- ❌ Filter projects Lambda - Integrated into actions
- ❌ Weather evaluator Lambda - Integrated into information actions
- ❌ Separate notification agent - Merged into scheduling

### Cost Savings
- 💰 94% reduction in monthly costs
- 💰 93% reduction in per-request costs
- ⏱️ 67% reduction in deployment time
- 🔧 47% fewer components to manage

---

**End of Deployment Guide**

For questions or issues, refer to the [Troubleshooting](#troubleshooting) section or check CloudWatch Logs for detailed error messages.

To get started immediately, run: `./scripts/DEPLOY.sh`
