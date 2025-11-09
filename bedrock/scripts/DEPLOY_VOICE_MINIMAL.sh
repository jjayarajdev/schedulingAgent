#!/bin/bash

# ============================================================================
# AWS Connect Voice Integration - Minimal Deployment
# ============================================================================
# Purpose: Deploy Lambda functions and supporting infrastructure only
# Connect instance and Lex bot will be created via AWS Console
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
PREFIX="pf"
ENVIRONMENT="dev"

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/infrastructure/terraform/voice-minimal"
LAMBDA_DIR="$PROJECT_ROOT/lambda"
CONFIG_FILE="$PROJECT_ROOT/config/agent_ids.json"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Voice Integration - Minimal Deployment${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo "Environment: $ENVIRONMENT"
echo ""
echo "This deployment includes:"
echo "  ✅ Lambda functions (lex-fulfillment, voice-bridge)"
echo "  ✅ DynamoDB table for sessions"
echo "  ✅ S3 bucket for call recordings"
echo "  ✅ IAM roles and permissions"
echo ""
echo "You will create manually (via Console):"
echo "  📋 AWS Connect instance"
echo "  📋 Amazon Lex bot"
echo "  📋 Contact flows"
echo "  📋 Phone number"
echo ""

# ============================================================================
# Step 1: Load Agent IDs
# ============================================================================

echo -e "${YELLOW}[1/5] Loading Bedrock Agent IDs...${NC}"

if [ ! -f "$CONFIG_FILE" ]; then
  echo -e "${RED}❌ Config file not found: $CONFIG_FILE${NC}"
  exit 1
fi

SUPERVISOR_AGENT_ID=$(jq -r '.agents.Supervisor.id' "$CONFIG_FILE")
SCHEDULING_AGENT_ID=$(jq -r '.agents.SchedulingAgent.id' "$CONFIG_FILE")
INFORMATION_AGENT_ID=$(jq -r '.agents["pf-information"].id' "$CONFIG_FILE")
CHITCHAT_AGENT_ID=$(jq -r '.agents["pf-chitchat"].id' "$CONFIG_FILE")

echo "  Supervisor Agent ID: $SUPERVISOR_AGENT_ID"
echo "  Scheduling Agent ID: $SCHEDULING_AGENT_ID"
echo "  Information Agent ID: $INFORMATION_AGENT_ID"
echo "  ChitChat Agent ID: $CHITCHAT_AGENT_ID"

SUPERVISOR_ALIAS_ID=$(aws bedrock-agent list-agent-aliases \
  --agent-id "$SUPERVISOR_AGENT_ID" \
  --region "$REGION" \
  --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' \
  --output text 2>/dev/null || echo "")

if [ -z "$SUPERVISOR_ALIAS_ID" ] || [ "$SUPERVISOR_ALIAS_ID" == "None" ]; then
  echo "  Using test alias: TSTALIASID"
  SUPERVISOR_ALIAS_ID="TSTALIASID"
else
  echo "  Supervisor v1 Alias ID: $SUPERVISOR_ALIAS_ID"
fi

echo -e "${GREEN}✅ Agent IDs loaded${NC}"
echo ""

# ============================================================================
# Step 2: Package Lambda Functions
# ============================================================================

echo -e "${YELLOW}[2/5] Packaging Lambda functions...${NC}"

package_lambda() {
  local LAMBDA_NAME=$1
  local LAMBDA_PATH="$LAMBDA_DIR/$LAMBDA_NAME"

  echo "  Packaging: $LAMBDA_NAME"

  if [ ! -d "$LAMBDA_PATH" ]; then
    echo -e "${RED}    ❌ Lambda directory not found: $LAMBDA_PATH${NC}"
    return 1
  fi

  cd "$LAMBDA_PATH"

  rm -f deployment.zip
  rm -rf package

  if [ -f "requirements.txt" ] && [ -s "requirements.txt" ]; then
    echo "    Installing dependencies..."
    mkdir -p package
    pip3 install -r requirements.txt -t package/ -q 2>&1 | grep -v "ERROR:" || true
    cd package
    zip -r ../deployment.zip . -q
    cd ..
    zip -g deployment.zip handler.py -q
  else
    zip deployment.zip handler.py -q
  fi

  PACKAGE_SIZE=$(ls -lh deployment.zip | awk '{print $5}')
  echo -e "${GREEN}    ✅ Packaged: deployment.zip ($PACKAGE_SIZE)${NC}"

  cd "$PROJECT_ROOT"
}

package_lambda "lex-fulfillment"
package_lambda "voice-bedrock-bridge"

echo -e "${GREEN}✅ Lambda functions packaged${NC}"
echo ""

# ============================================================================
# Step 3: Create Terraform Configuration
# ============================================================================

echo -e "${YELLOW}[3/5] Creating Terraform configuration...${NC}"

cd "$TERRAFORM_DIR"

cat > terraform.tfvars <<EOF
# Project Configuration
prefix      = "$PREFIX"
environment = "$ENVIRONMENT"
region      = "$REGION"

# Bedrock Agent IDs (loaded from config/agent_ids.json)
supervisor_agent_id       = "$SUPERVISOR_AGENT_ID"
supervisor_agent_alias_id = "$SUPERVISOR_ALIAS_ID"

# DynamoDB
dynamodb_table_name = "${PREFIX}-session-data-${ENVIRONMENT}"
EOF

echo -e "${GREEN}✅ Terraform configuration created${NC}"
echo ""

# ============================================================================
# Step 4: Deploy Infrastructure
# ============================================================================

echo -e "${YELLOW}[4/5] Deploying infrastructure...${NC}"

terraform init -upgrade

echo ""
echo "Terraform will create:"
terraform plan

echo ""
read -p "Deploy infrastructure? (yes/no): " DEPLOY_CONFIRM

if [ "$DEPLOY_CONFIRM" != "yes" ]; then
  echo -e "${RED}Deployment cancelled${NC}"
  exit 0
fi

terraform apply -auto-approve

echo -e "${GREEN}✅ Infrastructure deployed${NC}"
echo ""

# ============================================================================
# Step 5: Save Deployment Info
# ============================================================================

echo -e "${YELLOW}[5/5] Saving deployment information...${NC}"

LEX_FULFILLMENT_LAMBDA=$(terraform output -raw lex_fulfillment_function_name)
LEX_FULFILLMENT_ARN=$(terraform output -raw lex_fulfillment_function_arn)
VOICE_BRIDGE_LAMBDA=$(terraform output -raw voice_bedrock_bridge_function_name)
VOICE_BRIDGE_ARN=$(terraform output -raw voice_bedrock_bridge_function_arn)
DYNAMODB_TABLE=$(terraform output -raw dynamodb_table_name)
CALL_RECORDINGS_BUCKET=$(terraform output -raw call_recordings_bucket)

DEPLOYMENT_INFO_FILE="$PROJECT_ROOT/config/voice_deployment.json"

cat > "$DEPLOYMENT_INFO_FILE" <<EOF
{
  "deployed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "region": "$REGION",
  "account_id": "$ACCOUNT_ID",
  "deployment_type": "minimal",
  "lambda": {
    "lex_fulfillment": "$LEX_FULFILLMENT_LAMBDA",
    "lex_fulfillment_arn": "$LEX_FULFILLMENT_ARN",
    "voice_bridge": "$VOICE_BRIDGE_LAMBDA",
    "voice_bridge_arn": "$VOICE_BRIDGE_ARN"
  },
  "storage": {
    "dynamodb_table": "$DYNAMODB_TABLE",
    "call_recordings_bucket": "$CALL_RECORDINGS_BUCKET"
  },
  "bedrock_agents": {
    "supervisor_id": "$SUPERVISOR_AGENT_ID",
    "supervisor_alias_id": "$SUPERVISOR_ALIAS_ID",
    "scheduling_id": "$SCHEDULING_AGENT_ID",
    "information_id": "$INFORMATION_AGENT_ID",
    "chitchat_id": "$CHITCHAT_AGENT_ID"
  },
  "next_steps": {
    "create_connect_instance": "See docs/AWS_CONSOLE_SETUP_GUIDE.md - Part 1",
    "create_lex_bot": "See docs/AWS_CONSOLE_SETUP_GUIDE.md - Part 2",
    "integrate_everything": "See docs/AWS_CONSOLE_SETUP_GUIDE.md - Parts 4-5"
  }
}
EOF

echo -e "${GREEN}✅ Deployment info saved to: $DEPLOYMENT_INFO_FILE${NC}"
echo ""

# ============================================================================
# Deployment Summary
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "What was deployed:"
echo "  ✅ Lambda: $LEX_FULFILLMENT_LAMBDA"
echo "  ✅ Lambda: $VOICE_BRIDGE_LAMBDA"
echo "  ✅ DynamoDB: $DYNAMODB_TABLE"
echo "  ✅ S3: $CALL_RECORDINGS_BUCKET"
echo ""

echo "Lambda ARNs (for Lex setup):"
echo "  Lex Fulfillment ARN:"
echo "    $LEX_FULFILLMENT_ARN"
echo ""
echo "  Voice Bridge ARN:"
echo "    $VOICE_BRIDGE_ARN"
echo ""

echo "Bedrock Agent IDs (for Lambda env vars):"
echo "  Supervisor: $SUPERVISOR_AGENT_ID"
echo "  Alias: $SUPERVISOR_ALIAS_ID"
echo ""

echo "Next Steps:"
echo ""
echo "1. Test Lambda Functions:"
echo "   ./scripts/test_voice_integration.sh"
echo ""
echo "2. Follow AWS Console Setup Guide:"
echo "   Open: docs/AWS_CONSOLE_SETUP_GUIDE.md"
echo ""
echo "   Part 1: Create AWS Connect instance & claim phone number (10-15 min)"
echo "   Part 2: Create Amazon Lex bot (15-20 min)"
echo "   Part 4: Connect Lex to Lambda (5 min)"
echo "           Use ARN: $LEX_FULFILLMENT_ARN"
echo "   Part 5: Integrate Lex with Connect (10 min)"
echo "   Part 6: Test by calling your phone number"
echo ""

echo "Monitoring:"
echo "  aws logs tail /aws/lambda/$LEX_FULFILLMENT_LAMBDA --follow --region $REGION"
echo "  aws logs tail /aws/lambda/$VOICE_BRIDGE_LAMBDA --follow --region $REGION"
echo ""

echo -e "${GREEN}Deployment successful! Follow the Console Setup Guide for remaining steps.${NC}"
echo ""
