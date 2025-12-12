#!/bin/bash
# =============================================================================
# iam.sh - IAM role and policy management for Lambda functions
# =============================================================================
# Compatible with bash 3.2+ (macOS default)

# =============================================================================
# IAM Role Creation
# =============================================================================

# Create Lambda execution role with trust policy
# Usage: create_lambda_role "role-name"
create_lambda_role() {
    local role_name="$1"

    log_info "Creating IAM role: $role_name"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Create IAM role: $role_name"
        return 0
    fi

    # Check if role exists
    if aws iam get-role --role-name "$role_name" &>/dev/null; then
        log_info "Role $role_name already exists"
        return 0
    fi

    # Create the trust policy
    local trust_policy='{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }'

    # Create the role
    local create_output
    create_output=$(aws iam create-role \
        --role-name "$role_name" \
        --assume-role-policy-document "$trust_policy" \
        --description "Lambda execution role for ${role_name}" \
        2>&1)

    if [[ $? -ne 0 ]]; then
        log_error "Failed to create role $role_name: $create_output"
        return 1
    fi

    # Attach basic Lambda execution policy
    aws iam attach-role-policy \
        --role-name "$role_name" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" \
        2>/dev/null

    # Wait for role propagation
    log_info "Waiting for role propagation..."
    sleep 10

    log_info "Role $role_name created successfully"
    return 0
}

# =============================================================================
# Role-Specific Policy Configuration
# =============================================================================

# Route to appropriate policy configuration based on role base name
# Usage: ensure_role_policies "orchestrator" "pf-syn-orchestrator-role-dev"
ensure_role_policies() {
    local role_base="$1"
    local full_role_name="$2"

    log_info "Configuring policies for role: $full_role_name (base: $role_base)"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Configure policies for: $full_role_name"
        return 0
    fi

    case "$role_base" in
        "orchestrator")
            configure_orchestrator_role "$full_role_name"
            ;;
        "lex-fulfillment")
            configure_lex_fulfillment_role "$full_role_name"
            ;;
        "voice-bedrock-bridge")
            configure_voice_bedrock_bridge_role "$full_role_name"
            ;;
        "scheduling-actions"|"information-actions"|"chitchat-actions"|"notes-actions")
            configure_actions_role "$full_role_name"
            ;;
        "customer-lookup")
            configure_customer_lookup_role "$full_role_name"
            ;;
        "sms-inbound")
            configure_sms_inbound_role "$full_role_name"
            ;;
        *)
            log_warn "No specific policy configuration for role base: $role_base"
            ;;
    esac
}

# Configure orchestrator role policies
configure_orchestrator_role() {
    local role_name="$1"

    log_info "Configuring orchestrator role: $role_name"

    # Orchestrator permissions (Bedrock, Lambda invoke, Secrets)
    local orchestrator_policy
    orchestrator_policy=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockAccess",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": "*"
        },
        {
            "Sid": "LambdaInvoke",
            "Effect": "Allow",
            "Action": "lambda:InvokeFunction",
            "Resource": "arn:aws:lambda:${AWS_REGION}:${EXPECTED_ACCOUNT}:function:${RESOURCE_PREFIX}-*-${ENVIRONMENT}"
        },
        {
            "Sid": "SecretsAccess",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:${AWS_REGION}:${EXPECTED_ACCOUNT}:secret:projectforce/*"
        }
    ]
}
EOF
)

    put_role_policy "$role_name" "OrchestratorPermissions" "$orchestrator_policy"

    # Attach DynamoDB full access
    aws iam attach-role-policy \
        --role-name "$role_name" \
        --policy-arn "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess" \
        2>/dev/null

    log_info "Orchestrator role configured"
}

# Configure lex-fulfillment role policies
configure_lex_fulfillment_role() {
    local role_name="$1"

    log_info "Configuring lex-fulfillment role: $role_name"

    # Lex fulfillment permissions
    local lex_policy
    lex_policy=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DynamoDBAccess",
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:Query"
            ],
            "Resource": "arn:aws:dynamodb:${AWS_REGION}:${EXPECTED_ACCOUNT}:table/${RESOURCE_PREFIX}-*-${ENVIRONMENT}"
        },
        {
            "Sid": "LambdaInvoke",
            "Effect": "Allow",
            "Action": "lambda:InvokeFunction",
            "Resource": "arn:aws:lambda:${AWS_REGION}:${EXPECTED_ACCOUNT}:function:${RESOURCE_PREFIX}-*-${ENVIRONMENT}"
        },
        {
            "Sid": "SecretsAccess",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:${AWS_REGION}:${EXPECTED_ACCOUNT}:secret:projectforce/*"
        }
    ]
}
EOF
)

    put_role_policy "$role_name" "LexFulfillmentPolicy" "$lex_policy"

    # KMS decrypt policy for Lex
    local kms_policy
    kms_policy=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "KMSDecrypt",
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt",
                "kms:GenerateDataKey"
            ],
            "Resource": "arn:aws:kms:${AWS_REGION}:${EXPECTED_ACCOUNT}:key/*"
        }
    ]
}
EOF
)

    put_role_policy "$role_name" "KMSDecryptPolicy" "$kms_policy"

    log_info "Lex fulfillment role configured"
}

# Configure voice-bedrock-bridge role policies
configure_voice_bedrock_bridge_role() {
    local role_name="$1"

    log_info "Configuring voice-bedrock-bridge role: $role_name"

    # Bedrock access policy
    local bedrock_policy
    bedrock_policy=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockAccess",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": "*"
        },
        {
            "Sid": "DynamoDBAccess",
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:Query"
            ],
            "Resource": "arn:aws:dynamodb:${AWS_REGION}:${EXPECTED_ACCOUNT}:table/${RESOURCE_PREFIX}-*-${ENVIRONMENT}"
        },
        {
            "Sid": "SecretsAccess",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:${AWS_REGION}:${EXPECTED_ACCOUNT}:secret:projectforce/*"
        }
    ]
}
EOF
)

    put_role_policy "$role_name" "BedrockBridgePolicy" "$bedrock_policy"

    log_info "Voice bedrock bridge role configured"
}

# Configure actions roles (scheduling, information, chitchat)
configure_actions_role() {
    local role_name="$1"

    log_info "Configuring actions role: $role_name"

    # Actions permissions
    local actions_policy
    actions_policy=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DynamoDBAccess",
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": "arn:aws:dynamodb:${AWS_REGION}:${EXPECTED_ACCOUNT}:table/${RESOURCE_PREFIX}-*-${ENVIRONMENT}"
        },
        {
            "Sid": "SecretsAccess",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:${AWS_REGION}:${EXPECTED_ACCOUNT}:secret:projectforce/*"
        }
    ]
}
EOF
)

    put_role_policy "$role_name" "ActionsPolicy" "$actions_policy"

    # Attach DynamoDB full access as backup
    aws iam attach-role-policy \
        --role-name "$role_name" \
        --policy-arn "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess" \
        2>/dev/null

    log_info "Actions role configured"
}

# Configure customer-lookup role policies
configure_customer_lookup_role() {
    local role_name="$1"

    log_info "Configuring customer-lookup role: $role_name"

    # Customer lookup permissions
    local lookup_policy
    lookup_policy=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DynamoDBCustomers",
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": "arn:aws:dynamodb:${AWS_REGION}:${EXPECTED_ACCOUNT}:table/${RESOURCE_PREFIX}-customers-${ENVIRONMENT}"
        },
        {
            "Sid": "SecretsAccess",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:${AWS_REGION}:${EXPECTED_ACCOUNT}:secret:projectforce/*"
        }
    ]
}
EOF
)

    put_role_policy "$role_name" "CustomerLookupPolicy" "$lookup_policy"

    log_info "Customer lookup role configured"
}

# Configure sms-inbound role policies
configure_sms_inbound_role() {
    local role_name="$1"

    log_info "Configuring sms-inbound role: $role_name"

    # SMS inbound permissions - DynamoDB access for all SMS tables
    # Tables: sms-sessions, sms-consent, sms-messages, opt-out-tracking
    # Using explicit table names since wildcards don't match environment suffix properly
    local sms_dynamodb_policy
    sms_dynamodb_policy=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DynamoDBSMSTables",
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": [
                "arn:aws:dynamodb:${AWS_REGION}:${EXPECTED_ACCOUNT}:table/${RESOURCE_PREFIX}-sms-sessions-${ENVIRONMENT}",
                "arn:aws:dynamodb:${AWS_REGION}:${EXPECTED_ACCOUNT}:table/${RESOURCE_PREFIX}-sms-consent-${ENVIRONMENT}",
                "arn:aws:dynamodb:${AWS_REGION}:${EXPECTED_ACCOUNT}:table/${RESOURCE_PREFIX}-sms-messages-${ENVIRONMENT}",
                "arn:aws:dynamodb:${AWS_REGION}:${EXPECTED_ACCOUNT}:table/${RESOURCE_PREFIX}-opt-out-tracking-${ENVIRONMENT}"
            ]
        },
        {
            "Sid": "DynamoDBIndexes",
            "Effect": "Allow",
            "Action": [
                "dynamodb:Query"
            ],
            "Resource": [
                "arn:aws:dynamodb:${AWS_REGION}:${EXPECTED_ACCOUNT}:table/${RESOURCE_PREFIX}-sms-sessions-${ENVIRONMENT}/index/*"
            ]
        }
    ]
}
EOF
)

    put_role_policy "$role_name" "SMSDynamoDBPolicy" "$sms_dynamodb_policy"

    # SMS Lambda invocation and orchestrator access
    local sms_lambda_policy
    sms_lambda_policy=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "LambdaInvoke",
            "Effect": "Allow",
            "Action": "lambda:InvokeFunction",
            "Resource": "arn:aws:lambda:${AWS_REGION}:${EXPECTED_ACCOUNT}:function:${RESOURCE_PREFIX}-*-${ENVIRONMENT}"
        },
        {
            "Sid": "SecretsAccess",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:${AWS_REGION}:${EXPECTED_ACCOUNT}:secret:projectforce/*"
        }
    ]
}
EOF
)

    put_role_policy "$role_name" "SMSLambdaPolicy" "$sms_lambda_policy"

    # SMS sending via Pinpoint SMS Voice v2
    local sms_send_policy
    sms_send_policy=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PinpointSMSSend",
            "Effect": "Allow",
            "Action": [
                "sms-voice:SendTextMessage",
                "sms-voice:DescribePhoneNumbers"
            ],
            "Resource": "*"
        },
        {
            "Sid": "SNSPublish",
            "Effect": "Allow",
            "Action": [
                "sns:Publish"
            ],
            "Resource": "arn:aws:sns:${AWS_REGION}:${EXPECTED_ACCOUNT}:${RESOURCE_PREFIX}-*"
        }
    ]
}
EOF
)

    put_role_policy "$role_name" "SMSSendPolicy" "$sms_send_policy"

    log_info "SMS inbound role configured"
}

# =============================================================================
# Helper Functions
# =============================================================================

# Put inline policy on role
# Usage: put_role_policy "role-name" "policy-name" "policy-json"
put_role_policy() {
    local role_name="$1"
    local policy_name="$2"
    local policy_document="$3"

    log_debug "Attaching policy $policy_name to role $role_name"

    local put_output
    put_output=$(aws iam put-role-policy \
        --role-name "$role_name" \
        --policy-name "$policy_name" \
        --policy-document "$policy_document" \
        2>&1)

    if [[ $? -ne 0 ]]; then
        log_error "Failed to attach policy $policy_name to $role_name: $put_output"
        return 1
    fi

    log_debug "Policy $policy_name attached to $role_name"
    return 0
}

# Delete Lambda role and its policies
# Usage: delete_lambda_role "role-name"
delete_lambda_role() {
    local role_name="$1"

    log_info "Deleting IAM role: $role_name"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Delete IAM role: $role_name"
        return 0
    fi

    # Check if role exists
    if ! aws iam get-role --role-name "$role_name" &>/dev/null; then
        log_debug "Role $role_name does not exist"
        return 0
    fi

    # Delete inline policies
    local policies
    policies=$(aws iam list-role-policies --role-name "$role_name" --query 'PolicyNames[]' --output text 2>/dev/null)
    for policy in $policies; do
        log_debug "Deleting inline policy: $policy"
        aws iam delete-role-policy --role-name "$role_name" --policy-name "$policy" 2>/dev/null
    done

    # Detach managed policies
    local attached
    attached=$(aws iam list-attached-role-policies --role-name "$role_name" --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null)
    for policy_arn in $attached; do
        log_debug "Detaching managed policy: $policy_arn"
        aws iam detach-role-policy --role-name "$role_name" --policy-arn "$policy_arn" 2>/dev/null
    done

    # Delete the role
    aws iam delete-role --role-name "$role_name" 2>/dev/null

    log_info "Role $role_name deleted"
    return 0
}

# =============================================================================
# Validation Functions
# =============================================================================

# Validate role has required policies
# Usage: validate_role_policies "role-name" "role-base"
validate_role_policies() {
    local role_name="$1"
    local role_base="$2"
    local failed=0

    log_info "Validating policies for: $role_name"

    # Check role exists
    if ! aws iam get-role --role-name "$role_name" &>/dev/null; then
        log_error "Role $role_name does not exist"
        return 1
    fi

    # List inline policies
    local inline_policies
    inline_policies=$(aws iam list-role-policies --role-name "$role_name" --query 'PolicyNames[]' --output text 2>/dev/null)

    # List attached policies
    local attached_policies
    attached_policies=$(aws iam list-attached-role-policies --role-name "$role_name" --query 'AttachedPolicies[].PolicyName' --output text 2>/dev/null)

    log_info "  Inline policies: ${inline_policies:-none}"
    log_info "  Attached policies: ${attached_policies:-none}"

    # Check for basic execution role
    if ! echo "$attached_policies" | grep -q "AWSLambdaBasicExecutionRole"; then
        log_warn "  Missing AWSLambdaBasicExecutionRole"
        ((failed++))
    fi

    # Role-specific checks
    case "$role_base" in
        "orchestrator")
            if ! echo "$inline_policies" | grep -q "OrchestratorPermissions"; then
                log_warn "  Missing OrchestratorPermissions policy"
                ((failed++))
            fi
            ;;
        "lex-fulfillment")
            if ! echo "$inline_policies" | grep -q "LexFulfillmentPolicy"; then
                log_warn "  Missing LexFulfillmentPolicy"
                ((failed++))
            fi
            ;;
        "voice-bedrock-bridge")
            if ! echo "$inline_policies" | grep -q "BedrockBridgePolicy"; then
                log_warn "  Missing BedrockBridgePolicy"
                ((failed++))
            fi
            ;;
    esac

    if [[ $failed -gt 0 ]]; then
        return 1
    fi

    log_info "  Role policies validated"
    return 0
}
