#!/bin/bash
# Test Suite 5: Scheduling Operations
# Covers: Schedule, reschedule, cancel workflows

source test_config.sh

SESSION_ID="test-suite-5-$(date +%s)"

echo ""
echo "=========================================="
echo "Test Suite 5: Scheduling Operations"
echo "=========================================="
echo "Session ID: $SESSION_ID"
echo ""

# Test 1: List new/unscheduled projects
echo "📝 Test 5.1: User asks for new projects"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show me projects that need to be scheduled",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 2

# Test 2: Get details of first unscheduled
echo "📝 Test 5.2: User asks for details of first one"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "tell me about the first one",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 2

# Test 3: Schedule the project
echo "📝 Test 5.3: User schedules the project"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "schedule it for December 15th at 9am",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 2

# Test 4: List scheduled projects
echo "📝 Test 5.4: User checks scheduled projects"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show me all scheduled projects",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 2

# Test 5: Reschedule
echo "📝 Test 5.5: User reschedules the 2nd project"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "can you reschedule the 2nd project to December 20th at 2pm?",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 2

# Test 6: Confirm changes
echo "📝 Test 5.6: User asks to see updated schedule"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show me the updated schedule for that project",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"

echo "=========================================="
echo "Test Suite 5 Completed"
echo "=========================================="
