#!/bin/bash
#
# Configure VAPI Assistant
#
# Usage:
#   ./configure-assistant.sh dev      # Configure dev assistant
#   ./configure-assistant.sh prod     # Configure prod assistant
#
# This script updates the VAPI assistant configuration to:
# - Set the serverUrl to the Lambda webhook
# - Configure the projectforce_api tool with proper parameters
# - Update serverMessages to include function-call
#
# Required: VAPI_PRIVATE_KEY environment variable or --api-key flag
#

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${SCRIPT_DIR}/../config"

# Default environment
ENVIRONMENT="${1:-dev}"

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prod" ]]; then
    echo "Error: Environment must be 'dev' or 'prod'"
    echo "Usage: $0 [dev|prod]"
    exit 1
fi

# VAPI Configuration
# These should be stored in a config file or environment variables
VAPI_ASSISTANT_DEV="2b437308-b93e-4da6-a2f1-ffbf422d5298"
VAPI_ASSISTANT_PROD="fa7fd950-dd7b-4900-9e92-4d8bc2c7342f"

# Get assistant ID based on environment
if [[ "$ENVIRONMENT" == "dev" ]]; then
    ASSISTANT_ID="$VAPI_ASSISTANT_DEV"
else
    ASSISTANT_ID="$VAPI_ASSISTANT_PROD"
fi

if [[ -z "$ASSISTANT_ID" ]]; then
    echo "Error: No assistant ID configured for environment: ${ENVIRONMENT}"
    exit 1
fi

# Get API key from environment or prompt
VAPI_API_KEY="${VAPI_PRIVATE_KEY:-}"

if [[ -z "$VAPI_API_KEY" ]]; then
    echo "VAPI_PRIVATE_KEY not set. Please enter your VAPI private API key:"
    read -s VAPI_API_KEY
    echo ""
fi

if [[ -z "$VAPI_API_KEY" ]]; then
    echo "Error: VAPI API key is required"
    exit 1
fi

# Get Lambda Function URL
AWS_PROFILE="${AWS_PROFILE:-pf-aws}"
LAMBDA_NAME="pf-syn-vapi-webhook-${ENVIRONMENT}"
DEPLOY_REGION="us-east-1"

echo "=========================================="
echo "VAPI Assistant Configuration"
echo "=========================================="
echo "Environment:  ${ENVIRONMENT}"
echo "Assistant ID: ${ASSISTANT_ID}"
echo "=========================================="

# Get the webhook URL
echo ""
echo "[1/3] Getting Lambda Function URL..."
WEBHOOK_URL=$(aws --profile "$AWS_PROFILE" lambda get-function-url-config \
    --function-name "$LAMBDA_NAME" \
    --region "$DEPLOY_REGION" \
    --query 'FunctionUrl' \
    --output text 2>/dev/null || echo "")

if [[ -z "$WEBHOOK_URL" || "$WEBHOOK_URL" == "None" ]]; then
    echo "Error: Could not get Function URL for ${LAMBDA_NAME}"
    echo "Make sure the Lambda is deployed with: ./deploy-webhook.sh ${ENVIRONMENT}"
    exit 1
fi

echo "Webhook URL: ${WEBHOOK_URL}"

# Configure serverUrl and serverMessages
echo ""
echo "[2/3] Configuring server URL and messages..."
RESPONSE=$(curl -s -X PATCH "https://api.vapi.ai/assistant/${ASSISTANT_ID}" \
    --header "Authorization: Bearer ${VAPI_API_KEY}" \
    --header "Content-Type: application/json" \
    --data '{
        "serverUrl": "'"${WEBHOOK_URL}"'",
        "serverMessages": [
            "assistant.started",
            "conversation-update",
            "end-of-call-report",
            "function-call",
            "hang",
            "speech-update",
            "status-update",
            "tool-calls",
            "transfer-destination-request",
            "handoff-destination-request",
            "user-interrupted",
            "transcript"
        ]
    }')

# Check for errors
if echo "$RESPONSE" | grep -q '"error"'; then
    echo "Error updating server configuration:"
    echo "$RESPONSE" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "$RESPONSE"
    exit 1
fi

echo "Server configuration updated successfully"

# Configure the tool
echo ""
echo "[3/3] Configuring projectforce_api tool..."
RESPONSE=$(curl -s -X PATCH "https://api.vapi.ai/assistant/${ASSISTANT_ID}" \
    --header "Authorization: Bearer ${VAPI_API_KEY}" \
    --header "Content-Type: application/json" \
    --data '{
        "model": {
            "model": "gpt-4o",
            "provider": "openai",
            "temperature": 0.5,
            "messages": [
                {
                    "role": "system",
                    "content": "## Identity & Purpose\n\nYou are **Riley**, a project scheduling voice assistant for **ProjectForce**, a home services scheduling platform.\n\nYour primary purpose is to:\n* Help customers understand their projects\n* Schedule, confirm, reschedule, or cancel appointments\n* Provide clear project status and next-step guidance\n\n## CRITICAL: Using the ProjectForce Tool\n\nYou MUST use the `projectforce_api` tool for ANY of these requests:\n- List projects, show my projects, what projects do I have\n- Schedule, reschedule, or cancel appointments\n- Check project status\n- Get available dates or time slots\n- Any project-related questions\n\nWhen calling the tool, pass the user exact words as the message parameter.\n\n## Voice & Persona\n\n* Friendly, calm, and highly organized\n* Patient and supportive\n* Professional but conversational\n* Clear, concise language with natural contractions\n\n## Response Guidelines\n\n* Always use the projectforce_api tool for project queries\n* Ask one question at a time\n* Repeat dates, times, and addresses for confirmation\n* Keep explanations short and practical"
                }
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "projectforce_api",
                        "description": "Call this tool for ANY project-related request: listing projects, scheduling, rescheduling, canceling, checking status, getting available dates/times. Always use this tool when the user asks about their projects or appointments.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "message": {
                                    "type": "string",
                                    "description": "The user request or question about their projects. Pass the user exact words."
                                },
                                "action": {
                                    "type": "string",
                                    "enum": ["list_projects", "get_project_details", "get_available_dates", "get_time_slots", "schedule", "reschedule", "cancel", "other"],
                                    "description": "The type of action requested"
                                }
                            },
                            "required": ["message", "action"]
                        }
                    }
                }
            ]
        }
    }')

# Check for errors
if echo "$RESPONSE" | grep -q '"error"'; then
    echo "Error updating tool configuration:"
    echo "$RESPONSE" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "$RESPONSE"
    exit 1
fi

echo "Tool configuration updated successfully"

# Verify configuration
echo ""
echo "=========================================="
echo "Configuration Complete!"
echo "=========================================="
echo ""
echo "Verifying configuration..."

VERIFY=$(curl -s -X GET "https://api.vapi.ai/assistant/${ASSISTANT_ID}" \
    --header "Authorization: Bearer ${VAPI_API_KEY}")

# Extract key fields
SERVER_URL=$(echo "$VERIFY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('serverUrl', 'NOT SET'))" 2>/dev/null || echo "Error")
TOOL_NAME=$(echo "$VERIFY" | python3 -c "import sys,json; d=json.load(sys.stdin); tools=d.get('model',{}).get('tools',[]); print(tools[0]['function']['name'] if tools else 'NONE')" 2>/dev/null || echo "Error")

echo ""
echo "Current Configuration:"
echo "  Server URL: ${SERVER_URL}"
echo "  Tool:       ${TOOL_NAME}"
echo ""
echo "The VAPI assistant is now configured to route"
echo "voice requests through the ProjectForce orchestrator."
echo ""
echo "Test by calling your VAPI phone number and saying:"
echo '  "What are my projects?"'
echo "=========================================="
