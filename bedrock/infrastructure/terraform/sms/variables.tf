# Variables for AWS End User Messaging SMS Infrastructure

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "supervisor_agent_id" {
  description = "Bedrock Supervisor Agent ID"
  type        = string
  default     = "5VTIWONUMO"
}

variable "supervisor_alias_id" {
  description = "Bedrock Supervisor Agent Alias ID"
  type        = string
  default     = "HH2U7EZXMW"
}

variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "phone_number_deletion_protection" {
  description = "Enable deletion protection for phone number (recommended for prod)"
  type        = bool
  default     = false
}

variable "sms_cloudwatch_retention_days" {
  description = "CloudWatch logs retention period in days"
  type        = number
  default     = 30

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.sms_cloudwatch_retention_days)
    error_message = "Must be a valid CloudWatch retention period."
  }
}

variable "lambda_memory_size" {
  description = "Memory size for Lambda functions in MB"
  type        = number
  default     = 512

  validation {
    condition     = var.lambda_memory_size >= 128 && var.lambda_memory_size <= 10240
    error_message = "Lambda memory must be between 128 MB and 10240 MB."
  }
}

variable "lambda_timeout" {
  description = "Timeout for Lambda functions in seconds"
  type        = number
  default     = 30

  validation {
    condition     = var.lambda_timeout >= 3 && var.lambda_timeout <= 900
    error_message = "Lambda timeout must be between 3 and 900 seconds."
  }
}

variable "enable_point_in_time_recovery" {
  description = "Enable point-in-time recovery for DynamoDB tables (recommended for prod)"
  type        = bool
  default     = false
}

variable "sms_session_ttl_hours" {
  description = "TTL for SMS sessions in hours"
  type        = number
  default     = 24
}

variable "sms_message_retention_days" {
  description = "Retention period for SMS messages in DynamoDB (days)"
  type        = number
  default     = 1460 # 4 years for compliance
}

variable "tcpa_opt_out_deadline_days" {
  description = "Days to honor opt-out request (TCPA 2025 requirement)"
  type        = number
  default     = 10

  validation {
    condition     = var.tcpa_opt_out_deadline_days <= 10
    error_message = "TCPA 2025 requires opt-out processing within 10 business days."
  }
}
