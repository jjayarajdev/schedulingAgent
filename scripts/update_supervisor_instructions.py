#!/usr/bin/env python3
"""
Update Supervisor agent instructions and prepare agent
"""

import boto3
import sys

REGION = 'us-east-1'
AGENT_ID = 'GEMYQNPYB4'  # Supervisor
INSTRUCTIONS_FILE = '../infrastructure/agent_instructions/supervisor.txt'

bedrock = boto3.client('bedrock-agent', region_name=REGION)
sts = boto3.client('sts')

account_id = sts.get_caller_identity()['Account']
print(f"Account ID: {account_id}")
print(f"Updating Supervisor ({AGENT_ID}) instructions...")
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
        agentName='Supervisor',
        instruction=instructions,
        foundationModel='us.anthropic.claude-3-5-sonnet-20241022-v2:0',
        agentResourceRoleArn=f'arn:aws:iam::{account_id}:role/AmazonBedrockExecutionRoleForAgents_Supervisor'
    )

    print("✅ Agent instructions updated successfully!")
    print(f"   Status: {response['agent']['agentStatus']}")
    print()
    print("Now preparing the agent...")

    # Prepare the agent
    prepare_response = bedrock.prepare_agent(agentId=AGENT_ID)
    print(f"✅ Agent prepared! Status: {prepare_response['agentStatus']}")
    print()
    print("Supervisor now routes note queries to SchedulingAgent!")

except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
