# ProjectForce AI Scheduling Agent

**Version**: 4.0 (Production Ready)
**Status**: ✅ Production Deployment - Serverless Architecture Complete
**Framework**: AWS Bedrock Multi-Agent with Hybrid Routing
**Last Updated**: 2025-11-15

---

## 🎯 Overview

Production-ready multi-channel AI scheduling system for ProjectForce using AWS Bedrock multi-agent architecture with **hybrid routing** for optimal performance.

### Supported Channels
- ✅ **Web Chat** - Interactive test UI (localhost:8000)
- ✅ **API Gateway** - REST API for web/mobile integration
- 🔜 **Voice/Phone** - AWS Connect + Lex V2 (Phase 3, code ready)
- 🔜 **SMS** - AWS End User Messaging (Phase 2, code ready)

### AI Architecture
- **Hybrid Routing**: Direct Lambda (~2s) + Bedrock Agents (~5-25s)
- **Session Management**: DynamoDB (fully serverless, no VPC)
- **Multi-turn Conversations**: Context-aware via conversation history
- **Configuration**: USE_SUPERVISOR=false (direct agent routing)

---

## 🏗️ Architecture

### Hybrid Routing System (Production)

```
Customer Input → API Gateway → Orchestrator Lambda
                                      ↓
                         ┌────── Classifier (Claude) ──────┐
                         ↓                                  ↓
              Direct Lambda (~2s)              Bedrock Agents (~5-25s)
              ├─ list_projects                 ├─ Supervisor (GEMYQNPYB4)
              ├─ filter_projects               ├─ Scheduling (LMJI2V9E8Y)
              ├─ get_project_details           ├─ Information (VDWEVR6DJD)
              └─ get_available_dates           └─ Chitchat (DIT6BVFDYW)
                         ↓                                  ↓
              Lambda Action Functions ←────────┘
              ├─ pf-scheduling-actions
              └─ pf-information-actions
                         ↓
              ProjectForce Backend APIs
                         ↓
              DynamoDB (Session Storage)
```

**4 Bedrock Agents:**
1. **Supervisor (GEMYQNPYB4)** - Multi-agent orchestration (when USE_SUPERVISOR=true)
2. **Scheduling Agent (LMJI2V9E8Y)** - Appointments, bookings, rescheduling
3. **Information Agent (VDWEVR6DJD)** - Project queries, weather data
4. **Chitchat Agent (DIT6BVFDYW)** - Greetings, casual conversation

**Key Components:**
- **Orchestrator Lambda** - Request routing, session management, conversation context
- **3 Lambda Action Functions** - Business logic execution
- **DynamoDB Table** - Session history (pf-sessions-dev)
- **Secrets Manager** - API credentials (pf-api-credentials)

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

### Production System ✅
**Status**: Production Ready - All Components Operational

#### Bedrock Agents (4 Total)
- **Supervisor Agent** (GEMYQNPYB4) - Multi-agent orchestration
- **Scheduling Agent** (LMJI2V9E8Y) - Appointment management
- **Information Agent** (VDWEVR6DJD) - Information queries
- **Chitchat Agent** (DIT6BVFDYW) - Conversational interactions
- **Model**: Claude 3.5 Sonnet V2 (us.anthropic.claude-3-5-sonnet-20241022-v2:0)
- **Alias**: TSTALIASID (standardized across all agents)

#### Lambda Functions (3 Total)
- **pf-orchestrator** - Request routing, session management, classifier
- **pf-scheduling-actions** - Schedule, reschedule, cancel operations
- **pf-information-actions** - Project queries, weather data
- **Note**: No chitchat Lambda (handled by Chitchat Agent directly)

#### Infrastructure
- **DynamoDB Table**: pf-sessions-dev (session storage, 1-hour TTL)
- **API Gateway**: REST API endpoint for web/mobile
- **Secrets Manager**: pf-api-credentials (ProjectForce API tokens)
- **IAM Roles**: Full Bedrock + DynamoDB permissions
- **No VPC**: Serverless architecture, no ElastiCache/Redis

**Verified Working**: Real ProjectForce API integration, multi-turn conversations, context tracking

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
- **[Architecture Overview](./docs/ARCHITECTURE.md)** - System design
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

### Interactive Test UI (Recommended)

```bash
cd testing/ui
python3 -m http.server 8000
# Open browser: http://localhost:8000
```

Try queries:
- "Show me my projects"
- "Show me scheduled projects"
- "Tell me about the 3rd project"
- "Hello" (chitchat)
- "What's the weather in Tampa?"

### Formatted Test Suites

Run comprehensive test suites with clean, color-coded output:

```bash
cd testing

# Quick sanity check
./run_test_formatted.sh run_quick_tests.sh

# Full test suites
./run_test_formatted.sh test_suite_1_basic_workflow.sh
./run_test_formatted.sh test_suite_2_context_resolution.sh
./run_test_formatted.sh test_suite_3_filtering.sh
./run_test_formatted.sh test_suite_4_chitchat_mixed.sh
./run_test_formatted.sh test_suite_5_scheduling.sh
```

**Documentation**: See `testing/FORMATTED_TESTING.md` for detailed testing guide

### Validate Deployment

```bash
cd scripts
./VALIDATE.sh
```

Checks all deployed components and configurations.

---

## 🔑 Key Features

### Intelligent Hybrid Routing
- **Simple queries** → Direct Lambda calls (~2s) - list, filter, details
- **Complex queries** → Bedrock Agents (~5-25s) - scheduling, conversational
- **Classification** → Claude-based intent detection
- **Conversation Context** → build_conversation_context() tracks 4 most recent messages
- **Configuration** → USE_SUPERVISOR=false for direct agent routing

### Multi-Turn Conversations
- **Session Storage**: DynamoDB (pf-sessions-dev)
- **TTL**: 1 hour automatic cleanup
- **Context Tracking**: Maintains conversation history across turns
- **Reference Resolution**: "the 3rd project", "that one", "schedule it"
- **Location Inference**: Weather queries use project address context

### Production Ready
- **Serverless**: No VPC, fully serverless architecture
- **Performance**: Direct Lambda ~2s, Agents ~5-25s
- **Error Handling**: Comprehensive error catching and retries
- **Logging**: Structured JSON logging to CloudWatch
- **Monitoring**: CloudWatch metrics and dashboards
- **Security**: IAM roles, Secrets Manager integration
- **Cost**: ~$5/mo (DynamoDB) vs ~$64/mo (Redis + NAT)

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

## 🔄 Current Status (As of 2025-11-15)

### Completed ✅
- [x] **Production System**: All components deployed and operational
- [x] **4 Bedrock Agents**: Supervisor, Scheduling, Information, Chitchat
- [x] **3 Lambda Functions**: Orchestrator, Scheduling Actions, Information Actions
- [x] **Hybrid Routing**: Direct Lambda (~2s) + Bedrock Agents (~5-25s)
- [x] **DynamoDB Migration**: Serverless session management (no VPC/Redis)
- [x] **Conversation Context**: Multi-turn conversations with reference resolution
- [x] **Real API Integration**: ProjectForce backend integration working
- [x] **Testing Infrastructure**: 5 test suites with formatted output
- [x] **Test UI**: Interactive testing interface (localhost:8000)
- [x] **Deployment Automation**: DEPLOY.sh, CLEANUP.sh, VALIDATE.sh
- [x] **IAM Permissions**: Full Bedrock + DynamoDB access resolved
- [x] **Standardized Configuration**: TSTALIASID across all agents
- [x] **Documentation**: Comprehensive guides and references

### System Configuration
- **USE_SUPERVISOR**: false (direct agent routing)
- **ALLOW_DIRECT_LAMBDA**: true (hybrid routing enabled)
- **Session Storage**: DynamoDB (pf-sessions-dev)
- **No VPC**: Fully serverless architecture
- **Performance**: 2s (direct) / 5-25s (agents)

### Planned 📋
- [ ] Deploy Phase 3 (Voice integration - code ready)
- [ ] Deploy Phase 2 (SMS integration - code ready)
- [ ] Enhanced web chat UI for production
- [ ] Multi-client (B2B) support
- [ ] Advanced analytics dashboard
- [ ] Outbound notifications

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

### ✅ Phase 1: Production Core (COMPLETE)
- ✅ 4 Bedrock agents deployed with real API integration
- ✅ Hybrid routing with Direct Lambda + Agents
- ✅ DynamoDB session management (serverless)
- ✅ Multi-turn conversation context
- ✅ 5 comprehensive test suites
- ✅ Interactive test UI
- ✅ Complete deployment automation

### 📋 Phase 2: SMS Integration (Code Ready)
- Deploy AWS End User Messaging infrastructure
- Customer opt-in flow and TCPA compliance
- Two-way SMS conversations
- SMS analytics and monitoring

### 📋 Phase 3: Voice Integration (Code Ready)
- Deploy AWS Connect instance (Terraform ready)
- Lex V2 bot integration
- Voice contact flows
- Call recordings and analytics

### 📋 Phase 4: Advanced Features
- Enhanced web chat UI for production
- Outbound notifications (SMS/voice/email)
- Multi-client (B2B) support
- Multi-language support
- Advanced analytics dashboard
- Predictive scheduling

---

## 📄 License

Internal project for ProjectForce

---

## 🤝 Contributors

- ProjectForce Development Team
- AWS Bedrock Multi-Agent Architecture

---

**Last Updated**: 2025-11-15
**Current Phase**: Production Ready (Phase 1 Complete)
**Next Milestone**: Phase 2 (SMS) or Phase 3 (Voice) deployment
**System Status**: ✅ All components operational and production-ready
