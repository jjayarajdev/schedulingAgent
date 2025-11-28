#!/bin/bash
# Test Suite 2: Context Resolution & Multi-turn Conversation
# Covers: Complex context tracking with pronouns and references

source test_config.sh

SESSION_ID="test-suite-2-$(date +%s)"

echo ""
echo "=========================================="
echo "Test Suite 2: Context Resolution"
echo "=========================================="
echo "Session ID: $SESSION_ID"
echo ""

# Test 1: Initial query
echo " Test 2.1: User asks for scheduled projects"
curl -X POST "$API_ENDPOINT" \
 -H "Content-Type: application/json" \
 -d '{
 "message": "what projects do I have scheduled?",
 "session_id": "'"$SESSION_ID"'",
 "pf_token": "'"$PF_TOKEN"'",
 "pf_client_id": "'"$PF_CLIENT_ID"'",
 "pf_user_id": '"$PF_USER_ID"'
 }'
echo -e "\n\n"
sleep 2

# Test 2: Reference using ordinal
echo " Test 2.2: User references 'the first one'"
curl -X POST "$API_ENDPOINT" \
 -H "Content-Type: application/json" \
 -d '{
 "message": "tell me more about the first one",
 "session_id": "'"$SESSION_ID"'",
 "pf_token": "'"$PF_TOKEN"'",
 "pf_client_id": "'"$PF_CLIENT_ID"'",
 "pf_user_id": '"$PF_USER_ID"'
 }'
echo -e "\n\n"
sleep 2

# Test 3: Implicit reference
echo " Test 2.3: User asks 'what time was that scheduled for?'"
curl -X POST "$API_ENDPOINT" \
 -H "Content-Type: application/json" \
 -d '{
 "message": "what time was that scheduled for?",
 "session_id": "'"$SESSION_ID"'",
 "pf_token": "'"$PF_TOKEN"'",
 "pf_client_id": "'"$PF_CLIENT_ID"'",
 "pf_user_id": '"$PF_USER_ID"'
 }'
echo -e "\n\n"
sleep 2

# Test 4: Reference using pronoun
echo " Test 2.4: User says 'reschedule it'"
curl -X POST "$API_ENDPOINT" \
 -H "Content-Type: application/json" \
 -d '{
 "message": "can you reschedule it to next Monday at 10am?",
 "session_id": "'"$SESSION_ID"'",
 "pf_token": "'"$PF_TOKEN"'",
 "pf_client_id": "'"$PF_CLIENT_ID"'",
 "pf_user_id": '"$PF_USER_ID"'
 }'
echo -e "\n\n"
sleep 2

# Test 5: Switch context
echo " Test 2.5: User switches to different project"
curl -X POST "$API_ENDPOINT" \
 -H "Content-Type: application/json" \
 -d '{
 "message": "show me the 3rd project instead",
 "session_id": "'"$SESSION_ID"'",
 "pf_token": "'"$PF_TOKEN"'",
 "pf_client_id": "'"$PF_CLIENT_ID"'",
 "pf_user_id": '"$PF_USER_ID"'
 }'
echo -e "\n\n"
sleep 2

# Test 6: Get all projects for ordinal tests
echo " Test 2.6: List all projects"
curl -X POST "$API_ENDPOINT" \
 -H "Content-Type: application/json" \
 -d '{
 "message": "list all my projects",
 "session_id": "'"$SESSION_ID"'",
 "pf_token": "'"$PF_TOKEN"'",
 "pf_client_id": "'"$PF_CLIENT_ID"'",
 "pf_user_id": '"$PF_USER_ID"'
 }'
echo -e "\n\n"
sleep 2

# Test 7: "last" ordinal reference
echo " Test 2.7: Reference 'the last project'"
curl -X POST "$API_ENDPOINT" \
 -H "Content-Type: application/json" \
 -d '{
 "message": "give me details for the last project",
 "session_id": "'"$SESSION_ID"'",
 "pf_token": "'"$PF_TOKEN"'",
 "pf_client_id": "'"$PF_CLIENT_ID"'",
 "pf_user_id": '"$PF_USER_ID"'
 }'
echo -e "\n\n"
sleep 2

# Test 8: "second" ordinal reference
echo " Test 2.8: Reference 'the second one'"
curl -X POST "$API_ENDPOINT" \
 -H "Content-Type: application/json" \
 -d '{
 "message": "what about the second one?",
 "session_id": "'"$SESSION_ID"'",
 "pf_token": "'"$PF_TOKEN"'",
 "pf_client_id": "'"$PF_CLIENT_ID"'",
 "pf_user_id": '"$PF_USER_ID"'
 }'
echo -e "\n\n"
sleep 2

# Test 9: "last one" with pronoun
echo " Test 2.9: Schedule 'the last one'"
curl -X POST "$API_ENDPOINT" \
 -H "Content-Type: application/json" \
 -d '{
 "message": "I want to schedule the last one",
 "session_id": "'"$SESSION_ID"'",
 "pf_token": "'"$PF_TOKEN"'",
 "pf_client_id": "'"$PF_CLIENT_ID"'",
 "pf_user_id": '"$PF_USER_ID"'
 }'
echo -e "\n\n"

echo "=========================================="
echo "Test Suite 2 Completed (9 tests)"
echo "=========================================="
echo ""
echo "Ordinal References Tested:"
echo " 'the first one' (Test 2.2)"
echo " 'the 3rd project' (Test 2.5)"
echo " 'the last project' (Test 2.7)"
echo " 'the second one' (Test 2.8)"
echo " 'the last one' (Test 2.9)"
echo ""
