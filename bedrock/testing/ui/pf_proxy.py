#!/usr/bin/env python3
"""
Simple CORS proxy for ProjectForce API
Allows the HTML page to make API calls without CORS issues
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ProjectForce API base URL
PF_API_BASE = "https://api-cx-portal.dev.projectsforce.com"


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "service": "pf-proxy"})


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
    """Proxy for invoking AWS Bedrock agent"""
    try:
        import boto3

        data = request.json
        message = data.get('message', '')
        session_id = data.get('session_id', 'session-default')
        pf_token = data.get('pf_token', '')
        pf_client_id = data.get('pf_client_id', '09PF05VD')
        pf_user_id = data.get('pf_user_id', '1646085')

        logger.info(f"Invoking Bedrock agent with message: {message[:50]}...")

        # Initialize Bedrock client
        bedrock_client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

        # Get Supervisor agent ID from config or environment
        SUPERVISOR_AGENT_ID = 'WWBMPFWMNG'  # Your Supervisor agent ID

        # Invoke the Supervisor agent
        response = bedrock_client.invoke_agent(
            agentId=SUPERVISOR_AGENT_ID,
            agentAliasId='TSTALIASID',
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

        # Process the event stream
        event_stream = response['completion']
        full_response = []

        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    text = chunk['bytes'].decode('utf-8')
                    full_response.append(text)

        response_text = ''.join(full_response)
        logger.info(f"Agent response: {response_text[:100]}...")

        return jsonify({
            "response": response_text,
            "agent_name": "Supervisor Agent",
            "session_id": session_id
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
