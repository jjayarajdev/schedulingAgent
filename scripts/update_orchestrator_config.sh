#!/bin/bash

###############################################################################
# update_orchestrator_config.sh
#
# Updates the Orchestrator Lambda environment variables with:
# - Current agent IDs from AWS
# - Redis endpoint (if available)
# - Routing configuration
#
# Usage:
#   ./update_orchestrator_config.sh
#   ./update_orchestrator_config.sh --redis-endpoint pf-sessions-dev.xxxxx.cache.amazonaws.com
###############################################################################

set -e

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

REGION="${AWS_REGION:-us-east-1}"
ENV="${BEDROCK_ENV:-dev}"
REDIS_ENDPOINT_ARG=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --redis-endpoint)
            REDIS_ENDPOINT_ARG="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--redis-endpoint ENDPOINT]"
            exit 1
            ;;
    esac
done

echo ""
echo "=========================================="
echo "Update Orchestrator Lambda Configuration"
echo "=========================================="
echo ""

# Check if orchestrator Lambda exists
if ! aws_cmd lambda get-function --function-name pf-orchestrator --region "$REGION" &>/dev/null; then
    echo "❌ Error: pf-orchestrator Lambda not found"
    echo "   Run ./DEPLOY.sh first to create the Lambda"
    exit 1
fi

# Get AWS Account ID for IAM policy
ACCOUNT_ID=$(aws_cmd sts get-caller-identity --query Account --output text)

# Update IAM role policy to include inference-profile support
echo "→ Updating IAM role policy..."
ORCHESTRATOR_ROLE_NAME="pf-orchestrator-role-${ENV}"

if aws_cmd iam get-role --role-name "$ORCHESTRATOR_ROLE_NAME" --region "$REGION" &>/dev/null; then
    cat > /tmp/orchestrator-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockRuntimeAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:${REGION}::foundation-model/*",
        "arn:aws:bedrock:*::foundation-model/*",
        "arn:aws:bedrock:${REGION}::inference-profile/*",
        "arn:aws:bedrock:*::inference-profile/*",
        "arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:inference-profile/*"
      ]
    },
    {
      "Sid": "BedrockAgentInvokeAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeAgent",
        "bedrock-agent-runtime:InvokeAgent"
      ],
      "Resource": [
        "arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent/*",
        "arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent-alias/*/*",
        "arn:aws:bedrock:*:*:agent/*",
        "arn:aws:bedrock:*:*:agent-alias/*/*"
      ]
    },
    {
      "Sid": "BedrockGetAgentInfo",
      "Effect": "Allow",
      "Action": [
        "bedrock:GetAgent",
        "bedrock:GetAgentAlias",
        "bedrock:ListAgents",
        "bedrock:ListAgentAliases"
      ],
      "Resource": "*"
    },
    {
      "Sid": "LambdaInvokePermission",
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-scheduling-actions",
        "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:pf-information-actions"
      ]
    }
  ]
}
EOF

    aws_cmd iam put-role-policy \
        --role-name "$ORCHESTRATOR_ROLE_NAME" \
        --policy-name "OrchestratorPermissions" \
        --policy-document file:///tmp/orchestrator-policy.json \
        --region "$REGION" \
        &>/dev/null

    rm -f /tmp/orchestrator-policy.json
    echo "  ✅ IAM policy updated with inference-profile support"
else
    echo "  ⚠️  Warning: IAM role $ORCHESTRATOR_ROLE_NAME not found"
fi

echo ""

# Load agent IDs from config
CONFIG_FILE="$BEDROCK_DIR/config/agent_ids.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "⚠️  Warning: agent_ids.json not found"
    echo "   Fetching agent IDs from AWS..."

    # Fetch from AWS
    SUPERVISOR_AGENT_ID=$(aws_cmd bedrock-agent list-agents --region "$REGION" --query 'agentSummaries[?agentName==`Supervisor`].agentId' --output text 2>/dev/null || echo "")
    SCHEDULING_AGENT_ID=$(aws_cmd bedrock-agent list-agents --region "$REGION" --query 'agentSummaries[?agentName==`SchedulingAgent`].agentId' --output text 2>/dev/null || echo "")
    INFORMATION_AGENT_ID=$(aws_cmd bedrock-agent list-agents --region "$REGION" --query 'agentSummaries[?agentName==`pf-information`].agentId' --output text 2>/dev/null || echo "")
    CHITCHAT_AGENT_ID=$(aws_cmd bedrock-agent list-agents --region "$REGION" --query 'agentSummaries[?agentName==`pf-chitchat`].agentId' --output text 2>/dev/null || echo "")
else
    # Load from config file
    SUPERVISOR_AGENT_ID=$(jq -r '.agents.Supervisor.id' "$CONFIG_FILE" 2>/dev/null || echo "")
    SCHEDULING_AGENT_ID=$(jq -r '.agents.SchedulingAgent.id' "$CONFIG_FILE" 2>/dev/null || echo "")
    INFORMATION_AGENT_ID=$(jq -r '.agents."pf-information".id' "$CONFIG_FILE" 2>/dev/null || echo "")
    CHITCHAT_AGENT_ID=$(jq -r '.agents."pf-chitchat".id' "$CONFIG_FILE" 2>/dev/null || echo "")
fi

# Validate agent IDs
if [[ -z "$SUPERVISOR_AGENT_ID" ]] || [[ -z "$SCHEDULING_AGENT_ID" ]] || [[ -z "$INFORMATION_AGENT_ID" ]] || [[ -z "$CHITCHAT_AGENT_ID" ]]; then
    echo "❌ Error: Could not find all agent IDs"
    echo "   Run ./DEPLOY.sh to create agents first"
    exit 1
fi

echo "Agent IDs:"
echo "  • Supervisor:   $SUPERVISOR_AGENT_ID"
echo "  • Scheduling:   $SCHEDULING_AGENT_ID"
echo "  • Information:  $INFORMATION_AGENT_ID"
echo "  • Chitchat:     $CHITCHAT_AGENT_ID"
echo ""

# Check for Redis endpoint
REDIS_ENDPOINT=""

if [[ -n "$REDIS_ENDPOINT_ARG" ]]; then
    # Use provided Redis endpoint
    REDIS_ENDPOINT="$REDIS_ENDPOINT_ARG"
    echo "Using provided Redis endpoint: $REDIS_ENDPOINT"
else
    # Try to find Redis cluster
    if aws_cmd elasticache describe-cache-clusters --cache-cluster-id "pf-sessions-${ENV}" --region "$REGION" &>/dev/null; then
        REDIS_STATUS=$(aws_cmd elasticache describe-cache-clusters \
            --cache-cluster-id "pf-sessions-${ENV}" \
            --region "$REGION" \
            --query 'CacheClusters[0].CacheClusterStatus' \
            --output text 2>/dev/null || echo "")

        if [[ "$REDIS_STATUS" == "available" ]]; then
            REDIS_ENDPOINT=$(aws_cmd elasticache describe-cache-clusters \
                --cache-cluster-id "pf-sessions-${ENV}" \
                --region "$REGION" \
                --show-cache-node-info \
                --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' \
                --output text 2>/dev/null || echo "")
            echo "Found Redis endpoint: $REDIS_ENDPOINT"
        else
            echo "⚠️  Redis cluster exists but is not available (status: $REDIS_STATUS)"
        fi
    else
        echo "ℹ️  No Redis cluster found (pf-sessions-${ENV})"
    fi
fi

echo ""

# Wait for any pending Lambda updates
echo "→ Checking Lambda state..."
for i in {1..12}; do
    LAMBDA_STATUS=$(aws_cmd lambda get-function-configuration \
        --function-name pf-orchestrator \
        --region "$REGION" \
        --query 'LastUpdateStatus' \
        --output text 2>/dev/null || echo "")

    if [[ "$LAMBDA_STATUS" == "Successful" ]]; then
        break
    fi

    if [[ $i -eq 12 ]]; then
        echo "⚠️  Lambda update in progress, attempting configuration anyway..."
        break
    fi

    echo "  Waiting for Lambda to be ready... (attempt $i/12)"
    sleep 5
done

# Create environment configuration JSON
echo "→ Creating environment configuration..."

cat > /tmp/orchestrator-env.json <<EOF
{
  "Variables": {
    "SUPERVISOR_AGENT_ID": "$SUPERVISOR_AGENT_ID",
    "SCHEDULING_AGENT_ID": "$SCHEDULING_AGENT_ID",
    "INFORMATION_AGENT_ID": "$INFORMATION_AGENT_ID",
    "CHITCHAT_AGENT_ID": "$CHITCHAT_AGENT_ID",
    "SCHEDULING_LAMBDA_NAME": "pf-scheduling-actions",
    "INFORMATION_LAMBDA_NAME": "pf-information-actions",
    "USE_SUPERVISOR": "true",
    "ALLOW_DIRECT_LAMBDA": "true",
    "ROUTING_METHOD": "hybrid",
    "REDIS_PORT": "6379",
    "REDIS_SSL": "false"$(if [[ -n "$REDIS_ENDPOINT" ]]; then echo ",
    \"REDIS_ENDPOINT\": \"$REDIS_ENDPOINT\""; fi)
  }
}
EOF

echo "→ Updating Orchestrator Lambda environment variables..."

if aws_cmd lambda update-function-configuration \
    --function-name pf-orchestrator \
    --region "$REGION" \
    --environment file:///tmp/orchestrator-env.json \
    &>/dev/null; then

    echo ""
    echo "✅ Orchestrator Lambda configured successfully"
    echo ""
    echo "Configuration:"
    echo "  • Agent IDs: ✅ Updated"
    echo "  • Lambda names: ✅ Set"
    echo "  • Routing mode: supervisor (All requests via Supervisor agent)"

    if [[ -n "$REDIS_ENDPOINT" ]]; then
        echo "  • Redis endpoint: ✅ $REDIS_ENDPOINT"
    else
        echo "  • Redis endpoint: ⚠️  Not configured"
        echo ""
        echo "To add Redis later:"
        echo "  1. Deploy Redis: ./deploy_redis.sh"
        echo "  2. Re-run this script: ./update_orchestrator_config.sh"
    fi
else
    echo ""
    echo "❌ Failed to update Orchestrator Lambda configuration"
    echo ""
    echo "Troubleshooting:"
    echo "  • Check Lambda exists: aws_cmd lambda get-function --function-name pf-orchestrator --region $REGION"
    echo "  • Check IAM permissions for lambda:UpdateFunctionConfiguration"
    echo "  • Wait 60 seconds and try again (Lambda may be updating)"
    exit 1
fi

# Clean up
rm -f /tmp/orchestrator-env.json

echo ""
echo "=========================================="
echo "Configuration Complete!"
echo "=========================================="
echo ""
