# Lambda Functions - Step-by-Step Deployment Guide

**Date:** October 17, 2025
**Purpose:** Detailed manual deployment guide for Lambda functions
**Time:** 1-2 hours

---

## 📋 Overview

This guide walks you through deploying the 3 Lambda functions for your Bedrock Multi-Agent system:

1. **scheduling-actions** - 6 actions (list_projects, get_available_dates, etc.)
2. **information-actions** - 4 actions (get_project_details, get_working_hours, etc.)
3. **notes-actions** - 2 actions (add_note, list_notes)

---

## 🎯 Two Deployment Options

### Option A: Automated Script (Recommended) ⚡

**Fastest:** One command deploys everything

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
./scripts/deploy_lambda_functions.sh
```

**Time:** 5-10 minutes
**What it does:**
- Creates IAM role
- Packages all 3 Lambda functions
- Deploys to AWS
- Grants Bedrock permissions
- Tests each function

**Then skip to Step 4 below (Update Bedrock Action Groups)**

---

### Option B: Manual Deployment (This Guide)

**For:** Learning, troubleshooting, custom configuration

Follow steps below for complete control over deployment.

---

## ✅ Prerequisites

Before starting, ensure you have:

- [ ] AWS CLI installed and configured
- [ ] AWS credentials with Lambda and IAM permissions
- [ ] Python 3.11 installed
- [ ] pip installed
- [ ] Access to your Bedrock Agents (AISPL account, ap-south-1 region)

**Verify AWS Access:**
```bash
aws sts get-caller-identity

# Should show:
# {
#     "UserId": "AIDAI...",
#     "Account": "YOUR_ACCOUNT_ID",
#     "Arn": "arn:aws:iam::YOUR_ACCOUNT_ID:user/yourname"
# }
```

---

## 🚀 Step 1: Create IAM Role for Lambda

### 1.1 Create Trust Policy

Lambda functions need an IAM role to execute. Create the trust policy first.

```bash
cat > /tmp/lambda-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
```

### 1.2 Create IAM Role

```bash
aws iam create-role \
  --role-name scheduling-agent-lambda-role \
  --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
  --description "Execution role for Bedrock scheduling agent Lambda functions"
```

**Expected Output:**
```json
{
    "Role": {
        "RoleName": "scheduling-agent-lambda-role",
        "Arn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/scheduling-agent-lambda-role",
        ...
    }
}
```

**Save the ARN** - you'll need it later!

### 1.3 Attach Policies to Role

Attach required policies for logging, DynamoDB, and Secrets Manager:

```bash
# Basic Lambda execution (CloudWatch Logs)
aws iam attach-role-policy \
  --role-name scheduling-agent-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# DynamoDB access (for session storage)
aws iam attach-role-policy \
  --role-name scheduling-agent-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

# Secrets Manager (for PF360 API keys)
aws iam attach-role-policy \
  --role-name scheduling-agent-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite
```

### 1.4 Wait for Role Propagation

IAM changes take time to propagate:

```bash
echo "Waiting 10 seconds for IAM role propagation..."
sleep 10
```

✅ **Checkpoint:** IAM role created and policies attached

---

## 📦 Step 2: Package Lambda Functions

Each Lambda function needs to be packaged with its dependencies.

### 2.1 Package scheduling-actions

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/lambda/scheduling-actions

# Create package directory
mkdir -p package

# Install dependencies
pip install -r requirements.txt -t package/

# Copy Lambda code
cp handler.py package/
cp config.py package/
cp mock_data.py package/

# Create ZIP
cd package
zip -r ../scheduling-actions.zip .
cd ..

# Verify ZIP size
ls -lh scheduling-actions.zip
# Should be ~1-5 MB
```

**Common Issues:**

**Issue:** `pip: command not found`
```bash
# Install pip first
python3 -m ensurepip --upgrade
```

**Issue:** Permission denied
```bash
# Use sudo or virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -t package/
```

### 2.2 Package information-actions

```bash
cd ../information-actions

mkdir -p package
pip install -r requirements.txt -t package/
cp handler.py config.py mock_data.py package/
cd package && zip -r ../information-actions.zip . && cd ..
```

### 2.3 Package notes-actions

```bash
cd ../notes-actions

mkdir -p package
pip install -r requirements.txt -t package/
cp handler.py config.py mock_data.py package/
cd package && zip -r ../notes-actions.zip . && cd ..
```

✅ **Checkpoint:** 3 ZIP files created (scheduling-actions.zip, information-actions.zip, notes-actions.zip)

---

## ☁️ Step 3: Deploy to AWS Lambda

### 3.1 Deploy scheduling-actions

Get your IAM role ARN first:

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/scheduling-agent-lambda-role"

echo "Role ARN: $ROLE_ARN"
```

Deploy the function:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/lambda/scheduling-actions

aws lambda create-function \
  --function-name scheduling-agent-scheduling-actions \
  --runtime python3.11 \
  --role $ROLE_ARN \
  --handler handler.lambda_handler \
  --zip-file fileb://scheduling-actions.zip \
  --timeout 30 \
  --memory-size 512 \
  --environment Variables={USE_MOCK_API=true,AWS_REGION=ap-south-1} \
  --region ap-south-1 \
  --description "Scheduling actions Lambda for Bedrock Agent"
```

**Expected Output:**
```json
{
    "FunctionName": "scheduling-agent-scheduling-actions",
    "FunctionArn": "arn:aws:lambda:ap-south-1:ACCOUNT_ID:function:scheduling-agent-scheduling-actions",
    "Runtime": "python3.11",
    "Handler": "handler.lambda_handler",
    ...
}
```

**Common Errors:**

**Error:** `InvalidParameterValueException: The role defined for the function cannot be assumed by Lambda`
- **Fix:** Wait longer (role propagation), then retry after 30 seconds

**Error:** `ResourceConflictException: Function already exists`
- **Fix:** Function already deployed! Update instead:
```bash
aws lambda update-function-code \
  --function-name scheduling-agent-scheduling-actions \
  --zip-file fileb://scheduling-actions.zip \
  --region ap-south-1
```

### 3.2 Test scheduling-actions

```bash
aws lambda invoke \
  --function-name scheduling-agent-scheduling-actions \
  --payload '{"action":"list_projects","parameters":{}}' \
  --region ap-south-1 \
  output.json

cat output.json
```

**Expected Output:**
```json
{
  "statusCode": 200,
  "body": {
    "projects": [
      {
        "project_id": "12345",
        "project_type": "Flooring Installation",
        ...
      }
    ]
  }
}
```

✅ **Checkpoint:** scheduling-actions deployed and tested

### 3.3 Deploy information-actions

```bash
cd ../information-actions

aws lambda create-function \
  --function-name scheduling-agent-information-actions \
  --runtime python3.11 \
  --role $ROLE_ARN \
  --handler handler.lambda_handler \
  --zip-file fileb://information-actions.zip \
  --timeout 30 \
  --memory-size 512 \
  --environment Variables={USE_MOCK_API=true,AWS_REGION=ap-south-1} \
  --region ap-south-1 \
  --description "Information actions Lambda for Bedrock Agent"
```

**Test:**
```bash
aws lambda invoke \
  --function-name scheduling-agent-information-actions \
  --payload '{"action":"get_working_hours","parameters":{}}' \
  --region ap-south-1 \
  output.json && cat output.json
```

### 3.4 Deploy notes-actions

```bash
cd ../notes-actions

aws lambda create-function \
  --function-name scheduling-agent-notes-actions \
  --runtime python3.11 \
  --role $ROLE_ARN \
  --handler handler.lambda_handler \
  --zip-file fileb://notes-actions.zip \
  --timeout 30 \
  --memory-size 512 \
  --environment Variables={USE_MOCK_API=true,AWS_REGION=ap-south-1} \
  --region ap-south-1 \
  --description "Notes actions Lambda for Bedrock Agent"
```

**Test:**
```bash
aws lambda invoke \
  --function-name scheduling-agent-notes-actions \
  --payload '{"action":"list_notes","parameters":{"project_id":"12345"}}' \
  --region ap-south-1 \
  output.json && cat output.json
```

✅ **Checkpoint:** All 3 Lambda functions deployed and tested

---

## 🔗 Step 4: Grant Bedrock Permission to Invoke Lambda

Bedrock Agents need permission to invoke your Lambda functions.

### 4.1 Grant Permission for scheduling-actions

```bash
SCHEDULING_AGENT_ID="IX24FSMTQH"

aws lambda add-permission \
  --function-name scheduling-agent-scheduling-actions \
  --statement-id bedrock-invoke-scheduling \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn "arn:aws:bedrock:ap-south-1:${ACCOUNT_ID}:agent/${SCHEDULING_AGENT_ID}" \
  --region ap-south-1
```

### 4.2 Grant Permission for information-actions

```bash
INFORMATION_AGENT_ID="C9ANXRIO8Y"

aws lambda add-permission \
  --function-name scheduling-agent-information-actions \
  --statement-id bedrock-invoke-information \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn "arn:aws:bedrock:ap-south-1:${ACCOUNT_ID}:agent/${INFORMATION_AGENT_ID}" \
  --region ap-south-1
```

### 4.3 Grant Permission for notes-actions

```bash
NOTES_AGENT_ID="G5BVBYEPUM"

aws lambda add-permission \
  --function-name scheduling-agent-notes-actions \
  --statement-id bedrock-invoke-notes \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn "arn:aws:bedrock:ap-south-1:${ACCOUNT_ID}:agent/${NOTES_AGENT_ID}" \
  --region ap-south-1
```

✅ **Checkpoint:** Permissions granted

---

## 🤖 Step 5: Update Bedrock Agent Action Groups

Now connect the Lambda functions to your Bedrock Agents.

### 5.1 Update Scheduling Collaborator

**Via AWS Console (Easier):**

1. Go to: https://console.aws.amazon.com/bedrock/home?region=ap-south-1#/agents
2. Find agent: **scheduling-agent-scheduling-collab** (ID: IX24FSMTQH)
3. Click **Edit in Agent Builder**
4. Scroll to **Action groups** section
5. Find existing action group (should already exist from Terraform)
6. Click **Edit**
7. **Lambda function:** Select `scheduling-agent-scheduling-actions`
8. Click **Save**
9. Click **Prepare** button at top
10. Wait 30-60 seconds for preparation

**Via AWS CLI (Advanced):**

```bash
# Get existing action group ID
ACTION_GROUP_ID=$(aws bedrock-agent list-agent-action-groups \
  --agent-id IX24FSMTQH \
  --agent-version DRAFT \
  --region ap-south-1 \
  --query 'actionGroupSummaries[0].actionGroupId' \
  --output text)

# Update action group with Lambda ARN
aws bedrock-agent update-agent-action-group \
  --agent-id IX24FSMTQH \
  --agent-version DRAFT \
  --action-group-id $ACTION_GROUP_ID \
  --action-group-executor lambda={
    lambdaArn="arn:aws:lambda:ap-south-1:${ACCOUNT_ID}:function:scheduling-agent-scheduling-actions"
  } \
  --region ap-south-1

# Prepare agent
aws bedrock-agent prepare-agent \
  --agent-id IX24FSMTQH \
  --region ap-south-1
```

### 5.2 Update Information Collaborator

Repeat the same steps for **scheduling-agent-information-collab** (ID: C9ANXRIO8Y):

1. Edit agent in console
2. Update action group
3. Select Lambda: `scheduling-agent-information-actions`
4. Save and Prepare

### 5.3 Update Notes Collaborator

Repeat for **scheduling-agent-notes-collab** (ID: G5BVBYEPUM):

1. Edit agent in console
2. Update action group
3. Select Lambda: `scheduling-agent-notes-actions`
4. Save and Prepare

✅ **Checkpoint:** All agents updated with Lambda functions

---

## 🧪 Step 6: Test End-to-End in Bedrock Console

### 6.1 Test Supervisor Agent

1. Go to: https://console.aws.amazon.com/bedrock/home?region=ap-south-1#/agents
2. Click: **scheduling-agent-supervisor** (ID: 5VTIWONUMO)
3. Click: **Test** button in top right
4. Try test conversations:

**Test 1: Scheduling**
```
User: I want to schedule an appointment

Expected:
- Agent routes to scheduling collaborator
- Invokes list_projects Lambda
- Returns list of projects in natural language
```

**Test 2: Information**
```
User: What are your working hours?

Expected:
- Agent routes to information collaborator
- Invokes get_working_hours Lambda
- Returns hours in natural language
```

**Test 3: Notes**
```
User: Can you show me notes for project 12345?

Expected:
- Agent routes to notes collaborator
- Invokes list_notes Lambda
- Returns notes in natural language
```

### 6.2 Verify Lambda Invocations

Check CloudWatch Logs to verify Lambda was actually called:

```bash
# Get recent log events for scheduling-actions
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions \
  --follow \
  --region ap-south-1
```

You should see logs like:
```
START RequestId: abc-123...
Received event: {...}
Action: list_projects
Using mock API (USE_MOCK_API=true)
Returning mock projects data
END RequestId: abc-123...
```

✅ **Checkpoint:** End-to-end working!

---

## 🔧 Step 7: Clean Up Package Files (Optional)

Remove temporary build files:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/lambda

rm -rf scheduling-actions/package
rm -rf information-actions/package
rm -rf notes-actions/package

# Keep ZIP files for future updates
# rm scheduling-actions/scheduling-actions.zip
# rm information-actions/information-actions.zip
# rm notes-actions/notes-actions.zip
```

---

## 🎉 Success Checklist

You're done when:

- [ ] 3 Lambda functions deployed
- [ ] All 3 functions tested successfully via `aws lambda invoke`
- [ ] Bedrock permissions granted
- [ ] Action groups updated with Lambda ARNs
- [ ] All agents prepared (status: PREPARED)
- [ ] Test conversation in Bedrock console works
- [ ] CloudWatch logs show Lambda invocations

---

## 🛠️ Troubleshooting

### Issue: Lambda Invoke Returns Error

**Symptoms:**
```json
{"errorMessage": "...", "errorType": "..."}
```

**Debug Steps:**

1. **Check CloudWatch Logs:**
```bash
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions --region ap-south-1
```

2. **Check Environment Variables:**
```bash
aws lambda get-function-configuration \
  --function-name scheduling-agent-scheduling-actions \
  --region ap-south-1 \
  --query 'Environment'
```

3. **Test with Verbose Output:**
```bash
aws lambda invoke \
  --function-name scheduling-agent-scheduling-actions \
  --payload '{"action":"list_projects","parameters":{}}' \
  --cli-binary-format raw-in-base64-out \
  --log-type Tail \
  --region ap-south-1 \
  output.json

# View base64-encoded logs
aws lambda invoke ... --query 'LogResult' --output text | base64 --decode
```

---

### Issue: Bedrock Agent Not Calling Lambda

**Symptoms:** Agent responds but doesn't seem to invoke Lambda

**Debug Steps:**

1. **Check Action Group Configuration:**
```bash
aws bedrock-agent get-agent-action-group \
  --agent-id IX24FSMTQH \
  --agent-version DRAFT \
  --action-group-id [YOUR_ACTION_GROUP_ID] \
  --region ap-south-1
```

Verify `actionGroupExecutor.lambda` has correct ARN.

2. **Check Agent Status:**
```bash
aws bedrock-agent get-agent \
  --agent-id IX24FSMTQH \
  --region ap-south-1 \
  --query 'agent.agentStatus'
```

Should be `PREPARED`. If not, run:
```bash
aws bedrock-agent prepare-agent --agent-id IX24FSMTQH --region ap-south-1
```

3. **Check Lambda Permissions:**
```bash
aws lambda get-policy \
  --function-name scheduling-agent-scheduling-actions \
  --region ap-south-1
```

Should show Bedrock principal with permission.

---

### Issue: Permission Denied

**Symptoms:**
```
AccessDeniedException: User is not authorized to perform: lambda:CreateFunction
```

**Fix:** Ensure your AWS IAM user/role has Lambda permissions:

```bash
aws iam attach-user-policy \
  --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AWSLambda_FullAccess
```

Or use an IAM role with sufficient permissions.

---

## 📊 Monitoring Lambda Functions

### View Lambda Metrics

```bash
# Invocation count
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=scheduling-agent-scheduling-actions \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum \
  --region ap-south-1

# Error count
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=scheduling-agent-scheduling-actions \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum \
  --region ap-south-1
```

### View Recent Logs

```bash
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions \
  --since 1h \
  --region ap-south-1
```

---

## 🔄 Updating Lambda Functions

When you make code changes:

```bash
# Repackage
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/lambda/scheduling-actions
rm -rf package scheduling-actions.zip
mkdir package
pip install -r requirements.txt -t package/
cp *.py package/
cd package && zip -r ../scheduling-actions.zip . && cd ..

# Update function code
aws lambda update-function-code \
  --function-name scheduling-agent-scheduling-actions \
  --zip-file fileb://scheduling-actions.zip \
  --region ap-south-1

# Wait for update to complete
aws lambda wait function-updated \
  --function-name scheduling-agent-scheduling-actions \
  --region ap-south-1

# Test
aws lambda invoke \
  --function-name scheduling-agent-scheduling-actions \
  --payload '{"action":"list_projects","parameters":{}}' \
  --region ap-south-1 \
  output.json && cat output.json
```

---

## 🧪 Testing Lambda Functions

### Verify Deployment

```bash
# List all deployed Lambda functions
aws lambda list-functions \
  --region us-east-1 \
  --query 'Functions[?contains(FunctionName, `scheduling-agent`)].{Name:FunctionName,Runtime:Runtime,Size:CodeSize}' \
  --output table
```

Expected output:
```
--------------------------------------------------------------------
|                           ListFunctions                          |
+---------------------------------------+-------------+------------+
|                 Name                  |   Runtime   |   Size     |
+---------------------------------------+-------------+------------+
|  scheduling-agent-information-actions |  python3.11 |  17182348  |
|  scheduling-agent-scheduling-actions  |  python3.11 |  17181722  |
|  scheduling-agent-notes-actions       |  python3.11 |  17180483  |
+---------------------------------------+-------------+------------+
```

### Test Lambda Functions

**IMPORTANT:** These Lambda functions are designed to be invoked **by Bedrock agents**, not directly. Direct testing requires the correct Bedrock event format.

#### AWS CLI v2 Testing (Correct Method)

```bash
# Test Scheduling Actions
aws lambda invoke \
  --function-name scheduling-agent-scheduling-actions \
  --cli-binary-format raw-in-base64-out \
  --payload '{"messageVersion":"1.0","agent":{"name":"scheduling-agent","id":"IX24FSMTQH"},"apiPath":"/list_projects","httpMethod":"POST","parameters":[],"requestBody":{"content":{"application/json":{"properties":[]}}}}' \
  --region us-east-1 \
  output.json

cat output.json
```

**Note:** The `--cli-binary-format raw-in-base64-out` flag is **required for AWS CLI v2**. Without it, you'll get "Invalid UTF-8" errors.

#### Expected Response Format

```json
{
  "messageVersion": "1.0",
  "response": {
    "actionGroup": "scheduling",
    "apiPath": "/list_projects",
    "httpMethod": "POST",
    "httpStatusCode": 200,
    "responseBody": {
      "application/json": {
        "body": "{\"projects\": [{\"id\": \"12345\", \"name\": \"Flooring Installation\", ...}]}"
      }
    }
  }
}
```

### Get Lambda ARNs (for Bedrock Agent Configuration)

```bash
echo "=== Lambda Function ARNs ==="
echo ""
echo "Scheduling Actions:"
aws lambda get-function \
  --function-name scheduling-agent-scheduling-actions \
  --region us-east-1 \
  --query 'Configuration.FunctionArn' \
  --output text

echo ""
echo "Information Actions:"
aws lambda get-function \
  --function-name scheduling-agent-information-actions \
  --region us-east-1 \
  --query 'Configuration.FunctionArn' \
  --output text

echo ""
echo "Notes Actions:"
aws lambda get-function \
  --function-name scheduling-agent-notes-actions \
  --region us-east-1 \
  --query 'Configuration.FunctionArn' \
  --output text
```

### Test Through Bedrock Console (Recommended)

The **best way to test** is through Bedrock agents:

1. Open Supervisor Agent: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/5VTIWONUMO
2. Click **"Test"** button (top right)
3. Type: "I want to schedule an appointment"
4. Observe:
   - Agent routes to Scheduling collaborator
   - Lambda function is invoked
   - Mock project data is returned

---

## 🔧 Troubleshooting

### Issue 1: "Invalid UTF-8 middle byte" Error

**Symptoms:**
```
An error occurred (InvalidRequestContentException) when calling the Invoke operation:
Could not parse request body into json: Invalid UTF-8 middle byte 0x62
```

**Cause:** AWS CLI v2 requires the `--cli-binary-format` flag

**Solution:**
```bash
# Add this flag to all lambda invoke commands:
aws lambda invoke \
  --function-name scheduling-agent-scheduling-actions \
  --cli-binary-format raw-in-base64-out \
  --payload '{"action":"list_projects"}' \
  --region us-east-1 \
  output.json
```

---

### Issue 2: "AWS_REGION is a reserved key" Error

**Symptoms:**
```
InvalidParameterValueException: Lambda was unable to configure your environment
variables because the environment variables you have provided contains reserved keys
that are currently not supported for modification. Reserved keys used: AWS_REGION
```

**Cause:** AWS Lambda automatically provides `AWS_REGION` - you cannot set it manually

**Solution:**
```bash
# WRONG - includes AWS_REGION:
--environment "Variables={USE_MOCK_API=true,AWS_REGION=us-east-1}"

# CORRECT - AWS_REGION is automatic:
--environment "Variables={USE_MOCK_API=true}"
```

Lambda code can still access it:
```python
import os
region = os.environ['AWS_REGION']  # Automatically set by Lambda
```

---

### Issue 3: IAM Role Not Yet Propagated

**Symptoms:**
```
InvalidParameterValueException: The role defined for the function cannot be assumed by Lambda.
```

**Cause:** IAM role was just created, AWS needs time to propagate

**Solution:**
```bash
# Wait 15-30 seconds after creating IAM role
echo "Waiting for IAM role propagation..."
sleep 15

# Then create Lambda function
aws lambda create-function ...
```

The deployment script now includes this wait automatically.

---

### Issue 4: Package Too Large

**Symptoms:**
```
RequestEntityTooLargeException: Request must be smaller than 69905067 bytes
```

**Cause:** Lambda deployment package exceeds 50MB (or 250MB with layers)

**Solution:**

**Option 1: Use Lambda Layers (Recommended)**
```bash
# Create layer for dependencies
cd package
zip -r ../dependencies-layer.zip .
aws lambda publish-layer-version \
  --layer-name scheduling-agent-dependencies \
  --zip-file fileb://../dependencies-layer.zip \
  --compatible-runtimes python3.11 \
  --region us-east-1

# Deploy function without dependencies
cd ..
zip -r function.zip handler.py config.py mock_data.py
aws lambda create-function \
  --function-name scheduling-agent-scheduling-actions \
  --runtime python3.11 \
  --handler handler.lambda_handler \
  --zip-file fileb://function.zip \
  --layers arn:aws:lambda:us-east-1:123456789012:layer:scheduling-agent-dependencies:1 \
  --region us-east-1
```

**Option 2: Use S3 for Large Packages**
```bash
# Upload to S3
aws s3 cp function.zip s3://your-bucket/lambda/function.zip

# Create function from S3
aws lambda create-function \
  --function-name scheduling-agent-scheduling-actions \
  --runtime python3.11 \
  --handler handler.lambda_handler \
  --code S3Bucket=your-bucket,S3Key=lambda/function.zip \
  --region us-east-1
```

---

### Issue 5: Python Dependency Conflicts

**Symptoms:**
```
ERROR: pip's dependency resolver does not currently take into account all the
packages that are installed. This behaviour is the source of the following
dependency conflicts.
mcp 1.13.0 requires pydantic<3.0.0,>=2.11.0, but you have pydantic 2.8.2
```

**Cause:** Installing Lambda dependencies in your global Python environment

**Solution:** The deployment script now uses virtual environments automatically:

```bash
# Manual method if needed:
cd bedrock/lambda/scheduling-actions

# Create isolated environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt -t package/

# Deactivate
deactivate

# Clean up
rm -rf venv
```

---

### Issue 6: "No action specified in event" Error

**Symptoms:**
```json
{
  "error": "No action specified in event",
  "action": "unknown"
}
```

**Cause:** Lambda was invoked directly without the proper Bedrock event structure

**This is EXPECTED!** These Lambda functions are designed to be invoked by Bedrock agents, not directly.

**Solution:** Test through Bedrock Console (see Testing section above)

---

### Issue 7: Region Mismatch

**Symptoms:** Lambda deploys but Bedrock agents can't invoke it

**Cause:** Lambda function in different region than Bedrock agents

**Solution:**
```bash
# Check Bedrock agent region
aws bedrock-agent get-agent --agent-id 5VTIWONUMO --region us-east-1

# Deploy Lambda to SAME region
./deploy_lambda_functions.sh  # Now defaults to us-east-1
```

Bedrock agents are in **us-east-1**, so Lambda functions must be too.

---

### Issue 8: Bash Version Incompatibility (macOS)

**Symptoms:**
```
./deploy_lambda_functions.sh: line 271: declare: -A: invalid option
declare: usage: declare [-afFirtx] [-p] [name[=value] ...]
```

**Cause:** macOS uses bash 3.2, which doesn't support associative arrays

**Solution:** The script now uses case statements instead (bash 3.2 compatible):

```bash
# OLD (bash 4+ only):
declare -A AGENT_MAP
AGENT_MAP["func1"]=$ID1

# NEW (bash 3.2 compatible):
get_agent_id() {
    case "$1" in
        "func1") echo "$ID1" ;;
    esac
}
```

---

### Issue 9: Lambda Not Found After Deployment

**Symptoms:**
```
ResourceNotFoundException: Function not found
```

**Solution:**
```bash
# Check if function exists
aws lambda get-function \
  --function-name scheduling-agent-scheduling-actions \
  --region us-east-1

# List all Lambda functions
aws lambda list-functions --region us-east-1

# Verify correct region
echo $AWS_REGION  # Should be us-east-1
```

---

### Issue 10: Permission Denied Errors

**Symptoms:**
```
An error occurred (AccessDeniedException) when calling the CreateFunction operation
```

**Solution:** Verify IAM permissions for your AWS user/role:

Required permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:CreateFunction",
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:InvokeFunction",
        "lambda:GetFunction",
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PassRole"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 📚 Additional Resources

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [AWS Bedrock Agent Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Lambda Python Runtime](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)

---

## ✅ Next Steps

After successful deployment:

1. **Switch to Real PF360 API** (when ready):
   ```bash
   aws lambda update-function-configuration \
     --function-name scheduling-agent-scheduling-actions \
     --environment Variables={USE_MOCK_API=false,PF360_API_URL=https://api.pf360.com} \
     --region ap-south-1
   ```

2. **Create Database Models** - See CURRENT_PRIORITIES.md (Priority 3)

3. **Build Web Chat UI** - See CURRENT_PRIORITIES.md (Priority 4)

4. **Set Up Monitoring** - See CURRENT_PRIORITIES.md (Priority 5)

---

**Document Version:** 1.1
**Last Updated:** October 17, 2025
**Deployment Time:** 1-2 hours (manual) or 5-10 minutes (automated script)

**Updates in v1.1:**
- ✅ Added comprehensive Testing section
- ✅ Added 10 troubleshooting scenarios with solutions
- ✅ Fixed AWS CLI v2 compatibility (--cli-binary-format flag)
- ✅ Fixed AWS_REGION reserved environment variable issue
- ✅ Fixed macOS bash 3.2 compatibility issues
- ✅ Added IAM propagation wait time
- ✅ Added virtual environment isolation for dependencies

**Deployment complete! Your Bedrock Agents are now fully functional with Lambda actions! 🎉**
