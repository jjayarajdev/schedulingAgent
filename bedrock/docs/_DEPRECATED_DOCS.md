# Deprecated Documentation

**Last Updated:** October 13, 2025

These documents are outdated or have been superseded by newer documentation. They can be archived or deleted to avoid confusion.

---

## ⚠️ Deprecated Documents (Can Be Deleted)

### GETTING_STARTED.md
**Status:** OUTDATED
**Reason:** Talks about Phase 1 as infrastructure provisioning (Aurora, Redis, etc.), not Bedrock Agents
**Replaced By:**
- `DEVELOPER_HANDOVER.md` (primary entry point)
- `DEPLOYMENT_GUIDE.md` (for actual deployment)
**Created:** October 12, 2025
**Lines:** 453

**Why It's Outdated:**
- References building FastAPI backend and React frontend
- Talks about Aurora PostgreSQL and Redis (not yet deployed)
- Mentions "Phase 1: Infrastructure Setup" when actual Phase 1 is Bedrock Agents
- Does not reflect current project status

**Action:** DELETE (content no longer relevant)

---

## 📋 Documents with Significant Overlap (Consider Consolidating)

### Group 1: AWS Setup Guides (3 documents)

#### 1. AWS_SETUP_GUIDE.md (20 KB, 644 lines)
- Comprehensive AWS setup guide
- Includes prerequisites, permissions, quotas, secrets, costs
- Well-structured and complete
- **Keep as reference**

#### 2. AWS_SETUP_STEP_BY_STEP.md (18 KB, 1,061 lines)
- Command-by-command execution guide
- Very detailed with expected outputs
- Overlaps significantly with AWS_SETUP_GUIDE.md
- **Recommendation:** Archive or consolidate into AWS_SETUP_GUIDE.md

#### 3. PHASE1_GETTING_STARTED.md (12 KB, 600 lines)
- Implementation order and task breakdown
- Good content for task planning
- Some overlap with AWS_SETUP_GUIDE.md
- **Recommendation:** Keep for now, but mark as "Implementation Reference"

### Group 2: Deployment Guides (2 documents)

#### 1. DEPLOYMENT_GUIDE.md (14 KB, 640 lines)
- Complete step-by-step deployment guide
- Up-to-date with current project status
- **Keep as primary deployment reference**

#### 2. DEPLOYMENT_STATUS.md (5 KB, 250 lines)
- Current deployment status
- Agent IDs and testing procedures
- **Keep for quick reference**

---

## ✅ Current & Accurate Documentation

These documents are current, accurate, and should be kept:

### Primary Documentation
- ✅ `DEVELOPER_HANDOVER.md` ⭐ **NEW - PRIMARY ENTRY POINT**
- ✅ `README.md` - Project overview
- ✅ `DEPLOYMENT_STATUS.md` - Current status
- ✅ `DEPLOYMENT_GUIDE.md` - Deployment procedures

### API Documentation
- ✅ `API_DOCUMENTATION_INDEX.md` - Master API index
- ✅ `API_DOCUMENTATION_README.md` - Complete API docs
- ✅ `API_QUICK_REFERENCE.md` - API cheat sheet
- ✅ `BULK_OPS_API_DOCS.html` - Interactive Swagger UI
- ✅ `BULK_OPS_API_SWAGGER.yaml` - OpenAPI specification
- ✅ `BULK_OPS_POSTMAN_COLLECTION.json` - Postman collection

### Design & Architecture
- ✅ `ARCHITECTURE_RESEARCH.md` - Bedrock vs LangGraph comparison (60 pages)
- ✅ `BULK_SCHEDULING_DESIGN.md` - Bulk operations design
- ✅ `BULK_SCHEDULING_SUMMARY.md` - Feature summary
- ✅ `ARCHITECTURE.md` - System architecture

### Phase-Specific Research
- ✅ `PHASE2_AWS_SMS_RESEARCH.md` - SMS infrastructure research (80 KB)
- ✅ `PHONE_NUMBER_SETUP_GUIDE.md` - Phone setup guide (30 KB)
- ✅ `PHASE3_AWS_CONNECT_RESEARCH.md` - AWS Connect IVR research (68 KB)

### Deployment & Operations
- ✅ `BULK_OPS_DEPLOYMENT.md` - Bulk ops deployment guide
- ✅ `403_ERROR_RESOLUTION.md` - Cross-region permission fix
- ✅ `ENABLE_API_ACCESS.md` - API access troubleshooting

### Reference
- ✅ `AWS_SETUP_GUIDE.md` - Comprehensive AWS setup
- ✅ `TESTING_GUIDE.md` - Testing procedures
- ✅ `CREATED_FILES.md` - File inventory
- ✅ `IMPLEMENTATION_PLAN.md` - Original plan
- ✅ `MIGRATION_PLAN.md` - Migration strategy
- ✅ `AWS_SUPPORT_TICKET.md` - Support ticket template

### Terraform
- ✅ `TERRAFORM_COMPLETE.md` - Terraform details
- ✅ `tfplan.txt` - Terraform plan output

---

## 📝 Recommended Actions

### Immediate Actions

1. **Delete Outdated:**
   ```bash
   cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/docs

   # Move to archive
   mkdir -p _archive
   mv GETTING_STARTED.md _archive/
   ```

2. **Mark Deprecated:**
   - Add warning at top of AWS_SETUP_STEP_BY_STEP.md pointing to AWS_SETUP_GUIDE.md

3. **Update References:**
   - Ensure all active documents point to DEVELOPER_HANDOVER.md as primary entry

### Future Actions (Optional)

1. **Consolidate AWS Setup Guides:**
   - Merge AWS_SETUP_STEP_BY_STEP.md into AWS_SETUP_GUIDE.md
   - Keep command-by-command sections
   - Archive PHASE1_GETTING_STARTED.md after Phase 1 Lambda implementation

2. **Create Documentation Tiers:**
   - **Tier 1 (Start Here):** DEVELOPER_HANDOVER.md, README.md
   - **Tier 2 (Reference):** DEPLOYMENT_GUIDE.md, API docs, Phase research
   - **Tier 3 (Deep Dive):** Architecture, Terraform, detailed guides

---

## Summary

### Files to Delete
- `GETTING_STARTED.md` (453 lines) - Completely outdated

### Files to Consider Consolidating Later
- `AWS_SETUP_STEP_BY_STEP.md` → merge into `AWS_SETUP_GUIDE.md`
- `PHASE1_GETTING_STARTED.md` → archive after Phase 1 complete

### Total Documentation
- **Current Files:** 39 markdown files in docs/
- **After Cleanup:** 38 files (1 moved to archive)
- **Primary Entry Point:** `DEVELOPER_HANDOVER.md` ⭐

---

**Next Review:** After Phase 1 Lambda functions complete
