#!/usr/bin/env bash
###############################################################################
# Find v1 Alias IDs for Collaborator Agents
# Run this AFTER creating v1 aliases in AWS Console
###############################################################################

set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Load agent IDs from config
CONFIG_FILE="../config/agent_ids.json"

if [ -f "$CONFIG_FILE" ]; then
  SCHEDULING_ID=$(jq -r '.agents.SchedulingAgent.id' "$CONFIG_FILE")
  INFORMATION_ID=$(jq -r '.agents."pf-information".id' "$CONFIG_FILE")
  CHITCHAT_ID=$(jq -r '.agents."pf-chitchat".id' "$CONFIG_FILE")
else
  # Fallback to manual input
  SCHEDULING_ID="${SCHEDULING_AGENT_ID:-XWYHPGTXFC}"
  INFORMATION_ID="${INFORMATION_AGENT_ID:-YPHTBWTHU8}"
  CHITCHAT_ID="${CHITCHAT_AGENT_ID:-2VRYB01FGD}"
fi

echo "================================================================================"
echo "Finding v1 Alias IDs for Collaborator Agents"
echo "================================================================================"
echo ""
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo ""
echo "Agents:"
echo "  Scheduling:  $SCHEDULING_ID"
echo "  Information: $INFORMATION_ID"
echo "  Chitchat:    $CHITCHAT_ID"
echo ""
echo "================================================================================"
echo ""

# Function to get v1 alias info
get_v1_alias() {
  local agent_id=$1
  local agent_name=$2

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "$agent_name Agent ($agent_id)"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  # Get v1 alias details
  ALIAS_INFO=$(aws bedrock-agent list-agent-aliases \
    --agent-id "$agent_id" \
    --region "$REGION" \
    --query 'agentAliasSummaries[?agentAliasName==`v1`]' \
    --output json)

  # Check if v1 alias exists
  if [ "$(echo "$ALIAS_INFO" | jq length)" -eq 0 ]; then
    echo "❌ No v1 alias found"
    echo ""
    echo "Next steps:"
    echo "  1. Go to AWS Bedrock Console → Agents"
    echo "  2. Click on agent: $agent_name ($agent_id)"
    echo "  3. Create Version 1 from DRAFT"
    echo "  4. Create Alias 'v1' pointing to Version 1"
    echo ""
    return 1
  fi

  # Extract details
  ALIAS_ID=$(echo "$ALIAS_INFO" | jq -r '.[0].agentAliasId')
  ALIAS_ARN=$(echo "$ALIAS_INFO" | jq -r '.[0].agentAliasArn')
  ROUTING_CONFIG=$(echo "$ALIAS_INFO" | jq -r '.[0].routingConfiguration[0].agentVersion // "unknown"')
  UPDATED_AT=$(echo "$ALIAS_INFO" | jq -r '.[0].updatedAt')

  echo "✅ v1 alias found"
  echo ""
  echo "Alias ID:  $ALIAS_ID"
  echo "Alias ARN: $ALIAS_ARN"
  echo "Points to: Version $ROUTING_CONFIG"
  echo "Updated:   $UPDATED_AT"
  echo ""

  # Store for Terraform update command
  echo "TERRAFORM_UPDATE_${agent_name^^}=\"$ALIAS_ID\""
  echo ""
}

# Get v1 alias for each agent
get_v1_alias "$SCHEDULING_ID" "Scheduling"
SCHED_RESULT=$?

get_v1_alias "$INFORMATION_ID" "Information"
INFO_RESULT=$?

get_v1_alias "$CHITCHAT_ID" "Chitchat"
CHIT_RESULT=$?

echo "================================================================================"
echo ""

# Check if all aliases exist
if [ $SCHED_RESULT -eq 0 ] && [ $INFO_RESULT -eq 0 ] && [ $CHIT_RESULT -eq 0 ]; then
  echo "✅ All v1 aliases found!"
  echo ""
  echo "Next Steps:"
  echo ""
  echo "1. Update Terraform collaboration.tf with the alias IDs above"
  echo ""
  echo "2. Replace the placeholder ARNs in infrastructure/terraform/collaboration.tf:"
  echo "   - Find: 'V1_ALIAS_ID_HERE'"
  echo "   - Replace with actual alias IDs from above"
  echo ""
  echo "3. Apply Terraform:"
  echo "   cd infrastructure/terraform"
  echo "   terraform plan"
  echo "   terraform apply"
  echo ""
  echo "4. Verify collaboration:"
  echo "   ./scripts/verify_collaborators.sh"
  echo ""
else
  echo "⚠️  Some v1 aliases are missing"
  echo ""
  echo "Follow: ../ENABLE_COLLABORATION.md for instructions on creating v1 aliases"
  echo ""
  exit 1
fi
