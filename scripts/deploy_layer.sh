#!/bin/bash

###############################################################################
# Deploy Lambda Layer with Shared Dependencies
#
# This script packages and deploys the common Lambda layer containing:
# - Pydantic models
# - Shared utilities
# - Common dependencies (pydantic, boto3)
#
# Usage: ./deploy_layer.sh [environment]
# Example: ./deploy_layer.sh dev
###############################################################################

set -e

# Configuration
ENVIRONMENT=${1:-dev}
LAYER_NAME="pf-common-layer-${ENVIRONMENT}"
LAYER_DIR="lambda/layers/common"
BUILD_DIR="build/layer"
REGION=${AWS_REGION:-us-east-1}

echo "========================================="
echo "Deploying Lambda Layer: ${LAYER_NAME}"
echo "Environment: ${ENVIRONMENT}"
echo "Region: ${REGION}"
echo "========================================="

# Clean and create build directory
echo "Cleaning build directory..."
rm -rf ${BUILD_DIR}
mkdir -p ${BUILD_DIR}/python

# Copy Python code
echo "Copying Python code..."
cp -r ${LAYER_DIR}/python/* ${BUILD_DIR}/python/

# Install dependencies
echo "Installing dependencies..."
if [ -f "${LAYER_DIR}/requirements.txt" ]; then
    pip install -r ${LAYER_DIR}/requirements.txt -t ${BUILD_DIR}/python/ --upgrade
else
    echo "No requirements.txt found, skipping dependency installation"
fi

# Create ZIP package
echo "Creating ZIP package..."
cd ${BUILD_DIR}
zip -r ../layer.zip python -q
cd ../..

# Publish layer
echo "Publishing layer to AWS..."
LAYER_VERSION=$(aws lambda publish-layer-version \
    --layer-name ${LAYER_NAME} \
    --description "Common dependencies and models for ProjectForce voice lambdas" \
    --zip-file fileb://build/layer.zip \
    --compatible-runtimes python3.11 python3.12 \
    --region ${REGION} \
    --query 'Version' \
    --output text)

echo "✅ Layer published: ${LAYER_NAME}, Version: ${LAYER_VERSION}"

# Get layer ARN
LAYER_ARN=$(aws lambda list-layer-versions \
    --layer-name ${LAYER_NAME} \
    --region ${REGION} \
    --query "LayerVersions[0].LayerVersionArn" \
    --output text)

echo "Layer ARN: ${LAYER_ARN}"

# Update config file
CONFIG_FILE="config/voice_deployment.json"
if [ -f "${CONFIG_FILE}" ]; then
    echo "Updating ${CONFIG_FILE}..."

    # Use jq to update the config file
    tmp=$(mktemp)
    jq ".lambda.common_layer_arn = \"${LAYER_ARN}\" | .lambda.common_layer_version = ${LAYER_VERSION}" ${CONFIG_FILE} > "$tmp"
    mv "$tmp" ${CONFIG_FILE}

    echo "✅ Config file updated"
fi

# Cleanup
echo "Cleaning up..."
rm -rf build/layer
rm -f build/layer.zip

echo ""
echo "========================================="
echo "✅ Layer deployment complete!"
echo "========================================="
echo "Layer Name: ${LAYER_NAME}"
echo "Version: ${LAYER_VERSION}"
echo "ARN: ${LAYER_ARN}"
echo ""
echo "To use this layer, add it to your Lambda functions:"
echo "aws lambda update-function-configuration \\"
echo "  --function-name <function-name> \\"
echo "  --layers ${LAYER_ARN}"
echo "========================================="
