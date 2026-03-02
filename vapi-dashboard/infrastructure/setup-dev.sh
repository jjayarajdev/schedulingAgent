#!/bin/bash
# ============================================================================
# PF-SYN VAPI Dashboard - DEV Environment Setup
# Region: us-east-1
# ============================================================================

set -e

# Configuration
AWS_PROFILE="pf-aws"
REGION="us-east-1"
ENV="dev"
PREFIX="pf-syn-vapi-dashboard"

# Resource names
USERS_TABLE="${PREFIX}-users-${ENV}"
TENANTS_TABLE="${PREFIX}-tenants-${ENV}"
AUTH_LAMBDA="${PREFIX}-auth-${ENV}"
API_LAMBDA="${PREFIX}-api-${ENV}"
LAMBDA_ROLE="${PREFIX}-lambda-role-${ENV}"
API_GATEWAY="${PREFIX}-api-${ENV}"
S3_BUCKET="${PREFIX}-${ENV}"

echo "============================================"
echo "Setting up VAPI Dashboard - DEV (us-east-1)"
echo "============================================"

# ============================================================================
# 1. Create IAM Role for Lambda
# ============================================================================
echo ""
echo "[1/7] Creating IAM Role: ${LAMBDA_ROLE}"

# Trust policy for Lambda
cat > /tmp/lambda-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create role (ignore if exists)
AWS_PROFILE=$AWS_PROFILE aws iam create-role \
  --role-name $LAMBDA_ROLE \
  --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
  --region $REGION 2>/dev/null || echo "  Role already exists, skipping..."

# Attach basic Lambda execution policy
AWS_PROFILE=$AWS_PROFILE aws iam attach-role-policy \
  --role-name $LAMBDA_ROLE \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
  --region $REGION 2>/dev/null || echo "  Policy already attached"

# Create custom policy for DynamoDB and Secrets Manager
cat > /tmp/lambda-custom-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:${REGION}:*:table/${USERS_TABLE}",
        "arn:aws:dynamodb:${REGION}:*:table/${TENANTS_TABLE}",
        "arn:aws:dynamodb:${REGION}:*:table/${USERS_TABLE}/index/*",
        "arn:aws:dynamodb:${REGION}:*:table/${TENANTS_TABLE}/index/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:${REGION}:*:secret:pf-syn-vapi-*"
    }
  ]
}
EOF

# Create and attach custom policy
POLICY_NAME="${PREFIX}-lambda-policy-${ENV}"
AWS_PROFILE=$AWS_PROFILE aws iam put-role-policy \
  --role-name $LAMBDA_ROLE \
  --policy-name $POLICY_NAME \
  --policy-document file:///tmp/lambda-custom-policy.json \
  --region $REGION

echo "  IAM Role created and policies attached"

# Wait for role to propagate
echo "  Waiting for IAM role to propagate..."
sleep 10

# ============================================================================
# 2. Create DynamoDB Tables
# ============================================================================
echo ""
echo "[2/7] Creating DynamoDB Tables"

# Users table
echo "  Creating table: ${USERS_TABLE}"
AWS_PROFILE=$AWS_PROFILE aws dynamodb create-table \
  --table-name $USERS_TABLE \
  --attribute-definitions \
    AttributeName=username,AttributeType=S \
  --key-schema \
    AttributeName=username,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region $REGION 2>/dev/null || echo "    Table already exists, skipping..."

# Tenants table
echo "  Creating table: ${TENANTS_TABLE}"
AWS_PROFILE=$AWS_PROFILE aws dynamodb create-table \
  --table-name $TENANTS_TABLE \
  --attribute-definitions \
    AttributeName=tenant_id,AttributeType=S \
  --key-schema \
    AttributeName=tenant_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region $REGION 2>/dev/null || echo "    Table already exists, skipping..."

echo "  Waiting for tables to be active..."
AWS_PROFILE=$AWS_PROFILE aws dynamodb wait table-exists --table-name $USERS_TABLE --region $REGION
AWS_PROFILE=$AWS_PROFILE aws dynamodb wait table-exists --table-name $TENANTS_TABLE --region $REGION
echo "  Tables created successfully"

# ============================================================================
# 3. Seed Initial Data
# ============================================================================
echo ""
echo "[3/7] Seeding Initial Data"

# Seed tenants
echo "  Adding tenant: WTU"
AWS_PROFILE=$AWS_PROFILE aws dynamodb put-item \
  --table-name $TENANTS_TABLE \
  --item '{
    "tenant_id": {"S": "wtu"},
    "name": {"S": "Window Treatment Universe"},
    "vapi_phone_number_id": {"S": "04839e46-2cbc-467e-8e01-638900654c36"},
    "vapi_phone_number": {"S": "+12038946599"},
    "created_at": {"S": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}
  }' \
  --region $REGION

echo "  Adding tenant: PF-Agent"
AWS_PROFILE=$AWS_PROFILE aws dynamodb put-item \
  --table-name $TENANTS_TABLE \
  --item '{
    "tenant_id": {"S": "pf"},
    "name": {"S": "ProjectsForce"},
    "vapi_phone_number_id": {"S": "6b7ac954-1f6e-460d-962a-48883d31c1f0"},
    "vapi_phone_number": {"S": "+12185516488"},
    "created_at": {"S": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}
  }' \
  --region $REGION

echo "  Adding tenant: PF-Dev"
AWS_PROFILE=$AWS_PROFILE aws dynamodb put-item \
  --table-name $TENANTS_TABLE \
  --item '{
    "tenant_id": {"S": "pf-dev"},
    "name": {"S": "ProjectsForce Dev"},
    "vapi_phone_number_id": {"S": "1c99c266-9778-4809-bf5e-dba30326a0ae"},
    "vapi_phone_number": {"S": "+18624200502"},
    "created_at": {"S": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}
  }' \
  --region $REGION

# Seed admin user (password: admin123 - CHANGE IN PRODUCTION!)
# Password hash generated with: python3 -c "import hashlib; print(hashlib.sha256('admin123'.encode()).hexdigest())"
ADMIN_PASS_HASH="240be518fabd2724ddb6f04eeb9d5b0ccb8e4e6bdf0d53db4e19e7d0d6e6a2d1"
echo "  Adding admin user: admin"
AWS_PROFILE=$AWS_PROFILE aws dynamodb put-item \
  --table-name $USERS_TABLE \
  --item '{
    "username": {"S": "admin"},
    "password_hash": {"S": "'$ADMIN_PASS_HASH'"},
    "tenant_id": {"S": "pf"},
    "role": {"S": "admin"},
    "name": {"S": "Admin User"},
    "created_at": {"S": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}
  }' \
  --region $REGION

echo "  Initial data seeded"

# ============================================================================
# 4. Create S3 Bucket for Frontend
# ============================================================================
echo ""
echo "[4/7] Creating S3 Bucket: ${S3_BUCKET}"

AWS_PROFILE=$AWS_PROFILE aws s3api create-bucket \
  --bucket $S3_BUCKET \
  --region $REGION 2>/dev/null || echo "  Bucket already exists, skipping..."

# Enable static website hosting
AWS_PROFILE=$AWS_PROFILE aws s3 website s3://$S3_BUCKET/ \
  --index-document index.html \
  --error-document index.html

# Set bucket policy for public read (for static website)
cat > /tmp/s3-bucket-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${S3_BUCKET}/*"
    }
  ]
}
EOF

# Disable block public access first
AWS_PROFILE=$AWS_PROFILE aws s3api put-public-access-block \
  --bucket $S3_BUCKET \
  --public-access-block-configuration "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false" \
  --region $REGION

AWS_PROFILE=$AWS_PROFILE aws s3api put-bucket-policy \
  --bucket $S3_BUCKET \
  --policy file:///tmp/s3-bucket-policy.json \
  --region $REGION

echo "  S3 bucket created and configured for static hosting"

# ============================================================================
# 5. Create Lambda Functions (placeholder - actual deploy via deploy script)
# ============================================================================
echo ""
echo "[5/7] Lambda functions will be created by deploy-backend-dev.sh"

# ============================================================================
# 6. Create API Gateway
# ============================================================================
echo ""
echo "[6/7] Creating API Gateway: ${API_GATEWAY}"

# Create HTTP API (v2)
API_ID=$(AWS_PROFILE=$AWS_PROFILE aws apigatewayv2 create-api \
  --name $API_GATEWAY \
  --protocol-type HTTP \
  --cors-configuration "AllowOrigins=*,AllowMethods=GET,POST,OPTIONS,AllowHeaders=Content-Type,Authorization" \
  --region $REGION \
  --query 'ApiId' \
  --output text 2>/dev/null) || API_ID=""

if [ -z "$API_ID" ]; then
  # API might already exist, try to get it
  API_ID=$(AWS_PROFILE=$AWS_PROFILE aws apigatewayv2 get-apis \
    --region $REGION \
    --query "Items[?Name=='${API_GATEWAY}'].ApiId" \
    --output text)
  echo "  API Gateway already exists: ${API_ID}"
else
  echo "  API Gateway created: ${API_ID}"
fi

# Create $default stage with auto-deploy
AWS_PROFILE=$AWS_PROFILE aws apigatewayv2 create-stage \
  --api-id $API_ID \
  --stage-name '$default' \
  --auto-deploy \
  --region $REGION 2>/dev/null || echo "  Stage already exists"

# Store API ID for later use
echo $API_ID > /tmp/api-gateway-id-dev.txt
echo "  API Gateway ID saved to /tmp/api-gateway-id-dev.txt"

# ============================================================================
# 7. Output Summary
# ============================================================================
echo ""
echo "============================================"
echo "Setup Complete!"
echo "============================================"
echo ""
echo "Resources Created:"
echo "  - IAM Role: ${LAMBDA_ROLE}"
echo "  - DynamoDB: ${USERS_TABLE}"
echo "  - DynamoDB: ${TENANTS_TABLE}"
echo "  - S3 Bucket: ${S3_BUCKET}"
echo "  - API Gateway: ${API_GATEWAY} (ID: ${API_ID})"
echo ""
echo "Frontend URL (after deploy):"
echo "  http://${S3_BUCKET}.s3-website-${REGION}.amazonaws.com"
echo ""
echo "API URL (after Lambda deploy):"
echo "  https://${API_ID}.execute-api.${REGION}.amazonaws.com"
echo ""
echo "Default Admin Login:"
echo "  Username: admin"
echo "  Password: admin123 (CHANGE THIS!)"
echo ""
echo "Next Steps:"
echo "  1. Run: ./deploy-backend-dev.sh"
echo "  2. Run: ./deploy-frontend-dev.sh"
echo ""
