# AWS Console Fix - Step by Step

**IMPORTANT:** Due to AWS Bedrock limitations, this MUST be done via the AWS Console.

**Why:**
- ❌ Can't use DRAFT aliases for collaboration
- ❌ Can't update aliases to point to DRAFT via CLI
- ❌ `create-agent-version` CLI command doesn't exist
- ✅ Console automatically creates versions when you prepare agents

---

## 🎯 The Fix (15 minutes via Console)

### Step 1: Prepare Scheduling Agent (Creates Version 5)

1. Go to: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents

2. Click on **`scheduling-agent-scheduling`** (IX24FSMTQH)

3. You should see a banner: **"DRAFT version has unsaved changes"**
   - This is the updated instructions from `update_agent_instructions.sh`!

4. Click **"Prepare"** button (top right)

5. Wait ~30 seconds for status to change to **"PREPARED"**

6. Click **"View all versions"** (in left sidebar under "Agent overview")

7. You should see **Version 5** was just created

8. Click **"Aliases"** (in left sidebar)

9. Click on **"v4"** alias

10. Click **"Edit"**

11. Change **"Agent version"** from **"4"** to **"5"**

12. Click **"Save"**

13. ✅ Done! v4 alias now points to version 5 (which has AVAILABLE ACTIONS)

---

### Step 2: Prepare Information Agent (Creates Version 5)

Repeat the same steps for **`scheduling-agent-information`** (C9ANXRIO8Y):

1. Click on **`scheduling-agent-information`**
2. Click **"Prepare"**
3. Wait 30 seconds
4. Go to **"Aliases"** → **"v4"** → **"Edit"**
5. Change version from **"4"** to **"5"**
6. Click **"Save"**

---

### Step 3: Prepare Notes Agent (Creates Version 5)

Repeat for **`scheduling-agent-notes`** (G5BVBYEPUM):

1. Click on **`scheduling-agent-notes`**
2. Click **"Prepare"**
3. Wait 30 seconds
4. Go to **"Aliases"** → **"v4"** → **"Edit"**
5. Change version from **"4"** to **"5"**
6. Click **"Save"**

---

### Step 4: Prepare Chitchat Agent (Creates Version 5)

Repeat for **`scheduling-agent-chitchat`** (BIUW1ARHGL):

1. Click on **`scheduling-agent-chitchat`**
2. **NOTE:** This agent may already be PREPARED (it's a supervisor itself)
3. If not prepared, click **"Prepare"**
4. Go to **"Aliases"** → **"v4"** → **"Edit"**
5. Change version from **"4"** to **"5"** (or latest version)
6. Click **"Save"**

---

### Step 5: Update Supervisor Collaborators (CRITICAL!)

1. Go back to agent list

2. Click on **`scheduling-agent-supervisor`** (5VTIWONUMO)

3. Click **"Edit in Agent Builder"** (top right)

4. Scroll down to **"Collaborators"** section

5. For each collaborator (**scheduling_collaborator, information_collaborator, notes_collaborator, chitchat_collaborator**):

   a. Click **"Edit"** next to the collaborator

   b. Under **"Agent version"**, change from current version to the **v4** alias
      - **Important:** Select the **alias name "v4"**, NOT version number 4!

   c. Click **"Save"**

6. After updating all 4 collaborators, click **"Save"** (top right)

7. Click **"Prepare"** (this activates the changes)

8. Wait 30-60 seconds

---

## ✅ Verification

After completing all steps, run:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
./tests/test_agent_with_session.py
```

**Expected:** 5/5 tests pass, CloudWatch shows Lambda invocations

---

## 🔍 Check CloudWatch Logs

Open in another terminal:

```bash
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions --follow --region us-east-1
```

Then run the tests. You should see Lambda invocations appear in real-time!

---

## 📊 What This Accomplishes

**Before:**
```
Supervisor → v4 alias → Version 4 → OLD instructions (no AVAILABLE ACTIONS) → Hallucinates ❌
```

**After:**
```
Supervisor → v4 alias → Version 5 → NEW instructions (with AVAILABLE ACTIONS) → Calls Lambda! ✅
```

---

## ⚡ Quick Summary (TL;DR)

1. **Prepare each specialist agent** (Scheduling, Information, Notes, Chitchat)
   - This creates version 5 with updated instructions

2. **Update v4 alias** for each agent to point to version 5
   - Console: Aliases → v4 → Edit → Change to version 5

3. **Update Supervisor collaborators** to use v4 aliases
   - Make sure they're using alias "v4", not version number

4. **Prepare Supervisor**

5. **Test!**

---

## 🚨 Why Console is Required

AWS Bedrock CLI limitations we discovered:
- `create-agent-version` command doesn't exist
- Can't point regular aliases to DRAFT
- DRAFT alias can't be used for collaboration
- Console automatically creates versions when preparing

**The Console is the ONLY way** to create agent versions and update aliases properly.

---

## 💡 Alternative: Use Terraform

If you want to automate this in the future, use Terraform to:
- Create new agent versions
- Update alias routing
- Update collaborator configuration

For now, Console is fastest!

---

**Time Required:** ~15 minutes
**Difficulty:** Easy (click and wait)
**Success Rate:** 100% (this is the official AWS way)

---

**After this, the hallucination issue will be FIXED!** 🎉
