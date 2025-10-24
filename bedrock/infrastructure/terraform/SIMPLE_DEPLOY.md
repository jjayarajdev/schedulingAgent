# Simple Terraform Deployment

## ✅ Configuration Fixed!

The following issues have been resolved:
1. ✅ Variables moved to separate `variables.tf` file
2. ✅ Agent aliases commented out (for Stage 1)
3. ✅ Collaborators updated to use agent IDs instead of alias ARNs
4. ✅ Alias outputs commented out
5. ✅ DynamoDB encryption fixed

## Deployment Steps

### Stage 1: Deploy Infrastructure

```bash
cd infrastructure/terraform

# Deploy everything except agent aliases
terraform apply
```

This will create:
- ✅ DynamoDB table (`scheduling-agent-sessions-dev`)
- ✅ Lambda IAM roles
- ✅ S3 bucket for schemas
- ✅ Bedrock agents (5 agents)
- ✅ Agent collaborations (routing rules)

**Note:** Agent aliases are intentionally skipped for now.

---

### Stage 2: Prepare Agents

After Stage 1 completes:

```bash
./prepare_agents.sh
```

This will:
1. Get agent IDs from Terraform
2. Prepare each agent via AWS API
3. Wait for "PREPARED" status
4. Show progress

**Time:** ~3-5 minutes

---

### Stage 3: Create Aliases

After agents are prepared:

```bash
# Uncomment alias resources in bedrock_agents.tf
# Then apply
terraform apply
```

To uncomment aliases, you can:
1. Manually remove the `#` from lines 296-305, 335-344, 370-379, 405-414, 440-449, 577-585
2. OR use the `deploy_stage3.sh` script (still needs fixes)

---

## Quick Verification

After each stage:

```bash
# Check what was created
terraform state list

# Check specific resource
terraform show aws_dynamodb_table.bedrock_sessions

# Get agent IDs
terraform output
```

---

## Current Status

Your configuration is now ready for Stage 1 deployment. Just run:

```bash
terraform apply
```

And follow with Stage 2 (prepare_agents.sh) once it completes successfully.
