#!/bin/bash

# ============================================================================
# ProjectForce Advanced Voice Cleanup Script
# ============================================================================
# Purpose: Remove all voice Lambda functions and IAM roles
# Features: Proper IAM policy detachment, safe deletion, cross-platform
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

# IAM role names
LEX_FULFILLMENT_ROLE="pf-lex-fulfillment-role-${ENVIRONMENT}"
VOICE_BRIDGE_ROLE="pf-voice-bedrock-bridge-role-${ENVIRONMENT}"

# CloudWatch Log Groups
LEX_FULFILLMENT_LOG_GROUP="/aws/lambda/${LEX_FULFILLMENT_FUNCTION}"
VOICE_BRIDGE_LOG_GROUP="/aws/lambda/${VOICE_BRIDGE_FUNCTION}"

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

    echo -n "  → Checking $FUNCTION_NAME... "

    # Check if function exists
    if aws_cmd lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" &>/dev/null; then
        echo ""
        echo "  → Deleting $FUNCTION_NAME..."

        if aws_cmd lambda delete-function \
            --function-name "$FUNCTION_NAME" \
            --region "$REGION" 2>&1 | tee "./lambda-delete-$FUNCTION_NAME.log"; then
            echo -e "  ${GREEN}✓${NC} Deleted $FUNCTION_NAME"
        else
            echo -e "  ${RED}⊘${NC} Failed to delete $FUNCTION_NAME"
        fi
    else
        echo -e "${CYAN}⊘${NC} does not exist"
    fi
}

# Delete IAM role with proper policy detachment
delete_iam_role() {
    local ROLE_NAME=$1

    echo -n "  → Checking $ROLE_NAME... "

    # Check if role exists
    if aws_cmd iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
        echo ""
        echo "  → Deleting $ROLE_NAME..."

        # Step 1: Detach all attached managed policies
        echo "    → Detaching managed policies..."
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
            echo "    ✓ Managed policies detached"
        else
            echo "    ℹ️  No managed policies to detach"
        fi

        # Step 2: Delete all inline policies
        echo "    → Deleting inline policies..."
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
            echo "    ✓ Inline policies deleted"
        else
            echo "    ℹ️  No inline policies to delete"
        fi

        # Step 3: Delete the role itself
        echo "    → Deleting role..."
        if aws_cmd iam delete-role --role-name "$ROLE_NAME" &>/dev/null; then
            echo -e "  ${GREEN}✓${NC} Deleted $ROLE_NAME"
        else
            echo -e "  ${RED}⊘${NC} Failed to delete $ROLE_NAME"
        fi
    else
        echo -e "${CYAN}⊘${NC} does not exist"
    fi
}

# Delete CloudWatch Log Group
delete_log_group() {
    local LOG_GROUP=$1

    echo -n "  → Checking $LOG_GROUP... "

    # Check if log group exists
    if aws_cmd logs describe-log-groups \
        --log-group-name-prefix "$LOG_GROUP" \
        --region "$REGION" \
        --query 'logGroups[0].logGroupName' \
        --output text 2>/dev/null | grep -q "$LOG_GROUP"; then

        echo ""
        echo "  → Deleting $LOG_GROUP..."

        if aws_cmd logs delete-log-group \
            --log-group-name "$LOG_GROUP" \
            --region "$REGION" 2>&1 | tee "./log-delete-$(basename $LOG_GROUP).log"; then
            echo -e "  ${GREEN}✓${NC} Deleted $LOG_GROUP"
        else
            echo -e "  ${RED}⊘${NC} Failed to delete $LOG_GROUP"
        fi
    else
        echo -e "${CYAN}⊘${NC} does not exist"
    fi
}

# ============================================================================
# Main Cleanup
# ============================================================================

echo -e "${RED}════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${RED}🧹 ProjectForce Advanced Voice Cleanup Script${NC}"
echo -e "${RED}════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Account: $(get_account_id)"
echo "Region: $REGION"
echo ""
echo -e "${YELLOW}WARNING: This will delete:${NC}"
echo "  - Lambda functions: $LEX_FULFILLMENT_FUNCTION, $VOICE_BRIDGE_FUNCTION"
echo "  - IAM roles: $LEX_FULFILLMENT_ROLE, $VOICE_BRIDGE_ROLE"
echo "  - CloudWatch Log Groups for both functions"
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

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 1: Deleting Lambda Functions${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

delete_lambda_function "$LEX_FULFILLMENT_FUNCTION"
delete_lambda_function "$VOICE_BRIDGE_FUNCTION"

echo ""

# ============================================================================
# Step 2: Delete IAM Roles
# ============================================================================

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 2: Deleting IAM Roles${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

delete_iam_role "$LEX_FULFILLMENT_ROLE"
delete_iam_role "$VOICE_BRIDGE_ROLE"

echo ""

# ============================================================================
# Step 3: Delete CloudWatch Log Groups
# ============================================================================

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 3: Deleting CloudWatch Log Groups${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

delete_log_group "$LEX_FULFILLMENT_LOG_GROUP"
delete_log_group "$VOICE_BRIDGE_LOG_GROUP"

echo ""

# ============================================================================
# Step 4: Clean up local deployment files
# ============================================================================

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 4: Cleaning up local files${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Remove Lambda deployment packages
echo "  → Removing Lambda deployment packages..."

if [ -d "lambda/lex-fulfillment" ]; then
    rm -f lambda/lex-fulfillment/function.zip
    rm -rf lambda/lex-fulfillment/package
    echo "  ✓ Removed: lambda/lex-fulfillment/function.zip"
fi

if [ -d "lambda/voice-bedrock-bridge" ]; then
    rm -f lambda/voice-bedrock-bridge/function.zip
    rm -rf lambda/voice-bedrock-bridge/package
    echo "  ✓ Removed: lambda/voice-bedrock-bridge/function.zip"
fi

# Remove log files from current directory
echo "  → Removing log files..."
rm -f ./lambda-*.log
rm -f ./iam-*.log
rm -f ./log-*.log
rm -f ./pip-install-*.log
rm -f ./trust-policy-*.json
rm -f ./policy-*.json
echo "  ✓ Removed: All cleanup log files"

echo ""

# ============================================================================
# Cleanup Summary
# ============================================================================

echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Cleanup Complete!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

echo "What was deleted:"
echo "  ✅ Lambda Functions (2):"
echo "     - $LEX_FULFILLMENT_FUNCTION"
echo "     - $VOICE_BRIDGE_FUNCTION"
echo ""
echo "  ✅ IAM Roles (2):"
echo "     - $LEX_FULFILLMENT_ROLE"
echo "     - $VOICE_BRIDGE_ROLE"
echo ""
echo "  ✅ CloudWatch Log Groups (2):"
echo "     - $LEX_FULFILLMENT_LOG_GROUP"
echo "     - $VOICE_BRIDGE_LOG_GROUP"
echo ""
echo "  ✅ Local deployment files and logs"
echo ""

echo -e "${CYAN}What remains unchanged:${NC}"
echo "  ✅ Lex bot configuration (if deployed)"
echo "  ✅ AWS Connect instance (if deployed)"
echo "  ✅ Phone number configuration (if claimed)"
echo "  ✅ DynamoDB tables"
echo "  ✅ Secrets Manager secrets"
echo ""

echo -e "${GREEN}Voice Lambda cleanup completed successfully!${NC}"
echo ""
echo "To redeploy, run: ./scripts/DEPLOY_VOICE_ADVANCED.sh"
echo ""
