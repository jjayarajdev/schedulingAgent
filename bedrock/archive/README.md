# Archive Directory

**Purpose:** Historical and superseded files moved here to keep the main directories clean

**Date Organized:** 2025-10-19

---

## 📁 Archive Structure

```
archive/
├── docs/           # Superseded documentation
├── lambda/         # Old test scripts and unused modules
├── scripts/        # Old script outputs and superseded READMEs
└── tests/          # Old test scripts
```

---

## 📋 What's Archived

### docs/
- `ACTION_GROUPS_QUICK_SETUP.md` - Superseded by `COMPLETE_FIX_DEPLOYMENT.md`
- `AGENT_INSTRUCTIONS_UPDATE_CHECKLIST.md` - Superseded by automated scripts
- `old-archive/` - Previous archive folder
- `existingapp-docs/` - Legacy documentation

### lambda/
- `build_lambda.sh` - Superseded by `scripts/deploy_lambda_functions.sh`
- `test_all_actions*.py` - Old test scripts, superseded by `scripts/test_lambdas.sh`
- `test_complete_flows.py` - Superseded by `tests/test_agent_with_session.py`
- **Unused modules:**
  - `bedrock-agent-invoker/` - Not needed (using boto3 directly)
  - `bulk-operations/` - Future feature, not in Phase 1
  - `pf360_integration/` - Not implemented
  - `sms-inbound-processor/` - Phase 2 feature
  - `sms-outbound-sender/` - Phase 2 feature
  - `tcpa-compliance/` - Phase 2 feature
  - `shared/` - Not used
  - `validation/` - Not used

### scripts/
- `output*.json` - Old test output files
- `old-README.md` - Superseded by `README_AGENT_INSTRUCTIONS_UPDATE.md`

### tests/
- `comprehensive_test.py` - Old test without session context
- `test_agent.py` - Basic test, superseded by `test_agent_with_session.py`
- `test_agents_interactive.py` - Old interactive test
- `test_api_access.py` - API check script, no longer needed
- `TEST_EXECUTION_REPORT.md` - Old test report
- `old-README.md` - Superseded by updated test documentation

---

## ✅ Current Active Files (Not Archived)

### docs/ (14 current files)
- Agent setup guides (5 agents)
- Deployment guides (Lambda, Action Groups, Web Chat, Monitoring)
- B2B integration guides
- Hallucination fix guide
- Mock data reference
- Testing guide
- API documentation

### lambda/ (3 active modules + schemas)
- `scheduling-actions/` - Active Lambda function
- `information-actions/` - Active Lambda function
- `notes-actions/` - Active Lambda function
- `schemas/` - OpenAPI schemas for action groups

### scripts/ (9 active scripts)
- `configure_action_groups.sh` - Action groups setup
- `deploy_lambda_functions.sh` - Lambda deployment
- `gather_diagnostics.sh` - System diagnostics
- `init_database.sh` - Database initialization
- `setup_monitoring.sh` - CloudWatch monitoring
- `test_lambdas.sh` - Lambda function testing
- `update_agent_instructions.sh` - Update agent instructions with AVAILABLE ACTIONS
- `update_collaborator_aliases.sh` - Update Supervisor collaborators to DRAFT aliases
- `verify_deployment.sh` - Deployment verification

### tests/ (1 active test)
- `test_agent_with_session.py` - Complete test suite with session context

---

## 🔄 Restoration

If you need to restore any archived files:

```bash
# Example: Restore old test script
cp archive/tests/comprehensive_test.py tests/
```

---

## 🗑️ Safe to Delete

All files in this archive can be safely deleted if you're confident you won't need them. They have been superseded by newer implementations or are not part of the current Phase 1 scope.

**Recommendation:** Keep the archive for 30 days, then delete if not needed.

---

**Organized:** 2025-10-19
**By:** Automated cleanup process
