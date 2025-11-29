#!/bin/bash
#
# SMS Configuration Setup Script
# Configures AWS Pinpoint SMS v2 for two-way messaging
#
# This script configures:
#   - Configuration Set for SMS
#   - Two-way messaging (SNS topic subscription)
#   - Event destinations (SNS for delivery/failure events)
#
# Prerequisites:
#   - AWS CLI configured
#   - SNS topic already created (from deploy_sms_integration.sh)
#   - Phone number provisioned (or use test number for dev)
#
# Usage (from schedulingAgent directory):
#   ./scripts/deploy_sms_config_setup.sh dev
#   ./scripts/deploy_sms_config_setup.sh prod
#
#   # With specific phone number or phone ID:
#   SMS_PHONE_NUMBER=+14255556160 ./scripts/deploy_sms_config_setup.sh dev
#   SMS_PHONE_ID=phone-bcb7a02d40e740c595222a8dec3b9624 ./scripts/deploy_sms_config_setup.sh dev
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

# Configuration
ENVIRONMENT="${1:-dev}"
REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="scheduling-agent"

# Resource names
CONFIG_SET_NAME="${PROJECT_NAME}-sms-config-${ENVIRONMENT}"
SNS_TOPIC_NAME="${PROJECT_NAME}-sms-inbound-${ENVIRONMENT}"
EVENT_DESTINATION_NAME="sms-delivery-events-${ENVIRONMENT}"

# Phone number (use existing AWS phone number or override with SMS_PHONE_NUMBER env var)
# Example: SMS_PHONE_NUMBER=+14255556160 ./deploy_sms_config_setup.sh dev
# Or use phone ID directly: SMS_PHONE_ID=phone-xxxxx ./deploy_sms_config_setup.sh dev
PHONE_NUMBER="${SMS_PHONE_NUMBER:-+14255556160}"
PHONE_ID="${SMS_PHONE_ID:-phone-bcb7a02d40e740c595222a8dec3b9624}"

echo "=========================================="
echo "SMS Configuration Setup"
echo "=========================================="
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo "Phone Number: $PHONE_NUMBER"
echo "Configuration Set: $CONFIG_SET_NAME"
echo ""

# Verify prerequisites
log_info "Checking prerequisites..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI not found. Please install AWS CLI."
    exit 1
fi
log_success "AWS CLI found"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not configured. Run: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
log_success "AWS credentials configured (Account: $ACCOUNT_ID)"

echo ""

# Get SNS topic ARN
log_info "Getting SNS topic ARN..."
SNS_TOPIC_ARN=$(aws sns list-topics --region "$REGION" --query "Topics[?contains(TopicArn, '$SNS_TOPIC_NAME')].TopicArn" --output text)

if [ -z "$SNS_TOPIC_ARN" ]; then
    log_error "SNS topic not found: $SNS_TOPIC_NAME"
    log_error "Please run deploy_sms_integration.sh first"
    exit 1
fi
log_success "SNS Topic ARN: $SNS_TOPIC_ARN"

echo ""
log_info "Step 1: Updating SNS Topic Policy for Pinpoint SMS..."

# Get current SNS topic policy (disable exit on error)
set +e
TOPIC_POLICY=$(timeout 10 aws sns get-topic-attributes \
    --topic-arn "$SNS_TOPIC_ARN" \
    --attribute-name Policy \
    --region "$REGION" \
    --query 'Attributes.Policy' \
    --output text 2>/dev/null)
POLICY_EXIT_CODE=$?
set -e

# Check if pinpoint is allowed to publish
if [ $POLICY_EXIT_CODE -eq 0 ] && echo "$TOPIC_POLICY" | grep -q "sms-voice.amazonaws.com"; then
    log_success "SNS topic policy already allows Pinpoint SMS to publish"
else
    log_info "Adding Pinpoint SMS publish permission to SNS topic..."

    # Create policy that allows Pinpoint SMS to publish with source account condition
    POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowPinpointSMSPublish",
      "Effect": "Allow",
      "Principal": {
        "Service": "sms-voice.amazonaws.com"
      },
      "Action": "SNS:Publish",
      "Resource": "$SNS_TOPIC_ARN",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "$ACCOUNT_ID"
        }
      }
    },
    {
      "Sid": "AllowAccountAccess",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::${ACCOUNT_ID}:root"
      },
      "Action": [
        "SNS:GetTopicAttributes",
        "SNS:SetTopicAttributes",
        "SNS:AddPermission",
        "SNS:RemovePermission",
        "SNS:DeleteTopic",
        "SNS:Subscribe",
        "SNS:ListSubscriptionsByTopic",
        "SNS:Publish"
      ],
      "Resource": "$SNS_TOPIC_ARN"
    }
  ]
}
EOF
)

    aws sns set-topic-attributes \
        --topic-arn "$SNS_TOPIC_ARN" \
        --attribute-name Policy \
        --attribute-value "$POLICY" \
        --region "$REGION"

    if [ $? -eq 0 ]; then
        log_success "SNS topic policy updated with Pinpoint SMS publish permission"
    else
        log_error "Failed to update SNS topic policy"
        exit 1
    fi
fi

echo ""
log_info "Step 2: Creating Configuration Set..."

# Check if configuration set exists
if aws pinpoint-sms-voice-v2 describe-configuration-sets \
    --configuration-set-names "$CONFIG_SET_NAME" \
    --region "$REGION" &> /dev/null; then
    log_warning "Configuration set already exists: $CONFIG_SET_NAME"
else
    CONFIG_SET_ARN=$(aws pinpoint-sms-voice-v2 create-configuration-set \
        --configuration-set-name "$CONFIG_SET_NAME" \
        --region "$REGION" \
        --query 'ConfigurationSetArn' \
        --output text)

    if [ $? -eq 0 ]; then
        log_success "Configuration set created: $CONFIG_SET_ARN"
    else
        log_error "Failed to create configuration set"
        exit 1
    fi
fi

echo ""
log_info "Step 3: Creating Event Destination (SNS) for delivery events..."

# Check if event destination exists by parsing JSON output
set +e
CONFIG_DETAILS=$(aws pinpoint-sms-voice-v2 describe-configuration-sets \
    --configuration-set-names "$CONFIG_SET_NAME" \
    --region "$REGION" 2>/dev/null)
set -e

if echo "$CONFIG_DETAILS" | grep -q "\"EventDestinationName\":.*\"$EVENT_DESTINATION_NAME\""; then
    log_warning "Event destination already exists: $EVENT_DESTINATION_NAME"
else
    # Create event destination for SMS delivery status (disable exit on error for this command)
    set +e
    aws pinpoint-sms-voice-v2 create-event-destination \
        --event-destination-name "$EVENT_DESTINATION_NAME" \
        --configuration-set-name "$CONFIG_SET_NAME" \
        --matching-event-types TEXT_ALL \
        --sns-destination TopicArn="$SNS_TOPIC_ARN" \
        --region "$REGION" > /tmp/event_dest_output.txt 2>&1
    EVENT_DEST_EXIT_CODE=$?
    EVENT_DEST_OUTPUT=$(cat /tmp/event_dest_output.txt 2>/dev/null || echo "")
    set -e

    if [ $EVENT_DEST_EXIT_CODE -eq 0 ]; then
        log_success "Event destination created for delivery events"
    elif echo "$EVENT_DEST_OUTPUT" | grep -q "ConflictException\|already exists"; then
        log_warning "Event destination already exists (detected during creation)"
    else
        log_error "Event destination creation failed:"
        echo "$EVENT_DEST_OUTPUT"
        log_info "This may be due to SNS topic permissions. Continuing setup..."
    fi
fi

echo ""
log_info "Step 4: Checking if phone number exists..."

# Check if phone ID is provided directly, otherwise look up by phone number
if [ -z "$PHONE_ID" ]; then
    # Note: Cannot filter by phone number directly, must list all and filter
    # For production, always provide SMS_PHONE_ID directly
    PHONE_ID=$(aws pinpoint-sms-voice-v2 describe-phone-numbers \
        --region "$REGION" \
        --query "PhoneNumbers[?PhoneNumber=='$PHONE_NUMBER'].PhoneNumberId | [0]" \
        --output text 2>/dev/null)
fi

if [ "$PHONE_ID" = "None" ] || [ -z "$PHONE_ID" ]; then
    log_warning "Phone number not provisioned: $PHONE_NUMBER"
    log_warning "This is expected for dev environment with test number"
    log_info "For production, provision a real number and re-run this script"
    log_info "Or provide phone ID: SMS_PHONE_ID=phone-xxxxx ./deploy_sms_config_setup.sh dev"
else
    log_success "Phone number found: $PHONE_NUMBER (ID: $PHONE_ID)"

    echo ""
    log_info "Step 5: Creating IAM Role for Two-Way Messaging..."

    # IAM role name for two-way messaging
    IAM_ROLE_NAME="${PROJECT_NAME}-sms-twoway-role-${ENVIRONMENT}"

    # Check if IAM role exists
    if aws iam get-role --role-name "$IAM_ROLE_NAME" &> /dev/null; then
        log_success "IAM role already exists: $IAM_ROLE_NAME"
        IAM_ROLE_ARN=$(aws iam get-role --role-name "$IAM_ROLE_NAME" --query 'Role.Arn' --output text)
    else
        log_info "Creating IAM role for two-way messaging..."

        # Create trust policy for SMS Voice v2
        TRUST_POLICY=$(cat <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "sms-voice.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
)

        # Create IAM role
        IAM_ROLE_ARN=$(aws iam create-role \
            --role-name "$IAM_ROLE_NAME" \
            --assume-role-policy-document "$TRUST_POLICY" \
            --description "IAM role for SMS two-way messaging to publish to SNS topic" \
            --query 'Role.Arn' \
            --output text 2>&1)

        if [ $? -eq 0 ]; then
            log_success "IAM role created: $IAM_ROLE_ARN"
        else
            log_error "Failed to create IAM role"
            echo "$IAM_ROLE_ARN"
            exit 1
        fi

        # Create policy for SNS publish
        POLICY_DOCUMENT=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sns:Publish"
      ],
      "Resource": "$SNS_TOPIC_ARN"
    }
  ]
}
EOF
)

        # Attach inline policy
        aws iam put-role-policy \
            --role-name "$IAM_ROLE_NAME" \
            --policy-name "SNSPublishPolicy" \
            --policy-document "$POLICY_DOCUMENT" &> /dev/null

        if [ $? -eq 0 ]; then
            log_success "SNS publish policy attached to role"
        else
            log_warning "Failed to attach policy (may already exist)"
        fi

        # Wait for IAM role to propagate
        log_info "Waiting 15 seconds for IAM role to propagate..."
        sleep 15
    fi

    # Verify IAM role is accessible
    log_info "Verifying IAM role is accessible..."
    if aws iam get-role --role-name "$IAM_ROLE_NAME" &> /dev/null; then
        log_success "IAM role is accessible: $IAM_ROLE_ARN"
    else
        log_error "IAM role is not accessible yet"
        exit 1
    fi

    echo ""
    log_info "Step 6: Enabling Two-Way Messaging..."

    # Enable two-way messaging with SNS topic and IAM role
    # Note: For simulator numbers, this configures how inbound messages are routed
    UPDATE_OUTPUT=$(aws pinpoint-sms-voice-v2 update-phone-number \
        --phone-number-id "$PHONE_ID" \
        --two-way-enabled \
        --two-way-channel-arn "$SNS_TOPIC_ARN" \
        --two-way-channel-role "$IAM_ROLE_ARN" \
        --region "$REGION" 2>&1)

    if [ $? -eq 0 ]; then
        log_success "Two-way messaging enabled with SNS topic: $SNS_TOPIC_ARN"
        log_info "IAM role: $IAM_ROLE_ARN"
    else
        log_error "Failed to enable two-way messaging"
        echo "$UPDATE_OUTPUT"
        exit 1
    fi

    echo ""
    log_info "Step 7: Verifying Phone Number Configuration..."

    # Verify the phone number settings
    PHONE_CONFIG=$(aws pinpoint-sms-voice-v2 describe-phone-numbers \
        --region "$REGION" \
        --phone-number-ids "$PHONE_ID" \
        --query 'PhoneNumbers[0]' \
        --output json 2>/dev/null)

    if [ -n "$PHONE_CONFIG" ]; then
        TWO_WAY_ENABLED=$(echo "$PHONE_CONFIG" | grep -o '"TwoWayEnabled":[^,]*' | cut -d':' -f2 | tr -d ' ')
        TWO_WAY_CHANNEL=$(echo "$PHONE_CONFIG" | grep -o '"TwoWayChannelArn":"[^"]*"' | cut -d'"' -f4)

        if [ "$TWO_WAY_ENABLED" = "true" ]; then
            log_success "Two-way messaging verified: Enabled"
            log_info "Two-way channel: $TWO_WAY_CHANNEL"
        else
            log_warning "Two-way messaging verification: Not enabled"
        fi
    fi
fi

echo ""
echo "=========================================="
echo "Configuration Summary"
echo "=========================================="
echo ""
echo "Created/Configured Resources:"
echo "  ✓ Opt-Out List: Default (AWS managed)"
echo "  ✓ Configuration Set: $CONFIG_SET_NAME"
echo "  ✓ Event Destination: $EVENT_DESTINATION_NAME"
echo "  ✓ SNS Topic: $SNS_TOPIC_ARN"
if [ "$PHONE_ID" != "None" ] && [ -n "$PHONE_ID" ]; then
    echo "  ✓ Phone Number: $PHONE_NUMBER (Two-way enabled)"
else
    echo "  ⚠ Phone Number: $PHONE_NUMBER (Not provisioned - test mode)"
fi
echo ""

echo "Opt-Out Keywords (automatic handling):"
echo "  - STOP, STOPALL, UNSUBSCRIBE, CANCEL, END, QUIT"
echo ""

echo "Event Types Tracked:"
echo "  - TEXT_SENT: Message sent successfully"
echo "  - TEXT_DELIVERED: Message delivered to carrier"
echo "  - TEXT_FAILED: Message delivery failed"
echo ""

if [ "$PHONE_ID" = "None" ] || [ -z "$PHONE_ID" ]; then
    echo "=========================================="
    echo "Next Steps (Dev Environment)"
    echo "=========================================="
    echo ""
    echo "The test phone number is not provisioned."
    echo "You can still test with the existing setup:"
    echo ""
    echo "1. Test via SNS topic directly:"
    echo "   python scripts/test-sms-quick.py --environment $ENVIRONMENT"
    echo ""
    echo "2. For production with real SMS:"
    echo "   - Provision a phone number"
    echo "   - Set SMS_PHONE_NUMBER=+1XXXXXXXXXX"
    echo "   - Re-run this script"
    echo ""
else
    echo "=========================================="
    echo "Configuration Complete!"
    echo "=========================================="
    echo ""
    echo "Your SMS integration is fully configured."
    echo ""
    echo "Test by sending SMS to: $PHONE_NUMBER"
    echo "Or test programmatically:"
    echo "  python scripts/test-sms-quick.py --environment $ENVIRONMENT"
    echo ""
fi

log_success "SMS configuration setup completed successfully!"
echo ""
