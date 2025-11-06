#!/bin/bash

# Update agent config files with latest deployed agent IDs
# This script reads from config/agent_ids.json and updates all environment-specific configs

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$PROJECT_ROOT/config"
AGENT_IDS_FILE="$CONFIG_DIR/agent_ids.json"

echo "🔄 Updating agent configuration files..."
echo "================================================"

# Check if agent_ids.json exists
if [ ! -f "$AGENT_IDS_FILE" ]; then
    echo "❌ Error: $AGENT_IDS_FILE not found"
    echo "   Please run DEPLOY.sh first to create agent_ids.json"
    exit 1
fi

# Extract values from agent_ids.json
SUPERVISOR_ID=$(jq -r '.agents.Supervisor.id' "$AGENT_IDS_FILE")
SCHEDULING_ID=$(jq -r '.agents.SchedulingAgent.id' "$AGENT_IDS_FILE")
INFORMATION_ID=$(jq -r '.agents["pf-information"].id' "$AGENT_IDS_FILE")
CHITCHAT_ID=$(jq -r '.agents["pf-chitchat"].id' "$AGENT_IDS_FILE")
REGION=$(jq -r '.region' "$AGENT_IDS_FILE")
ACCOUNT_ID=$(jq -r '.account_id' "$AGENT_IDS_FILE")

echo "📋 Extracted Agent IDs:"
echo "   Supervisor:    $SUPERVISOR_ID"
echo "   Scheduling:    $SCHEDULING_ID"
echo "   Information:   $INFORMATION_ID"
echo "   Chitchat:      $CHITCHAT_ID"
echo "   Region:        $REGION"
echo "   Account:       $ACCOUNT_ID"
echo ""

# Function to update agent config file
update_config() {
    local env=$1
    local config_file="$CONFIG_DIR/agent_config.${env}.json"

    echo "📝 Updating $config_file..."

    # Create the config file
    cat > "$config_file" <<EOF
{
  "environment": "${env}",
  "supervisor_id": "${SUPERVISOR_ID}",
  "supervisor_alias": "TSTALIASID",
  "agents": {
    "scheduling": {
      "agent_id": "${SCHEDULING_ID}",
      "alias_id": "TSTALIASID"
    },
    "information": {
      "agent_id": "${INFORMATION_ID}",
      "alias_id": "TSTALIASID"
    },
    "chitchat": {
      "agent_id": "${CHITCHAT_ID}",
      "alias_id": "TSTALIASID"
    }
  },
  "routing": {
    "enabled": true,
    "method": "supervisor",
    "use_supervisor": true,
    "classifier_model": "anthropic.claude-3-haiku-20240307-v1:0"
  },
  "region": "${REGION}",
  "prefix": "pf_",
  "customer_context": {
    "injection_method": "prompt_augmentation_and_session_attributes",
    "session_attributes": [
      "customer_id",
      "customer_type",
      "client_id"
    ]
  }
}
EOF

    echo "   ✅ Updated $config_file"
}

# Update all environment configs
update_config "dev"
update_config "staging"
update_config "prod"

# Create symlink for backend compatibility (optional)
echo ""
echo "🔗 Creating symlinks for backward compatibility..."
if [ -L "$PROJECT_ROOT/backend/agent_config.json" ]; then
    rm "$PROJECT_ROOT/backend/agent_config.json"
fi
ln -s "../config/agent_config.dev.json" "$PROJECT_ROOT/backend/agent_config.json"
echo "   ✅ Created symlink: backend/agent_config.json -> config/agent_config.dev.json"

echo ""
echo "✅ All agent configuration files updated successfully!"
echo ""
echo "📂 Configuration files location: $CONFIG_DIR/"
echo "   - agent_config.dev.json"
echo "   - agent_config.staging.json"
echo "   - agent_config.prod.json"
echo ""
echo "💡 Tip: The backend will automatically use config/agent_config.dev.json"
