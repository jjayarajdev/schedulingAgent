#!/bin/bash

###############################################################################
# Associate Collaborators Script
# Run this AFTER creating v1 aliases in AWS Console
###############################################################################

set -e

REGION="us-east-1"
ACCOUNT_ID="618048437522"

# Current agent IDs
SUPERVISOR_AGENT_ID="ZZNSFE74NB"
SCHEDULING_AGENT_ID="XWYHPGTXFC"
INFORMATION_AGENT_ID="YPHTBWTHU8"
CHITCHAT_AGENT_ID="2VRYB01FGD"

echo "═══════════════════════════════════════════════════════════════"
echo "Associate Collaborators with Supervisor Agent"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Get v1 alias IDs
echo "Fetching v1 alias IDs..."
SCHEDULING_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "$SCHEDULING_AGENT_ID" --region "$REGION" --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' --output text)
INFORMATION_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "$INFORMATION_AGENT_ID" --region "$REGION" --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' --output text)
CHITCHAT_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "$CHITCHAT_AGENT_ID" --region "$REGION" --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' --output text)

if [ -z "$SCHEDULING_ALIAS" ] || [ -z "$INFORMATION_ALIAS" ] || [ -z "$CHITCHAT_ALIAS" ]; then
    echo "❌ Error: v1 aliases not found!"
    echo ""
    echo "Please create v1 aliases in AWS Bedrock Console first:"
    echo "  1. Go to AWS Bedrock Console → Agents"
    echo "  2. For each agent (Scheduling, Information, Chitchat):"
    echo "     - Click on the agent"
    echo "     - Click 'Create version' → Version 1"
    echo "     - Click 'Create alias' → Name: v1, Version: 1"
    echo ""
    exit 1
fi

echo "✅ Found v1 aliases:"
echo "  Scheduling:  $SCHEDULING_ALIAS"
echo "  Information: $INFORMATION_ALIAS"
echo "  Chitchat:    $CHITCHAT_ALIAS"
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "Associating Collaborators..."
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Associate Scheduling Agent
echo "📋 Associating SchedulingAgent..."
aws bedrock-agent associate-agent-collaborator \
  --agent-id "$SUPERVISOR_AGENT_ID" \
  --agent-version "DRAFT" \
  --collaborator-name "SchedulingAgent" \
  --agent-descriptor "aliasArn=arn:aws:bedrock:$REGION:$ACCOUNT_ID:agent-alias/$SCHEDULING_AGENT_ID/$SCHEDULING_ALIAS" \
  --collaboration-instruction "Route queries about projects, appointments, scheduling, availability, and booking to this agent. Examples: 'List my projects', 'Book an appointment', 'What dates are available?'" \
  --relay-conversation-history "TO_COLLABORATOR" \
  --region "$REGION" && echo "✅ SchedulingAgent associated" || echo "⚠️  May already exist"

echo ""

# Associate Information Agent
echo "📋 Associating InformationAgent..."
aws bedrock-agent associate-agent-collaborator \
  --agent-id "$SUPERVISOR_AGENT_ID" \
  --agent-version "DRAFT" \
  --collaborator-name "InformationAgent" \
  --agent-descriptor "aliasArn=arn:aws:bedrock:$REGION:$ACCOUNT_ID:agent-alias/$INFORMATION_AGENT_ID/$INFORMATION_ALIAS" \
  --collaboration-instruction "Route queries about weather, project details, appointment status, and general information lookup to this agent. Examples: 'What's the weather in New York?', 'Get project details', 'Check appointment status'." \
  --relay-conversation-history "TO_COLLABORATOR" \
  --region "$REGION" && echo "✅ InformationAgent associated" || echo "⚠️  May already exist"

echo ""

# Associate Chitchat Agent
echo "📋 Associating ChitchatAgent..."
aws bedrock-agent associate-agent-collaborator \
  --agent-id "$SUPERVISOR_AGENT_ID" \
  --agent-version "DRAFT" \
  --collaborator-name "ChitchatAgent" \
  --agent-descriptor "aliasArn=arn:aws:bedrock:$REGION:$ACCOUNT_ID:agent-alias/$CHITCHAT_AGENT_ID/$CHITCHAT_ALIAS" \
  --collaboration-instruction "Route greetings, casual conversation, thank you messages, and general pleasantries to this agent. Examples: 'Hello', 'Hi there', 'Thank you', 'Good morning'." \
  --relay-conversation-history "TO_COLLABORATOR" \
  --region "$REGION" && echo "✅ ChitchatAgent associated" || echo "⚠️  May already exist"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Preparing Supervisor Agent..."
echo "═══════════════════════════════════════════════════════════════"
echo ""

aws bedrock-agent prepare-agent \
  --agent-id "$SUPERVISOR_AGENT_ID" \
  --region "$REGION"

echo ""
echo "✅ Supervisor Agent prepared with collaborators!"
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "Verification"
echo "═══════════════════════════════════════════════════════════════"
echo ""

aws bedrock-agent list-agent-collaborators \
  --agent-id "$SUPERVISOR_AGENT_ID" \
  --agent-version DRAFT \
  --region "$REGION" \
  --query 'agentCollaboratorSummaries[*].[collaboratorName,agentDescriptor.aliasArn]' \
  --output table

echo ""
echo "✅ Collaboration configured successfully!"
echo ""
echo "Test with:"
echo "  aws bedrock-agent-runtime invoke-agent \\"
echo "    --agent-id $SUPERVISOR_AGENT_ID \\"
echo "    --agent-alias-id TSTALIASID \\"
echo "    --session-id test-\$(date +%s) \\"
echo "    --input-text 'List my projects' output.txt"
echo ""
