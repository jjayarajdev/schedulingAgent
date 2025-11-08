#!/bin/bash
# Setup AWS Secrets Manager for ProjectForce API credentials
# This script creates/updates the secret with authentication credentials

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REGION="${AWS_REGION:-us-east-1}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
SECRET_NAME="projectforce/api/${ENVIRONMENT}/credentials"

echo "========================================"
echo "AWS Secrets Manager Setup"
echo "========================================"
echo ""
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"
echo "Secret Name: $SECRET_NAME"
echo ""

# Check if secret exists
echo "Checking if secret exists..."
if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$REGION" >/dev/null 2>&1; then
    echo "✓ Secret already exists"
    ACTION="update"
else
    echo "✗ Secret does not exist"
    ACTION="create"
fi
echo ""

# Prompt for credentials
echo "Enter ProjectForce API credentials:"
echo ""
read -p "Email: " EMAIL
read -sp "Password: " PASSWORD
echo ""
read -sp "Encrypted Password (leave empty to use plain password): " ENCRYPTED_PASSWORD
echo ""
echo ""

# Use encrypted password if provided, otherwise use plain password
if [ -z "$ENCRYPTED_PASSWORD" ]; then
    ENCRYPTED_PASSWORD="$PASSWORD"
    echo "⚠️  Using plain password (not recommended for production)"
else
    echo "✓ Using encrypted password"
fi
echo ""

# Create secret JSON
SECRET_JSON=$(cat <<EOF
{
  "email": "$EMAIL",
  "encrypted_password": "$ENCRYPTED_PASSWORD",
  "environment": "$ENVIRONMENT",
  "auth_url": "https://api-cx-portal.${ENVIRONMENT}.projectsforce.com/authentication/login",
  "identifier": "projectsforce-validation",
  "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "description": "ProjectForce API authentication credentials for $ENVIRONMENT environment"
}
EOF
)

# Create or update secret
if [ "$ACTION" = "create" ]; then
    echo "Creating new secret..."
    aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --description "ProjectForce API credentials for $ENVIRONMENT environment" \
        --secret-string "$SECRET_JSON" \
        --region "$REGION"

    echo ""
    echo "✅ Secret created successfully!"
else
    echo "Updating existing secret..."
    aws secretsmanager put-secret-value \
        --secret-id "$SECRET_NAME" \
        --secret-string "$SECRET_JSON" \
        --region "$REGION"

    echo ""
    echo "✅ Secret updated successfully!"
fi

echo ""
echo "========================================"
echo "Secret Information"
echo "========================================"
echo ""
echo "Secret Name: $SECRET_NAME"
echo "Region: $REGION"
echo "ARN: $(aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$REGION" --query 'ARN' --output text)"
echo ""

# Create IAM policy for Lambda functions
POLICY_NAME="projectforce-secrets-access-${ENVIRONMENT}"
POLICY_FILE="/tmp/${POLICY_NAME}.json"

cat > "$POLICY_FILE" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:${REGION}:*:secret:projectforce/api/${ENVIRONMENT}/*"
    }
  ]
}
EOF

echo "========================================"
echo "Next Steps"
echo "========================================"
echo ""
echo "1. Attach this IAM policy to your Lambda execution roles:"
echo ""
echo "   Policy Name: $POLICY_NAME"
echo "   Policy JSON saved to: $POLICY_FILE"
echo ""
echo "2. Update Lambda environment variables:"
echo ""
echo "   TOKEN_SECRET_NAME=$SECRET_NAME"
echo "   AWS_REGION=$REGION"
echo ""
echo "3. Deploy the token_manager.py module to your Lambda functions"
echo ""
echo "4. Update your Lambda code to use:"
echo ""
echo "   from token_manager import get_bearer_token"
echo "   token = get_bearer_token()"
echo ""
echo "========================================"
echo ""

# Optionally create/update IAM policy
read -p "Would you like to create/update the IAM policy now? (y/n): " CREATE_POLICY

if [ "$CREATE_POLICY" = "y" ] || [ "$CREATE_POLICY" = "Y" ]; then
    echo ""
    echo "Creating/updating IAM policy..."

    # Try to create policy
    if aws iam create-policy \
        --policy-name "$POLICY_NAME" \
        --policy-document "file://$POLICY_FILE" \
        --description "Allow Lambda access to ProjectForce API secrets" \
        2>/dev/null; then

        echo "✅ IAM policy created: $POLICY_NAME"
    else
        # Policy might already exist, try to update
        POLICY_ARN=$(aws iam list-policies --query "Policies[?PolicyName=='$POLICY_NAME'].Arn" --output text)

        if [ -n "$POLICY_ARN" ]; then
            # Get next version number
            VERSIONS=$(aws iam list-policy-versions --policy-arn "$POLICY_ARN" --query 'Versions | length(@)')

            if [ "$VERSIONS" -ge 5 ]; then
                # Delete oldest non-default version
                OLDEST_VERSION=$(aws iam list-policy-versions --policy-arn "$POLICY_ARN" --query 'Versions[?IsDefaultVersion==`false`] | [-1].VersionId' --output text)
                aws iam delete-policy-version --policy-arn "$POLICY_ARN" --version-id "$OLDEST_VERSION"
            fi

            # Create new version
            aws iam create-policy-version \
                --policy-arn "$POLICY_ARN" \
                --policy-document "file://$POLICY_FILE" \
                --set-as-default

            echo "✅ IAM policy updated: $POLICY_NAME"
        else
            echo "❌ Failed to create or update policy"
        fi
    fi

    echo ""
    echo "To attach this policy to a Lambda role:"
    echo ""
    echo "  aws iam attach-role-policy \\"
    echo "    --role-name <your-lambda-role-name> \\"
    echo "    --policy-arn $(aws iam list-policies --query "Policies[?PolicyName=='$POLICY_NAME'].Arn" --output text)"
    echo ""
fi

echo "🎉 Setup complete!"
echo ""
