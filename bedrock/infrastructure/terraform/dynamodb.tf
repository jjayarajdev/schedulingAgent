# ==============================================================================
# DynamoDB Tables for Session Storage
# ==============================================================================
# This configuration creates DynamoDB table for managing:
# - Session state (customer_id, client_id, auth_token, request_id)
# - Multi-step scheduling flow state
# - TTL enabled for automatic cleanup after 30 minutes
# ==============================================================================

# DynamoDB table for session storage
resource "aws_dynamodb_table" "bedrock_sessions" {
  name         = "${var.project_name}-sessions-${var.environment}"
  billing_mode = "PAY_PER_REQUEST" # On-demand pricing for flexible scaling
  hash_key     = "session_id"

  # Primary key
  attribute {
    name = "session_id"
    type = "S"
  }

  # Global Secondary Index for customer_id lookups
  attribute {
    name = "customer_id"
    type = "S"
  }

  global_secondary_index {
    name            = "customer_id-index"
    hash_key        = "customer_id"
    projection_type = "ALL"
  }

  # TTL configuration - automatically delete sessions after 30 minutes
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Point-in-time recovery for production
  point_in_time_recovery {
    enabled = var.environment == "prod" ? true : false
  }

  # Server-side encryption (uses AWS-managed keys by default)
  # Encryption is enabled by default in DynamoDB, no explicit configuration needed

  tags = {
    Name        = "${var.project_name}-sessions"
    Environment = var.environment
    Purpose     = "Bedrock Agent Session Storage"
  }
}

# ==============================================================================
# IAM Policy Document for Lambda DynamoDB Access
# ==============================================================================

data "aws_iam_policy_document" "lambda_dynamodb_access" {
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query"
    ]
    resources = [
      aws_dynamodb_table.bedrock_sessions.arn,
      "${aws_dynamodb_table.bedrock_sessions.arn}/index/*"
    ]
  }

  # CloudWatch Logs permissions for Lambda
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = [
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.project_name}-*"
    ]
  }
}

# ==============================================================================
# IAM Role for Lambda Functions
# ==============================================================================

# Trust policy for Lambda
data "aws_iam_policy_document" "lambda_trust" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

# IAM role for scheduling Lambda
resource "aws_iam_role" "scheduling_lambda" {
  name               = "${var.project_name}-scheduling-lambda-role-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json

  tags = {
    Name        = "${var.project_name}-scheduling-lambda-role"
    Environment = var.environment
  }
}

# Attach DynamoDB access policy to scheduling Lambda
resource "aws_iam_role_policy" "scheduling_lambda_dynamodb" {
  name   = "${var.project_name}-scheduling-lambda-dynamodb-policy"
  role   = aws_iam_role.scheduling_lambda.id
  policy = data.aws_iam_policy_document.lambda_dynamodb_access.json
}

# IAM role for information Lambda
resource "aws_iam_role" "information_lambda" {
  name               = "${var.project_name}-information-lambda-role-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json

  tags = {
    Name        = "${var.project_name}-information-lambda-role"
    Environment = var.environment
  }
}

# Attach DynamoDB access policy to information Lambda
resource "aws_iam_role_policy" "information_lambda_dynamodb" {
  name   = "${var.project_name}-information-lambda-dynamodb-policy"
  role   = aws_iam_role.information_lambda.id
  policy = data.aws_iam_policy_document.lambda_dynamodb_access.json
}

# IAM role for notes Lambda
resource "aws_iam_role" "notes_lambda" {
  name               = "${var.project_name}-notes-lambda-role-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json

  tags = {
    Name        = "${var.project_name}-notes-lambda-role"
    Environment = var.environment
  }
}

# Attach DynamoDB access policy to notes Lambda
resource "aws_iam_role_policy" "notes_lambda_dynamodb" {
  name   = "${var.project_name}-notes-lambda-dynamodb-policy"
  role   = aws_iam_role.notes_lambda.id
  policy = data.aws_iam_policy_document.lambda_dynamodb_access.json
}

# ==============================================================================
# Outputs
# ==============================================================================

output "dynamodb_table_name" {
  description = "Name of the DynamoDB sessions table"
  value       = aws_dynamodb_table.bedrock_sessions.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB sessions table"
  value       = aws_dynamodb_table.bedrock_sessions.arn
}

output "scheduling_lambda_role_arn" {
  description = "ARN of the scheduling Lambda IAM role"
  value       = aws_iam_role.scheduling_lambda.arn
}

output "information_lambda_role_arn" {
  description = "ARN of the information Lambda IAM role"
  value       = aws_iam_role.information_lambda.arn
}

output "notes_lambda_role_arn" {
  description = "ARN of the notes Lambda IAM role"
  value       = aws_iam_role.notes_lambda.arn
}
