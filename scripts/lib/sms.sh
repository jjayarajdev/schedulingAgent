#!/bin/bash
# =============================================================================
# sms.sh - SMS integration (Pinpoint, SNS, SMS Lambda)
# =============================================================================

# SMS Lambda function BASE definitions (without prefix/environment)
# Format: base_name:source_dir:role_base:timeout:memory
# Compatible with bash 3.2+ (macOS default)
SMS_LAMBDA_FUNCTION_LIST=(
    "sms-inbound:lambda/sms-inbound-processor:sms-inbound:60:512"
)

# SMS configuration
SMS_PHONE_NUMBER="+18786789053"
SMS_ORIGINATION_ID=""  # Will be populated from Pinpoint

# SNS Topic BASE name (actual: ${PREFIX}-sms-inbound-${ENV})
SNS_TOPIC_BASE="sms-inbound"

# DynamoDB table BASE names for SMS
# These tables are required by the SMS Lambda:
#   - sms-sessions: Tracks conversation sessions per phone number
#   - sms-consent: Tracks opt-in/opt-out consent status
#   - sms-messages: Logs all sent and received messages
#   - opt-out-tracking: Tracks opt-out requests for compliance
SMS_DYNAMODB_TABLE_BASES=(
    "sms-sessions"
    "sms-consent"
    "sms-messages"
    "opt-out-tracking"
)

# Build SMS Lambda function name from base
sms_lambda_name() {
    local base="$1"
    resource_name "$base"
}

# Build SNS topic name from base
sns_topic_name() {
    resource_name "$SNS_TOPIC_BASE"
}

# Get list of full SMS Lambda function names
get_sms_lambda_function_names() {
    local names=()
    for entry in "${SMS_LAMBDA_FUNCTION_LIST[@]}"; do
        IFS=':' read -r base_name source_dir role_base timeout memory <<< "$entry"
        names+=("$(sms_lambda_name "$base_name")")
    done
    echo "${names[@]}"
}

# Get list of full SMS DynamoDB table names
get_sms_table_names() {
    local names=()
    for base in "${SMS_DYNAMODB_TABLE_BASES[@]}"; do
        names+=("$(table_name "$base")")
    done
    echo "${names[@]}"
}

# =============================================================================
# SMS Lambda Deployment
# =============================================================================

# Deploy SMS Lambda function
deploy_sms_lambda() {
    log_section "Deploying SMS Lambda Function"
    print_naming_config

    local failed=0

    for entry in "${SMS_LAMBDA_FUNCTION_LIST[@]}"; do
        IFS=':' read -r base_name source_dir role_base timeout memory <<< "$entry"
        local func_name=$(sms_lambda_name "$base_name")
        local full_role_name=$(role_name "$role_base")
        deploy_lambda "$func_name" "$source_dir" "$full_role_name" "$timeout" "$memory" "$role_base" || ((failed++))
    done

    if [[ $failed -gt 0 ]]; then
        log_error "Failed to deploy SMS Lambda function"
        return 1
    fi

    # Configure SNS trigger
    configure_sms_sns_trigger

    log_info "SMS Lambda function deployed successfully"
    return 0
}

# =============================================================================
# SNS Topic Management
# =============================================================================

# Get SNS topic ARN
get_sns_topic_arn() {
    local topic_name="$1"

    aws sns list-topics \
        --region "$VOICE_REGION" \
        --query "Topics[?contains(TopicArn, '$topic_name')].TopicArn" \
        --output text 2>/dev/null | head -1
}

# Create SNS topic for SMS
deploy_sns_topic() {
    log_info "Deploying SNS topic for SMS..."

    local topic_name=$(sns_topic_name)
    local topic_arn
    topic_arn=$(get_sns_topic_arn "$topic_name")

    if [[ -n "$topic_arn" && "$topic_arn" != "None" ]]; then
        log_info "SNS topic already exists: $topic_name"
        echo "$topic_arn"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Create SNS topic: $topic_name" >&2
        echo -e "${YELLOW}  \$ aws sns create-topic --name \"$topic_name\" --region \"$VOICE_REGION\"${NC}" >&2
        echo "" >&2
        # Return a placeholder ARN for dry-run mode (this is the only stdout)
        echo "arn:aws:sns:${AWS_REGION}:${EXPECTED_ACCOUNT}:${topic_name}"
        return 0
    fi

    log_info "Creating SNS topic: $topic_name"

    topic_arn=$(aws sns create-topic \
        --name "$topic_name" \
        --region "$VOICE_REGION" \
        --query 'TopicArn' \
        --output text 2>/dev/null)

    if [[ -n "$topic_arn" ]]; then
        log_info "SNS topic created: $topic_arn"
        echo "$topic_arn"
    else
        log_error "Failed to create SNS topic"
        return 1
    fi
}

# Configure SNS trigger for Lambda
configure_sms_sns_trigger() {
    log_info "Configuring SNS trigger for SMS Lambda..."

    local topic_name=$(sns_topic_name)
    local lambda_func_name=$(sms_lambda_name "sms-inbound")

    local topic_arn
    topic_arn=$(get_sns_topic_arn "$topic_name")

    if [[ -z "$topic_arn" || "$topic_arn" == "None" ]]; then
        log_warn "SNS topic not found, creating..."
        topic_arn=$(deploy_sns_topic)
    fi

    if [[ -z "$topic_arn" ]]; then
        log_error "Cannot configure SNS trigger without topic"
        return 1
    fi

    local lambda_arn="arn:aws:lambda:${AWS_REGION}:${EXPECTED_ACCOUNT}:function:${lambda_func_name}"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Configure SNS trigger for Lambda"
        echo -e "${YELLOW}  \$ aws lambda add-permission \\\\${NC}"
        echo -e "${YELLOW}      --function-name \"$lambda_func_name\" \\\\${NC}"
        echo -e "${YELLOW}      --statement-id \"sns-invoke-${topic_name}\" \\\\${NC}"
        echo -e "${YELLOW}      --action \"lambda:InvokeFunction\" \\\\${NC}"
        echo -e "${YELLOW}      --principal \"sns.amazonaws.com\" \\\\${NC}"
        echo -e "${YELLOW}      --source-arn \"<topic_arn>\" \\\\${NC}"
        echo -e "${YELLOW}      --region \"$VOICE_REGION\"${NC}"
        echo ""
        echo -e "${YELLOW}  \$ aws sns subscribe \\\\${NC}"
        echo -e "${YELLOW}      --topic-arn \"<topic_arn>\" \\\\${NC}"
        echo -e "${YELLOW}      --protocol lambda \\\\${NC}"
        echo -e "${YELLOW}      --notification-endpoint \"$lambda_arn\" \\\\${NC}"
        echo -e "${YELLOW}      --region \"$VOICE_REGION\"${NC}"
        echo ""
        return 0
    fi

    # Add Lambda permission for SNS
    aws lambda add-permission \
        --function-name "$lambda_func_name" \
        --statement-id "sns-invoke-${topic_name}" \
        --action "lambda:InvokeFunction" \
        --principal "sns.amazonaws.com" \
        --source-arn "$topic_arn" \
        --region "$VOICE_REGION" 2>/dev/null || true

    # Subscribe Lambda to SNS topic
    local existing_sub
    existing_sub=$(aws sns list-subscriptions-by-topic \
        --topic-arn "$topic_arn" \
        --region "$VOICE_REGION" \
        --query "Subscriptions[?Protocol=='lambda' && Endpoint=='$lambda_arn'].SubscriptionArn" \
        --output text 2>/dev/null)

    if [[ -z "$existing_sub" || "$existing_sub" == "None" ]]; then
        aws sns subscribe \
            --topic-arn "$topic_arn" \
            --protocol lambda \
            --notification-endpoint "$lambda_arn" \
            --region "$VOICE_REGION" \
            --output text &>/dev/null

        log_info "Lambda subscribed to SNS topic"
    else
        log_debug "Lambda already subscribed to SNS topic"
    fi

    return 0
}

# =============================================================================
# Pinpoint SMS Management
# =============================================================================

# Build two-way IAM role name
# Uses the standard role naming: ${RESOURCE_PREFIX}-${base}-role-${ENVIRONMENT}
sms_twoway_role_name() {
    role_name "sms-twoway"
}

# Get Pinpoint phone number configuration
get_pinpoint_phone_number() {
    log_info "Checking Pinpoint SMS configuration..."

    # List phone numbers
    local phone_info
    phone_info=$(aws pinpoint-sms-voice-v2 describe-phone-numbers \
        --region "$VOICE_REGION" \
        --query "PhoneNumbers[?PhoneNumber=='$SMS_PHONE_NUMBER']" \
        --output json 2>/dev/null)

    if [[ -n "$phone_info" && "$phone_info" != "[]" ]]; then
        log_info "Found Pinpoint phone number: $SMS_PHONE_NUMBER"
        echo "$phone_info"
        return 0
    fi

    log_warn "Phone number not found in Pinpoint: $SMS_PHONE_NUMBER"
    return 1
}

# Get Pinpoint phone number ID
get_pinpoint_phone_number_id() {
    aws pinpoint-sms-voice-v2 describe-phone-numbers \
        --region "$VOICE_REGION" \
        --query "PhoneNumbers[?PhoneNumber=='$SMS_PHONE_NUMBER'].PhoneNumberId" \
        --output text 2>/dev/null
}

# Check if two-way SMS is already configured
check_pinpoint_two_way_status() {
    local phone_number_id="$1"

    local two_way_enabled
    two_way_enabled=$(aws pinpoint-sms-voice-v2 describe-phone-numbers \
        --region "$VOICE_REGION" \
        --query "PhoneNumbers[?PhoneNumberId=='$phone_number_id'].TwoWayEnabled" \
        --output text 2>/dev/null)

    if [[ "$two_way_enabled" == "True" ]]; then
        return 0  # Already enabled
    fi
    return 1  # Not enabled
}

# Create IAM role for Pinpoint to publish to SNS
create_pinpoint_sns_role() {
    local role_name=$(sms_twoway_role_name)
    local topic_arn="$1"

    log_info "Creating IAM role for Pinpoint two-way SMS: $role_name"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Create IAM role: $role_name"
        echo -e "${YELLOW}  \$ aws iam create-role --role-name \"$role_name\" \\\\${NC}"
        echo -e "${YELLOW}      --assume-role-policy-document '<trust_policy>' \\\\${NC}"
        echo -e "${YELLOW}      --region \"$VOICE_REGION\"${NC}"
        echo -e "${YELLOW}  \$ aws iam put-role-policy --role-name \"$role_name\" \\\\${NC}"
        echo -e "${YELLOW}      --policy-name \"sns-publish-policy\" \\\\${NC}"
        echo -e "${YELLOW}      --policy-document '<sns_policy>'${NC}"
        echo ""
        return 0
    fi

    # Check if role exists
    if aws iam get-role --role-name "$role_name" &>/dev/null; then
        log_info "IAM role already exists: $role_name"
        echo "arn:aws:iam::${EXPECTED_ACCOUNT}:role/${role_name}"
        return 0
    fi

    # Trust policy for SMS Voice service
    local trust_policy
    trust_policy=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "sms-voice.amazonaws.com"
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": "${EXPECTED_ACCOUNT}"
                }
            }
        }
    ]
}
EOF
)

    # Create the role
    aws iam create-role \
        --role-name "$role_name" \
        --assume-role-policy-document "$trust_policy" \
        --description "Role for Pinpoint SMS two-way messaging to SNS - ${RESOURCE_PREFIX}-${ENVIRONMENT}" \
        --output text &>/dev/null

    # Policy to allow publishing to SNS topic
    local sns_policy
    sns_policy=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sns:Publish"
            ],
            "Resource": "${topic_arn}"
        }
    ]
}
EOF
)

    # Attach the policy
    aws iam put-role-policy \
        --role-name "$role_name" \
        --policy-name "sns-publish-policy" \
        --policy-document "$sns_policy" &>/dev/null

    log_info "IAM role created: $role_name"

    # Wait for role to propagate
    sleep 5

    echo "arn:aws:iam::${EXPECTED_ACCOUNT}:role/${role_name}"
}

# Configure Pinpoint two-way SMS
configure_pinpoint_two_way_sms() {
    local topic_arn="$1"

    log_section "Configuring Pinpoint Two-Way SMS"
    log_info "Phone Number: $SMS_PHONE_NUMBER"
    log_info "SNS Topic ARN: $topic_arn"

    # Get phone number ID
    local phone_number_id
    phone_number_id=$(get_pinpoint_phone_number_id)

    if [[ -z "$phone_number_id" || "$phone_number_id" == "None" ]]; then
        log_error "Phone number not found in Pinpoint: $SMS_PHONE_NUMBER"
        log_info "You need to register a phone number in AWS End User Messaging (Pinpoint) first"
        return 1
    fi

    log_info "Phone Number ID: $phone_number_id"

    # Check current two-way status
    if check_pinpoint_two_way_status "$phone_number_id"; then
        log_info "Two-way SMS is already enabled for $SMS_PHONE_NUMBER"

        # Verify it's pointing to correct SNS topic
        local current_channel
        current_channel=$(aws pinpoint-sms-voice-v2 describe-phone-numbers \
            --region "$VOICE_REGION" \
            --query "PhoneNumbers[?PhoneNumberId=='$phone_number_id'].TwoWayChannelArn" \
            --output text 2>/dev/null)

        if [[ "$current_channel" == "$topic_arn" ]]; then
            log_info "Two-way channel is correctly configured to: $topic_arn"
            return 0
        else
            log_warn "Two-way channel points to different topic: $current_channel"
            log_info "Updating to new topic: $topic_arn"
        fi
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        # Build expected topic ARN for dry-run display
        local expected_topic_arn
        if [[ -z "$topic_arn" || "$topic_arn" != arn:aws:sns:* ]]; then
            expected_topic_arn="arn:aws:sns:${AWS_REGION}:${EXPECTED_ACCOUNT}:$(sns_topic_name)"
        else
            expected_topic_arn="$topic_arn"
        fi

        echo -e "${CYAN}[DRY-RUN]${NC} Configure Pinpoint two-way SMS"
        echo -e "${YELLOW}  # Create IAM role for SMS-to-SNS${NC}"
        echo -e "${YELLOW}  \$ aws iam create-role --role-name \"$(sms_twoway_role_name)\" ...${NC}"
        echo ""
        echo -e "${YELLOW}  # Update phone number with two-way configuration${NC}"
        echo -e "${YELLOW}  \$ aws pinpoint-sms-voice-v2 update-phone-number \\\\${NC}"
        echo -e "${YELLOW}      --phone-number-id \"$phone_number_id\" \\\\${NC}"
        echo -e "${YELLOW}      --two-way-enabled \\\\${NC}"
        echo -e "${YELLOW}      --two-way-channel-arn \"$expected_topic_arn\" \\\\${NC}"
        echo -e "${YELLOW}      --two-way-channel-role \"arn:aws:iam::${EXPECTED_ACCOUNT}:role/$(sms_twoway_role_name)\" \\\\${NC}"
        echo -e "${YELLOW}      --region \"$VOICE_REGION\"${NC}"
        echo ""
        return 0
    fi

    # Create IAM role for Pinpoint to publish to SNS
    local role_arn
    role_arn=$(create_pinpoint_sns_role "$topic_arn")

    if [[ -z "$role_arn" ]]; then
        log_error "Failed to create/get IAM role for two-way SMS"
        return 1
    fi

    log_info "Using IAM role: $role_arn"

    # Update phone number with two-way configuration
    log_info "Enabling two-way SMS..."

    local output
    output=$(aws pinpoint-sms-voice-v2 update-phone-number \
        --phone-number-id "$phone_number_id" \
        --two-way-enabled \
        --two-way-channel-arn "$topic_arn" \
        --two-way-channel-role "$role_arn" \
        --region "$VOICE_REGION" 2>&1)

    local result=$?
    if [[ $result -eq 0 ]]; then
        log_info "Two-way SMS configured successfully!"
        log_info "  Phone: $SMS_PHONE_NUMBER"
        log_info "  SNS Topic: $topic_arn"
        log_info "  IAM Role: $role_arn"
        return 0
    else
        if echo "$output" | grep -q "AccessDeniedException"; then
            log_error "Permission denied: sms-voice:UpdatePhoneNumber"
            echo ""
            log_warn "Your IAM user needs the 'sms-voice:UpdatePhoneNumber' permission."
            log_warn "Either request this permission or update manually via AWS Console:"
            echo ""
            echo "  AWS Console: https://us-east-1.console.aws.amazon.com/sms-voice/home?region=us-east-1#/phone-numbers"
            echo ""
            echo "  Or run this command once you have permission:"
            echo "  aws pinpoint-sms-voice-v2 update-phone-number \\"
            echo "    --phone-number-id \"$phone_number_id\" \\"
            echo "    --two-way-enabled \\"
            echo "    --two-way-channel-arn \"$topic_arn\" \\"
            echo "    --two-way-channel-role \"$role_arn\" \\"
            echo "    --region \"$VOICE_REGION\""
            echo ""
        elif echo "$output" | grep -q "ValidationException"; then
            log_warn "Two-way SMS configuration may already exist or has validation issues"
            log_debug "Error: $output"
        else
            log_error "Failed to configure two-way SMS: $output"
        fi
        return 1
    fi
}

# Validate Pinpoint two-way SMS configuration
validate_pinpoint_two_way_sms() {
    log_info "Validating Pinpoint two-way SMS configuration..."

    local phone_number_id
    phone_number_id=$(get_pinpoint_phone_number_id)

    if [[ -z "$phone_number_id" || "$phone_number_id" == "None" ]]; then
        log_error "Phone number not found: $SMS_PHONE_NUMBER"
        return 1
    fi

    # Get full phone number details
    local phone_details
    phone_details=$(aws pinpoint-sms-voice-v2 describe-phone-numbers \
        --region "$VOICE_REGION" \
        --query "PhoneNumbers[?PhoneNumberId=='$phone_number_id']" \
        --output json 2>/dev/null)

    local two_way_enabled
    two_way_enabled=$(echo "$phone_details" | jq -r '.[0].TwoWayEnabled // "false"')

    local two_way_channel
    two_way_channel=$(echo "$phone_details" | jq -r '.[0].TwoWayChannelArn // "None"')

    local two_way_role
    two_way_role=$(echo "$phone_details" | jq -r '.[0].TwoWayChannelRole // "None"')

    echo ""
    log_info "Pinpoint Two-Way SMS Status:"
    log_info "  Phone Number: $SMS_PHONE_NUMBER"
    log_info "  Phone ID: $phone_number_id"
    log_info "  Two-Way Enabled: $two_way_enabled"
    log_info "  SNS Channel: $two_way_channel"
    log_info "  IAM Role: $two_way_role"

    if [[ "$two_way_enabled" == "true" ]]; then
        log_info "Two-way SMS is properly configured"
        return 0
    else
        log_warn "Two-way SMS is NOT enabled"
        return 1
    fi
}

# =============================================================================
# SMS DynamoDB Tables
# =============================================================================

# Deploy SMS-related DynamoDB tables
deploy_sms_dynamodb_tables() {
    log_info "Deploying DynamoDB tables for SMS..."

    for base in "${SMS_DYNAMODB_TABLE_BASES[@]}"; do
        local full_table_name=$(table_name "$base")
        deploy_sms_dynamodb_table "$full_table_name" "$base"
    done
}

# Deploy a single SMS DynamoDB table
# Tables have different key schemas:
#   - sms-sessions: phone_number (HASH) + phone-index GSI
#   - sms-consent, opt-out-tracking: phone_number (HASH)
#   - sms-messages: message_id (HASH)
deploy_sms_dynamodb_table() {
    local tbl_name="$1"
    local base_name="$2"  # Optional: base name to determine key schema

    if aws dynamodb describe-table --table-name "$tbl_name" --region "$VOICE_REGION" &>/dev/null; then
        log_debug "Table $tbl_name already exists"
        # Check if sms-sessions table needs phone-index GSI
        if [[ "$base_name" == "sms-sessions" || "$tbl_name" == *"sms-sessions"* ]]; then
            local has_gsi
            has_gsi=$(aws dynamodb describe-table --table-name "$tbl_name" --region "$VOICE_REGION" \
                --query "Table.GlobalSecondaryIndexes[?IndexName=='phone-index'].IndexName" --output text 2>/dev/null)
            if [[ -z "$has_gsi" || "$has_gsi" == "None" ]]; then
                log_info "Adding phone-index GSI to $tbl_name..."
                aws dynamodb update-table \
                    --table-name "$tbl_name" \
                    --attribute-definitions AttributeName=phone_number,AttributeType=S \
                    --global-secondary-index-updates \
                    "[{\"Create\":{\"IndexName\":\"phone-index\",\"KeySchema\":[{\"AttributeName\":\"phone_number\",\"KeyType\":\"HASH\"}],\"Projection\":{\"ProjectionType\":\"ALL\"}}}]" \
                    --region "$VOICE_REGION" &>/dev/null || true
            fi
        fi
        return 0
    fi

    # Determine key attribute based on table type
    local key_attr="phone_number"
    local key_type="S"
    if [[ "$base_name" == "sms-messages" || "$tbl_name" == *"sms-messages"* ]]; then
        key_attr="message_id"
    fi

    # Check if sms-sessions table needs GSI
    local gsi_option=""
    if [[ "$base_name" == "sms-sessions" || "$tbl_name" == *"sms-sessions"* ]]; then
        gsi_option='--global-secondary-indexes [{"IndexName":"phone-index","KeySchema":[{"AttributeName":"phone_number","KeyType":"HASH"}],"Projection":{"ProjectionType":"ALL"}}]'
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Create DynamoDB table: $tbl_name"
        echo -e "${YELLOW}  \$ aws dynamodb create-table \\\\${NC}"
        echo -e "${YELLOW}      --table-name \"$tbl_name\" \\\\${NC}"
        echo -e "${YELLOW}      --attribute-definitions AttributeName=$key_attr,AttributeType=$key_type \\\\${NC}"
        echo -e "${YELLOW}      --key-schema AttributeName=$key_attr,KeyType=HASH \\\\${NC}"
        if [[ -n "$gsi_option" ]]; then
            echo -e "${YELLOW}      $gsi_option \\\\${NC}"
        fi
        echo -e "${YELLOW}      --billing-mode PAY_PER_REQUEST \\\\${NC}"
        echo -e "${YELLOW}      --region \"$VOICE_REGION\"${NC}"
        echo ""
        return 0
    fi

    log_info "Creating DynamoDB table: $tbl_name (key: $key_attr)"

    if [[ -n "$gsi_option" ]]; then
        aws dynamodb create-table \
            --table-name "$tbl_name" \
            --attribute-definitions "AttributeName=$key_attr,AttributeType=$key_type" \
            --key-schema "AttributeName=$key_attr,KeyType=HASH" \
            --global-secondary-indexes '[{"IndexName":"phone-index","KeySchema":[{"AttributeName":"phone_number","KeyType":"HASH"}],"Projection":{"ProjectionType":"ALL"}}]' \
            --billing-mode PAY_PER_REQUEST \
            --region "$VOICE_REGION" \
            --output text &>/dev/null
    else
        aws dynamodb create-table \
            --table-name "$tbl_name" \
            --attribute-definitions "AttributeName=$key_attr,AttributeType=$key_type" \
            --key-schema "AttributeName=$key_attr,KeyType=HASH" \
            --billing-mode PAY_PER_REQUEST \
            --region "$VOICE_REGION" \
            --output text &>/dev/null
    fi

    # Wait for table to be active
    aws dynamodb wait table-exists --table-name "$tbl_name" --region "$VOICE_REGION" 2>/dev/null
}

# =============================================================================
# SMS Deployment (All Components)
# =============================================================================

# Deploy all SMS components
deploy_sms() {
    log_section "Deploying SMS Integration"

    local failed=0

    # Deploy DynamoDB tables first
    deploy_sms_dynamodb_tables

    # Deploy SNS topic
    local topic_arn
    topic_arn=$(deploy_sns_topic)

    # Deploy SMS Lambda
    deploy_sms_lambda || ((failed++))

    # Configure Pinpoint (may require manual setup)
    get_pinpoint_phone_number
    if [[ -n "$topic_arn" ]]; then
        configure_pinpoint_two_way_sms "$topic_arn" || true
    fi

    if [[ $failed -gt 0 ]]; then
        log_error "SMS deployment failed"
        return 1
    fi

    log_info "SMS integration deployed successfully"
    return 0
}

# =============================================================================
# SMS Cleanup
# =============================================================================

# Cleanup SMS Lambda
cleanup_sms_lambda() {
    log_section "Cleaning Up SMS Lambda"
    print_naming_config

    for entry in "${SMS_LAMBDA_FUNCTION_LIST[@]}"; do
        IFS=':' read -r base_name source_dir role_base timeout memory <<< "$entry"
        local func_name=$(sms_lambda_name "$base_name")
        local full_role_name=$(role_name "$role_base")
        cleanup_lambda "$func_name" "$full_role_name"
    done

    log_info "SMS Lambda cleaned up"
}

# Cleanup SNS topic
cleanup_sns_topic() {
    log_info "Cleaning up SNS topic..."

    local topic_name=$(sns_topic_name)
    local topic_arn
    topic_arn=$(get_sns_topic_arn "$topic_name")

    if [[ -z "$topic_arn" || "$topic_arn" == "None" ]]; then
        log_debug "SNS topic does not exist"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Delete SNS topic: $topic_name"
        echo -e "${YELLOW}  \$ aws sns list-subscriptions-by-topic --topic-arn \"$topic_arn\" --region \"$VOICE_REGION\"${NC}"
        echo -e "${YELLOW}  \$ aws sns unsubscribe --subscription-arn \"<sub_arn>\" --region \"$VOICE_REGION\"${NC}"
        echo -e "${YELLOW}  \$ aws sns delete-topic --topic-arn \"$topic_arn\" --region \"$VOICE_REGION\"${NC}"
        echo ""
        return 0
    fi

    # Delete all subscriptions first
    local subscriptions
    subscriptions=$(aws sns list-subscriptions-by-topic \
        --topic-arn "$topic_arn" \
        --region "$VOICE_REGION" \
        --query 'Subscriptions[*].SubscriptionArn' \
        --output text 2>/dev/null)

    for sub_arn in $subscriptions; do
        if [[ -n "$sub_arn" && "$sub_arn" != "None" && "$sub_arn" != "PendingConfirmation" ]]; then
            log_debug "Deleting subscription: $sub_arn"
            aws sns unsubscribe --subscription-arn "$sub_arn" --region "$VOICE_REGION" 2>/dev/null || true
        fi
    done

    # Delete the topic
    aws sns delete-topic --topic-arn "$topic_arn" --region "$VOICE_REGION" 2>/dev/null
    log_info "SNS topic deleted: $topic_name"
}

# Cleanup SMS DynamoDB tables
cleanup_sms_dynamodb_tables() {
    log_info "Cleaning up SMS DynamoDB tables..."

    for base in "${SMS_DYNAMODB_TABLE_BASES[@]}"; do
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

# Cleanup all SMS components
cleanup_sms() {
    log_section "Cleaning Up SMS Integration"

    local confirmation_msg="This will delete SMS Lambda, SNS topic, and related resources. Continue?"
    if ! confirm_action "$confirmation_msg"; then
        log_info "Cleanup cancelled"
        return 0
    fi

    # Cleanup in reverse order
    cleanup_sns_topic
    cleanup_sms_lambda
    cleanup_sms_dynamodb_tables

    log_info "SMS integration cleaned up"
    log_warn "Pinpoint phone number must be released manually via AWS Console"
    return 0
}

# =============================================================================
# SMS Validation
# =============================================================================

# Validate all SMS resources
validate_sms() {
    log_section "Validating SMS Resources"
    print_naming_config

    local failed=0

    # Validate SMS Lambda
    for entry in "${SMS_LAMBDA_FUNCTION_LIST[@]}"; do
        IFS=':' read -r base_name source_dir role_base timeout memory <<< "$entry"
        local func_name=$(sms_lambda_name "$base_name")
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

    # Validate SNS topic
    local topic_name=$(sns_topic_name)
    local topic_arn
    topic_arn=$(get_sns_topic_arn "$topic_name")
    if [[ -n "$topic_arn" && "$topic_arn" != "None" ]]; then
        log_info "SNS topic $topic_name: EXISTS"

        # Check subscriptions
        local sub_count
        sub_count=$(aws sns list-subscriptions-by-topic \
            --topic-arn "$topic_arn" \
            --region "$VOICE_REGION" \
            --query 'length(Subscriptions)' \
            --output text 2>/dev/null)
        log_info "  Subscriptions: $sub_count"
    else
        log_error "SNS topic $topic_name: NOT FOUND"
        ((failed++))
    fi

    # Validate Pinpoint two-way SMS configuration
    validate_pinpoint_two_way_sms || log_warn "Pinpoint two-way SMS validation had issues"

    # Validate DynamoDB tables
    for base in "${SMS_DYNAMODB_TABLE_BASES[@]}"; do
        local full_table_name=$(table_name "$base")
        if aws dynamodb describe-table --table-name "$full_table_name" --region "$VOICE_REGION" &>/dev/null; then
            log_info "Table $full_table_name: EXISTS"
        else
            log_error "Table $full_table_name: NOT FOUND"
            ((failed++))
        fi
    done

    if [[ $failed -gt 0 ]]; then
        log_error "Validation failed: $failed resource(s) missing or unhealthy"
        return 1
    fi

    log_info "All SMS resources validated successfully"
    return 0
}

# List SMS resources
list_sms_resources() {
    log_section "SMS Resources (${RESOURCE_PREFIX}-*-${ENVIRONMENT})"

    echo ""
    echo "SMS Lambda Functions:"
    for entry in "${SMS_LAMBDA_FUNCTION_LIST[@]}"; do
        IFS=':' read -r base_name source_dir role_base timeout memory <<< "$entry"
        echo "  - $(sms_lambda_name "$base_name")"
    done

    echo ""
    echo "SNS Topic: $(sns_topic_name)"
    echo "SMS Phone: $SMS_PHONE_NUMBER"

    echo ""
    echo "DynamoDB Tables:"
    for base in "${SMS_DYNAMODB_TABLE_BASES[@]}"; do
        echo "  - $(table_name "$base")"
    done
}

# =============================================================================
# SMS Sending Utility
# =============================================================================

# Send SMS message (for testing)
send_test_sms() {
    local to_number="$1"
    local message="$2"

    if [[ -z "$to_number" || -z "$message" ]]; then
        log_error "Usage: send_test_sms <phone_number> <message>"
        return 1
    fi

    log_info "Sending test SMS to $to_number..."

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Send SMS to $to_number"
        echo -e "${YELLOW}  \$ aws pinpoint-sms-voice-v2 send-text-message \\\\${NC}"
        echo -e "${YELLOW}      --destination-phone-number \"$to_number\" \\\\${NC}"
        echo -e "${YELLOW}      --message-body \"$message\" \\\\${NC}"
        echo -e "${YELLOW}      --region \"$VOICE_REGION\"${NC}"
        echo ""
        return 0
    fi

    aws pinpoint-sms-voice-v2 send-text-message \
        --destination-phone-number "$to_number" \
        --message-body "$message" \
        --region "$VOICE_REGION" \
        --output text

    if [[ $? -eq 0 ]]; then
        log_info "SMS sent successfully"
    else
        log_error "Failed to send SMS"
        return 1
    fi
}
