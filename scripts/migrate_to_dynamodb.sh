#!/bin/bash

##############################################################################
# migrate_to_dynamodb.sh - Update DEPLOY.sh to use DynamoDB instead of Redis
##############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_FILE="$SCRIPT_DIR/DEPLOY.sh"
BACKUP_FILE="$SCRIPT_DIR/DEPLOY.sh.redis-backup"

echo "=========================================="
echo "Migrating DEPLOY.sh: Redis → DynamoDB"
echo "=========================================="
echo ""

# 1. Update feature description
echo "1. Updating feature description..."
sed -i.bak1 's/Redis-based session management/DynamoDB-based session management/' "$DEPLOY_FILE"

# 2. Remove VPC execution policy
echo "2. Removing VPC execution policy..."
sed -i.bak2 '/AWSLambdaVPCAccessExecutionRole/d' "$DEPLOY_FILE"

# 3. Comment out entire VPC configuration section (lines 915-1090)
echo "3. Commenting out VPC configuration section..."
sed -i.bak3 '915,1090 s/^/# REMOVED_FOR_DYNAMODB: /' "$DEPLOY_FILE"

# 4. Replace Redis environment variable detection with DynamoDB
echo "4. Updating environment variable configuration..."

# Create a temporary file with the new DynamoDB section
cat > /tmp/dynamodb_config.txt << 'EOF'

    # DynamoDB Session Table Configuration
    DYNAMODB_TABLE="pf-sessions-${ENV}"

    # Check if DynamoDB table exists, create if not
    if ! aws_cmd dynamodb describe-table --table-name "$DYNAMODB_TABLE" --region "$REGION" &>/dev/null; then
        echo "  → Creating DynamoDB session table: $DYNAMODB_TABLE"
        aws_cmd dynamodb create-table \
            --table-name "$DYNAMODB_TABLE" \
            --attribute-definitions \
                AttributeName=session_id,AttributeType=S \
            --key-schema \
                AttributeName=session_id,KeyType=HASH \
            --billing-mode PAY_PER_REQUEST \
            --tags Key=Environment,Value=$ENV Key=Service,Value=projectforce-bedrock \
            --region "$REGION" \
            &>/dev/null

        echo "  ✅ DynamoDB table created: $DYNAMODB_TABLE"

        # Wait for table to be active
        echo "  ℹ️  Waiting for table to become active..."
        aws_cmd dynamodb wait table-exists --table-name "$DYNAMODB_TABLE" --region "$REGION"
    else
        echo "  ℹ️  DynamoDB table already exists: $DYNAMODB_TABLE"
    fi

    # Configure DynamoDB environment variable
    DYNAMODB_TABLE_NAME="$DYNAMODB_TABLE"
EOF

# Replace Redis endpoint detection section (around line 1690-1710)
sed -i.bak4 '1690,1710 s/^/# REMOVED_FOR_DYNAMODB: /' "$DEPLOY_FILE"

# Insert DynamoDB configuration before environment variables JSON
LINE_NUM=$(grep -n '"REDIS_PORT": "6379"' "$DEPLOY_FILE" | cut -d: -f1)
if [[ -n "$LINE_NUM" ]]; then
    sed -i.bak5 "${LINE_NUM}r /tmp/dynamodb_config.txt" "$DEPLOY_FILE"
fi

# 5. Update environment variables JSON
echo "5. Updating environment variables..."
sed -i.bak6 's/"REDIS_PORT": "6379",/# REMOVED: Redis environment variables/' "$DEPLOY_FILE"
sed -i.bak7 's/"REDIS_SSL": "false".*/"DYNAMODB_TABLE": "'"'$DYNAMODB_TABLE_NAME'"'"/' "$DEPLOY_FILE"
sed -i.bak8 '/REDIS_ENDPOINT/d' "$DEPLOY_FILE"

# 6. Update IAM policy to include DynamoDB permissions
echo "6. Adding DynamoDB permissions to IAM policy..."

# Find the IAM policy section and add DynamoDB permissions
IAM_LINE=$(grep -n '"Sid": "LambdaInvokePermission"' "$DEPLOY_FILE" | tail -1 | cut -d: -f1)
if [[ -n "$IAM_LINE" ]]; then
    # Insert DynamoDB policy after LambdaInvokePermission
    NEXT_LINE=$((IAM_LINE + 10))

    cat > /tmp/dynamodb_policy.txt << 'EOF'
        },
        {
            "Sid": "DynamoDBSessionAccess",
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": [
                "arn:aws:dynamodb:us-east-1:${ACCOUNT_ID}:table/pf-sessions-${ENV}"
            ]
EOF

    sed -i.bak9 "${NEXT_LINE}r /tmp/dynamodb_policy.txt" "$DEPLOY_FILE"
fi

# 7. Clean up temporary backup files
echo "7. Cleaning up..."
rm -f "$DEPLOY_FILE".bak*
rm -f /tmp/dynamodb_config.txt
rm -f /tmp/dynamodb_policy.txt

echo ""
echo "=========================================="
echo "✅ Migration Complete!"
echo "=========================================="
echo ""
echo "Changes made:"
echo "  1. ✅ Updated feature description (Redis → DynamoDB)"
echo "  2. ✅ Removed VPC execution policy"
echo "  3. ✅ Commented out VPC configuration section"
echo "  4. ✅ Replaced Redis with DynamoDB table creation"
echo "  5. ✅ Updated environment variables"
echo "  6. ✅ Added DynamoDB IAM permissions"
echo ""
echo "Backup saved to: $BACKUP_FILE"
echo ""
echo "Next steps:"
echo "  1. Review changes: diff $BACKUP_FILE $DEPLOY_FILE"
echo "  2. Test deployment: ./DEPLOY.sh --profile pf-aws"
echo ""
