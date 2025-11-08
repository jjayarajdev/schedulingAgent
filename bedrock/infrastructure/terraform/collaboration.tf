#############################
# Multi-agent Collaboration
#############################
#
# This module uses Terraform to manage AWS Bedrock multi-agent collaboration
# using the aws_bedrockagent_agent_collaborator resource.
#
# PREREQUISITES:
# 1. All 4 agents must exist (Supervisor + 3 collaborators)
# 2. Each collaborator agent must have a VERSION created (v1)
# 3. Each collaborator agent must have an ALIAS (v1) pointing to that version
#
# NOTE: Steps 2-3 currently require AWS Console (one-time setup, ~15 minutes)
#       See: ../ENABLE_COLLABORATION.md for detailed instructions
#
# Once v1 aliases exist, this Terraform config will:
# - Associate the 3 collaborator agents with the Supervisor
# - Configure conversation history relay
# - Automatically prepare the Supervisor agent
#
#############################

# Local variables for agent IDs (from bedrock_agents.tf outputs)
locals {
  supervisor_id  = aws_bedrockagent_agent.supervisor.agent_id
  scheduling_id  = aws_bedrockagent_agent.scheduling.agent_id
  information_id = aws_bedrockagent_agent.information.agent_id
  chitchat_id    = aws_bedrockagent_agent.chitchat.agent_id

  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name
}

#############################
# Collaboration Resources
#############################

# Associate Scheduling Agent as collaborator
resource "aws_bedrockagent_agent_collaborator" "scheduling" {
  # Prevent creation until v1 aliases exist
  # Comment out this block when v1 aliases are created via Console
  # lifecycle {
  #   prevent_destroy = true
  # }

  agent_id               = local.supervisor_id
  agent_version          = "DRAFT"
  collaborator_name      = "SchedulingAgent"
  relay_conversation_history = "TO_COLLABORATOR"

  # Collaboration instructions - how supervisor should route to this agent
  collaboration_instruction = "Route queries about projects, appointments, scheduling, availability, and booking to this agent. Examples: 'List my projects', 'Book an appointment', 'What dates are available?'"

  agent_descriptor {
    # This ARN must point to a v1 alias (not TSTALIASID)
    # Format: arn:aws:bedrock:REGION:ACCOUNT:agent-alias/AGENT_ID/V1_ALIAS_ID
    # Replace V1_ALIAS_ID with actual alias ID from Console
    alias_arn = "arn:aws:bedrock:${local.region}:${local.account_id}:agent-alias/${local.scheduling_id}/V1_ALIAS_ID_HERE"
  }
}

# Associate Information Agent as collaborator
resource "aws_bedrockagent_agent_collaborator" "information" {
  agent_id               = local.supervisor_id
  agent_version          = "DRAFT"
  collaborator_name      = "InformationAgent"
  relay_conversation_history = "TO_COLLABORATOR"

  collaboration_instruction = "Route queries about weather, project details, appointment status, and general information lookup to this agent. Examples: 'What's the weather in New York?', 'Get project details', 'Check appointment status'."

  agent_descriptor {
    alias_arn = "arn:aws:bedrock:${local.region}:${local.account_id}:agent-alias/${local.information_id}/V1_ALIAS_ID_HERE"
  }
}

# Associate Chitchat Agent as collaborator
resource "aws_bedrockagent_agent_collaborator" "chitchat" {
  agent_id               = local.supervisor_id
  agent_version          = "DRAFT"
  collaborator_name      = "ChitchatAgent"
  relay_conversation_history = "TO_COLLABORATOR"

  collaboration_instruction = "Route greetings, casual conversation, thank you messages, and general pleasantries to this agent. Examples: 'Hello', 'Hi there', 'Thank you', 'Good morning'."

  agent_descriptor {
    alias_arn = "arn:aws:bedrock:${local.region}:${local.account_id}:agent-alias/${local.chitchat_id}/V1_ALIAS_ID_HERE"
  }
}

#############################
# Outputs
#############################

output "collaboration_status" {
  description = "Status of agent collaboration configuration"
  value = {
    supervisor_id = local.supervisor_id
    collaborators = {
      scheduling  = aws_bedrockagent_agent_collaborator.scheduling.collaborator_name
      information = aws_bedrockagent_agent_collaborator.information.collaborator_name
      chitchat    = aws_bedrockagent_agent_collaborator.chitchat.collaborator_name
    }
  }
}

output "collaboration_alias_arns" {
  description = "Alias ARNs used for collaboration (for verification)"
  value = {
    scheduling  = aws_bedrockagent_agent_collaborator.scheduling.agent_descriptor[0].alias_arn
    information = aws_bedrockagent_agent_collaborator.information.agent_descriptor[0].alias_arn
    chitchat    = aws_bedrockagent_agent_collaborator.chitchat.agent_descriptor[0].alias_arn
  }
}

#############################
# Instructions for Use
#############################
#
# STEP 1: Create v1 aliases via AWS Console
#   Follow: ../ENABLE_COLLABORATION.md
#   This creates Version 1 and v1 alias for each collaborator agent
#
# STEP 2: Get v1 alias IDs
#   Run: ../scripts/find_v1_alias_ids.sh
#   This will output the 10-character alias IDs
#
# STEP 3: Update this file
#   Replace "V1_ALIAS_ID_HERE" with actual alias IDs in all 3 resources above
#
# STEP 4: Apply Terraform
#   terraform plan
#   terraform apply
#
# STEP 5: Verify
#   Run: ../scripts/verify_collaborators.sh
#
#############################
