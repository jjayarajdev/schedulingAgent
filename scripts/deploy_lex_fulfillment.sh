#!/bin/bash
#
# Deploy Lex Fulfillment Lambda
# Packages and deploys the lex-fulfillment Lambda function with all dependencies
# Works on Mac, Linux, and Windows (Git Bash/WSL)
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
FUNCTION_NAME="pf-lex-fulfillment-dev"
SOURCE_DIR="lambda/lex-fulfillment"
TEMP_DIR="/tmp/lex-fulfillment-deploy-$$"
ZIP_FILE="lex-fulfillment-deploy.zip"
REGION="us-east-1"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Lex Fulfillment Lambda Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI not found. Please install AWS CLI.${NC}"
    exit 1
fi

# Check if AWS_PROFILE is set
if [ -z "$AWS_PROFILE" ]; then
    echo -e "${YELLOW}Warning: AWS_PROFILE not set. Using default profile.${NC}"
fi

# Navigate to project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"

echo -e "${GREEN}✓ Project root: $PROJECT_ROOT${NC}"
echo ""

# Step 1: Clean up old temp directory
echo -e "${YELLOW}[1/6] Cleaning up old deployment files...${NC}"
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"
echo -e "${GREEN}✓ Created temp directory: $TEMP_DIR${NC}"
echo ""

# Step 2: Copy source files
echo -e "${YELLOW}[2/6] Copying source files...${NC}"
if [ ! -d "$SOURCE_DIR" ]; then
    echo -e "${RED}Error: Source directory not found: $SOURCE_DIR${NC}"
    exit 1
fi

# Copy Python source files (excluding __pycache__, zips, etc.)
cd "$SOURCE_DIR"
find . -type f -name "*.py" -not -path "./__pycache__/*" -exec cp --parents {} "$TEMP_DIR/" \;
echo -e "${GREEN}✓ Copied Python source files${NC}"

# Step 3: Copy dependencies from package directory
echo -e "${YELLOW}[3/6] Copying dependencies...${NC}"
if [ -d "package" ]; then
    cp -r package/* "$TEMP_DIR/"
    echo -e "${GREEN}✓ Copied package dependencies${NC}"
else
    echo -e "${YELLOW}Warning: No package directory found. Dependencies may be missing.${NC}"
fi
echo ""

# Step 4: Create deployment package
echo -e "${YELLOW}[4/6] Creating deployment package...${NC}"
cd "$TEMP_DIR"

# Create zip - handle cross-platform differences
if command -v zip &> /dev/null; then
    # Unix/Mac/Git Bash with zip installed
    zip -r -q "$ZIP_FILE" .
elif command -v python3 &> /dev/null; then
    # Use Python zipfile module as fallback
    python3 -m zipfile -c "$ZIP_FILE" ./*
elif command -v python &> /dev/null; then
    # Try python (might be Python 3)
    python -m zipfile -c "$ZIP_FILE" ./*
else
    echo -e "${RED}Error: No zip utility found (zip command or Python)${NC}"
    exit 1
fi

ZIP_SIZE=$(ls -lh "$ZIP_FILE" | awk '{print $5}')
echo -e "${GREEN}✓ Created deployment package: $ZIP_FILE ($ZIP_SIZE)${NC}"
echo ""

# Step 5: Deploy to AWS Lambda
echo -e "${YELLOW}[5/6] Deploying to AWS Lambda...${NC}"
echo "Function: $FUNCTION_NAME"
echo "Region: $REGION"
echo ""

DEPLOY_OUTPUT=$(aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://$ZIP_FILE" \
    --region "$REGION" \
    --query '{FunctionName:FunctionName,CodeSize:CodeSize,LastModified:LastModified,State:State}' \
    --output json 2>&1)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Deployment successful!${NC}"
    echo ""
    echo "$DEPLOY_OUTPUT" | python3 -m json.tool 2>/dev/null || echo "$DEPLOY_OUTPUT"
else
    echo -e "${RED}✗ Deployment failed!${NC}"
    echo "$DEPLOY_OUTPUT"
    exit 1
fi
echo ""

# Step 6: Wait for Lambda to be active
echo -e "${YELLOW}[6/6] Waiting for Lambda to be active...${NC}"
sleep 3

LAMBDA_STATE=$(aws lambda get-function \
    --function-name "$FUNCTION_NAME" \
    --region "$REGION" \
    --query 'Configuration.State' \
    --output text 2>&1)

if [ "$LAMBDA_STATE" = "Active" ]; then
    echo -e "${GREEN}✓ Lambda is active and ready!${NC}"
elif [ "$LAMBDA_STATE" = "Pending" ]; then
    echo -e "${YELLOW}⏳ Lambda is pending... (this is normal)${NC}"
else
    echo -e "${YELLOW}⚠ Lambda state: $LAMBDA_STATE${NC}"
fi
echo ""

# Cleanup temp directory
rm -rf "$TEMP_DIR"
echo -e "${GREEN}✓ Cleaned up temporary files${NC}"
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Function: $FUNCTION_NAME"
echo "Region: $REGION"
echo "Package Size: $ZIP_SIZE"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Test the voice system by saying: 'List my projects'"
echo "2. Check Lambda logs: aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo ""
