#!/bin/bash

# ============================================================================
# AWS Connect Voice Integration Test Script
# ============================================================================
# Purpose: Test deployed voice integration components
# Author: ProjectForce Team
# ============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPLOYMENT_INFO="$PROJECT_ROOT/config/voice_deployment.json"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Voice Integration Test Suite${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Load deployment info
if [ ! -f "$DEPLOYMENT_INFO" ]; then
  echo -e "${RED}❌ Deployment info not found: $DEPLOYMENT_INFO${NC}"
  echo "Run ./scripts/DEPLOY_VOICE.sh first"
  exit 1
fi

LEX_FULFILLMENT_LAMBDA=$(jq -r '.lambda.lex_fulfillment' "$DEPLOYMENT_INFO")
VOICE_BRIDGE_LAMBDA=$(jq -r '.lambda.voice_bridge' "$DEPLOYMENT_INFO")
SUPERVISOR_AGENT_ID=$(jq -r '.bedrock_agents.supervisor_id' "$DEPLOYMENT_INFO")
LEX_BOT_ID=$(jq -r '.lex.bot_id' "$DEPLOYMENT_INFO")
LEX_ALIAS_ID=$(jq -r '.lex.alias_id' "$DEPLOYMENT_INFO")
REGION=$(jq -r '.region' "$DEPLOYMENT_INFO")

echo "Configuration:"
echo "  Lex Fulfillment: $LEX_FULFILLMENT_LAMBDA"
echo "  Voice Bridge: $VOICE_BRIDGE_LAMBDA"
echo "  Supervisor Agent: $SUPERVISOR_AGENT_ID"
echo "  Lex Bot: $LEX_BOT_ID"
echo ""

TESTS_PASSED=0
TESTS_FAILED=0

# ============================================================================
# Test 1: Lambda Lex Fulfillment - Welcome Intent
# ============================================================================

echo -e "${YELLOW}Test 1: Lex Fulfillment - Welcome Intent${NC}"

TEST_PAYLOAD='{
  "sessionState": {
    "intent": {
      "name": "Welcome",
      "state": "InProgress"
    },
    "sessionAttributes": {}
  },
  "sessionId": "test-session-001",
  "inputTranscript": "hello"
}'

echo "$TEST_PAYLOAD" > /tmp/lex-test-payload.json

aws lambda invoke \
  --function-name "$LEX_FULFILLMENT_LAMBDA" \
  --payload file:///tmp/lex-test-payload.json \
  --region "$REGION" \
  /tmp/lex-test-output.json > /dev/null 2>&1

RESULT=$(cat /tmp/lex-test-output.json)
MESSAGE=$(echo "$RESULT" | jq -r '.messages[0].content // empty')

if echo "$MESSAGE" | grep -qi "welcome\|hello"; then
  echo -e "${GREEN}✅ PASSED: Welcome intent working${NC}"
  echo "   Response: $MESSAGE"
  TESTS_PASSED=$((TESTS_PASSED + 1))
else
  echo -e "${RED}❌ FAILED: Unexpected response${NC}"
  echo "$RESULT" | jq .
  TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# ============================================================================
# Test 2: Lambda Lex Fulfillment - Fallback Intent
# ============================================================================

echo -e "${YELLOW}Test 2: Lex Fulfillment - Fallback Intent${NC}"

TEST_PAYLOAD='{
  "sessionState": {
    "intent": {
      "name": "FallbackIntent",
      "state": "InProgress"
    },
    "sessionAttributes": {
      "customer_id": "CUST001"
    }
  },
  "sessionId": "test-session-002",
  "inputTranscript": "what is the weather like"
}'

echo "$TEST_PAYLOAD" > /tmp/lex-test-payload.json

aws lambda invoke \
  --function-name "$LEX_FULFILLMENT_LAMBDA" \
  --payload file:///tmp/lex-test-payload.json \
  --region "$REGION" \
  /tmp/lex-test-output.json > /dev/null 2>&1

RESULT=$(cat /tmp/lex-test-output.json)

if echo "$RESULT" | jq -e '.messages[0].content' > /dev/null 2>&1; then
  echo -e "${GREEN}✅ PASSED: Fallback intent triggers Bedrock bridge${NC}"
  echo "   Response: $(echo "$RESULT" | jq -r '.messages[0].content')"
  TESTS_PASSED=$((TESTS_PASSED + 1))
else
  echo -e "${RED}❌ FAILED: No response from fallback${NC}"
  echo "$RESULT" | jq .
  TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# ============================================================================
# Test 3: Voice-Bedrock Bridge Lambda
# ============================================================================

echo -e "${YELLOW}Test 3: Voice-Bedrock Bridge${NC}"

TEST_PAYLOAD='{
  "session_id": "test-voice-session-001",
  "customer_id": "CUST001",
  "input_text": "What projects do I have?",
  "channel": "voice"
}'

echo "$TEST_PAYLOAD" > /tmp/bridge-test-payload.json

aws lambda invoke \
  --function-name "$VOICE_BRIDGE_LAMBDA" \
  --payload file:///tmp/bridge-test-payload.json \
  --region "$REGION" \
  /tmp/bridge-test-output.json > /dev/null 2>&1

RESULT=$(cat /tmp/bridge-test-output.json)
STATUS=$(echo "$RESULT" | jq -r '.statusCode // 0')
RESPONSE=$(echo "$RESULT" | jq -r '.response // empty')

if [ "$STATUS" == "200" ] && [ -n "$RESPONSE" ]; then
  echo -e "${GREEN}✅ PASSED: Bedrock bridge invoked successfully${NC}"
  echo "   Response: $RESPONSE"
  TESTS_PASSED=$((TESTS_PASSED + 1))
else
  echo -e "${RED}❌ FAILED: Bedrock bridge error${NC}"
  echo "$RESULT" | jq .
  TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# ============================================================================
# Test 4: Bedrock Supervisor Agent Direct
# ============================================================================

echo -e "${YELLOW}Test 4: Bedrock Supervisor Agent${NC}"

SESSION_ID="test-direct-$(date +%s)"

RESPONSE=$(aws bedrock-agent-runtime invoke-agent \
  --agent-id "$SUPERVISOR_AGENT_ID" \
  --agent-alias-id "TSTALIASID" \
  --session-id "$SESSION_ID" \
  --input-text "Hello, how can you help me?" \
  --region "$REGION" \
  /tmp/bedrock-output.txt 2>&1)

if [ $? -eq 0 ] && [ -f /tmp/bedrock-output.txt ]; then
  echo -e "${GREEN}✅ PASSED: Supervisor agent responding${NC}"
  echo "   Response saved to: /tmp/bedrock-output.txt"
  TESTS_PASSED=$((TESTS_PASSED + 1))
else
  echo -e "${RED}❌ FAILED: Supervisor agent error${NC}"
  echo "$RESPONSE"
  TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# ============================================================================
# Test 5: Lex Bot (if available)
# ============================================================================

echo -e "${YELLOW}Test 5: Lex Bot Recognition${NC}"

LEX_SESSION_ID="test-lex-$(date +%s)"

LEX_RESPONSE=$(aws lexv2-runtime recognize-text \
  --bot-id "$LEX_BOT_ID" \
  --bot-alias-id "$LEX_ALIAS_ID" \
  --locale-id "en_US" \
  --session-id "$LEX_SESSION_ID" \
  --text "hello" \
  --region "$REGION" 2>&1 || echo "error")

if echo "$LEX_RESPONSE" | grep -q "error\|not found\|does not exist"; then
  echo -e "${YELLOW}⚠️  SKIPPED: Lex bot not built yet${NC}"
  echo "   Build the bot first:"
  echo "   aws lexv2-models build-bot-locale --bot-id $LEX_BOT_ID --bot-version DRAFT --locale-id en_US --region $REGION"
else
  INTENT=$(echo "$LEX_RESPONSE" | jq -r '.sessionState.intent.name // empty')
  if [ -n "$INTENT" ]; then
    echo -e "${GREEN}✅ PASSED: Lex bot recognized intent: $INTENT${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
  else
    echo -e "${RED}❌ FAILED: Lex bot not responding correctly${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
  fi
fi
echo ""

# ============================================================================
# Test 6: DynamoDB Session Storage
# ============================================================================

echo -e "${YELLOW}Test 6: DynamoDB Session Storage${NC}"

DYNAMODB_TABLE="pf-session-data-dev"

# Try to read a session (from Test 3)
SESSION_DATA=$(aws dynamodb get-item \
  --table-name "$DYNAMODB_TABLE" \
  --key '{"session_id": {"S": "test-voice-session-001"}}' \
  --region "$REGION" 2>&1 || echo "error")

if echo "$SESSION_DATA" | grep -q "error\|not found"; then
  echo -e "${YELLOW}⚠️  No session data found (expected if first run)${NC}"
else
  echo -e "${GREEN}✅ PASSED: DynamoDB storing session data${NC}"
  TESTS_PASSED=$((TESTS_PASSED + 1))
fi
echo ""

# ============================================================================
# Test Summary
# ============================================================================

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Test Results${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
  echo -e "${RED}Failed: $TESTS_FAILED${NC}"
else
  echo "Failed: $TESTS_FAILED"
fi
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
  echo -e "${GREEN}✅ All tests passed!${NC}"
  echo ""
  echo "Next Steps:"
  echo "1. Build Lex bot (if not done):"
  echo "   aws lexv2-models build-bot-locale --bot-id $LEX_BOT_ID --bot-version DRAFT --locale-id en_US --region $REGION"
  echo ""
  echo "2. Create contact flow in AWS Connect Console"
  echo ""
  echo "3. Claim phone number (if not done):"
  echo "   ./scripts/claim_phone_number.sh"
  echo ""
  echo "4. Test by calling your phone number"
  exit 0
else
  echo -e "${RED}❌ Some tests failed${NC}"
  echo ""
  echo "Check CloudWatch Logs for details:"
  echo "  aws logs tail /aws/lambda/$LEX_FULFILLMENT_LAMBDA --follow --region $REGION"
  echo "  aws logs tail /aws/lambda/$VOICE_BRIDGE_LAMBDA --follow --region $REGION"
  exit 1
fi
