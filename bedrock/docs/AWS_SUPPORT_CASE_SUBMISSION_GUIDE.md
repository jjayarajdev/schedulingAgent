# AWS Support Case Submission Guide

## Quick Summary for AWS Support

**Issue:** Bedrock agents with action groups output function calls as XML text instead of executing Lambda functions

**Impact:** Unable to use action groups with agents - blocks production deployment

**Evidence:**
- ✅ Lambda works perfectly when invoked directly
- ❌ Agent outputs `<function_calls>` XML as text to users
- ❌ CloudWatch shows ZERO Lambda invocations from agents
- ❌ AWS Bedrock Agent APIs experiencing internal errors

---

## How to Submit

### 1. Open AWS Support Center

Go to: https://console.aws.amazon.com/support/home#/case/create

### 2. Case Details

**Service:** Amazon Bedrock
**Category:** Agents
**Severity:** Production system impaired
**Subject:** Bedrock Agent Action Groups Not Invoking Lambda Functions

### 3. Case Description

Copy the entire contents of `AWS_SUPPORT_CASE.md` into the description field.

### 4. Attach Supporting Files

Attach these files from your project:

1. **test_agent_action_groups.py** - Reproduction script
2. **agent_config.json** - Your multi-agent configuration
3. **lambda-test-payload.json** - Direct Lambda test payload that works

### 5. Environment Information

**AWS Account ID:** 618048437522
**Region:** us-east-1
**Agent ID:** YDCJTJBSLO
**Alias ID:** VB7IU4DNIZ
**Lambda Function:** scheduling-agent-scheduling-actions

### 6. Additional Context

When AWS responds, mention:

1. **This is a known issue** - Reference AWS re:Post:
   - https://repost.aws/questions/QU7glCtys3QW-nwvT1IHQlsA
   - https://repost.aws/questions/QUi0g3aKyBQ2iSEtcSrNYi8Q

2. **Multiple symptoms:**
   - Action groups don't work in multi-agent collaboration
   - Cannot add action groups to supervisor agents (ValidationException)
   - Agents output XML instead of executing functions
   - Bedrock Agent APIs experiencing AuthorizerConfigurationException

3. **Already attempted:**
   - Re-prepared agents multiple times
   - Verified all IAM permissions (correct)
   - Tested Lambda directly (works)
   - Validated OpenAPI schemas (valid)
   - Checked S3 bucket access (accessible)

4. **Request:**
   - Timeline for fix
   - Workaround if available
   - Confirmation if this is a platform limitation

---

## Expected AWS Questions

### Q: "Can you provide CloudTrail logs?"

**Answer:** Yes, CloudTrail logs show:
- Lambda function invocations from direct tests (successful)
- Agent invocation API calls (successful)
- No Lambda invocations triggered by agents (the bug)

### Q: "Have you checked agent permissions?"

**Answer:** Yes, verified:
- Agent role has `lambda:InvokeFunction` permission
- Lambda resource policy allows `bedrock.amazonaws.com`
- S3 bucket policy allows agent to read schemas
- All ARNs are correct

### Q: "Can you provide the OpenAPI schema?"

**Answer:** Schema is included in AWS_SUPPORT_CASE.md lines 227-263. It's valid OpenAPI 3.0.0.

### Q: "What happens when you invoke the agent?"

**Answer:** Agent correctly identifies the action group but outputs:
```xml
<function_calls>
<invoke>
<tool_name>list_projects</tool_name>
<parameters>
<customer_id>$SESSION_ATTRIBUTES.customer_id$</customer_id>
</parameters>
</invoke>
</function_calls>
```

This XML appears as TEXT in the response instead of being executed.

---

## What to Expect

1. **Initial Response:** 1-2 business days
2. **Investigation:** AWS may ask for additional logs/traces
3. **Resolution Options:**
   - Platform bug fix (timeline TBD)
   - Workaround (if available)
   - Confirmation of limitation

---

## Current Status

**AWS Bedrock Service Issues (as of submission):**
```
aws bedrock-agent get-agent --agent-id YDCJTJBSLO --region us-east-1

Error: AuthorizerConfigurationException (reached max retries: 2):
Internal server error
```

This suggests AWS Bedrock is experiencing service degradation, which may be related to or exacerbating the action group issue.

---

## Files Location

All supporting files are in:
```
/Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/
├── AWS_SUPPORT_CASE.md (main case document)
├── AWS_SUPPORT_CASE_SUBMISSION_GUIDE.md (this file)
├── test_agent_action_groups.py (test script)
├── agent_config.json (configuration)
└── /tmp/lambda-test-payload.json (test payload)
```

---

## After Submission

1. **Save case number** - You'll receive one after submission
2. **Monitor email** - AWS will respond via email
3. **Update your team** - Share case number with stakeholders
4. **Keep testing** - Continue testing to gather more evidence if needed

---

## Temporary Workaround (Already Implemented)

While waiting for AWS response, you've implemented custom intent-based routing in `frontend/backend/app.py`:

- LLM classifies user intent (scheduling/information/notes/chitchat)
- Backend routes directly to appropriate specialist agent
- Bypasses supervisor until AWS fixes the bug

**Current System Status:**
- ✅ Intent classification working
- ✅ Routing to correct agents
- ❌ Action groups still not invoking Lambda (core platform bug)

---

## Next Steps After AWS Fixes

When AWS resolves the issue:

1. Update `agent_config.json`:
   ```json
   "routing": {
     "use_supervisor": true
   }
   ```

2. Restart backend:
   ```bash
   cd frontend
   ./start.sh
   ```

3. Test with supervisor agent routing

---

**Good luck with the support case!**
