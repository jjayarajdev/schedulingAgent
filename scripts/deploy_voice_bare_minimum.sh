#!/bin/bash
# Bare Minimum Voice Deployment - No Terraform, Just Lambda Functions

set -e

REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
PREFIX="pf"
ENV="dev"

echo "=========================================="
echo "Bare Minimum Voice Deployment"
echo "=========================================="
echo ""

# ============================================================================
# Step 1: Deploy Common Layer
# ============================================================================

echo "[1/4] Deploying common Lambda layer..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT/lambda/layers/common"

# Clean previous build
rm -rf build layer.zip

# Create temporary directory for dependencies
mkdir -p python

# Install dependencies locally (no global install, ignore version conflicts)
pip install -r requirements.txt -t python/ --no-cache-dir --ignore-installed -q 2>/dev/null || true

# Copy custom models to layer
if [ -d "models" ]; then
  echo "  Copying custom Pydantic models..."
  cp -r models python/
fi

# Create ZIP using Python (works on Windows)
python -c "import shutil; shutil.make_archive('layer', 'zip', '.', 'python')"

# Publish layer
LAYER_VERSION=$(aws lambda publish-layer-version \
  --layer-name "${PREFIX}-common-layer-${ENV}" \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.11 python3.12 \
  --region "$REGION" \
  --query 'Version' \
  --output text)

LAYER_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:layer:${PREFIX}-common-layer-${ENV}:${LAYER_VERSION}"

echo "✅ Layer deployed: $LAYER_ARN"
echo ""


# ============================================================================
# Step 2: Deploy Lex Fulfillment Lambda
# ============================================================================

echo "[2/4] Deploying Lex Fulfillment Lambda..."

cd "$PROJECT_ROOT/lambda/lex-fulfillment"
rm -f deployment.zip
python -c "import zipfile; z = zipfile.ZipFile('deployment.zip', 'w'); z.write('handler.py'); z.close()"

# Update function code (skip create if doesn't exist)
if aws lambda get-function --function-name "${PREFIX}-lex-fulfillment-${ENV}" --region "$REGION" >/dev/null 2>&1; then
  echo "  Updating code..."
  aws lambda update-function-code \
    --function-name "${PREFIX}-lex-fulfillment-${ENV}" \
    --zip-file fileb://deployment.zip \
    --region "$REGION" >/dev/null

  echo "  Waiting for code update to complete..."
  aws lambda wait function-updated \
    --function-name "${PREFIX}-lex-fulfillment-${ENV}" \
    --region "$REGION"

  echo "  Attaching layer..."
  aws lambda update-function-configuration \
    --function-name "${PREFIX}-lex-fulfillment-${ENV}" \
    --layers "$LAYER_ARN" \
    --region "$REGION" >/dev/null

  echo "✅ Updated: ${PREFIX}-lex-fulfillment-${ENV}"
else
  echo "⚠️  Function ${PREFIX}-lex-fulfillment-${ENV} doesn't exist - skipping"
fi

echo ""


# ============================================================================
# Step 3: Deploy Voice Bedrock Bridge Lambda
# ============================================================================

echo "[3/4] Deploying Voice Bedrock Bridge Lambda..."

cd "$PROJECT_ROOT/lambda/voice-bedrock-bridge"
rm -f deployment.zip
python -c "import zipfile; z = zipfile.ZipFile('deployment.zip', 'w'); z.write('handler.py'); z.close()"

if aws lambda get-function --function-name "${PREFIX}-voice-bedrock-bridge-${ENV}" --region "$REGION" >/dev/null 2>&1; then
  echo "  Updating code..."
  aws lambda update-function-code \
    --function-name "${PREFIX}-voice-bedrock-bridge-${ENV}" \
    --zip-file fileb://deployment.zip \
    --region "$REGION" >/dev/null

  echo "  Waiting for code update to complete..."
  aws lambda wait function-updated \
    --function-name "${PREFIX}-voice-bedrock-bridge-${ENV}" \
    --region "$REGION"

  echo "  Attaching layer..."
  aws lambda update-function-configuration \
    --function-name "${PREFIX}-voice-bedrock-bridge-${ENV}" \
    --layers "$LAYER_ARN" \
    --region "$REGION" >/dev/null

  echo "✅ Updated: ${PREFIX}-voice-bedrock-bridge-${ENV}"
else
  echo "⚠️  Function ${PREFIX}-voice-bedrock-bridge-${ENV} doesn't exist - skipping"
fi

echo ""


# ============================================================================
# Step 4: Deploy Customer Lookup Lambda
# ============================================================================

echo "[4/4] Deploying Customer Lookup Lambda..."

cd "$PROJECT_ROOT/lambda/customer-lookup"
rm -f deployment.zip
python -c "import zipfile; z = zipfile.ZipFile('deployment.zip', 'w'); z.write('handler.py'); z.close()"

if aws lambda get-function --function-name "${PREFIX}-customer-lookup-${ENV}" --region "$REGION" >/dev/null 2>&1; then
  echo "  Updating code..."
  aws lambda update-function-code \
    --function-name "${PREFIX}-customer-lookup-${ENV}" \
    --zip-file fileb://deployment.zip \
    --region "$REGION" >/dev/null

  echo "  Waiting for code update to complete..."
  aws lambda wait function-updated \
    --function-name "${PREFIX}-customer-lookup-${ENV}" \
    --region "$REGION"

  echo "  Attaching layer..."
  aws lambda update-function-configuration \
    --function-name "${PREFIX}-customer-lookup-${ENV}" \
    --layers "$LAYER_ARN" \
    --region "$REGION" >/dev/null

  echo "✅ Updated: ${PREFIX}-customer-lookup-${ENV}"
else
  echo "⚠️  Function ${PREFIX}-customer-lookup-${ENV} doesn't exist - skipping"
fi

echo ""


# ============================================================================
# Summary
# ============================================================================

echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "Deployed:"
echo "  - Lambda Layer: ${LAYER_ARN}"
echo "  - ${PREFIX}-lex-fulfillment-${ENV}"
echo "  - ${PREFIX}-voice-bedrock-bridge-${ENV}"
echo "  - ${PREFIX}-customer-lookup-${ENV}"
echo ""
echo "Next: Test the deployment"
echo "  cd ../testing/voice"
echo "  source voice_test_config.sh"
echo "  bash run_voice_quick_tests.sh"
echo ""
