# Scripts Directory

**Purpose:** Deployment and maintenance scripts for Bedrock Multi-Agent System

**Last Updated:** 2025-10-19

---

## 📋 Available Scripts

### 🚀 Deployment Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `deploy_lambda_functions.sh` | Deploy all Lambda functions | Initial setup or Lambda code updates |
| `configure_action_groups.sh` | Configure action groups for agents | After Lambda deployment |
| `update_agent_instructions.sh` | Update agent instructions with AVAILABLE ACTIONS | Fix hallucination issue (Step 1) |
| `update_collaborator_aliases_v2.sh` | Create versions & update Supervisor collaborators | Fix hallucination issue (Step 2) ⭐ |
| `init_database.sh` | Initialize database (if using real DB) | Initial setup |

### 🧪 Testing Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `test_lambdas.sh` | Test all Lambda functions directly | Verify Lambda deployment |
| `verify_deployment.sh` | Verify complete deployment | After all setup steps |

### 📊 Monitoring Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `setup_monitoring.sh` | Configure CloudWatch monitoring | Initial setup |
| `gather_diagnostics.sh` | Gather system diagnostics | Troubleshooting |

---

## 🎯 Quick Start Workflows

### Initial Setup
```bash
# 1. Deploy Lambda functions
./deploy_lambda_functions.sh

# 2. Configure action groups
./configure_action_groups.sh

# 3. Update agent instructions (hallucination fix)
./update_agent_instructions.sh

# 4. Update collaborators (hallucination fix - CRITICAL!)
./update_collaborator_aliases_v2.sh

# 5. Test everything
./test_lambdas.sh
./verify_deployment.sh
```

### Hallucination Fix (Current Issue)
```bash
# Step 1: Update agent instructions (ALREADY DONE ✅)
./update_agent_instructions.sh

# Step 2: Update collaborators (DO THIS NOW! ⏳)
./update_collaborator_aliases_v2.sh
```

### Update Agent Instructions (Future)
```bash
# 1. Edit instruction files
vi ../agent-instructions/scheduling-agent-instructions.txt

# 2. Run update script
./update_agent_instructions.sh

# 3. Collaborators automatically use updated instructions (DRAFT aliases)
# No need to run update_collaborator_aliases.sh again!
```

---

## 📚 Documentation

For detailed information about each script, see:
- **Agent Instructions Update:** `README_AGENT_INSTRUCTIONS_UPDATE.md`
- **Complete Fix Guide:** `../COMPLETE_FIX_DEPLOYMENT.md`
- **Quick Reference:** `../QUICK_FIX_GUIDE.md`

---

## 🔧 Script Details

### update_agent_instructions.sh ⭐
**Purpose:** Update agent instructions to include AVAILABLE ACTIONS sections

**What it does:**
1. Backs up current instructions
2. Updates Scheduling, Information, Notes agents
3. Prepares all agents
4. Verifies AVAILABLE ACTIONS sections exist

**Usage:**
```bash
./update_agent_instructions.sh
```

**Time:** ~3 minutes

---

### update_collaborator_aliases_v2.sh ⭐ NEW!
**Purpose:** Create agent versions and update Supervisor Agent collaborators

**What it does:**
1. Creates new versions from DRAFT (includes updated instructions)
2. Creates/updates version aliases pointing to new versions
3. Deletes old collaborators (pointing to old versions)
4. Recreates collaborators using version aliases
5. Prepares Supervisor Agent
6. Verifies all use version aliases

**Why version aliases:** AWS Bedrock doesn't allow DRAFT aliases for collaboration. Must use version-specific aliases.

**Why critical:** Version aliases point to versions with updated instructions, so agents call Lambda functions!

**Usage:**
```bash
./update_collaborator_aliases_v2.sh
```

**Time:** ~3 minutes

**See:** `../COLLABORATOR_ALIAS_ISSUE.md` for why we use version aliases instead of DRAFT

---

### deploy_lambda_functions.sh
**Purpose:** Deploy all Lambda functions to AWS

**What it does:**
1. Packages Lambda code with dependencies
2. Creates/updates Lambda functions
3. Sets environment variables
4. Grants Bedrock permissions

**Usage:**
```bash
./deploy_lambda_functions.sh
```

---

### configure_action_groups.sh
**Purpose:** Configure action groups for specialist agents

**What it does:**
1. Checks current action groups
2. Deletes existing if needed
3. Creates new action groups linked to Lambdas
4. Prepares all agents

**Usage:**
```bash
./configure_action_groups.sh
```

---

### test_lambdas.sh
**Purpose:** Test all Lambda functions directly

**What it does:**
1. Tests all 8 Lambda actions
2. Color-coded pass/fail output
3. Summary statistics

**Usage:**
```bash
./test_lambdas.sh
```

---

## 🗂️ Related Files

- `../agent-instructions/` - Agent instruction text files
- `../lambda/` - Lambda function code
- `../tests/` - Test scripts
- `../docs/` - Documentation

---

## 💡 Tips

1. **Always run scripts from the scripts directory:**
   ```bash
   cd /path/to/bedrock/scripts
   ./script_name.sh
   ```

2. **Check logs if scripts fail:**
   ```bash
   # CloudWatch logs
   aws logs tail /aws/lambda/scheduling-agent-scheduling-actions --follow
   ```

3. **Scripts create backups automatically**
   - Agent instructions: `../agent-instructions/backups/TIMESTAMP/`
   - Safe to re-run scripts

4. **For production deployment:**
   - Test in dev first
   - Use version control for instruction files
   - Document changes in git commits

---

## 🆕 NEW: Configuration Management & Testing (November 2025)

### update_agent_configs.sh
**Purpose:** Dynamically update environment-specific agent configuration files

**What it does:**
1. Reads `config/agent_ids.json` (generated by DEPLOY.sh)
2. Creates/updates environment configs:
   - `config/agent_config.dev.json`
   - `config/agent_config.staging.json`
   - `config/agent_config.prod.json`
3. Creates symlinks in `backend/` for backward compatibility

**Usage:**
```bash
./update_agent_configs.sh
```

**When to use:**
- Automatically runs after DEPLOY.sh
- After manually editing agent_ids.json
- To refresh environment configs

**Benefits:**
- Single source of truth (agent_ids.json)
- Automatic config generation
- Environment-specific settings
- No manual JSON editing required

---

### test_agent_flow.py ⭐
**Purpose:** Interactive end-to-end testing of multi-agent workflow

**What it does:**
1. **Chitchat Test** - Verifies conversational routing
2. **List Projects** - Tests project retrieval from API
3. **Project Details** - Iterates through projects and gets details

**Usage:**
```bash
./test_agent_flow.py
```

**Interactive Prompts:**
- Client ID
- User ID
- Bearer Token

**Features:**
- Color-coded output
- Automatic project ID extraction
- Session persistence
- Comprehensive error handling
- Test summary

**Example:**
```
Client ID: 09PF05VD
User ID: user123
Bearer Token: eyJhbG...

===================================================================
Test 1: Chitchat
===================================================================
✅ Chitchat test passed

Response:
Hi there! I'm doing great, thank you for asking!

===================================================================
Test 2: List Projects
===================================================================
✅ List projects test passed
ℹ️  Found 5 project ID(s): 233434, 233435, 233436, 233437, 233438

===================================================================
Test 3: Get Project Details
===================================================================
✅ Project 233434 details retrieved

===================================================================
Test Summary
===================================================================
Total: 3/3 tests passed
✅ All tests passed! 🎉
```

---

## 📂 NEW: Configuration Structure

```
config/
├── agent_config.dev.json        # Development (auto-generated)
├── agent_config.staging.json    # Staging (auto-generated)
├── agent_config.prod.json       # Production (auto-generated)
└── agent_ids.json               # Master config (DEPLOY.sh)

backend/
├── agent_config.json           -> ../config/agent_config.dev.json
├── agent_config.dev.json       -> ../config/agent_config.dev.json
├── agent_config.staging.json   -> ../config/agent_config.staging.json
└── agent_config.prod.json      -> ../config/agent_config.prod.json
```

**Benefits:**
- Centralized configuration in `config/` folder
- Environment-specific settings
- Symlinks for backward compatibility
- Automatic updates on deployment

---

## 🔄 Updated Workflow

### Complete Setup (New Recommended Flow)
```bash
# 1. Deploy all infrastructure
./DEPLOY.sh
# Automatically runs update_agent_configs.sh

# 2. Set up collaboration (if needed)
./SETUP_COLLABORATION.sh

# 3. Test end-to-end flow
./test_agent_flow.py
```

### Manual Config Update
```bash
# Update configs from agent_ids.json
./update_agent_configs.sh
```

---

**Last Updated:** 2025-11-06
**Status:** All scripts tested and working ✅
**New Scripts:** ✅ update_agent_configs.sh, ✅ test_agent_flow.py
