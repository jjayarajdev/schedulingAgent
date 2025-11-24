#!/bin/bash
# Test Redis connection with multi-turn conversation

# Load config
source /Users/jjayaraj/workspaces/studios/projectsforce/bedrock/testing/test_config.sh

SESSION="redis-test-$(date +%s)"

echo "=========================================="
echo "Testing Redis Connection with Multi-turn"
echo "=========================================="
echo ""
echo "Session ID: $SESSION"
echo ""

echo "Step 1: List projects (should store in Redis)"
echo "----------------------------------------------"
RESPONSE1=$(curl -s -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show my projects",
    "session_id": "'"$SESSION"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }')

echo "$RESPONSE1" | jq -r '.response' | head -3
echo ""
echo "Projects returned: $(echo "$RESPONSE1" | jq -r '.projects | length') projects"
echo ""

sleep 2

echo "Step 2: Get details by position (should retrieve from Redis)"
echo "-------------------------------------------------------------"
RESPONSE2=$(curl -s -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show details for the 1st project",
    "session_id": "'"$SESSION"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }')

echo "$RESPONSE2" | jq '.'
echo ""
echo "=========================================="
echo "Test Complete"
echo "=========================================="
