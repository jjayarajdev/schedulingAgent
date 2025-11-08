#!/bin/bash

# ProjectForce API Test Script
# Testing against: https://projectsforce-validation.cx-portal.dev.projectsforce.com

# Portal URL for authentication
PORTAL_URL="https://projectsforce-validation.cx-portal.dev.projectsforce.com"
# API URL for data access
API_URL="https://api-cx-portal.dev.projectsforce.com"

EMAIL="jay.jayakeerthy@syntegreti.com"
PASSWORD="All0wj@y5677"
CLIENT_ID="09PF05VD"

echo "========================================="
echo "ProjectForce API Authentication Test"
echo "========================================="
echo "Portal URL: $PORTAL_URL"
echo "API URL: $API_URL"
echo "User: $EMAIL"
echo ""

# Step 1: Login and get Bearer token
echo "Step 1: Authenticating via Portal..."
LOGIN_RESPONSE=$(curl -s -X POST "$PORTAL_URL/api/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

echo "Login Response:"
echo "$LOGIN_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$LOGIN_RESPONSE"
echo ""

# Extract token
TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "ERROR: Failed to obtain authentication token"
  exit 1
fi

echo "✓ Authentication successful"
echo "Token: ${TOKEN:0:20}..."
echo ""

# Step 2: Get Customer ID from token (if available in response)
CUSTOMER_ID=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('user', {}).get('customer_id', '1645869'))" 2>/dev/null)
if [ -z "$CUSTOMER_ID" ]; then
  CUSTOMER_ID="1645869"  # Default test customer
fi
echo "Using Customer ID: $CUSTOMER_ID"
echo ""

# Step 2: Test Dashboard API - Get Customer Projects
echo "========================================="
echo "Step 2: Testing Dashboard API (Customer Projects)"
echo "========================================="
DASHBOARD_RESPONSE=$(curl -s -X GET "$API_URL/dashboard/get/$CLIENT_ID/$CUSTOMER_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

echo "Dashboard Response:"
echo "$DASHBOARD_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$DASHBOARD_RESPONSE"
echo ""

# Count projects if successful
PROJECT_COUNT=$(echo "$DASHBOARD_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('data', [])))" 2>/dev/null)
if [ ! -z "$PROJECT_COUNT" ]; then
  echo "✓ Found $PROJECT_COUNT projects"
  echo ""
fi

# Step 3: Test Business Hours API
echo "========================================="
echo "Step 3: Testing Business Hours API"
echo "========================================="
HOURS_RESPONSE=$(curl -s -X GET "$API_URL/business-hours/$CLIENT_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

echo "Business Hours Response:"
echo "$HOURS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HOURS_RESPONSE"
echo ""

# Step 4: Test Get Single Project (if we have projects)
if [ ! -z "$PROJECT_COUNT" ] && [ "$PROJECT_COUNT" -gt "0" ]; then
  echo "========================================="
  echo "Step 4: Testing Single Project Details"
  echo "========================================="
  # Extract first project ID
  PROJECT_ID=$(echo "$DASHBOARD_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', [{}])[0].get('id', ''))" 2>/dev/null)

  if [ ! -z "$PROJECT_ID" ]; then
    echo "Testing with Project ID: $PROJECT_ID"
    PROJECT_RESPONSE=$(curl -s -X GET "$API_URL/dashboard/get/$CLIENT_ID/$CUSTOMER_ID?project_id=$PROJECT_ID" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json")

    echo "Project Details Response:"
    echo "$PROJECT_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$PROJECT_RESPONSE"
    echo ""
  fi
fi

# Summary
echo "========================================="
echo "Test Summary"
echo "========================================="
echo "✓ Login: Success"
echo "✓ Token: ${TOKEN:0:30}..."
echo "✓ Customer ID: $CUSTOMER_ID"
echo "✓ Client ID: $CLIENT_ID"
echo "✓ Dashboard API: $([ ! -z "$PROJECT_COUNT" ] && echo "$PROJECT_COUNT projects found" || echo 'No projects or error')"
echo "✓ Business Hours API: $([ ! -z "$HOURS_RESPONSE" ] && echo 'Response received' || echo 'No response')"
echo "✓ Project Details API: $([ ! -z "$PROJECT_RESPONSE" ] && echo 'Response received' || echo 'Skipped or error')"
echo ""
echo "Test completed at $(date)"
echo ""
echo "To use this token in Lambda, update environment variable:"
echo "BEARER_TOKEN=$TOKEN"
