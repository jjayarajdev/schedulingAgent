#!/bin/bash

# ============================================================================
# Complete Voice Resources Cleanup
# ============================================================================
# Purpose: Delete ALL voice-related resources before fresh deployment
# Account: 772634497954
# Region: us-east-1
# ============================================================================

set -e

REGION="us-east-1"
ACCOUNT_ID="772634497954"

echo "=============================================="
echo "Cleaning Up ALL Voice Resources"
echo "=============================================="
echo "Account: $ACCOUNT_ID"
echo "Region: $REGION"
echo ""

# ============================================================================
# 1. Delete Connect Instances
# ============================================================================

echo "Step 1: Deleting AWS Connect Instances..."
echo ""

INSTANCES=$(aws connect list-instances --region "$REGION" --query 'InstanceSummaryList[*].[Id,InstanceAlias]' --output text)

if [ -n "$INSTANCES" ]; then
    echo "$INSTANCES" | while read -r INSTANCE_ID INSTANCE_ALIAS; do
        echo "  Deleting: $INSTANCE_ALIAS ($INSTANCE_ID)"

        # Release phone numbers first
        PHONE_NUMBERS=$(aws connect list-phone-numbers-v2 \
            --target-arn "arn:aws:connect:${REGION}:${ACCOUNT_ID}:instance/${INSTANCE_ID}" \
            --region "$REGION" \
            --query 'ListPhoneNumbersSummaryList[*].PhoneNumberId' \
            --output text 2>/dev/null || echo "")

        if [ -n "$PHONE_NUMBERS" ]; then
            for PHONE_ID in $PHONE_NUMBERS; do
                echo "    Releasing phone: $PHONE_ID"
                aws connect release-phone-number \
                    --phone-number-id "$PHONE_ID" \
                    --region "$REGION" 2>/dev/null || true
            done
        fi

        # Delete instance
        aws connect delete-instance \
            --instance-id "$INSTANCE_ID" \
            --region "$REGION" 2>/dev/null && echo "  ✅ Deleted: $INSTANCE_ALIAS" || echo "  ⚠️  Failed to delete"
    done
else
    echo "  No Connect instances found"
fi

echo ""

# ============================================================================
# 2. Delete Lex Bots
# ============================================================================

echo "Step 2: Deleting Lex Bots..."
echo ""

BOTS=$(aws lexv2-models list-bots --region "$REGION" --query 'botSummaries[*].[botId,botName]' --output text)

if [ -n "$BOTS" ]; then
    echo "$BOTS" | while read -r BOT_ID BOT_NAME; do
        echo "  Deleting: $BOT_NAME ($BOT_ID)"
        aws lexv2-models delete-bot \
            --bot-id "$BOT_ID" \
            --region "$REGION" \
            --skip-resource-in-use-check 2>/dev/null && echo "  ✅ Deleted: $BOT_NAME" || echo "  ⚠️  Failed to delete"
    done
else
    echo "  No Lex bots found"
fi

echo ""

# ============================================================================
# 3. Delete Lambda Functions
# ============================================================================

echo "Step 3: Deleting Lambda Functions..."
echo ""

LAMBDAS=("pf-lex-fulfillment-dev" "pf-voice-bedrock-bridge-dev")

for LAMBDA_NAME in "${LAMBDAS[@]}"; do
    if aws lambda get-function --function-name "$LAMBDA_NAME" --region "$REGION" &>/dev/null; then
        echo "  Deleting: $LAMBDA_NAME"
        aws lambda delete-function \
            --function-name "$LAMBDA_NAME" \
            --region "$REGION" 2>/dev/null && echo "  ✅ Deleted: $LAMBDA_NAME" || echo "  ⚠️  Failed to delete"
    else
        echo "  Not found: $LAMBDA_NAME"
    fi
done

echo ""

# ============================================================================
# 4. Delete S3 Buckets
# ============================================================================

echo "Step 4: Deleting S3 Buckets..."
echo ""

S3_BUCKETS=$(aws s3 ls | grep "pf-call-recordings" | awk '{print $3}')

if [ -n "$S3_BUCKETS" ]; then
    for BUCKET in $S3_BUCKETS; do
        echo "  Emptying and deleting: $BUCKET"

        # Empty bucket
        aws s3 rm "s3://$BUCKET" --recursive --region "$REGION" 2>/dev/null || true

        # Delete all versions
        aws s3api list-object-versions \
            --bucket "$BUCKET" \
            --region "$REGION" 2>/dev/null | \
            jq -r '.Versions[]? | .Key + " " + .VersionId' | \
            while read key version; do
                aws s3api delete-object \
                    --bucket "$BUCKET" \
                    --key "$key" \
                    --version-id "$version" \
                    --region "$REGION" 2>/dev/null || true
            done

        # Delete bucket
        aws s3 rb "s3://$BUCKET" --region "$REGION" 2>/dev/null && echo "  ✅ Deleted: $BUCKET" || echo "  ⚠️  Failed to delete"
    done
else
    echo "  No S3 buckets found"
fi

echo ""

# ============================================================================
# 5. Delete DynamoDB Tables
# ============================================================================

echo "Step 5: Deleting DynamoDB Tables..."
echo ""

TABLES=$(aws dynamodb list-tables --region "$REGION" --query 'TableNames[*]' --output text | tr '\t' '\n' | grep "pf-session-data")

if [ -n "$TABLES" ]; then
    for TABLE in $TABLES; do
        echo "  Deleting: $TABLE"
        aws dynamodb delete-table \
            --table-name "$TABLE" \
            --region "$REGION" 2>/dev/null && echo "  ✅ Deleted: $TABLE" || echo "  ⚠️  Failed to delete"
    done
else
    echo "  No DynamoDB tables found"
fi

echo ""

# ============================================================================
# 6. Delete IAM Roles
# ============================================================================

echo "Step 6: Deleting IAM Roles..."
echo ""

IAM_ROLES=("pf-lex-fulfillment-role-dev" "pf-voice-bedrock-bridge-role-dev" "pf-lex-bot-role-dev")

for ROLE_NAME in "${IAM_ROLES[@]}"; do
    if aws iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
        echo "  Deleting: $ROLE_NAME"

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
        aws iam delete-role --role-name "$ROLE_NAME" 2>/dev/null && echo "  ✅ Deleted: $ROLE_NAME" || echo "  ⚠️  Failed to delete"
    else
        echo "  Not found: $ROLE_NAME"
    fi
done

echo ""

# ============================================================================
# 7. Delete KMS Keys
# ============================================================================

echo "Step 7: Scheduling KMS Keys for deletion..."
echo ""

KMS_ALIASES=$(aws kms list-aliases --region "$REGION" --query 'Aliases[?starts_with(AliasName, `alias/pf-connect`)].AliasName' --output text)

if [ -n "$KMS_ALIASES" ]; then
    for ALIAS in $KMS_ALIASES; do
        KEY_ID=$(aws kms describe-key --key-id "$ALIAS" --region "$REGION" --query 'KeyMetadata.KeyId' --output text 2>/dev/null || echo "")
        if [ -n "$KEY_ID" ]; then
            echo "  Scheduling deletion: $ALIAS"
            aws kms schedule-key-deletion \
                --key-id "$KEY_ID" \
                --pending-window-in-days 7 \
                --region "$REGION" 2>/dev/null && echo "  ✅ Scheduled: $ALIAS" || echo "  ⚠️  Failed"
        fi
    done
else
    echo "  No KMS keys found"
fi

echo ""

# ============================================================================
# 8. Delete CloudWatch Log Groups
# ============================================================================

echo "Step 8: Deleting CloudWatch Log Groups..."
echo ""

LOG_GROUPS=$(aws logs describe-log-groups --region "$REGION" --query 'logGroups[?contains(logGroupName, `pf-lex`) || contains(logGroupName, `pf-voice`)].logGroupName' --output text)

if [ -n "$LOG_GROUPS" ]; then
    for LOG_GROUP in $LOG_GROUPS; do
        echo "  Deleting: $LOG_GROUP"
        aws logs delete-log-group \
            --log-group-name "$LOG_GROUP" \
            --region "$REGION" 2>/dev/null && echo "  ✅ Deleted: $LOG_GROUP" || echo "  ⚠️  Failed to delete"
    done
else
    echo "  No log groups found"
fi

echo ""

# ============================================================================
# Summary
# ============================================================================

echo "=============================================="
echo "✅ Cleanup Complete!"
echo "=============================================="
echo ""
echo "All voice resources have been deleted."
echo "You can now run a fresh deployment:"
echo ""
echo "  ./DEPLOY_VOICE_FULL.sh"
echo ""
echo "New instance name will be: pf-schedule-voice-dev"
echo "Phone number: +1-833-877-1422"
echo ""
