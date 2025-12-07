#!/bin/bash

# ============================================================================
# Update Lex V2 Bot Waiting Messages
# ============================================================================
# Purpose: Update the fulfillment waiting messages to be more natural/human-like
# Run this after DEPLOY_VOICE_ADVANCED.sh to apply natural waiting messages
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
BOT_ID="${LEX_BOT_ID:-MCMSOW2OXJ}"
BOT_VERSION="DRAFT"
LOCALE_ID="en_US"
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_PROFILE_OPT=""

if [[ -n "$AWS_PROFILE" ]]; then
    AWS_PROFILE_OPT="--profile $AWS_PROFILE"
fi

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}    Update Lex V2 Bot Waiting Messages${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""
echo -e "Bot ID: ${YELLOW}${BOT_ID}${NC}"
echo -e "Region: ${YELLOW}${AWS_REGION}${NC}"
echo -e "Profile: ${YELLOW}${AWS_PROFILE:-default}${NC}"
echo ""

# Get all intents
echo -e "${BLUE}[1/3] Getting list of intents...${NC}"
INTENTS=$(aws lexv2-models list-intents \
    $AWS_PROFILE_OPT \
    --bot-id "$BOT_ID" \
    --bot-version "$BOT_VERSION" \
    --locale-id "$LOCALE_ID" \
    --region "$AWS_REGION" \
    --query 'intentSummaries[*].[intentId,intentName]' \
    --output text 2>/dev/null)

if [[ -z "$INTENTS" ]]; then
    echo -e "${RED}[ERROR] Could not get intents. Check bot ID and credentials.${NC}"
    exit 1
fi

echo -e "${GREEN}  Found intents:${NC}"
echo "$INTENTS" | while read -r id name; do
    echo "    - $name ($id)"
done
echo ""

# Create Python script for updating
echo -e "${BLUE}[2/3] Updating intent fulfillment messages...${NC}"

python3 << 'PYTHON_SCRIPT'
import boto3
import json
import time
import os

# Get configuration from environment
bot_id = os.environ.get('BOT_ID', 'MCMSOW2OXJ')
bot_version = os.environ.get('BOT_VERSION', 'DRAFT')
locale_id = os.environ.get('LOCALE_ID', 'en_US')
region = os.environ.get('AWS_REGION', 'us-east-1')
profile = os.environ.get('AWS_PROFILE')

# Create session
if profile:
    session = boto3.Session(profile_name=profile, region_name=region)
else:
    session = boto3.Session(region_name=region)

client = session.client('lexv2-models')

# Natural, human-like waiting messages with SSML for better voice quality
# Uses prosody rate="slow" for more natural pacing
NATURAL_FULFILLMENT_UPDATES = {
    'active': True,
    'startResponse': {
        'delayInSeconds': 5,  # Wait 5 seconds before any message (most responses are faster)
        'messageGroups': [
            {'message': {'ssmlMessage': {'value': '<speak><prosody rate="slow">One moment</prosody></speak>'}}},
            {'message': {'ssmlMessage': {'value': '<speak><prosody rate="slow">Just a sec</prosody></speak>'}}},
            {'message': {'ssmlMessage': {'value': '<speak><prosody rate="slow">Checking on that</prosody></speak>'}}},
        ],
        'allowInterrupt': False
    },
    'updateResponse': {
        'frequencyInSeconds': 10,  # Update every 10 seconds if still waiting
        'messageGroups': [
            {'message': {'ssmlMessage': {'value': '<speak><prosody rate="slow">Still working on it</prosody></speak>'}}},
            {'message': {'ssmlMessage': {'value': '<speak><prosody rate="slow">Almost done</prosody></speak>'}}},
        ],
        'allowInterrupt': False
    },
    'timeoutInSeconds': 90
}

# Get all intents
intents_response = client.list_intents(
    botId=bot_id,
    botVersion=bot_version,
    localeId=locale_id
)

intents = [(i['intentId'], i['intentName']) for i in intents_response.get('intentSummaries', [])]
print(f"  Processing {len(intents)} intents...")

updated_count = 0
skipped_count = 0

for intent_id, intent_name in intents:
    try:
        # Get current intent configuration
        response = client.describe_intent(
            botId=bot_id,
            botVersion=bot_version,
            localeId=locale_id,
            intentId=intent_id
        )

        # Check if it has fulfillment code hook
        if 'fulfillmentCodeHook' not in response:
            print(f"    - {intent_name}: No fulfillment hook (skipped)")
            skipped_count += 1
            continue

        fulfillment = response['fulfillmentCodeHook']
        if not fulfillment.get('enabled', False):
            print(f"    - {intent_name}: Fulfillment not enabled (skipped)")
            skipped_count += 1
            continue

        # Build update request
        update_params = {
            'botId': bot_id,
            'botVersion': bot_version,
            'localeId': locale_id,
            'intentId': intent_id,
            'intentName': intent_name,
        }

        # Copy over existing fields
        optional_fields = [
            'description', 'parentIntentSignature', 'sampleUtterances',
            'dialogCodeHook', 'fulfillmentCodeHook', 'intentConfirmationSetting',
            'intentClosingSetting', 'inputContexts', 'outputContexts',
            'kendraConfiguration', 'initialResponseSetting', 'qnAIntentConfiguration'
        ]

        for field in optional_fields:
            if field in response:
                update_params[field] = response[field]

        # Update fulfillment messages
        update_params['fulfillmentCodeHook']['fulfillmentUpdatesSpecification'] = NATURAL_FULFILLMENT_UPDATES

        # Execute update
        client.update_intent(**update_params)
        print(f"    - {intent_name}: Updated")
        updated_count += 1

        time.sleep(0.3)  # Brief pause to avoid throttling

    except Exception as e:
        print(f"    - {intent_name}: ERROR - {e}")

print(f"\n  Summary: {updated_count} updated, {skipped_count} skipped")

# Trigger bot rebuild
print("\n  Rebuilding bot locale...")
try:
    build_response = client.build_bot_locale(
        botId=bot_id,
        botVersion=bot_version,
        localeId=locale_id
    )
    print(f"  Build started: {build_response['botLocaleStatus']}")
except Exception as e:
    print(f"  Build error: {e}")

PYTHON_SCRIPT

# Export environment variables for Python
export BOT_ID="$BOT_ID"
export BOT_VERSION="$BOT_VERSION"
export LOCALE_ID="$LOCALE_ID"
export AWS_REGION="$AWS_REGION"

echo ""

# Wait for build
echo -e "${BLUE}[3/3] Waiting for bot rebuild...${NC}"
for i in {1..20}; do
    STATUS=$(aws lexv2-models describe-bot-locale \
        $AWS_PROFILE_OPT \
        --bot-id "$BOT_ID" \
        --bot-version "$BOT_VERSION" \
        --locale-id "$LOCALE_ID" \
        --region "$AWS_REGION" \
        --query 'botLocaleStatus' \
        --output text 2>/dev/null)

    if [[ "$STATUS" == "Built" ]] || [[ "$STATUS" == "ReadyExpressTesting" ]]; then
        echo -e "${GREEN}  Bot rebuilt successfully!${NC}"
        break
    fi
    echo "  Status: $STATUS (waiting...)"
    sleep 3
done

# Refresh bot alias WITH Lambda code hook settings (critical for voice to work!)
echo ""
echo -e "${BLUE}Refreshing bot alias with Lambda code hook...${NC}"

# IMPORTANT: Use pf-lex-fulfillment-dev (NOT pf-orchestrator)
# pf-orchestrator expects API Gateway format, pf-lex-fulfillment-dev handles Lex V2 format
LAMBDA_ARN=$(aws lambda get-function \
    $AWS_PROFILE_OPT \
    --function-name pf-lex-fulfillment-dev \
    --region "$AWS_REGION" \
    --query 'Configuration.FunctionArn' \
    --output text 2>/dev/null)

if [[ -z "$LAMBDA_ARN" ]] || [[ "$LAMBDA_ARN" == "None" ]]; then
    echo -e "${YELLOW}  Warning: Could not get pf-lex-fulfillment-dev Lambda ARN${NC}"
    LAMBDA_ARN="arn:aws:lambda:${AWS_REGION}:$(aws sts get-caller-identity $AWS_PROFILE_OPT --query Account --output text):function:pf-lex-fulfillment-dev"
fi

echo "  Lambda ARN: $LAMBDA_ARN"

aws lexv2-models update-bot-alias \
    $AWS_PROFILE_OPT \
    --bot-id "$BOT_ID" \
    --bot-alias-id TSTALIASID \
    --bot-alias-name TestBotAlias \
    --bot-version DRAFT \
    --bot-alias-locale-settings "{
      \"en_US\": {
        \"enabled\": true,
        \"codeHookSpecification\": {
          \"lambdaCodeHook\": {
            \"lambdaARN\": \"$LAMBDA_ARN\",
            \"codeHookInterfaceVersion\": \"1.0\"
          }
        }
      }
    }" \
    --region "$AWS_REGION" \
    --query '[botAliasId, botAliasStatus]' \
    --output text 2>/dev/null && echo -e "${GREEN}  Alias refreshed with Lambda code hook!${NC}"

echo ""
echo -e "${GREEN}============================================================================${NC}"
echo -e "${GREEN}    Done! Natural waiting messages applied.${NC}"
echo -e "${GREEN}============================================================================${NC}"
echo ""
echo "Messages configured (with SSML prosody rate='slow' for natural voice):"
echo "  Start (after 5s):  'One moment' / 'Just a sec' / 'Checking on that'"
echo "  Update (every 10s): 'Still working on it' / 'Almost done'"
echo ""
