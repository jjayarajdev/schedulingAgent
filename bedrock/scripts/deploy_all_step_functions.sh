#!/bin/bash
#
# Deploy All Step Functions State Machines and Lambda Functions
# This script deploys the complete Step Functions infrastructure
#

set -e  # Exit on error

echo "=========================================="
echo "Deploying Complete Step Functions Infrastructure"
echo "=========================================="

# Configuration
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
PREFIX="pf"

echo "Account ID: $ACCOUNT_ID"
echo "Region: $REGION"
echo ""

# ============================================================================
# STEP 1: Deploy Lambda Functions
# ============================================================================

echo "=========================================="
echo "STEP 1: Deploying Lambda Functions"
echo "=========================================="

# Query Router Lambda
echo ""
echo "1.1 Deploying Query Router Lambda..."
cd lambda/query-router

zip -q -r /tmp/query-router.zip . -x "*.pyc" "__pycache__/*" "test_*.py"

if aws lambda get-function --function-name ${PREFIX}-query-router --region $REGION 2>/dev/null; then
    echo "   Updating existing function..."
    aws lambda update-function-code \
        --function-name ${PREFIX}-query-router \
        --zip-file fileb:///tmp/query-router.zip \
        --region $REGION \
        --no-cli-pager > /dev/null
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
        --no-cli-pager > /dev/null
fi

echo "   ✅ Query Router deployed"
cd ../..

# Filter Projects Lambda
echo ""
echo "1.2 Deploying Filter Projects Lambda..."
cd lambda/filter-projects

zip -q -r /tmp/filter-projects.zip . -x "*.pyc" "__pycache__/*"

if aws lambda get-function --function-name ${PREFIX}-filter-projects --region $REGION 2>/dev/null; then
    echo "   Updating existing function..."
    aws lambda update-function-code \
        --function-name ${PREFIX}-filter-projects \
        --zip-file fileb:///tmp/filter-projects.zip \
        --region $REGION \
        --no-cli-pager > /dev/null
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
        --no-cli-pager > /dev/null
fi

echo "   ✅ Filter Projects Lambda deployed"
cd ../..

# Weather Evaluator Lambda
echo ""
echo "1.3 Deploying Weather Evaluator Lambda..."
cd lambda/weather-evaluator

zip -q -r /tmp/weather-evaluator.zip . -x "*.pyc" "__pycache__/*"

if aws lambda get-function --function-name ${PREFIX}-weather-evaluator --region $REGION 2>/dev/null; then
    echo "   Updating existing function..."
    aws lambda update-function-code \
        --function-name ${PREFIX}-weather-evaluator \
        --zip-file fileb:///tmp/weather-evaluator.zip \
        --region $REGION \
        --no-cli-pager > /dev/null
else
    echo "   Creating new function..."
    aws lambda create-function \
        --function-name ${PREFIX}-weather-evaluator \
        --runtime python3.11 \
        --role arn:aws:iam::${ACCOUNT_ID}:role/${PREFIX}-information-lambda-role-dev \
        --handler handler.lambda_handler \
        --zip-file fileb:///tmp/weather-evaluator.zip \
        --timeout 10 \
        --memory-size 256 \
        --region $REGION \
        --no-cli-pager > /dev/null
fi

echo "   ✅ Weather Evaluator Lambda deployed"
cd ../..

# ============================================================================
# STEP 2: Create/Update IAM Role for Step Functions
# ============================================================================

echo ""
echo "=========================================="
echo "STEP 2: Checking Step Functions IAM Role"
echo "=========================================="

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
        --no-cli-pager > /dev/null

    # Attach policy
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

# ============================================================================
# STEP 3: Deploy State Machines
# ============================================================================

echo ""
echo "=========================================="
echo "STEP 3: Deploying State Machines"
echo "=========================================="

# Helper function to deploy/update state machine
deploy_state_machine() {
    local NAME=$1
    local FILE=$2

    echo ""
    echo "3.${STATE_MACHINE_COUNTER} Deploying: $NAME"

    if aws stepfunctions describe-state-machine \
        --state-machine-arn "arn:aws:states:${REGION}:${ACCOUNT_ID}:stateMachine:${NAME}" \
        --region $REGION 2>/dev/null; then

        echo "   Updating existing state machine..."
        aws stepfunctions update-state-machine \
            --state-machine-arn "arn:aws:states:${REGION}:${ACCOUNT_ID}:stateMachine:${NAME}" \
            --definition file://$FILE \
            --region $REGION \
            --no-cli-pager > /dev/null
    else
        echo "   Creating new state machine..."
        aws stepfunctions create-state-machine \
            --name $NAME \
            --definition file://$FILE \
            --role-arn $ROLE_ARN \
            --region $REGION \
            --no-cli-pager > /dev/null
    fi

    echo "   ✅ $NAME deployed"
    STATE_MACHINE_COUNTER=$((STATE_MACHINE_COUNTER + 1))
}

STATE_MACHINE_COUNTER=1

# Deploy all state machines
deploy_state_machine "${PREFIX}-schedule-urgent-project" "infrastructure/step-functions/state-machines/schedule-urgent-project.json"
deploy_state_machine "${PREFIX}-schedule-weather-dependent" "infrastructure/step-functions/state-machines/schedule-weather-dependent.json"
deploy_state_machine "${PREFIX}-schedule-batch-projects" "infrastructure/step-functions/state-machines/schedule-batch-projects.json"
deploy_state_machine "${PREFIX}-schedule-with-preferences" "infrastructure/step-functions/state-machines/schedule-with-preferences.json"

# ============================================================================
# STEP 4: Update Query Router Environment Variables
# ============================================================================

echo ""
echo "=========================================="
echo "STEP 4: Updating Query Router Configuration"
echo "=========================================="

ENV_VARS="Variables={"
ENV_VARS+="STATE_MACHINE_SCHEDULE_URGENT=arn:aws:states:${REGION}:${ACCOUNT_ID}:stateMachine:${PREFIX}-schedule-urgent-project,"
ENV_VARS+="STATE_MACHINE_WEATHER=arn:aws:states:${REGION}:${ACCOUNT_ID}:stateMachine:${PREFIX}-schedule-weather-dependent,"
ENV_VARS+="STATE_MACHINE_BATCH=arn:aws:states:${REGION}:${ACCOUNT_ID}:stateMachine:${PREFIX}-schedule-batch-projects,"
ENV_VARS+="STATE_MACHINE_PREFERENCES=arn:aws:states:${REGION}:${ACCOUNT_ID}:stateMachine:${PREFIX}-schedule-with-preferences"
ENV_VARS+="}"

aws lambda update-function-configuration \
    --function-name ${PREFIX}-query-router \
    --environment "$ENV_VARS" \
    --region $REGION \
    --no-cli-pager > /dev/null

echo "   ✅ Environment variables updated"

# ============================================================================
# DEPLOYMENT SUMMARY
# ============================================================================

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "Lambda Functions Deployed:"
echo "  • ${PREFIX}-query-router"
echo "  • ${PREFIX}-filter-projects"
echo "  • ${PREFIX}-weather-evaluator"
echo ""
echo "State Machines Deployed:"
echo "  • ${PREFIX}-schedule-urgent-project"
echo "  • ${PREFIX}-schedule-weather-dependent"
echo "  • ${PREFIX}-schedule-batch-projects"
echo "  • ${PREFIX}-schedule-with-preferences"
echo ""
echo "IAM Role:"
echo "  • $ROLE_ARN"
echo ""
echo "Next Steps:"
echo "  1. Test all state machines: python3 tests/test_all_state_machines.py"
echo "  2. Test query router: cd lambda/query-router && python3 test_router.py"
echo "  3. Integrate with Flask backend"
echo "  4. Test through frontend UI"
echo ""
echo "View in AWS Console:"
echo "  https://console.aws.amazon.com/states/home?region=${REGION}#/statemachines"
echo ""
