# Outputs for AWS End User Messaging SMS Infrastructure

#==============================================================================
# Phone Number
#==============================================================================

output "phone_number" {
  description = "Provisioned toll-free phone number"
  value       = aws_pinpointsmsvoicev2_phone_number.main.phone_number
}

output "phone_number_id" {
  description = "Phone number ID for API operations"
  value       = aws_pinpointsmsvoicev2_phone_number.main.id
}

output "phone_number_arn" {
  description = "Phone number ARN"
  value       = aws_pinpointsmsvoicev2_phone_number.main.arn
}

#==============================================================================
# Opt-Out List
#==============================================================================

output "opt_out_list_name" {
  description = "Opt-out list name"
  value       = aws_pinpointsmsvoicev2_opt_out_list.main.opt_out_list_name
}

output "opt_out_list_arn" {
  description = "Opt-out list ARN"
  value       = aws_pinpointsmsvoicev2_opt_out_list.main.arn
}

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

output "sms_events_log_group" {
  description = "CloudWatch log group for SMS events"
  value       = aws_cloudwatch_log_group.sms_events.name
}

output "lambda_log_group" {
  description = "CloudWatch log group for Lambda function"
  value       = aws_cloudwatch_log_group.lambda_sms_inbound.name
}

#==============================================================================
# Configuration
#==============================================================================

output "configuration_set_name" {
  description = "SMS configuration set name"
  value       = aws_pinpointsmsvoicev2_configuration_set.main.name
}

#==============================================================================
# Environment Summary
#==============================================================================

output "environment_summary" {
  description = "Summary of deployed SMS infrastructure"
  value = {
    environment      = var.environment
    phone_number     = aws_pinpointsmsvoicev2_phone_number.main.phone_number
    region           = data.aws_region.current.name
    account_id       = data.aws_caller_identity.current.account_id
    supervisor_agent = var.supervisor_agent_id
    tables_deployed  = 4
    lambda_deployed  = 1
  }
}
