#!/usr/bin/env python3
"""
Query Router Lambda Function
Analyzes incoming queries and determines routing path:
- Simple queries → Direct to Bedrock Supervisor
- Complex queries → Route to Step Functions
"""

import boto3
import json
import re
import os
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
stepfunctions = boto3.client('stepfunctions', region_name='us-east-1')

# State machine ARNs (will be set via environment variables)
STATE_MACHINES = {
    'schedule_urgent': os.environ.get('STATE_MACHINE_SCHEDULE_URGENT', ''),
    'weather_scheduling': os.environ.get('STATE_MACHINE_WEATHER', ''),
    'batch_scheduling': os.environ.get('STATE_MACHINE_BATCH', ''),
    'schedule_preferences': os.environ.get('STATE_MACHINE_PREFERENCES', ''),
    'general_orchestration': os.environ.get('STATE_MACHINE_GENERAL', '')
}

def classify_query_complexity(query):
    """
    Use Claude to determine if query is simple or complex

    Returns: 'SIMPLE' or 'COMPLEX'
    """
    prompt = f"""Analyze this customer query and determine if it's SIMPLE or COMPLEX:

SIMPLE queries (handle with single agent call):
- Single straightforward question
- One agent can handle it
- No conditional logic needed
- Direct information retrieval
- Examples:
  * "Show me all my projects"
  * "What's the weather tomorrow?"
  * "Tell me about project PRJ-78945"
  * "What are your working hours?"
  * "Add a note to my appointment"

COMPLEX queries (need orchestration):
- Multiple steps required
- Conditional logic ("if...then...")
- Multiple agents needed to coordinate
- Requires data from one agent to inform another
- Parallel operations needed
- Examples:
  * "Schedule my most urgent project for the earliest time"
  * "If weather is good, schedule outdoor project"
  * "Check all pending projects and schedule the urgent ones"
  * "Find available slots and check weather for those days"

Customer Query: "{query}"

Respond with only one word: SIMPLE or COMPLEX"""

    try:
        response = bedrock_runtime.invoke_model(
            modelId='us.anthropic.claude-3-5-sonnet-20241022-v2:0',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 10,
                "temperature": 0.0,
                "messages": [{"role": "user", "content": prompt}]
            })
        )

        result = json.loads(response['body'].read())
        complexity = result['content'][0]['text'].strip().upper()

        logger.info(f"Query complexity: {complexity} for query: {query[:50]}...")
        return complexity if complexity in ['SIMPLE', 'COMPLEX'] else 'SIMPLE'

    except Exception as e:
        logger.error(f"Error classifying query: {e}")
        # Default to SIMPLE on error (safer)
        return 'SIMPLE'


def determine_state_machine(query):
    """
    Determine which Step Functions state machine to use based on query patterns

    Returns: State machine ARN
    """
    query_lower = query.lower()

    # Pattern matching for specific workflows
    patterns = {
        'schedule_urgent': [
            r'urgent.*schedule',
            r'schedule.*urgent',
            r'most urgent',
            r'highest priority',
            r'schedule.*earliest',
            r'soonest.*available'
        ],
        'weather_scheduling': [
            r'weather.*schedule',
            r'schedule.*weather',
            r'if.*weather',
            r'when.*weather.*good',
            r'weather.*dependent',
            r'outdoor.*project.*weather',
            r'weather.*suitable',
            r'check.*weather.*schedule'
        ],
        'batch_scheduling': [
            r'all.*pending.*schedule',
            r'schedule.*all',
            r'batch.*schedule',
            r'multiple.*project.*schedule',
            r'schedule.*installation.*projects',
            r'book.*all.*appointments',
            r'schedule.*everything'
        ],
        'schedule_preferences': [
            r'monday.*or.*tuesday',
            r'first choice.*second choice',
            r'preferred.*time',
            r'if.*not.*available.*try',
            r'fallback.*option',
            r'alternative.*time'
        ]
    }

    # Check each pattern category
    for machine_key, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, query_lower):
                arn = STATE_MACHINES.get(machine_key)
                if arn:
                    logger.info(f"Matched pattern '{pattern}' → {machine_key}")
                    return arn

    # Default to general orchestration
    logger.info("Using general orchestration state machine")
    return STATE_MACHINES.get('general_orchestration', '')


def lambda_handler(event, context):
    """
    Main handler for query routing

    Input event structure:
    {
        "query": "user query text",
        "customer_id": "CUST001",
        "client_id": "CLIENT001",
        "sessionId": "session-123"
    }

    Output:
    {
        "route": "bedrock_direct" | "step_functions",
        "agent_id": "...",  # if bedrock_direct
        "execution_arn": "..."  # if step_functions
    }
    """
    try:
        # Extract input
        query = event.get('query', '')
        customer_id = event.get('customer_id', 'CUST001')
        client_id = event.get('client_id', 'CLIENT001')
        session_id = event.get('sessionId', f'session-{customer_id}')

        logger.info(f"Routing query for customer {customer_id}: {query[:100]}...")

        # Classify query complexity
        complexity = classify_query_complexity(query)

        if complexity == 'SIMPLE':
            # Route directly to Bedrock Supervisor
            logger.info("Routing to Bedrock Supervisor (direct)")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'route': 'bedrock_direct',
                    'agent_id': 'WF1S95L7X1',  # Supervisor agent
                    'agent_alias_id': 'TSTALIASID',  # DRAFT version
                    'session_id': session_id,
                    'complexity': 'SIMPLE'
                })
            }

        else:  # COMPLEX
            # Determine appropriate state machine
            state_machine_arn = determine_state_machine(query)

            if not state_machine_arn:
                logger.warning("No state machine ARN found, falling back to Bedrock direct")
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'route': 'bedrock_direct',
                        'agent_id': 'WF1S95L7X1',
                        'agent_alias_id': 'TSTALIASID',
                        'session_id': session_id,
                        'complexity': 'COMPLEX_BUT_FALLBACK'
                    })
                }

            # Start Step Functions execution
            logger.info(f"Starting Step Functions execution: {state_machine_arn}")

            execution = stepfunctions.start_execution(
                stateMachineArn=state_machine_arn,
                input=json.dumps({
                    'query': query,
                    'customer_id': customer_id,
                    'client_id': client_id,
                    'sessionId': session_id
                })
            )

            logger.info(f"Execution started: {execution['executionArn']}")

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'route': 'step_functions',
                    'execution_arn': execution['executionArn'],
                    'session_id': session_id,
                    'complexity': 'COMPLEX',
                    'state_machine': state_machine_arn
                })
            }

    except Exception as e:
        logger.error(f"Error in query router: {e}", exc_info=True)

        # Fallback to direct Bedrock on error
        return {
            'statusCode': 200,
            'body': json.dumps({
                'route': 'bedrock_direct',
                'agent_id': 'WF1S95L7X1',
                'agent_alias_id': 'TSTALIASID',
                'error': str(e),
                'fallback': True
            })
        }
