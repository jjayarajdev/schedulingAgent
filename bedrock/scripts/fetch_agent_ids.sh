#!/bin/bash

# Script to automatically fetch Bedrock Agent IDs and update environment-specific config files
# Usage: ./fetch_agent_ids.sh [dev|staging|prod]

set -e

ENVIRONMENT=${1:-dev}
REGION=${AWS_REGION:-us-east-1}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"
CONFIG_FILE="$BACKEND_DIR/agent_config.$ENVIRONMENT.json"

echo "=========================================="
echo "Fetching Agent IDs for: $ENVIRONMENT"
echo "Region: $REGION"
echo "=========================================="
echo ""

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Config file not found: $CONFIG_FILE"
    echo "Please create it from the template first"
    exit 1
fi

# Function to list all agents and extract IDs by name pattern
fetch_agent_ids() {
    echo "📡 Fetching all Bedrock agents..."

    # List all agents
    agents_json=$(aws bedrock-agent list-agents --region $REGION --output json)

    if [ -z "$agents_json" ]; then
        echo "❌ Failed to fetch agents"
        exit 1
    fi

    echo "✅ Found agents in AWS"
    echo ""

    # Extract agent IDs based on name patterns
    # Adjust these patterns to match your agent naming convention
    SUPERVISOR_ID=$(echo "$agents_json" | jq -r '.agentSummaries[] | select(.agentName | contains("Supervisor") or contains("supervisor")) | .agentId' | head -1)
    SCHEDULING_ID=$(echo "$agents_json" | jq -r '.agentSummaries[] | select(.agentName | contains("Scheduling") or contains("scheduling")) | .agentId' | head -1)
    INFORMATION_ID=$(echo "$agents_json" | jq -r '.agentSummaries[] | select(.agentName | contains("Information") or contains("information")) | .agentId' | head -1)
    NOTES_ID=$(echo "$agents_json" | jq -r '.agentSummaries[] | select(.agentName | contains("Notes") or contains("notes")) | .agentId' | head -1)
    CHITCHAT_ID=$(echo "$agents_json" | jq -r '.agentSummaries[] | select(.agentName | contains("Chitchat") or contains("chitchat") or contains("ChitChat")) | .agentId' | head -1)

    echo "Found Agent IDs:"
    echo "  Supervisor:   ${SUPERVISOR_ID:-NOT FOUND}"
    echo "  Scheduling:   ${SCHEDULING_ID:-NOT FOUND}"
    echo "  Information:  ${INFORMATION_ID:-NOT FOUND}"
    echo "  Notes:        ${NOTES_ID:-NOT FOUND}"
    echo "  Chitchat:     ${CHITCHAT_ID:-NOT FOUND}"
    echo ""
}

# Function to fetch alias ID for an agent
fetch_alias_id() {
    local agent_id=$1
    local alias_name=${2:-TSTALIASID}  # Default to TSTALIASID for dev

    if [ -z "$agent_id" ]; then
        echo ""
        return
    fi

    # List aliases for the agent
    alias_id=$(aws bedrock-agent list-agent-aliases \
        --agent-id "$agent_id" \
        --region $REGION \
        --output json | jq -r ".agentAliasSummaries[] | select(.agentAliasName == \"$alias_name\") | .agentAliasId" | head -1)

    echo "${alias_id:-TSTALIASID}"
}

# Fetch agent IDs
fetch_agent_ids

# Determine alias name based on environment
case $ENVIRONMENT in
    dev)
        ALIAS_NAME="TSTALIASID"
        ;;
    staging)
        ALIAS_NAME="staging"
        ;;
    prod)
        ALIAS_NAME="prod"
        ;;
    *)
        ALIAS_NAME="TSTALIASID"
        ;;
esac

echo "🔍 Fetching alias IDs (alias name: $ALIAS_NAME)..."

# Fetch alias IDs for each agent
if [ -n "$SUPERVISOR_ID" ]; then
    SUPERVISOR_ALIAS=$(fetch_alias_id "$SUPERVISOR_ID" "$ALIAS_NAME")
    echo "  Supervisor Alias: $SUPERVISOR_ALIAS"
fi

if [ -n "$SCHEDULING_ID" ]; then
    SCHEDULING_ALIAS=$(fetch_alias_id "$SCHEDULING_ID" "$ALIAS_NAME")
    echo "  Scheduling Alias: $SCHEDULING_ALIAS"
fi

if [ -n "$INFORMATION_ID" ]; then
    INFORMATION_ALIAS=$(fetch_alias_id "$INFORMATION_ID" "$ALIAS_NAME")
    echo "  Information Alias: $INFORMATION_ALIAS"
fi

if [ -n "$NOTES_ID" ]; then
    NOTES_ALIAS=$(fetch_alias_id "$NOTES_ID" "$ALIAS_NAME")
    echo "  Notes Alias: $NOTES_ALIAS"
fi

if [ -n "$CHITCHAT_ID" ]; then
    CHITCHAT_ALIAS=$(fetch_alias_id "$CHITCHAT_ID" "$ALIAS_NAME")
    echo "  Chitchat Alias: $CHITCHAT_ALIAS"
fi

echo ""
echo "📝 Updating config file: $CONFIG_FILE"

# Update the config file using jq
tmp_file=$(mktemp)

jq --arg supervisor_id "${SUPERVISOR_ID:-REPLACE_WITH_SUPERVISOR_ID}" \
   --arg supervisor_alias "${SUPERVISOR_ALIAS:-TSTALIASID}" \
   --arg scheduling_id "${SCHEDULING_ID:-REPLACE_WITH_SCHEDULING_AGENT_ID}" \
   --arg scheduling_alias "${SCHEDULING_ALIAS:-TSTALIASID}" \
   --arg information_id "${INFORMATION_ID:-REPLACE_WITH_INFORMATION_AGENT_ID}" \
   --arg information_alias "${INFORMATION_ALIAS:-TSTALIASID}" \
   --arg notes_id "${NOTES_ID:-REPLACE_WITH_NOTES_AGENT_ID}" \
   --arg notes_alias "${NOTES_ALIAS:-TSTALIASID}" \
   --arg chitchat_id "${CHITCHAT_ID:-REPLACE_WITH_CHITCHAT_AGENT_ID}" \
   --arg chitchat_alias "${CHITCHAT_ALIAS:-TSTALIASID}" \
   '.supervisor_id = $supervisor_id |
    .supervisor_alias = $supervisor_alias |
    .agents.scheduling.agent_id = $scheduling_id |
    .agents.scheduling.alias_id = $scheduling_alias |
    .agents.information.agent_id = $information_id |
    .agents.information.alias_id = $information_alias |
    .agents.notes.agent_id = $notes_id |
    .agents.notes.alias_id = $notes_alias |
    .agents.chitchat.agent_id = $chitchat_id |
    .agents.chitchat.alias_id = $chitchat_alias' \
    "$CONFIG_FILE" > "$tmp_file" && mv "$tmp_file" "$CONFIG_FILE"

echo "✅ Config file updated successfully!"
echo ""
echo "Updated $CONFIG_FILE with:"
echo "  Supervisor: $SUPERVISOR_ID (alias: $SUPERVISOR_ALIAS)"
echo "  Scheduling: $SCHEDULING_ID (alias: $SCHEDULING_ALIAS)"
echo "  Information: $INFORMATION_ID (alias: $INFORMATION_ALIAS)"
echo "  Notes: $NOTES_ID (alias: $NOTES_ALIAS)"
echo "  Chitchat: $CHITCHAT_ID (alias: $CHITCHAT_ALIAS)"
echo ""
echo "🎉 Done! You can now use this config for the $ENVIRONMENT environment."
