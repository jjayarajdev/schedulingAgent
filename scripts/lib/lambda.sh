#!/bin/bash
# =============================================================================
# lambda.sh - Lambda function deployment and cleanup
# =============================================================================
# Compatible with bash 3.2+ (macOS default)

# Lambda function BASE definitions (without prefix/environment)
# Format: base_name:source_dir:role_base:timeout:memory
# Actual names will be: ${RESOURCE_PREFIX}-${base_name}-${ENVIRONMENT}
LAMBDA_FUNCTION_LIST=(
    "orchestrator:lambda/orchestrator:orchestrator:120:512"
    "scheduling-actions:lambda/scheduling-actions:scheduling-actions:60:1769"
    "information-actions:lambda/information-actions:information-actions:60:1769"
    "chitchat-actions:lambda/chitchat-actions:chitchat-actions:60:1769"
    "notes-actions:lambda/notes-actions:notes-actions:60:512"
    "vapi-webhook:lambda/vapi-webhook:vapi-webhook:30:256"
)

# DynamoDB table BASE names (without prefix/environment)
# Actual names will be: ${RESOURCE_PREFIX}-${base_name}-${ENVIRONMENT}
LAMBDA_DYNAMODB_TABLE_BASES=(
    "sessions"
    "workflow-states"
    "project-notes"
)

# Build full Lambda function name from base
# Usage: func_name=$(lambda_name "orchestrator")
lambda_name() {
    local base="$1"
    resource_name "$base"
}

# Get environment variables for a Lambda function based on its role base
# Usage: env_vars=$(get_lambda_env_vars "orchestrator")
#
# MULTI-REGION NOTE:
# - Core Lambdas (orchestrator, action Lambdas) run in CORE_REGION (us-east-2)
# - Voice/SMS Lambdas run in VOICE_REGION (us-east-1)
# - Voice/SMS Lambdas need full ARN to invoke orchestrator cross-region
get_lambda_env_vars() {
    local role_base="$1"
    local env_vars=""

    # Full ARN for cross-region orchestrator invocation
    local orchestrator_arn="arn:aws:lambda:${CORE_REGION}:${EXPECTED_ACCOUNT}:function:$(lambda_name 'orchestrator')"

    case "$role_base" in
        "orchestrator")
            # Core region Lambda - invokes other core Lambdas in same region
            # NOTE: AWS_REGION is reserved by Lambda and set automatically - do not include
            env_vars="REGION=${CORE_REGION}"
            env_vars="${env_vars},DYNAMODB_TABLE=$(table_name 'sessions')"
            env_vars="${env_vars},WORKFLOW_STATE_TABLE=$(table_name 'workflow-states')"
            env_vars="${env_vars},SCHEDULING_LAMBDA=$(lambda_name 'scheduling-actions')"
            env_vars="${env_vars},INFORMATION_LAMBDA=$(lambda_name 'information-actions')"
            env_vars="${env_vars},CHITCHAT_LAMBDA=$(lambda_name 'chitchat-actions')"
            env_vars="${env_vars},NOTES_LAMBDA=$(lambda_name 'notes-actions')"
            env_vars="${env_vars},ORCHESTRATOR_MODEL=us.anthropic.claude-3-5-sonnet-20241022-v2:0"
            env_vars="${env_vars},BEDROCK_REGION=${CORE_REGION}"
            env_vars="${env_vars},ALLOW_DIRECT_LAMBDA=true"
            env_vars="${env_vars},USE_SUPERVISOR=false"
            env_vars="${env_vars},ENABLE_MULTI_AGENT_ORCHESTRATION=false"
            ;;
        "scheduling-actions"|"information-actions"|"chitchat-actions")
            # Core region Lambdas
            env_vars="ENVIRONMENT=${ENVIRONMENT}"
            env_vars="${env_vars},USE_MOCK_API=false"
            env_vars="${env_vars},DEFAULT_CLIENT_ID=09PF05VD"
            env_vars="${env_vars},DYNAMODB_TABLE=$(table_name 'sessions')"
            env_vars="${env_vars},SECRET_NAME=${SECRETS_NAME:-projectforce/api/credentials}"
            env_vars="${env_vars},SECRETS_REGION=${SECRETS_REGION:-us-east-2}"
            env_vars="${env_vars},REGION=${CORE_REGION}"
            ;;
        "notes-actions")
            # Core region Lambda
            env_vars="ENVIRONMENT=${ENVIRONMENT}"
            env_vars="${env_vars},USE_MOCK_API=false"
            env_vars="${env_vars},DEFAULT_CLIENT_ID=09PF05VD"
            env_vars="${env_vars},DYNAMODB_TABLE=$(table_name 'project-notes')"
            env_vars="${env_vars},RESOURCE_PREFIX=${RESOURCE_PREFIX}"
            env_vars="${env_vars},SECRET_NAME=${SECRETS_NAME:-projectforce/api/credentials}"
            env_vars="${env_vars},SECRETS_REGION=${SECRETS_REGION:-us-east-2}"
            env_vars="${env_vars},REGION=${CORE_REGION}"
            ;;
        "lex-fulfillment")
            # Voice region Lambda - needs cross-region ARN to invoke orchestrator
            env_vars="ENVIRONMENT=${ENVIRONMENT}"
            env_vars="${env_vars},ORCHESTRATOR_LAMBDA=${orchestrator_arn}"
            env_vars="${env_vars},ORCHESTRATOR_REGION=${CORE_REGION}"
            env_vars="${env_vars},DYNAMODB_TABLE=$(table_name 'sessions')"
            env_vars="${env_vars},DYNAMODB_REGION=${CORE_REGION}"
            env_vars="${env_vars},SECRETS_REGION=${SECRETS_REGION:-us-east-2}"
            env_vars="${env_vars},REGION=${VOICE_REGION}"
            ;;
        "customer-lookup")
            # Voice region Lambda
            env_vars="ENVIRONMENT=${ENVIRONMENT}"
            env_vars="${env_vars},CUSTOMERS_TABLE=$(table_name 'customers')"
            env_vars="${env_vars},DYNAMODB_REGION=${CORE_REGION}"
            env_vars="${env_vars},REGION=${VOICE_REGION}"
            ;;
        "voice-bedrock-bridge")
            # Voice region Lambda - calls Bedrock in core region
            env_vars="ENVIRONMENT=${ENVIRONMENT}"
            env_vars="${env_vars},BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0"
            env_vars="${env_vars},BEDROCK_REGION=${CORE_REGION}"
            env_vars="${env_vars},DYNAMODB_TABLE=$(table_name 'sessions')"
            env_vars="${env_vars},DYNAMODB_REGION=${CORE_REGION}"
            env_vars="${env_vars},REGION=${VOICE_REGION}"
            ;;
        "sms-inbound")
            # Voice region Lambda - needs cross-region ARN to invoke orchestrator
            # SMS DynamoDB tables are in CORE_REGION (us-east-2), same as all other DynamoDB tables
            env_vars="ENVIRONMENT=${ENVIRONMENT}"
            env_vars="${env_vars},ORCHESTRATOR_LAMBDA=${orchestrator_arn}"
            env_vars="${env_vars},ORCHESTRATOR_REGION=${CORE_REGION}"
            env_vars="${env_vars},SMS_SESSIONS_TABLE=$(table_name 'sms-sessions')"
            env_vars="${env_vars},SESSIONS_TABLE=$(table_name 'sms-sessions')"
            env_vars="${env_vars},CONSENT_TABLE=$(table_name 'sms-consent')"
            env_vars="${env_vars},MESSAGES_TABLE=$(table_name 'sms-messages')"
            env_vars="${env_vars},OPT_OUT_TRACKING_TABLE=$(table_name 'opt-out-tracking')"
            env_vars="${env_vars},DYNAMODB_REGION=${CORE_REGION}"
            env_vars="${env_vars},ORIGINATION_NUMBER=${SMS_PHONE_NUMBER:-+18786789053}"
            env_vars="${env_vars},PF_SECRET_NAME=${SECRETS_NAME:-projectforce/api/credentials}"
            env_vars="${env_vars},SECRETS_REGION=${SECRETS_REGION:-us-east-2}"
            env_vars="${env_vars},AWS_REGION_NAME=${VOICE_REGION}"
            env_vars="${env_vars},REGION=${VOICE_REGION}"
            ;;
        "vapi-webhook")
            # Voice region Lambda - VAPI/Twilio voice webhook
            # Receives calls from VAPI, authenticates via phone-call-login, invokes orchestrator
            env_vars="ENVIRONMENT=${ENVIRONMENT}"
            env_vars="${env_vars},ORCHESTRATOR_LAMBDA=${orchestrator_arn}"
            env_vars="${env_vars},ORCHESTRATOR_REGION=${CORE_REGION}"
            env_vars="${env_vars},TWILIO_NUMBER=${TWILIO_PHONE_NUMBER:-+12185516488}"
            env_vars="${env_vars},PF_SECRET_NAME=${SECRETS_NAME:-projectforce/api/credentials}"
            env_vars="${env_vars},SECRETS_REGION=${SECRETS_REGION:-us-east-2}"
            env_vars="${env_vars},LOG_LEVEL=INFO"
            env_vars="${env_vars},REGION=${VOICE_REGION}"
            ;;
        *)
            env_vars="ENVIRONMENT=${ENVIRONMENT}"
            env_vars="${env_vars},REGION=${CORE_REGION}"
            ;;
    esac

    echo "$env_vars"
}

# Get list of full Lambda function names
get_lambda_function_names() {
    local names=()
    for entry in "${LAMBDA_FUNCTION_LIST[@]}"; do
        IFS=':' read -r base_name source_dir role_base timeout memory <<< "$entry"
        names+=("$(lambda_name "$base_name")")
    done
    echo "${names[@]}"
}

# Get list of full DynamoDB table names
get_lambda_table_names() {
    local names=()
    for base in "${LAMBDA_DYNAMODB_TABLE_BASES[@]}"; do
        names+=("$(table_name "$base")")
    done
    echo "${names[@]}"
}

# =============================================================================
# Lambda Deployment
# =============================================================================

# Deploy a single Lambda function
# Usage: deploy_lambda <func_name> <source_dir> <role_name> <timeout> <memory> [role_base] [deploy_region]
#
# MULTI-REGION: Core Lambdas deploy to CORE_REGION, Voice/SMS Lambdas to VOICE_REGION
deploy_lambda() {
    local func_name="$1"
    local source_dir="$2"
    local role_name="$3"
    local timeout="${4:-60}"
    local memory="${5:-512}"
    local role_base="${6:-}"
    local deploy_region="${7:-$CORE_REGION}"

    local project_root
    project_root="$(get_project_root)"
    local full_source_path="$project_root/$source_dir"
    local zip_file="/tmp/${func_name}.zip"
    local role_arn="arn:aws:iam::${EXPECTED_ACCOUNT}:role/${role_name}"

    log_info "Deploying Lambda: $func_name (region: $deploy_region)"
    log_debug "  Source: $full_source_path"
    log_debug "  Role: $role_name"
    log_debug "  Timeout: ${timeout}s, Memory: ${memory}MB"

    # Validate source directory
    if [[ ! -d "$full_source_path" ]]; then
        log_error "Source directory not found: $full_source_path"
        return 1
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Deploy Lambda: $func_name"
        echo -e "${YELLOW}  # Create deployment package with dependencies${NC}"
        case "$role_base" in
            "scheduling-actions"|"information-actions"|"notes-actions")
                echo -e "${YELLOW}  \$ pip3 install -t /tmp/${func_name}-build requests${NC}"
                ;;
        esac
        echo -e "${YELLOW}  \$ cp \"$full_source_path\"/*.py /tmp/${func_name}-build/${NC}"
        echo -e "${YELLOW}  \$ cd /tmp/${func_name}-build && zip -r \"$zip_file\" . -x \"*.pyc\" -x \"__pycache__/*\"${NC}"
        echo ""
        echo -e "${YELLOW}  # Create or update Lambda function${NC}"
        echo -e "${YELLOW}  \$ aws lambda create-function \\\\${NC}"
        echo -e "${YELLOW}      --function-name \"$func_name\" \\\\${NC}"
        echo -e "${YELLOW}      --runtime python3.11 \\\\${NC}"
        echo -e "${YELLOW}      --role \"$role_arn\" \\\\${NC}"
        echo -e "${YELLOW}      --handler handler.lambda_handler \\\\${NC}"
        echo -e "${YELLOW}      --zip-file \"fileb://$zip_file\" \\\\${NC}"
        echo -e "${YELLOW}      --timeout $timeout \\\\${NC}"
        echo -e "${YELLOW}      --memory-size $memory \\\\${NC}"
        echo -e "${YELLOW}      --region \"$deploy_region\"${NC}"
        echo ""
        echo -e "${YELLOW}  # OR update existing function${NC}"
        echo -e "${YELLOW}  \$ aws lambda update-function-code --function-name \"$func_name\" --zip-file \"fileb://$zip_file\" --region \"$deploy_region\"${NC}"
        echo -e "${YELLOW}  \$ aws lambda update-function-configuration --function-name \"$func_name\" --timeout $timeout --memory-size $memory --region \"$deploy_region\"${NC}"
        echo ""
        return 0
    fi

    # Create zip package with dependencies
    log_debug "Creating deployment package..."
    rm -f "$zip_file"

    local build_dir="/tmp/${func_name}-build"
    rm -rf "$build_dir"
    mkdir -p "$build_dir"

    # Check if Lambda needs external dependencies (scheduling-actions, information-actions, notes-actions need requests)
    local needs_requests=false
    case "$role_base" in
        "scheduling-actions"|"information-actions"|"notes-actions")
            needs_requests=true
            ;;
    esac

    # Install Python dependencies if needed
    if [[ "$needs_requests" == "true" ]]; then
        log_debug "Installing Python dependencies (requests)..."
        pip3 install -t "$build_dir" requests --quiet 2>/dev/null
    fi

    # Copy source files
    cp -r "$full_source_path"/*.py "$build_dir/" 2>/dev/null || true

    # Create zip from build directory
    (cd "$build_dir" && zip -r "$zip_file" . -x "*.pyc" -x "__pycache__/*" -x "*.git*" -x "tests/*") &>/dev/null

    # Cleanup build directory
    rm -rf "$build_dir"

    if [[ ! -f "$zip_file" ]]; then
        log_error "Failed to create deployment package"
        return 1
    fi

    # Get environment variables for this function
    local env_vars=""
    if [[ -n "$role_base" ]]; then
        env_vars=$(get_lambda_env_vars "$role_base")
    fi

    # Check if function exists
    if aws lambda get-function --function-name "$func_name" --region "$deploy_region" &>/dev/null; then
        # Update existing function
        log_debug "Updating existing function..."
        local update_output
        update_output=$(aws lambda update-function-code \
            --function-name "$func_name" \
            --zip-file "fileb://$zip_file" \
            --region "$deploy_region" \
            --output text 2>&1)
        if [[ $? -ne 0 ]]; then
            log_error "Failed to update Lambda code: $func_name"
            log_error "Error: $update_output"
            return 1
        fi

        # Wait for update to complete
        aws lambda wait function-updated --function-name "$func_name" --region "$deploy_region" 2>/dev/null || sleep 5

        # Update configuration including environment variables
        local config_output
        if [[ -n "$env_vars" ]]; then
            config_output=$(aws lambda update-function-configuration \
                --function-name "$func_name" \
                --timeout "$timeout" \
                --memory-size "$memory" \
                --environment "Variables={$env_vars}" \
                --region "$deploy_region" \
                --output text 2>&1)
        else
            config_output=$(aws lambda update-function-configuration \
                --function-name "$func_name" \
                --timeout "$timeout" \
                --memory-size "$memory" \
                --region "$deploy_region" \
                --output text 2>&1)
        fi
        if [[ $? -ne 0 ]]; then
            log_error "Failed to update Lambda configuration: $func_name"
            log_error "Error: $config_output"
            return 1
        fi
    else
        # Create new function
        log_debug "Creating new function..."

        # Ensure role exists and has correct policies
        if ! aws iam get-role --role-name "$role_name" &>/dev/null; then
            log_info "Creating IAM role: $role_name"
            create_lambda_role "$role_name"
        fi

        # Configure role-specific policies
        if [[ -n "$role_base" ]]; then
            ensure_role_policies "$role_base" "$role_name"
        fi

        # Create function with environment variables
        local create_output
        local create_result
        if [[ -n "$env_vars" ]]; then
            create_output=$(aws lambda create-function \
                --function-name "$func_name" \
                --runtime python3.11 \
                --role "$role_arn" \
                --handler handler.lambda_handler \
                --zip-file "fileb://$zip_file" \
                --timeout "$timeout" \
                --memory-size "$memory" \
                --environment "Variables={$env_vars}" \
                --region "$deploy_region" \
                --output text 2>&1)
            create_result=$?
        else
            create_output=$(aws lambda create-function \
                --function-name "$func_name" \
                --runtime python3.11 \
                --role "$role_arn" \
                --handler handler.lambda_handler \
                --zip-file "fileb://$zip_file" \
                --timeout "$timeout" \
                --memory-size "$memory" \
                --region "$deploy_region" \
                --output text 2>&1)
            create_result=$?
        fi

        if [[ $create_result -ne 0 ]]; then
            log_error "Failed to create Lambda function: $func_name"
            log_error "Error: $create_output"
            return 1
        fi

        # Wait for function to be active
        aws lambda wait function-active --function-name "$func_name" --region "$deploy_region" 2>/dev/null || sleep 5
    fi

    # Cleanup
    rm -f "$zip_file"

    log_info "Lambda $func_name deployed successfully"
    return 0
}

# Get deployment region for a Lambda based on its role
# Voice/SMS Lambdas deploy to VOICE_REGION, others to CORE_REGION
get_lambda_deploy_region() {
    local role_base="$1"
    case "$role_base" in
        "vapi-webhook"|"lex-fulfillment"|"sms-inbound"|"customer-lookup"|"voice-bedrock-bridge")
            echo "$VOICE_REGION"
            ;;
        *)
            echo "$CORE_REGION"
            ;;
    esac
}

# Deploy all Lambda functions
# Core Lambdas deploy to CORE_REGION (us-east-2)
# Voice/SMS Lambdas deploy to VOICE_REGION (us-east-1)
deploy_all_lambdas() {
    log_section "Deploying Lambda Functions"
    print_naming_config
    log_info "Core region: $CORE_REGION, Voice region: $VOICE_REGION"

    local failed=0

    # Deploy DynamoDB tables first (to CORE_REGION)
    deploy_lambda_dynamodb_tables

    # Deploy each Lambda function to appropriate region
    for entry in "${LAMBDA_FUNCTION_LIST[@]}"; do
        IFS=':' read -r base_name source_dir role_base timeout memory <<< "$entry"
        local func_name=$(lambda_name "$base_name")
        local full_role_name=$(role_name "$role_base")
        local deploy_region=$(get_lambda_deploy_region "$role_base")
        deploy_lambda "$func_name" "$source_dir" "$full_role_name" "$timeout" "$memory" "$role_base" "$deploy_region" || ((failed++))
    done

    if [[ $failed -gt 0 ]]; then
        log_error "Failed to deploy $failed Lambda function(s)"
        return 1
    fi

    log_info "All Lambda functions deployed successfully"
    return 0
}

# Deploy Lambda-related DynamoDB tables
deploy_lambda_dynamodb_tables() {
    log_info "Deploying DynamoDB tables for Lambda..."

    for base in "${LAMBDA_DYNAMODB_TABLE_BASES[@]}"; do
        local full_table_name=$(table_name "$base")
        deploy_dynamodb_table "$full_table_name"
    done
}

# Deploy a single DynamoDB table
# DynamoDB tables deploy to CORE_REGION
deploy_dynamodb_table() {
    local table_name="$1"

    if aws dynamodb describe-table --table-name "$table_name" --region "$CORE_REGION" &>/dev/null; then
        log_info "Table $table_name already exists in $CORE_REGION - skipping"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Create DynamoDB table: $table_name (region: $CORE_REGION)"
        echo -e "${YELLOW}  \$ aws dynamodb create-table \\\\${NC}"
        echo -e "${YELLOW}      --table-name \"$table_name\" \\\\${NC}"
        echo -e "${YELLOW}      --attribute-definitions AttributeName=session_id,AttributeType=S \\\\${NC}"
        echo -e "${YELLOW}      --key-schema AttributeName=session_id,KeyType=HASH \\\\${NC}"
        echo -e "${YELLOW}      --billing-mode PAY_PER_REQUEST \\\\${NC}"
        echo -e "${YELLOW}      --region \"$CORE_REGION\"${NC}"
        echo ""
        return 0
    fi

    log_info "Creating DynamoDB table: $table_name (region: $CORE_REGION)"

    # Default table schema (session-based)
    local create_output
    create_output=$(aws dynamodb create-table \
        --table-name "$table_name" \
        --attribute-definitions AttributeName=session_id,AttributeType=S \
        --key-schema AttributeName=session_id,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region "$CORE_REGION" \
        --output text 2>&1)

    local create_result=$?
    if [[ $create_result -ne 0 ]]; then
        log_error "Failed to create table $table_name: $create_output"
        return 1
    fi

    # Wait for table to be active (with timeout)
    log_info "Waiting for table $table_name to become active..."
    local max_wait=60
    local waited=0
    while [[ $waited -lt $max_wait ]]; do
        local status
        status=$(aws dynamodb describe-table --table-name "$table_name" --region "$CORE_REGION" \
            --query 'Table.TableStatus' --output text 2>/dev/null)

        if [[ "$status" == "ACTIVE" ]]; then
            log_info "Table $table_name is now ACTIVE"
            return 0
        fi

        log_debug "Table status: $status (waiting... $waited/$max_wait seconds)"
        sleep 5
        ((waited+=5))
    done

    log_error "Timeout waiting for table $table_name to become active"
    return 1
}

# =============================================================================
# Lambda Cleanup
# =============================================================================

# Delete a single Lambda function
# Usage: cleanup_lambda <func_name> <role_name> [region]
cleanup_lambda() {
    local func_name="$1"
    local role_name="$2"
    local cleanup_region="${3:-$CORE_REGION}"

    log_info "Cleaning up Lambda: $func_name (region: $cleanup_region)"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Delete Lambda: $func_name (region: $cleanup_region)"
        echo -e "${YELLOW}  \$ aws lambda delete-function --function-name \"$func_name\" --region \"$cleanup_region\"${NC}"
        if [[ -n "$role_name" ]]; then
            echo -e "${YELLOW}  \$ aws iam delete-role --role-name \"$role_name\"${NC}"
        fi
        echo ""
        return 0
    fi

    # Delete the Lambda function
    if aws lambda get-function --function-name "$func_name" --region "$cleanup_region" &>/dev/null; then
        aws lambda delete-function --function-name "$func_name" --region "$cleanup_region" 2>/dev/null
        log_info "Lambda $func_name deleted"
    else
        log_debug "Lambda $func_name does not exist"
    fi

    # Delete the IAM role (if provided)
    if [[ -n "$role_name" ]]; then
        delete_lambda_role "$role_name"
    fi

    return 0
}

# Cleanup all Lambda functions
cleanup_all_lambdas() {
    log_section "Cleaning Up Lambda Functions"
    print_naming_config

    local confirmation_msg="This will delete all Lambda functions and their IAM roles for ${RESOURCE_PREFIX}-*-${ENVIRONMENT}. Continue?"
    if ! confirm_action "$confirmation_msg"; then
        log_info "Cleanup cancelled"
        return 0
    fi

    # Delete Lambda functions (from appropriate regions)
    for entry in "${LAMBDA_FUNCTION_LIST[@]}"; do
        IFS=':' read -r base_name source_dir role_base timeout memory <<< "$entry"
        local func_name=$(lambda_name "$base_name")
        local full_role_name=$(role_name "$role_base")
        local cleanup_region=$(get_lambda_deploy_region "$role_base")
        cleanup_lambda "$func_name" "$full_role_name" "$cleanup_region"
    done

    # Delete DynamoDB tables
    cleanup_lambda_dynamodb_tables

    log_info "All Lambda resources cleaned up"
    return 0
}

# Cleanup Lambda-related DynamoDB tables (in CORE_REGION)
cleanup_lambda_dynamodb_tables() {
    log_info "Cleaning up DynamoDB tables in $CORE_REGION..."

    for base in "${LAMBDA_DYNAMODB_TABLE_BASES[@]}"; do
        local full_table_name=$(table_name "$base")
        if aws dynamodb describe-table --table-name "$full_table_name" --region "$CORE_REGION" &>/dev/null; then
            if [[ "$DRY_RUN" == "true" ]]; then
                echo -e "${CYAN}[DRY-RUN]${NC} Delete DynamoDB table: $full_table_name (region: $CORE_REGION)"
                echo -e "${YELLOW}  \$ aws dynamodb delete-table --table-name \"$full_table_name\" --region \"$CORE_REGION\"${NC}"
                echo ""
            else
                log_info "Deleting table: $full_table_name"
                aws dynamodb delete-table --table-name "$full_table_name" --region "$CORE_REGION" 2>/dev/null
            fi
        fi
    done
}

# =============================================================================
# Lambda Validation
# =============================================================================

# Validate all Lambda functions
# Validates each Lambda in its appropriate region
validate_lambdas() {
    log_section "Validating Lambda Functions"
    print_naming_config
    log_info "Core region: $CORE_REGION, Voice region: $VOICE_REGION"

    local failed=0

    for entry in "${LAMBDA_FUNCTION_LIST[@]}"; do
        IFS=':' read -r base_name source_dir role_base timeout memory <<< "$entry"
        local func_name=$(lambda_name "$base_name")
        local validate_region=$(get_lambda_deploy_region "$role_base")
        if aws lambda get-function --function-name "$func_name" --region "$validate_region" &>/dev/null; then
            local state
            state=$(aws lambda get-function --function-name "$func_name" --region "$validate_region" \
                --query 'Configuration.State' --output text 2>/dev/null)
            if [[ "$state" == "Active" ]]; then
                log_info "$func_name: Active (${validate_region})"
            else
                log_warn "$func_name: $state"
                ((failed++))
            fi
        else
            log_error "$func_name: NOT FOUND in $validate_region"
            ((failed++))
        fi
    done

    # Validate DynamoDB tables (in CORE_REGION)
    for base in "${LAMBDA_DYNAMODB_TABLE_BASES[@]}"; do
        local full_table_name=$(table_name "$base")
        if aws dynamodb describe-table --table-name "$full_table_name" --region "$CORE_REGION" &>/dev/null; then
            log_info "Table $full_table_name: EXISTS (${CORE_REGION})"
        else
            log_error "Table $full_table_name: NOT FOUND in $CORE_REGION"
            ((failed++))
        fi
    done

    if [[ $failed -gt 0 ]]; then
        log_error "Validation failed: $failed resource(s) missing or unhealthy"
        return 1
    fi

    log_info "All core Lambda resources validated successfully"
    return 0
}

# List Lambda functions in both regions
list_lambda_functions() {
    log_section "Lambda Functions (${RESOURCE_PREFIX}-*-${ENVIRONMENT})"

    log_info "Core Lambdas ($CORE_REGION):"
    aws lambda list-functions \
        --query "Functions[?starts_with(FunctionName, \`${RESOURCE_PREFIX}-\`) && ends_with(FunctionName, \`-${ENVIRONMENT}\`)].{Name:FunctionName,Runtime:Runtime,Memory:MemorySize,Timeout:Timeout}" \
        --output table \
        --region "$CORE_REGION"

    log_info "Voice/SMS Lambdas ($VOICE_REGION):"
    aws lambda list-functions \
        --query "Functions[?starts_with(FunctionName, \`${RESOURCE_PREFIX}-\`) && ends_with(FunctionName, \`-${ENVIRONMENT}\`)].{Name:FunctionName,Runtime:Runtime,Memory:MemorySize,Timeout:Timeout}" \
        --output table \
        --region "$VOICE_REGION"
}
