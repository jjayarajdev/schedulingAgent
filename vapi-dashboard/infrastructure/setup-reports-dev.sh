#!/bin/bash
# ============================================================================
# PF-SYN VAPI Dashboard - Reports Infrastructure Setup (DEV)
# Adds: Reports DynamoDB table, Report Generator Lambda, EventBridge schedule
# ============================================================================

set -e

# Configuration
AWS_PROFILE="pf-aws"
REGION="us-east-1"
ENV="dev"
PREFIX="pf-syn-vapi-dashboard"

# Resource names
REPORTS_TABLE="${PREFIX}-reports-${ENV}"
REPORTS_LAMBDA="${PREFIX}-reports-${ENV}"
LAMBDA_ROLE="${PREFIX}-lambda-role-${ENV}"
TENANTS_TABLE="${PREFIX}-tenants-${ENV}"
SCHEDULE_RULE="${PREFIX}-daily-report-${ENV}"

echo "============================================"
echo "Setting up Reports Infrastructure - DEV"
echo "============================================"

# ============================================================================
# 1. Create Reports DynamoDB Table
# ============================================================================
echo ""
echo "[1/4] Creating DynamoDB Table: ${REPORTS_TABLE}"

AWS_PROFILE=$AWS_PROFILE aws dynamodb create-table \
  --table-name $REPORTS_TABLE \
  --attribute-definitions \
    AttributeName=tenant_id,AttributeType=S \
    AttributeName=report_date,AttributeType=S \
  --key-schema \
    AttributeName=tenant_id,KeyType=HASH \
    AttributeName=report_date,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region $REGION 2>/dev/null || echo "  Table already exists, skipping..."

echo "  Waiting for table to be active..."
AWS_PROFILE=$AWS_PROFILE aws dynamodb wait table-exists \
  --table-name $REPORTS_TABLE \
  --region $REGION

# ============================================================================
# 2. Update IAM Role Policy
# ============================================================================
echo ""
echo "[2/4] Updating IAM Role Policy for reports table access"

# Get current policy and add reports table
cat > /tmp/lambda-reports-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
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
        "arn:aws:dynamodb:${REGION}:*:table/${PREFIX}-users-${ENV}",
        "arn:aws:dynamodb:${REGION}:*:table/${PREFIX}-tenants-${ENV}",
        "arn:aws:dynamodb:${REGION}:*:table/${PREFIX}-reports-${ENV}",
        "arn:aws:dynamodb:${REGION}:*:table/${PREFIX}-users-${ENV}/index/*",
        "arn:aws:dynamodb:${REGION}:*:table/${PREFIX}-tenants-${ENV}/index/*",
        "arn:aws:dynamodb:${REGION}:*:table/${PREFIX}-reports-${ENV}/index/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:${REGION}:*:secret:pf-syn-vapi-*"
    }
  ]
}
EOF

POLICY_NAME="${PREFIX}-lambda-policy-${ENV}"
AWS_PROFILE=$AWS_PROFILE aws iam put-role-policy \
  --role-name $LAMBDA_ROLE \
  --policy-name $POLICY_NAME \
  --policy-document file:///tmp/lambda-reports-policy.json \
  --region $REGION

echo "  Policy updated"

# ============================================================================
# 3. Create Reports Lambda
# ============================================================================
echo ""
echo "[3/4] Creating Reports Lambda: ${REPORTS_LAMBDA}"

# Get role ARN
ROLE_ARN=$(AWS_PROFILE=$AWS_PROFILE aws iam get-role \
  --role-name $LAMBDA_ROLE \
  --query 'Role.Arn' \
  --output text)

# Package Lambda code
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="${SCRIPT_DIR}/../backend/reports"
ZIP_FILE="/tmp/${REPORTS_LAMBDA}.zip"

cd "$BACKEND_DIR"
rm -f $ZIP_FILE
zip -j $ZIP_FILE handler.py

# Check if Lambda exists
if AWS_PROFILE=$AWS_PROFILE aws lambda get-function --function-name $REPORTS_LAMBDA --region $REGION 2>/dev/null; then
  echo "  Lambda exists, updating code..."
  AWS_PROFILE=$AWS_PROFILE aws lambda update-function-code \
    --function-name $REPORTS_LAMBDA \
    --zip-file fileb://$ZIP_FILE \
    --region $REGION > /dev/null
else
  echo "  Creating new Lambda..."
  AWS_PROFILE=$AWS_PROFILE aws lambda create-function \
    --function-name $REPORTS_LAMBDA \
    --runtime python3.11 \
    --handler handler.lambda_handler \
    --role $ROLE_ARN \
    --zip-file fileb://$ZIP_FILE \
    --timeout 300 \
    --memory-size 512 \
    --environment "Variables={ENVIRONMENT=${ENV},TENANTS_TABLE=${TENANTS_TABLE},REPORTS_TABLE=${REPORTS_TABLE},VAPI_API_KEY=${VAPI_API_KEY:-not-set}}" \
    --region $REGION > /dev/null
fi

echo "  Waiting for Lambda to be ready..."
AWS_PROFILE=$AWS_PROFILE aws lambda wait function-active \
  --function-name $REPORTS_LAMBDA \
  --region $REGION

# ============================================================================
# 4. Create EventBridge Schedule (Daily at 6 AM UTC)
# ============================================================================
echo ""
echo "[4/4] Creating EventBridge Schedule: ${SCHEDULE_RULE}"

# Get Lambda ARN
LAMBDA_ARN=$(AWS_PROFILE=$AWS_PROFILE aws lambda get-function \
  --function-name $REPORTS_LAMBDA \
  --region $REGION \
  --query 'Configuration.FunctionArn' \
  --output text)

# Create rule (runs daily at 6 AM UTC)
AWS_PROFILE=$AWS_PROFILE aws events put-rule \
  --name $SCHEDULE_RULE \
  --schedule-expression "cron(0 6 * * ? *)" \
  --state ENABLED \
  --description "Trigger daily VAPI report generation" \
  --region $REGION > /dev/null

# Add Lambda as target
AWS_PROFILE=$AWS_PROFILE aws events put-targets \
  --rule $SCHEDULE_RULE \
  --targets "Id=1,Arn=${LAMBDA_ARN}" \
  --region $REGION > /dev/null

# Add permission for EventBridge to invoke Lambda
AWS_PROFILE=$AWS_PROFILE aws lambda add-permission \
  --function-name $REPORTS_LAMBDA \
  --statement-id "EventBridgeInvoke" \
  --action "lambda:InvokeFunction" \
  --principal "events.amazonaws.com" \
  --source-arn "arn:aws:events:${REGION}:*:rule/${SCHEDULE_RULE}" \
  --region $REGION 2>/dev/null || echo "  Permission already exists"

echo ""
echo "============================================"
echo "Reports Infrastructure Setup Complete!"
echo "============================================"
echo ""
echo "Resources created:"
echo "  - DynamoDB Table: ${REPORTS_TABLE}"
echo "  - Lambda Function: ${REPORTS_LAMBDA}"
echo "  - EventBridge Rule: ${SCHEDULE_RULE} (daily at 6 AM UTC)"
echo ""
echo "Next steps:"
echo "  1. Update API Lambda with new handler code"
echo "  2. Set VAPI_API_KEY in Lambda environment if not already set:"
echo "     aws lambda update-function-configuration \\"
echo "       --function-name ${REPORTS_LAMBDA} \\"
echo "       --environment \"Variables={VAPI_API_KEY=your-key,...}\" \\"
echo "       --profile pf-aws --region us-east-1"
echo ""
echo "  3. Test report generation manually:"
echo "     aws lambda invoke --function-name ${REPORTS_LAMBDA} \\"
echo "       --payload '{\"tenant_id\": \"wtu\", \"date\": \"2026-02-05\"}' \\"
echo "       --profile pf-aws --region us-east-1 /tmp/report-output.json"
echo ""
