#!/bin/bash

# Quick script to update foundation model for existing agents
# IMPORTANT: This script preserves agent instructions when updating the model

REGION="us-east-1"
MODEL="us.anthropic.claude-3-7-sonnet-20250219-v1:0"  # Claude 3.7 Sonnet inference profile
INSTRUCTIONS_DIR="../infrastructure/agent_instructions"

echo "========================================="
echo "Updating Agents to Claude 3.7 Sonnet"
echo "========================================="
echo "Model: $MODEL"
echo ""

# Get agent IDs
SCHEDULING_ID=$(aws bedrock-agent list-agents --region $REGION --query 'agentSummaries[?agentName==`SchedulingAgent`].agentId' --output text)
INFORMATION_ID=$(aws bedrock-agent list-agents --region $REGION --query 'agentSummaries[?agentName==`pf-information`].agentId' --output text)
CHITCHAT_ID=$(aws bedrock-agent list-agents --region $REGION --query 'agentSummaries[?agentName==`pf-chitchat`].agentId' --output text)
SUPERVISOR_ID=$(aws bedrock-agent list-agents --region $REGION --query 'agentSummaries[?agentName==`Supervisor`].agentId' --output text)

echo "Found agents:"
echo "  Scheduling: $SCHEDULING_ID"
echo "  Information: $INFORMATION_ID"
echo "  Chitchat: $CHITCHAT_ID"
echo "  Supervisor: $SUPERVISOR_ID"
echo ""

# Function to update agent WITH instructions
update_agent() {
    local agent_id=$1
    local agent_name=$2
    local instruction_file=$3

    echo "Updating $agent_name..."

    # Get current agent config
    local role_arn=$(aws bedrock-agent get-agent --agent-id $agent_id --region $REGION --query 'agent.agentResourceRoleArn' --output text)

    # Path to instruction file
    local instruction_path="$INSTRUCTIONS_DIR/$instruction_file"

    if [ ! -f "$instruction_path" ]; then
        echo "  ❌ Instruction file not found: $instruction_path"
        return 1
    fi

    echo "  Using instruction: $instruction_file"

    # Update agent with new foundation model AND instructions
    aws bedrock-agent update-agent \
        --agent-id "$agent_id" \
        --agent-name "$agent_name" \
        --foundation-model "$MODEL" \
        --agent-resource-role-arn "$role_arn" \
        --instruction "file://$instruction_path" \
        --region $REGION \
        > /dev/null 2>&1 && echo "  ✅ Updated" || echo "  ❌ Failed"

    # Prepare agent
    echo "  Preparing..."
    aws bedrock-agent prepare-agent \
        --agent-id "$agent_id" \
        --region $REGION \
        > /dev/null 2>&1 && echo "  ✅ Prepared" || echo "  ❌ Failed to prepare"

    echo ""
}

# Update all agents WITH their instructions
update_agent "$SCHEDULING_ID" "SchedulingAgent" "scheduling_collaborator.txt"
update_agent "$INFORMATION_ID" "pf-information" "information_collaborator.txt"
update_agent "$CHITCHAT_ID" "pf-chitchat" "chitchat_collaborator.txt"
update_agent "$SUPERVISOR_ID" "Supervisor" "supervisor.txt"

echo "========================================="
echo "Done! Agents updated with new model."
echo "========================================="
echo ""
echo "Wait 30 seconds for changes to propagate, then test again."
