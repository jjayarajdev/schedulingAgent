#!/bin/bash
# =============================================================================
# api.sh - API Gateway deployment functions for pf-manage.sh
# =============================================================================

# =============================================================================
# Helper Functions
# =============================================================================

# Build API Gateway name
api_name() {
    local base_name="$1"
    echo "${RESOURCE_PREFIX}-${base_name}-${ENVIRONMENT}"
}

# Get Lambda ARN
get_lambda_arn() {
    local fn_name="$1"
    aws lambda get-function --function-name "$fn_name" --query 'Configuration.FunctionArn' --output text 2>/dev/null
}

# Get AWS Account ID
get_account_id() {
    aws sts get-caller-identity --query Account --output text 2>/dev/null
}

# =============================================================================
# API Gateway Deployment Functions
# =============================================================================

# Deploy API Gateway for orchestrator
deploy_api_gateway() {
    log_section "Deploying API Gateway"

    local api_gw_name
    api_gw_name=$(api_name "orchestrator-api")
    local lambda_name
    lambda_name=$(resource_name "orchestrator")

    log_info "API Gateway: $api_gw_name"
    log_info "Target Lambda: $lambda_name"

    # Check if Lambda exists
    local lambda_arn
    lambda_arn=$(get_lambda_arn "$lambda_name")

    if [[ -z "$lambda_arn" ]]; then
        log_error "Lambda function $lambda_name not found. Deploy Lambda first."
        return 1
    fi

    log_info "Lambda ARN: $lambda_arn"

    local account_id
    account_id=$(get_account_id)

    # Check if API Gateway already exists
    local api_id
    api_id=$(aws apigateway get-rest-apis --query "items[?name=='$api_gw_name'].id" --output text 2>/dev/null)

    if [[ -n "$api_id" && "$api_id" != "None" ]]; then
        log_info "API Gateway already exists: $api_id"
        log_info "Updating existing API..."
        update_api_gateway "$api_id" "$lambda_arn" "$account_id"
    else
        log_info "Creating new API Gateway..."
        create_api_gateway "$api_gw_name" "$lambda_arn" "$account_id"
    fi
}

# Create new API Gateway
create_api_gateway() {
    local api_name="$1"
    local lambda_arn="$2"
    local account_id="$3"

    if [[ "$DRY_RUN" == "true" ]]; then
        dry_run_cmd "Create API Gateway" \
            "aws apigateway create-rest-api --name '$api_name' --description 'API Gateway for ProjectForce Orchestrator Lambda ($ENVIRONMENT)'"
        return 0
    fi

    # Create REST API
    local api_id
    api_id=$(aws apigateway create-rest-api \
        --name "$api_name" \
        --description "API Gateway for ProjectForce Orchestrator Lambda ($ENVIRONMENT)" \
        --endpoint-configuration types=REGIONAL \
        --query 'id' --output text)

    if [[ -z "$api_id" ]]; then
        log_error "Failed to create API Gateway"
        return 1
    fi

    log_info "Created API Gateway: $api_id"

    # Get root resource ID
    local root_id
    root_id=$(aws apigateway get-resources --rest-api-id "$api_id" \
        --query "items[?path=='/'].id" --output text)

    # Create /invoke-agent resource
    log_info "Creating /invoke-agent resource..."
    local invoke_resource_id
    invoke_resource_id=$(aws apigateway create-resource \
        --rest-api-id "$api_id" \
        --parent-id "$root_id" \
        --path-part "invoke-agent" \
        --query 'id' --output text)

    # Create /health resource
    log_info "Creating /health resource..."
    local health_resource_id
    health_resource_id=$(aws apigateway create-resource \
        --rest-api-id "$api_id" \
        --parent-id "$root_id" \
        --path-part "health" \
        --query 'id' --output text)

    # Setup /invoke-agent POST method
    setup_invoke_agent_method "$api_id" "$invoke_resource_id" "$lambda_arn" "$account_id"

    # Setup /invoke-agent OPTIONS method (CORS)
    setup_cors_options "$api_id" "$invoke_resource_id"

    # Setup /health GET method
    setup_health_method "$api_id" "$health_resource_id" "$lambda_arn" "$account_id"

    # Deploy to stage
    deploy_api_stage "$api_id"

    # Add Lambda permission for API Gateway
    add_lambda_permission "$lambda_arn" "$api_id" "$account_id"

    log_info "API Gateway deployment complete!"
    log_info "Endpoint: https://${api_id}.execute-api.${AWS_REGION}.amazonaws.com/${ENVIRONMENT}/invoke-agent"

    return 0
}

# Update existing API Gateway
update_api_gateway() {
    local api_id="$1"
    local lambda_arn="$2"
    local account_id="$3"

    if [[ "$DRY_RUN" == "true" ]]; then
        dry_run_cmd "Update API Gateway $api_id" \
            "aws apigateway update-integration --rest-api-id '$api_id' ..."
        return 0
    fi

    # Get resource IDs
    local invoke_resource_id
    invoke_resource_id=$(aws apigateway get-resources --rest-api-id "$api_id" \
        --query "items[?path=='/invoke-agent'].id" --output text 2>/dev/null)

    local health_resource_id
    health_resource_id=$(aws apigateway get-resources --rest-api-id "$api_id" \
        --query "items[?path=='/health'].id" --output text 2>/dev/null)

    local root_id
    root_id=$(aws apigateway get-resources --rest-api-id "$api_id" \
        --query "items[?path=='/'].id" --output text)

    # Create resources if they don't exist
    if [[ -z "$invoke_resource_id" || "$invoke_resource_id" == "None" ]]; then
        log_info "Creating /invoke-agent resource..."
        invoke_resource_id=$(aws apigateway create-resource \
            --rest-api-id "$api_id" \
            --parent-id "$root_id" \
            --path-part "invoke-agent" \
            --query 'id' --output text)
    fi

    if [[ -z "$health_resource_id" || "$health_resource_id" == "None" ]]; then
        log_info "Creating /health resource..."
        health_resource_id=$(aws apigateway create-resource \
            --rest-api-id "$api_id" \
            --parent-id "$root_id" \
            --path-part "health" \
            --query 'id' --output text)
    fi

    # Update integration URI for POST /invoke-agent
    local integration_uri="arn:aws:apigateway:${AWS_REGION}:lambda:path/2015-03-31/functions/${lambda_arn}/invocations"

    # Check if POST method exists
    if aws apigateway get-method --rest-api-id "$api_id" \
        --resource-id "$invoke_resource_id" --http-method POST &>/dev/null; then

        log_info "Updating POST /invoke-agent integration..."
        aws apigateway update-integration \
            --rest-api-id "$api_id" \
            --resource-id "$invoke_resource_id" \
            --http-method POST \
            --patch-operations "op=replace,path=/uri,value=$integration_uri" &>/dev/null || true
    else
        setup_invoke_agent_method "$api_id" "$invoke_resource_id" "$lambda_arn" "$account_id"
    fi

    # Check if OPTIONS method exists
    if ! aws apigateway get-method --rest-api-id "$api_id" \
        --resource-id "$invoke_resource_id" --http-method OPTIONS &>/dev/null; then
        setup_cors_options "$api_id" "$invoke_resource_id"
    fi

    # Check if GET /health exists
    if aws apigateway get-method --rest-api-id "$api_id" \
        --resource-id "$health_resource_id" --http-method GET &>/dev/null; then

        log_info "Updating GET /health integration..."
        aws apigateway update-integration \
            --rest-api-id "$api_id" \
            --resource-id "$health_resource_id" \
            --http-method GET \
            --patch-operations "op=replace,path=/uri,value=$integration_uri" &>/dev/null || true
    else
        setup_health_method "$api_id" "$health_resource_id" "$lambda_arn" "$account_id"
    fi

    # Redeploy to stage
    deploy_api_stage "$api_id"

    # Ensure Lambda permission exists
    add_lambda_permission "$lambda_arn" "$api_id" "$account_id"

    log_info "API Gateway update complete!"
    log_info "Endpoint: https://${api_id}.execute-api.${AWS_REGION}.amazonaws.com/${ENVIRONMENT}/invoke-agent"

    return 0
}

# Setup POST /invoke-agent method
setup_invoke_agent_method() {
    local api_id="$1"
    local resource_id="$2"
    local lambda_arn="$3"
    local account_id="$4"

    local integration_uri="arn:aws:apigateway:${AWS_REGION}:lambda:path/2015-03-31/functions/${lambda_arn}/invocations"

    log_info "Setting up POST /invoke-agent method..."

    # Create method
    aws apigateway put-method \
        --rest-api-id "$api_id" \
        --resource-id "$resource_id" \
        --http-method POST \
        --authorization-type NONE \
        --no-api-key-required &>/dev/null

    # Create integration
    aws apigateway put-integration \
        --rest-api-id "$api_id" \
        --resource-id "$resource_id" \
        --http-method POST \
        --type AWS_PROXY \
        --integration-http-method POST \
        --uri "$integration_uri" &>/dev/null

    # Create method response
    aws apigateway put-method-response \
        --rest-api-id "$api_id" \
        --resource-id "$resource_id" \
        --http-method POST \
        --status-code 200 \
        --response-models '{"application/json": "Empty"}' &>/dev/null

    log_info "POST /invoke-agent method configured"
}

# Setup GET /health method
setup_health_method() {
    local api_id="$1"
    local resource_id="$2"
    local lambda_arn="$3"
    local account_id="$4"

    local integration_uri="arn:aws:apigateway:${AWS_REGION}:lambda:path/2015-03-31/functions/${lambda_arn}/invocations"

    log_info "Setting up GET /health method..."

    # Create method
    aws apigateway put-method \
        --rest-api-id "$api_id" \
        --resource-id "$resource_id" \
        --http-method GET \
        --authorization-type NONE \
        --no-api-key-required &>/dev/null

    # Create integration
    aws apigateway put-integration \
        --rest-api-id "$api_id" \
        --resource-id "$resource_id" \
        --http-method GET \
        --type AWS_PROXY \
        --integration-http-method POST \
        --uri "$integration_uri" &>/dev/null

    # Create method response
    aws apigateway put-method-response \
        --rest-api-id "$api_id" \
        --resource-id "$resource_id" \
        --http-method GET \
        --status-code 200 \
        --response-models '{"application/json": "Empty"}' &>/dev/null

    log_info "GET /health method configured"
}

# Setup CORS OPTIONS method
setup_cors_options() {
    local api_id="$1"
    local resource_id="$2"

    log_info "Setting up OPTIONS method for CORS..."

    # Create OPTIONS method
    aws apigateway put-method \
        --rest-api-id "$api_id" \
        --resource-id "$resource_id" \
        --http-method OPTIONS \
        --authorization-type NONE \
        --no-api-key-required &>/dev/null

    # Create MOCK integration
    aws apigateway put-integration \
        --rest-api-id "$api_id" \
        --resource-id "$resource_id" \
        --http-method OPTIONS \
        --type MOCK \
        --request-templates '{"application/json": "{\"statusCode\": 200}"}' &>/dev/null

    # Create method response with CORS headers
    aws apigateway put-method-response \
        --rest-api-id "$api_id" \
        --resource-id "$resource_id" \
        --http-method OPTIONS \
        --status-code 200 \
        --response-parameters '{
            "method.response.header.Access-Control-Allow-Headers": false,
            "method.response.header.Access-Control-Allow-Methods": false,
            "method.response.header.Access-Control-Allow-Origin": false
        }' \
        --response-models '{"application/json": "Empty"}' &>/dev/null

    # Create integration response with CORS headers
    aws apigateway put-integration-response \
        --rest-api-id "$api_id" \
        --resource-id "$resource_id" \
        --http-method OPTIONS \
        --status-code 200 \
        --response-parameters '{
            "method.response.header.Access-Control-Allow-Headers": "'"'"'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"'"'",
            "method.response.header.Access-Control-Allow-Methods": "'"'"'POST,OPTIONS'"'"'",
            "method.response.header.Access-Control-Allow-Origin": "'"'"'*'"'"'"
        }' &>/dev/null

    log_info "OPTIONS method configured for CORS"
}

# Deploy API to stage
deploy_api_stage() {
    local api_id="$1"

    log_info "Deploying API to '$ENVIRONMENT' stage..."

    aws apigateway create-deployment \
        --rest-api-id "$api_id" \
        --stage-name "$ENVIRONMENT" \
        --description "Deployed by pf-manage.sh" &>/dev/null

    log_info "API deployed to stage: $ENVIRONMENT"
}

# Add Lambda permission for API Gateway invocation
add_lambda_permission() {
    local lambda_arn="$1"
    local api_id="$2"
    local account_id="$3"

    local lambda_name
    lambda_name=$(resource_name "orchestrator")
    local statement_id="apigateway-${api_id}-invoke"

    # Remove existing permission if any (ignore errors)
    aws lambda remove-permission \
        --function-name "$lambda_name" \
        --statement-id "$statement_id" 2>/dev/null || true

    # Add new permission
    log_info "Adding Lambda permission for API Gateway..."
    aws lambda add-permission \
        --function-name "$lambda_name" \
        --statement-id "$statement_id" \
        --action "lambda:InvokeFunction" \
        --principal "apigateway.amazonaws.com" \
        --source-arn "arn:aws:execute-api:${AWS_REGION}:${account_id}:${api_id}/*" &>/dev/null

    log_info "Lambda permission added"
}

# =============================================================================
# Cleanup Functions
# =============================================================================

cleanup_api_gateway() {
    log_section "Cleaning Up API Gateway"

    local api_gw_name
    api_gw_name=$(api_name "orchestrator-api")

    # Find API Gateway
    local api_id
    api_id=$(aws apigateway get-rest-apis --query "items[?name=='$api_gw_name'].id" --output text 2>/dev/null)

    if [[ -z "$api_id" || "$api_id" == "None" ]]; then
        log_info "API Gateway $api_gw_name not found (already deleted?)"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        dry_run_cmd "Delete API Gateway $api_gw_name" \
            "aws apigateway delete-rest-api --rest-api-id '$api_id'"
        return 0
    fi

    log_info "Deleting API Gateway: $api_gw_name ($api_id)"
    aws apigateway delete-rest-api --rest-api-id "$api_id"

    log_info "API Gateway deleted"
    return 0
}

# =============================================================================
# Validation Functions
# =============================================================================

validate_api_gateway() {
    log_section "Validating API Gateway"

    local api_gw_name
    api_gw_name=$(api_name "orchestrator-api")
    local lambda_name
    lambda_name=$(resource_name "orchestrator")

    local failed=0

    # Check if API exists
    local api_id
    api_id=$(aws apigateway get-rest-apis --query "items[?name=='$api_gw_name'].id" --output text 2>/dev/null)

    if [[ -z "$api_id" || "$api_id" == "None" ]]; then
        log_error "API Gateway $api_gw_name not found"
        return 1
    fi

    log_info "✓ API Gateway exists: $api_id"

    # Check /invoke-agent endpoint
    local invoke_id
    invoke_id=$(aws apigateway get-resources --rest-api-id "$api_id" \
        --query "items[?path=='/invoke-agent'].id" --output text 2>/dev/null)

    if [[ -n "$invoke_id" && "$invoke_id" != "None" ]]; then
        log_info "✓ /invoke-agent endpoint exists"

        # Check POST method
        if aws apigateway get-method --rest-api-id "$api_id" \
            --resource-id "$invoke_id" --http-method POST &>/dev/null; then
            log_info "✓ POST method configured"
        else
            log_error "✗ POST method not configured"
            ((failed++))
        fi

        # Check OPTIONS method (CORS)
        if aws apigateway get-method --rest-api-id "$api_id" \
            --resource-id "$invoke_id" --http-method OPTIONS &>/dev/null; then
            log_info "✓ OPTIONS method (CORS) configured"
        else
            log_warn "✗ OPTIONS method (CORS) not configured"
        fi
    else
        log_error "✗ /invoke-agent endpoint not found"
        ((failed++))
    fi

    # Check /health endpoint
    local health_id
    health_id=$(aws apigateway get-resources --rest-api-id "$api_id" \
        --query "items[?path=='/health'].id" --output text 2>/dev/null)

    if [[ -n "$health_id" && "$health_id" != "None" ]]; then
        log_info "✓ /health endpoint exists"
    else
        log_warn "✗ /health endpoint not found"
    fi

    # Check deployment stage
    if aws apigateway get-stage --rest-api-id "$api_id" --stage-name "$ENVIRONMENT" &>/dev/null; then
        log_info "✓ Stage '$ENVIRONMENT' deployed"
    else
        log_error "✗ Stage '$ENVIRONMENT' not deployed"
        ((failed++))
    fi

    # Print endpoint URL
    local endpoint="https://${api_id}.execute-api.${AWS_REGION}.amazonaws.com/${ENVIRONMENT}"
    log_info "API Endpoint: $endpoint"

    if [[ $failed -gt 0 ]]; then
        return 1
    fi

    return 0
}
