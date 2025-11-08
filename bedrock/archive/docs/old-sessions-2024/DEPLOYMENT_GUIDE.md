# Terraform Deployment Guide

## Issues Fixed

### ✅ Issue 1: DynamoDB KMS Encryption Error
**Fixed:** Removed explicit KMS encryption configuration. DynamoDB now uses AWS-managed encryption by default.

### ✅ Issue 2: Bedrock Agent Alias Creation Error
**Cause:** Bedrock agents must be "prepared" before aliases can be created. The agents have `prepare_agent = false` because they need to be prepared AFTER collaborators are associated.

**Solution:** Two-stage deployment process

---

## Deployment Process

### Stage 1: Create Infrastructure Without Agent Aliases

**Option A: Temporary Workaround (Quick Fix)**

Comment out agent alias resources temporarily:

```bash
cd infrastructure/terraform

# Edit bedrock_agents.tf and comment out all agent alias resources:
# - aws_bedrockagent_agent_alias.supervisor (lines 319-328)
# - aws_bedrockagent_agent_alias.scheduling (lines 358-367)
# - aws_bedrockagent_agent_alias.information (lines 393-402)
# - aws_bedrockagent_agent_alias.notes (lines 428-437)
# - aws_bedrockagent_agent_alias.chitchat (lines 463-472)

# Then apply
terraform apply
```

**Option B: Target Specific Resources (Recommended)**

Apply only the resources that don't depend on prepared agents:

```bash
cd infrastructure/terraform

# Apply DynamoDB and Lambda IAM first
terraform apply \
  -target=aws_dynamodb_table.bedrock_sessions \
  -target=aws_iam_role.scheduling_lambda \
  -target=aws_iam_role.information_lambda \
  -target=aws_iam_role.notes_lambda \
  -target=aws_iam_role_policy.scheduling_lambda_dynamodb \
  -target=aws_iam_role_policy.information_lambda_dynamodb \
  -target=aws_iam_role_policy.notes_lambda_dynamodb

# Apply agents (without aliases)
terraform apply \
  -target=aws_bedrockagent_agent.supervisor \
  -target=aws_bedrockagent_agent.scheduling \
  -target=aws_bedrockagent_agent.information \
  -target=aws_bedrockagent_agent.notes \
  -target=aws_bedrockagent_agent.chitchat \
  -target=aws_bedrockagent_agent_collaborator.scheduling \
  -target=aws_bedrockagent_agent_collaborator.information \
  -target=aws_bedrockagent_agent_collaborator.notes \
  -target=aws_bedrockagent_agent_collaborator.chitchat
```

### Stage 2: Prepare Agents

After Stage 1 completes successfully, prepare the agents:

```bash
cd infrastructure/terraform

# Run the agent preparation script
./prepare_agents.sh
```

This script will:
1. Retrieve agent IDs from Terraform state
2. Prepare each collaborator agent (scheduling, information, notes, chitchat)
3. Wait for each agent to reach "PREPARED" state
4. Prepare the supervisor agent
5. Wait for supervisor to reach "PREPARED" state

**Expected output:**
```
============================================================================
Preparing Bedrock Agents
============================================================================

Retrieving agent IDs from Terraform...
✓ Agent IDs retrieved
  Supervisor: ABC123...
  Scheduling: DEF456...
  Information: GHI789...
  Notes: JKL012...
  Chitchat: MNO345...

============================================================================
Step 1: Preparing Collaborator Agents
============================================================================

Preparing Scheduling Agent (DEF456...)...
✓ Scheduling Agent prepared successfully
...

✅ All agents prepared successfully!
```

### Stage 3: Create Agent Aliases

Now that agents are prepared, create the aliases:

**Option A: If you commented out aliases in Stage 1**

```bash
# Uncomment the agent alias resources in bedrock_agents.tf
# Then apply
terraform apply
```

**Option B: If you used targeted apply**

```bash
# Apply the remaining resources (aliases)
terraform apply
```

This will create:
- supervisor agent alias
- scheduling agent alias
- information agent alias
- notes agent alias
- chitchat agent alias

---

## Complete Deployment Commands

Here's the full sequence:

```bash
cd infrastructure/terraform

# 1. Initialize Terraform (if not already done)
terraform init

# 2. Apply DynamoDB and Lambda IAM
terraform apply \
  -target=aws_dynamodb_table.bedrock_sessions \
  -target=aws_iam_role.scheduling_lambda \
  -target=aws_iam_role.information_lambda \
  -target=aws_iam_role.notes_lambda \
  -target=aws_iam_role_policy.scheduling_lambda_dynamodb \
  -target=aws_iam_role_policy.information_lambda_dynamodb \
  -target=aws_iam_role_policy.notes_lambda_dynamodb

# 3. Apply agents and collaborators
terraform apply \
  -target=aws_bedrockagent_agent.supervisor \
  -target=aws_bedrockagent_agent.scheduling \
  -target=aws_bedrockagent_agent.information \
  -target=aws_bedrockagent_agent.notes \
  -target=aws_bedrockagent_agent.chitchat \
  -target=aws_bedrockagent_agent_collaborator.scheduling \
  -target=aws_bedrockagent_agent_collaborator.information \
  -target=aws_bedrockagent_agent_collaborator.notes \
  -target=aws_bedrockagent_agent_collaborator.chitchat

# 4. Prepare agents
./prepare_agents.sh

# 5. Create aliases
terraform apply

# 6. Verify
terraform output
```

---

## Verification

After deployment, verify everything is working:

```bash
# Check DynamoDB table
aws dynamodb describe-table \
  --table-name scheduling-agent-sessions-dev \
  --region us-east-1

# Check agent status
SUPERVISOR_ID=$(terraform output -raw supervisor_agent_id)
aws bedrock-agent get-agent \
  --agent-id $SUPERVISOR_ID \
  --region us-east-1

# List agent aliases
aws bedrock-agent list-agent-aliases \
  --agent-id $SUPERVISOR_ID \
  --region us-east-1
```

---

## Troubleshooting

### Error: "Agent is in Not Prepared state"

**Cause:** Trying to create alias before agent is prepared

**Solution:** Run `./prepare_agents.sh` before creating aliases

### Error: KMS key does not exist

**Cause:** DynamoDB trying to use non-existent customer-managed KMS key

**Solution:** Already fixed in `dynamodb.tf`. Pull latest version.

### Error: "Resource not found"

**Cause:** Agents don't exist yet

**Solution:** Make sure Stage 1 completed successfully before Stage 2

### Timeout waiting for agent to be prepared

**Cause:** Agent preparation takes longer than expected

**Solution:**
- Check CloudWatch logs for errors
- Verify IAM permissions are correct
- Try preparing agent manually:
  ```bash
  aws bedrock-agent prepare-agent --agent-id AGENT_ID --region us-east-1
  ```

---

## Alternative: Manual Preparation

If the script doesn't work, prepare agents manually:

```bash
# Get agent IDs
SUPERVISOR_ID=$(terraform output -raw supervisor_agent_id)
SCHEDULING_ID=$(terraform output -raw scheduling_agent_id)
INFORMATION_ID=$(terraform output -raw information_agent_id)
NOTES_ID=$(terraform output -raw notes_agent_id)
CHITCHAT_ID=$(terraform output -raw chitchat_agent_id)

# Prepare collaborators first
aws bedrock-agent prepare-agent --agent-id $SCHEDULING_ID --region us-east-1
aws bedrock-agent prepare-agent --agent-id $INFORMATION_ID --region us-east-1
aws bedrock-agent prepare-agent --agent-id $NOTES_ID --region us-east-1
aws bedrock-agent prepare-agent --agent-id $CHITCHAT_ID --region us-east-1

# Wait a few minutes, then check status
aws bedrock-agent get-agent --agent-id $SCHEDULING_ID --region us-east-1 --query 'agent.agentStatus'

# Once all collaborators are PREPARED, prepare supervisor
aws bedrock-agent prepare-agent --agent-id $SUPERVISOR_ID --region us-east-1

# Wait and verify
aws bedrock-agent get-agent --agent-id $SUPERVISOR_ID --region us-east-1 --query 'agent.agentStatus'
```

---

## Next Steps

After successful deployment:

1. **Deploy Lambda Layer**
   ```bash
   cd ../../lambda/shared-layer
   ./build.sh
   ```

2. **Deploy Lambda Functions**
   ```bash
   cd ../scheduling-actions
   ./deploy.sh
   ```

3. **Run Tests**
   ```bash
   cd ../../tests
   ./run_tests.sh
   ```

4. **Test with Bedrock Agent**
   ```bash
   cd ../../tests
   python3 comprehensive_test.py
   ```

---

## Clean Up

To destroy all resources:

```bash
cd infrastructure/terraform

# Destroy aliases first
terraform destroy \
  -target=aws_bedrockagent_agent_alias.supervisor \
  -target=aws_bedrockagent_agent_alias.scheduling \
  -target=aws_bedrockagent_agent_alias.information \
  -target=aws_bedrockagent_agent_alias.notes \
  -target=aws_bedrockagent_agent_alias.chitchat

# Then destroy agents and collaborators
terraform destroy \
  -target=aws_bedrockagent_agent_collaborator.scheduling \
  -target=aws_bedrockagent_agent_collaborator.information \
  -target=aws_bedrockagent_agent_collaborator.notes \
  -target=aws_bedrockagent_agent_collaborator.chitchat \
  -target=aws_bedrockagent_agent.supervisor \
  -target=aws_bedrockagent_agent.scheduling \
  -target=aws_bedrockagent_agent.information \
  -target=aws_bedrockagent_agent.notes \
  -target=aws_bedrockagent_agent.chitchat

# Finally destroy DynamoDB and Lambda IAM
terraform destroy
```
