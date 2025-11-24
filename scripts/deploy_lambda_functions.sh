#!/bin/bash

################################################################################
# Lambda Functions Deployment Script
#
# This script automates the deployment of all 3 Lambda functions for the
# Bedrock Multi-Agent Scheduling System
#
# Usage: ./deploy_lambda_functions.sh
#
# Prerequisites:
# - AWS CLI configured with appropriate credentials
# - Python 3.11 installed
# - pip installed
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGION="${AWS_REGION:-us-east-1}"  # Must match Bedrock agents region
RUNTIME="python3.11"
TIMEOUT=30
MEMORY_SIZE=512
LAMBDA_ROLE_NAME="scheduling-agent-lambda-role"

# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Lambda Functions Deployment Script${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${GREEN}Account ID:${NC} $ACCOUNT_ID"
echo -e "${GREEN}Region:${NC} $REGION"
echo ""

################################################################################
# Step 1: Create IAM Role for Lambda (if not exists)
################################################################################

echo -e "${YELLOW}Step 1: Creating IAM Role for Lambda...${NC}"

if aws iam get-role --role-name $LAMBDA_ROLE_NAME &>/dev/null; then
    echo -e "${GREEN}✓ IAM role '$LAMBDA_ROLE_NAME' already exists${NC}"
else
    echo "Creating IAM role..."

    # Create role
    aws iam create-role \
      --role-name $LAMBDA_ROLE_NAME \
      --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
          "Effect": "Allow",
          "Principal": {"Service": "lambda.amazonaws.com"},
          "Action": "sts:AssumeRole"
        }]
      }' \
      --region $REGION

    # Attach basic execution policy
    aws iam attach-role-policy \
      --role-name $LAMBDA_ROLE_NAME \
      --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

    # Attach DynamoDB access (for future use)
    aws iam attach-role-policy \
      --role-name $LAMBDA_ROLE_NAME \
      --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

    # Attach Secrets Manager access (for PF360 API keys)
    aws iam attach-role-policy \
      --role-name $LAMBDA_ROLE_NAME \
      --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite

    echo -e "${GREEN}✓ IAM role created successfully${NC}"
    echo "Waiting 10 seconds for role propagation..."
    sleep 10
fi

LAMBDA_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${LAMBDA_ROLE_NAME}"
echo -e "${GREEN}Role ARN:${NC} $LAMBDA_ROLE_ARN"
echo ""

################################################################################
# Step 2: Package and Deploy Lambda Functions
################################################################################

echo -e "${YELLOW}Step 2: Packaging and Deploying Lambda Functions...${NC}"
echo ""

# Change to lambda directory
cd "$(dirname "$0")/../lambda"

# Array of Lambda functions
declare -a LAMBDAS=(
    "scheduling-actions"
    "information-actions"
    "notes-actions"
)

for LAMBDA_NAME in "${LAMBDAS[@]}"; do
    echo -e "${BLUE}──────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}Processing: $LAMBDA_NAME${NC}"
    echo -e "${BLUE}──────────────────────────────────────────────────${NC}"

    # Full function name
    FUNCTION_NAME="scheduling-agent-${LAMBDA_NAME}"

    # Navigate to Lambda directory
    cd "$LAMBDA_NAME"

    # Clean previous build
    echo "Cleaning previous build..."
    rm -rf package
    rm -rf venv
    rm -f ${LAMBDA_NAME}.zip

    # Create virtual environment for clean packaging
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate

    # Install dependencies in isolated environment
    echo "Installing dependencies..."
    if [ -f requirements.txt ]; then
        pip install -r requirements.txt -t package/ --quiet
        echo -e "${GREEN}✓ Dependencies installed${NC}"
    else
        echo -e "${YELLOW}⚠ No requirements.txt found, skipping dependency installation${NC}"
    fi

    # Deactivate venv
    deactivate

    # Copy Lambda code
    echo "Copying Lambda code..."
    cp handler.py package/
    cp config.py package/
    cp mock_data.py package/
    echo -e "${GREEN}✓ Code copied${NC}"

    # Create ZIP file
    echo "Creating deployment package..."
    cd package
    zip -r ../${LAMBDA_NAME}.zip . -q
    cd ..

    ZIP_SIZE=$(du -h ${LAMBDA_NAME}.zip | cut -f1)
    echo -e "${GREEN}✓ Package created: ${ZIP_SIZE}${NC}"

    # Check if Lambda function exists
    if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION &>/dev/null; then
        echo "Function exists, updating code..."

        aws lambda update-function-code \
          --function-name $FUNCTION_NAME \
          --zip-file fileb://${LAMBDA_NAME}.zip \
          --region $REGION \
          --output text &>/dev/null

        echo -e "${GREEN}✓ Function code updated${NC}"

        # Update environment variables
        echo "Updating environment variables..."
        aws lambda update-function-configuration \
          --function-name $FUNCTION_NAME \
          --environment "Variables={USE_MOCK_API=true}" \
          --timeout $TIMEOUT \
          --memory-size $MEMORY_SIZE \
          --region $REGION \
          --output text &>/dev/null

        echo -e "${GREEN}✓ Configuration updated${NC}"

    else
        echo "Function doesn't exist, creating..."

        # Wait for IAM role propagation
        echo "Waiting 15 seconds for IAM role propagation..."
        sleep 15

        if aws lambda create-function \
          --function-name $FUNCTION_NAME \
          --runtime $RUNTIME \
          --role $LAMBDA_ROLE_ARN \
          --handler handler.lambda_handler \
          --zip-file fileb://${LAMBDA_NAME}.zip \
          --timeout $TIMEOUT \
          --memory-size $MEMORY_SIZE \
          --environment "Variables={USE_MOCK_API=true}" \
          --region $REGION \
          --output json > /tmp/lambda-create-output.json 2>&1; then
            echo -e "${GREEN}✓ Function created${NC}"
        else
            echo -e "${RED}✗ Function creation failed${NC}"
            echo "Error details:"
            cat /tmp/lambda-create-output.json
            echo ""
            echo -e "${YELLOW}This might be due to:${NC}"
            echo "  1. IAM role not fully propagated (wait 30 seconds and retry)"
            echo "  2. Package too large (>50MB unzipped)"
            echo "  3. Missing permissions in IAM role"
            echo ""
            rm -f /tmp/lambda-create-output.json
            cd ..
            continue  # Skip to next function
        fi
    fi

    # Test the function
    echo "Testing function..."

    # Create test payload based on function type
    if [ "$LAMBDA_NAME" == "scheduling-actions" ]; then
        TEST_PAYLOAD='{"action":"list_projects","parameters":{}}'
    elif [ "$LAMBDA_NAME" == "information-actions" ]; then
        TEST_PAYLOAD='{"action":"get_working_hours","parameters":{}}'
    else
        TEST_PAYLOAD='{"action":"list_notes","parameters":{"project_id":"12345"}}'
    fi

    INVOKE_OUTPUT=$(mktemp)
    if aws lambda invoke \
      --function-name $FUNCTION_NAME \
      --payload "$TEST_PAYLOAD" \
      --region $REGION \
      $INVOKE_OUTPUT &>/dev/null; then

        # Check for errors in response
        if grep -q "errorMessage" $INVOKE_OUTPUT; then
            echo -e "${RED}✗ Function test failed${NC}"
            cat $INVOKE_OUTPUT
        else
            echo -e "${GREEN}✓ Function test passed${NC}"
        fi
    else
        echo -e "${RED}✗ Function invocation failed${NC}"
    fi
    rm -f $INVOKE_OUTPUT

    # Clean up
    echo "Cleaning up..."
    rm -rf package
    rm -rf venv

    # Get function ARN
    FUNCTION_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --region $REGION --query 'Configuration.FunctionArn' --output text)
    echo -e "${GREEN}Function ARN:${NC} $FUNCTION_ARN"

    echo ""
    cd ..
done

################################################################################
# Step 3: Grant Bedrock Permission to Invoke Lambda
################################################################################

echo -e "${YELLOW}Step 3: Granting Bedrock Permission to Invoke Lambda...${NC}"
echo ""

# Agent IDs (from your existing setup)
SCHEDULING_AGENT_ID="IX24FSMTQH"
INFORMATION_AGENT_ID="C9ANXRIO8Y"
NOTES_AGENT_ID="G5BVBYEPUM"

# Function to get agent ID for a function name (bash 3.2 compatible)
get_agent_id() {
    case "$1" in
        "scheduling-agent-scheduling-actions")
            echo "$SCHEDULING_AGENT_ID"
            ;;
        "scheduling-agent-information-actions")
            echo "$INFORMATION_AGENT_ID"
            ;;
        "scheduling-agent-notes-actions")
            echo "$NOTES_AGENT_ID"
            ;;
    esac
}

# List of Lambda functions
LAMBDA_FUNCTIONS=(
    "scheduling-agent-scheduling-actions"
    "scheduling-agent-information-actions"
    "scheduling-agent-notes-actions"
)

# Grant permissions for each function
for FUNCTION_NAME in "${LAMBDA_FUNCTIONS[@]}"; do
    AGENT_ID=$(get_agent_id "$FUNCTION_NAME")

    # Skip if function doesn't exist
    if ! aws lambda get-function --function-name $FUNCTION_NAME --region $REGION &>/dev/null; then
        echo -e "${YELLOW}⚠ Function $FUNCTION_NAME doesn't exist, skipping...${NC}"
        continue
    fi

    STATEMENT_ID="bedrock-invoke-$(echo $FUNCTION_NAME | cut -d'-' -f3)"

    echo "Granting permission for $FUNCTION_NAME (Agent: $AGENT_ID)..."

    # Remove existing permission if it exists
    aws lambda remove-permission \
      --function-name $FUNCTION_NAME \
      --statement-id $STATEMENT_ID \
      --region $REGION &>/dev/null || true

    # Add new permission
    aws lambda add-permission \
      --function-name $FUNCTION_NAME \
      --statement-id $STATEMENT_ID \
      --action lambda:InvokeFunction \
      --principal bedrock.amazonaws.com \
      --source-arn "arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent/${AGENT_ID}" \
      --region $REGION \
      --output text &>/dev/null

    echo -e "${GREEN}✓ Permission granted for agent $AGENT_ID${NC}"
done

echo ""

################################################################################
# Step 4: Summary
################################################################################

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "${BLUE}Deployed Functions:${NC}"
echo "  1. scheduling-agent-scheduling-actions"
echo "  2. scheduling-agent-information-actions"
echo "  3. scheduling-agent-notes-actions"
echo ""
echo -e "${BLUE}Function ARNs:${NC}"
aws lambda list-functions \
  --region $REGION \
  --query "Functions[?starts_with(FunctionName, 'scheduling-agent-')].FunctionArn" \
  --output table

echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Update Bedrock Agent action groups with Lambda ARNs (via console)"
echo "2. Prepare each agent (wait 30-60 seconds)"
echo "3. Test in Bedrock console"
echo ""
echo -e "${BLUE}To test, run:${NC}"
echo "  aws lambda invoke --function-name scheduling-agent-scheduling-actions \\"
echo "    --payload '{\"action\":\"list_projects\",\"parameters\":{}}' \\"
echo "    --region $REGION output.json && cat output.json"
echo ""
echo -e "${GREEN}All done! 🎉${NC}"
