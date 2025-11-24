#!/bin/bash
################################################################################
# Complete Bedrock Multi-Agent Deployment Script
################################################################################
# This script automates the full 4-stage deployment process:
#   Stage 1: Deploy infrastructure (agents, DynamoDB, S3, IAM)
#   Stage 2: Prepare agents via AWS API
#   Stage 3: Create aliases and collaborator associations
#   Stage 4: Lambda integration (optional - enables real data retrieval)
#
# Usage: ./deploy_complete.sh
################################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "================================================================================"
echo "  🤖 Bedrock Multi-Agent System - Complete Deployment"
echo "================================================================================"
echo ""

# Check prerequisites
echo "Checking prerequisites..."
echo ""

# Check Terraform
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}✗ Terraform not found. Please install Terraform first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Terraform found: $(terraform version | head -1)${NC}"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}✗ AWS CLI not found. Please install AWS CLI first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ AWS CLI found: $(aws --version | cut -d' ' -f1)${NC}"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}✗ AWS credentials not configured or invalid${NC}"
    echo "Run: aws configure"
    exit 1
fi
echo -e "${GREEN}✓ AWS credentials configured${NC}"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${BLUE}  AWS Account: ${ACCOUNT_ID}${NC}"
echo ""

# Confirm deployment
echo "This will deploy:"
echo "  • 5 Bedrock Agents (Supervisor + 4 Collaborators)"
echo "  • 5 Agent Aliases"
echo "  • 4 Collaborator Associations"
echo "  • DynamoDB Session Table"
echo "  • S3 Bucket for Schemas"
echo "  • Lambda IAM Roles"
echo "  • Lambda Functions (optional - prompted at Stage 4)"
echo ""
read -p "Continue with deployment? (yes/no): " confirm

if [[ "$confirm" != "yes" ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "================================================================================"
echo "  STAGE 1: Deploying Infrastructure"
echo "================================================================================"
echo ""

# Check if Terraform is initialized
if [ ! -d ".terraform" ]; then
    echo "Initializing Terraform..."
    terraform init
    echo ""
fi

echo "Deploying agents and supporting infrastructure..."
echo ""
terraform apply -auto-approve

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Stage 1 complete - Infrastructure deployed${NC}"
else
    echo -e "${RED}✗ Stage 1 failed${NC}"
    exit 1
fi

echo ""
echo "================================================================================"
echo "  STAGE 2: Preparing Agents"
echo "================================================================================"
echo ""

echo "Preparing all agents via AWS Bedrock API..."
echo "This will take 3-5 minutes..."
echo ""

# Run prepare_agents.sh
if [ ! -f "prepare_agents.sh" ]; then
    echo -e "${RED}✗ prepare_agents.sh not found${NC}"
    exit 1
fi

chmod +x prepare_agents.sh
./prepare_agents.sh

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Stage 2 complete - All agents prepared${NC}"
else
    echo -e "${RED}✗ Stage 2 failed${NC}"
    exit 1
fi

echo ""
echo "================================================================================"
echo "  STAGE 3: Creating Aliases and Collaborators"
echo "================================================================================"
echo ""

echo "Creating agent aliases and collaborator associations..."
echo ""
terraform apply -auto-approve

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Stage 3 complete - Aliases and collaborators created${NC}"
else
    echo -e "${RED}✗ Stage 3 failed${NC}"
    exit 1
fi

echo ""
echo "================================================================================"
echo "  ✅ DEPLOYMENT COMPLETE!"
echo "================================================================================"
echo ""

# Display outputs
echo "Deployment Summary:"
echo ""
terraform output

echo ""
echo "================================================================================"
echo "  Verification"
echo "================================================================================"
echo ""

SUPERVISOR_ID=$(terraform output -raw supervisor_agent_id)
echo "Checking collaborator associations..."
aws bedrock-agent list-agent-collaborators \
    --agent-id $SUPERVISOR_ID \
    --agent-version DRAFT \
    --region us-east-1 \
    --query 'agentCollaboratorSummaries[*].[collaboratorName,collaboratorId]' \
    --output table

echo ""
echo "================================================================================"
echo "  STAGE 4: Lambda Integration (Optional)"
echo "================================================================================"
echo ""
echo "Would you like to integrate Lambda functions for real data retrieval?"
echo "Without this, agents will only provide conversational responses."
echo ""
echo "This will:"
echo "  • Deploy 3 Lambda functions (scheduling, information, notes)"
echo "  • Configure action groups"
echo "  • Enable agents to retrieve real data from DynamoDB"
echo ""
read -p "Deploy Lambda integration now? (yes/no): " lambda_confirm

if [[ "$lambda_confirm" == "yes" ]]; then
    echo ""
    echo "Running Lambda integration setup..."
    echo ""

    if [ ! -f "setup_lambda_integration.sh" ]; then
        echo -e "${RED}✗ setup_lambda_integration.sh not found${NC}"
        echo "You can run it manually later: ./setup_lambda_integration.sh"
    else
        chmod +x setup_lambda_integration.sh
        ./setup_lambda_integration.sh

        if [ $? -eq 0 ]; then
            echo ""
            echo -e "${GREEN}✓ Stage 4 complete - Lambda integration deployed${NC}"
        else
            echo -e "${RED}✗ Stage 4 failed${NC}"
            echo "You can retry later: ./setup_lambda_integration.sh"
        fi
    fi
else
    echo ""
    echo -e "${YELLOW}⚠️  Lambda integration skipped${NC}"
    echo "To enable real data retrieval later, run:"
    echo "   ./setup_lambda_integration.sh"
    echo ""
fi

echo ""
echo "================================================================================"
echo "  Next Steps"
echo "================================================================================"
echo ""

if [[ "$lambda_confirm" == "yes" ]]; then
    echo "1. Test the deployment with real data:"
    echo "   cd ../../tests"
    echo "   python3 comprehensive_test.py"
    echo ""
    echo "2. Start the UI:"
    echo "   cd ../frontend"
    echo "   ./start.sh"
    echo ""
else
    echo "1. Complete Lambda integration:"
    echo "   ./setup_lambda_integration.sh"
    echo ""
    echo "2. Test the deployment:"
    echo "   cd ../../tests"
    echo "   python3 comprehensive_test.py"
    echo ""
fi

echo "3. Use the supervisor agent:"
echo "   Alias ARN: $(terraform output -raw supervisor_alias_arn)"
echo ""
echo "4. Review documentation:"
echo "   - DEPLOYMENT_SUMMARY.md (complete technical details)"
echo "   - WORK_COMPLETED.md (how-to guide)"
echo "   - SCRIPTS_REFERENCE.md (all scripts)"
echo ""
echo -e "${GREEN}🎉 Your Bedrock multi-agent system is ready!${NC}"
echo ""
