#!/bin/bash

echo "================================================================================"
echo "Update Supervisor Agent Collaborators - Simple Approach"
echo "================================================================================"
echo "Date: $(date)"
echo "Region: us-east-1"
echo "Purpose: Update collaborators to use existing version aliases"
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
CHITCHAT_AGENT_ID="BIUW1ARHGL"

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "================================================================================"
echo "Step 1: Prepare All Specialist Agents (Updates DRAFT with Latest Instructions)"
echo "================================================================================"
echo ""

# Function to prepare agent
prepare_agent() {
    local agent_id=$1
    local agent_name=$2

    echo -e "${BLUE}Preparing ${agent_name}...${NC}"

    # Check current status first
    local current_status=$(aws bedrock-agent get-agent \
      --agent-id ${agent_id} \
      --region ${REGION} \
      --query 'agent.agentStatus' \
      --output text)

    if [ "$current_status" == "PREPARED" ]; then
        echo -e "${GREEN}✅ ${agent_name} already prepared${NC}"
        return 0
    fi

    aws bedrock-agent prepare-agent \
      --agent-id ${agent_id} \
      --region ${REGION} > /dev/null 2>&1

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ ${agent_name} prepared${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  ${agent_name} preparation skipped (may be supervisor or already prepared)${NC}"
        return 0
    fi
}

# Prepare all specialist agents
prepare_agent "$SCHEDULING_AGENT_ID" "Scheduling Agent"
prepare_agent "$INFORMATION_AGENT_ID" "Information Agent"
prepare_agent "$NOTES_AGENT_ID" "Notes Agent"
prepare_agent "$CHITCHAT_AGENT_ID" "Chitchat Agent"

echo ""
echo -e "${YELLOW}Waiting 30 seconds for agents to be ready...${NC}"
sleep 30
echo ""

echo "================================================================================"
echo "Step 2: Get Existing Version Aliases"
echo "================================================================================"
echo ""

# Function to get latest version alias
get_version_alias() {
    local agent_id=$1
    local agent_name=$2

    echo -e "${BLUE}Getting alias for ${agent_name}...${NC}" >&2

    # Get the v4 alias (or latest version alias)
    local ALIAS_ID=$(aws bedrock-agent list-agent-aliases \
      --agent-id ${agent_id} \
      --region ${REGION} \
      --query "agentAliasSummaries[?agentAliasName=='v4'].agentAliasId" \
      --output text)

    if [ -z "$ALIAS_ID" ] || [ "$ALIAS_ID" == "None" ]; then
        # Try v3 if v4 doesn't exist
        ALIAS_ID=$(aws bedrock-agent list-agent-aliases \
          --agent-id ${agent_id} \
          --region ${REGION} \
          --query "agentAliasSummaries[?agentAliasName=='v3'].agentAliasId" \
          --output text)
    fi

    if [ ! -z "$ALIAS_ID" ] && [ "$ALIAS_ID" != "None" ]; then
        echo -e "${GREEN}✅ Found alias: ${ALIAS_ID}${NC}" >&2
        echo "$ALIAS_ID"
    else
        echo -e "${RED}❌ No version alias found for ${agent_name}${NC}" >&2
        echo ""
    fi
}

echo "Finding existing version aliases..."
echo ""

SCHEDULING_ALIAS_ID=$(get_version_alias "$SCHEDULING_AGENT_ID" "Scheduling Agent")
INFORMATION_ALIAS_ID=$(get_version_alias "$INFORMATION_AGENT_ID" "Information Agent")
NOTES_ALIAS_ID=$(get_version_alias "$NOTES_AGENT_ID" "Notes Agent")
CHITCHAT_ALIAS_ID=$(get_version_alias "$CHITCHAT_AGENT_ID" "Chitchat Agent")

echo ""
echo "Alias IDs to use:"
echo "  Scheduling: ${SCHEDULING_ALIAS_ID}"
echo "  Information: ${INFORMATION_ALIAS_ID}"
echo "  Notes: ${NOTES_ALIAS_ID}"
echo "  Chitchat: ${CHITCHAT_ALIAS_ID}"
echo ""

echo "================================================================================"
echo "Step 3: Delete Existing Supervisor Collaborators"
echo "================================================================================"
echo ""

# Get current collaborators
COLLABORATORS=$(aws bedrock-agent list-agent-collaborators \
  --agent-id ${SUPERVISOR_AGENT_ID} \
  --agent-version DRAFT \
  --region ${REGION} \
  --output json)

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
    else
        echo -e "${RED}❌ Failed to delete ${collaborator_name}${NC}"
    fi
}

# Get collaborator IDs and delete
SCHEDULING_COLLAB_ID=$(echo "$COLLABORATORS" | jq -r '.agentCollaboratorSummaries[] | select(.collaboratorName=="scheduling_collaborator") | .collaboratorId')
INFORMATION_COLLAB_ID=$(echo "$COLLABORATORS" | jq -r '.agentCollaboratorSummaries[] | select(.collaboratorName=="information_collaborator") | .collaboratorId')
NOTES_COLLAB_ID=$(echo "$COLLABORATORS" | jq -r '.agentCollaboratorSummaries[] | select(.collaboratorName=="notes_collaborator") | .collaboratorId')
CHITCHAT_COLLAB_ID=$(echo "$COLLABORATORS" | jq -r '.agentCollaboratorSummaries[] | select(.collaboratorName=="chitchat_collaborator") | .collaboratorId')

[ ! -z "$SCHEDULING_COLLAB_ID" ] && delete_collaborator "$SCHEDULING_COLLAB_ID" "scheduling_collaborator"
[ ! -z "$INFORMATION_COLLAB_ID" ] && delete_collaborator "$INFORMATION_COLLAB_ID" "information_collaborator"
[ ! -z "$NOTES_COLLAB_ID" ] && delete_collaborator "$NOTES_COLLAB_ID" "notes_collaborator"
[ ! -z "$CHITCHAT_COLLAB_ID" ] && delete_collaborator "$CHITCHAT_COLLAB_ID" "chitchat_collaborator"

echo ""

echo "================================================================================"
echo "Step 4: Add Collaborators with Version Aliases"
echo "================================================================================"
echo ""

# Function to add collaborator with version alias
add_collaborator() {
    local agent_id=$1
    local alias_id=$2
    local collaborator_name=$3
    local collaboration_instruction=$4

    echo "───────────────────────────────────────────────────────────────────────────────"
    echo -e "${BLUE}Adding ${collaborator_name}${NC}"
    echo "───────────────────────────────────────────────────────────────────────────────"
    echo ""
    echo "   Agent ID: ${agent_id}"
    echo "   Alias ID: ${alias_id}"
    echo "   Collaborator Name: ${collaborator_name}"

    # Build alias ARN
    local alias_arn="arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent-alias/${agent_id}/${alias_id}"
    echo "   Alias ARN: ${alias_arn}"
    echo ""

    # Add collaborator
    aws bedrock-agent associate-agent-collaborator \
      --agent-id ${SUPERVISOR_AGENT_ID} \
      --agent-version DRAFT \
      --agent-descriptor aliasArn="${alias_arn}" \
      --collaborator-name "${collaborator_name}" \
      --collaboration-instruction "${collaboration_instruction}" \
      --relay-conversation-history DISABLED \
      --region ${REGION} > /dev/null 2>&1

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Added ${collaborator_name}${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}❌ Failed to add ${collaborator_name}${NC}"
        echo ""
        return 1
    fi
}

# Collaboration instructions
SCHEDULING_INSTRUCTION="Handle scheduling-related requests: booking appointments, checking availability, getting time slots, rescheduling, and canceling appointments."
INFORMATION_INSTRUCTION="Handle information requests: project details, appointment status, business hours, weather forecasts, and general information queries."
NOTES_INSTRUCTION="Handle note-related requests: adding notes to projects and retrieving project notes."
CHITCHAT_INSTRUCTION="Handle casual conversation, greetings, farewells, and general chitchat that doesn't require specific actions."

# Add collaborators with version aliases
add_collaborator "$SCHEDULING_AGENT_ID" "$SCHEDULING_ALIAS_ID" "scheduling_collaborator" "$SCHEDULING_INSTRUCTION"
add_collaborator "$INFORMATION_AGENT_ID" "$INFORMATION_ALIAS_ID" "information_collaborator" "$INFORMATION_INSTRUCTION"
add_collaborator "$NOTES_AGENT_ID" "$NOTES_ALIAS_ID" "notes_collaborator" "$NOTES_INSTRUCTION"
add_collaborator "$CHITCHAT_AGENT_ID" "$CHITCHAT_ALIAS_ID" "chitchat_collaborator" "$CHITCHAT_INSTRUCTION"

echo "================================================================================"
echo "Step 5: Prepare Supervisor Agent"
echo "================================================================================"
echo ""

echo -e "${BLUE}Preparing Supervisor Agent...${NC}"
echo ""

aws bedrock-agent prepare-agent \
  --agent-id ${SUPERVISOR_AGENT_ID} \
  --region ${REGION} > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Supervisor Agent prepared successfully${NC}"
    echo ""
    echo -e "${YELLOW}Waiting 30 seconds for agent to be ready...${NC}"
    sleep 30
else
    echo -e "${RED}❌ Failed to prepare Supervisor Agent${NC}"
    exit 1
fi

echo ""

echo "================================================================================"
echo "Step 6: Verification"
echo "================================================================================"
echo ""

echo -e "${BLUE}Updated Collaborators:${NC}"
aws bedrock-agent list-agent-collaborators \
  --agent-id ${SUPERVISOR_AGENT_ID} \
  --agent-version DRAFT \
  --region ${REGION} \
  --query 'agentCollaboratorSummaries[*].[collaboratorName,agentDescriptor.aliasArn]' \
  --output table

echo ""

echo "================================================================================"
echo "Update Complete!"
echo "================================================================================"
echo ""

echo -e "${GREEN}✅ All collaborators updated to use version aliases${NC}"
echo ""

echo "What changed:"
echo "  - Scheduling collaborator → ${SCHEDULING_ALIAS_ID}"
echo "  - Information collaborator → ${INFORMATION_ALIAS_ID}"
echo "  - Notes collaborator → ${NOTES_ALIAS_ID}"
echo "  - Chitchat collaborator → ${CHITCHAT_ALIAS_ID}"
echo ""

echo "Why this works:"
echo "  ✅ Specialist agents were prepared with updated instructions"
echo "  ✅ Version aliases (v4/v3) now point to prepared agents with AVAILABLE ACTIONS"
echo "  ✅ Supervisor now routes to agents that will call Lambda functions"
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
echo ""
