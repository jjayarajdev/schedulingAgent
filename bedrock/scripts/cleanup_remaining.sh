#!/bin/bash

# Quick cleanup of remaining resources
REGION="us-east-1"

echo "Cleaning up remaining resources..."
echo ""

# Delete KMS Alias
echo "Deleting KMS alias..."
aws kms delete-alias \
  --alias-name alias/pf-connect-recordings-dev \
  --region "$REGION" 2>/dev/null && echo "✅ KMS alias deleted" || echo "⚠️  KMS alias not found"

# Delete IAM Roles
echo ""
echo "Deleting IAM roles..."

IAM_ROLES=("pf-lex-fulfillment-role-dev" "pf-voice-bedrock-bridge-role-dev" "pf-lex-bot-role-dev")

for ROLE_NAME in "${IAM_ROLES[@]}"; do
    echo "  Processing: $ROLE_NAME"

    # Detach managed policies
    POLICIES=$(aws iam list-attached-role-policies --role-name "$ROLE_NAME" --query 'AttachedPolicies[*].PolicyArn' --output text 2>/dev/null || echo "")
    if [ -n "$POLICIES" ]; then
        for POLICY_ARN in $POLICIES; do
            aws iam detach-role-policy --role-name "$ROLE_NAME" --policy-arn "$POLICY_ARN" 2>/dev/null || true
        done
    fi

    # Delete inline policies
    INLINE_POLICIES=$(aws iam list-role-policies --role-name "$ROLE_NAME" --query 'PolicyNames[*]' --output text 2>/dev/null || echo "")
    if [ -n "$INLINE_POLICIES" ]; then
        for POLICY_NAME in $INLINE_POLICIES; do
            aws iam delete-role-policy --role-name "$ROLE_NAME" --policy-name "$POLICY_NAME" 2>/dev/null || true
        done
    fi

    # Delete role
    aws iam delete-role --role-name "$ROLE_NAME" 2>/dev/null && echo "  ✅ Deleted: $ROLE_NAME" || echo "  ⚠️  Failed: $ROLE_NAME"
done

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "Now run: ./DEPLOY_VOICE_FULL.sh"
