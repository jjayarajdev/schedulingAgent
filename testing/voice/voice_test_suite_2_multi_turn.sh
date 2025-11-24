#!/bin/bash
# Voice Test Suite 2: Multi-Turn Conversation Flow
# Tests session persistence and context handling across multiple turns

# Set AWS profile for correct account
export AWS_PROFILE=projectsforce

# Load configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/voice_test_config.sh"

SESSION_ID="voice-multiturn-$(date +%s)"
CUSTOMER_PHONE="+18005551234"

echo ""
echo "=================================================="
echo "Voice Test Suite 2: Multi-Turn Conversation Flow"
echo "=================================================="
echo "Session ID: $SESSION_ID"
echo ""

# Helper function to invoke Bedrock bridge with session tracking
invoke_with_session() {
  local INPUT_TEXT=$1
  local TURN_NUMBER=$2

  echo -e "${BLUE}Turn $TURN_NUMBER: \"$INPUT_TEXT\"${NC}"

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

  RESPONSE=$(echo "$PAYLOAD" | aws lambda invoke \
    --function-name "$VOICE_BRIDGE_LAMBDA" \
    --payload file:///dev/stdin \
    --region "$AWS_REGION" \
    --cli-binary-format raw-in-base64-out \
    /dev/stdout 2>/dev/null)

  echo "$RESPONSE" | jq -C '.'

  # Extract key information
  AGENT_USED=$(echo "$RESPONSE" | jq -r '.agent_used // "none"')
  RESPONSE_TEXT=$(echo "$RESPONSE" | jq -r '.response // .error // "no response"')

  echo -e "${YELLOW}Agent: $AGENT_USED${NC}"
  echo -e "${GREEN}Response: ${RESPONSE_TEXT:0:150}...${NC}"
  echo ""
}


# ============================================================================
# Scenario 1: Project Discovery → Scheduling Flow
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Scenario 1: Complete Scheduling Workflow${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

invoke_with_session "hi, I want to schedule an appointment" 1
sleep 2

invoke_with_session "show me my projects" 2
sleep 2

invoke_with_session "what about the new ones" 3
sleep 2

invoke_with_session "tell me about the second one" 4
sleep 2

invoke_with_session "schedule it for tomorrow at 2pm" 5
sleep 2

invoke_with_session "actually, make it 3pm instead" 6
sleep 2


# ============================================================================
# Scenario 2: Interruption and Recovery
# ============================================================================

SESSION_ID="voice-interruption-$(date +%s)"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Scenario 2: Interruption Handling${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

invoke_with_session "schedule my roofing project" 1
sleep 2

invoke_with_session "wait, what's the weather like tomorrow?" 2
sleep 2

invoke_with_session "ok, back to scheduling" 3
sleep 2

invoke_with_session "book it for next Tuesday" 4
sleep 2


# ============================================================================
# Scenario 3: Clarification and Error Recovery
# ============================================================================

SESSION_ID="voice-clarification-$(date +%s)"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Scenario 3: Clarification and Error Recovery${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

invoke_with_session "schedule something" 1
sleep 2

invoke_with_session "the project" 2
sleep 2

invoke_with_session "project number 7751744" 3
sleep 2

invoke_with_session "tomorrow" 4
sleep 2

invoke_with_session "in the afternoon" 5
sleep 2


# ============================================================================
# Scenario 4: Mixed Agent Routing
# ============================================================================

SESSION_ID="voice-mixed-$(date +%s)"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Scenario 4: Mixed Agent Routing${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

invoke_with_session "hello there" 1
sleep 2

invoke_with_session "show me my projects" 2
sleep 2

invoke_with_session "what's the forecast for tomorrow" 3
sleep 2

invoke_with_session "book the first project for that day" 4
sleep 2

invoke_with_session "thanks for your help" 5
sleep 2


# ============================================================================
# Summary
# ============================================================================

echo ""
echo "=================================================="
echo -e "${GREEN}Voice Test Suite 2 Completed${NC}"
echo "=================================================="
echo ""
echo "Scenarios Tested:"
echo "  ✅ Complete scheduling workflow (6 turns)"
echo "  ✅ Interruption handling (4 turns)"
echo "  ✅ Clarification and error recovery (5 turns)"
echo "  ✅ Mixed agent routing (5 turns)"
echo ""
echo "Total Turns: 20"
echo ""
echo "Validation Checklist:"
echo "  □ Session IDs maintained across turns"
echo "  □ Context preserved between messages"
echo "  □ Correct agent selection for each turn"
echo "  □ Voice responses under 500 characters"
echo "  □ No markdown in responses"
echo "  □ Response times under 30 seconds"
echo ""
echo "Review Logs:"
echo "  aws logs tail /aws/lambda/$VOICE_BRIDGE_LAMBDA --follow --region $AWS_REGION --filter-pattern 'voice-multiturn'"
echo ""
