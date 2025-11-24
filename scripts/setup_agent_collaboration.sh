#!/bin/bash

##############################################################################
# Setup Agent Collaboration
# This script creates versions, aliases, and configures collaboration
##############################################################################

set -e

# Configuration
REGION="us-east-1"
ACCOUNT_ID="618048437522"

# Agent IDs (from config/agent_ids.json)
SUPERVISOR_AGENT_ID="SGI6MRCQ1Q"
SCHEDULING_AGENT_ID="M9E3PUQB2Z"
INFORMATION_AGENT_ID="RYOSDIY0WW"
CHITCHAT_AGENT_ID="0HWWAV16DW"

echo ""
echo "=========================================="
echo "AWS Bedrock Agent Collaboration Setup"
echo "=========================================="
echo ""
echo "This script will:"
echo "  1. Prepare all specialist agents"
echo "  2. Update specialist agent aliases for collaboration"
echo "  3. Associate specialist agents with Supervisor"
echo "  4. Prepare Supervisor with collaborators"
echo ""
echo "Region: $REGION"
echo "Supervisor: $SUPERVISOR_AGENT_ID"
echo ""

##############################################################################
# Step 1: Prepare Specialist Agents
##############################################################################

echo "=========================================="
echo "Step 1: Preparing Specialist Agents"
echo "=========================================="
echo ""

echo "Preparing SchedulingAgent..."
aws bedrock-agent prepare-agent \
    --agent-id "$SCHEDULING_AGENT_ID" \
    --region "$REGION" \
    &>/dev/null && echo "  ✅ SchedulingAgent prepared"

echo "Preparing pf-information..."
aws bedrock-agent prepare-agent \
    --agent-id "$INFORMATION_AGENT_ID" \
    --region "$REGION" \
    &>/dev/null && echo "  ✅ pf-information prepared"

echo "Preparing pf-chitchat..."
aws bedrock-agent prepare-agent \
    --agent-id "$CHITCHAT_AGENT_ID" \
    --region "$REGION" \
    &>/dev/null && echo "  ✅ pf-chitchat prepared"

echo ""

##############################################################################
# Step 2: Update Specialist Agent Aliases
##############################################################################

echo "=========================================="
echo "Step 2: Updating Specialist Agent Aliases"
echo "=========================================="
echo ""
echo "AWS Bedrock collaboration requires specialist agents to use"
echo "different aliases than TSTALIASID for collaboration..."
echo ""

# Function to update or create collaboration alias
update_collaboration_alias() {
    local AGENT_ID=$1
    local AGENT_NAME=$2

    echo "Updating alias for $AGENT_NAME ($AGENT_ID)..."

    # Update the existing TSTALIASID alias to allow invocations
    aws bedrock-agent update-agent-alias \
        --agent-id "$AGENT_ID" \
        --agent-alias-id "TSTALIASID" \
        --agent-alias-name "CollaborationAlias" \
        --description "Alias for agent collaboration with Supervisor" \
        --routing-configuration "[{\"agentVersion\":\"DRAFT\"}]" \
        --region "$REGION" \
        &>/dev/null && echo "  ✅ $AGENT_NAME alias updated for collaboration"
}

update_collaboration_alias "$SCHEDULING_AGENT_ID" "SchedulingAgent"
update_collaboration_alias "$INFORMATION_AGENT_ID" "InformationAgent"
update_collaboration_alias "$CHITCHAT_AGENT_ID" "ChitchatAgent"

echo ""

##############################################################################
# Step 3: Associate Collaborators with Supervisor
##############################################################################

echo "=========================================="
echo "Step 3: Associating Collaborators"
echo "=========================================="
echo ""

# First, remove any existing collaborators (ignore errors if none exist)
echo "Cleaning up any existing collaborator associations..."
aws bedrock-agent list-agent-collaborators \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --agent-version "DRAFT" \
    --region "$REGION" 2>/dev/null | \
    jq -r '.agentCollaboratorSummaries[].collaboratorId' 2>/dev/null | \
while read -r collab_id; do
    if [ -n "$collab_id" ]; then
        echo "  • Removing existing collaborator: $collab_id..."
        aws bedrock-agent disassociate-agent-collaborator \
            --agent-id "$SUPERVISOR_AGENT_ID" \
            --agent-version "DRAFT" \
            --collaborator-id "$collab_id" \
            --region "$REGION" \
            &>/dev/null || true
    fi
done

echo ""
echo "Adding new collaborators..."

# Associate SchedulingAgent
echo "  • Adding SchedulingAgent..."
aws bedrock-agent associate-agent-collaborator \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --agent-version "DRAFT" \
    --agent-descriptor aliasArn=arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent-alias/$SCHEDULING_AGENT_ID/TSTALIASID \
    --collaborator-name "SchedulingAgent" \
    --collaboration-instruction "Route queries about projects, appointments, scheduling, availability, and booking to this agent. Examples: 'List my projects', 'Book an appointment', 'What dates are available?'" \
    --region "$REGION" \
    2>&1 | grep -v "^$" && echo "    ✅ SchedulingAgent associated" || echo "    ⚠️  SchedulingAgent association failed"

# Associate pf-information
echo "  • Adding InformationAgent..."
aws bedrock-agent associate-agent-collaborator \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --agent-version "DRAFT" \
    --agent-descriptor aliasArn=arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent-alias/$INFORMATION_AGENT_ID/TSTALIASID \
    --collaborator-name "InformationAgent" \
    --collaboration-instruction "Route queries about weather, project details, appointment status, and general information lookup to this agent. Examples: 'What's the weather in New York?', 'Get project details', 'Check appointment status'." \
    --region "$REGION" \
    2>&1 | grep -v "^$" && echo "    ✅ InformationAgent associated" || echo "    ⚠️  InformationAgent association failed"

# Associate pf-chitchat
echo "  • Adding ChitchatAgent..."
aws bedrock-agent associate-agent-collaborator \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --agent-version "DRAFT" \
    --agent-descriptor aliasArn=arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent-alias/$CHITCHAT_AGENT_ID/TSTALIASID \
    --collaborator-name "ChitchatAgent" \
    --collaboration-instruction "Route greetings, casual conversation, thank you messages, and general pleasantries to this agent. Examples: 'Hello', 'Hi there', 'Thank you', 'Good morning', 'How are you?'" \
    --region "$REGION" \
    2>&1 | grep -v "^$" && echo "    ✅ ChitchatAgent associated" || echo "    ⚠️  ChitchatAgent association failed"

echo ""

##############################################################################
# Step 4: Prepare Supervisor with Collaborators
##############################################################################

echo "=========================================="
echo "Step 4: Preparing Supervisor"
echo "=========================================="
echo ""

echo "Preparing Supervisor agent with collaborators..."
aws bedrock-agent prepare-agent \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --region "$REGION" \
    2>&1

PREPARE_STATUS=$?

if [ $PREPARE_STATUS -eq 0 ]; then
    echo ""
    echo "  ✅ Supervisor prepared successfully with collaborators"
else
    echo ""
    echo "  ⚠️  Supervisor preparation failed (exit code: $PREPARE_STATUS)"
    echo ""
    echo "Checking collaborator status..."
    aws bedrock-agent list-agent-collaborators \
        --agent-id "$SUPERVISOR_AGENT_ID" \
        --agent-version "DRAFT" \
        --region "$REGION"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Supervisor agent ($SUPERVISOR_AGENT_ID) collaboration status:"
aws bedrock-agent list-agent-collaborators \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --agent-version "DRAFT" \
    --region "$REGION" | jq -r '.agentCollaboratorSummaries[] | "  • \(.collaboratorName) (\(.collaboratorId))"'

echo ""
echo "Test collaboration with:"
echo "  aws bedrock-agent-runtime invoke-agent \\"
echo "    --agent-id $SUPERVISOR_AGENT_ID \\"
echo "    --agent-alias-id TSTALIASID \\"
echo "    --session-id test-\$(date +%s) \\"
echo "    --input-text 'List my projects' /tmp/output.txt"
echo ""
