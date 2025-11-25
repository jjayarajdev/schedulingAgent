#!/bin/bash

##############################################################################
# Update ProjectForce Token in AWS Secrets Manager
#
# This script:
#   1. Gets a fresh pf_token by logging into PF360 API
#   2. Updates AWS Secrets Manager with the token
#   3. Validates the token works
#   4. Shows how to retrieve it from Lambdas
##############################################################################

set -e

SECRET_NAME="scheduling-agent/pf360/api-credentials"
PF_API_URL="https://api-cx-portal.dev.projectsforce.com"
PF_EMAIL="jay@mailinator.com"
PF_PASSWORD="U2FsdGVkX197AQMdkqthasfRGWLh41rhHVaw9Q9Q8cE="

echo "════════════════════════════════════════════════════════════════════════════"
echo "🔐 ProjectForce Token Manager - AWS Secrets Manager"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

# Step 1: Get fresh token from PF360 API
echo "📡 Step 1: Logging into ProjectForce API..."
LOGIN_RESPONSE=$(curl -s -X POST "${PF_API_URL}/authentication/login?identifier=projectforce-validation" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${PF_EMAIL}\",\"password\":\"${PF_PASSWORD}\",\"device_type\":1}")

# Extract token
ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.accesstoken // empty')
CLIENT_ID=$(echo "$LOGIN_RESPONSE" | jq -r '.user.client_id // "09PF05VD"')
CUSTOMER_ID=$(echo "$LOGIN_RESPONSE" | jq -r '.user.customer_id // "1646085"')

if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" = "null" ]; then
    echo "❌ Failed to get access token from PF360 API"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

echo "✅ Successfully obtained access token"
echo "   Client ID: $CLIENT_ID"
echo "   Customer ID: $CUSTOMER_ID"
echo "   Token length: ${#ACCESS_TOKEN} characters"
echo ""

# Step 2: Update AWS Secrets Manager
echo "☁️  Step 2: Updating AWS Secrets Manager..."

SECRET_VALUE=$(cat <<EOF
{
  "pf_token": "$ACCESS_TOKEN",
  "client_id": "$CLIENT_ID",
  "customer_id": "$CUSTOMER_ID",
  "api_url": "$PF_API_URL",
  "email": "$PF_EMAIL",
  "updated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "updated_by": "$(whoami)",
  "notes": "Auto-updated by update_pf_token_secret.sh"
}
EOF
)

aws secretsmanager put-secret-value \
  --secret-id "$SECRET_NAME" \
  --secret-string "$SECRET_VALUE" \
  > /dev/null

echo "✅ Secret updated successfully: $SECRET_NAME"
echo ""

# Step 3: Verify the secret was stored correctly
echo "🔍 Step 3: Verifying secret..."
STORED_TOKEN=$(aws secretsmanager get-secret-value \
  --secret-id "$SECRET_NAME" \
  --query 'SecretString' \
  --output text | jq -r '.pf_token')

if [ "$STORED_TOKEN" = "$ACCESS_TOKEN" ]; then
    echo "✅ Token verified in Secrets Manager"
else
    echo "❌ Token mismatch! Verification failed"
    exit 1
fi
echo ""

# Step 4: Test the token works
echo "🧪 Step 4: Testing token with PF360 API..."
TEST_RESPONSE=$(curl -s -X GET "${PF_API_URL}/api/projects" \
  -H "Content-Type: application/json" \
  -H "projectforcetoken: ${ACCESS_TOKEN}")

TEST_SUCCESS=$(echo "$TEST_RESPONSE" | jq -r 'if .projects then "true" else "false" end')

if [ "$TEST_SUCCESS" = "true" ]; then
    PROJECT_COUNT=$(echo "$TEST_RESPONSE" | jq '.projects | length')
    echo "✅ Token is valid - Retrieved $PROJECT_COUNT projects"
else
    echo "⚠️  Token validation unclear - check manually"
fi
echo ""

# Step 5: Show how to retrieve from Lambda
echo "════════════════════════════════════════════════════════════════════════════"
echo "📚 How to Use This Token in Your Services"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

echo "1️⃣  AWS Lambda (Python):"
echo "───────────────────────────────────────────────────────────────────────────"
cat << 'PYTHON'
import boto3
import json

def get_pf_token():
    """Retrieve PF token from AWS Secrets Manager"""
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='scheduling-agent/pf360/api-credentials')
    secret = json.loads(response['SecretString'])
    return secret['pf_token'], secret['client_id'], secret['customer_id']

# Usage in Lambda:
pf_token, client_id, customer_id = get_pf_token()
PYTHON
echo ""

echo "2️⃣  AWS Connect Contact Flow:"
echo "───────────────────────────────────────────────────────────────────────────"
cat << 'JSON'
{
  "Type": "GetExternalData",
  "Parameters": {
    "SecretsManager": {
      "SecretArn": "arn:aws:secretsmanager:us-east-1:618048437522:secret:scheduling-agent/pf360/api-credentials-XXXXXX"
    }
  },
  "Transitions": {
    "NextAction": "InvokeLambda",
    "Conditions": [],
    "Errors": []
  }
}
JSON
echo ""

echo "3️⃣  AWS CLI (Test):"
echo "───────────────────────────────────────────────────────────────────────────"
echo "aws secretsmanager get-secret-value \\"
echo "  --secret-id $SECRET_NAME \\"
echo "  --query 'SecretString' --output text | jq '.pf_token'"
echo ""

echo "4️⃣  Lambda Environment Variable (Auto-refresh):"
echo "───────────────────────────────────────────────────────────────────────────"
echo "# Set Lambda to pull from Secrets Manager on cold start"
echo "# No hardcoded tokens in environment variables!"
echo ""

echo "════════════════════════════════════════════════════════════════════════════"
echo "✅ Setup Complete!"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "Secret Name: $SECRET_NAME"
echo "Region: us-east-1"
echo "Token Expires: Never (PF360 tokens don't expire, but can be refreshed)"
echo ""
echo "📌 Next Steps:"
echo "  1. Update AWS Connect contact flow to retrieve secret"
echo "  2. Update Lambdas to use get_pf_token() instead of environment variables"
echo "  3. Set up a cron job to refresh token daily (optional)"
echo "  4. Grant AWS Connect IAM role permission to read this secret"
echo ""
echo "🔒 IAM Permission Required:"
echo "  {\"Effect\": \"Allow\", \"Action\": \"secretsmanager:GetSecretValue\", \"Resource\": \"arn:aws:secretsmanager:us-east-1:618048437522:secret:scheduling-agent/pf360/*\"}"
echo ""
