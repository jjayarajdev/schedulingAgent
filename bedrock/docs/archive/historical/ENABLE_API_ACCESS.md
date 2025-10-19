# Enable Bedrock API Access - Step-by-Step Guide

**How to enable programmatic (API) access for Claude Sonnet 4.5**

---

## 🎯 Current Situation

✅ **Console access works** - You can test agents in AWS Console
❌ **API access fails** - Python scripts get "AccessDeniedException"

**Goal:** Enable API access so Python scripts can invoke agents programmatically.

---

## 📋 Step-by-Step Instructions

### Step 1: Open Bedrock Model Access

**Method A: Direct Link**
```
https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess
```

**Method B: Navigate Manually**
1. Go to AWS Console: https://console.aws.amazon.com
2. Search for "Bedrock" in the top search bar
3. Click on **Amazon Bedrock**
4. In the left sidebar, click **Model access** (under "Foundation models")

---

### Step 2: Check Current Access Status

You should see a page titled **"Model access"** with a list of foundation models.

**Look for:**
- **Claude Sonnet 4.5** (or similar name)
- **Model ID:** `anthropic.claude-sonnet-4-5-20250929-v1:0`

**Check the Status Column:**

| Status | What It Means | What You Need |
|--------|---------------|---------------|
| ✅ **Access granted** | Full access (Console + API) | Nothing - you're good! |
| 🟡 **Console access only** | Can test in console, but API blocked | Enable API access |
| ⚠️ **Cross-region inference only** | Limited to cross-region profile | Enable direct model access |
| ❌ **Not available** | No access | Request access |

---

### Step 3: Enable API Access

#### Option A: If Status Shows "Access granted"

✅ **You already have full access!** The issue might be:
- Using wrong model ID
- Using wrong inference profile
- Account-level restrictions

**Skip to Step 5 (Troubleshooting)**

---

#### Option B: If Status Shows Partial Access

Look for one of these buttons:

**Button 1: "Manage model access"**
1. Click **"Manage model access"** (top right)
2. Find **Claude Sonnet 4.5** in the list
3. Look for checkboxes:
   - ☐ Console access
   - ☐ API access
   - ☐ On-demand throughput
   - ☐ Provisioned throughput
4. **Check ALL boxes** (especially "API access" or "On-demand")
5. Click **"Save changes"** at the bottom
6. Wait 2-5 minutes for changes to propagate

**Button 2: "Modify model access"**
1. Click **"Modify model access"**
2. Select the model
3. Choose access type:
   - ✅ **On-demand** (recommended - pay per use)
   - ☐ Provisioned (requires capacity commitment)
4. Click **"Save"**
5. Wait 2-5 minutes

**Button 3: "Request model access"**
1. Click **"Request model access"**
2. Select **Claude Sonnet 4.5**
3. Accept terms if prompted
4. Submit request
5. Wait for approval (usually instant for Anthropic models)

---

#### Option C: If Model Not Listed

**This means the model might not be available in your region or account.**

1. Check if you're in the correct region (top right: **us-east-1**)
2. Try selecting a different region that supports the model:
   - us-east-1 (N. Virginia) ✅
   - us-west-2 (Oregon) ✅
   - eu-central-1 (Frankfurt) ✅
3. If still not available, contact AWS Support

---

### Step 4: Verify API Access is Enabled

After enabling access, verify it works:

**Method 1: AWS CLI Test**

```bash
# Test direct model invocation
aws bedrock-runtime invoke-model \
  --model-id us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --region us-east-1 \
  --body '{"anthropic_version":"bedrock-2023-05-31","max_tokens":20,"messages":[{"role":"user","content":"Say hello"}]}' \
  /tmp/response.json

# Check response
cat /tmp/response.json
```

**Expected Output:**
```json
{
  "id": "msg_...",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Hello! How can I help you today?"
    }
  ],
  ...
}
```

**If you get AccessDeniedException:** Wait a few more minutes or proceed to troubleshooting.

---

**Method 2: Python Test**

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
python3 test_agent.py
```

**Expected Output:**
```
================================================================================
BEDROCK MULTI-AGENT COLLABORATION TEST
================================================================================

Supervisor Agent ID: 5VTIWONUMO
...

Test 1: Chitchat (Greeting)
User Input: Hello! How are you?
Agent: Hello! I'm doing great, thank you for asking!...
✅ Test 1 completed
```

**If still fails:** See troubleshooting below.

---

### Step 5: Troubleshooting

#### Issue 1: Still Getting AccessDenied After Enabling

**Possible Causes:**
1. **Propagation delay** - Wait 5-10 minutes
2. **Cache issue** - Try a different AWS CLI profile
3. **Regional mismatch** - Ensure model access is in **us-east-1**
4. **Account limits** - Check AWS Service Quotas

**Solutions:**

**A. Check Service Quotas**
```bash
# Check Bedrock quotas
aws service-quotas list-service-quotas \
  --service-code bedrock \
  --region us-east-1 | grep -A 5 "On-demand"
```

**B. Verify Region**
```bash
# Your current region
aws configure get region

# Should be: us-east-1
```

**C. Clear AWS CLI Cache**
```bash
# Remove cached credentials
rm -rf ~/.aws/cli/cache/

# Test again
aws bedrock-runtime invoke-model ...
```

---

#### Issue 2: Model Access Page Shows Different UI

AWS updates their console frequently. You might see:

**Version A: Tile/Card View**
- Models shown as cards/tiles
- Click on the Claude card
- Look for "Request access" or "Manage access" button

**Version B: Table View**
- Models in a table with columns
- Action buttons in the rightmost column
- Click the action button for Claude Sonnet 4.5

**Version C: Grouped by Provider**
- Models grouped under "Anthropic", "AI21", etc.
- Expand "Anthropic" section
- Find Claude Sonnet 4.5

---

#### Issue 3: "Manage Model Access" Button Grayed Out

**This means:** You don't have IAM permissions to modify model access.

**Solution:** Ask your AWS administrator to either:

**Option A: Grant you permissions**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:PutFoundationModelEntitlement",
        "bedrock:GetFoundationModelAvailability",
        "bedrock:ListFoundationModels"
      ],
      "Resource": "*"
    }
  ]
}
```

**Option B: They enable it for you**
- Share this guide with them
- They can enable API access on your behalf

---

#### Issue 4: Cross-Region Inference Only

If status shows **"Cross-region inference: Access granted"** but API still fails:

**The Issue:** You have access to the cross-region profile but not the direct model.

**Solution A: Use Cross-Region Profile ARN**

Check what inference profiles you have access to:
```bash
aws bedrock list-inference-profiles --region us-east-1
```

Look for profiles with "ACTIVE" status that include Claude Sonnet 4.5.

**Solution B: Request Direct Model Access**

1. Go back to Model Access page
2. Look for a separate entry for the **base model** (not just cross-region)
3. Request access to the base model specifically

---

### Step 6: Update Configuration (If Needed)

If you had to use a different model or inference profile, update your configuration:

**Edit terraform.tfvars:**
```bash
cd infrastructure/terraform
nano terraform.tfvars
```

**Update the foundation_model line:**
```hcl
# If you're using a different inference profile
foundation_model = "arn:aws:bedrock:us-east-1:YOUR_ACCOUNT:inference-profile/PROFILE_ID"

# Or just the profile ID
foundation_model = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
```

**Apply changes:**
```bash
terraform apply
aws bedrock-agent prepare-agent --agent-id 5VTIWONUMO --region us-east-1
```

---

## 🎯 Quick Reference Checklist

Use this to verify you've completed all steps:

- [ ] Opened Bedrock Model Access page
- [ ] Found Claude Sonnet 4.5 in the list
- [ ] Checked current access status
- [ ] Clicked "Manage model access" or similar
- [ ] Enabled API/On-demand access
- [ ] Saved changes
- [ ] Waited 5 minutes for propagation
- [ ] Tested with AWS CLI
- [ ] Tested with Python script
- [ ] API access working! 🎉

---

## 📸 What to Look For (Visual Guide)

### Model Access Page Should Look Like:

```
╔════════════════════════════════════════════════════════════════╗
║  Amazon Bedrock > Model access                                 ║
║                                                                 ║
║  [Manage model access]  [Request model access]                ║
║                                                                 ║
║  ┌────────────────────────────────────────────────────────┐   ║
║  │ Provider: Anthropic                                     │   ║
║  │                                                          │   ║
║  │ • Claude 3.5 Sonnet v2        ✅ Access granted        │   ║
║  │ • Claude Sonnet 4             ✅ Access granted        │   ║
║  │ • Claude Sonnet 4.5           ⚠️  Console only         │ ← THIS ONE
║  │                                                          │   ║
║  └────────────────────────────────────────────────────────┘   ║
╚════════════════════════════════════════════════════════════════╝
```

---

## 🆘 Still Not Working?

### Option 1: Use Console Testing (Workaround)

Console access works fine for Phase 1 testing:

```
https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents
→ scheduling-agent-supervisor
→ Test button
```

### Option 2: Contact AWS Support

If you need API access and can't enable it:

1. Go to AWS Support Center
2. Create a case: **"Technical Support"**
3. Service: **"Amazon Bedrock"**
4. Category: **"Model Access"**
5. Description:
   ```
   I have console access to Claude Sonnet 4.5 but API invocation fails with:
   "AccessDeniedException: You don't have access to the model with the specified model ID"

   Model ID: us.anthropic.claude-sonnet-4-5-20250929-v1:0
   Region: us-east-1
   Account: YOUR_ACCOUNT_ID

   Please enable API access for this model.
   ```

### Option 3: Use Different Model

If Claude Sonnet 4.5 is problematic, try an older model:

**Claude 3.5 Sonnet v2:**
```hcl
foundation_model = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
```

Check access:
```bash
aws bedrock list-foundation-models --region us-east-1 --by-provider anthropic
```

---

## 📊 Summary

| Access Type | What It Enables | How to Get It |
|-------------|-----------------|---------------|
| **Console access** | Test in AWS Console UI | Model access page → Check box |
| **API access** | Programmatic invocation (Python, CLI) | Model access page → Enable on-demand |
| **Cross-region** | Use across multiple regions | Automatically included |
| **Provisioned** | Guaranteed capacity | Separate purchase required |

**For our use case, you need:** ✅ Console access + ✅ API access (on-demand)

---

## ✅ Success Indicators

You'll know API access is working when:

1. **CLI test succeeds:**
   ```bash
   aws bedrock-runtime invoke-model ...
   # Returns: {"content":[{"text":"Hello!..."}]}
   ```

2. **Python test succeeds:**
   ```bash
   python3 test_agent.py
   # Returns: Agent responses without AccessDeniedException
   ```

3. **Interactive script works:**
   ```bash
   python3 test_agents_interactive.py
   # Choose option 2 (Interactive mode)
   # Type "Hello" - should get response
   ```

---

**Last Updated:** October 13, 2025
**Issue:** API invocation fails with AccessDeniedException
**Solution:** Enable on-demand/API access in Bedrock Model Access page
