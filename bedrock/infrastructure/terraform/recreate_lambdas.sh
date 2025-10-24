#!/bin/bash
set -e

###############################################################################
# Lambda Functions Recreation Script
# Purpose: Recreate Lambda functions without KMS encryption
# Used during Claude 4.5 migration to resolve KMS access issues
###############################################################################

REGION="us-east-1"
ACCOUNT_ID="618048437522"
PREFIX="pf"
LAMBDA_DIR="/Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/lambda"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          Lambda Functions Recreation Script                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Delete existing functions
echo "Step 1: Deleting existing Lambda functions..."
echo "═══════════════════════════════════════════════════════════════"

for func in "${PREFIX}-scheduling-actions" "${PREFIX}-information-actions" "${PREFIX}-notes-actions"; do
  echo "  Deleting $func..."
  aws lambda delete-function --function-name "$func" --region "$REGION" 2>/dev/null || echo "    (Function not found, skipping)"
done

echo "✓ Existing functions deleted"
echo ""

# Step 2: Create new functions without KMS
echo "Step 2: Creating Lambda functions without KMS encryption..."
echo "═══════════════════════════════════════════════════════════════"

cd "$LAMBDA_DIR"

# Create scheduling Lambda
echo "  Creating ${PREFIX}-scheduling-actions..."
aws lambda create-function \
  --function-name "${PREFIX}-scheduling-actions" \
  --runtime python3.11 \
  --role "arn:aws:iam::${ACCOUNT_ID}:role/${PREFIX}-scheduling-lambda-role-dev" \
  --handler handler.lambda_handler \
  --zip-file "fileb://scheduling-actions/scheduling-actions.zip" \
  --timeout 30 \
  --memory-size 512 \
  --environment "Variables={DYNAMODB_TABLE_PREFIX=${PREFIX},ENVIRONMENT=dev}" \
  --region "$REGION" \
  --query 'FunctionArn' --output text

# Create information Lambda
echo "  Creating ${PREFIX}-information-actions..."
aws lambda create-function \
  --function-name "${PREFIX}-information-actions" \
  --runtime python3.11 \
  --role "arn:aws:iam::${ACCOUNT_ID}:role/${PREFIX}-information-lambda-role-dev" \
  --handler handler.lambda_handler \
  --zip-file "fileb://information-actions/information-actions.zip" \
  --timeout 30 \
  --memory-size 512 \
  --environment "Variables={DYNAMODB_TABLE_PREFIX=${PREFIX},ENVIRONMENT=dev}" \
  --region "$REGION" \
  --query 'FunctionArn' --output text

# Create notes Lambda
echo "  Creating ${PREFIX}-notes-actions..."
aws lambda create-function \
  --function-name "${PREFIX}-notes-actions" \
  --runtime python3.11 \
  --role "arn:aws:iam::${ACCOUNT_ID}:role/${PREFIX}-notes-lambda-role-dev" \
  --handler handler.lambda_handler \
  --zip-file "fileb://notes-actions/notes-actions.zip" \
  --timeout 30 \
  --memory-size 512 \
  --environment "Variables={DYNAMODB_TABLE_PREFIX=${PREFIX},ENVIRONMENT=dev}" \
  --region "$REGION" \
  --query 'FunctionArn' --output text

echo "✓ Lambda functions created"
echo ""

# Step 3: Add Bedrock invoke permissions
echo "Step 3: Adding Bedrock invoke permissions..."
echo "═══════════════════════════════════════════════════════════════"

for func in "${PREFIX}-scheduling-actions" "${PREFIX}-information-actions" "${PREFIX}-notes-actions"; do
  echo "  Adding permission to $func..."
  aws lambda add-permission \
    --function-name "$func" \
    --statement-id "AllowBedrockInvoke" \
    --action "lambda:InvokeFunction" \
    --principal bedrock.amazonaws.com \
    --source-account "$ACCOUNT_ID" \
    --region "$REGION" > /dev/null 2>&1 || echo "    (Permission may already exist)"
done

echo "✓ Bedrock permissions added"
echo ""

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                 Lambda Recreation Complete!                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Functions created:"
echo "  • ${PREFIX}-scheduling-actions"
echo "  • ${PREFIX}-information-actions"
echo "  • ${PREFIX}-notes-actions"
echo ""
echo "Next step: Run ./prepare_agents.sh to configure action groups"
echo ""
