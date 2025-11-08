#!/bin/bash
# Test the bearer token directly against ProjectForce API

TOKEN="$1"
CLIENT_ID="${2:-09PF05VD}"
USER_ID="${3:-1646085}"

if [ -z "$TOKEN" ]; then
    echo "Usage: ./test_token_direct.sh <bearer_token> [client_id] [user_id]"
    exit 1
fi

echo "Testing ProjectForce API with provided token..."
echo "Client ID: $CLIENT_ID"
echo "User ID: $USER_ID"
echo ""

echo "=== Testing Dashboard API ==="
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://api-cx-portal.dev.projectsforce.com/dashboard/get/$CLIENT_ID/$USER_ID" | head -100

echo ""
echo "=== Testing Token Validation ===" 
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://api-cx-portal.dev.projectsforce.com/authentication/token/$USER_ID?identifier=projectsforce-validation"
