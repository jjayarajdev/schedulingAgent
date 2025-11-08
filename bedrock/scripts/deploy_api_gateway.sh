#!/bin/bash
# Deploy API Gateway to proxy requests to Bedrock Agents

set -e

# Configuration
ENVIRONMENT=${1:-dev}
REGION=${AWS_REGION:-us-east-1}
API_NAME="pf-agent-api-${ENVIRONMENT}"
LAMBDA_FUNCTION_NAME="pf-bedrock-agent-proxy-${ENVIRONMENT}"

echo "================================================"
echo "  API Gateway Deployment for Bedrock Agents"
echo "================================================"
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo "API Name: $API_NAME"
echo ""

# Step 1: Create Lambda function for API Gateway integration
echo "📦 Step 1: Creating Lambda function..."

# Create Lambda deployment package from backend/app.py
BUILD_DIR="/tmp/lambda-api-build"
rm -rf $BUILD_DIR
mkdir -p $BUILD_DIR

# Copy Flask backend
cp ../backend/app.py $BUILD_DIR/lambda_function.py
cp ../backend/agent_config.${ENVIRONMENT}.json $BUILD_DIR/agent_config.json

# Install dependencies
cd $BUILD_DIR
pip3 install flask boto3 -t . --quiet

# Create Lambda handler wrapper
cat > $BUILD_DIR/lambda_handler.py <<'EOF'
import json
from app import app

def lambda_handler(event, context):
    """API Gateway Lambda handler"""
    # Extract HTTP method and path
    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')

    # Extract query parameters
    query_params = event.get('queryStringParameters', {}) or {}

    # Extract body
    body = event.get('body', '')
    if body and event.get('isBase64Encoded', False):
        import base64
        body = base64.b64decode(body).decode('utf-8')

    # Call Flask app
    with app.test_client() as client:
        response = client.open(
            path=path,
            method=http_method,
            data=body,
            query_string=query_params,
            headers=dict(event.get('headers', {}))
        )

    return {
        'statusCode': response.status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': response.get_data(as_text=True)
    }
EOF

# Create deployment package
zip -r lambda.zip . -q

echo "✅ Lambda package created"

# Step 2: Create/Update Lambda function
echo ""
echo "🔧 Step 2: Deploying Lambda function..."

# Check if Lambda exists
if aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --region $REGION 2>/dev/null; then
    echo "Updating existing Lambda..."
    aws lambda update-function-code \
        --function-name $LAMBDA_FUNCTION_NAME \
        --zip-file fileb://lambda.zip \
        --region $REGION \
        --output json > /dev/null
else
    echo "Creating new Lambda..."

    # Create execution role first
    ROLE_NAME="pf-api-lambda-role-${ENVIRONMENT}"

    cat > /tmp/trust-policy.json <<EOF
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

    if ! aws iam get-role --role-name $ROLE_NAME 2>/dev/null; then
        aws iam create-role \
            --role-name $ROLE_NAME \
            --assume-role-policy-document file:///tmp/trust-policy.json \
            --output json > /dev/null

        aws iam attach-role-policy \
            --role-name $ROLE_NAME \
            --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

        aws iam attach-role-policy \
            --role-name $ROLE_NAME \
            --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

        echo "Waiting for IAM role to propagate..."
        sleep 10
    fi

    ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)

    aws lambda create-function \
        --function-name $LAMBDA_FUNCTION_NAME \
        --runtime python3.11 \
        --role $ROLE_ARN \
        --handler lambda_handler.lambda_handler \
        --zip-file fileb://lambda.zip \
        --timeout 30 \
        --memory-size 512 \
        --region $REGION \
        --output json > /dev/null
fi

echo "✅ Lambda function deployed"

# Step 3: Create API Gateway
echo ""
echo "🌐 Step 3: Creating API Gateway..."

# Check if API exists
API_ID=$(aws apigatewayv2 get-apis --region $REGION --query "Items[?Name=='${API_NAME}'].ApiId" --output text)

if [ -z "$API_ID" ]; then
    API_ID=$(aws apigatewayv2 create-api \
        --name $API_NAME \
        --protocol-type HTTP \
        --region $REGION \
        --cors-configuration AllowOrigins='*',AllowMethods='GET,POST,OPTIONS',AllowHeaders='Content-Type' \
        --query 'ApiId' \
        --output text)
    echo "✅ API created: $API_ID"
else
    echo "✅ API already exists: $API_ID"
fi

# Step 4: Create Lambda integration
echo ""
echo "🔌 Step 4: Configuring API integration..."

LAMBDA_ARN=$(aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --region $REGION --query 'Configuration.FunctionArn' --output text)

# Create integration
INTEGRATION_ID=$(aws apigatewayv2 create-integration \
    --api-id $API_ID \
    --integration-type AWS_PROXY \
    --integration-uri $LAMBDA_ARN \
    --payload-format-version 2.0 \
    --region $REGION \
    --query 'IntegrationId' \
    --output text)

# Create route for /api/{proxy+}
aws apigatewayv2 create-route \
    --api-id $API_ID \
    --route-key 'ANY /api/{proxy+}' \
    --target "integrations/$INTEGRATION_ID" \
    --region $REGION \
    --output json > /dev/null

echo "✅ Integration configured"

# Step 5: Grant API Gateway permission to invoke Lambda
echo ""
echo "🔑 Step 5: Setting Lambda permissions..."

aws lambda add-permission \
    --function-name $LAMBDA_FUNCTION_NAME \
    --statement-id apigateway-invoke \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:${REGION}:*:${API_ID}/*/*" \
    --region $REGION \
    --output json > /dev/null 2>&1 || echo "Permission already exists"

# Step 6: Create deployment
echo ""
echo "🚀 Step 6: Deploying API..."

STAGE_NAME="prod"

aws apigatewayv2 create-stage \
    --api-id $API_ID \
    --stage-name $STAGE_NAME \
    --auto-deploy \
    --region $REGION \
    --output json > /dev/null 2>&1 || echo "Stage already exists"

API_ENDPOINT="https://${API_ID}.execute-api.${REGION}.amazonaws.com/${STAGE_NAME}"

echo "✅ API deployed"

# Output results
echo ""
echo "================================================"
echo "  ✅ API Gateway Deployment Complete!"
echo "================================================"
echo ""
echo "API Endpoint:"
echo "  $API_ENDPOINT"
echo ""
echo "Test the API:"
echo "  curl $API_ENDPOINT/api/health"
echo ""
echo "Next Steps:"
echo "  1. Update UI files with this API endpoint"
echo "  2. Redeploy UI with: ./deploy_ui.sh $ENVIRONMENT"
echo ""

# Save endpoint to file
echo "$API_ENDPOINT" > /tmp/api-gateway-url.txt
echo "API endpoint saved to: /tmp/api-gateway-url.txt"
