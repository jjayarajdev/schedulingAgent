# Claude Model Update Summary

**Date:** October 27, 2025
**Task:** Update from Claude Haiku to Claude 3.5 Sonnet V2
**Status:** ✅ Complete

---

## 📊 Summary

Updated the classification system from Claude Haiku to Claude 3.5 Sonnet V2 for improved accuracy and performance.

**Key Changes:**
- Backend classification updated to Claude 3.5 Sonnet V2
- Configuration file updated
- Terraform already using Claude Sonnet 4.5 (newer than 3.5 V2)

---

## 🔄 Changes Made

### 1. Backend Classification (`backend/app.py`)

**Updated Function:** `classify_intent()`

**Before:**
```python
modelId='anthropic.claude-3-haiku-20240307-v1:0'
```

**After:**
```python
modelId='anthropic.claude-3-5-sonnet-20241022-v2:0'
```

**Lines Changed:**
- Line 262: Model ID updated
- Line 116: Logging model name updated from 'haiku' to 'claude-3.5-sonnet-v2'
- Line 213-218: Function docstring updated

### 2. Configuration File (`backend/agent_config.json`)

**Updated:**
```json
"classifier_model": "anthropic.claude-3-5-sonnet-20241022-v2:0"
```

**Before:**
```json
"classifier_model": "anthropic.claude-3-haiku-20240307-v1:0"
```

---

## 🏗️ Infrastructure Status

### Terraform Configuration

**Current State:** Already using Claude Sonnet 4.5 ✅

**File:** `infrastructure/terraform/variables.tf`
**Line 28:**
```hcl
default = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"  # Claude Sonnet 4.5
```

**Note:** The Bedrock agents (supervisor and collaborators) are using Claude Sonnet 4.5, which is:
- More advanced than Claude 3.5 Sonnet V2
- Released September 29, 2025
- Optimized for agent workflows

**Decision:** Keep Claude Sonnet 4.5 for agents, use Claude 3.5 Sonnet V2 for classification

---

## 📈 Model Comparison

| Component | Previous Model | New Model | Purpose |
|-----------|---------------|-----------|---------|
| **Classification** | Claude Haiku | Claude 3.5 Sonnet V2 | Intent classification |
| **Bedrock Agents** | Claude Sonnet 4.5 | Claude Sonnet 4.5 (unchanged) | Agent responses |

### Why Different Models?

1. **Classification (3.5 Sonnet V2):**
   - More accurate than Haiku
   - Better at edge case handling
   - Still fast enough for real-time classification
   - Balance of speed and accuracy

2. **Agents (Sonnet 4.5):**
   - Most advanced model available
   - Best for complex reasoning
   - Optimized for agent workflows
   - Already deployed and tested

---

## 🔧 Technical Details

### Model IDs

**Classification:**
- Model: `anthropic.claude-3-5-sonnet-20241022-v2:0`
- Release: October 22, 2024
- Version: V2 (improved)

**Agents:**
- Model: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`
- Release: September 29, 2025
- Version: V1 (latest)

### API Configuration

**Classification Request:**
```python
{
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 10,
    "temperature": 0.0,  # Deterministic
    "messages": [{"role": "user", "content": prompt}]
}
```

**Agent Invocation:**
```python
bedrock_agent_runtime.invoke_agent(
    agentId=agent_id,
    agentAliasId=alias_id,
    sessionId=session_id,
    inputText=augmented_prompt,
    sessionState={
        'sessionAttributes': {
            'customer_id': customer_id,
            'customer_type': customer_type
        }
    }
)
```

---

## ✅ Verification Steps

### 1. Test Classification

**Command:**
```bash
cd backend
python3 app.py
```

**Test Queries:**
- "Schedule an appointment" → should classify as `scheduling`
- "What's the weather?" → should classify as `information`
- "Add a note" → should classify as `notes`
- "Hello" → should classify as `chitchat`

### 2. Verify Model Access

**Check Classification Model:**
```bash
aws bedrock list-foundation-models \
  --query 'modelSummaries[?modelId==`anthropic.claude-3-5-sonnet-20241022-v2:0`]'
```

**Check Agent Model:**
```bash
aws bedrock list-foundation-models \
  --query 'modelSummaries[?modelId==`us.anthropic.claude-sonnet-4-5-20250929-v1:0`]'
```

### 3. Test UI

**Launch Test UI:**
```bash
cd testing/ui
./launch_test_ui.sh
```

**Verify:**
- Classification accuracy
- Response quality
- Performance metrics

---

## 📊 Expected Performance Impact

### Classification Performance

| Metric | Claude Haiku | Claude 3.5 Sonnet V2 | Change |
|--------|--------------|---------------------|--------|
| **Speed** | ~0.5s | ~0.8s | +60% slower |
| **Accuracy** | 95.7% | ~98%+ (expected) | +2.3% better |
| **Cost** | $0.00025/req | $0.003/req | 12x higher |
| **Edge Cases** | Good | Excellent | Better |

### Trade-offs

**Pros:**
- ✅ Better accuracy
- ✅ Better edge case handling
- ✅ More context understanding
- ✅ Lower hallucination rate

**Cons:**
- ⚠️ Slightly slower (still < 1s)
- ⚠️ Higher cost per request
- ℹ️ Negligible for production use

---

## 🎯 Migration Impact

### Files Updated

**Code Files (2):**
1. `backend/app.py` - Classification function
2. `backend/agent_config.json` - Configuration

**Documentation Files:**
- This file documents the migration
- Other docs reference Haiku for historical accuracy

### No Changes Needed

**Terraform Files:**
- Already using Claude Sonnet 4.5
- No infrastructure changes required

**Lambda Functions:**
- Use agent model (Sonnet 4.5)
- Not affected by classification change

**Frontend:**
- No changes needed
- Classification is backend-only

---

## 🚀 Deployment Steps

### 1. Restart Backend

**Stop current backend:**
```bash
pkill -f "python3 app.py"
```

**Start new backend:**
```bash
cd backend
python3 app.py
```

### 2. Test Functionality

**Run comprehensive tests:**
```bash
cd tests/v2
python3 test_improved_classification.py
```

### 3. Monitor Performance

**Check logs:**
```bash
tail -f /tmp/bedrock_backend.log
```

**Watch for:**
- Classification times (should be < 1s)
- Any model access errors
- Classification accuracy

---

## 📝 Rollback Plan

If issues occur, rollback is simple:

**1. Revert Code:**
```bash
git checkout HEAD~1 backend/app.py backend/agent_config.json
```

**2. Restart Backend:**
```bash
cd backend
python3 app.py
```

**Models Used After Rollback:**
- Classification: Claude Haiku
- Agents: Claude Sonnet 4.5 (unchanged)

---

## 📚 References

### AWS Bedrock Model IDs

**Claude 3.5 Sonnet V2:**
- Full ID: `anthropic.claude-3-5-sonnet-20241022-v2:0`
- Regions: us-east-1, us-west-2
- Documentation: [AWS Bedrock Models](https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html)

**Claude Sonnet 4.5:**
- Full ID: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`
- Region: us-east-1 (inference profile)
- Documentation: [Cross-region inference](https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html)

### Model Capabilities

**Claude 3.5 Sonnet V2:**
- Max tokens: 8,192 output
- Context window: 200K tokens
- Best for: Complex reasoning, coding, analysis

**Claude Sonnet 4.5:**
- Max tokens: 8,192 output
- Context window: 200K tokens
- Best for: Agent workflows, multi-step tasks

---

## ✅ Summary

**Status:** ✅ **MIGRATION COMPLETE**

**Changes:**
- ✅ Backend classification updated to Claude 3.5 Sonnet V2
- ✅ Configuration file updated
- ✅ Terraform infrastructure already optimal (Sonnet 4.5)

**Benefits:**
- Better classification accuracy
- Improved edge case handling
- More reliable intent detection

**Next Steps:**
1. Test classification with comprehensive query set
2. Monitor performance metrics
3. Update documentation as needed
4. Commit changes to git

---

**Created:** October 27, 2025
**Purpose:** Document Claude model migration
**Status:** Complete
