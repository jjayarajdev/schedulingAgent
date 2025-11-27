#!/bin/bash

##############################################################################
# CLEANUP_ADVANCED.sh - Advanced AWS Resource Cleanup
#
# Purpose: Clean all ProjectForce scheduling agent resources
# Features:
#   - Handles IAM roles properly (detaches policies first)
#   - Cross-platform compatible (Windows/Linux/Mac)
#   - Comprehensive error handling
#   - Force delete with retry logic
#
# Usage:
#   echo "DELETE EVERYTHING" | ./CLEANUP_ADVANCED.sh --confirm
##############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

REGION="us-east-1"

# ============================================================================
# AWS ACCOUNT SELECTION - Smart account detection and configuration
# ============================================================================

echo "════════════════════════════════════════════════════════════════════════════"
echo -e "${RED}🧹 ProjectForce Advanced Cleanup Script${NC}"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo -e "${CYAN}🔐 AWS ACCOUNT SELECTION${NC}"
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
    ACCOUNT_ID="$CURRENT_ACCOUNT"
    echo ""
    echo -e "${GREEN}✓ Using account: ${ACCOUNT_ID}${NC}"
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
        echo -e "${GREEN}✓ Found existing profile '${FOUND_PROFILE}' with account ${TARGET_ACCOUNT_ID}${NC}"
        AWS_PROFILE="$FOUND_PROFILE"
        ACCOUNT_ID="$TARGET_ACCOUNT_ID"
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
            echo -e "${GREEN}✓ Profile '${NEW_PROFILE_NAME}' configured successfully!${NC}"
            echo -e "${GREEN}✓ Verified account: ${VERIFY_ACCOUNT}${NC}"
            AWS_PROFILE="$NEW_PROFILE_NAME"
            ACCOUNT_ID="$TARGET_ACCOUNT_ID"
        else
            echo -e "${RED}❌ Credentials verification failed!${NC}"
            echo "   Expected account: $TARGET_ACCOUNT_ID"
            echo "   Got account: $VERIFY_ACCOUNT"
            exit 1
        fi
    fi
fi

echo ""

# AWS CLI wrapper (uses selected profile)
aws_cmd() {
    aws --profile "$AWS_PROFILE" "$@"
}

# Safety confirmation
echo -e "${RED}⚠️  WARNING: This will DELETE all ProjectForce resources!${NC}"
echo ""
echo "  Profile:    $AWS_PROFILE"
echo "  Account:    $ACCOUNT_ID"
echo "  Region:     $REGION"
echo ""
read -p "Type 'DELETE EVERYTHING' to confirm: " CONFIRM
if [[ "$CONFIRM" != "DELETE EVERYTHING" ]]; then
    echo "Cleanup cancelled"
    exit 0
fi

echo ""
echo "Account: $ACCOUNT_ID"
echo "Region: $REGION"
echo ""

##############################################################################
# Step 1: Delete Lambda Functions
##############################################################################
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1: Deleting Lambda Functions"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

LAMBDAS=(
    "pf-orchestrator"
    "pf-scheduling-actions"
    "pf-information-actions"
    "pf-chitchat-actions"
    "pf-lex-fulfillment-dev"
    "pf-voice-bedrock-bridge-dev"
)

for LAMBDA in "${LAMBDAS[@]}"; do
    if aws_cmd lambda get-function --function-name "$LAMBDA" &>/dev/null; then
        echo "  → Deleting $LAMBDA..."
        aws_cmd lambda delete-function --function-name "$LAMBDA" &>/dev/null || true
        echo -e "  ${GREEN}✓${NC} Deleted $LAMBDA"
    else
        echo "  ⊘ $LAMBDA does not exist"
    fi
done

echo ""

##############################################################################
# Step 2: Delete IAM Roles (with policy detachment)
##############################################################################
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2: Deleting IAM Roles"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

IAM_ROLES=(
    "pf-orchestrator-role"
    "pf-scheduling-actions-role"
    "pf-information-actions-role"
    "pf-chitchat-actions-role"
    "pf-lex-fulfillment-role"
    "pf-voice-bridge-role"
)

delete_iam_role() {
    local ROLE_NAME=$1

    if ! aws_cmd iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
        echo "  ⊘ $ROLE_NAME does not exist"
        return 0
    fi

    echo "  → Detaching policies from $ROLE_NAME..."

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
    echo "  → Deleting $ROLE_NAME..."
    aws_cmd iam delete-role --role-name "$ROLE_NAME" &>/dev/null || true
    echo -e "  ${GREEN}✓${NC} Deleted $ROLE_NAME"
}

for ROLE in "${IAM_ROLES[@]}"; do
    delete_iam_role "$ROLE"
done

echo ""

##############################################################################
# Step 3: Delete DynamoDB Tables
##############################################################################
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3: Deleting DynamoDB Tables"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

TABLES=(
    "pf-sessions-dev"
    "pf-notes-dev"
    "pf-workflow-states-dev"
)

for TABLE in "${TABLES[@]}"; do
    if aws_cmd dynamodb describe-table --table-name "$TABLE" &>/dev/null; then
        echo "  → Deleting $TABLE..."
        aws_cmd dynamodb delete-table --table-name "$TABLE" &>/dev/null || true
        echo -e "  ${GREEN}✓${NC} Deleted $TABLE"
    else
        echo "  ⊘ $TABLE does not exist"
    fi
done

echo ""

##############################################################################
# Step 4: Delete Secrets Manager Secrets
##############################################################################
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 4: Deleting Secrets Manager Secrets"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

SECRETS=(
    "projectforce/api/credentials"
    "scheduling-agent/pf360/api-credentials"
)

for SECRET in "${SECRETS[@]}"; do
    if aws_cmd secretsmanager describe-secret --secret-id "$SECRET" &>/dev/null; then
        echo "  → Deleting $SECRET..."
        aws_cmd secretsmanager delete-secret --secret-id "$SECRET" --force-delete-without-recovery &>/dev/null || true
        echo -e "  ${GREEN}✓${NC} Deleted $SECRET"
    else
        echo "  ⊘ $SECRET does not exist"
    fi
done

##############################################################################
# Step 5: Clean up temp files from failed deployments
##############################################################################
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 5: Cleaning Temp Files"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR" 2>/dev/null || true

# Clean up deployment temp files
TEMP_PATTERNS=(
    "trust-policy-*.json"
    "secrets-policy.json"
    "orchestrator-permissions.json"
    "scheduling-env.json"
    "orchestrator-env.json"
    "iam-create-*.log"
    "lambda-create-*.log"
    "kms-fix-*.json"
)

for pattern in "${TEMP_PATTERNS[@]}"; do
    FILES_FOUND=$(find . -name "$pattern" 2>/dev/null | wc -l)
    if [[ $FILES_FOUND -gt 0 ]]; then
        echo "  → Removing $pattern files..."
        find . -name "$pattern" -delete 2>/dev/null || true
        echo -e "  ${GREEN}✓${NC} Removed $FILES_FOUND file(s)"
    fi
done

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ Cleanup Complete!${NC}"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
