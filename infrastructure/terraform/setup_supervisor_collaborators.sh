#!/bin/bash
set -e

###############################################################################
# Supervisor Collaborator Setup Script
# Purpose: Associate specialist agents as collaborators to supervisor agent
# Created: October 21, 2025
###############################################################################

REGION="us-east-1"
SUPERVISOR_AGENT="WF1S95L7X1"

# Get v1 alias IDs for all specialist agents
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        Supervisor Collaborator Setup Script                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Fetching specialist agent alias IDs..."

SCHEDULING_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "TIGRBGSXCS" --region "$REGION" --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' --output text)
INFORMATION_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "JEK4SDJOOU" --region "$REGION" --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' --output text)
NOTES_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "CF0IPHCFFY" --region "$REGION" --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' --output text)
CHITCHAT_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "GXVZEOBQ64" --region "$REGION" --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' --output text)

echo "✓ Alias IDs fetched:"
echo "  Scheduling: TIGRBGSXCS / $SCHEDULING_ALIAS"
echo "  Information: JEK4SDJOOU / $INFORMATION_ALIAS"
echo "  Notes: CF0IPHCFFY / $NOTES_ALIAS"
echo "  Chitchat: GXVZEOBQ64 / $CHITCHAT_ALIAS"
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "Step 1: Associating Specialist Agents as Collaborators"
echo "═══════════════════════════════════════════════════════════════"

# Associate Scheduling Agent
echo "📋 Associating Scheduling-Agent..."
aws bedrock-agent associate-agent-collaborator \
  --agent-id "$SUPERVISOR_AGENT" \
  --agent-version "DRAFT" \
  --collaborator-name "Scheduling-Agent" \
  --agent-descriptor "aliasArn=arn:aws:bedrock:$REGION:618048437522:agent-alias/TIGRBGSXCS/$SCHEDULING_ALIAS" \
  --collaboration-instruction "This agent handles all appointment scheduling tasks including: listing available dates and time slots for projects, confirming and scheduling new appointments, rescheduling existing appointments, and canceling appointments. Route all scheduling-related requests to this agent." \
  --relay-conversation-history "TO_COLLABORATOR" \
  --region "$REGION" > /dev/null 2>&1 && echo "✓ Scheduling-Agent associated" || echo "  (May already exist)"

# Associate Information Agent
echo "📋 Associating Information-Agent..."
aws bedrock-agent associate-agent-collaborator \
  --agent-id "$SUPERVISOR_AGENT" \
  --agent-version "DRAFT" \
  --collaborator-name "Information-Agent" \
  --agent-descriptor "aliasArn=arn:aws:bedrock:$REGION:618048437522:agent-alias/JEK4SDJOOU/$INFORMATION_ALIAS" \
  --collaboration-instruction "This agent provides information about projects, orders, and their status. It can retrieve project details, order information, installation addresses, project types, and current status. Route all information and status inquiry requests to this agent." \
  --relay-conversation-history "TO_COLLABORATOR" \
  --region "$REGION" > /dev/null 2>&1 && echo "✓ Information-Agent associated" || echo "  (May already exist)"

# Associate Notes Agent
echo "📋 Associating Notes-Agent..."
aws bedrock-agent associate-agent-collaborator \
  --agent-id "$SUPERVISOR_AGENT" \
  --agent-version "DRAFT" \
  --collaborator-name "Notes-Agent" \
  --agent-descriptor "aliasArn=arn:aws:bedrock:$REGION:618048437522:agent-alias/CF0IPHCFFY/$NOTES_ALIAS" \
  --collaboration-instruction "This agent manages notes and communication related to projects. It can create, retrieve, update, and delete notes associated with projects and customers. Route all note-taking and note-retrieval requests to this agent." \
  --relay-conversation-history "TO_COLLABORATOR" \
  --region "$REGION" > /dev/null 2>&1 && echo "✓ Notes-Agent associated" || echo "  (May already exist)"

# Associate Chitchat Agent
echo "📋 Associating Chitchat-Agent..."
aws bedrock-agent associate-agent-collaborator \
  --agent-id "$SUPERVISOR_AGENT" \
  --agent-version "DRAFT" \
  --collaborator-name "Chitchat-Agent" \
  --agent-descriptor "aliasArn=arn:aws:bedrock:$REGION:618048437522:agent-alias/GXVZEOBQ64/$CHITCHAT_ALIAS" \
  --collaboration-instruction "This agent handles casual conversation, greetings, general inquiries, and small talk. It provides friendly, conversational responses to non-task-specific questions. Route all general conversation and greeting requests to this agent." \
  --relay-conversation-history "TO_COLLABORATOR" \
  --region "$REGION" > /dev/null 2>&1 && echo "✓ Chitchat-Agent associated" || echo "  (May already exist)"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Step 2: Preparing Supervisor Agent"
echo "═══════════════════════════════════════════════════════════════"

echo "🔧 Preparing supervisor agent..."
aws bedrock-agent prepare-agent \
  --agent-id "$SUPERVISOR_AGENT" \
  --region "$REGION" > /dev/null

echo "⏳ Waiting 15 seconds for agent to be ready..."
sleep 15

AGENT_STATUS=$(aws bedrock-agent get-agent --agent-id "$SUPERVISOR_AGENT" --region "$REGION" --query 'agent.agentStatus' --output text)
echo "✓ Agent status: $AGENT_STATUS"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Step 3: Verifying Collaborators"
echo "═══════════════════════════════════════════════════════════════"

echo "Listing associated collaborators..."
aws bedrock-agent list-agent-collaborators \
  --agent-id "$SUPERVISOR_AGENT" \
  --agent-version "DRAFT" \
  --region "$REGION" \
  --query 'agentCollaboratorSummaries[*].[collaboratorName,collaboratorId]' \
  --output table

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Supervisor Setup Complete!                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Supervisor Agent ID: $SUPERVISOR_AGENT"
echo "Collaborators: 4 specialist agents"
echo "Conversation Relay: TO_COLLABORATOR (enabled)"
echo ""
echo "Next: Test supervisor with 'python3 test_supervisor.py'"
echo ""
