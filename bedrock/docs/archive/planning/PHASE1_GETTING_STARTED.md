# Phase 1 Implementation - Getting Started Guide

**Current Status:** AWS infrastructure setup complete, waiting for Bedrock approval
**Timeline:** Can start development immediately, deploy after Bedrock approval (24-48 hours)

---

## What You've Completed ✅

From your AWS setup:
- ✅ S3 bucket for Terraform state: `projectsforce-terraform-state-618048437522`
- ✅ DynamoDB table for state locking: `terraform-lock`
- ✅ Secrets Manager secrets:
  - `scheduling-agent/aurora/master-password`
  - `scheduling-agent/jwt/secret-key`
  - `scheduling-agent/pf360/api-credentials`
- ✅ CloudWatch log groups (7-day retention)
- ✅ Billing alarms ($100, $200 thresholds)
- ✅ Terraform files:
  - `infrastructure/main.tf` (backend config)
  - `infrastructure/variables.tf` (input variables)
  - `infrastructure/networking.tf` (VPC, subnets, security groups)
  - `infrastructure/outputs.tf` (output definitions)
- ✅ Backend folder structure:
  - `backend/app/api/` (empty)
  - `backend/app/core/` (empty)
  - `backend/app/models/` (empty)
  - `backend/app/schemas/` (empty)
  - `backend/app/services/` (empty)
  - `backend/requirements.txt`
  - `backend/pyproject.toml`

---

## What's Pending ⏳

**Waiting for Bedrock approval (24-48 hours):**
- ⏳ Bedrock model access for Claude 3.5 Sonnet
  - Check status: https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess
  - You'll receive email when approved

**Can do NOW while waiting:**
- 🔨 Complete Terraform infrastructure files
- 🔨 Build backend application code
- 🔨 Set up database models
- 🔨 Write tests
- 🔨 Create Lambda functions for PF360 integration

---

## Implementation Order (Phase 1)

### WEEK 1: Infrastructure & Backend Foundation (NOW - Before Bedrock Approval)

**Priority tasks you can do immediately:**

#### Task 1: Complete Terraform Files (2-3 hours)

Create missing Terraform files:

1. **aurora.tf** - Aurora PostgreSQL Serverless v2
2. **redis.tf** - ElastiCache Redis
3. **iam.tf** - IAM roles for ECS, Lambda, Bedrock
4. **secrets.tf** - Reference existing secrets
5. **bedrock.tf** - Bedrock Agent (will fail until approval, but prepare it)

**Status:** Ready to create now

---

#### Task 2: Update Terraform Backend Configuration (5 minutes)

Update `infrastructure/main.tf` line 12:

**Current:**
```hcl
bucket = "projectsforce-terraform-state"
```

**Change to:**
```hcl
bucket = "projectsforce-terraform-state-618048437522"
```

**Command:**
```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/

# Update bucket name
sed -i '' 's/projectsforce-terraform-state"/projectsforce-terraform-state-618048437522"/' main.tf
```

---

#### Task 3: Create terraform.tfvars (5 minutes)

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
aurora_master_username = "dbadmin"
aurora_database_name = "scheduling_agent"
aurora_min_capacity = 0.5
aurora_max_capacity = 1.0

# Redis Configuration
redis_node_type = "cache.t4g.micro"
redis_num_cache_nodes = 1
redis_parameter_group_family = "redis7"

# Bedrock Configuration
bedrock_agent_name = "scheduling-agent"
bedrock_model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"

# Tags
additional_tags = {
  Owner = "ProjectsForce"
  Cost_Center = "Engineering"
}
EOF

echo "✅ terraform.tfvars created"
```

---

#### Task 4: Initialize Terraform (5 minutes)

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/

# Initialize Terraform with S3 backend
terraform init

# Validate configuration
terraform validate
```

**Expected output:**
```
Initializing the backend...
Successfully configured the backend "s3"!
Terraform has been successfully initialized!
```

---

#### Task 5: Build Backend Application (4-6 hours)

Create core backend files:

**Priority order:**

1. **app/core/config.py** - Configuration management
2. **app/core/database.py** - Database connection
3. **app/models/session.py** - Session model
4. **app/models/project.py** - Project model
5. **app/models/appointment.py** - Appointment model
6. **app/schemas/chat.py** - Request/response schemas
7. **app/api/routes.py** - API endpoints
8. **app/services/bedrock_service.py** - Bedrock Agent integration
9. **app/main.py** - FastAPI application
10. **alembic/env.py** - Database migrations

**Can start NOW** - doesn't require Bedrock approval

---

#### Task 6: Set Up Local Development (30 minutes)

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/backend/

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your values
# (You'll add Aurora/Redis endpoints after Terraform apply)
```

---

#### Task 7: Write Tests (2-3 hours)

Create test files:

1. **tests/test_config.py** - Configuration tests
2. **tests/test_models.py** - Model tests
3. **tests/test_api.py** - API endpoint tests
4. **tests/test_bedrock_service.py** - Bedrock service tests (mocked)

**Can start NOW** - use mocks for external dependencies

---

### WEEK 2: Infrastructure Deployment (After Bedrock Approval)

**After receiving Bedrock approval email:**

#### Task 8: Verify Bedrock Access

```bash
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query 'modelSummaries[?contains(modelId, `claude-3-5-sonnet`)].modelId' \
  --output text
```

**Expected output:**
```
anthropic.claude-3-5-sonnet-20240620-v1:0
```

✅ **If you see this, you can proceed with Terraform deployment**

---

#### Task 9: Deploy Infrastructure with Terraform (15-20 minutes)

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/

# Plan infrastructure
terraform plan -out=tfplan

# Review the plan carefully (should show ~40-50 resources to create)

# Apply infrastructure
terraform apply tfplan
```

**Resources created:**
- VPC with public/private subnets (2 AZs)
- NAT gateways (2)
- Aurora PostgreSQL Serverless v2 cluster
- Redis ElastiCache cluster
- Bedrock Agent
- IAM roles and policies
- Security groups

**Duration:** 15-20 minutes

---

#### Task 10: Save Infrastructure Outputs

```bash
# Save outputs to file
terraform output -json > ../outputs.json

# Display key outputs
echo "Aurora Endpoint:"
terraform output aurora_cluster_endpoint

echo "Redis Endpoint:"
terraform output redis_endpoint

echo "Bedrock Agent ID:"
terraform output bedrock_agent_id
```

---

#### Task 11: Update Backend .env File

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/backend/

# Get outputs from Terraform
AURORA_ENDPOINT=$(cd ../infrastructure && terraform output -raw aurora_cluster_endpoint)
REDIS_ENDPOINT=$(cd ../infrastructure && terraform output -raw redis_endpoint)
BEDROCK_AGENT_ID=$(cd ../infrastructure && terraform output -raw bedrock_agent_id)
AURORA_PASSWORD=$(aws secretsmanager get-secret-value --secret-id scheduling-agent/aurora/master-password --query SecretString --output text)

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

# PF360 API (from current system - core/tools.py line 20)
CUSTOMER_SCHEDULER_API_URL=https://your-pf360-api-url.com

# Secrets
JWT_SECRET_KEY=$(aws secretsmanager get-secret-value --secret-id scheduling-agent/jwt/secret-key --query SecretString --output text)

# Feature Flags (from current system - core/tools.py lines 22-23)
CONFIRM_SCHEDULE_FLAG=1
CANCEL_SCHEDULE_FLAG=1
EOF

echo "✅ .env file updated with infrastructure endpoints"
```

---

#### Task 12: Run Database Migrations

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/backend/

# Activate virtual environment
source venv/bin/activate

# Create initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head
```

---

#### Task 13: Test Backend Locally

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/backend/

# Run FastAPI development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Test endpoints:**
```bash
# Health check
curl http://localhost:8000/api/healthz

# Chat endpoint (test)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "authorization: Bearer test-token" \
  -H "client_id: 09PF05VD" \
  -d '{
    "message": "Hello",
    "session_id": "test-123",
    "customer_id": "1645975",
    "client_name": "projectsforce-validation"
  }'
```

---

#### Task 14: Run Tests

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/backend/

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

**Target:** 80%+ code coverage

---

### WEEK 3: Lambda Functions & Integration

#### Task 15: Create Lambda Functions for PF360 Integration

**From current system analysis:**
- Current system makes direct API calls to PF360 (from `core/tools.py`)
- Phase 1 should use Lambda functions as middleware

**Lambda functions needed:**

1. **lambda-get-projects** - Get available projects (tools.py line 156)
2. **lambda-get-working-days** - Get business hours (tools.py line 351)
3. **lambda-get-available-dates** - Get available dates (tools.py line 361)
4. **lambda-get-slots** - Get slots for date (tools.py lines 387-390)
5. **lambda-confirm-schedule** - Confirm appointment (tools.py line 439)
6. **lambda-cancel-schedule** - Cancel appointment (tools.py line 406)
7. **lambda-add-note** - Add project note (tools.py line 511)

**Create Lambda functions in:** `bedrock/lambda/`

---

#### Task 16: Deploy Lambda Functions

```bash
# Will be handled by Terraform or AWS SAM
```

---

### WEEK 4: Frontend & Deployment

#### Task 17: Build React Frontend

Create frontend in `bedrock/frontend/`:

1. React 18+ with TypeScript
2. Vite build setup
3. Chat interface
4. API integration

---

#### Task 18: Set Up CI/CD Pipeline

Create deployment pipeline (GitHub Actions or Bitbucket Pipelines)

---

#### Task 19: Deploy to Staging

Test full system in staging environment

---

#### Task 20: Deploy to Production

Production deployment after validation

---

## Current Next Steps (RIGHT NOW)

**You can start these tasks immediately without Bedrock approval:**

### Step 1: Fix Terraform Backend (2 minutes)

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/

# Update bucket name in main.tf
sed -i '' 's/projectsforce-terraform-state"/projectsforce-terraform-state-618048437522"/' main.tf

# Verify change
grep bucket main.tf
```

---

### Step 2: Create terraform.tfvars (2 minutes)

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/

cat > terraform.tfvars <<'EOF'
aws_region = "us-east-1"
environment = "dev"
vpc_cidr = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b"]
aurora_master_username = "dbadmin"
aurora_database_name = "scheduling_agent"
aurora_min_capacity = 0.5
aurora_max_capacity = 1.0
redis_node_type = "cache.t4g.micro"
redis_num_cache_nodes = 1
redis_parameter_group_family = "redis7"
bedrock_agent_name = "scheduling-agent"
bedrock_model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
EOF
```

---

### Step 3: Initialize Terraform (2 minutes)

```bash
terraform init
terraform validate
```

---

### Step 4: Choose Development Track

**Option A: Complete Terraform Files First (Recommended)**
- Complete infrastructure code
- Ready to deploy immediately after Bedrock approval
- Duration: 2-3 hours

**Option B: Build Backend Application First**
- Build FastAPI application
- Write tests
- Can develop/test without infrastructure
- Duration: 4-6 hours

**Option C: Parallel Development (If you have a team)**
- One person: Terraform files
- Another person: Backend code
- Duration: 2-3 hours (parallel)

---

## What I Can Help You With

**Choose one:**

1. **"Create all Terraform files"** - I'll create aurora.tf, redis.tf, bedrock.tf, iam.tf, secrets.tf
2. **"Build the backend application"** - I'll create all backend Python files
3. **"Create Lambda functions"** - I'll create Lambda functions for PF360 integration
4. **"Set up database models"** - I'll create SQLAlchemy models and migrations
5. **"Write tests"** - I'll create comprehensive test suite

**What would you like to work on first?**

---

## Resources

**Documentation:**
- bedrock/docs/AWS_SETUP_GUIDE.md - AWS setup reference
- bedrock/docs/AWS_SETUP_STEP_BY_STEP.md - Step-by-step AWS setup
- bedrock/docs/MIGRATION_PLAN.md - Gap analysis and migration plan
- bedrock/docs/GETTING_STARTED.md - Week-by-week implementation guide
- docs/TECHNICAL_FLOW.md - Current system technical flow (reference for replication)

**Current System (for reference):**
- api/routes.py - Current API endpoints
- core/tools.py - Current PF360 integration (527 lines)
- core/langchain_agent.py - Current agent setup
- models/schemas.py - Current request/response models

---

## Cost Tracking

**Current monthly cost:** ~$1.50/month (S3, Secrets, alarms)

**After Terraform apply:** $156-206/month
- Aurora Serverless v2: $25-50
- Redis: $12
- Bedrock: $15-30
- ECS Fargate: $15
- Lambda: $5
- NAT Gateway: $65
- Other: $24.20

**Check costs:**
```bash
# View billing dashboard
open https://console.aws.amazon.com/billing/home

# Check current month spend
aws ce get-cost-and-usage \
  --time-period Start=2025-10-01,End=2025-10-31 \
  --granularity MONTHLY \
  --metrics BlendedCost
```

---

## Troubleshooting

### Bedrock Approval Taking Too Long

**If >48 hours and no approval:**
1. Check AWS email (including spam folder)
2. Check Bedrock console status
3. Contact AWS Support

### Terraform Init Fails

**Error: "Failed to get existing workspaces"**
- Check bucket name is correct: `projectsforce-terraform-state-618048437522`
- Verify S3 bucket exists: `aws s3 ls | grep terraform-state`

### Can't Access Infrastructure

**Error: "AccessDenied" when running Terraform**
- Check AWS credentials: `aws sts get-caller-identity`
- Verify IAM permissions include EC2, RDS, ElastiCache, Bedrock

---

**Last Updated:** October 12, 2025
**Status:** Ready to start Phase 1 development
