#!/usr/bin/env bash
###############################################################################
# Setup Supervisor Agent Collaboration
#
# Run this AFTER creating v1 aliases in AWS Console
# This is a separate script because v1 alias creation requires Console
###############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BEDROCK_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Load agent IDs from config
CONFIG_FILE="$BEDROCK_DIR/config/agent_ids.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}❌ Error: agent_ids.json not found${NC}"
    echo "Please run DEPLOY.sh first to create agents"
    exit 1
fi

SCHEDULING_AGENT_ID=$(jq -r '.agents.SchedulingAgent.id' "$CONFIG_FILE")
INFORMATION_AGENT_ID=$(jq -r '.agents."pf-information".id' "$CONFIG_FILE")
CHITCHAT_AGENT_ID=$(jq -r '.agents."pf-chitchat".id' "$CONFIG_FILE")
SUPERVISOR_AGENT_ID=$(jq -r '.agents.Supervisor.id' "$CONFIG_FILE")

echo ""
echo "================================================================================"
echo "Setup Supervisor Agent Collaboration"
echo "================================================================================"
echo ""
echo "Region:  $REGION"
echo "Account: $ACCOUNT_ID"
echo ""
echo "Agents:"
echo "  Supervisor:   $SUPERVISOR_AGENT_ID"
echo "  Scheduling:   $SCHEDULING_AGENT_ID"
echo "  Information:  $INFORMATION_AGENT_ID"
echo "  Chitchat:     $CHITCHAT_AGENT_ID"
echo ""
echo "================================================================================"
echo ""

###############################################################################
# Step 1: Check for v1 Aliases
###############################################################################

echo -e "${BLUE}Step 1: Checking for v1 Aliases${NC}"
echo ""

SCHEDULING_ALIAS_ID=$(aws bedrock-agent list-agent-aliases \
    --agent-id "$SCHEDULING_AGENT_ID" \
    --region "$REGION" \
    --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' \
    --output text 2>/dev/null || echo "")

INFORMATION_ALIAS_ID=$(aws bedrock-agent list-agent-aliases \
    --agent-id "$INFORMATION_AGENT_ID" \
    --region "$REGION" \
    --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' \
    --output text 2>/dev/null || echo "")

CHITCHAT_ALIAS_ID=$(aws bedrock-agent list-agent-aliases \
    --agent-id "$CHITCHAT_AGENT_ID" \
    --region "$REGION" \
    --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' \
    --output text 2>/dev/null || echo "")

# Check if all v1 aliases exist
MISSING_ALIASES=0

if [[ -z "$SCHEDULING_ALIAS_ID" ]]; then
    echo -e "${RED}❌ SchedulingAgent: v1 alias NOT found${NC}"
    MISSING_ALIASES=1
else
    echo -e "${GREEN}✅ SchedulingAgent: v1 alias found${NC} ($SCHEDULING_ALIAS_ID)"
fi

if [[ -z "$INFORMATION_ALIAS_ID" ]]; then
    echo -e "${RED}❌ pf-information: v1 alias NOT found${NC}"
    MISSING_ALIASES=1
else
    echo -e "${GREEN}✅ pf-information: v1 alias found${NC} ($INFORMATION_ALIAS_ID)"
fi

if [[ -z "$CHITCHAT_ALIAS_ID" ]]; then
    echo -e "${RED}❌ pf-chitchat: v1 alias NOT found${NC}"
    MISSING_ALIASES=1
else
    echo -e "${GREEN}✅ pf-chitchat: v1 alias found${NC} ($CHITCHAT_ALIAS_ID)"
fi

if [ $MISSING_ALIASES -eq 1 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${YELLOW}⚠️  Create v1 Aliases via AWS Console (One-Time Step)${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "AWS Bedrock agent collaboration requires versioned aliases (v1)."
    echo "TSTALIASID cannot be used for collaboration."
    echo ""
    echo "To create v1 aliases (5 minutes per agent):"
    echo ""
    echo "1. Open AWS Bedrock Console:"
    echo "   https://console.aws.amazon.com/bedrock/"
    echo ""
    echo "2. Region: ${YELLOW}us-east-1${NC} (top-right)"
    echo ""
    echo "3. Click: ${YELLOW}Agents${NC} (left sidebar)"
    echo ""
    echo "4. For EACH missing agent above:"
    echo "   a. Click on the agent"
    echo "   b. Click 'Working draft' dropdown → 'Create version'"
    echo "   c. Confirm 'Create version 1' → Wait 30 seconds"
    echo "   d. Click 'Aliases' tab → 'Create alias'"
    echo "   e. Alias name: ${YELLOW}v1${NC}"
    echo "   f. Agent version: Select ${YELLOW}1${NC}"
    echo "   g. Click 'Create alias'"
    echo ""
    echo "5. After creating all v1 aliases, run this script again:"
    echo "   ${GREEN}./scripts/SETUP_COLLABORATION.sh${NC}"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    exit 1
fi

echo ""

###############################################################################
# Step 2: Build Alias ARNs
###############################################################################

echo -e "${BLUE}Step 2: Building Alias ARNs${NC}"
echo ""

SCHEDULING_ARN="arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent-alias/${SCHEDULING_AGENT_ID}/${SCHEDULING_ALIAS_ID}"
INFORMATION_ARN="arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent-alias/${INFORMATION_AGENT_ID}/${INFORMATION_ALIAS_ID}"
CHITCHAT_ARN="arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent-alias/${CHITCHAT_AGENT_ID}/${CHITCHAT_ALIAS_ID}"

echo "  SchedulingAgent:  $SCHEDULING_ARN"
echo "  InformationAgent: $INFORMATION_ARN"
echo "  ChitchatAgent:    $CHITCHAT_ARN"
echo ""

###############################################################################
# Step 3: Enable Collaboration on Supervisor Agent
###############################################################################

echo -e "${BLUE}Step 3: Enabling Collaboration on Supervisor Agent${NC}"
echo ""

# Check current collaboration status
CURRENT_COLLAB=$(aws bedrock-agent get-agent \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --region "$REGION" \
    --query 'agent.agentCollaboration' \
    --output text 2>/dev/null)

echo "  Current collaboration mode: $CURRENT_COLLAB"

if [ "$CURRENT_COLLAB" != "SUPERVISOR" ]; then
    echo "  → Enabling SUPERVISOR collaboration mode..."

    # Get current agent details
    AGENT_ROLE=$(aws bedrock-agent get-agent --agent-id "$SUPERVISOR_AGENT_ID" --region "$REGION" --query 'agent.agentResourceRoleArn' --output text)
    AGENT_MODEL=$(aws bedrock-agent get-agent --agent-id "$SUPERVISOR_AGENT_ID" --region "$REGION" --query 'agent.foundationModel' --output text)
    AGENT_INSTRUCTION=$(aws bedrock-agent get-agent --agent-id "$SUPERVISOR_AGENT_ID" --region "$REGION" --query 'agent.instruction' --output text)

    # Update agent to enable collaboration
    aws bedrock-agent update-agent \
        --agent-id "$SUPERVISOR_AGENT_ID" \
        --agent-name "Supervisor" \
        --agent-resource-role-arn "$AGENT_ROLE" \
        --foundation-model "$AGENT_MODEL" \
        --instruction "$AGENT_INSTRUCTION" \
        --agent-collaboration "SUPERVISOR" \
        --region "$REGION" \
        &>/dev/null && echo -e "  ${GREEN}✅ Collaboration enabled${NC}" || echo -e "  ${RED}❌ Failed to enable collaboration${NC}"
else
    echo -e "  ${GREEN}✅ Collaboration already enabled${NC}"
fi

echo ""

###############################################################################
# Step 4: Associate Collaborators with Supervisor
###############################################################################

echo -e "${BLUE}Step 4: Associating Collaborators with Supervisor${NC}"
echo ""

# Associate SchedulingAgent
echo "  • Adding SchedulingAgent as collaborator..."
aws bedrock-agent associate-agent-collaborator \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --agent-version "DRAFT" \
    --collaborator-name "SchedulingAgent" \
    --agent-descriptor aliasArn="${SCHEDULING_ARN}" \
    --collaboration-instruction "Route queries about projects, appointments, scheduling, availability, and booking to this agent. Examples: 'List my projects', 'Book an appointment', 'What dates are available?'" \
    --relay-conversation-history "TO_COLLABORATOR" \
    --region "$REGION" \
    2>/dev/null && echo -e "    ${GREEN}✅ SchedulingAgent collaboration configured${NC}" || echo -e "    ${YELLOW}⚠️  SchedulingAgent already configured or error occurred${NC}"

# Associate InformationAgent
echo "  • Adding pf-information as collaborator..."
aws bedrock-agent associate-agent-collaborator \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --agent-version "DRAFT" \
    --collaborator-name "InformationAgent" \
    --agent-descriptor aliasArn="${INFORMATION_ARN}" \
    --collaboration-instruction "Route ONLY weather queries to this agent. This agent specializes in weather forecasts and conditions using Open-Meteo API. Examples: 'What's the weather in New York?', 'Is it going to rain in Miami?', 'Check weather for Tampa, FL', 'What's the weather at my project location?'." \
    --relay-conversation-history "TO_COLLABORATOR" \
    --region "$REGION" \
    2>/dev/null && echo -e "    ${GREEN}✅ InformationAgent collaboration configured${NC}" || echo -e "    ${YELLOW}⚠️  InformationAgent already configured or error occurred${NC}"

# Associate ChitchatAgent
echo "  • Adding pf-chitchat as collaborator..."
aws bedrock-agent associate-agent-collaborator \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --agent-version "DRAFT" \
    --collaborator-name "ChitchatAgent" \
    --agent-descriptor aliasArn="${CHITCHAT_ARN}" \
    --collaboration-instruction "Route greetings, casual conversation, thank you messages, and general pleasantries to this agent. Examples: 'Hello', 'Hi there', 'Thank you', 'Good morning', 'How are you?'" \
    --relay-conversation-history "TO_COLLABORATOR" \
    --region "$REGION" \
    2>/dev/null && echo -e "    ${GREEN}✅ ChitchatAgent collaboration configured${NC}" || echo -e "    ${YELLOW}⚠️  ChitchatAgent already configured or error occurred${NC}"

echo ""

###############################################################################
# Step 5: Prepare Supervisor
###############################################################################

echo -e "${BLUE}Step 5: Preparing Supervisor Agent${NC}"
echo ""

aws bedrock-agent prepare-agent \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --region "$REGION" \
    &>/dev/null && echo -e "  ${GREEN}✅ Supervisor prepare initiated${NC}" || echo -e "  ${RED}❌ Failed to prepare Supervisor${NC}"

# Wait for agent to be ready before verification
echo -e "  ${YELLOW}→ Waiting for agent to be ready...${NC}"
MAX_WAIT=60
WAIT_TIME=0
while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    AGENT_STATUS=$(aws bedrock-agent get-agent \
        --agent-id "$SUPERVISOR_AGENT_ID" \
        --region "$REGION" \
        --query 'agent.agentStatus' \
        --output text 2>/dev/null)

    if [ "$AGENT_STATUS" = "PREPARED" ] || [ "$AGENT_STATUS" = "NOT_PREPARED" ]; then
        echo -e "  ${GREEN}✅ Agent is ready (status: $AGENT_STATUS)${NC}"
        break
    fi

    sleep 3
    WAIT_TIME=$((WAIT_TIME + 3))
    echo -n "."
done
echo ""

if [ $WAIT_TIME -ge $MAX_WAIT ]; then
    echo -e "  ${YELLOW}⚠️  Timeout waiting for agent, proceeding anyway...${NC}"
fi

echo ""

###############################################################################
# Step 6: Verify Collaboration
###############################################################################

echo -e "${BLUE}Step 6: Verifying Collaboration${NC}"
echo ""

COLLABORATORS=$(aws bedrock-agent list-agent-collaborators \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --agent-version "DRAFT" \
    --region "$REGION" \
    --query 'agentCollaboratorSummaries[*].collaboratorName' \
    --output text 2>/dev/null || echo "")

if [[ -z "$COLLABORATORS" ]]; then
    echo -e "  ${RED}❌ No collaborators found${NC}"
    exit 1
else
    echo -e "  ${GREEN}✅ Collaborators associated:${NC}"
    for collab in $COLLABORATORS; do
        echo "     • $collab"
    done
fi

###############################################################################
# Step 6: Update Proxy Configuration
###############################################################################

echo -e "${BLUE}Step 6: Updating Proxy Configuration${NC}"
echo ""

PROXY_FILE="$BEDROCK_DIR/testing/ui/pf_proxy.py"

if [[ -f "$PROXY_FILE" ]]; then
    # Update the Supervisor agent ID in the proxy
    sed -i.bak "s/SUPERVISOR_AGENT_ID = '[A-Z0-9]*'/SUPERVISOR_AGENT_ID = '$SUPERVISOR_AGENT_ID'/" "$PROXY_FILE"
    rm -f "${PROXY_FILE}.bak"
    echo -e "  ${GREEN}✅ Proxy configuration updated with Supervisor ID${NC}"
else
    echo -e "  ${YELLOW}⚠️  Proxy file not found: $PROXY_FILE${NC}"
fi

echo ""
echo "================================================================================"
echo -e "${GREEN}✅ Collaboration Setup Complete!${NC}"
echo "================================================================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Test with the web UI:"
echo "   ${GREEN}cd testing/ui && ./launch_auth_demo.sh${NC}"
echo ""
echo "2. Test routing with CLI:"
echo "   ${GREEN}./scripts/test_supervisor_routing.sh${NC}"
echo ""
echo "3. Or invoke directly:"
echo "   ${GREEN}aws bedrock-agent-runtime invoke-agent \\${NC}"
echo "     ${GREEN}--agent-id $SUPERVISOR_AGENT_ID \\${NC}"
echo "     ${GREEN}--agent-alias-id TSTALIASID \\${NC}"
echo "     ${GREEN}--session-id test-\$(date +%s) \\${NC}"
echo "     ${GREEN}--input-text 'List my projects' \\${NC}"
echo "     ${GREEN}/tmp/supervisor_test.txt${NC}"
echo ""
echo "================================================================================"
echo ""
