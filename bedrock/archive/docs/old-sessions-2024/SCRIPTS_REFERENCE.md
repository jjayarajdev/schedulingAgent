# Deployment Scripts Reference

## 📋 Available Scripts

### 🚀 Main Deployment Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `deploy_complete.sh` | Deploy complete infrastructure from scratch | New environment setup |
| `setup_lambda_integration.sh` | Connect Lambda functions to agents | After infrastructure deployed |
| `prepare_agents.sh` | Prepare agents via AWS API | After creating/updating agents |

---

## 🎯 Detailed Script Guide

### 1️⃣ deploy_complete.sh

**Purpose:** Automates full infrastructure deployment (3 stages)

**Usage:**
```bash
cd bedrock/infrastructure/terraform
./deploy_complete.sh
```

**What it does:**
- ✅ Checks prerequisites (Terraform, AWS CLI, credentials)
- ✅ Runs `terraform init` (if needed)
- ✅ **Stage 1:** Deploys infrastructure (`terraform apply`)
- ✅ **Stage 2:** Prepares agents (`./prepare_agents.sh`)
- ✅ **Stage 3:** Creates aliases & collaborators (`terraform apply`)
- ✅ **Stage 4 (Optional):** Lambda integration (`./setup_lambda_integration.sh`)
- ✅ Verifies deployment
- ✅ Shows summary

**Duration:** ~10 minutes (without Lambda) or ~25-30 minutes (with Lambda)

**Output:**
- All agents deployed and PREPARED
- All aliases created
- All collaborators associated
- Lambda functions deployed (if Stage 4 selected)
- Action groups configured (if Stage 4 selected)
- Ready for production use

**When to use:**
- ✅ First-time deployment
- ✅ New environment (dev/staging/prod)
- ✅ After complete teardown

---

### 2️⃣ setup_lambda_integration.sh

**Purpose:** Automates Lambda function integration with agents

**Usage:**
```bash
cd bedrock/infrastructure/terraform
./setup_lambda_integration.sh
```

**What it does:**
- ✅ Deploys Lambda functions (calls `../../scripts/deploy_lambda_functions.sh`)
- ✅ Captures Lambda ARNs automatically
- ✅ Updates `variables.tf` with Lambda variables
- ✅ Creates `terraform.tfvars` with ARNs
- ✅ Runs `configure_action_groups.py` to uncomment action groups
- ✅ Deploys action groups (`terraform apply`)
- ✅ Re-prepares agents (`./prepare_agents.sh`)
- ✅ Final sync (`terraform apply`)
- ✅ Verifies action groups are attached

**Duration:** ~15-20 minutes

**Output:**
- Lambda functions deployed
- Action groups attached to agents
- Agents can call Lambda functions
- Ready for testing with real data

**When to use:**
- ✅ After infrastructure is deployed
- ✅ When you want agents to perform real actions
- ✅ Before running comprehensive tests

**Prerequisites:**
- Infrastructure must be deployed (run `deploy_complete.sh` first)
- Agents must be in PREPARED state

---

### 3️⃣ prepare_agents.sh

**Purpose:** Prepares Bedrock agents via AWS API

**Usage:**
```bash
cd bedrock/infrastructure/terraform
./prepare_agents.sh
```

**What it does:**
- ✅ Gets agent IDs from Terraform
- ✅ Prepares each agent via AWS `prepare-agent` API
- ✅ Waits for PREPARED status (with progress indicator)
- ✅ Shows colored output for success/failure

**Duration:** ~3-5 minutes

**Output:**
```
============================================================================
Preparing Bedrock Agents
============================================================================

✓ Agent IDs retrieved
  Supervisor: YZOPVMTYWY
  Scheduling: VIPX4UDKMV
  Information: 7KY3T7JUMY
  Notes: R2GXYJOYNT
  Chitchat: IIMM8V2IFX

============================================================================
Step 1: Preparing Collaborator Agents
============================================================================

✓ Scheduling Agent prepared successfully
✓ Scheduling Agent is prepared
...

✅ All agents prepared successfully!
```

**When to use:**
- ✅ After creating new agents
- ✅ After updating agent configurations
- ✅ After adding/removing action groups
- ✅ Before creating agent aliases
- ✅ Any time agents are in NOT_PREPARED state

---

### 4️⃣ configure_action_groups.py

**Purpose:** Uncomments action group resources in bedrock_agents.tf

**Usage:**
```bash
cd bedrock/infrastructure/terraform
python3 configure_action_groups.py
```

**What it does:**
- ✅ Reads `bedrock_agents.tf`
- ✅ Backs up to `bedrock_agents.tf.backup_action_groups`
- ✅ Replaces commented example with actual action group resources
- ✅ Adds scheduling, information, and notes action groups

**Duration:** < 1 second

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

**When to use:**
- ✅ As part of Lambda integration
- ✅ Usually called by `setup_lambda_integration.sh`
- ✅ Rarely run manually (automated setup handles it)

**Note:** This is typically run automatically by `setup_lambda_integration.sh`

---

## 🔄 Common Workflows

### Workflow 1: Brand New Deployment (With Lambda - Recommended)
```bash
# One command - includes everything
./deploy_complete.sh
# When prompted for Stage 4, answer "yes"

# Test
cd ../../tests
python3 comprehensive_test.py
```

**Total time:** ~25-30 minutes

---

### Workflow 1b: Brand New Deployment (Without Lambda)
```bash
# Deploy infrastructure only
./deploy_complete.sh
# When prompted for Stage 4, answer "no"

# Add Lambda later
./setup_lambda_integration.sh
```

**Total time:** ~10 minutes + ~15 minutes later

---

### Workflow 2: Update Agent Configuration
```bash
# 1. Edit bedrock_agents.tf (change instructions, etc.)

# 2. Apply changes
terraform apply

# 3. Re-prepare agents
./prepare_agents.sh

# 4. Final apply
terraform apply
```

**Total time:** ~5-10 minutes

---

### Workflow 3: Add New Action Group
```bash
# 1. Deploy new Lambda function
cd ../../scripts
./deploy_lambda_functions.sh

# 2. Get new Lambda ARN
aws lambda get-function --function-name new-actions --query 'Configuration.FunctionArn'

# 3. Add to terraform.tfvars
cd ../infrastructure/terraform
nano terraform.tfvars  # Add new ARN

# 4. Add action group resource to bedrock_agents.tf
nano bedrock_agents.tf  # Add new action group

# 5. Deploy
terraform apply
./prepare_agents.sh
terraform apply
```

**Total time:** ~10-15 minutes

---

### Workflow 4: Deploy to New Environment (Staging/Prod)
```bash
# 1. Create environment-specific tfvars
cat > staging.tfvars <<EOF
environment  = "staging"
project_name = "scheduling-agent-staging"
EOF

# 2. Deploy infrastructure
terraform apply -var-file=staging.tfvars

# 3. Prepare agents
./prepare_agents.sh

# 4. Create aliases
terraform apply -var-file=staging.tfvars

# 5. Integrate Lambda
./setup_lambda_integration.sh
```

**Total time:** ~30-35 minutes

---

## 📊 Script Dependency Chart

```
deploy_complete.sh
├── terraform init
├── terraform apply (Stage 1)
├── prepare_agents.sh
└── terraform apply (Stage 3)

setup_lambda_integration.sh
├── ../../scripts/deploy_lambda_functions.sh
├── configure_action_groups.py
├── terraform apply
├── prepare_agents.sh
└── terraform apply

prepare_agents.sh
├── terraform output (get agent IDs)
└── aws bedrock-agent prepare-agent (for each agent)
```

---

## 🎯 Quick Reference

### Which Script Should I Run?

| Scenario | Script |
|----------|--------|
| Starting from scratch | `deploy_complete.sh` |
| Infrastructure exists, need Lambda | `setup_lambda_integration.sh` |
| Agents not prepared | `prepare_agents.sh` |
| Changed agent config | `prepare_agents.sh` + `terraform apply` |
| Added action group | `terraform apply` + `prepare_agents.sh` + `terraform apply` |

---

## ⚙️ Script Locations

All scripts are in: `bedrock/infrastructure/terraform/`

```
bedrock/infrastructure/terraform/
├── deploy_complete.sh              # Full deployment
├── setup_lambda_integration.sh     # Lambda integration
├── prepare_agents.sh               # Prepare agents
└── configure_action_groups.py      # Uncomment action groups
```

Helper scripts in: `bedrock/scripts/`

```
bedrock/scripts/
├── deploy_lambda_functions.sh      # Deploy Lambda functions
├── init_database.sh                # Populate DynamoDB with test data
├── setup_monitoring.sh             # CloudWatch dashboards & alarms
└── test_lambdas.sh                 # Test Lambda functions directly
```

---

## 🔍 Verification Commands

After running any deployment script:

```bash
# Check Terraform state
terraform output

# Check agents status
aws bedrock-agent get-agent \
  --agent-id $(terraform output -raw supervisor_agent_id) \
  --query 'agent.agentStatus'

# Check collaborators
aws bedrock-agent list-agent-collaborators \
  --agent-id $(terraform output -raw supervisor_agent_id) \
  --agent-version DRAFT

# Check action groups
aws bedrock-agent list-agent-action-groups \
  --agent-id $(terraform output -raw scheduling_agent_id) \
  --agent-version DRAFT

# Run tests
cd ../../tests
python3 comprehensive_test.py
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| `DEPLOY_NEW_ENVIRONMENT.md` | Complete deployment guide |
| `LAMBDA_INTEGRATION_GUIDE.md` | Lambda integration details |
| `NEXT_STEPS.md` | Action items checklist |
| `DEPLOYMENT_SUMMARY.md` | Technical details of deployment |
| `WORK_COMPLETED.md` | What was done + troubleshooting |
| `SCRIPTS_REFERENCE.md` | This file |

---

**Last Updated:** 2025-10-20
**Status:** All scripts tested and working
