# AWS Bedrock Agent Action Groups Not Invoking Lambda Functions

**Case Priority:** High
**Service:** Amazon Bedrock - Agents
**Region:** us-east-1
**Date:** October 20, 2025
**Account ID:** 618048437522

---

## Issue Summary

Bedrock agents with configured action groups are **not invoking Lambda functions**. The agent correctly identifies the need to call a function and includes the function call in its response, but **outputs the function call as XML text** instead of actually executing it.

---

## Problem Description

### Observed Behavior

When a user asks "Show me all my projects", the agent:

1. ✅ **Correctly receives the request**
2. ✅ **Identifies the appropriate action group** (`list_projects`)
3. ❌ **Outputs function call as TEXT instead of executing it**

**Agent Response:**
```xml
I'd be happy to show you your available projects! Let me retrieve that information for you.

<function_calls>
<invoke>
<tool_name>list_projects</tool_name>
<parameters>
<customer_id>$SESSION_ATTRIBUTES.customer_id$</customer_id>
<client_id>$SESSION_ATTRIBUTES.client_id$</client_id>
</parameters>
</invoke>
</function_calls>
```

**Expected Behavior:**
- Agent should invoke the Lambda function
- Lambda should return project data
- Agent should present the results to the user

**Actual Behavior:**
- Lambda function is **never invoked** (confirmed via CloudWatch logs - zero invocations)
- Function call syntax is returned as text to the user
- No `returnControl` event is emitted (based on similar reports)

---

## Environment Details

### Agent Configuration

**Agent ID:** YDCJTJBSLO
**Agent Alias ID:** VB7IU4DNIZ
**Agent Name:** scheduling-agent-scheduling
**Agent Status:** PREPARED
**Foundation Model:** `us.anthropic.claude-sonnet-4-5-20250929-v1:0`
**Region:** us-east-1

### Action Group Configuration

**Action Group ID:** 9ZAGKRPDVI
**Action Group Name:** scheduling-actions
**Action Group State:** ENABLED
**Description:** Actions for appointment scheduling and availability

**Lambda Function:**
- **ARN:** `arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-scheduling-actions`
- **Status:** Active
- **Runtime:** Python 3.11

**OpenAPI Schema Location:**
- **S3 Bucket:** scheduling-agent-schemas-dev-618048437522
- **S3 Key:** scheduling_actions.json
- **Schema Type:** OpenAPI 3.0.0

### Lambda Function Verification

Lambda function works perfectly when invoked directly:

```bash
# Direct Lambda invocation test
aws lambda invoke \
  --function-name scheduling-agent-scheduling-actions \
  --payload '{"actionGroup":"scheduling-actions","apiPath":"/list-projects","httpMethod":"POST"}' \
  output.json
```

**Result:** ✅ Success - Returns correct data:
```json
{
  "status": "success",
  "data": [
    {"project_id": "PROJ001", "project_name": "Kitchen Renovation", "customer_id": "CUST001", "status": "scheduled"},
    {"project_id": "PROJ002", "project_name": "Bathroom Remodel", "customer_id": "CUST001", "status": "in_progress"},
    {"project_id": "PROJ003", "project_name": "Exterior Painting", "customer_id": "CUST001", "status": "pending"}
  ]
}
```

**CloudWatch Logs:** Show successful invocation when called directly, but **ZERO invocations** when agent is used.

---

## Reproduction Steps

### Step 1: Agent Invocation Code

```python
import boto3
import json
import time

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

response = client.invoke_agent(
    agentId='YDCJTJBSLO',
    agentAliasId='VB7IU4DNIZ',
    sessionId=f'test-{int(time.time())}',
    inputText='Show me all my projects',
    sessionState={
        'sessionAttributes': {
            'customer_id': 'CUST001',
            'customer_type': 'B2C'
        }
    }
)

# Stream response
for event in response['completion']:
    if 'chunk' in event:
        chunk = event['chunk']
        if 'bytes' in chunk:
            print(chunk['bytes'].decode('utf-8'), end='')
```

### Step 2: Observed Output

```
I'd be happy to show you your available projects! Let me retrieve that information for you.

<function_calls>
<invoke>
<tool_name>list_projects</tool_name>
<parameters>
<customer_id>$SESSION_ATTRIBUTES.customer_id$</customer_id>
<client_id>$SESSION_ATTRIBUTES.client_id$</client_id>
</parameters>
</invoke>
</function_calls>
```

### Step 3: CloudWatch Verification

```bash
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions \
  --since 5m --region us-east-1 --format short
```

**Result:** No log entries (Lambda never invoked)

---

## Configuration Verification

### IAM Permissions

**Agent Service Role:** `arn:aws:iam::618048437522:role/scheduling-agent-scheduling-agent-role-dev`

**Permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockInvokeModel",
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel"],
      "Resource": ["arn:aws:bedrock:us-east-1::foundation-model/*"]
    },
    {
      "Sid": "BedrockRetrieveKnowledgeBase",
      "Effect": "Allow",
      "Action": ["bedrock:Retrieve"],
      "Resource": ["arn:aws:bedrock:us-east-1:618048437522:knowledge-base/*"]
    },
    {
      "Sid": "InvokeLambdaFunction",
      "Effect": "Allow",
      "Action": ["lambda:InvokeFunction"],
      "Resource": [
        "arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-*",
        "arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-*:*"
      ]
    }
  ]
}
```

**Lambda Resource Policy:**
```json
{
  "Sid": "AllowBedrock",
  "Effect": "Allow",
  "Principal": {"Service": "bedrock.amazonaws.com"},
  "Action": "lambda:InvokeFunction",
  "Resource": "arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-scheduling-actions",
  "Condition": {
    "ArnLike": {
      "AWS:SourceArn": "arn:aws:bedrock:us-east-1:618048437522:agent/*"
    }
  }
}
```

✅ **All permissions are correctly configured**

### OpenAPI Schema Sample

The action group uses a valid OpenAPI 3.0.0 schema:

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Scheduling Actions API",
    "version": "1.0.0"
  },
  "paths": {
    "/list-projects": {
      "post": {
        "summary": "List available projects for a customer",
        "operationId": "list_projects",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "customer_id": {"type": "string"},
                  "client_id": {"type": "string"}
                },
                "required": ["customer_id"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "List of available projects"
          }
        }
      }
    }
  }
}
```

✅ **Schema is valid and accessible in S3**

---

## Related AWS re:Post Issues

This issue has been reported by other customers:

### Issue 1: Tool Call Never Happens From Collaborator Agent
**URL:** https://repost.aws/questions/QU7glCtys3QW-nwvT1IHQlsA/potential-bug-aws-bedrock-inline-agent-collaboration-tool-call-never-happens-from-collaborator-agent

**Description:**
- "The action group is correctly identified in the trace but not actually executed when using collaboration"
- "There is no response back from the agent, with nothing in the trace suggesting the tool was ever called"
- "The tools logs (MCP server deployed in ECS) show no logs generated"

**Status:** Confirmed bug

### Issue 2: Multi-Agent Collaboration Routing
**URL:** https://repost.aws/questions/QUi0g3aKyBQ2iSEtcSrNYi8Q/potential-bug-amazon-multi-agent-collaboration-routing

**Description:** Routing issues in multi-agent collaboration scenarios

**Status:** Potential bug reported to AWS

---

## Additional Context

### Multi-Agent Collaboration Testing

We also tested with a supervisor-collaborator architecture and observed the same behavior:

**Supervisor Agent ID:** GUA4WQTCID
**Collaborators:** 4 specialist agents (scheduling, information, notes, chitchat)

**Findings:**
- ✅ Supervisor correctly routes to collaborators
- ✅ Collaborators receive requests
- ❌ Collaborators with action groups do not invoke Lambda functions
- ❌ Same XML output behavior observed

**Note:** We attempted to add action groups directly to the supervisor but received:
```
ValidationException: Failed to create OpenAPI 3 model from the JSON/YAML object
that you provided for action: supervisor-scheduling-actions
```

This suggests supervisors in SUPERVISOR mode cannot have action groups (which is expected/by design).

---

## Impact Assessment

**Severity:** High

**Business Impact:**
- Cannot build functional multi-agent systems with action groups
- Agent capabilities limited to conversational responses only
- Lambda functions cannot be invoked despite correct configuration
- Prevents production deployment of Bedrock Agents with external data sources

**Workaround Attempted:**
- Tried direct agent invocation (same issue)
- Tried re-preparing agents multiple times (same issue)
- Verified all permissions and configurations (all correct)
- Tested Lambda function directly (works perfectly)

**Conclusion:** This appears to be a platform-level bug in AWS Bedrock Agents

---

## Requested Actions

1. **Investigate why action groups are not invoking Lambda functions**
2. **Provide timeline for fix or workaround**
3. **Confirm if this is a known issue**
4. **Provide guidance on proper configuration if we're missing something**

---

## Supporting Evidence

### Terraform Configuration
All infrastructure is managed via Terraform. Configuration files available upon request.

### CloudWatch Log Groups
- `/aws/lambda/scheduling-agent-scheduling-actions` - Shows zero invocations from agent
- Direct Lambda test logs show successful execution

### Test Artifacts
- Agent invocation code (provided above)
- Lambda test payloads
- OpenAPI schemas
- IAM policy documents

---

## Contact Information

**AWS Account ID:** 618048437522
**Primary Region:** us-east-1
**Preferred Contact Method:** [Your email/phone]

---

## Additional Notes

- Agent was prepared multiple times to ensure latest configuration
- Issue persists across multiple test sessions
- Same behavior observed whether using agent alias or DRAFT version
- Issue affects all action groups, not just scheduling

**Last Updated:** October 20, 2025
