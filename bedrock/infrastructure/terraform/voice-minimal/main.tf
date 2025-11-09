# ============================================================================
# Simplified Voice Integration - Core Infrastructure Only
# ============================================================================
# Purpose: Deploy Lambda functions and supporting infrastructure
# Lex bot and Connect instance will be created manually via Console
# ============================================================================

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = "ProjectForce"
      ManagedBy   = "Terraform"
      Phase       = "Voice"
      Environment = var.environment
    }
  }
}

data "aws_caller_identity" "current" {}

# ============================================================================
# DynamoDB Table for Session Data
# ============================================================================

resource "aws_dynamodb_table" "session_data" {
  name         = var.dynamodb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "session_id"

  attribute {
    name = "session_id"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    Name = "${var.prefix}-session-data-${var.environment}"
  }
}

# ============================================================================
# S3 Bucket for Call Recordings (Optional - for when you set up Connect)
# ============================================================================

resource "aws_s3_bucket" "call_recordings" {
  bucket = "${var.prefix}-call-recordings-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name    = "${var.prefix}-call-recordings-${var.environment}"
    Purpose = "AWS Connect Call Recordings"
  }
}

resource "aws_s3_bucket_versioning" "call_recordings" {
  bucket = aws_s3_bucket.call_recordings.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "call_recordings" {
  bucket = aws_s3_bucket.call_recordings.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "call_recordings" {
  bucket = aws_s3_bucket.call_recordings.id

  rule {
    id     = "delete-old-recordings"
    status = "Enabled"

    filter {}

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

resource "aws_s3_bucket_public_access_block" "call_recordings" {
  bucket = aws_s3_bucket.call_recordings.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ============================================================================
# Lambda Function: Lex Fulfillment
# ============================================================================

resource "aws_lambda_function" "lex_fulfillment" {
  filename         = "${path.module}/../../../lambda/lex-fulfillment/deployment.zip"
  function_name    = "${var.prefix}-lex-fulfillment-${var.environment}"
  role             = aws_iam_role.lex_fulfillment.arn
  handler          = "handler.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/../../../lambda/lex-fulfillment/deployment.zip")
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 512

  environment {
    variables = {
      DYNAMODB_TABLE      = var.dynamodb_table_name
      INFORMATION_LAMBDA  = "pf-information-actions"
      VOICE_BRIDGE_LAMBDA = "${var.prefix}-voice-bedrock-bridge-${var.environment}"
    }
  }

  tags = {
    Name = "${var.prefix}-lex-fulfillment-${var.environment}"
  }
}

resource "aws_cloudwatch_log_group" "lex_fulfillment" {
  name              = "/aws/lambda/${aws_lambda_function.lex_fulfillment.function_name}"
  retention_in_days = 14

  tags = {
    Name = "${var.prefix}-lex-fulfillment-logs-${var.environment}"
  }
}

resource "aws_iam_role" "lex_fulfillment" {
  name = "${var.prefix}-lex-fulfillment-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.prefix}-lex-fulfillment-role-${var.environment}"
  }
}

resource "aws_iam_role_policy" "lex_fulfillment" {
  name = "${var.prefix}-lex-fulfillment-policy-${var.environment}"
  role = aws_iam_role.lex_fulfillment.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.prefix}-lex-fulfillment-${var.environment}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ]
        Resource = "arn:aws:dynamodb:${var.region}:${data.aws_caller_identity.current.account_id}:table/${var.dynamodb_table_name}"
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:pf-information-actions",
          "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${var.prefix}-voice-bedrock-bridge-${var.environment}"
        ]
      }
    ]
  })
}

# Lambda permission for Lex to invoke
resource "aws_lambda_permission" "lex_fulfillment" {
  statement_id  = "AllowExecutionFromLex"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lex_fulfillment.function_name
  principal     = "lexv2.amazonaws.com"
}

# ============================================================================
# Lambda Function: Voice-Bedrock Bridge
# ============================================================================

resource "aws_lambda_function" "voice_bedrock_bridge" {
  filename         = "${path.module}/../../../lambda/voice-bedrock-bridge/deployment.zip"
  function_name    = "${var.prefix}-voice-bedrock-bridge-${var.environment}"
  role             = aws_iam_role.voice_bedrock_bridge.arn
  handler          = "handler.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/../../../lambda/voice-bedrock-bridge/deployment.zip")
  runtime          = "python3.11"
  timeout          = 120
  memory_size      = 512

  environment {
    variables = {
      SUPERVISOR_AGENT_ID       = var.supervisor_agent_id
      SUPERVISOR_AGENT_ALIAS_ID = var.supervisor_agent_alias_id
      DYNAMODB_TABLE            = var.dynamodb_table_name
    }
  }

  tags = {
    Name = "${var.prefix}-voice-bedrock-bridge-${var.environment}"
  }
}

resource "aws_cloudwatch_log_group" "voice_bedrock_bridge" {
  name              = "/aws/lambda/${aws_lambda_function.voice_bedrock_bridge.function_name}"
  retention_in_days = 14

  tags = {
    Name = "${var.prefix}-voice-bridge-logs-${var.environment}"
  }
}

resource "aws_iam_role" "voice_bedrock_bridge" {
  name = "${var.prefix}-voice-bedrock-bridge-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.prefix}-voice-bedrock-bridge-role-${var.environment}"
  }
}

resource "aws_iam_role_policy" "voice_bedrock_bridge" {
  name = "${var.prefix}-voice-bedrock-bridge-policy-${var.environment}"
  role = aws_iam_role.voice_bedrock_bridge.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.prefix}-voice-bedrock-bridge-${var.environment}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ]
        Resource = "arn:aws:dynamodb:${var.region}:${data.aws_caller_identity.current.account_id}:table/${var.dynamodb_table_name}"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeAgent"
        ]
        Resource = [
          "arn:aws:bedrock:${var.region}:${data.aws_caller_identity.current.account_id}:agent/${var.supervisor_agent_id}",
          "arn:aws:bedrock:${var.region}:${data.aws_caller_identity.current.account_id}:agent-alias/${var.supervisor_agent_id}/*"
        ]
      }
    ]
  })
}

# ============================================================================
# Outputs
# ============================================================================

output "lex_fulfillment_function_name" {
  description = "Lex Fulfillment Lambda Function Name"
  value       = aws_lambda_function.lex_fulfillment.function_name
}

output "lex_fulfillment_function_arn" {
  description = "Lex Fulfillment Lambda Function ARN"
  value       = aws_lambda_function.lex_fulfillment.arn
}

output "voice_bedrock_bridge_function_name" {
  description = "Voice-Bedrock Bridge Lambda Function Name"
  value       = aws_lambda_function.voice_bedrock_bridge.function_name
}

output "voice_bedrock_bridge_function_arn" {
  description = "Voice-Bedrock Bridge Lambda Function ARN"
  value       = aws_lambda_function.voice_bedrock_bridge.arn
}

output "dynamodb_table_name" {
  description = "DynamoDB Table Name for Session Data"
  value       = aws_dynamodb_table.session_data.name
}

output "call_recordings_bucket" {
  description = "S3 Bucket for Call Recordings"
  value       = aws_s3_bucket.call_recordings.id
}

output "supervisor_agent_id" {
  description = "Bedrock Supervisor Agent ID (for reference)"
  value       = var.supervisor_agent_id
}

output "supervisor_agent_alias_id" {
  description = "Bedrock Supervisor Agent Alias ID (for reference)"
  value       = var.supervisor_agent_alias_id
}
