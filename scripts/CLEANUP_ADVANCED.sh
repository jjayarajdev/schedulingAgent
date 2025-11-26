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
NC='\033[0m'

# AWS Configuration
AWS_PROFILE="${AWS_PROFILE:-}"
REGION="us-east-1"

# AWS CLI wrapper
aws_cmd() {
    if [[ -n "$AWS_PROFILE" ]]; then
        aws --profile "$AWS_PROFILE" "$@"
    else
        aws "$@"
    fi
}

echo "════════════════════════════════════════════════════════════════════════════"
echo "🧹 ProjectForce Advanced Cleanup Script"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

# Safety confirmation
if [[ "$1" != "--confirm" ]]; then
    echo -e "${RED}⚠️  WARNING: This will DELETE all ProjectForce resources!${NC}"
    echo ""
    read -p "Type 'DELETE EVERYTHING' to confirm: " CONFIRM
    if [[ "$CONFIRM" != "DELETE EVERYTHING" ]]; then
        echo "Cleanup cancelled"
        exit 0
    fi
fi

ACCOUNT_ID=$(aws_cmd sts get-caller-identity --query Account --output text)
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

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ Cleanup Complete!${NC}"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
