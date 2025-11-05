#!/bin/bash

################################################################################
# dev_deploy.sh - Quick Development Environment Deployment
################################################################################
#
# Purpose: Simplified deployment wrapper for development environments
#
# This script:
#   1. Runs the main DEPLOY.sh script (creates infrastructure and agents)
#   2. Runs SETUP_COLLABORATION.sh (configures agent collaboration)
#   3. Provides next steps for testing
#
# Prerequisites:
#   - AWS CLI configured with proper credentials
#   - Python 3.x installed
#   - pip3 installed
#   - zip utility available
#   - jq installed (for JSON parsing)
#
# Usage:
#   ./dev_deploy.sh
#
# What gets deployed:
#   - DynamoDB table (pf-sessions-dev)
#   - IAM roles and policies
#   - Lambda functions (scheduling, information, chitchat)
#   - 4 Bedrock agents (Supervisor, SchedulingAgent, pf-information, pf-chitchat)
#   - Agent aliases (v1 for each agent)
#   - Agent collaborations (Supervisor → specialist agents)
#   - Action groups with function schemas
#
################################################################################

set -e

# Determine script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_SCRIPT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo -e "${CYAN}ProjectForce Bedrock Multi-Agent System - Development Deployment${NC}"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

################################################################################
# Step 1: Run Main Deployment
################################################################################

echo -e "${BLUE}Step 1: Running Main Deployment (DEPLOY.sh)${NC}"
echo "─────────────────────────────────────────────────────────────────────────────"
echo ""
echo "This will:"
echo "  • Create/update Secrets Manager secret for ProjectForce API credentials"
echo "  • Deploy DynamoDB table (pf-sessions-dev)"
echo "  • Create IAM roles and policies"
echo "  • Package and deploy Lambda functions"
echo "  • Create 4 Bedrock agents"
echo "  • Create action groups with function schemas"
echo ""

read -p "Press Enter to continue or Ctrl+C to cancel..."
echo ""

# Run the main deployment script
cd "$PARENT_SCRIPT_DIR"
./DEPLOY.sh

DEPLOY_EXIT_CODE=$?

if [ $DEPLOY_EXIT_CODE -ne 0 ]; then
    echo ""
    echo -e "${RED}✗ Main deployment failed with exit code $DEPLOY_EXIT_CODE${NC}"
    echo ""
    echo "Please check the logs above for errors."
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Main deployment completed successfully${NC}"
echo ""

################################################################################
# Step 2: Setup Agent Collaboration
################################################################################

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo -e "${BLUE}Step 2: Setting Up Agent Collaboration${NC}"
echo "─────────────────────────────────────────────────────────────────────────────"
echo ""
echo "This will:"
echo "  • Create v1 aliases for all 4 agents (if not exists)"
echo "  • Configure Supervisor to collaborate with:"
echo "    - SchedulingAgent (for appointment scheduling)"
echo "    - pf-information (for weather queries)"
echo "    - pf-chitchat (for casual conversation)"
echo ""

read -p "Press Enter to continue or Ctrl+C to skip..."
echo ""

# Run collaboration setup
./SETUP_COLLABORATION.sh

COLLAB_EXIT_CODE=$?

if [ $COLLAB_EXIT_CODE -ne 0 ]; then
    echo ""
    echo -e "${YELLOW}⚠ Collaboration setup had issues (exit code $COLLAB_EXIT_CODE)${NC}"
    echo ""
    echo "This is often okay if the aliases and collaborations already exist."
    echo "Check the logs above to verify."
    echo ""
else
    echo ""
    echo -e "${GREEN}✓ Collaboration setup completed successfully${NC}"
    echo ""
fi

################################################################################
# Step 3: Next Steps
################################################################################

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo -e "${GREEN}✓ Deployment Complete!${NC}"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo -e "${CYAN}Next Steps:${NC}"
echo ""
echo "1. Test the deployment with the web UI:"
echo "   ${YELLOW}cd ../testing/ui${NC}"
echo "   ${YELLOW}./launch_auth_demo.sh${NC}"
echo ""
echo "2. Or test via AWS Console:"
echo "   • Open AWS Bedrock Console"
echo "   • Navigate to Agents"
echo "   • Select 'Supervisor' agent"
echo "   • Go to 'Test' tab"
echo "   • Try queries like:"
echo "     - 'show me my projects'"
echo "     - 'what is the weather in New York?'"
echo "     - 'tell me a joke'"
echo ""
echo "3. View deployment artifacts:"
echo "   • Agent IDs: ../config/agent_ids.json"
echo "   • Deployment logs: deployment_dev_*.log"
echo ""
echo "4. Troubleshooting:"
echo "   • Lambda logs: ${YELLOW}aws logs tail /aws/lambda/pf-scheduling-actions --follow${NC}"
echo "   • DynamoDB sessions: ${YELLOW}aws dynamodb scan --table-name pf-sessions-dev${NC}"
echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
