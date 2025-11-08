#!/bin/bash
#
# Deploy Step Functions and Lambda Functions
# This script deploys the query router, helper lambdas, and state machines
#

set -e  # Exit on error

echo "=========================================="
echo "Deploying Step Functions Infrastructure"
echo "=========================================="

# Configuration
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
PREFIX="pf"

echo "Account ID: $ACCOUNT_ID"
echo "Region: $REGION"
echo ""

# Step 1: Deploy Query Router Lambda
echo "1. Deploying Query Router Lambda..."
cd lambda/query-router

# Create deployment package
zip -q -r /tmp/query-router.zip . -x "*.pyc" "__pycache__/*" "test_*.py"

# Check if function exists
if aws lambda get-function --function-name ${PREFIX}-query-router --region $REGION 2>/dev/null; then
    echo "   Updating existing function..."
    aws lambda update-function-code \
        --function-name ${PREFIX}-query-router \
        --zip-file fileb:///tmp/query-router.zip \
        --region $REGION \
        --no-cli-pager
else
    echo "   Creating new function..."
    aws lambda create-function \
        --function-name ${PREFIX}-query-router \
        --runtime python3.11 \
        --role arn:aws:iam::${ACCOUNT_ID}:role/${PREFIX}-information-lambda-role-dev \
        --handler handler.lambda_handler \
        --zip-file fileb:///tmp/query-router.zip \
        --timeout 30 \
        --memory-size 512 \
        --region $REGION \
        --no-cli-pager
fi

echo "   ✅ Query Router deployed"
cd ../..

# Step 2: Deploy Filter Projects Lambda
echo ""
echo "2. Deploying Filter Projects Lambda..."
cd lambda/filter-projects

# Create deployment package
zip -q -r /tmp/filter-projects.zip . -x "*.pyc" "__pycache__/*"

# Check if function exists
if aws lambda get-function --function-name ${PREFIX}-filter-projects --region $REGION 2>/dev/null; then
    echo "   Updating existing function..."
    aws lambda update-function-code \
        --function-name ${PREFIX}-filter-projects \
        --zip-file fileb:///tmp/filter-projects.zip \
        --region $REGION \
        --no-cli-pager
else
    echo "   Creating new function..."
    aws lambda create-function \
        --function-name ${PREFIX}-filter-projects \
        --runtime python3.11 \
        --role arn:aws:iam::${ACCOUNT_ID}:role/${PREFIX}-information-lambda-role-dev \
        --handler handler.lambda_handler \
        --zip-file fileb:///tmp/filter-projects.zip \
        --timeout 10 \
        --memory-size 256 \
        --region $REGION \
        --no-cli-pager
fi

echo "   ✅ Filter Projects Lambda deployed"
cd ../..

# Step 3: Create IAM Role for Step Functions (if not exists)
echo ""
echo "3. Checking Step Functions IAM Role..."

ROLE_NAME="${PREFIX}-step-functions-role"
TRUST_POLICY='{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Service": "states.amazonaws.com"
    },
    "Action": "sts:AssumeRole"
  }]
}'

if aws iam get-role --role-name $ROLE_NAME 2>/dev/null; then
    echo "   Role already exists"
else
    echo "   Creating IAM role..."
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document "$TRUST_POLICY" \
        --no-cli-pager

    # Attach policy to allow Lambda and Bedrock invocations
    POLICY_DOCUMENT='{
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Action": [
            "lambda:InvokeFunction",
            "bedrock:InvokeAgent"
          ],
          "Resource": "*"
        },
        {
          "Effect": "Allow",
          "Action": [
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents"
          ],
          "Resource": "arn:aws:logs:*:*:*"
        }
      ]
    }'

    aws iam put-role-policy \
        --role-name $ROLE_NAME \
        --policy-name "${PREFIX}-step-functions-policy" \
        --policy-document "$POLICY_DOCUMENT" \
        --no-cli-pager

    echo "   Waiting for role to propagate..."
    sleep 10
fi

ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
echo "   ✅ Step Functions Role: $ROLE_ARN"

# Step 4: Deploy Step Functions State Machine
echo ""
echo "4. Deploying Step Functions State Machine..."

STATE_MACHINE_NAME="${PREFIX}-schedule-urgent-project"
STATE_MACHINE_FILE="infrastructure/step-functions/state-machines/schedule-urgent-project.json"

# Check if state machine exists
if aws stepfunctions describe-state-machine \
    --state-machine-arn "arn:aws:states:${REGION}:${ACCOUNT_ID}:stateMachine:${STATE_MACHINE_NAME}" \
    --region $REGION 2>/dev/null; then

    echo "   Updating existing state machine..."
    aws stepfunctions update-state-machine \
        --state-machine-arn "arn:aws:states:${REGION}:${ACCOUNT_ID}:stateMachine:${STATE_MACHINE_NAME}" \
        --definition file://$STATE_MACHINE_FILE \
        --region $REGION \
        --no-cli-pager
else
    echo "   Creating new state machine..."
    aws stepfunctions create-state-machine \
        --name $STATE_MACHINE_NAME \
        --definition file://$STATE_MACHINE_FILE \
        --role-arn $ROLE_ARN \
        --region $REGION \
        --no-cli-pager
fi

STATE_MACHINE_ARN="arn:aws:states:${REGION}:${ACCOUNT_ID}:stateMachine:${STATE_MACHINE_NAME}"
echo "   ✅ State Machine deployed: $STATE_MACHINE_ARN"

# Step 5: Update Query Router with State Machine ARN
echo ""
echo "5. Updating Query Router environment variables..."

aws lambda update-function-configuration \
    --function-name ${PREFIX}-query-router \
    --environment "Variables={STATE_MACHINE_SCHEDULE_URGENT=$STATE_MACHINE_ARN}" \
    --region $REGION \
    --no-cli-pager > /dev/null

echo "   ✅ Environment variables updated"

# Summary
echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "Resources deployed:"
echo "  • Lambda: ${PREFIX}-query-router"
echo "  • Lambda: ${PREFIX}-filter-projects"
echo "  • State Machine: $STATE_MACHINE_ARN"
echo "  • IAM Role: $ROLE_ARN"
echo ""
echo "Next steps:"
echo "  1. Test the router: aws lambda invoke --function-name ${PREFIX}-query-router output.json"
echo "  2. Test state machine: See test_step_functions.py"
echo "  3. Update Flask backend to use router"
echo ""
