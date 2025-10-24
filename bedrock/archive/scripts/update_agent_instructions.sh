#!/bin/bash

echo "================================================================================"
echo "AWS Bedrock Agent Instructions Update Script"
echo "================================================================================"
echo "Date: $(date)"
echo "Region: us-east-1"
echo "Purpose: Add AVAILABLE ACTIONS sections to fix hallucination issue"
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
SCHEDULING_AGENT_ID="IX24FSMTQH"
INFORMATION_AGENT_ID="C9ANXRIO8Y"
NOTES_AGENT_ID="G5BVBYEPUM"

# Instruction files (relative to script location)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTRUCTIONS_DIR="${SCRIPT_DIR}/../agent-instructions"

SCHEDULING_INSTRUCTIONS="${INSTRUCTIONS_DIR}/scheduling-agent-instructions.txt"
INFORMATION_INSTRUCTIONS="${INSTRUCTIONS_DIR}/information-agent-instructions.txt"
NOTES_INSTRUCTIONS="${INSTRUCTIONS_DIR}/notes-agent-instructions.txt"

echo "================================================================================"
echo "Step 1: Verifying Instruction Files"
echo "================================================================================"
echo ""

# Function to check if file exists
check_file() {
    local file=$1
    local name=$2

    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ Error: $name not found at: $file${NC}"
        return 1
    else
        echo -e "${GREEN}✅ Found: $name${NC}"
        echo "   Path: $file"
        echo "   Size: $(wc -c < "$file") bytes"
        echo "   Lines: $(wc -l < "$file") lines"
        return 0
    fi
}

check_file "$SCHEDULING_INSTRUCTIONS" "Scheduling Agent Instructions"
SCHEDULING_OK=$?

check_file "$INFORMATION_INSTRUCTIONS" "Information Agent Instructions"
INFORMATION_OK=$?

check_file "$NOTES_INSTRUCTIONS" "Notes Agent Instructions"
NOTES_OK=$?

echo ""

if [ $SCHEDULING_OK -ne 0 ] || [ $INFORMATION_OK -ne 0 ] || [ $NOTES_OK -ne 0 ]; then
    echo -e "${RED}❌ Missing instruction files. Cannot proceed.${NC}"
    echo ""
    echo "Expected files:"
    echo "  - $SCHEDULING_INSTRUCTIONS"
    echo "  - $INFORMATION_INSTRUCTIONS"
    echo "  - $NOTES_INSTRUCTIONS"
    exit 1
fi

echo "================================================================================"
echo "Step 2: Backing Up Current Instructions"
echo "================================================================================"
echo ""

BACKUP_DIR="${SCRIPT_DIR}/../agent-instructions/backups"
BACKUP_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_SUBDIR="${BACKUP_DIR}/${BACKUP_TIMESTAMP}"

mkdir -p "$BACKUP_SUBDIR"

echo -e "${BLUE}Creating backups in: $BACKUP_SUBDIR${NC}"
echo ""

# Function to backup current instructions
backup_agent() {
    local agent_id=$1
    local agent_name=$2
    local backup_file="${BACKUP_SUBDIR}/${agent_name}-instructions-backup.txt"

    echo -e "${YELLOW}Backing up $agent_name instructions...${NC}"

    aws bedrock-agent get-agent \
      --agent-id ${agent_id} \
      --region ${REGION} \
      --query 'agent.instruction' \
      --output text > "$backup_file"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Backup saved: $backup_file${NC}"
        echo "   Size: $(wc -c < "$backup_file") bytes"
        return 0
    else
        echo -e "${RED}❌ Failed to backup $agent_name${NC}"
        return 1
    fi
}

backup_agent ${SCHEDULING_AGENT_ID} "scheduling-agent"
backup_agent ${INFORMATION_AGENT_ID} "information-agent"
backup_agent ${NOTES_AGENT_ID} "notes-agent"

echo ""
echo -e "${GREEN}✅ All backups created successfully${NC}"
echo ""

echo "================================================================================"
echo "Step 3: Updating Agent Instructions"
echo "================================================================================"
echo ""

# Function to update agent instructions
update_agent() {
    local agent_id=$1
    local agent_name=$2
    local instructions_file=$3

    echo "───────────────────────────────────────────────────────────────────────────────"
    echo -e "${YELLOW}Updating $agent_name (${agent_id})...${NC}"
    echo "───────────────────────────────────────────────────────────────────────────────"
    echo ""

    # Read instructions from file
    INSTRUCTIONS=$(cat "$instructions_file")

    # Get current agent details
    echo -e "${BLUE}Fetching current agent configuration...${NC}"
    AGENT_JSON=$(aws bedrock-agent get-agent \
      --agent-id ${agent_id} \
      --region ${REGION} \
      --output json)

    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to fetch agent details${NC}"
        return 1
    fi

    # Extract current values
    AGENT_NAME=$(echo "$AGENT_JSON" | jq -r '.agent.agentName')
    FOUNDATION_MODEL=$(echo "$AGENT_JSON" | jq -r '.agent.foundationModel')
    ROLE_ARN=$(echo "$AGENT_JSON" | jq -r '.agent.agentResourceRoleArn')

    echo "   Agent Name: $AGENT_NAME"
    echo "   Foundation Model: $FOUNDATION_MODEL"
    echo "   Role ARN: $ROLE_ARN"
    echo ""

    # Update agent with new instructions
    echo -e "${BLUE}Updating agent instructions...${NC}"

    aws bedrock-agent update-agent \
      --agent-id ${agent_id} \
      --agent-name "${AGENT_NAME}" \
      --foundation-model "${FOUNDATION_MODEL}" \
      --instruction "${INSTRUCTIONS}" \
      --agent-resource-role-arn "${ROLE_ARN}" \
      --region ${REGION} \
      --output json > /tmp/update_agent_output_${agent_id}.json

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Instructions updated successfully${NC}"

        # Show update timestamp
        UPDATED_AT=$(cat /tmp/update_agent_output_${agent_id}.json | jq -r '.agent.updatedAt')
        echo "   Updated at: $UPDATED_AT"
        echo ""
        return 0
    else
        echo -e "${RED}❌ Failed to update instructions${NC}"
        cat /tmp/update_agent_output_${agent_id}.json
        echo ""
        return 1
    fi
}

# Update all three agents
update_agent ${SCHEDULING_AGENT_ID} "Scheduling Agent" "$SCHEDULING_INSTRUCTIONS"
SCHEDULING_UPDATE=$?

update_agent ${INFORMATION_AGENT_ID} "Information Agent" "$INFORMATION_INSTRUCTIONS"
INFORMATION_UPDATE=$?

update_agent ${NOTES_AGENT_ID} "Notes Agent" "$NOTES_INSTRUCTIONS"
NOTES_UPDATE=$?

echo ""

if [ $SCHEDULING_UPDATE -ne 0 ] || [ $INFORMATION_UPDATE -ne 0 ] || [ $NOTES_UPDATE -ne 0 ]; then
    echo -e "${RED}❌ Some agents failed to update${NC}"
    echo ""
    echo "You can restore from backups at: $BACKUP_SUBDIR"
    exit 1
fi

echo "================================================================================"
echo "Step 4: Preparing Agents"
echo "================================================================================"
echo ""

# Function to prepare agent
prepare_agent() {
    local agent_id=$1
    local agent_name=$2

    echo "───────────────────────────────────────────────────────────────────────────────"
    echo -e "${YELLOW}Preparing $agent_name (${agent_id})...${NC}"
    echo "───────────────────────────────────────────────────────────────────────────────"
    echo ""

    aws bedrock-agent prepare-agent \
      --agent-id ${agent_id} \
      --region ${REGION} \
      --output json > /tmp/prepare_output_${agent_id}.json

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $agent_name is being prepared${NC}"

        # Wait for agent to be prepared
        echo -e "${YELLOW}Waiting for agent to be prepared (30 seconds)...${NC}"
        sleep 30

        # Check status
        STATUS=$(aws bedrock-agent get-agent \
          --agent-id ${agent_id} \
          --region ${REGION} \
          --query 'agent.agentStatus' \
          --output text)

        PREPARED_AT=$(aws bedrock-agent get-agent \
          --agent-id ${agent_id} \
          --region ${REGION} \
          --query 'agent.preparedAt' \
          --output text)

        echo "   Status: ${STATUS}"
        echo "   Prepared at: ${PREPARED_AT}"
        echo ""

        if [ "$STATUS" == "PREPARED" ]; then
            echo -e "${GREEN}✅ $agent_name is ready!${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  $agent_name is still preparing (${STATUS})${NC}"
            echo -e "${YELLOW}Wait another 30 seconds and check status again${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ Failed to prepare $agent_name${NC}"
        cat /tmp/prepare_output_${agent_id}.json
        return 1
    fi
    echo ""
}

# Prepare all three agents
prepare_agent ${SCHEDULING_AGENT_ID} "Scheduling Agent"
prepare_agent ${INFORMATION_AGENT_ID} "Information Agent"
prepare_agent ${NOTES_AGENT_ID} "Notes Agent"

echo ""
echo "================================================================================"
echo "Step 5: Verification"
echo "================================================================================"
echo ""

echo -e "${BLUE}Final Status Check:${NC}"
echo ""

# Function to verify agent
verify_agent() {
    local agent_id=$1
    local agent_name=$2

    echo "───────────────────────────────────────────────────────────────────────────────"
    echo "$agent_name:"

    STATUS=$(aws bedrock-agent get-agent \
      --agent-id ${agent_id} \
      --region ${REGION} \
      --query 'agent.agentStatus' \
      --output text)

    UPDATED_AT=$(aws bedrock-agent get-agent \
      --agent-id ${agent_id} \
      --region ${REGION} \
      --query 'agent.updatedAt' \
      --output text)

    PREPARED_AT=$(aws bedrock-agent get-agent \
      --agent-id ${agent_id} \
      --region ${REGION} \
      --query 'agent.preparedAt' \
      --output text)

    echo "   Status: $STATUS"
    echo "   Updated: $UPDATED_AT"
    echo "   Prepared: $PREPARED_AT"

    # Check if instructions contain "AVAILABLE ACTIONS"
    INSTRUCTIONS=$(aws bedrock-agent get-agent \
      --agent-id ${agent_id} \
      --region ${REGION} \
      --query 'agent.instruction' \
      --output text)

    if echo "$INSTRUCTIONS" | grep -q "AVAILABLE ACTIONS"; then
        echo -e "   ${GREEN}✅ AVAILABLE ACTIONS section found${NC}"
    else
        echo -e "   ${RED}❌ AVAILABLE ACTIONS section NOT found${NC}"
    fi

    echo ""
}

verify_agent ${SCHEDULING_AGENT_ID} "Scheduling Agent"
verify_agent ${INFORMATION_AGENT_ID} "Information Agent"
verify_agent ${NOTES_AGENT_ID} "Notes Agent"

echo "================================================================================"
echo "Update Complete!"
echo "================================================================================"
echo ""
echo -e "${GREEN}✅ All agents updated with AVAILABLE ACTIONS sections${NC}"
echo ""
echo "Backups saved to:"
echo "  $BACKUP_SUBDIR"
echo ""
echo "Next Steps:"
echo "1. Test agents with proper session context (see TESTING_COMPLETE_WORKFLOWS.md)"
echo "2. Monitor CloudWatch logs for Lambda invocations:"
echo "   aws logs tail /aws/lambda/scheduling-agent-scheduling-actions --follow --region us-east-1"
echo "3. Verify agents return real mock data (12345, 12347, 12350)"
echo "4. Confirm NO hallucinated data (Kitchen Remodel, Bathroom Renovation, etc.)"
echo ""
echo "If agents still hallucinate, check:"
echo "- Session attributes are provided in test requests"
echo "- CloudWatch logs show Lambda invocations"
echo "- Action groups are ENABLED (run configure_action_groups.sh if needed)"
echo ""
echo "================================================================================"

# Cleanup temp files
rm -f /tmp/update_agent_output_*.json
rm -f /tmp/prepare_output_*.json
