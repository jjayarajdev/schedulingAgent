#!/bin/bash

##############################################################################
# Disable Real API Mode for All Lambda Functions
#
# This script switches all Lambda functions back to mock API mode
# by updating the following environment variables:
#   - USE_MOCK_API=true
#   - ENABLE_REAL_CONFIRM=false
#   - ENABLE_REAL_CANCEL=false
#
# Functions updated:
#   - pf-scheduling-actions
#   - pf-information-actions
#   - pf-notes-actions
##############################################################################

set -e

REGION="${AWS_REGION:-us-east-1}"

# Lambda functions to update
FUNCTIONS=(
    "pf-scheduling-actions"
    "pf-information-actions"
    "pf-notes-actions"
)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}         Disable Real API Mode for Lambda Functions             ${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}This will update the following Lambda functions:${NC}"
for func in "${FUNCTIONS[@]}"; do
    echo -e "  ${CYAN}•${NC} $func"
done
echo ""
echo -e "${CYAN}Environment variables to be set:${NC}"
echo -e "  ${CYAN}•${NC} USE_MOCK_API=true"
echo -e "  ${CYAN}•${NC} ENABLE_REAL_CONFIRM=false"
echo -e "  ${CYAN}•${NC} ENABLE_REAL_CANCEL=false"
echo ""
echo -e "${YELLOW}⚠️  This will DISABLE real API calls and use mock data instead${NC}"
echo ""

read -p "Continue with disabling real API mode? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}❌ Operation cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Starting Lambda function updates...${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""

SUCCESS_COUNT=0
FAIL_COUNT=0

for func in "${FUNCTIONS[@]}"; do
    echo -e "${CYAN}📦 Processing $func...${NC}"

    # Get current environment variables
    echo -e "   ${BLUE}→${NC} Fetching current configuration..."
    CURRENT_ENV=$(aws lambda get-function-configuration \
        --function-name "$func" \
        --region "$REGION" \
        --query 'Environment.Variables' \
        --output json 2>/dev/null)

    if [ -z "$CURRENT_ENV" ] || [ "$CURRENT_ENV" = "null" ]; then
        echo -e "   ${RED}✗${NC} No environment variables found for $func"
        ((FAIL_COUNT++))
        echo ""
        continue
    fi

    # Show current mock status
    CURRENT_MOCK=$(echo "$CURRENT_ENV" | jq -r '.USE_MOCK_API // "not set"')
    echo -e "   ${BLUE}→${NC} Current USE_MOCK_API: $CURRENT_MOCK"

    # Update environment variables
    echo -e "   ${BLUE}→${NC} Updating to mock API mode..."
    UPDATED_ENV=$(echo "$CURRENT_ENV" | jq \
        '.USE_MOCK_API = "true" |
         .ENABLE_REAL_CONFIRM = "false" |
         .ENABLE_REAL_CANCEL = "false"')

    # Apply update
    UPDATE_RESULT=$(aws lambda update-function-configuration \
        --function-name "$func" \
        --region "$REGION" \
        --environment "Variables=$UPDATED_ENV" \
        --output json 2>&1)

    if [ $? -eq 0 ]; then
        echo -e "   ${GREEN}✓${NC} Successfully updated $func"
        ((SUCCESS_COUNT++))

        # Verify the update
        NEW_MOCK=$(echo "$UPDATE_RESULT" | jq -r '.Environment.Variables.USE_MOCK_API // "unknown"')
        echo -e "   ${GREEN}→${NC} Verified USE_MOCK_API: $NEW_MOCK"
    else
        echo -e "   ${RED}✗${NC} Failed to update $func"
        echo -e "   ${RED}Error:${NC} $UPDATE_RESULT"
        ((FAIL_COUNT++))
    fi

    echo ""

    # Small delay between updates
    sleep 2
done

echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Update Summary${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✓ Successful: $SUCCESS_COUNT${NC}"
if [ $FAIL_COUNT -gt 0 ]; then
    echo -e "${RED}✗ Failed: $FAIL_COUNT${NC}"
fi
echo ""

if [ $SUCCESS_COUNT -eq ${#FUNCTIONS[@]} ]; then
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ All Lambda functions successfully updated to mock API mode!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}The agents will now use mock data for all API calls.${NC}"
    echo ""
    echo -e "${CYAN}To re-enable real API mode:${NC}"
    echo -e "  ${BLUE}cd bedrock/scripts${NC}"
    echo -e "  ${BLUE}./enable_real_api.sh${NC}"
    echo ""
else
    echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}⚠️  Some updates failed. Please check errors above.${NC}"
    echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    exit 1
fi
