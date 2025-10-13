# Bedrock Multi-Agent Scheduling System

AWS Bedrock-based multi-agent collaboration system with Lambda-powered action groups for property management scheduling.

## 📁 Project Structure

```
bedrock/
├── lambda/                     # Lambda Functions (12 actions) ✅
│   ├── scheduling-actions/     # 6 scheduling actions
│   │   ├── handler.py          # Main Lambda handler
│   │   ├── config.py           # Configuration
│   │   ├── mock_data.py        # Mock API responses
│   │   └── requirements.txt    # Dependencies
│   │
│   ├── information-actions/    # 4 information actions
│   │   ├── handler.py
│   │   ├── config.py
│   │   ├── mock_data.py
│   │   └── requirements.txt
│   │
│   ├── notes-actions/          # 2 notes actions
│   │   ├── handler.py
│   │   ├── config.py
│   │   ├── mock_data.py
│   │   └── requirements.txt
│   │
│   ├── test_all_actions_v2.py       # Individual action tests
│   └── test_complete_flows.py       # Multi-step flow tests
│
├── docs/                       # Comprehensive Documentation
│   ├── DEVELOPER_HANDOVER.md         # 👈 START HERE
│   ├── BEDROCK_LAMBDA_INTEGRATION_GUIDE.md
│   ├── LAMBDA_MOCK_IMPLEMENTATION.md
│   ├── COMPLETE_FLOW_TEST_RESULTS.md
│   ├── MOCK_API_TESTING_RESULTS.md
│   ├── PF360_API_ANALYSIS.md
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT_GUIDE.md
│   ├── TESTING_GUIDE.md
│   ├── ENABLE_API_ACCESS.md
│   └── AWS_SUPPORT_TICKET.md
│
├── tests/                      # Agent Test Scripts
│   ├── test_api_access.py
│   ├── test_agents_interactive.py
│   ├── comprehensive_test.py
│   └── test_agent.py
│
├── infrastructure/             # Terraform IaC
│   ├── openapi_schemas/        # OpenAPI 3.0 schemas for action groups
│   │   ├── scheduling_actions.json
│   │   ├── information_actions.json
│   │   └── notes_actions.json
│   │
│   ├── terraform/              # Terraform configurations
│   │   ├── bedrock_agents.tf  # Multi-agent setup
│   │   ├── variables.tf       # Variables (Claude Sonnet 4.5)
│   │   └── provider.tf
│   │
│   └── agent_instructions/     # Agent instruction files
│       ├── supervisor.txt
│       ├── scheduling_collaborator.txt
│       ├── information_collaborator.txt
│       ├── notes_collaborator.txt
│       └── chitchat_collaborator.txt
│
├── utils/                      # Utility Scripts
│   └── prepare_all_agents.py
│
├── scripts/                    # Shell Scripts
│   ├── gather_diagnostics.sh
│   └── verify_deployment.sh
│
├── backend/                    # Backend services (Phase 2)
│   └── api/
│
├── frontend/                   # Frontend app (Phase 2)
│   └── app/
│
└── knowledge-base/             # Knowledge base (Phase 3)
    └── documents/
```

---

## 🎯 Lambda Functions (Action Groups)

### ✅ All 12 Actions Implemented and Tested

**Test Status:** 🟢 100% Pass Rate (6/6 flows, 22 Lambda invocations)

#### 1. Scheduling Actions (6 actions)
Lambda: `scheduling-actions`

| Action | Purpose | Status |
|--------|---------|--------|
| `list_projects` | List all customer projects | ✅ Tested |
| `get_available_dates` | Get available scheduling dates | ✅ Tested |
| `get_time_slots` | Get time slots for specific date | ✅ Tested |
| `confirm_appointment` | Schedule appointment | ✅ Tested |
| `reschedule_appointment` | Reschedule existing appointment | ✅ Tested |
| `cancel_appointment` | Cancel appointment | ✅ Tested |

#### 2. Information Actions (4 actions)
Lambda: `information-actions`

| Action | Purpose | Status |
|--------|---------|--------|
| `get_project_details` | Get detailed project information | ✅ Tested |
| `get_appointment_status` | Check appointment status | ✅ Tested |
| `get_working_hours` | Get business hours | ✅ Tested |
| `get_weather` | Get weather forecast for location | ✅ Tested |

#### 3. Notes Actions (2 actions)
Lambda: `notes-actions`

| Action | Purpose | Status |
|--------|---------|--------|
| `add_note` | Add note to project | ✅ Tested |
| `list_notes` | List all project notes | ✅ Tested |

---

## 🚀 Quick Start

### For New Developers

**START HERE:**
1. Read [`docs/DEVELOPER_HANDOVER.md`](docs/DEVELOPER_HANDOVER.md)
2. Review [`docs/LAMBDA_MOCK_IMPLEMENTATION.md`](docs/LAMBDA_MOCK_IMPLEMENTATION.md)
3. Check [`docs/COMPLETE_FLOW_TEST_RESULTS.md`](docs/COMPLETE_FLOW_TEST_RESULTS.md)

### 1. Test Lambda Functions Locally

```bash
# Test all actions (individual tests)
cd lambda
export USE_MOCK_API=true
python3 test_all_actions_v2.py

# Test complete conversation flows
python3 test_complete_flows.py
```

### 2. Test Specific Lambda

```bash
cd lambda/scheduling-actions
export USE_MOCK_API=true
python3 handler.py
```

### 3. Test Bedrock Agents (Console)

```bash
# Prepare all agents
cd ../..
python3 utils/prepare_all_agents.py

# Verify deployment
./scripts/verify_deployment.sh

# Interactive testing
python3 tests/test_agents_interactive.py
```

---

## 🔧 Mock/Real API Switching

**Zero code changes required to switch modes!**

### Development Mode (Mock Data)
```bash
export USE_MOCK_API=true
python3 lambda/test_complete_flows.py
```

### Production Mode (Real PF360 APIs)
```bash
export USE_MOCK_API=false
export CUSTOMER_SCHEDULER_API_URL=https://api.projectsforce.com
python3 lambda/test_complete_flows.py
```

**Benefits:**
- ✅ Fast development without API dependencies
- ✅ Consistent test data
- ✅ Seamless production transition
- ✅ No code changes needed

---

## 📚 Documentation

### Essential Guides (Start Here)

**For Developers:**
- **[DEVELOPER_HANDOVER.md](docs/DEVELOPER_HANDOVER.md)** - AWS setup, credentials, deployment status
- **[LAMBDA_MOCK_IMPLEMENTATION.md](docs/LAMBDA_MOCK_IMPLEMENTATION.md)** - Lambda implementation approach
- **[BEDROCK_LAMBDA_INTEGRATION_GUIDE.md](docs/BEDROCK_LAMBDA_INTEGRATION_GUIDE.md)** - How Lambda integrates with Bedrock

**Test Results:**
- **[COMPLETE_FLOW_TEST_RESULTS.md](docs/COMPLETE_FLOW_TEST_RESULTS.md)** - Multi-step flow test results (100% pass)
- **[MOCK_API_TESTING_RESULTS.md](docs/MOCK_API_TESTING_RESULTS.md)** - Individual action test results

**API & Architecture:**
- **[PF360_API_ANALYSIS.md](docs/PF360_API_ANALYSIS.md)** - Analysis of 8 PF360 API endpoints
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture overview

### Deployment & Troubleshooting

- **[DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)** - Step-by-step deployment
- **[TESTING_GUIDE.md](docs/TESTING_GUIDE.md)** - How to test the system
- **[ENABLE_API_ACCESS.md](docs/ENABLE_API_ACCESS.md)** - Fix 403 errors
- **[AWS_SUPPORT_TICKET.md](docs/AWS_SUPPORT_TICKET.md)** - Pre-filled support template

---

## 🤖 Bedrock Agents

### Multi-Agent Architecture

```
User Input (Chat/SMS/Phone)
    ↓
Supervisor Agent (Routes requests)
    ↓
┌───────────┬────────────┬───────────┬──────────┐
│ Scheduling│ Information│   Notes   │ Chitchat │
│ Agent     │   Agent    │   Agent   │  Agent   │
└───────────┴────────────┴───────────┴──────────┘
    ↓            ↓            ↓
Lambda      Lambda       Lambda
Functions   Functions    Functions
    ↓            ↓            ↓
Mock Data OR Real PF360 APIs
```

### Supervisor Agent
- **ID**: `5VTIWONUMO`
- **Latest Alias**: `HH2U7EZXMW` (version 6)
- **Model**: Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`)
- **Role**: Routes requests to specialized collaborators

### Collaborator Agents

| Agent | ID | V4 Alias | Lambda | Actions | Purpose |
|-------|-----|----------|--------|---------|---------|
| **Scheduling** | `IX24FSMTQH` | `TYJRF3CJ7F` | scheduling-actions | 6 | Appointments, availability, booking |
| **Information** | `C9ANXRIO8Y` | `YVNFXEKPWO` | information-actions | 4 | Project details, hours, weather |
| **Notes** | `G5BVBYEPUM` | `F9QQNLZUW8` | notes-actions | 2 | Note management |
| **Chitchat** | `BIUW1ARHGL` | `THIPMPJCPI` | (none) | 0 | Greetings, help, conversation |

**All agents use:** Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`)

---

## 🧪 Testing

### Lambda Function Tests

```bash
# Individual action testing (12 actions)
cd lambda
export USE_MOCK_API=true
python3 test_all_actions_v2.py

# Complete flow testing (6 scenarios)
python3 test_complete_flows.py
```

**Test Results:**
- ✅ 12/12 actions pass individual tests
- ✅ 6/6 complete flows pass (100% success rate)
- ✅ 22 Lambda invocations validated
- ✅ Multi-step data chaining confirmed

### Bedrock Agent Tests

```bash
# API access validation
python3 tests/test_api_access.py

# Interactive testing
python3 tests/test_agents_interactive.py

# Comprehensive test suite
cd tests
python3 comprehensive_test.py
```

### Console Testing (Always Works)

1. Go to: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents
2. Click: `scheduling-agent-supervisor`
3. Click: **Test** button
4. Try conversation scenarios

### Test Scenarios

**Multi-Step Scheduling:**
```
User: "Schedule my flooring installation for October 15th at 10 AM"

Behind the scenes:
1. Agent invokes list_projects → Finds flooring project 12345
2. Agent invokes get_available_dates → Oct 15 available
3. Agent invokes get_time_slots → 10 AM available
4. Agent invokes confirm_appointment → Scheduled!

Agent: "Perfect! Scheduled for Oct 15 at 10 AM. Confirmation: CONF-1760378607"
```

**Other Scenarios:**
- **Greeting**: "Hello! How are you today?"
- **Information**: "What are your working hours?"
- **Weather**: "What's the weather for my installation day?"
- **Notes**: "Add a note that I prefer morning appointments"
- **Reschedule**: "I need to reschedule to October 20th at 2 PM"

---

## 🛠️ Development Workflow

### After Lambda Code Changes

```bash
# 1. Test Lambda locally
cd lambda
export USE_MOCK_API=true
python3 test_all_actions_v2.py
python3 test_complete_flows.py

# 2. Package Lambda (when ready to deploy)
cd scheduling-actions
pip install -r requirements.txt -t package/
cp *.py package/
cd package && zip -r ../scheduling-actions.zip .

# 3. Deploy to AWS Lambda
aws lambda update-function-code \
  --function-name scheduling-agent-scheduling-actions \
  --zip-file fileb://scheduling-actions.zip

# 4. Test via Bedrock Agent console
```

### After Terraform Changes

```bash
# 1. Apply Terraform changes
cd infrastructure/terraform
terraform plan
terraform apply

# 2. Prepare agents
cd ../..
python3 utils/prepare_all_agents.py

# 3. Verify deployment
./scripts/verify_deployment.sh

# 4. Run tests
python3 tests/test_api_access.py
```

### Before Submitting PR

```bash
# Run full test suite
cd lambda
python3 test_all_actions_v2.py
python3 test_complete_flows.py

# Test agents
cd ..
python3 tests/test_agents_interactive.py  # Choose option 1

# Verify deployment
./scripts/verify_deployment.sh

# Generate diagnostic report
./scripts/gather_diagnostics.sh
```

---

## 📊 Current Status

### ✅ Phase 1: Complete - Lambda Implementation

**Lambda Functions:**
- ✅ 3 Lambda functions implemented
- ✅ 12 actions (scheduling, information, notes)
- ✅ Mock/Real API switching
- ✅ Comprehensive testing (100% pass rate)
- ✅ Complete documentation

**Multi-Agent System:**
- ✅ 5 Bedrock agents deployed (supervisor + 4 collaborators)
- ✅ Claude Sonnet 4.5 model upgraded
- ✅ OpenAPI 3.0 schemas created
- ✅ Agent routing and delegation working
- ✅ Console testing functional

**Testing:**
- ✅ Individual action tests (12/12 pass)
- ✅ Complete flow tests (6/6 pass)
- ✅ 22 Lambda invocations validated
- ✅ Multi-step orchestration confirmed

### ⏳ Phase 1.5: Deployment (Next Steps)

1. Package Lambda functions (create ZIP files)
2. Deploy Lambda to AWS
3. Configure Bedrock Agent action groups
4. Test via Bedrock Agent console
5. Switch to real PF360 APIs when available

### 📋 Phase 2: Backend & Frontend (Planned)

- ⏳ Backend API integration
- ⏳ Frontend application
- ⏳ SMS integration
- ⏳ Phone call integration

### 📋 Phase 3: Advanced Features (Planned)

- ⏳ Knowledge base integration
- ⏳ Advanced analytics
- ⏳ Multi-tenancy support

---

## 🚨 Troubleshooting

### Lambda Function Issues

#### Issue: Import Errors When Testing

**Symptoms:**
```
ModuleNotFoundError: No module named 'config'
```

**Solution:**
```bash
# Make sure you're in the right directory
cd lambda/scheduling-actions

# Ensure USE_MOCK_API is set
export USE_MOCK_API=true

# Run tests
python3 handler.py
```

#### Issue: Mock Data Not Loading

**Symptoms:**
```
KeyError: 'project_id' not found in mock data
```

**Solution:** Check that `mock_data.py` is in the same directory as `handler.py`

### Bedrock Agent Issues

#### Issue: 403 Access Denied on Agent Invocation

**Symptoms:**
```
accessDeniedException: Access denied when calling Bedrock
```

**Solution:**
1. Check [ENABLE_API_ACCESS.md](docs/ENABLE_API_ACCESS.md)
2. Or submit support ticket using [AWS_SUPPORT_TICKET.md](docs/AWS_SUPPORT_TICKET.md)

**Workaround:** Use Console testing (always works)

#### Issue: Agent Not Prepared

**Symptoms:**
```
ValidationException: Agent must be in PREPARED state
```

**Solution:**
```bash
python3 utils/prepare_all_agents.py
```

Wait 30-60 seconds, then retry.

#### Issue: Model Not Found

**Symptoms:**
```
ResourceNotFoundException: Model not found
```

**Solution:** Verify model ID in agent configuration:
```bash
aws bedrock-agent get-agent --agent-id 5VTIWONUMO --region us-east-1 \
  --query 'agent.foundationModel'
```

Should output: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`

---

## 🔒 AWS Resources

**Account:** 618048437522
**Region:** us-east-1

### Deployed Components

- ✅ 5 Bedrock Agents (supervisor + 4 collaborators)
- ✅ Claude Sonnet 4.5 model access
- ✅ IAM roles and policies
- ✅ OpenAPI schemas in S3
- ✅ Agent instructions configured
- ⏳ Lambda functions (ready to deploy)
- ⏳ Action group connections (ready to configure)

---

## 🔧 Requirements

### AWS Resources
- AWS Account with Bedrock access
- IAM permissions for Bedrock agents
- Model access to Claude Sonnet 4.5
- Lambda execution permissions

### Development Tools
```bash
# Python
python3 >= 3.8

# Python packages
pip install boto3 requests

# AWS CLI
brew install awscli  # macOS
pip install awscli   # Other

# Terraform
brew install terraform  # macOS
```

### AWS Credentials
```bash
aws configure
# Provide: Access Key, Secret Key, Region (us-east-1)
```

---

## 📦 Installation

### Clone Repository
```bash
git clone https://github.com/jjayarajdev/schedulingAgent.git
cd schedulingAgent-bb/bedrock
```

### Install Dependencies
```bash
pip install boto3 requests
```

### Configure AWS
```bash
aws configure
# Region: us-east-1
# Output format: json
```

### Test Lambda Functions
```bash
cd lambda
export USE_MOCK_API=true
python3 test_all_actions_v2.py
python3 test_complete_flows.py
```

### Deploy Infrastructure (if needed)
```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

### Prepare Agents
```bash
cd ../..
python3 utils/prepare_all_agents.py
```

### Verify Deployment
```bash
./scripts/verify_deployment.sh
```

---

## 🤝 Contributing

### Making Changes

1. Create feature branch
2. Make changes to Lambda or infrastructure
3. Test thoroughly:
   ```bash
   # Test Lambda
   cd lambda
   export USE_MOCK_API=true
   python3 test_all_actions_v2.py
   python3 test_complete_flows.py

   # Test agents
   cd ..
   ./scripts/verify_deployment.sh
   python3 tests/test_agents_interactive.py
   ```
4. Update documentation
5. Submit PR

### Documentation Updates

When you update Lambda or agents:
1. Update relevant docs in `docs/`
2. Update test scripts if needed
3. Update this README if structure changes

---

## 📞 Support

### Repository
**GitHub:** https://github.com/jjayarajdev/schedulingAgent

### AWS Support
- Use template: [AWS_SUPPORT_TICKET.md](docs/AWS_SUPPORT_TICKET.md)
- Gather diagnostics: `./scripts/gather_diagnostics.sh`

### Internal Support
- Check documentation in `docs/` directory
- Review test results for troubleshooting
- See `DEVELOPER_HANDOVER.md` for AWS access

---

## 📝 Technology Stack

- **AI/ML:** AWS Bedrock, Claude Sonnet 4.5
- **Compute:** AWS Lambda (Python 3.11)
- **API:** OpenAPI 3.0, REST
- **Infrastructure:** Terraform (IaC)
- **Testing:** Python unittest, custom test frameworks
- **Database:** DynamoDB (session storage, notes fallback)
- **Backend:** FastAPI (Phase 2)
- **Frontend:** React (Phase 2)

---

## 📜 License

© 2025 ProjectsForce. All rights reserved.

---

## 🏗️ Project Milestones

- **Phase 1.0**: ✅ Complete - Multi-agent infrastructure deployed
- **Phase 1.1**: ✅ Complete - Lambda functions implemented and tested
- **Phase 1.2**: ✅ Complete - Claude Sonnet 4.5 upgrade
- **Phase 1.5**: ⏳ In Progress - Lambda deployment to AWS
- **Phase 2.0**: 📋 Planned - Backend API and frontend
- **Phase 3.0**: 📋 Planned - Knowledge base and advanced features

---

**Last Updated**: October 13, 2025
**AWS Region**: us-east-1
**Model**: Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`)
**Status**: Phase 1.1 Complete - Ready for Lambda Deployment

---

**Generated with Claude Code**
https://claude.com/claude-code
