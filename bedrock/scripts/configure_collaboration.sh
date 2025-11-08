#!/bin/bash

##############################################################################
# Configure Supervisor Agent Collaboration
# This script associates specialist agents with the Supervisor agent
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
echo "Configuring Supervisor Agent Collaboration"
echo "=========================================="
echo ""
echo "Supervisor Agent: $SUPERVISOR_AGENT_ID"
echo "Region: $REGION"
echo ""

# Associate SchedulingAgent as collaborator
echo "  • Adding SchedulingAgent as collaborator..."
aws bedrock-agent associate-agent-collaborator \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --agent-version "DRAFT" \
    --agent-descriptor "agentId=$SCHEDULING_AGENT_ID,agentAliasArn=arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent-alias/$SCHEDULING_AGENT_ID/TSTALIASID" \
    --collaborator-name "SchedulingAgent" \
    --collaboration-instruction "Route queries about projects, appointments, scheduling, availability, and booking to this agent. Examples: 'List my projects', 'Book an appointment', 'What dates are available?'" \
    --region "$REGION" \
    &>/dev/null && echo "    ✅ SchedulingAgent collaboration configured" || echo "    ⚠️  SchedulingAgent collaboration may already exist"

# Associate pf-information as collaborator
echo "  • Adding pf-information as collaborator..."
aws bedrock-agent associate-agent-collaborator \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --agent-version "DRAFT" \
    --agent-descriptor "agentId=$INFORMATION_AGENT_ID,agentAliasArn=arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent-alias/$INFORMATION_AGENT_ID/TSTALIASID" \
    --collaborator-name "InformationAgent" \
    --collaboration-instruction "Route queries about weather, project details, appointment status, and general information lookup to this agent. Examples: 'What's the weather in New York?', 'Get project details', 'Check appointment status'." \
    --region "$REGION" \
    &>/dev/null && echo "    ✅ InformationAgent collaboration configured" || echo "    ⚠️  InformationAgent collaboration may already exist"

# Associate pf-chitchat as collaborator
echo "  • Adding pf-chitchat as collaborator..."
aws bedrock-agent associate-agent-collaborator \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --agent-version "DRAFT" \
    --agent-descriptor "agentId=$CHITCHAT_AGENT_ID,agentAliasArn=arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent-alias/$CHITCHAT_AGENT_ID/TSTALIASID" \
    --collaborator-name "ChitchatAgent" \
    --collaboration-instruction "Route greetings, casual conversation, thank you messages, and general pleasantries to this agent. Examples: 'Hello', 'Hi there', 'Thank you', 'Good morning', 'How are you?'" \
    --region "$REGION" \
    &>/dev/null && echo "    ✅ ChitchatAgent collaboration configured" || echo "    ⚠️  ChitchatAgent collaboration may already exist"

echo ""
echo "  ✅ Agent collaboration configuration complete"
echo "  ℹ️  Preparing Supervisor agent to activate collaborators..."
echo ""

# Prepare Supervisor again to activate the collaborator configuration
aws bedrock-agent prepare-agent \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --region "$REGION" \
    &>/dev/null && echo "  ✅ Supervisor prepared with collaborators" || echo "  ⚠️  Failed to prepare Supervisor agent"

echo ""
echo "=========================================="
echo "Collaboration Configuration Complete!"
echo "=========================================="
echo ""
echo "Supervisor agent ($SUPERVISOR_AGENT_ID) is now configured with:"
echo "  • SchedulingAgent ($SCHEDULING_AGENT_ID)"
echo "  • InformationAgent ($INFORMATION_AGENT_ID)"
echo "  • ChitchatAgent ($CHITCHAT_AGENT_ID)"
echo ""
echo "Test with:"
echo "  aws bedrock-agent-runtime invoke-agent \\"
echo "    --agent-id $SUPERVISOR_AGENT_ID \\"
echo "    --agent-alias-id TSTALIASID \\"
echo "    --session-id test-\$(date +%s) \\"
echo "    --input-text 'List my projects' output.txt"
echo ""
