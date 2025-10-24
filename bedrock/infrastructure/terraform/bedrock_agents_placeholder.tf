# This file temporarily replaces agent alias resources for Stage 1 deployment
# Agent aliases will be created in Stage 3 after agents are prepared

# Placeholder outputs to prevent Terraform errors
output "supervisor_alias_id_pending" {
  description = "Supervisor alias will be created in Stage 3"
  value       = "PENDING_STAGE_3"
}

output "supervisor_alias_arn_pending" {
  description = "Supervisor alias will be created in Stage 3"
  value       = "PENDING_STAGE_3"
}
