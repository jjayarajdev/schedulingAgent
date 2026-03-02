#!/bin/bash
# ============================================================================
# PF-SYN VAPI Dashboard - Deploy Backend to DEV
# Region: us-east-1
# ============================================================================

set -e

# Configuration
AWS_PROFILE="pf-aws"
REGION="us-east-1"
ENV="dev"
PREFIX="pf-syn-vapi-dashboard"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"

# Resource names
AUTH_LAMBDA="${PREFIX}-auth-${ENV}"
API_LAMBDA="${PREFIX}-api-${ENV}"
LAMBDA_ROLE="${PREFIX}-lambda-role-${ENV}"
API_GATEWAY="${PREFIX}-api-${ENV}"
USERS_TABLE="${PREFIX}-users-${ENV}"
TENANTS_TABLE="${PREFIX}-tenants-${ENV}"

# Get AWS Account ID
ACCOUNT_ID=$(AWS_PROFILE=$AWS_PROFILE aws sts get-caller-identity --query 'Account' --output text)
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${LAMBDA_ROLE}"

echo "============================================"
echo "Deploying VAPI Dashboard Backend - DEV"
echo "============================================"

# ============================================================================
# 1. Package Auth Lambda
# ============================================================================
echo ""
echo "[1/5] Packaging Auth Lambda"

cd "$BACKEND_DIR/auth"
zip -r /tmp/${AUTH_LAMBDA}.zip handler.py

echo "  Auth Lambda packaged"

# ============================================================================
# 2. Package API Lambda
# ============================================================================
echo ""
echo "[2/5] Packaging API Lambda"

cd "$BACKEND_DIR/api"
zip -r /tmp/${API_LAMBDA}.zip handler.py

echo "  API Lambda packaged"

# ============================================================================
# 3. Deploy Auth Lambda
# ============================================================================
echo ""
echo "[3/5] Deploying Auth Lambda: ${AUTH_LAMBDA}"

# Check if Lambda exists
if AWS_PROFILE=$AWS_PROFILE aws lambda get-function --function-name $AUTH_LAMBDA --region $REGION 2>/dev/null; then
  # Update existing
  AWS_PROFILE=$AWS_PROFILE aws lambda update-function-code \
    --function-name $AUTH_LAMBDA \
    --zip-file fileb:///tmp/${AUTH_LAMBDA}.zip \
    --region $REGION \
    --query '[FunctionName, LastModified]' \
    --output table
else
  # Create new
  AWS_PROFILE=$AWS_PROFILE aws lambda create-function \
    --function-name $AUTH_LAMBDA \
    --runtime python3.11 \
    --role $ROLE_ARN \
    --handler handler.lambda_handler \
    --zip-file fileb:///tmp/${AUTH_LAMBDA}.zip \
    --timeout 30 \
    --memory-size 256 \
    --environment "Variables={ENVIRONMENT=${ENV},USERS_TABLE=${USERS_TABLE},TENANTS_TABLE=${TENANTS_TABLE},JWT_SECRET=change-this-secret-in-production-${ENV}}" \
    --region $REGION \
    --query '[FunctionName, LastModified]' \
    --output table
fi

# Update environment variables (in case they changed)
AWS_PROFILE=$AWS_PROFILE aws lambda update-function-configuration \
  --function-name $AUTH_LAMBDA \
  --environment "Variables={ENVIRONMENT=${ENV},USERS_TABLE=${USERS_TABLE},TENANTS_TABLE=${TENANTS_TABLE},JWT_SECRET=change-this-secret-in-production-${ENV}}" \
  --region $REGION > /dev/null

echo "  Auth Lambda deployed"

# ============================================================================
# 4. Deploy API Lambda
# ============================================================================
echo ""
echo "[4/5] Deploying API Lambda: ${API_LAMBDA}"

# Get VAPI API Key from environment or prompt
VAPI_API_KEY="${VAPI_API_KEY:-}"
if [ -z "$VAPI_API_KEY" ]; then
  echo "  NOTE: VAPI_API_KEY not set. Set it with:"
  echo "  export VAPI_API_KEY=your-key && ./deploy-backend-dev.sh"
  VAPI_API_KEY="placeholder-set-via-console"
fi

# Check if Lambda exists
if AWS_PROFILE=$AWS_PROFILE aws lambda get-function --function-name $API_LAMBDA --region $REGION 2>/dev/null; then
  # Update existing
  AWS_PROFILE=$AWS_PROFILE aws lambda update-function-code \
    --function-name $API_LAMBDA \
    --zip-file fileb:///tmp/${API_LAMBDA}.zip \
    --region $REGION \
    --query '[FunctionName, LastModified]' \
    --output table
else
  # Create new
  AWS_PROFILE=$AWS_PROFILE aws lambda create-function \
    --function-name $API_LAMBDA \
    --runtime python3.11 \
    --role $ROLE_ARN \
    --handler handler.lambda_handler \
    --zip-file fileb:///tmp/${API_LAMBDA}.zip \
    --timeout 60 \
    --memory-size 512 \
    --environment "Variables={ENVIRONMENT=${ENV},TENANTS_TABLE=${TENANTS_TABLE},VAPI_API_KEY=${VAPI_API_KEY},JWT_SECRET=change-this-secret-in-production-${ENV}}" \
    --region $REGION \
    --query '[FunctionName, LastModified]' \
    --output table
fi

# Update environment variables
AWS_PROFILE=$AWS_PROFILE aws lambda update-function-configuration \
  --function-name $API_LAMBDA \
  --environment "Variables={ENVIRONMENT=${ENV},TENANTS_TABLE=${TENANTS_TABLE},VAPI_API_KEY=${VAPI_API_KEY},JWT_SECRET=change-this-secret-in-production-${ENV}}" \
  --region $REGION > /dev/null

echo "  API Lambda deployed"

# ============================================================================
# 5. Configure API Gateway Routes
# ============================================================================
echo ""
echo "[5/5] Configuring API Gateway Routes"

# Get API Gateway ID
API_ID=$(AWS_PROFILE=$AWS_PROFILE aws apigatewayv2 get-apis \
  --region $REGION \
  --query "Items[?Name=='${API_GATEWAY}'].ApiId" \
  --output text)

if [ -z "$API_ID" ]; then
  echo "  ERROR: API Gateway not found. Run setup-dev.sh first."
  exit 1
fi

echo "  API Gateway ID: ${API_ID}"

# Get Lambda ARNs
AUTH_LAMBDA_ARN=$(AWS_PROFILE=$AWS_PROFILE aws lambda get-function \
  --function-name $AUTH_LAMBDA \
  --region $REGION \
  --query 'Configuration.FunctionArn' \
  --output text)

API_LAMBDA_ARN=$(AWS_PROFILE=$AWS_PROFILE aws lambda get-function \
  --function-name $API_LAMBDA \
  --region $REGION \
  --query 'Configuration.FunctionArn' \
  --output text)

# Create/update integrations
echo "  Creating Auth Lambda integration..."
AUTH_INTEGRATION_ID=$(AWS_PROFILE=$AWS_PROFILE aws apigatewayv2 create-integration \
  --api-id $API_ID \
  --integration-type AWS_PROXY \
  --integration-uri $AUTH_LAMBDA_ARN \
  --payload-format-version 2.0 \
  --region $REGION \
  --query 'IntegrationId' \
  --output text 2>/dev/null) || \
AUTH_INTEGRATION_ID=$(AWS_PROFILE=$AWS_PROFILE aws apigatewayv2 get-integrations \
  --api-id $API_ID \
  --region $REGION \
  --query "Items[?IntegrationUri=='${AUTH_LAMBDA_ARN}'].IntegrationId" \
  --output text | head -1)

echo "  Creating API Lambda integration..."
API_INTEGRATION_ID=$(AWS_PROFILE=$AWS_PROFILE aws apigatewayv2 create-integration \
  --api-id $API_ID \
  --integration-type AWS_PROXY \
  --integration-uri $API_LAMBDA_ARN \
  --payload-format-version 2.0 \
  --region $REGION \
  --query 'IntegrationId' \
  --output text 2>/dev/null) || \
API_INTEGRATION_ID=$(AWS_PROFILE=$AWS_PROFILE aws apigatewayv2 get-integrations \
  --api-id $API_ID \
  --region $REGION \
  --query "Items[?IntegrationUri=='${API_LAMBDA_ARN}'].IntegrationId" \
  --output text | head -1)

# Create routes
echo "  Creating routes..."

# Auth routes
for ROUTE in "POST /auth/login" "GET /auth/verify" "POST /auth/logout"; do
  AWS_PROFILE=$AWS_PROFILE aws apigatewayv2 create-route \
    --api-id $API_ID \
    --route-key "$ROUTE" \
    --target "integrations/${AUTH_INTEGRATION_ID}" \
    --region $REGION 2>/dev/null || echo "    Route '$ROUTE' already exists"
done

# API routes
for ROUTE in "GET /api/calls" "GET /api/call/{callId}" "GET /api/stats" "GET /api/costs" "GET /api/tenants"; do
  AWS_PROFILE=$AWS_PROFILE aws apigatewayv2 create-route \
    --api-id $API_ID \
    --route-key "$ROUTE" \
    --target "integrations/${API_INTEGRATION_ID}" \
    --region $REGION 2>/dev/null || echo "    Route '$ROUTE' already exists"
done

# Add Lambda permissions for API Gateway
echo "  Adding Lambda permissions..."
AWS_PROFILE=$AWS_PROFILE aws lambda add-permission \
  --function-name $AUTH_LAMBDA \
  --statement-id apigateway-invoke-auth-${ENV} \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*" \
  --region $REGION 2>/dev/null || echo "    Auth permission already exists"

AWS_PROFILE=$AWS_PROFILE aws lambda add-permission \
  --function-name $API_LAMBDA \
  --statement-id apigateway-invoke-api-${ENV} \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*" \
  --region $REGION 2>/dev/null || echo "    API permission already exists"

# ============================================================================
# Output Summary
# ============================================================================
echo ""
echo "============================================"
echo "Backend Deployment Complete!"
echo "============================================"
echo ""
echo "API Endpoints:"
echo "  Base URL: https://${API_ID}.execute-api.${REGION}.amazonaws.com"
echo ""
echo "  Auth:"
echo "    POST /auth/login    - Login with username/password"
echo "    GET  /auth/verify   - Verify JWT token"
echo "    POST /auth/logout   - Logout"
echo ""
echo "  API:"
echo "    GET /api/calls      - List calls"
echo "    GET /api/call/{id}  - Get call details"
echo "    GET /api/stats      - Get statistics"
echo "    GET /api/costs      - Get cost breakdown"
echo "    GET /api/tenants    - List tenants (admin only)"
echo ""
echo "Test login:"
echo "  curl -X POST https://${API_ID}.execute-api.${REGION}.amazonaws.com/auth/login \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"username\":\"admin\",\"password\":\"admin123\"}'"
echo ""
