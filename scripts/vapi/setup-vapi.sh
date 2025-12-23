#!/bin/bash
#
# Complete VAPI Setup Script
#
# Usage:
#   ./setup-vapi.sh dev      # Full setup for dev environment
#   ./setup-vapi.sh prod     # Full setup for prod environment
#
# This script performs the complete VAPI integration setup:
# 1. Deploys the vapi-webhook Lambda
# 2. Configures the VAPI assistant
#
# Prerequisites:
# - AWS CLI configured with pf-aws profile
# - VAPI_PRIVATE_KEY environment variable set
#

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default environment
ENVIRONMENT="${1:-dev}"

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prod" ]]; then
    echo "Error: Environment must be 'dev' or 'prod'"
    echo "Usage: $0 [dev|prod]"
    exit 1
fi

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║     VAPI Integration Setup               ║"
echo "║     Environment: ${ENVIRONMENT}                      ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check AWS CLI
if ! command -v aws &>/dev/null; then
    echo "Error: AWS CLI is not installed"
    exit 1
fi

# Check AWS profile
if ! aws --profile pf-aws sts get-caller-identity &>/dev/null; then
    echo "Error: AWS profile 'pf-aws' is not configured or not valid"
    exit 1
fi

# Check VAPI API key
if [[ -z "$VAPI_PRIVATE_KEY" ]]; then
    echo ""
    echo "VAPI_PRIVATE_KEY environment variable not set."
    echo "Please enter your VAPI private API key:"
    read -s VAPI_PRIVATE_KEY
    export VAPI_PRIVATE_KEY
    echo ""
fi

if [[ -z "$VAPI_PRIVATE_KEY" ]]; then
    echo "Error: VAPI API key is required"
    exit 1
fi

echo "Prerequisites OK"
echo ""

# Step 1: Deploy Lambda
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1: Deploy VAPI Webhook Lambda"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

"${SCRIPT_DIR}/deploy-webhook.sh" "$ENVIRONMENT"

echo ""

# Step 2: Configure VAPI Assistant
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2: Configure VAPI Assistant"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

"${SCRIPT_DIR}/configure-assistant.sh" "$ENVIRONMENT"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║     VAPI Setup Complete!                 ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "Voice integration is now active for ${ENVIRONMENT} environment."
echo ""
echo "Test the integration:"
echo "  1. Call your VAPI phone number"
echo "  2. Say: 'What are my projects?'"
echo "  3. The assistant should list your projects"
echo ""
echo "Monitor logs with:"
echo "  aws --profile pf-aws logs tail /aws/lambda/pf-syn-vapi-webhook-${ENVIRONMENT} --follow --region us-east-1"
echo ""
