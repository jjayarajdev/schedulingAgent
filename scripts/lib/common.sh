#!/bin/bash
# =============================================================================
# common.sh - Shared utility functions for pf-manage.sh
# =============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_debug() { [[ "$DEBUG" == "true" ]] && echo -e "${CYAN}[DEBUG]${NC} $1"; }
log_section() { echo -e "\n${BLUE}=== $1 ===${NC}"; }

# AWS Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
EXPECTED_ACCOUNT="772634497954"

# =============================================================================
# Resource Naming Functions
# =============================================================================
# All resources follow the pattern: ${RESOURCE_PREFIX}-${base_name}-${ENVIRONMENT}
# Example: pf-syn-orchestrator-dev, pf-syn-scheduling-actions-qa

# Build resource name from base name
# Usage: name=$(resource_name "orchestrator")
# Result: pf-syn-orchestrator-dev (based on RESOURCE_PREFIX and ENVIRONMENT)
resource_name() {
    local base_name="$1"
    echo "${RESOURCE_PREFIX}-${base_name}-${ENVIRONMENT}"
}

# Build IAM role name from base name
# Usage: role=$(role_name "orchestrator")
# Result: pf-syn-orchestrator-role-dev
role_name() {
    local base_name="$1"
    echo "${RESOURCE_PREFIX}-${base_name}-role-${ENVIRONMENT}"
}

# Build DynamoDB table name from base name
# Usage: table=$(table_name "sessions")
# Result: pf-syn-sessions-dev
table_name() {
    local base_name="$1"
    echo "${RESOURCE_PREFIX}-${base_name}-${ENVIRONMENT}"
}

# Validate environment value
validate_environment() {
    local env="$1"
    if [[ ! " $VALID_ENVIRONMENTS " =~ " $env " ]]; then
        log_error "Invalid environment: $env"
        log_error "Valid environments: $VALID_ENVIRONMENTS"
        return 1
    fi
    return 0
}

# Print current naming configuration
print_naming_config() {
    log_info "Resource Naming Configuration:"
    log_info "  Prefix:      $RESOURCE_PREFIX"
    log_info "  Environment: $ENVIRONMENT"
    log_info "  Example:     $(resource_name 'orchestrator')"
}

# Detect AWS profile
detect_aws_profile() {
    # If already set, use it
    if [[ -n "$AWS_PROFILE" ]]; then
        echo "$AWS_PROFILE"
        return
    fi

    # Check for pf-aws profile
    if aws configure list-profiles 2>/dev/null | grep -q "^pf-aws$"; then
        echo "pf-aws"
        return
    fi

    # Fall back to default
    echo "default"
}

# Verify AWS account
verify_account() {
    local actual_account
    actual_account=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)

    if [[ "$actual_account" != "$EXPECTED_ACCOUNT" ]]; then
        log_error "Wrong AWS account: $actual_account (expected $EXPECTED_ACCOUNT)"
        log_error "Please configure AWS_PROFILE=pf-aws or check your credentials"
        return 1
    fi
    log_info "AWS Account verified: $actual_account"
    return 0
}

# Check if a command exists
command_exists() {
    command -v "$1" &>/dev/null
}

# Check required dependencies
check_dependencies() {
    local deps=("aws" "zip" "jq")
    local missing=()

    for dep in "${deps[@]}"; do
        if ! command_exists "$dep"; then
            missing+=("$dep")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing[*]}"
        return 1
    fi
    return 0
}

# Confirm action with user
confirm_action() {
    local message="$1"
    local default="${2:-n}"

    if [[ "$FORCE" == "true" ]]; then
        return 0
    fi

    local prompt
    if [[ "$default" == "y" ]]; then
        prompt="[Y/n]"
    else
        prompt="[y/N]"
    fi

    read -r -p "$message $prompt " response
    response="${response:-$default}"

    [[ "$response" =~ ^[Yy]$ ]]
}

# Wait for resource with timeout
wait_for_resource() {
    local check_cmd="$1"
    local resource_name="$2"
    local max_attempts="${3:-30}"
    local sleep_time="${4:-5}"

    log_info "Waiting for $resource_name to be ready..."

    local attempt=1
    while [[ $attempt -le $max_attempts ]]; do
        if eval "$check_cmd" &>/dev/null; then
            log_info "$resource_name is ready"
            return 0
        fi
        log_debug "Attempt $attempt/$max_attempts - $resource_name not ready yet"
        sleep "$sleep_time"
        ((attempt++))
    done

    log_error "Timeout waiting for $resource_name"
    return 1
}

# Get project root directory
get_project_root() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    # Go up from scripts/lib to project root (schedulingAgent)
    echo "$(cd "$script_dir/../.." && pwd)"
}

# Print usage help
print_help() {
    cat << 'EOF'
pf-manage.sh - Consolidated deployment script for ProjectForce Scheduling Agent

USAGE:
    ./pf-manage.sh <command> [options]

COMMANDS:
    deploy      Deploy AWS resources
    cleanup     Remove AWS resources
    validate    Validate deployed resources
    status      Show current resource status

RESOURCE OPTIONS:
    --all       Apply to all components (lambda, voice, sms)
    --lambda    Core Lambda functions only
    --voice     Voice integration (Connect, Lex, voice Lambdas)
    --sms       SMS integration (SMS Lambda, SNS, DynamoDB)

NAMING OPTIONS:
    --prefix <name>   Resource prefix (default: pf-syn)
    --env <env>       Environment: dev, qa, prod (default: dev)

BEHAVIOR OPTIONS:
    --dry-run   Show what would be done without executing
    --force     Skip confirmation prompts
    --debug     Enable debug output
    --help      Show this help message

EXAMPLES:
    ./pf-manage.sh deploy --all                          Deploy everything (dev)
    ./pf-manage.sh deploy --all --env prod               Deploy to production
    ./pf-manage.sh deploy --lambda --prefix pf-syn       Deploy with custom prefix
    ./pf-manage.sh deploy --all --prefix pf-syn --env qa Deploy to QA environment
    ./pf-manage.sh cleanup --voice --env dev             Clean up dev voice resources
    ./pf-manage.sh validate --all --env prod             Validate prod resources
    ./pf-manage.sh status --env dev                      Show dev resource status

RESOURCE NAMING:
    Resources are named as: ${PREFIX}-${resource}-${ENVIRONMENT}
    Example: pf-syn-orchestrator-dev, pf-syn-scheduling-actions-qa

ENVIRONMENT VARIABLES:
    AWS_PROFILE       AWS profile to use (default: pf-aws)
    AWS_REGION        AWS region (default: us-east-1)
    RESOURCE_PREFIX   Resource prefix (default: pf-syn)
    ENVIRONMENT       Target environment (default: dev)
    DEBUG             Enable debug output (set to 'true')

EOF
}

# =============================================================================
# Dry-Run Command Helper
# =============================================================================
# Helper to show AWS CLI commands in dry-run mode
# Usage: dry_run_cmd "description" "aws cli command..."
# In normal mode: executes the command
# In dry-run mode: prints the command that would be executed
dry_run_cmd() {
    local description="$1"
    shift
    local cmd="$*"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${CYAN}[DRY-RUN]${NC} $description"
        echo -e "${YELLOW}  \$ $cmd${NC}"
        return 0
    else
        eval "$cmd"
        return $?
    fi
}

# Print banner
print_banner() {
    echo -e "${BLUE}"
    cat << 'EOF'
     █████╗  ██████╗ ███████╗███╗   ██╗████████╗     █████╗ ██╗
    ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝    ██╔══██╗██║
    ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║       ███████║██║
    ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║       ██╔══██║██║
    ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║       ██║  ██║██║
    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝       ╚═╝  ╚═╝╚═╝

    ███████╗ ██████╗██╗  ██╗███████╗██████╗ ██╗   ██╗██╗     ███████╗██████╗
    ██╔════╝██╔════╝██║  ██║██╔════╝██╔══██╗██║   ██║██║     ██╔════╝██╔══██╗
    ███████╗██║     ███████║█████╗  ██║  ██║██║   ██║██║     █████╗  ██████╔╝
    ╚════██║██║     ██╔══██║██╔══╝  ██║  ██║██║   ██║██║     ██╔══╝  ██╔══██╗
    ███████║╚██████╗██║  ██║███████╗██████╔╝╚██████╔╝███████╗███████╗██║  ██║
    ╚══════╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═════╝  ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝
EOF
    echo -e "${NC}"
    echo "Agent AI Scheduler Setup - AWS Resource Manager"
    echo "Account: $EXPECTED_ACCOUNT | Region: $AWS_REGION"
    echo "Prefix: $RESOURCE_PREFIX | Environment: $ENVIRONMENT"
    echo ""
}
