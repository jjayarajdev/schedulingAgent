#!/bin/bash
# ============================================================================
# PF-SYN VAPI Dashboard - Deploy Frontend to DEV
# Region: us-east-1
# ============================================================================

set -e

# Configuration
AWS_PROFILE="pf-aws"
REGION="us-east-1"
ENV="dev"
S3_BUCKET="pf-syn-vapi-dashboard-${ENV}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/../frontend"

echo "============================================"
echo "Deploying VAPI Dashboard Frontend - DEV"
echo "============================================"

# Check if build exists
if [ ! -d "$FRONTEND_DIR/build" ] && [ ! -d "$FRONTEND_DIR/dist" ]; then
  echo ""
  echo "ERROR: Frontend build not found!"
  echo ""
  echo "Build the frontend first:"
  echo "  cd $FRONTEND_DIR"
  echo "  npm install"
  echo "  npm run build"
  echo ""
  exit 1
fi

# Determine build directory (create-react-app uses 'build', vite uses 'dist')
if [ -d "$FRONTEND_DIR/build" ]; then
  BUILD_DIR="$FRONTEND_DIR/build"
elif [ -d "$FRONTEND_DIR/dist" ]; then
  BUILD_DIR="$FRONTEND_DIR/dist"
fi

echo ""
echo "Uploading to S3: ${S3_BUCKET}"

# Sync build to S3
AWS_PROFILE=$AWS_PROFILE aws s3 sync $BUILD_DIR s3://$S3_BUCKET/ \
  --delete \
  --region $REGION

# Set cache headers for different file types
echo "Setting cache headers..."

# HTML - no cache (always fetch latest)
AWS_PROFILE=$AWS_PROFILE aws s3 cp s3://$S3_BUCKET/ s3://$S3_BUCKET/ \
  --recursive \
  --exclude "*" \
  --include "*.html" \
  --metadata-directive REPLACE \
  --cache-control "no-cache, no-store, must-revalidate" \
  --content-type "text/html" \
  --region $REGION

# JS/CSS - cache for 1 year (versioned by build)
AWS_PROFILE=$AWS_PROFILE aws s3 cp s3://$S3_BUCKET/ s3://$S3_BUCKET/ \
  --recursive \
  --exclude "*" \
  --include "*.js" \
  --include "*.css" \
  --metadata-directive REPLACE \
  --cache-control "public, max-age=31536000" \
  --region $REGION

echo ""
echo "============================================"
echo "Frontend Deployment Complete!"
echo "============================================"
echo ""
echo "Frontend URL:"
echo "  http://${S3_BUCKET}.s3-website-${REGION}.amazonaws.com"
echo ""
