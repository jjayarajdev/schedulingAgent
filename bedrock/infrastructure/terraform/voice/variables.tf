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
