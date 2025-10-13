# Bulk Operations Deployment Status

**Date:** October 13, 2025
**Status:** ✅ Partially Complete - Manual Steps Required
**Deployed by:** Automated Script

---

## Deployment Summary

### ✅ Completed Steps

#### 1. Lambda Function Deployed
- **Function Name:** `scheduling-agent-bulk-ops-dev`
- **Runtime:** Python 3.11
- **Memory:** 1024 MB
- **Timeout:** 60 seconds
- **Package Size:** 17.3 MB
- **ARN:** `arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-bulk-ops-dev`
- **Status:** Active ✅

**Environment Variables:**
```
ENVIRONMENT=dev
DYNAMODB_TABLE=scheduling-agent-bulk-ops-tracking-dev
MAX_PROJECTS=50
PF360_API_URL=https://api.pf360.com
```

#### 2. DynamoDB Table Created
- **Table Name:** `scheduling-agent-bulk-ops-tracking-dev`
- **Key:** `operation_id` (String, HASH)
- **Billing:** PAY_PER_REQUEST
- **TTL:** Enabled on `ttl` attribute
- **Status:** Active ✅

#### 3. S3 Artifacts Uploaded
- **Bucket:** `scheduling-agent-artifacts-dev`
- **Schema Location:** `s3://scheduling-agent-artifacts-dev/openapi-schemas/coordinator_actions.json`
- **Size:** 14.1 KB
- **Status:** Uploaded ✅

#### 4. IAM Roles Configured
- **Role Name:** `scheduling-agent-bulk-ops-lambda-role`
- **ARN:** `arn:aws:iam::618048437522:role/scheduling-agent-bulk-ops-lambda-role`
- **Policies Attached:**
  - AWSLambdaBasicExecutionRole (AWS Managed)
  - scheduling-agent-bulk-ops-policy (Custom)
- **Permissions:**
  - DynamoDB: PutItem, GetItem, Query, UpdateItem on `scheduling-agent-bulk-ops-*`
  - Secrets Manager: GetSecretValue on `pf360-api-*`
  - CloudWatch: Logs
  - Bedrock: InvokeFunction permission added ✅

#### 5. Coordinator Collaborator Agent Created
- **Agent Name:** `scheduling-agent-coordinator-collaborator`
- **Agent ID:** `QHUR9JP4GT`
- **Model:** Claude Sonnet 4.5 (anthropic.claude-sonnet-4-5-v1:0)
- **Status:** NOT_PREPARED ⚠️ (Needs action group)
- **ARN:** `arn:aws:bedrock:us-east-1:618048437522:agent/QHUR9JP4GT`

---

## ⚠️ Manual Steps Required

The following steps must be completed manually via AWS Console due to OpenAPI schema validation:

### Step 1: Add Action Group to Coordinator Agent

**Via AWS Console:**

1. Navigate to Amazon Bedrock → Agents → `scheduling-agent-coordinator-collaborator`

2. Click the **"Working draft"** tab

3. Scroll down to **"Action groups"** section

4. Click **"Add"**

5. Configure the action group:
   - **Action group name:** `coordinator_operations`
   - **Action group type:** Define with API schemas
   - **Description:** Bulk operations for coordinators - route optimization, bulk assignments, validation, conflict detection

6. **Action group invocation:**
   - Select: **Select an existing Lambda function**
   - Lambda function: `scheduling-agent-bulk-ops-dev`

7. **Action group schema:**
   - **Define via:** In-line schema editor
   - Click **"Upload"** and select:
     - File: `/Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/openapi_schemas/coordinator_actions.json`
   - OR use S3:
     - S3 URI: `s3://scheduling-agent-artifacts-dev/openapi-schemas/coordinator_actions.json`

8. Click **"Add"**

9. Click **"Prepare"** at the top of the page

10. Wait for agent status to become **"PREPARED"** (takes 1-2 minutes)

### Step 2: Create Agent Alias

1. Still in the coordinator agent page, go to the **"Aliases"** tab

2. Click **"Create alias"**

3. Configure:
   - **Alias name:** `prod`
   - **Description:** Production alias for bulk operations
   - **Version:** Select the prepared version (should be version 1)

4. Click **"Create alias"**

5. **Note the Alias ID** - you'll need it for the next step

### Step 3: Associate with Supervisor Agent

**Option A: Via AWS CLI**

```bash
# Get the coordinator agent alias ID from Step 2
COORDINATOR_ALIAS_ID="<alias-id-from-step-2>"

# Associate with supervisor
aws bedrock-agent associate-agent-collaborator \
  --agent-id 5VTIWONUMO \
  --agent-version DRAFT \
  --collaborator-name "coordinator_collaborator" \
  --agent-descriptor agentId=QHUR9JP4GT,agentAliasId=$COORDINATOR_ALIAS_ID \
  --collaboration-instruction "Route coordinator bulk operations (route optimization, bulk assignment, validation for multiple projects) to this collaborator. Examples: 'Optimize route for projects X, Y, Z', 'Assign projects 15001-15020 to Team A', 'Validate all projects in queue'." \
  --region us-east-1
```

**Option B: Via AWS Console**

1. Navigate to Bedrock → Agents → `scheduling-agent-supervisor` (ID: 5VTIWONUMO)

2. Go to **"Working draft"** tab

3. Scroll to **"Agent collaborators"** section

4. Click **"Add collaborator"**

5. Configure:
   - **Collaborator name:** `coordinator_collaborator`
   - **Agent:** Select `scheduling-agent-coordinator-collaborator`
   - **Agent alias:** Select the `prod` alias created in Step 2
   - **Collaboration instruction:**
     ```
     Route coordinator bulk operations (route optimization, bulk assignment, validation for multiple projects) to this collaborator.

     Examples:
     - "Optimize route for projects X, Y, Z"
     - "Assign projects 15001-15020 to Team A"
     - "Validate all projects in queue"
     ```

6. Click **"Add"**

7. Click **"Prepare"** to update the supervisor

### Step 4: Test the Integration

**Test via AWS Console:**

1. Navigate to the Supervisor Agent page

2. Click **"Test"** in the top right

3. Try these test messages:

**Test 1: Route Optimization**
```
Optimize route for projects 12345, 12347, 12350
```

Expected: Agent routes to coordinator_collaborator, calls optimize_route action

**Test 2: Bulk Assignment**
```
Assign projects 15001, 15002, 15003 to Team A for next week
```

Expected: Agent routes to coordinator_collaborator, calls bulk_assign_teams action

**Test 3: Validation**
```
Validate projects 10001, 10002, 10003 for scheduling
```

Expected: Agent routes to coordinator_collaborator, calls validate_projects action

---

## Deployment Architecture

```
┌────────────────────────────────────────────────────────────┐
│  Coordinator → Chat/API → Bedrock Supervisor (5VTIWONUMO) │
└───────────────────────────────┬────────────────────────────┘
                                ↓
┌────────────────────────────────────────────────────────────┐
│  Coordinator Collaborator Agent (QHUR9JP4GT)               │
│  - Status: NOT_PREPARED (needs action group)               │
└───────────────────────────────┬────────────────────────────┘
                                ↓
┌────────────────────────────────────────────────────────────┐
│  Action Group: coordinator_operations                      │
│  - ⚠️ NEEDS TO BE ADDED MANUALLY                           │
└───────────────────────────────┬────────────────────────────┘
                                ↓
┌────────────────────────────────────────────────────────────┐
│  Lambda: scheduling-agent-bulk-ops-dev                     │
│  - Runtime: Python 3.11                                    │
│  - Status: Active ✅                                        │
└───────────────────────────────┬────────────────────────────┘
                                ↓
                    ┌───────────┴───────────┐
                    ↓                       ↓
        ┌─────────────────────┐ ┌──────────────────────────┐
        │  DynamoDB Table      │ │  PF360 API               │
        │  (tracking)          │ │  (batch operations)      │
        │  Status: Active ✅   │ │  Status: Not configured  │
        └─────────────────────┘ └──────────────────────────┘
```

---

## Configuration Details

### Lambda Function Code Location
```
/Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/lambda/bulk-operations/
├── handler.py (627 lines)
├── lambda.zip (17.3 MB)
├── requirements.txt
└── README.md
```

### OpenAPI Schema Location
```
/Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/openapi_schemas/coordinator_actions.json
```

**Operations Defined:**
1. `/optimize_route` - Route optimization (2-50 projects)
2. `/bulk_assign` - Bulk team assignments (1-100 projects)
3. `/validate_projects` - Project validation (1-100 projects)
4. `/detect_conflicts` - Conflict detection

### Coordinator Agent Instructions

The agent has been created with the following instructions:

```
You are a specialized Bedrock Agent collaborator that handles bulk scheduling operations for field coordinators.

Your role is to process bulk requests for:
1. Route optimization - Optimize routes for 2-50 projects to minimize travel time
2. Bulk team assignments - Assign multiple projects (1-100) to teams with conflict detection
3. Project validation - Validate permits, measurements, and access for multiple projects
4. Conflict detection - Identify scheduling conflicts across projects and teams

When a coordinator requests bulk operations:
- Identify the operation type (route optimization, bulk assignment, validation, or conflict detection)
- Extract project IDs, date ranges, teams, and other parameters
- Call the appropriate action group with the extracted parameters
- Present results in a clear, actionable format

Examples of requests you should handle:
- "Optimize route for projects 12345, 12347, 12350"
- "Assign projects 15001-15020 to Team A for next week"
- "Validate all projects in queue for permit compliance"
- "Check for conflicts with Team B's schedule"

Always provide:
- Clear summary of what was done
- Key metrics (time saved, conflicts found, assignments made)
- Actionable next steps if issues are found
- Warnings for any projects that couldn't be processed

Be concise, professional, and focus on helping coordinators make efficient scheduling decisions.
```

---

## Troubleshooting

### Issue: Agent not routing to coordinator collaborator

**Check:**
1. Supervisor agent has coordinator_collaborator associated
2. Collaboration instruction is clear and includes examples
3. Both supervisor and collaborator are in PREPARED state

### Issue: Action group invocation fails

**Check:**
1. Lambda function has Bedrock invoke permission (✅ Already added)
2. OpenAPI schema is valid and uploaded
3. Lambda function environment variables are correct

### Issue: Lambda timeout or errors

**Check CloudWatch Logs:**
```bash
aws logs tail /aws/lambda/scheduling-agent-bulk-ops-dev --follow
```

**Common Issues:**
- PF360 API credentials not configured
- DynamoDB table permissions
- Network timeout (increase Lambda timeout if needed)

---

## Next Steps After Manual Configuration

Once manual steps are complete:

1. **Test all 4 operations** via AWS Console test interface

2. **Monitor CloudWatch Logs:**
   ```bash
   aws logs tail /aws/lambda/scheduling-agent-bulk-ops-dev --follow
   ```

3. **Track DynamoDB operations:**
   ```bash
   aws dynamodb scan --table-name scheduling-agent-bulk-ops-tracking-dev --region us-east-1
   ```

4. **Update supervisor instructions** to include bulk operations examples

5. **Train coordinators** on new bulk operations capabilities

6. **Deploy to production** once validated in dev

---

## Rollback Instructions

If needed, rollback with:

```bash
# Delete Lambda function
aws lambda delete-function --function-name scheduling-agent-bulk-ops-dev --region us-east-1

# Delete DynamoDB table
aws dynamodb delete-table --table-name scheduling-agent-bulk-ops-tracking-dev --region us-east-1

# Delete coordinator agent
aws bedrock-agent delete-agent --agent-id QHUR9JP4GT --region us-east-1

# Delete IAM resources
aws iam delete-role-policy --role-name scheduling-agent-bulk-ops-lambda-role --policy-name scheduling-agent-bulk-ops-policy
aws iam delete-role --role-name scheduling-agent-bulk-ops-lambda-role

# Remove S3 objects
aws s3 rm s3://scheduling-agent-artifacts-dev/openapi-schemas/coordinator_actions.json
```

---

## Cost Estimates

**Monthly costs for 1000 bulk operations:**

| Service | Usage | Cost |
|---------|-------|------|
| Lambda | 1000 invocations × 10s × 1GB | ~$0.40 |
| DynamoDB | Pay-per-request | ~$0.10 |
| Bedrock Agent | Included in model costs | ~$0.50 |
| **Total** | | **~$1.00/month** |

(Excluding PF360 API costs and external services)

---

## Status Summary

✅ **Lambda Function:** Deployed and Active
✅ **DynamoDB Table:** Created and Active
✅ **S3 Artifacts:** Uploaded
✅ **IAM Roles:** Configured
✅ **Coordinator Agent:** Created (NOT_PREPARED)
⚠️ **Action Group:** Needs manual addition via AWS Console
⚠️ **Supervisor Association:** Pending after action group
⚠️ **Testing:** Pending after association

**Estimated time to complete manual steps:** 10-15 minutes

---

**Last Updated:** October 13, 2025, 8:23 PM
**Deployed By:** Automated Deployment Script
**Next Action:** Complete manual steps in AWS Console
