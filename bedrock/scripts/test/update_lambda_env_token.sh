#!/bin/bash

# Update Lambda function environment variables with new bearer token
# This updates the BEARER_TOKEN in Lambda environment variables

set -e

REGION="${AWS_REGION:-us-east-1}"

# Lambda functions to update
FUNCTIONS=(
    "pf-scheduling-actions"
    "pf-information-actions"
)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Update Lambda Environment Variables${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}This will update BEARER_TOKEN in Lambda function environment variables.${NC}"
echo ""
echo "Functions to update:"
for func in "${FUNCTIONS[@]}"; do
    echo "  - $func"
done
echo ""

echo -e "${YELLOW}Please enter the new bearer token:${NC}"
read -r NEW_TOKEN

if [ -z "$NEW_TOKEN" ]; then
    echo -e "${RED}❌ No token provided. Exiting.${NC}"
    exit 1
fi

echo ""
read -p "Update Lambda functions with this token? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}❌ Update cancelled${NC}"
    exit 0
fi

echo ""
for func in "${FUNCTIONS[@]}"; do
    echo -e "${BLUE}🔄 Updating $func...${NC}"

    # Get current environment variables
    CURRENT_ENV=$(aws lambda get-function-configuration \
        --function-name "$func" \
        --region "$REGION" \
        --query 'Environment.Variables' \
        --output json 2>/dev/null)

    if [ -z "$CURRENT_ENV" ] || [ "$CURRENT_ENV" = "null" ]; then
        echo -e "${YELLOW}   ⚠️  No environment variables found for $func${NC}"
        continue
    fi

    # Update BEARER_TOKEN
    UPDATED_ENV=$(echo "$CURRENT_ENV" | jq --arg token "$NEW_TOKEN" '.BEARER_TOKEN = $token')

    # Update Lambda
    aws lambda update-function-configuration \
        --function-name "$func" \
        --region "$REGION" \
        --environment "Variables=$UPDATED_ENV" \
        --output json > /dev/null

    echo -e "${GREEN}   ✅ Updated $func${NC}"

    # Small delay between updates
    sleep 1
done

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ All Lambda functions updated!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "The new token will be used on the next Lambda invocation."
echo ""
echo "To test:"
echo "  cd bedrock/scripts"
echo "  ./test_agent_flow.py"
echo ""
