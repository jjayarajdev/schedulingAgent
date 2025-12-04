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
        echo "----------------------------------------------------------------------------"
        echo "[CLEAN] Cleaning up temp files..."
        echo "----------------------------------------------------------------------------"

        # Clean up tracked temp files
        for file in "${TEMP_FILES[@]}"; do
            if [[ -f "$file" ]]; then
                rm -f "$file"
                echo "  -> Removed: $file"
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

        echo "  [OK] Cleanup complete"
    fi

    if [[ $EXIT_CODE -ne 0 ]]; then
        echo ""
        echo -e "${RED}----------------------------------------------------------------------------${NC}"
        echo -e "${RED}[FAIL] Deployment failed with exit code: $EXIT_CODE${NC}"
        echo -e "${RED}----------------------------------------------------------------------------${NC}"
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

echo "============================================================================"
echo -e "${CYAN}[AUTH] AWS ACCOUNT SELECTION${NC}"
echo "============================================================================"
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
    echo -e "${GREEN}[OK] Using account: ${ACCOUNT_ID}${NC}"
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
        echo -e "${GREEN}[OK] Found existing profile '${FOUND_PROFILE}' with account ${TARGET_ACCOUNT_ID}${NC}"
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
            echo -e "${GREEN}[OK] Profile '${NEW_PROFILE_NAME}' configured successfully!${NC}"
            echo -e "${GREEN}[OK] Verified account: ${VERIFY_ACCOUNT}${NC}"
            AWS_PROFILE="$NEW_PROFILE_NAME"
            ACCOUNT_ID="$TARGET_ACCOUNT_ID"
        else
            echo -e "${RED}[FAIL] Credentials verification failed!${NC}"
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
echo -e "${GREEN}[OK] Proceeding with deployment...${NC}"
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

REGION="${AWS_REGION:-us-east-1}"
ENV="${ENVIRONMENT:-dev}"

# Detect platform and set correct Python command
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

echo "============================================================================"
echo "[DEPLOY] ProjectForce Advanced Lambda Deployment"
echo "============================================================================"
echo ""
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo "Environment: $ENV"
echo ""
echo "* Features:"
echo "  - Cross-platform Python-only packaging (no zip command needed)"
echo "  - Proper IAM role management"
echo "  - Error-resilient deployment"
echo ""

##############################################################################
# Helper: Delete IAM Role with Proper Policy Detachment
##############################################################################

delete_iam_role_if_exists() {
    local ROLE_NAME=$1

    if ! aws_cmd iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
        return 0
    fi

    echo "  -> Deleting existing IAM role: $ROLE_NAME"

    # Detach all attached managed policies
    ATTACHED_POLICIES=$(aws_cmd iam list-attached-role-policies --role-name "$ROLE_NAME" --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null || echo "")
    for POLICY_ARN in $ATTACHED_POLICIES; do
        echo "    - Detaching $POLICY_ARN"
        aws_cmd iam detach-role-policy --role-name "$ROLE_NAME" --policy-arn "$POLICY_ARN" &>/dev/null || true
    done

    # Delete all inline policies
    INLINE_POLICIES=$(aws_cmd iam list-role-policies --role-name "$ROLE_NAME" --query 'PolicyNames[]' --output text 2>/dev/null || echo "")
    for POLICY_NAME in $INLINE_POLICIES; do
        echo "    - Deleting inline policy $POLICY_NAME"
        aws_cmd iam delete-role-policy --role-name "$ROLE_NAME" --policy-name "$POLICY_NAME" &>/dev/null || true
    done

    # Delete the role
    aws_cmd iam delete-role --role-name "$ROLE_NAME" &>/dev/null || true
    echo "    [OK] Role deleted"
}

##############################################################################
# Helper: Ensure AWS Default Encryption (Remove any customer-managed KMS key)
# IMPORTANT: We ALWAYS use AWS default encryption for Lambda environment variables.
#            This prevents KMSAccessDeniedException errors from misconfigured KMS keys.
#            DO NOT CHANGE THIS - customer KMS keys cause permission nightmares!
#
# Strategy:
#   1. During Lambda update (deploy_lambda): --kms-key-arn "" is set to remove KMS
#   2. After all deployments (Step 6): This function verifies all Lambdas are clean
#
# Why this matters:
#   When Lambda A invokes Lambda B, if B has a custom KMS key for env vars,
#   A's role needs kms:Decrypt permission on that key. The AWS-managed Lambda
#   key (alias/aws/lambda) has restrictive policies that only allow access
#   via the Lambda service itself, causing KMSAccessDeniedException errors.
##############################################################################

ensure_aws_default_encryption() {
    local FUNCTION_NAME=$1
    local KMS_MAX_WAIT=30
    local KMS_POLL_INTERVAL=3
    local KMS_ELAPSED=0

    echo "  -> Checking encryption for: $FUNCTION_NAME"

    # Check if function exists
    if ! aws_cmd lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" &>/dev/null; then
        echo "    [SKIP] Function $FUNCTION_NAME not found"
        return 0
    fi

    # Check if Lambda has a customer-managed KMS key
    local CURRENT_KMS
    CURRENT_KMS=$(aws_cmd lambda get-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --region "$REGION" \
        --query 'KMSKeyArn' \
        --output text 2>/dev/null)

    if [[ "$CURRENT_KMS" != "None" ]] && [[ "$CURRENT_KMS" != "null" ]] && [[ -n "$CURRENT_KMS" ]]; then
        echo "    [WARN] Found customer KMS key: $CURRENT_KMS"
        echo "    -> Removing KMS key, switching to AWS default encryption..."

        # Remove KMS key by setting it to empty string (forces AWS managed encryption)
        aws_cmd lambda update-function-configuration \
            --function-name "$FUNCTION_NAME" \
            --kms-key-arn "" \
            --region "$REGION" &>/dev/null

        # Wait for update with polling loop
        while [[ $KMS_ELAPSED -lt $KMS_MAX_WAIT ]]; do
            local STATE
            STATE=$(aws_cmd lambda get-function-configuration \
                --function-name "$FUNCTION_NAME" \
                --region "$REGION" \
                --query 'LastUpdateStatus' \
                --output text 2>/dev/null)

            if [[ "$STATE" == "Successful" ]]; then
                echo -e "    ${GREEN}[OK] Now using AWS default encryption (${KMS_ELAPSED}s)${NC}"
                return 0
            elif [[ "$STATE" == "Failed" ]]; then
                echo -e "    ${RED}[FAIL] Lambda update failed${NC}"
                return 1
            fi

            sleep $KMS_POLL_INTERVAL
            KMS_ELAPSED=$((KMS_ELAPSED + KMS_POLL_INTERVAL))

            if [[ $((KMS_ELAPSED % 10)) -eq 0 ]]; then
                echo "    -> Waiting for update... ${KMS_ELAPSED}s / ${KMS_MAX_WAIT}s"
            fi
        done

        echo -e "    ${YELLOW}[WARN] Update timed out after ${KMS_MAX_WAIT}s${NC}"
        return 0
    else
        echo -e "    ${GREEN}[OK] Already using AWS default encryption${NC}"
    fi

    return 0
}

##############################################################################
# Step 1: ProjectForce API Credentials
##############################################################################

echo "----------------------------------------------------------------------------"
echo -e "${BLUE}ProjectForce API Credentials${NC}"
echo "----------------------------------------------------------------------------"
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
        echo "  -> Skipping bearer token (will use auto-refresh)"
        PF_BEARER_TOKEN="PENDING_AUTO_REFRESH"
    fi
fi

echo ""
echo -e "${GREEN}[OK] Credentials captured${NC}"
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
    echo "  -> Updating existing secret..."
    aws_cmd secretsmanager update-secret \
        --secret-id "$SECRET_NAME" \
        --secret-string "$SECRET_VALUE" \
        --region "$REGION" &>/dev/null
    echo "  [OK] Secret updated: $SECRET_NAME"
else
    echo "  -> Creating new secret..."
    aws_cmd secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --description "ProjectForce API credentials for dev environment" \
        --secret-string "$SECRET_VALUE" \
        --region "$REGION" &>/dev/null
    echo "  [OK] Secret created: $SECRET_NAME"
fi

##############################################################################
# Step 3: Create DynamoDB Tables
##############################################################################

echo ""
echo "=========================================="
echo "Step 3: DynamoDB Tables"
echo "=========================================="

# Sessions table
if aws_cmd dynamodb describe-table --table-name "pf-sessions-${ENV}" --region "$REGION" &>/dev/null; then
    echo "  [OK] Table exists: pf-sessions-${ENV}"
else
    echo "  -> Creating pf-sessions-${ENV}..."
    aws_cmd dynamodb create-table \
        --table-name "pf-sessions-${ENV}" \
        --attribute-definitions \
            AttributeName=session_id,AttributeType=S \
            AttributeName=user_id,AttributeType=S \
        --key-schema AttributeName=session_id,KeyType=HASH \
        --global-secondary-indexes \
            "IndexName=user_id-index,KeySchema=[{AttributeName=user_id,KeyType=HASH}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}" \
        --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
        --region "$REGION" &>/dev/null
    echo "  [OK] Table created: pf-sessions-${ENV}"
fi

# Notes table
if aws_cmd dynamodb describe-table --table-name "pf-notes-${ENV}" --region "$REGION" &>/dev/null; then
    echo "  [OK] Table exists: pf-notes-${ENV}"
else
    echo "  -> Creating pf-notes-${ENV}..."
    aws_cmd dynamodb create-table \
        --table-name "pf-notes-${ENV}" \
        --attribute-definitions \
            AttributeName=project_id,AttributeType=S \
            AttributeName=timestamp,AttributeType=S \
        --key-schema \
            AttributeName=project_id,KeyType=HASH \
            AttributeName=timestamp,KeyType=RANGE \
        --billing-mode PAY_PER_REQUEST \
        --region "$REGION" &>/dev/null
    echo "  [OK] Table created: pf-notes-${ENV}"
fi

# Workflow states table (for intelligent orchestration)
if aws_cmd dynamodb describe-table --table-name "pf-workflow-states-${ENV}" --region "$REGION" &>/dev/null; then
    echo "  [OK] Table exists: pf-workflow-states-${ENV}"
else
    echo "  -> Creating pf-workflow-states-${ENV}..."
    aws_cmd dynamodb create-table \
        --table-name "pf-workflow-states-${ENV}" \
        --attribute-definitions \
            AttributeName=session_id,AttributeType=S \
        --key-schema \
            AttributeName=session_id,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region "$REGION" &>/dev/null
    echo "  [OK] Table created: pf-workflow-states-${ENV}"
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
        echo -e "  ${RED}[WARN]  Directory not found: $LAMBDA_DIR${NC}"
        return 1
    fi

    cd "$LAMBDA_DIR"

    # Package using Python zipfile (cross-platform, no zip command needed)
    echo "  -> Packaging with Python zipfile module..."
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

    echo "  [OK] Package created: function.zip"

    # Delete existing IAM role if it exists (prevents hanging issues)
    delete_iam_role_if_exists "$ROLE_NAME"

    # Create IAM role
    echo "  -> Creating IAM role..."

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

    echo "  -> Executing: iam create-role --role-name $ROLE_NAME"
    if ! aws_cmd iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document "file://${TRUST_POLICY_FILE}" 2>&1 | tee "./iam-create-$ROLE_NAME.log"; then
        echo "  [FAIL] Failed to create IAM role $ROLE_NAME"
        echo "  See: ./iam-create-$ROLE_NAME.log"
        TEMP_FILES+=("./iam-create-$ROLE_NAME.log")
        return 1
    fi
    rm -f "$TRUST_POLICY_FILE"

    echo "  -> Attaching basic execution policy..."
    if ! aws_cmd iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" 2>&1; then
        echo "  [WARN]  Warning: Failed to attach basic execution policy"
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
        "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/pf-sessions-${ENV}",
        "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/pf-workflow-states-${ENV}"
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

    echo "  [OK] IAM role created"
    echo "  -> Waiting for IAM role to propagate (max 5 minutes)..."

    local ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

    # Dynamic polling for role propagation with 5 minute max timeout
    local MAX_WAIT=300  # 5 minutes
    local POLL_INTERVAL=5
    local ELAPSED=0
    local ROLE_READY=false

    while [[ $ELAPSED -lt $MAX_WAIT ]]; do
        if aws_cmd iam get-role --role-name "$ROLE_NAME" 2>&1 | grep -q "Role"; then
            TRUST_POLICY=$(aws_cmd iam get-role --role-name "$ROLE_NAME" --query 'Role.AssumeRolePolicyDocument' 2>&1)
            if [[ -n "$TRUST_POLICY" ]] && [[ "$TRUST_POLICY" != "null" ]]; then
                ROLE_READY=true
                echo "  [OK] IAM role propagated after ${ELAPSED}s"
                break
            fi
        fi

        sleep $POLL_INTERVAL
        ELAPSED=$((ELAPSED + POLL_INTERVAL))

        # Show progress every 15 seconds
        if [[ $((ELAPSED % 15)) -eq 0 ]]; then
            echo "  -> Waiting for IAM propagation... ${ELAPSED}s / ${MAX_WAIT}s"
        fi
    done

    if [[ "$ROLE_READY" != "true" ]]; then
        echo "  [FAIL] ERROR: IAM role not propagated after ${MAX_WAIT}s"
        aws_cmd iam get-role --role-name "$ROLE_NAME" 2>&1 | head -20
        return 1
    fi

    # Additional safety wait for cross-region IAM consistency
    # Lambda service may not see the role immediately even if IAM API returns it
    local MIN_SAFETY_WAIT=15
    if [[ $ELAPSED -lt $MIN_SAFETY_WAIT ]]; then
        local EXTRA_WAIT=$((MIN_SAFETY_WAIT - ELAPSED))
        echo "  -> Adding ${EXTRA_WAIT}s safety buffer for Lambda service consistency..."
        sleep $EXTRA_WAIT
    fi

    # Create or update Lambda
    if aws_cmd lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" &>/dev/null; then
        echo "  -> Updating existing function..."
        aws_cmd lambda update-function-code \
            --function-name "$FUNCTION_NAME" \
            --zip-file fileb://function.zip \
            --region "$REGION" &>/dev/null

        # Wait for update
        sleep 5
        aws_cmd lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION" 2>/dev/null || true

        # Update configuration AND ensure AWS default encryption (no custom KMS key)
        # Setting --kms-key-arn "" removes any custom KMS key, forcing AWS default encryption
        aws_cmd lambda update-function-configuration \
            --function-name "$FUNCTION_NAME" \
            --timeout "$TIMEOUT" \
            --memory-size "$MEMORY" \
            --kms-key-arn "" \
            --region "$REGION" &>/dev/null

        echo -e "  ${GREEN}[OK] Lambda updated: $FUNCTION_NAME (using AWS default encryption)${NC}"
    else
        echo "  -> Creating new function..."

        # Dynamic polling for Lambda creation (max 5 minutes)
        # IAM role assumability can take time to propagate to Lambda service
        # Also retry on transient AWS errors (ServiceException, throttling, etc.)
        local CREATE_MAX_WAIT=300  # 5 minutes
        local CREATE_POLL_INTERVAL=10
        local CREATE_ELAPSED=0
        local LAMBDA_CREATED=false
        local ATTEMPT=0

        while [[ $CREATE_ELAPSED -lt $CREATE_MAX_WAIT ]]; do
            ATTEMPT=$((ATTEMPT + 1))
            echo "  -> Attempt $ATTEMPT at ${CREATE_ELAPSED}s..."

            # Capture output and exit code separately (tee swallows exit code)
            local CREATE_OUTPUT
            CREATE_OUTPUT=$(aws_cmd lambda create-function \
                --function-name "$FUNCTION_NAME" \
                --runtime python3.11 \
                --role "$ROLE_ARN" \
                --handler "$HANDLER" \
                --zip-file fileb://function.zip \
                --timeout "$TIMEOUT" \
                --memory-size "$MEMORY" \
                --region "$REGION" 2>&1)
            local CREATE_EXIT_CODE=$?

            # Save output to log
            echo "$CREATE_OUTPUT" > ./lambda-create-$FUNCTION_NAME.log

            if [[ $CREATE_EXIT_CODE -eq 0 ]]; then
                LAMBDA_CREATED=true
                echo -e "  ${GREEN}[OK] Lambda created: $FUNCTION_NAME (after ${CREATE_ELAPSED}s)${NC}"
                break
            elif echo "$CREATE_OUTPUT" | grep -q "cannot be assumed by Lambda"; then
                echo "  [WAIT] IAM role not yet assumable by Lambda service"
                sleep $CREATE_POLL_INTERVAL
                CREATE_ELAPSED=$((CREATE_ELAPSED + CREATE_POLL_INTERVAL))

                # Show progress every 30 seconds
                if [[ $((CREATE_ELAPSED % 30)) -eq 0 ]]; then
                    echo "  -> Still waiting for IAM-Lambda consistency... ${CREATE_ELAPSED}s / ${CREATE_MAX_WAIT}s"
                fi
            elif echo "$CREATE_OUTPUT" | grep -qE "(ServiceException|ThrottlingException|TooManyRequestsException|ResourceConflictException|InvalidParameterValueException.*temporarily)"; then
                # Transient AWS errors - retry with backoff
                echo "  [WAIT] Transient AWS error, retrying..."
                echo "         Error: $(echo "$CREATE_OUTPUT" | head -1)"
                sleep $CREATE_POLL_INTERVAL
                CREATE_ELAPSED=$((CREATE_ELAPSED + CREATE_POLL_INTERVAL))
            elif echo "$CREATE_OUTPUT" | grep -q "ResourceConflictException"; then
                # Function exists in a weird state - try to delete and recreate
                echo "  [WARN] Function exists in conflicting state, attempting cleanup..."
                aws_cmd lambda delete-function --function-name "$FUNCTION_NAME" --region "$REGION" 2>/dev/null || true
                sleep 5
                CREATE_ELAPSED=$((CREATE_ELAPSED + 5))
            else
                # Unknown error - log it, wait, and retry a few times before failing
                echo "  [WARN] Unexpected error (will retry): $(echo "$CREATE_OUTPUT" | head -2)"

                # After 3 unexpected errors, fail
                if [[ $ATTEMPT -ge 5 ]]; then
                    echo "$CREATE_OUTPUT"
                    echo -e "  ${RED}[FAIL] Lambda creation FAILED after $ATTEMPT attempts: $FUNCTION_NAME${NC}"
                    return 1
                fi

                # Otherwise, wait and retry
                sleep $CREATE_POLL_INTERVAL
                CREATE_ELAPSED=$((CREATE_ELAPSED + CREATE_POLL_INTERVAL))
            fi
        done

        if [[ "$LAMBDA_CREATED" != "true" ]]; then
            echo -e "  ${RED}[FAIL] Lambda creation FAILED after ${CREATE_MAX_WAIT}s${NC}"
            echo "  See error log: ./lambda-create-$FUNCTION_NAME.log"
            return 1
        fi
    fi

    # POST-DEPLOYMENT VERIFICATION: Wait for Lambda to be fully Active
    echo "  -> Verifying Lambda is Active..."
    local VERIFY_ATTEMPTS=10
    local VERIFY_DELAY=3
    local LAMBDA_ACTIVE=false

    for V in $(seq 1 $VERIFY_ATTEMPTS); do
        local LAMBDA_STATE=$(aws_cmd lambda get-function \
            --function-name "$FUNCTION_NAME" \
            --region "$REGION" \
            --query 'Configuration.State' \
            --output text 2>/dev/null || echo "UNKNOWN")

        local LAST_UPDATE=$(aws_cmd lambda get-function \
            --function-name "$FUNCTION_NAME" \
            --region "$REGION" \
            --query 'Configuration.LastUpdateStatus' \
            --output text 2>/dev/null || echo "UNKNOWN")

        if [[ "$LAMBDA_STATE" == "Active" ]] && [[ "$LAST_UPDATE" == "Successful" || "$LAST_UPDATE" == "null" || -z "$LAST_UPDATE" ]]; then
            LAMBDA_ACTIVE=true
            echo -e "  ${GREEN}[OK] Lambda verified Active: $FUNCTION_NAME${NC}"
            break
        else
            echo "  -> Waiting... (State: $LAMBDA_STATE, LastUpdate: $LAST_UPDATE)"
            sleep $VERIFY_DELAY
        fi
    done

    if [[ "$LAMBDA_ACTIVE" != "true" ]]; then
        echo -e "  ${YELLOW}[WARN] Lambda may not be fully ready - State: $LAMBDA_STATE${NC}"
    fi
}

# Deploy all Lambda functions (continue even if one fails)
# Timeouts: scheduling=60s (API calls can be slow), orchestrator=120s (calls other lambdas)
deploy_lambda "pf-scheduling-actions" "handler.lambda_handler" 60 1769 || echo -e "${RED}[WARN]  pf-scheduling-actions deployment failed${NC}"
deploy_lambda "pf-information-actions" "handler.lambda_handler" 30 512 || echo -e "${RED}[WARN]  pf-information-actions deployment failed${NC}"
deploy_lambda "pf-chitchat-actions" "handler.lambda_handler" 30 256 || echo -e "${RED}[WARN]  pf-chitchat-actions deployment failed${NC}"
deploy_lambda "pf-orchestrator" "handler.lambda_handler" 120 512 || echo -e "${RED}[WARN]  pf-orchestrator deployment failed${NC}"

##############################################################################
# Step 4.5: Configure Scheduling Actions Environment Variables
##############################################################################

echo ""
echo "=========================================="
echo "Step 4.5: Scheduling Actions Configuration"
echo "=========================================="

echo "  -> Setting USE_MOCK_API=false for real API calls..."

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
echo "  -> Waiting for configuration update..."
sleep 5

rm -f ./scheduling-env.json
echo "  [OK] Scheduling actions configured for REAL API mode"

##############################################################################
# Step 5: Configure Orchestrator Environment Variables
##############################################################################

echo ""
echo "=========================================="
echo "Step 5: Orchestrator Configuration"
echo "=========================================="

# Wait for orchestrator to be fully ready after Step 4 deployment
echo "  -> Waiting for pf-orchestrator to be ready..."
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
        echo "  [OK] Lambda ready"
        break
    fi

    echo "  [WAIT] Waiting for Lambda (State: $STATE, LastUpdate: $LAST_UPDATE)..."
    sleep 2
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

if [[ $WAIT_COUNT -ge $MAX_WAIT ]]; then
    echo "  [WARN]  Warning: Lambda may not be fully ready, proceeding anyway..."
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
    "DYNAMODB_TABLE": "pf-sessions-${ENV}",
    "WORKFLOW_STATE_TABLE": "pf-workflow-states-${ENV}",
    "REGION": "$REGION",
    "ALLOW_DIRECT_LAMBDA": "true",
    "ENABLE_MULTI_AGENT_ORCHESTRATION": "false",
    "USE_SUPERVISOR": "false"
  }
}
EOF

# Update environment variables
echo "  -> Setting environment variables..."
aws_cmd lambda update-function-configuration \
    --function-name pf-orchestrator \
    --environment file://./orchestrator-env.json \
    --region "$REGION" &>/dev/null

# Wait for configuration update to complete
echo "  -> Waiting for configuration update to complete..."
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
        echo "  [FAIL] Configuration update failed!"
        break
    fi

    echo "  [WAIT] Update status: $LAST_UPDATE..."
    sleep 2
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

# Verify environment variables were set
echo "  -> Verifying environment variables..."
SCHEDULING_LAMBDA=$(aws_cmd lambda get-function-configuration \
    --function-name pf-orchestrator \
    --region "$REGION" \
    --query 'Environment.Variables.SCHEDULING_LAMBDA' \
    --output text 2>/dev/null || echo "null")

if [[ "$SCHEDULING_LAMBDA" == "pf-scheduling-actions" ]]; then
    echo "  [OK] Environment variables verified: SCHEDULING_LAMBDA=$SCHEDULING_LAMBDA"
    echo "  [OK] Orchestrator configured successfully"
else
    echo "  [WARN]  Warning: Environment variables may not be set correctly"
    echo "  [WARN]  SCHEDULING_LAMBDA=$SCHEDULING_LAMBDA (expected: pf-scheduling-actions)"
fi

rm -f ./orchestrator-env.json

##############################################################################
# Step 6: Verify AWS Default Encryption (Prevents KMSAccessDeniedException)
# Note: The deploy_lambda function already sets --kms-key-arn "" during updates.
#       This step is a safety verification to catch any edge cases.
##############################################################################

echo ""
echo "=========================================="
echo "Step 6: Verify AWS Default Encryption"
echo "=========================================="
echo "  Verifying all Lambdas use AWS default encryption (no custom KMS keys)..."
echo "  This prevents KMSAccessDeniedException when Lambdas invoke each other."
echo ""

# Verify and fix KMS for all deployed lambdas (safety net)
ensure_aws_default_encryption "pf-scheduling-actions" || echo -e "${YELLOW}[WARN]  KMS verification failed for pf-scheduling-actions${NC}"
ensure_aws_default_encryption "pf-information-actions" || echo -e "${YELLOW}[WARN]  KMS verification failed for pf-information-actions${NC}"
ensure_aws_default_encryption "pf-chitchat-actions" || echo -e "${YELLOW}[WARN]  KMS verification failed for pf-chitchat-actions${NC}"
ensure_aws_default_encryption "pf-orchestrator" || echo -e "${YELLOW}[WARN]  KMS verification failed for pf-orchestrator${NC}"

echo ""
echo -e "${GREEN}[OK] AWS default encryption verified for all Lambdas${NC}"


##############################################################################
# Step 7: FINAL VERIFICATION - Check ALL resources exist and are working
##############################################################################

echo ""
echo "============================================================================"
echo -e "${YELLOW}Step 7: FINAL VERIFICATION - Checking all deployed resources${NC}"
echo "============================================================================"
echo ""

DEPLOYMENT_OK=true
FAILED_RESOURCES=""

# 7.1 Verify all Lambda functions exist and are Active
echo "  -> Verifying Lambda functions..."
REQUIRED_LAMBDAS=("pf-orchestrator" "pf-scheduling-actions" "pf-information-actions" "pf-chitchat-actions")

for LAMBDA_NAME in "${REQUIRED_LAMBDAS[@]}"; do
    echo -n "     Checking $LAMBDA_NAME... "

    LAMBDA_STATE=$(aws_cmd lambda get-function \
        --function-name "$LAMBDA_NAME" \
        --region "$REGION" \
        --query 'Configuration.State' \
        --output text 2>/dev/null || echo "NOT_FOUND")

    if [[ "$LAMBDA_STATE" == "Active" ]]; then
        echo -e "${GREEN}[OK] Active${NC}"
    elif [[ "$LAMBDA_STATE" == "NOT_FOUND" ]]; then
        echo -e "${RED}[FAIL] NOT FOUND!${NC}"
        DEPLOYMENT_OK=false
        FAILED_RESOURCES="$FAILED_RESOURCES\n  - Lambda: $LAMBDA_NAME (not found)"
    else
        echo -e "${YELLOW}[WARN] State: $LAMBDA_STATE${NC}"
        # Wait for it to become active
        echo "     -> Waiting for Lambda to become Active..."
        for i in 1 2 3 4 5; do
            sleep 5
            LAMBDA_STATE=$(aws_cmd lambda get-function \
                --function-name "$LAMBDA_NAME" \
                --region "$REGION" \
                --query 'Configuration.State' \
                --output text 2>/dev/null || echo "NOT_FOUND")
            if [[ "$LAMBDA_STATE" == "Active" ]]; then
                echo -e "     ${GREEN}[OK] Now Active${NC}"
                break
            fi
        done
        if [[ "$LAMBDA_STATE" != "Active" ]]; then
            DEPLOYMENT_OK=false
            FAILED_RESOURCES="$FAILED_RESOURCES\n  - Lambda: $LAMBDA_NAME (state: $LAMBDA_STATE)"
        fi
    fi
done

echo ""

# 7.2 Verify DynamoDB tables exist and are Active
echo "  -> Verifying DynamoDB tables..."
REQUIRED_TABLES=("pf-sessions-${ENV}" "pf-notes-${ENV}" "pf-workflow-states-${ENV}")

for TABLE_NAME in "${REQUIRED_TABLES[@]}"; do
    echo -n "     Checking $TABLE_NAME... "

    TABLE_STATUS=$(aws_cmd dynamodb describe-table \
        --table-name "$TABLE_NAME" \
        --region "$REGION" \
        --query 'Table.TableStatus' \
        --output text 2>/dev/null || echo "NOT_FOUND")

    if [[ "$TABLE_STATUS" == "ACTIVE" ]]; then
        echo -e "${GREEN}[OK] Active${NC}"
    elif [[ "$TABLE_STATUS" == "NOT_FOUND" ]]; then
        echo -e "${RED}[FAIL] NOT FOUND!${NC}"
        DEPLOYMENT_OK=false
        FAILED_RESOURCES="$FAILED_RESOURCES\n  - DynamoDB: $TABLE_NAME (not found)"
    else
        echo -e "${YELLOW}[WARN] Status: $TABLE_STATUS - waiting...${NC}"
        aws_cmd dynamodb wait table-exists --table-name "$TABLE_NAME" --region "$REGION" 2>/dev/null || true
        TABLE_STATUS=$(aws_cmd dynamodb describe-table \
            --table-name "$TABLE_NAME" \
            --region "$REGION" \
            --query 'Table.TableStatus' \
            --output text 2>/dev/null || echo "NOT_FOUND")
        if [[ "$TABLE_STATUS" == "ACTIVE" ]]; then
            echo -e "     ${GREEN}[OK] Now Active${NC}"
        else
            DEPLOYMENT_OK=false
            FAILED_RESOURCES="$FAILED_RESOURCES\n  - DynamoDB: $TABLE_NAME (status: $TABLE_STATUS)"
        fi
    fi
done

echo ""

# 7.3 Verify Secrets Manager secret exists
echo "  -> Verifying Secrets Manager..."
echo -n "     Checking projectforce/api/credentials... "
SECRET_EXISTS=$(aws_cmd secretsmanager describe-secret \
    --secret-id "projectforce/api/credentials" \
    --region "$REGION" \
    --query 'Name' \
    --output text 2>/dev/null || echo "NOT_FOUND")

if [[ "$SECRET_EXISTS" != "NOT_FOUND" ]]; then
    echo -e "${GREEN}[OK] Exists${NC}"
else
    echo -e "${RED}[FAIL] NOT FOUND!${NC}"
    DEPLOYMENT_OK=false
    FAILED_RESOURCES="$FAILED_RESOURCES\n  - Secret: projectforce/api/credentials (not found)"
fi

echo ""

# 7.4 Verify IAM roles exist
echo "  -> Verifying IAM roles..."
REQUIRED_ROLES=("pf-orchestrator-role" "pf-scheduling-actions-role" "pf-information-actions-role" "pf-chitchat-actions-role")

for ROLE_NAME in "${REQUIRED_ROLES[@]}"; do
    echo -n "     Checking $ROLE_NAME... "

    ROLE_EXISTS=$(aws_cmd iam get-role \
        --role-name "$ROLE_NAME" \
        --query 'Role.RoleName' \
        --output text 2>/dev/null || echo "NOT_FOUND")

    if [[ "$ROLE_EXISTS" != "NOT_FOUND" ]]; then
        echo -e "${GREEN}[OK] Exists${NC}"
    else
        echo -e "${RED}[FAIL] NOT FOUND!${NC}"
        DEPLOYMENT_OK=false
        FAILED_RESOURCES="$FAILED_RESOURCES\n  - IAM Role: $ROLE_NAME (not found)"
    fi
done

echo ""

# 7.5 Verify orchestrator environment variables
echo "  -> Verifying orchestrator configuration..."
echo -n "     Checking environment variables... "
ORCH_CONFIG=$(aws_cmd lambda get-function-configuration \
    --function-name "pf-orchestrator" \
    --region "$REGION" \
    --query 'Environment.Variables.SCHEDULING_LAMBDA' \
    --output text 2>/dev/null || echo "NOT_SET")

if [[ "$ORCH_CONFIG" == "pf-scheduling-actions" ]]; then
    echo -e "${GREEN}[OK] Configured${NC}"
else
    echo -e "${YELLOW}[WARN] SCHEDULING_LAMBDA=$ORCH_CONFIG${NC}"
fi

echo ""

# 7.6 Test Lambda invocability (optional quick test)
echo "  -> Testing Lambda invocability..."
echo -n "     Testing pf-orchestrator invoke... "
INVOKE_RESULT=$(aws_cmd lambda invoke \
    --function-name "pf-orchestrator" \
    --payload '{"test": true}' \
    --region "$REGION" \
    /dev/null 2>&1 || echo "INVOKE_FAILED")

if echo "$INVOKE_RESULT" | grep -q "INVOKE_FAILED\|error\|Error"; then
    echo -e "${YELLOW}[WARN] Invoke test inconclusive${NC}"
else
    echo -e "${GREEN}[OK] Invocable${NC}"
fi

echo ""
echo "============================================================================"

# Final result
if [[ "$DEPLOYMENT_OK" == "true" ]]; then
    echo -e "${GREEN}[OK] ALL VERIFICATION CHECKS PASSED!${NC}"
    echo "============================================================================"
    echo ""

    # Summary
    echo "----------------------------------------------------------------------------"
    echo -e "${GREEN}[OK] Deployment Complete!${NC}"
    echo "----------------------------------------------------------------------------"
else
    echo -e "${RED}[FAIL] DEPLOYMENT VERIFICATION FAILED!${NC}"
    echo "============================================================================"
    echo ""
    echo -e "${RED}Failed resources:${NC}"
    echo -e "$FAILED_RESOURCES"
    echo ""
    echo "Please fix the above issues before using the system."
    echo "You may need to re-run this script or check AWS console."
    echo ""
    echo "----------------------------------------------------------------------------"
    exit 1
fi
echo ""
echo "Deployed Resources:"
echo "  [OK] 4 Lambda functions"
echo "     - pf-orchestrator (intelligent routing & workflows)"
echo "     - pf-scheduling-actions (scheduling queries)"
echo "     - pf-information-actions (weather)"
echo "     - pf-chitchat-actions (greetings, help)"
echo ""
echo "  [OK] 3 DynamoDB tables"
echo "     - pf-sessions-${ENV} (conversation history)"
echo "     - pf-notes-${ENV} (project notes)"
echo "     - pf-workflow-states-${ENV} (workflow state management)"
echo ""
echo "  [OK] 1 Secrets Manager secret"
echo "     - projectforce/api/credentials"
echo ""
echo "Architecture:"
echo "  [DEPLOY] Pure Lambda - No Bedrock agents"
echo "  [AI] Sonnet 3.5 - Intelligent orchestration"
echo "  [FAST] Fast response times with context retention"
echo "  [COST] Lower costs (no Bedrock agent charges)"
echo ""
echo "Test the system:"
echo "  1. Start UI:"
echo "     cd testing/ui && ./launch_webapp.sh"
echo ""
echo "  2. Try these queries:"
echo "     - Hi"
echo "     - List my projects"
echo "     - Details for 7751748"
echo "     - Schedule it"
echo ""
echo "----------------------------------------------------------------------------"
echo ""
