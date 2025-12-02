# Outputs for AWS End User Messaging SMS Infrastructure

#==============================================================================
# Note: Phone number, opt-out list, and configuration set are managed
# by deploy_sms_config_setup.sh script, not by Terraform
#==============================================================================

#==============================================================================
# SNS Topic
#==============================================================================

output "sns_inbound_topic_arn" {
  description = "SNS topic ARN for inbound messages"
  value       = aws_sns_topic.sms_inbound.arn
}

output "sns_inbound_topic_name" {
  description = "SNS topic name for inbound messages"
  value       = aws_sns_topic.sms_inbound.name
}

#==============================================================================
# DynamoDB Tables
#==============================================================================

output "consent_table_name" {
  description = "DynamoDB table name for SMS consent tracking"
  value       = aws_dynamodb_table.sms_consent.name
}

output "consent_table_arn" {
  description = "DynamoDB table ARN for SMS consent tracking"
  value       = aws_dynamodb_table.sms_consent.arn
}

output "opt_out_tracking_table_name" {
  description = "DynamoDB table name for opt-out tracking"
  value       = aws_dynamodb_table.opt_out_tracking.name
}

output "opt_out_tracking_table_arn" {
  description = "DynamoDB table ARN for opt-out tracking"
  value       = aws_dynamodb_table.opt_out_tracking.arn
}

output "messages_table_name" {
  description = "DynamoDB table name for SMS messages"
  value       = aws_dynamodb_table.sms_messages.name
}

output "messages_table_arn" {
  description = "DynamoDB table ARN for SMS messages"
  value       = aws_dynamodb_table.sms_messages.arn
}

output "sessions_table_name" {
  description = "DynamoDB table name for SMS sessions"
  value       = aws_dynamodb_table.sms_sessions.name
}

output "sessions_table_arn" {
  description = "DynamoDB table ARN for SMS sessions"
  value       = aws_dynamodb_table.sms_sessions.arn
}

#==============================================================================
# Lambda Functions
#==============================================================================

output "lambda_inbound_function_name" {
  description = "Lambda function name for inbound SMS processing"
  value       = aws_lambda_function.sms_inbound_processor.function_name
}

output "lambda_inbound_function_arn" {
  description = "Lambda function ARN for inbound SMS processing"
  value       = aws_lambda_function.sms_inbound_processor.arn
}

output "lambda_role_arn" {
  description = "IAM role ARN for Lambda SMS functions"
  value       = aws_iam_role.lambda_sms.arn
}

#==============================================================================
# CloudWatch Logs
#==============================================================================

output "lambda_log_group" {
  description = "CloudWatch log group for Lambda function"
  value       = aws_cloudwatch_log_group.lambda_sms_inbound.name
}

#==============================================================================
# Environment Summary
#==============================================================================

output "environment_summary" {
  description = "Summary of deployed SMS infrastructure"
  value = {
    environment     = var.environment
    region          = data.aws_region.current.name
    account_id      = data.aws_caller_identity.current.account_id
    tables_deployed = 4
    lambda_deployed = 1
  }
}
