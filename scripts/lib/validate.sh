#!/bin/bash
# =============================================================================
# validate.sh - Comprehensive validation functions
# =============================================================================

# =============================================================================
# Full System Validation
# =============================================================================

# Validate all resources
validate_all() {
    log_section "Full System Validation"

    local total_failed=0

    # Validate Lambda
    validate_lambdas || ((total_failed++))

    # Validate Voice
    validate_voice || ((total_failed++))

    # Validate SMS
    validate_sms || ((total_failed++))

    # Validate IAM roles
    validate_iam_roles || ((total_failed++))

    # Summary
    echo ""
    log_section "Validation Summary"

    if [[ $total_failed -gt 0 ]]; then
        log_error "Validation completed with $total_failed component(s) having issues"
        return 1
    fi

    log_info "All resources validated successfully!"
    return 0
}

# =============================================================================
# IAM Validation
# =============================================================================

# Validate all IAM roles
validate_iam_roles() {
    log_section "Validating IAM Roles (${RESOURCE_PREFIX}-*-${ENVIRONMENT})"

    local failed=0

    # Core Lambda role bases
    local core_role_bases=(
        "orchestrator"
        "scheduling-actions"
        "information-actions"
        "chitchat-actions"
    )

    # Voice Lambda role bases
    local voice_role_bases=(
        "lex-fulfillment"
        "customer-lookup"
        "voice-bedrock-bridge"
    )

    # SMS Lambda role bases
    local sms_role_bases=(
        "sms-inbound"
    )

    log_info "Checking Core Lambda roles..."
    for base in "${core_role_bases[@]}"; do
        local full_role=$(role_name "$base")
        if aws iam get-role --role-name "$full_role" &>/dev/null; then
            log_info "  $full_role: EXISTS"
        else
            log_error "  $full_role: NOT FOUND"
            ((failed++))
        fi
    done

    log_info "Checking Voice Lambda roles..."
    for base in "${voice_role_bases[@]}"; do
        local full_role=$(role_name "$base")
        if aws iam get-role --role-name "$full_role" &>/dev/null; then
            log_info "  $full_role: EXISTS"
        else
            log_error "  $full_role: NOT FOUND"
            ((failed++))
        fi
    done

    log_info "Checking SMS Lambda roles..."
    for base in "${sms_role_bases[@]}"; do
        local full_role=$(role_name "$base")
        if aws iam get-role --role-name "$full_role" &>/dev/null; then
            log_info "  $full_role: EXISTS"
        else
            log_error "  $full_role: NOT FOUND"
            ((failed++))
        fi
    done

    if [[ $failed -gt 0 ]]; then
        log_error "IAM validation failed: $failed role(s) missing"
        return 1
    fi

    log_info "All IAM roles validated successfully"
    return 0
}

# =============================================================================
# DynamoDB Validation
# =============================================================================

# Validate all DynamoDB tables
validate_dynamodb_tables() {
    log_section "Validating DynamoDB Tables (${RESOURCE_PREFIX}-*-${ENVIRONMENT})"

    local failed=0

    # Table base names (will be prefixed with RESOURCE_PREFIX and suffixed with ENVIRONMENT)
    local table_bases=(
        "sessions"
        "notes"
        "workflow-states"
        "customers"
        "sms-sessions"
    )

    for base in "${table_bases[@]}"; do
        local table=$(table_name "$base")
        if aws dynamodb describe-table --table-name "$table" --region "$AWS_REGION" &>/dev/null; then
            local status
            status=$(aws dynamodb describe-table --table-name "$table" --region "$AWS_REGION" \
                --query 'Table.TableStatus' --output text 2>/dev/null)
            if [[ "$status" == "ACTIVE" ]]; then
                log_info "$table: ACTIVE"
            else
                log_warn "$table: $status"
                ((failed++))
            fi
        else
            log_error "$table: NOT FOUND"
            ((failed++))
        fi
    done

    if [[ $failed -gt 0 ]]; then
        log_error "DynamoDB validation failed: $failed table(s) missing or unhealthy"
        return 1
    fi

    log_info "All DynamoDB tables validated successfully"
    return 0
}

# =============================================================================
# Connectivity Tests
# =============================================================================

# Test Lambda invocations
test_lambda_invocation() {
    local func_name="$1"
    local payload="${2:-{}}"

    log_info "Testing Lambda invocation: $func_name"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] Would test Lambda: $func_name"
        return 0
    fi

    local response
    response=$(aws lambda invoke \
        --function-name "$func_name" \
        --payload "$payload" \
        --region "$AWS_REGION" \
        /tmp/lambda_response.json 2>&1)

    if [[ $? -eq 0 ]]; then
        local status_code
        status_code=$(echo "$response" | grep -o '"StatusCode": [0-9]*' | grep -o '[0-9]*')
        if [[ "$status_code" == "200" ]]; then
            log_info "  Invocation successful (Status: 200)"
            return 0
        else
            log_warn "  Invocation returned status: $status_code"
            return 1
        fi
    else
        log_error "  Invocation failed: $response"
        return 1
    fi
}

# Test Lex bot
test_lex_bot() {
    local bot_name=$(lex_bot_name)
    log_info "Testing Lex bot recognition: $bot_name"

    local bot_id
    bot_id=$(get_lex_bot_id "$bot_name")

    if [[ -z "$bot_id" || "$bot_id" == "None" ]]; then
        log_error "Cannot test Lex bot - bot not found"
        return 1
    fi

    local alias_name=$(lex_alias_name)
    local alias_id
    alias_id=$(get_lex_bot_alias_id "$bot_id" "$alias_name")

    if [[ -z "$alias_id" || "$alias_id" == "None" ]]; then
        log_error "Cannot test Lex bot - alias not found"
        return 1
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] Would test Lex bot"
        return 0
    fi

    # Send a test utterance
    local response
    response=$(aws lexv2-runtime recognize-text \
        --bot-id "$bot_id" \
        --bot-alias-id "$alias_id" \
        --locale-id "$LEX_BOT_LOCALE" \
        --session-id "test-$(date +%s)" \
        --text "hello" \
        --region "$AWS_REGION" 2>&1)

    if [[ $? -eq 0 ]]; then
        log_info "  Lex bot responded successfully"
        return 0
    else
        log_error "  Lex bot test failed: $response"
        return 1
    fi
}

# =============================================================================
# Health Check
# =============================================================================

# Quick health check
health_check() {
    log_section "Quick Health Check"

    echo ""
    echo "AWS Account: $(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo 'NOT CONFIGURED')"
    echo "AWS Region: $AWS_REGION"
    echo "AWS Profile: ${AWS_PROFILE:-default}"
    echo "Resource Prefix: $RESOURCE_PREFIX"
    echo "Environment: $ENVIRONMENT"
    echo ""

    # Check Lambda functions
    echo "Lambda Functions (${RESOURCE_PREFIX}-*-${ENVIRONMENT}):"
    aws lambda list-functions \
        --query "Functions[?starts_with(FunctionName, \`${RESOURCE_PREFIX}-\`)].{Name:FunctionName,State:State}" \
        --output table \
        --region "$AWS_REGION" 2>/dev/null || echo "  Unable to list Lambda functions"

    echo ""

    # Check DynamoDB tables
    echo "DynamoDB Tables (${RESOURCE_PREFIX}-*-${ENVIRONMENT}):"
    aws dynamodb list-tables \
        --query "TableNames[?starts_with(@, \`${RESOURCE_PREFIX}-\`)]" \
        --output table \
        --region "$AWS_REGION" 2>/dev/null || echo "  Unable to list DynamoDB tables"

    echo ""

    # Check Lex bots
    echo "Lex Bots (${RESOURCE_PREFIX}-*-${ENVIRONMENT}):"
    aws lexv2-models list-bots \
        --query "botSummaries[?starts_with(botName, \`${RESOURCE_PREFIX}-\`)].{Name:botName,Status:botStatus}" \
        --output table \
        --region "$AWS_REGION" 2>/dev/null || echo "  Unable to list Lex bots"

    echo ""

    # Check Connect instances
    echo "Connect Instances (${RESOURCE_PREFIX}-*-${ENVIRONMENT}):"
    aws connect list-instances \
        --query "InstanceSummaryList[?starts_with(InstanceAlias, \`${RESOURCE_PREFIX}-\`)].{Alias:InstanceAlias,Status:InstanceStatus}" \
        --output table \
        --region "$AWS_REGION" 2>/dev/null || echo "  Unable to list Connect instances"
}

# =============================================================================
# Resource Inventory
# =============================================================================

# List all resources
list_all_resources() {
    log_section "Resource Inventory"

    # List Lambda functions
    list_lambda_functions

    # List voice resources
    list_voice_resources

    # List SMS resources
    list_sms_resources

    # List IAM roles
    list_scheduling_agent_roles
}

# Generate resource report
generate_resource_report() {
    local output_file="${1:-/tmp/${RESOURCE_PREFIX}-resource-report.txt}"

    log_info "Generating resource report: $output_file"

    # Table base names for iteration
    local table_bases=(
        "sessions"
        "notes"
        "workflow-states"
        "customers"
        "sms-sessions"
    )

    {
        echo "=========================================="
        echo "ProjectForce Scheduling Agent - Resource Report"
        echo "Generated: $(date)"
        echo "AWS Account: $EXPECTED_ACCOUNT"
        echo "AWS Region: $AWS_REGION"
        echo "Resource Prefix: $RESOURCE_PREFIX"
        echo "Environment: $ENVIRONMENT"
        echo "=========================================="
        echo ""

        echo "=== Lambda Functions (${RESOURCE_PREFIX}-*-${ENVIRONMENT}) ==="
        aws lambda list-functions \
            --query "Functions[?starts_with(FunctionName, \`${RESOURCE_PREFIX}-\`)].{Name:FunctionName,Runtime:Runtime,Memory:MemorySize,Timeout:Timeout,State:State}" \
            --output table \
            --region "$AWS_REGION" 2>/dev/null

        echo ""
        echo "=== DynamoDB Tables (${RESOURCE_PREFIX}-*-${ENVIRONMENT}) ==="
        for base in "${table_bases[@]}"; do
            local table=$(table_name "$base")
            local status
            status=$(aws dynamodb describe-table --table-name "$table" --region "$AWS_REGION" \
                --query 'Table.TableStatus' --output text 2>/dev/null || echo "NOT FOUND")
            echo "$table: $status"
        done

        echo ""
        echo "=== IAM Roles (${RESOURCE_PREFIX}-*-${ENVIRONMENT}) ==="
        aws iam list-roles \
            --query "Roles[?starts_with(RoleName, \`${RESOURCE_PREFIX}-\`)].{Name:RoleName,Created:CreateDate}" \
            --output table 2>/dev/null

        echo ""
        echo "=== Lex Bots (${RESOURCE_PREFIX}-*-${ENVIRONMENT}) ==="
        aws lexv2-models list-bots \
            --query "botSummaries[?starts_with(botName, \`${RESOURCE_PREFIX}-\`)].{Name:botName,Status:botStatus,Id:botId}" \
            --output table \
            --region "$AWS_REGION" 2>/dev/null

        echo ""
        echo "=== Connect Instances (${RESOURCE_PREFIX}-*-${ENVIRONMENT}) ==="
        aws connect list-instances \
            --query "InstanceSummaryList[?starts_with(InstanceAlias, \`${RESOURCE_PREFIX}-\`)].{Alias:InstanceAlias,Status:InstanceStatus,Id:Id}" \
            --output table \
            --region "$AWS_REGION" 2>/dev/null

        echo ""
        echo "=== SNS Topics (${RESOURCE_PREFIX}-*-${ENVIRONMENT}) ==="
        aws sns list-topics \
            --query "Topics[?contains(TopicArn, \`${RESOURCE_PREFIX}-\`)].TopicArn" \
            --output table \
            --region "$AWS_REGION" 2>/dev/null

    } > "$output_file"

    log_info "Report saved to: $output_file"
    cat "$output_file"
}

# =============================================================================
# Drift Detection
# =============================================================================

# Check for configuration drift
detect_drift() {
    log_section "Detecting Configuration Drift (${RESOURCE_PREFIX}-*-${ENVIRONMENT})"

    local issues=0

    # Check Lambda configurations
    log_info "Checking Lambda configurations..."

    # Check orchestrator timeout
    local orch_name=$(lambda_name "orchestrator")
    local orch_timeout
    orch_timeout=$(aws lambda get-function-configuration \
        --function-name "$orch_name" \
        --region "$AWS_REGION" \
        --query 'Timeout' \
        --output text 2>/dev/null)

    if [[ "$orch_timeout" != "120" ]]; then
        log_warn "$orch_name timeout is $orch_timeout (expected 120)"
        ((issues++))
    fi

    # Check scheduling-actions memory
    local sched_name=$(lambda_name "scheduling-actions")
    local sched_memory
    sched_memory=$(aws lambda get-function-configuration \
        --function-name "$sched_name" \
        --region "$AWS_REGION" \
        --query 'MemorySize' \
        --output text 2>/dev/null)

    if [[ "$sched_memory" != "1769" ]]; then
        log_warn "$sched_name memory is $sched_memory (expected 1769)"
        ((issues++))
    fi

    # Check for missing environment variables
    log_info "Checking environment variables..."
    local core_lambda_bases=(
        "orchestrator"
        "scheduling-actions"
        "information-actions"
        "chitchat-actions"
    )

    for base in "${core_lambda_bases[@]}"; do
        local func=$(lambda_name "$base")
        local env_vars
        env_vars=$(aws lambda get-function-configuration \
            --function-name "$func" \
            --region "$AWS_REGION" \
            --query 'Environment.Variables' \
            --output json 2>/dev/null)

        if [[ "$env_vars" == "null" || -z "$env_vars" ]]; then
            log_warn "$func has no environment variables configured"
            ((issues++))
        fi
    done

    if [[ $issues -gt 0 ]]; then
        log_warn "Detected $issues configuration drift issue(s)"
        return 1
    fi

    log_info "No configuration drift detected"
    return 0
}
