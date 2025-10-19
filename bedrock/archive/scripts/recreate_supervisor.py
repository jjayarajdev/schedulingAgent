#!/usr/bin/env python3
"""
Recreate Supervisor Agent with proper collaborator configuration.
Individual agents work, so we just need to fix the Supervisor routing.
"""

import boto3
import time
import json
from botocore.exceptions import ClientError

# Configuration
REGION = 'us-east-1'
SUPERVISOR_AGENT_ID = '5VTIWONUMO'

# Specialist agents (these work individually!)
SPECIALIST_AGENTS = {
    'scheduling': {
        'id': 'IX24FSMTQH',
        'name': 'scheduling_collaborator',
        'instruction': 'Handle scheduling-related requests: booking appointments, checking availability, getting time slots, rescheduling, and canceling appointments. ALWAYS use the available actions to retrieve real data from the system.'
    },
    'information': {
        'id': 'C9ANXRIO8Y',
        'name': 'information_collaborator',
        'instruction': 'Handle information requests: project details, appointment status, business hours, weather forecasts, and general information queries. ALWAYS use the available actions to retrieve real data from the system.'
    },
    'notes': {
        'id': 'G5BVBYEPUM',
        'name': 'notes_collaborator',
        'instruction': 'Handle note-related requests: adding notes to projects and retrieving project notes. ALWAYS use the available actions to interact with the notes system.'
    },
    'chitchat': {
        'id': 'BIUW1ARHGL',
        'name': 'chitchat_collaborator',
        'instruction': 'Handle casual conversation, greetings, farewells, and general chitchat that doesn\'t require specific actions.'
    }
}

# Initialize clients
bedrock_client = boto3.client('bedrock-agent', region_name=REGION)
sts_client = boto3.client('sts')

def get_account_id():
    """Get AWS account ID."""
    return sts_client.get_caller_identity()['Account']

def remove_all_collaborators():
    """Remove all existing collaborators from Supervisor."""
    print("\n" + "="*80)
    print("STEP 1: Removing Existing Collaborators")
    print("="*80 + "\n")

    try:
        response = bedrock_client.list_agent_collaborators(
            agentId=SUPERVISOR_AGENT_ID,
            agentVersion='DRAFT'
        )

        collaborators = response.get('agentCollaboratorSummaries', [])

        if not collaborators:
            print("✅ No existing collaborators to remove\n")
            return True

        print(f"Found {len(collaborators)} existing collaborators. Removing...\n")

        for collab in collaborators:
            collab_id = collab['collaboratorId']
            collab_name = collab['collaboratorName']

            print(f"   Removing {collab_name}...")
            bedrock_client.disassociate_agent_collaborator(
                agentId=SUPERVISOR_AGENT_ID,
                agentVersion='DRAFT',
                collaboratorId=collab_id
            )
            print(f"   ✅ Removed {collab_name}")

        print(f"\n✅ All collaborators removed\n")
        return True

    except ClientError as e:
        print(f"❌ Error removing collaborators: {e}\n")
        return False

def add_collaborator_with_draft_alias(agent_id, agent_name, collab_name, instruction):
    """Add collaborator using TSTALIASID (DRAFT alias) which points to latest prepared version."""
    account_id = get_account_id()

    # Use TSTALIASID which is the DRAFT alias
    # This automatically points to the latest prepared version
    alias_arn = f"arn:aws:bedrock:{REGION}:{account_id}:agent-alias/{agent_id}/TSTALIASID"

    print(f"   Adding {collab_name}...")
    print(f"      Agent ID: {agent_id}")
    print(f"      Alias ARN: {alias_arn}")
    print(f"      Using: DRAFT alias (TSTALIASID) → Always uses latest prepared version")

    try:
        bedrock_client.associate_agent_collaborator(
            agentId=SUPERVISOR_AGENT_ID,
            agentVersion='DRAFT',
            agentDescriptor={
                'aliasArn': alias_arn
            },
            collaboratorName=collab_name,
            collaborationInstruction=instruction,
            relayConversationHistory='DISABLED'
        )
        print(f"   ✅ Added {collab_name}\n")
        return True
    except ClientError as e:
        # If DRAFT alias doesn't work, it means AWS doesn't allow it for collaboration
        # This is expected based on our earlier errors
        print(f"   ⚠️  DRAFT alias not allowed: {e}")
        print(f"   This is expected - AWS doesn't allow TSTALIASID for collaboration\n")
        return False

def add_collaborators():
    """Add collaborators with proper configuration."""
    print("="*80)
    print("STEP 2: Adding Collaborators with Proper Configuration")
    print("="*80 + "\n")

    print("🔍 Attempting to use DRAFT aliases first...\n")

    draft_worked = True
    for agent_type, config in SPECIALIST_AGENTS.items():
        if not add_collaborator_with_draft_alias(
            config['id'],
            agent_type,
            config['name'],
            config['instruction']
        ):
            draft_worked = False
            break

    if draft_worked:
        print("✅ All collaborators added with DRAFT aliases!\n")
        return True

    print("="*80)
    print("DRAFT aliases don't work for collaboration (AWS limitation)")
    print("Switching to using latest prepared version directly...")
    print("="*80 + "\n")

    # Since DRAFT alias doesn't work, we need to:
    # 1. Get the latest prepared version for each agent
    # 2. Create/use an alias that points to that version
    # 3. Use that alias for collaboration

    account_id = get_account_id()
    success_count = 0

    for agent_type, config in SPECIALIST_AGENTS.items():
        agent_id = config['id']
        collab_name = config['name']
        instruction = config['instruction']

        print(f"   Adding {collab_name}...")

        try:
            # Get agent info to find latest version
            agent_info = bedrock_client.get_agent(agentId=agent_id)

            # List versions to find the highest version number
            versions_response = bedrock_client.list_agent_versions(agentId=agent_id)
            versions = versions_response.get('agentVersionSummaries', [])

            # Filter out DRAFT and get numeric versions
            numeric_versions = [
                int(v['agentVersion'])
                for v in versions
                if v['agentVersion'] != 'DRAFT' and v['agentVersion'].isdigit()
            ]

            if not numeric_versions:
                print(f"   ⚠️  No versions found for {agent_type}, skipping...")
                continue

            latest_version = max(numeric_versions)
            print(f"      Latest version: {latest_version}")

            # Check if alias exists for this version
            aliases_response = bedrock_client.list_agent_aliases(agentId=agent_id)
            aliases = aliases_response.get('agentAliasSummaries', [])

            # Find or create alias for latest version
            alias_id = None
            alias_name = f"v{latest_version}"

            for alias in aliases:
                if alias['agentAliasName'] == alias_name:
                    alias_id = alias['agentAliasId']
                    print(f"      Found existing alias: {alias_name} ({alias_id})")
                    break

            if not alias_id:
                # Create alias for latest version
                print(f"      Creating alias {alias_name} for version {latest_version}...")
                alias_response = bedrock_client.create_agent_alias(
                    agentId=agent_id,
                    agentAliasName=alias_name,
                    routingConfiguration=[{
                        'agentVersion': str(latest_version)
                    }]
                )
                alias_id = alias_response['agentAlias']['agentAliasId']
                print(f"      ✅ Created alias: {alias_name} ({alias_id})")

            # Now add collaborator with this alias
            alias_arn = f"arn:aws:bedrock:{REGION}:{account_id}:agent-alias/{agent_id}/{alias_id}"
            print(f"      Alias ARN: {alias_arn}")

            bedrock_client.associate_agent_collaborator(
                agentId=SUPERVISOR_AGENT_ID,
                agentVersion='DRAFT',
                agentDescriptor={
                    'aliasArn': alias_arn
                },
                collaboratorName=collab_name,
                collaborationInstruction=instruction,
                relayConversationHistory='DISABLED'
            )

            print(f"   ✅ Added {collab_name}\n")
            success_count += 1

        except ClientError as e:
            print(f"   ❌ Error adding {collab_name}: {e}\n")

    if success_count == len(SPECIALIST_AGENTS):
        print(f"✅ All {success_count} collaborators added successfully!\n")
        return True
    else:
        print(f"⚠️  Added {success_count}/{len(SPECIALIST_AGENTS)} collaborators\n")
        return success_count > 0

def prepare_supervisor():
    """Prepare the Supervisor agent."""
    print("="*80)
    print("STEP 3: Preparing Supervisor Agent")
    print("="*80 + "\n")

    try:
        print("   Preparing Supervisor Agent...")
        bedrock_client.prepare_agent(agentId=SUPERVISOR_AGENT_ID)
        print("   ✅ Supervisor Agent prepared\n")

        print("   ⏳ Waiting 30 seconds for agent to be ready...")
        time.sleep(30)
        print("   ✅ Ready!\n")
        return True
    except ClientError as e:
        print(f"   ❌ Error preparing Supervisor: {e}\n")
        return False

def verify_configuration():
    """Verify the final configuration."""
    print("="*80)
    print("STEP 4: Verifying Configuration")
    print("="*80 + "\n")

    try:
        response = bedrock_client.list_agent_collaborators(
            agentId=SUPERVISOR_AGENT_ID,
            agentVersion='DRAFT'
        )

        collaborators = response.get('agentCollaboratorSummaries', [])

        print(f"✅ Supervisor has {len(collaborators)} collaborators:\n")

        for collab in collaborators:
            print(f"   • {collab['collaboratorName']}")
            print(f"     Alias: {collab['agentDescriptor']['aliasArn']}")
            print(f"     Instruction: {collab['collaborationInstruction'][:80]}...")
            print()

        if len(collaborators) == len(SPECIALIST_AGENTS):
            print("✅ All collaborators configured correctly!\n")
            return True
        else:
            print(f"⚠️  Expected {len(SPECIALIST_AGENTS)} collaborators, found {len(collaborators)}\n")
            return False

    except ClientError as e:
        print(f"❌ Error verifying configuration: {e}\n")
        return False

def main():
    print("\n" + "="*80)
    print("RECREATE SUPERVISOR AGENT")
    print("="*80)
    print("\nThis script will:")
    print("  1. Remove all existing collaborators from Supervisor")
    print("  2. Add collaborators with proper configuration")
    print("  3. Prepare Supervisor Agent")
    print("  4. Verify configuration")
    print("\n" + "="*80 + "\n")

    # Step 1: Remove existing collaborators
    if not remove_all_collaborators():
        print("\n❌ Failed to remove collaborators")
        return 1

    # Step 2: Add collaborators
    if not add_collaborators():
        print("\n❌ Failed to add all collaborators")
        return 1

    # Step 3: Prepare Supervisor
    if not prepare_supervisor():
        print("\n❌ Failed to prepare Supervisor")
        return 1

    # Step 4: Verify
    if not verify_configuration():
        print("\n⚠️  Configuration may have issues")

    # Success!
    print("="*80)
    print("✅ SUPERVISOR RECREATED SUCCESSFULLY!")
    print("="*80)
    print("\nNext steps:")
    print("  1. Test the system:")
    print("     ./tests/test_agent_with_session.py")
    print("\n  2. Monitor CloudWatch logs:")
    print("     aws logs tail /aws/lambda/scheduling-agent-scheduling-actions --follow --region us-east-1")
    print("\n" + "="*80 + "\n")

    return 0

if __name__ == '__main__':
    exit(main())
