#!/bin/bash

# Fix Bedrock Agent Model Configuration
# This script updates all agents to use the correct inference profile

echo "========================================="
echo "Fixing Bedrock Agent Model Configuration"
echo "========================================="
echo ""

# Correct inference profile for Claude 3.5 Sonnet v2
INFERENCE_PROFILE="us.anthropic.claude-3-5-sonnet-20241022-v2:0"

# Agent IDs
SCHEDULING_AGENT="ILSZT5EWND"
INFORMATION_AGENT="Z9OJEMMFND"
CHITCHAT_AGENT="NOLG2YV3HJ"
SUPERVISOR_AGENT="CJ0EHPZGBU"

echo "Using inference profile: $INFERENCE_PROFILE"
echo ""

# Function to update agent
update_agent() {
    local agent_id=$1
    local agent_name=$2

    echo "Updating $agent_name ($agent_id)..."

    aws bedrock-agent update-agent \
        --agent-id "$agent_id" \
        --agent-name "$agent_name" \
        --foundation-model "$INFERENCE_PROFILE" \
        --region us-east-1 \
        2>&1 | grep -i "agent\|error" || echo "  ✅ Updated"

    echo ""
}

# Update all agents
update_agent "$SCHEDULING_AGENT" "SchedulingAgent"
update_agent "$INFORMATION_AGENT" "pf-information"
update_agent "$CHITCHAT_AGENT" "pf-chitchat"
update_agent "$SUPERVISOR_AGENT" "Supervisor"

echo "========================================="
echo "Preparing agents..."
echo "========================================="
echo ""

# Prepare all agents
for agent in $SCHEDULING_AGENT $INFORMATION_AGENT $CHITCHAT_AGENT $SUPERVISOR_AGENT; do
    echo "Preparing agent $agent..."
    aws bedrock-agent prepare-agent \
        --agent-id "$agent" \
        --region us-east-1 \
        2>&1 > /dev/null && echo "  ✅ Prepared" || echo "  ❌ Failed"
    echo ""
done

echo "========================================="
echo "Done!"
echo "========================================="
echo ""
echo "Please wait 30-60 seconds for changes to propagate, then try again."
echo ""
