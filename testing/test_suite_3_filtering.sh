#!/bin/bash
# Test Suite 3: Advanced Filtering
# Covers: Multiple filter criteria and combinations

source test_config.sh

SESSION_ID="test-suite-3-$(date +%s)"

echo ""
echo "=========================================="
echo "Test Suite 3: Advanced Filtering"
echo "=========================================="
echo "Session ID: $SESSION_ID"
echo ""

# Test 1: List all projects first
echo "📝 Test 3.1: User requests all projects"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show all my projects",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 2

# Test 2: Filter by status
echo "📝 Test 3.2: User filters by status (scheduled)"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "filter for scheduled status",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 2

# Test 3: Filter by category
echo "📝 Test 3.3: User filters by category (Decking)"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show me Decking projects only",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 2

# Test 4: Filter by project type
echo "📝 Test 3.4: User filters by project type"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "just the Call Back projects please",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 2

# Test 5: Reset to all
echo "📝 Test 3.5: User asks to see all again"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show me all of them again",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 2

# Test 6: Count projects
echo "📝 Test 3.6: User asks how many projects"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "how many projects do I have in total?",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"

echo "=========================================="
echo "Test Suite 3 Completed"
echo "=========================================="
