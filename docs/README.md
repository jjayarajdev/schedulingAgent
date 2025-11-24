# Bedrock Multi-Agent System - Documentation

**Last Updated:** 2025-11-15
**Version:** 4.0
**Status:** Production Ready - Serverless Architecture
**Performance:** Direct Lambda ~2s, Agents ~5-25s

---

## 📖 Documentation Structure

This folder contains all current and active documentation for the AWS Bedrock Multi-Agent Scheduling System.

### Key System Characteristics (Nov 2025)
- ✅ **Serverless**: DynamoDB sessions (no VPC/Redis)
- ✅ **Hybrid Routing**: Direct Lambda + Bedrock Agents
- ✅ **Direct Agent Routing**: USE_SUPERVISOR=false
- ✅ **Multi-turn Conversations**: Context-aware via conversation history
- ✅ **Production Ready**: All components deployed and tested

Historical and archived documents are in the `archive/` folder.

---

## 🚀 Quick Start

### New to the Project? Start Here:

**1. [`../README.md`](../README.md)** ⭐⭐⭐
   - **BEST STARTING POINT** - Project overview
   - Current architecture and system status
   - Quick deployment guide
   - Testing instructions
   - **START HERE for overall understanding**

**2. [`../scripts/README.md`](../scripts/README.md)** 🚀
   - Deployment workflows (DEPLOY.sh, CLEANUP.sh, VALIDATE.sh)
   - Script descriptions and usage
   - Step-by-step deployment guide
   - **READ THIS for deployment**

**3. [`../testing/README.md`](../testing/README.md)** 🧪
   - Interactive test UI (localhost:8000)
   - 5 comprehensive test suites
   - Formatted test results
   - Troubleshooting guide
   - **READ THIS for testing**

**4. [`../testing/FORMATTED_TESTING.md`](../testing/FORMATTED_TESTING.md)** 📊
   - Formatted test output guide
   - Color-coded results
   - Performance metrics
   - Test suite descriptions
   - **READ THIS for test automation**

**5. [`DYNAMODB_MIGRATION.md`](./DYNAMODB_MIGRATION.md)** 🔄 **IMPORTANT**
   - Redis to DynamoDB migration details
   - Performance improvements (TIMEOUT → ~2s)
   - Cost savings (~92% reduction)
   - Architecture comparison
   - **READ THIS to understand serverless migration**

**6. [`../lambda/orchestrator/README.md`](../lambda/orchestrator/README.md)** 🔧
   - Orchestrator Lambda details
   - Hybrid routing logic
   - Environment variables
   - API contract
   - **READ THIS for orchestrator understanding**

---

## 📚 Core Documentation (Current)

### v2.0 Routing & Improvements (NEW)

| Document | Purpose | Status |
|----------|---------|--------|
| **[ROUTING_COMPARISON.md](./ROUTING_COMPARISON.md)** | Supervisor vs Frontend routing analysis | ✅ v2.0 |
| **[IMPROVEMENTS_V2.md](./IMPROVEMENTS_V2.md)** | v2.0 technical improvements | ✅ v2.0 |
| **[ROUTING_QUICK_REFERENCE.md](./ROUTING_QUICK_REFERENCE.md)** | Quick routing reference | ✅ v2.0 |
| **[../IMPROVEMENTS_SUMMARY.md](../IMPROVEMENTS_SUMMARY.md)** | Executive summary of v2.0 | ✅ v2.0 |

### Agent Setup Guides (Production Ready)

| Document | Agent | Purpose | Status |
|----------|-------|---------|--------|
| **[SCHEDULING_AGENT_SETUP.md](./SCHEDULING_AGENT_SETUP.md)** | Scheduling (TIGRBGSXCS) | Appointments & projects | ✅ v2.0 Ready |
| **[INFORMATION_AGENT_SETUP.md](./INFORMATION_AGENT_SETUP.md)** | Information (JEK4SDJOOU) | Project details & status | ✅ v2.0 Ready |
| **[NOTES_AGENT_SETUP.md](./NOTES_AGENT_SETUP.md)** | Notes (CF0IPHCFFY) | Project notes | ✅ v2.0 Ready |
| **[CHITCHAT_AGENT_SETUP.md](./CHITCHAT_AGENT_SETUP.md)** | Chitchat (GXVZEOBQ64) | Casual conversation | ✅ v2.0 Ready |
| **[AGENT_INSTRUCTIONS_UPDATE_CHECKLIST.md](./AGENT_INSTRUCTIONS_UPDATE_CHECKLIST.md)** | All | Update checklist | ✅ Current |

**Note:** Supervisor agent setup is archived - v2.0 uses frontend routing for better accuracy and performance.

### Setup & Deployment Guides

| Document | Purpose | Status |
|----------|---------|--------|
| **[AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md](./AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md)** | Complete AWS setup (main guide) | ✅ Current |
| **[LAMBDA_DEPLOYMENT_GUIDE.md](./LAMBDA_DEPLOYMENT_GUIDE.md)** | Lambda deployment (automated) | ✅ Current |
| **[ACTION_GROUPS_SETUP_GUIDE.md](./ACTION_GROUPS_SETUP_GUIDE.md)** | Action groups setup | ✅ Current |
| **[WEB_CHAT_DEPLOYMENT_GUIDE.md](./WEB_CHAT_DEPLOYMENT_GUIDE.md)** | Web chat deployment | ✅ Current |
| **[MONITORING_SETUP_GUIDE.md](./MONITORING_SETUP_GUIDE.md)** | CloudWatch monitoring | ✅ Current |

### B2B Multi-Client Documentation

| Document | Purpose | Status |
|----------|---------|--------|
| **[B2B_MULTI_CLIENT_INTEGRATION_GUIDE.md](./B2B_MULTI_CLIENT_INTEGRATION_GUIDE.md)** | Complete B2B portal integration | ✅ Current |
| **[B2B_IMPLEMENTATION_SUMMARY.md](./B2B_IMPLEMENTATION_SUMMARY.md)** | B2B quick reference | ✅ Current |

### API Documentation

| Document | Purpose | Status |
|----------|---------|--------|
| **[api-documentation.html](./api-documentation.html)** | Interactive API docs (ReDoc) | ✅ Current |
| **[API_DOCUMENTATION_README.md](./API_DOCUMENTATION_README.md)** | How to use API docs | ✅ Current |

### Status & Planning

| Document | Purpose | Status |
|----------|---------|--------|
| **[CURRENT_STATUS_SUMMARY.md](./CURRENT_STATUS_SUMMARY.md)** | Project status & achievements | ✅ Current |
| **[CURRENT_PRIORITIES.md](./CURRENT_PRIORITIES.md)** | Actionable task list | ✅ Current |

---

## 📁 Phase-Specific Documentation

### Phase 2: SMS Integration (Future)

**Location:** [`phase2/`](./phase2/)

| Document | Purpose | Status |
|----------|---------|--------|
| **[PHASE2_AWS_SMS_RESEARCH.md](./phase2/PHASE2_AWS_SMS_RESEARCH.md)** | SMS integration research (Twilio approach) | 📝 Planning |

**Why Twilio?** AISPL account limitation prevents AWS SNS SMS usage

---

### Phase 3: Voice Integration (Future)

**Location:** [`phase3/`](./phase3/)

| Document | Purpose | Status |
|----------|---------|--------|
| **[PHASE3_AWS_CONNECT_RESEARCH.md](./phase3/PHASE3_AWS_CONNECT_RESEARCH.md)** | AWS Connect research | 📝 Planning |
| **[PHASE3_AISPL_ACCOUNT_WORKAROUND.md](./phase3/PHASE3_AISPL_ACCOUNT_WORKAROUND.md)** | AISPL limitation workaround | 📝 Planning |
| **[PHASE3_INDIAN_PHONE_SETUP.md](./phase3/PHASE3_INDIAN_PHONE_SETUP.md)** | Indian phone number setup | 📝 Planning |
| **[PHASE3_US_PHONE_SETUP.md](./phase3/PHASE3_US_PHONE_SETUP.md)** | US phone number setup | 📝 Planning |

**Why Twilio for Voice?** AISPL account cannot use AWS Connect

---

## 📦 Archive

**Location:** [`archive/`](./archive/)

Historical documents, outdated guides, and reference material that has been superseded by newer documentation.

### Archive Structure

```
archive/
├── bulk-ops/           # Bulk operations (future feature, not in current scope)
│   ├── BULK_OPS_API_DOCS.html
│   ├── BULK_OPS_API_SWAGGER.yaml
│   ├── BULK_OPS_DEPLOYMENT.md
│   ├── BULK_OPS_POSTMAN_COLLECTION.json
│   ├── BULK_SCHEDULING_DESIGN.md
│   └── BULK_SCHEDULING_SUMMARY.md
│
├── historical/         # Historical status docs and reference material
│   ├── 403_ERROR_RESOLUTION.md
│   ├── API_DOCUMENTATION_INDEX.md
│   ├── API_QUICK_REFERENCE.md
│   ├── AWS_SUPPORT_TICKET.md
│   ├── BEDROCK_LAMBDA_INTEGRATION_GUIDE.md
│   ├── CREATED_FILES.md
│   ├── DEPLOYMENT_STATUS.md
│   ├── DEVELOPER_HANDOVER.md
│   ├── DOCUMENTATION_INDEX.md
│   ├── ENABLE_API_ACCESS.md
│   ├── HANDOVER_SUMMARY.md
│   ├── HOW_TO_VIEW_SWAGGER_UI.md
│   ├── LAMBDA_MOCK_IMPLEMENTATION.md
│   ├── PF360_API_ANALYSIS.md
│   ├── QUICK_REFERENCE.md
│   ├── READY_TO_DEPLOY.md
│   ├── TERRAFORM_COMPLETE.md
│   ├── tfplan.txt
│   ├── UV_SETUP_COMPLETE.md
│   └── WORK_COMPLETED_SESSION_2.md
│
├── old-setup-guides/   # Superseded by AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md
│   ├── ARCHITECTURE.md
│   ├── AWS_SETUP_GUIDE.md
│   ├── AWS_SETUP_STEP_BY_STEP.md
│   ├── DEPLOYMENT_GUIDE.md
│   └── TESTING_GUIDE.md
│
├── phase2/             # Old Phase 2 docs (superseded)
│   ├── PHASE2_DEPLOYMENT_GUIDE.md
│   ├── PHASE2_IMPLEMENTATION_SUMMARY.md
│   └── PHONE_NUMBER_SETUP_GUIDE.md
│
├── planning/           # Early planning and research docs
│   ├── ARCHITECTURE_RESEARCH.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── MIGRATION_PLAN.md
│   ├── PHASE1_GETTING_STARTED.md
│   ├── PHASE3_IMPLEMENTATION_PLAN.md
│   └── PHASE3_QUICK_START.md
│
└── test-results/       # Historical test results (latest in tests/)
    ├── COMPLETE_FLOW_TEST_RESULTS.md
    ├── MOCK_API_TESTING_RESULTS.md
    └── TEST_EXECUTION_REPORT.md
```

**Note:** Archive documents are kept for historical reference but are outdated. Always use the main documentation in the root folder.

---

## 🎯 Documentation by Use Case

### I want to...

**Set up AWS from scratch:**
→ [`AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md`](./AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md)

**Deploy Lambda functions:**
→ [`LAMBDA_DEPLOYMENT_GUIDE.md`](./LAMBDA_DEPLOYMENT_GUIDE.md)

**Create action groups:**
→ [`ACTION_GROUPS_SETUP_GUIDE.md`](./ACTION_GROUPS_SETUP_GUIDE.md)
→ [`ACTION_GROUPS_QUICK_START.md`](./ACTION_GROUPS_QUICK_START.md) (quick reference)

**Deploy web chat:**
→ [`WEB_CHAT_DEPLOYMENT_GUIDE.md`](./WEB_CHAT_DEPLOYMENT_GUIDE.md)

**Set up monitoring:**
→ [`MONITORING_SETUP_GUIDE.md`](./MONITORING_SETUP_GUIDE.md)

**Understand API endpoints:**
→ [`api-documentation.html`](./api-documentation.html) (open in browser)

**Check project status:**
→ [`CURRENT_STATUS_SUMMARY.md`](./CURRENT_STATUS_SUMMARY.md)

**Know what to do next:**
→ [`CURRENT_PRIORITIES.md`](./CURRENT_PRIORITIES.md)

**Plan SMS integration:**
→ [`phase2/PHASE2_AWS_SMS_RESEARCH.md`](./phase2/PHASE2_AWS_SMS_RESEARCH.md)

**Plan voice integration:**
→ [`phase3/PHASE3_AWS_CONNECT_RESEARCH.md`](./phase3/PHASE3_AWS_CONNECT_RESEARCH.md)

---

## 🏗️ System Overview

### Current Architecture (v4.0 - Nov 2025)

```
API Gateway (REST API)
    ↓
Orchestrator Lambda (No VPC)
    ├── Claude Classifier (~200ms)
    │   ├── Direct Lambda (~2s)
    │   └── Bedrock Agents (~5-25s)
    │
    ├── 4 Bedrock Agents:
    │   ├── Supervisor (GEMYQNPYB4) - Multi-agent orchestration
    │   ├── Scheduling (LMJI2V9E8Y) - Appointment management
    │   ├── Information (VDWEVR6DJD) - Information queries
    │   └── Chitchat (DIT6BVFDYW) - Casual conversation
    │
    ├── 2 Lambda Action Functions:
    │   ├── pf-scheduling-actions
    │   └── pf-information-actions
    │
    └── DynamoDB (pf-sessions-dev)
        └── Session storage with 1hr TTL

Supporting Infrastructure:
├── Secrets Manager (pf-api-credentials)
├── IAM Roles (Bedrock + DynamoDB permissions)
├── CloudWatch Logs & Metrics
└── Interactive Test UI (localhost:8000)
```

### Current Status (2025-11-15)

- ✅ **Production System:** All components operational
- ✅ **Serverless Architecture:** DynamoDB sessions (no VPC/Redis)
- ✅ **Hybrid Routing:** Direct Lambda + Bedrock Agents
- ✅ **4 Bedrock Agents:** Deployed and tested
- ✅ **3 Lambda Functions:** Orchestrator + 2 action functions
- ✅ **Testing Infrastructure:** 5 test suites + interactive UI
- ✅ **Deployment Automation:** DEPLOY.sh, CLEANUP.sh, VALIDATE.sh
- 📝 **Phase 2:** SMS integration (code ready)
- 📝 **Phase 3:** Voice integration (code ready)

---

## 📊 Documentation Statistics

| Category | Count | Total Lines |
|----------|-------|-------------|
| **Current Guides** | 9 | ~5,500 |
| **Phase Docs** | 5 | ~200,000 |
| **Archive** | 44 | ~500,000 |
| **Total** | 58 | ~705,500 |

---

## 🔄 Documentation Updates

### Latest Changes (2025-11-15) - v4.0 Production Release

- ✅ **DynamoDB Migration:** Migrated from Redis to DynamoDB (serverless)
- ✅ **Performance Improvements:** Direct Lambda ~2s, no VPC overhead
- ✅ **Cost Optimization:** ~92% reduction ($64/mo → $5/mo)
- ✅ **Hybrid Routing:** Optimized classification and routing logic
- ✅ **Conversation Context:** build_conversation_context() for multi-turn
- ✅ **Testing Infrastructure:** 5 test suites with formatted output
- ✅ **Interactive Test UI:** localhost:8000 for manual testing
- ✅ **Deployment Automation:** Complete DEPLOY.sh, CLEANUP.sh, VALIDATE.sh
- ✅ **Documentation:** Updated all READMEs to reflect current state

### Version History

| Date | Change | Files Affected |
|------|--------|----------------|
| 2025-11-15 | **v4.0 Production** - DynamoDB migration + documentation update | All READMEs, DYNAMODB_MIGRATION.md |
| 2025-11-14 | DynamoDB migration complete | lambda/orchestrator/conversation.py, DEPLOY.sh, CLEANUP.sh |
| 2025-11-14 | Formatted testing infrastructure | testing/format_results.py, FORMATTED_TESTING.md |
| 2025-11-13 | 5 comprehensive test suites | testing/test_suite_*.sh |
| 2025-11-12 | Conversation context tracking | lambda/orchestrator/router.py |
| 2025-11-10 | Direct agent routing (USE_SUPERVISOR=false) | lambda/orchestrator/config.py |
| 2025-10-24 | v2.0 Release - Frontend routing + monitoring | frontend/backend/app.py |
| 2025-10-17 | Major reorganization | All docs |

---

## 🛠️ Utilities

### Viewing Documentation

**Local web server for docs:**
```bash
./serve-docs.sh
```

Opens documentation in browser with live reload.

**View API documentation:**
```bash
open api-documentation.html
```

Interactive ReDoc UI with all API endpoints.

---

## 📞 Support

### Documentation Issues

If you find any documentation issues:
1. Check if a newer version exists in the root folder
2. Check the archive for historical context
3. Refer to the comprehensive setup guide for current procedures

### Getting Help

- **AWS Issues:** Refer to AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md troubleshooting section
- **Lambda Issues:** Refer to LAMBDA_DEPLOYMENT_GUIDE.md troubleshooting section
- **Action Groups:** Refer to ACTION_GROUPS_SETUP_GUIDE.md

---

## 🎉 Quick Wins

**Want to get started quickly?**

1. **See what's done:** [`CURRENT_STATUS_SUMMARY.md`](./CURRENT_STATUS_SUMMARY.md) (5 min read)
2. **Complete action groups:** [`ACTION_GROUPS_QUICK_START.md`](./ACTION_GROUPS_QUICK_START.md) (30 min work)
3. **Test system:** See AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md Phase 6 (15 min)

**Want to deploy to production?**

1. Complete action groups setup
2. Follow [`WEB_CHAT_DEPLOYMENT_GUIDE.md`](./WEB_CHAT_DEPLOYMENT_GUIDE.md)
3. Follow [`MONITORING_SETUP_GUIDE.md`](./MONITORING_SETUP_GUIDE.md)

---

## 📝 Notes

- All current documentation is in the root `docs/` folder
- Phase-specific docs are in `phase2/` and `phase3/` folders
- Historical and outdated docs are in `archive/` (organized by category)
- API documentation is self-contained HTML (no server needed)
- All guides include troubleshooting sections

---

**Documentation maintained by:** Bedrock Multi-Agent Team
**Last Major Update:** 2025-10-17 (Reorganization & Cleanup)
**Next Review:** After action groups completion
