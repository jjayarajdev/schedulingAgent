# ProjectForce Scheduling Agent - Deployment Guide

## Overview
This guide documents the **proven deployment workflow** for the ProjectForce 4-agent scheduling system. This is the workflow you've been using successfully.

**System Architecture**:
- **4 Bedrock Agents**: Supervisor, SchedulingAgent, pf-information, pf-chitchat
- **2 Lambda Functions**: pf-scheduling-actions, pf-information-actions
- **1 DynamoDB Table**: pf-sessions-dev
- **API Integration**: ProjectForce Dashboard API

---

## Quick Start (TL;DR)

For a new environment, run these 3 commands:

```bash
# 1. Deploy everything
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/scripts
./DEPLOY.sh

# 2. Setup collaboration (after creating v1 aliases in AWS Console - see Step 5)
./SETUP_COLLABORATION.sh

# 3. Test with UI
cd ../testing/ui
open test_ui.html
```

**Total time**: ~20 minutes (including manual alias creation)

---

## Prerequisites

### 1. Required Software (Minimal)

| Tool | Purpose | Check if Installed | Installation |
|------|---------|-------------------|--------------|
| **AWS CLI** | Deploy to AWS | `aws --version` | [aws.amazon.com/cli](https://aws.amazon.com/cli/) |
| **Python 3** | Package Lambda functions | `python3 --version` | Pre-installed on macOS/Linux |
| **pip3** | Install Python packages | `pip3 --version` | Comes with Python 3 |
| **zip** | Package deployments | `which zip` | Pre-installed on macOS/Linux |
| **jq** | Parse JSON (for collaboration setup) | `jq --version` | `brew install jq` (macOS)<br>`sudo apt install jq` (Linux) |

**Not Required**: Terraform, Node.js, Docker, or any other tools

### 2. Verify Prerequisites

Run this quick check:

```bash
# Check all prerequisites at once
echo "Checking prerequisites..."
command -v aws &> /dev/null && echo "✅ AWS CLI" || echo "❌ AWS CLI missing"
command -v python3 &> /dev/null && echo "✅ Python 3" || echo "❌ Python 3 missing"
command -v pip3 &> /dev/null && echo "✅ pip3" || echo "❌ pip3 missing"
command -v zip &> /dev/null && echo "✅ zip" || echo "❌ zip missing"
command -v jq &> /dev/null && echo "✅ jq" || echo "⚠️  jq missing (install: brew install jq)"
aws sts get-caller-identity &> /dev/null && echo "✅ AWS credentials configured" || echo "❌ Run: aws configure"
```

### 3. AWS Requirements
- AWS Account with administrator access
- **Bedrock model access enabled**:
  - Claude 3.5 Sonnet v2 (anthropic.claude-3-5-sonnet-20241022-v2:0)
  - OR Claude 3 Haiku (anthropic.claude-3-haiku-20240307-v1:0)
- Region: **us-east-1** (recommended)

### 4. ProjectForce API Credentials
Gather these from ProjectForce Dashboard before deployment:

1. Login to https://dashboard.dev.projectsforce.com
2. Open Browser DevTools (F12 or Right-click → Inspect)
3. Go to **Application** tab → **Local Storage** → `https://dashboard.dev.projectsforce.com`
4. Copy these values:
   - `client_id` (e.g., `09PF05VD`)
   - `id` (User ID, e.g., `1646085`)
   - `accesstoken` (Bearer token - long JWT string)
   - `refreshToken` (optional - for auto-refresh)

---

## Step-by-Step Deployment

### Step 1: Verify AWS Setup

```bash
# Check AWS CLI is configured
aws sts get-caller-identity

# Should output:
# {
#   "UserId": "...",
#   "Account": "618048437522",
#   "Arn": "arn:aws:iam::..."
# }

# Check region
aws configure get region
# Should output: us-east-1
```

### Step 2: Navigate to Project

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb
git status  # Verify you're on the right branch
```

### Step 3: Run DEPLOY.sh

This is your main deployment script - it creates **everything from scratch**.

```bash
cd bedrock/scripts
./DEPLOY.sh
```

**What happens**:

1. **Prompts for ProjectForce credentials** (interactive):
   ```
   Client ID (e.g., 09PF05VD): [paste your client_id]
   User ID (e.g., 1646085): [paste your id]
   Bearer Token: [paste your accesstoken]
   Refresh Token (optional): [press Enter to skip or paste]
   ```

2. **Creates AWS Secrets Manager secret**: `projectforce/api/credentials`

3. **Creates DynamoDB table**: `pf-sessions-dev` (for session management)

4. **Deploys 2 Lambda functions** with dependencies:
   - `pf-scheduling-actions` (handler.py)
   - `pf-information-actions` (handler.py)
   - Packages include: requests, boto3, urllib3

5. **Creates 4 Bedrock agents**:
   - **SchedulingAgent** - Handles project scheduling, appointments
   - **pf-information** - Weather information specialist
   - **pf-chitchat** - Conversational greetings and casual chat
   - **Supervisor** - Orchestrator that routes requests

6. **Creates action groups** with function schemas:
   - SchedulingAgent actions: `list_projects`, `get_project_details`, `get_available_dates`, `get_time_slots`, `confirm_appointment`, `reschedule_appointment`, `cancel_appointment`
   - Information actions: `get_appointment_status`, `get_working_hours`, `get_weather`

7. **Prepares all agents** (makes them ready to use)

8. **Saves agent IDs** to `bedrock/config/agent_ids.json`

**Expected output**:
```
✅ Deployment Complete!

Created:
  ✅ 1 Secrets Manager secret (with real Bearer token)
  ✅ 2 Lambda functions (configured with Bearer token)
  ✅ 1 DynamoDB table
  ✅ 4 Bedrock agents (all PREPARED)
  ✅ 2 Action groups (SchedulingAgent, pf-information)

Agent IDs:
  • SchedulingAgent: ICSJNENK7I
  • pf-information: <GENERATED_ID>
  • pf-chitchat: <GENERATED_ID>
  • Supervisor: HXOKSZFJV5
```

**Duration**: 5-10 minutes

### Step 4: Test Individual Agents (Optional)

Before setting up collaboration, you can test individual agents:

```bash
# Test SchedulingAgent directly
aws bedrock-agent-runtime invoke-agent \
  --agent-id ICSJNENK7I \
  --agent-alias-id TSTALIASID \
  --session-id "test-$(date +%s)" \
  --input-text "Show me my projects" \
  --session-state '{"sessionAttributes":{"customer_id":"1646085","client_id":"09PF05VD"}}' \
  /tmp/test_response.txt

# View response
grep -o '"text":"[^"]*"' /tmp/test_response.txt | sed 's/"text":"//;s/"$//'
```

### Step 5: Setup Agent Collaboration

This enables the Supervisor agent to automatically route requests to specialist agents.

**IMPORTANT**: You must create v1 aliases in AWS Console first (one-time manual step).

#### 5a. Create v1 Aliases in AWS Console

**Why needed**: Bedrock agent collaboration requires versioned aliases. The default `TSTALIASID` cannot be used for collaboration.

**Steps** (repeat for SchedulingAgent, pf-information, pf-chitchat):

1. Open AWS Bedrock Console: https://console.aws.amazon.com/bedrock/
2. Select region: **us-east-1** (top-right dropdown)
3. Click **Agents** in left sidebar
4. Click on the agent name (e.g., "SchedulingAgent")
5. Click "Working draft" dropdown → **Create version**
6. Confirm dialog → Wait ~30 seconds → Version 1 created
7. Click **Aliases** tab → **Create alias**
8. Enter:
   - Alias name: `v1`
   - Agent version: Select `1`
9. Click **Create alias**
10. Note the Alias ID (e.g., `EJUYANKE6K`)

Repeat for all 3 collaborator agents (SchedulingAgent, pf-information, pf-chitchat).

**Time**: ~15 minutes total (5 minutes per agent)

#### 5b. Run SETUP_COLLABORATION.sh

After creating all v1 aliases:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/scripts
./SETUP_COLLABORATION.sh
```

**What it does**:
1. Checks for v1 aliases (fails if missing)
2. Builds alias ARNs for each collaborator
3. Associates collaborators with Supervisor:
   - SchedulingAgent → for scheduling queries
   - InformationAgent → for weather/information queries
   - ChitchatAgent → for greetings/casual chat
4. Prepares Supervisor agent with collaboration enabled
5. Verifies collaboration setup

**Expected output**:
```
✅ Collaboration Setup Complete!

✅ Collaborators associated:
   • SchedulingAgent
   • InformationAgent
   • ChitchatAgent
```

**Duration**: 1-2 minutes

### Step 6: Test with UI

Open the test UI to interact with the agents:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/testing/ui
open test_ui.html
```

**OR** use the auth demo (with authentication proxy):

```bash
./launch_auth_demo.sh
# Opens browser to http://localhost:5000
```

**Test queries to try**:
- "Show me my projects" → Routes to SchedulingAgent
- "Get details of project 7751741" → Routes to SchedulingAgent
- "What's the weather in New York?" → Routes to InformationAgent
- "Hello" → Routes to ChitchatAgent
- "Book an appointment for project 7751741" → Routes to SchedulingAgent

---

## Verification & Testing

### Check Agent Status

```bash
# List all agents
aws bedrock-agent list-agents --region us-east-1 --query 'agentSummaries[*].[agentName,agentId,agentStatus]' --output table

# Get specific agent details
aws bedrock-agent get-agent --agent-id ICSJNENK7I --region us-east-1
```

### Check Lambda Functions

```bash
# List Lambda functions
aws lambda list-functions --region us-east-1 | grep pf-

# Get function configuration
aws lambda get-function --function-name pf-scheduling-actions --region us-east-1
```

### Test Lambda Directly

```bash
# Test Lambda with sample event
aws lambda invoke \
  --function-name pf-scheduling-actions \
  --payload '{"actionGroup":"scheduling-actions","action":"list_projects","parameters":[{"name":"customer_id","value":"1646085"},{"name":"client_id","value":"09PF05VD"}]}' \
  /tmp/lambda_test.json

cat /tmp/lambda_test.json
```

### View CloudWatch Logs

```bash
# Tail Lambda logs
aws logs tail /aws/lambda/pf-scheduling-actions --follow --region us-east-1

# View last 10 minutes
aws logs tail /aws/lambda/pf-scheduling-actions --since 10m --region us-east-1
```

### Verify DynamoDB Table

```bash
# Check table exists
aws dynamodb describe-table --table-name pf-sessions-dev --region us-east-1

# List all DynamoDB tables
aws dynamodb list-tables --region us-east-1
```

### Check Secrets Manager

```bash
# Verify secret exists
aws secretsmanager describe-secret --secret-id projectforce/api/credentials --region us-east-1

# Get secret value (Bearer token)
aws secretsmanager get-secret-value --secret-id projectforce/api/credentials --region us-east-1 --query SecretString --output text | jq
```

---

## Troubleshooting

### Issue: "Bearer Token expired" or 401 Unauthorized

**Symptoms**: Lambda logs show HTTP 401 errors from ProjectForce API

**Solution**: Update Bearer token in Secrets Manager

```bash
# Get new token from browser (DevTools → Application → Local Storage → accesstoken)
NEW_TOKEN="your_new_token_here"

# Update secret
aws secretsmanager update-secret \
  --secret-id projectforce/api/credentials \
  --secret-string "{\"bearer_token\":\"$NEW_TOKEN\",\"client_id\":\"09PF05VD\",\"user_id\":\"1646085\",\"api_base_url\":\"https://api-cx-portal.dev.projectsforce.com\"}" \
  --region us-east-1
```

Lambda will automatically pick up the new token on next invocation (no redeployment needed).

### Issue: Lambda "ImportModuleError: No module named 'requests'"

**Symptoms**: Lambda fails to start with missing module error

**Solution**: Repackage Lambda with dependencies

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/lambda/scheduling-actions

# Clean and rebuild
rm -rf package function.zip
mkdir -p package
pip3 install -r requirements.txt -t package/
cd package && zip -r ../function.zip .
cd .. && zip -g function.zip *.py

# Redeploy
aws lambda update-function-code \
  --function-name pf-scheduling-actions \
  --zip-file fileb://function.zip \
  --region us-east-1
```

### Issue: Agent not calling correct function

**Symptoms**: Agent calls `list_projects` when you ask for project details

**Solution**: Function descriptions may need refinement. Check/update action group:

```bash
# View current action group
aws bedrock-agent get-agent-action-group \
  --agent-id ICSJNENK7I \
  --agent-version DRAFT \
  --action-group-id <ACTION_GROUP_ID> \
  --region us-east-1
```

Update descriptions in `/tmp/update_scheduling_action_group.sh` if needed, then run it.

### Issue: Collaboration not working

**Symptoms**: Supervisor doesn't route to specialist agents

**Checklist**:
1. ✅ Are v1 aliases created for all 3 collaborator agents?
2. ✅ Did you run `SETUP_COLLABORATION.sh` successfully?
3. ✅ Is Supervisor agent prepared after collaboration setup?

**Verify collaborators**:
```bash
aws bedrock-agent list-agent-collaborators \
  --agent-id HXOKSZFJV5 \
  --agent-version DRAFT \
  --region us-east-1
```

Should show 3 collaborators: SchedulingAgent, InformationAgent, ChitchatAgent

### Issue: "v1 alias not found" in SETUP_COLLABORATION.sh

**Solution**: You must create v1 aliases manually in AWS Console (see Step 5a). This is a one-time manual step that cannot be automated via AWS CLI.

---

## File Structure

Key files in your deployment:

```
schedulingAgent-bb/
├── bedrock/
│   ├── scripts/
│   │   ├── DEPLOY.sh                    ← Main deployment script (YOUR PRIMARY TOOL)
│   │   ├── SETUP_COLLABORATION.sh       ← Setup agent collaboration
│   │   ├── prepare_agents.sh            ← Utility to prepare agents
│   │   └── deployment/
│   │       └── DEPLOY_NEW_ENVIRONMENT.sh ← Alternative comprehensive deployment
│   ├── lambda/
│   │   ├── scheduling-actions/
│   │   │   ├── handler.py               ← Main Lambda handler
│   │   │   ├── requirements.txt         ← Python dependencies
│   │   │   └── function.zip             ← Deployment package
│   │   └── information-actions/
│   │       └── handler.py
│   ├── testing/
│   │   └── ui/
│   │       ├── test_ui.html             ← Simple test UI (YOUR TESTING TOOL)
│   │       └── launch_auth_demo.sh      ← Auth-enabled test UI
│   ├── config/
│   │   └── agent_ids.json               ← Generated agent IDs
│   └── infrastructure/
│       └── terraform/                    ← Alternative: Terraform IaC (not required)
└── DEPLOYMENT_GUIDE.md                  ← This file
```

---

## AWS Console Links

Quick access to AWS services:

- **Bedrock Agents**: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents
- **Lambda Functions**: https://console.aws.amazon.com/lambda/home?region=us-east-1#/functions
- **DynamoDB Tables**: https://console.aws.amazon.com/dynamodb/home?region=us-east-1#tables
- **CloudWatch Logs**: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups
- **Secrets Manager**: https://console.aws.amazon.com/secretsmanager/home?region=us-east-1#/listSecrets
- **IAM Roles**: https://console.aws.amazon.com/iam/home#/roles

---

## Summary: Complete Deployment Workflow

For a **brand new AWS environment**, follow this workflow:

### 1. Prerequisites (5 minutes)
- Configure AWS CLI
- Get ProjectForce API credentials from browser
- Install jq if needed

### 2. Main Deployment (5-10 minutes)
```bash
cd bedrock/scripts
./DEPLOY.sh
# Enter credentials when prompted
```

### 3. Create v1 Aliases (15 minutes) - Manual AWS Console Step
- Go to Bedrock Console
- For each of 3 agents: Create Version 1 → Create Alias "v1"

### 4. Setup Collaboration (2 minutes)
```bash
./SETUP_COLLABORATION.sh
```

### 5. Test (2 minutes)
```bash
cd ../testing/ui
open test_ui.html
```

**Total time**: ~30 minutes
**Total cost**: ~$0.50/day in AWS costs (mostly Lambda + Bedrock invocations)

---

## Alternative: Terraform Deployment

If you prefer Infrastructure as Code (IaC):

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/terraform

# Initialize Terraform
terraform init

# Review plan
terraform plan

# Deploy
terraform apply -auto-approve
```

**Note**: Terraform creates IAM roles and basic infrastructure, but you'll still need to run DEPLOY.sh for agents and action groups.

---

## Updating an Existing Deployment

To update Lambda code or agent configurations:

### Update Lambda Function

```bash
cd bedrock/lambda/scheduling-actions

# Make your code changes to handler.py

# Repackage
rm -rf package function.zip
mkdir -p package
pip3 install -r requirements.txt -t package/
cd package && zip -r ../function.zip .
cd .. && zip -g function.zip *.py

# Deploy
aws lambda update-function-code \
  --function-name pf-scheduling-actions \
  --zip-file fileb://function.zip \
  --region us-east-1
```

### Update Agent Instructions

```bash
# Update agent instruction
aws bedrock-agent update-agent \
  --agent-id ICSJNENK7I \
  --agent-name "SchedulingAgent" \
  --instruction "Your new instruction here..." \
  --region us-east-1

# Prepare agent to apply changes
aws bedrock-agent prepare-agent \
  --agent-id ICSJNENK7I \
  --region us-east-1
```

### Update Action Group Schema

Use the `/tmp/update_scheduling_action_group.sh` script (modify function descriptions, then run it).

---

## Support & Documentation

- **API Documentation**: See `API_AUTHENTICATION_GUIDE.md`
- **Dashboard API Status**: See `DASHBOARD_API_DEPLOYMENT_STATUS.md`
- **Lambda Handler**: See `bedrock/lambda/scheduling-actions/handler.py`
- **Action Group Schema**: See `/tmp/action_group_details.json`

---

**Last Updated**: 2025-11-05
**Version**: 1.0 (Based on working 24Oct branch)
**Primary Scripts**: DEPLOY.sh + SETUP_COLLABORATION.sh
