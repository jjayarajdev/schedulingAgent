#!/bin/bash
#
# SMS Integration Deployment Script
# Deploys SNS topic, Lambda function, DynamoDB tables for SMS processing
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

# Navigate to Terraform directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/../infrastructure/terraform/sms"

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

log_success "Deployment complete!"

# Get outputs
LAMBDA_NAME="${PROJECT_NAME}-sms-inbound-${ENVIRONMENT}"

echo ""
echo "Deployed Resources:"
echo "  Lambda: $LAMBDA_NAME"
echo "  SNS Topic: ${PROJECT_NAME}-sms-inbound-${ENVIRONMENT}"
echo "  DynamoDB Tables: ${PROJECT_NAME}-sms-{messages,sessions,consent,opt-out-tracking}-${ENVIRONMENT}"
echo ""

log_info "Test the deployment:"
echo "  cd $SCRIPT_DIR"
echo "  python test-sms-quick.py --environment $ENVIRONMENT"
echo ""
