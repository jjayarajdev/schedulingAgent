# Quick Start Guide - New Environment Deployment

## Prerequisites Checklist
- [ ] AWS CLI configured (`aws configure`)
- [ ] Terraform installed
- [ ] Python 3.11 installed
- [ ] Bedrock Claude 3.5 Sonnet v2 access enabled in AWS Console
- [ ] Region set to `us-east-1` (or your preferred region)

## Option 1: Automated Deployment (Recommended)

### Single Command Deployment
```bash
cd ~/workspaces/schedulingAgent-bb/bedrock
./DEPLOY_NEW_ENVIRONMENT.sh
```

This script will:
1. Deploy Terraform infrastructure (agents, lambdas, DynamoDB)
2. Deploy Step Functions (3 state machines + 3 lambdas)
3. Run verification tests
4. Configure backend and frontend
5. Display next steps

**Duration**: ~30-45 minutes

---

## Option 2: Manual Step-by-Step Deployment

### Step 1: Deploy Core Infrastructure (5-10 min)
```bash
cd infrastructure/terraform
terraform init
terraform apply
./prepare_agents.sh
```

### Step 2: Deploy Step Functions (2-3 min)
```bash
cd ../../
./scripts/deploy_all_step_functions.sh
```

### Step 3: Test Deployment (5 min)
```bash
# Test agents
cd infrastructure/terraform
python3 test_supervisor_routing.py

# Test Step Functions
cd ../../tests
python3 test_step_functions.py
```

### Step 4: Start Backend (1 min)
```bash
cd ../frontend/backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file with your agent IDs
cat > .env <<EOF
AWS_REGION=us-east-1
SUPERVISOR_AGENT_ID=[YOUR_AGENT_ID]
SUPERVISOR_AGENT_ALIAS_ID=TSTALIASID
EOF

python app.py
```

### Step 5: Start Frontend (1 min)
```bash
# In new terminal
cd frontend
npm install
npm start
```

### Step 6: Test
Open browser: `http://localhost:3000`

Try query: "Show me all my projects"

---

## Quick Commands Reference

### Get Agent IDs
```bash
aws bedrock-agent list-agents --region us-east-1 | \
  jq -r '.agentSummaries[] | "\(.agentName): \(.agentId)"'
```

### Get Lambda Functions
```bash
aws lambda list-functions --region us-east-1 | \
  jq -r '.Functions[] | select(.FunctionName | contains("pf-")) | .FunctionName'
```

### Get State Machines
```bash
aws stepfunctions list-state-machines --region us-east-1 | \
  jq -r '.stateMachines[] | select(.name | contains("pf-")) | .name'
```

### View Logs
```bash
# Backend logs
tail -f frontend/backend/logs/app.log

# Lambda logs
aws logs tail /aws/lambda/pf-query-router --follow

# Step Functions logs
aws logs tail /aws/states/pf-schedule-urgent-project --follow
```

### Test Commands
```bash
# Test backend
curl http://localhost:5001/health

# Test agent invocation
curl -X POST http://localhost:5001/invoke-agent \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Show me all my projects"}'

# Test Step Functions
python3 tests/test_step_functions.py
```

---

## Deployment Order (Critical!)

**DO NOT SKIP** - Follow this exact order:

1. ✅ Terraform core infrastructure
2. ✅ `prepare_agents.sh` (creates agent aliases)
3. ✅ Step Functions deployment
4. ✅ Verification tests
5. ✅ Backend configuration
6. ✅ Frontend configuration
7. ✅ Start servers

---

## Common Issues & Quick Fixes

### Issue: Terraform fails with "AccessDeniedException"
```bash
# Enable Bedrock model access in AWS Console
# Bedrock → Model Access → Request Claude 3.5 Sonnet v2
# Wait 5-10 minutes
```

### Issue: Agent not found
```bash
# Wait for agents to be created
sleep 60
cd infrastructure/terraform
./prepare_agents.sh
```

### Issue: Step Functions deployment error
```bash
# Re-run deployment (idempotent)
./scripts/deploy_all_step_functions.sh
```

### Issue: Backend can't connect to AWS
```bash
# Verify credentials
aws sts get-caller-identity

# Reconfigure if needed
aws configure
```

### Issue: Frontend CORS error
```bash
# Check backend is running on port 5001
curl http://localhost:5001/health

# Verify CORS in backend/app.py
grep -A 2 "CORS" frontend/backend/app.py
```

---

## Files You Need

### Configuration Files to Create:

**frontend/backend/.env**
```env
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=[YOUR_ACCOUNT_ID]
SUPERVISOR_AGENT_ID=[FROM_AWS_CONSOLE]
SUPERVISOR_AGENT_ALIAS_ID=TSTALIASID
QUERY_ROUTER_LAMBDA=pf-query-router
DYNAMODB_TABLE=pf-session-data-dev
FRONTEND_URL=http://localhost:3000
USE_MOCK_API=true
```

**frontend/.env.local**
```env
REACT_APP_BACKEND_URL=http://localhost:5001
REACT_APP_API_TIMEOUT=30000
```

### Scripts to Execute (in order):

1. `infrastructure/terraform/terraform apply`
2. `infrastructure/terraform/prepare_agents.sh`
3. `scripts/deploy_all_step_functions.sh`
4. `infrastructure/terraform/test_supervisor_routing.py`
5. `tests/test_step_functions.py`
6. `frontend/backend/python app.py`
7. `frontend/npm start`

---

## Success Verification

After deployment, verify:

- [ ] 5 Bedrock agents visible in AWS Console
- [ ] 5+ Lambda functions deployed
- [ ] 3 Step Functions state machines deployed
- [ ] DynamoDB table exists with data
- [ ] Backend responds: `curl http://localhost:5001/health`
- [ ] Frontend loads: `http://localhost:3000`
- [ ] Test query works: "Show me all my projects"
- [ ] Complex query works: "Schedule my most urgent project"

---

## Resource URLs

### AWS Console (us-east-1)
- [Bedrock Agents](https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents)
- [Lambda](https://console.aws.amazon.com/lambda/home?region=us-east-1#/functions)
- [Step Functions](https://console.aws.amazon.com/states/home?region=us-east-1#/statemachines)
- [DynamoDB](https://console.aws.amazon.com/dynamodbv2/home?region=us-east-1#tables)
- [CloudWatch Logs](https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups)

### Documentation
- [Complete Guide](./docs/NEW_ENVIRONMENT_DEPLOYMENT.md) - Full step-by-step guide
- [Step Functions](./docs/STEP_FUNCTIONS_IMPLEMENTATION.md) - State machine details
- [Complex Queries](./docs/COMPLEX_QUERY_SCENARIOS.md) - Supported scenarios
- [Terraform README](./infrastructure/terraform/README.md) - Infrastructure details

---

## Cleanup

To remove all resources:
```bash
# Stop servers (Ctrl+C in terminals)

# Delete Step Functions
aws stepfunctions delete-state-machine \
  --state-machine-arn arn:aws:states:us-east-1:[ACCOUNT]:stateMachine:pf-schedule-urgent-project

# Delete Lambdas
for func in pf-query-router pf-filter-projects pf-weather-evaluator; do
  aws lambda delete-function --function-name $func
done

# Destroy Terraform
cd infrastructure/terraform
terraform destroy
```

---

## Support

For detailed troubleshooting, see:
- [Full Deployment Guide](./docs/NEW_ENVIRONMENT_DEPLOYMENT.md#troubleshooting)
- CloudWatch Logs for error details
- Terraform plan output for infrastructure issues

---

**Quick Start Version 1.0**
Last Updated: 2025-10-28
