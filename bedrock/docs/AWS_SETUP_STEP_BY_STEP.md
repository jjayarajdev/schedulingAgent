# AWS Setup - Step-by-Step Execution Guide

**Document Purpose:** Command-by-command execution guide for AWS infrastructure setup
**Estimated Time:** 30 minutes (excluding Bedrock approval wait time of 24-48 hours)
**Prerequisites:** AWS CLI installed, AWS account with admin access

---

## Execution Overview

This guide walks you through the exact commands to run in sequence. Each step includes:
- ✅ Success criteria
- ❌ Common failure points
- 🔍 Validation commands

**IMPORTANT:** Bedrock model access takes 24-48 hours. Request it first, then complete other steps while waiting.

---

## Step 1: Verify AWS CLI Installation and Configuration

### 1.1 Check AWS CLI Version

```bash
aws --version
```

**Expected Output:**
```
aws-cli/2.x.x Python/3.x.x Darwin/24.x.x
```

✅ **Success:** Version shows `aws-cli/2.x.x`
❌ **Failure:** Command not found or version 1.x

**Fix if failed:**
```bash
# macOS
brew install awscli

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

---

### 1.2 Configure AWS Credentials

```bash
aws configure
```

**You'll be prompted for:**
```
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: us-east-1
Default output format [None]: json
```

**Where to get credentials:**
1. Go to AWS Console → IAM → Users → Your user → Security credentials
2. Click "Create access key"
3. Copy Access Key ID and Secret Access Key

---

### 1.3 Verify Configuration

```bash
aws sts get-caller-identity
```

**Expected Output:**
```json
{
    "UserId": "AIDAI...",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/yourname"
}
```

✅ **Success:** Returns your AWS account details
❌ **Failure:** "Unable to locate credentials" or "Access Denied"

**Fix if failed:**
- Verify access key is correct
- Check IAM user has required permissions
- Run `aws configure` again

---

## Step 2: Request Bedrock Model Access (CRITICAL - 24-48 HOURS)

**⚠️ DO THIS STEP FIRST - IT TAKES 24-48 HOURS FOR APPROVAL**

### 2.1 Open AWS Bedrock Console

```bash
# Open in browser
open https://console.aws.amazon.com/bedrock/
# Or manually go to: https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess
```

### 2.2 Request Model Access

1. Click **"Model access"** in left sidebar
2. Click **"Manage model access"** (orange button top right)
3. Scroll to **"Anthropic"** section
4. Check the box for **"Claude Sonnet 4.5"** (US Anthropic)
5. Click **"Request model access"** (orange button bottom right)

### 2.3 Fill Use Case Form

**Form fields:**
- **Use case:** `AI Scheduling Assistant for Project Management`
- **Description:** `Customer-facing chatbot for appointment scheduling with PF360 integration`
- **Expected monthly usage:** `Low to medium volume`
- **Industry:** `Software/Technology`

### 2.4 Submit and Wait

1. Click **"Submit"**
2. You'll see status: **"Access requested"**
3. Check your AWS account email for approval (24-48 hours)

### 2.5 Verify Access (After Approval Email)

```bash
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query 'modelSummaries[?contains(modelId, `claude-sonnet-4-5`)].modelId' \
  --output text
```

**Expected Output:**
```
us.anthropic.claude-sonnet-4-5-20250929-v1:0
```

✅ **Success:** Model ID is displayed
❌ **Failure:** Empty output or "AccessDeniedException"

**If failed:**
- Wait for approval email (check spam folder)
- Check status in Bedrock console
- Contact AWS Support if >48 hours

---

## Step 3: Create S3 Bucket for Terraform State

### 3.1 Set Bucket Name Variable

```bash
export BUCKET_NAME="projectsforce-terraform-state-$(aws sts get-caller-identity --query Account --output text)"
echo "Bucket name: $BUCKET_NAME"
```

**Expected Output:**
```
Bucket name: projectsforce-terraform-state-123456789012
```

✅ **Success:** Bucket name includes your AWS account number
❌ **Failure:** Empty or "None"

---

### 3.2 Create S3 Bucket

```bash
aws s3api create-bucket \
  --bucket $BUCKET_NAME \
  --region us-east-1
```

**Expected Output:**
```json
{
    "Location": "/projectsforce-terraform-state-123456789012"
}
```

✅ **Success:** Returns bucket location
❌ **Failure:** "BucketAlreadyExists" or "AccessDenied"

**Fix if failed:**
- If "BucketAlreadyExists": Choose different bucket name
- If "AccessDenied": Check IAM permissions for s3:CreateBucket

---

### 3.3 Enable Bucket Versioning

```bash
aws s3api put-bucket-versioning \
  --bucket $BUCKET_NAME \
  --versioning-configuration Status=Enabled
```

**No output means success**

**Verify:**
```bash
aws s3api get-bucket-versioning --bucket $BUCKET_NAME
```

**Expected Output:**
```json
{
    "Status": "Enabled"
}
```

✅ **Success:** Status shows "Enabled"

---

### 3.4 Enable Bucket Encryption

```bash
aws s3api put-bucket-encryption \
  --bucket $BUCKET_NAME \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

**No output means success**

**Verify:**
```bash
aws s3api get-bucket-encryption --bucket $BUCKET_NAME
```

**Expected Output:**
```json
{
    "ServerSideEncryptionConfiguration": {
        "Rules": [
            {
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }
        ]
    }
}
```

✅ **Success:** Shows AES256 encryption enabled

---

### 3.5 Block Public Access

```bash
aws s3api put-public-access-block \
  --bucket $BUCKET_NAME \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

**No output means success**

**Verify:**
```bash
aws s3api get-public-access-block --bucket $BUCKET_NAME
```

**Expected Output:**
```json
{
    "PublicAccessBlockConfiguration": {
        "BlockPublicAcls": true,
        "IgnorePublicAcls": true,
        "BlockPublicPolicy": true,
        "RestrictPublicBuckets": true
    }
}
```

✅ **Success:** All values are `true`

---

### 3.6 Verify S3 Bucket Complete

```bash
aws s3 ls | grep terraform-state
```

**Expected Output:**
```
2025-10-12 19:00:00 projectsforce-terraform-state-123456789012
```

✅ **Success:** Bucket is listed

---

## Step 4: Create DynamoDB Table for State Locking

### 4.1 Create Table

```bash
aws dynamodb create-table \
  --table-name terraform-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

**Expected Output:**
```json
{
    "TableDescription": {
        "TableName": "terraform-lock",
        "TableStatus": "CREATING",
        "AttributeDefinitions": [
            {
                "AttributeName": "LockID",
                "AttributeType": "S"
            }
        ],
        ...
    }
}
```

✅ **Success:** Returns table description with status "CREATING"
❌ **Failure:** "ResourceInUseException" (table already exists - OK) or "AccessDenied"

---

### 4.2 Wait for Table to Become Active

```bash
aws dynamodb wait table-exists --table-name terraform-lock
echo "Table is active"
```

**This will wait until table is ready (usually 10-30 seconds)**

✅ **Success:** Command completes and prints "Table is active"

---

### 4.3 Verify Table Status

```bash
aws dynamodb describe-table \
  --table-name terraform-lock \
  --query 'Table.TableStatus' \
  --output text
```

**Expected Output:**
```
ACTIVE
```

✅ **Success:** Shows "ACTIVE"
❌ **Failure:** Shows "CREATING" (wait longer) or error

---

## Step 5: Create Secrets in AWS Secrets Manager

### 5.1 Create Aurora Master Password

```bash
aws secretsmanager create-secret \
  --name scheduling-agent/aurora/master-password \
  --description "Aurora PostgreSQL master password" \
  --secret-string "$(openssl rand -base64 32)" \
  --region us-east-1
```

**Expected Output:**
```json
{
    "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:scheduling-agent/aurora/master-password-aBcDe",
    "Name": "scheduling-agent/aurora/master-password",
    "VersionId": "..."
}
```

✅ **Success:** Returns ARN of created secret
❌ **Failure:** "ResourceExistsException" (already exists - OK) or "AccessDenied"

**If secret already exists and you want to update:**
```bash
aws secretsmanager update-secret \
  --secret-id scheduling-agent/aurora/master-password \
  --secret-string "$(openssl rand -base64 32)"
```

---

### 5.2 Create JWT Secret Key

```bash
aws secretsmanager create-secret \
  --name scheduling-agent/jwt/secret-key \
  --description "JWT secret key for authentication" \
  --secret-string "$(openssl rand -base64 64)" \
  --region us-east-1
```

**Expected Output:**
```json
{
    "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:scheduling-agent/jwt/secret-key-XyZaB",
    "Name": "scheduling-agent/jwt/secret-key",
    "VersionId": "..."
}
```

✅ **Success:** Returns ARN of created secret

---

### 5.3 Create PF360 API Credentials (Optional - Update Later)

```bash
aws secretsmanager create-secret \
  --name scheduling-agent/pf360/api-credentials \
  --description "PF360 API credentials" \
  --secret-string '{"api_url":"PLACEHOLDER","api_key":"PLACEHOLDER"}' \
  --region us-east-1
```

**Expected Output:**
```json
{
    "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:scheduling-agent/pf360/api-credentials-MnOpQ",
    "Name": "scheduling-agent/pf360/api-credentials",
    "VersionId": "..."
}
```

✅ **Success:** Returns ARN of created secret

**Note:** You'll update this with actual PF360 credentials later

---

### 5.4 Verify All Secrets Created

```bash
aws secretsmanager list-secrets \
  --query 'SecretList[?contains(Name, `scheduling-agent`)].Name' \
  --output table
```

**Expected Output:**
```
---------------------------------------------------
|                   ListSecrets                   |
+-------------------------------------------------+
|  scheduling-agent/aurora/master-password       |
|  scheduling-agent/jwt/secret-key               |
|  scheduling-agent/pf360/api-credentials        |
+-------------------------------------------------+
```

✅ **Success:** Shows all 3 secrets

---

### 5.5 Retrieve Secret Values (For Your Records)

**Aurora Password:**
```bash
aws secretsmanager get-secret-value \
  --secret-id scheduling-agent/aurora/master-password \
  --query SecretString \
  --output text
```

**JWT Secret:**
```bash
aws secretsmanager get-secret-value \
  --secret-id scheduling-agent/jwt/secret-key \
  --query SecretString \
  --output text
```

**⚠️ SAVE THESE VALUES SECURELY** (you'll need them for .env files)

```bash
# Save to temporary file (will delete later)
echo "AURORA_PASSWORD=$(aws secretsmanager get-secret-value --secret-id scheduling-agent/aurora/master-password --query SecretString --output text)" > ~/aws-secrets-temp.txt
echo "JWT_SECRET=$(aws secretsmanager get-secret-value --secret-id scheduling-agent/jwt/secret-key --query SecretString --output text)" >> ~/aws-secrets-temp.txt
chmod 600 ~/aws-secrets-temp.txt
echo "Secrets saved to ~/aws-secrets-temp.txt"
```

---

## Step 6: Create CloudWatch Log Groups

### 6.1 Create ECS Log Group

```bash
aws logs create-log-group \
  --log-group-name /aws/ecs/scheduling-agent \
  --region us-east-1
```

**No output means success**

**Verify:**
```bash
aws logs describe-log-groups \
  --log-group-name-prefix /aws/ecs/scheduling-agent \
  --query 'logGroups[0].logGroupName' \
  --output text
```

**Expected Output:**
```
/aws/ecs/scheduling-agent
```

✅ **Success:** Returns log group name

---

### 6.2 Create Lambda Log Group

```bash
aws logs create-log-group \
  --log-group-name /aws/lambda/scheduling-agent \
  --region us-east-1
```

---

### 6.3 Create Bedrock Log Group

```bash
aws logs create-log-group \
  --log-group-name /aws/bedrock/scheduling-agent \
  --region us-east-1
```

---

### 6.4 Set Retention Policy (Cost Optimization)

```bash
# Set 7-day retention for all log groups
aws logs put-retention-policy \
  --log-group-name /aws/ecs/scheduling-agent \
  --retention-in-days 7

aws logs put-retention-policy \
  --log-group-name /aws/lambda/scheduling-agent \
  --retention-in-days 7

aws logs put-retention-policy \
  --log-group-name /aws/bedrock/scheduling-agent \
  --retention-in-days 7
```

**No output means success**

---

### 6.5 Verify All Log Groups

```bash
aws logs describe-log-groups \
  --log-group-name-prefix /aws \
  --query 'logGroups[?contains(logGroupName, `scheduling-agent`)].{Name:logGroupName,Retention:retentionInDays}' \
  --output table
```

**Expected Output:**
```
----------------------------------------------------
|              DescribeLogGroups                   |
+------------------------------------+--------------+
|              Name                  |  Retention   |
+------------------------------------+--------------+
|  /aws/ecs/scheduling-agent        |  7           |
|  /aws/lambda/scheduling-agent     |  7           |
|  /aws/bedrock/scheduling-agent    |  7           |
+------------------------------------+--------------+
```

✅ **Success:** Shows all 3 log groups with 7-day retention

---

## Step 7: Set Up Billing Alerts

### 7.1 Enable Billing Alerts (One-time Setup)

**Must be done in AWS Console:**
1. Go to: https://console.aws.amazon.com/billing/home#/preferences
2. Check ✅ **"Receive Billing Alerts"**
3. Click **"Save preferences"**

---

### 7.2 Create Cost Alarm

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "SchedulingAgent-MonthlyBillExceeds100USD" \
  --alarm-description "Alert if monthly bill exceeds $100" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --evaluation-periods 1 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold \
  --region us-east-1
```

**No output means success**

---

### 7.3 Create Cost Alarm at $200

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "SchedulingAgent-MonthlyBillExceeds200USD" \
  --alarm-description "Alert if monthly bill exceeds $200" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --evaluation-periods 1 \
  --threshold 200 \
  --comparison-operator GreaterThanThreshold \
  --region us-east-1
```

---

### 7.4 Verify Alarms

```bash
aws cloudwatch describe-alarms \
  --alarm-name-prefix "SchedulingAgent" \
  --query 'MetricAlarms[].{Name:AlarmName,Threshold:Threshold}' \
  --output table
```

**Expected Output:**
```
-----------------------------------------------------------------
|                       DescribeAlarms                          |
+------------------------------------------------------+--------+
|                         Name                         |Threshold|
+------------------------------------------------------+--------+
|  SchedulingAgent-MonthlyBillExceeds100USD           |  100.0  |
|  SchedulingAgent-MonthlyBillExceeds200USD           |  200.0  |
+------------------------------------------------------+--------+
```

✅ **Success:** Shows both alarms with correct thresholds

---

## Step 8: Update Terraform Backend Configuration

### 8.1 Get Your Bucket Name

```bash
aws sts get-caller-identity --query Account --output text
```

**Expected Output:**
```
123456789012
```

**Your bucket name is:** `projectsforce-terraform-state-123456789012`

---

### 8.2 Update main.tf

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/
```

Edit the `main.tf` file and update the S3 backend bucket name:

```hcl
backend "s3" {
  bucket         = "projectsforce-terraform-state-123456789012"  # ← Use your actual account number
  key            = "scheduling-agent/bedrock/terraform.tfstate"
  region         = "us-east-1"
  encrypt        = true
  dynamodb_table = "terraform-lock"
}
```

---

## Step 9: Final Verification

### 9.1 Run Complete Verification

```bash
echo "=== AWS Setup Verification ==="
echo ""

echo "1. AWS Identity:"
aws sts get-caller-identity --query 'Account' --output text
echo ""

echo "2. S3 Bucket:"
aws s3 ls | grep terraform-state
echo ""

echo "3. DynamoDB Table:"
aws dynamodb describe-table --table-name terraform-lock --query 'Table.TableStatus' --output text
echo ""

echo "4. Secrets:"
aws secretsmanager list-secrets --query 'SecretList[?contains(Name, `scheduling-agent`)].Name' --output text
echo ""

echo "5. Log Groups:"
aws logs describe-log-groups --log-group-name-prefix /aws --query 'logGroups[?contains(logGroupName, `scheduling-agent`)].logGroupName' --output text
echo ""

echo "6. Billing Alarms:"
aws cloudwatch describe-alarms --alarm-name-prefix "SchedulingAgent" --query 'MetricAlarms[].AlarmName' --output text
echo ""

echo "7. Bedrock Model Access (requires approval):"
aws bedrock list-foundation-models --region us-east-1 --query 'modelSummaries[?contains(modelId, `claude-sonnet-4-5`)].modelId' --output text 2>/dev/null || echo "NOT YET APPROVED (check after 24-48 hours)"
echo ""

echo "=== Verification Complete ==="
```

---

### 9.2 Expected Complete Output

```
=== AWS Setup Verification ===

1. AWS Identity:
123456789012

2. S3 Bucket:
2025-10-12 19:00:00 projectsforce-terraform-state-123456789012

3. DynamoDB Table:
ACTIVE

4. Secrets:
scheduling-agent/aurora/master-password	scheduling-agent/jwt/secret-key	scheduling-agent/pf360/api-credentials

5. Log Groups:
/aws/ecs/scheduling-agent	/aws/lambda/scheduling-agent	/aws/bedrock/scheduling-agent

6. Billing Alarms:
SchedulingAgent-MonthlyBillExceeds100USD	SchedulingAgent-MonthlyBillExceeds200USD

7. Bedrock Model Access (requires approval):
NOT YET APPROVED (check after 24-48 hours)

=== Verification Complete ===
```

✅ **Success:** All items show valid values
❌ **Failure:** Any item shows error or empty output

---

## Step 10: What to Do While Waiting for Bedrock Approval

While waiting for Bedrock model access (24-48 hours), you can:

### 10.1 Install Terraform

```bash
# macOS
brew install terraform

# Verify
terraform version
```

**Expected Output:**
```
Terraform v1.5.x
```

---

### 10.2 Initialize Terraform (Will Fail Until Backend is Updated)

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/

# First, update main.tf with your bucket name (see Step 8.2)

# Then initialize
terraform init
```

**Expected Output:**
```
Initializing the backend...
Successfully configured the backend "s3"!
...
Terraform has been successfully initialized!
```

✅ **Success:** Shows "successfully initialized"

---

### 10.3 Create terraform.tfvars

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/

cat > terraform.tfvars <<EOF
# AWS Configuration
aws_region = "us-east-1"
environment = "dev"

# Network Configuration
vpc_cidr = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b"]

# Aurora Configuration
aurora_instance_class = "db.serverless"
aurora_min_capacity = 0.5
aurora_max_capacity = 1.0

# Redis Configuration
redis_node_type = "cache.t4g.micro"
redis_num_cache_nodes = 1

# Bedrock Configuration
bedrock_model_id = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
bedrock_agent_name = "scheduling-agent"

# Tags
project_name = "scheduling-agent"
managed_by = "terraform"
EOF

echo "Created terraform.tfvars"
```

---

### 10.4 Validate Terraform Configuration

```bash
terraform validate
```

**Expected Output:**
```
Success! The configuration is valid.
```

✅ **Success:** Configuration is valid

---

## Step 11: After Bedrock Approval (24-48 Hours Later)

### 11.1 Check Email for Approval

Look for email from AWS with subject: **"Amazon Bedrock model access granted"**

---

### 11.2 Verify Bedrock Access

```bash
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query 'modelSummaries[?contains(modelId, `claude-sonnet-4-5`)].modelId' \
  --output text
```

**Expected Output:**
```
us.anthropic.claude-sonnet-4-5-20250929-v1:0
```

✅ **Success:** Model ID is shown - YOU CAN NOW PROCEED WITH TERRAFORM

---

### 11.3 Plan Terraform Infrastructure

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/

terraform plan -out=tfplan
```

**This will show all resources to be created (review carefully)**

---

### 11.4 Apply Terraform Infrastructure

```bash
terraform apply tfplan
```

**This will provision:**
- VPC with public/private subnets
- Aurora PostgreSQL Serverless v2
- Redis ElastiCache
- Bedrock Agent
- Security groups
- IAM roles

**Estimated time:** 15-20 minutes

---

### 11.5 Save Terraform Outputs

```bash
terraform output -json > ../outputs.json
echo "Outputs saved to ../outputs.json"

# Display key outputs
terraform output vpc_id
terraform output aurora_cluster_endpoint
terraform output redis_endpoint
terraform output bedrock_agent_id
```

---

## Completion Checklist

- [ ] AWS CLI configured and verified
- [ ] Bedrock model access requested (wait 24-48 hours)
- [ ] S3 bucket created with versioning and encryption
- [ ] DynamoDB table created for state locking
- [ ] 3 secrets created in Secrets Manager
- [ ] 3 CloudWatch log groups created with 7-day retention
- [ ] 2 billing alarms created ($100 and $200)
- [ ] Terraform backend configured with your bucket name
- [ ] Terraform initialized successfully
- [ ] terraform.tfvars created with configuration
- [ ] Bedrock model access approved (after 24-48 hours)
- [ ] Terraform plan reviewed
- [ ] Terraform infrastructure applied successfully

---

## Cost Summary

**Current monthly costs from setup:**
- S3 bucket: ~$0.10/month (minimal storage)
- DynamoDB table: $0/month (pay-per-request, no writes yet)
- Secrets Manager: $1.20/month (3 secrets × $0.40)
- CloudWatch log groups: $0/month (no logs yet)
- CloudWatch alarms: $0.20/month (2 alarms × $0.10)

**Total current cost:** ~$1.50/month

**After Terraform apply:**
- See bedrock/docs/AWS_SETUP_GUIDE.md line 438 for full cost breakdown
- Estimated: $156-206/month for Phase 1

---

## Troubleshooting

### Error: "Unable to locate credentials"

**Fix:**
```bash
aws configure
# Re-enter your access key and secret key
```

---

### Error: "BucketAlreadyExists"

**Fix:**
```bash
# Use a different bucket name
export BUCKET_NAME="projectsforce-tf-state-$(date +%s)"
# Then retry S3 bucket creation
```

---

### Error: "AccessDenied" on any operation

**Fix:**
1. Check IAM user has required permissions
2. Verify you're using correct AWS credentials
3. Attach `PowerUserAccess` policy to your IAM user

---

### Error: "ResourceInUseException" for DynamoDB

**This is OK** - table already exists. Skip to verification step.

---

### Error: "ResourceExistsException" for Secrets

**This is OK** - secret already exists. You can update it or skip.

---

## Next Steps

After completing this setup:

1. **Read:** bedrock/docs/GETTING_STARTED.md for development setup
2. **Read:** bedrock/docs/MIGRATION_PLAN.md for implementation plan
3. **Start:** Backend development in bedrock/backend/
4. **Create:** Lambda functions in bedrock/lambda/
5. **Build:** Frontend in bedrock/frontend/

---

## Support

- **AWS Documentation:** https://docs.aws.amazon.com/
- **Terraform AWS Provider:** https://registry.terraform.io/providers/hashicorp/aws/
- **Bedrock Documentation:** https://docs.aws.amazon.com/bedrock/

---

**Setup Duration:** ~30 minutes + 24-48 hours for Bedrock approval

**Last Updated:** October 12, 2025
