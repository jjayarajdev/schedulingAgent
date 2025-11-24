#!/usr/bin/env bash
###############################################################################
# Setup Supervisor Agent Collaboration
#
# Run this AFTER creating v1 aliases via AWS Console
# AWS Bedrock requires numbered versions (1, 2, 3...) for agent collaboration
# These can only be created through the AWS Console, not via CLI
###############################################################################

set -euo pipefail

# AWS Profile Support
AWS_PROFILE="${AWS_PROFILE:-}"

# Parse --profile parameter if present
ORIGINAL_ARGS=("$@")
while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            AWS_PROFILE="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done
# Restore original args for other parameter processing
set -- "${ORIGINAL_ARGS[@]}"

# AWS CLI wrapper function
aws_cmd() {
    if [[ -n "$AWS_PROFILE" ]]; then
        aws --profile "$AWS_PROFILE" "$@"
    else
        aws "$@"
    fi
}


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BEDROCK_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID=$(aws_cmd sts get-caller-identity --query Account --output text)

# Load agent IDs from config
CONFIG_FILE="$BEDROCK_DIR/config/agent_ids.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}❌ Error: agent_ids.json not found${NC}"
    echo "Please run DEPLOY.sh first to create agents"
    exit 1
fi

SCHEDULING_AGENT_ID=$(jq -r '.agents.SchedulingAgent.id' "$CONFIG_FILE")
INFORMATION_AGENT_ID=$(jq -r '.agents."pf-information".id' "$CONFIG_FILE")
CHITCHAT_AGENT_ID=$(jq -r '.agents."pf-chitchat".id' "$CONFIG_FILE")
SUPERVISOR_AGENT_ID=$(jq -r '.agents.Supervisor.id' "$CONFIG_FILE")

echo ""
echo "================================================================================"
echo "Setup Supervisor Agent Collaboration"
echo "================================================================================"
echo ""
echo "Region:  $REGION"
echo "Account: $ACCOUNT_ID"
echo ""
echo "Agents:"
echo "  Supervisor:   $SUPERVISOR_AGENT_ID"
echo "  Scheduling:   $SCHEDULING_AGENT_ID"
echo "  Information:  $INFORMATION_AGENT_ID"
echo "  Chitchat:     $CHITCHAT_AGENT_ID"
echo ""
echo "================================================================================"
echo ""

###############################################################################
# Step 1: Get v1 Aliases (Required for Collaboration)
###############################################################################

echo -e "${BLUE}Step 1: Getting v1 Aliases${NC}"
echo ""
echo "  ⚠️  Note: Agent collaboration requires numbered version aliases (v1, v2, etc.)"
echo "     TSTALIASID cannot be used for collaboration"
echo ""

# Get v1 alias IDs for all agents
SCHEDULING_ALIAS_ID=$(aws_cmd bedrock-agent list-agent-aliases \
    --agent-id "$SCHEDULING_AGENT_ID" \
    --region "$REGION" \
    --query "agentAliasSummaries[?agentAliasName=='v1'].agentAliasId" \
    --output text 2>/dev/null)

INFORMATION_ALIAS_ID=$(aws_cmd bedrock-agent list-agent-aliases \
    --agent-id "$INFORMATION_AGENT_ID" \
    --region "$REGION" \
    --query "agentAliasSummaries[?agentAliasName=='v1'].agentAliasId" \
    --output text 2>/dev/null)

CHITCHAT_ALIAS_ID=$(aws_cmd bedrock-agent list-agent-aliases \
    --agent-id "$CHITCHAT_AGENT_ID" \
    --region "$REGION" \
    --query "agentAliasSummaries[?agentAliasName=='v1'].agentAliasId" \
    --output text 2>/dev/null)

# Verify all aliases found
if [[ -z "$SCHEDULING_ALIAS_ID" ]] || [[ -z "$INFORMATION_ALIAS_ID" ]] || [[ -z "$CHITCHAT_ALIAS_ID" ]]; then
    echo -e "${RED}❌ Error: v1 aliases not found for all agents${NC}"
    echo ""
    echo "Please create v1 aliases via AWS Console:"
    echo "  1. Go to each agent (SchedulingAgent, pf-information, pf-chitchat)"
    echo "  2. Click 'Working draft' → 'Create version'"
    echo "  3. Click 'Aliases' tab → 'Create alias'"
    echo "  4. Name: v1, Version: 1"
    echo ""
    [[ -z "$SCHEDULING_ALIAS_ID" ]] && echo "  Missing: SchedulingAgent v1 alias"
    [[ -z "$INFORMATION_ALIAS_ID" ]] && echo "  Missing: InformationAgent v1 alias"
    [[ -z "$CHITCHAT_ALIAS_ID" ]] && echo "  Missing: ChitchatAgent v1 alias"
    exit 1
fi

echo -e "${GREEN}✅ SchedulingAgent v1: $SCHEDULING_ALIAS_ID${NC}"
echo -e "${GREEN}✅ InformationAgent v1: $INFORMATION_ALIAS_ID${NC}"
echo -e "${GREEN}✅ ChitchatAgent v1: $CHITCHAT_ALIAS_ID${NC}"

echo ""

###############################################################################
# Step 2: Build Alias ARNs
###############################################################################

echo -e "${BLUE}Step 2: Building Alias ARNs${NC}"
echo ""

SCHEDULING_ARN="arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent-alias/${SCHEDULING_AGENT_ID}/${SCHEDULING_ALIAS_ID}"
INFORMATION_ARN="arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent-alias/${INFORMATION_AGENT_ID}/${INFORMATION_ALIAS_ID}"
CHITCHAT_ARN="arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent-alias/${CHITCHAT_AGENT_ID}/${CHITCHAT_ALIAS_ID}"

echo "  SchedulingAgent:  $SCHEDULING_ARN"
echo "  InformationAgent: $INFORMATION_ARN"
echo "  ChitchatAgent:    $CHITCHAT_ARN"
echo ""

###############################################################################
# Step 3: Enable Collaboration on Supervisor Agent
###############################################################################

echo -e "${BLUE}Step 3: Enabling Collaboration on Supervisor Agent${NC}"
echo ""

# Check current collaboration status
CURRENT_COLLAB=$(aws_cmd bedrock-agent get-agent \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --region "$REGION" \
    --query 'agent.agentCollaboration' \
    --output text 2>/dev/null)

echo "  Current collaboration mode: $CURRENT_COLLAB"

if [ "$CURRENT_COLLAB" != "SUPERVISOR" ]; then
    echo "  → Enabling SUPERVISOR collaboration mode..."

    # Get current agent details
    AGENT_ROLE=$(aws_cmd bedrock-agent get-agent --agent-id "$SUPERVISOR_AGENT_ID" --region "$REGION" --query 'agent.agentResourceRoleArn' --output text)
    AGENT_MODEL=$(aws_cmd bedrock-agent get-agent --agent-id "$SUPERVISOR_AGENT_ID" --region "$REGION" --query 'agent.foundationModel' --output text)
    AGENT_INSTRUCTION=$(aws_cmd bedrock-agent get-agent --agent-id "$SUPERVISOR_AGENT_ID" --region "$REGION" --query 'agent.instruction' --output text)

    # Update agent to enable collaboration
    aws_cmd bedrock-agent update-agent \
        --agent-id "$SUPERVISOR_AGENT_ID" \
        --agent-name "Supervisor" \
        --agent-resource-role-arn "$AGENT_ROLE" \
        --foundation-model "$AGENT_MODEL" \
        --instruction "$AGENT_INSTRUCTION" \
        --agent-collaboration "SUPERVISOR" \
        --region "$REGION" \
        &>/dev/null && echo -e "  ${GREEN}✅ Collaboration enabled${NC}" || echo -e "  ${RED}❌ Failed to enable collaboration${NC}"
else
    echo -e "  ${GREEN}✅ Collaboration already enabled${NC}"
fi

echo ""

###############################################################################
# Step 4: Ensure Supervisor Has Required IAM Permissions
###############################################################################

echo -e "${BLUE}Step 4: Checking Supervisor IAM Permissions${NC}"
echo ""

# Check if Supervisor role has bedrock:InvokeAgent permission
SUPERVISOR_ROLE_NAME="AmazonBedrockExecutionRoleForAgents_Supervisor"
HAS_INVOKE_PERM=$(aws_cmd iam get-role-policy \
    --role-name "$SUPERVISOR_ROLE_NAME" \
    --policy-name "BedrockModelInvoke" \
    --region "$REGION" \
    --query "PolicyDocument.Statement[?contains(Action, 'bedrock:InvokeAgent')]" \
    --output text 2>/dev/null)

if [[ -z "$HAS_INVOKE_PERM" ]]; then
    echo -e "${YELLOW}⚠️  Supervisor role missing agent invocation permissions${NC}"
    echo "  → Adding bedrock:InvokeAgent and bedrock:GetAgentAlias permissions..."

    # Create updated policy with agent invocation permissions
    cat > /tmp/supervisor-bedrock-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockModelAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:${REGION}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
        "arn:aws:bedrock:*::foundation-model/*",
        "arn:aws:bedrock:${REGION}::inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        "arn:aws:bedrock:*::inference-profile/*",
        "arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:inference-profile/*"
      ]
    },
    {
      "Sid": "BedrockAgentRuntime",
      "Effect": "Allow",
      "Action": [
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel",
        "bedrock:GetInferenceProfile",
        "bedrock:ListInferenceProfiles"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AWSMarketplaceAccess",
      "Effect": "Allow",
      "Action": [
        "aws-marketplace:ViewSubscriptions"
      ],
      "Resource": "*"
    },
    {
      "Sid": "BedrockAgentInvoke",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeAgent",
        "bedrock:GetAgentAlias",
        "bedrock-agent-runtime:InvokeAgent"
      ],
      "Resource": [
        "arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent/*",
        "arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent-alias/*/*"
      ]
    },
    {
      "Sid": "LambdaInvokePermission",
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-scheduling-actions",
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-information-actions",
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-chitchat-actions"
      ]
    }
  ]
}
EOF

    aws_cmd iam put-role-policy \
        --role-name "$SUPERVISOR_ROLE_NAME" \
        --policy-name "BedrockModelInvoke" \
        --policy-document file:///tmp/supervisor-bedrock-policy.json \
        --region "$REGION" \
        &>/dev/null && echo -e "  ${GREEN}✅ IAM permissions updated${NC}" || echo -e "  ${RED}❌ Failed to update IAM permissions${NC}"

    rm -f /tmp/supervisor-bedrock-policy.json

    echo "  → Waiting 10 seconds for IAM propagation..."
    sleep 10
else
    echo -e "  ${GREEN}✅ Supervisor role has required permissions${NC}"
fi

echo ""

###############################################################################
# Step 5: Associate Collaborators with Supervisor
###############################################################################

echo -e "${BLUE}Step 5: Associating Collaborators with Supervisor${NC}"
echo ""

# Associate SchedulingAgent
echo "  • Adding SchedulingAgent as collaborator..."
aws_cmd bedrock-agent associate-agent-collaborator \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --agent-version "DRAFT" \
    --collaborator-name "SchedulingAgent" \
    --agent-descriptor aliasArn="${SCHEDULING_ARN}" \
    --collaboration-instruction "Route queries about projects, appointments, scheduling, availability, and booking to this agent. Examples: 'List my projects', 'Book an appointment', 'What dates are available?'" \
    --relay-conversation-history "TO_COLLABORATOR" \
    --region "$REGION" \
    2>/dev/null && echo -e "    ${GREEN}✅ SchedulingAgent collaboration configured${NC}" || echo -e "    ${YELLOW}⚠️  SchedulingAgent already configured or error occurred${NC}"

# Associate InformationAgent
echo "  • Adding pf-information as collaborator..."
aws_cmd bedrock-agent associate-agent-collaborator \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --agent-version "DRAFT" \
    --collaborator-name "InformationAgent" \
    --agent-descriptor aliasArn="${INFORMATION_ARN}" \
    --collaboration-instruction "Route ONLY weather queries to this agent. This agent specializes in weather forecasts and conditions using Open-Meteo API. Examples: 'What's the weather in New York?', 'Is it going to rain in Miami?', 'Check weather for Tampa, FL', 'What's the weather at my project location?'." \
    --relay-conversation-history "TO_COLLABORATOR" \
    --region "$REGION" \
    2>/dev/null && echo -e "    ${GREEN}✅ InformationAgent collaboration configured${NC}" || echo -e "    ${YELLOW}⚠️  InformationAgent already configured or error occurred${NC}"

# Associate ChitchatAgent
echo "  • Adding pf-chitchat as collaborator..."
aws_cmd bedrock-agent associate-agent-collaborator \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --agent-version "DRAFT" \
    --collaborator-name "ChitchatAgent" \
    --agent-descriptor aliasArn="${CHITCHAT_ARN}" \
    --collaboration-instruction "Route greetings, casual conversation, thank you messages, and general pleasantries to this agent. Examples: 'Hello', 'Hi there', 'Thank you', 'Good morning', 'How are you?'" \
    --relay-conversation-history "TO_COLLABORATOR" \
    --region "$REGION" \
    2>/dev/null && echo -e "    ${GREEN}✅ ChitchatAgent collaboration configured${NC}" || echo -e "    ${YELLOW}⚠️  ChitchatAgent already configured or error occurred${NC}"

echo ""

###############################################################################
# Step 6: Prepare Supervisor
###############################################################################

echo -e "${BLUE}Step 6: Preparing Supervisor Agent${NC}"
echo ""

aws_cmd bedrock-agent prepare-agent \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --region "$REGION" \
    &>/dev/null && echo -e "  ${GREEN}✅ Supervisor prepare initiated${NC}" || echo -e "  ${RED}❌ Failed to prepare Supervisor${NC}"

# Wait for agent to be ready before verification
echo -e "  ${YELLOW}→ Waiting for agent to be ready...${NC}"
MAX_WAIT=60
WAIT_TIME=0
while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    AGENT_STATUS=$(aws_cmd bedrock-agent get-agent \
        --agent-id "$SUPERVISOR_AGENT_ID" \
        --region "$REGION" \
        --query 'agent.agentStatus' \
        --output text 2>/dev/null)

    if [ "$AGENT_STATUS" = "PREPARED" ] || [ "$AGENT_STATUS" = "NOT_PREPARED" ]; then
        echo -e "  ${GREEN}✅ Agent is ready (status: $AGENT_STATUS)${NC}"
        break
    fi

    sleep 3
    WAIT_TIME=$((WAIT_TIME + 3))
    echo -n "."
done
echo ""

if [ $WAIT_TIME -ge $MAX_WAIT ]; then
    echo -e "  ${YELLOW}⚠️  Timeout waiting for agent, proceeding anyway...${NC}"
fi

echo ""

###############################################################################
# Step 7: Verify Collaboration
###############################################################################

echo -e "${BLUE}Step 7: Verifying Collaboration${NC}"
echo ""

COLLABORATORS=$(aws_cmd bedrock-agent list-agent-collaborators \
    --agent-id "$SUPERVISOR_AGENT_ID" \
    --agent-version "DRAFT" \
    --region "$REGION" \
    --query 'agentCollaboratorSummaries[*].collaboratorName' \
    --output text 2>/dev/null || echo "")

if [[ -z "$COLLABORATORS" ]]; then
    echo -e "  ${RED}❌ No collaborators found${NC}"
    exit 1
else
    echo -e "  ${GREEN}✅ Collaborators associated:${NC}"
    for collab in $COLLABORATORS; do
        echo "     • $collab"
    done
fi

###############################################################################
# Step 8: Update Proxy Configuration
###############################################################################

echo -e "${BLUE}Step 8: Updating Proxy Configuration${NC}"
echo ""

PROXY_FILE="$BEDROCK_DIR/testing/ui/pf_proxy.py"

if [[ -f "$PROXY_FILE" ]]; then
    # Update the Supervisor agent ID in the proxy
    sed -i.bak "s/SUPERVISOR_AGENT_ID = '[A-Z0-9]*'/SUPERVISOR_AGENT_ID = '$SUPERVISOR_AGENT_ID'/" "$PROXY_FILE"
    rm -f "${PROXY_FILE}.bak"
    echo -e "  ${GREEN}✅ Proxy configuration updated with Supervisor ID${NC}"
else
    echo -e "  ${YELLOW}⚠️  Proxy file not found: $PROXY_FILE${NC}"
fi

echo ""
echo "================================================================================"
echo -e "${GREEN}✅ Collaboration Setup Complete!${NC}"
echo "================================================================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Test with the web UI:"
echo "   ${GREEN}cd testing/ui && ./launch_auth_demo.sh${NC}"
echo ""
echo "2. Test routing with CLI:"
echo "   ${GREEN}./scripts/test_supervisor_routing.sh${NC}"
echo ""
echo "3. Or invoke directly:"
echo "   ${GREEN}aws bedrock-agent-runtime invoke-agent \\${NC}"
echo "     ${GREEN}--agent-id $SUPERVISOR_AGENT_ID \\${NC}"
echo "     ${GREEN}--agent-alias-id TSTALIASID \\${NC}"
echo "     ${GREEN}--session-id test-\$(date +%s) \\${NC}"
echo "     ${GREEN}--input-text 'List my projects' \\${NC}"
echo "     ${GREEN}/tmp/supervisor_test.txt${NC}"
echo ""
echo "================================================================================"
echo ""
