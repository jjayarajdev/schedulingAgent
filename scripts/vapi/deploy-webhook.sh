#!/bin/bash
#
# Deploy VAPI Webhook Lambda
#
# Usage:
#   ./deploy-webhook.sh dev      # Deploy to dev (us-east-1)
#   ./deploy-webhook.sh prod     # Deploy to prod (us-east-1)
#
# This script builds and deploys the pf-syn-vapi-webhook Lambda function
# which handles VAPI voice requests and routes them to the orchestrator.
#

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Default environment
ENVIRONMENT="${1:-dev}"

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prod" ]]; then
    echo "Error: Environment must be 'dev' or 'prod'"
    echo "Usage: $0 [dev|prod]"
    exit 1
fi

# Configuration
AWS_PROFILE="${AWS_PROFILE:-pf-aws}"
LAMBDA_NAME="pf-syn-vapi-webhook-${ENVIRONMENT}"
LAMBDA_SOURCE="${PROJECT_ROOT}/lambda/vapi-webhook"
BUILD_DIR="/tmp/vapi-webhook-build-$$"
ZIP_FILE="/tmp/vapi-webhook-$$.zip"

# VAPI webhook always deploys to us-east-1 (voice region)
DEPLOY_REGION="us-east-1"

# Orchestrator region varies by environment
if [[ "$ENVIRONMENT" == "prod" ]]; then
    ORCHESTRATOR_REGION="us-east-2"
else
    ORCHESTRATOR_REGION="us-east-1"
fi

ORCHESTRATOR_LAMBDA="pf-syn-orchestrator-${ENVIRONMENT}"

echo "=========================================="
echo "VAPI Webhook Lambda Deployment"
echo "=========================================="
echo "Environment:     ${ENVIRONMENT}"
echo "Lambda:          ${LAMBDA_NAME}"
echo "Deploy Region:   ${DEPLOY_REGION}"
echo "Orchestrator:    ${ORCHESTRATOR_LAMBDA} (${ORCHESTRATOR_REGION})"
echo "=========================================="

# Check if source exists
if [[ ! -d "$LAMBDA_SOURCE" ]]; then
    echo "Error: Lambda source not found at ${LAMBDA_SOURCE}"
    exit 1
fi

# Clean up any previous build
rm -rf "$BUILD_DIR" "$ZIP_FILE"

# Create build directory
echo ""
echo "[1/4] Creating build directory..."
mkdir -p "$BUILD_DIR"

# Copy source files
echo "[2/4] Copying source files..."
cp "${LAMBDA_SOURCE}"/*.py "$BUILD_DIR/"

# Install dependencies
echo "[3/4] Installing dependencies..."
pip3 install -q -t "$BUILD_DIR" requests 2>/dev/null

# Create deployment package
echo "[4/4] Creating deployment package..."
cd "$BUILD_DIR"
zip -q -r "$ZIP_FILE" .

PACKAGE_SIZE=$(du -h "$ZIP_FILE" | cut -f1)
echo "Package size: ${PACKAGE_SIZE}"

# Check if Lambda exists
echo ""
echo "Checking if Lambda exists..."
if aws --profile "$AWS_PROFILE" lambda get-function \
    --function-name "$LAMBDA_NAME" \
    --region "$DEPLOY_REGION" &>/dev/null; then

    # Update existing Lambda
    echo "Updating existing Lambda..."
    aws --profile "$AWS_PROFILE" lambda update-function-code \
        --function-name "$LAMBDA_NAME" \
        --zip-file "fileb://${ZIP_FILE}" \
        --region "$DEPLOY_REGION" \
        --query '[FunctionName, LastModified]' \
        --output table

    # Wait for update to complete
    echo "Waiting for update to complete..."
    aws --profile "$AWS_PROFILE" lambda wait function-updated \
        --function-name "$LAMBDA_NAME" \
        --region "$DEPLOY_REGION"

    # Update environment variables
    echo "Updating environment variables..."
    aws --profile "$AWS_PROFILE" lambda update-function-configuration \
        --function-name "$LAMBDA_NAME" \
        --region "$DEPLOY_REGION" \
        --environment "Variables={
            ENVIRONMENT=${ENVIRONMENT},
            ORCHESTRATOR_LAMBDA=${ORCHESTRATOR_LAMBDA},
            ORCHESTRATOR_REGION=${ORCHESTRATOR_REGION},
            TWILIO_NUMBER=+12185516488,
            PF_SECRET_NAME=projectforce/api/credentials,
            SECRETS_REGION=us-east-2,
            LOG_LEVEL=INFO,
            AWS_REGION=${DEPLOY_REGION}
        }" \
        --query '[FunctionName, LastModified]' \
        --output table

else
    # Create new Lambda
    echo "Creating new Lambda..."

    # Get the execution role ARN
    ROLE_ARN=$(aws --profile "$AWS_PROFILE" iam get-role \
        --role-name pf-syn-lambda-role \
        --query 'Role.Arn' \
        --output text 2>/dev/null || echo "")

    if [[ -z "$ROLE_ARN" ]]; then
        echo "Error: Could not find IAM role 'pf-syn-lambda-role'"
        exit 1
    fi

    aws --profile "$AWS_PROFILE" lambda create-function \
        --function-name "$LAMBDA_NAME" \
        --runtime python3.11 \
        --handler handler.lambda_handler \
        --role "$ROLE_ARN" \
        --zip-file "fileb://${ZIP_FILE}" \
        --timeout 30 \
        --memory-size 256 \
        --region "$DEPLOY_REGION" \
        --environment "Variables={
            ENVIRONMENT=${ENVIRONMENT},
            ORCHESTRATOR_LAMBDA=${ORCHESTRATOR_LAMBDA},
            ORCHESTRATOR_REGION=${ORCHESTRATOR_REGION},
            TWILIO_NUMBER=+12185516488,
            PF_SECRET_NAME=projectforce/api/credentials,
            SECRETS_REGION=us-east-2,
            LOG_LEVEL=INFO,
            AWS_REGION=${DEPLOY_REGION}
        }" \
        --query '[FunctionName, FunctionArn]' \
        --output table

    # Wait for creation
    echo "Waiting for Lambda to be active..."
    aws --profile "$AWS_PROFILE" lambda wait function-active \
        --function-name "$LAMBDA_NAME" \
        --region "$DEPLOY_REGION"

    # Create Function URL
    echo "Creating Function URL..."
    FUNCTION_URL=$(aws --profile "$AWS_PROFILE" lambda create-function-url-config \
        --function-name "$LAMBDA_NAME" \
        --auth-type NONE \
        --region "$DEPLOY_REGION" \
        --query 'FunctionUrl' \
        --output text 2>/dev/null || echo "")

    if [[ -n "$FUNCTION_URL" ]]; then
        echo "Function URL: ${FUNCTION_URL}"

        # Add permission for public access
        aws --profile "$AWS_PROFILE" lambda add-permission \
            --function-name "$LAMBDA_NAME" \
            --statement-id FunctionURLAllowPublicAccess \
            --action lambda:InvokeFunctionUrl \
            --principal "*" \
            --function-url-auth-type NONE \
            --region "$DEPLOY_REGION" 2>/dev/null || true
    fi
fi

# Get and display the Function URL
echo ""
echo "Getting Function URL..."
FUNCTION_URL=$(aws --profile "$AWS_PROFILE" lambda get-function-url-config \
    --function-name "$LAMBDA_NAME" \
    --region "$DEPLOY_REGION" \
    --query 'FunctionUrl' \
    --output text 2>/dev/null || echo "Not configured")

# Cleanup
rm -rf "$BUILD_DIR" "$ZIP_FILE"

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo "Lambda:       ${LAMBDA_NAME}"
echo "Region:       ${DEPLOY_REGION}"
echo "Function URL: ${FUNCTION_URL}"
echo ""
echo "Next step: Configure VAPI assistant with this URL"
echo "Run: ./configure-assistant.sh ${ENVIRONMENT}"
echo "=========================================="
