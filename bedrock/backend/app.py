#!/usr/bin/env python3
"""
Flask Backend for Bedrock Agent Chat UI
Handles Bedrock agent invocations with custom intent-based routing
"""

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import boto3
import json
import time
import os
import logging
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bedrock configuration (load from environment-specific agent_config file)
# Priority: agent_config.{ENVIRONMENT}.json > agent_config.json
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
CONFIG_DIR = os.path.dirname(__file__)
ENV_CONFIG_PATH = os.path.join(CONFIG_DIR, f'agent_config.{ENVIRONMENT}.json')
DEFAULT_CONFIG_PATH = os.path.join(CONFIG_DIR, 'agent_config.json')

# Try environment-specific config first, fall back to default
CONFIG_PATH = ENV_CONFIG_PATH if os.path.exists(ENV_CONFIG_PATH) else DEFAULT_CONFIG_PATH

try:
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
        SUPERVISOR_ID = config['supervisor_id']  # Keep for future use
        SUPERVISOR_ALIAS = config['supervisor_alias']  # Keep for future use
        AGENTS = config.get('agents', {})
        ROUTING_CONFIG = config.get('routing', {'enabled': True, 'use_supervisor': False})
        REGION = config.get('region', 'us-east-1')
        logger.info(f"✅ Loaded config from: {CONFIG_PATH} (environment: {ENVIRONMENT})")
except FileNotFoundError:
    logger.error(f"Config file not found at {CONFIG_PATH}")
    # Fallback to hardcoded values
    SUPERVISOR_ID = 'GUA4WQTCID'
    SUPERVISOR_ALIAS = 'TOCAWMGGLB'
    AGENTS = {
        'scheduling': {'agent_id': 'YDCJTJBSLO', 'alias_id': 'VB7IU4DNIZ'},
        'information': {'agent_id': 'I4UC076CNX', 'alias_id': '7VLJCIYKM5'},
        'chitchat': {'agent_id': '0HRRAJHJOA', 'alias_id': '9M3HS9XRDD'}
    }
    ROUTING_CONFIG = {'enabled': True, 'use_supervisor': False}
    REGION = 'us-east-1'

# Sample user data (matches mock_data.py)
SAMPLE_USER = {
    'customer_id': 'CUST001',
    'client_id': 'CLIENT001',
    'customer_type': 'B2C',
    'name': 'John Doe',
    'email': 'john.doe@example.com',
    'projects': [
        {
            'id': 'PRJ-78945',
            'number': 'ORD-2025-001',
            'type': 'Installation',
            'category': 'Flooring',
            'status': 'Scheduled',
            'address': '123 Main St, Tampa, FL 33601',
            'scheduled_date': '2025-11-15',
            'scheduled_time': '08:00 AM - 12:00 PM',
            'technician': 'John Smith',
            'store': 'ST-101'
        },
        {
            'id': 'PRJ-78946',
            'number': 'ORD-2025-002',
            'type': 'Installation',
            'category': 'Windows',
            'status': 'Pending',
            'address': '456 Oak Ave, Tampa, FL 33602',
            'technician': 'Jane Doe',
            'store': 'ST-102'
        },
        {
            'id': 'PRJ-78947',
            'number': 'ORD-2025-003',
            'type': 'Repair',
            'category': 'Deck Repair',
            'status': 'Pending',
            'address': '789 Pine Dr, Clearwater, FL 33755',
            'technician': 'Mike Johnson',
            'store': 'ST-103'
        },
        {
            'id': 'PRJ-78948',
            'number': 'ORD-2025-004',
            'type': 'Installation',
            'category': 'Kitchen Cabinets',
            'status': 'In Progress',
            'address': '321 Maple Ln, St Petersburg, FL 33710',
            'scheduled_date': '2025-10-25',
            'scheduled_time': '01:00 PM - 06:00 PM',
            'technician': 'Sarah Williams',
            'store': 'ST-101'
        },
        {
            'id': 'PRJ-78949',
            'number': 'ORD-2025-005',
            'type': 'Measurement',
            'category': 'Bathroom Remodel',
            'status': 'Pending',
            'address': '555 Beach Blvd, Clearwater Beach, FL 33767',
            'technician': 'Robert Chen',
            'store': 'ST-104'
        }
    ]
}

# Initialize Bedrock clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=REGION)
bedrock_runtime = boto3.client('bedrock-runtime', region_name=REGION)


# ==============================================================================
# Monitoring and Logging Functions
# ==============================================================================

def log_classification_decision(message: str, intent: str, classification_time: float):
    """
    Log classification decisions for monitoring and analytics

    Args:
        message: User message
        intent: Classified intent
        classification_time: Time taken to classify
    """
    try:
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'classification',
            'message': message[:200],  # Truncate for privacy
            'message_length': len(message),
            'classified_intent': intent,
            'classification_time_ms': round(classification_time * 1000, 2),
            'model': 'claude-3.5-sonnet-v2',
            'status': 'success'
        }

        # Log to standard logger
        logger.info(f"Classification: {json.dumps(log_entry)}")

        # TODO: In production, also send to CloudWatch Metrics or analytics service
        # Example: cloudwatch.put_metric_data(...)

    except Exception as e:
        logger.error(f"Error logging classification decision: {e}")


def log_classification_error(message: str, error: str, classification_time: float):
    """
    Log classification errors for monitoring

    Args:
        message: User message that failed classification
        error: Error message
        classification_time: Time taken before error
    """
    try:
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'classification_error',
            'message': message[:200],
            'error': str(error)[:500],
            'classification_time_ms': round(classification_time * 1000, 2),
            'status': 'error'
        }

        logger.error(f"Classification Error: {json.dumps(log_entry)}")

    except Exception as e:
        logger.error(f"Error logging classification error: {e}")


def log_agent_invocation(intent: str, agent_id: str, customer_id: str, message: str, invocation_time: float, success: bool):
    """
    Log agent invocations for monitoring

    Args:
        intent: Classified intent
        agent_id: Agent that was invoked
        customer_id: Customer ID
        message: User message
        invocation_time: Time taken for invocation
        success: Whether invocation succeeded
    """
    try:
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'agent_invocation',
            'intent': intent,
            'agent_id': agent_id,
            'customer_id': customer_id,
            'message_length': len(message),
            'invocation_time_ms': round(invocation_time * 1000, 2),
            'status': 'success' if success else 'error'
        }

        logger.info(f"Agent Invocation: {json.dumps(log_entry)}")

        # TODO: Send to CloudWatch or analytics
        # track_metric('agent_invocations', 1, {'intent': intent, 'agent': agent_id})

    except Exception as e:
        logger.error(f"Error logging agent invocation: {e}")


def get_routing_metrics():
    """
    Get routing metrics for monitoring dashboard
    Returns aggregated stats for the last hour
    """
    # TODO: Implement metrics aggregation from logs or CloudWatch
    # This is a placeholder for future implementation
    return {
        'total_requests': 0,
        'intents': {
            'scheduling': 0,
            'information': 0,
            'chitchat': 0
        },
        'avg_classification_time_ms': 0,
        'avg_invocation_time_ms': 0,
        'error_rate': 0
    }


# ==============================================================================
# Intent Classification
# ==============================================================================

def classify_intent(message):
    """
    Classify user intent using Claude 3.5 Sonnet V2 for accurate classification.
    Returns: 'scheduling', 'information', or 'chitchat'

    Version: 3.0 - Updated to 3-agent system with Claude 3.5 Sonnet V2
    """
    prompt = f"""You are an intent classifier for a property management scheduling system.

Given a user message, classify it into ONE of these categories:

1. **scheduling**:
   - **ALWAYS classify requests to list, show, or view projects as scheduling**
   - Examples: "show me my projects", "list my projects", "what projects do I have", "show projects", "my projects", "list all projects"
   - Booking appointments ("schedule an appointment", "book a time")
   - Checking availability ("what dates are available", "when can I schedule")
   - Getting dates/times ("available times", "open slots")
   - Confirming, rescheduling, or canceling appointments
   - Calendar operations ("what's on my calendar", "block out time")

2. **information**:
   - Specific project details ("tell me about project X", "details for project 123")
   - Appointment status ("is my appointment confirmed")
   - Working hours ("what time do you open")
   - Weather forecasts, general knowledge queries
   - Factual information lookups ("population of", "exchange rate")

3. **chitchat**:
   - Greetings ("hi", "hello", "good morning", "thanks", "goodbye")
   - Small talk, jokes, casual conversation
   - Emotional expressions ("I'm feeling stressed", "need to talk", "how are you")
   - Gratitude and acknowledgments
   - General help requests without specific intent

User message: "{message}"

Respond with ONLY the category name (scheduling/information/chitchat), nothing else."""

    classification_start_time = time.time()

    try:
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',  # Claude 3.5 Sonnet V2
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 10,
                "temperature": 0.0,  # Deterministic for classification
                "messages": [{"role": "user", "content": prompt}]
            })
        )

        response_body = json.loads(response['body'].read())
        intent = response_body['content'][0]['text'].strip().lower()

        # Validate intent
        valid_intents = ['scheduling', 'information', 'chitchat']
        if intent not in valid_intents:
            logger.warning(f"Invalid intent '{intent}' returned, defaulting to chitchat")
            intent = 'chitchat'

        classification_time = time.time() - classification_start_time
        logger.info(f"Intent classified: {intent} for message: '{message[:50]}...' (took {classification_time:.2f}s)")

        # Log to monitoring (for production analytics)
        log_classification_decision(message, intent, classification_time)

        return intent

    except Exception as e:
        classification_time = time.time() - classification_start_time
        logger.error(f"Intent classification error: {e} (took {classification_time:.2f}s)")

        # Log error for monitoring
        log_classification_error(message, str(e), classification_time)

        # Default to chitchat on error
        return 'chitchat'


def invoke_agent_with_context(message, customer_id, customer_type='B2C'):
    """
    Invoke Bedrock agent with custom intent-based routing

    Routing logic:
    1. If use_supervisor=True: use supervisor agent (for when AWS fixes the bug)
    2. If use_supervisor=False: classify intent and route to appropriate agent

    Version: 2.0 - With monitoring and logging
    """

    # CRITICAL: Inject customer context into prompt
    augmented_prompt = f"""Session Context:
- Customer ID: {customer_id}
- Client ID: {SAMPLE_USER.get('client_id', 'CLIENT001')}
- Client Name: {SAMPLE_USER.get('name', 'John Doe')}
- Customer Type: {customer_type}

User Request: {message}

Please help the customer with their request using their customer ID and client ID for any actions."""

    session_id = f"session-{customer_id}-{int(time.time())}"
    invocation_start_time = time.time()
    intent = 'unknown'
    agent_id = None

    try:
        # Determine which agent to use
        if ROUTING_CONFIG.get('use_supervisor', False):
            # Use supervisor (for future when AWS fixes multi-agent bug)
            agent_id = SUPERVISOR_ID
            alias_id = SUPERVISOR_ALIAS
            intent = 'supervisor'
            logger.info(f"Routing via SUPERVISOR agent: {agent_id}")
        else:
            # Custom routing: classify intent and route to appropriate agent
            intent = classify_intent(message)
            agent_config = AGENTS.get(intent, AGENTS['chitchat'])
            agent_id = agent_config['agent_id']
            alias_id = agent_config['alias_id']
            logger.info(f"Routing to {intent.upper()} agent: {agent_id}")

        # Invoke the selected agent
        response = bedrock_agent_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=session_id,
            inputText=augmented_prompt,
            sessionState={
                'sessionAttributes': {
                    'customer_id': customer_id,
                    'client_id': SAMPLE_USER.get('client_id', 'CLIENT001'),
                    'client_name': SAMPLE_USER.get('name', 'John Doe'),
                    'customer_type': customer_type
                }
            }
        )

        # Stream response
        chunk_count = 0
        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    chunk_count += 1
                    yield chunk['bytes'].decode('utf-8')

        # Log successful invocation
        invocation_time = time.time() - invocation_start_time
        log_agent_invocation(intent, agent_id, customer_id, message, invocation_time, True)
        logger.info(f"Agent invocation completed: {chunk_count} chunks in {invocation_time:.2f}s")

    except Exception as e:
        # Log failed invocation
        invocation_time = time.time() - invocation_start_time
        log_agent_invocation(intent, agent_id or 'unknown', customer_id, message, invocation_time, False)

        logger.error(f"Agent invocation error: {e} (after {invocation_time:.2f}s)")
        yield f"Error: {str(e)}"


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'routing': ROUTING_CONFIG,
        'supervisor_id': SUPERVISOR_ID,
        'agents': {intent: agent['agent_id'] for intent, agent in AGENTS.items()},
        'region': REGION
    })


@app.route('/api/user', methods=['GET'])
def get_user():
    """Get current user info (simulated login)"""
    return jsonify(SAMPLE_USER)


@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat endpoint - invokes Bedrock agent with streaming response"""
    data = request.json
    message = data.get('message')

    if not message:
        return jsonify({'error': 'Message is required'}), 400

    # Use sample user context
    customer_id = SAMPLE_USER['customer_id']
    customer_type = SAMPLE_USER['customer_type']

    def generate():
        for chunk in invoke_agent_with_context(message, customer_id, customer_type):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/api/chat/simple', methods=['POST'])
def chat_simple():
    """Simple non-streaming chat endpoint"""
    data = request.json
    message = data.get('message')

    if not message:
        return jsonify({'error': 'Message is required'}), 400

    # Use sample user context
    customer_id = SAMPLE_USER['customer_id']
    customer_type = SAMPLE_USER['customer_type']

    full_response = ""
    for chunk in invoke_agent_with_context(message, customer_id, customer_type):
        full_response += chunk

    return jsonify({
        'response': full_response,
        'customer_id': customer_id,
        'timestamp': time.time()
    })


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get Bedrock configuration"""
    return jsonify({
        'routing': ROUTING_CONFIG,
        'supervisor_id': SUPERVISOR_ID,
        'supervisor_alias': SUPERVISOR_ALIAS,
        'agents': AGENTS,
        'region': REGION
    })


@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    """
    Get routing metrics for monitoring dashboard
    Returns aggregated statistics for the current session
    """
    metrics = get_routing_metrics()
    return jsonify({
        'status': 'active',
        'routing_method': 'frontend' if not ROUTING_CONFIG.get('use_supervisor') else 'supervisor',
        'metrics': metrics,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/classify', methods=['POST'])
def classify_only():
    """
    Route requests to the Supervisor agent with multi-agent collaboration
    The Supervisor will automatically route to the appropriate collaborator agent
    """
    data = request.json
    message = data.get('message')

    if not message:
        return jsonify({'error': 'Message is required'}), 400

    # Get ProjectForce credentials from request
    pf_token = data.get('pf_token')
    pf_client_id = data.get('pf_client_id', '09PF05VD')
    pf_user_id = data.get('pf_user_id', '6f72bffa-c323-4058-a01c-9d495d696364')

    logger.info(f"Received request with PF token: {'Yes' if pf_token else 'No'}, Client ID: {pf_client_id}")
    if pf_token:
        logger.info(f"Token preview (first 20 chars): {pf_token[:20]}...")

    start_time = time.time()

    try:
        # Route directly to Supervisor - it will handle classification and routing
        agent_id = SUPERVISOR_ID
        alias_id = SUPERVISOR_ALIAS

        logger.info(f"Routing to Supervisor agent: {agent_id} with alias: {alias_id}")

        # Use real ProjectForce data if token is available
        if pf_token:
            customer_id = pf_user_id
            customer_type = 'B2C'
            client_id = pf_client_id
            client_name = 'ProjectForce User'
        else:
            # Fallback to sample data
            customer_id = SAMPLE_USER['customer_id']
            customer_type = SAMPLE_USER['customer_type']
            client_id = SAMPLE_USER.get('client_id', 'CLIENT001')
            client_name = SAMPLE_USER.get('name', 'John Doe')

        session_id = f"test-session-{customer_id}-{int(time.time())}"

        # Create augmented prompt with context
        augmented_prompt = f"""Session Context:
- Customer ID: {customer_id}
- Client ID: {client_id}
- Client Name: {client_name}
- Customer Type: {customer_type}

User Request: {message}

Please help the customer with their request using their customer ID and client ID for any actions."""

        # Invoke agent with ProjectForce token in session attributes
        invocation_start = time.time()

        session_attributes = {
            'customer_id': customer_id,
            'client_id': client_id,
            'client_name': client_name,
            'customer_type': customer_type
        }

        # Add ProjectForce token if available
        if pf_token:
            session_attributes['pf_bearer_token'] = pf_token
            session_attributes['pf_api_base'] = 'https://api-cx-portal.dev.projectsforce.com'
            logger.info(f"Session attributes being sent to Bedrock: {list(session_attributes.keys())}")

        response = bedrock_agent_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=session_id,
            inputText=augmented_prompt,
            enableTrace=True,
            sessionState={
                'sessionAttributes': session_attributes
            }
        )

        # Collect full response and trace
        full_response = ""
        chunk_count = 0
        trace_count = 0
        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    decoded = chunk['bytes'].decode('utf-8')
                    full_response += decoded
                    chunk_count += 1
            elif 'trace' in event:
                trace = event['trace']
                trace_count += 1
                # Log full trace for debugging
                logger.info(f"Full trace event: {json.dumps(trace, indent=2, default=str)}")
                if 'failureTrace' in trace:
                    logger.error(f"Failure trace: {trace['failureTrace']}")
                if 'orchestrationTrace' in trace:
                    orch = trace['orchestrationTrace']
                    if 'invocationInput' in orch:
                        logger.info(f"Action invocation: {orch['invocationInput']}")
                    if 'observation' in orch:
                        logger.info(f"Action observation: {orch['observation']}")

        logger.info(f"Received {chunk_count} chunks, {trace_count} trace events, total length: {len(full_response)} chars")
        logger.info(f"Response preview: {full_response[:200]}...")

        invocation_time = time.time() - invocation_start
        total_time = time.time() - start_time

        return jsonify({
            'intent': 'supervisor',  # All requests go through supervisor
            'agent_id': agent_id,
            'agent_alias_id': alias_id,
            'invocation_time_ms': round(invocation_time * 1000, 2),
            'total_time_ms': round(total_time * 1000, 2),
            'response': full_response,
            'customer_id': customer_id,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat(),
            'request_parameters': {
                'agentId': agent_id,
                'agentAliasId': alias_id,
                'sessionId': session_id,
                'inputText': augmented_prompt,
                'sessionState': {
                    'sessionAttributes': {
                        'customer_id': customer_id,
                        'customer_type': customer_type
                    }
                },
                'original_message': message
            }
        })

    except Exception as e:
        logger.error(f"Supervisor routing error: {e}")
        return jsonify({
            'error': str(e),
            'intent': 'supervisor',
            'total_time_ms': round((time.time() - start_time) * 1000, 2)
        }), 500


@app.route('/api/test-queries', methods=['GET'])
def get_test_queries():
    """
    Get test queries for the Testing UI
    Returns all predefined test queries organized by category
    """
    try:
        test_queries_path = os.path.join(os.path.dirname(__file__), 'test_queries.json')

        with open(test_queries_path, 'r') as f:
            test_queries = json.load(f)

        return jsonify(test_queries)
    except FileNotFoundError:
        logger.error("test_queries.json file not found")
        return jsonify({'error': 'Test queries file not found'}), 404
    except Exception as e:
        logger.error(f"Error loading test queries: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    routing_mode = "SUPERVISOR (Multi-Agent)" if ROUTING_CONFIG.get('use_supervisor') else "CUSTOM ROUTING (Intent-Based)"

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  Bedrock Agent Chat Backend - Custom Routing                ║
╚══════════════════════════════════════════════════════════════╝

Routing Mode: {routing_mode}
Region: {REGION}

Available Agents:
  • Scheduling:   {AGENTS['scheduling']['agent_id']}
  • Information:  {AGENTS['information']['agent_id']}
  • Chitchat:     {AGENTS['chitchat']['agent_id']}

Supervisor (for future use): {SUPERVISOR_ID}

Sample User: {SAMPLE_USER['name']} ({SAMPLE_USER['customer_id']})

Starting server on http://localhost:5001
    """)

    app.run(debug=True, host='0.0.0.0', port=5001)
