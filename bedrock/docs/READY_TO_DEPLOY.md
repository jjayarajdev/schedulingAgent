# ✅ Infrastructure Ready to Deploy

**Status:** Terraform configuration validated and plan generated successfully
**Date:** October 12, 2025
**Resources to Create:** 61 AWS resources
**Estimated Cost:** $114-134/month (dev environment)

---

## ✅ Completed Steps

1. ✅ **AWS Infrastructure Setup**
   - S3 bucket: `projectsforce-terraform-state-618048437522`
   - DynamoDB table: `terraform-lock`
   - Secrets Manager: 3 secrets created
   - CloudWatch log groups: 3 created
   - Billing alarms: 2 created ($100, $200 thresholds)

2. ✅ **Terraform Configuration**
   - All 10 Terraform files created
   - Backend configured (S3 + DynamoDB)
   - Variables defined (terraform.tfvars)
   - Outputs defined (25 outputs)

3. ✅ **Terraform Validation**
   - `terraform init` ✅ Successful
   - `terraform validate` ✅ Configuration valid
   - `terraform plan` ✅ Plan generated (61 resources)
   - Plan saved to: `tfplan`

---

## 📊 Infrastructure to Be Created

### Summary: 61 Resources

**Network Layer (18 resources):**
- 1 VPC
- 1 Internet Gateway
- 2 Public Subnets
- 2 Private Subnets
- 2 Elastic IPs
- 2 NAT Gateways
- 1 Public Route Table
- 2 Private Route Tables
- 4 Route Table Associations
- 3 Security Groups (Aurora, Redis, Application)
- 1 S3 VPC Endpoint
- 2 VPC Endpoint Route Table Associations

**Database Layer (10 resources):**
- 1 Aurora PostgreSQL Serverless v2 Cluster
- 1 Aurora Instance (db.serverless)
- 1 DB Subnet Group
- 1 Cluster Parameter Group
- 1 Instance Parameter Group
- 1 KMS Key for encryption
- 1 KMS Alias
- 1 CloudWatch Log Group
- 1 IAM Role (RDS monitoring)
- 1 IAM Role Policy Attachment

**Cache Layer (8 resources):**
- 1 ElastiCache Redis Cluster (Redis 7.1)
- 1 ElastiCache Subnet Group
- 1 Parameter Group
- 2 CloudWatch Log Groups (slow-log, engine-log)
- 1 SNS Topic
- 3 CloudWatch Alarms (CPU, memory, evictions)

**IAM Layer (12 resources):**
- 4 IAM Roles:
  - ECS Task Execution Role
  - ECS Task Role
  - Lambda Execution Role
  - Bedrock Agent Service Role
- 2 Managed Policy Attachments
- 6 Inline IAM Policies

**Bedrock Layer (4 resources):**
- 1 Bedrock Agent (Claude 3.5 Sonnet)
- 2 Agent Aliases (prod, dev)
- 1 CloudWatch Log Group

**Secrets Layer (6 resources):**
- 3 Data Sources (existing secrets):
  - Aurora master password
  - JWT secret key
  - PF360 API credentials
- 3 Secret Version Data Sources

**Other (3 resources):**
- 2 Data Sources (AWS account, region)
- 1 SNS Topic (ElastiCache notifications)

---

## 📤 Terraform Outputs (25)

**Network:**
- `vpc_id`
- `public_subnet_ids` (2 subnets)
- `private_subnet_ids` (2 subnets)

**Database:**
- `aurora_cluster_endpoint` (sensitive)
- `aurora_cluster_reader_endpoint` (sensitive)
- `aurora_cluster_id`
- `aurora_database_name` = "scheduling_agent"

**Cache:**
- `redis_endpoint` (sensitive)
- `redis_port`

**IAM:**
- `ecs_task_execution_role_arn`
- `ecs_task_role_arn`
- `lambda_execution_role_arn`
- `bedrock_agent_role_arn`

**Bedrock:**
- `bedrock_agent_id`
- `bedrock_agent_arn`
- `bedrock_agent_name` = "scheduling-agent"
- `bedrock_agent_version`
- `bedrock_agent_alias_prod_id`
- `bedrock_agent_alias_dev_id`

**Secrets:**
- `aurora_password_arn` (sensitive)
- `jwt_secret_arn` (sensitive)
- `pf360_credentials_arn` (sensitive)

**General:**
- `environment` = "dev"
- `region` = "us-east-1"

---

## ⏳ What's Blocking Deployment

**ONLY ONE THING:** Bedrock model access approval (24-48 hours)

### Check Bedrock Approval Status

**Via CLI:**
```bash
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query 'modelSummaries[?contains(modelId, `claude-3-5-sonnet`)].modelId' \
  --output text
```

**Expected output when approved:**
```
anthropic.claude-3-5-sonnet-20240620-v1:0
```

**Via Console:**
```bash
open https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess
```

**When approved:**
- Status will change from "Access requested" to "Access granted"
- You'll receive email notification
- Model will appear in CLI output above

---

## 🚀 Deploy Infrastructure (After Bedrock Approval)

### Step 1: Verify Bedrock Access

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/

# Check Bedrock access
aws bedrock list-foundation-models --region us-east-1 | grep claude-3-5-sonnet
```

If you see the model ID, proceed to next step.

---

### Step 2: Apply Infrastructure

```bash
# Apply the saved plan
terraform apply tfplan

# Or generate a fresh plan and apply
terraform apply

# Type 'yes' when prompted
```

**Duration:** 15-20 minutes

**Resources created in order:**
1. Network resources (VPC, subnets, NAT) - 2-3 min
2. Security groups - instant
3. KMS keys - instant
4. IAM roles - instant
5. Aurora cluster - 8-10 min
6. Redis cluster - 5-7 min
7. Bedrock Agent - 2-3 min
8. CloudWatch resources - instant

---

### Step 3: Save Outputs

```bash
# Save all outputs to JSON
terraform output -json > ../outputs.json

# View key outputs
echo "=== Infrastructure Outputs ==="
echo ""
echo "VPC ID:"
terraform output vpc_id
echo ""
echo "Aurora Endpoint:"
terraform output aurora_cluster_endpoint
echo ""
echo "Redis Endpoint:"
terraform output redis_endpoint
echo ""
echo "Bedrock Agent ID:"
terraform output bedrock_agent_id
```

---

### Step 4: Update Backend .env File

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/backend/

# Get infrastructure endpoints
AURORA_ENDPOINT=$(cd ../infrastructure && terraform output -raw aurora_cluster_endpoint)
REDIS_ENDPOINT=$(cd ../infrastructure && terraform output -raw redis_endpoint)
BEDROCK_AGENT_ID=$(cd ../infrastructure && terraform output -raw bedrock_agent_id)

# Get secrets
AURORA_PASSWORD=$(aws secretsmanager get-secret-value --secret-id scheduling-agent/aurora/master-password --query SecretString --output text)
JWT_SECRET=$(aws secretsmanager get-secret-value --secret-id scheduling-agent/jwt/secret-key --query SecretString --output text)

# Update .env file
cat > .env <<EOF
# Environment
ENVIRONMENT=dev

# Database
DATABASE_URL=postgresql+asyncpg://dbadmin:${AURORA_PASSWORD}@${AURORA_ENDPOINT}:5432/scheduling_agent

# Redis
REDIS_URL=redis://${REDIS_ENDPOINT}:6379/0

# AWS Bedrock
AWS_REGION=us-east-1
BEDROCK_AGENT_ID=${BEDROCK_AGENT_ID}
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0

# PF360 API (from current system)
CUSTOMER_SCHEDULER_API_URL=https://your-pf360-api-url.com

# Secrets
JWT_SECRET_KEY=${JWT_SECRET}

# Feature Flags
CONFIRM_SCHEDULE_FLAG=1
CANCEL_SCHEDULE_FLAG=1
EOF

echo "✅ .env file created with infrastructure endpoints"
```

---

## 💰 Cost Breakdown

**Monthly costs (after deployment):**

| Service | Configuration | Cost/Month |
|---------|--------------|-----------|
| Aurora Serverless v2 | 0.5-1.0 ACU, 20GB | $25-40 |
| ElastiCache Redis | t4g.micro, 1 node | $12 |
| NAT Gateway | 2 AZs × $32.50 | $65 |
| Data Transfer | Minimal | $5-10 |
| CloudWatch | Logs + Metrics | $5 |
| KMS | 1 key | $1 |
| Secrets Manager | 3 secrets | $1.20 |
| S3 (Terraform state) | Minimal | $0.10 |
| **SUBTOTAL** | | **$114-134** |

**After adding Bedrock Agent + ECS + Lambda:**
- Bedrock usage: +$15-30
- ECS Fargate: +$15
- Lambda: +$5
- **TOTAL:** **$149-184/month**

---

## 🔍 Verification After Deployment

```bash
# Check all resources are created
terraform show | grep "aws_" | grep "resource" | wc -l
# Should show: 61

# Check Aurora status
aws rds describe-db-clusters \
  --db-cluster-identifier scheduling-agent-dev-aurora \
  --query 'DBClusters[0].Status'
# Expected: "available"

# Check Redis status
aws elasticache describe-cache-clusters \
  --cache-cluster-id scheduling-agent-dev-redis \
  --query 'CacheClusters[0].CacheClusterStatus'
# Expected: "available"

# Check Bedrock Agent
aws bedrock-agent get-agent \
  --agent-id $(terraform output -raw bedrock_agent_id) \
  --query 'agent.agentStatus'
# Expected: "PREPARED"

# Check VPC
aws ec2 describe-vpcs \
  --vpc-ids $(terraform output -raw vpc_id) \
  --query 'Vpcs[0].State'
# Expected: "available"
```

---

## 📝 Next Steps After Deployment

### Week 2: Backend Development

1. **Set up Python environment**
   ```bash
   cd backend/
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Create database models** (SQLAlchemy)
   - Session model
   - Project model
   - Appointment model
   - User model

3. **Create API endpoints** (FastAPI)
   - GET /api/healthz
   - POST /api/chat
   - GET /api/sessions/{session_id}

4. **Integrate Bedrock Agent**
   - Bedrock service client
   - Agent invocation
   - Response parsing

5. **Database migrations** (Alembic)
   ```bash
   alembic revision --autogenerate -m "Initial schema"
   alembic upgrade head
   ```

6. **Run locally**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

---

### Week 3: Lambda Functions

Create 7 Lambda functions for PF360 integration:

1. `lambda-get-projects` - Get available projects
2. `lambda-get-working-days` - Get business hours
3. `lambda-get-available-dates` - Get available dates
4. `lambda-get-slots` - Get time slots
5. `lambda-confirm-schedule` - Confirm appointment
6. `lambda-cancel-schedule` - Cancel appointment
7. `lambda-add-note` - Add project note

Deploy Lambda functions and connect to Bedrock Agent as action groups.

---

### Week 4: Frontend & Deployment

1. **Build React frontend**
   - Chat interface
   - Session management
   - API integration

2. **Set up CI/CD**
   - GitHub Actions or Bitbucket Pipelines
   - Automated testing
   - Automated deployment

3. **Deploy to staging**

4. **Deploy to production**

---

## 🛡️ Important Security Notes

### 1. Secrets Rotation

```bash
# Aurora password - rotate every 90 days
aws secretsmanager rotate-secret \
  --secret-id scheduling-agent/aurora/master-password \
  --rotation-rules AutomaticallyAfterDays=90
```

### 2. Enable Deletion Protection (Production)

In `aurora.tf` line 108, change:
```hcl
deletion_protection = true  # Enable in production
skip_final_snapshot = false # Enable in production
```

### 3. Monitor Costs

```bash
# Daily cost check
aws ce get-cost-and-usage \
  --time-period Start=2025-10-01,End=2025-10-31 \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=TAG,Key=Project
```

### 4. Enable AWS GuardDuty

```bash
aws guardduty create-detector --enable
```

---

## 🐛 Troubleshooting

### Issue: Terraform apply fails with "AccessDeniedException" for Bedrock

**Solution:** Bedrock model access not approved yet. Wait for approval email.

---

### Issue: Aurora cluster stuck in "creating" state

**Solution:** Check CloudWatch logs. Aurora can take 10-15 minutes to create.

```bash
aws rds describe-db-clusters \
  --db-cluster-identifier scheduling-agent-dev-aurora \
  --query 'DBClusters[0].[Status,StatusInfos]'
```

---

### Issue: Redis cluster creation fails

**Solution:** Check ElastiCache service quotas:

```bash
aws service-quotas list-service-quotas \
  --service-code elasticache \
  --query 'Quotas[?QuotaName==`Nodes per cluster`]'
```

---

### Issue: NAT Gateway costs too high

**Solution:** For dev environment, consider:
1. Use single NAT Gateway instead of 2
2. Use VPC endpoints for AWS services
3. Or accept that private subnets can't reach internet (if not needed)

---

## 📚 Documentation

**Created documentation:**
- `PHASE1_GETTING_STARTED.md` - Complete Phase 1 guide
- `TERRAFORM_COMPLETE.md` - Terraform configuration details
- `READY_TO_DEPLOY.md` - This file (deployment checklist)

**AWS Setup guides:**
- `docs/AWS_SETUP_GUIDE.md` - Comprehensive AWS setup
- `docs/AWS_SETUP_STEP_BY_STEP.md` - Step-by-step execution

**System documentation:**
- `docs/TECHNICAL_FLOW.md` - Current system technical flow
- `docs/MIGRATION_PLAN.md` - Gap analysis and migration plan

---

## ✅ Deployment Checklist

- [x] AWS CLI configured
- [x] S3 bucket created for Terraform state
- [x] DynamoDB table created for state locking
- [x] Secrets created in Secrets Manager
- [x] CloudWatch log groups created
- [x] Billing alarms configured
- [x] Terraform files created (10 files)
- [x] Terraform initialized
- [x] Terraform validated
- [x] Terraform plan generated (61 resources)
- [ ] **Bedrock model access approved** ⏳ (24-48 hours)
- [ ] Terraform applied
- [ ] Infrastructure endpoints saved
- [ ] Backend .env file updated
- [ ] Database migrations run
- [ ] Backend application tested locally

---

**Current Status:** ✅ Ready to deploy immediately after Bedrock approval

**Estimated Time to Production:** 3-4 weeks after approval

---

**Last Updated:** October 12, 2025
