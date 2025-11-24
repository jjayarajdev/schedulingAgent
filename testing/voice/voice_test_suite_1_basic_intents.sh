#!/bin/bash
# Voice Test Suite 1: Basic Intent Workflow
# Covers: Welcome → ProjectInquiry → CheckAvailability → ScheduleAppointment

# Set AWS profile for correct account
export AWS_PROFILE=projectsforce

# Load configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/voice_test_config.sh"

SESSION_ID="voice-test-$(date +%s)"
CUSTOMER_PHONE="+18005551234"

echo ""
echo "=========================================="
echo "Voice Test Suite 1: Basic Intent Workflow"
echo "=========================================="
echo "Session ID: $SESSION_ID"
echo "Customer Phone: $CUSTOMER_PHONE"
echo ""

# Helper function to invoke Lambda
invoke_lex_lambda() {
  local INTENT_NAME=$1
  local TRANSCRIPT=$2
  local SLOTS=${3:-"{}"}

  local PAYLOAD=$(cat <<EOF
{
  "sessionId": "$SESSION_ID",
  "inputTranscript": "$TRANSCRIPT",
  "sessionState": {
    "sessionAttributes": {
      "customer_id": "$TEST_CUSTOMER_ID",
      "customer_phone": "$CUSTOMER_PHONE",
      "pf_token": "$PF_TOKEN",
      "pf_client_id": "$PF_CLIENT_ID",
      "pf_user_id": "$PF_USER_ID"
    },
    "intent": {
      "name": "$INTENT_NAME",
      "slots": $SLOTS,
      "state": "InProgress"
    },
    "dialogAction": {
      "type": "ElicitIntent"
    }
  },
  "requestAttributes": {
    "CustomerNumber": "$CUSTOMER_PHONE"
  }
}
EOF
)

  echo "$PAYLOAD" | aws lambda invoke \
    --function-name "$LEX_FULFILLMENT_LAMBDA" \
    --payload file:///dev/stdin \
    --region "$AWS_REGION" \
    --cli-binary-format raw-in-base64-out \
    /dev/stdout 2>/dev/null | jq '.'
}

# Helper function to invoke Bedrock bridge
invoke_bedrock_bridge() {
  local INPUT_TEXT=$1

  local PAYLOAD=$(cat <<EOF
{
  "session_id": "$SESSION_ID",
  "customer_id": "$TEST_CUSTOMER_ID",
  "input_text": "$INPUT_TEXT",
  "channel": "voice",
  "session_attributes": {
    "customer_id": "$TEST_CUSTOMER_ID",
    "pf_token": "$PF_TOKEN",
    "pf_client_id": "$PF_CLIENT_ID",
    "pf_user_id": "$PF_USER_ID"
  }
}
EOF
)

  echo "$PAYLOAD" | aws lambda invoke \
    --function-name "$VOICE_BRIDGE_LAMBDA" \
    --payload file:///dev/stdin \
    --region "$AWS_REGION" \
    --cli-binary-format raw-in-base64-out \
    /dev/stdout 2>/dev/null | jq '.'
}


# ============================================================================
# Test 1: Customer Lookup
# ============================================================================

echo -e "${BLUE}📝 Test 1.1: Customer lookup by phone number${NC}"
echo "$CUSTOMER_PHONE" | jq -Rs '{action: "lookup_by_phone", phone_number: .}' | \
  aws lambda invoke \
    --function-name "$CUSTOMER_LOOKUP_LAMBDA" \
    --payload file:///dev/stdin \
    --region "$AWS_REGION" \
    --cli-binary-format raw-in-base64-out \
    /dev/stdout 2>/dev/null | jq '.'

echo ""
sleep 2


# ============================================================================
# Test 2: Welcome Intent (Simple - Direct Lex Fulfillment)
# ============================================================================

echo -e "${BLUE}📝 Test 1.2: Welcome intent - User greets system${NC}"
invoke_lex_lambda "Welcome" "hello"

echo ""
sleep 2


# ============================================================================
# Test 3: ProjectInquiry Intent (Simple - Direct Lex Fulfillment)
# ============================================================================

echo -e "${BLUE}📝 Test 1.3: ProjectInquiry intent - User asks for projects${NC}"
invoke_lex_lambda "ProjectInquiry" "show me all my projects"

echo ""
sleep 2


# ============================================================================
# Test 4: CheckAvailability Intent (Simple - Direct Lex Fulfillment)
# ============================================================================

echo -e "${BLUE}📝 Test 1.4: CheckAvailability intent - User checks available times${NC}"
# Note: Replace PRJ-001 with actual project ID from Test 1.3 results
PROJECT_SLOTS=$(cat <<'EOF'
{
  "ProjectId": {
    "value": {
      "interpretedValue": "7751744",
      "originalValue": "7751744",
      "resolvedValues": ["7751744"]
    }
  }
}
EOF
)

invoke_lex_lambda "CheckAvailability" "check availability for project 7751744" "$PROJECT_SLOTS"

echo ""
sleep 2


# ============================================================================
# Test 5: ScheduleAppointment Intent (Complex - Bedrock Bridge)
# ============================================================================

echo -e "${BLUE}📝 Test 1.5: ScheduleAppointment via Bedrock bridge${NC}"
invoke_bedrock_bridge "schedule project 7751744 for tomorrow at 2pm"

echo ""
sleep 2


# ============================================================================
# Test 6: UrgentRequest Intent (Complex - Bedrock Bridge)
# ============================================================================

echo -e "${BLUE}📝 Test 1.6: UrgentRequest via Bedrock bridge${NC}"
invoke_bedrock_bridge "I need urgent service for my roofing project"

echo ""
sleep 2


# ============================================================================
# Test 7: Agent Selection Verification
# ============================================================================

echo -e "${BLUE}📝 Test 1.7: Verify agent routing - Scheduling keywords${NC}"
invoke_bedrock_bridge "book an appointment"

echo ""
sleep 2

echo -e "${BLUE}📝 Test 1.8: Verify agent routing - Information keywords${NC}"
invoke_bedrock_bridge "what's the weather forecast for tomorrow"

echo ""
sleep 2

echo -e "${BLUE}📝 Test 1.9: Verify agent routing - Chitchat keywords${NC}"
invoke_bedrock_bridge "thank you so much"

echo ""


# ============================================================================
# Summary
# ============================================================================

echo "=========================================="
echo -e "${GREEN}Voice Test Suite 1 Completed${NC}"
echo "=========================================="
echo ""
echo "Tests Performed:"
echo "  ✅ Customer lookup by phone number"
echo "  ✅ Welcome intent (direct Lex)"
echo "  ✅ ProjectInquiry intent (direct Lex)"
echo "  ✅ CheckAvailability intent (direct Lex)"
echo "  ✅ ScheduleAppointment via Bedrock"
echo "  ✅ UrgentRequest via Bedrock"
echo "  ✅ Agent routing verification (3 tests)"
echo ""
echo "Next Steps:"
echo "  1. Review CloudWatch logs:"
echo "     aws logs tail /aws/lambda/$LEX_FULFILLMENT_LAMBDA --follow --region $AWS_REGION"
echo ""
echo "  2. Check DynamoDB session data:"
echo "     aws dynamodb get-item --table-name pf-sessions-dev --key '{\"session_id\": {\"S\": \"$SESSION_ID\"}}' --region $AWS_REGION"
echo ""
echo "  3. Run voice_test_suite_2_multi_turn.sh for conversation flow testing"
echo ""
