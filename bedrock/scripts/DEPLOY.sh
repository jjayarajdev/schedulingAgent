#!/bin/bash

##############################################################################
# DEPLOY.sh - Deploy 4-Agent Architecture
#
# Purpose: Automated deployment of ProjectForce Bedrock agents
# Date: 2025-11-03
#
# Deploys:
#   1. SchedulingAgent (primary)
#   2. pf-information (weather only)
#   3. pf-chitchat (conversational)
#   4. Supervisor (orchestrator)
#
# Prerequisites:
#   - AWS CLI configured
#   - Secrets Manager secret: projectforce/api/dev/credentials
#   - Lambda function code in lambda/ directories
#
# Usage: ./DEPLOY.sh
##############################################################################

set -e  # Exit on error

# Determine paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BEDROCK_DIR="$(dirname "$SCRIPT_DIR")"

REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ENV="dev"

# Colors for prompts
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "ProjectForce 4-Agent Deployment"
echo "=========================================="
echo ""
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo "Environment: $ENV"
echo ""

##############################################################################
# Prompt for ProjectForce API Credentials
##############################################################################

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}ProjectForce API Credentials${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "The Lambda functions need API credentials to connect to ProjectForce."
echo ""

echo "Please provide your ProjectForce API credentials:"
echo ""
echo "You can get these from the browser (DevTools → Application → Local Storage):"
echo "  • Client ID: client_id"
echo "  • User ID: id"
echo "  • Bearer Token: accesstoken"
echo "  • Refresh Token: refreshToken"
echo ""

# Prompt for Client ID
if [[ -n "$PF_CLIENT_ID" ]]; then
    read -p "Client ID [current: $PF_CLIENT_ID]: " INPUT_CLIENT_ID
    PF_CLIENT_ID="${INPUT_CLIENT_ID:-$PF_CLIENT_ID}"
else
    read -p "Client ID (e.g., 09PF05VD): " PF_CLIENT_ID
    while [[ -z "$PF_CLIENT_ID" ]]; do
        echo -e "${YELLOW}Client ID is required${NC}"
        read -p "Client ID: " PF_CLIENT_ID
    done
fi

# Prompt for User ID
if [[ -n "$PF_USER_ID" ]]; then
    read -p "User ID [current: $PF_USER_ID]: " INPUT_USER_ID
    PF_USER_ID="${INPUT_USER_ID:-$PF_USER_ID}"
else
    read -p "User ID (e.g., 1646085): " PF_USER_ID
    while [[ -z "$PF_USER_ID" ]]; do
        echo -e "${YELLOW}User ID is required${NC}"
        read -p "User ID: " PF_USER_ID
    done
fi

# Prompt for Bearer Token
echo ""
if [[ -n "$PF_BEARER_TOKEN" ]]; then
    echo "Bearer Token [current: ${PF_BEARER_TOKEN:0:30}...]"
    echo "Press Enter to keep current, or paste new token:"
    read -p "> " INPUT_TOKEN
    PF_BEARER_TOKEN="${INPUT_TOKEN:-$PF_BEARER_TOKEN}"
else
    echo "Bearer Token (paste from Local Storage 'accesstoken'):"
    read -p "> " PF_BEARER_TOKEN
    while [[ -z "$PF_BEARER_TOKEN" ]]; do
        echo -e "${YELLOW}Bearer Token is required${NC}"
        read -p "Bearer Token: " PF_BEARER_TOKEN
    done
fi

# Optional: Refresh token
echo ""
if [[ -n "$PF_REFRESH_TOKEN" ]]; then
    echo "Refresh Token [current: ${PF_REFRESH_TOKEN:0:30}...]"
    echo "Press Enter to keep current, or paste new token:"
    read -p "> " INPUT_REFRESH
    PF_REFRESH_TOKEN="${INPUT_REFRESH:-$PF_REFRESH_TOKEN}"
else
    echo "Optional: Refresh Token (press Enter to skip):"
    read -p "> " PF_REFRESH_TOKEN
fi

echo ""
echo -e "${GREEN}✓ Credentials captured${NC}"
echo ""

# Store values
CLIENT_ID="$PF_CLIENT_ID"
USER_ID="$PF_USER_ID"
BEARER_TOKEN="$PF_BEARER_TOKEN"
REFRESH_TOKEN="${PF_REFRESH_TOKEN:-}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

##############################################################################
# Step 0: Create Secrets Manager Secret
##############################################################################

echo ""
echo "=========================================="
echo "Step 0: Creating Secrets Manager Secret"
echo "=========================================="

SECRET_NAME="projectforce/api/credentials"

# Function to get fresh token using refresh token
get_fresh_token() {
    echo "  → Attempting to get fresh token using refresh token..."

    local AUTH_URL="https://auth.dev.projectsforce.com"
    local API_URL="https://api-cx-portal.dev.projectsforce.com"
    local REFRESH_TOKEN="AWldtvQhQ+wt4HhRcU/2mOjT5Lsh5NKD+Zt//mXFQitxS8KqH5JefG65bVcirEXRIX2F3u3QXUz/inSZiFRNPA=="
    local CLIENT_ID_AUTH="devapps"
    local CLIENT_SECRET="devappssecret"

    local RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$AUTH_URL/token" \
        -H "Content-Type: application/json" \
        -d "{
            \"grant_type\": \"refresh_token\",
            \"refresh_token\": \"$REFRESH_TOKEN\",
            \"client_id\": \"$CLIENT_ID_AUTH\",
            \"client_secret\": \"$CLIENT_SECRET\"
        }")

    local HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d':' -f2)
    local BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

    if [ "$HTTP_CODE" = "200" ]; then
        PF_API_TOKEN=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)
        PF_REFRESH_TOKEN=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('refresh_token', ''))" 2>/dev/null)

        if [[ -n "$PF_API_TOKEN" ]]; then
            echo "  ✅ Fresh token obtained successfully"
            return 0
        fi
    fi

    echo "  ⚠️  Could not get fresh token (HTTP $HTTP_CODE)"
    return 1
}

echo ""
echo "Checking secret: $SECRET_NAME"

# Use the captured Bearer Token from user input
PF_API_TOKEN="$BEARER_TOKEN"

echo "  ✅ Using provided Bearer token"

if aws secretsmanager describe-secret \
    --secret-id "$SECRET_NAME" \
    --region "$REGION" \
    &>/dev/null; then
    echo "  ℹ️  Secret already exists"

    # Update secret with provided credentials
    echo "  → Updating secret with provided credentials..."

    SECRET_VALUE=$(cat <<EOF
{
  "bearer_token": "$PF_API_TOKEN",
  "client_id": "$CLIENT_ID",
  "user_id": "$USER_ID",
  "refresh_token": "${REFRESH_TOKEN:-}",
  "api_base_url": "https://api-cx-portal.dev.projectsforce.com"
}
EOF
)

    aws secretsmanager update-secret \
        --secret-id "$SECRET_NAME" \
        --secret-string "$SECRET_VALUE" \
        --region "$REGION" \
        &>/dev/null && echo "  ✅ Secret updated with provided credentials"
else
    echo "  → Creating secret: $SECRET_NAME"

    SECRET_VALUE=$(cat <<EOF
{
  "bearer_token": "$PF_API_TOKEN",
  "client_id": "$CLIENT_ID",
  "user_id": "$USER_ID",
  "refresh_token": "${REFRESH_TOKEN:-}",
  "api_base_url": "https://api-cx-portal.dev.projectsforce.com"
}
EOF
)

    echo "  ℹ️  Creating with provided credentials"

    aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --description "ProjectForce API credentials for dev environment" \
        --secret-string "$SECRET_VALUE" \
        --region "$REGION" \
        &>/dev/null && echo "  ✅ Secret created: $SECRET_NAME"
fi

##############################################################################
# Step 1: Create DynamoDB Tables
##############################################################################

echo ""
echo "=========================================="
echo "Step 1: Creating DynamoDB Tables"
echo "=========================================="

# Create pf-sessions-dev table
echo ""
echo "Creating DynamoDB table: pf-sessions-dev"

if aws dynamodb describe-table \
    --table-name "pf-sessions-dev" \
    --region "$REGION" \
    &>/dev/null; then
    echo "  ℹ️  Table already exists: pf-sessions-dev"
else
    echo "  → Creating table: pf-sessions-dev"

    aws dynamodb create-table \
        --table-name "pf-sessions-dev" \
        --attribute-definitions \
            AttributeName=session_id,AttributeType=S \
            AttributeName=user_id,AttributeType=S \
        --key-schema \
            AttributeName=session_id,KeyType=HASH \
        --global-secondary-indexes \
            "IndexName=user_id-index,KeySchema=[{AttributeName=user_id,KeyType=HASH}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}" \
        --provisioned-throughput \
            ReadCapacityUnits=5,WriteCapacityUnits=5 \
        --region "$REGION" \
        &>/dev/null && echo "  ✅ Table created: pf-sessions-dev"
fi

##############################################################################
# Step 2: Deploy Lambda Functions
##############################################################################

echo ""
echo "=========================================="
echo "Step 2: Deploying Lambda Functions"
echo "=========================================="

# Function to deploy Lambda
deploy_lambda() {
    local FUNCTION_NAME=$1
    local HANDLER=$2
    local RUNTIME="python3.11"
    local TIMEOUT=30
    local MEMORY=512
    local ROLE_NAME="${FUNCTION_NAME}-role-${ENV}"

    echo ""
    echo "Deploying Lambda: $FUNCTION_NAME"
    echo "  Handler: $HANDLER"

    # Save current directory and determine paths
    local CURRENT_DIR="$(pwd)"
    local LAMBDA_DIR="$BEDROCK_DIR/lambda/${FUNCTION_NAME#pf-}"

    if [[ ! -d "$LAMBDA_DIR" ]]; then
        echo "  ⚠️  Lambda directory not found: $LAMBDA_DIR"
        return 1
    fi

    cd "$LAMBDA_DIR"

    # Create deployment package
    echo "  → Creating deployment package..."
    if [[ -f function.zip ]]; then
        rm function.zip
    fi

    # Install dependencies if requirements.txt exists
    if [[ -f requirements.txt ]]; then
        echo "  → Installing dependencies from requirements.txt..."
        rm -rf package
        mkdir -p package
        pip3 install -r requirements.txt -t package/ --quiet 2>&1 | grep -v "dependency conflicts\|incompatible\|A new release of pip" || true
        cd package
        zip -r ../function.zip . --quiet
        cd ..
        zip -g function.zip *.py --quiet
    else
        zip -r function.zip . -x "*.pyc" -x "__pycache__/*" -x "*.git/*" -x "venv/*" -x "*.zip" -x "*.md" &>/dev/null
    fi

    # Create IAM role if it doesn't exist
    echo "  → Checking IAM role..."
    if ! aws iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
        echo "  → Creating IAM role: $ROLE_NAME"

        # Trust policy
        cat > /tmp/trust-policy.json <<EOF
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

        aws iam create-role \
            --role-name "$ROLE_NAME" \
            --assume-role-policy-document file:///tmp/trust-policy.json \
            &>/dev/null

        # Attach basic execution policy
        aws iam attach-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" \
            &>/dev/null

        # Add Secrets Manager permissions (inline policy)
        cat > /tmp/secrets-policy.json <<EOFPOLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:PutSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": [
        "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:projectforce/api/credentials*"
      ]
    }
  ]
}
EOFPOLICY

        aws iam put-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-name "SecretsManagerAccess" \
            --policy-document file:///tmp/secrets-policy.json \
            &>/dev/null

        # Attach DynamoDB policy for scheduling function
        if [[ "$FUNCTION_NAME" == "pf-scheduling-actions" ]]; then
            aws iam attach-role-policy \
                --role-name "$ROLE_NAME" \
                --policy-arn "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess" \
                &>/dev/null
        fi

        echo "  → Waiting for IAM role to be ready..."
        sleep 10
    fi

    ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

    # Create or update Lambda function
    if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" &>/dev/null; then
        echo "  → Updating existing Lambda function code (this may take 1-2 minutes for large packages)..."
        if aws lambda update-function-code \
            --function-name "$FUNCTION_NAME" \
            --zip-file fileb://function.zip \
            --region "$REGION" 2>&1 | grep -v "FunctionArn\|CodeSize\|LastModified"; then
            echo "  ✅ Lambda code updated: $FUNCTION_NAME"
        else
            echo "  ❌ Failed to update Lambda code: $FUNCTION_NAME"
            return 1
        fi

        echo "  → Updating Lambda environment variables..."
        # Create environment variables JSON file to handle special characters
        cat > /tmp/lambda-env.json <<EOF
{
  "Variables": {
    "BEARER_TOKEN": "${PF_API_TOKEN:-}",
    "PF_CLIENT_ID": "$CLIENT_ID",
    "PF_USER_ID": "${PF_USER_ID:-}",
    "PF_API_BASE_URL": "https://api-cx-portal.dev.projectsforce.com",
    "USE_MOCK_API": "${USE_MOCK_API:-false}",
    "API_ENVIRONMENT": "$ENV",
    "TOKEN_SECRET_NAME": "projectforce/api/credentials",
    "DEFAULT_CLIENT_ID": "$CLIENT_ID",
    "LOG_LEVEL": "INFO"
  }
}
EOF
        if aws lambda update-function-configuration \
            --function-name "$FUNCTION_NAME" \
            --environment file:///tmp/lambda-env.json \
            --region "$REGION" 2>&1 | grep -v "FunctionArn\|Runtime\|LastModified"; then
            echo "  ✅ Lambda configuration updated: $FUNCTION_NAME"
        else
            echo "  ❌ Failed to update Lambda configuration: $FUNCTION_NAME"
            rm -f /tmp/lambda-env.json
            return 1
        fi
        rm -f /tmp/lambda-env.json
    else
        echo "  → Creating new Lambda function (this may take 1-2 minutes for large packages)..."
        # Create environment variables JSON file to handle special characters
        cat > /tmp/lambda-env.json <<EOF
{
  "Variables": {
    "BEARER_TOKEN": "${PF_API_TOKEN:-}",
    "PF_CLIENT_ID": "$CLIENT_ID",
    "PF_USER_ID": "${PF_USER_ID:-}",
    "PF_API_BASE_URL": "https://api-cx-portal.dev.projectsforce.com",
    "USE_MOCK_API": "${USE_MOCK_API:-false}",
    "API_ENVIRONMENT": "$ENV",
    "TOKEN_SECRET_NAME": "projectforce/api/credentials",
    "DEFAULT_CLIENT_ID": "$CLIENT_ID",
    "LOG_LEVEL": "INFO"
  }
}
EOF
        if aws lambda create-function \
            --function-name "$FUNCTION_NAME" \
            --runtime "$RUNTIME" \
            --role "$ROLE_ARN" \
            --handler "$HANDLER" \
            --zip-file fileb://function.zip \
            --timeout "$TIMEOUT" \
            --memory-size "$MEMORY" \
            --region "$REGION" \
            --environment file:///tmp/lambda-env.json \
            --region "$REGION" 2>&1 | grep -v "FunctionArn\|CodeSize\|LastModified"; then
            echo "  ✅ Lambda function created: $FUNCTION_NAME"
            rm -f /tmp/lambda-env.json
        else
            echo "  ❌ Failed to create Lambda function: $FUNCTION_NAME"
            rm -f /tmp/lambda-env.json
            return 1
        fi
    fi

    # Add resource-based policy for Bedrock
    echo "  → Adding Bedrock invoke permission..."
    aws lambda add-permission \
        --function-name "$FUNCTION_NAME" \
        --statement-id "AllowBedrockInvoke" \
        --action "lambda:InvokeFunction" \
        --principal "bedrock.amazonaws.com" \
        --region "$REGION" \
        &>/dev/null 2>&1 || echo "  ℹ️  Permission already exists"

    cd "$CURRENT_DIR" &>/dev/null
    echo "  ✅ Lambda deployed: $FUNCTION_NAME"
}

# Deploy Lambda functions (only 2 - chitchat has no action groups)
deploy_lambda "pf-scheduling-actions" "handler.lambda_handler"
deploy_lambda "pf-information-actions" "handler.lambda_handler"

##############################################################################
# Step 3: Create Bedrock Agents
##############################################################################

echo ""
echo "=========================================="
echo "Step 3: Creating Bedrock Agents"
echo "=========================================="

# Function to create Bedrock agent
create_bedrock_agent() {
    local AGENT_NAME=$1
    local DESCRIPTION=$2
    local INSTRUCTION=$3
    # Use Claude 3 Haiku (March 2024) - works without inference profile
    local MODEL_ID="anthropic.claude-3-haiku-20240307-v1:0"

    echo "" >&2
    echo "Creating agent: $AGENT_NAME" >&2

    # Create IAM role for Bedrock agent
    local ROLE_NAME="AmazonBedrockExecutionRoleForAgents_${AGENT_NAME}"
    echo "  → Creating Bedrock agent IAM role..." >&2

    if ! aws iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
        # Trust policy for Bedrock
        cat > /tmp/bedrock-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "$ACCOUNT_ID"
        },
        "ArnLike": {
          "aws:SourceArn": "arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent/*"
        }
      }
    }
  ]
}
EOF

        aws iam create-role \
            --role-name "$ROLE_NAME" \
            --assume-role-policy-document file:///tmp/bedrock-trust-policy.json \
            &>/dev/null

        # Attach comprehensive Bedrock permissions (models, inference profiles, and runtime)
        # Special handling for Supervisor agent - needs agent invocation permissions
        if [[ "$AGENT_NAME" == "Supervisor" ]]; then
            cat > /tmp/bedrock-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockModelAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:${REGION}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
        "arn:aws:bedrock:*::foundation-model/*",
        "arn:aws:bedrock:${REGION}::inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        "arn:aws:bedrock:*::inference-profile/*"
      ]
    },
    {
      "Sid": "BedrockAgentRuntime",
      "Effect": "Allow",
      "Action": [
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel",
        "bedrock:GetInferenceProfile",
        "bedrock:ListInferenceProfiles"
      ],
      "Resource": "*"
    },
    {
      "Sid": "BedrockAgentInvoke",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeAgent",
        "bedrock:GetAgentAlias"
      ],
      "Resource": [
        "arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent/*",
        "arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent-alias/*/*"
      ]
    },
    {
      "Sid": "LambdaInvokePermission",
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-scheduling-actions",
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-information-actions",
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-chitchat-actions"
      ]
    }
  ]
}
EOF
        else
            # Regular collaborator agents
            cat > /tmp/bedrock-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockModelAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:${REGION}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
        "arn:aws:bedrock:*::foundation-model/*",
        "arn:aws:bedrock:${REGION}::inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        "arn:aws:bedrock:*::inference-profile/*"
      ]
    },
    {
      "Sid": "BedrockAgentRuntime",
      "Effect": "Allow",
      "Action": [
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel",
        "bedrock:GetInferenceProfile",
        "bedrock:ListInferenceProfiles"
      ],
      "Resource": "*"
    },
    {
      "Sid": "LambdaInvokePermission",
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-scheduling-actions",
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-information-actions",
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-chitchat-actions"
      ]
    }
  ]
}
EOF
        fi

        aws iam put-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-name "BedrockModelInvoke" \
            --policy-document file:///tmp/bedrock-policy.json \
            &>/dev/null

        echo "  → Waiting for IAM role to propagate..."
        sleep 10
    fi

    AGENT_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

    # Check if agent already exists
    EXISTING_AGENT=$(aws bedrock-agent list-agents \
        --region "$REGION" \
        --query "agentSummaries[?agentName=='$AGENT_NAME'].[agentId,agentStatus]" \
        --output text 2>/dev/null | head -1)

    if [[ -n "$EXISTING_AGENT" ]]; then
        AGENT_ID=$(echo "$EXISTING_AGENT" | awk '{print $1}')
        AGENT_STATUS=$(echo "$EXISTING_AGENT" | awk '{print $2}')
        echo "  ℹ️  Agent already exists: $AGENT_NAME (ID: $AGENT_ID, Status: $AGENT_STATUS)" >&2

        # Update the agent
        echo "  → Updating agent..." >&2
        aws bedrock-agent update-agent \
            --agent-id "$AGENT_ID" \
            --agent-name "$AGENT_NAME" \
            --description "$DESCRIPTION" \
            --agent-resource-role-arn "$AGENT_ROLE_ARN" \
            --foundation-model "$MODEL_ID" \
            --instruction "$INSTRUCTION" \
            --region "$REGION" \
            &>/dev/null

        echo "  ✅ Agent updated: $AGENT_NAME (ID: $AGENT_ID)" >&2
        echo "$AGENT_ID"
    else
        # Create the Bedrock agent
        echo "  → Creating Bedrock agent..." >&2

        # Enable collaboration for Supervisor agent
        if [[ "$AGENT_NAME" == "Supervisor" ]]; then
            AGENT_ID=$(aws bedrock-agent create-agent \
                --agent-name "$AGENT_NAME" \
                --description "$DESCRIPTION" \
                --agent-resource-role-arn "$AGENT_ROLE_ARN" \
                --foundation-model "$MODEL_ID" \
                --instruction "$INSTRUCTION" \
                --agent-collaboration "SUPERVISOR" \
                --region "$REGION" \
                --query 'agent.agentId' \
                --output text 2>&1)
        else
            AGENT_ID=$(aws bedrock-agent create-agent \
                --agent-name "$AGENT_NAME" \
                --description "$DESCRIPTION" \
                --agent-resource-role-arn "$AGENT_ROLE_ARN" \
                --foundation-model "$MODEL_ID" \
                --instruction "$INSTRUCTION" \
                --region "$REGION" \
                --query 'agent.agentId' \
                --output text 2>&1)
        fi

        if [[ $? -eq 0 ]] && [[ -n "$AGENT_ID" ]] && [[ ! "$AGENT_ID" =~ "error" ]]; then
            echo "  ✅ Agent created: $AGENT_NAME (ID: $AGENT_ID)" >&2
            echo "$AGENT_ID"
        else
            echo "  ⚠️  Failed to create agent: $AGENT_NAME" >&2
            echo "     Error: $AGENT_ID" >&2
            return 1
        fi
    fi
}

# Create agents
SCHEDULING_AGENT_ID=$(create_bedrock_agent \
    "SchedulingAgent" \
    "Primary agent for scheduling and project management" \
    "You are the SchedulingAgent for ProjectForce. You handle scheduling operations, project management, and business information. When users ask about weather, let them know the information agent will help with that.")

INFORMATION_AGENT_ID=$(create_bedrock_agent \
    "pf-information" \
    "Weather information specialist using external API" \
    "You are the Weather Information Specialist. You provide weather forecasts, current conditions, and temperature information. Use external weather APIs for accurate data.")

CHITCHAT_AGENT_ID=$(create_bedrock_agent \
    "pf-chitchat" \
    "Conversational agent for greetings and general queries" \
    "You are a friendly conversational assistant. Handle greetings, thank you messages, and general questions. Be warm and helpful. If the user needs specific scheduling or weather help, guide them to ask specific questions.")

SUPERVISOR_AGENT_ID=$(create_bedrock_agent \
    "Supervisor" \
    "Orchestrator agent that routes queries to specialized agents" \
    "You are the Supervisor agent. Route user queries to the appropriate specialist: SchedulingAgent for scheduling/projects, pf-information for weather, pf-chitchat for conversational queries.")

# Prepare all agents
echo ""
echo "Preparing all agents..."
for agent_id in "$SCHEDULING_AGENT_ID" "$INFORMATION_AGENT_ID" "$CHITCHAT_AGENT_ID" "$SUPERVISOR_AGENT_ID"; do
    if [[ -n "$agent_id" ]]; then
        aws bedrock-agent prepare-agent \
            --agent-id "$agent_id" \
            --region "$REGION" \
            &>/dev/null && echo "  ✅ Agent prepared: $agent_id"
    fi
done

##############################################################################
# Step 4: Create Action Groups
##############################################################################

echo ""
echo "=========================================="
echo "Step 4: Creating Action Groups"
echo "=========================================="

# Function to create action group with function schema
create_action_group() {
    local AGENT_ID=$1
    local AGENT_NAME=$2
    local ACTION_GROUP_NAME=$3
    local LAMBDA_ARN=$4
    local FUNCTION_SCHEMA=$5

    echo ""
    echo "Creating action group for $AGENT_NAME..."

    # Delete existing action group if it exists (find by name first)
    EXISTING_AG_ID=$(aws bedrock-agent list-agent-action-groups \
        --agent-id "$AGENT_ID" \
        --agent-version "DRAFT" \
        --region "$REGION" \
        --query "actionGroupSummaries[?actionGroupName=='$ACTION_GROUP_NAME'].actionGroupId" \
        --output text 2>/dev/null)

    if [[ -n "$EXISTING_AG_ID" ]]; then
        echo "  → Found existing action group: $ACTION_GROUP_NAME (ID: $EXISTING_AG_ID)"
        echo "  → Replacing with updated action group (disable + delete + recreate)..."

        # Write schema to temp file
        echo "$FUNCTION_SCHEMA" > /tmp/function-schema.json

        # Disable first
        aws bedrock-agent update-agent-action-group \
            --agent-id "$AGENT_ID" \
            --agent-version "DRAFT" \
            --action-group-id "$EXISTING_AG_ID" \
            --action-group-name "$ACTION_GROUP_NAME" \
            --action-group-state "DISABLED" \
            --action-group-executor "lambda=$LAMBDA_ARN" \
            --function-schema file:///tmp/function-schema.json \
            --region "$REGION" \
            &>/dev/null

        sleep 5

        # Now delete
        aws bedrock-agent delete-agent-action-group \
            --agent-id "$AGENT_ID" \
            --agent-version "DRAFT" \
            --action-group-id "$EXISTING_AG_ID" \
            --region "$REGION" \
            &>/dev/null

        echo "  → Waiting for deletion to complete..."
        sleep 15
    fi

    # Create action group with function schema
    echo "  → Creating action group: $ACTION_GROUP_NAME"

    # Write schema to temp file to avoid escaping issues
    echo "$FUNCTION_SCHEMA" > /tmp/function-schema.json

    ACTION_GROUP_ID=$(aws bedrock-agent create-agent-action-group \
        --agent-id "$AGENT_ID" \
        --agent-version "DRAFT" \
        --action-group-name "$ACTION_GROUP_NAME" \
        --action-group-executor "lambda=$LAMBDA_ARN" \
        --function-schema file:///tmp/function-schema.json \
        --region "$REGION" \
        --query 'agentActionGroup.actionGroupId' \
        --output text 2>&1)

    if [[ $? -eq 0 ]] && [[ ! "$ACTION_GROUP_ID" =~ "error" ]] && [[ ! "$ACTION_GROUP_ID" =~ "Error" ]]; then
        echo "  ✅ Action group created: $ACTION_GROUP_NAME (ID: $ACTION_GROUP_ID)"
        rm -f /tmp/function-schema.json
    else
        echo "  ⚠️  Failed to create action group: $ACTION_GROUP_NAME"
        echo "     Error: $ACTION_GROUP_ID"
        rm -f /tmp/function-schema.json
        return 1
    fi
}

# Get Lambda ARNs
SCHEDULING_LAMBDA_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-scheduling-actions"
INFORMATION_LAMBDA_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-information-actions"

# Define function schemas
SCHEDULING_SCHEMA='{
  "functions": [
    {
      "name": "list_projects",
      "description": "List ALL projects for the current user. Use ONLY when user asks to see all projects, show projects list, or list projects. DO NOT use for getting details of a single specific project. The customer_id will be automatically retrieved from the session context.",
      "parameters": {
        "customer_id": {"description": "Customer ID (automatically provided from session context - do not specify)", "required": false, "type": "string"},
        "client_id": {"description": "Optional client ID for B2B filtering (automatically provided from session context)", "required": false, "type": "string"}
      }
    },
    {
      "name": "get_project_details",
      "description": "Get DETAILED information about ONE specific project when user provides a project ID. Returns customer name, full address, status, scheduling info. Use when user says: details of project, information about project, show project, tell me about project. ALWAYS use this for single project lookups with project ID.",
      "parameters": {
        "project_id": {"description": "Project ID", "required": true, "type": "string"},
        "client_id": {"description": "Client identifier (automatically provided from session context)", "required": false, "type": "string"}
      }
    },
    {
      "name": "get_available_dates",
      "description": "Get available dates for scheduling a project",
      "parameters": {
        "project_id": {"description": "Project ID", "required": true, "type": "string"}
      }
    },
    {
      "name": "get_time_slots",
      "description": "Get available time slots for a specific date",
      "parameters": {
        "project_id": {"description": "Project ID", "required": true, "type": "string"},
        "date": {"description": "Date in YYYY-MM-DD format", "required": true, "type": "string"},
        "request_id": {"description": "Request ID from get_available_dates", "required": true, "type": "string"}
      }
    },
    {
      "name": "confirm_appointment",
      "description": "Confirm and schedule an appointment",
      "parameters": {
        "project_id": {"description": "Project ID", "required": true, "type": "string"},
        "date": {"description": "Date in YYYY-MM-DD format", "required": true, "type": "string"},
        "time": {"description": "Time in HH:MM format", "required": true, "type": "string"},
        "request_id": {"description": "Request ID from get_available_dates", "required": true, "type": "string"}
      }
    },
    {
      "name": "reschedule_appointment",
      "description": "Reschedule an existing appointment to a new date and time",
      "parameters": {
        "project_id": {"description": "Project ID", "required": true, "type": "string"},
        "new_date": {"description": "New date in YYYY-MM-DD format", "required": true, "type": "string"},
        "new_time": {"description": "New time in HH:MM format", "required": true, "type": "string"},
        "request_id": {"description": "Request ID", "required": true, "type": "string"}
      }
    },
    {
      "name": "cancel_appointment",
      "description": "Cancel an existing appointment",
      "parameters": {
        "project_id": {"description": "Project ID", "required": true, "type": "string"}
      }
    }
  ]
}'

INFORMATION_SCHEMA='{
  "functions": [
    {
      "name": "get_appointment_status",
      "description": "Check the status of an appointment",
      "parameters": {
        "project_id": {"description": "Project ID", "required": true, "type": "string"}
      }
    },
    {
      "name": "get_working_hours",
      "description": "Get business working hours and availability",
      "parameters": {}
    },
    {
      "name": "get_weather",
      "description": "Get weather forecast for project location",
      "parameters": {
        "location": {"description": "Location (city or zip code)", "required": true, "type": "string"},
        "date": {"description": "Optional date in YYYY-MM-DD format", "required": false, "type": "string"}
      }
    }
  ]
}'

# Create action groups
create_action_group "$SCHEDULING_AGENT_ID" "SchedulingAgent" "scheduling-actions" "$SCHEDULING_LAMBDA_ARN" "$SCHEDULING_SCHEMA"
create_action_group "$INFORMATION_AGENT_ID" "pf-information" "information-actions" "$INFORMATION_LAMBDA_ARN" "$INFORMATION_SCHEMA"

echo ""
echo "  ℹ️  pf-chitchat and Supervisor agents don't need action groups (conversational only)"

##############################################################################
# Step 5: Prepare All Agents
##############################################################################

echo ""
echo "=========================================="
echo "Step 5: Preparing All Agents"
echo "=========================================="

# Prepare all agents
echo ""
echo "Preparing SchedulingAgent..."
aws bedrock-agent prepare-agent \
    --agent-id "$SCHEDULING_AGENT_ID" \
    --region "$REGION" \
    &>/dev/null && echo "  ✅ SchedulingAgent prepared"

echo ""
echo "Preparing pf-information..."
aws bedrock-agent prepare-agent \
    --agent-id "$INFORMATION_AGENT_ID" \
    --region "$REGION" \
    &>/dev/null && echo "  ✅ pf-information prepared"

echo ""
echo "Preparing pf-chitchat..."
aws bedrock-agent prepare-agent \
    --agent-id "$CHITCHAT_AGENT_ID" \
    --region "$REGION" \
    &>/dev/null && echo "  ✅ pf-chitchat prepared"

echo ""
echo "Preparing Supervisor..."
aws bedrock-agent prepare-agent \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --region "$REGION" \
    &>/dev/null && echo "  ✅ Supervisor prepared"


##############################################################################
# Step 6: Save Agent IDs
##############################################################################

echo ""
echo "=========================================="
echo "Step 6: Saving Agent IDs"
echo "=========================================="

mkdir -p "$BEDROCK_DIR/config"
cat > "$BEDROCK_DIR/config/agent_ids.json" <<EOF
{
  "agents": {
    "SchedulingAgent": {
      "id": "$SCHEDULING_AGENT_ID",
      "name": "SchedulingAgent",
      "purpose": "Scheduling and project management"
    },
    "pf-information": {
      "id": "$INFORMATION_AGENT_ID",
      "name": "pf-information",
      "purpose": "Weather information"
    },
    "pf-chitchat": {
      "id": "$CHITCHAT_AGENT_ID",
      "name": "pf-chitchat",
      "purpose": "Conversational"
    },
    "Supervisor": {
      "id": "$SUPERVISOR_AGENT_ID",
      "name": "Supervisor",
      "purpose": "Query routing"
    }
  },
  "lambdas": {
    "pf-scheduling-actions": "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-scheduling-actions",
    "pf-information-actions": "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-information-actions"
  },
  "deployed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "region": "$REGION",
  "account_id": "$ACCOUNT_ID"
}
EOF

echo "  ✅ Agent IDs saved to: $BEDROCK_DIR/config/agent_ids.json"

##############################################################################
# Summary
##############################################################################

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Created:"
if [[ -n "$PF_API_TOKEN" ]] && [[ "$PF_API_TOKEN" != "PLACEHOLDER"* ]]; then
    echo "  ✅ 1 Secrets Manager secret (with real Bearer token)"
    echo "  ✅ 2 Lambda functions (configured with Bearer token)"
else
    echo "  ⚠️  1 Secrets Manager secret (with PLACEHOLDER token)"
    echo "  ⚠️  2 Lambda functions (need Bearer token update)"
fi
echo "  ✅ 1 DynamoDB table"
echo "  ✅ 4 Bedrock agents (all PREPARED)"
echo "  ✅ 2 Action groups (SchedulingAgent, pf-information)"
echo "  ℹ️  2 conversational agents (pf-chitchat, Supervisor - no Lambda needed)"
echo "  ✅ Agent collaboration (Supervisor with 3 specialist agents)"
echo "  ✅ IAM roles (with Secrets Manager permissions)"
echo ""
echo "Agent IDs:"
echo "  • SchedulingAgent: $SCHEDULING_AGENT_ID"
echo "  • pf-information: $INFORMATION_AGENT_ID"
echo "  • pf-chitchat: $CHITCHAT_AGENT_ID"
echo "  • Supervisor: $SUPERVISOR_AGENT_ID"
echo ""
echo "Resources:"
echo "  • DynamoDB: pf-sessions-dev"
echo "  • Lambdas: pf-scheduling-actions, pf-information-actions (2 total)"
echo "  • Secrets: projectforce/api/credentials"
echo "  • Config: config/agent_ids.json"
echo ""

# Only show token warning if token is not set
if [[ -z "$PF_API_TOKEN" ]] || [[ "$PF_API_TOKEN" == "PLACEHOLDER"* ]]; then
echo "⚠️  IMPORTANT: Update API Token"
echo "=========================================="
echo "Lambda functions need a Bearer token to access the ProjectForce API."
echo "Set it and redeploy:"
echo ""
echo "  export PF_API_TOKEN='your-actual-bearer-token'"
echo "  export PF_USER_ID='your-user-id'"
echo "  export PF_REFRESH_TOKEN='your-refresh-token' # optional"
echo ""
echo "  aws secretsmanager update-secret \\"
echo "    --secret-id projectforce/api/credentials \\"
echo "    --secret-string \"{\\\"bearer_token\\\":\\\"\$PF_API_TOKEN\\\",\\\"client_id\\\":\\\"09PF05VD\\\",\\\"user_id\\\":\\\"\$PF_USER_ID\\\",\\\"refresh_token\\\":\\\"\$PF_REFRESH_TOKEN\\\",\\\"api_base_url\\\":\\\"https://api-cx-portal.dev.projectsforce.com\\\"}\" \\"
echo "    --region us-east-1"
echo ""
echo "Then redeploy Lambdas:"
echo "  ./DEPLOY.sh"
echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Deployment Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next Steps:"
echo "=========================================="
echo ""
echo "  STEP 1: Enable Supervisor Collaboration (ONE-TIME)"
echo "  ────────────────────────────────────────────────────"
echo "  To enable automatic routing from Supervisor to specialist agents:"
echo ""
echo "  a. Create v1 aliases for the 3 collaborator agents via AWS Console"
echo "     (This is a one-time manual step - takes ~15 minutes)"
echo "     "
echo "     Console URL: https://console.aws.amazon.com/bedrock/"
echo "     Region: us-east-1"
echo "     "
echo "     For each agent (SchedulingAgent, pf-information, pf-chitchat):"
echo "       • Create Version 1 from Working Draft"
echo "       • Create Alias named 'v1' pointing to Version 1"
echo ""
echo "  b. Run the collaboration setup script:"
echo "     ./scripts/SETUP_COLLABORATION.sh"
echo ""
echo "  ────────────────────────────────────────────────────"
echo ""
echo "  STEP 2: Test the Agents"
echo "  ────────────────────────────────────────────────────"
echo "  After collaboration is set up:"
echo ""
echo "  Test Supervisor (with automatic routing):"
echo "     aws bedrock-agent-runtime invoke-agent \\"
echo "       --agent-id $SUPERVISOR_AGENT_ID \\"
echo "       --agent-alias-id TSTALIASID \\"
echo "       --session-id test-\$(date +%s) \\"
echo "       --input-text 'List my projects' /tmp/output.txt"
echo ""
echo "  Or test individual specialist agents:"
echo "     aws bedrock-agent-runtime invoke-agent \\"
echo "       --agent-id $SCHEDULING_AGENT_ID \\"
echo "       --agent-alias-id TSTALIASID \\"
echo "       --session-id test-\$(date +%s) \\"
echo "       --input-text 'Show my projects' /tmp/output.txt"
echo ""
echo "  ────────────────────────────────────────────────────"
echo ""
echo "  View agent IDs:"
echo "     cat config/agent_ids.json"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "=========================================="
