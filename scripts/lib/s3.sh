#!/bin/bash
# =============================================================================
# s3.sh - S3 bucket management for Lambda functions
# =============================================================================
# Compatible with bash 3.2+ (macOS default)

# =============================================================================
# S3 Bucket Definitions
# =============================================================================
# All S3 buckets needed by the scheduling agent system
# Buckets follow naming: ${RESOURCE_PREFIX}-${bucket-name}-${ENVIRONMENT}

# List of all S3 buckets needed for the system
# Format: "bucket_base_name:purpose"
S3_BUCKETS=(
    # Config bucket (already exists)
    "config:Configuration files and settings"

    # DSPy integration buckets
    "dspy-models:Optimized DSPy models for prompt enhancement"
    "training-logs:Classification logs for continuous learning"
)

# =============================================================================
# Bucket Creation Functions
# =============================================================================

# Get full bucket name with prefix and environment
# Usage: bucket_name "dspy-models"
bucket_name() {
    local base_name="$1"
    echo "${RESOURCE_PREFIX}-${base_name}-${ENVIRONMENT}"
}

# Create a single S3 bucket
# Usage: create_s3_bucket "bucket-base-name"
create_s3_bucket() {
    local bucket_base="$1"

    local full_bucket_name
    full_bucket_name=$(bucket_name "$bucket_base")

    log_info "Creating S3 bucket: $full_bucket_name"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Create S3 bucket: $full_bucket_name"
        return 0
    fi

    # Check if bucket exists
    if aws s3api head-bucket --bucket "$full_bucket_name" 2>/dev/null; then
        log_info "Bucket $full_bucket_name already exists"
        return 0
    fi

    # Create the bucket
    local create_output
    if [[ "$AWS_REGION" == "us-east-1" ]]; then
        # us-east-1 doesn't need LocationConstraint
        create_output=$(aws s3api create-bucket \
            --bucket "$full_bucket_name" \
            --region "$AWS_REGION" \
            2>&1)
    else
        create_output=$(aws s3api create-bucket \
            --bucket "$full_bucket_name" \
            --region "$AWS_REGION" \
            --create-bucket-configuration LocationConstraint="$AWS_REGION" \
            2>&1)
    fi

    if [[ $? -ne 0 ]]; then
        log_error "Failed to create bucket $full_bucket_name: $create_output"
        return 1
    fi

    # Enable versioning for important buckets
    if [[ "$bucket_base" == "dspy-models" ]]; then
        log_info "Enabling versioning on $full_bucket_name"
        aws s3api put-bucket-versioning \
            --bucket "$full_bucket_name" \
            --versioning-configuration Status=Enabled \
            2>/dev/null
    fi

    log_info "Bucket $full_bucket_name created successfully"
    return 0
}

# Create all S3 buckets
# Usage: create_all_s3_buckets
create_all_s3_buckets() {
    log_section "Creating S3 Buckets"

    local failed=0

    for bucket_def in "${S3_BUCKETS[@]}"; do
        IFS=':' read -r bucket_base purpose <<< "$bucket_def"

        if ! create_s3_bucket "$bucket_base"; then
            ((failed++))
        fi
    done

    if [[ $failed -gt 0 ]]; then
        log_error "$failed bucket(s) failed to create"
        return 1
    fi

    log_info "All S3 buckets created successfully"
    return 0
}

# Create only DSPy-related buckets
# Usage: create_dspy_s3_buckets
create_dspy_s3_buckets() {
    log_section "Creating DSPy S3 Buckets"

    local dspy_buckets=(
        "dspy-models"
        "training-logs"
    )

    local failed=0

    for bucket_base in "${dspy_buckets[@]}"; do
        if ! create_s3_bucket "$bucket_base"; then
            ((failed++))
        fi
    done

    if [[ $failed -gt 0 ]]; then
        log_error "$failed bucket(s) failed to create"
        return 1
    fi

    log_info "DSPy S3 buckets created successfully"
    return 0
}

# =============================================================================
# Bucket Deletion Functions
# =============================================================================

# Delete a single S3 bucket (must be empty)
# Usage: delete_s3_bucket "bucket-base-name"
delete_s3_bucket() {
    local bucket_base="$1"
    local force="${2:-false}"

    local full_bucket_name
    full_bucket_name=$(bucket_name "$bucket_base")

    log_info "Deleting S3 bucket: $full_bucket_name"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Delete S3 bucket: $full_bucket_name"
        return 0
    fi

    # Check if bucket exists
    if ! aws s3api head-bucket --bucket "$full_bucket_name" 2>/dev/null; then
        log_info "Bucket $full_bucket_name does not exist"
        return 0
    fi

    # If force, empty the bucket first
    if [[ "$force" == "true" ]]; then
        log_info "Emptying bucket $full_bucket_name..."
        aws s3 rm "s3://$full_bucket_name" --recursive 2>/dev/null
    fi

    # Delete the bucket
    local delete_output
    delete_output=$(aws s3api delete-bucket \
        --bucket "$full_bucket_name" \
        2>&1)

    if [[ $? -ne 0 ]]; then
        log_error "Failed to delete bucket $full_bucket_name: $delete_output"
        return 1
    fi

    log_info "Bucket $full_bucket_name deleted"
    return 0
}

# =============================================================================
# DSPy Model Upload Functions
# =============================================================================

# Upload DSPy models to S3
# Usage: upload_dspy_models "/path/to/models"
upload_dspy_models() {
    local models_dir="${1:-.}"

    local bucket_name
    bucket_name=$(bucket_name "dspy-models")

    log_info "Uploading DSPy models to s3://$bucket_name/optimized/"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Upload DSPy models to s3://$bucket_name/optimized/"
        return 0
    fi

    local model_files=(
        "optimized_classifier.json"
        "optimized_extractor.json"
        "optimized_weather.json"
    )

    local uploaded=0
    for model_file in "${model_files[@]}"; do
        local file_path="$models_dir/$model_file"
        if [[ -f "$file_path" ]]; then
            aws s3 cp "$file_path" "s3://$bucket_name/optimized/$model_file" 2>/dev/null
            if [[ $? -eq 0 ]]; then
                log_info "  Uploaded: $model_file"
                ((uploaded++))
            else
                log_warn "  Failed to upload: $model_file"
            fi
        else
            log_warn "  Not found: $file_path"
        fi
    done

    log_info "Uploaded $uploaded model file(s)"
    return 0
}

# =============================================================================
# Validation Functions
# =============================================================================

# Check if an S3 bucket exists
# Usage: validate_s3_bucket "bucket-base-name"
validate_s3_bucket() {
    local bucket_base="$1"

    local full_bucket_name
    full_bucket_name=$(bucket_name "$bucket_base")

    if aws s3api head-bucket --bucket "$full_bucket_name" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $full_bucket_name: EXISTS"
        return 0
    else
        echo -e "  ${RED}✗${NC} $full_bucket_name: NOT FOUND"
        return 1
    fi
}

# Validate all S3 buckets
# Usage: validate_all_s3_buckets
validate_all_s3_buckets() {
    log_section "Validating S3 Buckets"

    local failed=0

    for bucket_def in "${S3_BUCKETS[@]}"; do
        IFS=':' read -r bucket_base _ <<< "$bucket_def"

        if ! validate_s3_bucket "$bucket_base"; then
            ((failed++))
        fi
    done

    if [[ $failed -gt 0 ]]; then
        log_warn "$failed bucket(s) not found"
        return 1
    fi

    log_info "All S3 buckets validated"
    return 0
}

# =============================================================================
# Status Functions
# =============================================================================

# Show status of all S3 buckets
# Usage: show_s3_status
show_s3_status() {
    log_section "S3 Buckets Status"

    echo ""
    printf "%-45s %-10s %-20s\n" "BUCKET NAME" "EXISTS" "OBJECT COUNT"
    printf "%s\n" "--------------------------------------------------------------------------------"

    for bucket_def in "${S3_BUCKETS[@]}"; do
        IFS=':' read -r bucket_base purpose <<< "$bucket_def"

        local full_bucket_name
        full_bucket_name=$(bucket_name "$bucket_base")

        if aws s3api head-bucket --bucket "$full_bucket_name" 2>/dev/null; then
            # Get object count
            local object_count
            object_count=$(aws s3 ls "s3://$full_bucket_name" --recursive 2>/dev/null | wc -l | tr -d ' ')
            printf "%-45s %-10s %-20s\n" "$full_bucket_name" "YES" "$object_count"
        else
            printf "%-45s %-10s %-20s\n" "$full_bucket_name" "NO" "-"
        fi
    done

    echo ""
}

# List DSPy models in S3
# Usage: list_dspy_models
list_dspy_models() {
    local bucket_name
    bucket_name=$(bucket_name "dspy-models")

    log_section "DSPy Models in S3"

    echo ""
    echo "Bucket: s3://$bucket_name/optimized/"
    echo ""

    aws s3 ls "s3://$bucket_name/optimized/" 2>/dev/null || echo "  No models found or bucket doesn't exist"

    echo ""
}
