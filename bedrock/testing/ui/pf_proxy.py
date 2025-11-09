#!/usr/bin/env python3
"""
Simple CORS proxy for ProjectForce API
Allows the HTML page to make API calls without CORS issues
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import logging
import json
import os
import time
from pathlib import Path

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ProjectForce API base URL
PF_API_BASE = "https://api-cx-portal.dev.projectsforce.com"

# ============================================================================
# Conversation History Management
# ============================================================================

# In-memory conversation storage (session_id -> conversation history)
# Format: {session_id: {'messages': [...], 'last_activity': timestamp}}
conversation_store = {}

# Configuration
MAX_HISTORY_MESSAGES = 20  # Keep last 20 messages per session
SESSION_TIMEOUT = 3600  # 1 hour timeout for inactive sessions

def get_conversation_history(session_id):
    """Get conversation history for a session"""
    if session_id not in conversation_store:
        conversation_store[session_id] = {
            'messages': [],
            'last_activity': time.time()
        }
    return conversation_store[session_id]['messages']

def add_to_conversation_history(session_id, role, content, metadata=None):
    """Add a message to conversation history"""
    if session_id not in conversation_store:
        conversation_store[session_id] = {
            'messages': [],
            'last_activity': time.time()
        }

    message = {
        'role': role,  # 'user' or 'assistant'
        'content': content,
        'timestamp': time.time(),
        'metadata': metadata or {}
    }

    conversation_store[session_id]['messages'].append(message)
    conversation_store[session_id]['last_activity'] = time.time()

    # Trim history if too long
    if len(conversation_store[session_id]['messages']) > MAX_HISTORY_MESSAGES:
        conversation_store[session_id]['messages'] = conversation_store[session_id]['messages'][-MAX_HISTORY_MESSAGES:]

    logger.debug(f"Added to history for {session_id}: {role} - {content[:100]}...")

def cleanup_old_sessions():
    """Remove sessions that have been inactive for too long"""
    current_time = time.time()
    sessions_to_remove = []

    for session_id, session_data in conversation_store.items():
        if current_time - session_data['last_activity'] > SESSION_TIMEOUT:
            sessions_to_remove.append(session_id)

    for session_id in sessions_to_remove:
        del conversation_store[session_id]
        logger.info(f"Cleaned up inactive session: {session_id}")

    return len(sessions_to_remove)

# Load agent configuration dynamically
def load_agent_config():
    """Load agent configuration from config/agent_config.dev.json"""
    # Try multiple possible paths (from testing/ui to bedrock/config)
    possible_paths = [
        Path(__file__).parent / "../../config/agent_config.dev.json",               # bedrock/testing/ui -> bedrock/config
        Path(__file__).resolve().parent.parent.parent / "config" / "agent_config.dev.json",  # Absolute path
        Path(__file__).parent.parent / "config" / "agent_config.dev.json",          # Alternative
    ]

    for config_path in possible_paths:
        try:
            resolved_path = config_path.resolve()
            if resolved_path.exists():
                logger.info(f"✅ Loading agent config from: {resolved_path}")
                with open(resolved_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.debug(f"Could not load from {config_path}: {e}")
            continue

    # Fallback to hardcoded values if config not found
    logger.warning("⚠️  Could not find agent_config.dev.json, using hardcoded values")
    logger.warning(f"⚠️  Tried paths: {[str(p) for p in possible_paths]}")
    return {
        "supervisor_id": "76VIQYAT6R",
        "supervisor_alias": "TSTALIASID"
    }

# Load configuration at startup
AGENT_CONFIG = load_agent_config()
logger.info(f"📋 Loaded Supervisor Agent: {AGENT_CONFIG.get('supervisor_id')}")
logger.info(f"📋 Loaded Supervisor Alias: {AGENT_CONFIG.get('supervisor_alias')}")


def classify_intent_and_action(message, conversation_history=None):
    """
    Enhanced intent and action classification using Claude Sonnet with conversation context
    Returns: {'intent': 'scheduling', 'action': 'list_projects', 'can_call_direct': True}
    """
    import boto3

    # Build context from conversation history
    context_str = ""
    if conversation_history and len(conversation_history) > 0:
        context_str = "\n\nConversation history (most recent last):\n"
        # Include last 5 messages for context
        recent_history = conversation_history[-5:]
        for msg in recent_history:
            role = "User" if msg['role'] == 'user' else "Assistant"
            content = msg['content'][:200]  # Truncate long messages
            context_str += f"{role}: {content}\n"

    prompt = f"""You are an intent classifier for a property management scheduling system.

Classify the user message and determine if we can call Lambda directly or need an agent.
{context_str}
Current user message: "{message}"

Respond in JSON format with FOUR fields:
1. intent: scheduling/information/chitchat
2. action: specific action name (or null if needs agent conversation)
3. can_call_direct: true/false
4. params: object with extracted parameters (or null if none)

DIRECT Lambda actions (simple data retrieval - ALL are SCHEDULING intent):

list_projects:
- Examples: "show my projects", "list projects", "what projects do I have"
- Response: intent=scheduling, action=list_projects, can_call_direct=true, params=null

get_project_details:
- Examples: "show details for 7751742", "details for project 123", "show me project 7751742"
- Also handle references: "show me the first one", "the 3rd project", "project number 2 from the list"
- CRITICAL: Extract actual project_id from conversation history when user references position
- If user says "the first one" or "project 1", find the FIRST project_id from the previous project list
- If user says "the 3rd project" or "project 3", find the THIRD project_id from the previous project list
- DO NOT use the number itself as project_id - it's a position reference!
- Look for project lists in Assistant messages that contain "id" fields
- Response: intent=scheduling, action=get_project_details, can_call_direct=true, params with ACTUAL project_id (like "7751743" not "3")

get_available_dates:
- Examples: "show dates for project 123", "available dates", "when can I schedule project 456"
- Extract project_id if mentioned
- Response: intent=scheduling, action=get_available_dates, can_call_direct=true, params with project_id if found

get_time_slots:
- Examples: "show times for Nov 14", "available slots for Nov 14", "what times on November 14"
- Also handle: "go for Nov 12", "Nov 14", "I'll take November 15"
- Extract date from message
- CRITICAL: If conversation history shows available dates for a project, extract that project_id too
- Look for recent "get_available_dates" responses or project references in history
- Response: intent=scheduling, action=get_time_slots, can_call_direct=true, params with date AND project_id if found in context

NEEDS AGENT (requires conversation/confirmation):
- Booking/confirming appointments: needs confirmation dialog
- Rescheduling: needs conversation
- Canceling: needs confirmation
- Chitchat: conversational
- Information queries: weather, etc.

Example JSON responses (respond with VALID JSON only):

Example 1 - Direct ID:
For "show details for 7751742": {{"intent":"scheduling","action":"get_project_details","can_call_direct":true,"params":{{"project_id":"7751742"}}}}

Example 2 - Position reference (CRITICAL - extract from history):
History shows: projects with ids ["7751741", "7751742", "7751743", ...]
For "show me the 3rd project": {{"intent":"scheduling","action":"get_project_details","can_call_direct":true,"params":{{"project_id":"7751743"}}}}
Note: "3rd project" means the THIRD id from the list = "7751743", NOT the number 3!

Example 2b - Date selection with project context:
History shows: User asked "can you schedule 7751744", Agent showed available dates
For "go for Nov 12": {{"intent":"scheduling","action":"get_time_slots","can_call_direct":true,"params":{{"date":"2025-11-12","project_id":"7751744"}}}}
Note: Extract project_id from the scheduling context in history!

Example 3 - Other intents:
For "show my projects": {{"intent":"scheduling","action":"list_projects","can_call_direct":true,"params":null}}
For "book appointment": {{"intent":"scheduling","action":null,"can_call_direct":false,"params":null}}
For "hello": {{"intent":"chitchat","action":null,"can_call_direct":false,"params":null}}

Respond ONLY with the JSON object, nothing else."""

    try:
        bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
        response = bedrock_runtime.invoke_model(
            modelId='us.anthropic.claude-3-5-sonnet-20241022-v2:0',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 150,  # Increased from 50 to handle formatted JSON with whitespace
                "temperature": 0.0,
                "messages": [{"role": "user", "content": prompt}]
            })
        )

        response_body = json.loads(response['body'].read())
        classification_text = response_body['content'][0]['text'].strip()

        # Debug: log what the model returned
        logger.info(f"Raw classification response: {classification_text}")

        # Parse JSON response
        classification = json.loads(classification_text)

        logger.info(f"Classification: {classification} for message: '{message[:50]}...'")
        return classification

    except Exception as e:
        logger.error(f"Classification error: {e}")
        logger.error(f"Failed to parse classification text: {classification_text if 'classification_text' in locals() else 'N/A'}")
        # Fallback: return chitchat with no direct call
        return {'intent': 'chitchat', 'action': None, 'can_call_direct': False}


def classify_intent_simple(message):
    """
    Simple intent classification (legacy compatibility)
    Returns: 'scheduling', 'information', or 'chitchat'
    """
    classification = classify_intent_and_action(message)
    return classification['intent']


def call_lambda_directly(action, params):
    """
    Call Lambda function directly for simple actions
    Returns: Lambda response payload
    """
    import boto3

    lambda_client = boto3.client('lambda', region_name='us-east-1')

    # Map action to Lambda function
    lambda_functions = {
        'list_projects': 'pf-scheduling-actions',
        'get_project_details': 'pf-scheduling-actions',
        'get_available_dates': 'pf-scheduling-actions',
        'get_time_slots': 'pf-scheduling-actions'
    }

    function_name = lambda_functions.get(action)
    if not function_name:
        raise ValueError(f"Unknown action: {action}")

    # Construct Lambda event (Bedrock agent format)
    # Note: Lambda expects 'function' to be the action name
    event = {
        'actionGroup': 'scheduling-actions',
        'function': action,  # This is what Lambda uses to route
        'parameters': [
            {'name': key, 'value': str(value)}
            for key, value in params.items()
            if key not in ['customer_id', 'client_id', 'pf_bearer_token']
        ],
        'sessionAttributes': {
            'customer_id': params.get('customer_id', ''),
            'client_id': params.get('client_id', ''),
            'pf_bearer_token': params.get('pf_bearer_token', '')
        }
    }

    logger.debug(f"Lambda event: {json.dumps(event, indent=2)}")

    logger.info(f"⚡ Calling Lambda directly: {function_name}.{action}")

    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )

        payload = json.loads(response['Payload'].read())
        logger.info(f"✅ Lambda direct call successful")
        return payload

    except Exception as e:
        logger.error(f"Lambda direct call error: {e}")
        raise


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "service": "pf-proxy",
        "active_sessions": len(conversation_store),
        "features": {
            "direct_lambda": True,
            "conversation_history": True
        }
    })


@app.route('/api/conversation-history/<session_id>', methods=['GET'])
def get_session_history(session_id):
    """Get conversation history for a session (debugging endpoint)"""
    history = get_conversation_history(session_id)
    return jsonify({
        "session_id": session_id,
        "message_count": len(history),
        "messages": history
    })


@app.route('/api/login', methods=['POST'])
def login():
    """Proxy for login endpoint"""
    try:
        data = request.json
        logger.info(f"Login request for: {data.get('email', 'unknown')}")

        # Use the correct authentication endpoint
        response = requests.post(
            f"{PF_API_BASE}/authentication/login?identifier=projectsforce-validation",
            json=data,
            headers={"Content-Type": "application/json"}
        )

        logger.info(f"Login response status: {response.status_code}")

        # Return the response
        return jsonify(response.json()), response.status_code

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/validate-token', methods=['GET'])
def validate_token():
    """Proxy for token validation endpoint"""
    try:
        user_id = request.args.get('user_id', '1646085')
        identifier = request.args.get('identifier', 'projectsforce-validation')
        token = request.headers.get('Authorization', '').replace('Bearer ', '')

        logger.info(f"Validating token for user: {user_id}")

        response = requests.get(
            f"{PF_API_BASE}/authentication/token/{user_id}",
            params={"identifier": identifier},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )

        logger.info(f"Validation response status: {response.status_code}")

        return jsonify(response.json()), response.status_code

    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/dashboard', methods=['GET'])
def dashboard():
    """Proxy for dashboard/projects endpoint"""
    try:
        client_id = request.args.get('client_id', '09PF05VD')
        user_id = request.args.get('user_id', '1646085')
        token = request.headers.get('Authorization', '').replace('Bearer ', '')

        logger.info(f"Fetching dashboard for client: {client_id}, user: {user_id}")

        response = requests.get(
            f"{PF_API_BASE}/dashboard/get/{client_id}/{user_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )

        logger.info(f"Dashboard response status: {response.status_code}")

        return jsonify(response.json()), response.status_code

    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/invoke-agent', methods=['POST'])
def invoke_agent():
    """Proxy for invoking AWS Bedrock agent with streaming support"""
    try:
        import boto3

        # START PERFORMANCE TRACKING
        request_start = time.time()
        timing = {}

        data = request.json
        message = data.get('message', '')
        session_id = data.get('session_id', 'session-default')
        pf_token = data.get('pf_token', '')
        pf_client_id = data.get('pf_client_id', '09PF05VD')
        pf_user_id = data.get('pf_user_id', '1646085')
        stream = data.get('stream', False)  # Support both streaming and non-streaming

        logger.info(f"🚀 Invoking Bedrock agent with message: {message[:50]}... (stream={stream})")

        # Cleanup old sessions periodically
        cleanup_old_sessions()

        # Get conversation history for this session
        conversation_history = get_conversation_history(session_id)
        logger.info(f"📚 Session {session_id} has {len(conversation_history)} messages in history")

        # Add user message to history
        add_to_conversation_history(session_id, 'user', message)

        # Initialize Bedrock client
        init_start = time.time()
        bedrock_client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
        timing['boto3_init'] = time.time() - init_start

        # Determine routing based on config
        routing_config = AGENT_CONFIG.get('routing', {})
        use_supervisor = routing_config.get('use_supervisor', False)
        allow_direct_lambda = routing_config.get('allow_direct_lambda', True)  # NEW: enable direct Lambda calls

        # Enhanced classification with conversation context
        classification = classify_intent_and_action(message, conversation_history=conversation_history)
        intent = classification['intent']
        action = classification.get('action')
        can_call_direct = classification.get('can_call_direct', False)
        extracted_params = classification.get('params', {}) or {}  # Params extracted from message

        # OPTIMIZATION: Call Lambda directly for simple data retrieval
        if allow_direct_lambda and can_call_direct and action:
            logger.info(f"⚡ DIRECT LAMBDA CALL: {action} (bypassing agent)")
            logger.info(f"📋 Extracted params: {extracted_params}")

            try:
                lambda_start = time.time()

                # Prepare Lambda parameters (merge session params with extracted params)
                lambda_params = {
                    'customer_id': str(pf_user_id),
                    'client_id': pf_client_id,
                    'pf_bearer_token': pf_token,
                    **extracted_params  # Add extracted params from message
                }

                # Call Lambda directly
                lambda_response = call_lambda_directly(action, lambda_params)
                timing['lambda_direct'] = time.time() - lambda_start
                timing['total_request'] = time.time() - request_start

                # Extract response body from Lambda response
                # Lambda returns nested structure: response.functionResponse.responseBody.TEXT.body
                logger.debug(f"Lambda raw response: {json.dumps(lambda_response, indent=2)}")

                response_data = lambda_response.get('response', {})
                function_response = response_data.get('functionResponse', {})
                response_body_wrapper = function_response.get('responseBody', {})
                text_wrapper = response_body_wrapper.get('TEXT', {})
                response_body_str = text_wrapper.get('body', '{}')

                # Parse the JSON string
                if isinstance(response_body_str, str):
                    response_body = json.loads(response_body_str)
                else:
                    response_body = response_body_str

                # Format response for UI
                formatted_response = json.dumps(response_body, separators=(',', ':'))

                logger.info(f"⏱️  PERFORMANCE: Total={timing['total_request']:.2f}s | Lambda={timing['lambda_direct']:.2f}s | Init={timing['boto3_init']:.3f}s")
                logger.info(f"📝 Lambda response (first 100 chars): {formatted_response[:100]}...")

                # Add Lambda response to conversation history
                add_to_conversation_history(
                    session_id,
                    'assistant',
                    formatted_response,
                    metadata={
                        'action': action,
                        'intent': intent,
                        'direct_call': True,
                        'performance': timing
                    }
                )

                return jsonify({
                    "response": formatted_response,
                    "agent_name": "Direct Lambda",
                    "intent": intent,
                    "action": action,
                    "session_id": session_id,
                    "performance": timing,
                    "direct_call": True
                })

            except Exception as e:
                logger.error(f"Direct Lambda call failed: {e}, falling back to agent")
                # Fall through to agent invocation below

        # FALLBACK: Use Bedrock agent for complex queries or if direct call fails
        if use_supervisor:
            # Use Supervisor agent
            agent_id = AGENT_CONFIG.get('supervisor_id')
            alias_id = AGENT_CONFIG.get('supervisor_alias')
            agent_name = "Supervisor Agent"
            logger.info(f"Routing via SUPERVISOR: {agent_id} (Alias: {alias_id})")
        else:
            # Direct routing: route to appropriate agent
            agents = AGENT_CONFIG.get('agents', {})
            agent_config = agents.get(intent, agents.get('chitchat'))
            agent_id = agent_config['agent_id']
            alias_id = agent_config['alias_id']
            agent_name = f"{intent.capitalize()} Agent"
            logger.info(f"Routing to {intent.upper()} agent: {agent_id} (bypassing Supervisor)")

        # Invoke the selected agent
        invoke_start = time.time()
        response = bedrock_client.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=session_id,
            inputText=message,
            sessionState={
                'sessionAttributes': {
                    'customer_id': str(pf_user_id),
                    'client_id': pf_client_id,
                    'pf_bearer_token': pf_token
                }
            }
        )
        timing['bedrock_invoke'] = time.time() - invoke_start

        event_stream = response['completion']
        stream_start = time.time()

        if stream:
            # Stream response using Server-Sent Events
            def generate():
                try:
                    for event in event_stream:
                        if 'chunk' in event:
                            chunk = event['chunk']
                            if 'bytes' in chunk:
                                text = chunk['bytes'].decode('utf-8')
                                # Send as SSE format
                                yield f"data: {json.dumps({'chunk': text})}\n\n"
                    # Send completion event
                    yield f"data: {json.dumps({'done': True})}\n\n"
                except Exception as e:
                    logger.error(f"Streaming error: {str(e)}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"

            return app.response_class(
                generate(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'
                }
            )
        else:
            # Non-streaming: collect all chunks and return
            full_response = []
            for event in event_stream:
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        text = chunk['bytes'].decode('utf-8')
                        full_response.append(text)

            timing['stream_processing'] = time.time() - stream_start
            timing['total_request'] = time.time() - request_start

            response_text = ''.join(full_response)

            # Log performance metrics
            logger.info(f"⏱️  PERFORMANCE: Total={timing['total_request']:.2f}s | Invoke={timing['bedrock_invoke']:.2f}s | Stream={timing['stream_processing']:.2f}s | Init={timing['boto3_init']:.3f}s")
            logger.info(f"📝 Agent response: {response_text[:100]}...")

            # Add agent response to conversation history
            add_to_conversation_history(
                session_id,
                'assistant',
                response_text,
                metadata={
                    'agent_name': agent_name,
                    'intent': intent,
                    'direct_call': False,
                    'performance': timing
                }
            )

            return jsonify({
                "response": response_text,
                "agent_name": agent_name,
                "intent": intent,
                "session_id": session_id,
                "performance": timing
            })

    except Exception as e:
        logger.error(f"Agent invocation error: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("=" * 80)
    print("🚀 ProjectForce API Proxy Server")
    print("=" * 80)
    print()
    print("Server running on: http://localhost:5003")
    print()
    print("Endpoints:")
    print("  POST   /api/login           - Login and get token")
    print("  GET    /api/validate-token  - Validate token")
    print("  GET    /api/dashboard       - Get dashboard/projects")
    print("  POST   /api/invoke-agent    - Invoke AWS Bedrock agent")
    print("  GET    /health              - Health check")
    print()
    print("=" * 80)
    print()

    app.run(host='0.0.0.0', port=5003, debug=True)
