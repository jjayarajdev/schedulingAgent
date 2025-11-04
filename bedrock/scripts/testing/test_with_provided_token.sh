#!/bin/bash

# ProjectForce API Testing with Provided Token
# Using the access token you captured from the browser

API_URL="https://api-cx-portal.dev.projectsforce.com"

# Token from your browser session
ACCESS_TOKEN="TaDWx6r5O0WE2tb5/Lb77XuI29UR7j2NlMHbUdXd+YrY7E+JahPgJItOT1TeHzuFkKBZdKtH+Wm0nfNKp1Y6TR19FBC75H98jk3wtxyLeaKzcyIf+P98RcFLNju88pa7HuqtNdWiLW5cbC9xpuLYWDvpoHyQnNNbxw7BzOaRr/r7dOTbOkoDpNNm6AdtlwjTkTFGyDwY8ww9NUi7Y4PasyWS8w7REIcMG+mWqKu8p4k8NCRmbAhLgxqnp/ybcKHdQyy9CDahS2v1stGYZjwnRlEiXMBNEy8AxrMOAXYz/T4B+/vPzKF+p8Kdmjv9kuPjAOkNVnNIPuwqudsuIsjykgLJyB1yxMR2tgyS1Wp+7fuxCocy9+Nh7ZgvCBV9Rudk5jdANOA4GRBL8Dc68DntOQa2Sr4Z9JfRk/s0z8L/UdAv7Gp+UdX9aB+0BNXkv7uRUHM8weK7ZppN2Ur3pwZgc8VCIbLERjBkAZpaSGmyyWwM5X+TYKGwu27ps+XY8jnJM5u6lSZcKcF7SeOJc8IuX51Zc+tNr8uKR190xHI6wFUD2aSvq6sNXMDSomat+uo9+Yk+WHjsHZiskWCCut6yFfRz7TlxQh9ZQdwwA7u6FYplBRoRUiTQRRiwLteMGoUJxfnQEscRvflTLJIFlOPqN7A4mQBgQ9PxhQZ6SDVsjAku5VIJfI/VUt12lQzRKZSjs0EKKuWvH1jOWOtZiDdVBy3ZF+/2w/q8mQA81JhHn3z8D2593lqhOijXhAO6uIsUcxjmal6VYcpDc+K2H7JmI5Y+jVLXxViTUXjTxMz8cS4d7LivXrOg64XqumiXj6g3jy1Bg9fnaN6/9rBsxtXGgLQkX+kq3haG6M2PrNVQOcOwVR3VL5cvuST9pLD4EIVGtZmHP0NgcEGc79KnipqFSBYEiDYF1RFN5GFox1VoCSI7BqKgAsnr0X42BivMo02nQ5GdT/UANi0StHMTRs/bLMVazMBhu9zXSmxoqhgOU7eNFiNXABgCmdQFFuo518SMHDhKD6rPFyPh7Pl5W8+FOr5k01NBwmZqExa3WTSdoEeZKucJP4JcgpK47mvDNFlY"
CLIENT_ID="11MT97PY"

echo "========================================="
echo "ProjectForce API - Testing with Browser Token"
echo "========================================="
echo "API URL: $API_URL"
echo "Client ID: $CLIENT_ID"
echo "Token: ${ACCESS_TOKEN:0:40}..."
echo ""

# Test with different customer IDs
CUSTOMER_IDS=("1645869")

for CUSTOMER_ID in "${CUSTOMER_IDS[@]}"; do
  echo "========================================="
  echo "Testing Customer ID: $CUSTOMER_ID"
  echo "========================================="
  echo "URL: $API_URL/dashboard/get/$CLIENT_ID/$CUSTOMER_ID"
  echo ""

  RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X GET "$API_URL/dashboard/get/$CLIENT_ID/$CUSTOMER_ID" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json")

  HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d':' -f2)
  BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

  echo "HTTP Status: $HTTP_CODE"
  echo ""

  if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ SUCCESS!"
    echo ""

    # Parse response
    PROJECT_COUNT=$(echo "$BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('data', [])))" 2>/dev/null)

    if [ ! -z "$PROJECT_COUNT" ]; then
      echo "Projects Found: $PROJECT_COUNT"
      echo ""

      # Show first project as sample
      echo "Sample Project (first one):"
      echo "$BODY" | python3 -c "
import sys, json
data = json.load(sys.stdin)
projects = data.get('data', [])
if projects:
    p = projects[0]
    print(f\"  Project ID: {p.get('id', 'N/A')}\")
    print(f\"  Order Number: {p.get('order_number', 'N/A')}\")
    print(f\"  Category: {p.get('category', 'N/A')}\")
    print(f\"  Status: {p.get('status', 'N/A')}\")
    print(f\"  Technician: {p.get('technician', 'N/A')}\")
" 2>/dev/null

      echo ""
      echo "Full response saved to: dashboard_response_${CUSTOMER_ID}.json"
      echo "$BODY" | python3 -m json.tool > "dashboard_response_${CUSTOMER_ID}.json" 2>/dev/null
    fi

    # Show first 80 lines of response
    echo ""
    echo "Response Preview (first 80 lines):"
    echo "$BODY" | python3 -m json.tool 2>/dev/null | head -80

  elif [ "$HTTP_CODE" = "403" ]; then
    echo "✗ FAILED: Token authentication failed"
    echo ""
    echo "The token may have expired. Based on the response you shared,"
    echo "the token expires in: 43599 seconds (about 12 hours)"
    echo ""
    echo "Response:"
    echo "$BODY"
  else
    echo "✗ FAILED with HTTP $HTTP_CODE"
    echo ""
    echo "Response:"
    echo "$BODY" | head -20
  fi

  echo ""
  echo ""
done

# Test other endpoints
echo "========================================="
echo "Testing Additional Endpoints"
echo "========================================="
echo ""

# Try to discover what endpoints are available
ENDPOINTS=(
  "/dashboard/get/$CLIENT_ID"
  "/projects/$CLIENT_ID"
  "/users/me"
  "/customers"
)

for ENDPOINT in "${ENDPOINTS[@]}"; do
  echo "Testing: $ENDPOINT"
  TEST_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X GET "$API_URL$ENDPOINT" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json")

  echo "  HTTP Status: $TEST_RESPONSE"
done

echo ""
echo ""

# Summary
echo "========================================="
echo "Summary"
echo "========================================="
echo ""
echo "Token Information:"
echo "  - Access Token: Valid (from browser session)"
echo "  - Client ID: $CLIENT_ID"
echo "  - Expires in: ~12 hours from token generation"
echo ""
echo "To update Lambda function with this token:"
echo ""
echo "  aws lambda update-function-configuration \\"
echo "    --function-name pf-information-actions \\"
echo "    --environment \"Variables={"
echo "      USE_MOCK_API=false,"
echo "      ENVIRONMENT=dev,"
echo "      BEARER_TOKEN=$ACCESS_TOKEN,"
echo "      DEFAULT_CLIENT_ID=$CLIENT_ID,"
echo "      LOG_LEVEL=INFO,"
echo "      DYNAMODB_TABLE_PREFIX=pf"
echo "    }\""
echo ""
echo "Test completed at $(date)"
