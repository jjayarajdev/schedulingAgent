#!/bin/bash
set -e

###############################################################################
# Supervisor Collaborator Setup Script (v2 - Terraform Output Based)
# Purpose: Associate specialist agents as collaborators to supervisor agent
# Uses: Terraform outputs instead of hardcoded agent IDs
# Created: October 21, 2025
###############################################################################

REGION="us-east-1"
ACCOUNT_ID="618048437522"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        Supervisor Collaborator Setup Script (v2)            ║"
echo "║              (Using Terraform Outputs)                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Get agent IDs from Terraform outputs
echo "📊 Fetching agent IDs from Terraform..."
SUPERVISOR_AGENT=$(terraform output -raw supervisor_agent_id 2>/dev/null)
SCHEDULING_AGENT=$(terraform output -raw scheduling_agent_id 2>/dev/null)
INFORMATION_AGENT=$(terraform output -raw information_agent_id 2>/dev/null)
NOTES_AGENT=$(terraform output -raw notes_agent_id 2>/dev/null)
CHITCHAT_AGENT=$(terraform output -raw chitchat_agent_id 2>/dev/null)

# Validate all IDs were retrieved
if [[ -z "$SUPERVISOR_AGENT" || -z "$SCHEDULING_AGENT" || -z "$INFORMATION_AGENT" || -z "$NOTES_AGENT" || -z "$CHITCHAT_AGENT" ]]; then
    echo "❌ Error: Failed to retrieve agent IDs from Terraform outputs"
    echo "   Make sure you've run 'terraform apply' first"
    exit 1
fi

echo "✓ Agent IDs retrieved:"
echo "  Supervisor:   $SUPERVISOR_AGENT"
echo "  Scheduling:   $SCHEDULING_AGENT"
echo "  Information:  $INFORMATION_AGENT"
echo "  Notes:        $NOTES_AGENT"
echo "  Chitchat:     $CHITCHAT_AGENT"
echo ""

# Get v1 alias IDs for all specialist agents
echo "Fetching specialist agent alias IDs..."

SCHEDULING_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "$SCHEDULING_AGENT" --region "$REGION" --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' --output text)
INFORMATION_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "$INFORMATION_AGENT" --region "$REGION" --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' --output text)
NOTES_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "$NOTES_AGENT" --region "$REGION" --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' --output text)
CHITCHAT_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "$CHITCHAT_AGENT" --region "$REGION" --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' --output text)

echo "✓ Alias IDs fetched:"
echo "  Scheduling: $SCHEDULING_AGENT / $SCHEDULING_ALIAS"
echo "  Information: $INFORMATION_AGENT / $INFORMATION_ALIAS"
echo "  Notes: $NOTES_AGENT / $NOTES_ALIAS"
echo "  Chitchat: $CHITCHAT_AGENT / $CHITCHAT_ALIAS"
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
  --agent-descriptor "aliasArn=arn:aws:bedrock:$REGION:$ACCOUNT_ID:agent-alias/$SCHEDULING_AGENT/$SCHEDULING_ALIAS" \
  --collaboration-instruction "This agent handles all appointment scheduling tasks including: listing available dates and time slots for projects, confirming and scheduling new appointments, rescheduling existing appointments, and canceling appointments. Route all scheduling-related requests to this agent." \
  --relay-conversation-history "TO_COLLABORATOR" \
  --region "$REGION" > /dev/null 2>&1 && echo "✓ Scheduling-Agent associated" || echo "  (May already exist)"

# Associate Information Agent
echo "📋 Associating Information-Agent..."
aws bedrock-agent associate-agent-collaborator \
  --agent-id "$SUPERVISOR_AGENT" \
  --agent-version "DRAFT" \
  --collaborator-name "Information-Agent" \
  --agent-descriptor "aliasArn=arn:aws:bedrock:$REGION:$ACCOUNT_ID:agent-alias/$INFORMATION_AGENT/$INFORMATION_ALIAS" \
  --collaboration-instruction "This agent provides information about projects, orders, and their status. It can retrieve project details, order information, installation addresses, project types, and current status. Route all information and status inquiry requests to this agent." \
  --relay-conversation-history "TO_COLLABORATOR" \
  --region "$REGION" > /dev/null 2>&1 && echo "✓ Information-Agent associated" || echo "  (May already exist)"

# Associate Notes Agent
echo "📋 Associating Notes-Agent..."
aws bedrock-agent associate-agent-collaborator \
  --agent-id "$SUPERVISOR_AGENT" \
  --agent-version "DRAFT" \
  --collaborator-name "Notes-Agent" \
  --agent-descriptor "aliasArn=arn:aws:bedrock:$REGION:$ACCOUNT_ID:agent-alias/$NOTES_AGENT/$NOTES_ALIAS" \
  --collaboration-instruction "This agent manages notes and communication related to projects. It can create, retrieve, update, and delete notes associated with projects and customers. Route all note-taking and note-retrieval requests to this agent." \
  --relay-conversation-history "TO_COLLABORATOR" \
  --region "$REGION" > /dev/null 2>&1 && echo "✓ Notes-Agent associated" || echo "  (May already exist)"

# Associate Chitchat Agent
echo "📋 Associating Chitchat-Agent..."
aws bedrock-agent associate-agent-collaborator \
  --agent-id "$SUPERVISOR_AGENT" \
  --agent-version "DRAFT" \
  --collaborator-name "Chitchat-Agent" \
  --agent-descriptor "aliasArn=arn:aws:bedrock:$REGION:$ACCOUNT_ID:agent-alias/$CHITCHAT_AGENT/$CHITCHAT_ALIAS" \
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
echo "Next: Test with 'python3 test_supervisor.py' or run agent tests"
echo ""
