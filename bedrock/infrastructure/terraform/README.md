# AWS Bedrock Multi-Agent System - Master Documentation

**Version**: 2.0 - Frontend Routing
**Last Updated**: October 24, 2025
**Foundation Model**: Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`)
**Routing**: Frontend Classification (Claude Haiku)
**Environment**: Development (us-east-1)
**Status**: ✅ Production Ready
**Classification Accuracy**: 100%

---

## Quick Start

```bash
# 1. Initialize Terraform
terraform init

# 2. Plan deployment
terraform plan -out=tfplan

# 3. Deploy infrastructure
terraform apply tfplan

# 4. Prepare agents with action groups (v2 recommended)
./prepare_agents_v2.sh

# 5. Setup supervisor collaboration
./setup_supervisor_collaborators_v2.sh

# 6. Test deployment
python3 run_all_agent_tests.py
```

**⚡ For detailed deployment steps**, see [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Current Agent Configuration](#current-agent-configuration)
3. [Key Features](#key-features)
4. [Documentation Index](#documentation-index)
5. [Scripts Reference](#scripts-reference)
6. [Quick Testing](#quick-testing)
7. [Terraform Resources](#terraform-resources)
8. [OpenAPI Schemas](#openapi-schemas)
9. [Agent Instructions](#agent-instructions)
10. [Lambda Functions](#lambda-functions)
11. [Testing Procedures](#testing-procedures)
12. [Troubleshooting](#troubleshooting)
13. [AWS Support Case Summary](#aws-support-case-summary)
14. [Known Limitations](#known-limitations)
15. [Maintenance](#maintenance)
16. [Development Guidelines](#development-guidelines)

---

## Architecture Overview (v2.0)

```
┌─────────────────────────────────────┐
│   Frontend Routing Layer            │
│   (Claude Haiku Classification)     │
│                                     │
│   Accuracy: 100%                    │
│   Time: ~200ms                      │
│   Cost: $0.00025 per request       │
└─────────────┬───────────────────────┘
              │
              │ Direct Invocation
              │
    ┌─────────┴─────────┐
    │                   │
    ▼                   ▼
┌─────────┐         ┌─────────┐
│Scheduling│         │Chitchat │
│Agent     │         │Agent    │
│(6 actions)│         │         │
└─────────┘         └─────────┘
    ▼                   ▼
┌─────────┐         ┌─────────┐
│Information│        │Notes    │
│Agent     │         │Agent    │
│(4 actions)│         │(2 actions)│
└─────────┘         └─────────┘
```

### Frontend Routing (v2.0)

- **Classification Layer**: Claude Haiku classifies user intent (100% accuracy)
- **Direct Invocation**: Routes directly to specialist agents (no supervisor)
- **Specialist Agents**: Handle specific domains (scheduling, information, notes, chitchat)
- **Session Attributes**: Customer credentials passed in prompt and sessionState
- **Monitoring**: Comprehensive JSON-structured logging

### Why Frontend Routing?

- ✅ **100% accuracy** (vs 67% with supervisor routing)
- ✅ **44% cheaper** ($0.028 vs $0.050 per request)
- ✅ **36% faster** (1.9s vs 3.0s average)
- ✅ **No AWS platform bugs** (supervisor has execution issues)

**Note:** Supervisor routing deprecated in v2.0 due to AWS Bedrock platform limitations where function calls appear as XML text instead of executing. See `../../docs/ROUTING_COMPARISON.md` for detailed analysis.

---

## Current Agent Configuration (v2.0)

**Status as of October 24, 2025:**

| Agent | Agent ID | Alias ID (v1) | Lambda Function | Status | Routing |
|-------|----------|---------------|-----------------|--------|---------|
| **Scheduling** | `TIGRBGSXCS` | PNDF9AQVHW | ✅ pf-scheduling-actions | ✅ PRODUCTION | Direct |
| **Information** | `JEK4SDJOOU` | LF61ZU9X2T | ✅ pf-information-actions | ✅ PRODUCTION | Direct |
| **Notes** | `CF0IPHCFFY` | YOBOR0JJM7 | ✅ pf-notes-actions | ✅ PRODUCTION | Direct |
| **Chitchat** | `GXVZEOBQ64` | RSSE65OYGM | ❌ None | ✅ PRODUCTION | Direct |

**Classification Model:** `anthropic.claude-3-haiku-20240307-v1:0`

**Note:** Supervisor agent (WF1S95L7X1) is deprecated in v2.0 - frontend routing used instead.

### Infrastructure Details

- **AWS Region**: us-east-1
- **Account ID**: 618048437522
- **Project Prefix**: pf
- **S3 Schemas Bucket**: `pf-schemas-dev-618048437522`
- **Foundation Model**: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`

---

## Key Features

### ✅ Session Attributes (Fixed October 21, 2025)

**Problem**: Agents asked for customer_id/client_id despite them being in session
**Root Cause**: OpenAPI schema marked these as `required` parameters
**Solution**: Removed from `required` arrays in all operations
**Result**: Lambda invokes correctly, no credential prompts

**Implementation**:
- Frontend passes `sessionAttributes: { customer_id, client_id }`
- Agents auto-populate these from session state
- Lambda receives credentials automatically
- User never asked for credentials

See [SESSION_ATTRIBUTES_FIX_SUMMARY.md](SESSION_ATTRIBUTES_FIX_SUMMARY.md) for details.

### ✅ Lambda Action Groups

**Specialist agents** have Lambda-backed action groups:

1. **Scheduling Actions** (`pf-scheduling-actions`)
   - List projects
   - Get available dates
   - Get time slots
   - Confirm appointment
   - Reschedule appointment
   - Cancel appointment

2. **Information Actions** (`pf-information-actions`)
   - Get project details
   - Get order information
   - Get installation address
   - Get appointment status

3. **Notes Actions** (`pf-notes-actions`)
   - Create note
   - Get notes
   - Update note
   - Delete note

### ✅ Multi-Agent Collaboration

- **Supervisor Mode**: `SUPERVISOR_ROUTER`
- **Collaborator Associations**: 4 specialist agents
- **Relay Conversation History**: `TO_COLLABORATOR` (full context)
- **Collaboration Instructions**: Detailed routing guidance for each agent

**Note**: Supervisor routing has known platform limitations. Production uses frontend-based routing for reliability.

---

## Documentation Index

### Deployment & Configuration

- **[DEPLOY_GUIDE.md](DEPLOY_GUIDE.md)** - Comprehensive deployment guide with 5 phases
- **[CONFIGURATION_AUDIT_REPORT.md](CONFIGURATION_AUDIT_REPORT.md)** - Configuration consistency verification
- **[variables.tf](variables.tf)** - Terraform variable definitions
- **[bedrock_agents.tf](bedrock_agents.tf)** - Main Terraform configuration (569 lines)

### Implementation Details

- **[SESSION_ATTRIBUTES_FIX_SUMMARY.md](SESSION_ATTRIBUTES_FIX_SUMMARY.md)** - Session attributes implementation
- **[AGENT_TEST_RESULTS.md](AGENT_TEST_RESULTS.md)** - Comprehensive test results (19/19 passing)
- **[SUPERVISOR_RESEARCH_FINDINGS.md](SUPERVISOR_RESEARCH_FINDINGS.md)** - Multi-agent collaboration research

### Scripts & Testing

- **[prepare_agents_v2.sh](prepare_agents_v2.sh)** - Prepare agents using Terraform outputs ✅ Recommended
- **[setup_supervisor_collaborators_v2.sh](setup_supervisor_collaborators_v2.sh)** - Setup supervisor using Terraform outputs ✅ Recommended
- **[run_all_agent_tests.py](run_all_agent_tests.py)** - Comprehensive test suite
- **[test_scheduling_session_fix.py](test_scheduling_session_fix.py)** - Session attributes verification

---

## Scripts Reference

### ✅ Recommended: V2 Scripts (Terraform Output-Based)

These scripts fetch agent IDs dynamically from Terraform outputs:

#### `prepare_agents_v2.sh`

**Purpose**: Prepare all agents, create aliases, add action groups

```bash
./prepare_agents_v2.sh
```

**What it does**:
1. Fetches agent IDs from `terraform output`
2. Validates all IDs retrieved successfully
3. Prepares all 5 agents (creates DRAFT versions)
4. Creates v1 aliases for all agents
5. Adds action groups to specialist agents (scheduling, information, notes)
6. Re-prepares agents with action groups

**Duration**: ~2 minutes

#### `setup_supervisor_collaborators_v2.sh`

**Purpose**: Associate specialist agents as collaborators to supervisor

```bash
./setup_supervisor_collaborators_v2.sh
```

**What it does**:
1. Fetches agent and alias IDs from Terraform outputs
2. Associates 4 specialist agents as collaborators
3. Sets collaboration instructions for each agent
4. Enables conversation relay (`TO_COLLABORATOR`)
5. Prepares supervisor with collaborations
6. Verifies associations

**Duration**: ~30 seconds

### ⚠️ Legacy Scripts (Hardcoded IDs)

These scripts use hardcoded agent IDs and are deprecated:

- `prepare_agents.sh` - Use `prepare_agents_v2.sh` instead
- `setup_supervisor_collaborators.sh` - Use `setup_supervisor_collaborators_v2.sh` instead

**Why upgrade to v2?**
- ✅ Single source of truth (Terraform)
- ✅ No manual ID updates needed
- ✅ Validation ensures Terraform ran first
- ✅ Easier maintenance

---

## Quick Testing

### Test 1: Individual Agent (Quick Smoke Test)

```bash
# Test Chitchat Agent (no Lambda, fastest)
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

**Expected**: Friendly greeting response

### Test 2: Session Attributes Fix

```bash
python3 test_scheduling_session_fix.py
```

**Expected Output**:
```
✅ ✅ ✅ SUCCESS! Agent is using session attributes correctly!
  - Lambda was invoked
  - Agent did not ask for customer_id or client_id
```

### Test 3: Comprehensive Test Suite

```bash
python3 run_all_agent_tests.py
```

**Expected Results**:
- Chitchat: 6/6 passed (100%)
- Scheduling: 5/5 passed (100%)
- Information: 4/4 passed (100%)
- Notes: 4/4 passed (100%)

**Duration**: ~2-3 minutes

---

## Terraform Resources

### Core Resources Created

**File**: `bedrock_agents.tf` (569 lines)

1. **S3 Bucket** - Stores OpenAPI schemas
   - Name: `pf-schemas-dev-618048437522`
   - Versioning: Enabled
   - Server-side encryption: Enabled

2. **S3 Objects** - OpenAPI schemas
   - `scheduling_actions.json`
   - `information_actions.json`
   - `notes_actions.json`

3. **IAM Roles** - Agent execution roles
   - `pf-bedrock-supervisor-role-dev`
   - `pf-bedrock-scheduling-role-dev`
   - `pf-bedrock-information-role-dev`
   - `pf-bedrock-notes-role-dev`
   - `pf-bedrock-chitchat-role-dev`

4. **IAM Policies** - Agent permissions
   - Invoke Bedrock models
   - Read S3 schemas
   - Invoke Lambda functions
   - Invoke collaborator agents

5. **Bedrock Agents** - 5 agents
   - Supervisor: `pf-supervisor-dev`
   - Scheduling: `pf-scheduling-dev`
   - Information: `pf-information-dev`
   - Notes: `pf-notes-dev`
   - Chitchat: `pf-chitchat-dev`

### Terraform Outputs

```bash
terraform output
```

**Available outputs**:
- `supervisor_agent_id` - Supervisor agent ID
- `scheduling_agent_id` - Scheduling agent ID
- `information_agent_id` - Information agent ID
- `notes_agent_id` - Notes agent ID
- `chitchat_agent_id` - Chitchat agent ID
- `all_agent_ids` - Map of all agent IDs
- `agent_schemas_bucket` - S3 bucket name

### Resource Relationships

```
S3 Bucket
  └─→ S3 Objects (schemas)
       └─→ Agent Action Groups
            └─→ Bedrock Agents
                 └─→ IAM Roles
                      └─→ IAM Policies
```

---

## OpenAPI Schemas

**Location**: `infrastructure/openapi_schemas/`

### 1. Scheduling Actions Schema

**File**: `scheduling_actions.json`
**S3**: `s3://pf-schemas-dev-618048437522/scheduling_actions.json`
**Status**: ✅ Fixed (session attributes)

**Operations**:
- `POST /list_projects` - List available projects
- `POST /get_available_dates` - Get available appointment dates
- `POST /get_time_slots` - Get available time slots
- `POST /confirm_appointment` - Confirm new appointment
- `POST /reschedule_appointment` - Reschedule existing appointment
- `POST /cancel_appointment` - Cancel appointment

**Key Fix (October 21, 2025)**:
```json
// BEFORE (WRONG):
"required": ["customer_id", "client_id"]

// AFTER (CORRECT):
"required": []  // Empty - customer_id and client_id auto-populated from session
```

### 2. Information Actions Schema

**File**: `information_actions.json`
**S3**: `s3://pf-schemas-dev-618048437522/information_actions.json`

**Operations**:
- `GET /project/{project_id}` - Get project details
- `GET /order/{project_id}` - Get order information
- `GET /address/{project_id}` - Get installation address
- `GET /appointment/{project_id}` - Get appointment status

### 3. Notes Actions Schema

**File**: `notes_actions.json`
**S3**: `s3://pf-schemas-dev-618048437522/notes_actions.json`

**Operations**:
- `POST /notes` - Create new note
- `GET /notes/{appointment_id}` - Get notes for appointment
- `PUT /notes/{note_id}` - Update note
- `DELETE /notes/{note_id}` - Delete note

### Schema Update Process

```bash
# 1. Edit local schema
vim infrastructure/openapi_schemas/scheduling_actions.json

# 2. Upload to S3
aws s3 cp infrastructure/openapi_schemas/scheduling_actions.json \
  s3://pf-schemas-dev-618048437522/

# 3. Prepare agent (picks up new schema)
aws bedrock-agent prepare-agent \
  --agent-id TIGRBGSXCS \
  --region us-east-1

# 4. Verify
python3 test_scheduling_session_fix.py
```

---

## Agent Instructions

**Location**: `infrastructure/agent_instructions/`

### Supervisor Agent

**File**: `supervisor.txt`

**Key Sections**:
- Role definition (router/delegator)
- Collaborator routing rules
- Session attributes handling
- Fallback behavior

### Specialist Agents

1. **`scheduling_collaborator.txt`**
   - CRITICAL: Session attributes section (added October 21, 2025)
   - Scheduling workflow instructions
   - Error handling
   - Confirmation requirements

2. **`information_collaborator.txt`**
   - Project information retrieval
   - Order status queries
   - Address lookup
   - Appointment status

3. **`notes_collaborator.txt`**
   - Note creation
   - Note retrieval
   - Note management
   - Customer communication

4. **`chitchat_collaborator.txt`**
   - Conversational tone
   - Greeting handling
   - Small talk
   - Redirect to specialists when needed

### Updating Instructions

```bash
# 1. Edit instruction file
vim infrastructure/agent_instructions/scheduling_collaborator.txt

# 2. Update agent via AWS CLI
aws bedrock-agent update-agent \
  --agent-id TIGRBGSXCS \
  --agent-name pf-scheduling \
  --foundation-model us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --instruction file://infrastructure/agent_instructions/scheduling_collaborator.txt \
  --agent-resource-role-arn <ROLE_ARN> \
  --region us-east-1

# 3. Prepare agent
aws bedrock-agent prepare-agent --agent-id TIGRBGSXCS --region us-east-1
```

---

## Lambda Functions

### Created Lambda Functions

**Region**: us-east-1
**Account**: 618048437522

1. **pf-scheduling-actions**
   - ARN: `arn:aws:lambda:us-east-1:618048437522:function:pf-scheduling-actions`
   - Runtime: Python 3.11
   - Handler: `handler.lambda_handler`
   - Purpose: Scheduling operations (PF360 API integration)

2. **pf-information-actions**
   - ARN: `arn:aws:lambda:us-east-1:618048437522:function:pf-information-actions`
   - Runtime: Python 3.11
   - Handler: `handler.lambda_handler`
   - Purpose: Information retrieval (PF360 API integration)

3. **pf-notes-actions**
   - ARN: `arn:aws:lambda:us-east-1:618048437522:function:pf-notes-actions`
   - Runtime: Python 3.11
   - Handler: `handler.lambda_handler`
   - Purpose: Note management (PF360 API integration)

### Lambda Invocation Test

```bash
# Test scheduling Lambda
aws lambda invoke \
  --function-name pf-scheduling-actions \
  --payload '{"action":"health_check"}' \
  --region us-east-1 \
  /tmp/lambda-test.json

cat /tmp/lambda-test.json
```

### View Lambda Logs

```bash
# View recent logs for scheduling Lambda
aws logs tail /aws/lambda/pf-scheduling-actions \
  --since 1h --follow --region us-east-1

# View all pf-* Lambda logs
aws logs tail --follow \
  --log-group-name-prefix '/aws/lambda/pf-' \
  --region us-east-1
```

---

## Testing Procedures

### Comprehensive Test Suite

**File**: `run_all_agent_tests.py`

**Tests Performed**:

#### Chitchat Agent (6 tests)
1. ✅ Basic greeting
2. ✅ How are you question
3. ✅ Weather inquiry (graceful decline)
4. ✅ General conversation
5. ✅ Multiple exchanges
6. ✅ Redirect to specialists

#### Scheduling Agent (5 tests)
1. ✅ List projects (session attributes)
2. ✅ Get available dates
3. ✅ Get time slots
4. ✅ Schedule appointment confirmation
5. ✅ Reschedule handling

#### Information Agent (4 tests)
1. ✅ Project details
2. ✅ Order information
3. ✅ Installation address
4. ✅ Appointment status

#### Notes Agent (4 tests)
1. ✅ Create note
2. ✅ Retrieve notes
3. ✅ Update note
4. ✅ Delete note

**Run Tests**:
```bash
python3 run_all_agent_tests.py
```

**Expected**: 19/19 tests passing (100%)

### Agent Status Check

```bash
# Check all agents are PREPARED
for agent in TIGRBGSXCS JEK4SDJOOU CF0IPHCFFY GXVZEOBQ64 WF1S95L7X1; do
  echo -n "$agent: "
  aws bedrock-agent get-agent --agent-id $agent --region us-east-1 \
    --query 'agent.agentStatus' --output text
done
```

**Expected Output**:
```
TIGRBGSXCS: PREPARED
JEK4SDJOOU: PREPARED
CF0IPHCFFY: PREPARED
GXVZEOBQ64: PREPARED
WF1S95L7X1: PREPARED
```

### Collaborator Verification

```bash
aws bedrock-agent list-agent-collaborators \
  --agent-id WF1S95L7X1 \
  --agent-version DRAFT \
  --region us-east-1 \
  --query 'agentCollaboratorSummaries[*].[collaboratorName,collaboratorId]' \
  --output table
```

**Expected Output**:
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

## Troubleshooting

### 1. Agent Not Invoking Lambda

**Symptom**: Agent responds without calling Lambda function

**Common Causes**:
1. Schema has parameters in `required` array that should be optional
2. Lambda permissions not set correctly
3. Agent not prepared after schema change

**Solution**:
```bash
# Check schema in S3
aws s3 cp s3://pf-schemas-dev-618048437522/scheduling_actions.json - | \
  jq '.paths."/list_projects".post.requestBody.content."application/json".schema.required'

# Should return: [] (empty array) for session attribute parameters

# Re-prepare agent
aws bedrock-agent prepare-agent --agent-id TIGRBGSXCS --region us-east-1
```

### 2. Session Attributes Not Working

**Symptom**: Agent asks for customer_id/client_id despite them being in session

**Root Cause**: Parameters marked as `required` in OpenAPI schema

**Solution**: See [SESSION_ATTRIBUTES_FIX_SUMMARY.md](SESSION_ATTRIBUTES_FIX_SUMMARY.md)

**Quick Fix**:
- Remove `customer_id` and `client_id` from `required` arrays in schema
- Upload updated schema to S3
- Prepare agent

### 3. Terraform State Drift

**Symptom**: Terraform wants to recreate resources that already exist

**Solution**:
```bash
# Refresh state
terraform refresh

# Or import existing resource
terraform import aws_bedrockagent_agent.scheduling TIGRBGSXCS
```

### 4. Agent Status NOT_PREPARED

**Symptom**: Agent shows `NOT_PREPARED` or `FAILED` status

**Solution**:
```bash
# Re-prepare agent
aws bedrock-agent prepare-agent --agent-id <AGENT_ID> --region us-east-1

# Wait 15 seconds
sleep 15

# Check status
aws bedrock-agent get-agent --agent-id <AGENT_ID> --region us-east-1 \
  --query 'agent.agentStatus' --output text
```

---

## AWS Support Case Summary

**Case ID**: 176101182600456
**Date**: October 2025
**Status**: ✅ Resolved

### Original Issue

Bedrock agents not invoking Lambda functions. Agent asked for customer_id/client_id despite session attributes being provided.

### Root Cause

OpenAPI schema marked `customer_id` and `client_id` as **required parameters**, causing Bedrock to interpret them as user inputs that must be collected before invoking Lambda.

### Resolution

Removed `customer_id` and `client_id` from `required` arrays in all operations:

**Operations Fixed**:
1. `list_projects`
2. `get_available_dates`
3. `get_time_slots`
4. `confirm_appointment`
5. `reschedule_appointment`
6. `cancel_appointment`

### Key Learning

> "In Bedrock Agents, the OpenAPI schema's `required` array determines what the agent asks the user for, not the agent instructions."

**Parameter Behavior**:
- In `required` array → Agent WILL ask user
- NOT in `required` array → Agent checks session attributes first
- Not in schema at all → Lambda won't receive it

### Related Documentation

- [SESSION_ATTRIBUTES_FIX_SUMMARY.md](SESSION_ATTRIBUTES_FIX_SUMMARY.md) - Detailed fix documentation
- [CONFIGURATION_AUDIT_REPORT.md](CONFIGURATION_AUDIT_REPORT.md) - Post-fix verification

---

## Known Limitations

### 1. Supervisor Routing (Platform Limitation)

**Issue**: SUPERVISOR_ROUTER mode doesn't consistently delegate to collaborators

**Symptoms**:
- Supervisor responds directly instead of delegating
- Inconsistent routing behavior
- No invocation traces for collaborators

**Workaround**: Use frontend-based routing

**Frontend Routing Logic**:
```javascript
// Frontend determines specialist agent based on intent
if (intent === 'scheduling') {
  agentId = 'TIGRBGSXCS';  // Scheduling agent
} else if (intent === 'information') {
  agentId = 'JEK4SDJOOU';  // Information agent
}
// ... invoke specialist directly
```

**References**:
- [SUPERVISOR_RESEARCH_FINDINGS.md](SUPERVISOR_RESEARCH_FINDINGS.md)
- AWS Support Case 176101182600456 (optional question)

### 2. Cross-Region Inference (Not an Issue)

**Clarification**: Claude Sonnet 4.5 supports cross-region inference

**Supported Regions**:
- us-east-1 ✅
- us-east-2 ✅
- us-west-2 ✅

**Note**: If creating agents in us-east-1 but model is in us-west-2, requests automatically route to the correct region.

### 3. Action Group Associations (Platform Limitation)

**Issue**: Terraform can't reliably manage action groups due to Bedrock API limitations

**Current Approach**: Use shell scripts for action group management

**Scripts**:
- `prepare_agents_v2.sh` - Adds action groups after Terraform deployment
- Terraform creates agents WITHOUT action groups
- Scripts add action groups via AWS CLI

---

## Maintenance

### Regular Health Checks

```bash
# Check all agents are PREPARED
for agent in TIGRBGSXCS JEK4SDJOOU CF0IPHCFFY GXVZEOBQ64 WF1S95L7X1; do
  echo -n "$agent: "
  aws bedrock-agent get-agent --agent-id $agent --region us-east-1 \
    --query 'agent.agentStatus' --output text
done

# Run smoke tests
python3 run_all_agent_tests.py
```

### Schema Updates

```bash
# 1. Update local schema file
vim infrastructure/openapi_schemas/scheduling_actions.json

# 2. Upload to S3
aws s3 cp infrastructure/openapi_schemas/scheduling_actions.json \
  s3://pf-schemas-dev-618048437522/

# 3. Prepare agent
aws bedrock-agent prepare-agent --agent-id TIGRBGSXCS --region us-east-1

# 4. Test
python3 test_scheduling_session_fix.py
```

### Agent Instruction Updates

```bash
# 1. Update instruction file
vim infrastructure/agent_instructions/scheduling_collaborator.txt

# 2. Apply via Terraform (recommended)
terraform apply

# 3. Or update via AWS CLI
aws bedrock-agent update-agent \
  --agent-id TIGRBGSXCS \
  --agent-name pf-scheduling \
  --foundation-model us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --instruction file://infrastructure/agent_instructions/scheduling_collaborator.txt \
  --agent-resource-role-arn <ROLE_ARN> \
  --region us-east-1

# 4. Prepare agent
aws bedrock-agent prepare-agent --agent-id TIGRBGSXCS --region us-east-1
```

### Log Monitoring

```bash
# View Lambda logs (last hour, follow)
aws logs tail /aws/lambda/pf-scheduling-actions \
  --since 1h --follow --region us-east-1

# View all pf-* Lambda logs
aws logs tail --follow \
  --log-group-name-prefix '/aws/lambda/pf-' \
  --region us-east-1

# Filter for errors
aws logs tail /aws/lambda/pf-scheduling-actions \
  --since 1h --filter-pattern "ERROR" \
  --region us-east-1
```

---

## Development Guidelines

### Recommended Workflow

1. **Infrastructure Changes**:
   ```bash
   # Make changes in bedrock_agents.tf or variables.tf
   terraform plan
   terraform apply
   ```

2. **Agent Preparation**:
   ```bash
   # Use v2 scripts (Terraform output-based)
   ./prepare_agents_v2.sh
   ./setup_supervisor_collaborators_v2.sh
   ```

3. **Testing**:
   ```bash
   # Quick test
   python3 test_scheduling_session_fix.py

   # Comprehensive test
   python3 run_all_agent_tests.py
   ```

4. **Deployment**:
   ```bash
   # Follow DEPLOY_GUIDE.md for production deployment
   ```

### Best Practices

✅ **DO**:
- Use v2 scripts (Terraform output-based)
- Test after every schema change
- Prepare agents after updates
- Document changes in git commits
- Run comprehensive tests before production deployment

❌ **DON'T**:
- Hardcode agent IDs in new scripts
- Skip agent preparation after changes
- Deploy without testing
- Mark parameters as `required` if they're in session attributes
- Forget to upload schemas to S3 after local edits

### Git Workflow

```bash
# 1. Make changes
vim infrastructure/openapi_schemas/scheduling_actions.json

# 2. Test locally
python3 test_scheduling_session_fix.py

# 3. Commit with descriptive message
git add infrastructure/openapi_schemas/scheduling_actions.json
git commit -m "fix: Remove customer_id from required array in list_projects"

# 4. Push to branch
git push origin feature/schema-fix
```

---

## Quick Reference

### Deployment Sequence

```bash
# Complete deployment from scratch
terraform init
terraform plan -out=tfplan
terraform apply tfplan
./prepare_agents_v2.sh
./setup_supervisor_collaborators_v2.sh
python3 run_all_agent_tests.py
```

### Get Agent IDs

```bash
# All agent IDs
terraform output all_agent_ids

# Specific agent ID
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

# List collaborators
aws bedrock-agent list-agent-collaborators \
  --agent-id WF1S95L7X1 --agent-version DRAFT --region us-east-1
```

### Useful Terraform Commands

```bash
# Show current state
terraform show

# List all resources
terraform state list

# Get specific output
terraform output -raw supervisor_agent_id

# Refresh state from AWS
terraform refresh

# Format all .tf files
terraform fmt
```

---

## Support & Resources

### Documentation

- **Deployment**: [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md)
- **Configuration Audit**: [CONFIGURATION_AUDIT_REPORT.md](CONFIGURATION_AUDIT_REPORT.md)
- **Session Attributes**: [SESSION_ATTRIBUTES_FIX_SUMMARY.md](SESSION_ATTRIBUTES_FIX_SUMMARY.md)
- **Test Results**: [AGENT_TEST_RESULTS.md](AGENT_TEST_RESULTS.md)
- **Supervisor Research**: [SUPERVISOR_RESEARCH_FINDINGS.md](SUPERVISOR_RESEARCH_FINDINGS.md)

### AWS Documentation

- [Bedrock Agents User Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Multi-Agent Collaboration](https://aws.amazon.com/blogs/machine-learning/build-a-gen-ai-powered-financial-assistant-with-amazon-bedrock-multi-agent-collaboration/)
- [Action Groups](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-action-create.html)
- [Session Attributes](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-session-state.html)

### Contact

- **AWS Support Case**: 176101182600456 (resolved)
- **Project Repository**: schedulingAgent-bb/bedrock
- **Environment**: Development (us-east-1)

---

## Version History

### Version 2.0 (October 22, 2025)

**Changes**:
- ✅ Migrated to Claude Sonnet 4.5
- ✅ Fixed session attributes (OpenAPI schema)
- ✅ Created v2 scripts (Terraform output-based)
- ✅ Comprehensive documentation
- ✅ 19/19 tests passing
- ✅ Configuration audit completed
- ✅ Production ready

### Version 1.0 (Previous)

- Initial deployment with Claude 3.5 Sonnet v2
- Hardcoded agent IDs in scripts
- Session attributes not working
- Supervisor routing attempted

---

**Document Version**: 2.0
**Last Updated**: October 22, 2025
**Maintained By**: Development Team
**Status**: ✅ Production Ready
