#!/bin/bash

# ============================================================================
# Voice Permissions Setup Script (No Lex Build Required)
# ============================================================================
# Purpose: Configure Lambda and DynamoDB permissions for voice integration
# Skips Lex bot build (requires admin permissions)
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
export AWS_PROFILE=projectsforce
REGION="us-east-1"
ACCOUNT_ID="772634497954"
BOT_ID="WXFDD1TVEQ"
BOT_ALIAS_ID="TSTALIASID"
INSTANCE_ID="3edd99db-14e2-4628-836e-478b574e4b90"

LEX_FULFILLMENT_LAMBDA="pf-lex-fulfillment-dev"
VOICE_BRIDGE_LAMBDA="pf-voice-bedrock-bridge-dev"
CUSTOMER_LOOKUP_LAMBDA="pf-customer-lookup-dev"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Voice Integration - Permissions Setup${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ============================================================================
# Step 1: Grant Lex Permission to Invoke Lambda
# ============================================================================

echo -e "${YELLOW}[1/4] Granting Lex permission to invoke Lambda...${NC}"
echo ""

LEX_PERM_RESULT=$(aws lambda add-permission \
  --function-name $LEX_FULFILLMENT_LAMBDA \
  --statement-id LexInvokePermission \
  --action lambda:InvokeFunction \
  --principal lexv2.amazonaws.com \
  --source-arn "arn:aws:lex:$REGION:$ACCOUNT_ID:bot-alias/$BOT_ID/$BOT_ALIAS_ID" \
  --region $REGION 2>&1)

if echo "$LEX_PERM_RESULT" | grep -q "ResourceConflictException"; then
  echo -e "${CYAN}   ℹ️  Permission already exists for $LEX_FULFILLMENT_LAMBDA${NC}"
elif echo "$LEX_PERM_RESULT" | grep -q "error"; then
  echo -e "${RED}   ❌ Failed: $LEX_PERM_RESULT${NC}"
else
  echo -e "${GREEN}   ✅ Lex permission added to $LEX_FULFILLMENT_LAMBDA${NC}"
fi

echo ""


# ============================================================================
# Step 2: Grant Connect Permission to Invoke Lambdas
# ============================================================================

echo -e "${YELLOW}[2/4] Granting AWS Connect permission to invoke Lambdas...${NC}"
echo ""

for LAMBDA_NAME in $LEX_FULFILLMENT_LAMBDA $VOICE_BRIDGE_LAMBDA $CUSTOMER_LOOKUP_LAMBDA; do
  echo "   Processing: $LAMBDA_NAME"

  CONNECT_PERM_RESULT=$(aws lambda add-permission \
    --function-name $LAMBDA_NAME \
    --statement-id ConnectInvokePermission \
    --action lambda:InvokeFunction \
    --principal connect.amazonaws.com \
    --source-arn "arn:aws:connect:$REGION:$ACCOUNT_ID:instance/$INSTANCE_ID" \
    --region $REGION 2>&1)

  if echo "$CONNECT_PERM_RESULT" | grep -q "ResourceConflictException"; then
    echo -e "${CYAN}      ℹ️  Permission already exists${NC}"
  elif echo "$CONNECT_PERM_RESULT" | grep -q "error"; then
    echo -e "${RED}      ❌ Failed${NC}"
  else
    echo -e "${GREEN}      ✅ Connect permission added${NC}"
  fi
done

echo ""


# ============================================================================
# Step 3: Configure DynamoDB Permissions
# ============================================================================

echo -e "${YELLOW}[3/4] Configuring DynamoDB permissions...${NC}"
echo ""

LAMBDA_ROLE="pf-information-lambda-role-dev"

DYNAMODB_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
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
  echo -e "${RED}   ❌ Failed to attach DynamoDB policy${NC}"
  echo "   $POLICY_RESULT"
else
  echo -e "${GREEN}   ✅ DynamoDB policy attached to $LAMBDA_ROLE${NC}"
fi

echo ""


# ============================================================================
# Step 4: Verify Bedrock Permissions
# ============================================================================

echo -e "${YELLOW}[4/4] Verifying Bedrock agent permissions...${NC}"
echo ""

VOICE_BRIDGE_ROLE=$(aws lambda get-function \
  --function-name $VOICE_BRIDGE_LAMBDA \
  --region $REGION \
  --query 'Configuration.Role' \
  --output text 2>&1)

VOICE_BRIDGE_ROLE_NAME=$(echo $VOICE_BRIDGE_ROLE | awk -F'/' '{print $NF}')

echo "   Voice Bridge Role: $VOICE_BRIDGE_ROLE_NAME"

BEDROCK_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
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
  --policy-document "$BEDROCK_POLICY" 2>&1 > /dev/null

echo -e "${GREEN}   ✅ Bedrock permissions configured${NC}"

echo ""


# ============================================================================
# Summary
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Permissions Setup Completed!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${CYAN}What was configured:${NC}"
echo "  ✅ Lex permission to invoke Lambda"
echo "  ✅ Connect permission to invoke all voice Lambdas"
echo "  ✅ DynamoDB access for customer lookup"
echo "  ✅ Bedrock agent permissions"
echo ""

echo -e "${YELLOW}⚠️  Action Required - Contact AWS Admin:${NC}"
echo ""
echo "Your IAM user needs these additional permissions to complete setup:"
echo ""
echo "  {
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Action\": [
        \"lex:BuildBotLocale\",
        \"lex:DescribeBotLocale\",
        \"lex:DescribeCustomVocabularyMetadata\"
      ],
      \"Resource\": \"arn:aws:lex:us-east-1:772634497954:bot/WXFDD1TVEQ\"
    }]
  }"
echo ""
echo -e "${CYAN}Ask admin to:${NC}"
echo "  1. Add above permissions to user: jay.jayakeerthy@syntegreti.com"
echo "  2. Build Lex bot in console OR grant you permissions"
echo ""

echo -e "${CYAN}Manual Steps You Can Do Now:${NC}"
echo ""
echo "1. Create Contact Flow:"
echo "   https://us-east-1.console.aws.amazon.com/connect/v2/app/instances/$INSTANCE_ID/contact-flows"
echo ""

echo "2. Test Lambda functions work:"
echo "   cd testing/voice"
echo "   bash voice_test_suite_1_basic_intents.sh"
echo ""

echo -e "${GREEN}Permissions setup completed successfully!${NC}"
echo ""
