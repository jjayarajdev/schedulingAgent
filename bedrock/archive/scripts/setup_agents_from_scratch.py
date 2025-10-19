#!/usr/bin/env python3
"""
Complete agent setup from scratch with pf_ prefix.
Deletes existing agents and recreates everything properly.
"""

import boto3
import time
import json
from botocore.exceptions import ClientError

# Configuration
REGION = 'us-east-1'
PREFIX = 'pf_'

# Agent configurations
AGENTS_CONFIG = {
    'scheduling': {
        'name': f'{PREFIX}scheduling_agent',
        'description': 'Specialist agent for appointment scheduling, availability checks, and calendar management',
        'instruction': '''You are a scheduling specialist agent with access to appointment management tools.

CRITICAL INSTRUCTIONS:
1. ALWAYS use your available actions to interact with the scheduling system
2. NEVER make up or hallucinate appointment information
3. If you need information, use get_available_dates, get_time_slots, or get_appointment_status
4. When booking, use confirm_appointment action
5. When rescheduling, use reschedule_appointment action
6. When canceling, use cancel_appointment action

AVAILABLE ACTIONS:
- list_projects: List all projects for a customer
- get_available_dates: Get available dates for scheduling
- get_time_slots: Get available time slots for a specific date
- confirm_appointment: Book an appointment
- reschedule_appointment: Reschedule an existing appointment
- cancel_appointment: Cancel an appointment

WORKFLOW:
1. When user asks about availability, call get_available_dates
2. When user picks a date, call get_time_slots for that date
3. When user confirms, call confirm_appointment with all details
4. Always confirm the appointment details after booking

YOU MUST use these actions. DO NOT provide scheduling information without calling them first.''',
        'lambda_name': 'scheduling-agent-scheduling-actions',  # Use existing Lambda
        'action_group_name': f'{PREFIX}scheduling_actions',
        'schema_file': 'scheduling_actions.json'
    },
    'information': {
        'name': f'{PREFIX}information_agent',
        'description': 'Specialist agent for project information, status queries, and general information',
        'instruction': '''You are an information specialist agent with access to project and business information tools.

CRITICAL INSTRUCTIONS:
1. ALWAYS use your available actions to retrieve information
2. NEVER make up or hallucinate project details
3. If you need project information, use get_project_details
4. For appointment status, use get_appointment_status
5. For business hours, use get_working_hours
6. For weather, use get_weather

AVAILABLE ACTIONS:
- get_project_details: Get detailed information about a project
- get_appointment_status: Check appointment status
- get_working_hours: Get business operating hours
- get_weather: Get weather forecast for a location

WORKFLOW:
1. When user asks about a project, call get_project_details
2. When user asks about appointment status, call get_appointment_status
3. When user asks about hours, call get_working_hours
4. When user asks about weather, call get_weather

YOU MUST use these actions. DO NOT provide information without calling them first.''',
        'lambda_name': 'scheduling-agent-information-actions',  # Use existing Lambda
        'action_group_name': f'{PREFIX}information_actions',
        'schema_file': 'information_actions.json'
    },
    'notes': {
        'name': f'{PREFIX}notes_agent',
        'description': 'Specialist agent for managing project notes and comments',
        'instruction': '''You are a notes specialist agent with access to note management tools.

CRITICAL INSTRUCTIONS:
1. ALWAYS use your available actions to manage notes
2. NEVER make up note content
3. To add notes, use add_note action
4. To view notes, use list_notes action

AVAILABLE ACTIONS:
- add_note: Add a note to a project
- list_notes: List all notes for a project

WORKFLOW:
1. When user wants to add a note, call add_note with project_id and note content
2. When user wants to see notes, call list_notes with project_id

YOU MUST use these actions. DO NOT provide note information without calling them first.''',
        'lambda_name': 'scheduling-agent-notes-actions',  # Use existing Lambda
        'action_group_name': f'{PREFIX}notes_actions',
        'schema_file': 'notes_actions.json'
    },
    'chitchat': {
        'name': f'{PREFIX}chitchat_agent',
        'description': 'Specialist agent for casual conversation and greetings',
        'instruction': '''You are a friendly chitchat specialist agent.

Your role is to handle:
- Greetings (hello, hi, good morning)
- Farewells (goodbye, bye, see you)
- General chitchat
- Small talk
- Thank yous

Keep responses friendly, brief, and professional.

You do NOT have access to any business actions - if user asks about scheduling, projects, or business information, acknowledge their request and let them know a specialist will help them.''',
        'lambda_name': None,  # No Lambda for chitchat
        'action_group_name': None,
        'schema_file': None
    }
}

SUPERVISOR_CONFIG = {
    'name': f'{PREFIX}supervisor_agent',
    'description': 'Supervisor agent that routes requests to specialist agents',
    'instruction': '''You are a supervisor agent that coordinates between multiple specialist agents to help customers with appointment scheduling and project management.

YOUR ROLE:
- Route requests to the appropriate specialist agent
- Ensure customers get accurate information
- Maintain a friendly, professional tone

AVAILABLE SPECIALIST AGENTS:
1. scheduling_collaborator: For appointments, availability, booking, rescheduling, cancellations
2. information_collaborator: For project details, appointment status, business hours, weather
3. notes_collaborator: For adding or viewing project notes
4. chitchat_collaborator: For greetings, farewells, casual conversation

ROUTING RULES:
- Appointment/scheduling requests → scheduling_collaborator
- Project information requests → information_collaborator
- Note management requests → notes_collaborator
- Greetings/chitchat → chitchat_collaborator

IMPORTANT:
- You must route to the appropriate specialist
- Do NOT try to answer questions directly
- Trust the specialist agents to use their tools
- The specialists have access to real data through their actions'''
}

# Model configuration
MODEL_ID = 'us.anthropic.claude-sonnet-4-5-20250929-v1:0'

# Initialize clients
bedrock = boto3.client('bedrock-agent', region_name=REGION)
iam = boto3.client('iam', region_name=REGION)
lambda_client = boto3.client('lambda', region_name=REGION)
sts = boto3.client('sts')

ACCOUNT_ID = sts.get_caller_identity()['Account']

def delete_existing_agents():
    """Delete all existing pf_ agents."""
    print("\n" + "="*80)
    print("STEP 1: Cleaning Up Existing Agents")
    print("="*80 + "\n")

    try:
        response = bedrock.list_agents(maxResults=50)
        agents = response.get('agentSummaries', [])

        pf_agents = [a for a in agents if a['agentName'].startswith(PREFIX)]

        if not pf_agents:
            print("✅ No existing pf_ agents to clean up\n")
            return True

        print(f"Found {len(pf_agents)} pf_ agents to delete:\n")

        for agent in pf_agents:
            agent_id = agent['agentId']
            agent_name = agent['agentName']

            print(f"   Deleting {agent_name} ({agent_id})...")

            try:
                # Delete agent
                bedrock.delete_agent(
                    agentId=agent_id,
                    skipResourceInUseCheck=True
                )
                print(f"   ✅ Deleted {agent_name}")
            except ClientError as e:
                if 'ResourceNotFoundException' in str(e):
                    print(f"   ℹ️  Already deleted: {agent_name}")
                else:
                    print(f"   ⚠️  Error deleting {agent_name}: {e}")

        print(f"\n✅ Cleanup complete\n")
        print("⏳ Waiting 10 seconds for cleanup to propagate...")
        time.sleep(10)
        return True

    except ClientError as e:
        print(f"❌ Error during cleanup: {e}\n")
        return False

def get_or_create_agent_role(agent_name):
    """Get or create IAM role for agent."""
    role_name = f'{agent_name}_role'

    try:
        # Try to get existing role
        response = iam.get_role(RoleName=role_name)
        role_arn = response['Role']['Arn']
        print(f"   ✅ Using existing role: {role_name}")
        return role_arn
    except ClientError as e:
        if 'NoSuchEntity' not in str(e):
            raise

    # Create new role
    print(f"   Creating IAM role: {role_name}...")

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "bedrock.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }

    response = iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(trust_policy),
        Description=f'Role for {agent_name} Bedrock agent'
    )

    role_arn = response['Role']['Arn']

    # Attach policies
    iam.attach_role_policy(
        RoleName=role_name,
        PolicyArn='arn:aws:iam::aws:policy/AmazonBedrockFullAccess'
    )

    # Wait for role to be ready
    print(f"   ⏳ Waiting 10 seconds for role to be ready...")
    time.sleep(10)

    print(f"   ✅ Created role: {role_name}")
    return role_arn

def create_agent(agent_type, config):
    """Create a single agent."""
    agent_name = config['name']
    print(f"\n   Creating {agent_name}...")

    # Get or create IAM role
    role_arn = get_or_create_agent_role(agent_name)

    try:
        # Create agent
        response = bedrock.create_agent(
            agentName=agent_name,
            description=config['description'],
            agentResourceRoleArn=role_arn,
            foundationModel=MODEL_ID,
            instruction=config['instruction']
        )

        agent_id = response['agent']['agentId']
        print(f"   ✅ Created {agent_name}")
        print(f"      Agent ID: {agent_id}")

        return agent_id

    except ClientError as e:
        print(f"   ❌ Error creating {agent_name}: {e}")
        return None

def create_action_group(agent_id, agent_name, config):
    """Create action group for an agent."""
    if not config.get('lambda_name'):
        return True  # No action group needed (e.g., chitchat)

    action_group_name = config['action_group_name']
    lambda_name = config['lambda_name']

    print(f"   Creating action group: {action_group_name}...")

    try:
        # Get Lambda ARN
        lambda_response = lambda_client.get_function(FunctionName=lambda_name)
        lambda_arn = lambda_response['Configuration']['FunctionArn']
        print(f"      Lambda ARN: {lambda_arn}")

    except ClientError as e:
        print(f"   ⚠️  Lambda function {lambda_name} not found")
        print(f"      You need to deploy Lambda functions first!")
        print(f"      Run: ./scripts/deploy_lambda_functions.sh")
        return False

    try:
        # Load OpenAPI schema
        schema_path = f'/Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/lambda/schemas/{config["schema_file"]}'

        with open(schema_path, 'r') as f:
            schema_content = f.read()

        # Create action group
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

        print(f"   ✅ Created action group: {action_group_name}")

        # Grant Bedrock permission to invoke Lambda
        try:
            lambda_client.add_permission(
                FunctionName=lambda_name,
                StatementId=f'AllowBedrockInvoke_{agent_id}',
                Action='lambda:InvokeFunction',
                Principal='bedrock.amazonaws.com',
                SourceArn=f'arn:aws:bedrock:{REGION}:{ACCOUNT_ID}:agent/{agent_id}'
            )
            print(f"   ✅ Granted Lambda invoke permission")
        except ClientError as e:
            if 'ResourceConflictException' in str(e):
                print(f"   ℹ️  Lambda permission already exists")
            else:
                print(f"   ⚠️  Error granting permission: {e}")

        return True

    except ClientError as e:
        print(f"   ❌ Error creating action group: {e}")
        return False
    except FileNotFoundError:
        print(f"   ❌ Schema file not found: {config['schema_file']}")
        return False

def prepare_agent(agent_id, agent_name):
    """Prepare an agent."""
    print(f"   Preparing {agent_name}...")

    try:
        bedrock.prepare_agent(agentId=agent_id)
        print(f"   ✅ Prepared {agent_name}")
        return True
    except ClientError as e:
        print(f"   ❌ Error preparing {agent_name}: {e}")
        return False

def create_specialist_agents():
    """Create all specialist agents."""
    print("\n" + "="*80)
    print("STEP 2: Creating Specialist Agents")
    print("="*80 + "\n")

    agent_ids = {}

    for agent_type, config in AGENTS_CONFIG.items():
        print(f"{'─'*80}")
        print(f"Creating {agent_type.upper()} Agent")
        print(f"{'─'*80}")

        # Create agent
        agent_id = create_agent(agent_type, config)
        if not agent_id:
            continue

        agent_ids[agent_type] = agent_id

        # Create action group if needed
        if config.get('lambda_name'):
            if not create_action_group(agent_id, config['name'], config):
                print(f"   ⚠️  Action group creation failed, but agent exists")

        # Prepare agent
        prepare_agent(agent_id, config['name'])

        print()

    print(f"✅ Created {len(agent_ids)} specialist agents\n")
    print("⏳ Waiting 30 seconds for agents to be ready...")
    time.sleep(30)

    return agent_ids

def create_supervisor_agent(specialist_agent_ids):
    """Create supervisor agent with collaborators."""
    print("\n" + "="*80)
    print("STEP 3: Creating Supervisor Agent")
    print("="*80 + "\n")

    print("Creating supervisor agent...")

    # Get or create IAM role
    role_arn = get_or_create_agent_role(SUPERVISOR_CONFIG['name'])

    try:
        # Create supervisor agent
        response = bedrock.create_agent(
            agentName=SUPERVISOR_CONFIG['name'],
            description=SUPERVISOR_CONFIG['description'],
            agentResourceRoleArn=role_arn,
            foundationModel=MODEL_ID,
            instruction=SUPERVISOR_CONFIG['instruction']
        )

        supervisor_id = response['agent']['agentId']
        print(f"✅ Created {SUPERVISOR_CONFIG['name']}")
        print(f"   Supervisor ID: {supervisor_id}\n")

        # Wait a bit for supervisor to be ready
        print("⏳ Waiting 10 seconds for supervisor to be ready...")
        time.sleep(10)

        # Add collaborators
        print("\nAdding collaborators...\n")

        collaborator_mapping = {
            'scheduling': 'scheduling_collaborator',
            'information': 'information_collaborator',
            'notes': 'notes_collaborator',
            'chitchat': 'chitchat_collaborator'
        }

        collaboration_instructions = {
            'scheduling': 'Handle all scheduling-related requests including appointments, availability, booking, rescheduling, and cancellations.',
            'information': 'Handle all information requests including project details, appointment status, business hours, and weather.',
            'notes': 'Handle all note management requests including adding and viewing project notes.',
            'chitchat': 'Handle casual conversation, greetings, farewells, and small talk.'
        }

        for agent_type, collab_name in collaborator_mapping.items():
            if agent_type not in specialist_agent_ids:
                print(f"   ⚠️  Skipping {collab_name} - agent not created")
                continue

            agent_id = specialist_agent_ids[agent_type]

            print(f"   Adding {collab_name}...")

            # First, we need to create an alias for this agent
            # Prepare the agent first to create a version
            print(f"      Preparing {agent_type} agent to create version...")
            try:
                bedrock.prepare_agent(agentId=agent_id)
                time.sleep(5)  # Wait for prepare
            except:
                pass  # May already be prepared

            # Get the latest version
            try:
                versions_response = bedrock.list_agent_versions(agentId=agent_id)
                versions = versions_response.get('agentVersionSummaries', [])

                # Get numeric versions only
                numeric_versions = [
                    int(v['agentVersion'])
                    for v in versions
                    if v['agentVersion'] != 'DRAFT' and v['agentVersion'].isdigit()
                ]

                if numeric_versions:
                    latest_version = max(numeric_versions)
                else:
                    # No versions yet, prepare will create version 1
                    latest_version = 1

                print(f"      Latest version: {latest_version}")

                # Create or get alias for this version
                alias_name = f'v{latest_version}'
                alias_id = None

                # Check if alias exists
                aliases_response = bedrock.list_agent_aliases(agentId=agent_id)
                for alias in aliases_response.get('agentAliasSummaries', []):
                    if alias['agentAliasName'] == alias_name:
                        alias_id = alias['agentAliasId']
                        print(f"      Using existing alias: {alias_name} ({alias_id})")
                        break

                if not alias_id:
                    # Create new alias
                    print(f"      Creating alias: {alias_name}...")
                    alias_response = bedrock.create_agent_alias(
                        agentId=agent_id,
                        agentAliasName=alias_name,
                        routingConfiguration=[{
                            'agentVersion': str(latest_version)
                        }]
                    )
                    alias_id = alias_response['agentAlias']['agentAliasId']
                    print(f"      Created alias: {alias_name} ({alias_id})")
                    time.sleep(2)

                # Now create the alias ARN
                alias_arn = f"arn:aws:bedrock:{REGION}:{ACCOUNT_ID}:agent-alias/{agent_id}/{alias_id}"
                print(f"      Alias ARN: {alias_arn}")

                # Add collaborator with alias ARN
                bedrock.associate_agent_collaborator(
                    agentId=supervisor_id,
                    agentVersion='DRAFT',
                    agentDescriptor={
                        'aliasArn': alias_arn
                    },
                    collaboratorName=collab_name,
                    collaborationInstruction=collaboration_instructions[agent_type],
                    relayConversationHistory='DISABLED'
                )
                print(f"   ✅ Added {collab_name}\n")

            except ClientError as e:
                print(f"   ❌ Error adding {collab_name}: {e}\n")

        print("\n⏳ Waiting 10 seconds...")
        time.sleep(10)

        # Prepare supervisor
        print("\nPreparing supervisor agent...")
        prepare_agent(supervisor_id, SUPERVISOR_CONFIG['name'])

        print("\n⏳ Waiting 30 seconds for supervisor to be fully ready...")
        time.sleep(30)

        print(f"\n✅ Supervisor agent ready!\n")

        return supervisor_id

    except ClientError as e:
        print(f"❌ Error creating supervisor: {e}\n")
        return None

def create_test_alias(supervisor_id):
    """Create a test alias for the supervisor."""
    print("\n" + "="*80)
    print("STEP 4: Creating Test Alias")
    print("="*80 + "\n")

    alias_name = 'test'

    try:
        # First get the latest version
        print("Getting latest supervisor version...")
        versions_response = bedrock.list_agent_versions(agentId=supervisor_id)
        versions = versions_response.get('agentVersionSummaries', [])

        numeric_versions = [
            int(v['agentVersion'])
            for v in versions
            if v['agentVersion'] != 'DRAFT' and v['agentVersion'].isdigit()
        ]

        if not numeric_versions:
            print("⚠️  No versions found, using version 1")
            latest_version = 1
        else:
            latest_version = max(numeric_versions)

        print(f"   Latest version: {latest_version}")

        print(f"Creating alias '{alias_name}' pointing to version {latest_version}...")

        response = bedrock.create_agent_alias(
            agentId=supervisor_id,
            agentAliasName=alias_name,
            description='Test alias for development',
            routingConfiguration=[{
                'agentVersion': str(latest_version)
            }]
        )

        alias_id = response['agentAlias']['agentAliasId']
        print(f"✅ Created alias: {alias_name}")
        print(f"   Alias ID: {alias_id}\n")

        return alias_id

    except ClientError as e:
        if 'ConflictException' in str(e):
            print(f"ℹ️  Alias '{alias_name}' already exists\n")
            # Get existing alias
            response = bedrock.list_agent_aliases(agentId=supervisor_id)
            for alias in response.get('agentAliasSummaries', []):
                if alias['agentAliasName'] == alias_name:
                    return alias['agentAliasId']
        else:
            print(f"❌ Error creating alias: {e}\n")
            return None

def print_summary(agent_ids, supervisor_id, alias_id):
    """Print setup summary."""
    print("\n" + "="*80)
    print("✅ SETUP COMPLETE!")
    print("="*80 + "\n")

    print("Created Agents:")
    print("-" * 80)
    for agent_type, agent_id in agent_ids.items():
        agent_name = AGENTS_CONFIG[agent_type]['name']
        print(f"   {agent_name:30} {agent_id}")

    print(f"\n   {SUPERVISOR_CONFIG['name']:30} {supervisor_id}")
    print(f"   Test Alias:                      {alias_id}")

    print("\n" + "="*80)
    print("Next Steps:")
    print("="*80)
    print("\n1. Deploy Lambda functions (if not already done):")
    print("   cd scripts")
    print("   ./deploy_lambda_functions.sh")

    print("\n2. Test the setup:")
    print("   cd ..")
    print("   ./tests/test_agent_with_session.py")

    print("\n3. Update test script with new Supervisor ID:")
    print(f"   Supervisor ID: {supervisor_id}")
    print(f"   Alias ID: {alias_id}")

    print("\n" + "="*80 + "\n")

def main():
    print("\n" + "="*80)
    print("BEDROCK AGENTS SETUP FROM SCRATCH")
    print("="*80)
    print(f"\nPrefix: {PREFIX}")
    print(f"Region: {REGION}")
    print(f"Model: {MODEL_ID}")
    print("\nThis will:")
    print("  1. Delete any existing pf_ agents")
    print("  2. Create 4 specialist agents (scheduling, information, notes, chitchat)")
    print("  3. Create supervisor agent with collaborators")
    print("  4. Create test alias")
    print("\n" + "="*80)

    input("\nPress Enter to continue or Ctrl+C to cancel...")

    # Step 1: Cleanup
    if not delete_existing_agents():
        print("\n❌ Cleanup failed")
        return 1

    # Step 2: Create specialist agents
    agent_ids = create_specialist_agents()
    if not agent_ids:
        print("\n❌ No agents created")
        return 1

    # Step 3: Create supervisor
    supervisor_id = create_supervisor_agent(agent_ids)
    if not supervisor_id:
        print("\n❌ Supervisor creation failed")
        return 1

    # Step 4: Create alias
    alias_id = create_test_alias(supervisor_id)

    # Print summary
    print_summary(agent_ids, supervisor_id, alias_id)

    return 0

if __name__ == '__main__':
    exit(main())
