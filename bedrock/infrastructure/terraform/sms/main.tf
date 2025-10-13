# Phase 2: AWS End User Messaging SMS Infrastructure
# This Terraform configuration sets up AWS SMS services for two-way messaging

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
  tags = merge(
    var.additional_tags,
    {
      Project     = local.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Phase       = "Phase2-SMS"
    }
  )
}

#==============================================================================
# AWS End User Messaging SMS - Phone Number Pool
#==============================================================================

# Pool for phone numbers
resource "aws_pinpointsmsvoicev2_phone_number" "main" {
  iso_country_code         = "US"
  message_type            = "TRANSACTIONAL"
  number_type             = "TOLL_FREE"
  number_capabilities     = ["SMS", "MMS", "VOICE"]
  deletion_protection_enabled = var.environment == "prod" ? true : false

  tags = merge(
    local.tags,
    {
      Name = "${local.project_name}-toll-free-${var.environment}"
    }
  )
}

#==============================================================================
# Opt-Out List
#==============================================================================

resource "aws_pinpointsmsvoicev2_opt_out_list" "main" {
  opt_out_list_name = "${local.project_name}-opt-out-${var.environment}"

  tags = local.tags
}

# Associate phone number with opt-out list
resource "aws_pinpointsmsvoicev2_phone_number_association" "opt_out" {
  phone_number_id   = aws_pinpointsmsvoicev2_phone_number.main.id
  opt_out_list_name = aws_pinpointsmsvoicev2_opt_out_list.main.opt_out_list_name
}

#==============================================================================
# Configuration Set for Event Tracking
#==============================================================================

resource "aws_pinpointsmsvoicev2_configuration_set" "main" {
  name = "${local.project_name}-sms-config-${var.environment}"

  tags = local.tags
}

# CloudWatch event destination for delivery events
resource "aws_pinpointsmsvoicev2_event_destination" "cloudwatch" {
  configuration_set_name = aws_pinpointsmsvoicev2_configuration_set.main.name
  event_destination_name = "cloudwatch-logs"

  matching_event_types = [
    "TEXT_SENT",
    "TEXT_SUCCESSFUL",
    "TEXT_DELIVERED",
    "TEXT_TTL_EXPIRED",
    "TEXT_INVALID",
    "TEXT_UNREACHABLE",
    "TEXT_CARRIER_UNREACHABLE",
    "TEXT_BLOCKED",
    "TEXT_CARRIER_BLOCKED",
    "TEXT_SPAM",
    "TEXT_UNKNOWN",
  ]

  cloud_watch_logs_destination {
    iam_role_arn   = aws_iam_role.sms_cloudwatch.arn
    log_group_arn  = aws_cloudwatch_log_group.sms_events.arn
  }
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "sms_events" {
  name              = "/aws/sms/${local.project_name}/${var.environment}"
  retention_in_days = 30

  tags = local.tags
}

# IAM role for CloudWatch logging
resource "aws_iam_role" "sms_cloudwatch" {
  name = "${local.project_name}-sms-cloudwatch-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "sms-voice.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = local.tags
}

resource "aws_iam_role_policy" "sms_cloudwatch" {
  name = "cloudwatch-logs"
  role = aws_iam_role.sms_cloudwatch.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.sms_events.arn}:*"
      }
    ]
  })
}

#==============================================================================
# SNS Topic for Inbound Messages
#==============================================================================

resource "aws_sns_topic" "sms_inbound" {
  name              = "${local.project_name}-sms-inbound-${var.environment}"
  display_name      = "Inbound SMS Messages"
  kms_master_key_id = "alias/aws/sns"

  tags = local.tags
}

# SNS topic policy
resource "aws_sns_topic_policy" "sms_inbound" {
  arn = aws_sns_topic.sms_inbound.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowSMSPublish"
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

# Associate phone number with SNS topic for inbound messages
resource "aws_pinpointsmsvoicev2_phone_number_association" "sns" {
  phone_number_id = aws_pinpointsmsvoicev2_phone_number.main.id

  # Two-way configuration
  # Note: This must be configured via AWS Console or CLI after phone number is provisioned
  # The association with SNS topic for inbound messages happens through the console
  depends_on = [
    aws_sns_topic.sms_inbound,
    aws_pinpointsmsvoicev2_phone_number.main
  ]
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

  point_in_time_recovery {
    enabled = var.environment == "prod" ? true : false
  }

  tags = merge(
    local.tags,
    {
      Name = "${local.project_name}-sms-consent-${var.environment}"
    }
  )
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

  point_in_time_recovery {
    enabled = var.environment == "prod" ? true : false
  }

  tags = merge(
    local.tags,
    {
      Name = "${local.project_name}-opt-out-tracking-${var.environment}"
    }
  )
}

# SMS Messages Table (for audit trail)
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

  point_in_time_recovery {
    enabled = var.environment == "prod" ? true : false
  }

  tags = merge(
    local.tags,
    {
      Name = "${local.project_name}-sms-messages-${var.environment}"
    }
  )
}

# SMS Sessions Table (for conversation state)
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

  tags = merge(
    local.tags,
    {
      Name = "${local.project_name}-sms-sessions-${var.environment}"
    }
  )
}

#==============================================================================
# Lambda Functions
#==============================================================================

# Lambda execution role
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

# Lambda basic execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_sms.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Lambda SMS permissions policy
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
          "bedrock-agent-runtime:InvokeAgent"
        ]
        Resource = "arn:aws:bedrock:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:agent/*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.sms_inbound.arn
      }
    ]
  })
}

# Inbound SMS Processor Lambda
resource "aws_lambda_function" "sms_inbound_processor" {
  filename      = "${path.module}/../../../lambda/sms-inbound-processor/lambda.zip"
  function_name = "${local.project_name}-sms-inbound-${var.environment}"
  role          = aws_iam_role.lambda_sms.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 512

  environment {
    variables = {
      ENVIRONMENT             = var.environment
      SUPERVISOR_AGENT_ID     = var.supervisor_agent_id
      SUPERVISOR_ALIAS_ID     = var.supervisor_alias_id
      ORIGINATION_NUMBER      = aws_pinpointsmsvoicev2_phone_number.main.phone_number
      CONSENT_TABLE           = aws_dynamodb_table.sms_consent.name
      OPT_OUT_TRACKING_TABLE  = aws_dynamodb_table.opt_out_tracking.name
      MESSAGES_TABLE          = aws_dynamodb_table.sms_messages.name
      SESSIONS_TABLE          = aws_dynamodb_table.sms_sessions.name
      AWS_REGION_NAME         = data.aws_region.current.name
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy.lambda_sms_permissions
  ]

  tags = merge(
    local.tags,
    {
      Name = "${local.project_name}-sms-inbound-${var.environment}"
    }
  )
}

# SNS subscription for inbound messages
resource "aws_sns_topic_subscription" "sms_inbound_lambda" {
  topic_arn = aws_sns_topic.sms_inbound.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.sms_inbound_processor.arn
}

# Lambda permission for SNS to invoke
resource "aws_lambda_permission" "sns_invoke" {
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sms_inbound_processor.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.sms_inbound.arn
}

# CloudWatch log group for Lambda
resource "aws_cloudwatch_log_group" "lambda_sms_inbound" {
  name              = "/aws/lambda/${aws_lambda_function.sms_inbound_processor.function_name}"
  retention_in_days = 30

  tags = local.tags
}
