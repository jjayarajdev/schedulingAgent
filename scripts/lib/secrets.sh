#!/bin/bash
# =============================================================================
# secrets.sh - Secrets Manager deployment functions for pf-manage.sh
# =============================================================================

# =============================================================================
# Configuration
# =============================================================================

# Default secret name (shared across environments)
# The config file can override SECRETS_NAME if environment-specific secrets are needed
SHARED_SECRET_NAME="${SECRETS_NAME:-projectforce/api/credentials}"

# =============================================================================
# Helper Functions
# =============================================================================

# Build environment-specific secret name (if needed)
secret_name() {
    local base_name="$1"
    echo "${RESOURCE_PREFIX}-${base_name}-${ENVIRONMENT}"
}

# Get the secret ARN
get_secret_arn() {
    local secret_id="$1"
    aws secretsmanager describe-secret --secret-id "$secret_id" \
        --query 'ARN' --output text 2>/dev/null
}

# Check if secret exists
secret_exists() {
    local secret_id="$1"
    aws secretsmanager describe-secret --secret-id "$secret_id" &>/dev/null
}

# =============================================================================
# Secrets Deployment Functions
# =============================================================================

# Validate or create secrets
deploy_secrets() {
    log_section "Validating Secrets Manager"

    # Check if shared secret exists
    if secret_exists "$SHARED_SECRET_NAME"; then
        log_info "✓ Shared secret exists: $SHARED_SECRET_NAME"

        local secret_arn
        secret_arn=$(get_secret_arn "$SHARED_SECRET_NAME")
        log_info "  ARN: $secret_arn"

        # Validate secret has required keys
        validate_secret_keys "$SHARED_SECRET_NAME"
    else
        log_warn "✗ Shared secret not found: $SHARED_SECRET_NAME"
        log_warn "  This secret should be created manually with API credentials"
        log_info ""
        log_info "To create the secret, run:"
        log_info "  aws secretsmanager create-secret \\"
        log_info "    --name '$SHARED_SECRET_NAME' \\"
        log_info "    --description 'ProjectForce API credentials' \\"
        log_info "    --secret-string '{\"bearer_token\":\"\",\"refresh_token\":\"\",\"client_id\":\"\"}'"

        if [[ "$DRY_RUN" != "true" ]]; then
            return 1
        fi
    fi

    return 0
}

# Validate secret has required keys
validate_secret_keys() {
    local secret_id="$1"
    local required_keys=("bearer_token" "client_id")
    local missing_keys=()

    # Get secret value and check keys
    local secret_json
    secret_json=$(aws secretsmanager get-secret-value --secret-id "$secret_id" \
        --query 'SecretString' --output text 2>/dev/null)

    if [[ -z "$secret_json" ]]; then
        log_error "Could not retrieve secret value"
        return 1
    fi

    for key in "${required_keys[@]}"; do
        if ! echo "$secret_json" | jq -e "has(\"$key\")" &>/dev/null; then
            missing_keys+=("$key")
        fi
    done

    if [[ ${#missing_keys[@]} -gt 0 ]]; then
        log_warn "Secret missing required keys: ${missing_keys[*]}"
        return 1
    fi

    log_info "  ✓ All required keys present"
    return 0
}

# Create environment-specific secret (if needed)
create_env_secret() {
    local secret_name="$1"
    local description="$2"
    local initial_value="${3:-{}}"

    if [[ "$DRY_RUN" == "true" ]]; then
        dry_run_cmd "Create secret $secret_name" \
            "aws secretsmanager create-secret --name '$secret_name' --description '$description'"
        return 0
    fi

    if secret_exists "$secret_name"; then
        log_info "Secret already exists: $secret_name"
        return 0
    fi

    log_info "Creating secret: $secret_name"
    aws secretsmanager create-secret \
        --name "$secret_name" \
        --description "$description" \
        --secret-string "$initial_value" \
        --query 'ARN' --output text

    log_info "Secret created: $secret_name"
    return 0
}

# Update secret value
update_secret() {
    local secret_id="$1"
    local new_value="$2"

    if [[ "$DRY_RUN" == "true" ]]; then
        dry_run_cmd "Update secret $secret_id" \
            "aws secretsmanager put-secret-value --secret-id '$secret_id' ..."
        return 0
    fi

    aws secretsmanager put-secret-value \
        --secret-id "$secret_id" \
        --secret-string "$new_value"

    log_info "Secret updated: $secret_id"
    return 0
}

# =============================================================================
# Cleanup Functions
# =============================================================================

# Cleanup environment-specific secrets (not the shared one)
cleanup_secrets() {
    log_section "Cleaning Up Environment-Specific Secrets"

    # Only cleanup environment-specific secrets, not the shared one
    local env_secret
    env_secret=$(secret_name "api-credentials")

    if ! secret_exists "$env_secret"; then
        log_info "No environment-specific secret found to cleanup"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        dry_run_cmd "Delete secret $env_secret" \
            "aws secretsmanager delete-secret --secret-id '$env_secret' --force-delete-without-recovery"
        return 0
    fi

    log_warn "Deleting environment-specific secret: $env_secret"
    aws secretsmanager delete-secret \
        --secret-id "$env_secret" \
        --force-delete-without-recovery &>/dev/null || true

    log_info "Secret deleted: $env_secret"
    return 0
}

# =============================================================================
# Validation Functions
# =============================================================================

validate_secrets() {
    log_section "Validating Secrets Manager"

    local failed=0

    # Check shared secret
    if secret_exists "$SHARED_SECRET_NAME"; then
        log_info "✓ Shared secret exists: $SHARED_SECRET_NAME"

        if ! validate_secret_keys "$SHARED_SECRET_NAME"; then
            ((failed++))
        fi
    else
        log_error "✗ Shared secret not found: $SHARED_SECRET_NAME"
        ((failed++))
    fi

    if [[ $failed -gt 0 ]]; then
        return 1
    fi

    return 0
}

# Get secret ARN for use in IAM policies
get_secrets_arn_for_policy() {
    local secret_arn
    secret_arn=$(get_secret_arn "$SHARED_SECRET_NAME")

    if [[ -z "$secret_arn" || "$secret_arn" == "None" ]]; then
        # Return a pattern if secret doesn't exist yet
        echo "arn:aws:secretsmanager:${AWS_REGION}:*:secret:projectforce/*"
    else
        echo "$secret_arn"
    fi
}
