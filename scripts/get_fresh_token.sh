#!/usr/bin/env bash
###############################################################################
# Get Fresh ProjectForce API Token
#
# This script helps you get a valid bearer token from ProjectForce
###############################################################################

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}Get Fresh ProjectForce API Token${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Method 1: From Browser DevTools
echo -e "${YELLOW}Method 1: Get from Browser (Recommended)${NC}"
echo ""
echo "1. Open ProjectForce in your browser:"
echo "   https://cx-portal.dev.projectsforce.com"
echo ""
echo "2. Log in with your credentials"
echo ""
echo "3. Open Browser DevTools (F12 or Right-Click → Inspect)"
echo ""
echo "4. Go to: Application tab → Storage → Local Storage"
echo "   → https://cx-portal.dev.projectsforce.com"
echo ""
echo "5. Look for one of these keys:"
echo "   - access_token"
echo "   - bearer_token"
echo "   - authToken"
echo "   - token"
echo ""
echo "6. Copy the value (starts with 'eyJ...')"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "Have you copied the token? Press Enter when ready, or Ctrl+C to exit... "
echo ""

# Prompt for token
echo -e "${BLUE}Paste your bearer token:${NC}"
read -p "> " BEARER_TOKEN

if [[ -z "$BEARER_TOKEN" ]]; then
    echo -e "${RED}❌ Token cannot be empty${NC}"
    exit 1
fi

# Validate token format (should start with eyJ)
if [[ ! "$BEARER_TOKEN" =~ ^eyJ ]]; then
    echo -e "${YELLOW}⚠️  Warning: Token doesn't start with 'eyJ' - this might not be a valid JWT token${NC}"
    read -p "Continue anyway? (y/N): " CONTINUE
    if [[ ! "$CONTINUE" =~ ^[Yy] ]]; then
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}✓ Token captured${NC}"
echo ""
echo "Token preview: ${BEARER_TOKEN:0:50}..."
echo ""

# Test the token
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}Testing Token${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

API_URL="https://api-cx-portal.dev.projectsforce.com"
CLIENT_ID="09PF05VD"
USER_ID="1645869"

echo "Testing with API endpoint..."
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "Content-Type: application/json" \
    "$API_URL/api/customers/$USER_ID/clients/$CLIENT_ID/projects")

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d':' -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

echo ""
if [[ "$HTTP_CODE" == "200" ]]; then
    echo -e "${GREEN}✅ Token is valid!${NC}"
    echo ""

    # Count projects
    PROJECT_COUNT=$(echo "$BODY" | jq -r '.data.projects | length' 2>/dev/null || echo "0")
    echo "Found $PROJECT_COUNT projects"
    echo ""

    # Update Secrets Manager
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}Update AWS Secrets Manager?${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    read -p "Do you want to update the secret 'projectforce/api/credentials' with this token? (y/N): " UPDATE_SECRET

    if [[ "$UPDATE_SECRET" =~ ^[Yy] ]]; then
        echo ""
        echo "Updating secret..."

        SECRET_VALUE=$(cat <<EOF
{
  "bearer_token": "$BEARER_TOKEN",
  "client_id": "$CLIENT_ID",
  "user_id": "$USER_ID",
  "refresh_token": "",
  "api_base_url": "$API_URL"
}
EOF
)

        aws secretsmanager update-secret \
            --secret-id "projectforce/api/credentials" \
            --secret-string "$SECRET_VALUE" \
            --region us-east-1 \
            &>/dev/null && echo -e "${GREEN}✅ Secret updated successfully${NC}" || echo -e "${RED}❌ Failed to update secret${NC}"

        echo ""
        echo "You can now run:"
        echo "  ./scripts/test_agents.sh"
        echo ""
    else
        echo ""
        echo "To update manually later, run:"
        echo ""
        echo "export PF_BEARER_TOKEN=\"$BEARER_TOKEN\""
        echo "export PF_CLIENT_ID=\"$CLIENT_ID\""
        echo "export PF_USER_ID=\"$USER_ID\""
        echo "./scripts/DEPLOY.sh"
        echo ""
    fi

elif [[ "$HTTP_CODE" == "401" ]] || [[ "$HTTP_CODE" == "403" ]]; then
    echo -e "${RED}❌ Token is invalid or expired (HTTP $HTTP_CODE)${NC}"
    echo ""
    echo "The token was rejected by the API. Please:"
    echo "1. Make sure you're logged in to ProjectForce"
    echo "2. Get a fresh token from the browser"
    echo "3. Run this script again"
    echo ""
else
    echo -e "${YELLOW}⚠️  Unexpected response (HTTP $HTTP_CODE)${NC}"
    echo ""
    echo "Response:"
    echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
