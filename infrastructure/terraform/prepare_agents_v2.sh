#!/bin/bash
set -e

###############################################################################
# Prepare Agents Script (v2 - Terraform Output Based)
# Purpose: Prepare all agents, create aliases, and add action groups
# Uses: Terraform outputs instead of hardcoded agent IDs
# Created: October 21, 2025
###############################################################################

REGION="us-east-1"
ACCOUNT_ID="618048437522"
PREFIX="pf"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     Preparing Agents, Creating Aliases & Action Groups      ║"
echo "║              (Using Terraform Outputs)                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# Get agent IDs from Terraform outputs
echo ""
echo "📊 Fetching agent IDs from Terraform..."
SCHEDULING_AGENT=$(terraform output -raw scheduling_agent_id 2>/dev/null)
INFORMATION_AGENT=$(terraform output -raw information_agent_id 2>/dev/null)
NOTES_AGENT=$(terraform output -raw notes_agent_id 2>/dev/null)
CHITCHAT_AGENT=$(terraform output -raw chitchat_agent_id 2>/dev/null)
SUPERVISOR_AGENT=$(terraform output -raw supervisor_agent_id 2>/dev/null)

# Validate all IDs were retrieved
if [[ -z "$SCHEDULING_AGENT" || -z "$INFORMATION_AGENT" || -z "$NOTES_AGENT" || -z "$CHITCHAT_AGENT" || -z "$SUPERVISOR_AGENT" ]]; then
    echo "❌ Error: Failed to retrieve agent IDs from Terraform outputs"
    echo "   Make sure you've run 'terraform apply' first"
    exit 1
fi

echo "✓ Agent IDs retrieved:"
echo "  Scheduling:   $SCHEDULING_AGENT"
echo "  Information:  $INFORMATION_AGENT"
echo "  Notes:        $NOTES_AGENT"
echo "  Chitchat:     $CHITCHAT_AGENT"
echo "  Supervisor:   $SUPERVISOR_AGENT"

# Lambda ARNs
SCHEDULING_LAMBDA="arn:aws:lambda:$REGION:$ACCOUNT_ID:function:${PREFIX}-scheduling-actions"
INFORMATION_LAMBDA="arn:aws:lambda:$REGION:$ACCOUNT_ID:function:${PREFIX}-information-actions"
NOTES_LAMBDA="arn:aws:lambda:$REGION:$ACCOUNT_ID:function:${PREFIX}-notes-actions"

# S3 bucket
SCHEMA_BUCKET=$(terraform output -raw agent_schemas_bucket 2>/dev/null)
if [[ -z "$SCHEMA_BUCKET" ]]; then
    SCHEMA_BUCKET="${PREFIX}-schemas-dev-${ACCOUNT_ID}"
    echo "⚠️  Using default S3 bucket: $SCHEMA_BUCKET"
else
    echo "✓ S3 bucket: $SCHEMA_BUCKET"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Step 1: Prepare All Agents"
echo "═══════════════════════════════════════════════════════════════"

echo "🔧 Preparing Scheduling agent..."
aws bedrock-agent prepare-agent --agent-id "$SCHEDULING_AGENT" --region "$REGION" > /dev/null || true

echo "🔧 Preparing Information agent..."
aws bedrock-agent prepare-agent --agent-id "$INFORMATION_AGENT" --region "$REGION" > /dev/null || true

echo "🔧 Preparing Notes agent..."
aws bedrock-agent prepare-agent --agent-id "$NOTES_AGENT" --region "$REGION" > /dev/null || true

echo "🔧 Preparing Chitchat agent..."
aws bedrock-agent prepare-agent --agent-id "$CHITCHAT_AGENT" --region "$REGION" > /dev/null || true

echo "🔧 Preparing Supervisor agent..."
aws bedrock-agent prepare-agent --agent-id "$SUPERVISOR_AGENT" --region "$REGION" > /dev/null || true

echo "✓ All agents prepared"
echo ""
echo "⏳ Waiting 20 seconds for agents to be ready..."
sleep 20

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Step 2: Create Aliases"
echo "═══════════════════════════════════════════════════════════════"

echo "🏷️  Creating alias for Scheduling agent..."
SCHEDULING_ALIAS=$(aws bedrock-agent create-agent-alias \
    --agent-id "$SCHEDULING_AGENT" \
    --agent-alias-name "v1" \
    --region "$REGION" \
    --query 'agentAliasId' --output text 2>&1) || SCHEDULING_ALIAS="existing"

echo "🏷️  Creating alias for Information agent..."
INFORMATION_ALIAS=$(aws bedrock-agent create-agent-alias \
    --agent-id "$INFORMATION_AGENT" \
    --agent-alias-name "v1" \
    --region "$REGION" \
    --query 'agentAliasId' --output text 2>&1) || INFORMATION_ALIAS="existing"

echo "🏷️  Creating alias for Notes agent..."
NOTES_ALIAS=$(aws bedrock-agent create-agent-alias \
    --agent-id "$NOTES_AGENT" \
    --agent-alias-name "v1" \
    --region "$REGION" \
    --query 'agentAliasId' --output text 2>&1) || NOTES_ALIAS="existing"

echo "🏷️  Creating alias for Chitchat agent..."
CHITCHAT_ALIAS=$(aws bedrock-agent create-agent-alias \
    --agent-id "$CHITCHAT_AGENT" \
    --agent-alias-name "v1" \
    --region "$REGION" \
    --query 'agentAliasId' --output text 2>&1) || CHITCHAT_ALIAS="existing"

echo "🏷️  Creating alias for Supervisor agent..."
SUPERVISOR_ALIAS=$(aws bedrock-agent create-agent-alias \
    --agent-id "$SUPERVISOR_AGENT" \
    --agent-alias-name "v1" \
    --region "$REGION" \
    --query 'agentAliasId' --output text 2>&1) || SUPERVISOR_ALIAS="existing"

echo "✓ All aliases created"
echo ""
echo "⏳ Waiting 10 seconds for aliases..."
sleep 10

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Step 3: Add Action Groups to Specialist Agents"
echo "═══════════════════════════════════════════════════════════════"
echo "Note: Skipping supervisor (supervisors can't have action groups)"
echo ""

echo "📋 Adding action group to Scheduling agent..."
aws bedrock-agent create-agent-action-group \
    --agent-id "$SCHEDULING_AGENT" \
    --agent-version "DRAFT" \
    --action-group-name "scheduling-actions" \
    --action-group-executor "lambda=$SCHEDULING_LAMBDA" \
    --api-schema "s3={s3BucketName=$SCHEMA_BUCKET,s3ObjectKey=scheduling_actions.json}" \
    --region "$REGION" > /dev/null 2>&1 && echo "✓ Scheduling action group added" || echo "  (May already exist)"

echo "📋 Adding action group to Information agent..."
aws bedrock-agent create-agent-action-group \
    --agent-id "$INFORMATION_AGENT" \
    --agent-version "DRAFT" \
    --action-group-name "information-actions" \
    --action-group-executor "lambda=$INFORMATION_LAMBDA" \
    --api-schema "s3={s3BucketName=$SCHEMA_BUCKET,s3ObjectKey=information_actions.json}" \
    --region "$REGION" > /dev/null 2>&1 && echo "✓ Information action group added" || echo "  (May already exist)"

echo "📋 Adding action group to Notes agent..."
aws bedrock-agent create-agent-action-group \
    --agent-id "$NOTES_AGENT" \
    --agent-version "DRAFT" \
    --action-group-name "notes-actions" \
    --action-group-executor "lambda=$NOTES_LAMBDA" \
    --api-schema "s3={s3BucketName=$SCHEMA_BUCKET,s3ObjectKey=notes_actions.json}" \
    --region "$REGION" > /dev/null 2>&1 && echo "✓ Notes action group added" || echo "  (May already exist)"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Step 4: Re-prepare Agents with Action Groups"
echo "═══════════════════════════════════════════════════════════════"

echo "🔧 Re-preparing Scheduling agent..."
aws bedrock-agent prepare-agent --agent-id "$SCHEDULING_AGENT" --region "$REGION" > /dev/null

echo "🔧 Re-preparing Information agent..."
aws bedrock-agent prepare-agent --agent-id "$INFORMATION_AGENT" --region "$REGION" > /dev/null

echo "🔧 Re-preparing Notes agent..."
aws bedrock-agent prepare-agent --agent-id "$NOTES_AGENT" --region "$REGION" > /dev/null

echo "✓ All agents re-prepared"

echo ""
echo "⏳ Waiting for final preparation..."
sleep 15

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                 Setup Complete!                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Fetching final alias IDs..."

SCHEDULING_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "$SCHEDULING_AGENT" --region "$REGION" --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' --output text)
INFORMATION_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "$INFORMATION_AGENT" --region "$REGION" --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' --output text)
NOTES_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "$NOTES_AGENT" --region "$REGION" --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' --output text)
CHITCHAT_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "$CHITCHAT_AGENT" --region "$REGION" --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' --output text)
SUPERVISOR_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "$SUPERVISOR_AGENT" --region "$REGION" --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' --output text)

echo ""
echo "Agent IDs and Aliases:"
echo "  Scheduling:   $SCHEDULING_AGENT / $SCHEDULING_ALIAS"
echo "  Information:  $INFORMATION_AGENT / $INFORMATION_ALIAS"
echo "  Notes:        $NOTES_AGENT / $NOTES_ALIAS"
echo "  Chitchat:     $CHITCHAT_AGENT / $CHITCHAT_ALIAS"
echo "  Supervisor:   $SUPERVISOR_AGENT / $SUPERVISOR_ALIAS"
echo ""
echo "Next step: Run setup_supervisor_collaborators_v2.sh"
echo ""
