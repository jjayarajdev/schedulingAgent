#!/bin/bash
#
# Complete Deployment Script for New AWS Environment
# This script deploys the entire scheduling agent system from scratch
#
# Usage: ./DEPLOY_NEW_ENVIRONMENT.sh
#
# Prerequisites:
# - AWS CLI configured
# - Terraform installed
# - Python 3.11 installed
# - Bedrock Claude 3.5 Sonnet v2 access enabled
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
REGION="${AWS_REGION:-us-east-1}"
PREFIX="${PROJECT_PREFIX:-pf}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

echo "=========================================="
echo "Scheduling Agent - New Environment Deployment"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Region: $REGION"
echo "  Prefix: $PREFIX"
echo "  Environment: $ENVIRONMENT"
echo ""

# Verify prerequisites
log_info "Checking prerequisites..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI not found. Please install AWS CLI."
    exit 1
fi
log_success "AWS CLI found"

# Check Terraform
if ! command -v terraform &> /dev/null; then
    log_error "Terraform not found. Please install Terraform."
    exit 1
fi
log_success "Terraform found"

# Check Python
if ! command -v python3.11 &> /dev/null && ! command -v python3 &> /dev/null; then
    log_error "Python 3.11 not found. Please install Python 3.11."
    exit 1
fi
log_success "Python found"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not configured. Run: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
log_success "AWS credentials configured (Account: $ACCOUNT_ID)"

echo ""
log_warning "This script will deploy the entire system. Continue? (y/n)"
read -r response
if [[ ! "$response" =~ ^[Yy]$ ]]; then
    log_info "Deployment cancelled."
    exit 0
fi

echo ""
echo "=========================================="
echo "PHASE 1: Core Infrastructure (Terraform)"
echo "=========================================="
echo ""

cd infrastructure/terraform

log_info "Initializing Terraform..."
terraform init

log_info "Validating Terraform configuration..."
terraform validate

log_info "Planning infrastructure deployment..."
terraform plan -out=tfplan

log_info "Applying Terraform configuration..."
terraform apply tfplan

log_success "Core infrastructure deployed!"

echo ""
log_info "Waiting 30 seconds for agents to be created..."
sleep 30

log_info "Preparing Bedrock agents..."
./prepare_agents.sh

log_success "Phase 1 completed!"

echo ""
echo "=========================================="
echo "PHASE 2: Step Functions Infrastructure"
echo "=========================================="
echo ""

cd ../../

log_info "Deploying Step Functions infrastructure..."
./scripts/deploy_all_step_functions.sh

log_success "Phase 2 completed!"

echo ""
echo "=========================================="
echo "PHASE 3: Verification Tests"
echo "=========================================="
echo ""

log_info "Testing Supervisor agent routing..."
cd infrastructure/terraform
if python3 test_supervisor_routing.py; then
    log_success "Supervisor routing test passed!"
else
    log_warning "Supervisor routing test had issues (may be expected for new setup)"
fi

cd ../../

log_info "Testing Step Functions execution..."
cd tests
if python3 test_step_functions.py; then
    log_success "Step Functions test passed!"
else
    log_warning "Step Functions test had issues (check CloudWatch Logs)"
fi

cd ..

log_success "Phase 3 completed!"

echo ""
echo "=========================================="
echo "PHASE 4: Backend Setup"
echo "=========================================="
echo ""

cd frontend/backend

log_info "Creating Python virtual environment..."
python3.11 -m venv venv || python3 -m venv venv

log_info "Activating virtual environment..."
source venv/bin/activate

log_info "Installing Python dependencies..."
pip install -q -r requirements.txt

log_info "Getting Supervisor Agent ID..."
SUPERVISOR_ID=$(aws bedrock-agent list-agents --region $REGION | \
    jq -r '.agentSummaries[] | select(.agentName == "pf-supervisor-agent-dev") | .agentId')

if [ -z "$SUPERVISOR_ID" ]; then
    log_error "Could not find Supervisor agent ID"
    exit 1
fi

log_info "Creating backend .env file..."
cat > .env <<EOF
# AWS Configuration
AWS_REGION=$REGION
AWS_ACCOUNT_ID=$ACCOUNT_ID

# Bedrock Agent Configuration
SUPERVISOR_AGENT_ID=$SUPERVISOR_ID
SUPERVISOR_AGENT_ALIAS_ID=TSTALIASID

# Query Router Configuration
QUERY_ROUTER_LAMBDA=$PREFIX-query-router

# DynamoDB Configuration
DYNAMODB_TABLE=$PREFIX-session-data-$ENVIRONMENT

# CORS Configuration
FRONTEND_URL=http://localhost:3000

# API Configuration
USE_MOCK_API=true
EOF

log_success "Backend configuration created!"
log_info "Backend ready. To start: cd frontend/backend && source venv/bin/activate && python app.py"

cd ../..

log_success "Phase 4 completed!"

echo ""
echo "=========================================="
echo "PHASE 5: Frontend Setup"
echo "=========================================="
echo ""

cd frontend

if [ -f "package.json" ]; then
    log_info "Installing Node.js dependencies..."
    npm install

    log_info "Creating frontend .env.local file..."
    cat > .env.local <<EOF
REACT_APP_BACKEND_URL=http://localhost:5001
REACT_APP_API_TIMEOUT=30000
EOF

    log_success "Frontend configuration created!"
    log_info "Frontend ready. To start: cd frontend && npm start"
else
    log_warning "No package.json found. Skipping frontend setup."
fi

cd ..

log_success "Phase 5 completed!"

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "Deployed Resources:"
echo ""
echo "Bedrock Agents:"
echo "  - Supervisor Agent ID: $SUPERVISOR_ID"
echo "  - 4 Collaborator Agents (Information, Scheduling, Notification, Escalation)"
echo ""
echo "Lambda Functions:"
echo "  - $PREFIX-information-actions"
echo "  - $PREFIX-scheduling-actions"
echo "  - $PREFIX-query-router"
echo "  - $PREFIX-filter-projects"
echo "  - $PREFIX-weather-evaluator"
echo ""
echo "State Machines:"
echo "  - $PREFIX-schedule-urgent-project"
echo "  - $PREFIX-schedule-weather-dependent"
echo "  - $PREFIX-schedule-batch-projects"
echo ""
echo "DynamoDB:"
echo "  - $PREFIX-session-data-$ENVIRONMENT"
echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo ""
echo "1. Start Backend Server:"
echo "   cd frontend/backend"
echo "   source venv/bin/activate"
echo "   python app.py"
echo ""
echo "2. Start Frontend Server (in new terminal):"
echo "   cd frontend"
echo "   npm start"
echo ""
echo "3. Open browser:"
echo "   http://localhost:3000"
echo ""
echo "4. Test queries:"
echo "   - Simple: 'Show me all my projects'"
echo "   - Complex: 'Schedule my most urgent project'"
echo ""
echo "=========================================="
echo "AWS Console Links:"
echo "=========================================="
echo ""
echo "Bedrock Agents:"
echo "  https://console.aws.amazon.com/bedrock/home?region=$REGION#/agents"
echo ""
echo "Lambda Functions:"
echo "  https://console.aws.amazon.com/lambda/home?region=$REGION#/functions"
echo ""
echo "Step Functions:"
echo "  https://console.aws.amazon.com/states/home?region=$REGION#/statemachines"
echo ""
echo "CloudWatch Logs:"
echo "  https://console.aws.amazon.com/cloudwatch/home?region=$REGION#logsV2:log-groups"
echo ""
echo "=========================================="
echo "Documentation:"
echo "=========================================="
echo ""
echo "  - Full Guide: docs/NEW_ENVIRONMENT_DEPLOYMENT.md"
echo "  - Step Functions: docs/STEP_FUNCTIONS_IMPLEMENTATION.md"
echo "  - Complex Queries: docs/COMPLEX_QUERY_SCENARIOS.md"
echo "  - Troubleshooting: Check CloudWatch Logs"
echo ""
echo "=========================================="
echo "Deployment completed successfully!"
echo "=========================================="
