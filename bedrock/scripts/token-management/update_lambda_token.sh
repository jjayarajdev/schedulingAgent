#!/bin/bash
# Update Lambda with new Bearer token
# Usage: ./update_lambda_token.sh <ACCESS_TOKEN> [CLIENT_ID]

if [ -z "$1" ]; then
  echo "========================================="
  echo "Update Lambda Token"
  echo "========================================="
  echo ""
  echo "Usage: $0 <ACCESS_TOKEN> [CLIENT_ID]"
  echo ""
  echo "Example:"
  echo "  $0 'TaDWx6r5O0WE2tb5...' 11MT97PY"
  echo ""
  echo "To get a fresh token:"
  echo "  1. Go to https://pf.dev.projectsforce.com/"
  echo "  2. Log in with jay.jayakeerthy@syntegreti.com"
  echo "  3. Open DevTools (F12) → Network tab"
  echo "  4. Find 'token' request"
  echo "  5. Copy 'access_token' from Response"
  echo ""
  echo "See API_AUTHENTICATION_GUIDE.md for details"
  exit 1
fi

ACCESS_TOKEN="$1"
CLIENT_ID="${2:-11MT97PY}"

echo "========================================="
echo "Updating Lambda Function"
echo "========================================="
echo "Function: pf-information-actions"
echo "Client ID: $CLIENT_ID"
echo "Token: ${ACCESS_TOKEN:0:40}..."
echo ""

# Test the token first
echo "Step 1: Testing token validity..."
TEST_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -X GET "https://api-cx-portal.dev.projectsforce.com/dashboard/get/$CLIENT_ID/1645869" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json")

HTTP_CODE=$(echo "$TEST_RESPONSE" | grep "HTTP_CODE:" | cut -d':' -f2)

if [ "$HTTP_CODE" = "200" ]; then
  echo "✓ Token is valid (HTTP 200)"
  echo ""
elif [ "$HTTP_CODE" = "403" ]; then
  echo "✗ Token authentication failed (HTTP 403)"
  echo "  The token may be expired or invalid."
  echo "  Please get a fresh token from the browser."
  echo ""
  exit 1
elif [ "$HTTP_CODE" = "406" ]; then
  echo "✗ Session expired (HTTP 406)"
  echo "  Please get a fresh token from the browser."
  echo ""
  exit 1
else
  echo "⚠ Warning: Token test returned HTTP $HTTP_CODE"
  echo "  Proceeding anyway..."
  echo ""
fi

# Update Lambda
echo "Step 2: Updating Lambda environment variables..."

UPDATE_OUTPUT=$(aws lambda update-function-configuration \
  --function-name pf-information-actions \
  --environment "Variables={
    USE_MOCK_API=false,
    ENVIRONMENT=dev,
    BEARER_TOKEN=$ACCESS_TOKEN,
    DEFAULT_CLIENT_ID=$CLIENT_ID,
    LOG_LEVEL=INFO,
    DYNAMODB_TABLE_PREFIX=pf
  }" 2>&1)

if [ $? -eq 0 ]; then
  echo "✓ Lambda function updated successfully!"
  echo ""

  # Wait for update to complete
  echo "Step 3: Waiting for Lambda to be ready..."
  sleep 3

  aws lambda wait function-updated \
    --function-name pf-information-actions 2>/dev/null

  echo "✓ Lambda is ready"
  echo ""

  # Verify configuration
  echo "Step 4: Verifying configuration..."
  NEW_TOKEN=$(aws lambda get-function-configuration \
    --function-name pf-information-actions \
    --query 'Environment.Variables.BEARER_TOKEN' \
    --output text 2>/dev/null)

  NEW_CLIENT=$(aws lambda get-function-configuration \
    --function-name pf-information-actions \
    --query 'Environment.Variables.DEFAULT_CLIENT_ID' \
    --output text 2>/dev/null)

  if [ "${NEW_TOKEN:0:30}" = "${ACCESS_TOKEN:0:30}" ]; then
    echo "✓ Bearer token updated correctly"
  else
    echo "⚠ Warning: Token verification mismatch"
  fi

  if [ "$NEW_CLIENT" = "$CLIENT_ID" ]; then
    echo "✓ Client ID updated correctly: $NEW_CLIENT"
  else
    echo "⚠ Warning: Client ID is: $NEW_CLIENT"
  fi

  echo ""
  echo "========================================="
  echo "SUCCESS!"
  echo "========================================="
  echo ""
  echo "Lambda configuration:"
  echo "  Function: pf-information-actions"
  echo "  Bearer Token: ${NEW_TOKEN:0:40}..."
  echo "  Client ID: $NEW_CLIENT"
  echo "  Mock API: false (using real API)"
  echo ""
  echo "Token expires in: ~12 hours"
  echo "Next refresh needed: $(date -v+11H '+%Y-%m-%d %H:%M' 2>/dev/null || date -d '+11 hours' '+%Y-%m-%d %H:%M' 2>/dev/null || echo 'in 11 hours')"
  echo ""
  echo "To test the Lambda:"
  echo "  aws lambda invoke --function-name pf-information-actions \\"
  echo "    --payload '{\"apiPath\":\"/get-projects\",\"httpMethod\":\"POST\",\"actionGroup\":\"information\",\"parameters\":[{\"name\":\"customer_id\",\"value\":\"1645869\"}]}' \\"
  echo "    response.json && cat response.json | jq ."
  echo ""

else
  echo "✗ Failed to update Lambda function"
  echo ""
  echo "Error output:"
  echo "$UPDATE_OUTPUT"
  echo ""
  exit 1
fi
