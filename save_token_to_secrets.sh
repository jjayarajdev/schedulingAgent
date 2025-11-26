#!/bin/bash
# Save token to Secrets Manager

BEARER_TOKEN="$1"
CLIENT_ID="${2:-09PF05VD}"
USER_ID="${3:-1646085}"

if [ -z "$BEARER_TOKEN" ]; then
    echo "Usage: ./save_token_to_secrets.sh <bearer_token> [client_id] [user_id]"
    exit 1
fi

echo "Saving token to Secrets Manager..."
echo "  Client ID: $CLIENT_ID"
echo "  User ID: $USER_ID"
echo "  Token length: ${#BEARER_TOKEN}"

aws secretsmanager put-secret-value \
    --secret-id projectforce/api/credentials \
    --secret-string "{\"bearer_token\":\"$BEARER_TOKEN\",\"client_id\":\"$CLIENT_ID\",\"user_id\":\"$USER_ID\",\"api_base_url\":\"https://projectsforce-validation.cx-portal.dev.projectsforce.com\",\"updated_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"updated_by\":\"manual_save\"}" \
    --region us-east-1

echo "✅ Token saved to Secrets Manager!"
