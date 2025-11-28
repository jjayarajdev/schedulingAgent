#!/bin/bash
# Test Suite 4: Mixed Chitchat & Business Queries
# Covers: Agent routing between Chitchat and Information agents

source test_config.sh

SESSION_ID="test-suite-4-$(date +%s)"

echo ""
echo "=========================================="
echo "Test Suite 4: Mixed Chitchat & Business"
echo "=========================================="
echo "Session ID: $SESSION_ID"
echo ""

# Test 1: Chitchat greeting
echo " Test 4.1: User greets"
curl -X POST "$API_ENDPOINT" \
 -H "Content-Type: application/json" \
 -d '{
 "message": "good morning!",
 "session_id": "'"$SESSION_ID"'",
 "pf_token": "'"$PF_TOKEN"'",
 "pf_client_id": "'"$PF_CLIENT_ID"'",
 "pf_user_id": '"$PF_USER_ID"'
 }'
echo -e "\n\n"
sleep 2

# Test 2: Business query
echo " Test 4.2: User asks for projects"
curl -X POST "$API_ENDPOINT" \
 -H "Content-Type: application/json" \
 -d '{
 "message": "what projects do I have?",
 "session_id": "'"$SESSION_ID"'",
 "pf_token": "'"$PF_TOKEN"'",
 "pf_client_id": "'"$PF_CLIENT_ID"'",
 "pf_user_id": '"$PF_USER_ID"'
 }'
echo -e "\n\n"
sleep 2

# Test 3: Chitchat question
echo " Test 4.3: User asks how are you"
curl -X POST "$API_ENDPOINT" \
 -H "Content-Type: application/json" \
 -d '{
 "message": "how are you doing today?",
 "session_id": "'"$SESSION_ID"'",
 "pf_token": "'"$PF_TOKEN"'",
 "pf_client_id": "'"$PF_CLIENT_ID"'",
 "pf_user_id": '"$PF_USER_ID"'
 }'
echo -e "\n\n"
sleep 2

# Test 4: Business query with context
echo " Test 4.4: User references previous context"
curl -X POST "$API_ENDPOINT" \
 -H "Content-Type: application/json" \
 -d '{
 "message": "show me details for the last project",
 "session_id": "'"$SESSION_ID"'",
 "pf_token": "'"$PF_TOKEN"'",
 "pf_client_id": "'"$PF_CLIENT_ID"'",
 "pf_user_id": '"$PF_USER_ID"'
 }'
echo -e "\n\n"
sleep 2

# Test 5: Chitchat thanks
echo " Test 4.5: User says thanks"
curl -X POST "$API_ENDPOINT" \
 -H "Content-Type: application/json" \
 -d '{
 "message": "thank you so much!",
 "session_id": "'"$SESSION_ID"'",
 "pf_token": "'"$PF_TOKEN"'",
 "pf_client_id": "'"$PF_CLIENT_ID"'",
 "pf_user_id": '"$PF_USER_ID"'
 }'
echo -e "\n\n"
sleep 2

# Test 6: Weather query (Information Agent)
echo " Test 4.6: User asks about weather"
curl -X POST "$API_ENDPOINT" \
 -H "Content-Type: application/json" \
 -d '{
 "message": "what is the weather in Boston?",
 "session_id": "'"$SESSION_ID"'",
 "pf_token": "'"$PF_TOKEN"'",
 "pf_client_id": "'"$PF_CLIENT_ID"'",
 "pf_user_id": '"$PF_USER_ID"'
 }'
echo -e "\n\n"
sleep 2

# Test 7: Another weather query (different city)
echo " Test 4.7: User asks about weather in different city"
curl -X POST "$API_ENDPOINT" \
 -H "Content-Type: application/json" \
 -d '{
 "message": "how about Minneapolis?",
 "session_id": "'"$SESSION_ID"'",
 "pf_token": "'"$PF_TOKEN"'",
 "pf_client_id": "'"$PF_CLIENT_ID"'",
 "pf_user_id": '"$PF_USER_ID"'
 }'
echo -e "\n\n"
sleep 2

# Test 8: Business query again
echo " Test 4.8: User asks another business question"
curl -X POST "$API_ENDPOINT" \
 -H "Content-Type: application/json" \
 -d '{
 "message": "which ones are scheduled for next week?",
 "session_id": "'"$SESSION_ID"'",
 "pf_token": "'"$PF_TOKEN"'",
 "pf_client_id": "'"$PF_CLIENT_ID"'",
 "pf_user_id": '"$PF_USER_ID"'
 }'
echo -e "\n\n"

echo "=========================================="
echo "Test Suite 4 Completed (8 tests)"
echo "=========================================="
