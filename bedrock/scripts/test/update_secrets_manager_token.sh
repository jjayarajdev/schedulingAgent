#!/bin/bash

# Update AWS Secrets Manager with fresh ProjectForce API token
# This script updates the bearer token stored in Secrets Manager that Lambda functions use

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRET_NAME="projectforce/api/credentials"
REGION="${AWS_REGION:-us-east-1}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Update AWS Secrets Manager Token${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install it first.${NC}"
    exit 1
fi

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${RED}❌ jq not found. Please install it first.${NC}"
    exit 1
fi

echo -e "${YELLOW}This script will update the bearer token in AWS Secrets Manager.${NC}"
echo -e "${YELLOW}Lambda functions use this token to call ProjectForce API.${NC}"
echo ""

# Get current secret value
echo -e "${BLUE}📋 Fetching current secret...${NC}"
CURRENT_SECRET=$(aws secretsmanager get-secret-value \
    --secret-id "$SECRET_NAME" \
    --region "$REGION" \
    --query 'SecretString' \
    --output text 2>/dev/null || echo "{}")

if [ "$CURRENT_SECRET" = "{}" ]; then
    echo -e "${YELLOW}⚠️  Secret not found or empty. Will create new secret.${NC}"
else
    echo -e "${GREEN}✅ Current secret found${NC}"
    # Show first 50 chars of current token (masked)
    CURRENT_TOKEN=$(echo "$CURRENT_SECRET" | jq -r '.bearer_token // empty' 2>/dev/null || echo "")
    if [ -n "$CURRENT_TOKEN" ]; then
        TOKEN_PREVIEW="${CURRENT_TOKEN:0:30}...${CURRENT_TOKEN: -10}"
        echo -e "   Current token: ${TOKEN_PREVIEW}"
    fi
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Option 1: Enter Token Manually${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Please enter the new bearer token:${NC}"
read -r NEW_TOKEN

if [ -z "$NEW_TOKEN" ]; then
    echo -e "${RED}❌ No token provided. Exiting.${NC}"
    exit 1
fi

# Validate token format (basic check)
if [ ${#NEW_TOKEN} -lt 50 ]; then
    echo -e "${YELLOW}⚠️  Warning: Token seems too short (${#NEW_TOKEN} chars). Are you sure?${NC}"
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo -e "${BLUE}📝 Preparing secret update...${NC}"

# Create secret JSON
SECRET_JSON=$(jq -n \
    --arg token "$NEW_TOKEN" \
    '{
        "bearer_token": $token,
        "api_base_url": "https://api-cx-portal.dev.projectsforce.com",
        "updated_at": (now | strftime("%Y-%m-%d %H:%M:%S UTC")),
        "updated_by": "update_secrets_manager_token.sh"
    }')

echo ""
echo -e "${YELLOW}Secret structure:${NC}"
echo "$SECRET_JSON" | jq -r 'del(.bearer_token) + {"bearer_token": "***REDACTED***"}'
echo ""

read -p "Update Secrets Manager with this token? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}❌ Update cancelled${NC}"
    exit 0
fi

# Update secret
echo ""
echo -e "${BLUE}🔄 Updating secret in AWS Secrets Manager...${NC}"

if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$REGION" &>/dev/null; then
    # Secret exists, update it
    aws secretsmanager update-secret \
        --secret-id "$SECRET_NAME" \
        --secret-string "$SECRET_JSON" \
        --region "$REGION" \
        --description "ProjectForce API credentials - Updated $(date)" \
        >/dev/null

    echo -e "${GREEN}✅ Secret updated successfully!${NC}"
else
    # Secret doesn't exist, create it
    aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --secret-string "$SECRET_JSON" \
        --region "$REGION" \
        --description "ProjectForce API credentials" \
        >/dev/null

    echo -e "${GREEN}✅ Secret created successfully!${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Testing Token${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Test the token
echo -e "${BLUE}🧪 Testing token against ProjectForce API...${NC}"
TEST_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $NEW_TOKEN" \
    -H "Content-Type: application/json" \
    "https://api-cx-portal.dev.projectsforce.com/dashboard/get/09PF05VD/1646085")

HTTP_CODE=$(echo "$TEST_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$TEST_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Token is valid! (HTTP $HTTP_CODE)${NC}"
    echo ""
    echo -e "${GREEN}Response preview:${NC}"
    echo "$RESPONSE_BODY" | jq -r '. | if type == "array" then "Found \(length) projects" else . end' 2>/dev/null || echo "$RESPONSE_BODY" | head -5
elif [ "$HTTP_CODE" = "403" ]; then
    echo -e "${RED}❌ Token is invalid or expired (HTTP 403 Forbidden)${NC}"
    echo -e "${YELLOW}⚠️  Secret was updated but token doesn't work. Please get a fresh token.${NC}"
elif [ "$HTTP_CODE" = "401" ]; then
    echo -e "${RED}❌ Token authentication failed (HTTP 401 Unauthorized)${NC}"
else
    echo -e "${YELLOW}⚠️  Unexpected response (HTTP $HTTP_CODE)${NC}"
    echo "Response: $RESPONSE_BODY" | head -3
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Next Steps${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}✅ Secret updated in AWS Secrets Manager${NC}"
echo ""
echo "Lambda functions will now use the new token on their next invocation."
echo ""
echo "To test the integration:"
echo "  cd bedrock/scripts"
echo "  ./test_agent_flow.py"
echo ""
echo "To update Lambda environment variables (optional):"
echo "  cd bedrock/testing/ui"
echo "  ./update_lambda_env_token.sh"
echo ""
