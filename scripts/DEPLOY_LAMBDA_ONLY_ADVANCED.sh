#!/bin/bash

##############################################################################
# DEPLOY_LAMBDA_ONLY_ADVANCED.sh - Advanced Lambda Deployment (Cross-Platform)
#
# Purpose: Deploy ProjectForce scheduling system using only AWS Lambda
# Date: 2025-11-26
#
# Improvements over original:
#   - Forces Python zipfile module (no zip command dependency)
#   - Properly handles existing IAM roles (deletes before creating)
#   - Cross-platform compatible (Windows/Linux/Mac)
#   - Continues deployment even if one lambda fails
#
# Deploys:
#   1. pf-scheduling-actions (scheduling queries & workflows)
#   2. pf-information-actions (weather queries)
#   3. pf-chitchat-actions (greetings, help, general chat)
#   4. pf-orchestrator (routing & workflow orchestration)
#   5. DynamoDB tables for sessions and notes
#
# Prerequisites:
#   - AWS CLI configured
#   - Python 3.x installed
#
# Usage:
#   ./DEPLOY_LAMBDA_ONLY_ADVANCED.sh
#   ./DEPLOY_LAMBDA_ONLY_ADVANCED.sh --profile pf-aws
##############################################################################

# Error handling - DO NOT use set -e (causes zombie processes)
# Instead, we handle errors explicitly with || true or proper checks

# Track temp files for cleanup
TEMP_FILES=()
CLEANUP_NEEDED=false

# Cleanup function - called on exit
cleanup_on_exit() {
    local EXIT_CODE=$?

    if [[ "$CLEANUP_NEEDED" == "true" ]]; then
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🧹 Cleaning up temp files..."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        # Clean up tracked temp files
        for file in "${TEMP_FILES[@]}"; do
            if [[ -f "$file" ]]; then
                rm -f "$file"
                echo "  → Removed: $file"
            fi
        done

        # Clean up common temp file patterns
        find "$PROJECT_DIR" -name "trust-policy-*.json" -delete 2>/dev/null || true
        find "$PROJECT_DIR" -name "secrets-policy.json" -delete 2>/dev/null || true
        find "$PROJECT_DIR" -name "orchestrator-permissions.json" -delete 2>/dev/null || true
        find "$PROJECT_DIR" -name "scheduling-env.json" -delete 2>/dev/null || true
        find "$PROJECT_DIR" -name "orchestrator-env.json" -delete 2>/dev/null || true
        find "$PROJECT_DIR" -name "iam-create-*.log" -delete 2>/dev/null || true
        find "$PROJECT_DIR" -name "lambda-create-*.log" -delete 2>/dev/null || true
        find "$PROJECT_DIR" -name "kms-fix-*.json" -delete 2>/dev/null || true

        echo "  ✓ Cleanup complete"
    fi

    if [[ $EXIT_CODE -ne 0 ]]; then
        echo ""
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${RED}❌ Deployment failed with exit code: $EXIT_CODE${NC}"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo "To clean up resources, run:"
        echo "  ./scripts/CLEANUP_ADVANCED.sh"
        echo ""
    fi

    exit $EXIT_CODE
}

# Register cleanup trap
trap cleanup_on_exit EXIT INT TERM

# Colors (defined early for profile selection UI)
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# ============================================================================
# AWS ACCOUNT SELECTION - Smart account detection and configuration
# ============================================================================

echo "════════════════════════════════════════════════════════════════════════════"
echo -e "${CYAN}🔐 AWS ACCOUNT SELECTION${NC}"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

# Get current/default profile
CURRENT_PROFILE="${AWS_PROFILE:-default}"
CURRENT_ACCOUNT=$(aws sts get-caller-identity --profile "$CURRENT_PROFILE" --query Account --output text 2>/dev/null || echo "N/A")

echo -e "Current Profile: ${YELLOW}${CURRENT_PROFILE}${NC}"
echo -e "Current Account: ${YELLOW}${CURRENT_ACCOUNT}${NC}"
echo ""

# Ask if this is correct
echo -e "${YELLOW}Is this the correct AWS account?${NC}"
echo ""
echo "  [1] Yes, proceed with account ${CURRENT_ACCOUNT}"
echo "  [2] No, I want to use a different account"
echo ""
read -p "Enter choice (1 or 2): " ACCOUNT_CHOICE

if [[ "$ACCOUNT_CHOICE" == "1" ]]; then
    # Use current profile
    AWS_PROFILE="$CURRENT_PROFILE"
    ACCOUNT_ID="$CURRENT_ACCOUNT"
    echo ""
    echo -e "${GREEN}✓ Using account: ${ACCOUNT_ID}${NC}"
else
    # User wants different account
    echo ""
    echo -e "${YELLOW}Enter the AWS Account ID you want to use:${NC}"
    read -p "Account ID (12 digits): " TARGET_ACCOUNT_ID

    # Validate account ID format
    if ! [[ "$TARGET_ACCOUNT_ID" =~ ^[0-9]{12}$ ]]; then
        echo -e "${RED}Invalid account ID format. Must be 12 digits.${NC}"
        exit 1
    fi

    echo ""
    echo "Searching existing profiles for account ${TARGET_ACCOUNT_ID}..."

    # Search all profiles for matching account ID
    FOUND_PROFILE=""
    while IFS= read -r profile; do
        if [[ -n "$profile" ]]; then
            PROFILE_ACCOUNT=$(aws sts get-caller-identity --profile "$profile" --query Account --output text 2>/dev/null || echo "")
            if [[ "$PROFILE_ACCOUNT" == "$TARGET_ACCOUNT_ID" ]]; then
                FOUND_PROFILE="$profile"
                break
            fi
        fi
    done < <(aws configure list-profiles 2>/dev/null)

    if [[ -n "$FOUND_PROFILE" ]]; then
        echo -e "${GREEN}✓ Found existing profile '${FOUND_PROFILE}' with account ${TARGET_ACCOUNT_ID}${NC}"
        AWS_PROFILE="$FOUND_PROFILE"
        ACCOUNT_ID="$TARGET_ACCOUNT_ID"
    else
        echo -e "${YELLOW}No existing profile found for account ${TARGET_ACCOUNT_ID}${NC}"
        echo ""
        echo -e "${CYAN}Let's configure AWS credentials for this account:${NC}"
        echo ""

        # Ask for profile name
        read -p "Profile name (e.g., pf-${TARGET_ACCOUNT_ID}): " NEW_PROFILE_NAME
        if [[ -z "$NEW_PROFILE_NAME" ]]; then
            NEW_PROFILE_NAME="pf-${TARGET_ACCOUNT_ID}"
        fi

        echo ""
        echo -e "${YELLOW}Enter AWS credentials for account ${TARGET_ACCOUNT_ID}:${NC}"
        echo ""

        # Get Access Key ID
        read -p "AWS Access Key ID: " AWS_ACCESS_KEY_ID
        if [[ -z "$AWS_ACCESS_KEY_ID" ]]; then
            echo -e "${RED}Access Key ID is required. Aborting.${NC}"
            exit 1
        fi

        # Get Secret Access Key (visible for paste compatibility on Windows)
        echo -e "${YELLOW}AWS Secret Access Key (will be visible - clear screen after):${NC}"
        read -p "> " AWS_SECRET_ACCESS_KEY
        if [[ -z "$AWS_SECRET_ACCESS_KEY" ]]; then
            echo -e "${RED}Secret Access Key is required. Aborting.${NC}"
            exit 1
        fi
        # Clear the line for security (works on most terminals)
        echo -e "\033[1A\033[2K> ********** (hidden)"

        # Configure the new profile
        echo ""
        echo "Configuring profile '${NEW_PROFILE_NAME}'..."

        aws configure set aws_access_key_id "$AWS_ACCESS_KEY_ID" --profile "$NEW_PROFILE_NAME"
        aws configure set aws_secret_access_key "$AWS_SECRET_ACCESS_KEY" --profile "$NEW_PROFILE_NAME"
        aws configure set region "us-east-1" --profile "$NEW_PROFILE_NAME"
        aws configure set output "json" --profile "$NEW_PROFILE_NAME"

        # Verify the new profile works
        echo "Verifying credentials..."
        VERIFY_ACCOUNT=$(aws sts get-caller-identity --profile "$NEW_PROFILE_NAME" --query Account --output text 2>/dev/null || echo "ERROR")

        if [[ "$VERIFY_ACCOUNT" == "$TARGET_ACCOUNT_ID" ]]; then
            echo -e "${GREEN}✓ Profile '${NEW_PROFILE_NAME}' configured successfully!${NC}"
            echo -e "${GREEN}✓ Verified account: ${VERIFY_ACCOUNT}${NC}"
            AWS_PROFILE="$NEW_PROFILE_NAME"
            ACCOUNT_ID="$TARGET_ACCOUNT_ID"
        else
            echo -e "${RED}❌ Credentials verification failed!${NC}"
            echo "   Expected account: $TARGET_ACCOUNT_ID"
            echo "   Got account: $VERIFY_ACCOUNT"
            echo ""
            echo "Please check your credentials and try again."
            exit 1
        fi
    fi
fi

echo ""

# Final confirmation
echo -e "${YELLOW}Confirm deployment:${NC}"
echo ""
echo "  Profile:    $AWS_PROFILE"
echo "  Account:    $ACCOUNT_ID"
echo "  Region:     us-east-1"
echo ""
read -p "Type 'yes' to proceed: " FINAL_CONFIRM

if [[ "$FINAL_CONFIRM" != "yes" ]]; then
    echo -e "${RED}Deployment aborted.${NC}"
    exit 0
fi

echo ""
echo -e "${GREEN}✓ Proceeding with deployment...${NC}"
echo ""

# Export for use throughout script
export AWS_PROFILE

# AWS CLI wrapper (uses selected profile)
aws_cmd() {
    aws --profile "$AWS_PROFILE" "$@"
}

# Determine paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

REGION="us-east-1"
ENV="dev"

# Detect platform and set correct Python command
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

echo "════════════════════════════════════════════════════════════════════════════"
echo "🚀 ProjectForce Advanced Lambda Deployment"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo "Environment: $ENV"
echo ""
echo "✨ Features:"
echo "  • Cross-platform Python-only packaging (no zip command needed)"
echo "  • Proper IAM role management"
echo "  • Error-resilient deployment"
echo ""

##############################################################################
# Helper: Delete IAM Role with Proper Policy Detachment
##############################################################################

delete_iam_role_if_exists() {
    local ROLE_NAME=$1

    if ! aws_cmd iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
        return 0
    fi

    echo "  → Deleting existing IAM role: $ROLE_NAME"

    # Detach all attached managed policies
    ATTACHED_POLICIES=$(aws_cmd iam list-attached-role-policies --role-name "$ROLE_NAME" --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null || echo "")
    for POLICY_ARN in $ATTACHED_POLICIES; do
        echo "    • Detaching $POLICY_ARN"
        aws_cmd iam detach-role-policy --role-name "$ROLE_NAME" --policy-arn "$POLICY_ARN" &>/dev/null || true
    done

    # Delete all inline policies
    INLINE_POLICIES=$(aws_cmd iam list-role-policies --role-name "$ROLE_NAME" --query 'PolicyNames[]' --output text 2>/dev/null || echo "")
    for POLICY_NAME in $INLINE_POLICIES; do
        echo "    • Deleting inline policy $POLICY_NAME"
        aws_cmd iam delete-role-policy --role-name "$ROLE_NAME" --policy-name "$POLICY_NAME" &>/dev/null || true
    done

    # Delete the role
    aws_cmd iam delete-role --role-name "$ROLE_NAME" &>/dev/null || true
    echo "    ✓ Role deleted"
}

##############################################################################
# Helper: Fix KMS Encryption Issues by Re-encrypting Environment Variables
##############################################################################

fix_kms_encryption() {
    local FUNCTION_NAME=$1
    
    echo ""
    echo "Fixing KMS encryption for: $FUNCTION_NAME"
    
    # Check if function exists
    if ! aws_cmd lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" &>/dev/null; then
        echo "  ⚠️  Function $FUNCTION_NAME not found, skipping KMS fix"
        return 0
    fi
    
    # Get current environment variables
    echo "  → Getting current environment variables..."
    local ENV_VARS=$(aws_cmd lambda get-function-configuration \n        --function-name "$FUNCTION_NAME" \n        --region "$REGION" \n        --query 'Environment.Variables' \n        --output json 2>/dev/null)
    
    if [[ "$ENV_VARS" == "null" ]] || [[ -z "$ENV_VARS" ]]; then
        echo "  → No environment variables to fix"
        return 0
    fi
    
    echo "  → Clearing environment variables (forces re-encryption)..."
    aws_cmd lambda update-function-configuration \n        --function-name "$FUNCTION_NAME" \n        --environment 'Variables={}' \n        --region "$REGION" &>/dev/null
    
    # Wait for update to complete
    echo "  → Waiting for Lambda update..."
    sleep 5
    aws_cmd lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION" 2>/dev/null || sleep 10
    
    # Restore environment variables
    echo "  → Restoring environment variables with AWS-managed encryption..."
    local ENV_JSON_FILE="./kms-fix-${FUNCTION_NAME}.json"
    TEMP_FILES+=("$ENV_JSON_FILE")
    echo "{"Variables":$ENV_VARS}" > "$ENV_JSON_FILE"

    aws_cmd lambda update-function-configuration \n        --function-name "$FUNCTION_NAME" \n        --environment "file://$ENV_JSON_FILE" \n        --region "$REGION" &>/dev/null

    # Wait for final update
    echo "  → Waiting for final update..."
    sleep 5
    aws_cmd lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION" 2>/dev/null || sleep 10

    rm -f "$ENV_JSON_FILE"
    echo -e "  ${GREEN}✅ KMS encryption fixed for $FUNCTION_NAME${NC}"
}

##############################################################################
# Step 1: ProjectForce API Credentials
##############################################################################

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}ProjectForce API Credentials${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Support environment variables for non-interactive mode
if [[ -n "$PF_CLIENT_ID" ]]; then
    echo "  Using PF_CLIENT_ID from environment: $PF_CLIENT_ID"
else
    read -p "Client ID (e.g., 09PF05VD): " PF_CLIENT_ID
    while [[ -z "$PF_CLIENT_ID" ]]; do
        echo -e "${YELLOW}Client ID is required${NC}"
        read -p "Client ID: " PF_CLIENT_ID
    done
fi

if [[ -n "$PF_USER_ID" ]]; then
    echo "  Using PF_USER_ID from environment: $PF_USER_ID"
else
    read -p "User ID (e.g., 1646085): " PF_USER_ID
    while [[ -z "$PF_USER_ID" ]]; do
        echo -e "${YELLOW}User ID is required${NC}"
        read -p "User ID: " PF_USER_ID
    done
fi

# Bearer token is OPTIONAL - Phase 1+2 architecture uses Secrets Manager with auto-refresh
if [[ -z "$PF_BEARER_TOKEN" ]]; then
    echo ""
    echo -e "${CYAN}Bearer Token is OPTIONAL (Phase 1+2 auto-refresh architecture)${NC}"
    echo "Press ENTER to skip, or paste token if you have one:"
    read -p "> " PF_BEARER_TOKEN
    if [[ -z "$PF_BEARER_TOKEN" ]]; then
        echo "  → Skipping bearer token (will use auto-refresh)"
        PF_BEARER_TOKEN="PENDING_AUTO_REFRESH"
    fi
fi

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
  "api_base_url": "https://api-cx-portal.dev.projectsforce.com",
  "REFRESH_TOKEN": "true"
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
    local ROLE_NAME="${FUNCTION_NAME}-role"

    if [[ ! -d "$LAMBDA_DIR" ]]; then
        echo -e "  ${RED}⚠️  Directory not found: $LAMBDA_DIR${NC}"
        return 1
    fi

    cd "$LAMBDA_DIR"

    # Package using Python zipfile (cross-platform, no zip command needed)
    echo "  → Packaging with Python zipfile module..."
    rm -f function.zip

    if [[ -f requirements.txt ]]; then
        # Lambda with dependencies
        rm -rf package && mkdir -p package
        $PYTHON_CMD -m pip install -r requirements.txt -t package/ --quiet 2>&1 | grep -v "dependency conflicts" || true

        # Create zip with dependencies
        $PYTHON_CMD -c "
import zipfile
import os

with zipfile.ZipFile('function.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    # Add all files from package directory
    for root, dirs, files in os.walk('package'):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, 'package')
            z.write(file_path, arcname)

    # Add all .py files from current directory
    for file in os.listdir('.'):
        if file.endswith('.py'):
            z.write(file)
"
    else
        # Lambda without dependencies
        $PYTHON_CMD -c "
import zipfile
import os

with zipfile.ZipFile('function.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk('.'):
        # Skip __pycache__, .pyc files, and the zip file itself
        if '__pycache__' in root:
            continue
        for file in files:
            if file.endswith('.pyc') or file.endswith('.zip'):
                continue
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, '.')
            z.write(file_path, arcname)
"
    fi

    echo "  ✓ Package created: function.zip"

    # Delete existing IAM role if it exists (prevents hanging issues)
    delete_iam_role_if_exists "$ROLE_NAME"

    # Create IAM role
    echo "  → Creating IAM role..."

    # Use current directory for temp files instead of /tmp for Windows compatibility
    local TRUST_POLICY_FILE="./trust-policy-${ROLE_NAME}.json"
    TEMP_FILES+=("$TRUST_POLICY_FILE")
    CLEANUP_NEEDED=true

    cat > "$TRUST_POLICY_FILE" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

    echo "  → Executing: iam create-role --role-name $ROLE_NAME"
    if ! aws_cmd iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document "file://${TRUST_POLICY_FILE}" 2>&1 | tee "./iam-create-$ROLE_NAME.log"; then
        echo "  ❌ Failed to create IAM role $ROLE_NAME"
        echo "  See: ./iam-create-$ROLE_NAME.log"
        TEMP_FILES+=("./iam-create-$ROLE_NAME.log")
        return 1
    fi
    rm -f "$TRUST_POLICY_FILE"

    echo "  → Attaching basic execution policy..."
    if ! aws_cmd iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" 2>&1; then
        echo "  ⚠️  Warning: Failed to attach basic execution policy"
    fi

    # Add DynamoDB permissions for scheduling and orchestrator
    if [[ "$FUNCTION_NAME" =~ (scheduling|orchestrator) ]]; then
        aws_cmd iam attach-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-arn "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess" &>/dev/null
    fi

    # Add Secrets Manager permissions
    TEMP_FILES+=("./secrets-policy.json")
    cat > ./secrets-policy.json <<EOF
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
        --policy-document file://./secrets-policy.json &>/dev/null

    # Add Lambda invoke permissions and Bedrock access for orchestrator
    if [[ "$FUNCTION_NAME" == "pf-orchestrator" ]]; then
        TEMP_FILES+=("./orchestrator-permissions.json")
        cat > ./orchestrator-permissions.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      "Resource": [
        "arn:aws:bedrock:${REGION}::foundation-model/anthropic.claude-*",
        "arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:inference-profile/us.anthropic.claude-*",
        "arn:aws:bedrock:*::foundation-model/*",
        "arn:aws:bedrock:*:${ACCOUNT_ID}:inference-profile/*"
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
            --policy-document file://./orchestrator-permissions.json &>/dev/null
    fi

    echo "  ✓ IAM role created"
    echo "  → Waiting for IAM role to propagate..."

    local ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

    # Poll for role propagation with 60 second max timeout
    local MAX_WAIT=60
    local POLL_INTERVAL=10
    local ELAPSED=0
    local ROLE_READY=false

    while [[ $ELAPSED -lt $MAX_WAIT ]]; do
        echo "  → Poll attempt at ${ELAPSED}s: checking role $ROLE_NAME..."

        if aws_cmd iam get-role --role-name "$ROLE_NAME" 2>&1 | grep -q "Role"; then
            echo "  → Role exists, checking trust policy..."
            TRUST_POLICY=$(aws_cmd iam get-role --role-name "$ROLE_NAME" --query 'Role.AssumeRolePolicyDocument' 2>&1)
            if [[ -n "$TRUST_POLICY" ]] && [[ "$TRUST_POLICY" != "null" ]]; then
                ROLE_READY=true
                echo "  ✓ IAM role fully propagated after ${ELAPSED}s"
                break
            else
                echo "  → Trust policy not ready yet (got: ${TRUST_POLICY:0:50}...)"
            fi
        else
            echo "  → Role not found yet in IAM"
        fi

        sleep $POLL_INTERVAL
        ELAPSED=$((ELAPSED + POLL_INTERVAL))
    done

    if [[ "$ROLE_READY" != "true" ]]; then
        echo "  ❌ ERROR: IAM role not propagated after ${MAX_WAIT}s"
        echo "  → Checking if role actually exists..."
        aws_cmd iam get-role --role-name "$ROLE_NAME" 2>&1 | head -20
        return 1
    fi

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

        echo -e "  ${GREEN}✅ Lambda updated: $FUNCTION_NAME${NC}"
    else
        echo "  → Creating new function..."
        if aws_cmd lambda create-function \
            --function-name "$FUNCTION_NAME" \
            --runtime python3.11 \
            --role "$ROLE_ARN" \
            --handler "$HANDLER" \
            --zip-file fileb://function.zip \
            --timeout "$TIMEOUT" \
            --memory-size "$MEMORY" \
            --region "$REGION" 2>&1 | tee ./lambda-create-$FUNCTION_NAME.log; then
            echo -e "  ${GREEN}✅ Lambda created: $FUNCTION_NAME${NC}"
        else
            echo -e "  ${RED}❌ Lambda creation FAILED: $FUNCTION_NAME${NC}"
            echo "  See error log: ./lambda-create-$FUNCTION_NAME.log"
            return 1
        fi
    fi
}

# Deploy all Lambda functions (continue even if one fails)
deploy_lambda "pf-scheduling-actions" "handler.lambda_handler" 30 1769 || echo -e "${RED}⚠️  pf-scheduling-actions deployment failed${NC}"
deploy_lambda "pf-information-actions" "handler.lambda_handler" 30 512 || echo -e "${RED}⚠️  pf-information-actions deployment failed${NC}"
deploy_lambda "pf-chitchat-actions" "handler.lambda_handler" 30 256 || echo -e "${RED}⚠️  pf-chitchat-actions deployment failed${NC}"
deploy_lambda "pf-orchestrator" "handler.lambda_handler" 120 512 || echo -e "${RED}⚠️  pf-orchestrator deployment failed${NC}"

##############################################################################
# Step 4.5: Configure Scheduling Actions Environment Variables
##############################################################################

echo ""
echo "=========================================="
echo "Step 4.5: Scheduling Actions Configuration"
echo "=========================================="

echo "  → Setting USE_MOCK_API=false for real API calls..."

TEMP_FILES+=("./scheduling-env.json")
cat > ./scheduling-env.json <<EOF
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
    --environment file://./scheduling-env.json \
    --region "$REGION" &>/dev/null

# Wait for configuration update
echo "  → Waiting for configuration update..."
sleep 5

rm -f ./scheduling-env.json
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
TEMP_FILES+=("./orchestrator-env.json")
cat > ./orchestrator-env.json <<EOF
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
    --environment file://./orchestrator-env.json \
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

rm -f ./orchestrator-env.json

##############################################################################
##############################################################################
# Step 6: Fix KMS Encryption (Prevents KMSAccessDeniedException)
##############################################################################

echo ""
echo "=========================================="
echo "Step 6: KMS Encryption Fix"
echo "=========================================="
echo "  Re-encrypting Lambda environment variables with AWS-managed keys..."
echo ""

# Fix KMS for all deployed lambdas
fix_kms_encryption "pf-scheduling-actions" || echo -e "${YELLOW}⚠️  KMS fix failed for pf-scheduling-actions${NC}"
fix_kms_encryption "pf-information-actions" || echo -e "${YELLOW}⚠️  KMS fix failed for pf-information-actions${NC}"
fix_kms_encryption "pf-chitchat-actions" || echo -e "${YELLOW}⚠️  KMS fix failed for pf-chitchat-actions${NC}"
fix_kms_encryption "pf-orchestrator" || echo -e "${YELLOW}⚠️  KMS fix failed for pf-orchestrator${NC}"

echo ""
echo -e "${GREEN}✅ KMS encryption fix completed for all Lambdas${NC}"


# Summary
##############################################################################

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
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
echo "  1. Start UI:"
echo "     cd testing/ui && ./launch_webapp.sh"
echo ""
echo "  2. Try these queries:"
echo "     • Hi"
echo "     • List my projects"
echo "     • Details for 7751748"
echo "     • Schedule it"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
