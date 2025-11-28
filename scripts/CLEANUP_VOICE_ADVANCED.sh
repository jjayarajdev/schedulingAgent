#!/bin/bash

# ============================================================================
# ProjectForce Advanced Voice Cleanup Script
# ============================================================================
# Purpose: Remove all voice Lambda functions and IAM roles
# Features: Proper IAM policy detachment, safe deletion, cross-platform
# ============================================================================

# Error handling - DO NOT use set -e (causes immediate exit)
# Using explicit error handling with || true

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

echo -e "${RED}============================================================================${NC}"
echo -e "${RED}[CLEAN] ProjectForce Advanced Voice Cleanup Script${NC}"
echo -e "${RED}============================================================================${NC}"
echo ""
echo -e "${CYAN}[AUTH] AWS ACCOUNT SELECTION${NC}"
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

# Lambda function names
LEX_FULFILLMENT_FUNCTION="pf-lex-fulfillment-${ENVIRONMENT}"
VOICE_BRIDGE_FUNCTION="pf-voice-bedrock-bridge-${ENVIRONMENT}"
CUSTOMER_LOOKUP_FUNCTION="pf-customer-lookup-${ENVIRONMENT}"

# IAM role names
LEX_FULFILLMENT_ROLE="pf-lex-fulfillment-role-${ENVIRONMENT}"
VOICE_BRIDGE_ROLE="pf-voice-bedrock-bridge-role-${ENVIRONMENT}"
CUSTOMER_LOOKUP_ROLE="pf-customer-lookup-role-${ENVIRONMENT}"

# CloudWatch Log Groups
LEX_FULFILLMENT_LOG_GROUP="/aws/lambda/${LEX_FULFILLMENT_FUNCTION}"
VOICE_BRIDGE_LOG_GROUP="/aws/lambda/${VOICE_BRIDGE_FUNCTION}"
CUSTOMER_LOOKUP_LOG_GROUP="/aws/lambda/${CUSTOMER_LOOKUP_FUNCTION}"

# DynamoDB Tables
CUSTOMER_TABLE="pf-customers-${ENVIRONMENT}"

# ============================================================================
# Helper Functions
# ============================================================================

# AWS command wrapper
aws_cmd() {
    aws "$@"
}

# Get AWS account ID
get_account_id() {
    aws_cmd sts get-caller-identity --query Account --output text 2>&1
}

# Delete Lambda function
delete_lambda_function() {
    local FUNCTION_NAME=$1

    echo -n "  -> Checking $FUNCTION_NAME... "

    # Check if function exists
    if aws_cmd lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" &>/dev/null; then
        echo ""
        echo "  -> Deleting $FUNCTION_NAME..."

        if aws_cmd lambda delete-function \
            --function-name "$FUNCTION_NAME" \
            --region "$REGION" 2>&1 | tee "./lambda-delete-$FUNCTION_NAME.log"; then
            echo -e "  ${GREEN}[OK]${NC} Deleted $FUNCTION_NAME"
        else
            echo -e "  ${RED}[-]${NC} Failed to delete $FUNCTION_NAME"
        fi
    else
        echo -e "${CYAN}[-]${NC} does not exist"
    fi
}

# Delete IAM role with proper policy detachment
delete_iam_role() {
    local ROLE_NAME=$1

    echo -n "  -> Checking $ROLE_NAME... "

    # Check if role exists
    if aws_cmd iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
        echo ""
        echo "  -> Deleting $ROLE_NAME..."

        # Step 1: Detach all attached managed policies
        echo "    -> Detaching managed policies..."
        ATTACHED_POLICIES=$(aws_cmd iam list-attached-role-policies \
            --role-name "$ROLE_NAME" \
            --query 'AttachedPolicies[].PolicyArn' \
            --output text 2>/dev/null || echo "")

        if [ -n "$ATTACHED_POLICIES" ]; then
            for POLICY_ARN in $ATTACHED_POLICIES; do
                echo "      Detaching: $(basename $POLICY_ARN)"
                aws_cmd iam detach-role-policy \
                    --role-name "$ROLE_NAME" \
                    --policy-arn "$POLICY_ARN" &>/dev/null || true
            done
            echo "    [OK] Managed policies detached"
        else
            echo "    [INFO]  No managed policies to detach"
        fi

        # Step 2: Delete all inline policies
        echo "    -> Deleting inline policies..."
        INLINE_POLICIES=$(aws_cmd iam list-role-policies \
            --role-name "$ROLE_NAME" \
            --query 'PolicyNames[]' \
            --output text 2>/dev/null || echo "")

        if [ -n "$INLINE_POLICIES" ]; then
            for POLICY_NAME in $INLINE_POLICIES; do
                echo "      Deleting: $POLICY_NAME"
                aws_cmd iam delete-role-policy \
                    --role-name "$ROLE_NAME" \
                    --policy-name "$POLICY_NAME" &>/dev/null || true
            done
            echo "    [OK] Inline policies deleted"
        else
            echo "    [INFO]  No inline policies to delete"
        fi

        # Step 3: Delete the role itself
        echo "    -> Deleting role..."
        if aws_cmd iam delete-role --role-name "$ROLE_NAME" &>/dev/null; then
            echo -e "  ${GREEN}[OK]${NC} Deleted $ROLE_NAME"
        else
            echo -e "  ${RED}[-]${NC} Failed to delete $ROLE_NAME"
        fi
    else
        echo -e "${CYAN}[-]${NC} does not exist"
    fi
}

# Delete CloudWatch Log Group
delete_log_group() {
    local LOG_GROUP=$1

    echo -n "  -> Checking $LOG_GROUP... "

    # Check if log group exists
    if aws_cmd logs describe-log-groups \
        --log-group-name-prefix "$LOG_GROUP" \
        --region "$REGION" \
        --query 'logGroups[0].logGroupName' \
        --output text 2>/dev/null | grep -q "$LOG_GROUP"; then

        echo ""
        echo "  -> Deleting $LOG_GROUP..."

        if aws_cmd logs delete-log-group \
            --log-group-name "$LOG_GROUP" \
            --region "$REGION" 2>&1 | tee "./log-delete-$(basename $LOG_GROUP).log"; then
            echo -e "  ${GREEN}[OK]${NC} Deleted $LOG_GROUP"
        else
            echo -e "  ${RED}[-]${NC} Failed to delete $LOG_GROUP"
        fi
    else
        echo -e "${CYAN}[-]${NC} does not exist"
    fi
}

# Delete DynamoDB Table
delete_dynamodb_table() {
    local TABLE_NAME=$1

    echo -n "  -> Checking $TABLE_NAME... "

    # Check if table exists
    if aws_cmd dynamodb describe-table --table-name "$TABLE_NAME" --region "$REGION" &>/dev/null; then
        echo ""
        echo "  -> Deleting $TABLE_NAME..."

        if aws_cmd dynamodb delete-table \
            --table-name "$TABLE_NAME" \
            --region "$REGION" 2>&1 | tee "./dynamodb-delete-$TABLE_NAME.log"; then
            echo -e "  ${GREEN}[OK]${NC} Deleted $TABLE_NAME"
        else
            echo -e "  ${RED}[-]${NC} Failed to delete $TABLE_NAME"
        fi
    else
        echo -e "${CYAN}[-]${NC} does not exist"
    fi
}

# ============================================================================
# Main Cleanup - Confirmation
# ============================================================================

echo -e "${YELLOW}WARNING: This will delete:${NC}"
echo "  - Lambda functions: $LEX_FULFILLMENT_FUNCTION, $VOICE_BRIDGE_FUNCTION, $CUSTOMER_LOOKUP_FUNCTION"
echo "  - IAM roles: $LEX_FULFILLMENT_ROLE, $VOICE_BRIDGE_ROLE, $CUSTOMER_LOOKUP_ROLE, pf-lex-bot-role-${ENVIRONMENT}"
echo "  - DynamoDB tables: $CUSTOMER_TABLE"
echo "  - Lex bot: pf-scheduling-assistant-${ENVIRONMENT}"
echo "  - CloudWatch Log Groups for all functions"
echo ""
echo -e "${RED}This action cannot be undone!${NC}"
echo ""
read -p "Are you sure you want to continue? (type 'yes' to confirm): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Cleanup cancelled"
    exit 0
fi

echo ""

# ============================================================================
# Step 1: Delete Lambda Functions
# ============================================================================

echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo -e "${YELLOW}Step 1: Deleting Lambda Functions${NC}"
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"

delete_lambda_function "$LEX_FULFILLMENT_FUNCTION"
delete_lambda_function "$VOICE_BRIDGE_FUNCTION"
delete_lambda_function "$CUSTOMER_LOOKUP_FUNCTION"

echo ""

# ============================================================================
# Step 2: Delete IAM Roles
# ============================================================================

echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo -e "${YELLOW}Step 2: Deleting IAM Roles${NC}"
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"

delete_iam_role "$LEX_FULFILLMENT_ROLE"
delete_iam_role "$VOICE_BRIDGE_ROLE"
delete_iam_role "$CUSTOMER_LOOKUP_ROLE"

echo ""

# ============================================================================
# Step 3: Delete CloudWatch Log Groups
# ============================================================================

echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo -e "${YELLOW}Step 3: Deleting CloudWatch Log Groups${NC}"
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"

delete_log_group "$LEX_FULFILLMENT_LOG_GROUP"
delete_log_group "$VOICE_BRIDGE_LOG_GROUP"
delete_log_group "$CUSTOMER_LOOKUP_LOG_GROUP"

echo ""

# ============================================================================
# Step 3.5: Delete DynamoDB Tables
# ============================================================================

echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo -e "${YELLOW}Step 3.5: Deleting DynamoDB Tables${NC}"
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"

delete_dynamodb_table "$CUSTOMER_TABLE"

echo ""

# ============================================================================
# Step 3.6: Delete Lex Bot
# ============================================================================

echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo -e "${YELLOW}Step 3.6: Deleting Lex Bot${NC}"
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"

LEX_BOT_NAME="pf-scheduling-assistant-${ENVIRONMENT}"
echo "  -> Checking for Lex bot: $LEX_BOT_NAME..."

LEX_BOT_ID=$(aws_cmd lexv2-models list-bots --region "$REGION" --query "botSummaries[?botName=='${LEX_BOT_NAME}'].botId" --output text 2>/dev/null || echo "")

if [[ -n "$LEX_BOT_ID" && "$LEX_BOT_ID" != "None" ]]; then
    echo "  -> Found bot ID: $LEX_BOT_ID"
    echo "  -> Deleting bot aliases..."

    # Delete all bot aliases first
    ALIAS_IDS=$(aws_cmd lexv2-models list-bot-aliases --bot-id "$LEX_BOT_ID" --region "$REGION" --query "botAliasSummaries[].botAliasId" --output text 2>/dev/null || echo "")
    for ALIAS_ID in $ALIAS_IDS; do
        if [[ -n "$ALIAS_ID" && "$ALIAS_ID" != "None" ]]; then
            echo "    Deleting alias: $ALIAS_ID"
            aws_cmd lexv2-models delete-bot-alias --bot-id "$LEX_BOT_ID" --bot-alias-id "$ALIAS_ID" --region "$REGION" --skip-resource-in-use-check &>/dev/null || true
        fi
    done

    echo "  -> Deleting bot..."
    if aws_cmd lexv2-models delete-bot --bot-id "$LEX_BOT_ID" --region "$REGION" --skip-resource-in-use-check &>/dev/null; then
        echo "  [OK] Deleted Lex bot: $LEX_BOT_NAME"
    else
        echo "  [WARN] Could not delete Lex bot (may still be in use)"
    fi
else
    echo "  [SKIP] Lex bot does not exist"
fi

# Delete Lex bot IAM role
LEX_BOT_ROLE_NAME="pf-lex-bot-role-${ENVIRONMENT}"
delete_iam_role "$LEX_BOT_ROLE_NAME"

echo ""

# ============================================================================
# Step 4: Clean up local deployment files
# ============================================================================

echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"
echo -e "${YELLOW}Step 4: Cleaning up local files${NC}"
echo -e "${YELLOW}----------------------------------------------------------------------------${NC}"

# Remove Lambda deployment packages
echo "  -> Removing Lambda deployment packages..."

if [ -d "lambda/lex-fulfillment" ]; then
    rm -f lambda/lex-fulfillment/function.zip
    rm -rf lambda/lex-fulfillment/package
    echo "  [OK] Removed: lambda/lex-fulfillment/function.zip"
fi

if [ -d "lambda/voice-bedrock-bridge" ]; then
    rm -f lambda/voice-bedrock-bridge/function.zip
    rm -rf lambda/voice-bedrock-bridge/package
    echo "  [OK] Removed: lambda/voice-bedrock-bridge/function.zip"
fi

if [ -d "lambda/customer-lookup" ]; then
    rm -f lambda/customer-lookup/function.zip
    rm -rf lambda/customer-lookup/package
    echo "  [OK] Removed: lambda/customer-lookup/function.zip"
fi

# Remove log files from current directory
echo "  -> Removing log files..."
rm -f ./lambda-*.log
rm -f ./iam-*.log
rm -f ./log-*.log
rm -f ./pip-install-*.log
rm -f ./trust-policy-*.json
rm -f ./policy-*.json
echo "  [OK] Removed: All cleanup log files"

# Clean up temp files from deployment (if any remain)
echo "  -> Cleaning deployment temp files..."
find . -name "trust-policy-*.json" -delete 2>/dev/null || true
find . -name "policy-*.json" -delete 2>/dev/null || true
echo "  [OK] Removed: All temp policy files"

echo ""

# ============================================================================
# Cleanup Summary
# ============================================================================

echo -e "${BLUE}============================================================================${NC}"
echo -e "${GREEN}[OK] Cleanup Complete!${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

echo "What was deleted:"
echo "  [OK] Lambda Functions (3):"
echo "     - $LEX_FULFILLMENT_FUNCTION"
echo "     - $VOICE_BRIDGE_FUNCTION"
echo "     - $CUSTOMER_LOOKUP_FUNCTION"
echo ""
echo "  [OK] IAM Roles (3):"
echo "     - $LEX_FULFILLMENT_ROLE"
echo "     - $VOICE_BRIDGE_ROLE"
echo "     - $CUSTOMER_LOOKUP_ROLE"
echo ""
echo "  [OK] DynamoDB Tables (1):"
echo "     - $CUSTOMER_TABLE"
echo ""
echo "  [OK] CloudWatch Log Groups (3):"
echo "     - $LEX_FULFILLMENT_LOG_GROUP"
echo "     - $VOICE_BRIDGE_LOG_GROUP"
echo "     - $CUSTOMER_LOOKUP_LOG_GROUP"
echo ""
echo "  [OK] Local deployment files and logs"
echo ""

echo -e "${CYAN}What remains unchanged:${NC}"
echo "  [OK] Lex bot configuration (if deployed)"
echo "  [OK] AWS Connect instance (if deployed)"
echo "  [OK] Phone number configuration (if claimed)"
echo "  [OK] Secrets Manager secrets"
echo ""

echo -e "${GREEN}Voice Lambda cleanup completed successfully!${NC}"
echo ""
echo "To redeploy, run: ./scripts/DEPLOY_VOICE_ADVANCED.sh"
echo ""
