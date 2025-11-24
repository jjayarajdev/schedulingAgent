#!/usr/bin/env python3
"""
Configure Action Groups - Automated Setup
Uncomments action group resources in bedrock_agents.tf
"""

import re
import sys

def uncomment_action_groups():
    """Uncomment action group resources in bedrock_agents.tf"""

    tf_file = 'bedrock_agents.tf'

    print("🔧 Configuring Action Groups...")
    print(f"   Reading {tf_file}...")

    try:
        with open(tf_file, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ Error: {tf_file} not found")
        print("   Make sure you're in the terraform directory")
        sys.exit(1)

    # Check if already uncommented
    if 'resource "aws_bedrockagent_agent_action_group" "scheduling_actions"' in content and \
       not content.count('# resource "aws_bedrockagent_agent_action_group" "scheduling_actions"'):
        print("✅ Action groups already uncommented")
        return True

    original_content = content

    # Find the action groups section
    action_groups_section_start = content.find("# Action Groups (Placeholder")
    if action_groups_section_start == -1:
        print("❌ Could not find Action Groups section")
        sys.exit(1)

    # Find the section with commented action groups
    # Look for the pattern: # resource "aws_bedrockagent_agent_action_group" "scheduling_actions"

    # Replace the example comment block with actual resource definitions
    example_pattern = r'# Example structure \(to be uncommented when Lambda functions exist\):.*?# # \}'

    action_groups_code = '''
# Scheduling Action Group
resource "aws_bedrockagent_agent_action_group" "scheduling_actions" {
  agent_id              = aws_bedrockagent_agent.scheduling.agent_id
  agent_version         = "DRAFT"
  action_group_name     = "scheduling-actions"
  description           = "Actions for appointment scheduling and availability"

  action_group_executor {
    lambda = var.scheduling_lambda_arn
  }

  api_schema {
    s3 {
      s3_bucket_name = aws_s3_bucket.agent_schemas.id
      s3_object_key  = aws_s3_object.scheduling_actions_schema.key
    }
  }

  depends_on = [
    aws_bedrockagent_agent.scheduling
  ]
}

# Information Action Group
resource "aws_bedrockagent_agent_action_group" "information_actions" {
  agent_id              = aws_bedrockagent_agent.information.agent_id
  agent_version         = "DRAFT"
  action_group_name     = "information-actions"
  description           = "Actions for project information and status"

  action_group_executor {
    lambda = var.information_lambda_arn
  }

  api_schema {
    s3 {
      s3_bucket_name = aws_s3_bucket.agent_schemas.id
      s3_object_key  = aws_s3_object.information_actions_schema.key
    }
  }

  depends_on = [
    aws_bedrockagent_agent.information
  ]
}

# Notes Action Group
resource "aws_bedrockagent_agent_action_group" "notes_actions" {
  agent_id              = aws_bedrockagent_agent.notes.agent_id
  agent_version         = "DRAFT"
  action_group_name     = "notes-actions"
  description           = "Actions for managing appointment notes"

  action_group_executor {
    lambda = var.notes_lambda_arn
  }

  api_schema {
    s3 {
      s3_bucket_name = aws_s3_bucket.agent_schemas.id
      s3_object_key  = aws_s3_object.notes_actions_schema.key
    }
  }

  depends_on = [
    aws_bedrockagent_agent.notes
  ]
}
'''

    # Find and replace the example section
    content = re.sub(example_pattern, action_groups_code, content, flags=re.DOTALL)

    # Backup original file
    backup_file = f"{tf_file}.backup_action_groups"
    with open(backup_file, 'w') as f:
        f.write(original_content)
    print(f"✅ Backed up original to {backup_file}")

    # Write updated content
    with open(tf_file, 'w') as f:
        f.write(content)

    print("✅ Action groups uncommented successfully")
    print("\n📋 Added action groups:")
    print("   • scheduling_actions")
    print("   • information_actions")
    print("   • notes_actions")

    return True

if __name__ == "__main__":
    print("=" * 80)
    print("Action Groups Configuration Script")
    print("=" * 80)
    print()

    try:
        uncomment_action_groups()
        print()
        print("=" * 80)
        print("✅ Configuration complete!")
        print("=" * 80)
        print()
        print("Next steps:")
        print("  1. Verify changes: git diff bedrock_agents.tf")
        print("  2. Run: terraform plan")
        print("  3. Run: terraform apply")
        print()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
