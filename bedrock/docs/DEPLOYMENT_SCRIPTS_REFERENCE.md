# ProjectForce Deployment Scripts Reference

**Last Updated:** November 9, 2025

This document provides a comprehensive reference for all deployment, cleanup, and collaboration scripts in the ProjectForce Bedrock project.

---

## Quick Reference

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `DEPLOY.sh` | Deploy core 4-agent architecture | Initial setup or updates |
| `SETUP_COLLABORATION.sh` | Configure Supervisor-agent routing | After creating v1 aliases |
| `CLEANUP.sh` | Remove all core resources | Start fresh or troubleshoot |
| `DEPLOY_VOICE_MINIMAL.sh` | Deploy voice integration infrastructure | Add phone support |
| `CLEANUP_VOICE.sh` | Remove voice integration | Remove phone support |

---

## Core Deployment Scripts

### 1. DEPLOY.sh

**Purpose:** Deploy the complete 4-agent Bedrock architecture

**What it deploys:**
- ✅ 4 Bedrock Agents:
  - Supervisor (orchestrator)
  - SchedulingAgent (project management)
  - pf-information (weather data)
  - pf-chitchat (conversational)
- ✅ 2 Lambda Functions:
  - pf-scheduling-actions
  - pf-information-actions
- ✅ 2 Action Groups (attached to SchedulingAgent and pf-information)
- ✅ DynamoDB table: `pf-sessions-dev`
- ✅ Secrets Manager secret: `projectforce/api/credentials`
- ✅ IAM roles and permissions

**Prerequisites:**
- AWS CLI configured
- Python 3.11+ installed
- jq installed

**Usage:**
```bash
cd bedrock
./scripts/DEPLOY.sh
```

**Interactive prompts:**
- ProjectForce API credentials (Client ID, User ID, Bearer Token, Refresh Token)

**Outputs:**
- Agent IDs saved to `config/agent_ids.json`
- Deployment configuration

**Next steps after deployment:**
1. Create v1 aliases via AWS Console
2. Run `SETUP_COLLABORATION.sh`
3. Test agents
4. (Optional) Deploy voice integration

**Estimated time:** 15-20 minutes

---

### 2. SETUP_COLLABORATION.sh

**Purpose:** Configure Supervisor agent collaboration with specialist agents

**What it does:**
- Checks for v1 aliases on all 3 collaborator agents
- Associates collaborators with Supervisor agent
- Updates Supervisor agent alias with collaboration config
- Prepares all agents

**Prerequisites:**
- `DEPLOY.sh` must be completed
- v1 aliases created via AWS Console for:
  - SchedulingAgent
  - pf-information
  - pf-chitchat

**Usage:**
```bash
cd bedrock
./scripts/SETUP_COLLABORATION.sh
```

**Outputs:**
- Collaboration associations created
- Supervisor agent updated and prepared

**Estimated time:** 2-3 minutes

**Notes:**
- Creating v1 aliases is a one-time manual step (takes ~15 min via Console)
- This script reads from `config/agent_ids.json`

---

### 3. CLEANUP.sh

**Purpose:** Remove all core ProjectForce Bedrock resources

**What it deletes:**
- ✅ All 4 Bedrock agents
- ✅ All agent aliases (except TSTALIASID)
- ✅ 2 Lambda functions
- ✅ Secrets Manager secret
- ✅ DynamoDB tables (pf-sessions-dev, pf-notes-dev)
- ⚠️ IAM roles (optional - use `--delete-roles` flag)

**What it preserves:**
- Voice integration resources (must be deleted separately)

**Usage:**
```bash
# Delete agents and Lambda only
cd bedrock
./scripts/CLEANUP.sh

# Delete everything including IAM roles
./scripts/CLEANUP.sh --delete-roles
```

**Confirmations:**
- Requires typing "yes" to confirm

**Next steps after cleanup:**
1. (Optional) Run `CLEANUP_VOICE.sh` if voice was deployed
2. Review `FINAL_AGENT_ARCHITECTURE.md`
3. Run `DEPLOY.sh` to rebuild

**Estimated time:** 3-5 minutes

---

## Voice Integration Scripts

### 4. DEPLOY_VOICE_MINIMAL.sh

**Purpose:** Deploy Lambda functions and infrastructure for AWS Connect voice integration

**What it deploys:**
- ✅ 2 Lambda Functions:
  - `pf-lex-fulfillment-dev` (routes Lex intents)
  - `pf-voice-bedrock-bridge-dev` (bridges to Bedrock Supervisor)
- ✅ DynamoDB table: `pf-session-data-dev` (voice session state)
- ✅ S3 bucket: `pf-call-recordings-dev-{account-id}` (encrypted, versioned)
- ✅ IAM roles with Bedrock invocation permissions
- ✅ CloudWatch log groups (14-day retention)

**What it does NOT deploy:**
- ❌ AWS Connect instance (manual via Console)
- ❌ Amazon Lex bot (manual via Console)
- ❌ Contact flows (manual via Console)
- ❌ Phone number (manual via Console)

**Prerequisites:**
- Core agents deployed via `DEPLOY.sh`
- `config/agent_ids.json` exists
- Python 3.11+ and pip3 installed

**Usage:**
```bash
cd bedrock
./scripts/DEPLOY_VOICE_MINIMAL.sh
```

**Interactive prompts:**
- Confirmation to deploy infrastructure

**Outputs:**
- Lambda ARNs (needed for Lex setup)
- Deployment info saved to `config/voice_deployment.json`
- Test results (both Lambdas tested)

**Next steps after deployment:**
1. Follow `docs/AWS_CONSOLE_SETUP_GUIDE.md` to:
   - Create AWS Connect instance
   - Create Lex bot
   - Configure contact flows
2. Test end-to-end by calling phone number

**Estimated time:** 5-10 minutes (deployment only)
**Total time with manual setup:** 60-90 minutes

**Configuration:**
- Dynamically loads Supervisor agent ID from `config/agent_ids.json`
- Uses test alias (TSTALIASID) or v1 alias if available
- Packages Lambda functions with dependencies

---

### 5. CLEANUP_VOICE.sh

**Purpose:** Remove voice integration Lambda functions and storage

**What it deletes:**
- ✅ Lambda functions: `pf-lex-fulfillment-dev`, `pf-voice-bedrock-bridge-dev`
- ✅ S3 bucket (call recordings) - emptied first, then deleted
- ✅ DynamoDB table: `pf-session-data-dev`
- ✅ IAM roles and policies
- ✅ CloudWatch log groups
- ✅ Local deployment files (deployment.zip, package/)

**What requires manual deletion:**
- 📋 AWS Connect instance (via Console)
- 📋 Phone number (via Console)
- 📋 Lex bot (via Console)
- 📋 Contact flows (via Console)

**What it preserves:**
- ✅ Bedrock agents (Supervisor, SchedulingAgent, etc.)
- ✅ Action groups and collaborations
- ✅ Core infrastructure

**Usage:**
```bash
cd bedrock
./scripts/CLEANUP_VOICE.sh
```

**Confirmations:**
- Type "yes" to confirm
- Type "DELETE" to double-confirm

**Next steps after cleanup:**
1. Manually delete AWS Connect instance (if created)
2. Manually delete Lex bot (if created)
3. To redeploy: `./scripts/DEPLOY_VOICE_MINIMAL.sh`

**Estimated time:** 3-5 minutes

---

## Supporting Scripts

### 6. update_agent_configs.sh

**Purpose:** Update agent configuration files with current agent IDs

**Automatically called by:** `DEPLOY.sh`

**What it does:**
- Updates environment-specific config files
- Syncs agent IDs across configuration files

---

### 7. prepare_agents.sh

**Purpose:** Prepare all Bedrock agents (make them ready for invocation)

**Usage:**
```bash
./scripts/prepare_agents.sh
```

---

### 8. test_voice_integration.sh

**Purpose:** Test voice Lambda functions

**What it tests:**
- Lex fulfillment Lambda
- Voice-Bedrock bridge Lambda
- DynamoDB connectivity
- Bedrock agent invocation

**Usage:**
```bash
./scripts/test_voice_integration.sh
```

---

## Deployment Workflow

### Initial Setup (First Time)

```bash
# 1. Deploy core agents
./scripts/DEPLOY.sh
# → Prompts for API credentials
# → Deploys 4 agents, 2 Lambdas, DynamoDB

# 2. Create v1 aliases via AWS Console (15 min)
# Console → Bedrock → Agents → Each agent → Create version → Create alias

# 3. Setup collaboration
./scripts/SETUP_COLLABORATION.sh
# → Associates collaborators with Supervisor

# 4. Test agents
aws bedrock-agent-runtime invoke-agent \
  --agent-id <SUPERVISOR_ID> \
  --agent-alias-id TSTALIASID \
  --session-id test-123 \
  --input-text "List my projects" /tmp/output.txt

# 5. (Optional) Deploy voice integration
./scripts/DEPLOY_VOICE_MINIMAL.sh
# → Deploys voice Lambda functions

# 6. (Optional) Setup AWS Connect & Lex manually
# Follow: docs/AWS_CONSOLE_SETUP_GUIDE.md (60-90 min)
```

### Update Workflow

```bash
# Update core agents
./scripts/DEPLOY.sh
# → Updates existing agents, Lambdas

# If voice is deployed, update voice
./scripts/DEPLOY_VOICE_MINIMAL.sh
# → Updates voice Lambda functions
```

### Cleanup Workflow

```bash
# Remove everything
./scripts/CLEANUP.sh --delete-roles
./scripts/CLEANUP_VOICE.sh

# Then redeploy if needed
./scripts/DEPLOY.sh
./scripts/SETUP_COLLABORATION.sh
./scripts/DEPLOY_VOICE_MINIMAL.sh
```

---

## File Locations

### Scripts
```
bedrock/scripts/
├── DEPLOY.sh                    # Core deployment
├── CLEANUP.sh                   # Core cleanup
├── SETUP_COLLABORATION.sh       # Collaboration setup
├── DEPLOY_VOICE_MINIMAL.sh      # Voice deployment
├── CLEANUP_VOICE.sh             # Voice cleanup
├── update_agent_configs.sh      # Config sync
└── test_voice_integration.sh    # Voice testing
```

### Configuration Files
```
bedrock/config/
├── agent_ids.json              # Agent IDs (created by DEPLOY.sh)
└── voice_deployment.json       # Voice info (created by DEPLOY_VOICE_MINIMAL.sh)
```

### Infrastructure Code
```
bedrock/infrastructure/
├── agent_instructions/         # Agent instruction files
│   ├── supervisor.txt
│   ├── scheduling_collaborator.txt
│   ├── information_collaborator.txt
│   └── chitchat_collaborator.txt
└── terraform/
    └── voice-minimal/          # Voice Terraform config
        ├── main.tf
        ├── variables.tf
        └── terraform.tfvars (generated)
```

### Lambda Code
```
bedrock/lambda/
├── scheduling-actions/         # Scheduling Lambda
├── information-actions/        # Weather Lambda
├── lex-fulfillment/           # Lex intent router
└── voice-bedrock-bridge/      # Voice-to-Bedrock bridge
```

---

## Environment Variables

### Core Deployment (DEPLOY.sh)
- `PF_CLIENT_ID` - ProjectForce client ID
- `PF_USER_ID` - ProjectForce user ID
- `PF_API_TOKEN` - Bearer token
- `PF_REFRESH_TOKEN` - Refresh token (optional)
- `USE_MOCK_API` - Use mock data (default: false)

### Voice Deployment (DEPLOY_VOICE_MINIMAL.sh)
- Reads from `config/agent_ids.json`
- No environment variables required

---

## Troubleshooting

### DEPLOY.sh Issues

**Problem:** "Agent already exists"
- **Solution:** Script will update existing agent, this is normal

**Problem:** "Lambda deployment failed"
- **Solution:** Check CloudWatch logs, verify IAM role exists

**Problem:** "Secrets Manager access denied"
- **Solution:** Check AWS credentials have Secrets Manager permissions

### SETUP_COLLABORATION.sh Issues

**Problem:** "v1 alias not found"
- **Solution:** Create v1 alias via AWS Console first

**Problem:** "Failed to associate collaborator"
- **Solution:** Ensure Supervisor agent has collaboration enabled

### Voice Deployment Issues

**Problem:** "DynamoDB table already exists"
- **Solution:** Script imports existing table, this is expected

**Problem:** "Lambda environment variable AWS_REGION is reserved"
- **Solution:** Fixed in voice-minimal/main.tf (uses AWS-provided region)

**Problem:** "Bedrock access denied"
- **Solution:** IAM policy updated to include agent-alias ARN

---

## Cost Estimates

### Core Infrastructure (Monthly)
- Bedrock agents: Pay-per-use (~$0.003/1K tokens)
- Lambda (2 functions): ~$5-10 (depending on usage)
- DynamoDB: ~$5 (on-demand pricing)
- Secrets Manager: ~$1

**Total:** ~$15-20/month for moderate usage

### Voice Integration (Monthly)
- Lambda (2 additional): ~$5-10
- DynamoDB (voice sessions): ~$2-5
- S3 (call recordings): ~$1-3
- AWS Connect: ~$0.018/min inbound
- Amazon Lex: ~$0.00075/request
- Bedrock (via voice): ~$0.003/1K input, ~$0.015/1K output

**Total:** ~$35-60/month for 100-500 calls/month

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2025-11-09 | 2.0 | Added voice integration (minimal deployment) |
| 2025-11-04 | 1.5 | Updated for 4-agent architecture |
| 2025-11-03 | 1.0 | Initial deployment scripts |

---

## Related Documentation

- [AWS Console Setup Guide](./AWS_CONSOLE_SETUP_GUIDE.md) - Manual Lex/Connect setup
- [Voice Deployment Status](./VOICE_DEPLOYMENT_STATUS.md) - Current deployment status
- [Final Agent Architecture](./FINAL_AGENT_ARCHITECTURE.md) - Architecture overview
- [Voice Scripts Reference](./VOICE_SCRIPTS_REFERENCE.md) - Voice script details

---

## Support

For issues or questions:
1. Check CloudWatch logs
2. Review troubleshooting section above
3. Run verification: `./scripts/verify_deployment.sh`
4. Check AWS Console for resource status
