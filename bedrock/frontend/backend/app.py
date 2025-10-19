#!/usr/bin/env python3
"""
Flask Backend for Bedrock Agent Chat UI
Handles Bedrock agent invocations with customer context
"""

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import boto3
import json
import time
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Bedrock configuration (load from agent_config.json)
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agent_config.json')

try:
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
        SUPERVISOR_ID = config['supervisor_id']
        SUPERVISOR_ALIAS = config['supervisor_alias']
        REGION = config.get('region', 'us-east-1')
except FileNotFoundError:
    # Fallback to hardcoded values
    SUPERVISOR_ID = 'V3BW0KFBMX'
    SUPERVISOR_ALIAS = 'K6BWBY1RNY'
    REGION = 'us-east-1'

# Sample user data (from mock data)
SAMPLE_USER = {
    'customer_id': 'CUST001',
    'customer_type': 'B2C',
    'name': 'John Doe',
    'email': 'john.doe@example.com',
    'projects': [
        {
            'id': '12345',
            'number': 'ORD-2025-001',
            'type': 'Installation',
            'category': 'Flooring',
            'status': 'Scheduled',
            'address': '123 Main St, Tampa, FL 33601',
            'scheduled_date': '2025-10-15',
            'scheduled_time': '08:00 AM - 12:00 PM',
            'technician': 'John Smith',
            'store': 'ST-101'
        },
        {
            'id': '12347',
            'number': 'ORD-2025-002',
            'type': 'Installation',
            'category': 'Windows',
            'status': 'Pending',
            'address': '456 Oak Ave, Tampa, FL 33602',
            'technician': 'Jane Doe',
            'store': 'ST-102'
        },
        {
            'id': '12350',
            'number': 'ORD-2025-003',
            'type': 'Repair',
            'category': 'Deck Repair',
            'status': 'Pending',
            'address': '789 Pine Dr, Clearwater, FL 33755',
            'technician': 'Mike Johnson',
            'store': 'ST-103'
        }
    ]
}

# Initialize Bedrock client
bedrock_client = boto3.client('bedrock-agent-runtime', region_name=REGION)


def invoke_agent_with_context(message, customer_id, customer_type='B2C'):
    """
    Invoke Bedrock agent with customer context (the working pattern)
    """

    # CRITICAL: Inject customer context into prompt
    augmented_prompt = f"""Session Context:
- Customer ID: {customer_id}
- Customer Type: {customer_type}

User Request: {message}

Please help the customer with their request using their customer ID for any actions."""

    session_id = f"session-{customer_id}-{int(time.time())}"

    try:
        response = bedrock_client.invoke_agent(
            agentId=SUPERVISOR_ID,
            agentAliasId=SUPERVISOR_ALIAS,
            sessionId=session_id,
            inputText=augmented_prompt,
            sessionState={
                'sessionAttributes': {
                    'customer_id': customer_id,
                    'customer_type': customer_type
                }
            }
        )

        # Stream response
        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    yield chunk['bytes'].decode('utf-8')

    except Exception as e:
        yield f"Error: {str(e)}"


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'supervisor_id': SUPERVISOR_ID,
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
        'supervisor_id': SUPERVISOR_ID,
        'supervisor_alias': SUPERVISOR_ALIAS,
        'region': REGION
    })


if __name__ == '__main__':
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  Bedrock Agent Chat Backend                                  ║
╚══════════════════════════════════════════════════════════════╝

Supervisor Agent: {SUPERVISOR_ID}
Alias: {SUPERVISOR_ALIAS}
Region: {REGION}

Sample User: {SAMPLE_USER['name']} ({SAMPLE_USER['customer_id']})

Starting server on http://localhost:5001
    """)

    app.run(debug=True, host='0.0.0.0', port=5001)
