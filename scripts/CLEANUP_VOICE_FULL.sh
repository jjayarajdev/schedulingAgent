#!/bin/bash

# ============================================================================
# AWS Connect Voice Integration - Full Cleanup Script
# ============================================================================
# Purpose: Remove all AWS Connect voice integration resources
# Includes: Connect instance, Lex bot, Lambda functions, phone number, storage
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
TERRAFORM_DIR="$PROJECT_ROOT/infrastructure/terraform/voice"
DEPLOYMENT_INFO="$PROJECT_ROOT/config/voice_deployment.json"
REGION="us-east-1"

echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}  AWS Connect Voice Integration - Full Cleanup${NC}"
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}WARNING: This will delete:${NC}"
echo "  - AWS Connect instance"
echo "  - Phone number (will be released)"
echo "  - Amazon Lex bot"
echo "  - Lambda functions (lex-fulfillment, voice-bedrock-bridge)"
echo "  - S3 bucket (call recordings)"
echo "  - DynamoDB table (session data)"
echo "  - KMS keys"
echo "  - All IAM roles and policies"
echo "  - Contact flows and configurations"
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

echo -e "${YELLOW}[1/5] Loading deployment information...${NC}"

if [ -f "$DEPLOYMENT_INFO" ]; then
  CONNECT_INSTANCE_ID=$(jq -r '.connect.instance_id // empty' "$DEPLOYMENT_INFO")
  PHONE_NUMBER=$(jq -r '.phone_number // empty' "$DEPLOYMENT_INFO")
  LEX_BOT_ID=$(jq -r '.lex.bot_id // empty' "$DEPLOYMENT_INFO")
  CALL_RECORDINGS_BUCKET=$(jq -r '.storage.call_recordings_bucket // empty' "$DEPLOYMENT_INFO")
  DYNAMODB_TABLE=$(jq -r '.storage.dynamodb_table // empty' "$DEPLOYMENT_INFO")

  echo "  Connect Instance: $CONNECT_INSTANCE_ID"
  echo "  Phone Number: $PHONE_NUMBER"
  echo "  Lex Bot: $LEX_BOT_ID"
  echo "  S3 Bucket: $CALL_RECORDINGS_BUCKET"
  echo "  DynamoDB Table: $DYNAMODB_TABLE"
  echo ""
else
  echo -e "${YELLOW}  No deployment info found, will rely on Terraform state${NC}"
  echo ""
fi

# ============================================================================
# Step 2: Empty S3 bucket (required before deletion)
# ============================================================================

echo -e "${YELLOW}[2/5] Emptying S3 bucket...${NC}"

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
    echo "  Deleting all objects..."
    aws s3 rm "s3://$CALL_RECORDINGS_BUCKET" --recursive --region "$REGION" 2>/dev/null || true

    # Delete all versions (if versioning enabled)
    echo "  Deleting all versions..."
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

    # Delete delete markers
    echo "  Deleting delete markers..."
    aws s3api list-object-versions \
      --bucket "$CALL_RECORDINGS_BUCKET" \
      --region "$REGION" 2>/dev/null | \
      jq -r '.DeleteMarkers[]? | .Key + " " + .VersionId' | \
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
# Step 3: Delete Connect phone numbers (if any claimed)
# ============================================================================

echo -e "${YELLOW}[3/5] Releasing phone numbers...${NC}"

if [ -n "$CONNECT_INSTANCE_ID" ]; then
  echo "  Checking for phone numbers in Connect instance..."

  PHONE_NUMBERS=$(aws connect list-phone-numbers-v2 \
    --target-arn "arn:aws:connect:${REGION}:$(aws sts get-caller-identity --query Account --output text):instance/${CONNECT_INSTANCE_ID}" \
    --region "$REGION" \
    --query 'ListPhoneNumbersSummaryList[*].PhoneNumber' \
    --output text 2>/dev/null || echo "")

  if [ -n "$PHONE_NUMBERS" ]; then
    for PHONE in $PHONE_NUMBERS; do
      echo "  Releasing phone number: $PHONE"
      PHONE_NUMBER_ID=$(aws connect list-phone-numbers-v2 \
        --target-arn "arn:aws:connect:${REGION}:$(aws sts get-caller-identity --query Account --output text):instance/${CONNECT_INSTANCE_ID}" \
        --region "$REGION" \
        --query "ListPhoneNumbersSummaryList[?PhoneNumber=='${PHONE}'].PhoneNumberId" \
        --output text 2>/dev/null || echo "")

      if [ -n "$PHONE_NUMBER_ID" ]; then
        aws connect release-phone-number \
          --phone-number-id "$PHONE_NUMBER_ID" \
          --region "$REGION" 2>/dev/null || true
        echo -e "${GREEN}  ✅ Phone number released: $PHONE${NC}"
      fi
    done
  else
    echo "  No phone numbers found"
  fi
else
  echo "  No Connect instance ID found"
fi
echo ""

# ============================================================================
# Step 4: Destroy Terraform resources
# ============================================================================

echo -e "${YELLOW}[4/5] Destroying Terraform infrastructure...${NC}"

if [ -d "$TERRAFORM_DIR" ]; then
  cd "$TERRAFORM_DIR"

  # Check if Terraform state exists
  if [ -f "terraform.tfstate" ] || [ -f ".terraform/terraform.tfstate" ]; then
    echo "  Running terraform destroy..."
    echo ""

    # Destroy with auto-approve
    terraform destroy -auto-approve

    echo ""
    echo -e "${GREEN}  ✅ Terraform resources destroyed${NC}"
  else
    echo "  No Terraform state found"
  fi
else
  echo "  Terraform directory not found"
fi
echo ""

# ============================================================================
# Step 5: Delete IAM Roles (Critical - these survive terraform destroy)
# ============================================================================

echo -e "${YELLOW}[5/7] Deleting IAM Roles...${NC}"

IAM_ROLES=(
  "pf-lex-fulfillment-role-dev"
  "pf-voice-bedrock-bridge-role-dev"
  "pf-lex-bot-role-dev"
)

for ROLE_NAME in "${IAM_ROLES[@]}"; do
  if aws iam get-role --role-name "$ROLE_NAME" --region "$REGION" &>/dev/null; then
    echo "  Deleting role: $ROLE_NAME"

    # Detach all managed policies
    POLICIES=$(aws iam list-attached-role-policies \
      --role-name "$ROLE_NAME" \
      --query 'AttachedPolicies[*].PolicyArn' \
      --output text 2>/dev/null || echo "")

    if [ -n "$POLICIES" ]; then
      for POLICY_ARN in $POLICIES; do
        echo "    Detaching policy: $POLICY_ARN"
        aws iam detach-role-policy \
          --role-name "$ROLE_NAME" \
          --policy-arn "$POLICY_ARN" 2>/dev/null || true
      done
    fi

    # Delete all inline policies
    INLINE_POLICIES=$(aws iam list-role-policies \
      --role-name "$ROLE_NAME" \
      --query 'PolicyNames[*]' \
      --output text 2>/dev/null || echo "")

    if [ -n "$INLINE_POLICIES" ]; then
      for POLICY_NAME in $INLINE_POLICIES; do
        echo "    Deleting inline policy: $POLICY_NAME"
        aws iam delete-role-policy \
          --role-name "$ROLE_NAME" \
          --policy-name "$POLICY_NAME" 2>/dev/null || true
      done
    fi

    # Delete the role
    aws iam delete-role --role-name "$ROLE_NAME" 2>/dev/null && \
      echo -e "${GREEN}  ✅ Role deleted: $ROLE_NAME${NC}" || \
      echo -e "${RED}  ⚠️  Failed to delete role: $ROLE_NAME${NC}"
  else
    echo "  Role not found: $ROLE_NAME"
  fi
done
echo ""

# ============================================================================
# Step 6: Delete KMS Aliases (these can persist after terraform destroy)
# ============================================================================

echo -e "${YELLOW}[6/7] Deleting KMS Aliases...${NC}"

KMS_ALIASES=("alias/pf-connect-recordings-dev")

for ALIAS_NAME in "${KMS_ALIASES[@]}"; do
  # Check if alias exists
  if aws kms describe-key --key-id "$ALIAS_NAME" --region "$REGION" &>/dev/null; then
    echo "  Deleting KMS alias: $ALIAS_NAME"
    aws kms delete-alias \
      --alias-name "$ALIAS_NAME" \
      --region "$REGION" 2>/dev/null && \
      echo -e "${GREEN}  ✅ KMS alias deleted: $ALIAS_NAME${NC}" || \
      echo -e "${RED}  ⚠️  Failed to delete alias: $ALIAS_NAME${NC}"
  else
    echo "  KMS alias not found: $ALIAS_NAME"
  fi
done
echo ""

# ============================================================================
# Step 7: Delete CloudWatch Log Groups
# ============================================================================

echo -e "${YELLOW}[7/8] Deleting CloudWatch Log Groups...${NC}"

LOG_GROUPS=(
  "/aws/lambda/pf-lex-fulfillment-dev"
  "/aws/lambda/pf-voice-bedrock-bridge-dev"
)

for LOG_GROUP in "${LOG_GROUPS[@]}"; do
  if aws logs describe-log-groups \
    --log-group-name-prefix "$LOG_GROUP" \
    --region "$REGION" \
    --query 'logGroups[0].logGroupName' \
    --output text 2>/dev/null | grep -q "$LOG_GROUP"; then

    echo "  Deleting log group: $LOG_GROUP"
    aws logs delete-log-group \
      --log-group-name "$LOG_GROUP" \
      --region "$REGION" 2>/dev/null && \
      echo -e "${GREEN}  ✅ Log group deleted: $LOG_GROUP${NC}" || \
      echo -e "${RED}  ⚠️  Failed to delete: $LOG_GROUP${NC}"
  else
    echo "  Log group not found: $LOG_GROUP"
  fi
done
echo ""

# ============================================================================
# Step 8: Clean up local files
# ============================================================================

echo -e "${YELLOW}[8/8] Cleaning up local files...${NC}"

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
  rm -f terraform.tfvars
  echo "  Removed: Terraform state backups and variables"
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
echo "  ✅ AWS Connect instance"
if [ -n "$PHONE_NUMBER" ]; then
  echo "  ✅ Phone number: $PHONE_NUMBER"
fi
echo "  ✅ Amazon Lex bot"
echo "  ✅ Lambda functions (pf-lex-fulfillment-dev, pf-voice-bedrock-bridge-dev)"
echo "  ✅ S3 bucket (call recordings)"
echo "  ✅ DynamoDB table (session data)"
echo "  ✅ KMS keys and aliases"
echo "  ✅ IAM roles (3 roles with policies detached)"
echo "  ✅ Contact flows and configurations"
echo "  ✅ CloudWatch log groups"
echo "  ✅ Local deployment files"
echo ""

echo "What remains unchanged:"
echo "  ✅ Bedrock agents (Supervisor, SchedulingAgent, pf-information, pf-chitchat)"
echo "  ✅ Action groups and collaborator associations"
echo "  ✅ Core infrastructure (scheduling, information agents)"
echo ""

echo -e "${GREEN}Voice integration completely removed.${NC}"
echo ""
echo "To redeploy, run: ./scripts/DEPLOY_VOICE_FULL.sh"
echo ""
