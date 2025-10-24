#!/bin/bash
#
# Lambda Deployment Package Builder
# Builds deployment packages for all Lambda functions
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Lambda Deployment Package Builder${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# Function to build a Lambda package
build_lambda() {
    local FUNCTION_NAME=$1
    local FUNCTION_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/$FUNCTION_NAME"

    if [ ! -d "$FUNCTION_DIR" ]; then
        echo -e "${RED}ERROR: Directory not found: $FUNCTION_DIR${NC}"
        return 1
    fi

    echo -e "${YELLOW}Building: $FUNCTION_NAME${NC}"
    cd "$FUNCTION_DIR"

    # Clean up old artifacts
    rm -f lambda.zip
    rm -rf package

    # Check if requirements.txt exists
    if [ -f "requirements.txt" ]; then
        echo "  → Installing dependencies..."

        # Create package directory
        mkdir -p package

        # Install dependencies
        pip install -r requirements.txt --target package/ --quiet

        # Create zip from package directory
        cd package
        zip -r ../lambda.zip . -q
        cd ..

        # Add source files
        if [ -f "handler.py" ]; then
            zip -g lambda.zip handler.py -q
        fi

        if [ -f "tcpa_service.py" ]; then
            zip -g lambda.zip tcpa_service.py -q
        fi

        # Clean up package directory
        rm -rf package
    else
        # No dependencies - just zip source files
        echo "  → No dependencies, zipping source files..."

        if [ -f "handler.py" ]; then
            zip lambda.zip handler.py -q
        fi

        if [ -f "tcpa_service.py" ]; then
            zip lambda.zip tcpa_service.py -q
        fi
    fi

    # Show zip size
    local SIZE=$(du -h lambda.zip | cut -f1)
    echo -e "  → ${GREEN}Package created: lambda.zip ($SIZE)${NC}"

    cd - > /dev/null
    echo ""
}

# Build all Lambda functions
echo "Building Lambda packages..."
echo ""

# SMS Inbound Processor
if [ -d "sms-inbound-processor" ]; then
    build_lambda "sms-inbound-processor"
fi

# TCPA Compliance (library, not Lambda)
# Skipping - this is included in sms-inbound-processor

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Build Complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Lambda packages created:"
echo "  • sms-inbound-processor/lambda.zip"
echo ""
echo "Next steps:"
echo "  1. cd infrastructure/terraform/sms"
echo "  2. terraform init"
echo "  3. terraform plan"
echo "  4. terraform apply"
echo ""
