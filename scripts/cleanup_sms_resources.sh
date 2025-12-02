#!/bin/bash
#
# SMS Integration Cleanup Script
# Removes all AWS resources created by deploy_sms_integration.sh and deploy_sms_config_setup.sh
#
# This script removes:
#   - Two-way messaging configuration
#   - Event destinations
#   - Configuration sets
#   - IAM roles and policies
#   - Lambda functions (via Terraform)
#   - DynamoDB tables (via Terraform)
#   - SNS topics (via Terraform)
#
# Usage:
#   ./cleanup_sms_resources.sh dev               # Interactive mode with confirmations
#   ./cleanup_sms_resources.sh dev --dry-run     # Show what would be deleted without deleting
#   ./cleanup_sms_resources.sh dev --force       # Delete without confirmations (use with caution!)
#

set -e

# Wrapper function to execute AWS CLI commands (cross-platform)
aws_cmd() {
    if command -v aws &> /dev/null; then
        aws "$@"
    elif [ -f "/c/Program Files/Amazon/AWSCLIV2/aws.exe" ]; then
        "/c/Program Files/Amazon/AWSCLIV2/aws.exe" "$@"
    elif [ -f "/c/Program Files (x86)/Amazon/AWSCLIV2/aws.exe" ]; then
        "/c/Program Files (x86)/Amazon/AWSCLIV2/aws.exe" "$@"
    else
        echo "AWS CLI not found" >&2
        return 1
    fi
}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_action() { echo -e "${MAGENTA}[ACTION]${NC} $1"; }

# Parse arguments
ENVIRONMENT="${1:-dev}"
DRY_RUN=false
FORCE=false

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            ;;
        --force)
            FORCE=true
            ;;
    esac
done

# Configuration
REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="scheduling-agent"

# Resource names
CONFIG_SET_NAME="${PROJECT_NAME}-sms-config-${ENVIRONMENT}"
SNS_TOPIC_NAME="${PROJECT_NAME}-sms-inbound-${ENVIRONMENT}"
EVENT_DESTINATION_NAME="sms-delivery-events-${ENVIRONMENT}"
IAM_ROLE_NAME="${PROJECT_NAME}-sms-twoway-role-${ENVIRONMENT}"
LAMBDA_NAME="${PROJECT_NAME}-sms-inbound-${ENVIRONMENT}"

# Phone ID - can be provided via SMS_PHONE_ID environment variable
# If not provided, script will skip phone number configuration cleanup
PHONE_ID="${SMS_PHONE_ID:-}"

# DynamoDB table names
MESSAGES_TABLE="${PROJECT_NAME}-sms-messages-${ENVIRONMENT}"
SESSIONS_TABLE="${PROJECT_NAME}-sms-sessions-${ENVIRONMENT}"
CONSENT_TABLE="${PROJECT_NAME}-sms-consent-${ENVIRONMENT}"
OPT_OUT_TABLE="${PROJECT_NAME}-opt-out-tracking-${ENVIRONMENT}"

echo "=========================================="
echo "SMS Integration Cleanup"
echo "=========================================="
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}Mode: DRY RUN (no resources will be deleted)${NC}"
elif [ "$FORCE" = true ]; then
    echo -e "${RED}Mode: FORCE (no confirmations)${NC}"
else
    echo "Mode: Interactive"
fi
echo ""

# Check prerequisites
log_info "Checking prerequisites..."

if ! aws_cmd sts get-caller-identity &> /dev/null; then
    log_error "AWS CLI not found or credentials not configured"
    log_error "Please install AWS CLI and run: aws configure"
    exit 1
fi
log_success "AWS CLI found"

if ! command -v terraform &> /dev/null; then
    log_error "Terraform not found. Please install Terraform."
    exit 1
fi

ACCOUNT_ID=$(aws_cmd sts get-caller-identity --query Account --output text)
log_success "Prerequisites verified (Account: $ACCOUNT_ID)"
echo ""

# Function to execute or simulate command
execute_or_simulate() {
    local description="$1"
    local command="$2"

    if [ "$DRY_RUN" = true ]; then
        log_action "[DRY RUN] Would execute: $description"
        log_info "Command: $command"
    else
        log_action "$description"
        eval "$command"
        if [ $? -eq 0 ]; then
            log_success "Completed: $description"
        else
            log_warning "Failed or already deleted: $description"
        fi
    fi
}

# Function to ask for confirmation
confirm_action() {
    local prompt="$1"

    if [ "$FORCE" = true ] || [ "$DRY_RUN" = true ]; then
        return 0
    fi

    read -p "$prompt (yes/no): " CONFIRM
    if [[ "$CONFIRM" != "yes" ]]; then
        log_warning "Skipped by user"
        return 1
    fi
    return 0
}

# Display resources to be deleted
echo "=========================================="
echo "Resources to be Deleted:"
echo "=========================================="
echo ""
echo "SMS Configuration Resources:"
echo "  - Configuration Set: $CONFIG_SET_NAME"
echo "  - Event Destination: $EVENT_DESTINATION_NAME"
echo "  - IAM Role: $IAM_ROLE_NAME"
if [ -n "$PHONE_ID" ]; then
    echo "  - Two-way messaging config on phone: $PHONE_ID"
else
    echo "  - Two-way messaging config: N/A (set SMS_PHONE_ID to cleanup)"
fi
echo ""
echo "Infrastructure Resources (via Terraform):"
echo "  - Lambda Function: $LAMBDA_NAME"
echo "  - SNS Topic: $SNS_TOPIC_NAME"
echo "  - DynamoDB Tables:"
echo "    • $MESSAGES_TABLE"
echo "    • $SESSIONS_TABLE"
echo "    • $CONSENT_TABLE"
echo "    • $OPT_OUT_TABLE"
echo "  - IAM Roles and Policies (Lambda execution role)"
echo ""

if [ "$DRY_RUN" = false ]; then
    log_warning "This will permanently delete all SMS integration resources!"
    log_warning "DynamoDB data will be LOST (unless backups exist)"
    echo ""

    if ! confirm_action "Continue with cleanup?"; then
        log_error "Cleanup cancelled"
        exit 1
    fi
    echo ""
fi

# Step 1: Disable two-way messaging
log_info "Step 1/6: Disabling two-way messaging on phone number..."

if [ -z "$PHONE_ID" ]; then
    log_info "Phone ID not provided (set SMS_PHONE_ID environment variable to cleanup phone config)"
else
    # Check if phone number exists
    PHONE_EXISTS=$(aws_cmd pinpoint-sms-voice-v2 describe-phone-numbers \
        --region "$REGION" \
        --phone-number-ids "$PHONE_ID" \
        --query 'PhoneNumbers[0].PhoneNumberId' \
        --output text 2>/dev/null || echo "None")

    if [ "$PHONE_EXISTS" != "None" ] && [ -n "$PHONE_EXISTS" ]; then
        TWO_WAY_ENABLED=$(aws_cmd pinpoint-sms-voice-v2 describe-phone-numbers \
            --region "$REGION" \
            --phone-number-ids "$PHONE_ID" \
            --query 'PhoneNumbers[0].TwoWayEnabled' \
            --output text 2>/dev/null || echo "False")

        if [ "$TWO_WAY_ENABLED" = "True" ]; then
            execute_or_simulate \
                "Disable two-way messaging on phone $PHONE_ID" \
                "aws_cmd pinpoint-sms-voice-v2 update-phone-number --phone-number-id '$PHONE_ID' --no-two-way-enabled --region '$REGION' &> /dev/null"
        else
            log_info "Two-way messaging already disabled or not configured"
        fi
    else
        log_info "Phone number not found: $PHONE_ID"
    fi
fi

echo ""

# Step 2: Delete event destination
log_info "Step 2/6: Deleting event destination..."

CONFIG_EXISTS=$(aws_cmd pinpoint-sms-voice-v2 describe-configuration-sets \
    --configuration-set-names "$CONFIG_SET_NAME" \
    --region "$REGION" \
    --query 'ConfigurationSets[0].ConfigurationSetName' \
    --output text 2>/dev/null || echo "None")

if [ "$CONFIG_EXISTS" != "None" ] && [ -n "$CONFIG_EXISTS" ]; then
    execute_or_simulate \
        "Delete event destination: $EVENT_DESTINATION_NAME" \
        "$AWS_CLI pinpoint-sms-voice-v2 delete-event-destination --event-destination-name '$EVENT_DESTINATION_NAME' --configuration-set-name '$CONFIG_SET_NAME' --region '$REGION' &> /dev/null"
else
    log_info "Configuration set not found"
fi

echo ""

# Step 3: Delete configuration set
log_info "Step 3/6: Deleting configuration set..."

if [ "$CONFIG_EXISTS" != "None" ] && [ -n "$CONFIG_EXISTS" ]; then
    execute_or_simulate \
        "Delete configuration set: $CONFIG_SET_NAME" \
        "$AWS_CLI pinpoint-sms-voice-v2 delete-configuration-set --configuration-set-name '$CONFIG_SET_NAME' --region '$REGION' &> /dev/null"
else
    log_info "Configuration set not found"
fi

echo ""

# Step 4: Delete IAM role
log_info "Step 4/6: Deleting IAM role and policies..."

IAM_ROLE_EXISTS=$(aws_cmd iam get-role --role-name "$IAM_ROLE_NAME" --query 'Role.RoleName' --output text 2>/dev/null || echo "None")

if [ "$IAM_ROLE_EXISTS" != "None" ] && [ -n "$IAM_ROLE_EXISTS" ]; then
    # Delete inline policies first
    execute_or_simulate \
        "Delete inline policy from IAM role: $IAM_ROLE_NAME" \
        "$AWS_CLI iam delete-role-policy --role-name '$IAM_ROLE_NAME' --policy-name 'SNSPublishPolicy' &> /dev/null"

    # Delete role
    execute_or_simulate \
        "Delete IAM role: $IAM_ROLE_NAME" \
        "$AWS_CLI iam delete-role --role-name '$IAM_ROLE_NAME' &> /dev/null"
else
    log_info "IAM role not found"
fi

echo ""

# Step 5: Destroy Terraform infrastructure
log_info "Step 5/6: Destroying Terraform infrastructure..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/../infrastructure/terraform/sms"

if [ ! -d "$TERRAFORM_DIR" ]; then
    log_error "Terraform directory not found: $TERRAFORM_DIR"
    exit 1
fi

cd "$TERRAFORM_DIR"

if [ "$DRY_RUN" = true ]; then
    log_action "[DRY RUN] Would run: terraform destroy in $TERRAFORM_DIR"
    log_info "This would delete:"
    log_info "  - Lambda function: $LAMBDA_NAME"
    log_info "  - SNS topic: $SNS_TOPIC_NAME"
    log_info "  - DynamoDB tables: 4 tables"
    log_info "  - IAM roles and policies"
else
    log_info "Initializing Terraform..."
    terraform init -input=false

    log_info "Planning destroy..."
    terraform plan -destroy -var="environment=$ENVIRONMENT" -out=tfplan-destroy

    echo ""
    if confirm_action "Execute Terraform destroy?"; then
        log_action "Destroying infrastructure with Terraform..."
        terraform apply tfplan-destroy

        if [ $? -eq 0 ]; then
            log_success "Terraform infrastructure destroyed"
            # Clean up terraform plan file
            rm -f tfplan-destroy
        else
            log_error "Terraform destroy failed"
            exit 1
        fi
    else
        log_warning "Terraform destroy skipped"
        rm -f tfplan-destroy
    fi
fi

cd "$SCRIPT_DIR"

echo ""

# Step 6: Verify cleanup
log_info "Step 6/6: Verifying cleanup..."

if [ "$DRY_RUN" = false ]; then
    echo ""
    log_info "Checking if resources still exist..."

    # Check Lambda
    LAMBDA_CHECK=$(aws_cmd lambda get-function --function-name "$LAMBDA_NAME" --region "$REGION" 2>/dev/null || echo "")
    if [ -z "$LAMBDA_CHECK" ]; then
        log_success "✓ Lambda deleted: $LAMBDA_NAME"
    else
        log_warning "✗ Lambda still exists: $LAMBDA_NAME"
    fi

    # Check SNS topic
    SNS_CHECK=$(aws_cmd sns list-topics --region "$REGION" --query "Topics[?contains(TopicArn, '$SNS_TOPIC_NAME')].TopicArn" --output text 2>/dev/null || echo "")
    if [ -z "$SNS_CHECK" ]; then
        log_success "✓ SNS topic deleted: $SNS_TOPIC_NAME"
    else
        log_warning "✗ SNS topic still exists: $SNS_TOPIC_NAME"
    fi

    # Check DynamoDB tables
    for table in "$MESSAGES_TABLE" "$SESSIONS_TABLE" "$CONSENT_TABLE" "$OPT_OUT_TABLE"; do
        TABLE_CHECK=$(aws_cmd dynamodb describe-table --table-name "$table" --region "$REGION" 2>/dev/null || echo "")
        if [ -z "$TABLE_CHECK" ]; then
            log_success "✓ DynamoDB table deleted: $table"
        else
            log_warning "✗ DynamoDB table still exists: $table"
        fi
    done

    # Check Configuration Set
    CONFIG_CHECK=$(aws_cmd pinpoint-sms-voice-v2 describe-configuration-sets --configuration-set-names "$CONFIG_SET_NAME" --region "$REGION" 2>/dev/null || echo "")
    if [ -z "$CONFIG_CHECK" ]; then
        log_success "✓ Configuration set deleted: $CONFIG_SET_NAME"
    else
        log_warning "✗ Configuration set still exists: $CONFIG_SET_NAME"
    fi

    # Check IAM role
    IAM_CHECK=$(aws_cmd iam get-role --role-name "$IAM_ROLE_NAME" 2>/dev/null || echo "")
    if [ -z "$IAM_CHECK" ]; then
        log_success "✓ IAM role deleted: $IAM_ROLE_NAME"
    else
        log_warning "✗ IAM role still exists: $IAM_ROLE_NAME"
    fi
fi

echo ""
echo "=========================================="
if [ "$DRY_RUN" = true ]; then
    log_success "Dry run completed - no resources were deleted"
    echo ""
    echo "To actually delete resources, run:"
    echo "  ./cleanup_sms_resources.sh $ENVIRONMENT"
elif [ "$FORCE" = true ]; then
    log_success "Force cleanup completed!"
else
    log_success "Cleanup completed!"
fi
echo "=========================================="
echo ""

if [ "$DRY_RUN" = false ]; then
    log_info "Resources deleted:"
    echo "  ✓ SMS configuration (config set, event destinations)"
    echo "  ✓ IAM roles and policies"
    echo "  ✓ Lambda functions"
    echo "  ✓ DynamoDB tables (data permanently deleted)"
    echo "  ✓ SNS topics"
    echo ""
    log_warning "Note: Phone number $PHONE_ID was NOT deleted (only config removed)"
    echo "        To delete the phone number, use AWS Console or CLI manually"
    echo ""
fi
