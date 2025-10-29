# ============================================================================
# Terraform Provider Configuration for Voice Integration
# ============================================================================

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = "ProjectForce"
      ManagedBy   = "Terraform"
      Phase       = "3"
      Environment = var.environment
    }
  }
}
