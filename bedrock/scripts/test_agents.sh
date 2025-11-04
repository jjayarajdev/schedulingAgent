#!/bin/bash

##############################################################################
# TEST_AGENTS.sh - Test Bedrock Agents with Basic Queries
#
# Purpose: Send test queries to agents and display responses
# Usage: ./TEST_AGENTS.sh
##############################################################################

set -e

REGION="us-east-1"
SESSION_ID="test-$(date +%s)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo "=========================================="
echo "ProjectForce Agent Testing"
echo "=========================================="
echo "Session ID: $SESSION_ID"
echo "Region: $REGION"
echo ""

# Check environment variables
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Environment Variables Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check PF_BEARER_TOKEN or PF_API_TOKEN
if [[ -n "$PF_BEARER_TOKEN" ]] || [[ -n "$PF_API_TOKEN" ]]; then
    TOKEN="${PF_BEARER_TOKEN:-$PF_API_TOKEN}"
    echo -e "${GREEN}✓ PF_BEARER_TOKEN:${NC} SET (${#TOKEN} characters)"
else
    echo -e "${YELLOW}⚠ PF_BEARER_TOKEN:${NC} NOT SET (Lambda uses configured token)"
fi

# Check PF_CLIENT_ID
if [[ -n "$PF_CLIENT_ID" ]]; then
    echo -e "${GREEN}✓ PF_CLIENT_ID:${NC} $PF_CLIENT_ID"
else
    echo -e "${YELLOW}⚠ PF_CLIENT_ID:${NC} NOT SET (using session attribute: 09PF05VD)"
fi

# Check PF_USER_ID
if [[ -n "$PF_USER_ID" ]]; then
    echo -e "${GREEN}✓ PF_USER_ID:${NC} $PF_USER_ID"
else
    echo -e "${YELLOW}⚠ PF_USER_ID:${NC} NOT SET (using session attribute: 1645869)"
fi

# Check USE_MOCK_API
if [[ -n "$USE_MOCK_API" ]]; then
    echo -e "${GREEN}✓ USE_MOCK_API:${NC} $USE_MOCK_API"
else
    echo -e "${YELLOW}⚠ USE_MOCK_API:${NC} NOT SET (Lambda uses configured value)"
fi

echo ""

# Get agent IDs
SCHEDULING_AGENT_ID=$(aws bedrock-agent list-agents \
    --region "$REGION" \
    --query "agentSummaries[?agentName=='SchedulingAgent'].agentId" \
    --output text 2>/dev/null | head -1)

INFORMATION_AGENT_ID=$(aws bedrock-agent list-agents \
    --region "$REGION" \
    --query "agentSummaries[?agentName=='pf-information'].agentId" \
    --output text 2>/dev/null | head -1)

CHITCHAT_AGENT_ID=$(aws bedrock-agent list-agents \
    --region "$REGION" \
    --query "agentSummaries[?agentName=='pf-chitchat'].agentId" \
    --output text 2>/dev/null | head -1)

if [[ -z "$SCHEDULING_AGENT_ID" ]]; then
    echo -e "${RED}ERROR: SchedulingAgent not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found SchedulingAgent: $SCHEDULING_AGENT_ID${NC}"
echo -e "${GREEN}✓ Found pf-information: $INFORMATION_AGENT_ID${NC}"
echo -e "${GREEN}✓ Found pf-chitchat: $CHITCHAT_AGENT_ID${NC}"
echo ""

# Function to invoke agent and parse response
invoke_agent() {
    local agent_id=$1
    local query=$2
    local agent_name=$3

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${CYAN}Agent: ${NC}$agent_name"
    echo -e "${CYAN}Query: ${NC}$query"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Invoke agent using boto3
    python3 << EOFPYTHON
import boto3
import json
import sys

try:
    client = boto3.client('bedrock-agent-runtime', region_name='$REGION')

    response = client.invoke_agent(
        agentId='$agent_id',
        agentAliasId='TSTALIASID',
        sessionId='$SESSION_ID',
        inputText='$query',
        sessionState={
            'sessionAttributes': {
                'customer_id': '1645869',
                'client_id': '09PF05VD'
            }
        }
    )

    # Process event stream
    event_stream = response['completion']
    full_response = []

    for event in event_stream:
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                text = chunk['bytes'].decode('utf-8')
                full_response.append(text)

    print('${GREEN}Response:${NC}')
    print('───────────────────────────────────────────────────────────────────────────────')
    print(''.join(full_response))
    print('───────────────────────────────────────────────────────────────────────────────')
    print('')

except Exception as e:
    print('${RED}ERROR:${NC}', str(e))
    print('')
    sys.exit(1)
EOFPYTHON
}

##############################################################################
# Test 1: SchedulingAgent - List Projects
##############################################################################

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                        TEST 1: List Projects                                 ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

invoke_agent "$SCHEDULING_AGENT_ID" "Show me my projects" "SchedulingAgent"

sleep 2

##############################################################################
# Test 2: SchedulingAgent - Appointments
##############################################################################

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                        TEST 2: Get Appointments                              ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

invoke_agent "$SCHEDULING_AGENT_ID" "What appointments do I have?" "SchedulingAgent"

sleep 2

##############################################################################
# Test 3: Information Agent - Weather
##############################################################################

if [[ -n "$INFORMATION_AGENT_ID" ]]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                        TEST 3: Weather Information                           ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo ""

    invoke_agent "$INFORMATION_AGENT_ID" "What's the weather in Minneapolis?" "pf-information"

    sleep 2
fi

##############################################################################
# Test 4: Chitchat Agent - Greeting
##############################################################################

if [[ -n "$CHITCHAT_AGENT_ID" ]]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                        TEST 4: Chitchat Greeting                             ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo ""

    invoke_agent "$CHITCHAT_AGENT_ID" "Hello, how are you?" "pf-chitchat"
fi

##############################################################################
# Summary
##############################################################################

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                        TESTING COMPLETE                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}All tests completed successfully!${NC}"
echo ""
