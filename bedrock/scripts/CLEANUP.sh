#!/bin/bash

##############################################################################
# CLEANUP.sh - Delete all ProjectForce Bedrock agents and Lambda functions
#
# Purpose: Clean slate for rebuilding 4-agent architecture
# Date: 2025-11-04
#
# WARNING: This will delete:
#   - All 4 Bedrock agents
#   - 2 Lambda functions (scheduling, information)
#   - Associated IAM roles (optional)
#   - Action groups and aliases
#
# Usage: ./CLEANUP.sh [--delete-roles]
##############################################################################

set -e  # Exit on error

REGION="us-east-1"
DELETE_ROLES=false

# Parse arguments
if [[ "$1" == "--delete-roles" ]]; then
    DELETE_ROLES=true
fi

echo "=========================================="
echo "ProjectForce Cleanup Script"
echo "=========================================="
echo ""
echo "⚠️  WARNING: This will delete all agents and Lambda functions!"
echo ""
read -p "Are you sure you want to continue? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Cleanup cancelled."
    exit 0
fi

##############################################################################
# 1. Delete Bedrock Agents
##############################################################################

echo ""
echo "=========================================="
echo "Step 1: Deleting Bedrock Agents"
echo "=========================================="

# Dynamically fetch all agents (safer than hardcoding IDs)
echo "Fetching all Bedrock agents..."
AGENT_LIST=$(aws bedrock-agent list-agents --region "$REGION" --query 'agentSummaries[*].[agentId,agentName]' --output text 2>/dev/null || echo "")

if [ -z "$AGENT_LIST" ]; then
    echo "  ℹ️  No agents found to delete"
else
    echo "$AGENT_LIST" | while read -r AGENT_ID AGENT_NAME; do
        echo ""
        echo "Deleting agent: $AGENT_NAME (ID: $AGENT_ID)"

        # Delete all agent aliases first
        echo "  Deleting aliases for $AGENT_NAME..."
        ALIASES=$(aws bedrock-agent list-agent-aliases \
            --agent-id "$AGENT_ID" \
            --region "$REGION" \
            --query 'agentAliasSummaries[*].agentAliasId' \
            --output text 2>/dev/null || echo "")

        if [ -n "$ALIASES" ]; then
            for ALIAS_ID in $ALIASES; do
                if [ "$ALIAS_ID" != "TSTALIASID" ]; then
                    aws bedrock-agent delete-agent-alias \
                        --agent-id "$AGENT_ID" \
                        --agent-alias-id "$ALIAS_ID" \
                        --region "$REGION" &>/dev/null || true
                    echo "    ✅ Deleted alias: $ALIAS_ID"
                fi
            done
        fi

        # Delete the agent
        aws bedrock-agent delete-agent \
            --agent-id "$AGENT_ID" \
            --region "$REGION" \
            --skip-resource-in-use-check \
            &>/dev/null && echo "  ✅ Agent deleted: $AGENT_NAME" || echo "  ⚠️  Failed to delete agent: $AGENT_NAME"
    done
fi

##############################################################################
# 2. Delete Lambda Functions
##############################################################################

echo ""
echo "=========================================="
echo "Step 2: Deleting Lambda Functions"
echo "=========================================="

LAMBDA_FUNCTIONS=(
    "pf-scheduling-actions"
    "pf-information-actions"
)

for FUNCTION_NAME in "${LAMBDA_FUNCTIONS[@]}"; do
    echo ""
    echo "Deleting Lambda function: $FUNCTION_NAME"

    # Check if function exists
    if aws lambda get-function \
        --function-name "$FUNCTION_NAME" \
        --region "$REGION" \
        &>/dev/null; then

        # Delete the function
        aws lambda delete-function \
            --function-name "$FUNCTION_NAME" \
            --region "$REGION" \
            2>/dev/null && echo "  ✅ Lambda deleted: $FUNCTION_NAME" || echo "  ⚠️  Failed to delete Lambda: $FUNCTION_NAME"
    else
        echo "  ℹ️  Lambda not found (may already be deleted): $FUNCTION_NAME"
    fi
done

##############################################################################
# 3. Delete IAM Roles (Optional)
##############################################################################

if [[ "$DELETE_ROLES" == true ]]; then
    echo ""
    echo "=========================================="
    echo "Step 3: Deleting IAM Roles"
    echo "=========================================="

    IAM_ROLES=(
        # Bedrock agent roles (current 4-agent architecture)
        "pf_scheduling_agent_role"
        "pf_chitchat_agent_role"
        "pf_information_agent_role"
        "pf_supervisor_agent_role"
        # Lambda roles (only 2 - chitchat has no Lambda)
        "pf-scheduling-lambda-role"
        "pf-information-lambda-role"
    )

    for ROLE_NAME in "${IAM_ROLES[@]}"; do
        echo ""
        echo "Deleting IAM role: $ROLE_NAME"

        # Check if role exists
        if aws iam get-role \
            --role-name "$ROLE_NAME" \
            &>/dev/null; then

            # Detach all managed policies
            echo "  → Detaching managed policies..."
            POLICIES=$(aws iam list-attached-role-policies \
                --role-name "$ROLE_NAME" \
                --query 'AttachedPolicies[*].PolicyArn' \
                --output text 2>/dev/null || echo "")

            if [[ -n "$POLICIES" ]]; then
                for POLICY_ARN in $POLICIES; do
                    echo "  → Detaching policy: $POLICY_ARN"
                    aws iam detach-role-policy \
                        --role-name "$ROLE_NAME" \
                        --policy-arn "$POLICY_ARN" \
                        2>/dev/null || echo "    ⚠️  Failed to detach policy"
                done
            fi

            # Delete inline policies
            echo "  → Deleting inline policies..."
            INLINE_POLICIES=$(aws iam list-role-policies \
                --role-name "$ROLE_NAME" \
                --query 'PolicyNames[*]' \
                --output text 2>/dev/null || echo "")

            if [[ -n "$INLINE_POLICIES" ]]; then
                for POLICY_NAME in $INLINE_POLICIES; do
                    echo "  → Deleting inline policy: $POLICY_NAME"
                    aws iam delete-role-policy \
                        --role-name "$ROLE_NAME" \
                        --policy-name "$POLICY_NAME" \
                        2>/dev/null || echo "    ⚠️  Failed to delete inline policy"
                done
            fi

            # Delete the role
            echo "  → Deleting role..."
            aws iam delete-role \
                --role-name "$ROLE_NAME" \
                2>/dev/null && echo "  ✅ Role deleted: $ROLE_NAME" || echo "  ⚠️  Failed to delete role: $ROLE_NAME"
        else
            echo "  ℹ️  Role not found (may already be deleted): $ROLE_NAME"
        fi
    done
else
    echo ""
    echo "ℹ️  Skipping IAM role deletion (use --delete-roles to delete)"
fi

##############################################################################
# 4. Delete Secrets Manager
##############################################################################

echo ""
echo "=========================================="
echo "Step 4: Deleting Secrets Manager"
echo "=========================================="

SECRETS=(
    "projectforce/api/dev/credentials"
)

for SECRET_NAME in "${SECRETS[@]}"; do
    echo ""
    echo "Deleting secret: $SECRET_NAME"

    if aws secretsmanager describe-secret \
        --secret-id "$SECRET_NAME" \
        --region "$REGION" \
        &>/dev/null; then

        aws secretsmanager delete-secret \
            --secret-id "$SECRET_NAME" \
            --region "$REGION" \
            --force-delete-without-recovery \
            &>/dev/null && echo "  ✅ Secret deleted: $SECRET_NAME" || echo "  ⚠️  Failed to delete secret: $SECRET_NAME"
    else
        echo "  ℹ️  Secret not found (may already be deleted): $SECRET_NAME"
    fi
done

##############################################################################
# 5. Delete DynamoDB Tables
##############################################################################

echo ""
echo "=========================================="
echo "Step 5: Deleting DynamoDB Tables"
echo "=========================================="

DYNAMODB_TABLES=(
    "pf-sessions-dev"
    "pf-notes-dev"
)

for TABLE_NAME in "${DYNAMODB_TABLES[@]}"; do
    echo ""
    echo "Deleting DynamoDB table: $TABLE_NAME"

    if aws dynamodb describe-table \
        --table-name "$TABLE_NAME" \
        --region "$REGION" \
        &>/dev/null; then

        aws dynamodb delete-table \
            --table-name "$TABLE_NAME" \
            --region "$REGION" \
            &>/dev/null && echo "  ✅ Table deleted: $TABLE_NAME" || echo "  ⚠️  Failed to delete table: $TABLE_NAME"
    else
        echo "  ℹ️  Table not found (may already be deleted): $TABLE_NAME"
    fi
done

##############################################################################
# Summary
##############################################################################

echo ""
echo "=========================================="
echo "Cleanup Complete!"
echo "=========================================="
echo ""
echo "Deleted:"
echo "  ✅ 4 Bedrock agents"
echo "  ✅ 2 Lambda functions (scheduling, information)"
if [[ "$DELETE_ROLES" == true ]]; then
    echo "  ✅ IAM roles (6 roles: 4 agent + 2 Lambda)"
else
    echo "  ℹ️  IAM roles (kept - use --delete-roles to delete)"
fi
echo "  ✅ Secrets Manager secret"
echo "  ✅ DynamoDB tables (2 tables)"
echo ""
echo "AWS Status:"
echo "  ✅ All ProjectForce resources deleted"
echo "  ✅ Clean slate ready for rebuild"
echo ""
echo "Next Steps:"
echo "  1. Review FINAL_AGENT_ARCHITECTURE.md"
echo "  2. Run: ./scripts/DEPLOY.sh"
echo "  3. Test with: python3 test_deployment.py"
echo ""
echo "=========================================="
