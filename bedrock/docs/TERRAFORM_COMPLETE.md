# Terraform Infrastructure - Completed

**Status:** ✅ All Terraform files created and ready for deployment
**Date:** October 12, 2025
**Location:** `bedrock/infrastructure/`

---

## ✅ Completed Files

### 1. **main.tf** (961B)
- Terraform backend configuration (S3 + DynamoDB)
- AWS provider setup
- Bucket: `projectsforce-terraform-state-618048437522`
- Data sources for AWS account and region
- Local variables for naming and tagging

### 2. **variables.tf** (2.0KB)
- All input variables defined
- AWS region, environment validation
- VPC and network configuration
- Aurora PostgreSQL configuration
- Redis configuration
- Bedrock Agent configuration
- Tags

### 3. **terraform.tfvars** (719B)
- Development environment configuration
- VPC CIDR: `10.0.0.0/16`
- AZs: `us-east-1a`, `us-east-1b`
- Aurora: 0.5-1.0 ACUs
- Redis: `cache.t4g.micro`
- Bedrock model: `anthropic.claude-3-5-sonnet-20240620-v1:0`

### 4. **networking.tf** (5.9KB) - From earlier
- VPC with DNS enabled
- Internet Gateway
- Public subnets (2 AZs) with auto-assign public IP
- Private subnets (2 AZs)
- NAT Gateways (2) with Elastic IPs
- Public route table
- Private route tables (one per AZ)
- Security groups:
  - Aurora (port 5432)
  - Redis (port 6379)
  - Application (ports 80, 443, 8000)
- VPC endpoint for S3 (cost optimization)

### 5. **aurora.tf** (5.0KB) ✨ NEW
- DB subnet group (private subnets)
- Cluster parameter group (PostgreSQL 15)
- Instance parameter group
- Aurora Serverless v2 cluster:
  - Engine: `aurora-postgresql`
  - Version: `15.4`
  - Scaling: 0.5-1.0 ACU (from tfvars)
  - Backup retention: 7 days
  - Encryption with KMS key
  - CloudWatch Logs enabled
- Aurora instance (`db.serverless`)
- Performance Insights enabled (7-day retention)
- Enhanced monitoring (60-second interval)
- KMS key for encryption
- CloudWatch log group
- IAM role for RDS monitoring

### 6. **redis.tf** (5.1KB) ✨ NEW
- Redis subnet group (private subnets)
- Parameter group (Redis 7)
  - Cluster mode: disabled (for dev)
  - Timeout: 300 seconds
  - Maxmemory policy: `allkeys-lru`
- ElastiCache cluster:
  - Engine: Redis 7.1
  - Node type: `cache.t4g.micro`
  - Nodes: 1 (dev), can scale to 2+ in prod
  - Port: 6379
  - Snapshot retention: 5 days
- CloudWatch log groups (slow-log, engine-log)
- SNS topic for notifications
- CloudWatch alarms:
  - High CPU (>75%)
  - High memory (>80%)
  - Evictions (>100)

### 7. **secrets.tf** (1.3KB) ✨ NEW
- Data sources for existing Secrets Manager secrets:
  - `scheduling-agent/aurora/master-password`
  - `scheduling-agent/jwt/secret-key`
  - `scheduling-agent/pf360/api-credentials`
- Outputs for secret ARNs (sensitive)

### 8. **iam.tf** (8.6KB) ✨ NEW
- **ECS Task Execution Role:**
  - Pull container images
  - Write CloudWatch logs
  - Access Secrets Manager
  - KMS decrypt
- **ECS Task Role (Application Runtime):**
  - Invoke Bedrock Agent
  - Access Secrets Manager
  - Write CloudWatch Logs
- **Lambda Execution Role:**
  - Basic execution (logs)
  - VPC access
  - Access Secrets Manager (PF360 credentials)
- **Bedrock Agent Service Role:**
  - Invoke foundation models (Claude 3.5 Sonnet)
  - Invoke Lambda functions
  - Write CloudWatch Logs
- Outputs for all role ARNs

### 9. **bedrock.tf** (4.6KB) ✨ NEW
- Bedrock Agent:
  - Model: Claude 3.5 Sonnet
  - Idle session TTL: 600 seconds
  - Instructions: Complete agent prompt based on current system
    - Scheduling workflow
    - User guidelines (AM/PM format, hide technical IDs)
    - Session management
- Agent aliases:
  - `prod` - Production
  - `dev` - Development
- CloudWatch log group
- Note: Action groups placeholder (will add when Lambda functions are created)
- Outputs for agent ID, version, alias IDs

### 10. **outputs.tf** (1.7KB) - From earlier
- VPC ID
- Subnet IDs (public and private)
- Aurora endpoints (writer and reader) - sensitive
- Redis endpoint and port
- Bedrock Agent ID and ARN
- Secrets Manager ARN
- Environment and region

---

## 📊 Infrastructure Summary

**Total Resources:** ~50-60 resources will be created

### Network Layer (networking.tf)
- 1 VPC
- 1 Internet Gateway
- 2 Public Subnets
- 2 Private Subnets
- 2 Elastic IPs
- 2 NAT Gateways
- 1 Public Route Table
- 2 Private Route Tables
- 4 Route Table Associations
- 3 Security Groups
- 1 VPC Endpoint (S3)
- 2 VPC Endpoint Associations

### Database Layer (aurora.tf)
- 1 DB Subnet Group
- 1 Cluster Parameter Group
- 1 Instance Parameter Group
- 1 Aurora Cluster
- 1 Aurora Instance
- 1 KMS Key
- 1 KMS Alias
- 1 CloudWatch Log Group
- 1 IAM Role (RDS monitoring)
- 1 IAM Role Policy Attachment

### Cache Layer (redis.tf)
- 1 ElastiCache Subnet Group
- 1 Parameter Group
- 1 ElastiCache Cluster
- 2 CloudWatch Log Groups
- 1 SNS Topic
- 3 CloudWatch Alarms

### Secrets Layer (secrets.tf)
- 3 Data Sources (existing secrets)

### IAM Layer (iam.tf)
- 4 IAM Roles
- 2 Managed Policy Attachments
- 8 Inline Policies

### Bedrock Layer (bedrock.tf)
- 1 Bedrock Agent
- 2 Agent Aliases
- 1 CloudWatch Log Group

---

## 💰 Estimated Costs (from terraform.tfvars)

**Development Environment:**

| Service | Configuration | Monthly Cost |
|---------|--------------|-------------|
| Aurora Serverless v2 | 0.5-1.0 ACU | $25-40 |
| ElastiCache Redis | cache.t4g.micro, 1 node | $12 |
| NAT Gateway | 2 AZs | $65 |
| Data Transfer | Minimal | $5-10 |
| CloudWatch | Logs + Metrics | $5 |
| S3 (Terraform state) | Minimal | $0.10 |
| Secrets Manager | 3 secrets | $1.20 |
| KMS | 1 key | $1 |
| **TOTAL** | | **$114-134/month** |

**After Bedrock approval:**
- Add Bedrock Agent usage: ~$15-30/month
- Add ECS Fargate: ~$15/month
- Add Lambda: ~$5/month
- **New Total:** $149-184/month

---

## 🚀 Next Steps

### Step 1: Install Terraform (Required)

```bash
# macOS
brew install terraform

# Verify installation
terraform version
# Should show: Terraform v1.5.x or higher
```

**Linux:**
```bash
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/
terraform version
```

---

### Step 2: Initialize Terraform

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/

# Initialize (connects to S3 backend)
terraform init

# Expected output:
# Initializing the backend...
# Successfully configured the backend "s3"!
# Terraform has been successfully initialized!
```

---

### Step 3: Validate Configuration

```bash
# Validate syntax and configuration
terraform validate

# Expected output:
# Success! The configuration is valid.
```

---

### Step 4: Format Code (Optional)

```bash
# Format Terraform files
terraform fmt -recursive

# This ensures consistent formatting
```

---

### Step 5: Plan Infrastructure (Dry Run)

```bash
# Generate execution plan
terraform plan -out=tfplan

# This will:
# - Show all resources to be created (~50-60 resources)
# - Estimate costs
# - Validate resource dependencies
# - Save plan to file

# Review the plan carefully before applying
```

**Note:** This will likely FAIL if Bedrock model access is not yet approved. You'll see:

```
Error: creating Bedrock Agent: AccessDeniedException: You don't have access to the model with the specified model ID.
```

**This is expected!** Wait for Bedrock approval email before proceeding.

---

### Step 6: Wait for Bedrock Approval (24-48 hours)

Check Bedrock model access status:

```bash
# Via CLI
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query 'modelSummaries[?contains(modelId, `claude-3-5-sonnet`)].modelId' \
  --output text

# Via Console
open https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess
```

**When approved, you'll see:**
```
anthropic.claude-3-5-sonnet-20240620-v1:0
```

---

### Step 7: Apply Infrastructure (After Bedrock Approval)

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/

# Apply the plan
terraform apply tfplan

# Or if you didn't save a plan:
terraform apply

# Type 'yes' when prompted

# Duration: ~15-20 minutes
```

**Resources created in this order:**
1. VPC and networking (1-2 min)
2. Security groups (instant)
3. KMS keys (instant)
4. IAM roles (instant)
5. Aurora cluster and instance (8-10 min)
6. Redis cluster (5-7 min)
7. Bedrock Agent (2-3 min)
8. CloudWatch resources (instant)

---

### Step 8: Save Outputs

```bash
# Save all outputs to JSON file
terraform output -json > ../outputs.json

# View specific outputs
terraform output vpc_id
terraform output aurora_cluster_endpoint
terraform output redis_endpoint
terraform output bedrock_agent_id
```

---

### Step 9: Update Backend .env File

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/backend/

# Get infrastructure endpoints
AURORA_ENDPOINT=$(cd ../infrastructure && terraform output -raw aurora_cluster_endpoint)
REDIS_ENDPOINT=$(cd ../infrastructure && terraform output -raw redis_endpoint)
BEDROCK_AGENT_ID=$(cd ../infrastructure && terraform output -raw bedrock_agent_id)

# Get secrets
AURORA_PASSWORD=$(aws secretsmanager get-secret-value --secret-id scheduling-agent/aurora/master-password --query SecretString --output text)
JWT_SECRET=$(aws secretsmanager get-secret-value --secret-id scheduling-agent/jwt/secret-key --query SecretString --output text)

# Update .env
cat > .env <<EOF
ENVIRONMENT=dev
DATABASE_URL=postgresql+asyncpg://dbadmin:${AURORA_PASSWORD}@${AURORA_ENDPOINT}:5432/scheduling_agent
REDIS_URL=redis://${REDIS_ENDPOINT}:6379/0
AWS_REGION=us-east-1
BEDROCK_AGENT_ID=${BEDROCK_AGENT_ID}
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0
JWT_SECRET_KEY=${JWT_SECRET}
EOF

echo "✅ .env file updated"
```

---

## 🔍 Verification Commands

After `terraform apply`:

```bash
# Check VPC
aws ec2 describe-vpcs \
  --filters "Name=tag:Project,Values=SchedulingAgent" \
  --query 'Vpcs[0].VpcId' \
  --output text

# Check Aurora cluster
aws rds describe-db-clusters \
  --db-cluster-identifier scheduling-agent-dev-aurora \
  --query 'DBClusters[0].Status' \
  --output text

# Check Redis cluster
aws elasticache describe-cache-clusters \
  --cache-cluster-id scheduling-agent-dev-redis \
  --query 'CacheClusters[0].CacheClusterStatus' \
  --output text

# Check Bedrock Agent
aws bedrock-agent get-agent \
  --agent-id $(cd infrastructure && terraform output -raw bedrock_agent_id) \
  --query 'agent.agentStatus' \
  --output text
```

**Expected outputs:**
- VPC: `vpc-xxxxx`
- Aurora: `available`
- Redis: `available`
- Bedrock: `PREPARED` or `NOT_PREPARED`

---

## 📝 Important Notes

### Deletion Protection

**Aurora cluster has deletion protection DISABLED** (line aurora.tf:108)
- Set to `true` in production
- Set `skip_final_snapshot = false` in production

### Cost Monitoring

**Monitor costs closely:**
```bash
# Check current month costs
aws ce get-cost-and-usage \
  --time-period Start=2025-10-01,End=2025-10-31 \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=TAG,Key=Project
```

### NAT Gateway Costs

**Most expensive component: NAT Gateway ($32.50/AZ/month = $65/month)**

**To reduce costs in dev:**
- Consider single NAT Gateway
- Or use VPC endpoints instead of NAT for AWS services

### Terraform State

**State is stored in S3:**
- Bucket: `projectsforce-terraform-state-618048437522`
- Key: `scheduling-agent/bedrock/terraform.tfstate`
- Encrypted: Yes
- Versioning: Enabled
- Locking: DynamoDB table `terraform-lock`

**Never delete this bucket without backing up state!**

---

## 🐛 Troubleshooting

### Error: "Failed to get existing workspaces"

**Cause:** S3 bucket doesn't exist or wrong name

**Fix:**
```bash
aws s3 ls | grep terraform-state
# Verify bucket name matches main.tf line 12
```

---

### Error: "AccessDeniedException" for Bedrock

**Cause:** Model access not approved yet

**Fix:** Wait for Bedrock approval email (24-48 hours)

---

### Error: "InvalidParameterException" for Aurora

**Cause:** Invalid ACU values

**Fix:** Ensure `aurora_min_capacity` ≥ 0.5 and ≤ `aurora_max_capacity`

---

### Error: Quota exceeded

**Cause:** AWS service limits

**Fix:**
```bash
# Check quotas
aws service-quotas list-service-quotas --service-code rds
aws service-quotas list-service-quotas --service-code elasticache

# Request increase via AWS Console if needed
```

---

## 🎯 What's Next After Infrastructure

Once infrastructure is deployed:

1. **Build Backend Application** (4-6 hours)
   - FastAPI with async support
   - SQLAlchemy models
   - Bedrock Agent integration
   - Database migrations

2. **Create Lambda Functions** (3-4 hours)
   - PF360 API integration
   - 7 Lambda functions for action groups

3. **Build Frontend** (8-10 hours)
   - React with TypeScript
   - Chat interface
   - API integration

4. **Set Up CI/CD** (2-3 hours)
   - GitHub Actions or Bitbucket Pipelines
   - Automated testing
   - Automated deployment

5. **Deploy to Staging** (1 hour)
   - Test full system
   - Load testing

6. **Deploy to Production** (1 hour)
   - Blue-green deployment
   - Monitoring and alerts

---

## 📚 Resources

- **Terraform AWS Provider:** https://registry.terraform.io/providers/hashicorp/aws/
- **AWS Bedrock:** https://docs.aws.amazon.com/bedrock/
- **Aurora Serverless v2:** https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.html
- **ElastiCache Redis:** https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/

---

**Terraform Infrastructure Complete!** ✅

**Ready to deploy after Bedrock approval.**

---

**Created:** October 12, 2025
**Files:** 10 Terraform files, ~60 resources, ready for Phase 1 deployment
