#!/bin/bash
# Quick Test Script - Run common test scenarios
# Usage: ./run_quick_tests.sh

# Load configuration
source test_config.sh

echo ""
echo "=========================================="
echo "Running Quick Tests"
echo "=========================================="
echo ""

# Single session for the entire user conversation
SESSION_ID="quick-test-$(date +%s)"

echo "User Session ID: $SESSION_ID"
echo "(In real world: one user = one persistent session)"
echo ""

# Test 1: Greeting
echo "📝 Test 1: Greeting (Chitchat Agent)"
echo "Expected: Supervisor → Chitchat Agent (~11s)"
echo ""
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "hello",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"

# Test 2: List Projects
echo "📝 Test 2: List Projects (Direct Lambda)"
echo "Expected: Direct Lambda → pf-information-actions (~3s)"
echo ""
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show my projects",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"

# Test 3: Filter Scheduled Projects
echo "📝 Test 3: Filter Scheduled Projects (Direct Lambda)"
echo "Expected: Direct Lambda → pf-information-actions (~3s)"
echo ""
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show scheduled projects",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"

# Test 4: Get Project Details
echo "📝 Test 4: Get Project Details (Direct Lambda)"
echo "Expected: Direct Lambda → pf-information-actions (~3s)"
echo ""
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show details for the 1st project",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"

echo "=========================================="
echo "Quick Tests Completed"
echo "=========================================="
