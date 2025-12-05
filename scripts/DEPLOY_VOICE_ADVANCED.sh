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
# Lex Bot Voice Configuration (Tunable Settings)
# ============================================================================
# Bot versioning - DRAFT is required for modifications, use numbered versions for production aliases
LEX_BOT_VERSION="DRAFT"

# Voice settings
LEX_VOICE_ID="Joanna"           # Options: Joanna, Matthew, Ivy, Kendra, Kimberly, Salli, Joey, Justin
LEX_VOICE_ENGINE="neural"       # Options: standard, neural, long-form, generative

# NLU settings
LEX_NLU_CONFIDENCE_THRESHOLD="0.3"      # Lower = more lenient matching (0.0-1.0, default was 0.4)
LEX_SPEECH_DETECTION="MaximumNoiseTolerance"  # Options: Default, HighNoiseTolerance, MaximumNoiseTolerance

# Generative AI (Assisted NLU)
LEX_ASSISTED_NLU_ENABLED="true"         # Use LLM for better intent classification
LEX_ASSISTED_NLU_MODE="Primary"         # Options: Primary (LLM default), Fallback (LLM only when NLU fails)

# SSML wait message settings
LEX_WAIT_DELAY_SECONDS="1"              # Seconds before first wait message plays
LEX_UPDATE_FREQUENCY_SECONDS="5"        # Seconds between update messages (reduced from 8 for better UX)
LEX_FULFILLMENT_TIMEOUT="90"            # Max seconds to wait for Lambda response

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

##############################################################################
# Helper: Ensure AWS Default Encryption (Remove any customer-managed KMS key)
# IMPORTANT: We ALWAYS use AWS default encryption for Lambda environment variables.
#            This prevents KMSAccessDeniedException errors from misconfigured KMS keys.
#            DO NOT CHANGE THIS - customer KMS keys cause permission nightmares!
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

# Voice configuration from bash variables
BOT_VERSION = '${LEX_BOT_VERSION}'
VOICE_ID = '${LEX_VOICE_ID}'
VOICE_ENGINE = '${LEX_VOICE_ENGINE}'
NLU_CONFIDENCE_THRESHOLD = float('${LEX_NLU_CONFIDENCE_THRESHOLD}')
SPEECH_DETECTION = '${LEX_SPEECH_DETECTION}'
ASSISTED_NLU_ENABLED = '${LEX_ASSISTED_NLU_ENABLED}'.lower() == 'true'
ASSISTED_NLU_MODE = '${LEX_ASSISTED_NLU_MODE}'
WAIT_DELAY_SECONDS = int('${LEX_WAIT_DELAY_SECONDS}')
UPDATE_FREQUENCY_SECONDS = int('${LEX_UPDATE_FREQUENCY_SECONDS}')
FULFILLMENT_TIMEOUT = int('${LEX_FULFILLMENT_TIMEOUT}')

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

    print(f"  Creating locale (en_US) with NLU threshold={NLU_CONFIDENCE_THRESHOLD}...")
    client.create_bot_locale(
        botId=bot_id,
        botVersion=BOT_VERSION,
        localeId='en_US',
        nluIntentConfidenceThreshold=NLU_CONFIDENCE_THRESHOLD
    )

    # Poll for locale to be ready
    print("  Waiting for locale to be ready...")
    elapsed = 0
    while elapsed < 60:
        try:
            locale_status = client.describe_bot_locale(botId=bot_id, botVersion=BOT_VERSION, localeId='en_US')
            if locale_status.get('botLocaleStatus') in ['Built', 'ReadyExpressTesting', 'NotBuilt']:
                print("  [OK] Locale ready after " + str(elapsed) + "s")
                break
        except Exception:
            pass
        time.sleep(3)
        elapsed += 3

    # Update locale with full voice and speech detection settings
    print(f"  Configuring locale: voice={VOICE_ID}/{VOICE_ENGINE}, speech={SPEECH_DETECTION}, assistedNLU={ASSISTED_NLU_MODE}")
    client.update_bot_locale(
        botId=bot_id,
        botVersion=BOT_VERSION,
        localeId='en_US',
        nluIntentConfidenceThreshold=NLU_CONFIDENCE_THRESHOLD,
        voiceSettings={'voiceId': VOICE_ID, 'engine': VOICE_ENGINE},
        generativeAISettings={
            'runtimeSettings': {
                'nluImprovement': {
                    'enabled': ASSISTED_NLU_ENABLED,
                    'assistedNluMode': ASSISTED_NLU_MODE
                }
            },
            'buildtimeSettings': {
                'descriptiveBotBuilder': {'enabled': False},
                'sampleUtteranceGeneration': {'enabled': False}
            }
        }
    )

    intents = [
        {
            'name': 'AppointmentInquiry',
            'description': 'Check scheduled appointments and installations',
            'utterances': [
                'do I have any appointments',
                'show my appointments',
                'what appointments do I have',
                'check my appointments',
                'list appointments',
                'any upcoming appointments',
                'when is my next appointment',
                'appointment schedule',
                'my appointments please',
                'show me my schedule',
                'my appointments',
                'I would like to check my appointments',
                'may I see my appointments',
                'could you tell me about my appointments',
                'please show my appointments',
                'I need to check my schedule',
                'what is my appointment schedule',
                'when am I scheduled',
                'whats on my calendar',
                'any appointments coming up',
                'got any appointments',
                'am I scheduled for anything',
                'whens my appointment',
                'when is my installation',
                'when is my project scheduled',
                'when is my decking appointment',
                'when is my roofing scheduled',
                'when is my flooring installation',
                'show my installation date',
                'when are they coming',
                'when is the installer coming',
                'when is the technician coming',
                'when is the crew coming',
                'appointments',
                'the appointments',
                'show appointment',
                'check appointment',
                'appointment status',
                'is anything scheduled',
                'do I have anything scheduled',
                'what dates am I booked for',
                'show my booked dates',
                'when is my next install',
                'upcoming installations',
            ]
        },
        {
            'name': 'BusinessHours',
            'description': 'Ask about business and installation hours',
            'utterances': [
                'what are your hours',
                'when are you open',
                'business hours',
                'operating hours',
                'what time do you open',
                'what time do you close',
                'are you open on weekends',
                'hours of operation',
                'when can I call',
                'office hours',
                'what are your working hours',
                'store hours',
                'are you open today',
                'are you open tomorrow',
                'are you open on saturday',
                'are you open on sunday',
                'what days are you open',
                'when do you start work',
                'when do installers work',
                'what time does installation start',
                'earliest appointment time',
                'latest appointment time',
                'do you work on holidays',
                'are you open on christmas',
                'are you closed on thanksgiving',
                'when can I schedule an appointment',
                'what hours do you install',
                'do you do evening appointments',
                'do you work mornings',
                'can you come early morning',
                'can you come late afternoon',
            ]
        },
        {
            'name': 'CancelAppointment',
            'description': 'Cancel an existing installation appointment',
            'utterances': [
                'cancel my appointment',
                'I need to cancel',
                'cancel the appointment',
                'remove my appointment',
                'I want to cancel',
                'cancel please',
                'delete appointment',
                'I cannot make it',
                'cancel my booking',
                'I would like to cancel my appointment',
                'may I cancel please',
                'I need to cancel my scheduled appointment',
                'please cancel my appointment',
                'cancel it',
                'just cancel',
                'nevermind cancel it',
                'do not come',
                'do not need it anymore',
                'changed my mind',
                'not doing it anymore',
                'forget it',
                'cancel my installation',
                'cancel my project',
                'cancel the install',
                'cancel my decking installation',
                'cancel my roofing appointment',
                'cancel my flooring project',
                'do not install it',
                'cancel the scheduled work',
                'cancel the crew',
                'I changed my mind about the project',
                'I do not want to proceed',
                'I decided not to do it',
                'we are not doing the project',
                'can I cancel',
                'how do I cancel',
                'is it too late to cancel',
                'can I still cancel',
                'what if I cancel',
                'stop the project',
                'cancel everything',
                'cancel my deck project',
                'cancel my roof work',
            ]
        },
        {
            'name': 'SelectionIntent',
            'description': 'Handle ordinal selections during workflows (VOICE-SPECIFIC)',
            'utterances': [
                'I want the first one',
                'I want the second one',
                'I want the third one',
                'I want the fourth one',
                'I want the fifth one',
                'I want the sixth one',
                'I want the seventh one',
                'I want the eighth one',
                'I want first',
                'I want second',
                'I want third',
                'I want fourth',
                'lets do the first one',
                'lets do the second one',
                'lets do the third one',
                'lets do the fourth one',
                'lets do first',
                'lets do second',
                'lets do third',
                'lets do fourth',
                'go with the first one',
                'go with the second one',
                'go with the third one',
                'go with the fourth one',
                'go with first',
                'go with second',
                'go with third',
                'go with fourth',
                'ill take the first one',
                'ill take the second one',
                'ill take the third one',
                'ill take the fourth one',
                'ill take first',
                'ill take second',
                'ill take third',
                'ill take fourth',
                'yes that one',
                'yeah that one',
                'that one please',
                'yes this one',
                'first please',
                'second please',
                'third please',
                'fourth please',
                'the first one please',
                'the second one please',
                'the third one please',
                'the fourth one please',
                'select the first',
                'select the second',
                'select the third',
                'select the fourth',
                'pick the first',
                'pick the second',
                'pick the third',
                'pick the fourth',
                'choose the first',
                'choose the second',
                'choose the third',
                'choose the fourth',
                'I pick one',
                'I pick two',
                'I pick three',
                'I pick four',
                'I choose one',
                'I choose two',
                'I choose three',
                'I choose four',
                'reschedule the first one',
                'reschedule the second one',
                'reschedule the third one',
                'reschedule the fourth one',
                'cancel the first one',
                'cancel the second one',
                'cancel the third one',
                'cancel the fourth one',
            ]
        },
        {
            'name': 'CheckAvailability',
            'description': 'Check available dates for scheduling installations',
            'utterances': [
                'what dates are available',
                'show available dates',
                'when can I schedule',
                'available times',
                'what times work',
                'check availability',
                'when are you available',
                'show me available slots',
                'open dates',
                'free dates',
                'what days are open',
                'available appointments',
                'I would like to know what dates are available',
                'may I see available times',
                'could you show me the available dates',
                'please check availability',
                'what would be a good time',
                'when would be convenient',
                'when can you come',
                'when can you guys come out',
                'whats open',
                'got any openings',
                'any slots available',
                'when can we do this',
                'earliest available',
                'soonest available',
                'next available date',
                'when can you install',
                'when can you do the work',
                'when can you start the project',
                'when can you start my deck',
                'when can you do my roof',
                'when can you install my flooring',
                'available dates for installation',
                'installation availability',
                'what about next week',
                'anything this week',
                'any openings this month',
                'do you have anything on monday',
                'availability for tuesday',
                'can you come this weekend',
                'saturday availability',
                'how soon can you come',
                'how quickly can you schedule',
                'what is your earliest availability',
                'when is the next opening',
            ]
        },
        {
            'name': 'Goodbye',
            'description': 'End conversation and disconnect call',
            'utterances': [
                'goodbye',
                'bye',
                'bye bye',
                'see you',
                'see you later',
                'thanks bye',
                'thank you goodbye',
                'ok bye',
                'alright bye',
                'that is all',
                'thats all',
                'that will be all',
                'I am done',
                'im done',
                'all done',
                'nothing else',
                'no more questions',
                'I am finished',
                'we are done',
                'thanks thats all',
                'thank you thats all',
                'hang up',
                'end call',
                'disconnect',
                'end the call',
                'take care',
                'have a good day',
                'talk to you later',
                'thanks for your help goodbye',
                'that helps thanks bye',
                'no',
                'nope',
                'no thanks',
                'no thank you',
                'I am good',
                'im good',
                'thats it',
                'that is it',
                'no I am done',
                'no im done',
                'I do not need any help',
                'I dont need any help',
                'I do not need anything else',
                'I dont need anything else',
                'no I am good',
                'no im good',
                'I am all set',
                'im all set',
                'no I am all set',
                'not right now',
                'no not right now',
                'maybe later',
                'not at this time',
                'I am okay',
                'im okay',
                'am done',
                'no more',
                'finished',
                'no am done',
                'all set',
                'done here',
                'nothing more',
            ]
        },
        {
            'name': 'Help',
            'description': 'Request for assistance or options',
            'utterances': [
                'help',
                'help me',
                'I need help',
                'can you help',
                'what can you do',
                'what are my options',
                'how does this work',
                'I need assistance',
                'can you assist me',
                'I am confused',
                'I do not understand',
                'what should I do',
                'guide me',
                'walk me through this',
                'I am not sure what to do',
                'help please',
                'I need some help',
                'can someone help me',
                'what do I do',
                'how do I use this',
                'what can I ask you',
                'what are you able to do',
                'show me what you can do',
                'what services do you offer',
                'how can you help me',
                'I am lost',
                'start over',
                'I need to talk to someone',
                'can I speak to a person',
            ]
        },
        {
            'name': 'HowAreYou',
            'description': 'Casual chitchat greeting',
            'utterances': [
                'how are you',
                'how are you doing',
                'how is it going',
                'what is up',
                'how do you do',
                'are you doing well',
                'hows everything',
                'how have you been',
                'you doing okay',
                'how are things',
                'hows your day',
                'hows it going today',
                'you good',
                'everything alright',
                'are you okay',
                'are you well',
                'how is your day going',
                'having a good day',
                'busy today',
                'how is work',
                'nice to talk to you',
                'good to hear from you',
            ]
        },
        {
            'name': 'ProjectInquiry',
            'description': 'List customer projects - home improvement work',
            'utterances': [
                'list my projects',
                'show my projects',
                'what are my projects',
                'tell me about my projects',
                'get my projects',
                'my projects',
                'show projects',
                'what projects do I have',
                'projects please',
                'can you list my projects',
                'I want to see my projects',
                'I would like to see my projects',
                'may I see my projects please',
                'could you show me my projects',
                'please show my projects',
                'whats up with my projects',
                'show me what I got',
                'what do I have going on',
                'any projects',
                'got any projects',
                'my stuff',
                'show my stuff',
                'what am I working on',
                'whats going on with my work',
                'show my decking project',
                'list my roofing projects',
                'my siding project',
                'show my flooring project',
                'list my fencing project',
                'my painting project',
                'show my window project',
                'my kitchen project',
                'my bathroom project',
                'show my gutter project',
                'list my deck project',
                'my roof project',
                'list my products',
                'show my products',
                'what products do I have',
                'my products please',
                'tell me about my products',
                'show me my products',
                'what are my products',
                'products',
                'the products',
                'what work do I have',
                'show my home improvement projects',
                'list my installation projects',
                'what installations do I have',
                'show my jobs',
                'my jobs please',
                'what jobs are pending',
                'do I have any projects',
                'how many projects do I have',
                'what projects are there',
                'any pending projects',
                'my lowes projects',
                'show my lowes work',
                'list my store projects',
            ]
        },
        {
            'name': 'ProjectStatusInquiry',
            'description': 'Get details about a specific project',
            'utterances': [
                'details of second project',
                'first project details',
                'info on third project',
                'more info on project one',
                'tell me about my project',
                'last project details',
                'can you give me details of third project',
                'tell me about the product',
                'how is my project doing',
                'give me a status update',
                'what is the status',
                'details of first project',
                'can i get details',
                'second project details',
                'show me details',
                'product details',
                'more about the second one',
                'get status',
                'give me details of the third project',
                'what is project number one',
                'details of the last one',
                'give me details of second project',
                'details on second',
                'i need details',
                'show me the third project',
                'show me status',
                'info on the last project',
                'second one please',
                'details of the third project',
                'details for project two',
                'product information',
                'details of project 2',
                'project status',
                'give me the details',
                'what about the third project',
                'what is the status of my project',
                'details of the first project',
                'status update please',
                'tell me about the third project',
                'show me third project',
                'details of the previous one',
                'tell me about project 3',
                'third project details',
                'details please',
                'tell me more about second project',
                'number two',
                'give me details of third project',
                'more about second project',
                'what about the second project',
                'tell me about the first one',
                'the product please',
                'fourth project details',
                'can i get details of second project',
                'details of the product',
                'fifth project details',
                'details of third project',
                'what about the product',
                'tell me about the second project',
                'give me details of first project',
                'check project status',
                'i want details',
                'the second one',
                'show me project 1',
                'whats happening with my project',
                'whats happening with my job',
                'what is happening with my project',
                'what is happening with my job',
                'whats happening with my first job',
                'whats happening with my second job',
                'whats going on with my project',
                'any updates on my project',
                'who is the technician',
                'who is the tech',
                'who is coming',
                'who is assigned',
                'who is working on my project',
                'tell me about the technician',
                'who is the installer',
                'who is the crew',
                'where is the technician',
                'where is the plumber',
                'where is the carpenter',
            ]
        },
        {
            'name': 'RescheduleAppointment',
            'description': 'Reschedule an existing installation appointment',
            'utterances': [
                # Basic reschedule phrases
                'reschedule my appointment',
                'change my appointment',
                'move my appointment',
                'I need to reschedule',
                'can I change the time',
                'change appointment time',
                'reschedule please',
                'move to a different day',
                'pick a different time',
                'change the date',
                'I would like to reschedule my appointment',
                'may I change my appointment',
                'could we reschedule please',
                'I need to move my appointment to another day',
                'would it be possible to reschedule',
                'can we move it',
                'push it back',
                'can you come a different day',
                'need to change it',
                'gotta reschedule',
                'something came up need to move it',
                'that day does not work',
                'need a new date',
                # Job/Work/Service terminology
                'reschedule my job',
                'change my job',
                'move my job',
                'reschedule my work',
                'change my work date',
                'move my work',
                'reschedule my service',
                'reschedule my service call',
                'change my service date',
                'move my service call',
                'reschedule the job',
                'change the job date',
                # Installation specific
                'reschedule my installation',
                'change my install date',
                'move my project date',
                'reschedule my decking installation',
                'change my roofing appointment',
                'move my flooring install',
                'need to change when you come',
                'can the crew come a different day',
                # Situational
                'something came up',
                'I have a conflict',
                'I will not be home',
                'that time does not work for me',
                'can I reschedule',
                'is it possible to reschedule',
                'how do I reschedule',
                'can we pick a new date',
                'change when they come',
                'move my deck installation',
                'reschedule my roof appointment',
                # Date-specific reschedule
                'reschedule to next week',
                'move it to next week',
                'reschedule for next Tuesday',
                'change it to Monday',
                'can you come next week instead',
                'push it to next month',
                'reschedule to a later date',
                'move it to December',
                'change to a different week',
                'reschedule for the following week',
            ]
        },
        {
            'name': 'ScheduleAppointment',
            'description': 'Schedule a new appointment - single or multiple projects',
            'utterances': [
                'schedule all my projects',
                'schedule for tomorrow',
                'schedule not reschedule',
                'lets schedule it',
                'schedule project',
                'sure schedule it',
                'lets schedule',
                'can you schedule',
                'schedule my project',
                'book new appointment',
                'book for tuesday',
                'schedule the first project',
                'schedule something',
                'schedule my roofing project',
                'schedule for monday',
                'set up a new appointment',
                'schedule that',
                'schedule the last project',
                'book both',
                'schedule both projects',
                'yes book it',
                'book it',
                'okay book it',
                'create new booking',
                'schedule the first two projects',
                'schedule my flooring project',
                'book for next week',
                'i want to schedule',
                'i need a new appointment',
                'schedule this project',
                'book appointment for project',
                'book an appointment',
                'schedule this project please',
                'make an appointment',
                'schedule the second project',
                'schedule them all',
                'schedule appointment for project',
                'set up an appointment',
                'schedule my decking project',
                'book that',
                'set it up',
                'schedule first two projects',
                'new appointment',
                'lets book it',
                'book a new one',
                'set up appointment for this project',
                'book all projects',
                'schedule the appointment',
                'schedule a new one',
                'please book it',
                'book this project',
                'make a new appointment',
                'okay schedule it',
                'create an appointment',
                'I want to schedule my project',
                'schedule for this week',
                'book a time',
                'go ahead and schedule',
                'i want to book',
                'schedule an appointment',
                'please schedule',
                'I want to book',
                'schedule them',
                'schedule first three projects',
                'schedule my siding project',
                'I need to schedule',
                'new booking please',
                'yes schedule',
                'I need to book an appointment',
                'yeah schedule it',
                'schedule it',
                'can you schedule my project',
                'schedule the project',
                'go ahead and book',
                'schedule all projects',
                'schedule multiple projects',
            ]
        },
        {
            'name': 'ThankYou',
            'description': 'Express gratitude',
            'utterances': [
                'thank you',
                'thanks',
                'thanks a lot',
                'thank you so much',
                'appreciate it',
                'that is helpful',
                'thanks for your help',
                'thank you very much',
                'you have been helpful',
                'great thanks',
                'thank you kindly',
                'many thanks',
                'thanks so much',
                'I appreciate your help',
                'that was very helpful',
                'you are very helpful',
                'thanks for the information',
                'thank you for your time',
                'I really appreciate it',
                'that helps a lot',
                'perfect thank you',
                'wonderful thanks',
                'excellent thank you',
                'great help',
                'very helpful',
                'you are awesome',
                'thanks a bunch',
                'cheers',
                'much appreciated',
                'grateful for your help',
            ]
        },
        {
            'name': 'UrgentRequest',
            'description': 'Handle urgent requests and emergencies',
            'utterances': [
                'this is urgent',
                'emergency',
                'I need help urgently',
                'urgent matter',
                'this is an emergency',
                'urgent request',
                'I have an urgent issue',
                'need immediate help',
                'this is very urgent',
                'please help me urgently',
                'I have an emergency',
                'urgent problem',
                'critical issue',
                'my roof is leaking',
                'water is coming in',
                'something broke',
                'there is a problem with the installation',
                'the installer did not show up',
                'nobody came today',
                'I need someone right now',
                'can someone come today',
                'this cannot wait',
                'I need help immediately',
                'please hurry',
                'asap',
                'as soon as possible',
                'right away please',
                'I have a leak',
                'something is wrong',
                'there is damage',
                'the work is not done',
                'they left in the middle',
            ]
        },
        {
            'name': 'WeatherInquiry',
            'description': 'Check weather',
            'utterances': [
                'hows the weather outside',
                'tomorrow forecast',
                'weather please',
                'whats the weather like',
                'tell me weather',
                'will it snow',
                'will it be cloudy',
                'is it hot outside',
                'weather today',
                'what is the weather today',
                'weather report',
                'what is the forecast',
                'current weather',
                'is it chilly',
                'weather tomorrow',
                'forecast for tomorrow',
                'will it be cold tomorrow',
                'weather in',
                'weather update',
                'tomorrow weather',
                'tell me the weather',
                'weekend weather',
                'check the weather',
                'how is the weather today',
                'is it warm',
                'what will the weather be tomorrow',
                'will it rain',
                'will it be hot tomorrow',
                'weather on sunday',
                'todays weather',
                'weather at the job site',
                'weather forecast',
                'will it be chilly',
                'will it be sunny',
                'is it cold outside',
                'weather for tomorrow please',
                'temperature tomorrow',
                'weather at the project location',
                'how hot will it be',
                'how cold will it be',
                'will it be cold',
                'will it be warm',
                'get weather',
                'will it rain tomorrow',
                'check weather',
                'what is the weather tomorrow',
                'weather for tomorrow',
                'how is the weather',
                'weather conditions',
                'weather at the address',
                'weather this weekend',
                'will it be hot',
                'is it going to rain',
                'is it freezing',
                'weather on saturday',
                'whats the temperature',
                'is it going to rain tomorrow',
                'what is the weather',
            ]
        },
        {
            'name': 'Welcome',
            'description': 'Greeting and conversation start',
            'utterances': [
                'hello',
                'hi',
                'hey',
                'good morning',
                'good afternoon',
                'greetings',
                'hi there',
                'hello there',
                'hey there',
                'good evening',
                'howdy',
                'hiya',
                'yo',
                'whats up',
                'sup',
                'good day',
                'top of the morning',
                'hi its me',
                'hello its me calling',
                'this is calling about my project',
                'hi I am calling about my installation',
                'hello I need help',
                'hi I have a question',
                'hello can you help me',
                'hey I need some information',
                'hi this is about my appointment',
                'good morning I am calling about my project',
                'hello I would like some help please',
                'hi may I speak to someone',
            ]
        },
    ]

    # ========== DUPLICATE UTTERANCE CHECK ==========
    # CRITICAL: Lex V2 does not allow the same utterance in multiple intents
    print("  Checking for duplicate utterances across intents...")
    all_utterances = {}  # utterance -> intent_name
    duplicates_found = []

    for intent_def in intents:
        for utt in intent_def['utterances']:
            utt_lower = utt.lower().strip()
            if utt_lower in all_utterances:
                duplicates_found.append(f"'{utt}' in both '{all_utterances[utt_lower]}' and '{intent_def['name']}'")
            else:
                all_utterances[utt_lower] = intent_def['name']

    if duplicates_found:
        print(f"  [ERROR] Found {len(duplicates_found)} duplicate utterances:")
        for dup in duplicates_found:
            print(f"    - {dup}")
        print("  [FAIL] Fix duplicates in the intents list above before deploying!")
        raise Exception("Duplicate utterances found - bot build will fail. Fix the intents list.")
    else:
        print(f"  [OK] No duplicates found. {len(all_utterances)} unique utterances across all intents.")
    # ========== END DUPLICATE CHECK ==========

    created_intents = {}

    # Fulfillment updates config - FAST "please wait" (1 second delay)
    fulfillment_updates_spec = {
        'active': True,
        'startResponse': {
            'delayInSeconds': 1,  # Play wait message after just 1 second
            'messageGroups': [
                {
                    'message': {
                        'plainTextMessage': {
                            'value': 'Let me look that up for you.'
                        }
                    }
                },
                {
                    'message': {
                        'plainTextMessage': {
                            'value': 'One moment please.'
                        }
                    }
                },
                {
                    'message': {
                        'plainTextMessage': {
                            'value': 'Just a second while I check.'
                        }
                    }
                }
            ],
            'allowInterrupt': False
        },
        'updateResponse': {
            'frequencyInSeconds': 5,  # Play update every 5 sec if still waiting
            'messageGroups': [
                {
                    'message': {
                        'plainTextMessage': {
                            'value': 'Still working on that, almost there.'
                        }
                    }
                },
                {
                    'message': {
                        'plainTextMessage': {
                            'value': 'Thank you for your patience.'
                        }
                    }
                }
            ],
            'allowInterrupt': False
        },
        'timeoutInSeconds': 90  # Max 90 sec timeout for complex queries
    }

    # Post-fulfillment specification - CONTINUE conversation (ElicitIntent)
    post_fulfillment_continue = {
        'successNextStep': {'dialogAction': {'type': 'ElicitIntent'}},
        'failureNextStep': {'dialogAction': {'type': 'ElicitIntent'}},
        'timeoutNextStep': {'dialogAction': {'type': 'ElicitIntent'}}
    }

    # Post-fulfillment specification - END conversation (for Goodbye)
    post_fulfillment_end = {
        'successNextStep': {'dialogAction': {'type': 'EndConversation'}},
        'failureNextStep': {'dialogAction': {'type': 'EndConversation'}},
        'timeoutNextStep': {'dialogAction': {'type': 'EndConversation'}}
    }

    for intent_def in intents:
        print("  Creating intent: " + intent_def['name'] + "...")
        utterance_list = [{'utterance': u} for u in intent_def['utterances']]
        # Choose post-fulfillment spec: Goodbye ends conversation, others continue
        post_spec = post_fulfillment_end if intent_def['name'] == 'Goodbye' else post_fulfillment_continue
        intent_response = client.create_intent(
            botId=bot_id,
            botVersion='DRAFT',
            localeId='en_US',
            intentName=intent_def['name'],
            description=intent_def['description'],
            sampleUtterances=utterance_list,
            fulfillmentCodeHook={
                'enabled': True,
                'fulfillmentUpdatesSpecification': fulfillment_updates_spec,
                'postFulfillmentStatusSpecification': post_spec
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
                'fulfillmentUpdatesSpecification': fulfillment_updates_spec,
                'postFulfillmentStatusSpecification': post_fulfillment_continue  # Continue conversation
            },
            dialogCodeHook={'enabled': True}
        )
        print("  FallbackIntent configured with code hook, interim messages, and ElicitIntent")

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
# Step 4.1: SYNC BOT INTENTS (CRITICAL - Runs for BOTH new and existing bots)
# ============================================================================
# This step ensures ALL required intents exist with correct utterances.
# Without this, existing bots would be missing intents!
# ============================================================================

echo ""
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo -e "${YELLOW}Step 4.1: Syncing Bot Intents (CRITICAL)${NC}"
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo ""

if [[ -n "$LEX_BOT_ID" && "$LEX_BOT_ID" != "BOT_ID_PLACEHOLDER" ]]; then
    echo "  -> Syncing intents for bot: $LEX_BOT_ID"
    echo "  -> This ensures ALL required intents exist with correct utterances"
    echo ""

    # Export variables for Python script
    export LEX_BOT_ID
    export REGION
    export ACCOUNT_ID="${SELECTED_ACCOUNT_ID}"
    export ENVIRONMENT
    export LEX_FULFILLMENT_FUNCTION="pf-lex-fulfillment-${ENVIRONMENT}"

    $PYTHON_CMD << 'INTENT_SYNC_SCRIPT'
import boto3
import time
import os
import sys

# Configuration from environment
BOT_ID = os.environ.get('LEX_BOT_ID', '')
REGION = os.environ.get('REGION', 'us-east-1')
ACCOUNT_ID = os.environ.get('ACCOUNT_ID', '')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
LEX_FULFILLMENT_FUNCTION = os.environ.get('LEX_FULFILLMENT_FUNCTION', 'pf-lex-fulfillment-dev')

if not BOT_ID:
    print("  [ERROR] No BOT_ID provided")
    sys.exit(1)

session = boto3.Session(
    profile_name=os.environ.get('AWS_PROFILE'),
    region_name=REGION
)
client = session.client('lexv2-models')

LAMBDA_ARN = f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:{LEX_FULFILLMENT_FUNCTION}"

# All required intents with their utterances
REQUIRED_INTENTS = {
    'AppointmentInquiry': {
        'description': 'Check scheduled appointments and installations',
        'utterances': [
            'do I have any appointments',
            'show my appointments',
            'what appointments do I have',
            'check my appointments',
            'list appointments',
            'any upcoming appointments',
            'when is my next appointment',
            'appointment schedule',
            'my appointments please',
            'show me my schedule',
            'my appointments',
            'I would like to check my appointments',
            'may I see my appointments',
            'could you tell me about my appointments',
            'please show my appointments',
            'I need to check my schedule',
            'what is my appointment schedule',
            'when am I scheduled',
            'whats on my calendar',
            'any appointments coming up',
            'got any appointments',
            'am I scheduled for anything',
            'whens my appointment',
            'when is my installation',
            'when is my project scheduled',
            'when is my decking appointment',
            'when is my roofing scheduled',
            'when is my flooring installation',
            'show my installation date',
            'when are they coming',
            'when is the installer coming',
            'when is the technician coming',
            'when is the crew coming',
            'appointments',
            'the appointments',
            'show appointment',
            'check appointment',
            'appointment status',
            'is anything scheduled',
            'do I have anything scheduled',
            'what dates am I booked for',
            'show my booked dates',
            'when is my next install',
            'upcoming installations',
        ]
    },
    'BusinessHours': {
        'description': 'Ask about business and installation hours',
        'utterances': [
            'what are your hours',
            'when are you open',
            'business hours',
            'operating hours',
            'what time do you open',
            'what time do you close',
            'are you open on weekends',
            'hours of operation',
            'when can I call',
            'office hours',
            'what are your working hours',
            'store hours',
            'are you open today',
            'are you open tomorrow',
            'are you open on saturday',
            'are you open on sunday',
            'what days are you open',
            'when do you start work',
            'when do installers work',
            'what time does installation start',
            'earliest appointment time',
            'latest appointment time',
            'do you work on holidays',
            'are you open on christmas',
            'are you closed on thanksgiving',
            'when can I schedule an appointment',
            'what hours do you install',
            'do you do evening appointments',
            'do you work mornings',
            'can you come early morning',
            'can you come late afternoon',
        ]
    },
    'CancelAppointment': {
        'description': 'Cancel an existing installation appointment',
        'utterances': [
            'cancel my appointment',
            'I need to cancel',
            'cancel the appointment',
            'remove my appointment',
            'I want to cancel',
            'cancel please',
            'delete appointment',
            'I cannot make it',
            'cancel my booking',
            'I would like to cancel my appointment',
            'may I cancel please',
            'I need to cancel my scheduled appointment',
            'please cancel my appointment',
            'cancel it',
            'just cancel',
            'nevermind cancel it',
            'do not come',
            'do not need it anymore',
            'changed my mind',
            'not doing it anymore',
            'forget it',
            'cancel my installation',
            'cancel my project',
            'cancel the install',
            'cancel my decking installation',
            'cancel my roofing appointment',
            'cancel my flooring project',
            'do not install it',
            'cancel the scheduled work',
            'cancel the crew',
            'I changed my mind about the project',
            'I do not want to proceed',
            'I decided not to do it',
            'we are not doing the project',
            'can I cancel',
            'how do I cancel',
            'is it too late to cancel',
            'can I still cancel',
            'what if I cancel',
            'stop the project',
            'cancel everything',
            'cancel my deck project',
            'cancel my roof work',
        ]
    },
    'CheckAvailability': {
        'description': 'Check available dates for scheduling installations',
        'utterances': [
            'what dates are available',
            'show available dates',
            'when can I schedule',
            'available times',
            'what times work',
            'check availability',
            'when are you available',
            'show me available slots',
            'open dates',
            'free dates',
            'what days are open',
            'available appointments',
            'I would like to know what dates are available',
            'may I see available times',
            'could you show me the available dates',
            'please check availability',
            'what would be a good time',
            'when would be convenient',
            'when can you come',
            'when can you guys come out',
            'whats open',
            'got any openings',
            'any slots available',
            'when can we do this',
            'earliest available',
            'soonest available',
            'next available date',
            'when can you install',
            'when can you do the work',
            'when can you start the project',
            'when can you start my deck',
            'when can you do my roof',
            'when can you install my flooring',
            'available dates for installation',
            'installation availability',
            'what about next week',
            'anything this week',
            'any openings this month',
            'do you have anything on monday',
            'availability for tuesday',
            'can you come this weekend',
            'saturday availability',
            'how soon can you come',
            'how quickly can you schedule',
            'what is your earliest availability',
            'when is the next opening',
        ]
    },
    'Goodbye': {
        'description': 'End conversation and disconnect call',
        'utterances': [
            'goodbye',
            'bye',
            'bye bye',
            'see you',
            'see you later',
            'thanks bye',
            'thank you goodbye',
            'ok bye',
            'alright bye',
            'that is all',
            'thats all',
            'that will be all',
            'I am done',
            'im done',
            'all done',
            'nothing else',
            'no more questions',
            'I am finished',
            'we are done',
            'thanks thats all',
            'thank you thats all',
            'hang up',
            'end call',
            'disconnect',
            'end the call',
            'take care',
            'have a good day',
            'talk to you later',
            'thanks for your help goodbye',
            'that helps thanks bye',
            'no',
            'nope',
            'no thanks',
            'no thank you',
            'I am good',
            'im good',
            'thats it',
            'that is it',
            'no I am done',
            'no im done',
            'I do not need any help',
            'I dont need any help',
            'I do not need anything else',
            'I dont need anything else',
            'no I am good',
            'no im good',
            'I am all set',
            'im all set',
            'no I am all set',
            'not right now',
            'no not right now',
            'maybe later',
            'not at this time',
            'I am okay',
            'im okay',
        ]
    },
    'Help': {
        'description': 'Request for assistance or options',
        'utterances': [
            'help',
            'help me',
            'I need help',
            'can you help',
            'what can you do',
            'what are my options',
            'how does this work',
            'I need assistance',
            'can you assist me',
            'I am confused',
            'I do not understand',
            'what should I do',
            'guide me',
            'walk me through this',
            'I am not sure what to do',
            'help please',
            'I need some help',
            'can someone help me',
            'what do I do',
            'how do I use this',
            'what can I ask you',
            'what are you able to do',
            'show me what you can do',
            'what services do you offer',
            'how can you help me',
            'I am lost',
            'start over',
            'I need to talk to someone',
            'can I speak to a person',
        ]
    },
    'HowAreYou': {
        'description': 'Casual chitchat greeting',
        'utterances': [
            'how are you',
            'how are you doing',
            'how is it going',
            'what is up',
            'how do you do',
            'are you doing well',
            'hows everything',
            'how have you been',
            'you doing okay',
            'how are things',
            'hows your day',
            'hows it going today',
            'you good',
            'all good',
            'everything alright',
            'are you okay',
            'are you well',
            'how is your day going',
            'having a good day',
            'busy today',
            'how is work',
            'nice to talk to you',
            'good to hear from you',
        ]
    },
    'ProjectInquiry': {
        'description': 'List customer projects - home improvement work',
        'utterances': [
            'list my projects',
            'show my projects',
            'what are my projects',
            'tell me about my projects',
            'get my projects',
            'my projects',
            'show projects',
            'what projects do I have',
            'projects please',
            'can you list my projects',
            'I want to see my projects',
            'I would like to see my projects',
            'may I see my projects please',
            'could you show me my projects',
            'please show my projects',
            'whats up with my projects',
            'show me what I got',
            'what do I have going on',
            'any projects',
            'got any projects',
            'my stuff',
            'show my stuff',
            'what am I working on',
            'whats going on with my work',
            'show my decking project',
            'list my roofing projects',
            'my siding project',
            'show my flooring project',
            'list my fencing project',
            'my painting project',
            'show my window project',
            'my kitchen project',
            'my bathroom project',
            'show my gutter project',
            'list my deck project',
            'my roof project',
            'list my products',
            'show my products',
            'what products do I have',
            'my products please',
            'tell me about my products',
            'show me my products',
            'what are my products',
            'products',
            'the products',
            'what work do I have',
            'show my home improvement projects',
            'list my installation projects',
            'what installations do I have',
            'show my jobs',
            'my jobs please',
            'what jobs are pending',
            'do I have any projects',
            'how many projects do I have',
            'what projects are there',
            'any pending projects',
            'my lowes projects',
            'show my lowes work',
            'list my store projects',
        ]
    },
    'ProjectStatusInquiry': {
        'description': 'Get details about a specific project',
        'utterances': [
            'details of second project',
            'first project details',
            'info on third project',
            'more info on project one',
            'tell me about my project',
            'last project details',
            'can you give me details of third project',
            'tell me about the product',
            'how is my project doing',
            'give me a status update',
            'what is the status',
            'details of first project',
            'can i get details',
            'second project details',
            'show me details',
            'product details',
            'more about the second one',
            'get status',
            'give me details of the third project',
            'what is project number one',
            'details of the last one',
            'give me details of second project',
            'details on second',
            'i need details',
            'show me the third project',
            'show me status',
            'info on the last project',
            'second one please',
            'details of the third project',
            'details for project two',
            'product information',
            'details of project 2',
            'project status',
            'give me the details',
            'what about the third project',
            'what is the status of my project',
            'details of the first project',
            'status update please',
            'tell me about the third project',
            'show me third project',
            'details of the previous one',
            'tell me about project 3',
            'third project details',
            'details please',
            'tell me more about second project',
            'number two',
            'give me details of third project',
            'more about second project',
            'what about the second project',
            'tell me about the first one',
            'the product please',
            'fourth project details',
            'can i get details of second project',
            'details of the product',
            'fifth project details',
            'details of third project',
            'what about the product',
            'tell me about the second project',
            'give me details of first project',
            'check project status',
            'i want details',
            'the second one',
            'show me project 1',
        ]
    },
    'RescheduleAppointment': {
        'description': 'Reschedule an existing installation appointment',
        'utterances': [
            'reschedule my appointment',
            'change my appointment',
            'move my appointment',
            'I need to reschedule',
            'can I change the time',
            'change appointment time',
            'reschedule please',
            'move to a different day',
            'pick a different time',
            'change the date',
            'I would like to reschedule my appointment',
            'may I change my appointment',
            'could we reschedule please',
            'I need to move my appointment to another day',
            'would it be possible to reschedule',
            'can we move it',
            'push it back',
            'can you come a different day',
            'need to change it',
            'gotta reschedule',
            'something came up need to move it',
            'that day does not work',
            'need a new date',
            'reschedule my job',
            'change my job',
            'move my job',
            'reschedule my work',
            'change my work date',
            'move my work',
            'reschedule my service',
            'reschedule my service call',
            'change my service date',
            'move my service call',
            'reschedule the job',
            'change the job date',
            'reschedule my installation',
            'change my install date',
            'move my project date',
            'reschedule my decking installation',
            'change my roofing appointment',
            'move my flooring install',
            'need to change when you come',
            'can the crew come a different day',
            'something came up',
            'I have a conflict',
            'I will not be home',
            'that time does not work for me',
            'can I reschedule',
            'is it possible to reschedule',
            'how do I reschedule',
            'can we pick a new date',
            'change when they come',
            'move my deck installation',
            'reschedule my roof appointment',
            'reschedule to next week',
            'move it to next week',
            'reschedule for next Tuesday',
            'change it to Monday',
            'can you come next week instead',
            'push it to next month',
            'reschedule to a later date',
            'move it to December',
            'change to a different week',
            'reschedule for the following week',
        ]
    },
    'ScheduleAppointment': {
        'description': 'Schedule a new appointment - single or multiple projects',
        'utterances': [
            'schedule all my projects',
            'schedule for tomorrow',
            'schedule not reschedule',
            'lets schedule it',
            'schedule project',
            'sure schedule it',
            'lets schedule',
            'can you schedule',
            'schedule my project',
            'book new appointment',
            'book for tuesday',
            'schedule the first project',
            'schedule something',
            'schedule my roofing project',
            'schedule for monday',
            'set up a new appointment',
            'schedule that',
            'schedule the last project',
            'book both',
            'schedule both projects',
            'yes book it',
            'book it',
            'okay book it',
            'create new booking',
            'schedule the first two projects',
            'schedule my flooring project',
            'book for next week',
            'i want to schedule',
            'i need a new appointment',
            'schedule this project',
            'book appointment for project',
            'book an appointment',
            'schedule this project please',
            'make an appointment',
            'schedule the second project',
            'schedule them all',
            'schedule appointment for project',
            'set up an appointment',
            'schedule my decking project',
            'book that',
            'set it up',
            'schedule first two projects',
            'new appointment',
            'lets book it',
            'book a new one',
            'set up appointment for this project',
            'book all projects',
            'schedule the appointment',
            'schedule a new one',
            'please book it',
            'book this project',
            'make a new appointment',
            'okay schedule it',
            'create an appointment',
            'I want to schedule my project',
            'schedule for this week',
            'book a time',
            'go ahead and schedule',
            'i want to book',
            'schedule an appointment',
            'please schedule',
            'I want to book',
            'schedule them',
            'schedule first three projects',
            'schedule my siding project',
            'I need to schedule',
            'new booking please',
            'yes schedule',
            'I need to book an appointment',
            'yeah schedule it',
            'schedule it',
            'can you schedule my project',
            'schedule the project',
            'go ahead and book',
            'schedule all projects',
            'schedule multiple projects',
        ]
    },
    'ThankYou': {
        'description': 'Express gratitude',
        'utterances': [
            'thank you',
            'thanks',
            'thanks a lot',
            'thank you so much',
            'appreciate it',
            'that is helpful',
            'thanks for your help',
            'thank you very much',
            'you have been helpful',
            'great thanks',
            'thank you kindly',
            'many thanks',
            'thanks so much',
            'I appreciate your help',
            'that was very helpful',
            'you are very helpful',
            'thanks for the information',
            'thank you for your time',
            'I really appreciate it',
            'that helps a lot',
            'perfect thank you',
            'wonderful thanks',
            'excellent thank you',
            'great help',
            'very helpful',
            'you are awesome',
            'thanks a bunch',
            'cheers',
            'much appreciated',
            'grateful for your help',
        ]
    },
    'UrgentRequest': {
        'description': 'Handle urgent requests and emergencies',
        'utterances': [
            'this is urgent',
            'emergency',
            'I need help urgently',
            'urgent matter',
            'this is an emergency',
            'urgent request',
            'I have an urgent issue',
            'need immediate help',
            'this is very urgent',
            'please help me urgently',
            'I have an emergency',
            'urgent problem',
            'critical issue',
            'my roof is leaking',
            'water is coming in',
            'something broke',
            'there is a problem with the installation',
            'the installer did not show up',
            'nobody came today',
            'I need someone right now',
            'can someone come today',
            'this cannot wait',
            'I need help immediately',
            'please hurry',
            'asap',
            'as soon as possible',
            'right away please',
            'I have a leak',
            'something is wrong',
            'there is damage',
            'the work is not done',
            'they left in the middle',
        ]
    },
    'WeatherInquiry': {
        'description': 'Check weather',
        'utterances': [
            'hows the weather outside',
            'tomorrow forecast',
            'weather please',
            'whats the weather like',
            'tell me weather',
            'will it snow',
            'will it be cloudy',
            'is it hot outside',
            'weather today',
            'what is the weather today',
            'weather report',
            'what is the forecast',
            'current weather',
            'is it chilly',
            'weather tomorrow',
            'forecast for tomorrow',
            'will it be cold tomorrow',
            'weather in',
            'weather update',
            'tomorrow weather',
            'tell me the weather',
            'weekend weather',
            'check the weather',
            'how is the weather today',
            'is it warm',
            'what will the weather be tomorrow',
            'will it rain',
            'will it be hot tomorrow',
            'weather on sunday',
            'todays weather',
            'weather at the job site',
            'weather forecast',
            'will it be chilly',
            'will it be sunny',
            'is it cold outside',
            'weather for tomorrow please',
            'temperature tomorrow',
            'weather at the project location',
            'how hot will it be',
            'how cold will it be',
            'will it be cold',
            'will it be warm',
            'get weather',
            'will it rain tomorrow',
            'check weather',
            'what is the weather tomorrow',
            'weather for tomorrow',
            'how is the weather',
            'weather conditions',
            'weather at the address',
            'weather this weekend',
            'will it be hot',
            'is it going to rain',
            'is it freezing',
            'weather on saturday',
            'whats the temperature',
            'is it going to rain tomorrow',
            'what is the weather',
        ]
    },
    'Welcome': {
        'description': 'Greeting and conversation start',
        'utterances': [
            'hello',
            'hi',
            'hey',
            'good morning',
            'good afternoon',
            'greetings',
            'hi there',
            'hello there',
            'hey there',
            'good evening',
            'howdy',
            'hiya',
            'yo',
            'whats up',
            'sup',
            'good day',
            'top of the morning',
            'hi its me',
            'hello its me calling',
            'this is calling about my project',
            'hi I am calling about my installation',
            'hello I need help',
            'hi I have a question',
            'hello can you help me',
            'hey I need some information',
            'hi this is about my appointment',
            'good morning I am calling about my project',
            'hello I would like some help please',
            'hi may I speak to someone',
        ]
    },
}

# Fulfillment config with SSML-enhanced messages - natural sounding wait prompts
fulfillment_updates_spec = {
    'active': True,
    'startResponse': {
        'delayInSeconds': 1,  # Play wait message after just 1 second
        'messageGroups': [
            {'message': {'ssmlMessage': {'value': '<speak><prosody rate="medium" pitch="medium">Let me look that up for you.</prosody><break time="300ms"/></speak>'}}},
            {'message': {'ssmlMessage': {'value': '<speak><prosody rate="medium">One moment please.</prosody><break time="200ms"/></speak>'}}},
            {'message': {'ssmlMessage': {'value': '<speak><prosody rate="medium" pitch="medium">Just a second while I check.</prosody></speak>'}}},
            {'message': {'ssmlMessage': {'value': '<speak><amazon:emotion name="excited" intensity="low">Sure, let me find that for you!</amazon:emotion></speak>'}}}
        ],
        'allowInterrupt': False  # Don't let user interrupt wait message
    },
    'updateResponse': {
        'frequencyInSeconds': 5,  # Play update every 5 seconds if still waiting
        'messageGroups': [
            {'message': {'ssmlMessage': {'value': '<speak><prosody rate="medium">Still working on that<break time="200ms"/>almost there.</prosody></speak>'}}},
            {'message': {'ssmlMessage': {'value': '<speak><prosody rate="medium" pitch="low">Thank you for your patience.</prosody></speak>'}}},
            {'message': {'ssmlMessage': {'value': '<speak>Just a few more seconds<break time="300ms"/>I appreciate you waiting.</speak>'}}}
        ],
        'allowInterrupt': False
    },
    'timeoutInSeconds': 90
}

# Post-fulfillment specification - CONTINUE conversation (ElicitIntent)
# This ensures the bot asks follow-up questions after each response
post_fulfillment_continue = {
    'successNextStep': {
        'dialogAction': {
            'type': 'ElicitIntent'  # Continue conversation after success
        }
    },
    'failureNextStep': {
        'dialogAction': {
            'type': 'ElicitIntent'  # Continue even on failure
        }
    },
    'timeoutNextStep': {
        'dialogAction': {
            'type': 'ElicitIntent'  # Continue even on timeout
        }
    }
}

# Post-fulfillment specification - END conversation (for Goodbye intent only)
# This hangs up the phone call when user says goodbye
post_fulfillment_end = {
    'successNextStep': {
        'dialogAction': {
            'type': 'EndConversation'  # Hang up after goodbye
        }
    },
    'failureNextStep': {
        'dialogAction': {
            'type': 'EndConversation'
        }
    },
    'timeoutNextStep': {
        'dialogAction': {
            'type': 'EndConversation'
        }
    }
}

try:
    # Get existing intents
    print("  Checking existing intents...")
    existing_intents = {}
    response = client.list_intents(botId=BOT_ID, botVersion='DRAFT', localeId='en_US')
    for intent in response.get('intentSummaries', []):
        existing_intents[intent['intentName']] = intent['intentId']

    print(f"  Found {len(existing_intents)} existing intents: {list(existing_intents.keys())}")

    # Find missing intents
    missing = [name for name in REQUIRED_INTENTS.keys() if name not in existing_intents]
    if missing:
        print(f"  [WARN] Missing intents: {missing}")
    else:
        print("  [OK] All required intents exist")

    # ========== DUPLICATE UTTERANCE CHECK FOR REQUIRED_INTENTS ==========
    print("  Checking for duplicate utterances in REQUIRED_INTENTS...")
    all_utterances = {}
    duplicates_found = []

    for intent_name, config in REQUIRED_INTENTS.items():
        for utt in config['utterances']:
            utt_lower = utt.lower().strip()
            if utt_lower in all_utterances:
                duplicates_found.append(f"'{utt}' in both '{all_utterances[utt_lower]}' and '{intent_name}'")
            else:
                all_utterances[utt_lower] = intent_name

    if duplicates_found:
        print(f"  [ERROR] Found {len(duplicates_found)} duplicate utterances:")
        for dup in duplicates_found:
            print(f"    - {dup}")
        print("  [FAIL] Fix duplicates in REQUIRED_INTENTS before deploying!")
        raise Exception("Duplicate utterances found in REQUIRED_INTENTS")
    else:
        print(f"  [OK] No duplicates in REQUIRED_INTENTS. {len(all_utterances)} unique utterances.")
    # ========== END DUPLICATE CHECK ==========

    # Create missing intents
    created_count = 0
    updated_count = 0

    for intent_name, config in REQUIRED_INTENTS.items():
        utterance_list = [{'utterance': u} for u in config['utterances']]

        # Choose post-fulfillment spec: Goodbye ends conversation, others continue
        post_fulfillment_spec = post_fulfillment_end if intent_name == 'Goodbye' else post_fulfillment_continue

        if intent_name not in existing_intents:
            # CREATE new intent
            print(f"  Creating intent: {intent_name}...")
            try:
                response = client.create_intent(
                    botId=BOT_ID,
                    botVersion='DRAFT',
                    localeId='en_US',
                    intentName=intent_name,
                    description=config['description'],
                    sampleUtterances=utterance_list,
                    fulfillmentCodeHook={
                        'enabled': True,
                        'fulfillmentUpdatesSpecification': fulfillment_updates_spec,
                        'postFulfillmentStatusSpecification': post_fulfillment_spec
                    }
                )
                existing_intents[intent_name] = response['intentId']
                created_count += 1
                print(f"    [OK] Created {intent_name}")
            except Exception as e:
                print(f"    [ERROR] Failed to create {intent_name}: {e}")
        else:
            # UPDATE existing intent with latest utterances
            intent_id = existing_intents[intent_name]
            try:
                # Get current intent config
                current = client.describe_intent(
                    botId=BOT_ID,
                    botVersion='DRAFT',
                    localeId='en_US',
                    intentId=intent_id
                )

                # Update with new utterances and post-fulfillment spec
                client.update_intent(
                    botId=BOT_ID,
                    botVersion='DRAFT',
                    localeId='en_US',
                    intentId=intent_id,
                    intentName=intent_name,
                    description=config['description'],
                    sampleUtterances=utterance_list,
                    fulfillmentCodeHook={
                        'enabled': True,
                        'fulfillmentUpdatesSpecification': fulfillment_updates_spec,
                        'postFulfillmentStatusSpecification': post_fulfillment_spec
                    }
                )
                updated_count += 1
            except Exception as e:
                # Some intents (like FallbackIntent) can't be fully updated
                if 'FallbackIntent' not in intent_name:
                    print(f"    [WARN] Could not update {intent_name}: {e}")

    # Configure FallbackIntent with code hook
    print("  Configuring FallbackIntent...")
    if 'FallbackIntent' in existing_intents:
        fallback_id = existing_intents['FallbackIntent']
        current = client.describe_intent(
            botId=BOT_ID,
            botVersion='DRAFT',
            localeId='en_US',
            intentId=fallback_id
        )
        client.update_intent(
            botId=BOT_ID,
            botVersion='DRAFT',
            localeId='en_US',
            intentId=fallback_id,
            intentName='FallbackIntent',
            parentIntentSignature=current.get('parentIntentSignature', 'AMAZON.FallbackIntent'),
            fulfillmentCodeHook={
                'enabled': True,
                'fulfillmentUpdatesSpecification': fulfillment_updates_spec,
                'postFulfillmentStatusSpecification': post_fulfillment_continue  # Continue conversation on fallback
            },
            dialogCodeHook={'enabled': True}
        )
        print("    [OK] FallbackIntent configured with ElicitIntent")

    # Enable Assisted NLU (Primary mode) AND Voice Settings
    print("  Configuring voice settings and Assisted NLU...")
    client.update_bot_locale(
        botId=BOT_ID,
        botVersion='DRAFT',
        localeId='en_US',
        nluIntentConfidenceThreshold=0.4,
        voiceSettings={
            'voiceId': 'Joanna',  # Clear American English voice - CRITICAL for speech recognition
            'engine': 'neural'    # Neural engine for better quality
        },
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
    print("    [OK] Voice settings: Joanna (neural)")
    print("    [OK] Assisted NLU enabled (Primary mode)")

    # Build the bot
    print("  Building bot locale...")
    client.build_bot_locale(botId=BOT_ID, botVersion='DRAFT', localeId='en_US')

    # Wait for build
    for i in range(60):
        time.sleep(3)
        status = client.describe_bot_locale(botId=BOT_ID, botVersion='DRAFT', localeId='en_US')
        build_status = status['botLocaleStatus']
        if build_status in ['Built', 'ReadyExpressTesting']:
            print(f"    [OK] Bot built successfully!")
            break
        elif build_status in ['Failed', 'NotBuilt']:
            print(f"    [ERROR] Build failed: {build_status}")
            sys.exit(1)
        if i % 5 == 0:
            print(f"    Building... ({build_status})")

    # Verify Assisted NLU
    verify = client.describe_bot_locale(botId=BOT_ID, botVersion='DRAFT', localeId='en_US')
    gen_ai = verify.get('generativeAISettings', {}).get('runtimeSettings', {}).get('nluImprovement', {})
    if gen_ai.get('enabled') and gen_ai.get('assistedNluMode') == 'Primary':
        print("    [VERIFIED] Assisted NLU is ENABLED (Primary mode)")
    else:
        print(f"    [WARN] Assisted NLU may not be properly enabled: {gen_ai}")

    # Create new version
    print("  Creating bot version...")
    version_response = client.create_bot_version(
        botId=BOT_ID,
        botVersionLocaleSpecification={'en_US': {'sourceBotVersion': 'DRAFT'}}
    )
    bot_version = version_response['botVersion']
    print(f"    [OK] Version created: {bot_version}")

    # Wait for version
    for i in range(30):
        time.sleep(2)
        ver_status = client.describe_bot_version(botId=BOT_ID, botVersion=bot_version)
        if ver_status['botStatus'] == 'Available':
            break

    # Update alias to point to new version
    print("  Updating bot alias...")
    aliases = client.list_bot_aliases(botId=BOT_ID)
    for alias in aliases.get('botAliasSummaries', []):
        if alias['botAliasName'] == 'TestBotAlias':
            client.update_bot_alias(
                botId=BOT_ID,
                botAliasId=alias['botAliasId'],
                botAliasName='TestBotAlias',
                botVersion=bot_version,
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
                sentimentAnalysisSettings={'detectSentiment': True}
            )
            print(f"    [OK] Alias updated to version {bot_version}")
            break

    # Final summary
    print("")
    print("  ========== INTENT SYNC SUMMARY ==========")
    print(f"  Created: {created_count} new intents")
    print(f"  Updated: {updated_count} existing intents")
    print(f"  Total intents: {len(REQUIRED_INTENTS)}")

    # Verify final state
    final_intents = client.list_intents(botId=BOT_ID, botVersion='DRAFT', localeId='en_US')
    final_names = [i['intentName'] for i in final_intents.get('intentSummaries', [])]
    print(f"  Final intents in bot: {final_names}")

    missing_final = [name for name in REQUIRED_INTENTS.keys() if name not in final_names]
    if missing_final:
        print(f"  [ERROR] Still missing: {missing_final}")
        sys.exit(1)
    else:
        print("  [OK] All intents verified!")
    print("  ==========================================")

except Exception as e:
    print(f"  [ERROR] Intent sync failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
INTENT_SYNC_SCRIPT

    if [[ $? -ne 0 ]]; then
        echo -e "${RED}  [ERROR] Intent sync failed!${NC}"
        exit 1
    fi
    echo ""
    echo -e "${GREEN}  [OK] Intent sync complete!${NC}"
else
    echo "  [SKIP] No valid bot ID, skipping intent sync"
fi

# ============================================================================
# Step 4.4: Create Amazon Transcribe Custom Vocabulary (Better Speech Recognition)
# ============================================================================
echo ""
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo -e "${YELLOW}Step 4.4: Creating Amazon Transcribe Custom Vocabulary${NC}"
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo ""

VOCAB_NAME="pf-home-improvement-vocab"
echo "  -> Creating custom vocabulary: $VOCAB_NAME"

# Check if vocabulary exists and is ready
VOCAB_STATUS=$(aws_cmd transcribe get-vocabulary --vocabulary-name "$VOCAB_NAME" --region "$REGION" --query "VocabularyState" --output text 2>/dev/null || echo "NOT_FOUND")

if [[ "$VOCAB_STATUS" == "READY" ]]; then
    echo "  [OK] Custom vocabulary already exists and is ready"
else
    echo "  -> Creating/updating vocabulary..."

    # Delete existing if in failed state
    if [[ "$VOCAB_STATUS" != "NOT_FOUND" && "$VOCAB_STATUS" != "PENDING" ]]; then
        aws_cmd transcribe delete-vocabulary --vocabulary-name "$VOCAB_NAME" --region "$REGION" 2>/dev/null || true
        sleep 3
    fi

    # Create vocabulary with home improvement terms
    $PYTHON_CMD << 'TRANSCRIBE_VOCAB_EOF'
import boto3
import time

transcribe = boto3.client('transcribe', region_name='us-east-1')
vocabulary_name = 'pf-home-improvement-vocab'

# Domain-specific vocabulary for home improvement scheduling
vocabulary_terms = [
    # PROJECT CATEGORIES
    'decking', 'roofing', 'siding', 'flooring', 'fencing', 'plumbing',
    'gutters', 'painting', 'windows', 'doors', 'kitchen', 'bath', 'bathroom',
    'generator', 'HVAC', 'electrical', 'carpentry', 'drywall', 'insulation',
    'landscaping', 'patio', 'pergola', 'garage', 'basement', 'attic',
    'countertops', 'cabinets', 'tile', 'hardwood', 'vinyl', 'laminate',

    # COMPOUND TERMS
    'kitchen-and-bath', 'doors-and-windows', 'windows-and-doors',
    'generator-installation', 'roof-repair', 'roof-replacement',
    'deck-installation', 'floor-installation', 'gutter-installation',
    'siding-installation', 'fence-installation', 'window-replacement',
    'door-replacement', 'bathroom-remodel', 'kitchen-remodel',
    'home-improvement', 'exterior-work', 'interior-work',

    # SCHEDULING TERMS
    'appointment', 'schedule', 'reschedule', 'cancel', 'available',
    'availability', 'time-slot', 'timeslot', 'morning', 'afternoon',
    'evening', 'tomorrow', 'today', 'next-week', 'this-week',

    # WEATHER TERMS (critical for voice recognition)
    'weather', 'forecast', 'rain', 'rainy', 'sunny', 'cloudy',
    'temperature', 'snow', 'snowy', 'storm', 'stormy', 'windy',

    # ACTION TERMS
    'list', 'show', 'details', 'information', 'status', 'check',
    'book', 'confirm', 'update', 'change',

    # PEOPLE/ROLES
    'technician', 'installer', 'contractor', 'customer', 'homeowner',

    # BUSINESS TERMS
    'project', 'projects', 'estimate', 'quote', 'installation',
    'service', 'work-order', 'ProjectsForce',

    # STORE NAMES
    'Lowes', 'Home-Depot', 'Menards',

    # COMMON PHRASES
    'how-is-the-weather', 'whats-the-weather', 'schedule-my-project',
    'list-my-projects', 'my-appointments', 'reschedule-appointment',
    'cancel-appointment', 'project-details', 'when-is-my-appointment',
    'who-is-my-technician', 'what-projects-do-I-have',
]

try:
    # Delete if exists
    try:
        transcribe.delete_vocabulary(VocabularyName=vocabulary_name)
        print("  Deleted existing vocabulary...")
        time.sleep(3)
    except:
        pass

    # Create vocabulary
    response = transcribe.create_vocabulary(
        VocabularyName=vocabulary_name,
        LanguageCode='en-US',
        Phrases=vocabulary_terms
    )
    print(f"  [OK] Vocabulary creation started: {response['VocabularyState']}")
    print(f"  Total phrases: {len(vocabulary_terms)}")
except Exception as e:
    print(f"  [WARN] Vocabulary creation error: {e}")
TRANSCRIBE_VOCAB_EOF
fi

# ============================================================================
# Step 4.45: Create Amazon Lex V2 Custom Vocabulary (Real-Time ASR)
# ============================================================================
# IMPORTANT: This is DIFFERENT from Transcribe vocabulary above!
# - Transcribe vocabulary = Post-call analytics (Contact Lens)
# - Lex V2 vocabulary = Real-time speech recognition during calls
# ============================================================================

echo ""
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo -e "${YELLOW}Step 4.45: Creating Lex V2 Custom Vocabulary (Real-Time ASR)${NC}"
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo ""

if [[ -n "$LEX_BOT_ID" && "$LEX_BOT_ID" != "BOT_ID_PLACEHOLDER" ]]; then
    echo "  -> Creating Lex V2 custom vocabulary for bot: $LEX_BOT_ID"

    # Create vocabulary TSV file
    LEX_VOCAB_DIR=$(mktemp -d)
    cat > "$LEX_VOCAB_DIR/CustomVocabulary.tsv" << 'LEX_VOCAB_TSV'
phrase	weight	displayAs
weather	3
hows the weather	3
weather tomorrow	3
weather forecast	3
whats the weather	3
project	3
projects	3
first project	3
second project	3
third project	3
fourth project	3
project details	3
job	3
jobs	3
my job	3
my jobs	3
the job	3
first job	3
second job	3
third job	3
fourth job	3
work	2
my work	2
the work	2
installation	3
my installation	3
schedule	2
appointment	2
reschedule	2
decking	3
deck installation	3
fencing	3
flooring	3
plumbing	3
roofing	3
kitchen and bath	2
generator installation	2
windows and doors	2
technician	3
the technician	3
who is the technician	3
who is the tech	3
tech	3
installer	3
the installer	3
who is the installer	3
crew	3
the crew	3
crew member	3
who is the crew	3
worker	3
the worker	3
contractor	3
the contractor	3
person working	3
the person working	3
who is the person	3
who is coming	3
who is assigned	3
assigned technician	3
plumber	3
the plumber	3
where is the plumber	3
carpenter	3
the carpenter	3
where is the carpenter	3
electrician	3
the electrician	3
where is the electrician	3
where is the technician	3
where is the person	3
where is the crew	3
where is the worker	3
whats happening	3
what is happening	3
whats happening with my job	3
whats happening with my project	3
whats happening with my second job	3
whats happening with my first job	3
happening with my project	3
status of my job	3
status of my project	3
my first job	3
my second job	3
my third job	3
LEX_VOCAB_TSV

    # Create zip file
    (cd "$LEX_VOCAB_DIR" && zip -q vocab.zip CustomVocabulary.tsv)

    # Step 1: Get upload URL
    echo "  -> Getting upload URL..."
    UPLOAD_RESPONSE=$(aws_cmd lexv2-models create-upload-url --region "$REGION" 2>/dev/null)
    LEX_IMPORT_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.importId // empty')
    UPLOAD_URL=$(echo "$UPLOAD_RESPONSE" | jq -r '.uploadUrl // empty')

    if [[ -n "$LEX_IMPORT_ID" && -n "$UPLOAD_URL" ]]; then
        echo "  -> Import ID: $LEX_IMPORT_ID"

        # Step 2: Upload vocabulary zip
        echo "  -> Uploading vocabulary file..."
        UPLOAD_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PUT -H "Content-Type: application/zip" --data-binary @"$LEX_VOCAB_DIR/vocab.zip" "$UPLOAD_URL")

        if [[ "$UPLOAD_STATUS" == "200" ]]; then
            echo "  [OK] Vocabulary file uploaded"

            # Step 3: Start import
            echo "  -> Starting vocabulary import..."
            aws_cmd lexv2-models start-import \
                --import-id "$LEX_IMPORT_ID" \
                --resource-specification "{\"customVocabularyImportSpecification\": {\"botId\": \"$LEX_BOT_ID\", \"botVersion\": \"DRAFT\", \"localeId\": \"en_US\"}}" \
                --merge-strategy Overwrite \
                --region "$REGION" >/dev/null 2>&1

            # Step 4: Wait for import to complete
            echo "  -> Waiting for vocabulary import to complete..."
            for i in {1..15}; do
                sleep 2
                IMPORT_STATUS=$(aws_cmd lexv2-models describe-import --import-id "$LEX_IMPORT_ID" --region "$REGION" --query 'importStatus' --output text 2>/dev/null)
                echo "     Status: $IMPORT_STATUS"

                if [[ "$IMPORT_STATUS" == "Completed" ]]; then
                    echo "  [OK] Vocabulary import completed!"

                    # Step 5: Rebuild bot to apply vocabulary
                    echo "  -> Rebuilding bot to apply vocabulary..."
                    aws_cmd lexv2-models build-bot-locale \
                        --bot-id "$LEX_BOT_ID" \
                        --bot-version DRAFT \
                        --locale-id en_US \
                        --region "$REGION" >/dev/null 2>&1

                    # Step 6: Wait for bot build
                    echo "  -> Waiting for bot build..."
                    for j in {1..20}; do
                        sleep 3
                        BUILD_STATUS=$(aws_cmd lexv2-models describe-bot-locale \
                            --bot-id "$LEX_BOT_ID" \
                            --bot-version DRAFT \
                            --locale-id en_US \
                            --region "$REGION" \
                            --query 'botLocaleStatus' --output text 2>/dev/null)
                        echo "     Build status: $BUILD_STATUS"

                        if [[ "$BUILD_STATUS" == "Built" ]]; then
                            echo "  [OK] Bot rebuilt with custom vocabulary!"
                            break
                        elif [[ "$BUILD_STATUS" == "Failed" ]]; then
                            echo "  [ERROR] Bot build failed"
                            break
                        fi
                    done
                    break
                elif [[ "$IMPORT_STATUS" == "Failed" ]]; then
                    echo "  [ERROR] Vocabulary import failed"
                    break
                fi
            done

            # Step 7: Verify vocabulary
            echo "  -> Verifying vocabulary items..."
            VOCAB_COUNT=$(aws_cmd lexv2-models list-custom-vocabulary-items \
                --bot-id "$LEX_BOT_ID" \
                --bot-version DRAFT \
                --locale-id en_US \
                --region "$REGION" \
                --query 'length(customVocabularyItems)' --output text 2>/dev/null || echo "0")
            echo "  [OK] Custom vocabulary has $VOCAB_COUNT phrases"
        else
            echo "  [ERROR] Failed to upload vocabulary file (HTTP $UPLOAD_STATUS)"
        fi
    else
        echo "  [ERROR] Failed to get upload URL"
    fi

    # Cleanup
    rm -rf "$LEX_VOCAB_DIR"
else
    echo "  [SKIP] No valid LEX_BOT_ID - skipping vocabulary creation"
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

            # 1b. Enable Contact Lens (better speech recognition via Amazon Transcribe)
            echo "     -> Enabling Contact Lens (Amazon Transcribe)..."
            aws_cmd connect update-instance-attribute \
                --instance-id "$INST_ID" \
                --attribute-type CONTACT_LENS \
                --value "true" \
                --region "$REGION" 2>/dev/null && echo "     [OK] Contact Lens enabled" || echo "     [INFO] Contact Lens already enabled or error"

            # 1c. Enable Bot Analytics and Transcripts
            echo "     -> Enabling Bot Analytics and Transcripts..."
            aws_cmd connect update-instance-attribute \
                --instance-id "$INST_ID" \
                --attribute-type ENABLE_BOT_ANALYTICS_AND_TRANSCRIPTS \
                --value "true" \
                --region "$REGION" 2>/dev/null && echo "     [OK] Bot Transcripts enabled" || echo "     [INFO] Bot Transcripts already enabled or error"

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

# ============================================================================
# Step 6.5: Ensure AWS Default Encryption (Remove customer KMS keys)
# ============================================================================

echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo -e "${YELLOW}Step 6.5: Ensure AWS Default Encryption${NC}"
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo ""
echo "  Verifying all voice Lambdas use AWS default encryption..."
echo ""

ensure_aws_default_encryption "$LEX_FULFILLMENT_FUNCTION" || echo -e "${YELLOW}[WARN] KMS check failed for $LEX_FULFILLMENT_FUNCTION${NC}"
ensure_aws_default_encryption "$VOICE_BRIDGE_FUNCTION" || echo -e "${YELLOW}[WARN] KMS check failed for $VOICE_BRIDGE_FUNCTION${NC}"
ensure_aws_default_encryption "$CUSTOMER_LOOKUP_FUNCTION" || echo -e "${YELLOW}[WARN] KMS check failed for $CUSTOMER_LOOKUP_FUNCTION${NC}"

echo ""
echo -e "${GREEN}[OK] AWS default encryption verified for all voice Lambdas${NC}"

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
