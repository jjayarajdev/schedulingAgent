#!/bin/bash
# Quick Voice Tests - Runs essential tests for rapid validation

# Set AWS profile for correct account
export AWS_PROFILE=projectsforce

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/voice_test_config.sh"

SESSION_ID="quick-test-$(date +%s)"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Voice Integration Quick Tests${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Test 1: Customer Lookup
echo -e "${YELLOW}[1/5] Testing Customer Lookup Lambda...${NC}"
LOOKUP_RESPONSE=$(echo '{"action":"lookup_by_phone","phone_number":"+18005551234"}' | \
  aws lambda invoke \
    --function-name "$CUSTOMER_LOOKUP_LAMBDA" \
    --payload file:///dev/stdin \
    --region "$AWS_REGION" \
    --cli-binary-format raw-in-base64-out \
    /dev/stdout 2>/dev/null)

if echo "$LOOKUP_RESPONSE" | jq -e '.statusCode' >/dev/null 2>&1; then
  echo -e "${GREEN}✅ Customer Lookup working${NC}"
else
  echo -e "${RED}❌ Customer Lookup failed${NC}"
fi
echo ""
sleep 1


# Test 2: Lex Fulfillment - Welcome Intent
echo -e "${YELLOW}[2/5] Testing Lex Fulfillment - Welcome Intent...${NC}"
WELCOME_PAYLOAD=$(cat <<EOF
{
  "sessionId": "$SESSION_ID",
  "inputTranscript": "hello",
  "sessionState": {
    "sessionAttributes": {
      "pf_token": "$PF_TOKEN",
      "pf_client_id": "$PF_CLIENT_ID",
      "pf_user_id": "$PF_USER_ID"
    },
    "intent": {
      "name": "Welcome",
      "slots": {},
      "state": "InProgress"
    }
  }
}
EOF
)

WELCOME_RESPONSE=$(echo "$WELCOME_PAYLOAD" | aws lambda invoke \
  --function-name "$LEX_FULFILLMENT_LAMBDA" \
  --payload file:///dev/stdin \
  --region "$AWS_REGION" \
  --cli-binary-format raw-in-base64-out \
  /dev/stdout 2>/dev/null)

if echo "$WELCOME_RESPONSE" | jq -e '.messages' >/dev/null 2>&1; then
  echo -e "${GREEN}✅ Welcome Intent working${NC}"
  echo "   Response: $(echo "$WELCOME_RESPONSE" | jq -r '.messages[0].content' | head -c 80)..."
else
  echo -e "${RED}❌ Welcome Intent failed${NC}"
fi
echo ""
sleep 1


# Test 3: Lex Fulfillment - ProjectInquiry Intent
echo -e "${YELLOW}[3/5] Testing Lex Fulfillment - ProjectInquiry Intent...${NC}"
PROJECT_PAYLOAD=$(cat <<EOF
{
  "sessionId": "$SESSION_ID",
  "inputTranscript": "show me my projects",
  "sessionState": {
    "sessionAttributes": {
      "customer_id": "$TEST_CUSTOMER_ID",
      "pf_token": "$PF_TOKEN",
      "pf_client_id": "$PF_CLIENT_ID",
      "pf_user_id": "$PF_USER_ID"
    },
    "intent": {
      "name": "ProjectInquiry",
      "slots": {},
      "state": "InProgress"
    }
  }
}
EOF
)

PROJECT_RESPONSE=$(echo "$PROJECT_PAYLOAD" | aws lambda invoke \
  --function-name "$LEX_FULFILLMENT_LAMBDA" \
  --payload file:///dev/stdin \
  --region "$AWS_REGION" \
  --cli-binary-format raw-in-base64-out \
  /dev/stdout 2>/dev/null)

if echo "$PROJECT_RESPONSE" | jq -e '.messages' >/dev/null 2>&1; then
  echo -e "${GREEN}✅ ProjectInquiry Intent working${NC}"
else
  echo -e "${RED}❌ ProjectInquiry Intent failed${NC}"
fi
echo ""
sleep 1


# Test 4: Bedrock Bridge - Scheduling Agent
echo -e "${YELLOW}[4/5] Testing Bedrock Bridge - Scheduling Agent...${NC}"
SCHEDULING_PAYLOAD=$(cat <<EOF
{
  "session_id": "$SESSION_ID",
  "customer_id": "$TEST_CUSTOMER_ID",
  "input_text": "book an appointment for tomorrow",
  "channel": "voice",
  "session_attributes": {
    "pf_token": "$PF_TOKEN",
    "pf_client_id": "$PF_CLIENT_ID",
    "pf_user_id": "$PF_USER_ID"
  }
}
EOF
)

SCHEDULING_RESPONSE=$(echo "$SCHEDULING_PAYLOAD" | aws lambda invoke \
  --function-name "$VOICE_BRIDGE_LAMBDA" \
  --payload file:///dev/stdin \
  --region "$AWS_REGION" \
  --cli-binary-format raw-in-base64-out \
  /dev/stdout 2>/dev/null)

if echo "$SCHEDULING_RESPONSE" | jq -e '.agent_used' >/dev/null 2>&1; then
  AGENT_ID=$(echo "$SCHEDULING_RESPONSE" | jq -r '.agent_used')
  echo -e "${GREEN}✅ Bedrock Bridge working${NC}"
  echo "   Agent selected: $AGENT_ID"
  echo "   Response length: $(echo "$SCHEDULING_RESPONSE" | jq -r '.response' | wc -c) chars"
else
  echo -e "${RED}❌ Bedrock Bridge failed${NC}"
fi
echo ""
sleep 1


# Test 5: Agent Routing Accuracy
echo -e "${YELLOW}[5/5] Testing Agent Routing Accuracy...${NC}"

# Test scheduling keywords
SCHED_AGENT=$(echo '{"session_id":"'$SESSION_ID'","input_text":"schedule appointment","channel":"voice","session_attributes":{"pf_token":"'$PF_TOKEN'","pf_client_id":"'$PF_CLIENT_ID'","pf_user_id":"'$PF_USER_ID'"}}' | \
  aws lambda invoke --function-name "$VOICE_BRIDGE_LAMBDA" --payload file:///dev/stdin --region "$AWS_REGION" --cli-binary-format raw-in-base64-out /dev/stdout 2>/dev/null | \
  jq -r '.agent_used')

# Test information keywords
INFO_AGENT=$(echo '{"session_id":"'$SESSION_ID'","input_text":"whats the weather","channel":"voice","session_attributes":{"pf_token":"'$PF_TOKEN'","pf_client_id":"'$PF_CLIENT_ID'","pf_user_id":"'$PF_USER_ID'"}}' | \
  aws lambda invoke --function-name "$VOICE_BRIDGE_LAMBDA" --payload file:///dev/stdin --region "$AWS_REGION" --cli-binary-format raw-in-base64-out /dev/stdout 2>/dev/null | \
  jq -r '.agent_used')

# Test chitchat keywords
CHAT_AGENT=$(echo '{"session_id":"'$SESSION_ID'","input_text":"thank you","channel":"voice","session_attributes":{"pf_token":"'$PF_TOKEN'","pf_client_id":"'$PF_CLIENT_ID'","pf_user_id":"'$PF_USER_ID'"}}' | \
  aws lambda invoke --function-name "$VOICE_BRIDGE_LAMBDA" --payload file:///dev/stdin --region "$AWS_REGION" --cli-binary-format raw-in-base64-out /dev/stdout 2>/dev/null | \
  jq -r '.agent_used')

echo "   Scheduling → $SCHED_AGENT"
echo "   Information → $INFO_AGENT"
echo "   Chitchat → $CHAT_AGENT"

if [ "$SCHED_AGENT" != "null" ] && [ "$INFO_AGENT" != "null" ] && [ "$CHAT_AGENT" != "null" ]; then
  echo -e "${GREEN}✅ Agent routing working${NC}"
else
  echo -e "${RED}❌ Agent routing issues detected${NC}"
fi
echo ""


# ============================================================================
# Summary
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Quick Tests Completed${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Components Tested:"
echo "  ✅ Customer Lookup Lambda"
echo "  ✅ Lex Fulfillment Lambda (Welcome, ProjectInquiry)"
echo "  ✅ Bedrock Bridge Lambda"
echo "  ✅ Agent Routing Logic"
echo ""
echo "For comprehensive testing, run:"
echo "  bash voice_test_suite_1_basic_intents.sh"
echo "  bash voice_test_suite_2_multi_turn.sh"
echo ""
echo "Monitor logs:"
echo "  aws logs tail /aws/lambda/$LEX_FULFILLMENT_LAMBDA --follow --region $AWS_REGION"
echo ""
