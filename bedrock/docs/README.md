# AWS Bedrock Multi-Agent Scheduling System

**Status**: ✅ Phase 1 Complete - Agents Deployed
**Model**: Claude Sonnet 4.5 (us.anthropic.claude-sonnet-4-5-20250929-v1:0)
**Region**: us-east-1
**Deployment Date**: October 12, 2025

---

## 🚀 **NEW DEVELOPER? START HERE**

**→ Read [DEVELOPER_HANDOVER.md](./DEVELOPER_HANDOVER.md) first!**

This comprehensive handover document contains:
- ✅ Complete AWS account information & credentials
- ✅ All deployed resources with IDs and ARNs
- ✅ Phase status (Phase 1 complete, Phases 2-3 research done)
- ✅ Quick start guide & testing procedures
- ✅ Known issues & manual configuration steps
- ✅ Cost information & documentation index

**It's your single source of truth for taking over this project.**

---

## 🎯 Overview

This project implements an **AI-powered scheduling agent system** using **AWS Bedrock's Multi-Agent Collaboration** capability with a supervisor-collaborator architecture. The system uses 5 specialized agents powered by Claude Sonnet 4.5 to handle customer scheduling requests.

### Architecture Decision

After comprehensive research comparing AWS Bedrock Agents vs LangGraph ([see ARCHITECTURE_RESEARCH.md](./ARCHITECTURE_RESEARCH.md)), we chose **AWS Bedrock Agents native multi-agent collaboration** for:

- **65-72% cost savings** vs self-managed LangGraph
- **2 days vs 2 weeks** development time
- **55% less code** to maintain (1,350 lines vs 3,000+)
- **Built-in** session management, memory, and observability
- **FREE** AgentCore until September 16, 2025

---

## 🏗️ Architecture

```
                    ┌─────────────────────────────────┐
                    │   Customer Request              │
                    └──────────────┬──────────────────┘
                                   │
                                   ↓
                    ┌─────────────────────────────────┐
                    │   Supervisor Agent              │
                    │   (Routes to specialists)       │
                    └──────────────┬──────────────────┘
                                   │
                ┌──────────────────┼──────────────────┬─────────────┐
                │                  │                  │             │
                ↓                  ↓                  ↓             ↓
    ┌───────────────────┐ ┌───────────────┐ ┌──────────────┐ ┌──────────┐
    │ Scheduling Agent  │ │ Information   │ │ Notes Agent  │ │ Chitchat │
    │ (6 actions)       │ │ Agent         │ │ (2 actions)  │ │ Agent    │
    │                   │ │ (4 actions)   │ │              │ │          │
    └─────────┬─────────┘ └───────┬───────┘ └──────┬───────┘ └────┬─────┘
              │                   │                 │               │
              └───────────────────┴─────────────────┴───────────────┘
                                   │
                                   ↓
                        ┌────────────────────┐
                        │ Lambda Functions   │
                        │ (Phase 2 - TBD)    │
                        └──────────┬─────────┘
                                   │
                                   ↓
                        ┌────────────────────┐
                        │  PF360 API         │
                        └────────────────────┘
```

### Agent Responsibilities

| Agent | ID | Role | Actions |
|-------|-----|------|---------|
| **Supervisor** | `5VTIWONUMO` | Routes requests to appropriate specialist | None (routing only) |
| **Scheduling** | `IX24FSMTQH` | Manages appointments, availability, bookings | 6 scheduling actions |
| **Information** | `C9ANXRIO8Y` | Provides project details, status, hours, weather | 4 information actions |
| **Notes** | `G5BVBYEPUM` | Manages appointment notes and documentation | 2 note actions |
| **Chitchat** | `BIUW1ARHGL` | Handles greetings, thanks, general conversation | None (conversational) |

---

## 📁 Project Structure

```
bedrock/
├── README.md                                # Main project guide
├── QUICK_REFERENCE.md                       # Command cheat sheet
│
├── docs/                                    # Documentation
│   ├── README.md                            # This file
│   ├── TESTING_GUIDE.md                     # Testing documentation
│   ├── DEPLOYMENT_GUIDE.md                  # Deployment instructions
│   ├── ENABLE_API_ACCESS.md                 # API access troubleshooting
│   ├── AWS_SUPPORT_TICKET.md                # Support ticket template
│   ├── ARCHITECTURE_RESEARCH.md             # Research & decision rationale
│   ├── DOCUMENTATION_INDEX.md               # All docs index
│   └── DEPLOYMENT_STATUS.md                 # Current deployment status
│
├── tests/                                   # Test scripts
│   ├── README.md                            # Testing documentation
│   ├── test_api_access.py                   # API access validation
│   ├── test_agents_interactive.py           # Interactive testing
│   └── test_agent.py                        # Basic test (legacy)
│
├── utils/                                   # Utility scripts
│   ├── README.md                            # Utilities documentation
│   └── prepare_all_agents.py                # Agent preparation
│
├── scripts/                                 # Shell scripts
│   ├── README.md                            # Scripts documentation
│   ├── gather_diagnostics.sh                # Diagnostic collection
│   └── verify_deployment.sh                 # Deployment verification
│
├── infrastructure/                          # Terraform IaC
│   ├── terraform/
│   │   ├── bedrock_agents.tf               # Main agent configuration
│   │   ├── provider.tf                     # AWS provider setup
│   │   ├── terraform.tfvars                # Variable values
│   │   └── variables.tf                    # Variable definitions
│   │
│   ├── agent_instructions/                  # Agent prompt instructions
│   │   ├── supervisor.txt                  # Supervisor routing logic
│   │   ├── scheduling_collaborator.txt     # Scheduling workflows
│   │   ├── information_collaborator.txt    # Information retrieval
│   │   ├── notes_collaborator.txt          # Note management
│   │   └── chitchat_collaborator.txt       # Conversational handling
│   │
│   └── openapi_schemas/                     # Action group definitions
│       ├── scheduling_actions.json         # 6 scheduling actions
│       ├── information_actions.json        # 4 information actions
│       └── notes_actions.json              # 2 note actions
│
├── backend/                                 # Backend services (Phase 2)
├── frontend/                                # Frontend app (Phase 2)
├── lambda/                                  # Lambda functions
└── knowledge-base/                          # Knowledge base content
```

---

## ✅ Current Status

### Phase 1: Complete ✅

**Deployed Infrastructure:**
- ✅ 5 Bedrock Agents created and configured
- ✅ Multi-agent collaboration enabled
- ✅ All 4 collaborators associated with supervisor
- ✅ Claude Sonnet 4.5 inference profile configured
- ✅ IAM roles and policies set up
- ✅ S3 bucket with 3 OpenAPI schemas
- ✅ All agents in PREPARED status

**Agent IDs:**
- **Supervisor**: `5VTIWONUMO`
  - Latest Alias: `HH2U7EZXMW` (version 6 with v4 collaborators)
  - Test Alias: `TSTALIASID` (points to DRAFT)
  - v1 Alias: `PEXPJRXIML` (deprecated - uses old model)

- **Collaborator Agents** (all use Claude Sonnet 4.5):

| Agent | ID | v4 Alias | Version |
|-------|-----|----------|---------|
| Scheduling | `IX24FSMTQH` | `TYJRF3CJ7F` | 4 |
| Information | `C9ANXRIO8Y` | `YVNFXEKPWO` | 4 |
| Notes | `G5BVBYEPUM` | `F9QQNLZUW8` | 4 |
| Chitchat | `BIUW1ARHGL` | `THIPMPJCPI` | 5 |

**Cost:** FREE until September 16, 2025 (AgentCore preview pricing)

### Phase 2: Next Steps 🚧

**Lambda Function Implementation** (12 actions total):
1. **Scheduling Lambda** - 6 actions:
   - `list_projects` - Show available projects
   - `get_available_dates` - Get available dates for a project
   - `get_time_slots` - Get available time slots for a date
   - `confirm_appointment` - Confirm a new appointment
   - `reschedule_appointment` - Reschedule existing appointment
   - `cancel_appointment` - Cancel an appointment

2. **Information Lambda** - 4 actions:
   - `get_project_details` - Get project information
   - `get_appointment_status` - Check appointment status
   - `get_working_hours` - Get business hours
   - `get_weather` - Get weather forecast

3. **Notes Lambda** - 2 actions:
   - `add_note` - Add note to appointment
   - `list_notes` - List appointment notes

---

## 🚀 Testing Your Agents

### Option 1: AWS Console (Recommended - Always Works)

1. Open the [Bedrock Agents Console](https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents)
2. Click on **scheduling-agent-supervisor**
3. Click the **"Test"** button (top right)
4. Try these test scenarios:

| Test | Input | Expected Routing |
|------|-------|------------------|
| Chitchat | `Hello! How are you?` | → chitchat_collaborator |
| Scheduling | `I want to schedule an appointment` | → scheduling_collaborator |
| Information | `What are your working hours?` | → information_collaborator |
| Notes | `Add a note that I prefer mornings` | → notes_collaborator |

### Option 2: Interactive Testing (Most Features)

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
python3 tests/test_agents_interactive.py
```

**Features:**
- Pre-flight checks (credentials, agent status, collaborators)
- 4 predefined test scenarios
- Interactive chat mode
- Console testing instructions

**See:** [tests/README.md](../tests/README.md) for detailed testing documentation

### Option 3: API Access Validation

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
python3 tests/test_api_access.py
```

Tests three scenarios:
- ✅ Direct model invocation (works)
- ⚠️ Agent invocation (currently fails with 403 - pending AWS to enable on-demand API access)
- ⚠️ Supervisor invocation (currently fails with 403)

**Note:** API invocation currently fails due to missing on-demand access. See [ENABLE_API_ACCESS.md](./ENABLE_API_ACCESS.md) for solution.

### Option 4: Deployment Verification

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
./scripts/verify_deployment.sh
```

This script checks:
- ✅ All agent statuses
- ✅ Collaborator associations
- ✅ S3 bucket contents
- ✅ Model access

### Option 5: Gather Diagnostics

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
./scripts/gather_diagnostics.sh
```

Collects diagnostic information for troubleshooting or AWS Support tickets.
See [AWS_SUPPORT_TICKET.md](./AWS_SUPPORT_TICKET.md) for support ticket template.

---

## 🛠️ Technology Stack

### Infrastructure
- **IaC**: Terraform
- **Region**: us-east-1
- **Provider**: AWS (hashicorp/aws ~> 6.0)

### AWS Services
- **AI**: AWS Bedrock Agents with Multi-Agent Collaboration
- **Model**: Claude Sonnet 4.5 (inference profile)
- **Storage**: S3 (for OpenAPI schemas)
- **Permissions**: IAM roles and policies
- **Compute**: Lambda Functions (Phase 2)

### Languages
- **Infrastructure**: HCL (Terraform)
- **Testing**: Python 3.11+
- **Lambda Functions**: Python 3.11+ (Phase 2)

---

## 📖 Documentation

### Main Documentation
- **[DEPLOYMENT_STATUS.md](../DEPLOYMENT_STATUS.md)** - Current deployment status and testing guide
- **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)** - Step-by-step deployment instructions
- **[ARCHITECTURE_RESEARCH.md](./ARCHITECTURE_RESEARCH.md)** - Research comparing Bedrock vs LangGraph (60+ pages)
- **[CREATED_FILES.md](./CREATED_FILES.md)** - Complete list of files created

### Additional Documentation
- **[AWS_SETUP_GUIDE.md](./AWS_SETUP_GUIDE.md)** - AWS account setup
- **[TERRAFORM_COMPLETE.md](./TERRAFORM_COMPLETE.md)** - Terraform configuration details
- **tfplan.txt** - Terraform plan output

---

## 🔧 Development Setup

### Prerequisites
- AWS CLI configured with credentials
- Terraform 1.5+
- Python 3.11+
- Access to AWS Bedrock in us-east-1
- Claude Sonnet 4.5 model access enabled

### Quick Start

1. **Clone and navigate**:
   ```bash
   cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
   ```

2. **Review configuration**:
   ```bash
   cat infrastructure/terraform/terraform.tfvars
   ```

3. **Verify deployment**:
   ```bash
   ./verify_deployment.sh
   ```

4. **Test agents**:
   - Use AWS Console: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents
   - Select `scheduling-agent-supervisor`
   - Click "Test" button

---

## 📊 Key Metrics & Costs

### Performance Targets
- Intent accuracy: >95%
- Response latency: <2s (p95)
- Multi-agent routing: <500ms
- Session completion rate: >70%

### Cost Analysis

**Current (Phase 1):**
- AgentCore: **FREE** until Sept 16, 2025
- S3 Storage: ~$0.01/month
- **Total: $0.01/month**

**Estimated (Phase 2 with Lambda):**
- Model invocations: $204/month (estimated at 10,000 requests)
- Lambda: $5-10/month
- **Total: ~$215/month**

**vs LangGraph Alternative:**
- Self-hosted: $256-340/month
- **Savings: 65-72%**

---

## 🎯 Success Criteria

### Phase 1 (Complete ✅)
- ✅ 5 agents deployed with multi-agent collaboration
- ✅ Claude Sonnet 4.5 integration working
- ✅ Routing logic configured
- ✅ All agents prepared and tested
- ✅ Infrastructure as code (Terraform)
- ✅ Documentation complete

### Phase 2 (Next)
- ⏳ 12 Lambda functions implemented
- ⏳ PF360 API integration complete
- ⏳ End-to-end testing passed
- ⏳ Error handling and retry logic
- ⏳ Monitoring and logging set up

---

## 🚨 Troubleshooting

### Common Issues

**1. Access Denied Errors**
```bash
# Check model access
aws bedrock get-inference-profile \
  --inference-profile-identifier us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --region us-east-1
```
Solution: Verify Claude Sonnet 4.5 model access in AWS Console → Bedrock → Model access

**2. Agent Not Responding**
```bash
# Check agent status
aws bedrock-agent get-agent --agent-id 5VTIWONUMO --region us-east-1
```
Solution: Verify agent status is "PREPARED". If not, run `prepare-agent`.

**3. Terraform State Issues**
```bash
# List resources
cd infrastructure/terraform
terraform state list
```
Solution: See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for state management.

---

## 📞 Support

For questions or issues:
- **Agent IDs**: See "Current Status" section above
- **AWS Console**: [Bedrock Agents](https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents)
- **Verification**: Run `./verify_deployment.sh`
- **Documentation**: Check `docs/` folder

---

## 🔄 Development Workflow

### Making Changes to Agents

1. **Update configuration**:
   ```bash
   cd infrastructure/terraform
   # Edit bedrock_agents.tf or terraform.tfvars
   ```

2. **Plan changes**:
   ```bash
   terraform plan
   ```

3. **Apply changes**:
   ```bash
   terraform apply
   ```

4. **Prepare agents**:
   ```bash
   aws bedrock-agent prepare-agent --agent-id 5VTIWONUMO --region us-east-1
   ```

5. **Test**:
   - Use AWS Console test feature
   - Or run `./verify_deployment.sh`

---

## 📝 License

Internal use only - ProjectsForce 360

---

## 🏆 Acknowledgments

- Architecture decision based on comprehensive research (see ARCHITECTURE_RESEARCH.md)
- AWS Bedrock Multi-Agent Collaboration (GA: March 10, 2025)
- Claude Sonnet 4.5 by Anthropic
- Terraform AWS Provider 6.x
