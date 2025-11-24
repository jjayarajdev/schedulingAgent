#!/bin/bash

##############################################################################
# update_agent_instructions.sh
#
# Purpose: Update Bedrock agent instructions from instruction files
#
# This script:
#   1. Reads instruction files from infrastructure/agent_instructions/
#   2. Updates each agent with the proper instructions
#   3. Prepares agents after updating
#
# Usage: ./update_agent_instructions.sh
##############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BEDROCK_DIR="$(dirname "$SCRIPT_DIR")"
INSTRUCTIONS_DIR="$BEDROCK_DIR/infrastructure/agent_instructions"
REGION="us-east-1"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "Update Bedrock Agent Instructions"
echo "=========================================="
echo ""

##############################################################################
# Function: Update agent instructions
##############################################################################

update_agent_instruction() {
    local AGENT_NAME=$1
    local INSTRUCTION_FILE=$2

    echo -e "${BLUE}Updating: $AGENT_NAME${NC}"
    echo "  Instruction file: $INSTRUCTION_FILE"

    # Check if instruction file exists
    if [[ ! -f "$INSTRUCTION_FILE" ]]; then
        echo -e "${RED}  ✗ Instruction file not found: $INSTRUCTION_FILE${NC}"
        return 1
    fi

    # Get agent ID and details
    AGENT_INFO=$(aws bedrock-agent list-agents \
        --region "$REGION" \
        --query "agentSummaries[?agentName=='$AGENT_NAME'] | [0].{id:agentId,status:agentStatus}" \
        --output json 2>/dev/null)

    if [[ -z "$AGENT_INFO" ]] || [[ "$AGENT_INFO" == "null" ]]; then
        echo -e "${YELLOW}  ⚠️  Agent not found: $AGENT_NAME${NC}"
        return 1
    fi

    AGENT_ID=$(echo "$AGENT_INFO" | jq -r '.id')
    AGENT_STATUS=$(echo "$AGENT_INFO" | jq -r '.status')

    echo "  Agent ID: $AGENT_ID"
    echo "  Current Status: $AGENT_STATUS"

    # Get current agent configuration
    AGENT_CONFIG=$(aws bedrock-agent get-agent \
        --agent-id "$AGENT_ID" \
        --region "$REGION" \
        --output json 2>/dev/null)

    FOUNDATION_MODEL=$(echo "$AGENT_CONFIG" | jq -r '.agent.foundationModel')
    ROLE_ARN=$(echo "$AGENT_CONFIG" | jq -r '.agent.agentResourceRoleArn')
    COLLABORATION=$(echo "$AGENT_CONFIG" | jq -r '.agent.agentCollaboration')

    echo "  Foundation Model: $FOUNDATION_MODEL"

    # Read instruction file content
    INSTRUCTION_TEXT=$(cat "$INSTRUCTION_FILE")

    # Update agent with new instructions
    echo "  → Updating agent instructions..."

    # Check if agent has collaboration mode (Supervisor)
    if [[ "$COLLABORATION" != "null" && "$COLLABORATION" != "DISABLED" ]]; then
        echo "  → Agent has collaboration mode: $COLLABORATION"
        aws bedrock-agent update-agent \
            --agent-id "$AGENT_ID" \
            --agent-name "$AGENT_NAME" \
            --foundation-model "$FOUNDATION_MODEL" \
            --agent-resource-role-arn "$ROLE_ARN" \
            --agent-collaboration "$COLLABORATION" \
            --instruction "$INSTRUCTION_TEXT" \
            --region "$REGION" \
            --output json > /dev/null 2>&1
    else
        aws bedrock-agent update-agent \
            --agent-id "$AGENT_ID" \
            --agent-name "$AGENT_NAME" \
            --foundation-model "$FOUNDATION_MODEL" \
            --agent-resource-role-arn "$ROLE_ARN" \
            --instruction "$INSTRUCTION_TEXT" \
            --region "$REGION" \
            --output json > /dev/null 2>&1
    fi

    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}  ✓ Instructions updated${NC}"

        # Prepare agent
        echo "  → Preparing agent..."
        aws bedrock-agent prepare-agent \
            --agent-id "$AGENT_ID" \
            --region "$REGION" \
            --output json > /dev/null 2>&1

        if [[ $? -eq 0 ]]; then
            echo -e "${GREEN}  ✓ Agent prepared${NC}"
        else
            echo -e "${YELLOW}  ⚠️  Failed to prepare agent${NC}"
        fi
    else
        echo -e "${RED}  ✗ Failed to update instructions${NC}"
        return 1
    fi

    echo ""
}

##############################################################################
# Update all agents
##############################################################################

echo "Updating agent instructions from files..."
echo ""

# Update SchedulingAgent
update_agent_instruction \
    "SchedulingAgent" \
    "$INSTRUCTIONS_DIR/scheduling_collaborator.txt"

# Update pf-information
update_agent_instruction \
    "pf-information" \
    "$INSTRUCTIONS_DIR/information_collaborator.txt"

# Update pf-chitchat
update_agent_instruction \
    "pf-chitchat" \
    "$INSTRUCTIONS_DIR/chitchat_collaborator.txt"

# Update Supervisor
update_agent_instruction \
    "Supervisor" \
    "$INSTRUCTIONS_DIR/supervisor.txt"

##############################################################################
# Summary
##############################################################################

echo "=========================================="
echo -e "${GREEN}✓ Agent Instructions Updated${NC}"
echo "=========================================="
echo ""
echo "All agents have been updated with the latest instructions from:"
echo "  $INSTRUCTIONS_DIR"
echo ""
echo "Next steps:"
echo "  • Test the agents in AWS Console or via UI"
echo "  • Verify JSON formatting works correctly"
echo ""
