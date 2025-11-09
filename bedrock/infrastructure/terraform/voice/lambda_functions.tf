# ============================================================================
# Lambda Functions for Voice Integration (Phase 3)
# ============================================================================

data "aws_caller_identity" "current" {}

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
      DYNAMODB_TABLE       = var.dynamodb_table_name
      INFORMATION_LAMBDA   = "${var.prefix}-information-actions"
      VOICE_BRIDGE_LAMBDA  = "${var.prefix}-voice-bedrock-bridge-${var.environment}"
    }
  }

  tags = {
    Name        = "${var.prefix}-lex-fulfillment-${var.environment}"
    Environment = var.environment
    Phase       = "3"
  }
}

# CloudWatch Log Group for Lex Fulfillment
resource "aws_cloudwatch_log_group" "lex_fulfillment" {
  name              = "/aws/lambda/${aws_lambda_function.lex_fulfillment.function_name}"
  retention_in_days = 14

  tags = {
    Name        = "${var.prefix}-lex-fulfillment-logs-${var.environment}"
    Environment = var.environment
  }
}

# IAM Role for Lex Fulfillment
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

# IAM Policy for Lex Fulfillment
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
          "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${var.prefix}-information-actions",
          "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${var.prefix}-voice-bedrock-bridge-${var.environment}"
        ]
      }
    ]
  })
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
  timeout          = 120  # Longer timeout for Bedrock calls
  memory_size      = 512

  environment {
    variables = {
      SUPERVISOR_AGENT_ID       = var.supervisor_agent_id
      SUPERVISOR_AGENT_ALIAS_ID = var.supervisor_agent_alias_id
      DYNAMODB_TABLE            = var.dynamodb_table_name
    }
  }

  tags = {
    Name        = "${var.prefix}-voice-bedrock-bridge-${var.environment}"
    Environment = var.environment
    Phase       = "3"
  }
}

# CloudWatch Log Group for Voice-Bedrock Bridge
resource "aws_cloudwatch_log_group" "voice_bedrock_bridge" {
  name              = "/aws/lambda/${aws_lambda_function.voice_bedrock_bridge.function_name}"
  retention_in_days = 14

  tags = {
    Name        = "${var.prefix}-voice-bridge-logs-${var.environment}"
    Environment = var.environment
  }
}

# IAM Role for Voice-Bedrock Bridge
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

# IAM Policy for Voice-Bedrock Bridge
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
        Resource = "arn:aws:bedrock:${var.region}:${data.aws_caller_identity.current.account_id}:agent/${var.supervisor_agent_id}"
      }
    ]
  })
}

# ============================================================================
# Lambda Permissions for Connect
# ============================================================================

resource "aws_lambda_permission" "lex_fulfillment_connect" {
  statement_id  = "AllowExecutionFromConnect"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lex_fulfillment.function_name
  principal     = "connect.amazonaws.com"
  source_arn    = aws_connect_instance.main.arn
}

resource "aws_lambda_permission" "voice_bridge_connect" {
  statement_id  = "AllowExecutionFromConnect"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.voice_bedrock_bridge.function_name
  principal     = "connect.amazonaws.com"
  source_arn    = aws_connect_instance.main.arn
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
