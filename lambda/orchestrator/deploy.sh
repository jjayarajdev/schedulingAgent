#!/bin/bash

###############################################################################
# Orchestrator Lambda Deployment Script
###############################################################################

set -e  # Exit on error

# Configuration
FUNCTION_NAME="pf-orchestrator"
REGION="us-east-1"
RUNTIME="python3.11"
HANDLER="handler.lambda_handler"
MEMORY_SIZE=512
TIMEOUT=30

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "================================================================================"
echo "Deploying Orchestrator Lambda: ${FUNCTION_NAME}"
echo "================================================================================"
echo ""

# Step 1: Create temporary package directory
echo -e "${YELLOW}Step 1:${NC} Creating package directory..."
PACKAGE_DIR="/tmp/orchestrator-package-$(date +%s)"
mkdir -p "$PACKAGE_DIR"
echo -e "${GREEN}✓${NC} Package directory created: $PACKAGE_DIR"
echo ""

# Step 2: Install dependencies
echo -e "${YELLOW}Step 2:${NC} Installing dependencies..."
pip3 install -r requirements.txt -t "$PACKAGE_DIR" --quiet
echo -e "${GREEN}✓${NC} Dependencies installed"
echo ""

# Step 3: Copy Python modules
echo -e "${YELLOW}Step 3:${NC} Copying Python modules..."
cp *.py "$PACKAGE_DIR/"
echo -e "${GREEN}✓${NC} Modules copied:"
ls -1 "$PACKAGE_DIR"/*.py | xargs -n1 basename
echo ""

# Step 4: Create deployment package
echo -e "${YELLOW}Step 4:${NC} Creating deployment ZIP..."
ZIP_FILE="/tmp/${FUNCTION_NAME}-$(date +%Y%m%d-%H%M%S).zip"
cd "$PACKAGE_DIR"
zip -r "$ZIP_FILE" . > /dev/null
cd - > /dev/null
ZIP_SIZE=$(du -h "$ZIP_FILE" | cut -f1)
echo -e "${GREEN}✓${NC} Deployment package created: $ZIP_FILE ($ZIP_SIZE)"
echo ""

# Step 5: Check if Lambda function exists
echo -e "${YELLOW}Step 5:${NC} Checking if Lambda function exists..."
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Function exists, updating code..."

    # Update function code
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://$ZIP_FILE" \
        --region "$REGION" \
        > /dev/null

    echo -e "${GREEN}✓${NC} Function code updated"
    echo ""

    echo -e "${YELLOW}Note:${NC} Environment variables NOT updated. To update environment, use:"
    echo "  aws lambda update-function-configuration --function-name $FUNCTION_NAME --environment Variables={KEY=VALUE,...}"
else
    echo -e "${RED}✗${NC} Function does not exist"
    echo ""
    echo -e "${YELLOW}Creating new function requires:${NC}"
    echo "  - VPC configuration (subnets, security groups)"
    echo "  - IAM role ARN"
    echo "  - Environment variables"
    echo ""
    echo "Please create the function manually via AWS Console or use CloudFormation/Terraform."
    echo "After creation, run this script again to update the code."
    exit 1
fi

# Step 6: Wait for update to complete
echo -e "${YELLOW}Step 6:${NC} Waiting for update to complete..."
aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION"
echo -e "${GREEN}✓${NC} Update completed"
echo ""

# Step 7: Get function details
echo -e "${YELLOW}Step 7:${NC} Function details:"
aws lambda get-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --region "$REGION" \
    --query '{FunctionName:FunctionName,Runtime:Runtime,Handler:Handler,MemorySize:MemorySize,Timeout:Timeout,LastModified:LastModified}' \
    --output table
echo ""

# Step 8: Cleanup
echo -e "${YELLOW}Step 8:${NC} Cleaning up..."
rm -rf "$PACKAGE_DIR"
echo -e "${GREEN}✓${NC} Temporary files removed (keeping ZIP: $ZIP_FILE)"
echo ""

echo "================================================================================"
echo -e "${GREEN}Deployment successful!${NC}"
echo "================================================================================"
echo ""
echo "Function Name: $FUNCTION_NAME"
echo "Region: $REGION"
echo "Package Size: $ZIP_SIZE"
echo ""
echo "Next steps:"
echo "  1. Test the function via API Gateway or AWS Console"
echo "  2. Monitor CloudWatch Logs: aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo "  3. Check metrics in CloudWatch console"
echo ""
