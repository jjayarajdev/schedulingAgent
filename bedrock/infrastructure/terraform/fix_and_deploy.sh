#!/bin/bash
################################################################################
# Fix Deployment Issues and Complete Setup
################################################################################

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "================================================================================"
echo "  🔧 Fixing Deployment Issues"
echo "================================================================================"
echo ""

cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/terraform

# Step 1: Import existing resources
echo -e "${YELLOW}Step 1: Importing existing resources...${NC}"
echo ""

terraform import aws_s3_bucket.agent_schemas scheduling-agent-schemas-dev-618048437522 2>/dev/null || echo "S3 bucket already in state"
terraform import aws_dynamodb_table.bedrock_sessions scheduling-agent-sessions-dev 2>/dev/null || echo "DynamoDB table already in state"

echo ""
echo -e "${GREEN}✓ Resources imported${NC}"
echo ""

# Step 2: Comment out aliases and collaborators temporarily
echo -e "${YELLOW}Step 2: Commenting out aliases and related outputs (temporary)...${NC}"
cp bedrock_agents.tf bedrock_agents.tf.backup

# Comment out all alias resources
sed -i.bak '/^resource "aws_bedrockagent_agent_alias"/,/^}/s/^/#/' bedrock_agents.tf
# Comment out all collaborator resources
sed -i.bak '/^resource "aws_bedrockagent_agent_collaborator"/,/^}/s/^/#/' bedrock_agents.tf
# Comment out alias outputs (lines 577-585)
sed -i.bak '577,585s/^/#/' bedrock_agents.tf

echo -e "${GREEN}✓ Aliases commented out${NC}"
echo ""

# Step 3: Apply to create/update agents only
echo -e "${YELLOW}Step 3: Creating/updating agents...${NC}"
echo ""
terraform apply -auto-approve

echo ""
echo -e "${GREEN}✓ Agents created${NC}"
echo ""

# Step 4: Prepare agents
echo -e "${YELLOW}Step 4: Preparing agents (this takes 3-5 minutes)...${NC}"
echo ""

chmod +x prepare_agents.sh
./prepare_agents.sh

echo ""
echo -e "${GREEN}✓ Agents prepared${NC}"
echo ""

# Step 5: Restore aliases and collaborators
echo -e "${YELLOW}Step 5: Restoring aliases and outputs...${NC}"
mv bedrock_agents.tf.backup bedrock_agents.tf
rm -f bedrock_agents.tf.bak

echo -e "${GREEN}✓ Configuration restored${NC}"
echo ""

# Step 6: Apply to create aliases and collaborators
echo -e "${YELLOW}Step 6: Creating aliases and collaborators...${NC}"
echo ""
terraform apply -auto-approve

echo ""
echo -e "${GREEN}✓ Aliases and collaborators created${NC}"
echo ""

# Step 7: Verification
echo ""
echo "================================================================================"
echo "  ✅ DEPLOYMENT COMPLETE!"
echo "================================================================================"
echo ""

echo "Deployment Summary:"
terraform output

echo ""
echo "Verifying collaborators..."
SUPERVISOR_ID=$(terraform output -raw supervisor_agent_id 2>/dev/null || echo "")
if [ ! -z "$SUPERVISOR_ID" ]; then
    aws bedrock-agent list-agent-collaborators \
        --agent-id $SUPERVISOR_ID \
        --agent-version DRAFT \
        --region us-east-1 \
        --query 'agentCollaboratorSummaries[*].[collaboratorName,collaboratorId]' \
        --output table 2>/dev/null || echo "Collaborators will be available shortly"
fi

echo ""
echo -e "${GREEN}🎉 Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Test: cd ../../tests && python3 comprehensive_test.py"
echo "  2. Start UI: cd ../frontend && ./start.sh"
echo ""
