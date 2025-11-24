#!/bin/bash
# Test Suite 1: Basic Project Workflow
# Covers: List → Filter → Details → Schedule

source test_config.sh

SESSION_ID="test-suite-1-$(date +%s)"

echo ""
echo "=========================================="
echo "Test Suite 1: Basic Project Workflow"
echo "=========================================="
echo "Session ID: $SESSION_ID"
echo ""

# Test 1: Greeting
echo "📝 Test 1.1: User greets the system"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "hi there",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 2

# Test 2: List all projects
echo "📝 Test 1.2: User asks for all projects"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show me all my projects",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 2

# Test 3: Filter by status
echo "📝 Test 1.3: User filters for new projects"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show me only the new ones",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 2

# Test 4: Get details using context
echo "📝 Test 1.4: User asks for details of 2nd project"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "give me details about the 2nd project",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 2

# Test 5: Schedule project
echo "📝 Test 1.5: User schedules the project"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "schedule this project for tomorrow at 2pm",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"

echo "=========================================="
echo "Test Suite 1 Completed"
echo "=========================================="
