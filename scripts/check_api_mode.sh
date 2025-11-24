#!/bin/bash

##############################################################################
# Check API Mode for All Lambda Functions
#
# This script displays the current API mode configuration for all Lambda functions
# showing whether they're using mock or real API calls.
##############################################################################

set -e

REGION="${AWS_REGION:-us-east-1}"

# Lambda functions to check
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
echo -e "${BLUE}         Lambda Functions API Mode Status                       ${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""

for func in "${FUNCTIONS[@]}"; do
    echo -e "${CYAN}📦 $func${NC}"
    echo -e "${BLUE}   ─────────────────────────────────────────────────────────${NC}"

    # Get environment variables
    ENV_VARS=$(aws lambda get-function-configuration \
        --function-name "$func" \
        --region "$REGION" \
        --query 'Environment.Variables' \
        --output json 2>/dev/null)

    if [ -z "$ENV_VARS" ] || [ "$ENV_VARS" = "null" ]; then
        echo -e "   ${RED}✗${NC} No environment variables found"
        echo ""
        continue
    fi

    # Extract relevant variables
    USE_MOCK=$(echo "$ENV_VARS" | jq -r '.USE_MOCK_API // "not set"')
    ENABLE_CONFIRM=$(echo "$ENV_VARS" | jq -r '.ENABLE_REAL_CONFIRM // "not set"')
    ENABLE_CANCEL=$(echo "$ENV_VARS" | jq -r '.ENABLE_REAL_CANCEL // "not set"')
    ENVIRONMENT=$(echo "$ENV_VARS" | jq -r '.ENVIRONMENT // "not set"')
    HAS_TOKEN=$(echo "$ENV_VARS" | jq -r '.BEARER_TOKEN // "not set"')

    if [ "$HAS_TOKEN" != "not set" ]; then
        TOKEN_STATUS="${GREEN}✓ configured${NC}"
    else
        TOKEN_STATUS="${RED}✗ not configured${NC}"
    fi

    # Display status
    echo -e "   ${CYAN}USE_MOCK_API:${NC}         $USE_MOCK"
    echo -e "   ${CYAN}ENABLE_REAL_CONFIRM:${NC}  $ENABLE_CONFIRM"
    echo -e "   ${CYAN}ENABLE_REAL_CANCEL:${NC}   $ENABLE_CANCEL"
    echo -e "   ${CYAN}ENVIRONMENT:${NC}          $ENVIRONMENT"
    echo -e "   ${CYAN}BEARER_TOKEN:${NC}         $TOKEN_STATUS"

    # Overall status
    if [ "$USE_MOCK" = "false" ]; then
        echo -e "   ${GREEN}→ Status: Real API Mode ENABLED${NC}"
    elif [ "$USE_MOCK" = "true" ]; then
        echo -e "   ${YELLOW}→ Status: Mock API Mode (Real API disabled)${NC}"
    else
        echo -e "   ${RED}→ Status: Unknown (USE_MOCK_API not set)${NC}"
    fi

    echo ""
done

echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}To enable real API mode:${NC}"
echo -e "  ${BLUE}cd bedrock/scripts${NC}"
echo -e "  ${BLUE}./enable_real_api.sh${NC}"
echo ""
echo -e "${CYAN}To disable real API mode (revert to mock):${NC}"
echo -e "  ${BLUE}cd bedrock/scripts${NC}"
echo -e "  ${BLUE}./disable_real_api.sh${NC}"
echo ""
