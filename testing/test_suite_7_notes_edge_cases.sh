#!/bin/bash
# Test Suite 7: Notes Edge Cases
# Tests error handling, special characters, and boundary conditions

source test_config.sh

SESSION_ID="test-suite-7-$(date +%s)"

echo ""
echo "=========================================="
echo "Test Suite 7: Notes Edge Cases"
echo "=========================================="
echo "Session ID: $SESSION_ID"
echo ""

# ============================================================================
# Category 1: Input Validation Edge Cases
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Category 1: Input Validation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test 1: Empty note text
echo "📝 Test 7.1: Add note with empty text (should fail)"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "add a note to project 7751741 saying ",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 3

# Test 2: Very long note text (>2000 chars per OpenAPI spec)
LONG_TEXT="This is a very long note that exceeds the maximum length. $(printf 'a%.0s' {1..2100})"
echo "📝 Test 7.2: Add note exceeding 2000 character limit"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "add note to project 7751741: '"${LONG_TEXT:0:200}"'...",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 3

# Test 3: Non-existent project ID
echo "📝 Test 7.3: Add note to non-existent project"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "add a note to project 9999999999 saying test note",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 3

# Test 4: Invalid project ID format
echo "📝 Test 7.4: Add note with invalid project ID format"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "add note to project ABC123XYZ saying test",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 3

# ============================================================================
# Category 2: Special Characters and Encoding
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Category 2: Special Characters & Encoding"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test 5: Note with special characters
echo "📝 Test 7.5: Add note with special characters"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "add note to project 7751741: Customer said \"Call me at 555-1234\" & wants 50% discount!",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 3

# Test 6: Note with emojis
echo "📝 Test 7.6: Add note with emojis"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "add note to project 7751741: Customer is 😊 happy with service! 👍",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 3

# Test 7: Note with newlines/multiline
echo "📝 Test 7.7: Add note with newline characters"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "add note to project 7751741: Line 1: Customer called\nLine 2: Wants appointment\nLine 3: Will call back",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 3

# Test 8: Note with single quotes and apostrophes
echo "📝 Test 7.8: Add note with apostrophes and quotes"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": \"add note to project 7751741: Customer's name is O'Brien, he said 'call tomorrow'\",
    \"session_id\": \"$SESSION_ID\",
    \"pf_token\": \"$PF_TOKEN\",
    \"pf_client_id\": \"$PF_CLIENT_ID\",
    \"pf_user_id\": $PF_USER_ID
  }"
echo -e "\n\n"
sleep 3

# Test 9: Note with HTML/Script tags (injection test)
echo "📝 Test 7.9: Add note with HTML tags (security test)"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "add note to project 7751741: <script>alert(\"test\")</script> Customer note",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 3

# ============================================================================
# Category 3: List Notes Edge Cases
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Category 3: List Notes Boundary Conditions"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test 10: List notes for project with no notes
echo "📝 Test 7.10: List notes for project with no notes"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show notes for project 7751742",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 3

# Test 11: List notes for non-existent project
echo "📝 Test 7.11: List notes for non-existent project"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "list notes for project 9999999999",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 3

# ============================================================================
# Category 4: Context and Ambiguity Edge Cases
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Category 4: Context & Ambiguity Handling"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test 12: Add note without any project context
echo "📝 Test 7.12: Add note without project context (should ask for clarification)"
SESSION_ID_FRESH="test-suite-7-fresh-$(date +%s)"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "add a note saying customer called",
    "session_id": "'"$SESSION_ID_FRESH"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 3

# Test 13: Ambiguous project reference
echo "📝 Test 7.13: Add note with ambiguous project reference"
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "add note to the first project saying needs callback",
    "session_id": "'"$SESSION_ID"'",
    "pf_token": "'"$PF_TOKEN"'",
    "pf_client_id": "'"$PF_CLIENT_ID"'",
    "pf_user_id": '"$PF_USER_ID"'
  }'
echo -e "\n\n"
sleep 3

# ============================================================================
# Category 5: Performance and Stress Tests
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Category 5: Performance & Stress Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test 14: Add multiple notes rapidly (concurrent-like behavior)
echo "📝 Test 7.14: Add 5 notes rapidly to same project"
for i in {1..5}; do
  curl -X POST "$API_ENDPOINT" \
    -H "Content-Type: application/json" \
    -d '{
      "message": "add note to project 7751741: Rapid note '"$i"'",
      "session_id": "'"$SESSION_ID"'-rapid-'"$i"'",
      "pf_token": "'"$PF_TOKEN"'",
      "pf_client_id": "'"$PF_CLIENT_ID"'",
      "pf_user_id": '"$PF_USER_ID"'
    }' &
done
wait
echo -e "\n\n"
sleep 5

# Test 15: List notes after stress test
echo "📝 Test 7.15: List all notes after rapid additions"
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
echo "Test Suite 7 Complete"
echo "=========================================="
echo "Total Tests: 15"
echo "Categories:"
echo "  - Input Validation: 4 tests"
echo "  - Special Characters: 5 tests"
echo "  - List Notes Boundaries: 2 tests"
echo "  - Context Handling: 2 tests"
echo "  - Performance: 2 tests"
echo ""
echo "Expected Failures/Warnings:"
echo "  - Test 7.1: Empty note text"
echo "  - Test 7.2: Note exceeding 2000 chars"
echo "  - Test 7.12: Note without project context"
echo ""
echo "Security Tests:"
echo "  - Test 7.9: HTML/script injection"
echo ""
