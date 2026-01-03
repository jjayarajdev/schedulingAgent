#!/bin/bash
# =============================================================================
# dynamodb.sh - DynamoDB table management for Lambda functions
# =============================================================================
# Compatible with bash 3.2+ (macOS default)

# =============================================================================
# Table Definitions
# =============================================================================
# All DynamoDB tables needed by the scheduling agent system
# Tables follow naming: ${RESOURCE_PREFIX}-${table-name}-${ENVIRONMENT}

# List of all DynamoDB tables needed for the system
# Format: "table_base_name:partition_key:sort_key:partition_type:sort_type"
# If no sort key, use "NONE" for sort_key and sort_type
DYNAMODB_TABLES=(
    # Core orchestrator tables
    "sessions:session_id:NONE:S:NONE"
    "workflow-states:session_id:NONE:S:NONE"

    # Notes tables (for notes-actions Lambda)
    "project-notes:project_id:timestamp:S:S"

    # SMS tables
    "sms-sessions:session_id:NONE:S:NONE"
    "sms-consent:phone_number:NONE:S:NONE"
    "sms-messages:session_id:timestamp:S:S"
    "opt-out-tracking:phone_number:timestamp:S:S"

    # Customer tables
    "customers:phone_number:NONE:S:NONE"

    # DSPy training logs (for continuous learning)
    "training-logs:log_id:NONE:S:NONE"
)

# =============================================================================
# Table Creation Functions
# =============================================================================

# Create a single DynamoDB table
# Usage: create_dynamodb_table "table-name" "pk_name" "sk_name" "pk_type" "sk_type"
create_dynamodb_table() {
    local table_name="$1"
    local pk_name="$2"
    local sk_name="$3"
    local pk_type="$4"
    local sk_type="$5"

    local full_table_name
    full_table_name=$(table_name "$table_name")

    log_info "Creating DynamoDB table: $full_table_name"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Create DynamoDB table: $full_table_name"
        echo -e "  Partition Key: $pk_name ($pk_type)"
        [[ "$sk_name" != "NONE" ]] && echo -e "  Sort Key: $sk_name ($sk_type)"
        return 0
    fi

    # Check if table exists
    if aws dynamodb describe-table --table-name "$full_table_name" &>/dev/null; then
        log_info "Table $full_table_name already exists"
        return 0
    fi

    # Build the create-table command
    local attr_defs="AttributeName=$pk_name,AttributeType=$pk_type"
    local key_schema="AttributeName=$pk_name,KeyType=HASH"

    if [[ "$sk_name" != "NONE" ]]; then
        attr_defs="$attr_defs AttributeName=$sk_name,AttributeType=$sk_type"
        key_schema="$key_schema AttributeName=$sk_name,KeyType=RANGE"
    fi

    local create_output
    create_output=$(aws dynamodb create-table \
        --table-name "$full_table_name" \
        --attribute-definitions $attr_defs \
        --key-schema $key_schema \
        --billing-mode PAY_PER_REQUEST \
        --query 'TableDescription.TableName' \
        --output text \
        2>&1)

    if [[ $? -ne 0 ]]; then
        log_error "Failed to create table $full_table_name: $create_output"
        return 1
    fi

    log_info "Table $full_table_name created, waiting for it to become active..."

    # Wait for table to be active
    aws dynamodb wait table-exists --table-name "$full_table_name" 2>/dev/null

    log_info "Table $full_table_name is now active"
    return 0
}

# Create all DynamoDB tables
# Usage: create_all_dynamodb_tables
create_all_dynamodb_tables() {
    log_section "Creating DynamoDB Tables"

    local failed=0

    for table_def in "${DYNAMODB_TABLES[@]}"; do
        IFS=':' read -r table_name pk_name sk_name pk_type sk_type <<< "$table_def"

        if ! create_dynamodb_table "$table_name" "$pk_name" "$sk_name" "$pk_type" "$sk_type"; then
            ((failed++))
        fi
    done

    if [[ $failed -gt 0 ]]; then
        log_error "$failed table(s) failed to create"
        return 1
    fi

    log_info "All DynamoDB tables created successfully"
    return 0
}

# Create only core Lambda tables (sessions, workflow-states, project-notes)
# Usage: create_core_dynamodb_tables
create_core_dynamodb_tables() {
    log_section "Creating Core DynamoDB Tables"

    local core_tables=(
        "sessions:session_id:NONE:S:NONE"
        "workflow-states:session_id:NONE:S:NONE"
        "project-notes:project_id:timestamp:S:S"
    )

    local failed=0

    for table_def in "${core_tables[@]}"; do
        IFS=':' read -r table_name pk_name sk_name pk_type sk_type <<< "$table_def"

        if ! create_dynamodb_table "$table_name" "$pk_name" "$sk_name" "$pk_type" "$sk_type"; then
            ((failed++))
        fi
    done

    if [[ $failed -gt 0 ]]; then
        log_error "$failed table(s) failed to create"
        return 1
    fi

    log_info "Core DynamoDB tables created successfully"
    return 0
}

# Create only SMS-related tables
# Usage: create_sms_dynamodb_tables
create_sms_dynamodb_tables() {
    log_section "Creating SMS DynamoDB Tables"

    local sms_tables=(
        "sms-sessions:session_id:NONE:S:NONE"
        "sms-consent:phone_number:NONE:S:NONE"
        "sms-messages:session_id:timestamp:S:S"
        "opt-out-tracking:phone_number:timestamp:S:S"
    )

    local failed=0

    for table_def in "${sms_tables[@]}"; do
        IFS=':' read -r table_name pk_name sk_name pk_type sk_type <<< "$table_def"

        if ! create_dynamodb_table "$table_name" "$pk_name" "$sk_name" "$pk_type" "$sk_type"; then
            ((failed++))
        fi
    done

    if [[ $failed -gt 0 ]]; then
        log_error "$failed table(s) failed to create"
        return 1
    fi

    log_info "SMS DynamoDB tables created successfully"
    return 0
}

# =============================================================================
# Table Deletion Functions
# =============================================================================

# Delete a single DynamoDB table
# Usage: delete_dynamodb_table "table-base-name"
delete_dynamodb_table() {
    local table_name="$1"

    local full_table_name
    full_table_name=$(table_name "$table_name")

    log_info "Deleting DynamoDB table: $full_table_name"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Delete DynamoDB table: $full_table_name"
        return 0
    fi

    # Check if table exists
    if ! aws dynamodb describe-table --table-name "$full_table_name" &>/dev/null; then
        log_info "Table $full_table_name does not exist"
        return 0
    fi

    local delete_output
    delete_output=$(aws dynamodb delete-table \
        --table-name "$full_table_name" \
        2>&1)

    if [[ $? -ne 0 ]]; then
        log_error "Failed to delete table $full_table_name: $delete_output"
        return 1
    fi

    log_info "Table $full_table_name deleted"
    return 0
}

# Delete all DynamoDB tables
# Usage: delete_all_dynamodb_tables
delete_all_dynamodb_tables() {
    log_section "Deleting DynamoDB Tables"

    if [[ "$DRY_RUN" != "true" ]]; then
        if ! confirm_action "This will delete ALL DynamoDB tables for ${RESOURCE_PREFIX}-*-${ENVIRONMENT}. Continue?"; then
            log_info "Cancelled by user"
            return 0
        fi
    fi

    local failed=0

    for table_def in "${DYNAMODB_TABLES[@]}"; do
        IFS=':' read -r table_name _ _ _ _ <<< "$table_def"

        if ! delete_dynamodb_table "$table_name"; then
            ((failed++))
        fi
    done

    if [[ $failed -gt 0 ]]; then
        log_error "$failed table(s) failed to delete"
        return 1
    fi

    log_info "All DynamoDB tables deleted successfully"
    return 0
}

# =============================================================================
# Validation Functions
# =============================================================================

# Check if a DynamoDB table exists and is active
# Usage: validate_dynamodb_table "table-base-name"
validate_dynamodb_table() {
    local table_name="$1"

    local full_table_name
    full_table_name=$(table_name "$table_name")

    local status
    status=$(aws dynamodb describe-table \
        --table-name "$full_table_name" \
        --query 'Table.TableStatus' \
        --output text \
        2>/dev/null)

    if [[ "$status" == "ACTIVE" ]]; then
        echo -e "  ${GREEN}✓${NC} $full_table_name: ACTIVE"
        return 0
    elif [[ -n "$status" ]]; then
        echo -e "  ${YELLOW}!${NC} $full_table_name: $status"
        return 1
    else
        echo -e "  ${RED}✗${NC} $full_table_name: NOT FOUND"
        return 1
    fi
}

# Validate all DynamoDB tables
# Usage: validate_all_dynamodb_tables
validate_all_dynamodb_tables() {
    log_section "Validating DynamoDB Tables"

    local failed=0

    for table_def in "${DYNAMODB_TABLES[@]}"; do
        IFS=':' read -r table_name _ _ _ _ <<< "$table_def"

        if ! validate_dynamodb_table "$table_name"; then
            ((failed++))
        fi
    done

    if [[ $failed -gt 0 ]]; then
        log_warn "$failed table(s) not in expected state"
        return 1
    fi

    log_info "All DynamoDB tables validated"
    return 0
}

# =============================================================================
# Index Management Functions
# =============================================================================

# Add a Global Secondary Index to a table
# Usage: add_gsi_to_table "table-base-name" "index-name" "pk_name" "pk_type"
add_gsi_to_table() {
    local table_name="$1"
    local index_name="$2"
    local pk_name="$3"
    local pk_type="$4"

    local full_table_name
    full_table_name=$(table_name "$table_name")

    log_info "Adding GSI $index_name to table $full_table_name"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Add GSI $index_name to $full_table_name"
        return 0
    fi

    # Check if index already exists
    local existing_indexes
    existing_indexes=$(aws dynamodb describe-table \
        --table-name "$full_table_name" \
        --query 'Table.GlobalSecondaryIndexes[].IndexName' \
        --output text \
        2>/dev/null)

    if echo "$existing_indexes" | grep -q "$index_name"; then
        log_info "GSI $index_name already exists on $full_table_name"
        return 0
    fi

    # Add the GSI
    local update_output
    update_output=$(aws dynamodb update-table \
        --table-name "$full_table_name" \
        --attribute-definitions "AttributeName=$pk_name,AttributeType=$pk_type" \
        --global-secondary-index-updates "[{\"Create\":{\"IndexName\":\"$index_name\",\"KeySchema\":[{\"AttributeName\":\"$pk_name\",\"KeyType\":\"HASH\"}],\"Projection\":{\"ProjectionType\":\"ALL\"}}}]" \
        2>&1)

    if [[ $? -ne 0 ]]; then
        log_error "Failed to add GSI $index_name to $full_table_name: $update_output"
        return 1
    fi

    log_info "GSI $index_name added to $full_table_name"

    # Wait for GSI to become active
    log_info "Waiting for GSI to become active..."
    aws dynamodb wait table-exists --table-name "$full_table_name" 2>/dev/null

    return 0
}

# =============================================================================
# Status Functions
# =============================================================================

# Show status of all DynamoDB tables
# Usage: show_dynamodb_status
show_dynamodb_status() {
    log_section "DynamoDB Tables Status"

    echo ""
    printf "%-50s %-12s %-15s\n" "TABLE NAME" "STATUS" "ITEM COUNT"
    printf "%s\n" "--------------------------------------------------------------------------------"

    for table_def in "${DYNAMODB_TABLES[@]}"; do
        IFS=':' read -r table_name _ _ _ _ <<< "$table_def"

        local full_table_name
        full_table_name=$(table_name "$table_name")

        local info
        info=$(aws dynamodb describe-table \
            --table-name "$full_table_name" \
            --query 'Table.[TableStatus,ItemCount]' \
            --output text \
            2>/dev/null)

        if [[ -n "$info" ]]; then
            local status item_count
            read -r status item_count <<< "$info"
            printf "%-50s %-12s %-15s\n" "$full_table_name" "$status" "$item_count"
        else
            printf "%-50s %-12s %-15s\n" "$full_table_name" "NOT FOUND" "-"
        fi
    done

    echo ""
}
