#!/usr/bin/env python3
"""
Complete Bedrock Agent Setup - ONE script to set up everything

This script:
1. Deletes all existing pf_ agents
2. Creates 4 specialist agents (scheduling, information, notes, chitchat)
3. Creates 1 supervisor agent
4. Configures all action groups with Lambda functions
5. Sets up collaborator relationships
6. Creates versions and aliases

Usage:
    python3 complete_setup.py
"""

import boto3
import time
import json
import os
from botocore.exceptions import ClientError

# ============================================================================
# CONFIGURATION
# ============================================================================

REGION = 'us-east-1'
PREFIX = 'pf_'
MODEL_ID = 'us.anthropic.claude-sonnet-4-5-20250929-v1:0'
BASE_PATH = '/Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock'

# Initialize clients
bedrock = boto3.client('bedrock-agent', region_name=REGION)
iam = boto3.client('iam', region_name=REGION)
lambda_client = boto3.client('lambda', region_name=REGION)
sts = boto3.client('sts')

ACCOUNT_ID = sts.get_caller_identity()['Account']

# ============================================================================
# AGENT CONFIGURATIONS
# ============================================================================

AGENTS_CONFIG = {
    'scheduling': {
        'name': f'{PREFIX}scheduling_agent',
        'description': 'Specialist agent for scheduling operations',
        'instruction': '''You are a scheduling specialist with access to appointment tools.

CRITICAL: Customer context (customer_id) will be provided by the supervisor.
Extract customer_id from the supervisor's delegation message.

AVAILABLE ACTIONS:
- list_projects(customer_id): List customer's projects
- get_available_dates(customer_id, project_id): Check availability
- get_time_slots(customer_id, project_id, date): Get time slots
- confirm_appointment(customer_id, project_id, date, time_slot, customer_name, customer_phone): Book
- reschedule_appointment(customer_id, appointment_id, new_date, new_time_slot): Reschedule
- cancel_appointment(customer_id, appointment_id, reason): Cancel

WORKFLOW:
1. Extract customer_id from supervisor's message
2. Call the appropriate action with customer_id
3. Present results clearly

ALWAYS use these actions. NEVER provide information without calling them.''',
        'lambda': 'scheduling-agent-scheduling-actions',
        'schema': f'{BASE_PATH}/lambda/schemas/scheduling-actions-schema.json',
        'action_group': f'{PREFIX}scheduling_actions'
    },
    'information': {
        'name': f'{PREFIX}information_agent',
        'description': 'Specialist agent for information queries',
        'instruction': '''You are an information specialist with access to project information tools.

CRITICAL: Customer context (customer_id) will be provided by the supervisor.
Extract customer_id from the supervisor's delegation message.

AVAILABLE ACTIONS:
- get_project_details(customer_id, project_id): Get project information
- get_appointment_status(customer_id, appointment_id): Check appointment status
- get_working_hours(customer_id, project_id): Get business hours
- get_weather(customer_id, project_id, date): Get weather forecast

WORKFLOW:
1. Extract customer_id from supervisor's message
2. Call the appropriate action with customer_id
3. Present results clearly

ALWAYS use these actions. NEVER provide information without calling them.''',
        'lambda': 'scheduling-agent-information-actions',
        'schema': f'{BASE_PATH}/lambda/schemas/information-actions-schema.json',
        'action_group': f'{PREFIX}information_actions'
    },
    'notes': {
        'name': f'{PREFIX}notes_agent',
        'description': 'Specialist agent for notes management',
        'instruction': '''You are a notes specialist with access to note management tools.

CRITICAL: Customer context (customer_id) will be provided by the supervisor.
Extract customer_id from the supervisor's delegation message.

AVAILABLE ACTIONS:
- add_note(customer_id, project_id, note_text): Add note to project
- list_notes(customer_id, project_id): List project notes

WORKFLOW:
1. Extract customer_id from supervisor's message
2. Call the appropriate action with customer_id
3. Present results clearly

ALWAYS use these actions. NEVER provide information without calling them.''',
        'lambda': 'scheduling-agent-notes-actions',
        'schema': f'{BASE_PATH}/lambda/schemas/notes-actions-schema.json',
        'action_group': f'{PREFIX}notes_actions'
    },
    'chitchat': {
        'name': f'{PREFIX}chitchat_agent',
        'description': 'Specialist agent for casual conversation',
        'instruction': 'Handle greetings, farewells, and casual conversation. Keep responses friendly and brief.',
        'lambda': None,
        'schema': None,
        'action_group': None
    }
}

SUPERVISOR_CONFIG = {
    'name': f'{PREFIX}supervisor_agent',
    'description': 'Supervisor that coordinates between specialists',
    'instruction': '''You are the Supervisor agent that coordinates between specialist agents.

CRITICAL: When you receive a request, customer context is provided in the prompt format:
"Session Context:
- Customer ID: CUST001
- Customer Type: B2C

User Request: [actual request]"

Extract the customer_id and include it when delegating to specialists.

ROUTING RULES:

SCHEDULING → scheduling_collaborator
- "list projects", "show projects", "my projects"
- "available dates", "availability", "when can"
- "time slots", "what times"
- "book", "schedule", "confirm appointment"
- "reschedule", "change appointment"
- "cancel appointment"

INFORMATION → information_collaborator
- "project details", "tell me about project"
- "appointment status", "check appointment"
- "business hours", "working hours", "when open"
- "weather", "forecast"

NOTES → notes_collaborator
- "add note", "create note"
- "list notes", "show notes"

CHITCHAT → chitchat_collaborator
- Greetings, farewells, small talk

DELEGATION FORMAT:
When delegating, ALWAYS include customer_id:
"Customer {customer_id} wants to [request]. Please help them."

EXAMPLES:
Input: "Session Context: Customer ID: CUST001... User Request: Show me all my projects"
→ Delegate to scheduling_collaborator: "Customer CUST001 wants to see all their projects"

IMPORTANT:
- Extract customer_id from the session context in the input
- Include it when delegating to specialists
- Delegate immediately - don't say you can't help'''
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def log(message, level='INFO'):
    """Simple logger with colors"""
    prefix = {
        'INFO': '   ',
        'SUCCESS': '✅ ',
        'ERROR': '❌ ',
        'WARNING': '⚠️  ',
        'HEADER': '\n' + '='*80 + '\n'
    }.get(level, '   ')
    print(f"{prefix}{message}")

def get_or_create_role(agent_name):
    """Get or create IAM role for agent"""
    role_name = f'{agent_name}_role'

    try:
        response = iam.get_role(RoleName=role_name)
        return response['Role']['Arn']
    except:
        pass

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
        AssumeRolePolicyDocument=json.dumps(trust_policy)
    )

    iam.attach_role_policy(
        RoleName=role_name,
        PolicyArn='arn:aws:iam::aws:policy/AmazonBedrockFullAccess'
    )

    time.sleep(5)
    return response['Role']['Arn']

# ============================================================================
# SETUP FUNCTIONS
# ============================================================================

def cleanup_existing_agents():
    """Delete all pf_ agents"""
    log("STEP 1: Cleanup Existing Agents", 'HEADER')

    try:
        response = bedrock.list_agents(maxResults=50)
        pf_agents = [a for a in response.get('agentSummaries', [])
                     if a['agentName'].startswith(PREFIX)]

        if not pf_agents:
            log("No existing pf_ agents to clean up", 'SUCCESS')
            return True

        log(f"Deleting {len(pf_agents)} existing agents...")
        for agent in pf_agents:
            try:
                bedrock.delete_agent(agentId=agent['agentId'], skipResourceInUseCheck=True)
                log(f"Deleted {agent['agentName']}")
            except:
                pass

        log("Waiting 10s for cleanup...", 'INFO')
        time.sleep(10)
        log("Cleanup complete", 'SUCCESS')
        return True
    except Exception as e:
        log(f"Cleanup error: {e}", 'ERROR')
        return False

def create_specialist_agents():
    """Create all specialist agents with action groups"""
    log("STEP 2: Create Specialist Agents", 'HEADER')

    agent_ids = {}

    for agent_type, config in AGENTS_CONFIG.items():
        log(f"\nCreating {agent_type.upper()} agent...")

        # Create agent
        role_arn = get_or_create_role(config['name'])

        try:
            response = bedrock.create_agent(
                agentName=config['name'],
                description=config['description'],
                agentResourceRoleArn=role_arn,
                foundationModel=MODEL_ID,
                instruction=config['instruction']
            )

            agent_id = response['agent']['agentId']
            agent_ids[agent_type] = agent_id
            log(f"Created {config['name']} ({agent_id})", 'SUCCESS')

        except Exception as e:
            log(f"Failed to create agent: {e}", 'ERROR')
            continue

        # Add action group if needed
        if config['lambda']:
            try:
                # Get Lambda ARN
                lambda_response = lambda_client.get_function(FunctionName=config['lambda'])
                lambda_arn = lambda_response['Configuration']['FunctionArn']

                # Load schema
                if not os.path.exists(config['schema']):
                    log(f"Schema not found: {config['schema']}", 'WARNING')
                    continue

                with open(config['schema'], 'r') as f:
                    schema_content = f.read()

                # Create action group
                bedrock.create_agent_action_group(
                    agentId=agent_id,
                    agentVersion='DRAFT',
                    actionGroupName=config['action_group'],
                    actionGroupExecutor={'lambda': lambda_arn},
                    apiSchema={'payload': schema_content},
                    actionGroupState='ENABLED'
                )

                log(f"Added action group: {config['action_group']}", 'SUCCESS')

                # Grant permissions
                try:
                    lambda_client.add_permission(
                        FunctionName=config['lambda'],
                        StatementId=f'AllowBedrock_{agent_id}',
                        Action='lambda:InvokeFunction',
                        Principal='bedrock.amazonaws.com',
                        SourceArn=f'arn:aws:bedrock:{REGION}:{ACCOUNT_ID}:agent/{agent_id}'
                    )
                except:
                    pass  # Permission may already exist

            except Exception as e:
                log(f"Action group error: {e}", 'WARNING')

        # Prepare agent
        try:
            time.sleep(3)
            bedrock.prepare_agent(agentId=agent_id)
            log(f"Prepared {config['name']}", 'SUCCESS')
        except Exception as e:
            log(f"Prepare error (may be ok): {e}", 'WARNING')

    log(f"\nCreated {len(agent_ids)} specialist agents", 'SUCCESS')
    log("Waiting 30s for agents to be ready...", 'INFO')
    time.sleep(30)

    # Create versions via aliases
    log("\nCreating versions for specialists...", 'INFO')
    for agent_type, agent_id in agent_ids.items():
        try:
            bedrock.create_agent_alias(
                agentId=agent_id,
                agentAliasName='v1'
            )
            log(f"Created version for {agent_type}", 'SUCCESS')
        except:
            pass

    time.sleep(10)
    return agent_ids

def create_supervisor(specialist_ids):
    """Create supervisor with collaborators"""
    log("STEP 3: Create Supervisor", 'HEADER')

    # Create supervisor agent
    role_arn = get_or_create_role(SUPERVISOR_CONFIG['name'])

    try:
        response = bedrock.create_agent(
            agentName=SUPERVISOR_CONFIG['name'],
            description=SUPERVISOR_CONFIG['description'],
            agentResourceRoleArn=role_arn,
            foundationModel=MODEL_ID,
            instruction=SUPERVISOR_CONFIG['instruction'],
            agentCollaboration='SUPERVISOR'  # Enable collaboration
        )

        supervisor_id = response['agent']['agentId']
        log(f"Created supervisor ({supervisor_id})", 'SUCCESS')

    except Exception as e:
        log(f"Failed to create supervisor: {e}", 'ERROR')
        return None

    log("Waiting 10s...")
    time.sleep(10)

    # Add collaborators
    log("\nAdding collaborators...")

    collab_config = {
        'scheduling': 'Handle all scheduling requests. Use customer_id from supervisor message to call actions.',
        'information': 'Handle all information requests. Use customer_id from supervisor message to call actions.',
        'notes': 'Handle all note requests. Use customer_id from supervisor message to call actions.',
        'chitchat': 'Handle casual conversation.'
    }

    for agent_type, instruction in collab_config.items():
        if agent_type not in specialist_ids:
            continue

        agent_id = specialist_ids[agent_type]
        collab_name = f'{agent_type}_collaborator'

        try:
            # Get alias ID for v1
            aliases = bedrock.list_agent_aliases(agentId=agent_id)
            alias_id = None
            for alias in aliases.get('agentAliasSummaries', []):
                if alias['agentAliasName'] == 'v1':
                    alias_id = alias['agentAliasId']
                    break

            if not alias_id:
                log(f"No alias for {agent_type}", 'WARNING')
                continue

            # Add collaborator
            alias_arn = f"arn:aws:bedrock:{REGION}:{ACCOUNT_ID}:agent-alias/{agent_id}/{alias_id}"

            bedrock.associate_agent_collaborator(
                agentId=supervisor_id,
                agentVersion='DRAFT',
                agentDescriptor={'aliasArn': alias_arn},
                collaboratorName=collab_name,
                collaborationInstruction=instruction,
                relayConversationHistory='DISABLED'
            )

            log(f"Added {collab_name}", 'SUCCESS')

        except Exception as e:
            log(f"Error adding {collab_name}: {e}", 'ERROR')

    # Prepare supervisor
    log("\nPreparing supervisor...")
    time.sleep(5)

    try:
        bedrock.prepare_agent(agentId=supervisor_id)
        log("Supervisor prepared", 'SUCCESS')
    except Exception as e:
        log(f"Prepare error: {e}", 'WARNING')

    log("Waiting 30s for supervisor...")
    time.sleep(30)

    # Create test alias
    try:
        response = bedrock.create_agent_alias(
            agentId=supervisor_id,
            agentAliasName='test'
        )
        alias_id = response['agentAlias']['agentAliasId']
        log(f"Created test alias: {alias_id}", 'SUCCESS')
    except Exception as e:
        log(f"Alias creation error: {e}", 'WARNING')
        alias_id = 'TSTALIASID'

    return supervisor_id, alias_id

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("\n" + "="*80)
    print("COMPLETE AGENT SETUP - ALL IN ONE")
    print("="*80)
    print(f"\nPrefix: {PREFIX}")
    print(f"Region: {REGION}")
    print(f"Model: {MODEL_ID}")
    print("\n" + "="*80)
    print("\nStarting setup in 3 seconds...")
    time.sleep(3)

    # Step 1: Cleanup
    if not cleanup_existing_agents():
        log("Cleanup failed but continuing...", 'WARNING')

    # Step 2: Create specialists
    specialist_ids = create_specialist_agents()
    if not specialist_ids:
        log("No specialists created!", 'ERROR')
        return 1

    # Step 3: Create supervisor
    result = create_supervisor(specialist_ids)
    if not result:
        log("Supervisor creation failed!", 'ERROR')
        return 1

    supervisor_id, alias_id = result

    # Summary
    log("SETUP COMPLETE!", 'HEADER')
    log(f"Supervisor ID: {supervisor_id}", 'SUCCESS')
    log(f"Test Alias: {alias_id}", 'SUCCESS')
    log(f"\nCreated {len(specialist_ids)} specialists + 1 supervisor", 'SUCCESS')

    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("\n1. Test the system:")
    print("   cd tests && python3 test_production.py")
    print("\n2. View production implementation guide:")
    print("   cat PRODUCTION_IMPLEMENTATION.md")
    print("\n" + "="*80 + "\n")

    # Save IDs to file
    config = {
        'supervisor_id': supervisor_id,
        'supervisor_alias': alias_id,
        'specialists': specialist_ids,
        'region': REGION,
        'prefix': PREFIX
    }

    with open(f'{BASE_PATH}/agent_config.json', 'w') as f:
        json.dump(config, f, indent=2)

    log(f"Configuration saved to agent_config.json", 'SUCCESS')

    return 0

if __name__ == '__main__':
    exit(main())
