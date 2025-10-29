# ProjectForce AI Scheduling Agent

**Version**: 3.0 (Phase 1-3 Complete)
**Status**: 🚧 Phase 1 API Integration In Progress
**Framework**: AWS Bedrock Agents (Primary) + SuperAgent (Backup Option)

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
├── Information Agent → get_projects, get_weather
├── Scheduling Agent → schedule_project, reschedule, cancel
├── Notification Agent → send_sms, send_email
└── Escalation Agent → create_ticket, escalate

    ↓
Lambda Action Functions
    ↓
ProjectForce Backend APIs
```

**5 Agents Total:**
1. **Supervisor Agent** - Routes requests, orchestrates collaborators
2. **Information Agent** - Project data, weather, general info
3. **Scheduling Agent** - Appointments, bookings, availability
4. **Notification Agent** - SMS, email, alerts
5. **Escalation Agent** - Support tickets, escalations

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
cd bedrock
./DEPLOY.sh
```

This deploys:
- ✅ 5 Bedrock agents
- ✅ 5+ Lambda functions
- ✅ DynamoDB session table
- ✅ Step Functions (3 state machines)
- ✅ S3 buckets for storage

**Duration**: ~30-45 minutes

### Option 2: Manual Step-by-Step

See [`QUICK_START.md`](./QUICK_START.md) for detailed instructions.

---

## 📦 What's Deployed

### Phase 1: Core Multi-Agent System ✅
**Status**: Deployed, API integration in progress

- 5 Bedrock agents (Supervisor + 4 collaborators)
- Lambda action functions (information, scheduling, notification, escalation)
- DynamoDB for session management
- Web chat interface (React + Flask)
- Testing UI for agent testing

**Current Work**: Updating Lambda functions to call real ProjectForce APIs

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
- [x] Phase 1: Bedrock agents deployed
- [x] Web chat interface working
- [x] Step Functions for complex queries
- [x] Testing UI deployed
- [x] Phase 3: Voice infrastructure code ready
- [x] Phase 2: SMS code complete

### In Progress 🚧
- [ ] Phase 1: Integrate real ProjectForce APIs
  - Update Lambda functions
  - Add authentication (Bearer token)
  - Update data models
  - Add missing actions (reschedule-slots, cancel-reschedule)

### Planned 📋
- [ ] Deploy Phase 3 (Voice) after Phase 1 API integration
- [ ] Deploy Phase 2 (SMS) after Phase 1 API integration
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
├── infrastructure/
│   ├── terraform/          # Main infrastructure
│   │   ├── bedrock_agents.tf
│   │   ├── dynamodb.tf
│   │   └── voice/          # Phase 3 voice infrastructure
│   └── voice/
│       └── contact-flows/  # AWS Connect flows
├── lambda/
│   ├── information-actions/
│   ├── scheduling-actions/
│   ├── lex-fulfillment/    # Phase 3
│   └── voice-bedrock-bridge/ # Phase 3
├── frontend/
│   ├── backend/            # Flask API
│   └── src/                # React app
├── testing/ui/             # Test UI
├── tests/                  # Test suites
├── scripts/                # Deployment scripts
└── docs/                   # Documentation
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

### Phase 1.1: API Integration (Current)
- Real ProjectForce API calls
- Authentication setup
- Customer lookup by phone
- Additional actions (slots, cancel)

### Phase 3.1: Voice Production
- Deploy to production
- Optimize Lex intents
- Add DTMF fallback
- Call analytics dashboard

### Phase 2.1: SMS Production
- Deploy SMS infrastructure
- Customer opt-in flow
- SMS analytics

### Phase 4: Advanced Features
- Outbound calling
- Proactive notifications
- Multi-language support
- Advanced analytics

---

## 📄 License

Internal project for ProjectForce

---

## 🤝 Contributors

- ProjectForce Team
- AWS Bedrock Agents
- Claude Code Assistant

---

**Last Updated**: 2025-10-28
**Current Phase**: 1.1 (API Integration)
**Next Milestone**: Real API integration complete
