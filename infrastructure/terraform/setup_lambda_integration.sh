#!/bin/bash
################################################################################
# Lambda Integration Setup Script
################################################################################
# This script automates the complete Lambda integration process:
# 1. Deploys Lambda functions
# 2. Captures Lambda ARNs
# 3. Updates Terraform configuration
# 4. Configures action groups
# 5. Deploys action groups to agents
################################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "================================================================================"
echo "  🔧 Lambda Integration Setup"
echo "================================================================================"
echo ""

# Check we're in the right directory
if [ ! -f "bedrock_agents.tf" ]; then
    echo -e "${RED}❌ Error: bedrock_agents.tf not found${NC}"
    echo "Please run this script from: bedrock/infrastructure/terraform"
    exit 1
fi

# Check if Lambda deployment script exists
LAMBDA_DEPLOY_SCRIPT="../../scripts/deploy_lambda_functions.sh"
if [ ! -f "$LAMBDA_DEPLOY_SCRIPT" ]; then
    echo -e "${RED}❌ Error: Lambda deployment script not found${NC}"
    echo "Expected: $LAMBDA_DEPLOY_SCRIPT"
    exit 1
fi

echo "================================================================================"
echo "  Step 1: Deploy Lambda Functions"
echo "================================================================================"
echo ""

echo "Deploying Lambda functions..."
echo "This will take ~5-10 minutes..."
echo ""

# Deploy Lambda functions and capture output
LAMBDA_OUTPUT=$(bash "$LAMBDA_DEPLOY_SCRIPT" 2>&1 | tee /dev/tty)

# Extract Lambda ARNs from output
echo ""
echo "Extracting Lambda ARNs from deployment output..."

SCHEDULING_ARN=$(echo "$LAMBDA_OUTPUT" | grep -o "scheduling-actions.*arn:aws:lambda[^[:space:]]*" | grep -o "arn:aws:lambda[^[:space:]]*" | head -1)
INFORMATION_ARN=$(echo "$LAMBDA_OUTPUT" | grep -o "information-actions.*arn:aws:lambda[^[:space:]]*" | grep -o "arn:aws:lambda[^[:space:]]*" | head -1)
NOTES_ARN=$(echo "$LAMBDA_OUTPUT" | grep -o "notes-actions.*arn:aws:lambda[^[:space:]]*" | grep -o "arn:aws:lambda[^[:space:]]*" | head -1)

# If grep didn't work, try alternative extraction from AWS CLI
if [ -z "$SCHEDULING_ARN" ]; then
    echo "Attempting to get ARNs from AWS CLI..."
    SCHEDULING_ARN=$(aws lambda get-function --function-name scheduling-actions --query 'Configuration.FunctionArn' --output text 2>/dev/null || echo "")
    INFORMATION_ARN=$(aws lambda get-function --function-name information-actions --query 'Configuration.FunctionArn' --output text 2>/dev/null || echo "")
    NOTES_ARN=$(aws lambda get-function --function-name notes-actions --query 'Configuration.FunctionArn' --output text 2>/dev/null || echo "")
fi

# Validate ARNs
if [ -z "$SCHEDULING_ARN" ] || [ -z "$INFORMATION_ARN" ] || [ -z "$NOTES_ARN" ]; then
    echo ""
    echo -e "${RED}❌ Could not extract all Lambda ARNs${NC}"
    echo ""
    echo "Please provide them manually:"
    echo ""

    if [ -z "$SCHEDULING_ARN" ]; then
        read -p "Scheduling Lambda ARN: " SCHEDULING_ARN
    fi

    if [ -z "$INFORMATION_ARN" ]; then
        read -p "Information Lambda ARN: " INFORMATION_ARN
    fi

    if [ -z "$NOTES_ARN" ]; then
        read -p "Notes Lambda ARN: " NOTES_ARN
    fi
fi

echo ""
echo -e "${GREEN}✅ Lambda ARNs captured:${NC}"
echo "   Scheduling:  $SCHEDULING_ARN"
echo "   Information: $INFORMATION_ARN"
echo "   Notes:       $NOTES_ARN"
echo ""

echo "================================================================================"
echo "  Step 2: Update Terraform Configuration"
echo "================================================================================"
echo ""

# Add Lambda variables to variables.tf if not already present
echo "Updating variables.tf..."

if ! grep -q "variable \"scheduling_lambda_arn\"" variables.tf 2>/dev/null; then
    cat >> variables.tf <<'EOF'

# ==============================================================================
# Lambda Function ARNs
# ==============================================================================

variable "scheduling_lambda_arn" {
  description = "ARN of the scheduling Lambda function"
  type        = string
  default     = ""
}

variable "information_lambda_arn" {
  description = "ARN of the information Lambda function"
  type        = string
  default     = ""
}

variable "notes_lambda_arn" {
  description = "ARN of the notes Lambda function"
  type        = string
  default     = ""
}
EOF
    echo -e "${GREEN}✅ Added Lambda variables to variables.tf${NC}"
else
    echo -e "${BLUE}ℹ️  Lambda variables already exist in variables.tf${NC}"
fi

# Create/update terraform.tfvars with Lambda ARNs
echo ""
echo "Creating terraform.tfvars with Lambda ARNs..."

cat > terraform.tfvars <<EOF
# ==============================================================================
# Lambda Function ARNs
# ==============================================================================
# Auto-generated by setup_lambda_integration.sh
# Date: $(date)

scheduling_lambda_arn  = "$SCHEDULING_ARN"
information_lambda_arn = "$INFORMATION_ARN"
notes_lambda_arn       = "$NOTES_ARN"
EOF

echo -e "${GREEN}✅ Created terraform.tfvars${NC}"
echo ""

echo "================================================================================"
echo "  Step 3: Configure Action Groups"
echo "================================================================================"
echo ""

echo "Running action groups configuration script..."
python3 configure_action_groups.py

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Action groups configuration failed${NC}"
    exit 1
fi

echo ""
echo "================================================================================"
echo "  Step 4: Deploy Action Groups"
echo "================================================================================"
echo ""

echo "Validating Terraform configuration..."
terraform validate

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Terraform validation failed${NC}"
    exit 1
fi

echo ""
echo "Planning Terraform changes..."
terraform plan -out=tfplan

echo ""
read -p "Apply these changes? (yes/no): " confirm

if [[ "$confirm" != "yes" ]]; then
    echo "Deployment cancelled."
    rm -f tfplan
    exit 0
fi

echo ""
echo "Applying Terraform changes..."
terraform apply tfplan
rm -f tfplan

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Terraform apply failed${NC}"
    exit 1
fi

echo ""
echo "================================================================================"
echo "  Step 5: Prepare Agents"
echo "================================================================================"
echo ""

echo "Re-preparing agents after adding action groups..."
echo "This ensures agents are in PREPARED state with new action groups..."
echo ""

./prepare_agents.sh

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Agent preparation failed${NC}"
    exit 1
fi

echo ""
echo "================================================================================"
echo "  Step 6: Final Terraform Apply"
echo "================================================================================"
echo ""

echo "Running final Terraform apply to ensure everything is synchronized..."
terraform apply -auto-approve

echo ""
echo "================================================================================"
echo "  ✅ Lambda Integration Complete!"
echo "================================================================================"
echo ""

echo "Summary:"
echo "  ✅ Lambda functions deployed"
echo "  ✅ Action groups configured"
echo "  ✅ Agents prepared with action groups"
echo "  ✅ Infrastructure synchronized"
echo ""

echo "Verification:"
echo ""

# Get supervisor agent ID
SUPERVISOR_ID=$(terraform output -raw supervisor_agent_id 2>/dev/null)

# List action groups for each agent
echo "Action Groups per Agent:"
echo ""

for agent_name in scheduling information notes; do
    AGENT_ID=$(terraform output -raw ${agent_name}_agent_id 2>/dev/null)
    if [ -n "$AGENT_ID" ]; then
        echo "  ${agent_name} agent:"
        aws bedrock-agent list-agent-action-groups \
            --agent-id "$AGENT_ID" \
            --agent-version DRAFT \
            --region us-east-1 \
            --query 'actionGroupSummaries[*].[actionGroupName,actionGroupState]' \
            --output text 2>/dev/null | sed 's/^/    /'
        echo ""
    fi
done

echo "================================================================================"
echo "  Next Steps"
echo "================================================================================"
echo ""
echo "1. Test the integration:"
echo "   cd ../../tests"
echo "   python3 comprehensive_test.py"
echo ""
echo "2. Verify Lambda invocations:"
echo "   aws logs tail /aws/lambda/scheduling-actions --follow"
echo ""
echo "3. Monitor agent behavior:"
echo "   aws logs tail /aws/bedrock/agents/$SUPERVISOR_ID --follow"
echo ""
echo -e "${GREEN}🎉 Your agents can now call Lambda functions!${NC}"
echo ""
