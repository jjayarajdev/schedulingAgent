#!/bin/bash

EMAIL="jay.jayakeerthy@syntegreti.com"
PASSWORD="All0wj@y5677"
API_URL="https://api-cx-portal.dev.projectsforce.com"

echo "Testing various authentication endpoints..."
echo ""

# Test different possible endpoints
endpoints=(
  "/login"
  "/api/login"
  "/api/auth/login"
  "/auth"
  "/authenticate"
  "/api/authenticate"
  "/api/v1/login"
  "/api/v1/auth/login"
)

for endpoint in "${endpoints[@]}"; do
  echo "========================================="
  echo "Testing: $endpoint"
  echo "========================================="

  response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$API_URL$endpoint" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

  http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d':' -f2)
  body=$(echo "$response" | sed '/HTTP_CODE:/d')

  echo "HTTP Code: $http_code"
  echo "Response:"
  echo "$body" | head -10
  echo ""

  # Check if we got a successful response
  if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
    echo "✓ SUCCESS! This endpoint works!"
    echo "Full response:"
    echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    break
  fi
done

echo ""
echo "Testing complete"
