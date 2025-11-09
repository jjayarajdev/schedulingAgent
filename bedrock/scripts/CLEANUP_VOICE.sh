#!/bin/bash

# ============================================================================
# AWS Connect Voice Integration Cleanup Script
# ============================================================================
# Purpose: Remove all AWS Connect voice integration resources
# Author: ProjectForce Team
# WARNING: This will delete all resources created by DEPLOY_VOICE.sh
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/infrastructure/terraform/voice-minimal"
DEPLOYMENT_INFO="$PROJECT_ROOT/config/voice_deployment.json"
REGION="us-east-1"

echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}  AWS Connect Voice Integration Cleanup${NC}"
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}WARNING: This will delete:${NC}"
echo "  - Lambda functions (lex-fulfillment, voice-bedrock-bridge)"
echo "  - S3 bucket (call recordings)"
echo "  - DynamoDB table (session data)"
echo "  - All IAM roles and policies"
echo ""
echo -e "${BLUE}NOTE: AWS Connect instance and Lex bot must be deleted manually via Console${NC}"
echo "      (They were created manually and are not managed by Terraform)"
echo ""
echo -e "${RED}This action cannot be undone!${NC}"
echo ""
read -p "Are you sure you want to continue? (type 'yes' to confirm): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo "Cleanup cancelled"
  exit 0
fi

echo ""
read -p "Type 'DELETE' to confirm deletion: " CONFIRM2

if [ "$CONFIRM2" != "DELETE" ]; then
  echo "Cleanup cancelled"
  exit 0
fi

echo ""
echo -e "${YELLOW}Starting cleanup...${NC}"
echo ""

# ============================================================================
# Step 1: Load deployment info
# ============================================================================

if [ -f "$DEPLOYMENT_INFO" ]; then
  echo -e "${YELLOW}[1/6] Loading deployment information...${NC}"

  CONNECT_INSTANCE_ID=$(jq -r '.connect.instance_id // empty' "$DEPLOYMENT_INFO")
  PHONE_NUMBER=$(jq -r '.connect.phone_number // empty' "$DEPLOYMENT_INFO")
  PHONE_NUMBER_ID=$(jq -r '.connect.phone_number_id // empty' "$DEPLOYMENT_INFO")
  CALL_RECORDINGS_BUCKET=$(jq -r '.storage.call_recordings_bucket // empty' "$DEPLOYMENT_INFO")

  echo "  Connect Instance: $CONNECT_INSTANCE_ID"
  echo "  Phone Number: $PHONE_NUMBER"
  echo "  S3 Bucket: $CALL_RECORDINGS_BUCKET"
  echo ""
else
  echo -e "${YELLOW}No deployment info found, will proceed with Terraform destroy only${NC}"
  echo ""
fi

# ============================================================================
# Step 2: Release phone number (if claimed)
# ============================================================================

echo -e "${YELLOW}[2/6] Releasing phone number...${NC}"

if [ -n "$PHONE_NUMBER_ID" ]; then
  echo "  Releasing: $PHONE_NUMBER (ID: $PHONE_NUMBER_ID)"

  RELEASE_RESULT=$(aws connect release-phone-number \
    --phone-number-id "$PHONE_NUMBER_ID" \
    --region "$REGION" 2>&1 || echo "error")

  if echo "$RELEASE_RESULT" | grep -q "error"; then
    echo -e "${YELLOW}  ⚠️  Could not release phone number (may already be released)${NC}"
  else
    echo -e "${GREEN}  ✅ Phone number released${NC}"
  fi
else
  echo "  No phone number to release"
fi
echo ""

# ============================================================================
# Step 3: Empty S3 bucket (required before deletion)
# ============================================================================

echo -e "${YELLOW}[3/6] Emptying S3 bucket...${NC}"

if [ -n "$CALL_RECORDINGS_BUCKET" ]; then
  echo "  Emptying bucket: $CALL_RECORDINGS_BUCKET"

  # Check if bucket exists
  BUCKET_EXISTS=$(aws s3api head-bucket \
    --bucket "$CALL_RECORDINGS_BUCKET" \
    --region "$REGION" 2>&1 || echo "not_found")

  if echo "$BUCKET_EXISTS" | grep -q "not_found\|404"; then
    echo "  Bucket does not exist or already deleted"
  else
    # Delete all objects and versions
    aws s3 rm "s3://$CALL_RECORDINGS_BUCKET" --recursive --region "$REGION" 2>/dev/null || true

    # Delete all versions (if versioning enabled)
    aws s3api list-object-versions \
      --bucket "$CALL_RECORDINGS_BUCKET" \
      --region "$REGION" 2>/dev/null | \
      jq -r '.Versions[]? | .Key + " " + .VersionId' | \
      while read key version; do
        aws s3api delete-object \
          --bucket "$CALL_RECORDINGS_BUCKET" \
          --key "$key" \
          --version-id "$version" \
          --region "$REGION" 2>/dev/null || true
      done

    echo -e "${GREEN}  ✅ S3 bucket emptied${NC}"
  fi
else
  echo "  No S3 bucket to empty"
fi
echo ""

# ============================================================================
# Step 4: Delete DynamoDB table
# ============================================================================

echo -e "${YELLOW}[4/6] Deleting DynamoDB table...${NC}"

DYNAMODB_TABLE="pf-session-data-dev"

TABLE_EXISTS=$(aws dynamodb describe-table \
  --table-name "$DYNAMODB_TABLE" \
  --region "$REGION" 2>&1 || echo "not_found")

if echo "$TABLE_EXISTS" | grep -q "not_found\|ResourceNotFoundException"; then
  echo "  Table does not exist or already deleted"
else
  echo "  Deleting table: $DYNAMODB_TABLE"

  aws dynamodb delete-table \
    --table-name "$DYNAMODB_TABLE" \
    --region "$REGION" > /dev/null 2>&1

  echo "  Waiting for table deletion..."
  aws dynamodb wait table-not-exists \
    --table-name "$DYNAMODB_TABLE" \
    --region "$REGION" 2>/dev/null || true

  echo -e "${GREEN}  ✅ DynamoDB table deleted${NC}"
fi
echo ""

# ============================================================================
# Step 5: Destroy Terraform resources
# ============================================================================

echo -e "${YELLOW}[5/6] Destroying Terraform infrastructure...${NC}"

if [ -d "$TERRAFORM_DIR" ]; then
  cd "$TERRAFORM_DIR"

  # Check if Terraform state exists
  if [ -f "terraform.tfstate" ] || [ -f ".terraform/terraform.tfstate" ]; then
    echo "  Running terraform destroy..."

    terraform destroy -auto-approve

    echo -e "${GREEN}  ✅ Terraform resources destroyed${NC}"
  else
    echo "  No Terraform state found"
  fi
else
  echo "  Terraform directory not found"
fi
echo ""

# ============================================================================
# Step 6: Clean up local files
# ============================================================================

echo -e "${YELLOW}[6/6] Cleaning up local files...${NC}"

# Remove deployment info
if [ -f "$DEPLOYMENT_INFO" ]; then
  rm "$DEPLOYMENT_INFO"
  echo "  Removed: $DEPLOYMENT_INFO"
fi

# Remove Terraform state backups
if [ -d "$TERRAFORM_DIR" ]; then
  cd "$TERRAFORM_DIR"
  rm -f terraform.tfstate.backup
  rm -f terraform.tfstate.*.backup
  rm -f tfplan
  echo "  Removed: Terraform state backups"
fi

# Remove Lambda deployment packages
rm -f "$PROJECT_ROOT/lambda/lex-fulfillment/deployment.zip"
rm -f "$PROJECT_ROOT/lambda/voice-bedrock-bridge/deployment.zip"
rm -rf "$PROJECT_ROOT/lambda/lex-fulfillment/package"
rm -rf "$PROJECT_ROOT/lambda/voice-bedrock-bridge/package"
echo "  Removed: Lambda deployment packages"

echo -e "${GREEN}  ✅ Local files cleaned${NC}"
echo ""

# ============================================================================
# Cleanup Summary
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Cleanup Complete!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Deleted:"
echo "  ✅ Lambda functions (pf-lex-fulfillment-dev, pf-voice-bedrock-bridge-dev)"
echo "  ✅ S3 bucket (call recordings)"
echo "  ✅ DynamoDB table (session data)"
echo "  ✅ IAM roles and policies"
echo "  ✅ Local deployment files"
echo ""

echo "Manual cleanup required (via AWS Console):"
if [ -n "$PHONE_NUMBER" ]; then
  echo "  📋 Phone number: $PHONE_NUMBER (release via Connect Console)"
fi
if [ -n "$CONNECT_INSTANCE_ID" ]; then
  echo "  📋 Connect instance: $CONNECT_INSTANCE_ID (delete via Connect Console)"
fi
echo "  📋 Lex bot (if created - delete via Lex Console)"
echo "  📋 Contact flows (if created - delete via Connect Console)"
echo ""

echo "What remains unchanged:"
echo "  ✅ Bedrock agents (Supervisor, SchedulingAgent, pf-information, pf-chitchat)"
echo "  ✅ Action groups and collaborator associations"
echo "  ✅ Core infrastructure (scheduling, information agents)"
echo ""

echo -e "${GREEN}Voice integration Lambda functions and storage removed.${NC}"
echo ""
echo "To redeploy, run: ./scripts/DEPLOY_VOICE_MINIMAL.sh"
echo ""
