#!/bin/bash
#
# SMS Integration Deployment Script
# Packages Lambda, deploys SNS topic, Lambda function, DynamoDB tables for SMS processing
#
# Usage:
#   ./deploy_sms_integration.sh dev
#   ./deploy_sms_integration.sh prod
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

echo "=========================================="
echo "SMS Integration Deployment"
echo "=========================================="
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/../infrastructure/terraform/sms"
LAMBDA_DIR="$SCRIPT_DIR/../lambda/sms-inbound-processor"
BUILD_DIR="$LAMBDA_DIR/build"
ZIP_FILE="$LAMBDA_DIR/lambda.zip"

# Step 1: Package Lambda function
log_info "Step 1/3: Packaging Lambda function..."

if [ ! -f "$LAMBDA_DIR/handler.py" ]; then
    log_error "Lambda handler not found: $LAMBDA_DIR/handler.py"
    exit 1
fi

# Clean previous build
if [ -d "$BUILD_DIR" ]; then
    log_info "Cleaning previous build..."
    rm -rf "$BUILD_DIR"
fi

if [ -f "$ZIP_FILE" ]; then
    rm -f "$ZIP_FILE"
fi

# Create build directory
mkdir -p "$BUILD_DIR"

# Copy Lambda handler
log_info "Copying Lambda handler..."
cp "$LAMBDA_DIR/handler.py" "$BUILD_DIR/"

# Install dependencies if requirements.txt exists
if [ -f "$LAMBDA_DIR/requirements.txt" ] && [ -s "$LAMBDA_DIR/requirements.txt" ]; then
    log_info "Installing Python dependencies..."
    pip install -r "$LAMBDA_DIR/requirements.txt" -t "$BUILD_DIR/" --quiet --no-cache-dir

    if [ $? -ne 0 ]; then
        log_error "Failed to install dependencies"
        exit 1
    fi
    log_success "Dependencies installed"
else
    log_warning "No requirements.txt found, packaging handler only"
fi

# Create ZIP package
log_info "Creating lambda.zip..."
cd "$BUILD_DIR"
zip -r "$ZIP_FILE" . -q

if [ $? -ne 0 ]; then
    log_error "Failed to create lambda.zip"
    exit 1
fi

# Get package size
PACKAGE_SIZE=$(du -h "$ZIP_FILE" | cut -f1)
log_success "Lambda package created: $PACKAGE_SIZE"

# Clean up build directory
cd "$SCRIPT_DIR"
rm -rf "$BUILD_DIR"

echo ""

# Step 2: Deploy infrastructure with Terraform
log_info "Step 2/3: Deploying infrastructure with Terraform..."
cd "$TERRAFORM_DIR" || exit 1

log_info "Initializing Terraform..."
terraform init

log_info "Planning deployment..."
terraform plan -var="environment=$ENVIRONMENT" -out=tfplan

echo ""
read -p "Apply this plan? (yes/no): " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
    log_error "Deployment cancelled"
    exit 1
fi

log_info "Deploying infrastructure..."
terraform apply tfplan

log_success "Infrastructure deployed successfully!"

echo ""

# Step 3: Verify deployment
log_info "Step 3/3: Verifying deployment..."

LAMBDA_NAME="${PROJECT_NAME}-sms-inbound-${ENVIRONMENT}"

# Check if Lambda exists
LAMBDA_ARN=$(aws lambda get-function --function-name "$LAMBDA_NAME" --region "$REGION" --query 'Configuration.FunctionArn' --output text 2>/dev/null || echo "")

if [ -n "$LAMBDA_ARN" ]; then
    log_success "Lambda function verified: $LAMBDA_NAME"
else
    log_warning "Could not verify Lambda deployment"
fi

# Check SNS topic
SNS_TOPIC_NAME="${PROJECT_NAME}-sms-inbound-${ENVIRONMENT}"
SNS_TOPIC_ARN=$(aws sns list-topics --region "$REGION" --query "Topics[?contains(TopicArn, '$SNS_TOPIC_NAME')].TopicArn" --output text 2>/dev/null || echo "")

if [ -n "$SNS_TOPIC_ARN" ]; then
    log_success "SNS topic verified: $SNS_TOPIC_NAME"
else
    log_warning "Could not verify SNS topic"
fi

echo ""
log_success "Deployment complete!"

echo ""
echo "=========================================="
echo "Deployed Resources:"
echo "=========================================="
echo "Lambda Function:  $LAMBDA_NAME"
echo "SNS Topic:        $SNS_TOPIC_NAME"
echo "DynamoDB Tables:"
echo "  - ${PROJECT_NAME}-sms-messages-${ENVIRONMENT}"
echo "  - ${PROJECT_NAME}-sms-sessions-${ENVIRONMENT}"
echo "  - ${PROJECT_NAME}-sms-consent-${ENVIRONMENT}"
echo "  - ${PROJECT_NAME}-opt-out-tracking-${ENVIRONMENT}"
echo ""

echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo "1. Configure AWS Pinpoint SMS:"
echo "   ./deploy_sms_config_setup.sh $ENVIRONMENT"
echo ""
echo "2. Test the deployment:"
echo "   python test-sms-integration.py --environment $ENVIRONMENT --quick"
echo ""
echo "3. Run comprehensive test:"
echo "   python test-sms-integration.py --environment $ENVIRONMENT"
echo ""
