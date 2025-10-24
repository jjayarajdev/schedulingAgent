# AWS Setup Guide for Phase 1 Implementation

**Document Version:** 1.0
**Last Updated:** October 12, 2025
**Estimated Setup Time:** 2-4 hours

---

## Prerequisites Checklist

### Required Tools
- [ ] **AWS CLI v2** installed and configured
- [ ] **Terraform v1.5+** installed
- [ ] **Git** for version control
- [ ] **AWS Account** with admin access (or specific permissions below)
- [ ] **Credit card** on file for AWS billing

### Recommended Tools
- [ ] **AWS Vault** or **aws-sso** for credential management
- [ ] **tfenv** for Terraform version management
- [ ] **Docker** for local testing
- [ ] **jq** for JSON parsing

---

## AWS Account Requirements

### 1. AWS Account Setup

**Option A: New AWS Account (Recommended for isolation)**
```bash
# Create new AWS account specifically for this project
# Go to: https://portal.aws.amazon.com/billing/signup

# Benefits:
- Clean separation from other projects
- Easier cost tracking
- Isolated permissions and security
```

**Option B: Existing AWS Account (Use existing account)**
```bash
# Use existing account with new VPC
# Ensure no resource conflicts
```

### 2. Billing Alerts Setup

```bash
# Set up billing alerts immediately
aws cloudwatch put-metric-alarm \
  --alarm-name "MonthlyBillExceeds100USD" \
  --alarm-description "Alert if monthly bill exceeds $100" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --evaluation-periods 1 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold
```

**Manual Setup:**
1. Go to AWS Console → Billing → Billing preferences
2. Check "Receive Billing Alerts"
3. Set up budgets: https://console.aws.amazon.com/billing/home#/budgets

---

## Required AWS Permissions

### Minimum IAM Permissions Required

Create an IAM user or role with these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:*",
        "rds:*",
        "elasticache:*",
        "ec2:*",
        "ecs:*",
        "lambda:*",
        "s3:*",
        "secretsmanager:*",
        "cloudwatch:*",
        "logs:*",
        "iam:CreateRole",
        "iam:PutRolePolicy",
        "iam:AttachRolePolicy",
        "iam:GetRole",
        "iam:PassRole",
        "iam:DeleteRole",
        "iam:DeleteRolePolicy",
        "iam:DetachRolePolicy"
      ],
      "Resource": "*"
    }
  ]
}
```

**Or use AWS Managed Policies:**
- `PowerUserAccess` (recommended for dev)
- `AdministratorAccess` (use cautiously)

---

## AWS Service Quotas & Limits

### Check Current Quotas

```bash
# Check Bedrock quotas
aws service-quotas list-service-quotas \
  --service-code bedrock \
  --region us-east-1

# Check RDS quotas
aws service-quotas list-service-quotas \
  --service-code rds \
  --region us-east-1

# Check ElastiCache quotas
aws service-quotas list-service-quotas \
  --service-code elasticache \
  --region us-east-1
```

### Request Quota Increases (If Needed)

**AWS Bedrock Model Access:**
```bash
# Request access to Claude Sonnet 4.5
# Go to: AWS Console → Bedrock → Model access
# Request access to: us.anthropic.claude-sonnet-4-5-20250929-v1:0

# This may take 24-48 hours for approval
```

**Important Quotas:**
| Service | Quota | Default | Needed | Action |
|---------|-------|---------|--------|--------|
| Bedrock Agents | Max agents | 10 | 1 | ✅ OK |
| Aurora Serverless v2 | Max clusters | 5 | 1 | ✅ OK |
| ElastiCache | Max nodes | 20 | 1 | ✅ OK |
| Lambda concurrent executions | 1000 | 1000 | ~10 | ✅ OK |
| VPC Elastic IPs | 5 | 5 | 2 | ✅ OK |

---

## Step-by-Step AWS Setup

### Step 1: Install AWS CLI

**macOS:**
```bash
brew install awscli

# Verify
aws --version
# Should show: aws-cli/2.x.x
```

**Linux:**
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify
aws --version
```

**Windows:**
```powershell
# Download and run installer from:
# https://awscli.amazonaws.com/AWSCLIV2.msi

# Verify
aws --version
```

---

### Step 2: Configure AWS Credentials

**Option A: Access Keys (Simple)**
```bash
aws configure

# Enter when prompted:
AWS Access Key ID: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name: us-east-1
Default output format: json
```

**Option B: AWS SSO (Recommended for Organizations)**
```bash
aws configure sso

# Follow prompts:
SSO session name: my-session
SSO start URL: https://my-sso-portal.awsapps.com/start
SSO region: us-east-1
SSO registration scopes: sso:account:access
```

**Verify Configuration:**
```bash
aws sts get-caller-identity

# Should return:
{
    "UserId": "AIDAI...",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/yourname"
}
```

---

### Step 3: Request AWS Bedrock Model Access

**CRITICAL: Do this first! It takes 24-48 hours.**

1. **Go to AWS Console**:
   ```
   https://console.aws.amazon.com/bedrock/
   ```

2. **Navigate to Model Access**:
   - Click "Model access" in left sidebar
   - Click "Manage model access"

3. **Request Claude Sonnet 4.5**:
   - Find "Anthropic" section
   - Check box for: `Claude Sonnet 4.5` (US Anthropic)
   - Model ID: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`
   - Click "Request model access"

4. **Fill out Use Case Form**:
   - Use case: "AI Scheduling Assistant for Project Management"
   - Description: "Customer-facing chatbot for appointment scheduling"
   - Expected usage: "Low to medium volume"

5. **Wait for Approval**:
   - Check email for approval notification
   - Usually approved within 24-48 hours
   - Can check status in Bedrock console

**Verify Access (After Approval):**
```bash
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query 'modelSummaries[?contains(modelId, `claude-sonnet-4-5`)].modelId'
```

---

### Step 4: Set Up Terraform Backend (S3 + DynamoDB)

**Create S3 Bucket for Terraform State:**
```bash
# Replace with your unique bucket name
BUCKET_NAME="projectsforce-terraform-state-$(aws sts get-caller-identity --query Account --output text)"

aws s3api create-bucket \
  --bucket $BUCKET_NAME \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket $BUCKET_NAME \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket $BUCKET_NAME \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Block public access
aws s3api put-public-access-block \
  --bucket $BUCKET_NAME \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

**Create DynamoDB Table for State Locking:**
```bash
aws dynamodb create-table \
  --table-name terraform-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

**Update Terraform Backend Configuration:**
```hcl
# In infrastructure/main.tf
backend "s3" {
  bucket         = "projectsforce-terraform-state-123456789012"  # Your bucket name
  key            = "scheduling-agent/bedrock/terraform.tfstate"
  region         = "us-east-1"
  encrypt        = true
  dynamodb_table = "terraform-lock"
}
```

---

### Step 5: Create Secrets in AWS Secrets Manager

```bash
# Aurora database master password
aws secretsmanager create-secret \
  --name scheduling-agent/aurora/master-password \
  --description "Aurora PostgreSQL master password" \
  --secret-string "$(openssl rand -base64 32)" \
  --region us-east-1

# PF360 API credentials (if needed)
aws secretsmanager create-secret \
  --name scheduling-agent/pf360/api-key \
  --description "PF360 API key" \
  --secret-string '{"api_key":"your-api-key-here"}' \
  --region us-east-1

# JWT secret key
aws secretsmanager create-secret \
  --name scheduling-agent/jwt/secret-key \
  --description "JWT secret key for authentication" \
  --secret-string "$(openssl rand -base64 64)" \
  --region us-east-1
```

**Retrieve Secrets (for .env files):**
```bash
# Get Aurora password
aws secretsmanager get-secret-value \
  --secret-id scheduling-agent/aurora/master-password \
  --query SecretString \
  --output text

# Get JWT secret
aws secretsmanager get-secret-value \
  --secret-id scheduling-agent/jwt/secret-key \
  --query SecretString \
  --output text
```

---

### Step 6: Set Up CloudWatch Log Groups

```bash
# Create log groups in advance
aws logs create-log-group \
  --log-group-name /aws/ecs/scheduling-agent

aws logs create-log-group \
  --log-group-name /aws/lambda/scheduling-agent

aws logs create-log-group \
  --log-group-name /aws/bedrock/scheduling-agent

# Set retention to 7 days (cost optimization)
aws logs put-retention-policy \
  --log-group-name /aws/ecs/scheduling-agent \
  --retention-in-days 7
```

---

### Step 7: Enable AWS Cost Explorer & Budgets

```bash
# Create a budget (via AWS Console is easier)
# Go to: https://console.aws.amazon.com/billing/home#/budgets

# Create monthly budget:
# - Name: SchedulingAgent-Monthly
# - Budget amount: $200/month
# - Alert at 80% ($160)
# - Alert at 100% ($200)
```

**Budget Configuration (JSON):**
```json
{
  "BudgetName": "SchedulingAgent-Monthly",
  "BudgetType": "COST",
  "TimeUnit": "MONTHLY",
  "BudgetLimit": {
    "Amount": "200",
    "Unit": "USD"
  },
  "CostFilters": {
    "TagKeyValue": [
      "Project$SchedulingAgent"
    ]
  }
}
```

---

## Cost Estimates

### Monthly AWS Costs (Phase 1)

| Service | Configuration | Estimated Cost |
|---------|--------------|----------------|
| **Aurora Serverless v2** | 0.5-2 ACUs, 20GB storage | $25-50 |
| **Redis ElastiCache** | cache.t4g.micro | $12 |
| **AWS Bedrock** | Claude 3.5 Sonnet, ~1M tokens/month | $15-30 |
| **ECS Fargate** | 0.5 vCPU, 1GB RAM, always on | $15 |
| **Lambda** | 1M invocations, 512MB, 3s avg | $5 |
| **Data Transfer** | Outbound transfer | $5-10 |
| **CloudWatch** | Logs, metrics | $5 |
| **NAT Gateway** | 2 AZs | $65 |
| **S3** | Terraform state, logs | $1 |
| **Secrets Manager** | 3 secrets | $1.20 |
| **VPC** | Elastic IPs | $7 |
| **TOTAL** | | **$156-206/month** |

**Cost Optimization Tips:**
- Use Aurora Serverless v2 auto-scaling (scale to 0.5 ACU when idle)
- Use single-AZ Redis for dev (multi-AZ for prod)
- Set CloudWatch log retention to 7 days
- Use S3 lifecycle policies for old logs
- Consider Reserved Instances for prod

---

## Environment-Specific Setup

### Development Environment

```bash
# Use smaller resources
export TF_VAR_environment="dev"
export TF_VAR_aurora_min_capacity=0.5
export TF_VAR_aurora_max_capacity=1
export TF_VAR_redis_node_type="cache.t4g.micro"
```

**Dev Cost:** ~$80-100/month

### Staging Environment

```bash
export TF_VAR_environment="staging"
export TF_VAR_aurora_min_capacity=0.5
export TF_VAR_aurora_max_capacity=2
export TF_VAR_redis_node_type="cache.t4g.small"
```

**Staging Cost:** ~$120-150/month

### Production Environment

```bash
export TF_VAR_environment="prod"
export TF_VAR_aurora_min_capacity=1
export TF_VAR_aurora_max_capacity=4
export TF_VAR_redis_node_type="cache.r7g.large"
export TF_VAR_redis_num_cache_nodes=2  # Multi-AZ
```

**Prod Cost:** ~$300-400/month

---

## Security Best Practices

### 1. Enable MFA
```bash
# Enable MFA for root account and IAM users
# Go to: IAM → Users → Security credentials → Assign MFA device
```

### 2. Enable CloudTrail
```bash
aws cloudtrail create-trail \
  --name scheduling-agent-audit \
  --s3-bucket-name projectsforce-cloudtrail-logs

aws cloudtrail start-logging \
  --name scheduling-agent-audit
```

### 3. Enable GuardDuty
```bash
aws guardduty create-detector --enable
```

### 4. Enable Security Hub
```bash
aws securityhub enable-security-hub
```

### 5. Rotate Secrets Regularly
```bash
# Set up automatic rotation for database passwords
aws secretsmanager rotate-secret \
  --secret-id scheduling-agent/aurora/master-password \
  --rotation-rules AutomaticallyAfterDays=90
```

---

## Verification Checklist

After completing setup, verify:

```bash
# 1. AWS CLI configured
aws sts get-caller-identity

# 2. Bedrock access granted
aws bedrock list-foundation-models --region us-east-1 | grep claude-sonnet-4-5

# 3. S3 bucket created
aws s3 ls | grep terraform-state

# 4. DynamoDB table created
aws dynamodb describe-table --table-name terraform-lock

# 5. Secrets created
aws secretsmanager list-secrets | grep scheduling-agent

# 6. Required services available in region
aws ec2 describe-regions --query 'Regions[?RegionName==`us-east-1`]'
```

---

## Troubleshooting Common Issues

### Issue 1: Bedrock Model Access Denied
```bash
# Check model access status
aws bedrock list-foundation-models --region us-east-1

# If not approved yet, wait 24-48 hours
# Check AWS email for approval notification
```

### Issue 2: Insufficient Permissions
```bash
# Test permissions
aws iam simulate-principal-policy \
  --policy-source-arn $(aws sts get-caller-identity --query Arn --output text) \
  --action-names bedrock:InvokeModel

# If denied, attach PowerUserAccess policy
```

### Issue 3: Terraform Backend Access Denied
```bash
# Check S3 bucket policy
aws s3api get-bucket-policy --bucket projectsforce-terraform-state

# Ensure your IAM user/role has s3:* permissions
```

### Issue 4: Region-Specific Services
```bash
# Bedrock is only available in specific regions
# Supported regions: us-east-1, us-west-2, eu-west-1

# Use us-east-1 for best coverage
```

---

## Next Steps After AWS Setup

1. **Update Terraform Variables**:
   ```bash
   cd infrastructure/
   cp terraform.tfvars.example terraform.tfvars
   # Edit with your AWS account details
   ```

2. **Initialize Terraform**:
   ```bash
   terraform init
   ```

3. **Plan Infrastructure**:
   ```bash
   terraform plan -out=tfplan
   ```

4. **Apply Infrastructure** (when ready):
   ```bash
   terraform apply tfplan
   ```

5. **Save Outputs**:
   ```bash
   terraform output > outputs.txt
   # Save Aurora endpoint, Redis endpoint, etc.
   ```

---

## Support & Resources

- **AWS Documentation**: https://docs.aws.amazon.com/
- **AWS Bedrock**: https://docs.aws.amazon.com/bedrock/
- **Terraform AWS Provider**: https://registry.terraform.io/providers/hashicorp/aws/
- **AWS Support**: https://console.aws.amazon.com/support/
- **Cost Calculator**: https://calculator.aws/

---

## Emergency Contacts

- **AWS Support**: File ticket via AWS Console
- **Billing Issues**: billing-support@amazon.com
- **Security Issues**: aws-security@amazon.com

---

**Setup Complete! ✅**

Once you've completed all steps above, you're ready to provision infrastructure with Terraform.

**Estimated Total Setup Time**: 2-4 hours (excluding Bedrock approval wait time)
