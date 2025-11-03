# Complete Deployment Guide for New AWS Environment

This guide provides step-by-step instructions to deploy the entire scheduling agent system in a new AWS environment from scratch.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Deployment Order](#deployment-order)
4. [Verification Steps](#verification-steps)
5. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools
- AWS CLI v2.x or higher
- Terraform v1.5 or higher
- Python 3.11 or higher
- Git
- Bash shell (Linux/macOS) or Git Bash (Windows)
- jq (JSON processor)

### AWS Account Requirements
- AWS Account with administrative access
- AWS Region: `us-east-1` (recommended, can be changed)
- Service quotas:
  - Bedrock Claude 3.5 Sonnet access enabled
  - Lambda concurrent executions: 10+
  - Step Functions state machines: 10+
  - IAM roles: 10+
  - DynamoDB tables: 5+

### Install Required Tools

```bash
# AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Terraform
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Python 3.11 (if not already installed)
sudo apt update && sudo apt install python3.11 python3.11-venv

# jq
sudo apt install jq
```

### Configure AWS Credentials

```bash
# Configure AWS CLI
aws configure

# Verify configuration
aws sts get-caller-identity

# Enable Bedrock Claude 3.5 Sonnet in us-east-1 region
# Go to AWS Console → Bedrock → Model Access → Request Access
# Request: Claude 3.5 Sonnet v2 (us.anthropic.claude-3-5-sonnet-20241022-v2:0)
```

---

## Environment Setup

### 1. Clone Repository

```bash
cd ~/workspaces
git clone https://github.com/your-org/schedulingAgent-bb.git
cd schedulingAgent-bb/bedrock
```

### 2. Set Environment Variables

```bash
# Create environment configuration file
cat > .env <<EOF
# AWS Configuration
export AWS_REGION="us-east-1"
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Project Configuration
export PROJECT_PREFIX="pf"
export ENVIRONMENT="dev"

# Bedrock Model
export BEDROCK_MODEL_ID="us.anthropic.claude-3-5-sonnet-20241022-v2:0"

# DynamoDB Configuration
export DYNAMODB_TABLE_NAME="${PROJECT_PREFIX}-session-data-${ENVIRONMENT}"

# Frontend Configuration
export FRONTEND_PORT="3000"
export BACKEND_PORT="5001"
EOF

# Load environment variables
source .env

# Add to your shell profile for persistence
echo 'source ~/workspaces/schedulingAgent-bb/bedrock/.env' >> ~/.bashrc
```

---

## Deployment Order

### Phase 1: Core Infrastructure (Terraform)

#### Step 1.1: Initialize Terraform

```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Validate configuration
terraform validate

# Review planned changes
terraform plan
```

#### Step 1.2: Deploy Infrastructure

```bash
# Deploy all infrastructure
terraform apply

# Note: This will create:
# - Bedrock Agents (Supervisor + 4 Collaborators)
# - Lambda Functions (information-actions, scheduling-actions)
# - DynamoDB Table (session-data)
# - IAM Roles and Policies
# - CloudWatch Log Groups

# Expected duration: 5-10 minutes
```

#### Step 1.3: Verify Core Deployment

```bash
# Verify Bedrock Agents
aws bedrock-agent list-agents --region $AWS_REGION

# Verify Lambda Functions
aws lambda list-functions --region $AWS_REGION | grep $PROJECT_PREFIX

# Verify DynamoDB Table
aws dynamodb describe-table --table-name $DYNAMODB_TABLE_NAME --region $AWS_REGION

# Output:
# - Supervisor Agent ID: [AGENT_ID]
# - Information Agent ID: [AGENT_ID]
# - Scheduling Agent ID: [AGENT_ID]
# - Notification Agent ID: [AGENT_ID]
# - Escalation Agent ID: [AGENT_ID]
```

#### Step 1.4: Prepare Agents

```bash
# Wait for agents to be created
sleep 30

# Prepare all agents (creates DRAFT aliases and associates action groups)
./prepare_agents.sh

# Expected output:
# ✅ Prepared supervisor agent
# ✅ Prepared information agent
# ✅ Prepared scheduling agent
# ✅ Prepared notification agent
# ✅ Prepared escalation agent
```

#### Step 1.5: Configure Environment-Aware Agent IDs

```bash
# Automatically fetch and populate agent IDs into environment-specific config
cd ../backend
../scripts/fetch_agent_ids.sh $ENVIRONMENT

# This script will:
# - Query AWS Bedrock for all deployed agents
# - Match agents by name pattern (Supervisor, Scheduling, Information, Notes, Chitchat)
# - Fetch appropriate alias IDs for the environment (TSTALIASID for dev)
# - Update backend/agent_config.$ENVIRONMENT.json with actual IDs
# - Preserve all other configuration settings

# Verify the configuration was updated correctly
echo "✅ Agent configuration for $ENVIRONMENT:"
cat agent_config.$ENVIRONMENT.json | jq -r '
  "Environment: \(.environment)",
  "Supervisor: \(.supervisor_id)",
  "Agents:",
  "  - Scheduling: \(.agents.scheduling.agent_id)",
  "  - Information: \(.agents.information.agent_id)",
  "  - Notes: \(.agents.notes.agent_id)",
  "  - Chitchat: \(.agents.chitchat.agent_id)"
'

cd ../infrastructure/terraform
```

**Note**: The backend application will automatically use the environment-specific configuration file (`agent_config.$ENVIRONMENT.json`) based on the `ENVIRONMENT` environment variable. No manual agent ID configuration is needed.

---

### Phase 2: Step Functions Infrastructure

#### Step 2.1: Deploy Lambda Functions for Step Functions

```bash
cd ../../  # Back to bedrock directory

# Deploy all Step Functions infrastructure
./scripts/deploy_all_step_functions.sh

# This deploys:
# - pf-query-router Lambda
# - pf-filter-projects Lambda
# - pf-weather-evaluator Lambda
# - pf-step-functions-role IAM Role
# - pf-schedule-urgent-project State Machine
# - pf-schedule-weather-dependent State Machine
# - pf-schedule-batch-projects State Machine

# Expected duration: 2-3 minutes
```

#### Step 2.2: Verify Step Functions Deployment

```bash
# List deployed Lambda functions
aws lambda list-functions --region $AWS_REGION \
  | jq -r '.Functions[] | select(.FunctionName | contains("pf-")) | .FunctionName'

# List deployed state machines
aws stepfunctions list-state-machines --region $AWS_REGION \
  | jq -r '.stateMachines[] | select(.name | contains("pf-")) | .name'

# Expected output:
# Lambda Functions:
# - pf-query-router
# - pf-filter-projects
# - pf-weather-evaluator
# - pf-information-actions
# - pf-scheduling-actions
#
# State Machines:
# - pf-schedule-urgent-project
# - pf-schedule-weather-dependent
# - pf-schedule-batch-projects
```

---

### Phase 3: Testing Infrastructure

#### Step 3.1: Test Core Bedrock Agents

```bash
cd infrastructure/terraform

# Test Supervisor Agent routing
python3 test_supervisor_routing.py

# Expected output:
# ✅ Information query routed correctly
# ✅ Scheduling query routed correctly
# ✅ Session attributes preserved
```

#### Step 3.2: Test Step Functions

```bash
cd ../../tests

# Test urgent project scheduling
python3 test_step_functions.py

# Expected output:
# ✅ Execution SUCCEEDED
# Found urgent project: PRJ-78945 (Flooring)
```

#### Step 3.3: Test All State Machines (Optional)

```bash
# Comprehensive test of all state machines
python3 test_all_state_machines.py

# Expected output:
# ✅ PASSED: X/Y tests
# 📊 PASS RATE: XX%
```

---

### Phase 4: Backend Deployment

#### Step 4.1: Install Python Dependencies

```bash
cd ../frontend/backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Expected packages:
# - flask
# - flask-cors
# - boto3
# - python-dotenv
```

#### Step 4.2: Configure Backend

```bash
# Automatically fetch and populate agent IDs from AWS
cd backend
../scripts/fetch_agent_ids.sh $ENVIRONMENT

# This will:
# - Fetch all Bedrock agent IDs from AWS
# - Match agents by name pattern
# - Update backend/agent_config.$ENVIRONMENT.json with actual IDs
# - Set appropriate alias IDs for the environment

# Verify the configuration was updated
echo "Agent configuration for $ENVIRONMENT:"
cat agent_config.$ENVIRONMENT.json | jq '{supervisor_id, agents}'

# Set environment variable for backend to use correct config
export ENVIRONMENT=$ENVIRONMENT

# Optional: Create .env file for additional configuration
cat > .env <<EOF
# AWS Configuration
AWS_REGION=$AWS_REGION
AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID

# Environment (determines which agent_config file to use)
ENVIRONMENT=$ENVIRONMENT

# Query Router Configuration
QUERY_ROUTER_LAMBDA=pf-query-router

# DynamoDB Configuration
DYNAMODB_TABLE=$DYNAMODB_TABLE_NAME

# CORS Configuration
FRONTEND_URL=http://localhost:3000
EOF

source .env
```

#### Step 4.3: Start Backend Server

```bash
# Start Flask backend
python app.py

# Expected output:
# * Running on http://127.0.0.1:5001
# * Debug mode: on

# Keep this terminal open
```

---

### Phase 5: Frontend Deployment

#### Step 5.1: Install Node.js Dependencies

Open a new terminal:

```bash
cd schedulingAgent-bb/bedrock/frontend

# Install dependencies
npm install

# Expected packages:
# - react
# - axios
# - react-router-dom
# - tailwindcss
```

#### Step 5.2: Configure Frontend

```bash
# Update frontend configuration
cat > .env.local <<EOF
REACT_APP_BACKEND_URL=http://localhost:5001
REACT_APP_API_TIMEOUT=30000
EOF
```

#### Step 5.3: Start Frontend Development Server

```bash
# Start React development server
npm start

# Expected output:
# Compiled successfully!
# Local: http://localhost:3000
#
# The app will automatically open in your browser
```

---

## Verification Steps

### 1. End-to-End Test via Frontend

Open browser to `http://localhost:3000`

**Test Case 1: Simple Information Query**
```
Query: "Show me all my projects"
Expected: List of projects displayed
Agent: Information Agent (via Supervisor)
```

**Test Case 2: Simple Scheduling Query**
```
Query: "Schedule project PRJ-78945 for Monday at 10 AM"
Expected: Scheduling confirmation or available times
Agent: Scheduling Agent (via Supervisor)
```

**Test Case 3: Complex Query (Step Functions)**
```
Query: "Schedule my most urgent project for the earliest time"
Expected: Urgent project identified and ready to schedule
Route: Step Functions (pf-schedule-urgent-project)
```

**Test Case 4: Weather-Dependent Query**
```
Query: "If the weather is good, schedule my outdoor flooring project"
Expected: Weather evaluation and scheduling recommendation
Route: Step Functions (pf-schedule-weather-dependent)
```

**Test Case 5: Batch Scheduling Query**
```
Query: "Schedule all my pending installation projects"
Expected: List of projects ready for batch scheduling
Route: Step Functions (pf-schedule-batch-projects)
```

### 2. Backend Health Check

```bash
# Test backend endpoint
curl http://localhost:5001/health

# Expected response:
# {"status": "healthy", "timestamp": "..."}
```

### 3. AWS Console Verification

**Bedrock Agents:**
- Console → Bedrock → Agents
- Verify all 5 agents are "Prepared" status
- Check agent aliases are created

**Lambda Functions:**
- Console → Lambda → Functions
- Verify all 5+ Lambda functions exist
- Check recent invocations

**Step Functions:**
- Console → Step Functions → State machines
- Verify 3 state machines exist
- Check execution history

**DynamoDB:**
- Console → DynamoDB → Tables
- Verify session data table exists
- Check item count > 0 after testing

**CloudWatch Logs:**
- Console → CloudWatch → Log groups
- Verify logs for all Lambda functions
- Check for errors

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: Terraform Apply Fails

**Error**: `Error creating Bedrock Agent: AccessDeniedException`

**Solution**:
```bash
# Verify Bedrock model access
aws bedrock list-foundation-models --region $AWS_REGION \
  | grep -i claude

# If no models listed, request access in AWS Console:
# Bedrock → Model Access → Request Access for Claude 3.5 Sonnet v2

# Wait 5-10 minutes for approval
```

#### Issue 2: Agent Preparation Fails

**Error**: `Agent not found` or `Alias creation failed`

**Solution**:
```bash
# Check agent creation status
aws bedrock-agent get-agent --agent-id [AGENT_ID] --region $AWS_REGION

# If status is "Creating", wait longer:
sleep 60

# Retry preparation
./prepare_agents.sh
```

#### Issue 3: Step Functions Deployment Error

**Error**: `Invalid State Machine Definition`

**Solution**:
```bash
# Validate JSON syntax
cat infrastructure/step-functions/state-machines/schedule-urgent-project.json | jq .

# If syntax error, fix JSON and redeploy:
./scripts/deploy_all_step_functions.sh
```

#### Issue 4: Lambda Function Timeout

**Error**: `Task timed out after 30.00 seconds`

**Solution**:
```bash
# Increase Lambda timeout
aws lambda update-function-configuration \
  --function-name pf-query-router \
  --timeout 60 \
  --region $AWS_REGION
```

#### Issue 5: Backend Can't Connect to AWS

**Error**: `Unable to locate credentials`

**Solution**:
```bash
# Verify AWS credentials
aws sts get-caller-identity

# If error, reconfigure:
aws configure

# Verify region
echo $AWS_REGION

# If empty:
export AWS_REGION=us-east-1
```

#### Issue 6: Frontend Can't Connect to Backend

**Error**: `Network Error` or `CORS Error`

**Solution**:
```bash
# Check backend is running
curl http://localhost:5001/health

# If not running, restart backend:
cd frontend/backend
source venv/bin/activate
python app.py

# Verify CORS configuration in app.py:
# CORS(app, origins=["http://localhost:3000"])
```

#### Issue 7: Agent Returns Empty Response

**Error**: Agent invocation succeeds but returns no useful data

**Solution**:
```bash
# Check agent instructions
aws bedrock-agent get-agent --agent-id [AGENT_ID] --region $AWS_REGION \
  | jq .agent.instruction

# Verify action groups are associated
aws bedrock-agent list-agent-action-groups \
  --agent-id [AGENT_ID] \
  --agent-version DRAFT \
  --region $AWS_REGION

# If no action groups, run prepare script:
cd infrastructure/terraform
./prepare_agents.sh
```

#### Issue 8: DynamoDB Permission Denied

**Error**: `AccessDeniedException: User is not authorized to perform: dynamodb:PutItem`

**Solution**:
```bash
# Check Lambda execution role permissions
aws iam get-role-policy \
  --role-name pf-information-lambda-role-dev \
  --policy-name pf-information-lambda-policy-dev

# If missing DynamoDB permissions, update Terraform and reapply:
cd infrastructure/terraform
terraform apply
```

---

## Post-Deployment Configuration

### 1. Update Agent Instructions (Optional)

```bash
# Edit agent instructions
aws bedrock-agent update-agent \
  --agent-id [AGENT_ID] \
  --agent-name "pf-supervisor-agent-dev" \
  --instruction "$(cat updated_instructions.txt)" \
  --region $AWS_REGION

# Prepare agent after updates
aws bedrock-agent prepare-agent \
  --agent-id [AGENT_ID] \
  --region $AWS_REGION
```

### 2. Configure Mock vs Real API Mode

```bash
# For testing with mock data:
aws lambda update-function-configuration \
  --function-name pf-information-actions \
  --environment "Variables={USE_MOCK_API=true}" \
  --region $AWS_REGION

# For production with real APIs:
aws lambda update-function-configuration \
  --function-name pf-information-actions \
  --environment "Variables={USE_MOCK_API=false,API_BASE_URL=https://api.yourdomain.com}" \
  --region $AWS_REGION
```

### 3. Enable CloudWatch Logs for Step Functions

```bash
# Enable detailed logging for state machines
aws stepfunctions update-state-machine \
  --state-machine-arn arn:aws:states:$AWS_REGION:$AWS_ACCOUNT_ID:stateMachine:pf-schedule-urgent-project \
  --logging-configuration level=ALL,includeExecutionData=true,destinations='[{"cloudWatchLogsLogGroup":{"logGroupArn":"arn:aws:logs:'$AWS_REGION':'$AWS_ACCOUNT_ID':log-group:/aws/states/pf-schedule-urgent-project"}}]' \
  --region $AWS_REGION
```

---

## Deployment Checklist

Use this checklist to track deployment progress:

### Infrastructure
- [ ] AWS CLI configured
- [ ] Terraform initialized
- [ ] Core infrastructure deployed (Terraform)
- [ ] All 5 Bedrock agents created
- [ ] Agents prepared with action groups
- [ ] Environment-specific agent config populated (fetch_agent_ids.sh)
- [ ] Lambda functions deployed (information, scheduling)
- [ ] DynamoDB table created
- [ ] IAM roles and policies configured

### Step Functions
- [ ] Query router Lambda deployed
- [ ] Filter projects Lambda deployed
- [ ] Weather evaluator Lambda deployed
- [ ] IAM role for Step Functions created
- [ ] Urgent scheduling state machine deployed
- [ ] Weather-dependent state machine deployed
- [ ] Batch scheduling state machine deployed
- [ ] Query router environment variables configured

### Testing
- [ ] Supervisor routing test passed
- [ ] Step Functions test passed
- [ ] All state machines tested (optional)
- [ ] Lambda functions tested individually

### Application
- [ ] Backend dependencies installed
- [ ] Backend configuration updated
- [ ] Backend server running
- [ ] Frontend dependencies installed
- [ ] Frontend configuration updated
- [ ] Frontend server running
- [ ] End-to-end test via UI passed

### Verification
- [ ] AWS Console verification completed
- [ ] Health check endpoint responding
- [ ] CloudWatch logs showing activity
- [ ] DynamoDB table has data
- [ ] All test cases passed

---

## Cleanup / Teardown

If you need to remove all resources:

```bash
# Stop frontend and backend servers
# Ctrl+C in their respective terminals

# Destroy Step Functions infrastructure
cd ~/workspaces/schedulingAgent-bb/bedrock

# Delete state machines
aws stepfunctions delete-state-machine \
  --state-machine-arn arn:aws:states:$AWS_REGION:$AWS_ACCOUNT_ID:stateMachine:pf-schedule-urgent-project

aws stepfunctions delete-state-machine \
  --state-machine-arn arn:aws:states:$AWS_REGION:$AWS_ACCOUNT_ID:stateMachine:pf-schedule-weather-dependent

aws stepfunctions delete-state-machine \
  --state-machine-arn arn:aws:states:$AWS_REGION:$AWS_ACCOUNT_ID:stateMachine:pf-schedule-batch-projects

# Delete Lambda functions
for func in pf-query-router pf-filter-projects pf-weather-evaluator; do
  aws lambda delete-function --function-name $func --region $AWS_REGION
done

# Destroy Terraform infrastructure
cd infrastructure/terraform
terraform destroy

# Confirm with 'yes' when prompted
```

---

## Production Considerations

### Security
1. **API Keys**: Store sensitive keys in AWS Secrets Manager
2. **CORS**: Restrict to specific domains in production
3. **Authentication**: Implement user authentication (Cognito)
4. **VPC**: Deploy Lambda functions in VPC for network isolation

### Monitoring
1. **CloudWatch Dashboards**: Create dashboards for key metrics
2. **Alarms**: Set up alarms for errors and performance
3. **X-Ray**: Enable X-Ray tracing for distributed tracing
4. **Cost Monitoring**: Set up AWS Budgets and Cost Explorer

### Scalability
1. **Lambda Concurrency**: Configure reserved concurrency
2. **DynamoDB Auto-scaling**: Enable auto-scaling for tables
3. **Step Functions**: Monitor state transitions and optimize
4. **Caching**: Implement caching layer (ElastiCache/CloudFront)

### Backup & Disaster Recovery
1. **DynamoDB Backups**: Enable point-in-time recovery
2. **Infrastructure as Code**: Keep Terraform state in S3
3. **Multi-Region**: Consider multi-region deployment for HA
4. **Documentation**: Maintain runbooks for incidents

---

## Support and Resources

### Documentation
- [Terraform Configuration](../infrastructure/terraform/README.md)
- [Step Functions Implementation](./STEP_FUNCTIONS_IMPLEMENTATION.md)
- [Complex Query Scenarios](./COMPLEX_QUERY_SCENARIOS.md)
- [API Migration](./API_MIGRATION_README.md)

### AWS Console Links (us-east-1)
- [Bedrock Agents](https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents)
- [Lambda Functions](https://console.aws.amazon.com/lambda/home?region=us-east-1#/functions)
- [Step Functions](https://console.aws.amazon.com/states/home?region=us-east-1#/statemachines)
- [DynamoDB Tables](https://console.aws.amazon.com/dynamodbv2/home?region=us-east-1#tables)
- [CloudWatch Logs](https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups)

### Getting Help
- Check CloudWatch Logs for errors
- Review Terraform plan before apply
- Test components individually before integration
- Verify AWS service quotas and limits

---

## Deployment Time Estimates

| Phase | Duration | Notes |
|-------|----------|-------|
| Prerequisites | 30-60 min | One-time setup |
| Terraform Infrastructure | 5-10 min | Agent creation is slow |
| Agent Preparation | 2-5 min | Waiting for DRAFT aliases |
| Step Functions | 2-3 min | Lambda deployments |
| Testing | 5-10 min | Verification tests |
| Backend Setup | 5 min | Python environment |
| Frontend Setup | 5 min | Node.js environment |
| **Total** | **~30-45 min** | Excluding prerequisites |

---

## Success Criteria

Deployment is successful when:
1. All Terraform resources created without errors
2. All 5 Bedrock agents in "Prepared" status
3. All Lambda functions deployed and invocable
4. All 3 state machines deployed and executable
5. Backend server responds to health check
6. Frontend loads in browser
7. End-to-end test completes successfully
8. No errors in CloudWatch Logs

---

## Version Information

- **Last Updated**: 2025-10-28
- **Terraform Version**: 1.5+
- **AWS CLI Version**: 2.x
- **Python Version**: 3.11
- **Node.js Version**: 18+ (LTS)
- **Bedrock Model**: Claude 3.5 Sonnet v2
- **AWS Region**: us-east-1 (primary)

---

**End of Deployment Guide**

For questions or issues, refer to the [Troubleshooting](#troubleshooting) section or check CloudWatch Logs for detailed error messages.
