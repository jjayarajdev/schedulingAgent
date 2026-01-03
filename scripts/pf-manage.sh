#!/bin/bash
# =============================================================================
# pf-manage.sh - Consolidated Deployment Script for ProjectForce Scheduling Agent
# =============================================================================
# This script provides unified deploy, cleanup, and validate commands for all
# AWS resources related to the ProjectForce Scheduling Agent.
#
# Usage:
#     ./pf-manage.sh <command> [options]
#
# Commands:
#     deploy      Deploy AWS resources
#     cleanup     Remove AWS resources
#     validate    Validate deployed resources
#     status      Show current resource status
#     phone       Manage voice phone numbers (claim, release, reclaim)
#
# Resource Options:
#     --all       Apply to all components (lambda, voice, sms)
#     --lambda    Core Lambda functions only
#     --voice     Voice integration (Connect, Lex, voice Lambdas)
#     --sms       SMS integration (SMS Lambda, SNS, DynamoDB)
#
# Naming Options:
#     --prefix <name>   Resource prefix (default: pf-syn)
#     --env <env>       Environment: dev, qa, prod (default: dev)
#
# Behavior Options:
#     --dry-run   Show what would be done without executing
#     --force     Skip confirmation prompts
#     --debug     Enable debug output
#     --help      Show this help message
#
# Examples:
#     ./pf-manage.sh deploy --all                          Deploy everything (dev)
#     ./pf-manage.sh deploy --all --env prod               Deploy to production
#     ./pf-manage.sh deploy --lambda --prefix pf-syn       Deploy with custom prefix
#     ./pf-manage.sh deploy --all --prefix pf-syn --env qa Deploy to QA environment
#     ./pf-manage.sh cleanup --voice --env dev             Clean up dev voice resources
#     ./pf-manage.sh validate --all --env prod             Validate prod resources
#     ./pf-manage.sh status --env dev                      Show dev resource status
#
# Resource Naming:
#     Resources are named as: ${PREFIX}-${resource}-${ENVIRONMENT}
#     Example: pf-syn-orchestrator-dev, pf-syn-scheduling-actions-qa
#
# Environment Variables:
#     AWS_PROFILE       AWS profile to use (default: pf-aws)
#     AWS_REGION        AWS region (default: us-east-1)
#     RESOURCE_PREFIX   Resource prefix (default: pf-syn)
#     ENVIRONMENT       Target environment (default: dev)
#     DEBUG             Enable debug output (set to 'true')
#
# =============================================================================

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source library files
source "$SCRIPT_DIR/lib/common.sh"
source "$SCRIPT_DIR/lib/iam.sh"
source "$SCRIPT_DIR/lib/lambda.sh"
source "$SCRIPT_DIR/lib/dynamodb.sh"
source "$SCRIPT_DIR/lib/s3.sh"
source "$SCRIPT_DIR/lib/voice.sh"
source "$SCRIPT_DIR/lib/sms.sh"
source "$SCRIPT_DIR/lib/api.sh"
source "$SCRIPT_DIR/lib/secrets.sh"
source "$SCRIPT_DIR/lib/cloudwatch.sh"
source "$SCRIPT_DIR/lib/validate.sh"

# Source configuration (optional)
if [[ -f "$SCRIPT_DIR/config/resources.env" ]]; then
    source "$SCRIPT_DIR/config/resources.env"
fi

# =============================================================================
# Global Variables
# =============================================================================

COMMAND=""
PHONE_ACTION=""
COMPONENT_LAMBDA=false
COMPONENT_VOICE=false
COMPONENT_SMS=false
COMPONENT_ALL=false
DRY_RUN=false
FORCE=false
DEBUG="${DEBUG:-false}"

# =============================================================================
# Argument Parsing
# =============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            deploy|cleanup|validate|status)
                COMMAND="$1"
                shift
                ;;
            phone)
                COMMAND="$1"
                shift
                # Phone subcommand: claim, release, reclaim, status
                if [[ -n "$1" && "$1" != --* ]]; then
                    PHONE_ACTION="$1"
                    shift
                else
                    PHONE_ACTION="status"
                fi
                ;;
            --all)
                COMPONENT_ALL=true
                shift
                ;;
            --lambda)
                COMPONENT_LAMBDA=true
                shift
                ;;
            --voice)
                COMPONENT_VOICE=true
                shift
                ;;
            --sms)
                COMPONENT_SMS=true
                shift
                ;;
            --prefix)
                if [[ -z "$2" || "$2" == --* ]]; then
                    log_error "--prefix requires a value"
                    exit 1
                fi
                RESOURCE_PREFIX="$2"
                shift 2
                ;;
            --env)
                if [[ -z "$2" || "$2" == --* ]]; then
                    log_error "--env requires a value (dev, qa, prod)"
                    exit 1
                fi
                ENVIRONMENT="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --force|-f)
                FORCE=true
                shift
                ;;
            --debug|-d)
                DEBUG=true
                shift
                ;;
            --help|-h)
                print_help
                exit 0
                ;;
            *)
                log_error "Unknown argument: $1"
                print_help
                exit 1
                ;;
        esac
    done

    # Validate environment if provided
    if ! validate_environment "$ENVIRONMENT"; then
        exit 1
    fi

    # Default to --all if no component specified
    if [[ "$COMPONENT_LAMBDA" == "false" && "$COMPONENT_VOICE" == "false" && "$COMPONENT_SMS" == "false" && "$COMPONENT_ALL" == "false" ]]; then
        COMPONENT_ALL=true
    fi

    # --all sets all components
    if [[ "$COMPONENT_ALL" == "true" ]]; then
        COMPONENT_LAMBDA=true
        COMPONENT_VOICE=true
        COMPONENT_SMS=true
    fi

    # Export naming variables for all library functions
    export RESOURCE_PREFIX
    export ENVIRONMENT
}

# =============================================================================
# Command Handlers
# =============================================================================

# Deploy command
cmd_deploy() {
    log_section "Deploying Resources"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY-RUN MODE: No changes will be made"
    fi

    local failed=0

    # Always validate secrets first (required by Lambdas)
    deploy_secrets || log_warn "Secrets validation had issues (non-blocking)"

    # Create DynamoDB tables (required by Lambdas)
    if [[ "$COMPONENT_LAMBDA" == "true" ]]; then
        create_core_dynamodb_tables || log_warn "Core DynamoDB tables had issues (non-blocking)"
    fi

    if [[ "$COMPONENT_LAMBDA" == "true" ]]; then
        deploy_all_lambdas || ((failed++))

        # Deploy API Gateway for orchestrator
        deploy_api_gateway || ((failed++))
    fi

    if [[ "$COMPONENT_VOICE" == "true" ]]; then
        deploy_voice || ((failed++))
    fi

    if [[ "$COMPONENT_SMS" == "true" ]]; then
        create_sms_dynamodb_tables || log_warn "SMS DynamoDB tables had issues (non-blocking)"
        deploy_sms || ((failed++))
    fi

    # Deploy CloudWatch log groups with retention policy for all Lambdas
    deploy_cloudwatch_logs || log_warn "CloudWatch log group setup had issues (non-blocking)"

    echo ""
    log_section "Deployment Summary"

    if [[ $failed -gt 0 ]]; then
        log_error "Deployment completed with $failed component(s) having issues"
        return 1
    fi

    log_info "All requested resources deployed successfully!"
    return 0
}

# Cleanup command
cmd_cleanup() {
    log_section "Cleaning Up Resources"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY-RUN MODE: No changes will be made"
    fi

    # Confirm cleanup (unless --force)
    if [[ "$FORCE" != "true" && "$DRY_RUN" != "true" ]]; then
        echo ""
        log_warn "This will DELETE AWS resources!"
        echo ""
        echo "Components to be cleaned:"
        [[ "$COMPONENT_LAMBDA" == "true" ]] && echo "  - Core Lambda functions and IAM roles"
        [[ "$COMPONENT_VOICE" == "true" ]] && echo "  - Voice Lambdas, Lex bot"
        [[ "$COMPONENT_SMS" == "true" ]] && echo "  - SMS Lambda, SNS topic"
        echo ""

        if ! confirm_action "Are you sure you want to proceed?"; then
            log_info "Cleanup cancelled"
            return 0
        fi
    fi

    local failed=0

    # Cleanup in reverse dependency order
    if [[ "$COMPONENT_SMS" == "true" ]]; then
        cleanup_sms || ((failed++))
    fi

    if [[ "$COMPONENT_VOICE" == "true" ]]; then
        cleanup_voice || ((failed++))
    fi

    if [[ "$COMPONENT_LAMBDA" == "true" ]]; then
        # Cleanup API Gateway first (depends on Lambda)
        cleanup_api_gateway || ((failed++))
        cleanup_all_lambdas || ((failed++))
    fi

    echo ""
    log_section "Cleanup Summary"

    if [[ $failed -gt 0 ]]; then
        log_error "Cleanup completed with $failed component(s) having issues"
        return 1
    fi

    log_info "All requested resources cleaned up successfully!"
    return 0
}

# Validate command
cmd_validate() {
    log_section "Validating Resources"

    local failed=0

    # Always validate secrets and API Gateway
    validate_secrets || ((failed++))

    if [[ "$COMPONENT_LAMBDA" == "true" ]]; then
        validate_lambdas || ((failed++))
        validate_api_gateway || ((failed++))
    fi

    if [[ "$COMPONENT_VOICE" == "true" ]]; then
        validate_voice || ((failed++))
    fi

    if [[ "$COMPONENT_SMS" == "true" ]]; then
        validate_sms || ((failed++))
    fi

    # Validate DynamoDB tables
    validate_all_dynamodb_tables || ((failed++))

    # Also validate IAM roles
    validate_iam_roles || ((failed++))

    # Validate CloudWatch log groups
    validate_cloudwatch_logs || ((failed++))

    echo ""
    log_section "Validation Summary"

    if [[ $failed -gt 0 ]]; then
        log_error "Validation completed with $failed component(s) having issues"
        return 1
    fi

    log_info "All resources validated successfully!"
    return 0
}

# Status command
cmd_status() {
    log_section "Current Resource Status"

    # Quick health check
    health_check

    # Generate full report
    echo ""
    generate_resource_report

    # Show DynamoDB table status
    echo ""
    show_dynamodb_status

    # Check for drift
    echo ""
    detect_drift

    return 0
}

# =============================================================================
# Phone Command
# =============================================================================

# Manage voice phone numbers
cmd_phone() {
    log_section "Phone Number Management"

    case "$PHONE_ACTION" in
        status)
            log_info "Checking phone number status..."
            validate_voice_phone_number
            ;;
        claim)
            log_info "Claiming phone number: $VOICE_PHONE_NUMBER"
            ensure_phone_number_claimed
            ;;
        release)
            log_info "Releasing phone number: $VOICE_PHONE_NUMBER"
            local phone_id
            phone_id=$(get_connect_phone_number_id "$VOICE_PHONE_NUMBER")
            if [[ -n "$phone_id" && "$phone_id" != "None" ]]; then
                release_phone_number "$phone_id"
            else
                log_error "Phone number not found: $VOICE_PHONE_NUMBER"
                return 1
            fi
            ;;
        reclaim)
            log_info "Releasing and reclaiming phone number: $VOICE_PHONE_NUMBER"
            release_and_reclaim_phone_number "$VOICE_PHONE_NUMBER"
            ;;
        search)
            log_info "Searching for available phone numbers..."
            search_available_phone_numbers
            ;;
        *)
            log_error "Unknown phone action: $PHONE_ACTION"
            echo "Usage: ./pf-manage.sh phone <action> [options]"
            echo ""
            echo "Actions:"
            echo "  status   Show current phone number status (default)"
            echo "  claim    Claim the configured phone number for Connect instance"
            echo "  release  Release the phone number from Connect"
            echo "  reclaim  Release and reclaim phone number (migrate between instances)"
            echo "  search   Search for available phone numbers to claim"
            echo ""
            echo "Options:"
            echo "  --env <env>   Target environment (dev, qa, prod)"
            echo ""
            echo "Examples:"
            echo "  ./pf-manage.sh phone status --env prod"
            echo "  ./pf-manage.sh phone claim --env prod"
            echo "  ./pf-manage.sh phone reclaim --env prod"
            return 1
            ;;
    esac
}

# =============================================================================
# Main Entry Point
# =============================================================================

main() {
    # Parse command line arguments
    parse_args "$@"

    # Validate command
    if [[ -z "$COMMAND" ]]; then
        log_error "No command specified"
        print_help
        exit 1
    fi

    # Print banner
    print_banner

    # Detect and set AWS profile
    if [[ -z "$AWS_PROFILE" ]]; then
        AWS_PROFILE=$(detect_aws_profile)
        export AWS_PROFILE
    fi
    log_info "Using AWS Profile: $AWS_PROFILE"

    # Check dependencies
    if ! check_dependencies; then
        exit 1
    fi

    # Verify AWS account
    if ! verify_account; then
        exit 1
    fi

    # Execute command
    case "$COMMAND" in
        deploy)
            cmd_deploy
            ;;
        cleanup)
            cmd_cleanup
            ;;
        validate)
            cmd_validate
            ;;
        status)
            cmd_status
            ;;
        phone)
            cmd_phone
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            print_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
