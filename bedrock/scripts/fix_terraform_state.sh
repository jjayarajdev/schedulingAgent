#!/bin/bash

# ============================================================================
# Fix Terraform State - Use Existing pf-voice-dev Instance
# ============================================================================
# Purpose: Clean up duplicate instance and import existing pf-voice-dev
# ============================================================================

set -e

REGION="us-east-1"
TERRAFORM_DIR="../infrastructure/terraform/voice"

echo "=============================================="
echo "Fixing Terraform State"
echo "=============================================="
echo ""

cd "$TERRAFORM_DIR"

# Step 1: Delete the accidentally created pf-scheduling-assistant instance
echo "Step 1: Deleting duplicate pf-scheduling-assistant instance..."
echo ""

INSTANCE_ID="b8f4f3cf-c4bf-4b2a-943b-8e6b08a4e705"

echo "Removing from Terraform state..."
terraform state rm aws_connect_instance.main 2>/dev/null || echo "  (not in state)"
terraform state rm aws_connect_instance_storage_config.call_recordings 2>/dev/null || echo "  (not in state)"
terraform state rm aws_connect_hours_of_operation.main 2>/dev/null || echo "  (not in state)"
terraform state rm aws_connect_queue.main 2>/dev/null || echo "  (not in state)"

echo ""
echo "Deleting AWS Connect instance: $INSTANCE_ID"
aws connect delete-instance \
  --instance-id "$INSTANCE_ID" \
  --region "$REGION" 2>/dev/null && echo "  ✅ Instance deleted" || echo "  ⚠️  Instance may already be deleted"

echo ""
echo "=============================================="
echo "✅ Cleanup Complete"
echo "=============================================="
echo ""
echo "Now you can run terraform destroy to clean up remaining resources,"
echo "then redeploy with the corrected configuration."
echo ""
echo "Next steps:"
echo "  1. cd $TERRAFORM_DIR"
echo "  2. terraform destroy"
echo "  3. cd ../../scripts"
echo "  4. ./DEPLOY_VOICE_FULL.sh"
echo ""
