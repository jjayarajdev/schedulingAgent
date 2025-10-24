# Lambda Integration - Quick Start Guide

## 🎯 Purpose

Connect your Bedrock agents to AWS Lambda functions so they can perform real actions (scheduling, information lookup, notes management).

## 📋 Prerequisites

Before running the integration:
- ✅ Bedrock agents deployed (already done)
- ✅ Agent aliases created (already done)
- ✅ Lambda IAM roles created (already done)
- ✅ AWS CLI configured with proper credentials

## 🚀 One-Command Setup (Recommended)

### Simple Automated Setup

```bash
cd bedrock/infrastructure/terraform
./setup_lambda_integration.sh
```

**What this does:**
1. ✅ Deploys all 3 Lambda functions
2. ✅ Captures Lambda ARNs automatically
3. ✅ Updates `variables.tf` with Lambda variables
4. ✅ Creates `terraform.tfvars` with ARNs
5. ✅ Uncomments action group resources
6. ✅ Deploys action groups to agents
7. ✅ Re-prepares agents
8. ✅ Verifies deployment

**Duration:** ~15-20 minutes (mostly Lambda deployment time)

**What you'll see:**
```
================================================================================
  🔧 Lambda Integration Setup
================================================================================

  Step 1: Deploy Lambda Functions
  ...deploying Lambda functions...

  Step 2: Update Terraform Configuration
  ✅ Lambda ARNs captured
  ✅ Added Lambda variables to variables.tf
  ✅ Created terraform.tfvars

  Step 3: Configure Action Groups
  ✅ Action groups uncommented successfully

  Step 4: Deploy Action Groups
  ...terraform apply...

  Step 5: Prepare Agents
  ...preparing agents...

  Step 6: Final Terraform Apply
  ...final sync...

  ✅ Lambda Integration Complete!
```

---

## 🔧 Manual Setup (If You Prefer Step-by-Step)

### Step 1: Deploy Lambda Functions
```bash
cd ../../scripts
./deploy_lambda_functions.sh
```

**Output will show:**
```
Lambda Function ARNs:
  scheduling-actions:  arn:aws:lambda:us-east-1:xxxxx:function:scheduling-actions
  information-actions: arn:aws:lambda:us-east-1:xxxxx:function:information-actions
  notes-actions:       arn:aws:lambda:us-east-1:xxxxx:function:notes-actions
```

**Copy these ARNs** - you'll need them in the next steps.

---

### Step 2: Update Terraform Variables

```bash
cd ../infrastructure/terraform

# Add variables to variables.tf
cat >> variables.tf <<'EOF'

variable "scheduling_lambda_arn" {
  description = "ARN of the scheduling Lambda function"
  type        = string
  default     = ""
}

variable "information_lambda_arn" {
  description = "ARN of the information Lambda function"
  type        = string
  default     = ""
}

variable "notes_lambda_arn" {
  description = "ARN of the notes Lambda function"
  type        = string
  default     = ""
}
EOF
```

---

### Step 3: Create terraform.tfvars

```bash
cat > terraform.tfvars <<EOF
scheduling_lambda_arn  = "arn:aws:lambda:us-east-1:xxxxx:function:scheduling-actions"
information_lambda_arn = "arn:aws:lambda:us-east-1:xxxxx:function:information-actions"
notes_lambda_arn       = "arn:aws:lambda:us-east-1:xxxxx:function:notes-actions"
EOF
```

Replace the ARNs with your actual ARNs from Step 1.

---

### Step 4: Configure Action Groups

```bash
python3 configure_action_groups.py
```

**Output:**
```
🔧 Configuring Action Groups...
✅ Backed up original to bedrock_agents.tf.backup_action_groups
✅ Action groups uncommented successfully

📋 Added action groups:
   • scheduling_actions
   • information_actions
   • notes_actions
```

---

### Step 5: Deploy Action Groups

```bash
terraform plan
terraform apply
```

---

### Step 6: Re-Prepare Agents

After adding action groups, agents need to be re-prepared:

```bash
./prepare_agents.sh
```

---

### Step 7: Final Apply

```bash
terraform apply
```

---

## ✅ Verification

### Check Action Groups Are Attached

```bash
# Get agent IDs
SCHEDULING_ID=$(terraform output -raw scheduling_agent_id)
INFORMATION_ID=$(terraform output -raw information_agent_id)
NOTES_ID=$(terraform output -raw notes_agent_id)

# Check each agent's action groups
aws bedrock-agent list-agent-action-groups \
  --agent-id $SCHEDULING_ID \
  --agent-version DRAFT \
  --region us-east-1

# Should show: scheduling-actions (ENABLED)
```

### Test Lambda Integration

```bash
cd ../../tests
python3 comprehensive_test.py
```

**Expected output:**
```
Total Tests: 18
Passed: ✅ 18 (100.0%)
```

---

## 📁 Files Created/Modified

### Created:
- ✅ `terraform.tfvars` - Lambda ARNs configuration
- ✅ `bedrock_agents.tf.backup_action_groups` - Backup of original

### Modified:
- ✅ `variables.tf` - Added Lambda ARN variables
- ✅ `bedrock_agents.tf` - Uncommented action groups

---

## 🐛 Troubleshooting

### Issue: Lambda deployment fails

**Check IAM permissions:**
```bash
aws iam get-role --role-name scheduling-agent-scheduling-lambda-role-dev
```

**Check if function exists:**
```bash
aws lambda get-function --function-name scheduling-actions
```

---

### Issue: Action groups won't apply

**Check agent is PREPARED:**
```bash
aws bedrock-agent get-agent \
  --agent-id $(terraform output -raw scheduling_agent_id) \
  --query 'agent.agentStatus'
```

Should output: `"PREPARED"`

**Re-prepare if needed:**
```bash
./prepare_agents.sh
```

---

### Issue: Can't extract Lambda ARNs

**Get them manually:**
```bash
aws lambda get-function --function-name scheduling-actions --query 'Configuration.FunctionArn' --output text
aws lambda get-function --function-name information-actions --query 'Configuration.FunctionArn' --output text
aws lambda get-function --function-name notes-actions --query 'Configuration.FunctionArn' --output text
```

---

## 🔄 Rollback

If something goes wrong:

### Restore Original Configuration

```bash
# Restore bedrock_agents.tf
cp bedrock_agents.tf.backup_action_groups bedrock_agents.tf

# Remove terraform.tfvars
rm terraform.tfvars

# Remove Lambda variables from variables.tf
# (manually edit and remove the Lambda variables section)

# Apply to remove action groups
terraform apply
```

---

## 📊 What Happens After Integration

### Before Integration:
```
User: "Schedule an appointment"
Agent: "I can help you schedule an appointment. What time works for you?"
       (conversational only, no real action taken)
```

### After Integration:
```
User: "Schedule an appointment"
Agent: → Calls scheduling Lambda function
       → Gets available time slots from DynamoDB
       → Returns: "I found 3 available slots:
                   - Tomorrow at 10:00 AM
                   - Tomorrow at 2:00 PM
                   - Friday at 9:00 AM
                   Which would you prefer?"
       (real data, real actions)
```

---

## 🎯 Success Criteria

You're done when:
- [ ] All Lambda functions deployed
- [ ] terraform.tfvars contains Lambda ARNs
- [ ] Action groups visible in `terraform state list`
- [ ] All agents showing PREPARED status
- [ ] `comprehensive_test.py` shows 18/18 passing
- [ ] Agents returning real data (not just conversational)

---

## 📖 Related Documentation

- `NEXT_STEPS.md` - Overall action items
- `DEPLOYMENT_SUMMARY.md` - Infrastructure overview
- `../../scripts/README.md` - Lambda deployment details
- `../../docs/PRODUCTION_IMPLEMENTATION.md` - Integration patterns

---

## ⚡ Quick Commands Reference

```bash
# Automated setup (recommended)
./setup_lambda_integration.sh

# Manual step-by-step
cd ../../scripts && ./deploy_lambda_functions.sh
cd ../infrastructure/terraform
python3 configure_action_groups.py
terraform apply
./prepare_agents.sh
terraform apply

# Verify
terraform output
cd ../../tests && python3 comprehensive_test.py

# Monitor
aws logs tail /aws/lambda/scheduling-actions --follow
aws logs tail /aws/bedrock/agents/$(terraform output -raw supervisor_agent_id) --follow
```

---

**Status:** Ready to integrate
**Estimated Time:** 15-20 minutes (automated) or 30-40 minutes (manual)
**Difficulty:** Easy (automated) or Medium (manual)
