#!/bin/bash

echo "================================================================================"
echo "Update Supervisor Agent Collaborators - Version-based Approach"
echo "================================================================================"
echo "Date: $(date)"
echo "Region: us-east-1"
echo "Purpose: Create new versions with updated instructions and update collaborators"
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

echo "================================================================================"
echo "Step 1: Create New Versions from DRAFT (with updated instructions)"
echo "================================================================================"
echo ""

# Function to create agent version
create_agent_version() {
    local agent_id=$1
    local agent_name=$2

    echo -e "${BLUE}Creating new version for ${agent_name}...${NC}"

    # Create version from DRAFT
    RESULT=$(aws bedrock-agent create-agent-version \
      --agent-id ${agent_id} \
      --region ${REGION} \
      --output json 2>&1)

    if [ $? -eq 0 ]; then
        VERSION=$(echo "$RESULT" | jq -r '.agentVersion.version')
        echo -e "${GREEN}✅ Created version ${VERSION} for ${agent_name}${NC}"
        echo "$VERSION"
        return 0
    else
        echo -e "${RED}❌ Failed to create version for ${agent_name}${NC}"
        echo "$RESULT"
        echo "0"
        return 1
    fi
}

# Create new versions for each agent
echo -e "${YELLOW}Creating versions with updated instructions...${NC}"
echo ""

SCHEDULING_VERSION=$(create_agent_version "$SCHEDULING_AGENT_ID" "Scheduling Agent")
INFORMATION_VERSION=$(create_agent_version "$INFORMATION_AGENT_ID" "Information Agent")
NOTES_VERSION=$(create_agent_version "$NOTES_AGENT_ID" "Notes Agent")
CHITCHAT_VERSION=$(create_agent_version "$CHITCHAT_AGENT_ID" "Chitchat Agent")

echo ""
echo "New Versions Created:"
echo "  Scheduling: v${SCHEDULING_VERSION}"
echo "  Information: v${INFORMATION_VERSION}"
echo "  Notes: v${NOTES_VERSION}"
echo "  Chitchat: v${CHITCHAT_VERSION}"
echo ""

# Wait for versions to be ready
echo -e "${BLUE}Waiting 10 seconds for versions to stabilize...${NC}"
sleep 10
echo ""

echo "================================================================================"
echo "Step 2: Update Version Aliases to Point to New Versions"
echo "================================================================================"
echo ""

# Function to update or create alias
update_alias() {
    local agent_id=$1
    local agent_name=$2
    local version=$3
    local alias_name="v${version}"

    echo -e "${BLUE}Updating alias ${alias_name} for ${agent_name}...${NC}"

    # Check if alias exists
    EXISTING_ALIAS=$(aws bedrock-agent list-agent-aliases \
      --agent-id ${agent_id} \
      --region ${REGION} \
      --query "agentAliasSummaries[?agentAliasName=='${alias_name}'].agentAliasId" \
      --output text)

    if [ ! -z "$EXISTING_ALIAS" ] && [ "$EXISTING_ALIAS" != "None" ]; then
        # Update existing alias
        aws bedrock-agent update-agent-alias \
          --agent-id ${agent_id} \
          --agent-alias-id ${EXISTING_ALIAS} \
          --agent-alias-name ${alias_name} \
          --routing-configuration "agentVersion=${version}" \
          --region ${REGION} > /dev/null 2>&1

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Updated alias ${alias_name} → version ${version} (${EXISTING_ALIAS})${NC}"
            echo "$EXISTING_ALIAS"
        else
            echo -e "${RED}❌ Failed to update alias${NC}"
            echo ""
        fi
    else
        # Create new alias
        RESULT=$(aws bedrock-agent create-agent-alias \
          --agent-id ${agent_id} \
          --agent-alias-name ${alias_name} \
          --routing-configuration "agentVersion=${version}" \
          --region ${REGION} \
          --output json 2>&1)

        if [ $? -eq 0 ]; then
            ALIAS_ID=$(echo "$RESULT" | jq -r '.agentAlias.agentAliasId')
            echo -e "${GREEN}✅ Created alias ${alias_name} → version ${version} (${ALIAS_ID})${NC}"
            echo "$ALIAS_ID"
        else
            echo -e "${RED}❌ Failed to create alias${NC}"
            echo "$RESULT"
            echo ""
        fi
    fi
}

# Update aliases for each agent
SCHEDULING_ALIAS_ID=$(update_alias "$SCHEDULING_AGENT_ID" "Scheduling Agent" "$SCHEDULING_VERSION")
INFORMATION_ALIAS_ID=$(update_alias "$INFORMATION_AGENT_ID" "Information Agent" "$INFORMATION_VERSION")
NOTES_ALIAS_ID=$(update_alias "$NOTES_AGENT_ID" "Notes Agent" "$NOTES_VERSION")
CHITCHAT_ALIAS_ID=$(update_alias "$CHITCHAT_AGENT_ID" "Chitchat Agent" "$CHITCHAT_VERSION")

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
echo "Step 4: Add Collaborators with New Version Aliases"
echo "================================================================================"
echo ""

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

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

# Add collaborators with new version aliases
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

echo -e "${GREEN}✅ All collaborators updated to use new version aliases${NC}"
echo ""

echo "What changed:"
echo "  - Scheduling collaborator → v${SCHEDULING_VERSION} (${SCHEDULING_ALIAS_ID})"
echo "  - Information collaborator → v${INFORMATION_VERSION} (${INFORMATION_ALIAS_ID})"
echo "  - Notes collaborator → v${NOTES_VERSION} (${NOTES_ALIAS_ID})"
echo "  - Chitchat collaborator → v${CHITCHAT_VERSION} (${CHITCHAT_ALIAS_ID})"
echo ""

echo "Benefits:"
echo "  ✅ Collaborators use latest agent instructions (with AVAILABLE ACTIONS)"
echo "  ✅ Agents will call Lambda functions instead of hallucinating"
echo "  ✅ Version-based aliases allow for stable collaboration"
echo "  ✅ Can roll back to previous versions if needed"
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
