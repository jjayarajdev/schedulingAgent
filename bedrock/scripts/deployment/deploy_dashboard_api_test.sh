#!/bin/bash
# ==============================================================================
# Deploy Dashboard API Test - Single Lambda for "Show Me My Projects"
# ==============================================================================

set -e

echo "=================================="
echo "Dashboard API Deployment"
echo "=================================="

# Configuration
FUNCTION_NAME="pf-information-actions"
BEARER_TOKEN="TaDWx6r5O0WE2tb5/Lb77XuI29UR7j2NlMHbUdXd+YrYPR7ZdTrczgYigcaRHxvF4JIl7HafKfQQ/5LsVFFOZGD24DEJC28GMyszZP2MG/Qw0SE671I4y0BVXQk99DQxvgSrfBN2b5LlkPkMW9Ur6w76iPS2iRAFp42buydSNFiFxopFSw7jenDA+CnW1dpVVCwq8MPuGWPUuME0OsSp0HUKl6nq5ma6lKe2Mavvj+1arCjC7LvZ4WngVYwloD/Q+eZ8RJ6VABdKHizCsZhe3b1hvPTC7TbXvAN1kgyXIDKmVsw8zgW+HDUyaUbLcVgKHAQbdV3R+s9vez0hBhLp+ssIECoHUsjHsu0pFlMvvcpG+yxgkhOnf5u22jflQzdYyTPkluhwUZoWnYU0DGWbWmCttPsUijVL2qRluhgzP/Kt6aSN2pi2VnlAS6La6ABdQd0BUOr3O8bXTw7w3mwRlJIkfwOGEO8BBnXtCj2IOHjhUiJSQnY8UgXI+n/1+1YnJHunUH1g9/CagTvARvH72PUFgxSilKf5zpD4E5396lZ5uwsziz5z97tg9EZB0N1/1kyVonjtVmcdKkNsNpv32JQZR2DHf4FgKZgNslqAfZYkK9YkCg7x0dqbmqsmvM4dhM9VjwmhmaA9mShiOCEI4XBVAFyqLlDZnzlDEbEKVPrD+2+9pjNye5US2NPe63vaDDgTxIb11HB0ZjAxJNytIgL0sYVLdQOMcoEmFZ1/STB/+tGW0ucp3SbaeJlGeAXK"
CLIENT_ID="09PF05VD"

echo ""
echo "Step 1: Package Lambda function..."
cd lambda/information-actions
rm -f ../information-actions-deployment.zip

# Create deployment package
zip -r ../information-actions-deployment.zip . -x "*.pyc" -x "__pycache__/*" -x "*.md"

cd ../..

echo "✅ Lambda package created"

echo ""
echo "Step 2: Update Lambda code..."
aws lambda update-function-code \
  --function-name $FUNCTION_NAME \
  --zip-file fileb://lambda/information-actions-deployment.zip

echo "✅ Lambda code updated"

echo ""
echo "Step 3: Waiting for Lambda update to complete..."
aws lambda wait function-updated --function-name $FUNCTION_NAME

echo "✅ Lambda is ready"

echo ""
echo "Step 4: Update environment variables..."
aws lambda update-function-configuration \
  --function-name $FUNCTION_NAME \
  --environment "Variables={
    USE_MOCK_API=false,
    ENVIRONMENT=dev,
    BEARER_TOKEN=$BEARER_TOKEN,
    DEFAULT_CLIENT_ID=$CLIENT_ID,
    LOG_LEVEL=INFO,
    DYNAMODB_TABLE_PREFIX=pf
  }"

echo "✅ Environment variables updated"

echo ""
echo "Step 5: Waiting for configuration update..."
aws lambda wait function-updated --function-name $FUNCTION_NAME

echo "✅ Configuration is ready"

echo ""
echo "=================================="
echo "✅ Deployment Complete!"
echo "=================================="
echo ""
echo "Lambda Function: $FUNCTION_NAME"
echo "API Mode: REAL (USE_MOCK_API=false)"
echo "Environment: dev"
echo "Client ID: $CLIENT_ID"
echo "Bearer Token: Configured"
echo ""
echo "Next steps:"
echo "1. Test Lambda directly with test event"
echo "2. Test via Bedrock Agent"
echo ""

