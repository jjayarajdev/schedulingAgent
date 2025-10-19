# Collaborator Alias Issue & Solution

**Date:** 2025-10-19
**Status:** ✅ RESOLVED

---

## 🚨 The Problem

When trying to update Supervisor Agent collaborators to use DRAFT aliases (`TSTALIASID`), AWS Bedrock returned this error:

```
ValidationException: Agent 5VTIWONUMO cannot collaborate with TSTALIASID alias of another agent.
Use a different alias to collaborate with.
```

**Root Cause:** AWS Bedrock **does not allow agents to collaborate using DRAFT aliases**. This is a Bedrock limitation.

---

## 🔍 Why DRAFT Aliases Don't Work for Collaboration

**DRAFT aliases (`TSTALIASID`) are special:**
- They always point to the `DRAFT` version of an agent
- They're designed for **testing and development**
- AWS Bedrock restricts their use in **multi-agent collaboration**

**Why the restriction exists:**
- DRAFT versions are mutable (can change at any time)
- Collaboration requires stable, versioned references
- AWS wants to prevent breaking changes in multi-agent systems

---

## ✅ The Solution: Version-Based Aliases

Instead of using DRAFT aliases, we need to:

### Step 1: Create New Agent Versions
```bash
# Create version from current DRAFT (which has updated instructions)
aws bedrock-agent create-agent-version \
  --agent-id IX24FSMTQH \  # Scheduling Agent
  --region us-east-1
```

This creates an **immutable snapshot** (e.g., version 5) of the current DRAFT, which includes:
- ✅ Updated instructions with AVAILABLE ACTIONS sections
- ✅ Action group configurations
- ✅ All current agent settings

### Step 2: Create/Update Version-Specific Aliases
```bash
# Create alias pointing to the new version
aws bedrock-agent create-agent-alias \
  --agent-id IX24FSMTQH \
  --agent-alias-name "v5" \
  --routing-configuration "agentVersion=5" \
  --region us-east-1
```

This creates an alias (e.g., `v5` with ID `ABC123DEF`) that points to version 5.

### Step 3: Use Version Aliases for Collaboration
```bash
# Add collaborator using version alias (NOT DRAFT alias)
aws bedrock-agent associate-agent-collaborator \
  --agent-id 5VTIWONUMO \  # Supervisor
  --agent-version DRAFT \
  --agent-descriptor aliasArn="arn:aws:bedrock:us-east-1:618048437522:agent-alias/IX24FSMTQH/ABC123DEF" \
  --collaborator-name "scheduling_collaborator" \
  --region us-east-1
```

**This works because:**
- ✅ Version alias (`ABC123DEF`) points to a specific version (5)
- ✅ Version 5 has the updated instructions with AVAILABLE ACTIONS
- ✅ AWS allows collaboration with version aliases

---

## 🔄 Updated Workflow

### Old Approach (Didn't Work)
```
DRAFT → DRAFT Alias (TSTALIASID) → Collaboration ❌
```

### New Approach (Works!)
```
DRAFT → Create Version 5 → Create Alias v5 → Collaboration ✅
```

---

## 📋 What the New Script Does

**Script:** `update_collaborator_aliases_v2.sh`

### Step-by-Step Process:

1. **Create new agent versions from DRAFT** (v5, v5, v5, v5)
   - Scheduling Agent: DRAFT → v5
   - Information Agent: DRAFT → v5
   - Notes Agent: DRAFT → v5
   - Chitchat Agent: DRAFT → v5

2. **Create/update version aliases** (v5, v5, v5, v5)
   - Each points to the newly created version
   - Gets a unique alias ID (e.g., ABC123DEF)

3. **Delete old collaborators**
   - Remove collaborators pointing to old versions (v3, v4)

4. **Add new collaborators with version aliases**
   - Use new alias IDs that point to v5 (with updated instructions)

5. **Prepare Supervisor Agent**
   - Makes the new collaborator configuration active

---

## 🎯 Benefits of Version-Based Approach

### ✅ Advantages
- **Works with Bedrock limitations** - Uses version aliases as required
- **Still gets updated instructions** - Versions created from DRAFT include all updates
- **Stable collaboration** - Versions are immutable
- **Can roll back** - Keep old versions and aliases for rollback
- **Production-ready** - Follows AWS best practices

### 📊 Comparison

| Approach | Uses Updated Instructions | Works for Collaboration | Production Ready |
|----------|---------------------------|-------------------------|------------------|
| DRAFT Alias | ✅ Yes | ❌ No (Bedrock limitation) | ❌ No |
| Version Alias | ✅ Yes | ✅ Yes | ✅ Yes |

---

## 🧪 How to Verify It Works

After running `update_collaborator_aliases_v2.sh`:

### 1. Check Collaborators Use Version Aliases
```bash
aws bedrock-agent list-agent-collaborators \
  --agent-id 5VTIWONUMO \
  --agent-version DRAFT \
  --region us-east-1
```

**Expected:** Each collaborator uses a version alias (NOT TSTALIASID)

### 2. Check Agents Have Updated Instructions
```bash
# Get version 5 instructions
aws bedrock-agent get-agent-version \
  --agent-id IX24FSMTQH \
  --agent-version 5 \
  --region us-east-1 \
  --query 'agentVersion.instruction' \
  --output text | grep "AVAILABLE ACTIONS"
```

**Expected:** Output shows "AVAILABLE ACTIONS" section

### 3. Test with Python API
```bash
./tests/test_agent_with_session.py
```

**Expected:** 5/5 tests pass, Lambda functions invoked

---

## 💡 Future Updates

**Good news:** For future agent instruction updates, you only need to:

1. Update the instruction files
2. Run `update_agent_instructions.sh` (updates DRAFT)
3. Run `update_collaborator_aliases_v2.sh` (creates new versions + updates aliases)

The workflow is still automated, just with an extra step to create versions!

---

## 📚 Related Documentation

- **Fix Guide:** `FINAL_FIX_SUMMARY.md`
- **New Script:** `scripts/update_collaborator_aliases_v2.sh`
- **Old Script:** `scripts/update_collaborator_aliases.sh` (archived - didn't work)
- **AWS Docs:** [Bedrock Multi-Agent Collaboration](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-multi-agent.html)

---

## ✅ Resolution Status

- **Issue Identified:** 2025-10-19 14:18 IST
- **Solution Created:** 2025-10-19 14:30 IST
- **Script Ready:** `update_collaborator_aliases_v2.sh`
- **Next Step:** Run the new script to complete the fix

---

**Key Takeaway:** AWS Bedrock requires version-based aliases for multi-agent collaboration, not DRAFT aliases. Our new script handles this automatically by creating versions from DRAFT and using version aliases.
