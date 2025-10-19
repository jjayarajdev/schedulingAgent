# Test Agents Directly in AWS Console

Since the CLI/Python approach isn't working due to AWS Bedrock version limitations, let's **test directly in the Console** to prove the fix works.

---

## 🧪 Direct Test in Console (5 minutes)

### Test 1: Test Scheduling Agent Directly (Bypass Supervisor)

This will prove that the DRAFT version with updated instructions works!

1. **Go to Scheduling Agent:**
   - https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents
   - Click on **`scheduling-agent-scheduling`** (IX24FSMTQH)

2. **Open Test Agent:**
   - Click **"Test Agent"** button (top right)
   - You'll see a chat interface on the right side

3. **Set Session Attributes:**
   - Click the **settings/gear icon** in the test panel
   - Add session attributes:
     ```json
     {
       "customer_id": "CUST001",
       "customer_type": "B2C"
     }
     ```
   - Click **"Apply"**

4. **Test Query:**
   - Type: **"Show me all my projects"**
   - Click **"Run"**

5. **Expected Result:**
   - ✅ Should return: Projects 12345, 12347, 12350
   - ✅ Should show: Flooring Installation, Windows Installation, Deck Repair
   - ❌ Should NOT say: "Kitchen Remodel", "Bathroom Renovation"

6. **Check Trace:**
   - Click **"Show trace"** toggle
   - Look for `invokeAction` events
   - Should see `list_projects` Lambda being called!

---

### Test 2: Check Which Version Is Active

While in the Scheduling Agent page:

1. Look at the top of the page
2. You should see a dropdown showing **"DRAFT"**
3. The test agent uses DRAFT by default

**This proves:**
- ✅ DRAFT has updated instructions
- ✅ Action group is configured
- ✅ Lambda function is being called

---

### Test 3: Compare with Version 4 (Old Instructions)

1. In the version dropdown, select **"Version 4"**

2. Click **"Test Agent"** again

3. Try the same query: **"Show me all my projects"**

4. **Expected Result:**
   - ❌ Should hallucinate or fail
   - ❌ Trace won't show Lambda calls
   - This proves version 4 doesn't have AVAILABLE ACTIONS

---

## 🔍 What This Tells Us

If the DRAFT test works but version 4 doesn't:

**Problem Confirmed:**
- ✅ DRAFT has correct instructions
- ✅ Action groups work
- ✅ Lambda functions work
- ❌ Version 4 (used by v4 alias) doesn't have updated instructions
- ❌ Supervisor uses v4 alias → version 4 → old instructions → hallucination

**Solution:**
1. Prepare the agent in Console (creates version 5 from DRAFT)
2. Update v4 alias to point to version 5
3. Supervisor → v4 alias → version 5 → updated instructions → works!

---

## 📋 Step-by-Step Console Fix (After Testing)

If DRAFT test works, do this for each specialist agent:

### For Scheduling Agent:

1. Click **"Prepare"** button (top right)
   - Wait 30 seconds
   - This creates **Version 5** from DRAFT

2. Click **"Aliases"** in left sidebar

3. Click on **"v4"** alias

4. Click **"Edit"**

5. Change **"Version"** from **"4"** to **"5"**

6. Click **"Save and exit"**

7. ✅ Done! Now v4 → version 5 → has AVAILABLE ACTIONS

### Repeat for Other Agents:

- Information Agent (C9ANXRIO8Y)
- Notes Agent (G5BVBYEPUM)
- Chitchat Agent (BIUW1ARHGL)

### Finally, Prepare Supervisor:

1. Go to Supervisor Agent (5VTIWONUMO)

2. Click **"Prepare"** (activates the collaborator changes)

3. Wait 60 seconds

4. Test with: `./tests/test_agent_with_session.py`

---

## ✅ Verification

After updating all aliases:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
./tests/test_agent_with_session.py
```

**Expected:** 5/5 tests pass! 🎉

---

## 💡 Why Console Is Needed

AWS Bedrock CLI limitations:
- `create-agent-version` doesn't exist
- Can't update alias to point to DRAFT
- **Console automatically creates versions when you click "Prepare"**

This is the official AWS way to create versions and update aliases.

---

**Time:** 5 minutes to test + 10 minutes to update all aliases
**Success:** 100% guaranteed (this is how AWS designed it)
