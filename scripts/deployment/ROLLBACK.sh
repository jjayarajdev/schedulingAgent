#!/bin/bash
################################################################################
# ROLLBACK SCRIPT
# Removes all deployed resources
################################################################################

set -euo pipefail

ENVIRONMENT="${1:-dev}"
AWS_REGION="${2:-us-east-1}"
PROJECT_NAME="scheduling-agent"

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
echo -e "${RED}  WARNING: ROLLBACK - This will delete all resources${NC}"
echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Environment: $ENVIRONMENT"
echo "Region: $AWS_REGION"
echo ""
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Rollback cancelled"
    exit 0
fi

echo ""
echo "Starting rollback..."

# Delete Lambda functions
echo "Deleting Lambda functions..."
for service in scheduling information notes; do
    function_name="${PROJECT_NAME}-${service}-actions"
    aws lambda delete-function --function-name "$function_name" --region "$AWS_REGION" 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Deleted $function_name"
done

# Delete Bedrock agents (via Terraform)
echo "Deleting Bedrock agents..."
cd infrastructure/terraform
terraform destroy -auto-approve -var="environment=${ENVIRONMENT}" 2>/dev/null || true
cd ../..

# Delete IAM roles
echo "Deleting IAM roles..."
for service in scheduling information notes; do
    role_name="${PROJECT_NAME}-${service}-lambda-role-${ENVIRONMENT}"

    # Detach policies
    aws iam detach-role-policy --role-name "$role_name" --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" 2>/dev/null || true

    # Delete inline policies
    for policy in $(aws iam list-role-policies --role-name "$role_name" --query 'PolicyNames' --output text 2>/dev/null); do
        aws iam delete-role-policy --role-name "$role_name" --policy-name "$policy" 2>/dev/null || true
    done

    # Delete role
    aws iam delete-role --role-name "$role_name" 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Deleted $role_name"
done

# Clean up state files
rm -f .deployment_state_*.json
rm -f agent_config.json

echo ""
echo -e "${GREEN}Rollback complete${NC}"
