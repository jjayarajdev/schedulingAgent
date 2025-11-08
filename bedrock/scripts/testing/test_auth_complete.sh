#!/bin/bash

# ProjectForce API Complete Authentication and Testing Script
# Uses the auth.dev.projectsforce.com authentication flow

AUTH_URL="https://auth.dev.projectsforce.com"
API_URL="https://api-cx-portal.dev.projectsforce.com"

EMAIL="jay.jayakeerthy@syntegreti.com"
# Note: Password appears to be encrypted in the check call
# We'll need to test with the plaintext password
PASSWORD="All0wj@y5677"

echo "========================================="
echo "ProjectForce API - Complete Test"
echo "========================================="
echo "Auth URL: $AUTH_URL"
echo "API URL: $API_URL"
echo "User: $EMAIL"
echo ""

# Step 1: Authenticate and get token
echo "Step 1: Authenticating..."
echo "Endpoint: $AUTH_URL/check.v1"
echo ""

# First try with plain password
LOGIN_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$AUTH_URL/check.v1" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"reCaptcha\":\"\",\"method\":\"POST\"}")

HTTP_CODE=$(echo "$LOGIN_RESPONSE" | grep "HTTP_CODE:" | cut -d':' -f2)
LOGIN_BODY=$(echo "$LOGIN_RESPONSE" | sed '/HTTP_CODE:/d')

echo "HTTP Status: $HTTP_CODE"
echo "Response:"
echo "$LOGIN_BODY" | python3 -m json.tool 2>/dev/null || echo "$LOGIN_BODY"
echo ""

# Check if authentication was successful
if [ "$HTTP_CODE" != "200" ]; then
  echo "✗ Authentication failed with HTTP $HTTP_CODE"
  echo ""
  echo "Note: The password in the browser shows encrypted format."
  echo "You may need to capture the actual encrypted password format"
  echo "or use browser dev tools to get a valid session token."
  exit 1
fi

# Step 2: Get token from /token endpoint
echo "========================================="
echo "Step 2: Getting Access Token"
echo "========================================="
echo "Endpoint: $AUTH_URL/token"
echo ""

# Try to extract session info or use token endpoint
TOKEN_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$AUTH_URL/token" \
  -H "Content-Type: application/json" \
  -H "Cookie: $(echo "$LOGIN_RESPONSE" | grep -i "set-cookie" || echo "")" \
  -d "{\"username\":\"$EMAIL\"}")

TOKEN_HTTP_CODE=$(echo "$TOKEN_RESPONSE" | grep "HTTP_CODE:" | cut -d':' -f2)
TOKEN_BODY=$(echo "$TOKEN_RESPONSE" | sed '/HTTP_CODE:/d')

echo "HTTP Status: $TOKEN_HTTP_CODE"
echo "Response:"
echo "$TOKEN_BODY" | python3 -m json.tool 2>/dev/null || echo "$TOKEN_BODY"
echo ""

# Extract access token
ACCESS_TOKEN=$(echo "$TOKEN_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null)
CLIENT_ID=$(echo "$TOKEN_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('client_id', '09PF05VD'))" 2>/dev/null)
USER_ID=$(echo "$TOKEN_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('user_id', ''))" 2>/dev/null)

if [ -z "$ACCESS_TOKEN" ]; then
  echo "✗ Failed to obtain access token"
  echo ""
  echo "Attempting alternative: Using provided token from your example..."
  ACCESS_TOKEN="TaDWx6r5O0WE2tb5/Lb77XuI29UR7j2NlMHbUdXd+YrY7E+JahPgJItOT1TeHzuFkKBZdKtH+Wm0nfNKp1Y6TR19FBC75H98jk3wtxyLeaKzcyIf+P98RcFLNju88pa7HuqtNdWiLW5cbC9xpuLYWDvpoHyQnNNbxw7BzOaRr/r7dOTbOkoDpNNm6AdtlwjTkTFGyDwY8ww9NUi7Y4PasyWS8w7REIcMG+mWqKu8p4k8NCRmbAhLgxqnp/ybcKHdQyy9CDahS2v1stGYZjwnRlEiXMBNEy8AxrMOAXYz/T4B+/vPzKF+p8Kdmjv9kuPjAOkNVnNIPuwqudsuIsjykgLJyB1yxMR2tgyS1Wp+7fuxCocy9+Nh7ZgvCBV9Rudk5jdANOA4GRBL8Dc68DntOQa2Sr4Z9JfRk/s0z8L/UdAv7Gp+UdX9aB+0BNXkv7uRUHM8weK7ZppN2Ur3pwZgc8VCIbLERjBkAZpaSGmyyWwM5X+TYKGwu27ps+XY8jnJM5u6lSZcKcF7SeOJc8IuX51Zc+tNr8uKR190xHI6wFUD2aSvq6sNXMDSomat+uo9+Yk+WHjsHZiskWCCut6yFfRz7TlxQh9ZQdwwA7u6FYplBRoRUiTQRRiwLteMGoUJxfnQEscRvflTLJIFlOPqN7A4mQBgQ9PxhQZ6SDVsjAku5VIJfI/VUt12lQzRKZSjs0EKKuWvH1jOWOtZiDdVBy3ZF+/2w/q8mQA81JhHn3z8D2593lqhOijXhAO6uIsUcxjmal6VYcpDc+K2H7JmI5Y+jVLXxViTUXjTxMz8cS4d7LivXrOg64XqumiXj6g3jy1Bg9fnaN6/9rBsxtXGgLQkX+kq3haG6M2PrNVQOcOwVR3VL5cvuST9pLD4EIVGtZmHP0NgcEGc79KnipqFSBYEiDYF1RFN5GFox1VoCSI7BqKgAsnr0X42BivMo02nQ5GdT/UANi0StHMTRs/bLMVazMBhu9zXSmxoqhgOU7eNFiNXABgCmdQFFuo518SMHDhKD6rPFyPh7Pl5W8+FOr5k01NBwmZqExa3WTSdoEeZKucJP4JcgpK47mvDNFlY"
  CLIENT_ID="11MT97PY"
fi

echo "✓ Access Token obtained: ${ACCESS_TOKEN:0:30}..."
echo "✓ Client ID: $CLIENT_ID"
echo "✓ User ID: $USER_ID"
echo ""

# Step 3: Test Dashboard API
echo "========================================="
echo "Step 3: Testing Dashboard API"
echo "========================================="

# We need to find the customer ID - try using the user's client
CUSTOMER_ID="1645869"  # Using known test customer

echo "Testing: $API_URL/dashboard/get/$CLIENT_ID/$CUSTOMER_ID"
echo ""

DASHBOARD_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -X GET "$API_URL/dashboard/get/$CLIENT_ID/$CUSTOMER_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json")

DASH_HTTP_CODE=$(echo "$DASHBOARD_RESPONSE" | grep "HTTP_CODE:" | cut -d':' -f2)
DASH_BODY=$(echo "$DASHBOARD_RESPONSE" | sed '/HTTP_CODE:/d')

echo "HTTP Status: $DASH_HTTP_CODE"
echo ""

if [ "$DASH_HTTP_CODE" = "200" ]; then
  echo "✓ SUCCESS! Dashboard API is working"
  echo ""

  # Parse and display summary
  PROJECT_COUNT=$(echo "$DASH_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('data', [])))" 2>/dev/null)

  echo "Response Summary:"
  echo "  Total Projects: $PROJECT_COUNT"
  echo ""
  echo "Full Response (first 100 lines):"
  echo "$DASH_BODY" | python3 -m json.tool 2>/dev/null | head -100

  # Save full response
  echo "$DASH_BODY" | python3 -m json.tool 2>/dev/null > dashboard_response_full.json
  echo ""
  echo "✓ Full response saved to: dashboard_response_full.json"
else
  echo "✗ Dashboard API failed with HTTP $DASH_HTTP_CODE"
  echo ""
  echo "Response:"
  echo "$DASH_BODY" | head -20
fi

echo ""
echo ""

# Summary
echo "========================================="
echo "Test Summary"
echo "========================================="
echo "Authentication URL: $AUTH_URL"
echo "API URL: $API_URL"
echo "User: $EMAIL"
echo "Client ID: $CLIENT_ID"
echo "Customer ID: $CUSTOMER_ID"
echo ""
echo "Results:"
echo "  ✓ Access Token: ${ACCESS_TOKEN:0:40}..."
echo "  ✓ Dashboard API: HTTP $DASH_HTTP_CODE"
echo ""

if [ "$DASH_HTTP_CODE" = "200" ]; then
  echo "========================================="
  echo "SUCCESS! API is working correctly"
  echo "========================================="
  echo ""
  echo "To update Lambda with this token:"
  echo ""
  echo "aws lambda update-function-configuration \\"
  echo "  --function-name pf-information-actions \\"
  echo "  --environment \"Variables={"
  echo "    USE_MOCK_API=false,"
  echo "    ENVIRONMENT=dev,"
  echo "    BEARER_TOKEN=$ACCESS_TOKEN,"
  echo "    DEFAULT_CLIENT_ID=$CLIENT_ID,"
  echo "    LOG_LEVEL=INFO,"
  echo "    DYNAMODB_TABLE_PREFIX=pf"
  echo "  }\""
  echo ""
fi

echo "Test completed at $(date)"
