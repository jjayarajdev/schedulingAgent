terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "projectsforce-terraform-state-618048437522"
    key            = "scheduling-agent/bedrock/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "SchedulingAgent"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Phase       = "Phase1-Bedrock"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Local variables
locals {
  project_name = "scheduling-agent"
  name_prefix  = "${local.project_name}-${var.environment}"

  common_tags = {
    Application = "SchedulingAgent"
    Phase       = "Phase1"
    Team        = "Engineering"
  }
}
