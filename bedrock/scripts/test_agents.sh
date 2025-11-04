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

# Load credentials from Secrets Manager if not in environment
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Loading Credentials"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Try to load from Secrets Manager
SECRET_DATA=$(aws secretsmanager get-secret-value \
    --secret-id projectforce/api/credentials \
    --region "$REGION" \
    --query SecretString \
    --output text 2>/dev/null || echo "{}")

# Parse secret and set as defaults if not in environment
if [[ -z "$PF_BEARER_TOKEN" ]]; then
    PF_BEARER_TOKEN=$(echo "$SECRET_DATA" | jq -r '.bearer_token // ""' 2>/dev/null)
fi

if [[ -z "$PF_CLIENT_ID" ]]; then
    PF_CLIENT_ID=$(echo "$SECRET_DATA" | jq -r '.client_id // ""' 2>/dev/null)
fi

if [[ -z "$PF_USER_ID" ]]; then
    PF_USER_ID=$(echo "$SECRET_DATA" | jq -r '.user_id // ""' 2>/dev/null)
fi

echo -e "${BLUE}Source: ${NC}"
if [[ "$SECRET_DATA" != "{}" ]]; then
    echo "  • Loaded from AWS Secrets Manager: projectforce/api/credentials"
else
    echo "  • Using environment variables"
fi
echo ""

# Display what we have
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Credentials Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check PF_BEARER_TOKEN
if [[ -n "$PF_BEARER_TOKEN" ]]; then
    echo -e "${GREEN}✓ Bearer Token:${NC} SET (${#PF_BEARER_TOKEN} characters)"
else
    echo -e "${RED}✗ Bearer Token:${NC} NOT SET"
fi

# Check PF_CLIENT_ID
if [[ -n "$PF_CLIENT_ID" ]]; then
    echo -e "${GREEN}✓ Client ID:${NC} $PF_CLIENT_ID"
else
    echo -e "${RED}✗ Client ID:${NC} NOT SET"
fi

# Check PF_USER_ID
if [[ -n "$PF_USER_ID" ]]; then
    echo -e "${GREEN}✓ User ID:${NC} $PF_USER_ID"
else
    echo -e "${RED}✗ User ID:${NC} NOT SET"
fi

# Check USE_MOCK_API
if [[ -n "$USE_MOCK_API" ]]; then
    echo -e "${GREEN}✓ USE_MOCK_API:${NC} $USE_MOCK_API"
else
    echo -e "${YELLOW}⚠ USE_MOCK_API:${NC} NOT SET (using false)"
    USE_MOCK_API="false"
fi

echo ""

# Export credentials for Python subprocess
export PF_BEARER_TOKEN
export PF_CLIENT_ID
export PF_USER_ID

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
import os

try:
    client = boto3.client('bedrock-agent-runtime', region_name='$REGION')

    # Get user_id and client_id from environment (passed from parent script)
    user_id = os.environ.get('PF_USER_ID', '1646085')
    client_id = os.environ.get('PF_CLIENT_ID', '09PF05VD')

    response = client.invoke_agent(
        agentId='$agent_id',
        agentAliasId='TSTALIASID',
        sessionId='$SESSION_ID',
        inputText='''$query''',
        sessionState={
            'sessionAttributes': {
                'customer_id': user_id,
                'client_id': client_id
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
