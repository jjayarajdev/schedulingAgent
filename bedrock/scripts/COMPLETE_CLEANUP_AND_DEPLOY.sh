#!/bin/bash

# ============================================================================
# Complete Cleanup and Fresh Deploy
# ============================================================================
# Purpose: One script to rule them all - complete cleanup + fresh deployment
# ============================================================================

set -e

REGION="us-east-1"

echo "=============================================="
echo "Complete Cleanup and Fresh Deploy"
echo "=============================================="
echo ""
echo "This will:"
echo "  1. Delete ALL voice resources"
echo "  2. Clean Terraform state"
echo "  3. Deploy fresh"
echo ""
read -p "Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo "Cancelled."
  exit 0
fi

# ============================================================================
# STEP 1: Complete Cleanup
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 1: Complete Cleanup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

./CLEANUP_ALL_VOICE_RESOURCES.sh

# ============================================================================
# STEP 2: Clean Terraform State
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 2: Cleaning Terraform State"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd ../infrastructure/terraform/voice
rm -f terraform.tfstate*
rm -f .terraform.lock.hcl
rm -rf .terraform
echo "✅ Terraform state cleaned"

cd ../../../scripts

# ============================================================================
# STEP 3: Fresh Deployment
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 3: Fresh Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

./DEPLOY_VOICE_FULL.sh

echo ""
echo "=============================================="
echo "✅ COMPLETE!"
echo "=============================================="
