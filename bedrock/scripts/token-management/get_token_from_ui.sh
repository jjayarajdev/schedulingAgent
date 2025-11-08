#!/bin/bash
# Extract token from test UI console

echo "=================================================="
echo "Getting Token from Test UI"
echo "=================================================="
echo ""
echo "Please open the Test UI at http://localhost:3000"
echo "Open browser console (F12) and run:"
echo ""
echo "  localStorage.getItem('pf_access_token')"
echo ""
echo "Then paste the token here:"
read -r TOKEN

if [ -z "$TOKEN" ]; then
    echo "❌ No token provided"
    exit 1
fi

echo ""
echo "✅ Token received: ${TOKEN:0:20}..."
echo ""
echo "Testing with CURL..."
echo "=================================================="

# Test the ProjectForce API with CURL
curl -X GET "https://api.dev.projectsforce.com/cx-scheduled/projects/6f72bffa-c323-4058-a01c-9d495d696364" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -w "\n\nHTTP Status: %{http_code}\n" \
  2>/dev/null | python3 -m json.tool 2>/dev/null || cat

echo ""
echo "=================================================="
echo "Now testing Lambda handler with this token..."
echo "=================================================="

cd "$(dirname "$0")"
python3 test_lambda_direct.py "$TOKEN"
