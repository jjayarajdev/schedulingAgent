#!/bin/bash

##############################################################################
# DEPLOY_LAMBDA_ONLY.sh - Deploy Pure Lambda Architecture (No Bedrock)
#
# Purpose: Deploy ProjectForce scheduling system using only AWS Lambda
# Date: 2025-11-23
#
# Deploys:
#   1. pf-scheduling-actions (scheduling queries & workflows)
#   2. pf-information-actions (weather queries)
#   3. pf-chitchat-actions (greetings, help, general chat)
#   4. pf-orchestrator (routing & workflow orchestration)
#   5. DynamoDB tables for sessions and notes
#
# NO BEDROCK AGENTS - Everything runs via direct Lambda calls
#
# Prerequisites:
#   - AWS CLI configured
#   - Secrets Manager secret: projectforce/api/credentials
#
# Usage:
#   ./DEPLOY_LAMBDA_ONLY.sh
#   ./DEPLOY_LAMBDA_ONLY.sh --profile pf-aws
##############################################################################

set -e  # Exit on error

# AWS Profile Support
AWS_PROFILE="${AWS_PROFILE:-}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            AWS_PROFILE="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# AWS CLI wrapper
aws_cmd() {
    if [[ -n "$AWS_PROFILE" ]]; then
        aws --profile "$AWS_PROFILE" "$@"
    else
        aws "$@"
    fi
}

# Determine paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

REGION="us-east-1"
ACCOUNT_ID=$(aws_cmd sts get-caller-identity --query Account --output text)
ENV="dev"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "ProjectForce Lambda-Only Deployment"
echo "=========================================="
echo ""
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo "Environment: $ENV"
echo ""
echo "🚀 Pure Lambda Architecture - No Bedrock agents!"
echo ""

##############################################################################
# Step 1: ProjectForce API Credentials
##############################################################################

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}ProjectForce API Credentials${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "Client ID (e.g., 09PF05VD): " PF_CLIENT_ID
while [[ -z "$PF_CLIENT_ID" ]]; do
    echo -e "${YELLOW}Client ID is required${NC}"
    read -p "Client ID: " PF_CLIENT_ID
done

read -p "User ID (e.g., 1646085): " PF_USER_ID
while [[ -z "$PF_USER_ID" ]]; do
    echo -e "${YELLOW}User ID is required${NC}"
    read -p "User ID: " PF_USER_ID
done

echo ""
echo "Bearer Token (paste from Local Storage 'accesstoken'):"
read -p "> " PF_BEARER_TOKEN
while [[ -z "$PF_BEARER_TOKEN" ]]; do
    echo -e "${YELLOW}Bearer Token is required${NC}"
    read -p "Bearer Token: " PF_BEARER_TOKEN
done

echo ""
echo -e "${GREEN}✓ Credentials captured${NC}"
echo ""

##############################################################################
# Step 2: Create/Update Secrets Manager Secret
##############################################################################

echo ""
echo "=========================================="
echo "Step 2: Secrets Manager"
echo "=========================================="

SECRET_NAME="projectforce/api/credentials"
SECRET_VALUE=$(cat <<EOF
{
  "bearer_token": "$PF_BEARER_TOKEN",
  "client_id": "$PF_CLIENT_ID",
  "user_id": "$PF_USER_ID",
  "api_base_url": "https://api-cx-portal.dev.projectsforce.com"
}
EOF
)

if aws_cmd secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$REGION" &>/dev/null; then
    echo "  → Updating existing secret..."
    aws_cmd secretsmanager update-secret \
        --secret-id "$SECRET_NAME" \
        --secret-string "$SECRET_VALUE" \
        --region "$REGION" &>/dev/null
    echo "  ✅ Secret updated: $SECRET_NAME"
else
    echo "  → Creating new secret..."
    aws_cmd secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --description "ProjectForce API credentials for dev environment" \
        --secret-string "$SECRET_VALUE" \
        --region "$REGION" &>/dev/null
    echo "  ✅ Secret created: $SECRET_NAME"
fi

##############################################################################
# Step 3: Create DynamoDB Tables
##############################################################################

echo ""
echo "=========================================="
echo "Step 3: DynamoDB Tables"
echo "=========================================="

# Sessions table
if aws_cmd dynamodb describe-table --table-name "pf-sessions-dev" --region "$REGION" &>/dev/null; then
    echo "  ✅ Table exists: pf-sessions-dev"
else
    echo "  → Creating pf-sessions-dev..."
    aws_cmd dynamodb create-table \
        --table-name "pf-sessions-dev" \
        --attribute-definitions \
            AttributeName=session_id,AttributeType=S \
            AttributeName=user_id,AttributeType=S \
        --key-schema AttributeName=session_id,KeyType=HASH \
        --global-secondary-indexes \
            "IndexName=user_id-index,KeySchema=[{AttributeName=user_id,KeyType=HASH}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}" \
        --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
        --region "$REGION" &>/dev/null
    echo "  ✅ Table created: pf-sessions-dev"
fi

# Notes table
if aws_cmd dynamodb describe-table --table-name "pf-notes-dev" --region "$REGION" &>/dev/null; then
    echo "  ✅ Table exists: pf-notes-dev"
else
    echo "  → Creating pf-notes-dev..."
    aws_cmd dynamodb create-table \
        --table-name "pf-notes-dev" \
        --attribute-definitions \
            AttributeName=project_id,AttributeType=S \
            AttributeName=timestamp,AttributeType=S \
        --key-schema \
            AttributeName=project_id,KeyType=HASH \
            AttributeName=timestamp,KeyType=RANGE \
        --billing-mode PAY_PER_REQUEST \
        --region "$REGION" &>/dev/null
    echo "  ✅ Table created: pf-notes-dev"
fi

# Workflow states table (for intelligent orchestration)
if aws_cmd dynamodb describe-table --table-name "pf-workflow-states-dev" --region "$REGION" &>/dev/null; then
    echo "  ✅ Table exists: pf-workflow-states-dev"
else
    echo "  → Creating pf-workflow-states-dev..."
    aws_cmd dynamodb create-table \
        --table-name "pf-workflow-states-dev" \
        --attribute-definitions \
            AttributeName=session_id,AttributeType=S \
        --key-schema \
            AttributeName=session_id,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region "$REGION" &>/dev/null
    echo "  ✅ Table created: pf-workflow-states-dev"
fi

##############################################################################
# Step 4: Deploy Lambda Functions
##############################################################################

echo ""
echo "=========================================="
echo "Step 4: Lambda Functions"
echo "=========================================="

deploy_lambda() {
    local FUNCTION_NAME=$1
    local HANDLER=$2
    local TIMEOUT=${3:-30}
    local MEMORY=${4:-512}

    echo ""
    echo "Deploying: $FUNCTION_NAME"

    local LAMBDA_DIR="$PROJECT_DIR/lambda/${FUNCTION_NAME#pf-}"
    local ROLE_NAME="${FUNCTION_NAME}-role-${ENV}"

    if [[ ! -d "$LAMBDA_DIR" ]]; then
        echo "  ⚠️  Directory not found: $LAMBDA_DIR"
        return 1
    fi

    cd "$LAMBDA_DIR"

    # Package
    echo "  → Packaging..."
    rm -f function.zip

    if [[ -f requirements.txt ]]; then
        rm -rf package && mkdir -p package
        pip3 install -r requirements.txt -t package/ --quiet 2>&1 | grep -v "dependency conflicts" || true
        cd package && zip -r ../function.zip . --quiet && cd ..
        zip -g function.zip *.py --quiet
    else
        zip -r function.zip . -x "*.pyc" -x "__pycache__/*" -x "*.zip" &>/dev/null
    fi

    # IAM Role
    if ! aws_cmd iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
        echo "  → Creating IAM role..."

        cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

        aws_cmd iam create-role \
            --role-name "$ROLE_NAME" \
            --assume-role-policy-document file:///tmp/trust-policy.json &>/dev/null

        aws_cmd iam attach-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" &>/dev/null

        # Add DynamoDB permissions for scheduling and orchestrator
        if [[ "$FUNCTION_NAME" =~ (scheduling|orchestrator) ]]; then
            aws_cmd iam attach-role-policy \
                --role-name "$ROLE_NAME" \
                --policy-arn "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess" &>/dev/null
        fi

        # Add Secrets Manager permissions
        cat > /tmp/secrets-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["secretsmanager:GetSecretValue"],
    "Resource": "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:projectforce/api/credentials*"
  }]
}
EOF

        aws_cmd iam put-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-name "SecretsAccess" \
            --policy-document file:///tmp/secrets-policy.json &>/dev/null

        # Add Lambda invoke permissions and Bedrock access for orchestrator
        if [[ "$FUNCTION_NAME" == "pf-orchestrator" ]]; then
            cat > /tmp/orchestrator-permissions.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel"],
      "Resource": [
        "arn:aws:bedrock:${REGION}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
        "arn:aws:bedrock:${REGION}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
        "arn:aws:bedrock:*::foundation-model/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["lambda:InvokeFunction"],
      "Resource": [
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-scheduling-actions",
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-information-actions",
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-chitchat-actions"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/pf-sessions-dev",
        "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/pf-workflow-states-dev"
      ]
    }
  ]
}
EOF

            aws_cmd iam put-role-policy \
                --role-name "$ROLE_NAME" \
                --policy-name "OrchestratorPermissions" \
                --policy-document file:///tmp/orchestrator-permissions.json &>/dev/null
        fi

        sleep 10
    fi

    local ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

    # Create or update Lambda
    if aws_cmd lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" &>/dev/null; then
        echo "  → Updating existing function..."
        aws_cmd lambda update-function-code \
            --function-name "$FUNCTION_NAME" \
            --zip-file fileb://function.zip \
            --region "$REGION" &>/dev/null

        # Wait for update
        sleep 5
        aws_cmd lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION" 2>/dev/null || true

        # Update configuration
        aws_cmd lambda update-function-configuration \
            --function-name "$FUNCTION_NAME" \
            --timeout "$TIMEOUT" \
            --memory-size "$MEMORY" \
            --region "$REGION" &>/dev/null

        echo "  ✅ Lambda updated: $FUNCTION_NAME"
    else
        echo "  → Creating new function..."
        aws_cmd lambda create-function \
            --function-name "$FUNCTION_NAME" \
            --runtime python3.11 \
            --role "$ROLE_ARN" \
            --handler "$HANDLER" \
            --zip-file fileb://function.zip \
            --timeout "$TIMEOUT" \
            --memory-size "$MEMORY" \
            --region "$REGION" &>/dev/null

        echo "  ✅ Lambda created: $FUNCTION_NAME"
    fi
}

# Deploy all Lambda functions
deploy_lambda "pf-scheduling-actions" "handler.lambda_handler" 30 1769
deploy_lambda "pf-information-actions" "handler.lambda_handler" 30 512
deploy_lambda "pf-chitchat-actions" "handler.lambda_handler" 30 256
deploy_lambda "pf-orchestrator" "handler.lambda_handler" 120 512

##############################################################################
# Step 4.5: Configure Scheduling Actions Environment Variables
##############################################################################

echo ""
echo "=========================================="
echo "Step 4.5: Scheduling Actions Configuration"
echo "=========================================="

echo "  → Setting USE_MOCK_API=false for real API calls..."

cat > /tmp/scheduling-env.json <<EOF
{
  "Variables": {
    "USE_MOCK_API": "false",
    "ENVIRONMENT": "$ENV",
    "DEFAULT_CLIENT_ID": "$PF_CLIENT_ID"
  }
}
EOF

aws_cmd lambda update-function-configuration \
    --function-name pf-scheduling-actions \
    --environment file:///tmp/scheduling-env.json \
    --region "$REGION" &>/dev/null

# Wait for configuration update
echo "  → Waiting for configuration update..."
sleep 5

rm -f /tmp/scheduling-env.json
echo "  ✅ Scheduling actions configured for REAL API mode"

##############################################################################
# Step 5: Configure Orchestrator Environment Variables
##############################################################################

echo ""
echo "=========================================="
echo "Step 5: Orchestrator Configuration"
echo "=========================================="

# Wait for orchestrator to be fully ready after Step 4 deployment
echo "  → Waiting for pf-orchestrator to be ready..."
WAIT_COUNT=0
MAX_WAIT=30
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    STATE=$(aws_cmd lambda get-function-configuration \
        --function-name pf-orchestrator \
        --region "$REGION" \
        --query 'State' \
        --output text 2>/dev/null || echo "Pending")

    LAST_UPDATE=$(aws_cmd lambda get-function-configuration \
        --function-name pf-orchestrator \
        --region "$REGION" \
        --query 'LastUpdateStatus' \
        --output text 2>/dev/null || echo "InProgress")

    if [[ "$STATE" == "Active" && "$LAST_UPDATE" == "Successful" ]]; then
        echo "  ✅ Lambda ready"
        break
    fi

    echo "  ⏳ Waiting for Lambda (State: $STATE, LastUpdate: $LAST_UPDATE)..."
    sleep 2
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

if [[ $WAIT_COUNT -ge $MAX_WAIT ]]; then
    echo "  ⚠️  Warning: Lambda may not be fully ready, proceeding anyway..."
fi

# Create environment configuration
cat > /tmp/orchestrator-env.json <<EOF
{
  "Variables": {
    "SCHEDULING_LAMBDA": "pf-scheduling-actions",
    "INFORMATION_LAMBDA": "pf-information-actions",
    "CHITCHAT_LAMBDA": "pf-chitchat-actions",
    "ORCHESTRATOR_MODEL": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    "DYNAMODB_TABLE": "pf-sessions-dev",
    "WORKFLOW_STATE_TABLE": "pf-workflow-states-dev",
    "REGION": "$REGION",
    "ALLOW_DIRECT_LAMBDA": "true",
    "ENABLE_MULTI_AGENT_ORCHESTRATION": "false",
    "USE_SUPERVISOR": "false"
  }
}
EOF

# Update environment variables
echo "  → Setting environment variables..."
aws_cmd lambda update-function-configuration \
    --function-name pf-orchestrator \
    --environment file:///tmp/orchestrator-env.json \
    --region "$REGION" &>/dev/null

# Wait for configuration update to complete
echo "  → Waiting for configuration update to complete..."
WAIT_COUNT=0
MAX_WAIT=30
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    LAST_UPDATE=$(aws_cmd lambda get-function-configuration \
        --function-name pf-orchestrator \
        --region "$REGION" \
        --query 'LastUpdateStatus' \
        --output text 2>/dev/null || echo "InProgress")

    if [[ "$LAST_UPDATE" == "Successful" ]]; then
        break
    fi

    if [[ "$LAST_UPDATE" == "Failed" ]]; then
        echo "  ❌ Configuration update failed!"
        break
    fi

    echo "  ⏳ Update status: $LAST_UPDATE..."
    sleep 2
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

# Verify environment variables were set
echo "  → Verifying environment variables..."
SCHEDULING_LAMBDA=$(aws_cmd lambda get-function-configuration \
    --function-name pf-orchestrator \
    --region "$REGION" \
    --query 'Environment.Variables.SCHEDULING_LAMBDA' \
    --output text 2>/dev/null || echo "null")

if [[ "$SCHEDULING_LAMBDA" == "pf-scheduling-actions" ]]; then
    echo "  ✅ Environment variables verified: SCHEDULING_LAMBDA=$SCHEDULING_LAMBDA"
    echo "  ✅ Orchestrator configured successfully"
else
    echo "  ⚠️  Warning: Environment variables may not be set correctly"
    echo "  ⚠️  SCHEDULING_LAMBDA=$SCHEDULING_LAMBDA (expected: pf-scheduling-actions)"
fi

rm -f /tmp/orchestrator-env.json

##############################################################################
# Summary
##############################################################################

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Deployment Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Deployed Resources:"
echo "  ✅ 4 Lambda functions"
echo "     • pf-orchestrator (intelligent routing & workflows)"
echo "     • pf-scheduling-actions (scheduling queries)"
echo "     • pf-information-actions (weather)"
echo "     • pf-chitchat-actions (greetings, help)"
echo ""
echo "  ✅ 3 DynamoDB tables"
echo "     • pf-sessions-dev (conversation history)"
echo "     • pf-notes-dev (project notes)"
echo "     • pf-workflow-states-dev (workflow state management)"
echo ""
echo "  ✅ 1 Secrets Manager secret"
echo "     • projectforce/api/credentials"
echo ""
echo "Architecture:"
echo "  🚀 Pure Lambda - No Bedrock agents"
echo "  🧠 Sonnet 3.5 - Intelligent orchestration"
echo "  ⚡ Fast response times with context retention"
echo "  💰 Lower costs (no Bedrock agent charges)"
echo ""
echo "Test the system:"
echo "  1. Start UI proxy:"
echo "     cd testing/ui && python3 pf_proxy.py"
echo ""
echo "  2. Open browser:"
echo "     http://localhost:5003"
echo ""
echo "  3. Try these queries:"
echo "     • Hi"
echo "     • List my projects"
echo "     • Details for 7751748"
echo "     • Schedule it"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
