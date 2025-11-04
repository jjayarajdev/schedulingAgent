#!/bin/bash

# Get fresh access token using refresh token
# Based on OAuth2 refresh token flow

AUTH_URL="https://auth.dev.projectsforce.com"
API_URL="https://api-cx-portal.dev.projectsforce.com"

# From localStorage
REFRESH_TOKEN="AWldtvQhQ+wt4HhRcU/2mOjT5Lsh5NKD+Zt//mXFQitxS8KqH5JefG65bVcirEXRIX2F3u3QXUz/inSZiFRNPA=="
CLIENT_ID="devapps"
CLIENT_SECRET="devappssecret"

echo "========================================="
echo "Getting Fresh Access Token"
echo "========================================="
echo "Using refresh_token from localStorage"
echo ""

# Try to get new access token with refresh token
echo "POST $AUTH_URL/token"
echo "Grant type: refresh_token"
echo ""

RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$AUTH_URL/token" \
  -H "Content-Type: application/json" \
  -d "{
    \"grant_type\": \"refresh_token\",
    \"refresh_token\": \"$REFRESH_TOKEN\",
    \"client_id\": \"$CLIENT_ID\",
    \"client_secret\": \"$CLIENT_SECRET\"
  }")

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d':' -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

echo "HTTP Status: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ SUCCESS! Got new access token"
    echo ""

    # Parse response
    ACCESS_TOKEN=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)
    NEW_REFRESH=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('refresh_token', ''))" 2>/dev/null)
    EXPIRES_IN=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('expires_in', ''))" 2>/dev/null)

    echo "Access Token: ${ACCESS_TOKEN:0:50}..."
    echo "Refresh Token: ${NEW_REFRESH:0:50}..."
    echo "Expires In: $EXPIRES_IN seconds"
    echo ""

    # Test the new token
    echo "Testing new token against Dashboard API..."
    echo ""

    TEST_RESPONSE=$(curl -s -X GET "$API_URL/dashboard/get/09PF05VD/1645869" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json")

    PROJECT_COUNT=$(echo "$TEST_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('data', [])))" 2>/dev/null)

    if [ ! -z "$PROJECT_COUNT" ] && [ "$PROJECT_COUNT" != "0" ]; then
        echo "✓ Token is working! Found $PROJECT_COUNT projects"
        echo ""

        # Save to file
        echo "$BODY" | python3 -m json.tool > fresh_token_data.json 2>/dev/null
        echo "✓ Token data saved to: fresh_token_data.json"
        echo ""

        echo "========================================="
        echo "To update Lambda:"
        echo "========================================="
        echo ""
        echo "aws lambda update-function-configuration \\"
        echo "  --function-name pf-information-actions \\"
        echo "  --environment \"Variables={"
        echo "    USE_MOCK_API=false,"
        echo "    ENVIRONMENT=dev,"
        echo "    BEARER_TOKEN=$ACCESS_TOKEN,"
        echo "    DEFAULT_CLIENT_ID=09PF05VD,"
        echo "    LOG_LEVEL=INFO,"
        echo "    DYNAMODB_TABLE_PREFIX=pf"
        echo "  }\""
        echo ""
    else
        echo "✗ Token obtained but not working!"
        echo "Response: $TEST_RESPONSE"
    fi
else
    echo "✗ Failed to get new token"
    echo ""
    echo "Response:"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
fi

echo ""
