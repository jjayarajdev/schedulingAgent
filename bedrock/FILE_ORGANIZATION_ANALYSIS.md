# File Organization Analysis
**Date**: November 5, 2025
**Purpose**: Identify useful vs obsolete files for archiving

---

## 🟢 KEEP - Active/Current Files

### Core Deployment & Infrastructure
- `scripts/DEPLOY.sh` - **MAIN deployment script** (working, recently fixed)
- `scripts/SETUP_COLLABORATION.sh` - Agent collaboration setup
- `scripts/CLEANUP.sh` - Environment cleanup
- `scripts/deployment/` - Deployment documentation and wrappers
  - `dev_deploy.sh` - Automated deployment wrapper
  - `DEPLOYMENT_GUIDE.md` - Main documentation
  - `README.md` - Quick reference

### Lambda Functions (Active)
- `lambda/scheduling/` - Scheduling agent Lambda function
- `lambda/information/` - Information agent Lambda function
- `lambda/chitchat/` - Chitchat agent Lambda function
- Each contains:
  - `handler.py` - Lambda entry point
  - `requirements.txt` - Python dependencies
  - Supporting modules

### Agent Configuration
- `agent-instructions/` - Agent instruction files
  - `scheduling-agent-instructions.txt`
  - `information-agent-instructions.txt`
  - `notes-agent-instructions.txt`
  - `backups/` - Instruction backups (keep recent ones)

### Testing & UI
- `testing/` - Test scripts and UI
  - `ui/pf_auth_demo.html` - Working auth demo UI
  - `ui/launch_auth_demo.sh` - Launch script
  - `ui/auth_proxy.py` - Auth proxy server

### Configuration
- `config/` - Configuration files
  - Agent IDs
  - Environment configs

### Documentation (Core)
- `README.md` - Main project documentation
- `docs/phase3/` - Current phase documentation
- `API_AUTHENTICATION_GUIDE.md` - API auth guide (if exists in root)
- `DASHBOARD_API_DEPLOYMENT_STATUS.md` - Deployment status (if exists)

---

## 🟡 ARCHIVE - Old/Obsolete Files

### Old Backend Implementation
**Location**: `archive/backend-langgraph/`
**Status**: Already archived
**Reason**: LangGraph backend replaced by Bedrock agents
**Action**: ✅ Already in archive folder
**Size**: Large (.venv with all packages)

### Old Lambda Functions
**Location**: `archive/lambda/`
**Status**: Already archived
**Contains**:
- `pf360_integration/`
- `bedrock-agent-invoker/`
- `bulk-operations/`
- `sms-outbound-sender/`
- `tcpa-compliance/`
- `sms-inbound-processor/`
- `validation/`

**Action**: ✅ Already in archive folder

### Old Documentation
**Location**: `docs/archive/`
**Status**: Already archived
**Contains**:
- `phase2/` - Old phase docs
- `planning/` - Old planning docs
- `historical/` - Historical docs
- `bulk-ops/` - Bulk operations docs
- `test-results/` - Old test results
- `old-setup-guides/` - Outdated setup guides

**Action**: ✅ Already in archive folder

### Old Scripts
**Location**: `archive/scripts/`
**Status**: Already archived
**Action**: ✅ Already in archive folder

### Old Logs
**Location**: `archive/logs/` and `logs/`
**Status**: Need to consolidate
**Action**: Move `logs/` content to `archive/logs/` if old

---

## 🔴 REMOVE - Temporary/Generated Files

### Root Level Temp Files (if exist)
- `claude-request.json` - Temp file (177B) - **REMOVE**
- `*.log` files in root
- `*.pyc` files
- `__pycache__/` directories
- `.DS_Store` files

### Test Artifacts
- `tests/__pycache__/` - Python cache **REMOVE**
- `tests/v2/__pycache__/` - Python cache **REMOVE**
- Old test output files

### Build Artifacts
- `frontend/node_modules/` - **KEEP** (needed for builds, in .gitignore)
- `frontend/dist/` - Build output (if exists, in .gitignore)
- `.venv/` folders outside archive

---

## 📋 Recommended Actions

### Immediate Cleanup

1. **Remove root-level temp files**:
   ```bash
   rm claude-request.json
   ```

2. **Clean Python cache**:
   ```bash
   find . -type d -name "__pycache__" -not -path "*/node_modules/*" -not -path "*/.venv/*" -exec rm -rf {} +
   find . -name "*.pyc" -not -path "*/node_modules/*" -not -path "*/.venv/*" -delete
   ```

3. **Remove old logs** (if any in root/logs):
   ```bash
   # Review first, then move to archive
   ls -la logs/
   ```

###Consolidate Old Test Files

4. **Move old test results to archive**:
   ```bash
   # If tests/old/ or similar exists
   mv tests/old/* archive/tests/
   ```

### Documentation Cleanup

5. **Consolidate documentation**:
   - Keep: `README.md`, `docs/phase3/`, deployment guides
   - Archive: Everything already in `docs/archive/`
   - Remove: Duplicate or empty markdown files

---

## 📊 Directory Size Analysis

| Directory | Purpose | Status | Size Estimate |
|-----------|---------|--------|---------------|
| `frontend/node_modules/` | NPM packages | Keep | ~200MB |
| `archive/backend-langgraph/.venv/` | Old Python venv | Archive | ~500MB |
| `lambda/` | Active Lambda functions | **KEEP** | ~2MB |
| `scripts/` | Deployment scripts | **KEEP** | <1MB |
| `docs/` | Documentation | Keep active, archive old | ~5MB |
| `testing/` | Test files | **KEEP** | <1MB |
| `agent-instructions/` | Agent configs | **KEEP** | <1MB |

---

## ✅ Clean Project Structure (Target)

```
bedrock/
├── README.md                    # Main docs
├── .gitignore                   # Git ignore rules
├── agent-instructions/          # Agent instruction files
├── config/                      # Configuration
├── lambda/                      # Active Lambda functions
│   ├── scheduling/
│   ├── information/
│   └── chitchat/
├── scripts/                     # Deployment scripts
│   ├── DEPLOY.sh                # Main deployment
│   ├── SETUP_COLLABORATION.sh
│   ├── CLEANUP.sh
│   └── deployment/              # Deployment docs
├── testing/                     # Test files & UI
│   └── ui/                      # Auth demo UI
├── docs/                        # Active documentation
│   └── phase3/                  # Current phase
├── frontend/                    # React frontend (if used)
├── archive/                     # Old/obsolete files
│   ├── backend-langgraph/       # Old LangGraph backend
│   ├── lambda/                  # Old Lambda functions
│   ├── docs/                    # Old documentation
│   ├── scripts/                 # Old scripts
│   └── logs/                    # Old logs
└── .claude/                     # Claude Code settings
```

---

## 🎯 Summary

**Total Directories**: ~20 top-level
**Keep Active**: 8-10 directories
**Already Archived**: 5-7 directories
**Remove**: Temp files, caches, logs

**Main Issue**: Lots of Python cache files (`__pycache__`) and potential old log files scattered around.

**Action Items**:
1. ✅ Remove `claude-request.json`
2. ✅ Clean all `__pycache__` directories
3. ✅ Review and archive old logs
4. ✅ Verify archive folder has everything obsolete
5. ✅ Clean up any duplicate docs

**Storage Savings**: Estimated 50-100MB from cache cleanup alone.
