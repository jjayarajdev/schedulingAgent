#!/bin/bash

# ============================================================================
# AWS Connect Voice Integration - Full Deployment
# ============================================================================
# Purpose: Deploy complete AWS Connect + Lex + Lambda + Bedrock integration
# Includes: Connect instance, Lex bot, Lambda functions, phone number config
# Phone Number: +1-833-877-1422
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
PHONE_NUMBER="+18338771422"  # 1-833-877-1422

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/infrastructure/terraform/voice"
LAMBDA_DIR="$PROJECT_ROOT/lambda"
CONFIG_FILE="$PROJECT_ROOT/config/agent_ids.json"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  AWS Connect Voice Integration - Full Deployment${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo "Environment: $ENVIRONMENT"
echo "Phone Number: $PHONE_NUMBER"
echo ""
echo "This deployment includes:"
echo "  ✅ AWS Connect instance"
echo "  ✅ Amazon Lex bot (with 5 intents)"
echo "  ✅ Lambda functions (lex-fulfillment, voice-bridge)"
echo "  ✅ DynamoDB table for sessions"
echo "  ✅ S3 bucket for call recordings"
echo "  ✅ IAM roles and permissions"
echo "  ✅ KMS encryption for recordings"
echo "  ✅ Contact flows"
echo ""

# ============================================================================
# Step 1: Load Agent IDs
# ============================================================================

echo -e "${YELLOW}[1/7] Loading Bedrock Agent IDs...${NC}"

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

echo -e "${YELLOW}[2/7] Packaging Lambda functions...${NC}"

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

echo -e "${YELLOW}[3/7] Creating Terraform configuration...${NC}"

cd "$TERRAFORM_DIR"

cat > terraform.tfvars <<EOF
# Project Configuration
prefix      = "$PREFIX"
environment = "$ENVIRONMENT"
region      = "$REGION"

# Bedrock Agent IDs (loaded from config/agent_ids.json)
supervisor_agent_id       = "$SUPERVISOR_AGENT_ID"
supervisor_agent_alias_id = "$SUPERVISOR_ALIAS_ID"
scheduling_agent_id       = "$SCHEDULING_AGENT_ID"
information_agent_id      = "$INFORMATION_AGENT_ID"
chitchat_agent_id         = "$CHITCHAT_AGENT_ID"

# Phone Number Configuration
connect_phone_number  = "$PHONE_NUMBER"
connect_instance_alias = "schedule-voice-dev"

# DynamoDB
dynamodb_table_name = "${PREFIX}-session-data-${ENVIRONMENT}"

# Lex Bot Configuration
lex_bot_name = "${PREFIX}-scheduling-assistant-${ENVIRONMENT}"
lex_voice_id = "Joanna"
EOF

echo -e "${GREEN}✅ Terraform configuration created${NC}"
echo ""

# ============================================================================
# Step 4: Initialize Terraform
# ============================================================================

echo -e "${YELLOW}[4/7] Initializing Terraform...${NC}"

terraform init -upgrade

echo -e "${GREEN}✅ Terraform initialized${NC}"
echo ""

# ============================================================================
# Step 5: Plan Deployment
# ============================================================================

echo -e "${YELLOW}[5/7] Planning Terraform deployment...${NC}"

terraform plan -out=tfplan

echo -e "${GREEN}✅ Terraform plan created${NC}"
echo ""

# ============================================================================
# Step 6: Deploy Infrastructure
# ============================================================================

echo -e "${YELLOW}[6/7] Deploying infrastructure...${NC}"
echo ""
read -p "Deploy infrastructure? (yes/no): " DEPLOY_CONFIRM

if [ "$DEPLOY_CONFIRM" != "yes" ]; then
  echo -e "${RED}Deployment cancelled${NC}"
  rm -f tfplan
  exit 0
fi

terraform apply tfplan
rm -f tfplan

echo -e "${GREEN}✅ Infrastructure deployed${NC}"
echo ""

# ============================================================================
# Step 7: Save Deployment Info
# ============================================================================

echo -e "${YELLOW}[7/7] Saving deployment information...${NC}"

# Get Terraform outputs
CONNECT_INSTANCE_ID=$(terraform output -raw connect_instance_id 2>/dev/null || echo "")
CONNECT_INSTANCE_ARN=$(terraform output -raw connect_instance_arn 2>/dev/null || echo "")
LEX_BOT_ID=$(terraform output -raw lex_bot_id 2>/dev/null || echo "")
LEX_BOT_ALIAS_ID=$(terraform output -raw lex_bot_alias_id 2>/dev/null || echo "")
LEX_FULFILLMENT_LAMBDA=$(terraform output -raw lex_fulfillment_function_name 2>/dev/null || echo "")
LEX_FULFILLMENT_ARN=$(terraform output -raw lex_fulfillment_function_arn 2>/dev/null || echo "")
VOICE_BRIDGE_LAMBDA=$(terraform output -raw voice_bedrock_bridge_function_name 2>/dev/null || echo "")
VOICE_BRIDGE_ARN=$(terraform output -raw voice_bedrock_bridge_function_arn 2>/dev/null || echo "")
DYNAMODB_TABLE=$(terraform output -raw dynamodb_table_name 2>/dev/null || echo "")
CALL_RECORDINGS_BUCKET=$(terraform output -raw call_recordings_bucket 2>/dev/null || echo "")

DEPLOYMENT_INFO_FILE="$PROJECT_ROOT/config/voice_deployment.json"

cat > "$DEPLOYMENT_INFO_FILE" <<EOF
{
  "deployed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "region": "$REGION",
  "account_id": "$ACCOUNT_ID",
  "deployment_type": "full",
  "phone_number": "$PHONE_NUMBER",
  "connect": {
    "instance_id": "$CONNECT_INSTANCE_ID",
    "instance_arn": "$CONNECT_INSTANCE_ARN",
    "phone_number": "$PHONE_NUMBER"
  },
  "lex": {
    "bot_id": "$LEX_BOT_ID",
    "bot_alias_id": "$LEX_BOT_ALIAS_ID",
    "bot_name": "${PREFIX}-scheduling-assistant-${ENVIRONMENT}"
  },
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
  "testing": {
    "test_phone_number": "$PHONE_NUMBER",
    "test_instructions": "Call $PHONE_NUMBER to test the voice assistant"
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
echo "  ✅ AWS Connect Instance: $CONNECT_INSTANCE_ID"
echo "  ✅ Phone Number: $PHONE_NUMBER"
echo "  ✅ Lex Bot: $LEX_BOT_ID"
echo "  ✅ Lambda: $LEX_FULFILLMENT_LAMBDA"
echo "  ✅ Lambda: $VOICE_BRIDGE_LAMBDA"
echo "  ✅ DynamoDB: $DYNAMODB_TABLE"
echo "  ✅ S3: $CALL_RECORDINGS_BUCKET"
echo ""

if [ -n "$CONNECT_INSTANCE_ID" ]; then
  echo "AWS Connect Console:"
  echo "  https://console.aws.amazon.com/connect/v2/app/instances/$CONNECT_INSTANCE_ID/admin"
  echo ""
fi

if [ -n "$LEX_BOT_ID" ]; then
  echo "Lex Bot Console:"
  echo "  https://console.aws.amazon.com/lexv2/home?region=$REGION#bot/$LEX_BOT_ID"
  echo ""
fi

echo "Lambda Functions:"
echo "  Lex Fulfillment ARN: $LEX_FULFILLMENT_ARN"
echo "  Voice Bridge ARN: $VOICE_BRIDGE_ARN"
echo ""

echo "Bedrock Agents:"
echo "  Supervisor: $SUPERVISOR_AGENT_ID (Alias: $SUPERVISOR_ALIAS_ID)"
echo ""

echo "Next Steps:"
echo ""
echo "1. Test the Phone Number:"
echo "   📞 Call: $PHONE_NUMBER"
echo ""
echo "2. Monitor Call Logs:"
echo "   aws logs tail /aws/lambda/$LEX_FULFILLMENT_LAMBDA --follow --region $REGION"
echo ""
echo "3. View Connect Metrics:"
echo "   https://console.aws.amazon.com/connect/v2/app/instances/$CONNECT_INSTANCE_ID/metrics"
echo ""
echo "4. Update Contact Flows (if needed):"
echo "   https://console.aws.amazon.com/connect/v2/app/instances/$CONNECT_INSTANCE_ID/contact-flows"
echo ""

echo -e "${GREEN}Voice integration fully deployed! Call $PHONE_NUMBER to test.${NC}"
echo ""
