#!/bin/bash
set -e

echo "=== AWS Connect Phone Number Claim Tool ==="
echo ""

# Get Connect instance
echo "Fetching Connect instance..."
INSTANCE_ARN=$(aws connect list-instances \
  --region us-east-1 \
  --query 'InstanceSummaryList[0].Arn' \
  --output text 2>/dev/null || echo "")

if [ -z "$INSTANCE_ARN" ] || [ "$INSTANCE_ARN" == "None" ]; then
  echo "❌ No Connect instance found!"
  echo ""
  echo "You need to create a Connect instance first."
  echo ""
  echo "Option 1: Via AWS Console (easiest)"
  echo "  1. Go to: https://console.aws.amazon.com/connect/"
  echo "  2. Click 'Create instance'"
  echo "  3. Set alias: pf-voice-dev"
  echo "  4. Complete setup (takes 2-3 min)"
  echo ""
  echo "Option 2: Via Terraform (automated)"
  echo "  cd infrastructure/terraform/voice"
  echo "  terraform init"
  echo "  terraform apply"
  echo ""
  exit 1
fi

INSTANCE_ID=$(echo "$INSTANCE_ARN" | awk -F'/' '{print $2}')
echo "✅ Found instance: $INSTANCE_ID"
echo "   ARN: $INSTANCE_ARN"
echo ""

# Ask user for number type
echo "What type of number do you want?"
echo "1) Toll-Free (1-800 number) - Recommended for business"
echo "   Cost: \$2.00/month + \$0.022/min inbound"
echo ""
echo "2) DID (Local area code number)"
echo "   Cost: \$0.90/month + \$0.0022/min inbound"
echo ""
read -p "Enter choice (1 or 2): " CHOICE

if [ "$CHOICE" == "1" ]; then
  NUMBER_TYPE="TOLL_FREE"
  echo ""
  echo "Searching for available toll-free numbers..."
  echo ""

  NUMBERS=$(aws connect search-available-phone-numbers \
    --target-arn "$INSTANCE_ARN" \
    --phone-number-country-code "US" \
    --phone-number-type "TOLL_FREE" \
    --max-results 10 \
    --region us-east-1 2>&1)

  if echo "$NUMBERS" | grep -q "error" || echo "$NUMBERS" | grep -q "Error"; then
    echo "❌ Error searching for numbers:"
    echo "$NUMBERS"
    exit 1
  fi

  echo "$NUMBERS" | jq -r '.AvailableNumbersList[] | .PhoneNumber' | nl -w2 -s'. '

elif [ "$CHOICE" == "2" ]; then
  NUMBER_TYPE="DID"
  echo ""
  read -p "Enter area code (e.g., 813 for Tampa, 212 for NYC): " AREA_CODE
  echo ""
  echo "Searching for available numbers in area code $AREA_CODE..."
  echo ""

  NUMBERS=$(aws connect search-available-phone-numbers \
    --target-arn "$INSTANCE_ARN" \
    --phone-number-country-code "US" \
    --phone-number-type "DID" \
    --phone-number-prefix "$AREA_CODE" \
    --max-results 10 \
    --region us-east-1 2>&1)

  if echo "$NUMBERS" | grep -q "error" || echo "$NUMBERS" | grep -q "Error"; then
    echo "❌ Error searching for numbers:"
    echo "$NUMBERS"
    exit 1
  fi

  if echo "$NUMBERS" | jq -r '.AvailableNumbersList | length' | grep -q "^0$"; then
    echo "❌ No numbers available in area code $AREA_CODE"
    echo "Try a different area code or choose toll-free (option 1)"
    exit 1
  fi

  echo "$NUMBERS" | jq -r '.AvailableNumbersList[] | .PhoneNumber' | nl -w2 -s'. '
else
  echo "❌ Invalid choice!"
  exit 1
fi

echo ""
read -p "Enter the phone number you want to claim (format: +18005551234): " PHONE_NUMBER

# Validate format
if ! echo "$PHONE_NUMBER" | grep -qE '^\+1[0-9]{10}$'; then
  echo "❌ Invalid format! Must be: +1XXXXXXXXXX (e.g., +18005551234)"
  exit 1
fi

echo ""
echo "Claiming $PHONE_NUMBER..."

CLAIM_RESULT=$(aws connect claim-phone-number \
  --target-arn "$INSTANCE_ARN" \
  --phone-number "$PHONE_NUMBER" \
  --phone-number-description "ProjectForce main inbound line" \
  --region us-east-1 2>&1)

if echo "$CLAIM_RESULT" | grep -q "error" || echo "$CLAIM_RESULT" | grep -q "Error"; then
  echo "❌ Error claiming number:"
  echo "$CLAIM_RESULT"
  exit 1
fi

PHONE_NUMBER_ID=$(echo "$CLAIM_RESULT" | jq -r '.PhoneNumberId')

echo ""
echo "✅ Success! Phone number claimed: $PHONE_NUMBER"
echo "   Phone Number ID: $PHONE_NUMBER_ID"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Next Steps:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Update Terraform variables:"
echo "   Edit: infrastructure/terraform/voice/terraform.tfvars"
echo "   Add:  connect_phone_number = \"$PHONE_NUMBER\""
echo ""
echo "2. Create a contact flow (if not done yet):"
echo "   - AWS Console → Connect → Routing → Contact flows"
echo "   - Create flow: pf-main-inbound"
echo "   - Add Lex bot integration"
echo ""
echo "3. Associate number with contact flow:"
echo "   - AWS Console → Connect → Channels → Phone numbers"
echo "   - Click on: $PHONE_NUMBER"
echo "   - Set Contact flow: pf-main-inbound"
echo "   - Click Save"
echo ""
echo "4. Test by calling: $PHONE_NUMBER"
echo ""
echo "For full deployment guide, see:"
echo "docs/AWS_CONNECT_IMPLEMENTATION_PLAN.md"
echo ""
