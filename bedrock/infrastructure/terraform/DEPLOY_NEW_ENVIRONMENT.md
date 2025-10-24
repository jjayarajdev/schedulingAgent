# Deploy to New Environment - Step-by-Step

## Prerequisites

### 1. AWS Configuration
```bash
# Configure AWS credentials
aws configure

# Verify access
aws sts get-caller-identity

# Request Claude Sonnet 4.5 model access (if not already done)
# Go to AWS Console > Bedrock > Model access
# Request: us.anthropic.claude-sonnet-4-5-20250929-v1:0
```

### 2. Required Tools
```bash
# Terraform >= 1.0
terraform --version

# AWS CLI >= 2.0
aws --version

# jq (optional, for JSON parsing)
which jq
```

## Deployment Steps

### Step 1: Navigate to Terraform Directory
```bash
cd bedrock/infrastructure/terraform
```

### Step 2: Initialize Terraform
```bash
terraform init
```

Expected output:
```
Initializing the backend...
Initializing provider plugins...
Terraform has been successfully initialized!
```

### Step 3: Configure Variables (Optional)
Create `terraform.tfvars` if you want custom values:

```bash
cat > terraform.tfvars <<EOF
environment      = "dev"
aws_region       = "us-east-1"
project_name     = "scheduling-agent"
foundation_model = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
EOF
```

Or use defaults from `variables.tf`.

### Step 4: STAGE 1 - Deploy Infrastructure
```bash
terraform plan
terraform apply
```

**What this creates:**
- 5 Bedrock agents (NOT prepared yet)
- DynamoDB session table
- S3 bucket for OpenAPI schemas
- Lambda IAM roles
- All supporting IAM policies

**Duration:** ~2-3 minutes

**Verification:**
```bash
terraform output
# Should show agent IDs but NO alias IDs yet
```

### Step 5: STAGE 2 - Prepare Agents
```bash
./prepare_agents.sh
```

**What this does:**
- Gets agent IDs from Terraform
- Calls AWS API to prepare each agent
- Waits for all agents to reach PREPARED status
- Shows progress with colored output

**Duration:** ~3-5 minutes

**Expected output:**
```
============================================================================
Preparing Bedrock Agents
============================================================================

✓ Agent IDs retrieved
  Supervisor: XXXXXXXXXX
  Scheduling: XXXXXXXXXX
  Information: XXXXXXXXXX
  Notes: XXXXXXXXXX
  Chitchat: XXXXXXXXXX

============================================================================
Step 1: Preparing Collaborator Agents
============================================================================

✓ Scheduling Agent prepared successfully
✓ Scheduling Agent is prepared

✓ Information Agent prepared successfully
✓ Information Agent is prepared

✓ Notes Agent prepared successfully
✓ Notes Agent is prepared

✓ Chitchat Agent prepared successfully
✓ Chitchat Agent is prepared

============================================================================
Step 2: Preparing Supervisor Agent
============================================================================

✓ Supervisor Agent prepared successfully
✓ Supervisor Agent is prepared

============================================================================
✅ All agents prepared successfully!
============================================================================
```

### Step 6: STAGE 3 - Create Aliases and Collaborators
```bash
terraform apply
```

**What this creates:**
- 5 agent aliases (v1)
- 4 collaborator associations
- Supervisor alias (main entry point)

**Duration:** ~1-2 minutes

**Note:** You may see provider warnings about `relay_conversation_history` - these are cosmetic and can be ignored. Resources are created successfully.

### Step 7: Verify Deployment
```bash
# View all outputs
terraform output

# Should now show:
# - supervisor_alias_id
# - supervisor_alias_arn
# - All agent IDs
# - DynamoDB table name
# - S3 bucket name

# Verify collaborators are associated
aws bedrock-agent list-agent-collaborators \
  --agent-id $(terraform output -raw supervisor_agent_id) \
  --agent-version DRAFT \
  --region us-east-1

# Should show 4 collaborators:
# - scheduling_collaborator
# - information_collaborator
# - notes_collaborator
# - chitchat_collaborator
```

## Complete Deployment Script

For convenience, here's the complete sequence:

```bash
#!/bin/bash
set -e

echo "=== Bedrock Multi-Agent Deployment ==="
echo ""

# Step 1: Navigate to directory
cd bedrock/infrastructure/terraform

# Step 2: Initialize Terraform
echo "Step 1: Initializing Terraform..."
terraform init
echo "✓ Terraform initialized"
echo ""

# Step 3: Stage 1 - Deploy infrastructure
echo "Step 2: Deploying infrastructure (Stage 1)..."
terraform apply -auto-approve
echo "✓ Infrastructure deployed"
echo ""

# Step 4: Stage 2 - Prepare agents
echo "Step 3: Preparing agents (Stage 2)..."
./prepare_agents.sh
echo "✓ Agents prepared"
echo ""

# Step 5: Stage 3 - Create aliases and collaborators
echo "Step 4: Creating aliases and collaborators (Stage 3)..."
terraform apply -auto-approve
echo "✓ Aliases and collaborators created"
echo ""

# Step 6: Verify
echo "Step 5: Verifying deployment..."
echo ""
terraform output
echo ""

echo "=== Deployment Complete ==="
echo ""
echo "Supervisor Agent ARN:"
terraform output -raw supervisor_alias_arn
echo ""
echo ""
echo "Test with:"
echo "  cd ../../tests"
echo "  python3 test_agent.py"
```

## Expected Total Time

| Stage | Duration | Description |
|-------|----------|-------------|
| Init  | 30s      | Terraform initialization |
| Stage 1 | 2-3 min | Deploy agents & infrastructure |
| Stage 2 | 3-5 min | Prepare agents via AWS API |
| Stage 3 | 1-2 min | Create aliases & collaborators |
| **Total** | **~7-11 min** | **Complete deployment** |

## Verification Commands

### Check Agent Status
```bash
AGENT_ID=$(terraform output -raw supervisor_agent_id)
aws bedrock-agent get-agent \
  --agent-id $AGENT_ID \
  --region us-east-1 \
  --query 'agent.agentStatus' \
  --output text
```

Should output: `PREPARED`

### List All Collaborators
```bash
aws bedrock-agent list-agent-collaborators \
  --agent-id $(terraform output -raw supervisor_agent_id) \
  --agent-version DRAFT \
  --region us-east-1 \
  --query 'agentCollaboratorSummaries[*].[collaboratorName,collaboratorId]' \
  --output table
```

Should show 4 collaborators.

### Test the Agent
```bash
cd ../../tests

# Quick test
python3 test_agent.py

# Comprehensive test
python3 comprehensive_test.py
```

## Troubleshooting

### Issue: "No such file or directory: prepare_agents.sh"
```bash
# Make sure you're in the terraform directory
pwd  # Should end with: /bedrock/infrastructure/terraform

# Make script executable
chmod +x prepare_agents.sh

# Run from correct directory
./prepare_agents.sh
```

### Issue: "Agent is in Not Prepared state"
```bash
# This means you skipped Stage 2
# Run prepare_agents.sh before Stage 3
./prepare_agents.sh

# Then retry Stage 3
terraform apply
```

### Issue: "Model access denied"
```bash
# Request model access in AWS Console
# Bedrock > Model access > Request access
# Model: us.anthropic.claude-sonnet-4-5-20250929-v1:0
# Region: us-east-1

# Wait 2-5 minutes for approval
# Verify access:
aws bedrock list-foundation-models \
  --region us-east-1 \
  --by-provider anthropic \
  --query 'modelSummaries[?modelId==`us.anthropic.claude-sonnet-4-5-20250929-v1:0`]'
```

### Issue: "Provider returned invalid result"
**Status:** This is a cosmetic warning from the Terraform provider.
**Action:** Ignore it - resources are created successfully.
**Verification:** Run `terraform output` to confirm all resources exist.

## Clean Deployment (If Redeploying)

### Option 1: Destroy and Redeploy
```bash
# Destroy everything
terraform destroy

# Redeploy from scratch
terraform apply
./prepare_agents.sh
terraform apply
```

### Option 2: Remove Specific Resources
```bash
# Remove only aliases and collaborators (keep agents)
terraform state rm aws_bedrockagent_agent_alias.supervisor
terraform state rm aws_bedrockagent_agent_alias.scheduling
terraform state rm aws_bedrockagent_agent_alias.information
terraform state rm aws_bedrockagent_agent_alias.notes
terraform state rm aws_bedrockagent_agent_alias.chitchat
terraform state rm aws_bedrockagent_agent_collaborator.scheduling
terraform state rm aws_bedrockagent_agent_collaborator.information
terraform state rm aws_bedrockagent_agent_collaborator.notes
terraform state rm aws_bedrockagent_agent_collaborator.chitchat

# Recreate
terraform apply
```

## Different Environments

### Deploy to Development
```bash
# Use default variables (already set to dev)
terraform apply
```

### Deploy to Staging
```bash
# Create staging.tfvars
cat > staging.tfvars <<EOF
environment  = "staging"
project_name = "scheduling-agent-staging"
EOF

# Deploy
terraform apply -var-file=staging.tfvars
```

### Deploy to Production
```bash
# Create production.tfvars
cat > production.tfvars <<EOF
environment  = "prod"
project_name = "scheduling-agent-prod"
EOF

# Deploy
terraform apply -var-file=production.tfvars
```

## What Gets Created

### AWS Resources (35 total)
- 5 × Bedrock Agents
- 5 × Agent Aliases
- 4 × Agent Collaborators
- 1 × DynamoDB Table
- 1 × S3 Bucket
- 3 × S3 Objects (OpenAPI schemas)
- 8 × IAM Roles
- 8 × IAM Role Policies

### Terraform State
- terraform.tfstate (current state)
- terraform.tfstate.backup (previous state)

### Cost Estimate
- Bedrock Agents: Pay per invocation (~$0.003 per 1000 tokens)
- DynamoDB: On-demand pricing (minimal for sessions)
- S3: Negligible (< $0.01/month for schemas)
- IAM: Free

**Estimated monthly cost:** < $10 for development/testing

## Next Steps After Deployment

1. **Test the deployment**
   ```bash
   cd ../../tests
   python3 comprehensive_test.py
   ```

2. **Deploy Lambda functions** (if using action groups)
   ```bash
   cd ../../lambda
   # Deploy your Lambda functions
   # Then add action groups to agents
   ```

3. **Set up monitoring**
   - Enable CloudWatch logs
   - Set up alarms for errors
   - Create CloudWatch dashboard

4. **Production hardening**
   - Enable Bedrock guardrails
   - Configure rate limiting
   - Set up CloudTrail audit logging
   - Implement backup automation

## Quick Reference

```bash
# Complete deployment from scratch
cd bedrock/infrastructure/terraform
terraform init
terraform apply              # Stage 1
./prepare_agents.sh          # Stage 2
terraform apply              # Stage 3

# Verify
terraform output
aws bedrock-agent list-agent-collaborators \
  --agent-id $(terraform output -raw supervisor_agent_id) \
  --agent-version DRAFT \
  --region us-east-1

# Test
cd ../../tests
python3 comprehensive_test.py
```

---

**That's it!** Follow these steps in order, and you'll have a fully functional multi-agent system deployed in ~10 minutes.
