#!/bin/bash
# Deploy scheduling-actions Lambda with all dependencies
set -e

LAMBDA_NAME="pf-scheduling-actions"
REGION="us-east-1"
PKG_DIR="/tmp/scheduling-actions-pkg"
ZIP_FILE="/tmp/scheduling-actions-deploy.zip"

echo "=== Building $LAMBDA_NAME deployment package ==="

# Clean up
rm -rf "$PKG_DIR" "$ZIP_FILE"
mkdir -p "$PKG_DIR"

# Install dependencies
echo "Installing dependencies..."
pip install requests -t "$PKG_DIR" --quiet --upgrade

# Copy Lambda code
echo "Copying Lambda code..."
cp *.py "$PKG_DIR/"

# Create zip
echo "Creating deployment package..."
cd "$PKG_DIR"
zip -rq "$ZIP_FILE" .

echo "Package size: $(du -h $ZIP_FILE | cut -f1)"

# Deploy
echo "Deploying to AWS Lambda..."
aws lambda update-function-code \
    --function-name "$LAMBDA_NAME" \
    --zip-file "fileb://$ZIP_FILE" \
    --region "$REGION" \
    --query 'Configuration.{FunctionName:FunctionName,LastModified:LastModified,CodeSize:CodeSize}' \
    --output table

# Wait and verify
echo "Waiting for deployment to complete..."
sleep 5
STATUS=$(aws lambda get-function --function-name "$LAMBDA_NAME" --region "$REGION" --query 'Configuration.LastUpdateStatus' --output text)
echo "Deployment status: $STATUS"

if [ "$STATUS" = "Successful" ]; then
    echo "✅ Deployment successful!"
else
    echo "❌ Deployment may have issues. Status: $STATUS"
fi

# Cleanup
rm -rf "$PKG_DIR"
echo "Done!"
