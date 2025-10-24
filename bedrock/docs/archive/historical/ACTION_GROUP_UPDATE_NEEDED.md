# Action Group Schema Update Required

**Date:** 2025-10-17
**Reason:** Removed unnecessary `client_id` parameters that were causing agents to ask for information they don't need

---

## ✅ What Was Fixed

### Information Actions Schema

**Removed `client_id` from these actions:**

1. **`get-project-details`**
   - Before: Required `project_id`, `customer_id` + optional `client_id`
   - After: Required `project_id`, `customer_id` only

2. **`get-appointment-status`**
   - Before: Required `project_id` + optional `customer_id`, `client_id`
   - After: Required `project_id` only

3. **`get-working-hours`**
   - Before: Required `client_id`
   - After: No required parameters (completely optional)

4. **`get-weather`**
   - Before: Required `location` + optional `client_id`
   - After: Required `location` only

---

## 🔧 Manual Update Required

### Information Agent (C9ANXRIO8Y)

1. **Go to AWS Console:**
   ```
   https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/C9ANXRIO8Y
   ```

2. **Edit Action Group:**
   - Click on `information_actions` action group
   - Click **"Edit"** button

3. **Update OpenAPI Schema:**
   - Copy entire content from: `bedrock/lambda/schemas/information-actions-schema.json`
   - Paste into schema editor
   - Click **"Validate"**

4. **Save and Prepare:**
   - Click **"Save"**
   - Click **"Prepare"** button at top of agent page
   - Wait for status to return to `PREPARED`

---

## ✅ Lambda Already Updated

The Lambda function has already been updated to handle optional parameters:

```bash
# Verify Lambda update
aws lambda get-function \
  --function-name scheduling-agent-information-actions \
  --region us-east-1 \
  --query 'Configuration.LastModified'
```

---

## 🧪 Test Cases After Update

### Test 1: Get Project Details (with customer_id)
```
Tell me about project PROJECT001 for customer CUST001
```

**Expected:** Should work without asking for `client_id`

### Test 2: Get Appointment Status (no customer_id needed)
```
What's the status of the appointment for project PROJECT001?
```

**Expected:** Should work with just project_id

### Test 3: Get Working Hours (no parameters needed)
```
What are your business hours?
```

**Expected:** Should return default business hours without asking for anything

### Test 4: Get Weather (just location)
```
What's the weather in Tampa?
```

**Expected:** Should work without asking for `client_id`

---

## 📝 Why This Change?

**Problem:**
- Agents were asking for `client_id` even when it's not needed
- `client_id` is a business/company identifier (e.g., 09PF05VD)
- `customer_id` is individual customer identifier (e.g., CUST001)
- Mock mode doesn't need `client_id` at all

**Solution:**
- Removed `client_id` from all Information actions
- Made `get-working-hours` completely optional (returns default hours)
- Simplified parameter requirements to minimum needed

**Result:**
- More natural conversations
- Less back-and-forth asking for parameters
- Better user experience

---

## 🔄 Files Changed

1. **Schema:** `bedrock/lambda/schemas/information-actions-schema.json`
   - Removed `client_id` from all 4 actions
   - Updated descriptions

2. **Lambda:** `bedrock/lambda/information-actions/handler.py`
   - Updated `get_working_hours` to provide default hours
   - Already handles optional parameters correctly

3. **Lambda Deployed:** ✅ `scheduling-agent-information-actions`
   - Updated: 2025-10-17
   - Status: Active

---

## ⚠️ Action Required

**You must manually update the action group schema in AWS Console as described above.**

The Lambda is already updated, but Bedrock won't use the new behavior until you update the action group schema.

---

**After updating, test all 4 actions to verify they work without unnecessary parameter requests.**
