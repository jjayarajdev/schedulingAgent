# AWS Bedrock Multi-Agent System - Deployment Guide

**Version**: 2.0
**Last Updated**: October 21, 2025
**Environment**: Development (us-east-1)
**Foundation Model**: Claude Sonnet 4.5

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Deployment Steps](#deployment-steps)
4. [Post-Deployment Testing](#post-deployment-testing)
5. [Troubleshooting](#troubleshooting)
6. [Rollback Procedures](#rollback-procedures)
7. [Maintenance](#maintenance)

---

## Prerequisites

### Required Tools

- **Terraform** >= 1.5.0
- **AWS CLI** >= 2.31.0
- **Python** 3.11
- **Boto3** (Python AWS SDK)
- **jq** (JSON processor)
- **Git** (version control)

### AWS Permissions

Your AWS credentials must have permissions for:

- ✅ AWS Bedrock (agents, models)
- ✅ AWS Lambda (functions, permissions)
- ✅ AWS S3 (buckets, objects)
- ✅ AWS IAM (roles, policies)
- ✅ AWS CloudWatch (logs)

### Verify Prerequisites

```bash
# Check tool versions
terraform --version
aws --version
python3 --version
jq --version

# Verify AWS credentials
aws sts get-caller-identity

# Verify Bedrock model access
aws bedrock list-foundation-models --region us-east-1 \
  --query 'modelSummaries[?contains(modelId, `claude-sonnet-4-5`)]'
```

---

## Architecture Overview

### Agents Structure

```
┌─────────────────────────────────────┐
│      Supervisor Agent               │
│      (WF1S95L7X1)                  │
│                                     │
│  Collaboration: SUPERVISOR_ROUTER   │
└─────────────┬───────────────────────┘
              │
    ┌─────────┴─────────┐
    │                   │
    ▼                   ▼
┌─────────┐         ┌─────────┐
│Specialist│         │Specialist│
│ Agents   │         │ Agents   │
│          │         │          │
│Schedule  │         │Chitchat  │
│Information│         │Notes     │
└─────────┘         └─────────┘
```

### Current Agent IDs

| Agent | ID | Alias | Lambda |
|-------|-----|-------|--------|
| **Supervisor** | `WF1S95L7X1` | TSTALIASID, v1 | ❌ None |
| **Scheduling** | `TIGRBGSXCS` | PNDF9AQVHW (v1) | ✅ pf-scheduling-actions |
| **Information** | `JEK4SDJOOU` | LF61ZU9X2T (v1) | ✅ pf-information-actions |
| **Notes** | `CF0IPHCFFY` | YOBOR0JJM7 (v1) | ✅ pf-notes-actions |
| **Chitchat** | `GXVZEOBQ64` | RSSE65OYGM (v1) | ❌ None |

---

## Deployment Steps

### Phase 1: Infrastructure Preparation

#### Step 1.1: Navigate to Terraform Directory

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/terraform
```

#### Step 1.2: Review Variables

Check `variables.tf` for:

```hcl
project_name        = "pf"
environment         = "dev"
aws_region          = "us-east-1"
foundation_model    = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
```

#### Step 1.3: Initialize Terraform

```bash
terraform init
```

**Expected Output:**
```
Terraform has been successfully initialized!
```

#### Step 1.4: Review Terraform Plan

```bash
terraform plan -out=tfplan
```

**What to Check:**
- ✅ 5 agents will be created
- ✅ IAM roles and policies
- ✅ S3 bucket for schemas
- ✅ S3 objects for OpenAPI schemas

#### Step 1.5: Apply Terraform Configuration

```bash
terraform apply tfplan
```

**Duration:** ~2-3 minutes

**Expected Resources Created:**
- 5 Bedrock agents
- 4 IAM roles
- 1 S3 bucket
- 3 S3 objects (schemas)

#### Step 1.6: Verify Terraform Outputs

```bash
terraform output
```

**Expected Output:**
```
all_agent_ids = {
  "chitchat" = "GXVZEOBQ64"
  "information" = "JEK4SDJOOU"
  "notes" = "CF0IPHCFFY"
  "scheduling" = "TIGRBGSXCS"
  "supervisor" = "WF1S95L7X1"
}
agent_schemas_bucket = "pf-schemas-dev-618048437522"
```

---

### Phase 2: Lambda Functions

#### Step 2.1: Verify Lambda Functions Exist

```bash
aws lambda list-functions --region us-east-1 \
  --query 'Functions[?contains(FunctionName, `pf-`)].FunctionName'
```

**Expected Functions:**
- `pf-scheduling-actions`
- `pf-information-actions`
- `pf-notes-actions`

#### Step 2.2: Test Lambda Functions (Optional)

```bash
# Test scheduling Lambda
aws lambda invoke \
  --function-name pf-scheduling-actions \
  --payload '{"action":"health_check"}' \
  --region us-east-1 \
  /tmp/lambda-test.json

cat /tmp/lambda-test.json
```

---

### Phase 3: Agent Preparation

**IMPORTANT:** Use the v2 scripts that leverage Terraform outputs.

#### Step 3.1: Make Scripts Executable

```bash
chmod +x prepare_agents_v2.sh
chmod +x setup_supervisor_collaborators_v2.sh
```

#### Step 3.2: Prepare All Agents

```bash
./prepare_agents_v2.sh
```

**What This Does:**
1. Fetches agent IDs from Terraform outputs
2. Prepares all 5 agents (creates DRAFT versions)
3. Creates v1 aliases for all agents
4. Adds action groups to specialist agents (scheduling, information, notes)
5. Re-prepares agents with action groups

**Duration:** ~2 minutes

**Expected Output:**
```
✓ Agent IDs retrieved:
  Scheduling:   TIGRBGSXCS
  Information:  JEK4SDJOOU
  Notes:        CF0IPHCFFY
  Chitchat:     GXVZEOBQ64
  Supervisor:   WF1S95L7X1
...
✓ All agents prepared
✓ All aliases created
✓ All action groups added
Setup Complete!
```

#### Step 3.3: Verify Agent Status

```bash
# Check all agents are PREPARED
for agent in TIGRBGSXCS JEK4SDJOOU CF0IPHCFFY GXVZEOBQ64 WF1S95L7X1; do
  echo -n "$agent: "
  aws bedrock-agent get-agent --agent-id $agent --region us-east-1 \
    --query 'agent.agentStatus' --output text
done
```

**Expected Output:**
```
TIGRBGSXCS: PREPARED
JEK4SDJOOU: PREPARED
CF0IPHCFFY: PREPARED
GXVZEOBQ64: PREPARED
WF1S95L7X1: PREPARED
```

---

### Phase 4: Supervisor Collaboration Setup

#### Step 4.1: Associate Collaborators

```bash
./setup_supervisor_collaborators_v2.sh
```

**What This Does:**
1. Fetches agent and alias IDs from Terraform outputs
2. Associates 4 specialist agents as collaborators to supervisor
3. Enables conversation relay (`TO_COLLABORATOR`)
4. Prepares supervisor with collaborations
5. Verifies associations

**Duration:** ~30 seconds

**Expected Output:**
```
✓ Scheduling-Agent associated
✓ Information-Agent associated
✓ Notes-Agent associated
✓ Chitchat-Agent associated
✓ Agent status: PREPARED
Supervisor Setup Complete!
```

#### Step 4.2: Verify Collaborators

```bash
aws bedrock-agent list-agent-collaborators \
  --agent-id WF1S95L7X1 \
  --agent-version DRAFT \
  --region us-east-1 \
  --query 'agentCollaboratorSummaries[*].[collaboratorName,collaboratorId]' \
  --output table
```

**Expected Output:**
```
-----------------------------------------
|        ListAgentCollaborators         |
+------------------------+--------------+
|  Scheduling-Agent      |  TIGRBGSXCS  |
|  Information-Agent     |  JEK4SDJOOU  |
|  Notes-Agent           |  CF0IPHCFFY  |
|  Chitchat-Agent        |  GXVZEOBQ64  |
+------------------------+--------------+
```

---

### Phase 5: Upload OpenAPI Schemas (If Not Done by Terraform)

#### Step 5.1: Verify Schemas in S3

```bash
aws s3 ls s3://pf-schemas-dev-618048437522/
```

**Expected Files:**
- `scheduling_actions.json`
- `information_actions.json`
- `notes_actions.json`

#### Step 5.2: Update Schemas (If Needed)

```bash
# Upload updated scheduling schema (with session attributes fix)
aws s3 cp ../openapi_schemas/scheduling_actions.json \
  s3://pf-schemas-dev-618048437522/scheduling_actions.json

# Verify upload
aws s3 ls s3://pf-schemas-dev-618048437522/scheduling_actions.json
```

#### Step 5.3: Re-prepare Agents After Schema Update

```bash
aws bedrock-agent prepare-agent --agent-id TIGRBGSXCS --region us-east-1
```

---

## Post-Deployment Testing

### Test 1: Individual Agent Testing

#### Test Chitchat Agent (No Lambda)

```bash
python3 << 'EOF'
import boto3
import uuid

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

response = client.invoke_agent(
    agentId='GXVZEOBQ64',
    agentAliasId='TSTALIASID',
    sessionId=str(uuid.uuid4()),
    inputText='Hello! How are you?'
)

for event in response['completion']:
    if 'chunk' in event:
        print(event['chunk']['bytes'].decode('utf-8'), end='')
EOF
```

**Expected:** Friendly greeting response

#### Test Scheduling Agent (With Lambda)

```bash
python3 test_scheduling_session_fix.py
```

**Expected Output:**
```
✅ ✅ ✅ SUCCESS! Agent is using session attributes correctly!
  - Lambda was invoked
  - Agent did not ask for customer_id or client_id
```

### Test 2: Comprehensive Agent Test Suite

```bash
python3 run_all_agent_tests.py
```

**Expected Results:**
- Chitchat: 6/6 passed (100%)
- Scheduling: 5/5 passed (100%)
- Information: 4/4 passed (100%)
- Notes: 4/4 passed (100%)

**Test Duration:** ~2-3 minutes

### Test 3: Supervisor Routing (Optional)

```bash
python3 test_supervisor.py
```

**Note:** Supervisor routing may not work as expected (known platform limitation). Use frontend-based routing instead.

---

## Troubleshooting

### Issue 1: Agent Not Prepared

**Symptom:** Agent status shows `NOT_PREPARED` or `FAILED`

**Solution:**
```bash
# Re-prepare the agent
aws bedrock-agent prepare-agent --agent-id <AGENT_ID> --region us-east-1

# Wait 15 seconds
sleep 15

# Check status
aws bedrock-agent get-agent --agent-id <AGENT_ID> --region us-east-1 \
  --query 'agent.agentStatus' --output text
```

### Issue 2: Lambda Not Invoked

**Symptom:** Agent responds without calling Lambda function

**Common Causes:**
1. Schema has parameters in `required` array (should be optional for session attributes)
2. Lambda permissions not set correctly
3. Agent not prepared after schema change

**Solution:**
```bash
# Check schema in S3
aws s3 cp s3://pf-schemas-dev-618048437522/scheduling_actions.json - | jq '.paths."/list_projects".post.requestBody.content."application/json".schema.required'

# Should return: [] (empty array) for session attribute parameters

# Re-prepare agent
aws bedrock-agent prepare-agent --agent-id TIGRBGSXCS --region us-east-1
```

### Issue 3: Session Attributes Not Accessible

**Symptom:** Agent asks for customer_id/client_id despite them being in session

**Root Cause:** Parameters marked as `required` in OpenAPI schema

**Solution:** See `SESSION_ATTRIBUTES_FIX_SUMMARY.md`

### Issue 4: Terraform State Drift

**Symptom:** Terraform wants to recreate resources that already exist

**Solution:**
```bash
# Import existing resource
terraform import aws_bedrockagent_agent.scheduling <AGENT_ID>

# Or refresh state
terraform refresh
```

### Issue 5: Alias Already Exists

**Symptom:** Script fails with "Alias already exists" error

**Solution:** This is expected and handled in scripts with `|| true`. Continue with deployment.

---

## Rollback Procedures

### Rollback Terraform Changes

```bash
# Get previous state version
terraform state pull > current_state.json

# Rollback to previous plan
terraform apply previous.tfplan
```

### Rollback Agent Preparation

```bash
# List agent versions
aws bedrock-agent list-agent-versions \
  --agent-id <AGENT_ID> \
  --region us-east-1

# Update alias to point to previous version
aws bedrock-agent update-agent-alias \
  --agent-id <AGENT_ID> \
  --agent-alias-id <ALIAS_ID> \
  --agent-version <PREVIOUS_VERSION> \
  --region us-east-1
```

### Complete Teardown

```bash
# WARNING: This deletes ALL resources

# 1. Delete collaborator associations
aws bedrock-agent disassociate-agent-collaborator \
  --agent-id WF1S95L7X1 \
  --agent-version DRAFT \
  --collaborator-id <EACH_COLLABORATOR_ID> \
  --region us-east-1

# 2. Run Terraform destroy
terraform destroy
```

---

## Maintenance

### Regular Health Checks

```bash
# Check all agents are PREPARED
./scripts/check_agent_status.sh

# Run smoke tests
python3 run_all_agent_tests.py
```

### Schema Updates

```bash
# 1. Update local schema file
vim ../openapi_schemas/scheduling_actions.json

# 2. Upload to S3
aws s3 cp ../openapi_schemas/scheduling_actions.json \
  s3://pf-schemas-dev-618048437522/

# 3. Prepare agent
aws bedrock-agent prepare-agent --agent-id TIGRBGSXCS --region us-east-1
```

### Agent Instruction Updates

```bash
# 1. Update instruction file
vim ../agent_instructions/scheduling_collaborator.txt

# 2. Update agent via AWS CLI
aws bedrock-agent update-agent \
  --agent-id TIGRBGSXCS \
  --agent-name pf-scheduling \
  --foundation-model us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --instruction file://../agent_instructions/scheduling_collaborator.txt \
  --agent-resource-role-arn <ROLE_ARN> \
  --region us-east-1

# 3. Prepare agent
aws bedrock-agent prepare-agent --agent-id TIGRBGSXCS --region us-east-1
```

### Log Monitoring

```bash
# View Lambda logs
aws logs tail /aws/lambda/pf-scheduling-actions \
  --since 1h --follow --region us-east-1

# View all Lambda functions
aws logs tail --follow \
  --log-group-name-prefix '/aws/lambda/pf-' \
  --region us-east-1
```

---

## Quick Reference

### Deployment Sequence

```bash
# 1. Terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan

# 2. Agent Preparation
./prepare_agents_v2.sh

# 3. Supervisor Setup
./setup_supervisor_collaborators_v2.sh

# 4. Testing
python3 run_all_agent_tests.py
```

### Agent IDs Quick Access

```bash
# Get all agent IDs
terraform output all_agent_ids

# Get specific agent ID
terraform output -raw scheduling_agent_id
```

### Common AWS CLI Commands

```bash
# List all agents
aws bedrock-agent list-agents --region us-east-1

# Get agent details
aws bedrock-agent get-agent --agent-id <ID> --region us-east-1

# List action groups
aws bedrock-agent list-agent-action-groups \
  --agent-id <ID> --agent-version DRAFT --region us-east-1

# Prepare agent
aws bedrock-agent prepare-agent --agent-id <ID> --region us-east-1
```

---

## Support & Documentation

### Related Documents

- `README.md` - Project overview and quick start
- `CONFIGURATION_AUDIT_REPORT.md` - Configuration consistency verification
- `SESSION_ATTRIBUTES_FIX_SUMMARY.md` - Session attributes implementation details
- `AGENT_TEST_RESULTS.md` - Comprehensive test results
- `SUPERVISOR_RESEARCH_FINDINGS.md` - Multi-agent collaboration research

### AWS Documentation

- [Bedrock Agents User Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Multi-Agent Collaboration](https://aws.amazon.com/blogs/machine-learning/build-a-gen-ai-powered-financial-assistant-with-amazon-bedrock-multi-agent-collaboration/)

### AWS Support Case

- Case ID: 176101182600456
- Status: Resolved (session attributes fix applied)

---

**Document Version:** 2.0
**Last Updated:** October 21, 2025
**Maintained By:** Development Team
