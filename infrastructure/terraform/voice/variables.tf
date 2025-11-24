# ============================================================================
# Terraform Variables for Voice Integration (Phase 3)
# ============================================================================

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "prefix" {
  description = "Project prefix for resource naming"
  type        = string
  default     = "pf"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "supervisor_agent_id" {
  description = "Bedrock Supervisor Agent ID"
  type        = string
}

variable "supervisor_agent_alias_id" {
  description = "Bedrock Supervisor Agent Alias ID"
  type        = string
  default     = "TSTALIASID"
}

variable "dynamodb_table_name" {
  description = "DynamoDB table name for session data"
  type        = string
  default     = "pf-session-data-dev"
}

variable "connect_phone_number" {
  description = "Phone number to associate with AWS Connect (format: +1XXXXXXXXXX)"
  type        = string
  default     = "+18005551234"  # Placeholder
}

variable "connect_instance_alias" {
  description = "Unique alias for AWS Connect instance"
  type        = string
  default     = "voice-dev"
}

variable "scheduling_agent_id" {
  description = "Bedrock Scheduling Agent ID"
  type        = string
}

variable "information_agent_id" {
  description = "Bedrock Information Agent ID"
  type        = string
}

variable "chitchat_agent_id" {
  description = "Bedrock ChitChat Agent ID"
  type        = string
}

variable "lex_bot_name" {
  description = "Name for the Lex bot"
  type        = string
  default     = "pf-scheduling-assistant-dev"
}

variable "lex_voice_id" {
  description = "Amazon Polly voice ID for Lex bot"
  type        = string
  default     = "Joanna"
}
