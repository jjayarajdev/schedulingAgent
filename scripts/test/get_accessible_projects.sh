#!/bin/bash

# Get list of projects accessible with current credentials
# This helps identify which project IDs you can use for testing

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Get Accessible Projects${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check for existing token scripts
if [ -f "$SCRIPT_DIR/get_token_with_refresh.sh" ]; then
    echo -e "${BLUE}Found get_token_with_refresh.sh${NC}"
    echo -e "${YELLOW}Getting fresh token...${NC}"
    TOKEN_RESPONSE=$("$SCRIPT_DIR/get_token_with_refresh.sh" 2>&1)
    TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o 'Bearer .*' | sed 's/Bearer //')
elif [ -f "$SCRIPT_DIR/test_api_live.sh" ]; then
    echo -e "${YELLOW}⚠️  Please enter your bearer token manually:${NC}"
    read -r TOKEN
else
    echo -e "${YELLOW}Please enter your bearer token:${NC}"
    read -r TOKEN
fi

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ No token available. Exiting.${NC}"
    exit 1
fi

CLIENT_ID="${1:-09PF05VD}"
USER_ID="${2:-1646085}"

echo ""
echo -e "${BLUE}Testing with:${NC}"
echo "  Client ID: $CLIENT_ID"
echo "  User ID: $USER_ID"
echo "  Token: ${TOKEN:0:30}...${TOKEN: -10}"
echo ""

echo -e "${BLUE}🔍 Fetching dashboard/projects...${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    "https://api-cx-portal.dev.projectsforce.com/dashboard/get/$CLIENT_ID/$USER_ID")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Success! (HTTP 200)${NC}"
    echo ""

    # Try to parse projects
    if command -v jq &> /dev/null; then
        # Check if response is JSON array
        if echo "$BODY" | jq -e 'type == "array"' &>/dev/null; then
            PROJECT_COUNT=$(echo "$BODY" | jq 'length')
            echo -e "${GREEN}Found $PROJECT_COUNT projects${NC}"
            echo ""

            # Extract project IDs and names
            echo -e "${BLUE}Available Projects:${NC}"
            echo "$BODY" | jq -r '.[] | "\(.project_id // .id // "N/A") - \(.project_name // .name // "No Name")"' | head -20

            echo ""
            echo -e "${YELLOW}Project IDs you can use for testing:${NC}"
            echo "$BODY" | jq -r '.[].project_id // .[].id' | head -10 | tr '\n' ', ' | sed 's/,$/\n/'

        elif echo "$BODY" | jq -e 'type == "object"' &>/dev/null; then
            # Response is an object, might contain projects array
            if echo "$BODY" | jq -e '.projects' &>/dev/null; then
                PROJECT_COUNT=$(echo "$BODY" | jq '.projects | length')
                echo -e "${GREEN}Found $PROJECT_COUNT projects${NC}"
                echo ""

                echo -e "${BLUE}Available Projects:${NC}"
                echo "$BODY" | jq -r '.projects[] | "\(.project_id // .id) - \(.project_name // .name)"' | head -20

                echo ""
                echo -e "${YELLOW}Project IDs you can use:${NC}"
                echo "$BODY" | jq -r '.projects[] | .project_id // .id' | head -10 | tr '\n' ', ' | sed 's/,$/\n/'
            else
                echo -e "${YELLOW}Response structure:${NC}"
                echo "$BODY" | jq '.' | head -50
            fi
        else
            echo -e "${YELLOW}Unexpected response format:${NC}"
            echo "$BODY" | head -50
        fi
    else
        echo -e "${YELLOW}jq not installed. Raw response:${NC}"
        echo "$BODY" | head -50
    fi

elif [ "$HTTP_CODE" = "403" ]; then
    echo -e "${RED}❌ Access Forbidden (HTTP 403)${NC}"
    echo -e "${YELLOW}Token is expired or invalid.${NC}"
    echo ""
    echo "Response:"
    echo "$BODY"
    echo ""
    echo "Please get a fresh token using:"
    echo "  ./get_token_with_refresh.sh"

elif [ "$HTTP_CODE" = "401" ]; then
    echo -e "${RED}❌ Unauthorized (HTTP 401)${NC}"
    echo -e "${YELLOW}Authentication failed.${NC}"
    echo ""
    echo "Response:"
    echo "$BODY"

else
    echo -e "${RED}❌ Request failed (HTTP $HTTP_CODE)${NC}"
    echo ""
    echo "Response:"
    echo "$BODY" | head -20
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}API Endpoint Tested:${NC}"
echo "  https://api-cx-portal.dev.projectsforce.com/dashboard/get/$CLIENT_ID/$USER_ID"
echo -e "${BLUE}========================================${NC}"
echo ""
