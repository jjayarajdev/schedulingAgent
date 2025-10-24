#!/bin/bash

echo "================================================================================"
echo "AWS Bedrock Action Groups Configuration Script"
echo "================================================================================"
echo "Date: $(date)"
echo "Region: us-east-1"
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
ACCOUNT_ID="618048437522"

# Agent IDs
SCHEDULING_AGENT_ID="IX24FSMTQH"
INFORMATION_AGENT_ID="C9ANXRIO8Y"
NOTES_AGENT_ID="G5BVBYEPUM"

# Lambda ARNs
SCHEDULING_LAMBDA_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:scheduling-agent-scheduling-actions"
INFORMATION_LAMBDA_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:scheduling-agent-information-actions"
NOTES_LAMBDA_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:scheduling-agent-notes-actions"

# Schema files
SCHEDULING_SCHEMA="../lambda/schemas/scheduling-actions-schema.json"
INFORMATION_SCHEMA="../lambda/schemas/information-actions-schema.json"
NOTES_SCHEMA="../lambda/schemas/notes-actions-schema.json"

echo "================================================================================"
echo "Step 1: Checking Current Action Groups"
echo "================================================================================"
echo ""

echo -e "${BLUE}Checking Scheduling Agent (IX24FSMTQH)...${NC}"
aws bedrock-agent list-agent-action-groups \
  --agent-id ${SCHEDULING_AGENT_ID} \
  --agent-version DRAFT \
  --region ${REGION} \
  --query 'actionGroupSummaries[*].{Name:actionGroupName,State:actionGroupState}' \
  --output table

echo ""
echo -e "${BLUE}Checking Information Agent (C9ANXRIO8Y)...${NC}"
aws bedrock-agent list-agent-action-groups \
  --agent-id ${INFORMATION_AGENT_ID} \
  --agent-version DRAFT \
  --region ${REGION} \
  --query 'actionGroupSummaries[*].{Name:actionGroupName,State:actionGroupState}' \
  --output table

echo ""
echo -e "${BLUE}Checking Notes Agent (G5BVBYEPUM)...${NC}"
aws bedrock-agent list-agent-action-groups \
  --agent-id ${NOTES_AGENT_ID} \
  --agent-version DRAFT \
  --region ${REGION} \
  --query 'actionGroupSummaries[*].{Name:actionGroupName,State:actionGroupState}' \
  --output table

echo ""
echo "================================================================================"
echo "Step 2: Creating Action Groups"
echo "================================================================================"
echo ""

# Function to create action group
create_action_group() {
    local agent_id=$1
    local agent_name=$2
    local action_group_name=$3
    local lambda_arn=$4
    local schema_file=$5
    local description=$6

    echo -e "${YELLOW}Creating action group '${action_group_name}' for ${agent_name}...${NC}"

    # Check if schema file exists
    if [ ! -f "$schema_file" ]; then
        echo -e "${RED}❌ Error: Schema file not found: ${schema_file}${NC}"
        return 1
    fi

    # Read and minify schema
    SCHEMA_PAYLOAD=$(cat "$schema_file" | jq -c .)

    # Create action group
    aws bedrock-agent create-agent-action-group \
      --agent-id ${agent_id} \
      --agent-version DRAFT \
      --action-group-name ${action_group_name} \
      --description "${description}" \
      --action-group-executor lambda="${lambda_arn}" \
      --api-schema payload="${SCHEMA_PAYLOAD}" \
      --region ${REGION} \
      --output json > /tmp/action_group_output.json

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Action group '${action_group_name}' created successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to create action group '${action_group_name}'${NC}"
        cat /tmp/action_group_output.json
        return 1
    fi
}

# Check if action groups already exist and delete if needed
check_and_delete_if_exists() {
    local agent_id=$1
    local action_group_name=$2

    echo -e "${BLUE}Checking if '${action_group_name}' already exists...${NC}"

    EXISTING=$(aws bedrock-agent list-agent-action-groups \
      --agent-id ${agent_id} \
      --agent-version DRAFT \
      --region ${REGION} \
      --query "actionGroupSummaries[?actionGroupName=='${action_group_name}'].actionGroupId" \
      --output text)

    if [ ! -z "$EXISTING" ]; then
        echo -e "${YELLOW}Action group '${action_group_name}' already exists (ID: ${EXISTING})${NC}"
        echo -e "${YELLOW}Deleting existing action group...${NC}"

        aws bedrock-agent delete-agent-action-group \
          --agent-id ${agent_id} \
          --agent-version DRAFT \
          --action-group-id ${EXISTING} \
          --region ${REGION}

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Deleted existing action group${NC}"
            sleep 2
        else
            echo -e "${RED}❌ Failed to delete existing action group${NC}"
            return 1
        fi
    fi
}

# Configure Scheduling Agent
echo ""
echo "───────────────────────────────────────────────────────────────────────────────"
echo "Configuring Scheduling Agent Action Group"
echo "───────────────────────────────────────────────────────────────────────────────"
check_and_delete_if_exists ${SCHEDULING_AGENT_ID} "scheduling_actions"
create_action_group \
    ${SCHEDULING_AGENT_ID} \
    "Scheduling Agent" \
    "scheduling_actions" \
    ${SCHEDULING_LAMBDA_ARN} \
    ${SCHEDULING_SCHEMA} \
    "Scheduling operations including list projects, check availability, confirm/reschedule/cancel appointments"

# Configure Information Agent
echo ""
echo "───────────────────────────────────────────────────────────────────────────────"
echo "Configuring Information Agent Action Group"
echo "───────────────────────────────────────────────────────────────────────────────"
check_and_delete_if_exists ${INFORMATION_AGENT_ID} "information_actions"
create_action_group \
    ${INFORMATION_AGENT_ID} \
    "Information Agent" \
    "information_actions" \
    ${INFORMATION_LAMBDA_ARN} \
    ${INFORMATION_SCHEMA} \
    "Information operations including project details, appointment status, working hours, weather"

# Configure Notes Agent (optional - may already exist)
echo ""
echo "───────────────────────────────────────────────────────────────────────────────"
echo "Configuring Notes Agent Action Group (if not exists)"
echo "───────────────────────────────────────────────────────────────────────────────"

NOTES_EXISTS=$(aws bedrock-agent list-agent-action-groups \
  --agent-id ${NOTES_AGENT_ID} \
  --agent-version DRAFT \
  --region ${REGION} \
  --query "actionGroupSummaries[?actionGroupName=='notes_actions'].actionGroupId" \
  --output text)

if [ -z "$NOTES_EXISTS" ]; then
    echo -e "${YELLOW}Notes action group does not exist, creating...${NC}"
    create_action_group \
        ${NOTES_AGENT_ID} \
        "Notes Agent" \
        "notes_actions" \
        ${NOTES_LAMBDA_ARN} \
        ${NOTES_SCHEMA} \
        "Notes operations including add note and list notes"
else
    echo -e "${GREEN}✅ Notes action group already exists, skipping${NC}"
fi

echo ""
echo "================================================================================"
echo "Step 3: Preparing Agents"
echo "================================================================================"
echo ""

prepare_agent() {
    local agent_id=$1
    local agent_name=$2

    echo -e "${BLUE}Preparing ${agent_name} (${agent_id})...${NC}"

    aws bedrock-agent prepare-agent \
      --agent-id ${agent_id} \
      --region ${REGION} \
      --output json > /tmp/prepare_output.json

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ ${agent_name} is being prepared${NC}"

        # Wait for agent to be prepared
        echo -e "${YELLOW}Waiting for agent to be prepared (30 seconds)...${NC}"
        sleep 30

        # Check status
        STATUS=$(aws bedrock-agent get-agent \
          --agent-id ${agent_id} \
          --region ${REGION} \
          --query 'agent.agentStatus' \
          --output text)

        echo -e "${BLUE}Status: ${STATUS}${NC}"

        if [ "$STATUS" == "PREPARED" ]; then
            echo -e "${GREEN}✅ ${agent_name} is ready!${NC}"
        else
            echo -e "${YELLOW}⚠️  ${agent_name} is still preparing (${STATUS})${NC}"
            echo -e "${YELLOW}Wait another 30 seconds and check status again${NC}"
        fi
    else
        echo -e "${RED}❌ Failed to prepare ${agent_name}${NC}"
        cat /tmp/prepare_output.json
    fi
    echo ""
}

prepare_agent ${SCHEDULING_AGENT_ID} "Scheduling Agent"
prepare_agent ${INFORMATION_AGENT_ID} "Information Agent"
prepare_agent ${NOTES_AGENT_ID} "Notes Agent"

echo ""
echo "================================================================================"
echo "Step 4: Verifying Configuration"
echo "================================================================================"
echo ""

echo -e "${BLUE}Final Status Check:${NC}"
echo ""

echo "Scheduling Agent Action Groups:"
aws bedrock-agent list-agent-action-groups \
  --agent-id ${SCHEDULING_AGENT_ID} \
  --agent-version DRAFT \
  --region ${REGION} \
  --query 'actionGroupSummaries[*].{Name:actionGroupName,State:actionGroupState}' \
  --output table

echo ""
echo "Information Agent Action Groups:"
aws bedrock-agent list-agent-action-groups \
  --agent-id ${INFORMATION_AGENT_ID} \
  --agent-version DRAFT \
  --region ${REGION} \
  --query 'actionGroupSummaries[*].{Name:actionGroupName,State:actionGroupState}' \
  --output table

echo ""
echo "Notes Agent Action Groups:"
aws bedrock-agent list-agent-action-groups \
  --agent-id ${NOTES_AGENT_ID} \
  --agent-version DRAFT \
  --region ${REGION} \
  --query 'actionGroupSummaries[*].{Name:actionGroupName,State:actionGroupState}' \
  --output table

echo ""
echo "================================================================================"
echo "Configuration Complete!"
echo "================================================================================"
echo ""
echo -e "${GREEN}✅ All action groups have been configured${NC}"
echo ""
echo "Next Steps:"
echo "1. Wait 1-2 minutes for all agents to be fully prepared"
echo "2. Test in Bedrock Console:"
echo "   - Scheduling Agent: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/IX24FSMTQH"
echo "   - Information Agent: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/C9ANXRIO8Y"
echo ""
echo "3. Test query: 'Show me all projects for customer CUST001'"
echo "   Expected: Returns 3 real mock projects (12345, 12347, 12350)"
echo "   NOT: Hallucinated data like 'Website Redesign'"
echo ""
echo "4. If agents still hallucinate, check CloudWatch logs:"
echo "   aws logs tail /aws/lambda/scheduling-agent-scheduling-actions --follow --region us-east-1"
echo ""
echo "================================================================================"

# Cleanup
rm -f /tmp/action_group_output.json /tmp/prepare_output.json
