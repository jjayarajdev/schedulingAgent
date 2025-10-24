# Quick Deployment Guide

## Problem
Terraform tries to create agent aliases before agents are prepared, causing the error:
```
ValidationException: Create operation can't be performed on AgentAlias when Agent is in Not Prepared state.
```

## Solution
Use the automated 3-stage deployment scripts.

---

## Automated Deployment (Recommended)

### Step 1: Deploy Infrastructure
```bash
cd infrastructure/terraform
./deploy_stage1.sh
```

**What it does:**
- Backs up `bedrock_agents.tf`
- Temporarily disables agent alias resources
- Deploys DynamoDB, Lambda IAM, agents, and collaborators
- Creates everything EXCEPT agent aliases

### Step 2: Prepare Agents
```bash
./prepare_agents.sh
```

**What it does:**
- Retrieves agent IDs from Terraform
- Prepares each collaborator agent (scheduling, information, notes, chitchat)
- Waits for agents to reach "PREPARED" state
- Prepares supervisor agent
- Verifies all agents are ready

### Step 3: Create Aliases
```bash
./deploy_stage3.sh
```

**What it does:**
- Verifies agents are prepared
- Restores original `bedrock_agents.tf`
- Creates all agent aliases
- Cleans up temporary files

---

## Complete Command Sequence

```bash
cd infrastructure/terraform

# Stage 1: Infrastructure
./deploy_stage1.sh

# Stage 2: Prepare agents
./prepare_agents.sh

# Stage 3: Create aliases
./deploy_stage3.sh

# Verify
terraform output
```

**Total time:** ~5-10 minutes (most time is waiting for agents to prepare)

---

## What Each Script Does

### `deploy_stage1.sh`
- Creates backup of configuration
- Temporarily removes alias resources from Terraform
- Runs `terraform apply` to create:
  - DynamoDB table (`scheduling-agent-sessions-dev`)
  - Lambda IAM roles (scheduling, information, notes)
  - Bedrock agents (supervisor, 4 collaborators)
  - Agent collaborations (routing rules)

### `prepare_agents.sh`
- Gets agent IDs from Terraform state
- Calls AWS API to prepare each agent
- Waits for "PREPARED" status (required before alias creation)
- Shows progress with color-coded output

### `deploy_stage3.sh`
- Checks that agents are prepared
- Restores original Terraform configuration
- Creates agent aliases
- Enables testing and usage of agents

---

## Verification

After all stages complete:

```bash
# Check DynamoDB table
aws dynamodb describe-table \
  --table-name scheduling-agent-sessions-dev \
  --region us-east-1

# Check supervisor agent
SUPERVISOR_ID=$(terraform output -raw supervisor_agent_id)
aws bedrock-agent get-agent \
  --agent-id $SUPERVISOR_ID \
  --region us-east-1

# List aliases
ALIAS_ID=$(terraform output -raw supervisor_alias_id)
echo "Supervisor Alias: $ALIAS_ID"

# Test agent
aws bedrock-agent-runtime invoke-agent \
  --agent-id $SUPERVISOR_ID \
  --agent-alias-id $ALIAS_ID \
  --session-id "test-$(date +%s)" \
  --input-text "Show me my projects" \
  /tmp/output.txt

cat /tmp/output.txt
```

---

## Troubleshooting

### "Backup file already exists"
**Cause:** Stage 1 was already run

**Solution:**
```bash
# Check if you need to restore
ls -la bedrock_agents.tf*

# If Stage 1 failed, restore:
mv bedrock_agents.tf.backup bedrock_agents.tf
rm -f bedrock_agents.tf.disabled

# Then run Stage 1 again
./deploy_stage1.sh
```

### "Agent is not prepared"
**Cause:** Trying to run Stage 3 before Stage 2

**Solution:** Run `./prepare_agents.sh` first

### "Could not retrieve agent IDs"
**Cause:** Stage 1 didn't complete successfully

**Solution:**
```bash
# Check Terraform state
terraform state list | grep bedrock

# If agents don't exist, run Stage 1 again
./deploy_stage1.sh
```

### Script permission errors
```bash
chmod +x deploy_stage1.sh prepare_agents.sh deploy_stage3.sh
```

---

## Manual Deployment (Alternative)

If scripts don't work, deploy manually:

### Stage 1: Comment out aliases
```bash
# Edit bedrock_agents.tf
# Comment out these resources (lines 319-472):
# - aws_bedrockagent_agent_alias.supervisor
# - aws_bedrockagent_agent_alias.scheduling
# - aws_bedrockagent_agent_alias.information
# - aws_bedrockagent_agent_alias.notes
# - aws_bedrockagent_agent_alias.chitchat

# Apply
terraform apply
```

### Stage 2: Prepare manually
```bash
# Get IDs
SUPERVISOR_ID=$(terraform output -raw supervisor_agent_id)
SCHEDULING_ID=$(terraform output -raw scheduling_agent_id)
INFORMATION_ID=$(terraform output -raw information_agent_id)
NOTES_ID=$(terraform output -raw notes_agent_id)
CHITCHAT_ID=$(terraform output -raw chitchat_agent_id)

# Prepare collaborators
aws bedrock-agent prepare-agent --agent-id $SCHEDULING_ID --region us-east-1
aws bedrock-agent prepare-agent --agent-id $INFORMATION_ID --region us-east-1
aws bedrock-agent prepare-agent --agent-id $NOTES_ID --region us-east-1
aws bedrock-agent prepare-agent --agent-id $CHITCHAT_ID --region us-east-1

# Wait 2-3 minutes, then prepare supervisor
aws bedrock-agent prepare-agent --agent-id $SUPERVISOR_ID --region us-east-1

# Verify (wait for "PREPARED")
aws bedrock-agent get-agent --agent-id $SUPERVISOR_ID --region us-east-1 --query 'agent.agentStatus'
```

### Stage 3: Uncomment and apply
```bash
# Uncomment the alias resources in bedrock_agents.tf
terraform apply
```

---

## Clean Up

To destroy everything:

```bash
cd infrastructure/terraform

# Use the cleanup script (TODO: create this)
# Or manually:
terraform destroy
```

---

## Next Steps

After successful deployment:

1. **Build Lambda Layer**
   ```bash
   cd ../../lambda/shared-layer
   ./build.sh
   ```

2. **Deploy Lambda Functions**
   ```bash
   cd ../scheduling-actions
   # Update and deploy handler_v2.py
   ```

3. **Run Tests**
   ```bash
   cd ../../tests
   ./run_tests.sh
   ```

---

## Quick Reference

| Script | Purpose | Time |
|--------|---------|------|
| `deploy_stage1.sh` | Create infrastructure | 2-3 min |
| `prepare_agents.sh` | Prepare Bedrock agents | 3-5 min |
| `deploy_stage3.sh` | Create aliases | 1-2 min |

**Total:** ~10 minutes for full deployment
