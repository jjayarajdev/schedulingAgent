#!/bin/bash
# Test Suite 6: Notes Functionality
# Covers: Add Note → List Notes → Context-Aware Notes

source test_config.sh

SESSION_ID="test-suite-6-$(date +%s)"

echo ""
echo "=========================================="
echo "Test Suite 6: Notes Functionality"
echo "=========================================="
echo "Session ID: $SESSION_ID"
echo ""

# Test 1: List projects to get a project_id
echo "📝 Test 6.1: Get list of projects for testing"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show me my projects",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 3

# Test 2: Add note with explicit project ID
echo "📝 Test 6.2: Add note to project 7751741"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Add a note to project 7751741 saying Customer prefers morning appointments",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 3

# Test 3: List notes for project
echo "📝 Test 6.3: List all notes for project 7751741"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show me all notes for project 7751741",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 3

# Test 4: Add another note to same project
echo "📝 Test 6.4: Add second note to project 7751741"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "add note to project 7751741: Customer has a dog, gate at entrance",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 3

# Test 5: List notes again (should show 2 notes)
echo "📝 Test 6.5: List notes again (should show 2 notes)"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "list notes for 7751741",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 3

# Test 6: Context-aware note (after viewing project details)
echo "📝 Test 6.6: View project details to set context"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show details for project 7751744",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 3

# Test 7: Add note using context (no explicit project ID)
echo "📝 Test 6.7: Add note using context (refers to project 7751744)"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "add a note saying customer wants blue siding",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 3

# Test 8: List notes for the context project
echo "📝 Test 6.8: Show notes for that project (context-aware)"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show notes for that project",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 3

# Test 9: Add note with different author
echo "📝 Test 6.9: Add note specifying author"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "add note to project 7751741: Technician confirmed tools needed for install",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 3

# Test 10: List all notes for first project (should show 3 notes)
echo "📝 Test 6.10: List all notes for project 7751741 (should have 3 notes)"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show all notes for project 7751741",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"

echo ""
echo "=========================================="
echo "Test Suite 6 Complete"
echo "=========================================="
echo "Total Tests: 10"
echo "- 2 setup tests (list projects, get details)"
echo "- 4 add note tests (explicit ID, context-aware)"
echo "- 4 list notes tests (single project, multiple notes)"
echo ""
