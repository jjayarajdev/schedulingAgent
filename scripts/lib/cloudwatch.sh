#!/bin/bash
# =============================================================================
# cloudwatch.sh - CloudWatch Logs management for pf-manage.sh
# =============================================================================

# Default log retention period (from resources.env or default to 14 days)
DEFAULT_LOG_RETENTION="${CLOUDWATCH_LOG_RETENTION_DAYS:-14}"

# =============================================================================
# Helper Functions
# =============================================================================

# Build log group name for a Lambda function
log_group_name() {
    local lambda_name="$1"
    echo "/aws/lambda/${lambda_name}"
}

# Check if log group exists
log_group_exists() {
    local log_group="$1"
    aws logs describe-log-groups --log-group-name-prefix "$log_group" \
        --query "logGroups[?logGroupName=='$log_group'].logGroupName" \
        --output text 2>/dev/null | grep -q "$log_group"
}

# Get current retention for a log group
get_log_retention() {
    local log_group="$1"
    aws logs describe-log-groups --log-group-name-prefix "$log_group" \
        --query "logGroups[?logGroupName=='$log_group'].retentionInDays" \
        --output text 2>/dev/null
}

# =============================================================================
# Log Group Management Functions
# =============================================================================

# Create or update log group with retention policy
ensure_log_group() {
    local lambda_name="$1"
    local retention="${2:-$DEFAULT_LOG_RETENTION}"
    local log_group
    log_group=$(log_group_name "$lambda_name")

    if [[ "$DRY_RUN" == "true" ]]; then
        dry_run_cmd "Ensure log group $log_group with ${retention}-day retention" \
            "aws logs create-log-group --log-group-name '$log_group' && aws logs put-retention-policy --log-group-name '$log_group' --retention-in-days $retention"
        return 0
    fi

    if log_group_exists "$log_group"; then
        # Log group exists, check/update retention
        local current_retention
        current_retention=$(get_log_retention "$log_group")

        if [[ "$current_retention" != "$retention" ]]; then
            log_info "Updating retention for $log_group: $current_retention -> ${retention} days"
            aws logs put-retention-policy \
                --log-group-name "$log_group" \
                --retention-in-days "$retention" 2>/dev/null
        else
            log_debug "Log group $log_group already has ${retention}-day retention"
        fi
    else
        # Create new log group
        log_info "Creating log group: $log_group"
        aws logs create-log-group --log-group-name "$log_group" 2>/dev/null

        # Set retention policy
        log_info "Setting retention to ${retention} days"
        aws logs put-retention-policy \
            --log-group-name "$log_group" \
            --retention-in-days "$retention" 2>/dev/null
    fi

    return 0
}

# Deploy CloudWatch log groups for all Lambda functions
deploy_cloudwatch_logs() {
    log_section "Deploying CloudWatch Log Groups"

    local retention="$DEFAULT_LOG_RETENTION"
    log_info "Default retention: ${retention} days"

    # Core Lambda functions
    local core_lambdas=(
        "$(resource_name 'orchestrator')"
        "$(resource_name 'scheduling-actions')"
        "$(resource_name 'information-actions')"
        "$(resource_name 'chitchat-actions')"
    )

    # Voice Lambda functions
    local voice_lambdas=(
        "$(resource_name 'lex-fulfillment')"
        "$(resource_name 'customer-lookup')"
        "$(resource_name 'voice-bedrock-bridge')"
    )

    # SMS Lambda functions
    local sms_lambdas=(
        "$(resource_name 'sms-inbound')"
    )

    log_info "Setting up log groups for Core Lambdas..."
    for lambda_name in "${core_lambdas[@]}"; do
        ensure_log_group "$lambda_name" "$retention"
    done

    log_info "Setting up log groups for Voice Lambdas..."
    for lambda_name in "${voice_lambdas[@]}"; do
        ensure_log_group "$lambda_name" "$retention"
    done

    log_info "Setting up log groups for SMS Lambdas..."
    for lambda_name in "${sms_lambdas[@]}"; do
        ensure_log_group "$lambda_name" "$retention"
    done

    log_info "CloudWatch log groups configured"
    return 0
}

# =============================================================================
# Cleanup Functions
# =============================================================================

# Delete log group
delete_log_group() {
    local lambda_name="$1"
    local log_group
    log_group=$(log_group_name "$lambda_name")

    if [[ "$DRY_RUN" == "true" ]]; then
        dry_run_cmd "Delete log group $log_group" \
            "aws logs delete-log-group --log-group-name '$log_group'"
        return 0
    fi

    if log_group_exists "$log_group"; then
        log_info "Deleting log group: $log_group"
        aws logs delete-log-group --log-group-name "$log_group" 2>/dev/null
    else
        log_debug "Log group $log_group does not exist"
    fi

    return 0
}

# Cleanup all CloudWatch log groups for Lambda functions
cleanup_cloudwatch_logs() {
    log_section "Cleaning Up CloudWatch Log Groups"

    # All Lambda functions
    local all_lambdas=(
        "$(resource_name 'orchestrator')"
        "$(resource_name 'scheduling-actions')"
        "$(resource_name 'information-actions')"
        "$(resource_name 'chitchat-actions')"
        "$(resource_name 'lex-fulfillment')"
        "$(resource_name 'customer-lookup')"
        "$(resource_name 'voice-bedrock-bridge')"
        "$(resource_name 'sms-inbound')"
    )

    for lambda_name in "${all_lambdas[@]}"; do
        delete_log_group "$lambda_name"
    done

    log_info "CloudWatch log groups cleaned up"
    return 0
}

# =============================================================================
# Validation Functions
# =============================================================================

# Validate CloudWatch log groups
validate_cloudwatch_logs() {
    log_section "Validating CloudWatch Log Groups"

    local failed=0
    local retention="$DEFAULT_LOG_RETENTION"

    # All Lambda functions
    local all_lambdas=(
        "$(resource_name 'orchestrator')"
        "$(resource_name 'scheduling-actions')"
        "$(resource_name 'information-actions')"
        "$(resource_name 'chitchat-actions')"
        "$(resource_name 'lex-fulfillment')"
        "$(resource_name 'customer-lookup')"
        "$(resource_name 'voice-bedrock-bridge')"
        "$(resource_name 'sms-inbound')"
    )

    for lambda_name in "${all_lambdas[@]}"; do
        local log_group
        log_group=$(log_group_name "$lambda_name")

        if log_group_exists "$log_group"; then
            local current_retention
            current_retention=$(get_log_retention "$log_group")

            if [[ "$current_retention" == "$retention" ]]; then
                log_info "✓ $log_group (${retention}-day retention)"
            elif [[ -z "$current_retention" || "$current_retention" == "None" ]]; then
                log_warn "! $log_group (no retention set - logs never expire)"
            else
                log_info "✓ $log_group (${current_retention}-day retention)"
            fi
        else
            log_warn "✗ $log_group (not found - will be created on first Lambda invocation)"
        fi
    done

    return $failed
}

# List all Lambda log groups with retention info
list_cloudwatch_logs() {
    log_section "CloudWatch Log Groups (${RESOURCE_PREFIX}-*-${ENVIRONMENT})"

    aws logs describe-log-groups \
        --log-group-name-prefix "/aws/lambda/${RESOURCE_PREFIX}-" \
        --query "logGroups[?contains(logGroupName, '-${ENVIRONMENT}')].{Name:logGroupName,Retention:retentionInDays,StoredBytes:storedBytes}" \
        --output table \
        --region "$AWS_REGION" 2>/dev/null

    # Show total storage
    local total_bytes
    total_bytes=$(aws logs describe-log-groups \
        --log-group-name-prefix "/aws/lambda/${RESOURCE_PREFIX}-" \
        --query "logGroups[?contains(logGroupName, '-${ENVIRONMENT}')].storedBytes | sum(@)" \
        --output text \
        --region "$AWS_REGION" 2>/dev/null)

    if [[ -n "$total_bytes" && "$total_bytes" != "None" ]]; then
        local total_mb=$((total_bytes / 1024 / 1024))
        log_info "Total log storage: ${total_mb} MB"
    fi
}
