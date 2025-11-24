#!/bin/bash

###############################################################################
# deploy_api_gateway.sh - Deploy API Gateway for Orchestrator Lambda
###############################################################################
#
# Purpose: Create REST API Gateway with routes for orchestrator invocation
#
# Prerequisites:
#   - AWS CLI configured
#   - pf-orchestrator Lambda function deployed
#   - Proper IAM permissions
#
# Usage: ./deploy_api_gateway.sh [environment]
#
###############################################################################

set -e

# AWS Profile Support
AWS_PROFILE="${AWS_PROFILE:-}"

# Parse --profile parameter if present
ORIGINAL_ARGS=("$@")
while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            AWS_PROFILE="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done
# Restore original args for other parameter processing
set -- "${ORIGINAL_ARGS[@]}"

# AWS CLI wrapper function
aws_cmd() {
    if [[ -n "$AWS_PROFILE" ]]; then
        aws --profile "$AWS_PROFILE" "$@"
    else
        aws "$@"
    fi
}


# Configuration
ENV="${1:-dev}"
REGION="${AWS_REGION:-us-east-1}"
API_NAME="pf-orchestrator-api-${ENV}"
STAGE_NAME="${ENV}"
LAMBDA_FUNCTION_NAME="pf-orchestrator"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "================================================================================"
echo -e "${BLUE}API Gateway Deployment${NC}"
echo "================================================================================"
echo ""
echo "Environment:     $ENV"
echo "Region:          $REGION"
echo "API Name:        $API_NAME"
echo "Stage:           $STAGE_NAME"
echo "Lambda Function: $LAMBDA_FUNCTION_NAME"
echo ""

###############################################################################
# Step 1: Check if Lambda exists
###############################################################################

echo -e "${YELLOW}Step 1: Verifying Lambda function exists${NC}"
echo ""

if ! aws_cmd lambda get-function \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --region "$REGION" \
    &>/dev/null; then
    echo -e "${RED}✗ Lambda function not found: $LAMBDA_FUNCTION_NAME${NC}"
    echo ""
    echo "Please deploy the Orchestrator Lambda first:"
    echo "  ./scripts/DEPLOY.sh"
    echo ""
    exit 1
fi

LAMBDA_ARN=$(aws_cmd lambda get-function \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --region "$REGION" \
    --query 'Configuration.FunctionArn' \
    --output text)

echo -e "${GREEN}✓ Lambda function found${NC}"
echo "  ARN: $LAMBDA_ARN"
echo ""

###############################################################################
# Step 2: Create or Get REST API
###############################################################################

echo -e "${YELLOW}Step 2: Creating REST API${NC}"
echo ""

# Check if API already exists
EXISTING_API_ID=$(aws_cmd apigateway get-rest-apis \
    --region "$REGION" \
    --query "items[?name=='$API_NAME'].id" \
    --output text 2>/dev/null || echo "")

if [[ -n "$EXISTING_API_ID" && "$EXISTING_API_ID" != "None" ]]; then
    API_ID="$EXISTING_API_ID"
    echo -e "${GREEN}✓ REST API already exists: $API_ID${NC}"
else
    echo "  → Creating REST API: $API_NAME"

    API_ID=$(aws_cmd apigateway create-rest-api \
        --name "$API_NAME" \
        --description "API Gateway for ProjectForce Orchestrator Lambda ($ENV)" \
        --region "$REGION" \
        --endpoint-configuration types=REGIONAL \
        --query 'id' \
        --output text)

    echo -e "${GREEN}✓ REST API created: $API_ID${NC}"
fi

echo ""

# Get root resource ID
ROOT_RESOURCE_ID=$(aws_cmd apigateway get-resources \
    --rest-api-id "$API_ID" \
    --region "$REGION" \
    --query 'items[?path==`/`].id' \
    --output text)

echo "  Root Resource ID: $ROOT_RESOURCE_ID"
echo ""

###############################################################################
# Step 3: Create /invoke-agent Resource
###############################################################################

echo -e "${YELLOW}Step 3: Creating /invoke-agent resource${NC}"
echo ""

# Check if resource exists
INVOKE_RESOURCE_ID=$(aws_cmd apigateway get-resources \
    --rest-api-id "$API_ID" \
    --region "$REGION" \
    --query "items[?path=='/invoke-agent'].id" \
    --output text 2>/dev/null || echo "")

if [[ -n "$INVOKE_RESOURCE_ID" && "$INVOKE_RESOURCE_ID" != "None" ]]; then
    echo -e "${GREEN}✓ Resource already exists: /invoke-agent${NC}"
else
    echo "  → Creating resource: /invoke-agent"

    INVOKE_RESOURCE_ID=$(aws_cmd apigateway create-resource \
        --rest-api-id "$API_ID" \
        --parent-id "$ROOT_RESOURCE_ID" \
        --path-part "invoke-agent" \
        --region "$REGION" \
        --query 'id' \
        --output text)

    echo -e "${GREEN}✓ Resource created: $INVOKE_RESOURCE_ID${NC}"
fi

echo ""

###############################################################################
# Step 4: Create POST Method for /invoke-agent
###############################################################################

echo -e "${YELLOW}Step 4: Creating POST method${NC}"
echo ""

# Check if POST method exists
if aws_cmd apigateway get-method \
    --rest-api-id "$API_ID" \
    --resource-id "$INVOKE_RESOURCE_ID" \
    --http-method POST \
    --region "$REGION" \
    &>/dev/null; then
    echo "  → Deleting existing POST method to recreate"
    aws_cmd apigateway delete-method \
        --rest-api-id "$API_ID" \
        --resource-id "$INVOKE_RESOURCE_ID" \
        --http-method POST \
        --region "$REGION" \
        &>/dev/null || true
fi

echo "  → Creating POST method"

# Create POST method
aws_cmd apigateway put-method \
    --rest-api-id "$API_ID" \
    --resource-id "$INVOKE_RESOURCE_ID" \
    --http-method POST \
    --authorization-type NONE \
    --region "$REGION" \
    &>/dev/null

echo -e "${GREEN}✓ POST method created${NC}"
echo ""

# Create Lambda integration
echo "  → Creating Lambda integration"

AWS_ACCOUNT_ID=$(aws_cmd sts get-caller-identity --query Account --output text)
LAMBDA_URI="arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/${LAMBDA_ARN}/invocations"

aws_cmd apigateway put-integration \
    --rest-api-id "$API_ID" \
    --resource-id "$INVOKE_RESOURCE_ID" \
    --http-method POST \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "$LAMBDA_URI" \
    --region "$REGION" \
    &>/dev/null

echo -e "${GREEN}✓ Lambda integration created${NC}"
echo ""

###############################################################################
# Step 5: Create OPTIONS Method (CORS)
###############################################################################

echo -e "${YELLOW}Step 5: Configuring CORS (OPTIONS method)${NC}"
echo ""

# Delete existing OPTIONS method if present
if aws_cmd apigateway get-method \
    --rest-api-id "$API_ID" \
    --resource-id "$INVOKE_RESOURCE_ID" \
    --http-method OPTIONS \
    --region "$REGION" \
    &>/dev/null; then
    echo "  → Deleting existing OPTIONS method to recreate"
    aws_cmd apigateway delete-method \
        --rest-api-id "$API_ID" \
        --resource-id "$INVOKE_RESOURCE_ID" \
        --http-method OPTIONS \
        --region "$REGION" \
        &>/dev/null || true
fi

echo "  → Creating OPTIONS method"

# Create OPTIONS method
aws_cmd apigateway put-method \
    --rest-api-id "$API_ID" \
    --resource-id "$INVOKE_RESOURCE_ID" \
    --http-method OPTIONS \
    --authorization-type NONE \
    --region "$REGION" \
    &>/dev/null

# Create MOCK integration for OPTIONS
aws_cmd apigateway put-integration \
    --rest-api-id "$API_ID" \
    --resource-id "$INVOKE_RESOURCE_ID" \
    --http-method OPTIONS \
    --type MOCK \
    --region "$REGION" \
    --request-templates '{"application/json": "{\"statusCode\": 200}"}' \
    &>/dev/null

# Create OPTIONS method response
aws_cmd apigateway put-method-response \
    --rest-api-id "$API_ID" \
    --resource-id "$INVOKE_RESOURCE_ID" \
    --http-method OPTIONS \
    --status-code 200 \
    --region "$REGION" \
    --response-parameters \
        "method.response.header.Access-Control-Allow-Headers=false,method.response.header.Access-Control-Allow-Methods=false,method.response.header.Access-Control-Allow-Origin=false" \
    &>/dev/null

# Create OPTIONS integration response
aws_cmd apigateway put-integration-response \
    --rest-api-id "$API_ID" \
    --resource-id "$INVOKE_RESOURCE_ID" \
    --http-method OPTIONS \
    --status-code 200 \
    --region "$REGION" \
    --response-parameters \
        '{"method.response.header.Access-Control-Allow-Headers":"'"'"'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"'"'","method.response.header.Access-Control-Allow-Methods":"'"'"'POST,OPTIONS'"'"'","method.response.header.Access-Control-Allow-Origin":"'"'"'*'"'"'"}' \
    &>/dev/null

echo -e "${GREEN}✓ CORS configured${NC}"
echo ""

###############################################################################
# Step 6: Create /health Resource
###############################################################################

echo -e "${YELLOW}Step 6: Creating /health resource${NC}"
echo ""

# Check if resource exists
HEALTH_RESOURCE_ID=$(aws_cmd apigateway get-resources \
    --rest-api-id "$API_ID" \
    --region "$REGION" \
    --query "items[?path=='/health'].id" \
    --output text 2>/dev/null || echo "")

if [[ -n "$HEALTH_RESOURCE_ID" && "$HEALTH_RESOURCE_ID" != "None" ]]; then
    echo -e "${GREEN}✓ Resource already exists: /health${NC}"
else
    echo "  → Creating resource: /health"

    HEALTH_RESOURCE_ID=$(aws_cmd apigateway create-resource \
        --rest-api-id "$API_ID" \
        --parent-id "$ROOT_RESOURCE_ID" \
        --path-part "health" \
        --region "$REGION" \
        --query 'id' \
        --output text)

    echo -e "${GREEN}✓ Resource created: $HEALTH_RESOURCE_ID${NC}"
fi

echo ""

###############################################################################
# Step 7: Create GET Method for /health
###############################################################################

echo -e "${YELLOW}Step 7: Creating GET method for /health${NC}"
echo ""

# Check if GET method exists
if aws_cmd apigateway get-method \
    --rest-api-id "$API_ID" \
    --resource-id "$HEALTH_RESOURCE_ID" \
    --http-method GET \
    --region "$REGION" \
    &>/dev/null; then
    echo "  → Deleting existing GET method to recreate"
    aws_cmd apigateway delete-method \
        --rest-api-id "$API_ID" \
        --resource-id "$HEALTH_RESOURCE_ID" \
        --http-method GET \
        --region "$REGION" \
        &>/dev/null || true
fi

echo "  → Creating GET method"

# Create GET method
aws_cmd apigateway put-method \
    --rest-api-id "$API_ID" \
    --resource-id "$HEALTH_RESOURCE_ID" \
    --http-method GET \
    --authorization-type NONE \
    --region "$REGION" \
    &>/dev/null

# Create Lambda integration for GET
aws_cmd apigateway put-integration \
    --rest-api-id "$API_ID" \
    --resource-id "$HEALTH_RESOURCE_ID" \
    --http-method GET \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "$LAMBDA_URI" \
    --region "$REGION" \
    &>/dev/null

echo -e "${GREEN}✓ GET method created${NC}"
echo ""

###############################################################################
# Step 8: Add Lambda Permission for API Gateway
###############################################################################

echo -e "${YELLOW}Step 8: Adding Lambda permissions${NC}"
echo ""

# Remove existing permission if present
aws_cmd lambda remove-permission \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --statement-id "apigateway-invoke-${API_ID}" \
    --region "$REGION" \
    &>/dev/null || true

echo "  → Adding API Gateway invoke permission"

# Add permission for API Gateway to invoke Lambda
aws_cmd lambda add-permission \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --statement-id "apigateway-invoke-${API_ID}" \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:${REGION}:${AWS_ACCOUNT_ID}:${API_ID}/*" \
    --region "$REGION" \
    &>/dev/null

echo -e "${GREEN}✓ Lambda permission added${NC}"
echo ""

###############################################################################
# Step 9: Deploy API to Stage
###############################################################################

echo -e "${YELLOW}Step 9: Deploying API to stage: $STAGE_NAME${NC}"
echo ""

echo "  → Creating deployment"

aws_cmd apigateway create-deployment \
    --rest-api-id "$API_ID" \
    --stage-name "$STAGE_NAME" \
    --description "Deployment for $ENV environment" \
    --region "$REGION" \
    &>/dev/null

echo -e "${GREEN}✓ API deployed to stage: $STAGE_NAME${NC}"
echo ""

###############################################################################
# Step 10: Get API Endpoint
###############################################################################

API_ENDPOINT="https://${API_ID}.execute-api.${REGION}.amazonaws.com/${STAGE_NAME}"

echo ""
echo "================================================================================"
echo -e "${GREEN}✓ API Gateway Deployment Complete!${NC}"
echo "================================================================================"
echo ""
echo "API Details:"
echo "  • API ID:        $API_ID"
echo "  • API Name:      $API_NAME"
echo "  • Stage:         $STAGE_NAME"
echo "  • Region:        $REGION"
echo ""
echo "API Endpoints:"
echo "  • POST Endpoint: ${API_ENDPOINT}/invoke-agent"
echo "  • Health Check:  ${API_ENDPOINT}/health"
echo ""
echo "================================================================================"
echo -e "${GREEN}Testing Instructions:${NC}"
echo "================================================================================"
echo ""
echo "1. Test Health Check:"
echo ""
echo -e "${YELLOW}curl ${API_ENDPOINT}/health${NC}"
echo ""
echo "2. Test Orchestrator Invocation:"
echo ""
echo -e "${YELLOW}curl -X POST ${API_ENDPOINT}/invoke-agent \\\\${NC}"
echo -e "${YELLOW}  -H \"Content-Type: application/json\" \\\\${NC}"
echo -e "${YELLOW}  -d '{${NC}"
echo -e "${YELLOW}    \"message\": \"show my projects\",${NC}"
echo -e "${YELLOW}    \"session_id\": \"test-session-1\",${NC}"
echo -e "${YELLOW}    \"pf_token\": \"YOUR_BEARER_TOKEN\",${NC}"
echo -e "${YELLOW}    \"pf_client_id\": \"09PF05VD\",${NC}"
echo -e "${YELLOW}    \"pf_user_id\": 1646085${NC}"
echo -e "${YELLOW}  }'${NC}"
echo ""
echo "3. Test with Filtering:"
echo ""
echo -e "${YELLOW}curl -X POST ${API_ENDPOINT}/invoke-agent \\\\${NC}"
echo -e "${YELLOW}  -H \"Content-Type: application/json\" \\\\${NC}"
echo -e "${YELLOW}  -d '{${NC}"
echo -e "${YELLOW}    \"message\": \"show scheduled projects\",${NC}"
echo -e "${YELLOW}    \"session_id\": \"test-session-2\",${NC}"
echo -e "${YELLOW}    \"pf_token\": \"YOUR_BEARER_TOKEN\",${NC}"
echo -e "${YELLOW}    \"pf_client_id\": \"09PF05VD\",${NC}"
echo -e "${YELLOW}    \"pf_user_id\": 1646085${NC}"
echo -e "${YELLOW}  }'${NC}"
echo ""
echo "================================================================================"
echo -e "${GREEN}Configuration Updates:${NC}"
echo "================================================================================"
echo ""
echo "1. Update UI configuration to use API Gateway endpoint:"
echo ""
echo "   File: testing/ui/agent_ui.html"
echo "   Replace: const API_URL = 'http://localhost:5003/api/invoke-agent'"
echo "   With:    const API_URL = '${API_ENDPOINT}/invoke-agent'"
echo ""
echo "2. Update Orchestrator Lambda environment variables (if not set):"
echo ""
echo -e "${YELLOW}aws lambda update-function-configuration \\\\${NC}"
echo -e "${YELLOW}  --function-name pf-orchestrator \\\\${NC}"
echo -e "${YELLOW}  --environment Variables='{${NC}"
echo -e "${YELLOW}    \"REDIS_ENDPOINT\":\"your-redis-endpoint\",${NC}"
echo -e "${YELLOW}    \"REDIS_PORT\":\"6379\",${NC}"
echo -e "${YELLOW}    \"REDIS_SSL\":\"true\",${NC}"
echo -e "${YELLOW}    \"SUPERVISOR_AGENT_ID\":\"CRKFEYCNTV\",${NC}"
echo -e "${YELLOW}    \"SCHEDULING_AGENT_ID\":\"MTZGUHW3FK\",${NC}"
echo -e "${YELLOW}    \"INFORMATION_AGENT_ID\":\"HQPYL61L5B\",${NC}"
echo -e "${YELLOW}    \"CHITCHAT_AGENT_ID\":\"SPE68WI5TY\",${NC}"
echo -e "${YELLOW}    \"SCHEDULING_LAMBDA_NAME\":\"pf-scheduling-actions\",${NC}"
echo -e "${YELLOW}    \"INFORMATION_LAMBDA_NAME\":\"pf-information-actions\",${NC}"
echo -e "${YELLOW}    \"AWS_REGION\":\"${REGION}\",${NC}"
echo -e "${YELLOW}    \"USE_SUPERVISOR\":\"false\",${NC}"
echo -e "${YELLOW}    \"ALLOW_DIRECT_LAMBDA\":\"true\",${NC}"
echo -e "${YELLOW}    \"ROUTING_METHOD\":\"hybrid\"${NC}"
echo -e "${YELLOW}  }'${NC}"
echo ""
echo "================================================================================"
echo -e "${GREEN}Monitoring:${NC}"
echo "================================================================================"
echo ""
echo "• CloudWatch Logs (API Gateway):"
echo "  aws_cmd logs tail \"/aws/apigateway/${API_ID}\" --follow"
echo ""
echo "• CloudWatch Logs (Orchestrator Lambda):"
echo "  aws_cmd logs tail \"/aws/lambda/pf-orchestrator\" --follow"
echo ""
echo "• API Gateway Metrics (AWS Console):"
echo "  https://console.aws.amazon.com/apigateway/home?region=${REGION}#/apis/${API_ID}/dashboard"
echo ""
echo "================================================================================"
echo ""

###############################################################################
# Step 11: Update UI Configuration (Optional)
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BEDROCK_DIR="$(dirname "$SCRIPT_DIR")"
UI_FILE="$BEDROCK_DIR/testing/ui/index.html"

if [[ -f "$UI_FILE" ]]; then
    echo "================================================================================"
    echo -e "${YELLOW}Step 11: Updating UI Configuration${NC}"
    echo "================================================================================"
    echo ""

    # Check if API_URL needs updating
    if grep -q "const API_URL = 'http://localhost:5003" "$UI_FILE"; then
        echo "  → Updating UI to use API Gateway endpoint..."

        # Backup original file
        cp "$UI_FILE" "${UI_FILE}.backup"

        # Update API_URL
        sed -i.tmp "s|const API_URL = 'http://localhost:5003/api'|const API_URL = '${API_ENDPOINT}'|g" "$UI_FILE"
        rm -f "${UI_FILE}.tmp"

        echo -e "${GREEN}  ✅ UI configuration updated${NC}"
        echo "  • File: testing/ui/index.html"
        echo "  • Old: http://localhost:5003/api"
        echo "  • New: ${API_ENDPOINT}"
        echo "  • Backup: testing/ui/index.html.backup"
    else
        echo -e "${GREEN}  ℹ️  UI already configured for API Gateway${NC}"
    fi
    echo ""
fi

echo "================================================================================"
echo ""
