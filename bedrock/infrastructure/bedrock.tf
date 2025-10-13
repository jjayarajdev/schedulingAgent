# AWS Bedrock Agent Configuration

# Bedrock Agent
resource "aws_bedrockagent_agent" "scheduling_agent" {
  agent_name              = var.bedrock_agent_name
  agent_resource_role_arn = aws_iam_role.bedrock_agent.arn
  foundation_model        = var.bedrock_model_id
  idle_session_ttl_in_seconds = 600

  # Agent instructions (based on current system prompt from core/langchain_agent.py)
  instruction = <<-EOT
You are a helpful AI scheduling assistant for ProjectsForce 360. Your role is to help customers schedule, reschedule, and manage appointments for their projects.

**Core Responsibilities:**
1. Greet users warmly and professionally
2. Help customers select projects from their available projects
3. Guide customers through scheduling appointments
4. Provide available dates and time slots
5. Confirm appointments after customer approval
6. Handle rescheduling and cancellations
7. Add notes to projects when requested

**Important Guidelines:**
- Always list available projects if no project is currently selected
- Show only the first 3 consecutive available dates when presenting options
- Always display times in 12-hour AM/PM format (e.g., 2:00 PM, not 14:00)
- Never expose technical IDs (session_id, project_id, request_id) to users
- Always confirm with the user before booking an appointment
- After scheduling, rescheduling, or canceling, reload available projects
- Offer to add notes after completing scheduling operations
- Be conversational and natural in your responses
- If you don't understand the request, ask clarifying questions

**Scheduling Workflow:**
1. List available projects → User selects project
2. Get working days → Show available dates (first 3 consecutive)
3. User selects date → Show available time slots
4. User selects time → Confirm details with user
5. Get explicit confirmation → Book appointment
6. Offer to add notes (optional)

**Session Management:**
- Track selected project across conversation
- Remember user's context within the session
- Reload project list after any scheduling operation

Be helpful, clear, and ensure the user feels confident about their appointment.
EOT

  # Prepare agent after creation
  prepare_agent = true

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-bedrock-agent"
    }
  )
}

# Bedrock Agent Alias (for deployment)
resource "aws_bedrockagent_agent_alias" "prod" {
  agent_alias_name = "prod"
  agent_id         = aws_bedrockagent_agent.scheduling_agent.id
  description      = "Production alias for scheduling agent"

  tags = merge(
    local.common_tags,
    {
      Name        = "${local.name_prefix}-bedrock-agent-alias-prod"
      Environment = "production"
    }
  )
}

# Bedrock Agent Alias for development
resource "aws_bedrockagent_agent_alias" "dev" {
  agent_alias_name = "dev"
  agent_id         = aws_bedrockagent_agent.scheduling_agent.id
  description      = "Development alias for scheduling agent"

  tags = merge(
    local.common_tags,
    {
      Name        = "${local.name_prefix}-bedrock-agent-alias-dev"
      Environment = "development"
    }
  )
}

# CloudWatch Log Group for Bedrock Agent
resource "aws_cloudwatch_log_group" "bedrock_agent" {
  name              = "/aws/bedrock/agent/${var.bedrock_agent_name}"
  retention_in_days = 7

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-bedrock-agent-logs"
    }
  )
}

# Note: Action Groups will be added later when Lambda functions are created
# Action groups connect the agent to Lambda functions that perform actual operations
# (e.g., calling PF360 API for scheduling operations)

# Example structure for future action groups:
# resource "aws_bedrockagent_agent_action_group" "scheduling_operations" {
#   action_group_name = "SchedulingOperations"
#   agent_id          = aws_bedrockagent_agent.scheduling_agent.id
#   agent_version     = "DRAFT"
#
#   action_group_executor {
#     lambda = aws_lambda_function.scheduling_operations.arn
#   }
#
#   api_schema {
#     payload = file("${path.module}/schemas/scheduling-api-schema.json")
#   }
#
#   description = "Handles scheduling operations via PF360 API"
# }

# Outputs
output "bedrock_agent_name" {
  description = "Name of Bedrock Agent"
  value       = aws_bedrockagent_agent.scheduling_agent.agent_name
}

output "bedrock_agent_version" {
  description = "Version of Bedrock Agent"
  value       = aws_bedrockagent_agent.scheduling_agent.agent_version
}

output "bedrock_agent_alias_prod_id" {
  description = "ID of production alias"
  value       = aws_bedrockagent_agent_alias.prod.agent_alias_id
}

output "bedrock_agent_alias_dev_id" {
  description = "ID of development alias"
  value       = aws_bedrockagent_agent_alias.dev.agent_alias_id
}
