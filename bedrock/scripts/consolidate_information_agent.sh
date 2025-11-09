#!/bin/bash

################################################################################
# CONSOLIDATE INFORMATION AGENT - Keep Weather Only
################################################################################
# This script deploys the updated information agent that ONLY handles weather.
# All project-related actions have been moved to scheduling agent.
#
# Changes:
# - information-actions handler: Removed 4 actions, kept only get_weather
# - information_actions.json schema: Updated to show only weather action
# - information agent instructions: Updated to focus on weather only
# - information mock_data.py: Removed project-related mock functions
#
# Usage:
#   ./consolidate_information_agent.sh
#
# Prerequisites:
#   - AWS CLI configured with appropriate credentials
#   - Agent IDs in config/agent_ids.json
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}  CONSOLIDATE INFORMATION AGENT - Weather Only${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

################################################################################
# Step 1: Verify Prerequisites
################################################################################

echo -e "${YELLOW}[1/6] Verifying prerequisites...${NC}"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install it first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ AWS CLI found${NC}"

# Check jq
if ! command -v jq &> /dev/null; then
    echo -e "${RED}❌ jq not found. Please install it first (brew install jq).${NC}"
    exit 1
fi
echo -e "${GREEN}✓ jq found${NC}"

# Check agent IDs file
AGENT_IDS_FILE="$PROJECT_ROOT/config/agent_ids.json"
if [ ! -f "$AGENT_IDS_FILE" ]; then
    echo -e "${RED}❌ Agent IDs file not found: $AGENT_IDS_FILE${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Agent IDs file found${NC}"

# Get agent IDs
INFORMATION_AGENT_ID=$(jq -r '.agents["pf-information"].id' "$AGENT_IDS_FILE")
LAMBDA_ARN=$(jq -r '.lambdas["pf-information-actions"]' "$AGENT_IDS_FILE")

# Get v1 alias ID
INFORMATION_AGENT_ALIAS_ID=$(aws bedrock-agent list-agent-aliases --agent-id "$INFORMATION_AGENT_ID" --region us-east-1 --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' --output text)

if [ "$INFORMATION_AGENT_ID" == "null" ] || [ -z "$INFORMATION_AGENT_ID" ]; then
    echo -e "${RED}❌ Information agent ID not found in $AGENT_IDS_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Information Agent ID: $INFORMATION_AGENT_ID${NC}"
echo -e "${GREEN}✓ Information Agent Alias ID: $INFORMATION_AGENT_ALIAS_ID${NC}"
echo -e "${GREEN}✓ Lambda ARN: $LAMBDA_ARN${NC}"
echo ""

################################################################################
# Step 2: Package Lambda Function
################################################################################

echo -e "${YELLOW}[2/6] Packaging information-actions Lambda function...${NC}"

LAMBDA_DIR="$PROJECT_ROOT/lambda/information-actions"
cd "$LAMBDA_DIR"

# Create deployment package
echo "Creating deployment zip..."
rm -f information-actions.zip

# Add Python files
zip -q information-actions.zip handler.py config.py mock_data.py token_manager.py 2>/dev/null || true

# Add dependencies if they exist
if [ -d "requests" ]; then
    zip -qr information-actions.zip requests/
fi
if [ -d "urllib3" ]; then
    zip -qr information-actions.zip urllib3/
fi
if [ -d "certifi" ]; then
    zip -qr information-actions.zip certifi/
fi
if [ -d "charset_normalizer" ]; then
    zip -qr information-actions.zip charset_normalizer/
fi
if [ -d "idna" ]; then
    zip -qr information-actions.zip idna/
fi
if [ -d "dateutil" ]; then
    zip -qr information-actions.zip dateutil/
fi

ZIP_SIZE=$(du -h information-actions.zip | cut -f1)
echo -e "${GREEN}✓ Lambda package created: information-actions.zip ($ZIP_SIZE)${NC}"
echo ""

################################################################################
# Step 3: Update Lambda Function Code
################################################################################

echo -e "${YELLOW}[3/6] Updating Lambda function code...${NC}"

aws lambda update-function-code \
    --function-name pf-information-actions \
    --zip-file fileb://information-actions.zip \
    --region us-east-1 \
    --no-cli-pager

echo -e "${GREEN}✓ Lambda function code updated${NC}"
echo ""

# Wait for Lambda to be ready
echo "Waiting for Lambda function to be ready..."
aws lambda wait function-updated \
    --function-name pf-information-actions \
    --region us-east-1

echo -e "${GREEN}✓ Lambda function is ready${NC}"
echo ""

################################################################################
# Step 4: Update Agent Instructions
################################################################################

echo -e "${YELLOW}[4/6] Updating information agent instructions...${NC}"

INSTRUCTIONS_FILE="$PROJECT_ROOT/agent-instructions/information-agent-instructions.txt"

if [ ! -f "$INSTRUCTIONS_FILE" ]; then
    echo -e "${RED}❌ Instructions file not found: $INSTRUCTIONS_FILE${NC}"
    exit 1
fi

# Read instructions
INSTRUCTIONS=$(cat "$INSTRUCTIONS_FILE")

# Get current agent config
AGENT_FOUNDATION_MODEL=$(aws bedrock-agent get-agent --agent-id "$INFORMATION_AGENT_ID" --region us-east-1 --query 'agent.foundationModel' --output text)
AGENT_ROLE_ARN=$(aws bedrock-agent get-agent --agent-id "$INFORMATION_AGENT_ID" --region us-east-1 --query 'agent.agentResourceRoleArn' --output text)

# Update agent
aws bedrock-agent update-agent \
    --agent-id "$INFORMATION_AGENT_ID" \
    --agent-name "pf-information" \
    --foundation-model "$AGENT_FOUNDATION_MODEL" \
    --agent-resource-role-arn "$AGENT_ROLE_ARN" \
    --instruction "$INSTRUCTIONS" \
    --region us-east-1 \
    --no-cli-pager \
    --output json > /dev/null

echo -e "${GREEN}✓ Agent instructions updated${NC}"
echo ""

################################################################################
# Step 5: Prepare Agent
################################################################################

echo -e "${YELLOW}[5/6] Preparing agent (creating new version)...${NC}"

aws bedrock-agent prepare-agent \
    --agent-id "$INFORMATION_AGENT_ID" \
    --region us-east-1 \
    --no-cli-pager \
    --output json > /dev/null

echo -e "${GREEN}✓ Agent prepared${NC}"
echo ""

# Wait a moment for preparation to complete
echo "Waiting for agent preparation to complete..."
sleep 10

################################################################################
# Step 6: Update Agent Alias
################################################################################

echo -e "${YELLOW}[6/6] Updating agent alias to point to new version...${NC}"

# Get latest agent version
LATEST_VERSION=$(aws bedrock-agent list-agent-versions \
    --agent-id "$INFORMATION_AGENT_ID" \
    --region us-east-1 \
    --query 'agentVersionSummaries[0].agentVersion' \
    --output text)

echo "Latest agent version: $LATEST_VERSION"

# Update alias
aws bedrock-agent update-agent-alias \
    --agent-id "$INFORMATION_AGENT_ID" \
    --agent-alias-id "$INFORMATION_AGENT_ALIAS_ID" \
    --agent-alias-name "live" \
    --routing-configuration "agentVersion=$LATEST_VERSION" \
    --region us-east-1 \
    --no-cli-pager \
    --output json > /dev/null

echo -e "${GREEN}✓ Agent alias updated to version $LATEST_VERSION${NC}"
echo ""

################################################################################
# Summary
################################################################################

echo -e "${BLUE}============================================================================${NC}"
echo -e "${GREEN}✅ DEPLOYMENT COMPLETE${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""
echo -e "${GREEN}Information Agent has been updated:${NC}"
echo ""
echo "  • Lambda function: pf-information-actions (updated)"
echo "  • Agent ID: $INFORMATION_AGENT_ID"
echo "  • Agent Alias: $INFORMATION_AGENT_ALIAS_ID"
echo "  • Latest Version: $LATEST_VERSION"
echo ""
echo -e "${YELLOW}CHANGES SUMMARY:${NC}"
echo "  ✓ Removed: get_projects action → moved to scheduling agent"
echo "  ✓ Removed: get_project_details action → moved to scheduling agent"
echo "  ✓ Removed: get_appointment_status action → moved to scheduling agent"
echo "  ✓ Removed: get_working_hours action → moved to scheduling agent"
echo "  ✓ Kept: get_weather action (ONLY action remaining)"
echo ""
echo -e "${YELLOW}NEXT STEPS:${NC}"
echo "  1. Update Bedrock agent action group schema in AWS Console:"
echo "     - Go to Bedrock Console → Agents → pf-information"
echo "     - Update action group with: infrastructure/openapi_schemas/information_actions.json"
echo "  2. Test weather queries:"
echo "     - \"What's the weather in Tampa?\""
echo "     - \"Check weather for Miami, FL\""
echo "  3. Verify routing:"
echo "     - Project queries should now route to scheduling agent"
echo "     - Weather queries should route to information agent"
echo ""
echo -e "${BLUE}============================================================================${NC}"

cd "$PROJECT_ROOT"
