#!/bin/bash

##############################################################################
# Test SchedulingAgent directly via AWS Bedrock Runtime API
# This bypasses the Supervisor to get JSON responses
##############################################################################

SCHEDULING_AGENT_ID="SOILTYW7SI"
SCHEDULING_ALIAS_ID="GIMRYJ3NCI"
REGION="us-east-1"

# Customer context
CUSTOMER_ID="1646085"
CLIENT_ID="09PF05VD"
BEARER_TOKEN="TaDWx6r5O0WE2tb5/Lb77XuI29UR7j2NlMHbUdXd+YrYPR7ZdTrczgYigcaRHxvF4PUl7KCfKcSa/5LTVI9GZGD2xjCQuIIGifYzjbeIG4F9hljoQfRSa4yHgXV4iKYuqyrGhSMR2SSZtZYnMIprKV5SeEOzLetV5rSRAmv7Gaql+7WMxg9YyXONFcV7MJHDvSyDXZFIDx0aAvhffakC3AN86giYM7H6QGlwo7OqqkfH88MV+MyJTJqMzWJXx7lI5xPuAc0lLtoRftNZ2PQN8Q4APfRkyfsVbm0IkMidTHw4CtIbnDF7rnLdOYO4amUcvntMnR8iAFikdkbGodCW5OZQzMhQxWZIizfX4mkYqNw9jGxOfbFGMonzQZwFgrFfn2F3Zys3lNQR2TlYo78wiYlMAWafKsVYWChjCpCrFuKGIb6pNfW8s38eqDAG2ApYEVxGpEPLUxQpPR7m88ofRS9zL2e3QABL83MVSl487zpM8Epq9if0WJFQ+3KccrHKtkfIwrn3A/IGw8nYmSIXx9kLXwpdYsyRz6hUXkuaqMLnJ9hJctt4TLiMohyrqqcjXhGQoOKKu0eYH+f/mPWkf6hV9rdiKWhLwpCK0j44eDeHgoarYxZZcJGd9KK+2G6pnlvgi6sP8sZcuJTMc4kCiaFFLlXZDJppdXjIBlj9ItscnV2RRIP/I6CLrRsBmkgQpSiw88wW/XihrEVZKXTG2lRKGoZlVLreA0C1NBUbKs8="

# Generate session ID
SESSION_ID="test-cli-$(date +%s)"

echo "======================================================================"
echo "Testing SchedulingAgent Directly via AWS CLI"
echo "======================================================================"
echo "Agent ID: $SCHEDULING_AGENT_ID"
echo "Alias ID: $SCHEDULING_ALIAS_ID"
echo "Session ID: $SESSION_ID"
echo "Customer ID: $CUSTOMER_ID"
echo "Client ID: $CLIENT_ID"
echo "======================================================================"
echo ""

# Create input JSON for invoke-agent
INPUT_JSON=$(cat <<EOF
{
  "inputText": "show me my projects",
  "sessionState": {
    "sessionAttributes": {
      "customer_id": "$CUSTOMER_ID",
      "client_id": "$CLIENT_ID",
      "bearer_token": "$BEARER_TOKEN"
    }
  }
}
EOF
)

echo "Invoking SchedulingAgent..."
echo ""

# Invoke agent and capture response
RESPONSE=$(aws bedrock-agent-runtime invoke-agent \
  --agent-id "$SCHEDULING_AGENT_ID" \
  --agent-alias-id "$SCHEDULING_ALIAS_ID" \
  --session-id "$SESSION_ID" \
  --region "$REGION" \
  --cli-binary-format raw-in-base64-out \
  --input-text "show me my projects" \
  --session-state "{\"sessionAttributes\":{\"customer_id\":\"$CUSTOMER_ID\",\"client_id\":\"$CLIENT_ID\",\"bearer_token\":\"$BEARER_TOKEN\"}}" \
  /tmp/bedrock_response.json 2>&1)

echo "Response saved to: /tmp/bedrock_response.json"
echo ""

# Parse the response file (it's a streaming response)
if [ -f /tmp/bedrock_response.json ]; then
    echo "======================================================================"
    echo "Agent Response:"
    echo "======================================================================"

    # Extract text from the streaming response
    cat /tmp/bedrock_response.json

    echo ""
    echo "======================================================================"
    echo "Checking for JSON code blocks..."
    echo "======================================================================"

    # Check if response contains JSON blocks
    if grep -q '```json' /tmp/bedrock_response.json; then
        echo "✅ JSON code block detected!"
        echo ""
        echo "Extracted JSON:"
        grep -A 20 '```json' /tmp/bedrock_response.json | grep -B 20 '```' | grep -v '```'
    else
        echo "⚠️  No JSON code block found in response"
    fi
else
    echo "❌ Response file not created"
    echo "Error: $RESPONSE"
fi

echo ""
echo "======================================================================"
