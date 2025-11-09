# ============================================================================
# Terraform Variables for Voice Integration (Minimal)
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
