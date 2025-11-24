#!/bin/bash

# ============================================================================
# Complete Voice Setup Script
# ============================================================================
# Purpose: Finalize AWS Connect + Lex + Lambda integration for voice calls
# Prerequisites: Lambda functions must be deployed first
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
export AWS_PROFILE=projectsforce
REGION="us-east-1"
ACCOUNT_ID="772634497954"
BOT_ID="WXFDD1TVEQ"
BOT_ALIAS_ID="TSTALIASID"
INSTANCE_ID="3edd99db-14e2-4628-836e-478b574e4b90"
PHONE_NUMBER="+18338771422"

# Lambda functions
LEX_FULFILLMENT_LAMBDA="pf-lex-fulfillment-dev"
VOICE_BRIDGE_LAMBDA="pf-voice-bedrock-bridge-dev"
CUSTOMER_LOOKUP_LAMBDA="pf-customer-lookup-dev"

# IAM role
LAMBDA_ROLE="pf-information-lambda-role-dev"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Complete Voice Integration Setup${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}Account:${NC} $ACCOUNT_ID"
echo -e "${CYAN}Region:${NC} $REGION"
echo -e "${CYAN}Phone:${NC} $PHONE_NUMBER"
echo ""

# Verify AWS credentials
echo -e "${YELLOW}[SETUP] Verifying AWS credentials...${NC}"
CURRENT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text 2>&1)
if [ "$CURRENT_ACCOUNT" != "$ACCOUNT_ID" ]; then
  echo -e "${RED}❌ Wrong AWS account. Expected: $ACCOUNT_ID, Got: $CURRENT_ACCOUNT${NC}"
  echo -e "${YELLOW}   Run: export AWS_PROFILE=projectsforce${NC}"
  exit 1
fi
echo -e "${GREEN}✅ AWS credentials verified (Account: $ACCOUNT_ID)${NC}"
echo ""


# ============================================================================
# Step 1: Build Lex Bot
# ============================================================================

echo -e "${YELLOW}[1/5] Building Lex Bot...${NC}"
echo "   Bot ID: $BOT_ID"
echo "   Locale: en_US"
echo ""

# Check current bot status
echo "   Checking bot status..."
BOT_STATUS=$(aws lexv2-models describe-bot-locale \
  --bot-id $BOT_ID \
  --bot-version DRAFT \
  --locale-id en_US \
  --region $REGION \
  --query 'botLocaleStatus' \
  --output text 2>&1)

echo "   Current status: $BOT_STATUS"

if [ "$BOT_STATUS" == "Built" ]; then
  echo -e "${GREEN}✅ Lex bot already built${NC}"
elif [ "$BOT_STATUS" == "Building" ]; then
  echo -e "${YELLOW}⏳ Bot is currently building, waiting for completion...${NC}"

  # Wait for build to complete (max 5 minutes)
  for i in {1..30}; do
    sleep 10
    BOT_STATUS=$(aws lexv2-models describe-bot-locale \
      --bot-id $BOT_ID \
      --bot-version DRAFT \
      --locale-id en_US \
      --region $REGION \
      --query 'botLocaleStatus' \
      --output text 2>&1)

    echo "   Status check $i/30: $BOT_STATUS"

    if [ "$BOT_STATUS" == "Built" ]; then
      echo -e "${GREEN}✅ Lex bot build completed${NC}"
      break
    fi

    if [ $i -eq 30 ]; then
      echo -e "${RED}❌ Bot build timeout. Check AWS Console.${NC}"
      exit 1
    fi
  done
else
  echo "   Starting bot build..."

  BUILD_RESPONSE=$(aws lexv2-models build-bot-locale \
    --bot-id $BOT_ID \
    --bot-version DRAFT \
    --locale-id en_US \
    --region $REGION 2>&1)

  if echo "$BUILD_RESPONSE" | grep -q "error"; then
    echo -e "${RED}❌ Failed to start bot build${NC}"
    echo "$BUILD_RESPONSE"
    exit 1
  fi

  echo -e "${YELLOW}⏳ Bot build started. Waiting for completion...${NC}"

  # Wait for build
  for i in {1..30}; do
    sleep 10
    BOT_STATUS=$(aws lexv2-models describe-bot-locale \
      --bot-id $BOT_ID \
      --bot-version DRAFT \
      --locale-id en_US \
      --region $REGION \
      --query 'botLocaleStatus' \
      --output text 2>&1)

    echo "   Build progress $i/30: $BOT_STATUS"

    if [ "$BOT_STATUS" == "Built" ]; then
      echo -e "${GREEN}✅ Lex bot build completed successfully${NC}"
      break
    fi

    if [ "$BOT_STATUS" == "Failed" ]; then
      echo -e "${RED}❌ Bot build failed. Check AWS Console for details.${NC}"
      exit 1
    fi

    if [ $i -eq 30 ]; then
      echo -e "${RED}❌ Bot build timeout (5 minutes). Check AWS Console.${NC}"
      exit 1
    fi
  done
fi

echo ""


# ============================================================================
# Step 2: Grant Lex Permission to Invoke Lambda Functions
# ============================================================================

echo -e "${YELLOW}[2/5] Granting Lex permission to invoke Lambda functions...${NC}"
echo ""

# Permission for lex-fulfillment Lambda
echo "   Granting permission for: $LEX_FULFILLMENT_LAMBDA"
LEX_PERM_RESULT=$(aws lambda add-permission \
  --function-name $LEX_FULFILLMENT_LAMBDA \
  --statement-id LexInvokePermission \
  --action lambda:InvokeFunction \
  --principal lexv2.amazonaws.com \
  --source-arn "arn:aws:lex:$REGION:$ACCOUNT_ID:bot-alias/$BOT_ID/$BOT_ALIAS_ID" \
  --region $REGION 2>&1)

if echo "$LEX_PERM_RESULT" | grep -q "ResourceConflictException"; then
  echo -e "${CYAN}   ℹ️  Permission already exists${NC}"
elif echo "$LEX_PERM_RESULT" | grep -q "error"; then
  echo -e "${RED}   ❌ Failed to add permission${NC}"
  echo "   $LEX_PERM_RESULT"
else
  echo -e "${GREEN}   ✅ Permission added${NC}"
fi

echo ""


# ============================================================================
# Step 3: Grant Connect Permission to Invoke Lambda Functions
# ============================================================================

echo -e "${YELLOW}[3/5] Granting AWS Connect permission to invoke Lambda functions...${NC}"
echo ""

# Permission for all voice Lambda functions
for LAMBDA_NAME in $LEX_FULFILLMENT_LAMBDA $VOICE_BRIDGE_LAMBDA $CUSTOMER_LOOKUP_LAMBDA; do
  echo "   Granting permission for: $LAMBDA_NAME"

  CONNECT_PERM_RESULT=$(aws lambda add-permission \
    --function-name $LAMBDA_NAME \
    --statement-id ConnectInvokePermission \
    --action lambda:InvokeFunction \
    --principal connect.amazonaws.com \
    --source-arn "arn:aws:connect:$REGION:$ACCOUNT_ID:instance/$INSTANCE_ID" \
    --region $REGION 2>&1)

  if echo "$CONNECT_PERM_RESULT" | grep -q "ResourceConflictException"; then
    echo -e "${CYAN}   ℹ️  Permission already exists${NC}"
  elif echo "$CONNECT_PERM_RESULT" | grep -q "error"; then
    echo -e "${RED}   ❌ Failed to add permission${NC}"
    echo "   $CONNECT_PERM_RESULT"
  else
    echo -e "${GREEN}   ✅ Permission added${NC}"
  fi
done

echo ""


# ============================================================================
# Step 4: Fix DynamoDB IAM Permissions
# ============================================================================

echo -e "${YELLOW}[4/5] Configuring DynamoDB permissions for customer lookup...${NC}"
echo "   Role: $LAMBDA_ROLE"
echo "   Tables: pf-customers-dev, pf-sessions-dev"
echo ""

DYNAMODB_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBTableAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:Query",
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/pf-customers-dev",
        "arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/pf-customers-dev/index/*",
        "arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/pf-sessions-dev",
        "arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/pf-sessions-dev/index/*"
      ]
    }
  ]
}
EOF
)

POLICY_RESULT=$(aws iam put-role-policy \
  --role-name $LAMBDA_ROLE \
  --policy-name VoiceDynamoDBAccessPolicy \
  --policy-document "$DYNAMODB_POLICY" 2>&1)

if echo "$POLICY_RESULT" | grep -q "error"; then
  echo -e "${RED}❌ Failed to attach DynamoDB policy${NC}"
  echo "$POLICY_RESULT"
else
  echo -e "${GREEN}✅ DynamoDB policy attached to $LAMBDA_ROLE${NC}"
fi

echo ""


# ============================================================================
# Step 5: Verify Bedrock Agent Permissions
# ============================================================================

echo -e "${YELLOW}[5/5] Verifying Bedrock agent permissions...${NC}"
echo ""

# Get the role used by voice-bridge Lambda
VOICE_BRIDGE_ROLE=$(aws lambda get-function \
  --function-name $VOICE_BRIDGE_LAMBDA \
  --region $REGION \
  --query 'Configuration.Role' \
  --output text 2>&1)

VOICE_BRIDGE_ROLE_NAME=$(echo $VOICE_BRIDGE_ROLE | awk -F'/' '{print $NF}')

echo "   Voice Bridge Lambda Role: $VOICE_BRIDGE_ROLE_NAME"

# Check if Bedrock permissions exist
BEDROCK_POLICY_CHECK=$(aws iam list-role-policies \
  --role-name $VOICE_BRIDGE_ROLE_NAME \
  --region $REGION \
  --query 'PolicyNames' \
  --output text 2>&1)

if echo "$BEDROCK_POLICY_CHECK" | grep -q "Bedrock"; then
  echo -e "${GREEN}✅ Bedrock permissions already configured${NC}"
else
  echo -e "${CYAN}   ℹ️  Bedrock permissions not found, adding...${NC}"

  BEDROCK_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockAgentInvoke",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeAgent",
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:$REGION:$ACCOUNT_ID:agent/*",
        "arn:aws:bedrock:$REGION:$ACCOUNT_ID:agent-alias/*/*"
      ]
    }
  ]
}
EOF
)

  aws iam put-role-policy \
    --role-name $VOICE_BRIDGE_ROLE_NAME \
    --policy-name BedrockAgentAccessPolicy \
    --policy-document "$BEDROCK_POLICY" 2>&1

  echo -e "${GREEN}✅ Bedrock permissions added${NC}"
fi

echo ""


# ============================================================================
# Summary and Next Steps
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Voice Setup Completed Successfully!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${CYAN}What was configured:${NC}"
echo "  ✅ Lex bot built and ready"
echo "  ✅ Lambda permissions granted (Lex + Connect)"
echo "  ✅ DynamoDB access configured"
echo "  ✅ Bedrock agent permissions verified"
echo ""

echo -e "${YELLOW}⚠️  Manual Steps Required:${NC}"
echo ""
echo "1. Create Contact Flow in AWS Connect Console:"
echo "   URL: https://us-east-1.console.aws.amazon.com/connect/v2/app/instances/$INSTANCE_ID/contact-flows"
echo ""
echo "   Steps:"
echo "   a) Click 'Create contact flow'"
echo "   b) Name: pf-main-inbound-voice"
echo "   c) Add blocks:"
echo "      - Set contact attributes (customer_phone, channel=voice)"
echo "      - Get customer input → Lex bot ($BOT_ID)"
echo "      - Invoke Lambda → $LEX_FULFILLMENT_LAMBDA"
echo "      - Play prompt (speak Lambda response)"
echo "      - Disconnect"
echo "   d) Save and PUBLISH"
echo ""

echo "2. Associate Phone Number with Contact Flow:"
echo "   URL: https://us-east-1.console.aws.amazon.com/connect/v2/app/instances/$INSTANCE_ID/phone-numbers"
echo ""
echo "   Steps:"
echo "   a) Find: $PHONE_NUMBER"
echo "   b) Click Edit"
echo "   c) Set Contact flow: pf-main-inbound-voice"
echo "   d) Save"
echo ""

echo "3. Test in Lex Console (before calling):"
echo "   URL: https://us-east-1.console.aws.amazon.com/lexv2/home?region=$REGION#bot/$BOT_ID"
echo ""
echo "   Test inputs:"
echo "   - 'hello' → Should get welcome message"
echo "   - 'show me my projects' → Should list projects"
echo "   - 'schedule appointment' → Should route to Bedrock"
echo ""

echo "4. Make Test Call:"
echo "   Call: $PHONE_NUMBER"
echo "   Say: 'hello' then 'show me my projects'"
echo ""

echo -e "${CYAN}Monitoring Commands:${NC}"
echo ""
echo "# Watch Lex Fulfillment logs:"
echo "aws logs tail /aws/lambda/$LEX_FULFILLMENT_LAMBDA --follow --region $REGION"
echo ""
echo "# Watch Voice Bridge logs:"
echo "aws logs tail /aws/lambda/$VOICE_BRIDGE_LAMBDA --follow --region $REGION"
echo ""
echo "# Check Connect call logs:"
echo "aws connect search-contact-flows --instance-id $INSTANCE_ID --region $REGION"
echo ""

echo -e "${GREEN}Setup script completed successfully!${NC}"
echo ""
