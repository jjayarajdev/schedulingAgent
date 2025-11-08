#!/bin/bash
# Deploy ProjectForce Agent UI to AWS S3 + CloudFront

set -e

# Configuration
ENVIRONMENT=${1:-dev}
REGION=${AWS_REGION:-us-east-1}
S3_BUCKET="pf-agent-ui-${ENVIRONMENT}"
CLOUDFRONT_COMMENT="ProjectForce Agent UI - ${ENVIRONMENT}"
API_GATEWAY_URL=""  # Will be set after API Gateway deployment

echo "================================================"
echo "  ProjectForce Agent UI Deployment"
echo "================================================"
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo "S3 Bucket: $S3_BUCKET"
echo ""

# Step 1: Create S3 bucket for static hosting
echo "📦 Step 1: Creating S3 bucket..."
if aws s3 ls "s3://${S3_BUCKET}" 2>&1 | grep -q 'NoSuchBucket'; then
    aws s3 mb "s3://${S3_BUCKET}" --region $REGION
    echo "✅ Bucket created"
else
    echo "✅ Bucket already exists"
fi

# Step 2: Configure bucket for static website hosting
echo ""
echo "🌐 Step 2: Configuring static website hosting..."
aws s3 website "s3://${S3_BUCKET}" \
    --index-document index.html \
    --error-document index.html

# Step 3: Set bucket policy for public read access
echo ""
echo "🔓 Step 3: Setting bucket policy..."
cat > /tmp/bucket-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${S3_BUCKET}/*"
    }
  ]
}
EOF

aws s3api put-bucket-policy \
    --bucket "${S3_BUCKET}" \
    --policy file:///tmp/bucket-policy.json

# Step 4: Build and prepare UI files
echo ""
echo "🔨 Step 4: Preparing UI files..."
UI_DIR="../testing/ui"
BUILD_DIR="/tmp/pf-ui-build"
rm -rf $BUILD_DIR
mkdir -p $BUILD_DIR

# Copy UI files
cp $UI_DIR/index.html $BUILD_DIR/
cp $UI_DIR/pf_proxy.py $BUILD_DIR/ 2>/dev/null || true

# Update API endpoint in index.html
if [ ! -z "$API_GATEWAY_URL" ]; then
    sed -i.bak "s|http://localhost:5001|$API_GATEWAY_URL|g" $BUILD_DIR/index.html
    echo "✅ Updated API endpoint to: $API_GATEWAY_URL"
else
    echo "⚠️  Warning: API_GATEWAY_URL not set. Update manually after API Gateway deployment."
fi

# Step 5: Upload files to S3
echo ""
echo "📤 Step 5: Uploading files to S3..."
aws s3 sync $BUILD_DIR "s3://${S3_BUCKET}" \
    --delete \
    --cache-control "max-age=3600" \
    --metadata-directive REPLACE

# Set correct content types
aws s3 cp "s3://${S3_BUCKET}/index.html" "s3://${S3_BUCKET}/index.html" \
    --content-type "text/html" \
    --metadata-directive REPLACE

echo "✅ Files uploaded"

# Step 6: Create CloudFront distribution (optional, for HTTPS and caching)
echo ""
echo "☁️  Step 6: CloudFront distribution..."
echo "Note: Creating CloudFront distribution takes 15-20 minutes."
echo "You can create it manually or use the AWS Console for now."
echo ""
echo "If you want to create it, run:"
echo "  aws cloudfront create-distribution --origin-domain-name ${S3_BUCKET}.s3-website-${REGION}.amazonaws.com"

# Step 7: Output URLs
echo ""
echo "================================================"
echo "  ✅ Deployment Complete!"
echo "================================================"
echo ""
echo "S3 Website URL:"
echo "  http://${S3_BUCKET}.s3-website-${REGION}.amazonaws.com"
echo ""
echo "Next Steps:"
echo "  1. Deploy API Gateway (see deploy_api_gateway.sh)"
echo "  2. Update API endpoint in index.html"
echo "  3. (Optional) Set up CloudFront for HTTPS"
echo "  4. (Optional) Configure custom domain"
echo ""
