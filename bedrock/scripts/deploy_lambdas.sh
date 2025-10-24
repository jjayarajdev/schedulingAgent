#!/bin/bash
set -e

REGION="us-east-1"
ACCOUNT_ID="618048437522"
PREFIX="pf"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          Deploying Lambda Functions with pf prefix          ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# Function names
LAMBDAS=("scheduling-actions" "information-actions" "notes-actions")

for LAMBDA in "${LAMBDAS[@]}"; do
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "Deploying: $PREFIX-$LAMBDA"
    echo "═══════════════════════════════════════════════════════════════"

    LAMBDA_DIR="lambda/${LAMBDA}"
    ZIP_FILE="${PREFIX}_${LAMBDA}.zip"
    FUNCTION_NAME="${PREFIX}-${LAMBDA}"
    ROLE_NAME="${PREFIX}-${LAMBDA%-actions}-lambda-role-dev"

    # Check if source directory exists
    if [ ! -d "$LAMBDA_DIR" ]; then
        echo "❌ Directory not found: $LAMBDA_DIR"
        continue
    fi

    # Create deployment package
    echo "📦 Creating deployment package..."
    cd "$LAMBDA_DIR"

    # Remove old zip if exists
    rm -f "../../$ZIP_FILE"

    # Package Lambda function (exclude venv and tests)
    zip -r "../../$ZIP_FILE" . -x "venv/*" "*.pyc" "__pycache__/*" "*.git/*" > /dev/null

    cd ../..

    echo "✓ Package created: $ZIP_FILE"

    # Get IAM role ARN
    ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text 2>/dev/null || echo "")

    if [ -z "$ROLE_ARN" ]; then
        echo "❌ Role not found: $ROLE_NAME"
        continue
    fi

    echo "✓ Found role: $ROLE_NAME"

    # Check if Lambda function exists
    FUNCTION_EXISTS=$(aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" 2>&1 || echo "NotFound")

    if echo "$FUNCTION_EXISTS" | grep -q "ResourceNotFoundException\|NotFound"; then
        # Create new function
        echo "🚀 Creating Lambda function..."

        aws lambda create-function \
            --function-name "$FUNCTION_NAME" \
            --runtime python3.11 \
            --role "$ROLE_ARN" \
            --handler "handler.lambda_handler" \
            --zip-file "fileb://$ZIP_FILE" \
            --timeout 30 \
            --memory-size 256 \
            --region "$REGION" \
            --environment "Variables={DYNAMODB_TABLE_PREFIX=${PREFIX},ENVIRONMENT=dev}" \
            > /dev/null

        echo "✓ Lambda function created: $FUNCTION_NAME"
    else
        # Update existing function
        echo "🔄 Updating Lambda function code..."

        aws lambda update-function-code \
            --function-name "$FUNCTION_NAME" \
            --zip-file "fileb://$ZIP_FILE" \
            --region "$REGION" \
            > /dev/null

        echo "✓ Lambda function updated: $FUNCTION_NAME"
    fi

    # Add resource policy to allow Bedrock to invoke
    echo "🔐 Adding Bedrock invoke permissions..."

    aws lambda add-permission \
        --function-name "$FUNCTION_NAME" \
        --statement-id "AllowBedrock" \
        --action "lambda:InvokeFunction" \
        --principal bedrock.amazonaws.com \
        --source-arn "arn:aws:bedrock:$REGION:$ACCOUNT_ID:agent/*" \
        --region "$REGION" 2>/dev/null || echo "  (Permission may already exist)"

    echo "✓ Permissions configured"

    # Clean up zip file
    rm -f "$ZIP_FILE"

done

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         Lambda Deployment Complete!                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Deployed functions:"
for LAMBDA in "${LAMBDAS[@]}"; do
    echo "  • $PREFIX-$LAMBDA"
done
echo ""
