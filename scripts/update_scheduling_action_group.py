#!/usr/bin/env python3
"""
Update SchedulingAgent action group with Notes functionality
"""

import boto3
import json
import sys

REGION = 'us-east-1'
AGENT_ID = 'LMJI2V9E8Y'  # SchedulingAgent
ACTION_GROUP_ID = 'BBEWVIGYHU'  # scheduling-actions
SCHEMA_FILE = '../infrastructure/openapi_schemas/scheduling_actions.json'

bedrock = boto3.client('bedrock-agent', region_name=REGION)
sts = boto3.client('sts')

account_id = sts.get_caller_identity()['Account']
print(f"Account ID: {account_id}")
print(f"Updating SchedulingAgent ({AGENT_ID}) action group...")
print()

# Read the OpenAPI schema
with open(SCHEMA_FILE, 'r') as f:
    schema = json.load(f)

print(f"Schema has {len(schema.get('paths', {}))} endpoints:")
for path in schema.get('paths', {}).keys():
    print(f"  - {path}")
print()

# Update the action group
try:
    response = bedrock.update_agent_action_group(
        agentId=AGENT_ID,
        agentVersion='DRAFT',
        actionGroupId=ACTION_GROUP_ID,
        actionGroupName='scheduling-actions',
        actionGroupExecutor={
            'lambda': f'arn:aws:lambda:{REGION}:{account_id}:function:pf-scheduling-actions'
        },
        apiSchema={
            'payload': json.dumps(schema)
        }
    )

    print("✅ Action group updated successfully!")
    print(f"   State: {response['agentActionGroup']['actionGroupState']}")
    print()
    print("Now preparing the agent...")

    # Prepare the agent
    prepare_response = bedrock.prepare_agent(agentId=AGENT_ID)
    print(f"✅ Agent prepared! Status: {prepare_response['agentStatus']}")
    print()
    print("Notes functionality is now deployed to SchedulingAgent!")

except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
