# Hallucination Fix - Quick Reference

**Two commands to fix everything:**

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/scripts

# Already done ✅
# ./update_agent_instructions.sh

# DO THIS NOW! ⬇️
./update_collaborator_aliases_v2.sh
```

**Note:** Using `v2` script (version-based approach) because AWS Bedrock doesn't allow DRAFT aliases for collaboration. See `COLLABORATOR_ALIAS_ISSUE.md` for details.

**Then test:**

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock

./tests/test_agent_with_session.py
```

**Expected:** 5/5 tests pass ✅

---

## What Each Script Does

| Script | What It Fixes | Status |
|--------|---------------|---------|
| `update_agent_instructions.sh` | Adds AVAILABLE ACTIONS to agent instructions | ✅ Done |
| `update_collaborator_aliases_v2.sh` | Creates versions & updates Supervisor to use version aliases | ⏳ **Run this now!** |

---

## Why Both Are Needed

**Script 1** updated the agents, but **Script 2** updates the Supervisor to actually USE those updated agents!

Think of it like:
- Script 1 = Fixed the specialists ✅
- Script 2 = Told the supervisor to use the fixed specialists ⏳

---

## Verification

After running Script 2, you should see:

```bash
# CloudWatch logs show Lambda invocations
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions --since 1m --region us-east-1

# Agents return real data
# Query: "Show me all my projects"
# Response: Projects 12345, 12347, 12350 (NOT Kitchen Remodel!)
```

---

**See `FINAL_FIX_SUMMARY.md` for complete details.**
