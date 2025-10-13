# AWS Bedrock Multi-Agent Deployment Guide

**Complete step-by-step guide for deploying 5 Bedrock Agents with multi-agent collaboration**

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Model Access Setup](#model-access-setup)
3. [Project Structure](#project-structure)
4. [Terraform Configuration](#terraform-configuration)
5. [Deployment Steps](#deployment-steps)
6. [Post-Deployment](#post-deployment)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools

- ✅ **AWS CLI** (v2.x recommended)
  ```bash
  aws --version
  ```

- ✅ **Terraform** (>= 1.5.0)
  ```bash
  terraform --version
  ```

- ✅ **Python** 3.11+ (for testing scripts)
  ```bash
  python3 --version
  ```

- ✅ **jq** (for JSON parsing - optional but recommended)
  ```bash
  jq --version
  ```

### AWS Permissions

Your IAM user/role must have permissions for:
- AWS Bedrock (agents, models, inference profiles)
- IAM (create roles and policies)
- S3 (create buckets, upload objects)
- CloudWatch Logs (for agent logging)

**Minimum Policy Example:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:*",
        "iam:CreateRole",
        "iam:CreatePolicy",
        "iam:AttachRolePolicy",
        "iam:PutRolePolicy",
        "s3:CreateBucket",
        "s3:PutObject",
        "s3:GetObject",
        "logs:CreateLogGroup",
        "logs:CreateLogStream"
      ],
      "Resource": "*"
    }
  ]
}
```

### Verify AWS CLI Configuration

```bash
# Test credentials
aws sts get-caller-identity

# Should output your AWS account ID, user ARN
```

---

## Model Access Setup

### Option 1: Check Existing Access

```bash
# List all inference profiles
aws bedrock list-inference-profiles --region us-east-1 | grep -i "claude-sonnet-4"

# Check specific model access
aws bedrock get-inference-profile \
  --inference-profile-identifier us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --region us-east-1
```

### Option 2: Request Model Access

1. **AWS Console Method:**
   - Navigate to: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess
   - Click **"Manage model access"**
   - Find **"Claude Sonnet 4.5"** in the list
   - Click **"Request access"** or verify **"Access granted"** status
   - For Anthropic models, access is typically instant

2. **Verify Access:**
   ```bash
   aws bedrock list-foundation-models \
     --region us-east-1 \
     --by-provider anthropic | grep -A 5 "claude-sonnet-4"
   ```

**Important:** AWS Bedrock requires **inference profiles** for newer Claude models. Direct model IDs won't work.

---

## Project Structure

```
bedrock/
├── infrastructure/
│   ├── terraform/
│   │   ├── bedrock_agents.tf        # Main agent configuration (550 lines)
│   │   ├── provider.tf               # AWS provider setup
│   │   ├── terraform.tfvars          # Variable values (YOU EDIT THIS)
│   │   └── variables.tf              # Variable definitions
│   │
│   ├── agent_instructions/           # Agent prompts (5 files)
│   │   ├── supervisor.txt           # 2.7 KB - Routing logic
│   │   ├── scheduling_collaborator.txt  # 6.8 KB - Scheduling workflows
│   │   ├── information_collaborator.txt # 5.2 KB - Information retrieval
│   │   ├── notes_collaborator.txt   # 4.1 KB - Note management
│   │   └── chitchat_collaborator.txt # 5.6 KB - Conversations
│   │
│   └── openapi_schemas/              # Action group APIs (3 files)
│       ├── scheduling_actions.json  # 10.2 KB - 6 actions
│       ├── information_actions.json # 7.8 KB - 4 actions
│       └── notes_actions.json       # 4.3 KB - 2 actions
│
├── tests/                            # Test scripts
│   ├── test_agents_interactive.py   # Interactive testing
│   ├── test_api_access.py           # API access validation
│   └── test_agent.py                # Basic test
│
├── utils/                            # Utility scripts
│   └── prepare_all_agents.py        # Agent preparation
│
└── scripts/                          # Shell scripts
    ├── gather_diagnostics.sh        # Diagnostic collection
    └── verify_deployment.sh         # Verification script
```

---

## Terraform Configuration

### Step 1: Navigate to Terraform Directory

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/terraform
```

### Step 2: Review terraform.tfvars

The file should look like this:

```hcl
# Environment: Development
environment = "dev"

# AWS Region
aws_region = "us-east-1"

# Project name (used for resource naming)
project_name = "scheduling-agent"

# Bedrock Foundation Model
# Using Claude Sonnet 4.5 inference profile (newest, fastest Claude model)
foundation_model = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

# Note: All newer Claude models require inference profiles:
# - us.anthropic.claude-sonnet-4-5-20250929-v1:0 (Claude Sonnet 4.5 - US) ← Using this
# - us.anthropic.claude-sonnet-4-20250514-v1:0 (Claude Sonnet 4 - US)
# - us.anthropic.claude-3-5-sonnet-20241022-v2:0 (Claude 3.5 Sonnet v2 - US)
```

### Step 3: Customize (Optional)

Edit values to match your requirements:

```bash
# Change project name (affects all resource names)
project_name = "my-scheduling-agent"

# Change environment
environment = "staging"  # or "prod"

# Change region (ensure model access in that region)
aws_region = "us-west-2"

# Use different model (if you have access)
foundation_model = "us.anthropic.claude-sonnet-4-20250514-v1:0"
```

---

## Deployment Steps

### Step 1: Initialize Terraform

```bash
cd infrastructure/terraform
terraform init
```

**Expected Output:**
```
Initializing the backend...
Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 6.0"...
- Installing hashicorp/aws v6.16.0...
Terraform has been successfully initialized!
```

### Step 2: Review Terraform Plan

```bash
terraform plan
```

This will show:
- **5 agents** to be created
- **5 agent aliases** to be created
- **5 IAM roles** to be created
- **5 IAM policies** to be created
- **1 S3 bucket** to be created
- **3 S3 objects** (OpenAPI schemas) to be uploaded
- **Total: ~30 resources**

**Save plan for review:**
```bash
terraform plan -out=tfplan
terraform show tfplan > ../../docs/tfplan.txt
```

### Step 3: Apply Terraform Configuration

```bash
terraform apply
```

When prompted, type **`yes`** to confirm.

**This will create:**
1. S3 bucket for OpenAPI schemas
2. Upload 3 OpenAPI schema files
3. Create 5 IAM roles (one per agent)
4. Create 5 IAM policies
5. Create 5 Bedrock Agents
6. Create 5 Agent Aliases
7. Update all agents to use Claude Sonnet 4.5

**Expected Duration:** 2-3 minutes

**Known Issue:** You may see Terraform errors about creating collaborator associations. This is expected due to a Terraform AWS provider limitation. Continue to the next step.

### Step 4: Associate Collaborators (Manual)

Due to Terraform provider limitations, we must manually associate collaborators via AWS CLI:

```bash
# Associate Scheduling Collaborator
aws bedrock-agent associate-agent-collaborator \
  --agent-id 5VTIWONUMO \
  --agent-version DRAFT \
  --agent-descriptor aliasArn=arn:aws:bedrock:us-east-1:618048437522:agent-alias/IX24FSMTQH/NOVFEOSU4F \
  --collaborator-name "scheduling_collaborator" \
  --collaboration-instruction "Route all appointment scheduling, availability checking, booking, rescheduling, and cancellation requests to this agent." \
  --region us-east-1

# Associate Information Collaborator
aws bedrock-agent associate-agent-collaborator \
  --agent-id 5VTIWONUMO \
  --agent-version DRAFT \
  --agent-descriptor aliasArn=arn:aws:bedrock:us-east-1:618048437522:agent-alias/C9ANXRIO8Y/OPWAD4NASM \
  --collaborator-name "information_collaborator" \
  --collaboration-instruction "Route all information requests to this agent, including project details, appointment status checks, working hours inquiries, and weather forecasts." \
  --region us-east-1

# Associate Notes Collaborator
aws bedrock-agent associate-agent-collaborator \
  --agent-id 5VTIWONUMO \
  --agent-version DRAFT \
  --agent-descriptor aliasArn=arn:aws:bedrock:us-east-1:618048437522:agent-alias/G5BVBYEPUM/4EIFEQLFVF \
  --collaborator-name "notes_collaborator" \
  --collaboration-instruction "Route all note management requests to this agent, including adding notes to appointments and viewing existing notes." \
  --region us-east-1

# Associate Chitchat Collaborator
aws bedrock-agent associate-agent-collaborator \
  --agent-id 5VTIWONUMO \
  --agent-version DRAFT \
  --agent-descriptor aliasArn=arn:aws:bedrock:us-east-1:618048437522:agent-alias/BIUW1ARHGL/I5IDDX1I6I \
  --collaborator-name "chitchat_collaborator" \
  --collaboration-instruction "Route all conversational interactions to this agent, including greetings, thank you messages, goodbye messages, help requests, and general friendly conversation." \
  --region us-east-1
```

**Note:** Replace agent IDs and alias ARNs with your actual values if they differ. You can find these in the Terraform output or AWS Console.

### Step 5: Prepare Supervisor Agent

After associating all collaborators, prepare the supervisor agent:

```bash
# Prepare supervisor agent with collaborators
aws bedrock-agent prepare-agent --agent-id 5VTIWONUMO --region us-east-1

# Wait 15-20 seconds for preparation to complete
sleep 20

# Verify it's prepared
aws bedrock-agent get-agent --agent-id 5VTIWONUMO --region us-east-1 | grep agentStatus
```

**Expected Output:**
```
"agentStatus": "PREPARED"
```

---

## Post-Deployment

### Verify Deployment

Run the verification script:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
./scripts/verify_deployment.sh
```

**Expected Output:**
```
==========================================
AWS Bedrock Multi-Agent Deployment Check
==========================================

✓ Checking Supervisor Agent...
Agent: scheduling-agent-supervisor | Status: PREPARED | Model: us.anthropic.claude-sonnet-4-5-20250929-v1:0

✓ Checking Collaborator Associations...
Found 4 collaborators associated with supervisor
  - information_collaborator
  - notes_collaborator
  - chitchat_collaborator
  - scheduling_collaborator

✓ Checking All Agent Statuses...
  scheduling-agent-supervisor: PREPARED
  scheduling-agent-scheduling: PREPARED
  scheduling-agent-information: PREPARED
  scheduling-agent-notes: PREPARED
  scheduling-agent-chitchat: PREPARED

✓ Checking S3 Bucket...
  Found 3 OpenAPI schema files

✓ Checking Model Access...
  Profile: US Anthropic Claude Sonnet 4.5 | Status: ACTIVE

==========================================
✅ Deployment Verification Complete!
==========================================
```

### Get Agent IDs

```bash
# List all agents
aws bedrock-agent list-agents --region us-east-1

# Get specific agent details
aws bedrock-agent get-agent --agent-id 5VTIWONUMO --region us-east-1

# List collaborators
aws bedrock-agent list-agent-collaborators \
  --agent-id 5VTIWONUMO \
  --agent-version DRAFT \
  --region us-east-1
```

### Check Terraform State

```bash
cd infrastructure/terraform

# List all managed resources
terraform state list

# Show specific resource
terraform state show aws_bedrockagent_agent.supervisor
```

---

## Testing

### Option 1: AWS Console (Recommended)

1. Navigate to: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents
2. Click on **scheduling-agent-supervisor**
3. Click the **"Test"** button in the top right corner
4. Try these test messages:

| Test Case | Input Message | Expected Behavior |
|-----------|---------------|-------------------|
| **Chitchat** | `Hello! How are you?` | Routes to chitchat_collaborator, responds warmly |
| **Scheduling** | `I want to schedule an appointment` | Routes to scheduling_collaborator, asks about project |
| **Information** | `What are your working hours?` | Routes to information_collaborator, provides hours info |
| **Notes** | `Add a note that I prefer mornings` | Routes to notes_collaborator, confirms note addition |

### Option 2: Python Test Script

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
python3 tests/test_agents_interactive.py
```

**Note:** This may fail with "Access denied" errors due to API invocation permissions. Use AWS Console testing instead.

### Option 3: AWS CLI

```bash
# Create a session
SESSION_ID=$(uuidgen)

# Note: Direct CLI invocation requires bedrock-agent-runtime API
# which has different permissions than console testing
aws bedrock-agent-runtime invoke-agent \
  --agent-id 5VTIWONUMO \
  --agent-alias-id PEXPJRXIML \
  --session-id $SESSION_ID \
  --input-text "Hello" \
  --region us-east-1
```

---

## Troubleshooting

### Issue 1: IAM Permission Denied

**Error:**
```
User: arn:aws:iam::ACCOUNT:user/USER is not authorized to perform: iam:CreateRole
```

**Solution:**
1. Add IAM permissions to your user:
   ```bash
   # Contact your AWS administrator to add these permissions:
   # - iam:CreateRole
   # - iam:CreatePolicy
   # - iam:AttachRolePolicy
   # - iam:PutRolePolicy
   ```

2. Or use a role with admin access:
   ```bash
   aws sts assume-role --role-arn arn:aws:iam::ACCOUNT:role/ADMIN_ROLE --role-session-name terraform
   ```

### Issue 2: Model Access Denied

**Error:**
```
Invocation of model ID ... with on-demand throughput isn't supported
```

**Solution:**
1. This means you're using a direct model ID instead of an inference profile
2. Update `terraform.tfvars`:
   ```hcl
   # Wrong (direct model ID):
   foundation_model = "anthropic.claude-sonnet-4-5-20250929-v1:0"

   # Correct (inference profile):
   foundation_model = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
   ```

3. Re-run terraform:
   ```bash
   terraform apply
   aws bedrock-agent prepare-agent --agent-id 5VTIWONUMO --region us-east-1
   ```

### Issue 3: Agent Collaboration Cannot Be Prepared

**Error:**
```
This agent cannot be prepared. The AgentCollaboration attribute is set to SUPERVISOR but no agent collaborators are added.
```

**Solution:**
This means collaborators weren't associated yet. Follow Step 4 in Deployment to manually associate them.

### Issue 4: Terraform Provider Bug - prepared_at Unknown

**Error:**
```
After the apply operation, the provider still indicated an unknown value for aws_bedrockagent_agent.supervisor.prepared_at
```

**Solution:**
This is a known Terraform AWS provider 6.x bug when `prepare_agent = false`. The infrastructure IS created successfully despite the error. Verify with:

```bash
aws bedrock-agent list-agents --region us-east-1
```

Then proceed to manual collaborator association (Step 4).

### Issue 5: Access Denied When Testing

**Error:**
```
Access denied when calling Bedrock. Check your request permissions
```

**Solution:**
1. Use AWS Console testing instead of programmatic API calls
2. Or add bedrock-agent-runtime permissions:
   ```json
   {
     "Effect": "Allow",
     "Action": [
       "bedrock-agent-runtime:InvokeAgent"
     ],
     "Resource": "*"
   }
   ```

### Issue 6: Agent Not Responding in Console

**Checklist:**
1. ✅ Verify agent status is "PREPARED":
   ```bash
   aws bedrock-agent get-agent --agent-id 5VTIWONUMO --region us-east-1 | grep agentStatus
   ```

2. ✅ Verify collaborators are associated:
   ```bash
   aws bedrock-agent list-agent-collaborators --agent-id 5VTIWONUMO --agent-version DRAFT --region us-east-1
   ```

3. ✅ Verify model access:
   ```bash
   aws bedrock get-inference-profile --inference-profile-identifier us.anthropic.claude-sonnet-4-5-20250929-v1:0 --region us-east-1
   ```

4. ✅ Re-prepare agent:
   ```bash
   aws bedrock-agent prepare-agent --agent-id 5VTIWONUMO --region us-east-1
   ```

---

## Clean Up (Optional)

To delete all resources:

```bash
cd infrastructure/terraform

# Preview what will be deleted
terraform plan -destroy

# Delete all resources
terraform destroy

# Type 'yes' to confirm
```

**Note:** S3 bucket must be empty before deletion. If terraform destroy fails:

```bash
# Empty S3 bucket first
aws s3 rm s3://scheduling-agent-schemas-dev-ACCOUNT_ID --recursive --region us-east-1

# Then retry destroy
terraform destroy
```

---

## Next Steps

After successful deployment:

1. **✅ Test all routing scenarios** in AWS Console
2. **🚧 Build Lambda functions** for the 12 actions
3. **🚧 Connect Lambda functions** to agent action groups
4. **🚧 Test end-to-end workflows** with real PF360 API calls
5. **🚧 Set up monitoring** with CloudWatch
6. **🚧 Configure alerts** for agent failures

---

## Support

- **Documentation**: [README.md](./README.md)
- **Deployment Status**: [DEPLOYMENT_STATUS.md](../DEPLOYMENT_STATUS.md)
- **AWS Console**: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents
- **Verification Script**: `./scripts/verify_deployment.sh`

---

## Appendix: Agent IDs Quick Reference

| Agent | ID | Alias ID | Purpose |
|-------|-----|----------|---------|
| Supervisor | `5VTIWONUMO` | `PEXPJRXIML` | Routes to specialists |
| Scheduling | `IX24FSMTQH` | `NOVFEOSU4F` | Manages appointments |
| Information | `C9ANXRIO8Y` | `OPWAD4NASM` | Provides information |
| Notes | `G5BVBYEPUM` | `4EIFEQLFVF` | Manages notes |
| Chitchat | `BIUW1ARHGL` | `I5IDDX1I6I` | Handles conversation |

**S3 Bucket:** `scheduling-agent-schemas-dev-618048437522`

**Region:** `us-east-1`

**Model:** Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`)
