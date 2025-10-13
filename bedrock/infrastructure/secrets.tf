# AWS Secrets Manager - Reference Existing Secrets

# Aurora Master Password
data "aws_secretsmanager_secret" "aurora_password" {
  name = "scheduling-agent/aurora/master-password"
}

data "aws_secretsmanager_secret_version" "aurora_password" {
  secret_id = data.aws_secretsmanager_secret.aurora_password.id
}

# JWT Secret Key
data "aws_secretsmanager_secret" "jwt_secret" {
  name = "scheduling-agent/jwt/secret-key"
}

data "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id = data.aws_secretsmanager_secret.jwt_secret.id
}

# PF360 API Credentials
data "aws_secretsmanager_secret" "pf360_credentials" {
  name = "scheduling-agent/pf360/api-credentials"
}

data "aws_secretsmanager_secret_version" "pf360_credentials" {
  secret_id = data.aws_secretsmanager_secret.pf360_credentials.id
}

# Outputs for application use
output "aurora_password_arn" {
  description = "ARN of Aurora password secret"
  value       = data.aws_secretsmanager_secret.aurora_password.arn
  sensitive   = true
}

output "jwt_secret_arn" {
  description = "ARN of JWT secret"
  value       = data.aws_secretsmanager_secret.jwt_secret.arn
  sensitive   = true
}

output "pf360_credentials_arn" {
  description = "ARN of PF360 credentials secret"
  value       = data.aws_secretsmanager_secret.pf360_credentials.arn
  sensitive   = true
}
