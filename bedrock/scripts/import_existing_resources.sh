#!/bin/bash

# ============================================================================
# Import Existing Resources into Terraform State
# ============================================================================
# Purpose: Import resources created in previous partial deployment
# ============================================================================

set -e

REGION="us-east-1"
TERRAFORM_DIR="../infrastructure/terraform/voice"

echo "=============================================="
echo "Importing Existing Resources"
echo "=============================================="
echo ""

cd "$TERRAFORM_DIR"

# Connect Instance
echo "1. Importing Connect instance..."
terraform import aws_connect_instance.main 4d798e12-1364-42ce-9b5b-cd4ae93804a7 2>/dev/null && \
  echo "  ✅ Connect instance imported" || echo "  ⚠️  Already imported or not found"

# S3 Bucket
echo "2. Importing S3 bucket..."
terraform import aws_s3_bucket.call_recordings pf-call-recordings-dev-772634497954 2>/dev/null && \
  echo "  ✅ S3 bucket imported" || echo "  ⚠️  Already imported or not found"

# S3 Bucket configurations
echo "3. Importing S3 bucket configurations..."
terraform import aws_s3_bucket_versioning.call_recordings pf-call-recordings-dev-772634497954 2>/dev/null && \
  echo "  ✅ S3 versioning imported" || echo "  ⚠️  Already imported"

terraform import aws_s3_bucket_server_side_encryption_configuration.call_recordings pf-call-recordings-dev-772634497954 2>/dev/null && \
  echo "  ✅ S3 encryption imported" || echo "  ⚠️  Already imported"

terraform import aws_s3_bucket_public_access_block.call_recordings pf-call-recordings-dev-772634497954 2>/dev/null && \
  echo "  ✅ S3 public access block imported" || echo "  ⚠️  Already imported"

terraform import aws_s3_bucket_lifecycle_configuration.call_recordings pf-call-recordings-dev-772634497954 2>/dev/null && \
  echo "  ✅ S3 lifecycle imported" || echo "  ⚠️  Already imported"

# KMS Key
echo "4. Importing KMS key..."
terraform import aws_kms_key.connect_recordings cce5245f-359a-4cde-8235-6b1ba33bce6b 2>/dev/null && \
  echo "  ✅ KMS key imported" || echo "  ⚠️  Already imported"

terraform import aws_kms_alias.connect_recordings alias/pf-connect-recordings-dev 2>/dev/null && \
  echo "  ✅ KMS alias imported" || echo "  ⚠️  Already imported"

# Connect Hours of Operation
echo "5. Importing Connect hours of operation..."
terraform import aws_connect_hours_of_operation.main 4d798e12-1364-42ce-9b5b-cd4ae93804a7:116853d2-7d71-4c75-b6e8-2e65e948149c 2>/dev/null && \
  echo "  ✅ Hours of operation imported" || echo "  ⚠️  Already imported"

# Connect Queue
echo "6. Importing Connect queue..."
terraform import aws_connect_queue.main 4d798e12-1364-42ce-9b5b-cd4ae93804a7:2d6039ab-0239-4d64-8de5-15e5a89aae2b 2>/dev/null && \
  echo "  ✅ Connect queue imported" || echo "  ⚠️  Already imported"

# Connect Storage Config
echo "7. Importing Connect storage config..."
terraform import 'aws_connect_instance_storage_config.call_recordings' '4d798e12-1364-42ce-9b5b-cd4ae93804a7:09bcd56684ef58e7b885894a3c07f38d6f7b1fcaf8b3d2eb89124534c9fd307f:CALL_RECORDINGS' 2>/dev/null && \
  echo "  ✅ Storage config imported" || echo "  ⚠️  Already imported"

# CloudWatch Log Groups
echo "8. Importing CloudWatch log groups..."
terraform import aws_cloudwatch_log_group.lex_fulfillment /aws/lambda/pf-lex-fulfillment-dev 2>/dev/null && \
  echo "  ✅ Lex fulfillment log group imported" || echo "  ⚠️  Already imported"

terraform import aws_cloudwatch_log_group.voice_bedrock_bridge /aws/lambda/pf-voice-bedrock-bridge-dev 2>/dev/null && \
  echo "  ✅ Voice bridge log group imported" || echo "  ⚠️  Already imported"

echo ""
echo "=============================================="
echo "✅ Import Complete!"
echo "=============================================="
echo ""
echo "Now run: terraform apply -auto-approve"
echo ""
