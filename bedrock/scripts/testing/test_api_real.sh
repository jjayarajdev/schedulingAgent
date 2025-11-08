#!/bin/bash

# ProjectForce API Test Script - UPDATED FOR NEW API ENDPOINTS
# Using OAuth2 authentication flow with real API endpoints

# OAuth2 + API URLs
AUTH_URL="https://auth.dev.projectsforce.com"
API_URL="https://api.dev.projectsforce.com"

CLIENT_ID="web-client"
CLIENT_SECRET="77mq6MbaNyU0Gzz7SV1zXx"
USERNAME="jay@mailinator.com"
PASSWORD="All0wj@y5677"  # Plaintext password (encrypted version: U2FsdGVkX1/ZiR9CNgR3SeEgf5MHKaC1npGOA+P5PTY=)
PF_CLIENT_ID="09PF05VD"
PF_USER_ID="6f72bffa-c323-4058-a01c-9d495d696364"
DEVICE_TYPE="1"

echo "========================================="
echo "ProjectForce Real API Test (OAuth2)"
echo "========================================="
echo "Auth URL: $AUTH_URL"
echo "API URL: $API_URL"
echo "Username: $USERNAME"
echo ""

# Step 1: Get OAuth2 token
echo "Step 1: Getting OAuth2 Access Token..."
TOKEN_RESPONSE=$(curl -s -X POST "$AUTH_URL/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&username=$USERNAME&password=$PASSWORD&client_id=$CLIENT_ID&client_secret=$CLIENT_SECRET")

echo "Token Response:"
echo "$TOKEN_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$TOKEN_RESPONSE"
echo ""

# Extract access token
ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ -z "$ACCESS_TOKEN" ]; then
  echo "❌ ERROR: Failed to obtain access token"
  echo "Response: $TOKEN_RESPONSE"
  exit 1
fi

echo "✅ Authentication successful"
echo "Access Token: ${ACCESS_TOKEN:0:30}..."
echo ""

# Step 2: Test Dashboard API - Get Customer Projects (NEW ENDPOINT)
echo "========================================="
echo "Step 2: Testing Dashboard API (NEW)"
echo "========================================="
echo "Endpoint: GET $API_URL/cx-scheduled/projects/$PF_USER_ID"
echo ""

DASHBOARD_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X GET \
  "$API_URL/cx-scheduled/projects/$PF_USER_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json")

# Split response and status
HTTP_BODY=$(echo "$DASHBOARD_RESPONSE" | sed -e 's/HTTP_STATUS\:.*//g')
HTTP_STATUS=$(echo "$DASHBOARD_RESPONSE" | tr -d '\n' | sed -e 's/.*HTTP_STATUS://')

echo "HTTP Status: $HTTP_STATUS"
echo "Dashboard Response:"
echo "$HTTP_BODY" | python3 -m json.tool 2>/dev/null || echo "$HTTP_BODY"
echo ""

# Count projects if successful
if [ "$HTTP_STATUS" = "200" ]; then
  PROJECT_COUNT=$(echo "$HTTP_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('data', [])))" 2>/dev/null)
  if [ ! -z "$PROJECT_COUNT" ]; then
    echo "✅ Found $PROJECT_COUNT projects"

    # Show first 3 projects
    echo ""
    echo "First 3 Projects:"
    echo "$HTTP_BODY" | python3 -c "
import sys, json
data = json.load(sys.stdin)
projects = data.get('data', [])
for i, p in enumerate(projects[:3], 1):
    print(f\"{i}. {p.get('project_type_project_type', 'Unknown')} at {p.get('installation_address_full_address', 'N/A')}\")
    print(f\"   Status: {p.get('status_info_status', 'N/A')} | Project ID: {p.get('project_project_id', 'N/A')}\")
" 2>/dev/null
  fi
else
  echo "❌ Dashboard API failed with status: $HTTP_STATUS"
fi

echo ""

# Step 3: Test Business Hours API (NEW ENDPOINT)
echo "========================================="
echo "Step 3: Testing Business Hours API (NEW)"
echo "========================================="
echo "Endpoint: GET $API_URL/system/client-details/$PF_CLIENT_ID/business-hours"
echo ""

HOURS_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X GET \
  "$API_URL/system/client-details/$PF_CLIENT_ID/business-hours" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json")

# Split response and status
HOURS_BODY=$(echo "$HOURS_RESPONSE" | sed -e 's/HTTP_STATUS\:.*//g')
HOURS_STATUS=$(echo "$HOURS_RESPONSE" | tr -d '\n' | sed -e 's/.*HTTP_STATUS://')

echo "HTTP Status: $HOURS_STATUS"
echo "Business Hours Response:"
echo "$HOURS_BODY" | python3 -m json.tool 2>/dev/null || echo "$HOURS_BODY"
echo ""

if [ "$HOURS_STATUS" = "200" ]; then
  echo "✅ Business Hours API successful"
else
  echo "❌ Business Hours API failed with status: $HOURS_STATUS"
fi

echo ""

# Summary
echo "========================================="
echo "Test Summary"
echo "========================================="
echo "✅ OAuth2 Authentication: Success"
echo "   Access Token: ${ACCESS_TOKEN:0:40}..."
echo ""
echo "API Test Results:"
echo "  Dashboard API (/cx-scheduled/projects): $([ "$HTTP_STATUS" = "200" ] && echo "✅ SUCCESS ($PROJECT_COUNT projects)" || echo "❌ FAILED (HTTP $HTTP_STATUS)")"
echo "  Business Hours API (/system/client-details): $([ "$HOURS_STATUS" = "200" ] && echo "✅ SUCCESS" || echo "❌ FAILED (HTTP $HOURS_STATUS)")"
echo ""
echo "User Context:"
echo "  PF Client ID: $PF_CLIENT_ID"
echo "  PF User ID: $PF_USER_ID"
echo ""
echo "Test completed at $(date)"
echo ""

# Save token for Lambda testing
if [ "$HTTP_STATUS" = "200" ]; then
  echo "========================================="
  echo "Testing Lambda Handler with Real Token"
  echo "========================================="
  cd "$(dirname "$0")"
  python3 test_lambda_direct.py "$ACCESS_TOKEN"
fi
