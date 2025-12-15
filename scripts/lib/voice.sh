#!/bin/bash
# =============================================================================
# voice.sh - Voice integration (Connect, Lex, Voice Lambdas)
# =============================================================================

# Voice Lambda function BASE definitions (without prefix/environment)
# Format: base_name:source_dir:role_base:timeout:memory
# Compatible with bash 3.2+ (macOS default)
VOICE_LAMBDA_FUNCTION_LIST=(
    "lex-fulfillment:lambda/lex-fulfillment:lex-fulfillment:60:512"
    "customer-lookup:lambda/customer-lookup:customer-lookup:30:256"
    "voice-bedrock-bridge:lambda/voice-bedrock-bridge:voice-bedrock-bridge:120:512"
)

# Lex Bot BASE configuration (actual name: pf-scheduling-assistant-${ENV})
# Note: Lex bot uses simplified naming (pf-{base}-{env}) to match existing resources
LEX_BOT_BASE="scheduling-assistant"
LEX_BOT_ALIAS="TestBotAlias"
LEX_BOT_LOCALE="en_US"

# Connect BASE configuration (actual name: pf-schedule-voice-${ENV})
# Note: Connect instance uses simplified naming (pf-{base}-{env}) to match existing resources
CONNECT_INSTANCE_BASE="schedule-voice"

# =============================================================================
# PROTECTED PHONE NUMBERS - NEVER DELETE THESE
# =============================================================================
# These phone numbers are protected and will NEVER be released by any cleanup
# script. Add any production phone numbers here to prevent accidental loss.
# When a Connect instance is deleted, any phone numbers attached to it are
# PERMANENTLY released back to the carrier pool and cannot be recovered via API.
# =============================================================================
PROTECTED_PHONE_NUMBERS=(
    "+18447845789"   # Production toll-free number - Agentic Solution for PF
)

# Current voice phone number (must be in PROTECTED_PHONE_NUMBERS for safety)
VOICE_PHONE_NUMBER="+18447845789"

# =============================================================================
# Phone Number Protection Functions
# =============================================================================

# Check if a phone number is protected
# Usage: if is_phone_number_protected "+18447845789"; then echo "Protected!"; fi
is_phone_number_protected() {
    local phone_number="$1"
    for protected in "${PROTECTED_PHONE_NUMBERS[@]}"; do
        if [[ "$protected" == "$phone_number" ]]; then
            return 0  # true - is protected
        fi
    done
    return 1  # false - not protected
}

# Safe release phone number - REFUSES to release protected numbers
# Usage: safe_release_phone_number "phone-number-id" "+18447845789"
safe_release_phone_number() {
    local phone_number_id="$1"
    local phone_number="$2"

    # Check protection
    if is_phone_number_protected "$phone_number"; then
        log_error "BLOCKED: Cannot release protected phone number $phone_number"
        log_error "This number is in PROTECTED_PHONE_NUMBERS list and cannot be released."
        log_error "To release this number, you must first remove it from the protected list in voice.sh"
        return 1
    fi

    log_warn "Releasing phone number: $phone_number (ID: $phone_number_id)"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Would release phone number $phone_number" >&2
        return 0
    fi

    aws connect release-phone-number \
        --phone-number-id "$phone_number_id" \
        --region "$VOICE_REGION" 2>&1
}

# Check if any Connect instance has protected phone numbers
# Returns 0 (success) if safe to delete, 1 if instance has protected numbers
check_instance_for_protected_numbers() {
    local instance_id="$1"

    log_info "Checking instance $instance_id for protected phone numbers..."

    local phone_numbers
    phone_numbers=$(aws connect list-phone-numbers-v2 \
        --target-arn "arn:aws:connect:${VOICE_REGION}:$(get_account_id):instance/${instance_id}" \
        --region "$VOICE_REGION" \
        --query 'ListPhoneNumbersSummaryList[*].PhoneNumber' \
        --output text 2>/dev/null || echo "")

    if [[ -z "$phone_numbers" ]]; then
        log_info "  No phone numbers attached to instance"
        return 0
    fi

    local has_protected=false
    for phone in $phone_numbers; do
        if is_phone_number_protected "$phone"; then
            log_error "  PROTECTED: $phone - Cannot delete this instance!"
            has_protected=true
        else
            log_info "  Unprotected: $phone"
        fi
    done

    if [[ "$has_protected" == "true" ]]; then
        log_error ""
        log_error "This Connect instance has PROTECTED phone numbers attached!"
        log_error "Deleting this instance would permanently release these numbers to the carrier."
        log_error ""
        log_error "To proceed, you must either:"
        log_error "  1. Move the phone numbers to another instance first"
        log_error "  2. Remove the numbers from PROTECTED_PHONE_NUMBERS in voice.sh"
        log_error ""
        return 1
    fi

    return 0
}

# DynamoDB table BASE names for Voice
VOICE_DYNAMODB_TABLE_BASES=(
    "customers"
)

# Build full Lex bot name
# Uses standard naming: ${RESOURCE_PREFIX}-${base}-${ENVIRONMENT}
lex_bot_name() {
    resource_name "$LEX_BOT_BASE"
}

# Build full Connect instance alias
# Uses standard naming: ${RESOURCE_PREFIX}-${base}-${ENVIRONMENT}
connect_instance_alias() {
    resource_name "$CONNECT_INSTANCE_BASE"
}

# Build voice Lambda function name from base
voice_lambda_name() {
    local base="$1"
    resource_name "$base"
}

# Get list of full voice Lambda function names
get_voice_lambda_function_names() {
    local names=()
    for entry in "${VOICE_LAMBDA_FUNCTION_LIST[@]}"; do
        IFS=':' read -r base_name source_dir role_base timeout memory <<< "$entry"
        names+=("$(voice_lambda_name "$base_name")")
    done
    echo "${names[@]}"
}

# Get list of full voice DynamoDB table names
get_voice_table_names() {
    local names=()
    for base in "${VOICE_DYNAMODB_TABLE_BASES[@]}"; do
        names+=("$(table_name "$base")")
    done
    echo "${names[@]}"
}

# =============================================================================
# Voice Lambda Deployment
# =============================================================================

# Deploy voice-related Lambda functions
deploy_voice_lambdas() {
    log_section "Deploying Voice Lambda Functions"
    print_naming_config

    local failed=0

    for entry in "${VOICE_LAMBDA_FUNCTION_LIST[@]}"; do
        IFS=':' read -r base_name source_dir role_base timeout memory <<< "$entry"
        local func_name=$(voice_lambda_name "$base_name")
        local full_role_name=$(role_name "$role_base")
        # Voice Lambda deploys to VOICE_REGION (us-east-1)
        deploy_lambda "$func_name" "$source_dir" "$full_role_name" "$timeout" "$memory" "$role_base" "$VOICE_REGION" || ((failed++))
    done

    if [[ $failed -gt 0 ]]; then
        log_error "Failed to deploy $failed voice Lambda function(s)"
        return 1
    fi

    log_info "All voice Lambda functions deployed successfully"
    return 0
}

# =============================================================================
# Lex Bot Management
# =============================================================================

# Get Lex bot ID by name
get_lex_bot_id() {
    local bot_name="$1"

    aws lexv2-models list-bots \
        --region "$VOICE_REGION" \
        --query "botSummaries[?botName=='$bot_name'].botId" \
        --output text 2>/dev/null
}

# Get Lex bot alias ID
get_lex_bot_alias_id() {
    local bot_id="$1"
    local alias_name="$2"

    aws lexv2-models list-bot-aliases \
        --bot-id "$bot_id" \
        --region "$VOICE_REGION" \
        --query "botAliasSummaries[?botAliasName=='$alias_name'].botAliasId" \
        --output text 2>/dev/null
}

# Deploy/Update Lex bot configuration
deploy_lex_bot() {
    log_section "Deploying Lex Bot"

    local bot_name=$(lex_bot_name)
    log_info "Looking for Lex bot: $bot_name"

    local bot_id
    bot_id=$(get_lex_bot_id "$bot_name")

    if [[ -z "$bot_id" || "$bot_id" == "None" ]]; then
        log_warn "Lex bot $bot_name not found"
        log_info "Attempting to clone from template bot..."

        # Try to clone from the existing template bot
        if clone_lex_bot "pf-scheduling-assistant-dev" "$bot_name"; then
            bot_id=$(get_lex_bot_id "$bot_name")
        else
            log_error "Failed to create Lex bot"
            return 1
        fi
    fi

    log_info "Found Lex bot: $bot_name (ID: $bot_id)"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Update Lex bot configuration: $bot_name"
        echo -e "${YELLOW}  \$ aws lexv2-models list-bot-aliases --bot-id \"$bot_id\" --region \"$VOICE_REGION\"${NC}"
        echo -e "${YELLOW}  \$ aws lexv2-models list-bot-versions --bot-id \"$bot_id\" --region \"$VOICE_REGION\"${NC}"
        echo ""
        return 0
    fi

    # Update bot alias to use latest version
    local alias_id
    alias_id=$(get_lex_bot_alias_id "$bot_id" "$LEX_BOT_ALIAS")

    if [[ -n "$alias_id" && "$alias_id" != "None" ]]; then
        log_info "Found bot alias: $LEX_BOT_ALIAS (ID: $alias_id)"

        # Get current bot version
        local bot_version
        bot_version=$(aws lexv2-models list-bot-versions \
            --bot-id "$bot_id" \
            --region "$VOICE_REGION" \
            --query 'botVersionSummaries[-1].botVersion' \
            --output text 2>/dev/null)

        if [[ -n "$bot_version" && "$bot_version" != "DRAFT" ]]; then
            log_info "Latest bot version: $bot_version"
        fi
    else
        log_warn "Bot alias $LEX_BOT_ALIAS not found"
    fi

    # Configure the bot alias with Lambda code hook (critical for voice calls)
    configure_lex_bot_alias_lambda "$bot_id" "$LEX_BOT_ALIAS"

    log_info "Lex bot configuration verified"
    return 0
}

# Verify Lex fulfillment Lambda connection
verify_lex_fulfillment() {
    local bot_id="$1"
    local fulfillment_lambda=$(voice_lambda_name "lex-fulfillment")

    log_info "Verifying Lex fulfillment Lambda connection..."

    # Get the fulfillment Lambda ARN
    local lambda_arn
    lambda_arn="arn:aws:lambda:${VOICE_REGION}:${EXPECTED_ACCOUNT}:function:${fulfillment_lambda}"

    # Check if Lambda exists
    if aws lambda get-function --function-name "$fulfillment_lambda" --region "$VOICE_REGION" &>/dev/null; then
        log_info "Fulfillment Lambda exists: $fulfillment_lambda"

        # Check Lambda permission for Lex
        local policy
        policy=$(aws lambda get-policy --function-name "$fulfillment_lambda" --region "$VOICE_REGION" 2>/dev/null || echo "")

        if [[ -z "$policy" ]] || ! echo "$policy" | grep -q "lexv2"; then
            log_warn "Lambda may not have Lex invocation permission"
            log_info "Adding Lex permission to Lambda..."

            if [[ "$DRY_RUN" != "true" ]]; then
                aws lambda add-permission \
                    --function-name "$fulfillment_lambda" \
                    --statement-id "lex-invoke-${bot_id}" \
                    --action "lambda:InvokeFunction" \
                    --principal "lexv2.amazonaws.com" \
                    --source-arn "arn:aws:lex:${VOICE_REGION}:${EXPECTED_ACCOUNT}:bot-alias/${bot_id}/*" \
                    --region "$VOICE_REGION" 2>/dev/null || true
            fi
        else
            log_info "Lambda has Lex invocation permission"
        fi
    else
        log_error "Fulfillment Lambda not found: $fulfillment_lambda"
        return 1
    fi

    return 0
}

# Build Lex bot (create new version)
build_lex_bot() {
    local bot_id="$1"

    log_info "Building Lex bot..."

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Build Lex bot: $bot_id"
        echo -e "${YELLOW}  \$ aws lexv2-models build-bot-locale \\\\${NC}"
        echo -e "${YELLOW}      --bot-id \"$bot_id\" \\\\${NC}"
        echo -e "${YELLOW}      --bot-version \"DRAFT\" \\\\${NC}"
        echo -e "${YELLOW}      --locale-id \"$LEX_BOT_LOCALE\" \\\\${NC}"
        echo -e "${YELLOW}      --region \"$VOICE_REGION\"${NC}"
        echo ""
        return 0
    fi

    # Build the bot locale
    aws lexv2-models build-bot-locale \
        --bot-id "$bot_id" \
        --bot-version "DRAFT" \
        --locale-id "$LEX_BOT_LOCALE" \
        --region "$VOICE_REGION" \
        --output text &>/dev/null

    # Wait for build to complete
    log_info "Waiting for bot build to complete..."
    local max_attempts=30
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        local status
        status=$(aws lexv2-models describe-bot-locale \
            --bot-id "$bot_id" \
            --bot-version "DRAFT" \
            --locale-id "$LEX_BOT_LOCALE" \
            --region "$VOICE_REGION" \
            --query 'botLocaleStatus' \
            --output text 2>/dev/null)

        if [[ "$status" == "Built" ]]; then
            log_info "Bot build complete"
            return 0
        elif [[ "$status" == "Failed" ]]; then
            log_error "Bot build failed"
            return 1
        fi

        log_debug "Build status: $status (attempt $attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done

    log_error "Timeout waiting for bot build"
    return 1
}

# =============================================================================
# Connect Management
# =============================================================================

# Get Connect instance ID by alias
get_connect_instance_id() {
    local alias="$1"

    aws connect list-instances \
        --region "$VOICE_REGION" \
        --query "InstanceSummaryList[?InstanceAlias=='$alias'].Id" \
        --output text 2>/dev/null
}

# Validate Connect instance
validate_connect_instance() {
    log_section "Validating Connect Instance"

    local instance_alias=$(connect_instance_alias)
    local instance_id
    instance_id=$(get_connect_instance_id "$instance_alias")

    if [[ -z "$instance_id" || "$instance_id" == "None" ]]; then
        log_error "Connect instance not found: $instance_alias"
        log_info "Connect instances must be created via AWS Console"
        return 1
    fi

    log_info "Found Connect instance: $instance_alias (ID: $instance_id)"

    # Get instance details
    local instance_status
    instance_status=$(aws connect describe-instance \
        --instance-id "$instance_id" \
        --region "$VOICE_REGION" \
        --query 'Instance.InstanceStatus' \
        --output text 2>/dev/null)

    log_info "Instance status: $instance_status"

    # Check for Lex bot association
    log_info "Checking Lex bot associations..."
    local lex_bots
    lex_bots=$(aws connect list-lex-bots \
        --instance-id "$instance_id" \
        --region "$VOICE_REGION" \
        --query 'LexBots[*].Name' \
        --output text 2>/dev/null || echo "")

    if [[ -n "$lex_bots" ]]; then
        log_info "Associated Lex bots: $lex_bots"
    else
        log_warn "No Lex bots associated with Connect instance"
    fi

    return 0
}

# Associate Lex V2 bot with Connect
associate_lex_with_connect() {
    local instance_id="$1"
    local bot_id="$2"
    local alias_id="$3"

    local bot_name=$(lex_bot_name)
    local alias_arn="arn:aws:lex:${VOICE_REGION}:${EXPECTED_ACCOUNT}:bot-alias/${bot_id}/${alias_id}"

    log_info "Associating Lex V2 bot with Connect..."
    log_info "  Bot: $bot_name (ID: $bot_id)"
    log_info "  Alias: $LEX_BOT_ALIAS (ID: $alias_id)"
    log_info "  Alias ARN: $alias_arn"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Associate Lex V2 bot with Connect"
        echo -e "${YELLOW}  \$ aws connect associate-bot \\\\${NC}"
        echo -e "${YELLOW}      --instance-id \"$instance_id\" \\\\${NC}"
        echo -e "${YELLOW}      --lex-v2-bot \"AliasArn=$alias_arn\" \\\\${NC}"
        echo -e "${YELLOW}      --region \"$VOICE_REGION\"${NC}"
        echo ""
        return 0
    fi

    # Use Lex V2 association format (associate-bot, not associate-lex-bot)
    local output
    output=$(aws connect associate-bot \
        --instance-id "$instance_id" \
        --lex-v2-bot "AliasArn=$alias_arn" \
        --region "$VOICE_REGION" 2>&1)

    local result=$?
    if [[ $result -eq 0 ]]; then
        log_info "Lex V2 bot association configured successfully"
    elif echo "$output" | grep -q "ResourceNotFoundException"; then
        # Check if already associated
        local existing
        existing=$(aws connect list-bots \
            --instance-id "$instance_id" \
            --lex-version "V2" \
            --region "$VOICE_REGION" \
            --query "LexBots[?LexV2Bot.AliasArn=='$alias_arn']" \
            --output text 2>/dev/null)

        if [[ -n "$existing" ]]; then
            log_info "Lex V2 bot already associated with Connect"
            return 0
        else
            log_error "Failed to associate Lex bot with Connect: $output"
            return 1
        fi
    else
        log_error "Failed to associate Lex bot with Connect: $output"
        return 1
    fi

    return 0
}

# =============================================================================
# Voice DynamoDB Tables
# =============================================================================

# Deploy voice-related DynamoDB tables
deploy_voice_dynamodb_tables() {
    log_info "Deploying DynamoDB tables for Voice..."

    for base in "${VOICE_DYNAMODB_TABLE_BASES[@]}"; do
        local full_table_name=$(table_name "$base")
        deploy_voice_dynamodb_table "$full_table_name" "$base"
    done
}

# Deploy a single voice DynamoDB table
# Args: full_table_name, base_name
deploy_voice_dynamodb_table() {
    local tbl_name="$1"
    local base_name="$2"

    if aws dynamodb describe-table --table-name "$tbl_name" --region "$VOICE_REGION" &>/dev/null; then
        log_info "Table $tbl_name already exists - skipping"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        local key_attr="session_id"
        [[ "$base_name" == "customers" ]] && key_attr="phone_number"
        echo -e "${CYAN}[DRY-RUN]${NC} Create DynamoDB table: $tbl_name"
        echo -e "${YELLOW}  \$ aws dynamodb create-table \\\\${NC}"
        echo -e "${YELLOW}      --table-name \"$tbl_name\" \\\\${NC}"
        echo -e "${YELLOW}      --attribute-definitions AttributeName=$key_attr,AttributeType=S \\\\${NC}"
        echo -e "${YELLOW}      --key-schema AttributeName=$key_attr,KeyType=HASH \\\\${NC}"
        echo -e "${YELLOW}      --billing-mode PAY_PER_REQUEST \\\\${NC}"
        echo -e "${YELLOW}      --region \"$VOICE_REGION\"${NC}"
        echo ""
        return 0
    fi

    log_info "Creating DynamoDB table: $tbl_name"

    local create_output
    # Customer table has phone_number as key
    if [[ "$base_name" == "customers" ]]; then
        create_output=$(aws dynamodb create-table \
            --table-name "$tbl_name" \
            --attribute-definitions AttributeName=phone_number,AttributeType=S \
            --key-schema AttributeName=phone_number,KeyType=HASH \
            --billing-mode PAY_PER_REQUEST \
            --region "$VOICE_REGION" \
            --output text 2>&1)
    else
        # Default session-based schema
        create_output=$(aws dynamodb create-table \
            --table-name "$tbl_name" \
            --attribute-definitions AttributeName=session_id,AttributeType=S \
            --key-schema AttributeName=session_id,KeyType=HASH \
            --billing-mode PAY_PER_REQUEST \
            --region "$VOICE_REGION" \
            --output text 2>&1)
    fi

    local create_result=$?
    if [[ $create_result -ne 0 ]]; then
        log_error "Failed to create table $tbl_name: $create_output"
        return 1
    fi

    # Wait for table to be active (with timeout)
    log_info "Waiting for table $tbl_name to become active..."
    local max_wait=60
    local waited=0
    while [[ $waited -lt $max_wait ]]; do
        local status
        status=$(aws dynamodb describe-table --table-name "$tbl_name" --region "$VOICE_REGION" \
            --query 'Table.TableStatus' --output text 2>/dev/null)

        if [[ "$status" == "ACTIVE" ]]; then
            log_info "Table $tbl_name is now ACTIVE"
            return 0
        fi

        log_debug "Table status: $status (waiting... $waited/$max_wait seconds)"
        sleep 5
        ((waited+=5))
    done

    log_error "Timeout waiting for table $tbl_name to become active"
    return 1
}

# =============================================================================
# Voice Deployment (All Components)
# =============================================================================

# Deploy all voice components
deploy_voice() {
    log_section "Deploying Voice Integration"

    local failed=0

    # Deploy DynamoDB tables first
    deploy_voice_dynamodb_tables

    # Deploy voice Lambdas
    deploy_voice_lambdas || ((failed++))

    # Deploy/verify Lex bot (or import if missing)
    deploy_lex_bot || import_lex_bot || ((failed++))

    # Validate Connect instance and associate Lex bot
    validate_connect_instance || ((failed++))

    # Associate Lex bot with Connect if both exist
    associate_lex_bot_with_connect_if_needed || log_warn "Could not associate Lex bot with Connect"

    # Deploy Contact Flows
    deploy_contact_flows || ((failed++))

    # Update Contact Flows to use the correct Lex bot ARN
    # This is CRITICAL - ensures the Contact Flow references the correct environment's Lex bot
    update_all_contact_flows_lex_bot || log_warn "Could not update Contact Flow Lex bot references"

    # Configure voice phone number routing
    configure_voice_phone_number || log_warn "Could not configure phone number routing"

    if [[ $failed -gt 0 ]]; then
        log_warn "Voice deployment completed with $failed warning(s)"
        log_info "Some voice components require manual setup via AWS Console"
    else
        log_info "Voice integration deployed successfully"
    fi

    return 0
}

# Associate Lex bot with Connect if both exist and not already associated
associate_lex_bot_with_connect_if_needed() {
    local bot_name=$(lex_bot_name)
    local instance_alias=$(connect_instance_alias)

    # Get bot ID
    local bot_id
    bot_id=$(get_lex_bot_id "$bot_name")

    if [[ -z "$bot_id" || "$bot_id" == "None" ]]; then
        log_warn "Lex bot not found: $bot_name"
        return 1
    fi

    # Get alias ID
    local alias_id
    alias_id=$(get_lex_bot_alias_id "$bot_id" "$LEX_BOT_ALIAS")

    if [[ -z "$alias_id" || "$alias_id" == "None" ]]; then
        log_warn "Lex bot alias not found: $LEX_BOT_ALIAS"
        return 1
    fi

    # Get Connect instance ID
    local instance_id
    instance_id=$(get_connect_instance_id "$instance_alias")

    if [[ -z "$instance_id" || "$instance_id" == "None" ]]; then
        log_warn "Connect instance not found: $instance_alias"
        return 1
    fi

    # Check if already associated
    local associated_bots
    associated_bots=$(aws connect list-lex-bots \
        --instance-id "$instance_id" \
        --region "$VOICE_REGION" \
        --output json 2>/dev/null || echo "{}")

    if echo "$associated_bots" | grep -q "$bot_id"; then
        log_info "Lex bot already associated with Connect"
        return 0
    fi

    # Associate the bot
    log_info "Associating Lex bot with Connect..."
    associate_lex_with_connect "$instance_id" "$bot_id" "$alias_id"

    return $?
}

# =============================================================================
# Voice Cleanup
# =============================================================================

# Cleanup voice Lambda functions
cleanup_voice_lambdas() {
    log_section "Cleaning Up Voice Lambda Functions"
    print_naming_config

    for entry in "${VOICE_LAMBDA_FUNCTION_LIST[@]}"; do
        IFS=':' read -r base_name source_dir role_base timeout memory <<< "$entry"
        local func_name=$(voice_lambda_name "$base_name")
        local full_role_name=$(role_name "$role_base")
        # Voice Lambda is in VOICE_REGION (us-east-1)
        cleanup_lambda "$func_name" "$full_role_name" "$VOICE_REGION"
    done

    log_info "Voice Lambda functions cleaned up"
}

# Cleanup Lex bot
cleanup_lex_bot() {
    log_section "Cleaning Up Lex Bot"

    local bot_name=$(lex_bot_name)
    local bot_id
    bot_id=$(get_lex_bot_id "$bot_name")

    if [[ -z "$bot_id" || "$bot_id" == "None" ]]; then
        log_debug "Lex bot $bot_name does not exist"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Delete Lex bot: $bot_name (ID: $bot_id)"
        echo -e "${YELLOW}  \$ aws lexv2-models list-bot-aliases --bot-id \"$bot_id\" --region \"$VOICE_REGION\"${NC}"
        echo -e "${YELLOW}  \$ aws lexv2-models delete-bot-alias --bot-id \"$bot_id\" --bot-alias-id \"<alias_id>\" --region \"$VOICE_REGION\"${NC}"
        echo -e "${YELLOW}  \$ aws lexv2-models delete-bot --bot-id \"$bot_id\" --region \"$VOICE_REGION\"${NC}"
        echo ""
        return 0
    fi

    log_info "Deleting Lex bot: $bot_name (ID: $bot_id)"

    # Delete all aliases first
    local aliases
    aliases=$(aws lexv2-models list-bot-aliases \
        --bot-id "$bot_id" \
        --region "$VOICE_REGION" \
        --query 'botAliasSummaries[*].botAliasId' \
        --output text 2>/dev/null)

    for alias_id in $aliases; do
        if [[ -n "$alias_id" && "$alias_id" != "None" && "$alias_id" != "TSTALIASID" ]]; then
            log_debug "Deleting bot alias: $alias_id"
            aws lexv2-models delete-bot-alias \
                --bot-id "$bot_id" \
                --bot-alias-id "$alias_id" \
                --region "$VOICE_REGION" 2>/dev/null || true
        fi
    done

    # Delete all versions except DRAFT
    local versions
    versions=$(aws lexv2-models list-bot-versions \
        --bot-id "$bot_id" \
        --region "$VOICE_REGION" \
        --query 'botVersionSummaries[?botVersion!=`DRAFT`].botVersion' \
        --output text 2>/dev/null)

    for version in $versions; do
        if [[ -n "$version" && "$version" != "None" ]]; then
            log_debug "Deleting bot version: $version"
            aws lexv2-models delete-bot-version \
                --bot-id "$bot_id" \
                --bot-version "$version" \
                --region "$VOICE_REGION" 2>/dev/null || true
        fi
    done

    # Delete the bot
    aws lexv2-models delete-bot \
        --bot-id "$bot_id" \
        --region "$VOICE_REGION" 2>/dev/null

    log_info "Lex bot deleted: $bot_name"
    return 0
}

# Cleanup voice DynamoDB tables
cleanup_voice_dynamodb_tables() {
    log_info "Cleaning up Voice DynamoDB tables..."

    for base in "${VOICE_DYNAMODB_TABLE_BASES[@]}"; do
        local full_table_name=$(table_name "$base")
        if aws dynamodb describe-table --table-name "$full_table_name" --region "$VOICE_REGION" &>/dev/null; then
            if [[ "$DRY_RUN" == "true" ]]; then
                echo -e "${CYAN}[DRY-RUN]${NC} Delete DynamoDB table: $full_table_name"
                echo -e "${YELLOW}  \$ aws dynamodb delete-table --table-name \"$full_table_name\" --region \"$VOICE_REGION\"${NC}"
                echo ""
            else
                log_info "Deleting table: $full_table_name"
                aws dynamodb delete-table --table-name "$full_table_name" --region "$VOICE_REGION" 2>/dev/null
            fi
        fi
    done
}

# Cleanup all voice components
cleanup_voice() {
    log_section "Cleaning Up Voice Integration"

    local confirmation_msg="This will delete voice Lambdas, Lex bot, and related resources. Continue?"
    if ! confirm_action "$confirmation_msg"; then
        log_info "Cleanup cancelled"
        return 0
    fi

    # Cleanup in reverse order
    cleanup_lex_bot
    cleanup_voice_lambdas
    cleanup_voice_dynamodb_tables

    log_info "Voice integration cleaned up"
    log_warn "Connect instance must be deleted manually via AWS Console"
    return 0
}

# =============================================================================
# Voice Validation
# =============================================================================

# Validate all voice resources
validate_voice() {
    log_section "Validating Voice Resources"
    print_naming_config

    local failed=0

    # Validate voice Lambdas
    for entry in "${VOICE_LAMBDA_FUNCTION_LIST[@]}"; do
        IFS=':' read -r base_name source_dir role_base timeout memory <<< "$entry"
        local func_name=$(voice_lambda_name "$base_name")
        if aws lambda get-function --function-name "$func_name" --region "$VOICE_REGION" &>/dev/null; then
            local state
            state=$(aws lambda get-function --function-name "$func_name" --region "$VOICE_REGION" \
                --query 'Configuration.State' --output text 2>/dev/null)
            if [[ "$state" == "Active" ]]; then
                log_info "$func_name: Active"
            else
                log_warn "$func_name: $state"
                ((failed++))
            fi
        else
            log_error "$func_name: NOT FOUND"
            ((failed++))
        fi
    done

    # Validate Lex bot
    local bot_name=$(lex_bot_name)
    local bot_id
    bot_id=$(get_lex_bot_id "$bot_name")
    if [[ -n "$bot_id" && "$bot_id" != "None" ]]; then
        log_info "Lex bot $bot_name: EXISTS (ID: $bot_id)"
    else
        log_error "Lex bot $bot_name: NOT FOUND"
        ((failed++))
    fi

    # Validate Connect instance
    local instance_alias=$(connect_instance_alias)
    local instance_id
    instance_id=$(get_connect_instance_id "$instance_alias")
    if [[ -n "$instance_id" && "$instance_id" != "None" ]]; then
        log_info "Connect instance $instance_alias: EXISTS"
    else
        log_error "Connect instance $instance_alias: NOT FOUND"
        ((failed++))
    fi

    # Validate DynamoDB tables
    for base in "${VOICE_DYNAMODB_TABLE_BASES[@]}"; do
        local full_table_name=$(table_name "$base")
        if aws dynamodb describe-table --table-name "$full_table_name" --region "$VOICE_REGION" &>/dev/null; then
            log_info "Table $full_table_name: EXISTS"
        else
            log_error "Table $full_table_name: NOT FOUND"
            ((failed++))
        fi
    done

    # Validate voice phone number
    validate_voice_phone_number || ((failed++))

    # Validate Contact Flows
    validate_contact_flows || ((failed++))

    if [[ $failed -gt 0 ]]; then
        log_error "Validation failed: $failed resource(s) missing or unhealthy"
        return 1
    fi

    log_info "All voice resources validated successfully"
    return 0
}

# List voice resources
list_voice_resources() {
    log_section "Voice Resources (${RESOURCE_PREFIX}-*-${ENVIRONMENT})"

    echo ""
    echo "Voice Lambda Functions:"
    for entry in "${VOICE_LAMBDA_FUNCTION_LIST[@]}"; do
        IFS=':' read -r base_name source_dir role_base timeout memory <<< "$entry"
        echo "  - $(voice_lambda_name "$base_name")"
    done

    echo ""
    echo "Lex Bot: $(lex_bot_name)"
    echo "Connect Instance: $(connect_instance_alias)"
    echo "Voice Phone: $VOICE_PHONE_NUMBER"

    echo ""
    echo "DynamoDB Tables:"
    for base in "${VOICE_DYNAMODB_TABLE_BASES[@]}"; do
        echo "  - $(table_name "$base")"
    done
}

# =============================================================================
# Phone Number Management
# =============================================================================

# Get Connect phone number ID by phone number
# Usage: phone_id=$(get_connect_phone_number_id "+14702832382")
get_connect_phone_number_id() {
    local phone_number="$1"

    aws connect list-phone-numbers-v2 \
        --region "$VOICE_REGION" \
        --query "ListPhoneNumbersSummaryList[?PhoneNumber=='$phone_number'].PhoneNumberId" \
        --output text 2>/dev/null
}

# Check if phone number has Contact Flow association
# Returns: Contact Flow ID or empty if not associated
get_phone_number_contact_flow() {
    local instance_id="$1"
    local phone_number_id="$2"

    # Note: AWS Connect API doesn't directly return contact flow association
    # The phone number routing is managed via Contact Flow association
    # We need to check via associate-phone-number-contact-flow
    aws connect describe-phone-number \
        --phone-number-id "$phone_number_id" \
        --region "$VOICE_REGION" \
        --query 'ClaimedPhoneNumberSummary.TargetArn' \
        --output text 2>/dev/null
}

# Associate phone number with a Contact Flow
# Args: instance_id, phone_number_id, contact_flow_id
associate_phone_number_with_contact_flow() {
    local instance_id="$1"
    local phone_number_id="$2"
    local contact_flow_id="$3"
    local phone_number="${4:-$VOICE_PHONE_NUMBER}"

    log_info "Associating phone number $phone_number with Contact Flow..."
    log_info "  Phone Number ID: $phone_number_id"
    log_info "  Contact Flow ID: $contact_flow_id"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Associate phone number with Contact Flow" >&2
        echo -e "${YELLOW}  \$ aws connect associate-phone-number-contact-flow \\\\${NC}" >&2
        echo -e "${YELLOW}      --phone-number-id \"$phone_number_id\" \\\\${NC}" >&2
        echo -e "${YELLOW}      --instance-id \"$instance_id\" \\\\${NC}" >&2
        echo -e "${YELLOW}      --contact-flow-id \"$contact_flow_id\" \\\\${NC}" >&2
        echo -e "${YELLOW}      --region \"$VOICE_REGION\"${NC}" >&2
        echo "" >&2
        return 0
    fi

    local output
    output=$(aws connect associate-phone-number-contact-flow \
        --phone-number-id "$phone_number_id" \
        --instance-id "$instance_id" \
        --contact-flow-id "$contact_flow_id" \
        --region "$VOICE_REGION" 2>&1)

    local result=$?
    if [[ $result -eq 0 ]]; then
        log_info "Phone number successfully associated with Contact Flow"
        return 0
    else
        # Check if already associated or other error
        if echo "$output" | grep -q "already associated\|ResourceConflictException"; then
            log_info "Phone number already associated with a Contact Flow"
            return 0
        else
            log_error "Failed to associate phone number with Contact Flow: $output"
            return 1
        fi
    fi
}

# Configure voice phone number routing
# This finds the phone number and associates it with the main inbound contact flow
configure_voice_phone_number() {
    log_section "Configuring Voice Phone Number Routing"

    local instance_alias=$(connect_instance_alias)
    local instance_id
    instance_id=$(get_connect_instance_id "$instance_alias")

    if [[ -z "$instance_id" || "$instance_id" == "None" ]]; then
        log_error "Connect instance not found: $instance_alias"
        return 1
    fi

    # Get phone number ID
    local phone_number_id
    phone_number_id=$(get_connect_phone_number_id "$VOICE_PHONE_NUMBER")

    if [[ -z "$phone_number_id" || "$phone_number_id" == "None" ]]; then
        log_warn "Phone number not found in Connect: $VOICE_PHONE_NUMBER"
        log_info "Attempting to claim phone number automatically..."

        # Try to ensure the phone number is claimed
        if ensure_phone_number_claimed; then
            # Re-fetch the phone number ID after claiming
            phone_number_id=$(get_connect_phone_number_id "$VOICE_PHONE_NUMBER")
            if [[ -z "$phone_number_id" || "$phone_number_id" == "None" ]]; then
                log_error "Phone number still not found after claim attempt"
                return 1
            fi
        else
            log_error "Failed to claim phone number: $VOICE_PHONE_NUMBER"
            log_info "You may need to manually claim the number or set VOICE_PHONE_NUMBER=AUTO"
            return 1
        fi
    fi

    log_info "Found phone number: $VOICE_PHONE_NUMBER (ID: $phone_number_id)"

    # Get the main inbound contact flow ID
    local main_flow_name=$(contact_flow_name "main-inbound-voice")
    local contact_flow_id
    contact_flow_id=$(aws connect list-contact-flows \
        --instance-id "$instance_id" \
        --region "$VOICE_REGION" \
        --query "ContactFlowSummaryList[?Name=='$main_flow_name'].Id" \
        --output text 2>/dev/null)

    if [[ -z "$contact_flow_id" || "$contact_flow_id" == "None" ]]; then
        # Try alternate flow name patterns
        log_warn "Contact Flow not found: $main_flow_name"
        log_info "Checking for existing inbound flows..."

        # List available flows
        local flows
        flows=$(aws connect list-contact-flows \
            --instance-id "$instance_id" \
            --contact-flow-types "CONTACT_FLOW" \
            --region "$VOICE_REGION" \
            --query "ContactFlowSummaryList[*].{Name:Name,Id:Id}" \
            --output json 2>/dev/null)

        log_debug "Available Contact Flows: $flows"

        # Try to find any main or inbound flow
        contact_flow_id=$(echo "$flows" | jq -r '.[] | select(.Name | test("(?i)main|inbound|voice")) | .Id' | head -1)

        if [[ -z "$contact_flow_id" || "$contact_flow_id" == "null" ]]; then
            log_warn "No suitable Contact Flow found for phone number routing"
            log_info "Deploy Contact Flows first, then re-run phone number configuration"
            return 1
        fi

        local found_flow_name
        found_flow_name=$(echo "$flows" | jq -r ".[] | select(.Id==\"$contact_flow_id\") | .Name")
        log_info "Using Contact Flow: $found_flow_name (ID: $contact_flow_id)"
    else
        log_info "Found Contact Flow: $main_flow_name (ID: $contact_flow_id)"
    fi

    # Associate phone number with contact flow
    associate_phone_number_with_contact_flow "$instance_id" "$phone_number_id" "$contact_flow_id" "$VOICE_PHONE_NUMBER"
}

# Validate voice phone number configuration
validate_voice_phone_number() {
    log_info "Validating voice phone number configuration..."

    local phone_number_id
    phone_number_id=$(get_connect_phone_number_id "$VOICE_PHONE_NUMBER")

    if [[ -z "$phone_number_id" || "$phone_number_id" == "None" ]]; then
        log_error "Voice phone number not found: $VOICE_PHONE_NUMBER"
        return 1
    fi

    log_info "Phone number $VOICE_PHONE_NUMBER: CLAIMED (ID: $phone_number_id)"

    # Get target ARN to verify it's associated with the instance
    local target_arn
    target_arn=$(aws connect describe-phone-number \
        --phone-number-id "$phone_number_id" \
        --region "$VOICE_REGION" \
        --query 'ClaimedPhoneNumberSummary.TargetArn' \
        --output text 2>/dev/null)

    if [[ -n "$target_arn" && "$target_arn" != "None" ]]; then
        log_info "Phone number target: $target_arn"
    else
        log_warn "Phone number not associated with any instance"
    fi

    return 0
}

# Search for available phone numbers in the region
# Args: country_code (default: US), phone_number_type (default: DID), area_code (optional)
# Returns: JSON list of available phone numbers
search_available_phone_numbers() {
    local country_code="${1:-US}"
    local phone_number_type="${2:-DID}"
    local area_code="${3:-}"

    log_info "Searching for available $phone_number_type phone numbers in $country_code..."

    local search_cmd="aws connect search-available-phone-numbers \
        --target-arn \"arn:aws:connect:${VOICE_REGION}:${EXPECTED_ACCOUNT}:instance/\$(get_connect_instance_id \"\$(connect_instance_alias)\")\" \
        --phone-number-country-code $country_code \
        --phone-number-type $phone_number_type \
        --region $VOICE_REGION \
        --max-results 10"

    if [[ -n "$area_code" ]]; then
        search_cmd="$search_cmd --phone-number-prefix \"+1${area_code}\""
    fi

    eval "$search_cmd" 2>/dev/null
}

# Claim a phone number for the Connect instance
# Args: phone_number (e.g., +14702832382)
# Returns: Phone number ID if successful
claim_phone_number() {
    local phone_number="$1"
    local instance_alias=$(connect_instance_alias)
    local instance_id
    instance_id=$(get_connect_instance_id "$instance_alias")

    if [[ -z "$instance_id" || "$instance_id" == "None" ]]; then
        log_error "Connect instance not found: $instance_alias"
        return 1
    fi

    local target_arn="arn:aws:connect:${VOICE_REGION}:${EXPECTED_ACCOUNT}:instance/${instance_id}"

    log_info "Claiming phone number $phone_number for instance $instance_alias..."
    log_info "  Target ARN: $target_arn"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Claim phone number: $phone_number" >&2
        echo -e "${YELLOW}  \$ aws connect claim-phone-number \\\\${NC}" >&2
        echo -e "${YELLOW}      --target-arn \"$target_arn\" \\\\${NC}" >&2
        echo -e "${YELLOW}      --phone-number \"$phone_number\" \\\\${NC}" >&2
        echo -e "${YELLOW}      --region \"$VOICE_REGION\"${NC}" >&2
        echo "" >&2
        return 0
    fi

    local output
    output=$(aws connect claim-phone-number \
        --target-arn "$target_arn" \
        --phone-number "$phone_number" \
        --region "$VOICE_REGION" 2>&1)

    local result=$?
    if [[ $result -eq 0 ]]; then
        local phone_number_id
        phone_number_id=$(echo "$output" | jq -r '.PhoneNumberId // empty')
        log_info "Phone number claimed successfully: $phone_number (ID: $phone_number_id)"
        echo "$phone_number_id"
        return 0
    else
        if echo "$output" | grep -q "ResourceInUseException\|already claimed"; then
            log_warn "Phone number $phone_number is already claimed"
            # Try to get the ID
            local existing_id
            existing_id=$(get_connect_phone_number_id "$phone_number")
            if [[ -n "$existing_id" && "$existing_id" != "None" ]]; then
                echo "$existing_id"
                return 0
            fi
        fi
        log_error "Failed to claim phone number: $output"
        return 1
    fi
}

# Release a phone number from Connect
# Args: phone_number_id
release_phone_number() {
    local phone_number_id="$1"

    log_info "Releasing phone number ID: $phone_number_id..."

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Release phone number ID: $phone_number_id" >&2
        echo -e "${YELLOW}  \$ aws connect release-phone-number \\\\${NC}" >&2
        echo -e "${YELLOW}      --phone-number-id \"$phone_number_id\" \\\\${NC}" >&2
        echo -e "${YELLOW}      --region \"$VOICE_REGION\"${NC}" >&2
        echo "" >&2
        return 0
    fi

    local output
    output=$(aws connect release-phone-number \
        --phone-number-id "$phone_number_id" \
        --region "$VOICE_REGION" 2>&1)

    local result=$?
    if [[ $result -eq 0 ]]; then
        log_info "Phone number released successfully"
        return 0
    else
        log_error "Failed to release phone number: $output"
        return 1
    fi
}

# Ensure the configured phone number is claimed for the Connect instance
# If not claimed and VOICE_PHONE_NUMBER is specific, try to claim it
# If VOICE_PHONE_NUMBER is "AUTO", search and claim an available number
ensure_phone_number_claimed() {
    log_section "Ensuring Phone Number is Claimed"

    local instance_alias=$(connect_instance_alias)
    local instance_id
    instance_id=$(get_connect_instance_id "$instance_alias")

    if [[ -z "$instance_id" || "$instance_id" == "None" ]]; then
        log_error "Connect instance not found: $instance_alias"
        return 1
    fi

    local target_arn="arn:aws:connect:${VOICE_REGION}:${EXPECTED_ACCOUNT}:instance/${instance_id}"

    # Check if phone number is already claimed for this instance
    local phone_number_id
    phone_number_id=$(get_connect_phone_number_id "$VOICE_PHONE_NUMBER")

    if [[ -n "$phone_number_id" && "$phone_number_id" != "None" ]]; then
        # Phone number exists, check if it's for our instance
        local current_target
        current_target=$(aws connect describe-phone-number \
            --phone-number-id "$phone_number_id" \
            --region "$VOICE_REGION" \
            --query 'ClaimedPhoneNumberSummary.TargetArn' \
            --output text 2>/dev/null)

        if [[ "$current_target" == "$target_arn" ]]; then
            log_info "Phone number $VOICE_PHONE_NUMBER is already claimed for this instance"
            return 0
        else
            log_warn "Phone number $VOICE_PHONE_NUMBER is claimed by a different instance: $current_target"
            log_warn "You may need to release it from the other instance first"
            return 1
        fi
    fi

    # Phone number not claimed, try to claim it
    log_info "Phone number $VOICE_PHONE_NUMBER is not claimed"

    if [[ "$VOICE_PHONE_NUMBER" == "AUTO" ]]; then
        # Search for available numbers and claim the first one
        log_info "Searching for available phone numbers..."
        local available
        available=$(aws connect search-available-phone-numbers \
            --target-arn "$target_arn" \
            --phone-number-country-code US \
            --phone-number-type DID \
            --region "$VOICE_REGION" \
            --max-results 5 \
            --query 'AvailableNumbersList[0].PhoneNumber' \
            --output text 2>/dev/null)

        if [[ -z "$available" || "$available" == "None" ]]; then
            log_error "No available phone numbers found"
            return 1
        fi

        log_info "Found available number: $available"
        VOICE_PHONE_NUMBER="$available"
    fi

    # Try to claim the specific phone number
    phone_number_id=$(claim_phone_number "$VOICE_PHONE_NUMBER")
    local result=$?

    if [[ $result -eq 0 && -n "$phone_number_id" ]]; then
        log_info "Successfully claimed phone number: $VOICE_PHONE_NUMBER"
        return 0
    else
        log_error "Failed to claim phone number: $VOICE_PHONE_NUMBER"
        log_info "The phone number may need to be released from another instance first"
        log_info "Or you can set VOICE_PHONE_NUMBER=AUTO to claim a new available number"
        return 1
    fi
}

# Release and reclaim a phone number for the current instance
# This is useful when migrating a number between instances
# Args: phone_number (optional, defaults to VOICE_PHONE_NUMBER)
release_and_reclaim_phone_number() {
    local phone_number="${1:-$VOICE_PHONE_NUMBER}"

    log_section "Release and Reclaim Phone Number"
    log_info "Phone number: $phone_number"

    # Step 1: Find the phone number
    local phone_number_id
    phone_number_id=$(get_connect_phone_number_id "$phone_number")

    if [[ -z "$phone_number_id" || "$phone_number_id" == "None" ]]; then
        log_warn "Phone number $phone_number not found - attempting to claim directly"
        ensure_phone_number_claimed
        return $?
    fi

    # Step 2: Check current target
    local current_target
    current_target=$(aws connect describe-phone-number \
        --phone-number-id "$phone_number_id" \
        --region "$VOICE_REGION" \
        --query 'ClaimedPhoneNumberSummary.TargetArn' \
        --output text 2>/dev/null)

    local instance_alias=$(connect_instance_alias)
    local instance_id
    instance_id=$(get_connect_instance_id "$instance_alias")
    local target_arn="arn:aws:connect:${VOICE_REGION}:${EXPECTED_ACCOUNT}:instance/${instance_id}"

    if [[ "$current_target" == "$target_arn" ]]; then
        log_info "Phone number is already claimed for this instance"
        return 0
    fi

    log_info "Phone number currently assigned to: $current_target"
    log_info "Will reassign to: $target_arn"

    # Step 3: Release the phone number
    log_info "Releasing phone number..."
    if ! release_phone_number "$phone_number_id"; then
        log_error "Failed to release phone number"
        return 1
    fi

    # Wait for release to complete
    log_info "Waiting for phone number release to complete..."
    sleep 10

    # Step 4: Reclaim for our instance
    log_info "Reclaiming phone number for target instance..."
    local new_phone_id
    new_phone_id=$(claim_phone_number "$phone_number")

    if [[ $? -eq 0 && -n "$new_phone_id" ]]; then
        log_info "Successfully reclaimed phone number: $phone_number (ID: $new_phone_id)"
        return 0
    else
        log_error "Failed to reclaim phone number"
        log_error "The number may have been claimed by another account"
        return 1
    fi
}

# =============================================================================
# Contact Flow Management
# =============================================================================

# Contact Flow definitions
CONTACT_FLOW_CONFIG_DIR="$SCRIPT_DIR/config/connect"

# Contact Flow BASE names (without prefix/environment)
CONTACT_FLOW_BASES=(
    "main-inbound-voice"
    "scheduling-voice"
)

# Build full Contact Flow name from base
contact_flow_name() {
    local base="$1"
    resource_name "$base"
}

# Deploy Contact Flow from JSON definition
# Args: base_name, instance_id
# Note: Config files use static names (pf-<base>.json or pf-<base>-<env>.json)
#       Resources get dynamic names at deploy time
deploy_contact_flow() {
    local base_name="$1"
    local instance_id="$2"
    local flow_name=$(contact_flow_name "$base_name")

    # Try environment-specific config first, then generic
    local config_file="$CONTACT_FLOW_CONFIG_DIR/pf-${base_name}-${ENVIRONMENT}.json"
    if [[ ! -f "$config_file" ]]; then
        config_file="$CONTACT_FLOW_CONFIG_DIR/pf-${base_name}.json"
    fi

    log_info "Deploying Contact Flow: $flow_name"

    if [[ ! -f "$config_file" ]]; then
        log_error "Contact Flow config not found: $config_file"
        return 1
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Deploy Contact Flow: $flow_name"
        echo -e "${YELLOW}  Config file: $config_file${NC}"
        echo -e "${YELLOW}  \$ aws connect create-contact-flow \\\\${NC}"
        echo -e "${YELLOW}      --instance-id \"$instance_id\" \\\\${NC}"
        echo -e "${YELLOW}      --name \"$flow_name\" \\\\${NC}"
        echo -e "${YELLOW}      --type \"CONTACT_FLOW\" \\\\${NC}"
        echo -e "${YELLOW}      --content \"<flow_content_from_json>\" \\\\${NC}"
        echo -e "${YELLOW}      --region \"$VOICE_REGION\"${NC}"
        echo ""
        echo -e "${YELLOW}  # OR update existing flow${NC}"
        echo -e "${YELLOW}  \$ aws connect update-contact-flow-content --instance-id \"$instance_id\" --contact-flow-id \"<id>\" --content \"<content>\" --region \"$VOICE_REGION\"${NC}"
        echo ""
        return 0
    fi

    # Extract the Content field from the JSON
    local flow_content
    flow_content=$(jq -r '.ContactFlow.Content' "$config_file")

    if [[ -z "$flow_content" || "$flow_content" == "null" ]]; then
        log_error "Invalid Contact Flow config: missing Content"
        return 1
    fi

    # Check if flow already exists
    local existing_flow_id
    existing_flow_id=$(aws connect list-contact-flows \
        --instance-id "$instance_id" \
        --region "$VOICE_REGION" \
        --query "ContactFlowSummaryList[?Name=='$flow_name'].Id" \
        --output text 2>/dev/null)

    if [[ -n "$existing_flow_id" && "$existing_flow_id" != "None" ]]; then
        # Update existing flow
        log_info "Updating existing Contact Flow: $flow_name (ID: $existing_flow_id)"

        aws connect update-contact-flow-content \
            --instance-id "$instance_id" \
            --contact-flow-id "$existing_flow_id" \
            --content "$flow_content" \
            --region "$VOICE_REGION" 2>/dev/null

        if [[ $? -eq 0 ]]; then
            log_info "Contact Flow updated: $flow_name"
        else
            log_error "Failed to update Contact Flow: $flow_name"
            return 1
        fi
    else
        # Create new flow
        log_info "Creating new Contact Flow: $flow_name"

        local description
        description=$(jq -r '.ContactFlow.Description // ""' "$config_file")

        aws connect create-contact-flow \
            --instance-id "$instance_id" \
            --name "$flow_name" \
            --type "CONTACT_FLOW" \
            --description "$description" \
            --content "$flow_content" \
            --region "$VOICE_REGION" 2>/dev/null

        if [[ $? -eq 0 ]]; then
            log_info "Contact Flow created: $flow_name"
        else
            log_error "Failed to create Contact Flow: $flow_name"
            return 1
        fi
    fi

    return 0
}

# Deploy all Contact Flows
deploy_contact_flows() {
    log_section "Deploying Contact Flows"

    local instance_alias=$(connect_instance_alias)
    local instance_id
    instance_id=$(get_connect_instance_id "$instance_alias")

    if [[ -z "$instance_id" || "$instance_id" == "None" ]]; then
        log_error "Connect instance not found: $instance_alias"
        log_info "Create Connect instance first, then deploy Contact Flows"
        return 1
    fi

    local failed=0
    for base in "${CONTACT_FLOW_BASES[@]}"; do
        deploy_contact_flow "$base" "$instance_id" || ((failed++))
    done

    if [[ $failed -gt 0 ]]; then
        log_error "Failed to deploy $failed Contact Flow(s)"
        return 1
    fi

    log_info "All Contact Flows deployed successfully"
    return 0
}

# Export Contact Flow to JSON (for backup)
export_contact_flow() {
    local flow_name="$1"
    local instance_id="$2"
    local output_file="${3:-$CONTACT_FLOW_CONFIG_DIR/${flow_name}.json}"

    log_info "Exporting Contact Flow: $flow_name"

    # Get flow ID
    local flow_id
    flow_id=$(aws connect list-contact-flows \
        --instance-id "$instance_id" \
        --region "$VOICE_REGION" \
        --query "ContactFlowSummaryList[?Name=='$flow_name'].Id" \
        --output text 2>/dev/null)

    if [[ -z "$flow_id" || "$flow_id" == "None" ]]; then
        log_error "Contact Flow not found: $flow_name"
        return 1
    fi

    # Export the flow
    aws connect describe-contact-flow \
        --instance-id "$instance_id" \
        --contact-flow-id "$flow_id" \
        --region "$VOICE_REGION" \
        --output json > "$output_file"

    log_info "Exported to: $output_file"
    return 0
}

# Validate Contact Flows
validate_contact_flows() {
    log_info "Validating Contact Flows..."

    local instance_alias=$(connect_instance_alias)
    local instance_id
    instance_id=$(get_connect_instance_id "$instance_alias")

    if [[ -z "$instance_id" || "$instance_id" == "None" ]]; then
        log_error "Connect instance not found"
        return 1
    fi

    local failed=0
    for base in "${CONTACT_FLOW_BASES[@]}"; do
        local flow_name=$(contact_flow_name "$base")
        local flow_id
        flow_id=$(aws connect list-contact-flows \
            --instance-id "$instance_id" \
            --region "$VOICE_REGION" \
            --query "ContactFlowSummaryList[?Name=='$flow_name'].Id" \
            --output text 2>/dev/null)

        if [[ -n "$flow_id" && "$flow_id" != "None" ]]; then
            log_info "Contact Flow $flow_name: EXISTS (ID: $flow_id)"
        else
            log_error "Contact Flow $flow_name: NOT FOUND"
            ((failed++))
        fi
    done

    return $failed
}

# =============================================================================
# Contact Flow Lex Bot Configuration
# =============================================================================
# This is CRITICAL: Contact Flows must reference the correct Lex bot ARN.
# If the Contact Flow references the wrong bot (e.g., dev instead of prod),
# the voice calls will fail or invoke the wrong fulfillment Lambda.
# =============================================================================

# Update Contact Flow to use the correct Lex bot ARN
# This function finds all Lex bot references in a Contact Flow and updates them
# to use the current environment's Lex bot.
# Args: instance_id, contact_flow_id
update_contact_flow_lex_bot() {
    local instance_id="$1"
    local contact_flow_id="$2"

    local bot_name=$(lex_bot_name)
    local bot_id
    bot_id=$(get_lex_bot_id "$bot_name")

    if [[ -z "$bot_id" || "$bot_id" == "None" ]]; then
        log_error "Cannot update Contact Flow - Lex bot not found: $bot_name"
        return 1
    fi

    local alias_id
    alias_id=$(get_lex_bot_alias_id "$bot_id" "$LEX_BOT_ALIAS")

    if [[ -z "$alias_id" || "$alias_id" == "None" ]]; then
        log_error "Cannot update Contact Flow - Lex bot alias not found: $LEX_BOT_ALIAS"
        return 1
    fi

    local target_lex_arn="arn:aws:lex:${VOICE_REGION}:${EXPECTED_ACCOUNT}:bot-alias/${bot_id}/${alias_id}"

    log_info "Updating Contact Flow Lex bot reference..."
    log_info "  Target Lex ARN: $target_lex_arn"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Update Contact Flow Lex bot ARN" >&2
        echo -e "${YELLOW}  Contact Flow ID: $contact_flow_id${NC}" >&2
        echo -e "${YELLOW}  Target Lex ARN: $target_lex_arn${NC}" >&2
        echo "" >&2
        return 0
    fi

    # Get current Contact Flow content
    local flow_content
    flow_content=$(aws connect describe-contact-flow \
        --instance-id "$instance_id" \
        --contact-flow-id "$contact_flow_id" \
        --region "$VOICE_REGION" \
        --query 'ContactFlow.Content' \
        --output text 2>/dev/null)

    if [[ -z "$flow_content" ]]; then
        log_error "Failed to get Contact Flow content"
        return 1
    fi

    # Check if Contact Flow has any Lex bot references
    if ! echo "$flow_content" | grep -q "bot-alias"; then
        log_info "Contact Flow has no Lex bot references - skipping"
        return 0
    fi

    # Extract current Lex ARN(s) from the flow
    local current_arns
    current_arns=$(echo "$flow_content" | grep -o 'arn:aws:lex:[^"]*bot-alias/[^"]*' | sort -u)

    if [[ -z "$current_arns" ]]; then
        log_info "No Lex bot ARNs found in Contact Flow"
        return 0
    fi

    log_info "Current Lex ARN(s) in Contact Flow:"
    echo "$current_arns" | while read -r arn; do
        log_info "  - $arn"
    done

    # Check if already using the correct ARN
    if echo "$current_arns" | grep -q "$target_lex_arn"; then
        log_info "Contact Flow already using correct Lex bot"
        return 0
    fi

    # Update all Lex bot ARNs to the target ARN
    # This handles different bot IDs (e.g., MCMSOW2OXJ -> 8WGHCIZS8C)
    local updated_content="$flow_content"

    # Replace any bot-alias ARN with the target ARN
    # Pattern: arn:aws:lex:REGION:ACCOUNT:bot-alias/BOT_ID/ALIAS_ID
    updated_content=$(echo "$updated_content" | sed -E "s|arn:aws:lex:[^:]+:[0-9]+:bot-alias/[A-Z0-9]+/[A-Z0-9]+|${target_lex_arn}|g")

    # Also update the metadata bot name references
    # Handle all possible bot name patterns (dev/prod, with/without -syn- prefix)
    updated_content=$(echo "$updated_content" | sed "s/pf-scheduling-assistant-dev/${bot_name}/g")
    updated_content=$(echo "$updated_content" | sed "s/pf-scheduling-assistant-prod/${bot_name}/g")
    updated_content=$(echo "$updated_content" | sed "s/pf-syn-scheduling-assistant-dev/${bot_name}/g")
    updated_content=$(echo "$updated_content" | sed "s/pf-syn-scheduling-assistant-prod/${bot_name}/g")

    # Apply the update
    local output
    output=$(aws connect update-contact-flow-content \
        --instance-id "$instance_id" \
        --contact-flow-id "$contact_flow_id" \
        --content "$updated_content" \
        --region "$VOICE_REGION" 2>&1)

    local result=$?
    if [[ $result -eq 0 ]]; then
        log_info "Contact Flow updated to use Lex bot: $bot_name"
    else
        log_error "Failed to update Contact Flow: $output"
        return 1
    fi

    return 0
}

# Update all Contact Flows to use the correct Lex bot
update_all_contact_flows_lex_bot() {
    log_section "Updating Contact Flows with Correct Lex Bot"

    local instance_alias=$(connect_instance_alias)
    local instance_id
    instance_id=$(get_connect_instance_id "$instance_alias")

    if [[ -z "$instance_id" || "$instance_id" == "None" ]]; then
        log_error "Connect instance not found: $instance_alias"
        return 1
    fi

    local failed=0
    for base in "${CONTACT_FLOW_BASES[@]}"; do
        local flow_name=$(contact_flow_name "$base")
        local flow_id
        flow_id=$(aws connect list-contact-flows \
            --instance-id "$instance_id" \
            --region "$VOICE_REGION" \
            --query "ContactFlowSummaryList[?Name=='$flow_name'].Id" \
            --output text 2>/dev/null)

        if [[ -n "$flow_id" && "$flow_id" != "None" ]]; then
            log_info "Checking Contact Flow: $flow_name"
            update_contact_flow_lex_bot "$instance_id" "$flow_id" || ((failed++))
        else
            log_warn "Contact Flow not found: $flow_name"
        fi
    done

    if [[ $failed -gt 0 ]]; then
        log_error "Failed to update $failed Contact Flow(s)"
        return 1
    fi

    log_info "All Contact Flows updated successfully"
    return 0
}

# =============================================================================
# Lex Bot Import/Export
# =============================================================================

LEX_BOT_CONFIG_DIR="$SCRIPT_DIR/config/lex"

# Get Lex bot export file path
# Note: Config files use static names (templates), resources get dynamic names at deploy time
lex_bot_export_file() {
    # Use the static template file name (pf-scheduling-assistant-dev.zip)
    # The bot will be created with the dynamic name from lex_bot_name()
    echo "$LEX_BOT_CONFIG_DIR/pf-${LEX_BOT_BASE}-${ENVIRONMENT}.zip"
}

# Import Lex bot from export file
import_lex_bot() {
    log_section "Importing Lex Bot"

    local bot_name=$(lex_bot_name)
    local export_file=$(lex_bot_export_file)
    local lex_role=$(role_name "lex-bot")

    if [[ ! -f "$export_file" ]]; then
        log_error "Lex bot export file not found: $export_file"
        return 1
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Import Lex bot: $bot_name"
        echo -e "${YELLOW}  Export file: $export_file${NC}"
        echo -e "${YELLOW}  \$ aws lexv2-models create-bot-import \\\\${NC}"
        echo -e "${YELLOW}      --import-id \"import-<timestamp>\" \\\\${NC}"
        echo -e "${YELLOW}      --resource-specification \"botImportSpecification={botName=$bot_name,roleArn=arn:aws:iam::${EXPECTED_ACCOUNT}:role/${lex_role},dataPrivacy={childDirected=false},idleSessionTTLInSeconds=300}\" \\\\${NC}"
        echo -e "${YELLOW}      --merge-strategy \"FailOnConflict\" \\\\${NC}"
        echo -e "${YELLOW}      --region \"$VOICE_REGION\"${NC}"
        echo ""
        return 0
    fi

    # Check if bot already exists
    local existing_bot_id
    existing_bot_id=$(get_lex_bot_id "$bot_name")

    if [[ -n "$existing_bot_id" && "$existing_bot_id" != "None" ]]; then
        log_info "Lex bot already exists: $bot_name (ID: $existing_bot_id)"
        log_info "To update, delete the existing bot first"
        return 0
    fi

    log_info "Creating Lex bot import..."

    # Upload the export file to S3 or use local path
    # Note: Lex import requires the file to be accessible
    local import_id
    import_id=$(aws lexv2-models create-bot-import \
        --import-id "import-$(date +%s)" \
        --resource-specification "botImportSpecification={botName=$bot_name,roleArn=arn:aws:iam::${EXPECTED_ACCOUNT}:role/${lex_role},dataPrivacy={childDirected=false},idleSessionTTLInSeconds=300}" \
        --merge-strategy "FailOnConflict" \
        --file-password "" \
        --region "$VOICE_REGION" \
        --query 'importId' \
        --output text 2>/dev/null || echo "")

    if [[ -z "$import_id" ]]; then
        log_warn "Direct import not available"
        log_info "To import Lex bot:"
        log_info "  1. Go to AWS Console > Amazon Lex V2"
        log_info "  2. Click 'Action' > 'Import'"
        log_info "  3. Upload: $export_file"
        return 1
    fi

    log_info "Import started: $import_id"
    return 0
}

# Export Lex bot to file (for backup)
export_lex_bot() {
    local bot_name=$(lex_bot_name)
    local output_file="${1:-$(lex_bot_export_file)}"

    log_info "Exporting Lex bot: $bot_name"

    local bot_id
    bot_id=$(get_lex_bot_id "$bot_name")

    if [[ -z "$bot_id" || "$bot_id" == "None" ]]; then
        log_error "Lex bot not found: $bot_name"
        return 1
    fi

    # Create export
    local export_response
    export_response=$(aws lexv2-models create-export \
        --resource-specification "botExportSpecification={botId=$bot_id,botVersion=DRAFT}" \
        --file-format LexJson \
        --region "$VOICE_REGION" \
        --output json 2>/dev/null)

    local export_id
    export_id=$(echo "$export_response" | jq -r '.exportId')

    if [[ -z "$export_id" || "$export_id" == "null" ]]; then
        log_error "Failed to create export"
        return 1
    fi

    log_info "Export created: $export_id"
    log_info "Waiting for export to complete..."

    # Wait for export
    local max_attempts=30
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        local status
        status=$(aws lexv2-models describe-export \
            --export-id "$export_id" \
            --region "$VOICE_REGION" \
            --query 'exportStatus' \
            --output text 2>/dev/null)

        if [[ "$status" == "Completed" ]]; then
            # Get download URL
            local download_url
            download_url=$(aws lexv2-models describe-export \
                --export-id "$export_id" \
                --region "$VOICE_REGION" \
                --query 'downloadUrl' \
                --output text 2>/dev/null)

            if [[ -n "$download_url" ]]; then
                curl -s -o "$output_file" "$download_url"
                log_info "Exported to: $output_file"
                return 0
            fi
        elif [[ "$status" == "Failed" ]]; then
            log_error "Export failed"
            return 1
        fi

        sleep 5
        ((attempt++))
    done

    log_error "Timeout waiting for export"
    return 1
}

# =============================================================================
# Lex Bot Clone (Export from source, Import with new name)
# =============================================================================

# Clone an existing Lex bot with a new name
# Usage: clone_lex_bot "source-bot-name" "target-bot-name"
# If no source is provided, uses the template bot (pf-scheduling-assistant-dev)
clone_lex_bot() {
    local source_bot_name="${1:-pf-scheduling-assistant-dev}"
    local target_bot_name="${2:-$(lex_bot_name)}"
    local lex_role=$(role_name "lex-bot")
    local temp_export="/tmp/lex-bot-export-$(date +%s).zip"

    log_section "Cloning Lex Bot"
    log_info "Source: $source_bot_name"
    log_info "Target: $target_bot_name"

    # Check if target already exists
    local existing_bot_id
    existing_bot_id=$(get_lex_bot_id "$target_bot_name")
    if [[ -n "$existing_bot_id" && "$existing_bot_id" != "None" ]]; then
        log_info "Target bot already exists: $target_bot_name (ID: $existing_bot_id)"
        return 0
    fi

    # Get source bot ID
    local source_bot_id
    source_bot_id=$(get_lex_bot_id "$source_bot_name")
    if [[ -z "$source_bot_id" || "$source_bot_id" == "None" ]]; then
        log_error "Source bot not found: $source_bot_name"
        return 1
    fi

    log_info "Source bot ID: $source_bot_id"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Clone Lex bot: $source_bot_name -> $target_bot_name" >&2
        echo -e "${YELLOW}  Step 1: Export source bot${NC}" >&2
        echo -e "${YELLOW}    \$ aws lexv2-models create-export --resource-specification \"botExportSpecification={botId=$source_bot_id,botVersion=DRAFT}\" --file-format LexJson${NC}" >&2
        echo -e "${YELLOW}  Step 2: Download export file${NC}" >&2
        echo -e "${YELLOW}    \$ curl -o \"$temp_export\" \"<download_url>\"${NC}" >&2
        echo -e "${YELLOW}  Step 3: Create upload URL${NC}" >&2
        echo -e "${YELLOW}    \$ aws lexv2-models create-upload-url${NC}" >&2
        echo -e "${YELLOW}  Step 4: Upload export file${NC}" >&2
        echo -e "${YELLOW}    \$ curl -X PUT -T \"$temp_export\" \"<upload_url>\"${NC}" >&2
        echo -e "${YELLOW}  Step 5: Start import with new name${NC}" >&2
        echo -e "${YELLOW}    \$ aws lexv2-models start-import --import-id \"<import_id>\" \\\\${NC}" >&2
        echo -e "${YELLOW}        --resource-specification \"botImportSpecification={botName=$target_bot_name,roleArn=arn:aws:iam::${EXPECTED_ACCOUNT}:role/$lex_role,dataPrivacy={childDirected=false},idleSessionTTLInSeconds=300}\" \\\\${NC}" >&2
        echo -e "${YELLOW}        --merge-strategy FailOnConflict${NC}" >&2
        echo -e "${YELLOW}  Step 6: Wait for import and build bot${NC}" >&2
        echo "" >&2
        return 0
    fi

    # Ensure IAM role exists for the new bot
    ensure_lex_role "$lex_role"

    # Step 1: Export source bot
    log_info "Step 1: Exporting source bot..."
    local export_response
    export_response=$(aws lexv2-models create-export \
        --resource-specification "botExportSpecification={botId=$source_bot_id,botVersion=DRAFT}" \
        --file-format LexJson \
        --region "$VOICE_REGION" \
        --output json 2>&1)

    local export_result=$?
    if [[ $export_result -ne 0 ]]; then
        log_error "Failed to create export: $export_response"
        return 1
    fi

    local export_id
    export_id=$(echo "$export_response" | jq -r '.exportId')
    if [[ -z "$export_id" || "$export_id" == "null" ]]; then
        log_error "Failed to parse export ID from response"
        return 1
    fi

    log_info "Export ID: $export_id"
    log_info "Waiting for export to complete..."

    # Wait for export
    local max_attempts=60
    local attempt=1
    local download_url=""

    while [[ $attempt -le $max_attempts ]]; do
        local status
        status=$(aws lexv2-models describe-export \
            --export-id "$export_id" \
            --region "$VOICE_REGION" \
            --query 'exportStatus' \
            --output text 2>/dev/null)

        if [[ "$status" == "Completed" ]]; then
            download_url=$(aws lexv2-models describe-export \
                --export-id "$export_id" \
                --region "$VOICE_REGION" \
                --query 'downloadUrl' \
                --output text 2>/dev/null)
            break
        elif [[ "$status" == "Failed" ]]; then
            log_error "Export failed"
            return 1
        fi

        log_debug "Export status: $status (attempt $attempt/$max_attempts)"
        sleep 3
        ((attempt++))
    done

    if [[ -z "$download_url" ]]; then
        log_error "Timeout waiting for export"
        return 1
    fi

    # Step 2: Download export file
    log_info "Step 2: Downloading export file..."
    curl -s -o "$temp_export" "$download_url"
    if [[ ! -f "$temp_export" ]]; then
        log_error "Failed to download export file"
        return 1
    fi
    log_info "Downloaded to: $temp_export ($(du -h "$temp_export" | cut -f1))"

    # Step 3: Create upload URL
    log_info "Step 3: Creating upload URL..."
    local upload_response
    upload_response=$(aws lexv2-models create-upload-url \
        --region "$VOICE_REGION" \
        --output json 2>/dev/null)

    local upload_url
    local import_id
    upload_url=$(echo "$upload_response" | jq -r '.uploadUrl')
    import_id=$(echo "$upload_response" | jq -r '.importId')

    if [[ -z "$upload_url" || "$upload_url" == "null" ]]; then
        log_error "Failed to create upload URL"
        rm -f "$temp_export"
        return 1
    fi

    log_info "Import ID: $import_id"

    # Step 4: Upload export file
    log_info "Step 4: Uploading export file..."
    local upload_result
    upload_result=$(curl -s -w "%{http_code}" -X PUT -T "$temp_export" "$upload_url")
    local http_code="${upload_result: -3}"

    if [[ "$http_code" != "200" ]]; then
        log_error "Failed to upload file (HTTP $http_code)"
        rm -f "$temp_export"
        return 1
    fi
    log_info "Upload successful"

    # Step 5: Start import with new name
    log_info "Step 5: Starting import with new name: $target_bot_name"
    local import_response
    import_response=$(aws lexv2-models start-import \
        --import-id "$import_id" \
        --resource-specification "botImportSpecification={botName=$target_bot_name,roleArn=arn:aws:iam::${EXPECTED_ACCOUNT}:role/$lex_role,dataPrivacy={childDirected=false},idleSessionTTLInSeconds=300}" \
        --merge-strategy "FailOnConflict" \
        --region "$VOICE_REGION" \
        --output json 2>/dev/null)

    if [[ -z "$import_response" ]]; then
        log_error "Failed to start import"
        rm -f "$temp_export"
        return 1
    fi

    # Step 6: Wait for import to complete
    log_info "Step 6: Waiting for import to complete..."
    attempt=1
    while [[ $attempt -le $max_attempts ]]; do
        local import_status
        import_status=$(aws lexv2-models describe-import \
            --import-id "$import_id" \
            --region "$VOICE_REGION" \
            --query 'importStatus' \
            --output text 2>/dev/null)

        if [[ "$import_status" == "Completed" ]]; then
            log_info "Import completed successfully!"
            break
        elif [[ "$import_status" == "Failed" ]]; then
            local failure_reason
            failure_reason=$(aws lexv2-models describe-import \
                --import-id "$import_id" \
                --region "$VOICE_REGION" \
                --query 'failureReasons' \
                --output text 2>/dev/null)
            log_error "Import failed: $failure_reason"
            rm -f "$temp_export"
            return 1
        fi

        log_debug "Import status: $import_status (attempt $attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done

    # Cleanup temp file
    rm -f "$temp_export"

    # Get the new bot ID
    local new_bot_id
    new_bot_id=$(get_lex_bot_id "$target_bot_name")
    if [[ -z "$new_bot_id" || "$new_bot_id" == "None" ]]; then
        log_error "Failed to find imported bot"
        return 1
    fi

    log_info "New bot created: $target_bot_name (ID: $new_bot_id)"

    # Build the bot
    log_info "Building bot locale..."
    build_lex_bot "$new_bot_id"

    # Create bot alias
    create_lex_bot_alias "$new_bot_id" "$LEX_BOT_ALIAS"

    log_info "Lex bot clone completed successfully!"
    return 0
}

# Ensure Lex IAM role exists
ensure_lex_role() {
    local role_name="$1"

    if aws iam get-role --role-name "$role_name" &>/dev/null; then
        log_debug "Lex role exists: $role_name"
        return 0
    fi

    log_info "Creating Lex IAM role: $role_name"

    # Create trust policy for Lex
    local trust_policy='{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lexv2.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }'

    aws iam create-role \
        --role-name "$role_name" \
        --assume-role-policy-document "$trust_policy" \
        --description "IAM role for Lex V2 bot" \
        --output text &>/dev/null

    # Attach basic Lex policy
    aws iam attach-role-policy \
        --role-name "$role_name" \
        --policy-arn "arn:aws:iam::aws:policy/AmazonLexFullAccess" \
        --output text &>/dev/null

    # Wait for role to propagate
    sleep 10

    log_info "Lex role created: $role_name"
    return 0
}

# Create Lex bot alias
create_lex_bot_alias() {
    local bot_id="$1"
    local alias_name="$2"

    # Check if alias already exists
    local existing_alias
    existing_alias=$(get_lex_bot_alias_id "$bot_id" "$alias_name")
    if [[ -n "$existing_alias" && "$existing_alias" != "None" ]]; then
        log_info "Bot alias already exists: $alias_name"
        return 0
    fi

    log_info "Creating bot alias: $alias_name"

    # Get the latest bot version
    local bot_version
    bot_version=$(aws lexv2-models list-bot-versions \
        --bot-id "$bot_id" \
        --region "$VOICE_REGION" \
        --query 'botVersionSummaries[?botVersion!=`DRAFT`].botVersion' \
        --output text 2>/dev/null | tail -1)

    # If no version exists, create one
    if [[ -z "$bot_version" || "$bot_version" == "None" ]]; then
        log_info "Creating bot version..."
        local version_response
        version_response=$(aws lexv2-models create-bot-version \
            --bot-id "$bot_id" \
            --bot-version-locale-specification '{"en_US":{"sourceBotVersion":"DRAFT"}}' \
            --region "$VOICE_REGION" \
            --output json 2>/dev/null)

        bot_version=$(echo "$version_response" | jq -r '.botVersion')

        # Wait for version to be available
        sleep 5
    fi

    log_info "Using bot version: $bot_version"

    # Create alias pointing to the version
    aws lexv2-models create-bot-alias \
        --bot-id "$bot_id" \
        --bot-alias-name "$alias_name" \
        --bot-version "$bot_version" \
        --region "$VOICE_REGION" \
        --output text &>/dev/null

    log_info "Bot alias created: $alias_name"

    # Configure Lambda code hook for the alias
    configure_lex_bot_alias_lambda "$bot_id" "$alias_name"

    return 0
}

# =============================================================================
# Configure Lex Bot Alias with Lambda Code Hook
# =============================================================================
# This is CRITICAL for voice calls to work - without the code hook configuration,
# the Lex bot will not invoke the fulfillment Lambda and calls will disconnect
# immediately after the welcome message.
# =============================================================================

# Configure Lex bot alias with Lambda code hook specification
# Args: bot_id, alias_name (default: $LEX_BOT_ALIAS)
configure_lex_bot_alias_lambda() {
    local bot_id="$1"
    local alias_name="${2:-$LEX_BOT_ALIAS}"
    local fulfillment_lambda=$(voice_lambda_name "lex-fulfillment")
    local lambda_arn="arn:aws:lambda:${VOICE_REGION}:${EXPECTED_ACCOUNT}:function:${fulfillment_lambda}"

    log_info "Configuring Lex bot alias Lambda code hook..."
    log_info "  Bot ID: $bot_id"
    log_info "  Alias: $alias_name"
    log_info "  Lambda: $fulfillment_lambda"

    # Get the alias ID
    local alias_id
    alias_id=$(get_lex_bot_alias_id "$bot_id" "$alias_name")

    if [[ -z "$alias_id" || "$alias_id" == "None" ]]; then
        log_error "Bot alias not found: $alias_name"
        return 1
    fi

    log_info "  Alias ID: $alias_id"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Configure Lex bot alias Lambda code hook" >&2
        echo -e "${YELLOW}  \$ aws lexv2-models update-bot-alias \\\\${NC}" >&2
        echo -e "${YELLOW}      --bot-id \"$bot_id\" \\\\${NC}" >&2
        echo -e "${YELLOW}      --bot-alias-id \"$alias_id\" \\\\${NC}" >&2
        echo -e "${YELLOW}      --bot-alias-name \"$alias_name\" \\\\${NC}" >&2
        echo -e "${YELLOW}      --bot-alias-locale-settings '{\"${LEX_BOT_LOCALE}\":{\"enabled\":true,\"codeHookSpecification\":{\"lambdaCodeHook\":{\"lambdaARN\":\"$lambda_arn\",\"codeHookInterfaceVersion\":\"1.0\"}}}}' \\\\${NC}" >&2
        echo -e "${YELLOW}      --region \"$VOICE_REGION\"${NC}" >&2
        echo "" >&2
        return 0
    fi

    # Check if Lambda exists
    if ! aws lambda get-function --function-name "$fulfillment_lambda" --region "$VOICE_REGION" &>/dev/null; then
        log_error "Fulfillment Lambda not found: $fulfillment_lambda"
        log_info "Deploy voice Lambdas first, then configure the bot alias"
        return 1
    fi

    # Build the locale settings JSON with code hook specification
    local locale_settings=$(cat <<EOF
{
    "${LEX_BOT_LOCALE}": {
        "enabled": true,
        "codeHookSpecification": {
            "lambdaCodeHook": {
                "lambdaARN": "${lambda_arn}",
                "codeHookInterfaceVersion": "1.0"
            }
        }
    }
}
EOF
)

    # Update the bot alias with Lambda code hook
    local output
    output=$(aws lexv2-models update-bot-alias \
        --bot-id "$bot_id" \
        --bot-alias-id "$alias_id" \
        --bot-alias-name "$alias_name" \
        --bot-alias-locale-settings "$locale_settings" \
        --region "$VOICE_REGION" 2>&1)

    local result=$?
    if [[ $result -eq 0 ]]; then
        log_info "Bot alias Lambda code hook configured successfully"
    else
        log_error "Failed to configure bot alias Lambda code hook: $output"
        return 1
    fi

    # Add Lambda permission for Lex to invoke the function
    add_lex_lambda_permission "$bot_id" "$alias_id" "$fulfillment_lambda"

    return 0
}

# Add Lambda permission for Lex bot alias to invoke the function
# Args: bot_id, alias_id, lambda_name
add_lex_lambda_permission() {
    local bot_id="$1"
    local alias_id="$2"
    local lambda_name="$3"
    local statement_id="lex-invoke-${alias_id}"
    local source_arn="arn:aws:lex:${VOICE_REGION}:${EXPECTED_ACCOUNT}:bot-alias/${bot_id}/${alias_id}"

    log_info "Adding Lambda permission for Lex invocation..."
    log_info "  Statement ID: $statement_id"
    log_info "  Source ARN: $source_arn"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Add Lambda permission for Lex" >&2
        echo -e "${YELLOW}  \$ aws lambda add-permission \\\\${NC}" >&2
        echo -e "${YELLOW}      --function-name \"$lambda_name\" \\\\${NC}" >&2
        echo -e "${YELLOW}      --statement-id \"$statement_id\" \\\\${NC}" >&2
        echo -e "${YELLOW}      --action \"lambda:InvokeFunction\" \\\\${NC}" >&2
        echo -e "${YELLOW}      --principal \"lexv2.amazonaws.com\" \\\\${NC}" >&2
        echo -e "${YELLOW}      --source-arn \"$source_arn\" \\\\${NC}" >&2
        echo -e "${YELLOW}      --region \"$VOICE_REGION\"${NC}" >&2
        echo "" >&2
        return 0
    fi

    # Try to add the permission (may fail if it already exists)
    local output
    output=$(aws lambda add-permission \
        --function-name "$lambda_name" \
        --statement-id "$statement_id" \
        --action "lambda:InvokeFunction" \
        --principal "lexv2.amazonaws.com" \
        --source-arn "$source_arn" \
        --region "$VOICE_REGION" 2>&1)

    local result=$?
    if [[ $result -eq 0 ]]; then
        log_info "Lambda permission added successfully"
    elif echo "$output" | grep -q "ResourceConflictException\|already exists"; then
        log_info "Lambda permission already exists"
    else
        log_warn "Could not add Lambda permission: $output"
        log_info "This may already exist or may need manual configuration"
    fi

    return 0
}
