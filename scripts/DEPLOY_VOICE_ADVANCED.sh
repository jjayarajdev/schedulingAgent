#!/bin/bash

# ============================================================================
# ProjectForce Advanced Voice Lambda Deployment
# ============================================================================
# Purpose: Deploy Lex Fulfillment and Voice Bedrock Bridge Lambda functions
# Features: Cross-platform, proper IAM role management, error-resilient
# Platform: Windows (Git Bash), Linux, macOS
# ============================================================================

set -e

# ============================================================================
# Colors
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ============================================================================
# Configuration
# ============================================================================
REGION="${AWS_REGION:-us-east-1}"
ENVIRONMENT="dev"
PREFIX="pf"

# Lambda function names
LEX_FULFILLMENT_FUNCTION="pf-lex-fulfillment-${ENVIRONMENT}"
VOICE_BRIDGE_FUNCTION="pf-voice-bedrock-bridge-${ENVIRONMENT}"

# Lambda source directories
LEX_FULFILLMENT_DIR="lambda/lex-fulfillment"
VOICE_BRIDGE_DIR="lambda/voice-bedrock-bridge"

# IAM role names
LEX_FULFILLMENT_ROLE="pf-lex-fulfillment-role-${ENVIRONMENT}"
VOICE_BRIDGE_ROLE="pf-voice-bedrock-bridge-role-${ENVIRONMENT}"

# ============================================================================
# Platform Detection & Python Command
# ============================================================================
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    PYTHON_CMD="python"
    PLATFORM="Windows (Git Bash)"
else
    PYTHON_CMD="python3"
    PLATFORM="Unix/Linux/Mac"
fi

# ============================================================================
# Helper Functions
# ============================================================================

# AWS command wrapper for error logging
aws_cmd() {
    aws "$@"
}

# Get AWS account ID
get_account_id() {
    aws_cmd sts get-caller-identity --query Account --output text 2>&1
}

# Create IAM role with proper error handling and propagation polling
create_iam_role() {
    local ROLE_NAME=$1
    local SERVICE_PRINCIPAL=$2
    local DESCRIPTION=$3

    echo "  → Creating IAM role: $ROLE_NAME"

    # Check if role already exists
    if aws_cmd iam get-role --role-name "$ROLE_NAME" 2>&1 | grep -q "NoSuchEntity"; then
        echo "    Role does not exist, creating..."
    else
        echo "  ℹ️  IAM role already exists: $ROLE_NAME"
        return 0
    fi

    # Create trust policy file (using current directory instead of /tmp/)
    local TRUST_POLICY_FILE="./trust-policy-${ROLE_NAME}.json"

    cat > "$TRUST_POLICY_FILE" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "$SERVICE_PRINCIPAL"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

    # Create the IAM role with error logging (not suppression)
    if ! aws_cmd iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document "file://${TRUST_POLICY_FILE}" \
        --description "$DESCRIPTION" 2>&1 | tee "./iam-create-$ROLE_NAME.log"; then
        echo "  ❌ Failed to create IAM role $ROLE_NAME"
        rm -f "$TRUST_POLICY_FILE"
        return 1
    fi

    # Clean up trust policy file
    rm -f "$TRUST_POLICY_FILE"

    echo "  ✓ IAM role created"

    # Poll for role propagation (10s intervals, 60s timeout, early exit when ready)
    echo "  → Waiting for IAM role to propagate..."
    local MAX_WAIT=60
    local POLL_INTERVAL=10
    local ELAPSED=0
    local ROLE_READY=false

    while [[ $ELAPSED -lt $MAX_WAIT ]]; do
        if aws_cmd iam get-role --role-name "$ROLE_NAME" 2>&1 | grep -q "Role"; then
            ROLE_READY=true
            echo "  ✓ IAM role propagated (checked at ${ELAPSED}s)"
            break
        fi
        sleep $POLL_INTERVAL
        ELAPSED=$((ELAPSED + POLL_INTERVAL))
        echo "    Polling... ${ELAPSED}s elapsed"
    done

    if [[ "$ROLE_READY" != "true" ]]; then
        echo "  ⚠️  Warning: IAM role may not be fully propagated after ${MAX_WAIT}s"
    fi

    return 0
}

# Attach managed policy to role
attach_managed_policy() {
    local ROLE_NAME=$1
    local POLICY_ARN=$2

    echo "  → Attaching policy: $(basename $POLICY_ARN)"

    if ! aws_cmd iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn "$POLICY_ARN" 2>&1 | tee "./iam-attach-policy-$ROLE_NAME.log"; then
        echo "  ⚠️  Warning: Failed to attach policy $POLICY_ARN"
        return 1
    fi

    echo "  ✓ Policy attached"
    return 0
}

# Create inline policy for role
create_inline_policy() {
    local ROLE_NAME=$1
    local POLICY_NAME=$2
    local POLICY_DOCUMENT=$3

    echo "  → Creating inline policy: $POLICY_NAME"

    # Write policy document to file (using current directory)
    local POLICY_FILE="./policy-${ROLE_NAME}-${POLICY_NAME}.json"
    echo "$POLICY_DOCUMENT" > "$POLICY_FILE"

    if ! aws_cmd iam put-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-name "$POLICY_NAME" \
        --policy-document "file://${POLICY_FILE}" 2>&1 | tee "./iam-inline-policy-$ROLE_NAME-$POLICY_NAME.log"; then
        echo "  ⚠️  Warning: Failed to create inline policy $POLICY_NAME"
        rm -f "$POLICY_FILE"
        return 1
    fi

    rm -f "$POLICY_FILE"
    echo "  ✓ Inline policy created"
    return 0
}

# Package Lambda function using Python zipfile module (cross-platform)
package_lambda() {
    local SOURCE_DIR=$1
    local OUTPUT_ZIP=$2

    echo "  → Packaging with Python zipfile module..."

    if [ ! -d "$SOURCE_DIR" ]; then
        echo "  ❌ Source directory not found: $SOURCE_DIR"
        return 1
    fi

    # Store original directory
    local ORIG_DIR=$(pwd)

    cd "$SOURCE_DIR"

    # Remove old packages
    rm -f "$OUTPUT_ZIP" 2>/dev/null || true
    rm -rf package 2>/dev/null || true

    # Install dependencies if requirements.txt exists
    if [ -f "requirements.txt" ] && [ -s "requirements.txt" ]; then
        echo "  → Installing dependencies..."
        mkdir -p package

        # Use detected Python command
        if ! $PYTHON_CMD -m pip install -r requirements.txt -t package/ --upgrade 2>&1 | tee "../../pip-install-$(basename $SOURCE_DIR).log"; then
            echo "  ⚠️  Warning: Some dependencies may have failed to install"
        fi

        # Package dependencies
        cd package
        $PYTHON_CMD -m zipfile -c "../$OUTPUT_ZIP" .
        cd ..

        # Add handler to zip
        $PYTHON_CMD -m zipfile -c temp.zip handler.py
        $PYTHON_CMD << 'PYTHON_SCRIPT'
import zipfile
import sys

# Merge zips
with zipfile.ZipFile('function.zip', 'a') as base_zip:
    with zipfile.ZipFile('temp.zip', 'r') as temp_zip:
        for item in temp_zip.namelist():
            base_zip.writestr(item, temp_zip.read(item))
PYTHON_SCRIPT
        rm -f temp.zip
    else
        # No dependencies, just package handler
        $PYTHON_CMD -m zipfile -c "$OUTPUT_ZIP" handler.py
    fi

    if [ ! -f "$OUTPUT_ZIP" ]; then
        echo "  ❌ Failed to create package: $OUTPUT_ZIP"
        cd "$ORIG_DIR"
        return 1
    fi

    local PACKAGE_SIZE=$(ls -lh "$OUTPUT_ZIP" | awk '{print $5}')
    echo "  ✓ Package created: $OUTPUT_ZIP ($PACKAGE_SIZE)"

    # Return to original directory
    cd "$ORIG_DIR"
    return 0
}

# Deploy Lambda function
deploy_lambda() {
    local FUNCTION_NAME=$1
    local ROLE_NAME=$2
    local SOURCE_DIR=$3
    local HANDLER=$4
    local RUNTIME=$5
    local DESCRIPTION=$6

    echo ""
    echo "Deploying: $FUNCTION_NAME"

    # Convert SOURCE_DIR to absolute path BEFORE packaging
    local ABS_SOURCE_DIR="$(cd "$SOURCE_DIR" && pwd)"

    # Convert Unix-style path to Windows path if on Windows (Git Bash)
    if command -v cygpath &> /dev/null; then
        ZIP_PATH="$(cygpath -w "${ABS_SOURCE_DIR}/function.zip")"
    else
        ZIP_PATH="${ABS_SOURCE_DIR}/function.zip"
    fi

    # Package the Lambda
    if ! package_lambda "$SOURCE_DIR" "function.zip"; then
        echo "  ❌ Packaging failed for $FUNCTION_NAME"
        return 1
    fi

    # Get role ARN
    local ACCOUNT_ID=$(get_account_id)
    local ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

    # Check if Lambda exists
    if aws_cmd lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" 2>&1 | grep -q "ResourceNotFoundException"; then
        echo "  → Creating new function..."

        if ! aws_cmd lambda create-function \
            --function-name "$FUNCTION_NAME" \
            --runtime "$RUNTIME" \
            --role "$ROLE_ARN" \
            --handler "$HANDLER" \
            --zip-file "fileb://${ZIP_PATH}" \
            --description "$DESCRIPTION" \
            --timeout 60 \
            --memory-size 512 \
            --region "$REGION" 2>&1 | tee "./lambda-create-$FUNCTION_NAME.log"; then
            echo "  ❌ Failed to create Lambda function $FUNCTION_NAME"
            return 1
        fi

        echo -e "  ${GREEN}✅ Lambda created: $FUNCTION_NAME${NC}"
    else
        echo "  → Updating existing function code..."

        if ! aws_cmd lambda update-function-code \
            --function-name "$FUNCTION_NAME" \
            --zip-file "fileb://${ZIP_PATH}" \
            --region "$REGION" 2>&1 | tee "./lambda-update-$FUNCTION_NAME.log"; then
            echo "  ❌ Failed to update Lambda function $FUNCTION_NAME"
            return 1
        fi

        echo -e "  ${GREEN}✅ Lambda updated: $FUNCTION_NAME${NC}"
    fi

    # Clean up zip file (convert back to Unix path for rm if needed)
    if command -v cygpath &> /dev/null; then
        rm -f "$(cygpath -u "$ZIP_PATH")"
    else
        rm -f "$ZIP_PATH"
    fi

    return 0
}

# ============================================================================
# Main Deployment
# ============================================================================

echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🚀 ProjectForce Advanced Voice Lambda Deployment${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Region: $REGION"
echo "Account: $(get_account_id)"
echo "Environment: $ENVIRONMENT"
echo "Platform: $PLATFORM"
echo "Python: $PYTHON_CMD"
echo ""
echo "✨ Features:"
echo "  • Cross-platform Python-only packaging (no zip command needed)"
echo "  • Proper IAM role management"
echo "  • Error-resilient deployment"
echo ""

# ============================================================================
# Step 1: Create IAM Roles
# ============================================================================

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 1: Creating IAM Roles${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Create Lex Fulfillment Role
create_iam_role "$LEX_FULFILLMENT_ROLE" "lambda.amazonaws.com" "Role for Lex fulfillment Lambda function"

# Attach managed policies
attach_managed_policy "$LEX_FULFILLMENT_ROLE" "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

# Create inline policy for Lex fulfillment
ACCOUNT_ID=$(get_account_id)

LEX_FULFILLMENT_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/pf-sessions-${ENVIRONMENT}",
        "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/pf-notes-${ENVIRONMENT}",
        "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/pf-workflow-states-${ENVIRONMENT}"
      ]
    },
    {
      "Sid": "LambdaInvoke",
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-voice-bedrock-bridge-${ENVIRONMENT}"
    },
    {
      "Sid": "SecretsManagerAccess",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:projectforce/api/credentials*"
    }
  ]
}
EOF
)

create_inline_policy "$LEX_FULFILLMENT_ROLE" "LexFulfillmentPolicy" "$LEX_FULFILLMENT_POLICY"

echo ""

# Create Voice Bedrock Bridge Role
create_iam_role "$VOICE_BRIDGE_ROLE" "lambda.amazonaws.com" "Role for voice Bedrock bridge Lambda function"

# Attach managed policies
attach_managed_policy "$VOICE_BRIDGE_ROLE" "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

# Create inline policy for Voice Bridge
VOICE_BRIDGE_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockAgentInvoke",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeAgent",
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent/*",
        "arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent-alias/*/*"
      ]
    },
    {
      "Sid": "DynamoDBAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/pf-sessions-${ENVIRONMENT}"
      ]
    }
  ]
}
EOF
)

create_inline_policy "$VOICE_BRIDGE_ROLE" "VoiceBridgePolicy" "$VOICE_BRIDGE_POLICY"

echo ""

# ============================================================================
# Step 2: Deploy Lambda Functions
# ============================================================================

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 2: Deploying Lambda Functions${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Deploy Lex Fulfillment Lambda
deploy_lambda \
    "$LEX_FULFILLMENT_FUNCTION" \
    "$LEX_FULFILLMENT_ROLE" \
    "$LEX_FULFILLMENT_DIR" \
    "handler.lambda_handler" \
    "python3.11" \
    "Lex fulfillment handler for voice integration"

# Deploy Voice Bedrock Bridge Lambda
deploy_lambda \
    "$VOICE_BRIDGE_FUNCTION" \
    "$VOICE_BRIDGE_ROLE" \
    "$VOICE_BRIDGE_DIR" \
    "handler.lambda_handler" \
    "python3.11" \
    "Voice to Bedrock agent bridge for voice integration"

echo ""

# ============================================================================
# Step 3: Grant Permissions
# ============================================================================

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 3: Granting Lambda Invoke Permissions${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Grant Lex permission to invoke Lex Fulfillment Lambda
echo "  → Granting Lex V2 permission to invoke $LEX_FULFILLMENT_FUNCTION..."

LEX_PERM_RESULT=$(aws_cmd lambda add-permission \
    --function-name "$LEX_FULFILLMENT_FUNCTION" \
    --statement-id "AllowLexInvoke" \
    --action "lambda:InvokeFunction" \
    --principal "lexv2.amazonaws.com" \
    --region "$REGION" 2>&1 || echo "")

if echo "$LEX_PERM_RESULT" | grep -q "ResourceConflictException"; then
    echo "  ℹ️  Permission already exists"
elif echo "$LEX_PERM_RESULT" | grep -q "error\|Error"; then
    echo "  ⚠️  Warning: Failed to add Lex permission"
    echo "$LEX_PERM_RESULT"
else
    echo "  ✓ Lex permission granted"
fi

echo ""

# Grant Connect permission to invoke both Lambda functions
for FUNCTION_NAME in "$LEX_FULFILLMENT_FUNCTION" "$VOICE_BRIDGE_FUNCTION"; do
    echo "  → Granting AWS Connect permission to invoke $FUNCTION_NAME..."

    CONNECT_PERM_RESULT=$(aws_cmd lambda add-permission \
        --function-name "$FUNCTION_NAME" \
        --statement-id "AllowConnectInvoke" \
        --action "lambda:InvokeFunction" \
        --principal "connect.amazonaws.com" \
        --region "$REGION" 2>&1 || echo "")

    if echo "$CONNECT_PERM_RESULT" | grep -q "ResourceConflictException"; then
        echo "  ℹ️  Permission already exists"
    elif echo "$CONNECT_PERM_RESULT" | grep -q "error\|Error"; then
        echo "  ⚠️  Warning: Failed to add Connect permission"
        echo "$CONNECT_PERM_RESULT"
    else
        echo "  ✓ Connect permission granted"
    fi

    echo ""
done

# ============================================================================
# Deployment Summary
# ============================================================================

echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

echo "Deployed Lambda Functions:"
echo "  ✅ $LEX_FULFILLMENT_FUNCTION (python3.11)"
echo "  ✅ $VOICE_BRIDGE_FUNCTION (python3.11)"
echo ""

echo "IAM Roles Created:"
echo "  ✅ $LEX_FULFILLMENT_ROLE"
echo "  ✅ $VOICE_BRIDGE_ROLE"
echo ""

echo "Permissions Granted:"
echo "  ✅ Lex V2 → $LEX_FULFILLMENT_FUNCTION"
echo "  ✅ AWS Connect → $LEX_FULFILLMENT_FUNCTION"
echo "  ✅ AWS Connect → $VOICE_BRIDGE_FUNCTION"
echo ""

echo -e "${CYAN}Next Steps:${NC}"
echo ""
echo "1. Configure Lex Bot:"
echo "   - Build the Lex bot in AWS Console"
echo "   - Set fulfillment Lambda: $LEX_FULFILLMENT_FUNCTION"
echo ""
echo "2. Configure AWS Connect:"
echo "   - Create contact flow"
echo "   - Add Lex bot to contact flow"
echo "   - Associate phone number with contact flow"
echo ""
echo "3. Test Voice Integration:"
echo "   - Call the phone number"
echo "   - Test: 'Hello', 'List my projects', 'Schedule appointment'"
echo ""
echo "4. Monitor Logs:"
echo "   aws logs tail /aws/lambda/$LEX_FULFILLMENT_FUNCTION --follow --region $REGION"
echo "   aws logs tail /aws/lambda/$VOICE_BRIDGE_FUNCTION --follow --region $REGION"
echo ""

echo -e "${GREEN}Voice Lambda functions deployed successfully!${NC}"
echo ""
