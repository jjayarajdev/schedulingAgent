#!/usr/bin/env python3
"""
Update SchedulingAgent instructions and prepare agent
"""

import boto3
import sys

REGION = 'us-east-1'
AGENT_ID = 'LMJI2V9E8Y'  # SchedulingAgent
INSTRUCTIONS_FILE = '../infrastructure/agent_instructions/scheduling_collaborator.txt'

bedrock = boto3.client('bedrock-agent', region_name=REGION)
sts = boto3.client('sts')

account_id = sts.get_caller_identity()['Account']
print(f"Account ID: {account_id}")
print(f"Updating SchedulingAgent ({AGENT_ID}) instructions...")
print()

# Read the instructions
with open(INSTRUCTIONS_FILE, 'r') as f:
    instructions = f.read()

print(f"Instructions length: {len(instructions)} characters")
print()

# Update the agent
try:
    response = bedrock.update_agent(
        agentId=AGENT_ID,
        agentName='SchedulingAgent',
        instruction=instructions,
        foundationModel='us.anthropic.claude-3-5-sonnet-20241022-v2:0',
        agentResourceRoleArn=f'arn:aws:iam::{account_id}:role/AmazonBedrockExecutionRoleForAgents_SchedulingAgent'
    )

    print("✅ Agent instructions updated successfully!")
    print(f"   Status: {response['agent']['agentStatus']}")
    print()
    print("Now preparing the agent...")

    # Prepare the agent
    prepare_response = bedrock.prepare_agent(agentId=AGENT_ID)
    print(f"✅ Agent prepared! Status: {prepare_response['agentStatus']}")
    print()
    print("SchedulingAgent now has note examples in instructions!")

except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
