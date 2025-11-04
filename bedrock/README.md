# ProjectForce AI Scheduling Agent

**Version**: 3.1 (Phase 1 Complete, Phases 2-3 Ready)
**Status**: ✅ Core System Deployed - Lambda Integration Complete
**Framework**: AWS Bedrock Multi-Agent Architecture

---

## 🎯 Overview

Multi-channel AI scheduling system for ProjectForce using AWS Bedrock multi-agent architecture with supervisor pattern.

### Supported Channels
- ✅ **Web Chat** - React frontend with Flask backend
- ✅ **Voice/Phone** - AWS Connect + Lex V2 (Phase 3)
- 🔜 **SMS** - AWS End User Messaging (Phase 2, code complete)

### AI Architecture
- **Primary**: AWS Bedrock Agents with Supervisor pattern
- **Backup**: SuperAgent Framework (under evaluation)

---

## 🏗️ Architecture

### Multi-Agent System (AWS Bedrock)

```
Customer Input (Chat/Voice/SMS)
    ↓
Supervisor Agent (Orchestrator)
    ↓
├── SchedulingAgent → schedule_project, reschedule, cancel
├── pf-information → get_projects, get_weather
└── pf-chitchat → greetings, general conversation

    ↓
Lambda Action Functions
    ↓
ProjectForce Backend APIs (Real Integration)
```

**4 Agents Total:**
1. **Supervisor** - Routes requests, orchestrates multi-agent collaboration
2. **SchedulingAgent** - Appointments, bookings, availability
3. **pf-information** - Project data, customer information
4. **pf-chitchat** - Conversational interactions, greetings

### Voice Integration (Phase 3)

```
Customer Phone Call
    ↓
AWS Connect (Contact Center)
    ↓
Amazon Lex V2 (Speech-to-Text + Intent Recognition)
    ↓
Lambda: lex-fulfillment (simple) | voice-bedrock-bridge (complex)
    ↓
Bedrock Supervisor Agent
    ↓
Response (Text-to-Speech)
```

---

## 🚀 Quick Start

### Prerequisites
- AWS CLI configured
- Terraform 1.0+
- Python 3.11
- Node.js 18+ (for frontend)
- AWS Bedrock access (Claude 3.5 Sonnet v2)

### Option 1: Automated Deployment (Recommended)

```bash
cd bedrock/scripts
./DEPLOY.sh
```

This deploys:
- ✅ 4 Bedrock agents (Supervisor + 3 collaborators)
- ✅ 3 Lambda functions with real ProjectForce API integration
- ✅ DynamoDB session table
- ✅ IAM roles and policies
- ✅ Secrets Manager for API credentials

**Duration**: ~15-20 minutes

### Environment Variables

Before deployment, export your ProjectForce API credentials:

```bash
export PF_BEARER_TOKEN="your-bearer-token"
export PF_CLIENT_ID="09PF05VD"
export PF_USER_ID="1645869"
```

Or the script will use placeholder values (requires manual update later).

### Option 2: Manual Step-by-Step

See [`QUICK_START.md`](./QUICK_START.md) for detailed instructions.

---

## 📦 What's Deployed

### Phase 1: Core Multi-Agent System ✅
**Status**: Complete - Real API Integration Working

- 4 Bedrock agents (Supervisor + 3 collaborators)
  - Model: Claude 3.5 Sonnet V2 (us.anthropic.claude-3-5-sonnet-20241022-v2:0)
  - Multi-agent collaboration enabled on Supervisor
- 3 Lambda action functions with real ProjectForce API calls:
  - pf-scheduling-actions (schedule, reschedule, cancel)
  - pf-information-actions (projects, weather)
  - pf-chitchat-actions (conversation)
- DynamoDB for session management
- Secrets Manager for API credentials
- IAM roles with comprehensive Bedrock permissions

**Verified Working**: Lambda returns 25 real projects from ProjectForce API

### Phase 2: SMS Integration ✅
**Status**: Code complete, not deployed

- AWS End User Messaging SMS
- Two-way SMS conversations
- TCPA 2025 compliance
- Consent tracking

**Location**: `infrastructure/terraform/sms/`

### Phase 3: Voice Integration ✅
**Status**: Infrastructure code complete, ready to deploy

- AWS Connect instance (us-east-1 for USA customers)
- Amazon Lex V2 bot (5 intents)
- 2 Lambda functions (lex-fulfillment, voice-bedrock-bridge)
- Contact flow for call routing
- Call recordings to S3

**Location**: `infrastructure/terraform/voice/`

**Deployment**: `./scripts/deploy_voice_integration.sh`

---

## 📚 Documentation

### Getting Started
- **[Quick Start Guide](./QUICK_START.md)** - Fast deployment
- **[Architecture Overview](./ARCHITECTURE.md)** - System design
- **[Deployment Guide](./docs/NEW_ENVIRONMENT_DEPLOYMENT.md)** - Complete setup

### Phase-Specific Guides
- **[Phase 1: Core Agents](./docs/README.md)** - Bedrock agents setup
- **[Phase 2: SMS](./docs/archive/phase2/)** - SMS integration (not deployed)
- **[Phase 3: Voice](./docs/phase3/README.md)** - Voice integration guide

### Development
- **[API Documentation](./docs/api-calls.txt)** - Real backend API examples
- **[Testing Guide](./tests/README.md)** - How to test agents
- **[Complex Queries](./docs/COMPLEX_QUERY_SCENARIOS.md)** - Step Functions workflows

### Operations
- **[Monitoring Setup](./docs/MONITORING_SETUP_GUIDE.md)** - CloudWatch dashboards
- **[Terraform README](./infrastructure/terraform/README.md)** - Infrastructure details

---

## 🧪 Testing

### Test Web Chat Interface

```bash
cd testing/ui
./launch_test_ui.sh
```

Open browser: http://localhost:3000

Try queries:
- "Show me my projects"
- "Schedule my most urgent project"
- "What's the weather like?"

### Test Voice Integration

```bash
cd tests
python3 test_voice_integration.py
```

### Test Bedrock Agents Directly

```bash
cd infrastructure/terraform
python3 test_supervisor_routing.py
```

---

## 🔑 Key Features

### Intelligent Routing
- **Simple queries** → Direct Lambda calls (<3s)
- **Complex queries** → Step Functions workflows (<8s)
- **Conversational** → Bedrock Supervisor orchestration

### Multi-Turn Conversations
- Session management in DynamoDB
- Context maintained across turns
- Cross-channel continuity (chat → voice → SMS)

### Production Ready
- Error handling and retries
- Comprehensive logging
- Monitoring dashboards
- Call/chat recordings
- TCPA compliance for SMS

---

## 💰 Cost Estimate

**Monthly costs for 1,000 interactions across all channels:**

| Service | Cost |
|---------|------|
| Bedrock Agents (5 agents) | $50 |
| Lambda Functions | $5 |
| DynamoDB | $5 |
| Step Functions | $2 |
| AWS Connect (1,000 calls, 5min avg) | $90 |
| Phone Number (toll-free) | $3 |
| Lex V2 | $2 |
| S3 Storage | $10 |
| CloudWatch Logs | $5 |
| **Total** | **~$172/month** |

**Per-interaction cost**: ~$0.17

---

## 🔄 Current Status

### Completed ✅
- [x] Phase 1: Core Bedrock agents deployed and working
- [x] Real ProjectForce API integration (25 projects returned)
- [x] Multi-agent collaboration with Supervisor pattern
- [x] Lambda functions with Bearer token authentication
- [x] DynamoDB session management
- [x] Deployment automation (DEPLOY.sh, CLEANUP.sh)
- [x] Validation and testing scripts (VALIDATE.sh, TEST_AGENTS.sh)
- [x] Phase 3: Voice infrastructure code ready
- [x] Phase 2: SMS code complete
- [x] Project organization and documentation

### Known Issues 🐛
- [ ] Agent invocation via bedrock-agent-runtime (accessDeniedException)
  - Direct model invocation: ✅ Works
  - Lambda functions: ✅ Works (returns real data)
  - Agent invocation: ❌ Blocked (likely account-level service enablement)
  - **Workaround**: Use Lambda functions directly

### Planned 📋
- [ ] Resolve agent invocation permissions (AWS Support or console enablement)
- [ ] Deploy Phase 3 (Voice integration)
- [ ] Deploy Phase 2 (SMS integration)
- [ ] Web chat UI integration with agents
- [ ] Multi-client (B2B) support
- [ ] Advanced analytics dashboard

---

## 🛠️ Technology Stack

**AI/ML:**
- AWS Bedrock (Claude 3.5 Sonnet v2)
- Amazon Lex V2 (Speech-to-Text)
- Amazon Polly (Text-to-Speech)

**Infrastructure:**
- AWS Lambda (Python 3.11)
- AWS Step Functions
- DynamoDB
- S3
- AWS Connect
- Terraform (IaC)

**Frontend:**
- React 18
- Flask (Python)
- WebSocket for real-time chat

**Monitoring:**
- CloudWatch Logs
- CloudWatch Metrics
- X-Ray tracing

---

## 📁 Project Structure

```
bedrock/
├── scripts/                    # Main deployment & testing
│   ├── DEPLOY.sh              # Main deployment script
│   ├── CLEANUP.sh             # Cleanup/deletion script
│   ├── VALIDATE.sh            # Validation script
│   ├── TEST_AGENTS.sh         # Agent testing script
│   ├── deployment/            # Additional deployment utilities
│   ├── testing/               # Test scripts
│   └── token-management/      # Token fetch/update scripts
├── lambda/                    # Lambda function code
│   ├── scheduling-actions/    # Scheduling operations
│   ├── information-actions/   # Project/customer info
│   └── chitchat-actions/      # Conversational responses
├── agent-instructions/        # Agent prompt instructions
│   ├── supervisor.txt
│   ├── scheduling.txt
│   ├── information.txt
│   └── chitchat.txt
├── docs/                      # Comprehensive documentation
│   ├── archive/               # Historical docs
│   └── *.md                   # All project documentation
├── logs/                      # Deployment and test logs
├── infrastructure/            # Terraform (future phases)
│   ├── terraform/
│   │   └── voice/            # Phase 3 voice infrastructure
│   └── voice/
│       └── contact-flows/    # AWS Connect flows
├── frontend/                  # Web chat UI (future)
│   ├── backend/              # Flask API
│   └── src/                  # React app
├── testing/ui/               # Test UI
└── tests/                    # Test suites
```

---

## 🆘 Support

### Troubleshooting
- **Agents not responding**: Check CloudWatch logs `/aws/lambda/pf-*`
- **Voice calls fail**: Verify phone number associated with contact flow
- **API errors**: Check `docs/api-calls.txt` for correct format

### Getting Help
1. Check relevant Phase documentation
2. Review CloudWatch Logs
3. Test components individually
4. Consult Terraform plan output

---

## 🗺️ Roadmap

### Phase 1.1: Agent Testing & Troubleshooting (Current)
- ✅ Real ProjectForce API integration complete
- ✅ Lambda functions returning live data (25 projects)
- 🐛 Resolve agent invocation permissions
- Test end-to-end agent workflows
- Web chat UI integration

### Phase 3.1: Voice Production (Next)
- Deploy voice infrastructure (Terraform ready)
- AWS Connect instance setup
- Lex V2 bot integration
- Test phone call workflows
- Call analytics dashboard

### Phase 2.1: SMS Production
- Deploy SMS infrastructure (code ready)
- Customer opt-in flow
- Two-way SMS conversations
- SMS analytics

### Phase 4: Advanced Features
- Outbound calling & notifications
- Multi-client (B2B) support
- Multi-language support
- Advanced analytics dashboard

---

## 📄 License

Internal project for ProjectForce

---

## 🤝 Contributors

- ProjectForce Team
- AWS Bedrock Agents
- Claude Code Assistant

---

**Last Updated**: 2025-11-04
**Current Phase**: 1.1 (Agent Testing & Troubleshooting)
**Next Milestone**: Resolve agent invocation, then Voice integration (Phase 3)
