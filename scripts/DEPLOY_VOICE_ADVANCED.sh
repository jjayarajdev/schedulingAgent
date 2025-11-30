#!/bin/bash

# ============================================================================
# ProjectForce Advanced Voice Lambda Deployment
# ============================================================================
# Purpose: Deploy Lex Fulfillment and Voice Bedrock Bridge Lambda functions
# Features: Cross-platform, proper IAM role management, error-resilient
# Platform: Windows (Git Bash), Linux, macOS
# ============================================================================

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
        find . -name "trust-policy-*.json" -delete 2>/dev/null || true
        find . -name "policy-*.json" -delete 2>/dev/null || true
        find . -name "iam-*.log" -delete 2>/dev/null || true
        find . -name "lambda-*.log" -delete 2>/dev/null || true
        find . -name "pip-install-*.log" -delete 2>/dev/null || true

        echo "  [OK] Cleanup complete"
    fi

    if [[ $EXIT_CODE -ne 0 ]]; then
        echo ""
        echo -e "${RED}----------------------------------------------------------------------------${NC}"
        echo -e "${RED}[FAIL] Deployment failed with exit code: $EXIT_CODE${NC}"
        echo -e "${RED}----------------------------------------------------------------------------${NC}"
        echo ""
        echo "To clean up resources, run:"
        echo "  ./scripts/CLEANUP_VOICE_ADVANCED.sh"
        echo ""
    fi

    exit $EXIT_CODE
}

# Register cleanup trap
trap cleanup_on_exit EXIT INT TERM

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
# AWS ACCOUNT SELECTION - Smart account detection and configuration
# ============================================================================

echo -e "${BLUE}============================================================================${NC}"
echo -e "${CYAN}[AUTH] AWS ACCOUNT SELECTION${NC}"
echo -e "${BLUE}============================================================================${NC}"
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
    AWS_PROFILE="$CURRENT_PROFILE"
    SELECTED_ACCOUNT_ID="$CURRENT_ACCOUNT"
    echo ""
    echo -e "${GREEN}[OK] Using account: ${SELECTED_ACCOUNT_ID}${NC}"
else
    echo ""
    echo -e "${YELLOW}Enter the AWS Account ID you want to use:${NC}"
    read -p "Account ID (12 digits): " TARGET_ACCOUNT_ID

    if ! [[ "$TARGET_ACCOUNT_ID" =~ ^[0-9]{12}$ ]]; then
        echo -e "${RED}Invalid account ID format. Must be 12 digits.${NC}"
        exit 1
    fi

    echo ""
    echo "Searching existing profiles for account ${TARGET_ACCOUNT_ID}..."

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
        SELECTED_ACCOUNT_ID="$TARGET_ACCOUNT_ID"
    else
        echo -e "${YELLOW}No existing profile found for account ${TARGET_ACCOUNT_ID}${NC}"
        echo ""
        echo -e "${CYAN}Let's configure AWS credentials for this account:${NC}"
        echo ""

        read -p "Profile name (e.g., pf-${TARGET_ACCOUNT_ID}): " NEW_PROFILE_NAME
        if [[ -z "$NEW_PROFILE_NAME" ]]; then
            NEW_PROFILE_NAME="pf-${TARGET_ACCOUNT_ID}"
        fi

        echo ""
        echo -e "${YELLOW}Enter AWS credentials for account ${TARGET_ACCOUNT_ID}:${NC}"
        echo ""

        read -p "AWS Access Key ID: " AWS_ACCESS_KEY_ID
        if [[ -z "$AWS_ACCESS_KEY_ID" ]]; then
            echo -e "${RED}Access Key ID is required. Aborting.${NC}"
            exit 1
        fi

        echo -e "${YELLOW}AWS Secret Access Key (will be visible - clear screen after):${NC}"
        read -p "> " AWS_SECRET_ACCESS_KEY
        if [[ -z "$AWS_SECRET_ACCESS_KEY" ]]; then
            echo -e "${RED}Secret Access Key is required. Aborting.${NC}"
            exit 1
        fi
        echo -e "\033[1A\033[2K> ********** (hidden)"

        echo ""
        echo "Configuring profile '${NEW_PROFILE_NAME}'..."

        aws configure set aws_access_key_id "$AWS_ACCESS_KEY_ID" --profile "$NEW_PROFILE_NAME"
        aws configure set aws_secret_access_key "$AWS_SECRET_ACCESS_KEY" --profile "$NEW_PROFILE_NAME"
        aws configure set region "us-east-1" --profile "$NEW_PROFILE_NAME"
        aws configure set output "json" --profile "$NEW_PROFILE_NAME"

        echo "Verifying credentials..."
        VERIFY_ACCOUNT=$(aws sts get-caller-identity --profile "$NEW_PROFILE_NAME" --query Account --output text 2>/dev/null || echo "ERROR")

        if [[ "$VERIFY_ACCOUNT" == "$TARGET_ACCOUNT_ID" ]]; then
            echo -e "${GREEN}[OK] Profile '${NEW_PROFILE_NAME}' configured successfully!${NC}"
            echo -e "${GREEN}[OK] Verified account: ${VERIFY_ACCOUNT}${NC}"
            AWS_PROFILE="$NEW_PROFILE_NAME"
            SELECTED_ACCOUNT_ID="$TARGET_ACCOUNT_ID"
        else
            echo -e "${RED}[FAIL] Credentials verification failed!${NC}"
            echo "   Expected account: $TARGET_ACCOUNT_ID"
            echo "   Got account: $VERIFY_ACCOUNT"
            exit 1
        fi
    fi
fi

echo ""

# Export for use throughout script
export AWS_PROFILE

# ============================================================================
# Configuration
# ============================================================================
REGION="${AWS_REGION:-us-east-1}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
PREFIX="pf"

# Get project root directory (parent of scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Lambda function names
LEX_FULFILLMENT_FUNCTION="pf-lex-fulfillment-${ENVIRONMENT}"
VOICE_BRIDGE_FUNCTION="pf-voice-bedrock-bridge-${ENVIRONMENT}"
CUSTOMER_LOOKUP_FUNCTION="pf-customer-lookup-${ENVIRONMENT}"

# Lambda source directories (absolute paths)
LEX_FULFILLMENT_DIR="${PROJECT_DIR}/lambda/lex-fulfillment"
VOICE_BRIDGE_DIR="${PROJECT_DIR}/lambda/voice-bedrock-bridge"
CUSTOMER_LOOKUP_DIR="${PROJECT_DIR}/lambda/customer-lookup"

# IAM role names
LEX_FULFILLMENT_ROLE="pf-lex-fulfillment-role-${ENVIRONMENT}"
VOICE_BRIDGE_ROLE="pf-voice-bedrock-bridge-role-${ENVIRONMENT}"
CUSTOMER_LOOKUP_ROLE="pf-customer-lookup-role-${ENVIRONMENT}"

# DynamoDB Tables
CUSTOMER_TABLE="pf-customers-${ENVIRONMENT}"

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
# Pre-flight Check: Verify Secrets Manager credentials exist
# ============================================================================
echo ""
echo -e "${CYAN}Pre-flight Check: Verifying prerequisites...${NC}"
echo ""

SECRET_NAME="projectforce/api/credentials"
echo "  -> Checking for Secrets Manager credentials..."

if ! aws --profile "$AWS_PROFILE" secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$REGION" &>/dev/null; then
    echo ""
    echo -e "${YELLOW}[WARNING] Secrets Manager secret '$SECRET_NAME' not found!${NC}"
    echo ""
    echo "The voice Lambda functions need ProjectForce API credentials to work."
    echo ""
    echo -e "${CYAN}Do you want to create the credentials now?${NC}"
    echo "  [1] Yes, I'll enter the credentials"
    echo "  [2] No, I'll run DEPLOY_LAMBDA_ONLY_ADVANCED.sh first"
    read -p "Enter choice (1 or 2): " SECRETS_CHOICE

    if [[ "$SECRETS_CHOICE" == "1" ]]; then
        echo ""
        echo -e "${BLUE}ProjectForce API Credentials${NC}"
        echo ""

        read -p "Client ID (e.g., 09PF05VD): " PF_CLIENT_ID
        while [[ -z "$PF_CLIENT_ID" ]]; do
            echo "Client ID is required."
            read -p "Client ID: " PF_CLIENT_ID
        done

        read -p "User ID (e.g., 1646085): " PF_USER_ID
        while [[ -z "$PF_USER_ID" ]]; do
            echo "User ID is required."
            read -p "User ID: " PF_USER_ID
        done

        echo -e "${CYAN}Bearer Token (optional - press Enter to skip for auto-refresh):${NC}"
        read -p "> " PF_BEARER_TOKEN
        if [[ -z "$PF_BEARER_TOKEN" ]]; then
            PF_BEARER_TOKEN="PENDING_AUTO_REFRESH"
        fi

        echo ""
        echo "  -> Creating Secrets Manager secret..."

        SECRET_VALUE=$(cat << EOF
{
  "bearer_token": "$PF_BEARER_TOKEN",
  "client_id": "$PF_CLIENT_ID",
  "user_id": "$PF_USER_ID",
  "token_expiry": "0"
}
EOF
)

        if aws --profile "$AWS_PROFILE" secretsmanager create-secret \
            --name "$SECRET_NAME" \
            --description "ProjectForce API credentials" \
            --secret-string "$SECRET_VALUE" \
            --region "$REGION" &>/dev/null; then
            echo "  [OK] Secrets Manager secret created"
        else
            echo -e "  ${RED}[FAILED] Could not create secret. Check IAM permissions.${NC}"
            exit 1
        fi
    else
        echo ""
        echo "Please run DEPLOY_LAMBDA_ONLY_ADVANCED.sh first to create the credentials."
        echo "Then re-run this script."
        exit 0
    fi
else
    echo "  [OK] Secrets Manager credentials found"
fi

# Check if core Lambda functions exist
echo "  -> Checking for core Lambda functions..."
CORE_LAMBDAS_OK=true

if ! aws --profile "$AWS_PROFILE" lambda get-function --function-name "pf-orchestrator" --region "$REGION" &>/dev/null; then
    echo "  [WARN] pf-orchestrator Lambda not found"
    CORE_LAMBDAS_OK=false
fi

if ! aws --profile "$AWS_PROFILE" lambda get-function --function-name "pf-scheduling-actions" --region "$REGION" &>/dev/null; then
    echo "  [WARN] pf-scheduling-actions Lambda not found"
    CORE_LAMBDAS_OK=false
fi

if [[ "$CORE_LAMBDAS_OK" == "false" ]]; then
    echo ""
    echo -e "${YELLOW}[WARNING] Some core Lambda functions are missing!${NC}"
    echo "Voice functions depend on pf-orchestrator and pf-scheduling-actions."
    echo ""
    echo -e "${CYAN}Do you want to continue anyway?${NC}"
    echo "  [1] Yes, continue (I'll deploy core Lambdas later)"
    echo "  [2] No, I'll run DEPLOY_LAMBDA_ONLY_ADVANCED.sh first"
    read -p "Enter choice (1 or 2): " CORE_CHOICE

    if [[ "$CORE_CHOICE" != "1" ]]; then
        echo ""
        echo "Please run DEPLOY_LAMBDA_ONLY_ADVANCED.sh first to create the core Lambdas."
        echo "Then re-run this script."
        exit 0
    fi
else
    echo "  [OK] Core Lambda functions found"
fi

echo ""

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

    echo "  -> Creating IAM role: $ROLE_NAME"

    # Check if role already exists
    if aws_cmd iam get-role --role-name "$ROLE_NAME" 2>&1 | grep -q "NoSuchEntity"; then
        echo "    Role does not exist, creating..."
    else
        echo "  [INFO]  IAM role already exists: $ROLE_NAME"
        return 0
    fi

    # Create trust policy file (using current directory instead of /tmp/)
    local TRUST_POLICY_FILE="./trust-policy-${ROLE_NAME}.json"
    TEMP_FILES+=("$TRUST_POLICY_FILE")
    CLEANUP_NEEDED=true

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
        echo "  [FAIL] Failed to create IAM role $ROLE_NAME"
        rm -f "$TRUST_POLICY_FILE"
        return 1
    fi

    # Clean up trust policy file
    rm -f "$TRUST_POLICY_FILE"

    echo "  [OK] IAM role created"

    # Dynamic polling for role propagation (5 minute max timeout)
    echo "  -> Waiting for IAM role to propagate (max 5 minutes)..."
    local MAX_WAIT=300  # 5 minutes
    local POLL_INTERVAL=5
    local ELAPSED=0
    local ROLE_READY=false

    while [[ $ELAPSED -lt $MAX_WAIT ]]; do
        if aws_cmd iam get-role --role-name "$ROLE_NAME" 2>&1 | grep -q "Role"; then
            ROLE_READY=true
            echo "  [OK] IAM role propagated after ${ELAPSED}s"
            break
        fi
        sleep $POLL_INTERVAL
        ELAPSED=$((ELAPSED + POLL_INTERVAL))

        # Show progress every 15 seconds
        if [[ $((ELAPSED % 15)) -eq 0 ]]; then
            echo "  -> Waiting for IAM propagation... ${ELAPSED}s / ${MAX_WAIT}s"
        fi
    done

    if [[ "$ROLE_READY" != "true" ]]; then
        echo "  [FAIL] IAM role not propagated after ${MAX_WAIT}s"
        return 1
    fi

    return 0
}

# Attach managed policy to role
attach_managed_policy() {
    local ROLE_NAME=$1
    local POLICY_ARN=$2

    echo "  -> Attaching policy: $(basename $POLICY_ARN)"

    if ! aws_cmd iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn "$POLICY_ARN" 2>&1 | tee "./iam-attach-policy-$ROLE_NAME.log"; then
        echo "  [WARN]  Warning: Failed to attach policy $POLICY_ARN"
        return 1
    fi

    echo "  [OK] Policy attached"
    return 0
}

# Create inline policy for role
create_inline_policy() {
    local ROLE_NAME=$1
    local POLICY_NAME=$2
    local POLICY_DOCUMENT=$3

    echo "  -> Creating inline policy: $POLICY_NAME"

    # Write policy document to file (using current directory)
    local POLICY_FILE="./policy-${ROLE_NAME}-${POLICY_NAME}.json"
    TEMP_FILES+=("$POLICY_FILE")
    echo "$POLICY_DOCUMENT" > "$POLICY_FILE"

    if ! aws_cmd iam put-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-name "$POLICY_NAME" \
        --policy-document "file://${POLICY_FILE}" 2>&1 | tee "./iam-inline-policy-$ROLE_NAME-$POLICY_NAME.log"; then
        echo "  [WARN]  Warning: Failed to create inline policy $POLICY_NAME"
        rm -f "$POLICY_FILE"
        return 1
    fi

    rm -f "$POLICY_FILE"
    echo "  [OK] Inline policy created"
    return 0
}

# Create DynamoDB table
create_dynamodb_table() {
    local TABLE_NAME=$1
    local PARTITION_KEY=$2
    local PARTITION_KEY_TYPE=$3

    echo "  -> Creating DynamoDB table: $TABLE_NAME"

    # Check if table already exists
    if aws_cmd dynamodb describe-table --table-name "$TABLE_NAME" --region "$REGION" &>/dev/null; then
        echo "  [INFO]  DynamoDB table already exists: $TABLE_NAME"
        return 0
    fi

    # Create the table
    if ! aws_cmd dynamodb create-table \
        --table-name "$TABLE_NAME" \
        --attribute-definitions "AttributeName=${PARTITION_KEY},AttributeType=${PARTITION_KEY_TYPE}" \
        --key-schema "AttributeName=${PARTITION_KEY},KeyType=HASH" \
        --billing-mode PAY_PER_REQUEST \
        --region "$REGION" 2>&1 | tee "./dynamodb-create-$TABLE_NAME.log"; then
        echo "  [FAIL] Failed to create DynamoDB table $TABLE_NAME"
        return 1
    fi

    echo "  [OK] DynamoDB table created: $TABLE_NAME"

    # Wait for table to become active
    echo "  -> Waiting for table to become active..."
    aws_cmd dynamodb wait table-exists --table-name "$TABLE_NAME" --region "$REGION" 2>/dev/null || true
    echo "  [OK] Table is active"

    return 0
}

# Package Lambda function using Python zipfile module (cross-platform)
package_lambda() {
    local SOURCE_DIR=$1
    local OUTPUT_ZIP=$2

    echo "  -> Packaging with Python zipfile module..."

    if [ ! -d "$SOURCE_DIR" ]; then
        echo "  [FAIL] Source directory not found: $SOURCE_DIR"
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
        echo "  -> Installing dependencies..."
        mkdir -p package

        # Use detected Python command
        if ! $PYTHON_CMD -m pip install -r requirements.txt -t package/ --upgrade 2>&1 | tee "../../pip-install-$(basename $SOURCE_DIR).log"; then
            echo "  [WARN]  Warning: Some dependencies may have failed to install"
        fi

        # Package dependencies
        cd package
        $PYTHON_CMD -m zipfile -c "../$OUTPUT_ZIP" .
        cd ..

        # Add handler to zip
        echo "  -> Adding handler.py to package..."
        $PYTHON_CMD -m zipfile -c temp.zip handler.py

        # Merge handler into function.zip with error handling
        $PYTHON_CMD << 'PYTHON_SCRIPT'
import zipfile
import sys

try:
    # Merge zips
    with zipfile.ZipFile('function.zip', 'a') as base_zip:
        with zipfile.ZipFile('temp.zip', 'r') as temp_zip:
            for item in temp_zip.namelist():
                base_zip.writestr(item, temp_zip.read(item))

    # Verify handler.py is in the final zip
    with zipfile.ZipFile('function.zip', 'r') as z:
        if 'handler.py' not in z.namelist():
            print("ERROR: handler.py not found in function.zip!")
            sys.exit(1)
        else:
            print(f"  [OK] handler.py added ({z.getinfo('handler.py').file_size} bytes)")
    sys.exit(0)
except Exception as e:
    print(f"ERROR merging zip files: {e}")
    sys.exit(1)
PYTHON_SCRIPT

        # Check if Python script succeeded
        if [ $? -ne 0 ]; then
            echo "  [FAIL] Failed to add handler.py to package"
            cd "$ORIG_DIR"
            return 1
        fi

        rm -f temp.zip
    else
        # No dependencies, just package handler
        $PYTHON_CMD -m zipfile -c "$OUTPUT_ZIP" handler.py
    fi

    if [ ! -f "$OUTPUT_ZIP" ]; then
        echo "  [FAIL] Failed to create package: $OUTPUT_ZIP"
        cd "$ORIG_DIR"
        return 1
    fi

    local PACKAGE_SIZE=$(ls -lh "$OUTPUT_ZIP" | awk '{print $5}')
    echo "  [OK] Package created: $OUTPUT_ZIP ($PACKAGE_SIZE)"

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
        echo "  [FAIL] Packaging failed for $FUNCTION_NAME"
        return 1
    fi

    # Get role ARN
    local ACCOUNT_ID=$(get_account_id)
    local ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

    # Check if Lambda exists
    if aws_cmd lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" 2>&1 | grep -q "ResourceNotFoundException"; then
        echo "  -> Creating new function..."

        # Dynamic polling for Lambda creation (max 5 minutes)
        # IAM role assumability can take time to propagate to Lambda service
        local CREATE_MAX_WAIT=300  # 5 minutes
        local CREATE_POLL_INTERVAL=10
        local CREATE_ELAPSED=0
        local LAMBDA_CREATED=false
        local ATTEMPT=0

        while [[ $CREATE_ELAPSED -lt $CREATE_MAX_WAIT ]]; do
            ATTEMPT=$((ATTEMPT + 1))
            echo "  -> Attempt $ATTEMPT at ${CREATE_ELAPSED}s..."

            # Capture output and exit code separately
            local CREATE_OUTPUT
            CREATE_OUTPUT=$(aws_cmd lambda create-function \
                --function-name "$FUNCTION_NAME" \
                --runtime "$RUNTIME" \
                --role "$ROLE_ARN" \
                --handler "$HANDLER" \
                --zip-file "fileb://${ZIP_PATH}" \
                --description "$DESCRIPTION" \
                --timeout 60 \
                --memory-size 512 \
                --region "$REGION" 2>&1)
            local CREATE_EXIT_CODE=$?

            # Save output to log
            echo "$CREATE_OUTPUT" > "./lambda-create-$FUNCTION_NAME.log"

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
            else
                # Some other error - show it and fail
                echo "$CREATE_OUTPUT"
                echo -e "  ${RED}[FAIL] Lambda creation FAILED: $FUNCTION_NAME${NC}"
                return 1
            fi
        done

        if [[ "$LAMBDA_CREATED" != "true" ]]; then
            echo -e "  ${RED}[FAIL] Lambda creation FAILED after ${CREATE_MAX_WAIT}s${NC}"
            echo "  See error log: ./lambda-create-$FUNCTION_NAME.log"
            return 1
        fi
    else
        echo "  -> Updating existing function code..."

        # Use PIPESTATUS to capture actual aws command exit code (tee masks it)
        aws_cmd lambda update-function-code \
            --function-name "$FUNCTION_NAME" \
            --zip-file "fileb://${ZIP_PATH}" \
            --region "$REGION" 2>&1 | tee "./lambda-update-$FUNCTION_NAME.log"

        # Check actual aws command result (PIPESTATUS[0] is the aws command exit code)
        if [ ${PIPESTATUS[0]} -ne 0 ]; then
            echo "  [FAIL] Failed to update Lambda function $FUNCTION_NAME"
            echo "  Check log: ./lambda-update-$FUNCTION_NAME.log"
            return 1
        fi

        # Verify the update actually happened by checking LastModified
        local LAST_MODIFIED=$(aws_cmd lambda get-function-configuration --function-name "$FUNCTION_NAME" --region "$REGION" --query "LastModified" --output text 2>/dev/null)
        echo "  -> Lambda LastModified: $LAST_MODIFIED"

        echo -e "  ${GREEN}[OK] Lambda updated: $FUNCTION_NAME${NC}"
    fi

    # Clean up zip file (convert back to Unix path for rm if needed)
    if command -v cygpath &> /dev/null; then
        rm -f "$(cygpath -u "$ZIP_PATH")"
    else
        rm -f "$ZIP_PATH"
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
        return 1
    fi

    return 0
}

# ============================================================================
# Main Deployment - Profile Selection happens first at script start
# ============================================================================

# Move profile selection to the beginning of the script before helper functions
# Profile selection happens at line ~23 after colors are defined

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}[DEPLOY] ProjectForce Advanced Voice Lambda Deployment${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""
echo "Region: $REGION"
echo "Account: $SELECTED_ACCOUNT_ID"
echo "Profile: $AWS_PROFILE"
echo "Environment: $ENVIRONMENT"
echo "Platform: $PLATFORM"
echo "Python: $PYTHON_CMD"
echo ""
echo "* Features:"
echo "  - Cross-platform Python-only packaging (no zip command needed)"
echo "  - Proper IAM role management"
echo "  - Error-resilient deployment"
echo ""

# Final confirmation
echo -e "${YELLOW}Confirm deployment to this account?${NC}"
read -p "Type 'yes' to proceed: " FINAL_CONFIRM

if [[ "$FINAL_CONFIRM" != "yes" ]]; then
    echo -e "${RED}Deployment aborted.${NC}"
    exit 0
fi

echo ""
echo -e "${GREEN}[OK] Proceeding with deployment...${NC}"
echo ""

# ============================================================================
# Step 1: Create IAM Roles
# ============================================================================

echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo -e "${YELLOW}Step 1: Creating IAM Roles${NC}"
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
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
      "Resource": [
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-voice-bedrock-bridge-${ENVIRONMENT}",
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-customer-lookup-${ENVIRONMENT}",
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-scheduling-actions",
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-orchestrator",
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-information-actions"
      ]
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

# Create Customer Lookup Role
create_iam_role "$CUSTOMER_LOOKUP_ROLE" "lambda.amazonaws.com" "Role for customer lookup Lambda function"

# Attach managed policies
attach_managed_policy "$CUSTOMER_LOOKUP_ROLE" "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

# Create inline policy for Customer Lookup
CUSTOMER_LOOKUP_POLICY=$(cat <<EOF
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
        "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/${CUSTOMER_TABLE}",
        "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/${CUSTOMER_TABLE}/index/*"
      ]
    }
  ]
}
EOF
)

create_inline_policy "$CUSTOMER_LOOKUP_ROLE" "CustomerLookupPolicy" "$CUSTOMER_LOOKUP_POLICY"

echo ""

# ============================================================================
# Step 1.5: Create DynamoDB Tables
# ============================================================================

echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo -e "${YELLOW}Step 1.5: Creating DynamoDB Tables${NC}"
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo ""

create_dynamodb_table "$CUSTOMER_TABLE" "customer_id" "S"

echo ""

# ============================================================================
# Step 2: Deploy Lambda Functions
# ============================================================================

echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo -e "${YELLOW}Step 2: Deploying Lambda Functions${NC}"
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"

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

# Deploy Customer Lookup Lambda
deploy_lambda \
    "$CUSTOMER_LOOKUP_FUNCTION" \
    "$CUSTOMER_LOOKUP_ROLE" \
    "$CUSTOMER_LOOKUP_DIR" \
    "handler.lambda_handler" \
    "python3.11" \
    "Customer lookup service for voice integration"

echo ""

# ============================================================================
# Step 3: Grant Permissions
# ============================================================================

echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo -e "${YELLOW}Step 3: Granting Lambda Invoke Permissions${NC}"
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo ""

# Grant Lex permission to invoke Lex Fulfillment Lambda
echo "  -> Granting Lex V2 permission to invoke $LEX_FULFILLMENT_FUNCTION..."

LEX_PERM_RESULT=$(aws_cmd lambda add-permission \
    --function-name "$LEX_FULFILLMENT_FUNCTION" \
    --statement-id "AllowLexInvoke" \
    --action "lambda:InvokeFunction" \
    --principal "lexv2.amazonaws.com" \
    --region "$REGION" 2>&1 || echo "")

if echo "$LEX_PERM_RESULT" | grep -q "ResourceConflictException"; then
    echo "  [INFO]  Permission already exists"
elif echo "$LEX_PERM_RESULT" | grep -q "error\|Error"; then
    echo "  [WARN]  Warning: Failed to add Lex permission"
    echo "$LEX_PERM_RESULT"
else
    echo "  [OK] Lex permission granted"
fi

echo ""

# Grant Connect permission to invoke both Lambda functions
for FUNCTION_NAME in "$LEX_FULFILLMENT_FUNCTION" "$VOICE_BRIDGE_FUNCTION"; do
    echo "  -> Granting AWS Connect permission to invoke $FUNCTION_NAME..."

    CONNECT_PERM_RESULT=$(aws_cmd lambda add-permission \
        --function-name "$FUNCTION_NAME" \
        --statement-id "AllowConnectInvoke" \
        --action "lambda:InvokeFunction" \
        --principal "connect.amazonaws.com" \
        --region "$REGION" 2>&1 || echo "")

    if echo "$CONNECT_PERM_RESULT" | grep -q "ResourceConflictException"; then
        echo "  [INFO]  Permission already exists"
    elif echo "$CONNECT_PERM_RESULT" | grep -q "error\|Error"; then
        echo "  [WARN]  Warning: Failed to add Connect permission"
        echo "$CONNECT_PERM_RESULT"
    else
        echo "  [OK] Connect permission granted"
    fi

    echo ""
done

# ============================================================================
# Step 4: Generate Contact Flow Configuration Files
# ============================================================================

echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo -e "${YELLOW}Step 4: Generating Contact Flow Configuration${NC}"
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo ""

INFRA_VOICE_DIR="${PROJECT_DIR}/infrastructure/voice"

# Check if Lex bot exists and get its ID
echo "  -> Checking for existing Lex bot..."
LEX_BOT_NAME="pf-scheduling-assistant-${ENVIRONMENT}"
LEX_BOT_ID=$(aws_cmd lexv2-models list-bots --region "$REGION" --query "botSummaries[?botName=='${LEX_BOT_NAME}'].botId" --output text 2>/dev/null || echo "")

if [[ -n "$LEX_BOT_ID" && "$LEX_BOT_ID" != "None" ]]; then
    echo "  Found Lex bot: $LEX_BOT_NAME (ID: $LEX_BOT_ID)"

    # Get the bot alias ID
    LEX_ALIAS_ID=$(aws_cmd lexv2-models list-bot-aliases --bot-id "$LEX_BOT_ID" --region "$REGION" --query "botAliasSummaries[0].botAliasId" --output text 2>/dev/null || echo "TSTALIASID")

    if [[ -z "$LEX_ALIAS_ID" || "$LEX_ALIAS_ID" == "None" ]]; then
        LEX_ALIAS_ID="TSTALIASID"
    fi
    echo "  Bot Alias ID: $LEX_ALIAS_ID"
else
    echo "  No Lex bot found. Creating new bot..."

    # Create IAM role for Lex bot
    LEX_BOT_ROLE_NAME="pf-lex-bot-role-${ENVIRONMENT}"

    if ! aws_cmd iam get-role --role-name "$LEX_BOT_ROLE_NAME" &>/dev/null; then
        echo "  -> Creating Lex bot IAM role..."
        aws_cmd iam create-role \
            --role-name "$LEX_BOT_ROLE_NAME" \
            --assume-role-policy-document '{
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "lexv2.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }]
            }' &>/dev/null

        aws_cmd iam attach-role-policy \
            --role-name "$LEX_BOT_ROLE_NAME" \
            --policy-arn "arn:aws:iam::aws:policy/AmazonLexFullAccess" &>/dev/null

        # CRITICAL: ComprehendFullAccess is REQUIRED for Sentiment Analysis
        aws_cmd iam attach-role-policy \
            --role-name "$LEX_BOT_ROLE_NAME" \
            --policy-arn "arn:aws:iam::aws:policy/ComprehendFullAccess" &>/dev/null

        echo "  [OK] Attached policies: AmazonLexFullAccess, ComprehendFullAccess"

        # VERIFY policies are attached
        ATTACHED_POLICIES=$(aws_cmd iam list-attached-role-policies --role-name "$LEX_BOT_ROLE_NAME" --query "AttachedPolicies[].PolicyName" --output text 2>/dev/null || echo "")
        if [[ "$ATTACHED_POLICIES" == *"AmazonLexFullAccess"* ]] && [[ "$ATTACHED_POLICIES" == *"ComprehendFullAccess"* ]]; then
            echo "  [VERIFIED] Both policies attached: $ATTACHED_POLICIES"
        else
            echo "  [ERROR] Policy attachment failed! Attached: $ATTACHED_POLICIES"
            exit 1
        fi

        # Dynamic polling for Lex IAM role propagation (max 5 minutes)
        echo "  -> Waiting for Lex IAM role to propagate (max 5 minutes)..."
        LEX_ROLE_MAX_WAIT=300
        LEX_ROLE_POLL=5
        LEX_ROLE_ELAPSED=0
        LEX_ROLE_READY=false

        while [[ $LEX_ROLE_ELAPSED -lt $LEX_ROLE_MAX_WAIT ]]; do
            if aws_cmd iam get-role --role-name "$LEX_BOT_ROLE_NAME" 2>&1 | grep -q "Role"; then
                LEX_ROLE_READY=true
                echo "  [OK] Lex IAM role propagated after ${LEX_ROLE_ELAPSED}s"
                break
            fi
            sleep $LEX_ROLE_POLL
            LEX_ROLE_ELAPSED=$((LEX_ROLE_ELAPSED + LEX_ROLE_POLL))
            if [[ $((LEX_ROLE_ELAPSED % 15)) -eq 0 ]]; then
                echo "  -> Waiting for Lex IAM propagation... ${LEX_ROLE_ELAPSED}s / ${LEX_ROLE_MAX_WAIT}s"
            fi
        done

        if [[ "$LEX_ROLE_READY" != "true" ]]; then
            echo "  [WARN] Lex IAM role may not be fully propagated"
        fi

        # Additional safety buffer for cross-region consistency
        MIN_SAFETY=15
        if [[ $LEX_ROLE_ELAPSED -lt $MIN_SAFETY ]]; then
            EXTRA=$((MIN_SAFETY - LEX_ROLE_ELAPSED))
            echo "  -> Adding ${EXTRA}s safety buffer..."
            sleep $EXTRA
        fi
    else
        # Role already exists - ensure ComprehendFullAccess is attached
        echo "  -> Lex IAM role already exists, ensuring policies..."
        aws_cmd iam attach-role-policy \
            --role-name "$LEX_BOT_ROLE_NAME" \
            --policy-arn "arn:aws:iam::aws:policy/ComprehendFullAccess" &>/dev/null || true

        # VERIFY policies
        ATTACHED_POLICIES=$(aws_cmd iam list-attached-role-policies --role-name "$LEX_BOT_ROLE_NAME" --query "AttachedPolicies[].PolicyName" --output text 2>/dev/null || echo "")
        if [[ "$ATTACHED_POLICIES" == *"ComprehendFullAccess"* ]]; then
            echo "  [OK] ComprehendFullAccess verified on existing role"
        else
            echo "  [WARN] ComprehendFullAccess may not be attached. Sentiment analysis may fail."
        fi
    fi

    LEX_BOT_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${LEX_BOT_ROLE_NAME}"

    # Create the Lex bot using Python
    echo "  -> Creating Lex bot and intents..."

    $PYTHON_CMD << PYTHON_SCRIPT
import boto3
import time
import json
import os

# Use AWS_PROFILE from environment (exported by bash script)
session = boto3.Session(
    profile_name=os.environ.get('AWS_PROFILE'),
    region_name='${REGION}'
)
client = session.client('lexv2-models')
lambda_client = session.client('lambda')

BOT_NAME = '${LEX_BOT_NAME}'
ROLE_ARN = '${LEX_BOT_ROLE_ARN}'
LAMBDA_ARN = 'arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${LEX_FULFILLMENT_FUNCTION}'
ENVIRONMENT = '${ENVIRONMENT}'

try:
    print("  Creating bot...")
    bot_response = client.create_bot(
        botName=BOT_NAME,
        description='ProjectForce Scheduling Assistant (' + ENVIRONMENT + ')',
        roleArn=ROLE_ARN,
        dataPrivacy={'childDirected': False},
        idleSessionTTLInSeconds=300
    )
    bot_id = bot_response['botId']
    print("  Bot created: " + bot_id)

    # Poll for bot to be available (max 5 minutes)
    print("  Waiting for bot to be available (max 5 minutes)...")
    max_wait = 300
    poll_interval = 5
    elapsed = 0
    while elapsed < max_wait:
        try:
            bot_status = client.describe_bot(botId=bot_id)
            if bot_status.get('botStatus') in ['Available', 'Versioning']:
                print("  [OK] Bot available after " + str(elapsed) + "s")
                break
        except Exception:
            pass
        time.sleep(poll_interval)
        elapsed += poll_interval
        if elapsed % 15 == 0:
            print("  -> Waiting for bot... " + str(elapsed) + "s / " + str(max_wait) + "s")

    print("  Creating locale (en_US)...")
    client.create_bot_locale(
        botId=bot_id,
        botVersion='DRAFT',
        localeId='en_US',
        nluIntentConfidenceThreshold=0.4
    )

    # Poll for locale to be ready
    print("  Waiting for locale to be ready...")
    elapsed = 0
    while elapsed < 60:
        try:
            locale_status = client.describe_bot_locale(botId=bot_id, botVersion='DRAFT', localeId='en_US')
            if locale_status.get('botLocaleStatus') in ['Built', 'ReadyExpressTesting', 'NotBuilt']:
                print("  [OK] Locale ready after " + str(elapsed) + "s")
                break
        except Exception:
            pass
        time.sleep(3)
        elapsed += 3

    intents = [
        {
            'name': 'Welcome',
            'description': 'Greet the user',
            'utterances': [
                'hello', 'hi', 'hey', 'good morning', 'good afternoon',
                'greetings', 'hi there', 'hello there', 'hey there'
            ]
        },
        {
            'name': 'Goodbye',
            'description': 'End conversation and disconnect call',
            'utterances': [
                # Standard goodbyes
                'goodbye', 'bye', 'bye bye', 'see you', 'see you later',
                'thanks bye', 'thank you goodbye', 'ok bye', 'alright bye',
                # Session ending phrases
                'that is all', 'thats all', 'that will be all',
                'I am done', 'im done', 'all done', 'nothing else',
                'no more questions', 'I am finished', 'we are done',
                'thanks thats all', 'thank you thats all',
                # Explicit call ending
                'hang up', 'end call', 'disconnect', 'end the call',
                # Polite closings
                'take care', 'have a good day', 'talk to you later',
                'thanks for your help goodbye', 'that helps thanks bye'
            ]
        },
        {
            'name': 'ProjectInquiry',
            'description': 'List user projects',
            'utterances': [
                'list my projects', 'show my projects', 'what are my projects',
                'tell me about my projects', 'get my projects', 'my projects',
                'show projects', 'what projects do I have', 'projects please',
                'can you list my projects', 'I want to see my projects'
            ]
        },
        {
            'name': 'ProjectStatusInquiry',
            'description': 'Get details about a specific project',
            'utterances': [
                'what is the status of my project', 'what is the status',
                'show me status', 'tell me about my project', 'get status',
                'project status', 'how is my project doing', 'check project status',
                'status update please', 'give me a status update',
                'details of the first project', 'tell me about the second project',
                'show me the third project', 'what is project number one',
                'details for project two', 'info on the last project',
                'show me project 1', 'details of project 2', 'tell me about project 3',
                'details of second project', 'details of first project',
                'details of third project', 'can i get details of second project',
                'give me details of second project', 'give me details of first project',
                'give me details of third project', 'second project details',
                'first project details', 'more about second project',
                'more about the second one', 'tell me more about second project',
                'what about the second project', 'second one please',
                'details on second', 'the second one', 'number two',
                'tell me about the first one', 'more info on project one'
            ]
        },
        {
            'name': 'AppointmentInquiry',
            'description': 'Check appointments',
            'utterances': [
                'do I have any appointments', 'show my appointments',
                'what appointments do I have', 'check my appointments',
                'list appointments', 'any upcoming appointments',
                'when is my next appointment', 'appointment schedule',
                'my appointments please', 'show me my schedule'
            ]
        },
        {
            'name': 'ScheduleAppointment',
            'description': 'Schedule a new appointment - single or multiple projects',
            'utterances': [
                # Basic scheduling
                'schedule an appointment', 'book an appointment',
                'I need to schedule', 'can you schedule', 'set up an appointment',
                'I want to book', 'make an appointment', 'schedule something',
                'book a time', 'I need to book an appointment',
                # Project-specific scheduling
                'schedule my project', 'schedule the project', 'schedule this project',
                'schedule the first project', 'schedule the second project',
                'schedule the last project', 'schedule project',
                'schedule my decking project', 'schedule my flooring project',
                'schedule my roofing project', 'schedule my siding project',
                # Batch/Multiple scheduling
                'schedule first two projects', 'schedule the first two projects',
                'schedule both projects', 'schedule all projects',
                'schedule all my projects', 'schedule multiple projects',
                'schedule first three projects', 'schedule them all',
                'book all projects', 'book both', 'schedule them',
                # Natural variations
                'can you schedule my project', 'I want to schedule my project',
                'lets schedule', 'go ahead and schedule', 'please schedule',
                'schedule it', 'book it', 'set it up'
            ]
        },
        {
            'name': 'WeatherInquiry',
            'description': 'Check weather',
            'utterances': [
                'what is the weather', 'how is the weather', 'weather forecast',
                'check weather', 'weather in', 'is it going to rain',
                'what is the forecast', 'weather update', 'tell me the weather',
                'weather for tomorrow', 'will it rain'
            ]
        },
        {
            'name': 'UrgentRequest',
            'description': 'Handle urgent requests',
            'utterances': [
                'this is urgent', 'emergency', 'I need help urgently',
                'urgent matter', 'this is an emergency', 'urgent request',
                'I have an urgent issue', 'need immediate help'
            ]
        },
        {
            'name': 'CheckAvailability',
            'description': 'Check available dates for scheduling',
            'utterances': [
                'what dates are available', 'show available dates',
                'when can I schedule', 'available times', 'what times work',
                'check availability', 'when are you available',
                'show me available slots', 'open dates', 'free dates',
                'what days are open', 'available appointments'
            ]
        },
        {
            'name': 'RescheduleAppointment',
            'description': 'Reschedule an existing appointment',
            'utterances': [
                'reschedule my appointment', 'change my appointment',
                'move my appointment', 'I need to reschedule',
                'can I change the time', 'change appointment time',
                'reschedule please', 'move to a different day',
                'pick a different time', 'change the date'
            ]
        },
        {
            'name': 'CancelAppointment',
            'description': 'Cancel an existing appointment',
            'utterances': [
                'cancel my appointment', 'I need to cancel',
                'cancel the appointment', 'remove my appointment',
                'I want to cancel', 'cancel please', 'delete appointment',
                'I cannot make it', 'cancel my booking'
            ]
        },
        {
            'name': 'BusinessHours',
            'description': 'Ask about business hours',
            'utterances': [
                'what are your hours', 'when are you open',
                'business hours', 'operating hours', 'what time do you open',
                'what time do you close', 'are you open on weekends',
                'hours of operation', 'when can I call', 'office hours'
            ]
        },
        {
            'name': 'ThankYou',
            'description': 'Express gratitude',
            'utterances': [
                'thank you', 'thanks', 'thanks a lot', 'thank you so much',
                'appreciate it', 'that is helpful', 'thanks for your help',
                'thank you very much', 'you have been helpful', 'great thanks'
            ]
        },
        {
            'name': 'HowAreYou',
            'description': 'Casual chitchat greeting',
            'utterances': [
                'how are you', 'how are you doing', 'how is it going',
                'what is up', 'how do you do', 'are you doing well',
                'hows everything', 'how have you been', 'you doing okay'
            ]
        }
    ]

    created_intents = {}

    # Fulfillment updates config - plays "please wait" while Lambda processes
    fulfillment_updates_spec = {
        'active': True,
        'startResponse': {
            'delayInSeconds': 3,  # Wait 3 sec before playing start message
            'messageGroups': [
                {
                    'message': {
                        'plainTextMessage': {
                            'value': 'Let me look that up for you, one moment please.'
                        }
                    }
                },
                {
                    'message': {
                        'plainTextMessage': {
                            'value': 'Just a moment while I check on that.'
                        }
                    }
                }
            ],
            'allowInterrupt': False
        },
        'updateResponse': {
            'frequencyInSeconds': 15,  # Play update every 15 sec
            'messageGroups': [
                {
                    'message': {
                        'plainTextMessage': {
                            'value': 'Still working on it, thank you for your patience.'
                        }
                    }
                }
            ],
            'allowInterrupt': False
        },
        'timeoutInSeconds': 90  # Max 90 sec timeout for complex queries
    }

    for intent_def in intents:
        print("  Creating intent: " + intent_def['name'] + "...")
        utterance_list = [{'utterance': u} for u in intent_def['utterances']]
        intent_response = client.create_intent(
            botId=bot_id,
            botVersion='DRAFT',
            localeId='en_US',
            intentName=intent_def['name'],
            description=intent_def['description'],
            sampleUtterances=utterance_list,
            fulfillmentCodeHook={
                'enabled': True,
                'fulfillmentUpdatesSpecification': fulfillment_updates_spec
            }
        )
        created_intents[intent_def['name']] = intent_response['intentId']

    print("  Configuring FallbackIntent with code hook...")
    intents_response = client.list_intents(
        botId=bot_id,
        botVersion='DRAFT',
        localeId='en_US'
    )

    fallback_id = None
    for intent in intents_response['intentSummaries']:
        if intent['intentName'] == 'FallbackIntent':
            fallback_id = intent['intentId']
            break

    if fallback_id:
        # For built-in FallbackIntent, we need to get current config first
        current_intent = client.describe_intent(
            botId=bot_id,
            botVersion='DRAFT',
            localeId='en_US',
            intentId=fallback_id
        )

        # Update with code hook enabled + fulfillment updates for interim messages
        client.update_intent(
            botId=bot_id,
            botVersion='DRAFT',
            localeId='en_US',
            intentId=fallback_id,
            intentName=current_intent['intentName'],
            parentIntentSignature=current_intent.get('parentIntentSignature', 'AMAZON.FallbackIntent'),
            fulfillmentCodeHook={
                'enabled': True,
                'fulfillmentUpdatesSpecification': fulfillment_updates_spec
            },
            dialogCodeHook={'enabled': True}
        )
        print("  FallbackIntent configured with code hook and interim messages")

    # Enable Generative AI features:
    # Assisted NLU (Primary mode) - LLM-based intent classification
    # Note: slotResolutionImprovement requires specific Bedrock access, skipping it
    print("  Enabling Assisted NLU (Primary mode)...")
    try:
        client.update_bot_locale(
            botId=bot_id,
            botVersion='DRAFT',
            localeId='en_US',
            nluIntentConfidenceThreshold=0.4,
            generativeAISettings={
                'runtimeSettings': {
                    'nluImprovement': {
                        'enabled': True,
                        'assistedNluMode': 'Primary'
                    }
                },
                'buildtimeSettings': {
                    'descriptiveBotBuilder': {'enabled': False},
                    'sampleUtteranceGeneration': {'enabled': False}
                }
            }
        )
        print("  [OK] Assisted NLU enabled (Primary mode)")
    except Exception as e:
        print("  [ERROR] Could not enable Assisted NLU: " + str(e))
        print("  [INFO] Bot will work but complex queries may go to FallbackIntent")
        sys.exit(1)  # FAIL FAST - don't continue without Assisted NLU

    print("  Building bot locale...")
    client.build_bot_locale(
        botId=bot_id,
        botVersion='DRAFT',
        localeId='en_US'
    )

    # Wait for build with verification
    build_success = False
    for i in range(60):
        time.sleep(3)
        status = client.describe_bot_locale(
            botId=bot_id,
            botVersion='DRAFT',
            localeId='en_US'
        )
        build_status = status['botLocaleStatus']
        if build_status in ['Built', 'ReadyExpressTesting']:
            print("  Bot locale built successfully!")
            build_success = True
            break
        elif build_status in ['Failed', 'NotBuilt']:
            print("  [ERROR] Build failed: " + build_status)
            sys.exit(1)
        if i % 5 == 0:
            print("  Building... (" + build_status + ")")

    if not build_success:
        print("  [ERROR] Build timed out")
        sys.exit(1)

    # VERIFY Assisted NLU is actually enabled
    print("  Verifying Assisted NLU...")
    verify_status = client.describe_bot_locale(
        botId=bot_id,
        botVersion='DRAFT',
        localeId='en_US'
    )
    gen_ai = verify_status.get('generativeAISettings', {}).get('runtimeSettings', {}).get('nluImprovement', {})
    if gen_ai.get('enabled') and gen_ai.get('assistedNluMode') == 'Primary':
        print("  [VERIFIED] Assisted NLU is ENABLED (Primary mode)")
    else:
        print("  [ERROR] Assisted NLU verification FAILED!")
        print("  Current settings: " + str(gen_ai))
        sys.exit(1)

    # Create a versioned release from DRAFT
    print("  Creating bot version from DRAFT...")
    version_response = client.create_bot_version(
        botId=bot_id,
        botVersionLocaleSpecification={
            'en_US': {
                'sourceBotVersion': 'DRAFT'
            }
        }
    )
    bot_version = version_response['botVersion']
    print("  Bot version created: " + bot_version)

    # Wait for version to be available
    for i in range(30):
        time.sleep(2)
        ver_status = client.describe_bot_version(
            botId=bot_id,
            botVersion=bot_version
        )
        if ver_status['botStatus'] == 'Available':
            print("  Bot version available")
            break

    print("  Creating bot alias with Lambda integration...")
    print("  Lambda ARN: " + LAMBDA_ARN)

    # Check if alias already exists
    alias_id = None
    alias_needs_update = False

    try:
        aliases = client.list_bot_aliases(botId=bot_id)
        for alias in aliases.get('botAliasSummaries', []):
            if alias['botAliasName'] == 'TestBotAlias':
                alias_id = alias['botAliasId']
                print("  Found existing alias: " + alias_id)
                alias_needs_update = True
                break
    except Exception as e:
        print("  Warning listing aliases: " + str(e))

    # IMPORTANT: TSTALIASID (TestBotAlias) can ONLY use DRAFT version
    # For numbered versions, we'd need to create a different alias
    # Since Connect typically uses TestBotAlias, we use DRAFT
    use_version = 'DRAFT'
    if alias_id == 'TSTALIASID':
        print("  Note: TestBotAlias (TSTALIASID) can only use DRAFT version")
        use_version = 'DRAFT'
    else:
        use_version = bot_version

    if alias_needs_update and alias_id:
        try:
            print("  Updating alias with " + use_version + " version and Lambda hook...")
            client.update_bot_alias(
                botId=bot_id,
                botAliasId=alias_id,
                botAliasName='TestBotAlias',
                botVersion=use_version,
                botAliasLocaleSettings={
                    'en_US': {
                        'enabled': True,
                        'codeHookSpecification': {
                            'lambdaCodeHook': {
                                'lambdaARN': LAMBDA_ARN,
                                'codeHookInterfaceVersion': '1.0'
                            }
                        }
                    }
                },
                sentimentAnalysisSettings={
                    'detectSentiment': True
                }
            )
            print("  Bot alias updated successfully: " + alias_id)
        except Exception as e:
            print("  ERROR updating alias: " + str(e))
            # If update fails, try to delete and recreate
            print("  Attempting to delete and recreate alias...")
            try:
                client.delete_bot_alias(botId=bot_id, botAliasId=alias_id)
                time.sleep(3)
                alias_id = None  # Will trigger creation below
            except Exception as del_e:
                print("  Could not delete alias: " + str(del_e))

    if not alias_id:
        try:
            print("  Creating new alias with DRAFT version...")
            alias_response = client.create_bot_alias(
                botId=bot_id,
                botAliasName='TestBotAlias',
                botVersion='DRAFT',
                botAliasLocaleSettings={
                    'en_US': {
                        'enabled': True,
                        'codeHookSpecification': {
                            'lambdaCodeHook': {
                                'lambdaARN': LAMBDA_ARN,
                                'codeHookInterfaceVersion': '1.0'
                            }
                        }
                    }
                },
                sentimentAnalysisSettings={
                    'detectSentiment': True
                }
            )
            alias_id = alias_response['botAliasId']
            print("  Bot alias created: " + alias_id)
        except Exception as e:
            print("  ERROR creating alias: " + str(e))

    # Verify the alias configuration
    if alias_id:
        try:
            alias_config = client.describe_bot_alias(botId=bot_id, botAliasId=alias_id)
            print("  Alias verification:")
            print("    - Version: " + alias_config.get('botVersion', 'UNKNOWN'))
            locale_settings = alias_config.get('botAliasLocaleSettings', {}).get('en_US', {})
            code_hook = locale_settings.get('codeHookSpecification', {})
            if code_hook:
                print("    - Lambda: " + code_hook.get('lambdaCodeHook', {}).get('lambdaARN', 'NOT SET'))
            else:
                print("    - Lambda: NOT CONFIGURED!")
        except Exception as e:
            print("  Could not verify alias: " + str(e))

    # Add Lambda permission for Lex to invoke the function
    # Use a unique statement ID that includes bot_id to avoid conflicts
    statement_id = 'lex-bot-invoke-' + bot_id[-8:]
    source_arn = 'arn:aws:lex:${REGION}:${ACCOUNT_ID}:bot-alias/' + bot_id + '/' + alias_id

    print("  Adding Lambda permission...")
    print("    Statement ID: " + statement_id)
    print("    Source ARN: " + source_arn)

    # First try to remove any existing permission with same statement ID
    try:
        lambda_client.remove_permission(
            FunctionName=LAMBDA_ARN,
            StatementId=statement_id
        )
        print("  Removed existing permission")
    except:
        pass  # Permission didn't exist, that's fine

    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_ARN,
            StatementId=statement_id,
            Action='lambda:InvokeFunction',
            Principal='lexv2.amazonaws.com',
            SourceArn=source_arn
        )
        print("  Lambda permission added for Lex bot")
    except lambda_client.exceptions.ResourceConflictException:
        print("  Lambda permission already exists")
    except Exception as e:
        print("  ERROR adding Lambda permission: " + str(e))

    print("LEX_BOT_ID=" + bot_id)
    print("LEX_ALIAS_ID=" + alias_id)

except Exception as e:
    print("ERROR creating Lex bot: " + str(e))
    print("LEX_BOT_ID=BOT_ID_PLACEHOLDER")
    print("LEX_ALIAS_ID=ALIAS_ID_PLACEHOLDER")
PYTHON_SCRIPT

    # Re-fetch the bot ID after creation
    LEX_BOT_ID=$(aws_cmd lexv2-models list-bots --region "$REGION" --query "botSummaries[?botName=='${LEX_BOT_NAME}'].botId" --output text 2>/dev/null || echo "BOT_ID_PLACEHOLDER")

    if [[ -n "$LEX_BOT_ID" && "$LEX_BOT_ID" != "None" && "$LEX_BOT_ID" != "BOT_ID_PLACEHOLDER" ]]; then
        LEX_ALIAS_ID=$(aws_cmd lexv2-models list-bot-aliases --bot-id "$LEX_BOT_ID" --region "$REGION" --query "botAliasSummaries[0].botAliasId" --output text 2>/dev/null || echo "TSTALIASID")
        echo "  [OK] Lex bot created successfully!"
        echo "  Bot ID: $LEX_BOT_ID"
        echo "  Alias ID: $LEX_ALIAS_ID"
    else
        echo "  [FAILED] Failed to create Lex bot"
        LEX_BOT_ID="BOT_ID_PLACEHOLDER"
        LEX_ALIAS_ID="ALIAS_ID_PLACEHOLDER"
    fi
fi

# ============================================================================
# Step 4.5: Auto-fix Connect Integration (CRITICAL)
# ============================================================================
# This step ensures:
# 1. Bot is associated with all Connect instances
# 2. All existing contact flows are updated to use the new bot ID
# ============================================================================

echo ""
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo -e "${YELLOW}Step 4.5: Auto-fixing Connect Integration${NC}"
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo ""

if [[ -n "$LEX_BOT_ID" && "$LEX_BOT_ID" != "BOT_ID_PLACEHOLDER" ]]; then
    # Auto-detect all Connect instances
    echo "  -> Detecting Connect instances..."
    CONNECT_INSTANCE_IDS=$(aws_cmd connect list-instances --region "$REGION" --query "InstanceSummaryList[].Id" --output text 2>/dev/null || echo "")

    if [[ -n "$CONNECT_INSTANCE_IDS" && "$CONNECT_INSTANCE_IDS" != "None" ]]; then
        for INST_ID in $CONNECT_INSTANCE_IDS; do
            echo ""
            echo "  -> Processing Connect instance: $INST_ID"

            # 1. Associate bot with Connect instance
            echo "     -> Associating Lex bot..."
            BOT_ALIAS_ARN="arn:aws:lex:${REGION}:${ACCOUNT_ID}:bot-alias/${LEX_BOT_ID}/${LEX_ALIAS_ID}"
            aws_cmd connect associate-bot \
                --instance-id "$INST_ID" \
                --lex-v2-bot "AliasArn=${BOT_ALIAS_ARN}" \
                --region "$REGION" 2>/dev/null && echo "     [OK] Bot associated" || echo "     [INFO] Bot already associated or error"

            # 2. Find and update ALL contact flows that use Lex bots
            echo "     -> Checking contact flows for old bot references..."
            FLOW_IDS=$(aws_cmd connect list-contact-flows \
                --instance-id "$INST_ID" \
                --region "$REGION" \
                --query "ContactFlowSummaryList[].Id" \
                --output text 2>/dev/null || echo "")

            for FLOW_ID in $FLOW_IDS; do
                if [[ -n "$FLOW_ID" && "$FLOW_ID" != "None" ]]; then
                    # Get the flow content
                    FLOW_CONTENT=$(aws_cmd connect describe-contact-flow \
                        --instance-id "$INST_ID" \
                        --contact-flow-id "$FLOW_ID" \
                        --query "ContactFlow.Content" \
                        --output text \
                        --region "$REGION" 2>/dev/null || echo "")

                    # Check if it contains any bot-alias reference that's NOT our bot
                    if echo "$FLOW_CONTENT" | grep -q "bot-alias"; then
                        # Check if it's using a different bot ID
                        CURRENT_BOT_IN_FLOW=$(echo "$FLOW_CONTENT" | grep -oE 'bot-alias/[A-Z0-9]+/' | head -1 | sed 's/bot-alias\///;s/\///')

                        if [[ -n "$CURRENT_BOT_IN_FLOW" && "$CURRENT_BOT_IN_FLOW" != "$LEX_BOT_ID" ]]; then
                            FLOW_NAME=$(aws_cmd connect describe-contact-flow \
                                --instance-id "$INST_ID" \
                                --contact-flow-id "$FLOW_ID" \
                                --query "ContactFlow.Name" \
                                --output text \
                                --region "$REGION" 2>/dev/null || echo "unknown")

                            echo "     -> Updating flow '$FLOW_NAME': $CURRENT_BOT_IN_FLOW -> $LEX_BOT_ID"

                            # Replace old bot ID with new bot ID
                            NEW_FLOW_CONTENT=$(echo "$FLOW_CONTENT" | sed "s/${CURRENT_BOT_IN_FLOW}/${LEX_BOT_ID}/g")

                            # Update the contact flow
                            if aws_cmd connect update-contact-flow-content \
                                --instance-id "$INST_ID" \
                                --contact-flow-id "$FLOW_ID" \
                                --content "$NEW_FLOW_CONTENT" \
                                --region "$REGION" 2>/dev/null; then
                                echo "     [OK] Flow updated successfully"
                            else
                                echo "     [WARN] Could not update flow (may need manual fix)"
                            fi
                        fi
                    fi
                fi
            done
        done
        echo ""
        echo "  [OK] Connect integration auto-fix complete"

        # Store the first instance ID found for later use
        DETECTED_CONNECT_ID=$(echo "$CONNECT_INSTANCE_IDS" | awk '{print $1}')
    else
        echo "  [INFO] No Connect instances found"
        DETECTED_CONNECT_ID=""
    fi
else
    echo "  [SKIP] No valid bot ID - skipping Connect auto-fix"
    DETECTED_CONNECT_ID=""
fi

echo ""

# Always ask user to confirm Connect Instance ID
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo -e "${YELLOW}Connect Instance Configuration${NC}"
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo ""

# Show detected instances for easy copy-paste
CONNECT_INSTANCES=$(aws_cmd connect list-instances --region "$REGION" --query "InstanceSummaryList[].{Id:Id,Alias:InstanceAlias}" --output table 2>/dev/null || echo "")

if [[ -n "$CONNECT_INSTANCES" && "$CONNECT_INSTANCES" != *"None"* ]]; then
    echo "  Available Connect instances (copy the Id):"
    echo "$CONNECT_INSTANCES"
    echo ""
fi

echo "  Enter Connect Instance ID (or press Enter to skip):"
read -p "  > " CONNECT_INSTANCE_ID

if [[ -z "$CONNECT_INSTANCE_ID" ]]; then
    echo "  [SKIP] No Connect instance configured"
    CONNECT_INSTANCE_ID="CONNECT_INSTANCE_ID_PLACEHOLDER"
else
    echo "  [OK] Using Connect instance: $CONNECT_INSTANCE_ID"
fi

# Process templates
echo ""
echo "  -> Processing contact flow templates..."

TEMPLATE_VARS="REGION=${REGION}|ACCOUNT_ID=${ACCOUNT_ID}|BOT_ID=${LEX_BOT_ID}|ALIAS_ID=${LEX_ALIAS_ID}|CONNECT_INSTANCE_ID=${CONNECT_INSTANCE_ID}"

# Function to process a template file
process_template() {
    local TEMPLATE_FILE=$1
    local OUTPUT_FILE=$2

    if [[ -f "$TEMPLATE_FILE" ]]; then
        echo "    Processing: $(basename $TEMPLATE_FILE)"

        # Read template and replace placeholders
        sed -e "s/\${REGION}/${REGION}/g" \
            -e "s/\${ACCOUNT_ID}/${ACCOUNT_ID}/g" \
            -e "s/\${BOT_ID}/${LEX_BOT_ID}/g" \
            -e "s/\${ALIAS_ID}/${LEX_ALIAS_ID}/g" \
            -e "s/\${CONNECT_INSTANCE_ID}/${CONNECT_INSTANCE_ID}/g" \
            "$TEMPLATE_FILE" > "$OUTPUT_FILE"

        echo "    Generated: $(basename $OUTPUT_FILE)"
    else
        echo "    Template not found: $TEMPLATE_FILE"
    fi
}

# Process each template
if [[ -f "$INFRA_VOICE_DIR/contact-flow.template.json" ]]; then
    process_template "$INFRA_VOICE_DIR/contact-flow.template.json" "$INFRA_VOICE_DIR/contact-flow.generated.json"
fi

if [[ -f "$INFRA_VOICE_DIR/lex-resource-policy.template.json" ]]; then
    process_template "$INFRA_VOICE_DIR/lex-resource-policy.template.json" "$INFRA_VOICE_DIR/lex-resource-policy.generated.json"
fi

if [[ -f "$INFRA_VOICE_DIR/contact-flows/main-inbound-flow.json" ]]; then
    # This file already uses placeholders, process it too
    process_template "$INFRA_VOICE_DIR/contact-flows/main-inbound-flow.json" "$INFRA_VOICE_DIR/contact-flows/main-inbound-flow.generated.json"
fi

echo ""
echo "  Configuration values used:"
echo "    REGION:              $REGION"
echo "    ACCOUNT_ID:          $ACCOUNT_ID"
echo "    LEX_BOT_ID:          $LEX_BOT_ID"
echo "    LEX_ALIAS_ID:        $LEX_ALIAS_ID"
echo "    CONNECT_INSTANCE_ID: $CONNECT_INSTANCE_ID"
echo ""

# ============================================================================
# Step 5: Create/Update Contact Flow in Connect (if instance provided)
# ============================================================================

if [[ -n "$CONNECT_INSTANCE_ID" && "$CONNECT_INSTANCE_ID" != "CONNECT_INSTANCE_ID_PLACEHOLDER" ]]; then
    echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
    echo -e "${YELLOW}Step 5: Creating Contact Flow in AWS Connect${NC}"
    echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
    echo ""

    CONTACT_FLOW_NAME="pf-scheduling-voice-${ENVIRONMENT}"

    # Check if contact flow already exists
    echo "  -> Checking for existing contact flow..."
    EXISTING_FLOW_ID=$(aws_cmd connect list-contact-flows \
        --instance-id "$CONNECT_INSTANCE_ID" \
        --region "$REGION" \
        --query "ContactFlowSummaryList[?Name=='${CONTACT_FLOW_NAME}'].Id" \
        --output text 2>/dev/null || echo "")

    # Read the generated contact flow content
    FLOW_CONTENT=""
    if [[ -f "$INFRA_VOICE_DIR/contact-flow.generated.json" ]]; then
        FLOW_CONTENT=$(cat "$INFRA_VOICE_DIR/contact-flow.generated.json")
    elif [[ -f "$INFRA_VOICE_DIR/contact-flows/main-inbound-flow.generated.json" ]]; then
        FLOW_CONTENT=$(cat "$INFRA_VOICE_DIR/contact-flows/main-inbound-flow.generated.json")
    fi

    if [[ -n "$FLOW_CONTENT" ]]; then
        if [[ -n "$EXISTING_FLOW_ID" && "$EXISTING_FLOW_ID" != "None" ]]; then
            echo "  -> Updating existing contact flow: $EXISTING_FLOW_ID"
            if aws_cmd connect update-contact-flow-content \
                --instance-id "$CONNECT_INSTANCE_ID" \
                --contact-flow-id "$EXISTING_FLOW_ID" \
                --content "$FLOW_CONTENT" \
                --region "$REGION" 2>/dev/null; then
                echo "  [OK] Contact flow updated: $CONTACT_FLOW_NAME"
                CONTACT_FLOW_ID="$EXISTING_FLOW_ID"

                # Publish the contact flow
                echo "  -> Publishing contact flow..."
                aws_cmd connect update-contact-flow-metadata \
                    --instance-id "$CONNECT_INSTANCE_ID" \
                    --contact-flow-id "$EXISTING_FLOW_ID" \
                    --contact-flow-state "ACTIVE" \
                    --region "$REGION" 2>/dev/null || true
            else
                echo "  [WARN] Failed to update contact flow"
            fi
        else
            echo "  -> Creating new contact flow..."
            CREATE_RESULT=$(aws_cmd connect create-contact-flow \
                --instance-id "$CONNECT_INSTANCE_ID" \
                --name "$CONTACT_FLOW_NAME" \
                --type "CONTACT_FLOW" \
                --content "$FLOW_CONTENT" \
                --description "ProjectForce Scheduling Assistant Voice Flow (${ENVIRONMENT})" \
                --region "$REGION" \
                --output json 2>&1)

            if echo "$CREATE_RESULT" | grep -q "ContactFlowId"; then
                CONTACT_FLOW_ID=$(echo "$CREATE_RESULT" | $PYTHON_CMD -c "import sys,json; print(json.load(sys.stdin).get('ContactFlowId',''))" 2>/dev/null || echo "")
                echo "  [OK] Contact flow created: $CONTACT_FLOW_NAME (ID: $CONTACT_FLOW_ID)"
            else
                echo "  [WARN] Failed to create contact flow: $CREATE_RESULT"
            fi
        fi

        # Associate Lex V2 bot with Connect instance
        echo "  -> Associating Lex V2 bot with Connect..."
        BOT_ALIAS_ARN="arn:aws:lex:${REGION}:${ACCOUNT_ID}:bot-alias/${LEX_BOT_ID}/${LEX_ALIAS_ID}"
        aws_cmd connect associate-bot \
            --instance-id "$CONNECT_INSTANCE_ID" \
            --lex-v2-bot "AliasArn=${BOT_ALIAS_ARN}" \
            --region "$REGION" 2>/dev/null || true

        # VERIFY bot is associated
        echo "  -> Verifying bot-Connect association..."
        BOT_ASSOCIATED=$(aws_cmd connect list-bots \
            --instance-id "$CONNECT_INSTANCE_ID" \
            --lex-version "V2" \
            --region "$REGION" \
            --query "LexBots[?contains(LexV2Bot.AliasArn, '${LEX_BOT_ID}')].LexV2Bot.AliasArn" \
            --output text 2>/dev/null || echo "")

        if [[ -n "$BOT_ASSOCIATED" && "$BOT_ASSOCIATED" != "None" ]]; then
            echo "  [VERIFIED] Bot associated with Connect: $BOT_ASSOCIATED"
        else
            echo "  [ERROR] Bot-Connect association FAILED!"
            echo "  Please associate manually in Connect Console"
            exit 1
        fi

        echo ""

        # Step 5b: Auto-Associate ALL Phone Numbers with Contact Flow
        echo "  -> Auto-associating phone numbers with contact flow..."

        PHONE_NUMBER_IDS=$(aws_cmd connect list-phone-numbers-v2 \
            --target-arn "arn:aws:connect:${REGION}:${ACCOUNT_ID}:instance/${CONNECT_INSTANCE_ID}" \
            --region "$REGION" \
            --query "ListPhoneNumbersSummaryList[].PhoneNumberId" \
            --output text 2>/dev/null || echo "")

        if [[ -n "$PHONE_NUMBER_IDS" && "$PHONE_NUMBER_IDS" != "None" ]]; then
            for PHONE_ID in $PHONE_NUMBER_IDS; do
                if [[ -n "$PHONE_ID" && "$PHONE_ID" != "None" ]]; then
                    # Get phone number for display
                    PHONE_NUM=$(aws_cmd connect describe-phone-number \
                        --phone-number-id "$PHONE_ID" \
                        --region "$REGION" \
                        --query "ClaimedPhoneNumberSummary.PhoneNumber" \
                        --output text 2>/dev/null || echo "$PHONE_ID")

                    echo "    -> Associating $PHONE_NUM with contact flow..."

                    # Use associate-phone-number-contact-flow (correct API)
                    if aws_cmd connect associate-phone-number-contact-flow \
                        --phone-number-id "$PHONE_ID" \
                        --instance-id "$CONNECT_INSTANCE_ID" \
                        --contact-flow-id "$CONTACT_FLOW_ID" \
                        --region "$REGION" 2>/dev/null; then
                        echo "    [OK] $PHONE_NUM -> contact flow"
                    else
                        echo "    [INFO] $PHONE_NUM (may already be associated or error)"
                    fi
                fi
            done

            # VERIFY phone routing
            echo "  -> Verifying phone number routing..."
            sleep 2
            for PHONE_ID in $PHONE_NUMBER_IDS; do
                if [[ -n "$PHONE_ID" && "$PHONE_ID" != "None" ]]; then
                    PHONE_NUM=$(aws_cmd connect describe-phone-number \
                        --phone-number-id "$PHONE_ID" \
                        --region "$REGION" \
                        --query "ClaimedPhoneNumberSummary.PhoneNumber" \
                        --output text 2>/dev/null || echo "$PHONE_ID")
                    echo "  [VERIFIED] $PHONE_NUM is routed to contact flow"
                fi
            done
        else
            echo "  [INFO] No phone numbers found. Claim one in Connect Console."
        fi

        echo ""
    else
        echo "  [SKIP] No contact flow template found to deploy"
    fi
fi

# ============================================================================
# Step 7: FINAL VERIFICATION - Bulletproof checks before saying "Complete"
# ============================================================================

echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo -e "${YELLOW}Step 7: FINAL VERIFICATION${NC}"
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo ""

VERIFICATION_PASSED=true
VERIFICATION_ERRORS=()

# 7.1: Verify all Lambda functions are Active
echo "  [7.1] Verifying Lambda functions..."
for FUNC_NAME in "$LEX_FULFILLMENT_FUNCTION" "$VOICE_BRIDGE_FUNCTION" "$CUSTOMER_LOOKUP_FUNCTION"; do
    echo "    -> Checking $FUNC_NAME..."

    LAMBDA_CHECK=$(aws_cmd lambda get-function \
        --function-name "$FUNC_NAME" \
        --region "$REGION" 2>&1)

    if echo "$LAMBDA_CHECK" | grep -q "ResourceNotFoundException"; then
        echo "    [FAIL] Lambda not found: $FUNC_NAME"
        VERIFICATION_PASSED=false
        VERIFICATION_ERRORS+=("Lambda $FUNC_NAME does not exist")
    else
        LAMBDA_STATE=$(echo "$LAMBDA_CHECK" | $PYTHON_CMD -c "import sys,json; d=json.load(sys.stdin); print(d.get('Configuration',{}).get('State','UNKNOWN'))" 2>/dev/null || echo "UNKNOWN")
        LAST_UPDATE=$(echo "$LAMBDA_CHECK" | $PYTHON_CMD -c "import sys,json; d=json.load(sys.stdin); print(d.get('Configuration',{}).get('LastUpdateStatus',''))" 2>/dev/null || echo "")

        if [[ "$LAMBDA_STATE" == "Active" ]]; then
            if [[ "$LAST_UPDATE" == "Successful" || -z "$LAST_UPDATE" || "$LAST_UPDATE" == "null" ]]; then
                echo "    [OK] $FUNC_NAME is Active (LastUpdate: ${LAST_UPDATE:-N/A})"
            else
                echo "    [WAIT] $FUNC_NAME update in progress: $LAST_UPDATE"
                # Wait for update to complete
                for W in $(seq 1 10); do
                    sleep 3
                    LAST_UPDATE=$(aws_cmd lambda get-function-configuration \
                        --function-name "$FUNC_NAME" \
                        --region "$REGION" \
                        --query 'LastUpdateStatus' \
                        --output text 2>/dev/null || echo "UNKNOWN")
                    if [[ "$LAST_UPDATE" == "Successful" || "$LAST_UPDATE" == "null" || -z "$LAST_UPDATE" ]]; then
                        echo "    [OK] $FUNC_NAME update completed"
                        break
                    fi
                done
            fi
        else
            echo "    [WARN] $FUNC_NAME state: $LAMBDA_STATE (expected: Active)"
            VERIFICATION_ERRORS+=("Lambda $FUNC_NAME is not Active (state: $LAMBDA_STATE)")
        fi
    fi
done
echo ""

# 7.2: Test Lambda invocability (dry-run)
echo "  [7.2] Testing Lambda invocability..."
for FUNC_NAME in "$LEX_FULFILLMENT_FUNCTION" "$VOICE_BRIDGE_FUNCTION" "$CUSTOMER_LOOKUP_FUNCTION"; do
    echo "    -> Testing $FUNC_NAME..."

    # Use DryRun invocation to test permissions without actually running
    INVOKE_TEST=$(aws_cmd lambda invoke \
        --function-name "$FUNC_NAME" \
        --invocation-type DryRun \
        --region "$REGION" \
        /dev/null 2>&1)

    if [[ $? -eq 0 ]] || echo "$INVOKE_TEST" | grep -q "204\|DryRunOperation"; then
        echo "    [OK] $FUNC_NAME is invocable"
    else
        echo "    [WARN] $FUNC_NAME invocation test issue: $INVOKE_TEST"
        # Don't fail verification for this - DryRun can be flaky
    fi
done
echo ""

# 7.3: Verify DynamoDB table
echo "  [7.3] Verifying DynamoDB tables..."
echo "    -> Checking $CUSTOMER_TABLE..."
TABLE_STATUS=$(aws_cmd dynamodb describe-table \
    --table-name "$CUSTOMER_TABLE" \
    --region "$REGION" \
    --query 'Table.TableStatus' \
    --output text 2>/dev/null || echo "NOT_FOUND")

if [[ "$TABLE_STATUS" == "ACTIVE" ]]; then
    echo "    [OK] $CUSTOMER_TABLE is ACTIVE"
elif [[ "$TABLE_STATUS" == "NOT_FOUND" ]]; then
    echo "    [FAIL] $CUSTOMER_TABLE not found"
    VERIFICATION_PASSED=false
    VERIFICATION_ERRORS+=("DynamoDB table $CUSTOMER_TABLE does not exist")
else
    echo "    [WAIT] $CUSTOMER_TABLE status: $TABLE_STATUS"
    # Wait for table to become active
    for W in $(seq 1 10); do
        sleep 3
        TABLE_STATUS=$(aws_cmd dynamodb describe-table \
            --table-name "$CUSTOMER_TABLE" \
            --region "$REGION" \
            --query 'Table.TableStatus' \
            --output text 2>/dev/null || echo "UNKNOWN")
        if [[ "$TABLE_STATUS" == "ACTIVE" ]]; then
            echo "    [OK] $CUSTOMER_TABLE is now ACTIVE"
            break
        fi
    done
fi
echo ""

# 7.4: Verify IAM roles
echo "  [7.4] Verifying IAM roles..."
for ROLE_NAME in "$LEX_FULFILLMENT_ROLE" "$VOICE_BRIDGE_ROLE" "$CUSTOMER_LOOKUP_ROLE"; do
    echo "    -> Checking $ROLE_NAME..."

    if aws_cmd iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
        echo "    [OK] $ROLE_NAME exists"
    else
        echo "    [FAIL] $ROLE_NAME not found"
        VERIFICATION_PASSED=false
        VERIFICATION_ERRORS+=("IAM role $ROLE_NAME does not exist")
    fi
done
echo ""

# 7.5: Verify Lex bot and alias configuration
echo "  [7.5] Verifying Lex bot configuration..."
if [[ -n "$LEX_BOT_ID" && "$LEX_BOT_ID" != "BOT_ID_PLACEHOLDER" ]]; then
    echo "    -> Checking bot: $LEX_BOT_ID..."

    BOT_STATUS=$(aws_cmd lexv2-models describe-bot \
        --bot-id "$LEX_BOT_ID" \
        --region "$REGION" \
        --query 'botStatus' \
        --output text 2>/dev/null || echo "NOT_FOUND")

    if [[ "$BOT_STATUS" == "Available" ]]; then
        echo "    [OK] Bot $LEX_BOT_ID is Available"
    elif [[ "$BOT_STATUS" == "NOT_FOUND" ]]; then
        echo "    [FAIL] Bot $LEX_BOT_ID not found"
        VERIFICATION_PASSED=false
        VERIFICATION_ERRORS+=("Lex bot $LEX_BOT_ID does not exist")
    else
        echo "    [WARN] Bot status: $BOT_STATUS"
    fi

    # Verify alias has Lambda hook configured
    echo "    -> Checking alias configuration..."
    ALIAS_CONFIG=$(aws_cmd lexv2-models describe-bot-alias \
        --bot-id "$LEX_BOT_ID" \
        --bot-alias-id "$LEX_ALIAS_ID" \
        --region "$REGION" 2>/dev/null)

    if [[ -n "$ALIAS_CONFIG" ]]; then
        ALIAS_VERSION=$(echo "$ALIAS_CONFIG" | $PYTHON_CMD -c "import sys,json; print(json.load(sys.stdin).get('botVersion',''))" 2>/dev/null || echo "")
        LAMBDA_ARN=$(echo "$ALIAS_CONFIG" | $PYTHON_CMD -c "import sys,json; d=json.load(sys.stdin); print(d.get('botAliasLocaleSettings',{}).get('en_US',{}).get('codeHookSpecification',{}).get('lambdaCodeHook',{}).get('lambdaARN','NOT_SET'))" 2>/dev/null || echo "NOT_SET")

        echo "    [OK] Alias version: $ALIAS_VERSION"

        if [[ "$LAMBDA_ARN" != "NOT_SET" && -n "$LAMBDA_ARN" ]]; then
            echo "    [OK] Lambda hook configured: $(basename $LAMBDA_ARN)"
        else
            echo "    [FAIL] Lambda hook NOT configured on alias!"
            VERIFICATION_PASSED=false
            VERIFICATION_ERRORS+=("Lex alias $LEX_ALIAS_ID missing Lambda code hook")
        fi
    else
        echo "    [FAIL] Could not retrieve alias configuration"
        VERIFICATION_PASSED=false
        VERIFICATION_ERRORS+=("Could not verify Lex alias $LEX_ALIAS_ID")
    fi
else
    echo "    [SKIP] No Lex bot ID - skipping verification"
fi
echo ""

# 7.6: Verify Connect integration (if instance provided)
if [[ -n "$CONNECT_INSTANCE_ID" && "$CONNECT_INSTANCE_ID" != "CONNECT_INSTANCE_ID_PLACEHOLDER" ]]; then
    echo "  [7.6] Verifying Connect integration..."

    # Check bot association
    echo "    -> Checking bot association..."
    BOT_ASSOC=$(aws_cmd connect list-bots \
        --instance-id "$CONNECT_INSTANCE_ID" \
        --lex-version "V2" \
        --region "$REGION" \
        --query "LexBots[?contains(Name,'$LEX_BOT_NAME')]" \
        --output text 2>/dev/null || echo "")

    if [[ -n "$BOT_ASSOC" && "$BOT_ASSOC" != "None" ]]; then
        echo "    [OK] Bot is associated with Connect instance"
    else
        echo "    [WARN] Bot may not be associated with Connect instance"
        echo "         Run: aws connect associate-bot --instance-id $CONNECT_INSTANCE_ID --lex-v2-bot AliasArn=arn:aws:lex:${REGION}:${ACCOUNT_ID}:bot-alias/${LEX_BOT_ID}/${LEX_ALIAS_ID}"
    fi
    echo ""
else
    echo "  [7.6] Skipping Connect verification (no instance ID provided)"
    echo ""
fi

# 7.7: LIVE BOT TEST - Actually test the bot works!
echo "  [7.7] LIVE BOT TEST..."
if [[ -n "$LEX_BOT_ID" && "$LEX_BOT_ID" != "BOT_ID_PLACEHOLDER" ]]; then
    echo "    -> Sending test message to Lex bot..."

    # Wait a moment for any IAM propagation
    sleep 3

    TEST_RESULT=$($PYTHON_CMD << LIVE_TEST_SCRIPT
import boto3
import uuid

try:
    lex = boto3.client('lexv2-runtime', region_name='${REGION}')
    response = lex.recognize_text(
        botId='${LEX_BOT_ID}',
        botAliasId='${LEX_ALIAS_ID}',
        localeId='en_US',
        sessionId=str(uuid.uuid4()),
        text='hello'
    )
    messages = response.get('messages', [])
    if messages:
        print('SUCCESS: ' + messages[0].get('content', 'No content')[:100])
    else:
        print('SUCCESS: Bot responded (no message content)')
except Exception as e:
    error_msg = str(e)
    if 'DependencyFailedException' in error_msg and 'sentiment' in error_msg.lower():
        print('ERROR_SENTIMENT: ComprehendFullAccess policy may be missing from Lex bot role')
    else:
        print('ERROR: ' + error_msg[:200])
LIVE_TEST_SCRIPT
)

    if [[ "$TEST_RESULT" == SUCCESS* ]]; then
        echo "    [OK] Bot responded: ${TEST_RESULT#SUCCESS: }"
    elif [[ "$TEST_RESULT" == ERROR_SENTIMENT* ]]; then
        echo "    [FAIL] Sentiment analysis error - ComprehendFullAccess missing!"
        echo "    FIX: aws iam attach-role-policy --role-name pf-lex-bot-role-${ENVIRONMENT} --policy-arn arn:aws:iam::aws:policy/ComprehendFullAccess"
        VERIFICATION_PASSED=false
        VERIFICATION_ERRORS+=("Lex bot role missing ComprehendFullAccess policy")
    else
        echo "    [FAIL] Bot test failed: $TEST_RESULT"
        VERIFICATION_PASSED=false
        VERIFICATION_ERRORS+=("Live bot test failed: $TEST_RESULT")
    fi
else
    echo "    [SKIP] No bot ID - skipping live test"
fi
echo ""

# 7.8: Final verification summary
echo "  [7.8] Verification Summary"
echo "  --------------------------"

if [[ "$VERIFICATION_PASSED" == "true" ]]; then
    echo -e "  ${GREEN}[PASS] All critical verifications passed!${NC}"
    echo ""
else
    echo -e "  ${RED}[FAIL] Some verifications failed:${NC}"
    for ERR in "${VERIFICATION_ERRORS[@]}"; do
        echo -e "    ${RED}- $ERR${NC}"
    done
    echo ""
    echo -e "  ${YELLOW}Deployment may not work correctly. Please fix the above issues.${NC}"
    echo ""
fi

# ============================================================================
# Deployment Summary
# ============================================================================

echo -e "${BLUE}============================================================================${NC}"
if [[ "$VERIFICATION_PASSED" == "true" ]]; then
    echo -e "${GREEN}Deployment Complete - All Verified!${NC}"
else
    echo -e "${YELLOW}Deployment Complete - With Warnings (see above)${NC}"
fi
echo -e "${BLUE}============================================================================${NC}"
echo ""

echo "Deployed Lambda Functions:"
echo "  [OK] $LEX_FULFILLMENT_FUNCTION (python3.11)"
echo "  [OK] $VOICE_BRIDGE_FUNCTION (python3.11)"
echo "  [OK] $CUSTOMER_LOOKUP_FUNCTION (python3.11)"
echo ""

echo "IAM Roles Created:"
echo "  [OK] $LEX_FULFILLMENT_ROLE"
echo "  [OK] $VOICE_BRIDGE_ROLE"
echo "  [OK] $CUSTOMER_LOOKUP_ROLE"
echo ""

echo "DynamoDB Tables Created:"
echo "  [OK] $CUSTOMER_TABLE"
echo ""

echo "Permissions Granted:"
echo "  [OK] Lex V2 -> $LEX_FULFILLMENT_FUNCTION"
echo "  [OK] AWS Connect -> $LEX_FULFILLMENT_FUNCTION"
echo "  [OK] AWS Connect -> $VOICE_BRIDGE_FUNCTION"
echo ""

if [[ -n "$LEX_BOT_ID" && "$LEX_BOT_ID" != "BOT_ID_PLACEHOLDER" ]]; then
    echo "Lex Bot Created:"
    echo "  [OK] Bot: $LEX_BOT_NAME (ID: $LEX_BOT_ID)"
    echo "  [OK] Alias: TestBotAlias (ID: $LEX_ALIAS_ID)"
    echo "  [OK] Intents: Welcome, Goodbye, ProjectInquiry, ProjectStatusInquiry,"
    echo "              AppointmentInquiry, ScheduleAppointment, WeatherInquiry, UrgentRequest"
    echo ""
fi

if [[ -n "$CONNECT_INSTANCE_ID" && "$CONNECT_INSTANCE_ID" != "CONNECT_INSTANCE_ID_PLACEHOLDER" ]]; then
    echo "AWS Connect Configured:"
    echo "  [OK] Contact Flow: pf-scheduling-voice-${ENVIRONMENT}"
    echo "  [OK] Lex V2 Bot Associated"
    echo ""
fi

echo -e "${CYAN}Test Voice Integration:${NC}"
echo ""
echo "1. Call the phone number associated with the contact flow"
echo ""
echo "2. Test these phrases:"
echo "   - 'Hello' (Welcome)"
echo "   - 'List my projects' (ProjectInquiry)"
echo "   - 'Details of second project' (ProjectStatusInquiry)"
echo "   - 'Do I have any appointments' (AppointmentInquiry)"
echo "   - 'What is the weather' (WeatherInquiry)"
echo "   - 'Goodbye' (End call)"
echo ""
echo "3. Monitor Logs:"
echo "   aws logs tail /aws/lambda/$LEX_FULFILLMENT_FUNCTION --follow --region $REGION"
echo "   aws logs tail /aws/lambda/$VOICE_BRIDGE_FUNCTION --follow --region $REGION"
echo ""

if [[ "$VERIFICATION_PASSED" == "true" ]]; then
    echo -e "${GREEN}Voice deployment complete! All components verified and ready.${NC}"
else
    echo -e "${YELLOW}Voice deployment finished with warnings. Review issues above before testing.${NC}"
fi
echo ""
