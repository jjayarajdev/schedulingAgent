#!/usr/bin/env python3
"""
Configure action groups for existing pf_ agents and setup supervisor collaborators.
"""

import boto3
import time
from botocore.exceptions import ClientError

REGION = 'us-east-1'

# Existing agent IDs (from complete_setup.py output)
AGENT_IDS = {
    'scheduling': '8BGUCA98U7',
    'information': 'UVF5I7KLZ0',
    'notes': 'H0UWLOOQWN',
    'chitchat': 'OBSED5E3TZ',
    'supervisor': 'V3BW0KFBMX'
}

# Lambda and action group configuration
ACTION_GROUPS = {
    'scheduling': {
        'lambda_name': 'scheduling-agent-scheduling-actions',
        'action_group_name': 'pf_scheduling_actions',
        'schema_file': 'scheduling-actions-schema.json'
    },
    'information': {
        'lambda_name': 'scheduling-agent-information-actions',
        'action_group_name': 'pf_information_actions',
        'schema_file': 'information-actions-schema.json'
    },
    'notes': {
        'lambda_name': 'scheduling-agent-notes-actions',
        'action_group_name': 'pf_notes_actions',
        'schema_file': 'notes-actions-schema.json'
    }
}

# Initialize clients
bedrock = boto3.client('bedrock-agent', region_name=REGION)
lambda_client = boto3.client('lambda', region_name=REGION)
sts = boto3.client('sts')

ACCOUNT_ID = sts.get_caller_identity()['Account']

def add_action_group(agent_id, agent_type, config):
    """Add action group to an agent."""
    action_group_name = config['action_group_name']
    lambda_name = config['lambda_name']

    print(f"\n{'─'*80}")
    print(f"Configuring {agent_type.upper()} Agent")
    print(f"{'─'*80}")
    print(f"Agent ID: {agent_id}")
    print(f"Action Group: {action_group_name}")
    print(f"Lambda: {lambda_name}\n")

    try:
        # Get Lambda ARN
        lambda_response = lambda_client.get_function(FunctionName=lambda_name)
        lambda_arn = lambda_response['Configuration']['FunctionArn']
        print(f"✅ Found Lambda: {lambda_arn}")

    except ClientError as e:
        print(f"❌ Lambda function not found: {lambda_name}")
        return False

    try:
        # Load OpenAPI schema
        schema_path = f'/Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/lambda/schemas/{config["schema_file"]}'

        with open(schema_path, 'r') as f:
            schema_content = f.read()

        # Check if action group already exists
        existing_groups = bedrock.list_agent_action_groups(
            agentId=agent_id,
            agentVersion='DRAFT'
        )

        action_group_id = None
        for group in existing_groups.get('actionGroupSummaries', []):
            if group['actionGroupName'] == action_group_name:
                action_group_id = group['actionGroupId']
                print(f"ℹ️  Action group already exists, updating...")
                break

        if action_group_id:
            # Update existing
            bedrock.update_agent_action_group(
                agentId=agent_id,
                agentVersion='DRAFT',
                actionGroupId=action_group_id,
                actionGroupName=action_group_name,
                actionGroupExecutor={
                    'lambda': lambda_arn
                },
                apiSchema={
                    'payload': schema_content
                },
                actionGroupState='ENABLED'
            )
            print(f"✅ Updated action group: {action_group_name}")
        else:
            # Create new
            bedrock.create_agent_action_group(
                agentId=agent_id,
                agentVersion='DRAFT',
                actionGroupName=action_group_name,
                actionGroupExecutor={
                    'lambda': lambda_arn
                },
                apiSchema={
                    'payload': schema_content
                },
                actionGroupState='ENABLED'
            )
            print(f"✅ Created action group: {action_group_name}")

        # Grant Bedrock permission to invoke Lambda
        try:
            lambda_client.add_permission(
                FunctionName=lambda_name,
                StatementId=f'AllowBedrockInvoke_{agent_id}',
                Action='lambda:InvokeFunction',
                Principal='bedrock.amazonaws.com',
                SourceArn=f'arn:aws:bedrock:{REGION}:{ACCOUNT_ID}:agent/{agent_id}'
            )
            print(f"✅ Granted Lambda invoke permission")
        except ClientError as e:
            if 'ResourceConflictException' in str(e):
                print(f"ℹ️  Lambda permission already exists")
            else:
                print(f"⚠️  Error granting permission: {e}")

        # Prepare agent
        print(f"Preparing agent...")
        bedrock.prepare_agent(agentId=agent_id)
        print(f"✅ Agent prepared")

        return True

    except ClientError as e:
        print(f"❌ Error configuring action group: {e}")
        return False
    except FileNotFoundError:
        print(f"❌ Schema file not found: {config['schema_file']}")
        return False

def configure_supervisor_collaborators():
    """Configure supervisor collaborators."""
    supervisor_id = AGENT_IDS['supervisor']

    print(f"\n{'='*80}")
    print("Configuring Supervisor Collaborators")
    print(f"{'='*80}\n")

    # Remove existing collaborators
    print("Removing existing collaborators...")
    try:
        response = bedrock.list_agent_collaborators(
            agentId=supervisor_id,
            agentVersion='DRAFT'
        )

        for collab in response.get('agentCollaboratorSummaries', []):
            collab_id = collab['collaboratorId']
            collab_name = collab['collaboratorName']

            print(f"   Removing {collab_name}...")
            bedrock.disassociate_agent_collaborator(
                agentId=supervisor_id,
                agentVersion='DRAFT',
                collaboratorId=collab_id
            )
            print(f"   ✅ Removed")

    except ClientError as e:
        print(f"⚠️  Error removing collaborators: {e}")

    print("\nAdding collaborators...\n")

    collaborators = {
        'scheduling': {
            'name': 'scheduling_collaborator',
            'instruction': 'Handle all scheduling-related requests including appointments, availability, booking, rescheduling, and cancellations. MUST use available actions to retrieve and modify scheduling data.'
        },
        'information': {
            'name': 'information_collaborator',
            'instruction': 'Handle all information requests including project details, appointment status, business hours, and weather. MUST use available actions to retrieve information.'
        },
        'notes': {
            'name': 'notes_collaborator',
            'instruction': 'Handle all note management requests including adding and viewing project notes. MUST use available actions to manage notes.'
        },
        'chitchat': {
            'name': 'chitchat_collaborator',
            'instruction': 'Handle casual conversation, greetings, farewells, and small talk.'
        }
    }

    for agent_type, config in collaborators.items():
        agent_id = AGENT_IDS[agent_type]
        collab_name = config['name']

        print(f"   Adding {collab_name}...")

        try:
            # Get agent versions
            versions_response = bedrock.list_agent_versions(agentId=agent_id)
            versions = versions_response.get('agentVersionSummaries', [])

            numeric_versions = [
                int(v['agentVersion'])
                for v in versions
                if v['agentVersion'] != 'DRAFT' and v['agentVersion'].isdigit()
            ]

            if not numeric_versions:
                print(f"      ⚠️  No versions found, preparing agent...")
                bedrock.prepare_agent(agentId=agent_id)
                time.sleep(5)

                versions_response = bedrock.list_agent_versions(agentId=agent_id)
                versions = versions_response.get('agentVersionSummaries', [])
                numeric_versions = [
                    int(v['agentVersion'])
                    for v in versions
                    if v['agentVersion'] != 'DRAFT' and v['agentVersion'].isdigit()
                ]

            if not numeric_versions:
                print(f"      ❌ Could not create version for {agent_type}")
                continue

            latest_version = max(numeric_versions)
            print(f"      Using version: {latest_version}")

            # Get or create alias
            alias_name = f'v{latest_version}'
            alias_id = None

            aliases_response = bedrock.list_agent_aliases(agentId=agent_id)
            for alias in aliases_response.get('agentAliasSummaries', []):
                if alias['agentAliasName'] == alias_name:
                    alias_id = alias['agentAliasId']
                    break

            if not alias_id:
                print(f"      Creating alias {alias_name}...")
                alias_response = bedrock.create_agent_alias(
                    agentId=agent_id,
                    agentAliasName=alias_name,
                    routingConfiguration=[{
                        'agentVersion': str(latest_version)
                    }]
                )
                alias_id = alias_response['agentAlias']['agentAliasId']

            # Create alias ARN
            alias_arn = f"arn:aws:bedrock:{REGION}:{ACCOUNT_ID}:agent-alias/{agent_id}/{alias_id}"
            print(f"      Alias ARN: {alias_arn}")

            # Add collaborator
            bedrock.associate_agent_collaborator(
                agentId=supervisor_id,
                agentVersion='DRAFT',
                agentDescriptor={
                    'aliasArn': alias_arn
                },
                collaboratorName=collab_name,
                collaborationInstruction=config['instruction'],
                relayConversationHistory='DISABLED'
            )

            print(f"   ✅ Added {collab_name}\n")

        except ClientError as e:
            print(f"   ❌ Error adding {collab_name}: {e}\n")

    # Prepare supervisor
    print("Preparing supervisor...")
    try:
        bedrock.prepare_agent(agentId=supervisor_id)
        print("✅ Supervisor prepared")
        print("\n⏳ Waiting 30 seconds for supervisor to be ready...")
        time.sleep(30)
    except ClientError as e:
        print(f"❌ Error preparing supervisor: {e}")

def create_test_alias():
    """Create test alias for supervisor."""
    supervisor_id = AGENT_IDS['supervisor']

    print(f"\n{'='*80}")
    print("Creating Test Alias")
    print(f"{'='*80}\n")

    try:
        # Get latest version
        versions_response = bedrock.list_agent_versions(agentId=supervisor_id)
        versions = versions_response.get('agentVersionSummaries', [])

        numeric_versions = [
            int(v['agentVersion'])
            for v in versions
            if v['agentVersion'] != 'DRAFT' and v['agentVersion'].isdigit()
        ]

        if not numeric_versions:
            print("⚠️  No versions found")
            return None

        latest_version = max(numeric_versions)
        print(f"Latest version: {latest_version}")

        # Create test alias
        alias_name = 'test'
        print(f"Creating alias '{alias_name}'...")

        response = bedrock.create_agent_alias(
            agentId=supervisor_id,
            agentAliasName=alias_name,
            routingConfiguration=[{
                'agentVersion': str(latest_version)
            }]
        )

        alias_id = response['agentAlias']['agentAliasId']
        print(f"✅ Created alias: {alias_name} ({alias_id})")

        return alias_id

    except ClientError as e:
        if 'ConflictException' in str(e):
            print(f"ℹ️  Alias already exists")
            response = bedrock.list_agent_aliases(agentId=supervisor_id)
            for alias in response.get('agentAliasSummaries', []):
                if alias['agentAliasName'] == 'test':
                    return alias['agentAliasId']
        else:
            print(f"❌ Error creating alias: {e}")
            return None

def main():
    print("\n" + "="*80)
    print("CONFIGURE PF_ AGENTS")
    print("="*80)
    print("\nThis will:")
    print("  1. Add action groups to specialist agents")
    print("  2. Configure supervisor collaborators")
    print("  3. Create test alias")
    print("\n" + "="*80 + "\n")

    # Step 1: Add action groups
    print("="*80)
    print("STEP 1: Adding Action Groups")
    print("="*80)

    success_count = 0
    for agent_type, config in ACTION_GROUPS.items():
        agent_id = AGENT_IDS[agent_type]
        if add_action_group(agent_id, agent_type, config):
            success_count += 1

    print(f"\n✅ Configured {success_count}/{len(ACTION_GROUPS)} action groups")

    print("\n⏳ Waiting 30 seconds for agents to be ready...")
    time.sleep(30)

    # Step 2: Configure supervisor
    print("\n" + "="*80)
    print("STEP 2: Configuring Supervisor")
    print("="*80)

    configure_supervisor_collaborators()

    # Step 3: Create test alias
    alias_id = create_test_alias()

    # Summary
    print("\n" + "="*80)
    print("✅ CONFIGURATION COMPLETE!")
    print("="*80)
    print(f"\nSupervisor ID: {AGENT_IDS['supervisor']}")
    print(f"Test Alias: {alias_id}")
    print("\nNext step:")
    print("  ./tests/test_agent_with_session.py")
    print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    main()
