# ==============================================================================
# Terraform Variables
# ==============================================================================
# Variables used across all Terraform configurations
# ==============================================================================

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "pf"
}

variable "foundation_model" {
  description = "Bedrock foundation model ID"
  type        = string
  default     = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"  # Claude Sonnet 4.5
}

# ==============================================================================
# Lambda Function ARNs
# ==============================================================================

variable "scheduling_lambda_arn" {
  description = "ARN of the scheduling Lambda function"
  type        = string
  default     = ""
}

variable "information_lambda_arn" {
  description = "ARN of the information Lambda function"
  type        = string
  default     = ""
}

variable "notes_lambda_arn" {
  description = "ARN of the notes Lambda function"
  type        = string
  default     = ""
}
