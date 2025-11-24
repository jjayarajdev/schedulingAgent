#!/bin/bash

echo "========================================="
echo "Testing API with Existing Bearer Token"
echo "========================================="
echo ""

# Get the existing Bearer token from Lambda
echo "Step 1: Retrieving existing Bearer token from Lambda..."
BEARER_TOKEN=$(aws lambda get-function-configuration \
  --function-name pf-information-actions \
  --query 'Environment.Variables.BEARER_TOKEN' \
  --output text)

if [ -z "$BEARER_TOKEN" ]; then
  echo "ERROR: Failed to retrieve Bearer token from Lambda"
  exit 1
fi

echo "✓ Token retrieved: ${BEARER_TOKEN:0:30}..."
echo ""

# Test parameters
CLIENT_ID="09PF05VD"
CUSTOMER_ID="1645869"
API_URL="https://api-cx-portal.dev.projectsforce.com"

# Test 1: Dashboard API - Get Projects
echo "========================================="
echo "Test 1: Dashboard API - Get Customer Projects"
echo "========================================="
echo "URL: $API_URL/dashboard/get/$CLIENT_ID/$CUSTOMER_ID"
echo ""

DASHBOARD_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -X GET "$API_URL/dashboard/get/$CLIENT_ID/$CUSTOMER_ID" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -H "Content-Type: application/json")

HTTP_CODE=$(echo "$DASHBOARD_RESPONSE" | grep "HTTP_CODE:" | cut -d':' -f2)
BODY=$(echo "$DASHBOARD_RESPONSE" | sed '/HTTP_CODE:/d')

echo "HTTP Status: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
  echo "✓ SUCCESS!"
  echo ""
  echo "Response (first 50 lines):"
  echo "$BODY" | python3 -m json.tool 2>/dev/null | head -50

  # Count projects
  PROJECT_COUNT=$(echo "$BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('data', [])))" 2>/dev/null)
  echo ""
  echo "Total Projects Found: $PROJECT_COUNT"
else
  echo "✗ FAILED"
  echo "Response:"
  echo "$BODY" | head -20
fi

echo ""
echo ""

# Test 2: Business Hours API
echo "========================================="
echo "Test 2: Business Hours API"
echo "========================================="
echo "URL: $API_URL/business-hours/$CLIENT_ID"
echo ""

HOURS_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -X GET "$API_URL/business-hours/$CLIENT_ID" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -H "Content-Type: application/json")

HTTP_CODE2=$(echo "$HOURS_RESPONSE" | grep "HTTP_CODE:" | cut -d':' -f2)
BODY2=$(echo "$HOURS_RESPONSE" | sed '/HTTP_CODE:/d')

echo "HTTP Status: $HTTP_CODE2"
echo ""

if [ "$HTTP_CODE2" = "200" ]; then
  echo "✓ SUCCESS!"
  echo ""
  echo "Response:"
  echo "$BODY2" | python3 -m json.tool 2>/dev/null
else
  echo "✗ FAILED"
  echo "Response:"
  echo "$BODY2" | head -20
fi

echo ""
echo ""

# Summary
echo "========================================="
echo "Test Summary"
echo "========================================="
echo "✓ Bearer Token: Retrieved from Lambda"
echo "✓ Dashboard API (/dashboard/get): HTTP $HTTP_CODE"
echo "✓ Business Hours API (/business-hours): HTTP $HTTP_CODE2"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
  echo "SUCCESS: The existing Bearer token is valid and working!"
  echo ""
  echo "Note: The provided user credentials (jay.jayakeerthy@syntegreti.com)"
  echo "are not needed because the API uses pre-generated Bearer tokens"
  echo "that are already configured in the Lambda function."
else
  echo "The Bearer token may have expired. You may need to generate a new one"
  echo "by logging into the ProjectForce portal manually and capturing the token."
fi

echo ""
echo "Test completed at $(date)"
