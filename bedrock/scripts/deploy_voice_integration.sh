#!/bin/bash
#
# Phase 3 Voice Integration Deployment Script
# Deploys AWS Connect, Lex V2, and Voice Lambda functions
#
# Usage: ./deploy_voice_integration.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
REGION="${AWS_REGION:-us-east-1}"
PREFIX="${PROJECT_PREFIX:-pf}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

echo "=========================================="
echo "Phase 3: Voice Integration Deployment"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Region: $REGION"
echo "  Prefix: $PREFIX"
echo "  Environment: $ENVIRONMENT"
echo ""

# Verify prerequisites
log_info "Checking prerequisites..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI not found. Please install AWS CLI."
    exit 1
fi
log_success "AWS CLI found"

# Check Terraform
if ! command -v terraform &> /dev/null; then
    log_error "Terraform not found. Please install Terraform."
    exit 1
fi
log_success "Terraform found"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not configured. Run: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
log_success "AWS credentials configured (Account: $ACCOUNT_ID)"

# Get Supervisor Agent ID
log_info "Getting Bedrock Supervisor Agent ID..."
SUPERVISOR_ID=$(aws bedrock-agent list-agents --region $REGION | \
    jq -r '.agentSummaries[] | select(.agentName == "pf-supervisor-agent-dev") | .agentId')

if [ -z "$SUPERVISOR_ID" ]; then
    log_error "Could not find Supervisor agent ID. Please deploy Phase 1 first."
    exit 1
fi
log_success "Found Supervisor Agent: $SUPERVISOR_ID"

echo ""
log_warning "This script will deploy voice integration infrastructure. Continue? (y/n)"
read -r response
if [[ ! "$response" =~ ^[Yy]$ ]]; then
    log_info "Deployment cancelled."
    exit 0
fi

echo ""
echo "=========================================="
echo "STEP 1: Package Lambda Functions"
echo "=========================================="
echo ""

log_info "Packaging lex-fulfillment Lambda..."
cd lambda/lex-fulfillment
if [ -f deployment.zip ]; then
    rm deployment.zip
fi
zip -q -r deployment.zip handler.py
cd ../..
log_success "lex-fulfillment packaged"

log_info "Packaging voice-bedrock-bridge Lambda..."
cd lambda/voice-bedrock-bridge
if [ -f deployment.zip ]; then
    rm deployment.zip
fi
zip -q -r deployment.zip handler.py
cd ../..
log_success "voice-bedrock-bridge packaged"

echo ""
echo "=========================================="
echo "STEP 2: Deploy Voice Infrastructure (Terraform)"
echo "=========================================="
echo ""

cd infrastructure/terraform/voice

log_info "Initializing Terraform..."
terraform init

log_info "Validating Terraform configuration..."
terraform validate

log_info "Planning voice infrastructure deployment..."
terraform plan \
    -var="region=$REGION" \
    -var="prefix=$PREFIX" \
    -var="environment=$ENVIRONMENT" \
    -var="supervisor_agent_id=$SUPERVISOR_ID" \
    -var="supervisor_agent_alias_id=TSTALIASID" \
    -var="dynamodb_table_name=$PREFIX-session-data-$ENVIRONMENT" \
    -out=tfplan_voice

log_info "Applying Terraform configuration..."
terraform apply tfplan_voice

log_success "Voice infrastructure deployed!"

# Get outputs
CONNECT_INSTANCE_ID=$(terraform output -raw connect_instance_id 2>/dev/null || echo "")
LEX_BOT_ID=$(terraform output -raw lex_bot_id 2>/dev/null || echo "")
LEX_BOT_ALIAS_ARN=$(terraform output -raw lex_bot_alias_arn 2>/dev/null || echo "")

cd ../../..

echo ""
echo "=========================================="
echo "STEP 3: Claim Phone Number (Manual Step)"
echo "=========================================="
echo ""

log_warning "AWS Connect phone numbers must be claimed through the AWS Console"
log_info "Please follow these steps:"
echo ""
echo "1. Open AWS Connect Console:"
echo "   https://console.aws.amazon.com/connect/v2/app/instances/$CONNECT_INSTANCE_ID/phone-numbers"
echo ""
echo "2. Click 'Claim a number'"
echo "3. Select 'Toll free' (recommended)"
echo "4. Choose a number and claim it"
echo "5. Note the phone number for later steps"
echo ""
log_info "Press Enter when you have claimed a phone number..."
read -r

echo ""
echo "=========================================="
echo "STEP 4: Update Contact Flow ARNs"
echo "=========================================="
echo ""

log_info "Updating contact flow with actual ARNs..."

# Replace placeholders in contact flow
CONTACT_FLOW="infrastructure/voice/contact-flows/main-inbound-flow.json"
TEMP_FLOW="infrastructure/voice/contact-flows/main-inbound-flow-configured.json"

sed "s/REGION/$REGION/g" $CONTACT_FLOW | \
sed "s/ACCOUNT_ID/$ACCOUNT_ID/g" | \
sed "s/BOT_ID/$LEX_BOT_ID/g" > $TEMP_FLOW

log_success "Contact flow configured"

echo ""
echo "=========================================="
echo "STEP 5: Import Contact Flow (Manual Step)"
echo "=========================================="
echo ""

log_warning "Contact flows must be imported through the AWS Console"
log_info "Please follow these steps:"
echo ""
echo "1. Open AWS Connect Console:"
echo "   https://console.aws.amazon.com/connect/v2/app/instances/$CONNECT_INSTANCE_ID/contact-flows"
echo ""
echo "2. Click 'Create contact flow'"
echo "3. Click the dropdown arrow next to 'Save'"
echo "4. Select 'Import flow (beta)'"
echo "5. Select file: $TEMP_FLOW"
echo "6. Click 'Import'"
echo "7. Click 'Publish'"
echo "8. Note the Contact Flow ID from the URL"
echo ""
log_info "Press Enter when you have imported the contact flow..."
read -r

echo ""
echo "=========================================="
echo "STEP 6: Associate Phone Number with Flow (Manual Step)"
echo "=========================================="
echo ""

log_warning "Phone number must be associated through the AWS Console"
log_info "Please follow these steps:"
echo ""
echo "1. Open AWS Connect Phone Numbers:"
echo "   https://console.aws.amazon.com/connect/v2/app/instances/$CONNECT_INSTANCE_ID/phone-numbers"
echo ""
echo "2. Click on your claimed phone number"
echo "3. In 'Contact flow / IVR', select the flow you just created"
echo "4. Click 'Save'"
echo ""
log_info "Press Enter when you have associated the phone number..."
read -r

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "Deployed Resources:"
echo ""
echo "AWS Connect:"
echo "  - Instance ID: $CONNECT_INSTANCE_ID"
echo "  - Console: https://console.aws.amazon.com/connect/v2/app/instances"
echo ""
echo "Amazon Lex:"
echo "  - Bot ID: $LEX_BOT_ID"
echo "  - Bot Alias ARN: $LEX_BOT_ALIAS_ARN"
echo "  - Console: https://console.aws.amazon.com/lexv2/home?region=$REGION#bots"
echo ""
echo "Lambda Functions:"
echo "  - $PREFIX-lex-fulfillment-$ENVIRONMENT"
echo "  - $PREFIX-voice-bedrock-bridge-$ENVIRONMENT"
echo ""
echo "S3 Buckets:"
echo "  - $PREFIX-call-recordings-$ENVIRONMENT-$ACCOUNT_ID"
echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo ""
echo "1. Test the phone number by calling it"
echo ""
echo "2. Monitor CloudWatch Logs:"
echo "   - /aws/lambda/$PREFIX-lex-fulfillment-$ENVIRONMENT"
echo "   - /aws/lambda/$PREFIX-voice-bedrock-bridge-$ENVIRONMENT"
echo "   - /aws/connect/$CONNECT_INSTANCE_ID"
echo ""
echo "3. Test queries:"
echo "   - 'Show me my projects'"
echo "   - 'Schedule my most urgent project'"
echo "   - 'What's the weather like?'"
echo ""
echo "4. Review call recordings in S3:"
echo "   s3://$PREFIX-call-recordings-$ENVIRONMENT-$ACCOUNT_ID/recordings/"
echo ""
echo "=========================================="
echo "Troubleshooting:"
echo "=========================================="
echo ""
echo "If calls don't work:"
echo "  1. Check contact flow is published"
echo "  2. Verify phone number is associated with flow"
echo "  3. Check Lambda permissions in IAM"
echo "  4. Review CloudWatch Logs for errors"
echo ""
echo "If Lex doesn't respond:"
echo "  1. Verify Lex bot is built and published"
echo "  2. Check bot alias is 'prod'"
echo "  3. Test bot in Lex console"
echo ""
echo "If Bedrock doesn't respond:"
echo "  1. Verify Supervisor agent is deployed"
echo "  2. Check Lambda has bedrock:InvokeAgent permission"
echo "  3. Review voice-bedrock-bridge logs"
echo ""
echo "=========================================="
log_success "Phase 3 deployment completed successfully!"
echo "=========================================="
