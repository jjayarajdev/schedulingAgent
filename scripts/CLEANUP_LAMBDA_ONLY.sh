#!/bin/bash

##############################################################################
# CLEANUP_LAMBDA_ONLY.sh - Clean up Lambda-Only Architecture
#
# Purpose: Remove all Lambda functions and related resources
# Date: 2025-11-23
#
# Removes:
#   - 4 Lambda functions
#   - IAM roles for Lambdas
#   - DynamoDB tables (optional)
#   - Secrets Manager secret (optional)
#
# Usage:
#   ./CLEANUP_LAMBDA_ONLY.sh
#   ./CLEANUP_LAMBDA_ONLY.sh --profile pf-aws
#   ./CLEANUP_LAMBDA_ONLY.sh --keep-data  # Keep DynamoDB and secrets
##############################################################################

set -e

# AWS Profile Support
AWS_PROFILE="${AWS_PROFILE:-}"
KEEP_DATA=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            AWS_PROFILE="$2"
            shift 2
            ;;
        --keep-data)
            KEEP_DATA=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

aws_cmd() {
    if [[ -n "$AWS_PROFILE" ]]; then
        aws --profile "$AWS_PROFILE" "$@"
    else
        aws "$@"
    fi
}

REGION="us-east-1"
ACCOUNT_ID=$(aws_cmd sts get-caller-identity --query Account --output text)
ENV="dev"

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "ProjectForce Lambda-Only Cleanup"
echo "=========================================="
echo ""
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo ""

if [[ "$KEEP_DATA" == "true" ]]; then
    echo "⚠️  Data preservation mode: DynamoDB tables and secrets will NOT be deleted"
else
    echo "⚠️  WARNING: This will delete Lambda functions, DynamoDB tables, and secrets"
fi

echo ""
read -p "Are you sure you want to proceed? (yes/no): " CONFIRM

if [[ "$CONFIRM" != "yes" ]]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "Starting cleanup..."

##############################################################################
# Step 1: Delete Lambda Functions
##############################################################################

echo ""
echo "=========================================="
echo "Step 1: Lambda Functions"
echo "=========================================="

LAMBDA_FUNCTIONS=(
    "pf-orchestrator"
    "pf-scheduling-actions"
    "pf-information-actions"
    "pf-chitchat-actions"
)

for FUNCTION_NAME in "${LAMBDA_FUNCTIONS[@]}"; do
    echo ""
    echo "Deleting Lambda: $FUNCTION_NAME"

    if aws_cmd lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" &>/dev/null; then
        aws_cmd lambda delete-function \
            --function-name "$FUNCTION_NAME" \
            --region "$REGION" &>/dev/null
        echo "  ✅ Deleted: $FUNCTION_NAME"
    else
        echo "  ⚠️  Not found: $FUNCTION_NAME"
    fi
done

##############################################################################
# Step 2: Delete IAM Roles
##############################################################################

echo ""
echo "=========================================="
echo "Step 2: IAM Roles"
echo "=========================================="

IAM_ROLES=(
    "pf-orchestrator-role-${ENV}"
    "pf-scheduling-actions-role-${ENV}"
    "pf-information-actions-role-${ENV}"
    "pf-chitchat-actions-role-${ENV}"
)

for ROLE_NAME in "${IAM_ROLES[@]}"; do
    echo ""
    echo "Deleting IAM role: $ROLE_NAME"

    if aws_cmd iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
        # Delete inline policies
        INLINE_POLICIES=$(aws_cmd iam list-role-policies --role-name "$ROLE_NAME" --query 'PolicyNames[]' --output text 2>/dev/null || echo "")
        if [[ -n "$INLINE_POLICIES" ]]; then
            for POLICY in $INLINE_POLICIES; do
                aws_cmd iam delete-role-policy --role-name "$ROLE_NAME" --policy-name "$POLICY" &>/dev/null
                echo "  → Deleted inline policy: $POLICY"
            done
        fi

        # Detach managed policies
        ATTACHED_POLICIES=$(aws_cmd iam list-attached-role-policies --role-name "$ROLE_NAME" --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null || echo "")
        if [[ -n "$ATTACHED_POLICIES" ]]; then
            for POLICY_ARN in $ATTACHED_POLICIES; do
                aws_cmd iam detach-role-policy --role-name "$ROLE_NAME" --policy-arn "$POLICY_ARN" &>/dev/null
                echo "  → Detached policy: $(basename $POLICY_ARN)"
            done
        fi

        # Delete role
        aws_cmd iam delete-role --role-name "$ROLE_NAME" &>/dev/null
        echo "  ✅ Deleted: $ROLE_NAME"
    else
        echo "  ⚠️  Not found: $ROLE_NAME"
    fi
done

##############################################################################
# Step 3: Delete DynamoDB Tables (optional)
##############################################################################

if [[ "$KEEP_DATA" != "true" ]]; then
    echo ""
    echo "=========================================="
    echo "Step 3: DynamoDB Tables"
    echo "=========================================="

    TABLES=(
        "pf-sessions-dev"
        "pf-notes-dev"
        "pf-workflow-states-dev"
    )

    for TABLE in "${TABLES[@]}"; do
        echo ""
        echo "Deleting table: $TABLE"

        if aws_cmd dynamodb describe-table --table-name "$TABLE" --region "$REGION" &>/dev/null; then
            aws_cmd dynamodb delete-table --table-name "$TABLE" --region "$REGION" &>/dev/null
            echo "  ✅ Deleted: $TABLE"
        else
            echo "  ⚠️  Not found: $TABLE"
        fi
    done
fi

##############################################################################
# Step 4: Delete Secrets Manager Secret (optional)
##############################################################################

if [[ "$KEEP_DATA" != "true" ]]; then
    echo ""
    echo "=========================================="
    echo "Step 4: Secrets Manager"
    echo "=========================================="

    SECRET_NAME="projectforce/api/credentials"

    echo ""
    echo "Deleting secret: $SECRET_NAME"

    if aws_cmd secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$REGION" &>/dev/null; then
        # Delete immediately (no recovery)
        aws_cmd secretsmanager delete-secret \
            --secret-id "$SECRET_NAME" \
            --force-delete-without-recovery \
            --region "$REGION" &>/dev/null
        echo "  ✅ Deleted: $SECRET_NAME"
    else
        echo "  ⚠️  Not found: $SECRET_NAME"
    fi
fi

##############################################################################
# Summary
##############################################################################

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Cleanup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Deleted:"
echo "  ✅ 4 Lambda functions"
echo "  ✅ 4 IAM roles"

if [[ "$KEEP_DATA" != "true" ]]; then
    echo "  ✅ 3 DynamoDB tables"
    echo "  ✅ 1 Secrets Manager secret"
else
    echo "  ⚠️  Preserved: DynamoDB tables and secrets (--keep-data flag)"
fi

echo ""
echo "To re-deploy:"
echo "  ./DEPLOY_LAMBDA_ONLY.sh"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
