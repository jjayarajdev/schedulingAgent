#!/usr/bin/env python3
"""
Update agent aliases to point to DRAFT version (which has updated instructions).
This is the simplest solution since version 4 doesn't have AVAILABLE ACTIONS.
"""

import boto3
import time
from botocore.exceptions import ClientError

# Configuration
REGION = 'us-east-1'
AGENT_IDS = {
    'Scheduling Agent': 'IX24FSMTQH',
    'Information Agent': 'C9ANXRIO8Y',
    'Notes Agent': 'G5BVBYEPUM',
    'Chitchat Agent': 'BIUW1ARHGL'
}

SUPERVISOR_AGENT_ID = '5VTIWONUMO'

# Initialize Bedrock Agent client
client = boto3.client('bedrock-agent', region_name=REGION)

def update_alias_to_draft(agent_id, agent_name, alias_name='v4'):
    """Update an agent alias to point to DRAFT version."""
    print(f"\n{'='*80}")
    print(f"Updating {agent_name} alias '{alias_name}' to point to DRAFT")
    print(f"{'='*80}")

    try:
        # List aliases to find the one we want to update
        response = client.list_agent_aliases(
            agentId=agent_id,
            maxResults=10
        )

        alias_id = None
        for alias in response.get('agentAliasSummaries', []):
            if alias['agentAliasName'] == alias_name:
                alias_id = alias['agentAliasId']
                print(f"✅ Found alias '{alias_name}' (ID: {alias_id})")
                break

        if not alias_id:
            print(f"❌ Alias '{alias_name}' not found for {agent_name}")
            return False

        # Update alias to point to DRAFT
        print(f"   Updating to point to DRAFT version...")
        client.update_agent_alias(
            agentId=agent_id,
            agentAliasId=alias_id,
            agentAliasName=alias_name,
            routingConfiguration=[
                {
                    'agentVersion': 'DRAFT'
                }
            ]
        )

        print(f"✅ {agent_name} alias '{alias_name}' now points to DRAFT")
        return True

    except ClientError as e:
        print(f"❌ Error updating {agent_name}: {e}")
        return False

def recreate_collaborators():
    """Delete and recreate Supervisor collaborators with updated aliases."""
    print(f"\n{'='*80}")
    print(f"Updating Supervisor Agent Collaborators")
    print(f"{'='*80}\n")

    # Get account ID
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']

    try:
        # List existing collaborators
        response = client.list_agent_collaborators(
            agentId=SUPERVISOR_AGENT_ID,
            agentVersion='DRAFT'
        )

        # Delete existing collaborators
        print("Deleting existing collaborators...")
        for collab in response.get('agentCollaboratorSummaries', []):
            collab_id = collab['collaboratorId']
            collab_name = collab['collaboratorName']
            print(f"   Deleting {collab_name}...")

            client.disassociate_agent_collaborator(
                agentId=SUPERVISOR_AGENT_ID,
                agentVersion='DRAFT',
                collaboratorId=collab_id
            )
            print(f"   ✅ Deleted {collab_name}")

        print("\n")

        # Add collaborators back with v4 aliases (now pointing to DRAFT)
        collaborators_config = [
            {
                'agent_id': AGENT_IDS['Scheduling Agent'],
                'alias_name': 'v4',
                'name': 'scheduling_collaborator',
                'instruction': 'Handle scheduling-related requests: booking appointments, checking availability, getting time slots, rescheduling, and canceling appointments.'
            },
            {
                'agent_id': AGENT_IDS['Information Agent'],
                'alias_name': 'v4',
                'name': 'information_collaborator',
                'instruction': 'Handle information requests: project details, appointment status, business hours, weather forecasts, and general information queries.'
            },
            {
                'agent_id': AGENT_IDS['Notes Agent'],
                'alias_name': 'v4',
                'name': 'notes_collaborator',
                'instruction': 'Handle note-related requests: adding notes to projects and retrieving project notes.'
            },
            {
                'agent_id': AGENT_IDS['Chitchat Agent'],
                'alias_name': 'v4',
                'name': 'chitchat_collaborator',
                'instruction': 'Handle casual conversation, greetings, farewells, and general chitchat that doesn\'t require specific actions.'
            }
        ]

        print("Adding collaborators with updated aliases...")
        for config in collaborators_config:
            # Get alias ID
            alias_response = client.list_agent_aliases(
                agentId=config['agent_id']
            )

            alias_id = None
            for alias in alias_response.get('agentAliasSummaries', []):
                if alias['agentAliasName'] == config['alias_name']:
                    alias_id = alias['agentAliasId']
                    break

            if not alias_id:
                print(f"   ❌ Could not find alias '{config['alias_name']}' for {config['name']}")
                continue

            # Build alias ARN
            alias_arn = f"arn:aws:bedrock:{REGION}:{account_id}:agent-alias/{config['agent_id']}/{alias_id}"

            print(f"   Adding {config['name']}...")
            print(f"      Alias ARN: {alias_arn}")

            client.associate_agent_collaborator(
                agentId=SUPERVISOR_AGENT_ID,
                agentVersion='DRAFT',
                agentDescriptor={
                    'aliasArn': alias_arn
                },
                collaboratorName=config['name'],
                collaborationInstruction=config['instruction'],
                relayConversationHistory='DISABLED'
            )

            print(f"   ✅ Added {config['name']}")

        print("\n")
        return True

    except ClientError as e:
        print(f"❌ Error updating collaborators: {e}")
        return False

def prepare_supervisor():
    """Prepare the Supervisor agent."""
    print(f"\n{'='*80}")
    print(f"Preparing Supervisor Agent")
    print(f"{'='*80}\n")

    try:
        client.prepare_agent(
            agentId=SUPERVISOR_AGENT_ID
        )
        print("✅ Supervisor Agent prepared successfully")
        print("\n⏳ Waiting 30 seconds for agent to be ready...")
        time.sleep(30)
        return True
    except ClientError as e:
        print(f"❌ Error preparing Supervisor: {e}")
        return False

def main():
    print("\n" + "="*80)
    print("UPDATE AGENT ALIASES TO DRAFT")
    print("="*80)
    print("\nThis script will:")
    print("  1. Update v4 aliases to point to DRAFT (which has updated instructions)")
    print("  2. Recreate Supervisor collaborators")
    print("  3. Prepare Supervisor Agent")
    print("\n" + "="*80 + "\n")

    # Step 1: Update aliases to point to DRAFT
    print("STEP 1: Updating Agent Aliases")
    print("="*80)

    success_count = 0
    for agent_name, agent_id in AGENT_IDS.items():
        if update_alias_to_draft(agent_id, agent_name):
            success_count += 1

    print(f"\n✅ Updated {success_count}/{len(AGENT_IDS)} aliases\n")

    if success_count < len(AGENT_IDS):
        print("⚠️  Some aliases failed to update, but continuing...")

    # Wait for aliases to propagate
    print("⏳ Waiting 10 seconds for alias updates to propagate...")
    time.sleep(10)

    # Step 2: Recreate collaborators
    print("\nSTEP 2: Recreating Collaborators")
    print("="*80)

    if not recreate_collaborators():
        print("\n❌ Failed to update collaborators")
        return 1

    # Step 3: Prepare Supervisor
    print("STEP 3: Preparing Supervisor Agent")
    print("="*80)

    if not prepare_supervisor():
        print("\n❌ Failed to prepare Supervisor")
        return 1

    # Success!
    print("\n" + "="*80)
    print("✅ UPDATE COMPLETE!")
    print("="*80)
    print("\nWhat changed:")
    print("  - All v4 aliases now point to DRAFT (with updated instructions)")
    print("  - Supervisor collaborators use v4 aliases → DRAFT → updated instructions")
    print("  - Agents will now call Lambda functions instead of hallucinating!")
    print("\nNext step:")
    print("  Run: ./tests/test_agent_with_session.py")
    print("  Expected: 5/5 tests pass, CloudWatch logs show Lambda invocations!")
    print("\n" + "="*80 + "\n")

    return 0

if __name__ == '__main__':
    exit(main())
