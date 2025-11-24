#!/bin/bash

# ============================================================================
# AWS Connect Voice Integration Deployment Script
# ============================================================================
# Purpose: Deploy complete AWS Connect + Lex + Lambda + Bedrock integration
# Author: ProjectForce Team
# Date: November 2025
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
PREFIX="pf"
ENVIRONMENT="dev"

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/infrastructure/terraform/voice"
LAMBDA_DIR="$PROJECT_ROOT/lambda"
CONFIG_FILE="$PROJECT_ROOT/config/agent_ids.json"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  AWS Connect Voice Integration Deployment${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo "Environment: $ENVIRONMENT"
echo ""

# ============================================================================
# Step 1: Load Agent IDs from config
# ============================================================================

echo -e "${YELLOW}[1/8] Loading Bedrock Agent IDs...${NC}"

if [ ! -f "$CONFIG_FILE" ]; then
  echo -e "${RED}❌ Config file not found: $CONFIG_FILE${NC}"
  exit 1
fi

# Extract agent IDs
SUPERVISOR_AGENT_ID=$(jq -r '.agents.Supervisor.id' "$CONFIG_FILE")
SCHEDULING_AGENT_ID=$(jq -r '.agents.SchedulingAgent.id' "$CONFIG_FILE")
INFORMATION_AGENT_ID=$(jq -r '.agents["pf-information"].id' "$CONFIG_FILE")
CHITCHAT_AGENT_ID=$(jq -r '.agents["pf-chitchat"].id' "$CONFIG_FILE")

echo "  Supervisor Agent ID: $SUPERVISOR_AGENT_ID"
echo "  Scheduling Agent ID: $SCHEDULING_AGENT_ID"
echo "  Information Agent ID: $INFORMATION_AGENT_ID"
echo "  ChitChat Agent ID: $CHITCHAT_AGENT_ID"

# Get Supervisor v1 alias ID
echo ""
echo "  Fetching Supervisor v1 alias..."
SUPERVISOR_ALIAS_ID=$(aws bedrock-agent list-agent-aliases \
  --agent-id "$SUPERVISOR_AGENT_ID" \
  --region "$REGION" \
  --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' \
  --output text 2>/dev/null || echo "")

if [ -z "$SUPERVISOR_ALIAS_ID" ] || [ "$SUPERVISOR_ALIAS_ID" == "None" ]; then
  echo -e "${YELLOW}  ⚠️  No v1 alias found, checking for TSTALIASID...${NC}"
  SUPERVISOR_ALIAS_ID="TSTALIASID"
else
  echo "  Supervisor v1 Alias ID: $SUPERVISOR_ALIAS_ID"
fi

echo -e "${GREEN}✅ Agent IDs loaded${NC}"
echo ""

# ============================================================================
# Step 2: Check DynamoDB table
# ============================================================================

echo -e "${YELLOW}[2/8] Checking DynamoDB table...${NC}"

DYNAMODB_TABLE="${PREFIX}-session-data-${ENVIRONMENT}"

TABLE_EXISTS=$(aws dynamodb describe-table \
  --table-name "$DYNAMODB_TABLE" \
  --region "$REGION" 2>&1 || echo "not_found")

if echo "$TABLE_EXISTS" | grep -q "not_found\|ResourceNotFoundException"; then
  echo "  Table does not exist, creating: $DYNAMODB_TABLE"

  aws dynamodb create-table \
    --table-name "$DYNAMODB_TABLE" \
    --attribute-definitions \
      AttributeName=session_id,AttributeType=S \
    --key-schema \
      AttributeName=session_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "$REGION" \
    --tags Key=Environment,Value="$ENVIRONMENT" Key=Project,Value=ProjectForce

  echo "  Waiting for table to be active..."
  aws dynamodb wait table-exists --table-name "$DYNAMODB_TABLE" --region "$REGION"
  echo -e "${GREEN}✅ DynamoDB table created${NC}"
else
  echo -e "${GREEN}✅ DynamoDB table exists: $DYNAMODB_TABLE${NC}"
fi
echo ""

# ============================================================================
# Step 3: Package Lambda Functions
# ============================================================================

echo -e "${YELLOW}[3/8] Packaging Lambda functions...${NC}"

package_lambda() {
  local LAMBDA_NAME=$1
  local LAMBDA_PATH="$LAMBDA_DIR/$LAMBDA_NAME"

  echo "  Packaging: $LAMBDA_NAME"

  if [ ! -d "$LAMBDA_PATH" ]; then
    echo -e "${RED}    ❌ Lambda directory not found: $LAMBDA_PATH${NC}"
    return 1
  fi

  cd "$LAMBDA_PATH"

  # Clean previous deployment package
  rm -f deployment.zip

  # Check if requirements.txt exists and has dependencies
  if [ -f "requirements.txt" ] && [ -s "requirements.txt" ]; then
    echo "    Installing dependencies..."

    # Clean old packages
    rm -rf package
    mkdir -p package

    # Install dependencies
    pip3 install -r requirements.txt -t package/ -q

    # Create zip with dependencies
    cd package
    zip -r ../deployment.zip . -q
    cd ..

    # Add handler
    zip -g deployment.zip handler.py -q
  else
    # No dependencies, just zip handler
    zip deployment.zip handler.py -q
  fi

  PACKAGE_SIZE=$(ls -lh deployment.zip | awk '{print $5}')
  echo -e "${GREEN}    ✅ Packaged: deployment.zip ($PACKAGE_SIZE)${NC}"

  cd "$PROJECT_ROOT"
}

# Package both Lambda functions
package_lambda "lex-fulfillment"
package_lambda "voice-bedrock-bridge"

echo -e "${GREEN}✅ Lambda functions packaged${NC}"
echo ""

# ============================================================================
# Step 4: Create Terraform variables file
# ============================================================================

echo -e "${YELLOW}[4/8] Creating Terraform configuration...${NC}"

cd "$TERRAFORM_DIR"

# Create terraform.tfvars with dynamic values
cat > terraform.tfvars <<EOF
# Project Configuration
prefix      = "$PREFIX"
environment = "$ENVIRONMENT"
region      = "$REGION"

# Bedrock Agent IDs (loaded from config/agent_ids.json)
supervisor_agent_id       = "$SUPERVISOR_AGENT_ID"
supervisor_agent_alias_id = "$SUPERVISOR_ALIAS_ID"

# DynamoDB
dynamodb_table_name = "$DYNAMODB_TABLE"

# AWS Connect Configuration
connect_instance_alias = "voice-${ENVIRONMENT}"
connect_phone_number   = "+18005551234"  # Will be updated after claiming

# Tags
tags = {
  Environment = "$ENVIRONMENT"
  Project     = "ProjectForce"
  ManagedBy   = "Terraform"
  Phase       = "2-Voice"
}
EOF

echo -e "${GREEN}✅ Terraform variables created${NC}"
cat terraform.tfvars
echo ""

# ============================================================================
# Step 5: Initialize Terraform
# ============================================================================

echo -e "${YELLOW}[5/8] Initializing Terraform...${NC}"

terraform init -upgrade

echo -e "${GREEN}✅ Terraform initialized${NC}"
echo ""

# ============================================================================
# Step 6: Plan Terraform deployment
# ============================================================================

echo -e "${YELLOW}[6/8] Planning Terraform deployment...${NC}"

terraform plan -out=tfplan

echo ""
read -p "Do you want to apply this plan? (yes/no): " APPLY_CONFIRM

if [ "$APPLY_CONFIRM" != "yes" ]; then
  echo -e "${RED}Deployment cancelled by user${NC}"
  exit 0
fi

echo ""

# ============================================================================
# Step 7: Apply Terraform deployment
# ============================================================================

echo -e "${YELLOW}[7/8] Deploying infrastructure...${NC}"

terraform apply tfplan

echo -e "${GREEN}✅ Infrastructure deployed${NC}"
echo ""

# ============================================================================
# Step 8: Get deployment outputs
# ============================================================================

echo -e "${YELLOW}[8/8] Retrieving deployment information...${NC}"

CONNECT_INSTANCE_ID=$(terraform output -raw connect_instance_id 2>/dev/null || echo "")
CONNECT_INSTANCE_URL=$(terraform output -raw connect_instance_url 2>/dev/null || echo "")
LEX_BOT_ID=$(terraform output -raw lex_bot_id 2>/dev/null || echo "")
LEX_BOT_ALIAS_ID=$(terraform output -raw lex_bot_alias_id 2>/dev/null || echo "")
LEX_FULFILLMENT_LAMBDA=$(terraform output -raw lex_fulfillment_function_name 2>/dev/null || echo "")
VOICE_BRIDGE_LAMBDA=$(terraform output -raw voice_bedrock_bridge_function_name 2>/dev/null || echo "")
CALL_RECORDINGS_BUCKET=$(terraform output -raw call_recordings_bucket 2>/dev/null || echo "")

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Deployment Outputs:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "AWS Connect:"
echo "  Instance ID: $CONNECT_INSTANCE_ID"
echo "  Console URL: $CONNECT_INSTANCE_URL"
echo ""
echo "Amazon Lex:"
echo "  Bot ID: $LEX_BOT_ID"
echo "  Alias ID: $LEX_BOT_ALIAS_ID"
echo ""
echo "Lambda Functions:"
echo "  Lex Fulfillment: $LEX_FULFILLMENT_LAMBDA"
echo "  Voice Bridge: $VOICE_BRIDGE_LAMBDA"
echo ""
echo "Storage:"
echo "  Call Recordings: s3://$CALL_RECORDINGS_BUCKET"
echo ""

# Save deployment info to config
DEPLOYMENT_INFO_FILE="$PROJECT_ROOT/config/voice_deployment.json"

cat > "$DEPLOYMENT_INFO_FILE" <<EOF
{
  "deployed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "region": "$REGION",
  "account_id": "$ACCOUNT_ID",
  "connect": {
    "instance_id": "$CONNECT_INSTANCE_ID",
    "instance_url": "$CONNECT_INSTANCE_URL"
  },
  "lex": {
    "bot_id": "$LEX_BOT_ID",
    "alias_id": "$LEX_BOT_ALIAS_ID"
  },
  "lambda": {
    "lex_fulfillment": "$LEX_FULFILLMENT_LAMBDA",
    "voice_bridge": "$VOICE_BRIDGE_LAMBDA"
  },
  "storage": {
    "call_recordings_bucket": "$CALL_RECORDINGS_BUCKET"
  },
  "bedrock_agents": {
    "supervisor_id": "$SUPERVISOR_AGENT_ID",
    "supervisor_alias_id": "$SUPERVISOR_ALIAS_ID",
    "scheduling_id": "$SCHEDULING_AGENT_ID",
    "information_id": "$INFORMATION_AGENT_ID",
    "chitchat_id": "$CHITCHAT_AGENT_ID"
  }
}
EOF

echo "Deployment info saved to: $DEPLOYMENT_INFO_FILE"
echo ""

# ============================================================================
# Deployment Summary
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "What was deployed:"
echo "  ✅ AWS Connect instance"
echo "  ✅ Amazon Lex V2 bot with 5 intents"
echo "  ✅ 2 Lambda functions (lex-fulfillment, voice-bridge)"
echo "  ✅ DynamoDB table for session data"
echo "  ✅ S3 bucket for call recordings"
echo "  ✅ IAM roles and permissions"
echo "  ✅ CloudWatch log groups"
echo ""

echo "Next Steps:"
echo ""
echo "1. Build Lex Bot:"
echo "   aws lexv2-models build-bot-locale \\"
echo "     --bot-id $LEX_BOT_ID \\"
echo "     --bot-version DRAFT \\"
echo "     --locale-id en_US \\"
echo "     --region $REGION"
echo ""

echo "2. Test Lambda Functions:"
echo "   ./scripts/test_voice_integration.sh"
echo ""

echo "3. Claim a Phone Number:"
echo "   - Use AWS Console or run: ./scripts/claim_phone_number.sh"
echo ""

echo "4. Create Contact Flow:"
echo "   - Go to: $CONNECT_INSTANCE_URL"
echo "   - Navigate to: Routing → Contact flows"
echo "   - Create flow: pf-main-inbound"
echo "   - Add Lex bot: $LEX_BOT_ID"
echo ""

echo "5. Associate Phone Number with Contact Flow:"
echo "   - Go to: Channels → Phone numbers"
echo "   - Select your claimed number"
echo "   - Set Contact flow: pf-main-inbound"
echo ""

echo "6. Test by calling your phone number"

echo ""
echo "Monitoring:"
echo "  Lex Fulfillment Logs:"
echo "    aws logs tail /aws/lambda/$LEX_FULFILLMENT_LAMBDA --follow --region $REGION"
echo ""
echo "  Voice Bridge Logs:"
echo "    aws logs tail /aws/lambda/$VOICE_BRIDGE_LAMBDA --follow --region $REGION"
echo ""

echo "Documentation:"
echo "  Implementation Plan: docs/AWS_CONNECT_IMPLEMENTATION_PLAN.md"
echo "  Deployment Info: config/voice_deployment.json"
echo ""

echo -e "${GREEN}Deployment script completed successfully!${NC}"
echo ""
