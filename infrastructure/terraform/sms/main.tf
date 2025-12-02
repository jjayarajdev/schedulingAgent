# Simplified SMS Infrastructure for Development
# This version excludes phone number provisioning for faster testing
# Use this for development, then switch to main.tf for production

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# Data sources
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# Local variables
locals {
  project_name = "scheduling-agent"
  environment  = var.environment
  # Phone number for development (matches the provisioned number)
  phone_number = "+14255556160"
  tags = merge(
    var.additional_tags,
    {
      Project     = local.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Phase       = "Phase2-SMS-Dev"
    }
  )
}

#==============================================================================
# SNS Topic for Inbound Messages
#==============================================================================

resource "aws_sns_topic" "sms_inbound" {
  name         = "${local.project_name}-sms-inbound-${var.environment}"
  display_name = "Inbound SMS Messages"
  # KMS encryption removed for dev environment

  tags = local.tags
}

resource "aws_sns_topic_policy" "sms_inbound" {
  arn = aws_sns_topic.sms_inbound.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "sms-voice.amazonaws.com"
        }
        Action   = "SNS:Publish"
        Resource = aws_sns_topic.sms_inbound.arn
      }
    ]
  })
}

#==============================================================================
# DynamoDB Tables
#==============================================================================

# SMS Consent Tracking Table
resource "aws_dynamodb_table" "sms_consent" {
  name           = "${local.project_name}-sms-consent-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "phone_number"

  attribute {
    name = "phone_number"
    type = "S"
  }

  attribute {
    name = "opt_out_deadline"
    type = "S"
  }

  attribute {
    name = "customer_id"
    type = "S"
  }

  global_secondary_index {
    name            = "customer-index"
    hash_key        = "customer_id"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "deadline-index"
    hash_key        = "opt_out_deadline"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = merge(local.tags, {
    Name = "${local.project_name}-sms-consent-${var.environment}"
  })
}

# Opt-Out Tracking Table
resource "aws_dynamodb_table" "opt_out_tracking" {
  name           = "${local.project_name}-opt-out-tracking-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "tracking_id"
  range_key      = "timestamp"

  attribute {
    name = "tracking_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "phone_number"
    type = "S"
  }

  global_secondary_index {
    name            = "phone-index"
    hash_key        = "phone_number"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  tags = merge(local.tags, {
    Name = "${local.project_name}-opt-out-tracking-${var.environment}"
  })
}

# SMS Messages Table
resource "aws_dynamodb_table" "sms_messages" {
  name           = "${local.project_name}-sms-messages-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "message_id"
  range_key      = "timestamp"

  attribute {
    name = "message_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "phone_number"
    type = "S"
  }

  attribute {
    name = "session_id"
    type = "S"
  }

  global_secondary_index {
    name            = "phone-index"
    hash_key        = "phone_number"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "session-index"
    hash_key        = "session_id"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = merge(local.tags, {
    Name = "${local.project_name}-sms-messages-${var.environment}"
  })
}

# SMS Sessions Table
resource "aws_dynamodb_table" "sms_sessions" {
  name           = "${local.project_name}-sms-sessions-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "session_id"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "phone_number"
    type = "S"
  }

  global_secondary_index {
    name            = "phone-index"
    hash_key        = "phone_number"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = merge(local.tags, {
    Name = "${local.project_name}-sms-sessions-${var.environment}"
  })
}

#==============================================================================
# CloudWatch Logs
#==============================================================================

resource "aws_cloudwatch_log_group" "lambda_sms_inbound" {
  name              = "/aws/lambda/${local.project_name}-sms-inbound-${var.environment}"
  retention_in_days = 7  # Shorter retention for dev

  tags = local.tags
}

#==============================================================================
# Lambda IAM Role
#==============================================================================

resource "aws_iam_role" "lambda_sms" {
  name = "${local.project_name}-lambda-sms-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_sms.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_sms_permissions" {
  name = "sms-permissions"
  role = aws_iam_role.lambda_sms.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sms-voice:SendTextMessage",
          "sms-voice:DescribePhoneNumbers",
          "sms-voice:DescribeOptOutLists"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.sms_consent.arn,
          "${aws_dynamodb_table.sms_consent.arn}/index/*",
          aws_dynamodb_table.opt_out_tracking.arn,
          "${aws_dynamodb_table.opt_out_tracking.arn}/index/*",
          aws_dynamodb_table.sms_messages.arn,
          "${aws_dynamodb_table.sms_messages.arn}/index/*",
          aws_dynamodb_table.sms_sessions.arn,
          "${aws_dynamodb_table.sms_sessions.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:pf-orchestrator",
          "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:*-orchestrator-*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.sms_inbound.arn
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:projectforce/api/credentials-*"
      }
    ]
  })
}

#==============================================================================
# Lambda Function
#==============================================================================

resource "aws_lambda_function" "sms_inbound_processor" {
  filename      = "${path.module}/../../../lambda/sms-inbound-processor/lambda.zip"
  function_name = "${local.project_name}-sms-inbound-${var.environment}"
  role          = aws_iam_role.lambda_sms.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 512

  source_code_hash = filebase64sha256("${path.module}/../../../lambda/sms-inbound-processor/lambda.zip")

  environment {
    variables = {
      ENVIRONMENT             = var.environment
      ORCHESTRATOR_LAMBDA     = "pf-orchestrator"  # Using existing pf-orchestrator lambda
      ORIGINATION_NUMBER      = local.phone_number
      CONSENT_TABLE           = aws_dynamodb_table.sms_consent.name
      OPT_OUT_TRACKING_TABLE  = aws_dynamodb_table.opt_out_tracking.name
      MESSAGES_TABLE          = aws_dynamodb_table.sms_messages.name
      SESSIONS_TABLE          = aws_dynamodb_table.sms_sessions.name
      AWS_REGION_NAME         = data.aws_region.current.name
      SMS_CONFIGURATION_SET   = "${local.project_name}-sms-config-${var.environment}"
      PF_SECRET_NAME          = "projectforce/api/credentials"
    }
  }

  tags = local.tags
}

# SNS subscription to trigger Lambda
resource "aws_sns_topic_subscription" "sms_inbound_lambda" {
  topic_arn = aws_sns_topic.sms_inbound.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.sms_inbound_processor.arn
}

# Grant SNS permission to invoke Lambda
resource "aws_lambda_permission" "sns_invoke" {
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sms_inbound_processor.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.sms_inbound.arn
}

#==============================================================================
# Outputs
#==============================================================================

output "sns_topic_arn" {
  description = "SNS topic ARN for testing"
  value       = aws_sns_topic.sms_inbound.arn
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.sms_inbound_processor.function_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.sms_inbound_processor.arn
}

output "dynamodb_tables" {
  description = "DynamoDB table names"
  value = {
    consent      = aws_dynamodb_table.sms_consent.name
    opt_out      = aws_dynamodb_table.opt_out_tracking.name
    messages     = aws_dynamodb_table.sms_messages.name
    sessions     = aws_dynamodb_table.sms_sessions.name
  }
}

output "test_command" {
  description = "Command to test the SMS processor"
  value       = "python scripts/test-sms-sns-trigger.py --environment ${var.environment} --phone +15555551234 --message 'Test message'"
}
