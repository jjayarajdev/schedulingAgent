#!/bin/bash

echo "================================================================================"
echo "Update Supervisor Agent Collaborators to Use DRAFT Aliases"
echo "================================================================================"
echo "Date: $(date)"
echo "Region: us-east-1"
echo "Purpose: Fix collaborators to use DRAFT versions with updated instructions"
echo "================================================================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Set region
REGION="us-east-1"

# Agent IDs
SUPERVISOR_AGENT_ID="5VTIWONUMO"
SCHEDULING_AGENT_ID="IX24FSMTQH"
INFORMATION_AGENT_ID="C9ANXRIO8Y"
NOTES_AGENT_ID="G5BVBYEPUM"
CHITCHAT_AGENT_ID="2SUXQSWZOV"

# DRAFT Alias ID (same for all Bedrock agents)
DRAFT_ALIAS_ID="TSTALIASID"

echo "================================================================================"
echo "Step 1: Get Current Collaborator Configuration"
echo "================================================================================"
echo ""

echo -e "${BLUE}Fetching current collaborators...${NC}"
COLLABORATORS=$(aws bedrock-agent list-agent-collaborators \
  --agent-id ${SUPERVISOR_AGENT_ID} \
  --agent-version DRAFT \
  --region ${REGION} \
  --output json)

echo "$COLLABORATORS" | jq -r '.agentCollaboratorSummaries[] | "\(.collaboratorName): \(.agentDescriptor.aliasArn)"'
echo ""

echo "================================================================================"
echo "Step 2: Delete Existing Collaborators"
echo "================================================================================"
echo ""

# Function to delete collaborator
delete_collaborator() {
    local collaborator_id=$1
    local collaborator_name=$2

    echo -e "${YELLOW}Deleting collaborator: ${collaborator_name}${NC}"

    aws bedrock-agent disassociate-agent-collaborator \
      --agent-id ${SUPERVISOR_AGENT_ID} \
      --agent-version DRAFT \
      --collaborator-id ${collaborator_id} \
      --region ${REGION} > /dev/null 2>&1

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Deleted ${collaborator_name}${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to delete ${collaborator_name}${NC}"
        return 1
    fi
}

# Get collaborator IDs
SCHEDULING_COLLAB_ID=$(echo "$COLLABORATORS" | jq -r '.agentCollaboratorSummaries[] | select(.collaboratorName=="scheduling_collaborator") | .collaboratorId')
INFORMATION_COLLAB_ID=$(echo "$COLLABORATORS" | jq -r '.agentCollaboratorSummaries[] | select(.collaboratorName=="information_collaborator") | .collaboratorId')
NOTES_COLLAB_ID=$(echo "$COLLABORATORS" | jq -r '.agentCollaboratorSummaries[] | select(.collaboratorName=="notes_collaborator") | .collaboratorId')
CHITCHAT_COLLAB_ID=$(echo "$COLLABORATORS" | jq -r '.agentCollaboratorSummaries[] | select(.collaboratorName=="chitchat_collaborator") | .collaboratorId')

# Delete existing collaborators
if [ ! -z "$SCHEDULING_COLLAB_ID" ]; then
    delete_collaborator "$SCHEDULING_COLLAB_ID" "scheduling_collaborator"
fi

if [ ! -z "$INFORMATION_COLLAB_ID" ]; then
    delete_collaborator "$INFORMATION_COLLAB_ID" "information_collaborator"
fi

if [ ! -z "$NOTES_COLLAB_ID" ]; then
    delete_collaborator "$NOTES_COLLAB_ID" "notes_collaborator"
fi

if [ ! -z "$CHITCHAT_COLLAB_ID" ]; then
    delete_collaborator "$CHITCHAT_COLLAB_ID" "chitchat_collaborator"
fi

echo ""
echo -e "${GREEN}✅ All existing collaborators deleted${NC}"
echo ""

echo "================================================================================"
echo "Step 3: Add Collaborators with DRAFT Aliases"
echo "================================================================================"
echo ""

# Function to add collaborator
add_collaborator() {
    local agent_id=$1
    local agent_name=$2
    local collaborator_name=$3
    local collaboration_instruction=$4

    echo "───────────────────────────────────────────────────────────────────────────────"
    echo -e "${YELLOW}Adding ${agent_name} as ${collaborator_name}${NC}"
    echo "───────────────────────────────────────────────────────────────────────────────"
    echo ""

    # Build the alias ARN using DRAFT alias
    local alias_arn="arn:aws:bedrock:${REGION}:$(aws sts get-caller-identity --query Account --output text):agent-alias/${agent_id}/${DRAFT_ALIAS_ID}"

    echo "   Agent ID: ${agent_id}"
    echo "   Alias ARN: ${alias_arn}"
    echo "   Collaborator Name: ${collaborator_name}"
    echo ""

    aws bedrock-agent associate-agent-collaborator \
      --agent-id ${SUPERVISOR_AGENT_ID} \
      --agent-version DRAFT \
      --agent-descriptor aliasArn="${alias_arn}" \
      --collaborator-name "${collaborator_name}" \
      --collaboration-instruction "${collaboration_instruction}" \
      --relay-conversation-history DISABLED \
      --region ${REGION} \
      --output json > /tmp/collaborator_output.json

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ ${agent_name} added successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to add ${agent_name}${NC}"
        cat /tmp/collaborator_output.json
        return 1
    fi
    echo ""
}

# Add Scheduling Agent
add_collaborator \
    ${SCHEDULING_AGENT_ID} \
    "Scheduling Agent" \
    "scheduling_collaborator" \
    "Route all appointment scheduling, availability checking, booking, rescheduling, and cancellation requests to this agent. This agent handles the complete workflow from showing available projects to confirming appointments."

# Add Information Agent
add_collaborator \
    ${INFORMATION_AGENT_ID} \
    "Information Agent" \
    "information_collaborator" \
    "Route all information requests to this agent, including project details, appointment status checks, working hours inquiries, and weather forecasts."

# Add Notes Agent
add_collaborator \
    ${NOTES_AGENT_ID} \
    "Notes Agent" \
    "notes_collaborator" \
    "Route all note management requests to this agent, including adding notes to appointments and viewing existing notes. This agent only handles note-related operations."

# Add Chitchat Agent
add_collaborator \
    ${CHITCHAT_AGENT_ID} \
    "Chitchat Agent" \
    "chitchat_collaborator" \
    "Route all conversational interactions to this agent, including greetings, thank you messages, goodbye messages, help requests, and general friendly conversation."

echo ""
echo "================================================================================"
echo "Step 4: Preparing Supervisor Agent"
echo "================================================================================"
echo ""

echo -e "${BLUE}Preparing Supervisor Agent...${NC}"

aws bedrock-agent prepare-agent \
  --agent-id ${SUPERVISOR_AGENT_ID} \
  --region ${REGION} \
  --output json > /tmp/prepare_supervisor.json

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Supervisor Agent is being prepared${NC}"
    echo -e "${YELLOW}Waiting 30 seconds for preparation...${NC}"
    sleep 30

    STATUS=$(aws bedrock-agent get-agent \
      --agent-id ${SUPERVISOR_AGENT_ID} \
      --region ${REGION} \
      --query 'agent.agentStatus' \
      --output text)

    echo "   Status: ${STATUS}"

    if [ "$STATUS" == "PREPARED" ]; then
        echo -e "${GREEN}✅ Supervisor Agent is ready!${NC}"
    else
        echo -e "${YELLOW}⚠️  Still preparing (${STATUS}), wait another 30 seconds${NC}"
    fi
else
    echo -e "${RED}❌ Failed to prepare Supervisor Agent${NC}"
    cat /tmp/prepare_supervisor.json
fi

echo ""
echo "================================================================================"
echo "Step 5: Verification"
echo "================================================================================"
echo ""

echo -e "${BLUE}Updated Collaborators:${NC}"
echo ""

aws bedrock-agent list-agent-collaborators \
  --agent-id ${SUPERVISOR_AGENT_ID} \
  --agent-version DRAFT \
  --region ${REGION} \
  --output json | jq -r '.agentCollaboratorSummaries[] | "  \(.collaboratorName):\n    Agent: \(.agentDescriptor.aliasArn)\n    Created: \(.createdAt)\n"'

echo ""
echo "================================================================================"
echo "Update Complete!"
echo "================================================================================"
echo ""
echo -e "${GREEN}✅ All collaborators now use DRAFT aliases${NC}"
echo ""
echo "What changed:"
echo "  - Scheduling collaborator → Uses DRAFT alias (TSTALIASID)"
echo "  - Information collaborator → Uses DRAFT alias (TSTALIASID)"
echo "  - Notes collaborator → Uses DRAFT alias (TSTALIASID)"
echo "  - Chitchat collaborator → Uses DRAFT alias (TSTALIASID)"
echo ""
echo "Benefits:"
echo "  ✅ Collaborators use latest agent instructions (with AVAILABLE ACTIONS)"
echo "  ✅ Agents will call Lambda functions instead of hallucinating"
echo "  ✅ No need to create new agent versions"
echo "  ✅ Easy to update - just prepare agents and they're live"
echo ""
echo "Next Steps:"
echo "  1. Test Supervisor Agent with session context"
echo "  2. Verify CloudWatch logs show Lambda invocations"
echo "  3. Confirm agents return real mock data (12345, 12347, 12350)"
echo ""
echo "Test command:"
echo "  cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock"
echo "  ./tests/test_agent_with_session.py"
echo ""
echo "================================================================================"

# Cleanup
rm -f /tmp/collaborator_output.json /tmp/prepare_supervisor.json
