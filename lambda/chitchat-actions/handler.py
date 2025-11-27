"""
Chitchat Actions Lambda Handler
Handles greetings, small talk, and general conversational queries

Actions:
1. greet - Respond to greetings (hi, hello, etc.)
2. help - Provide help information
3. general - General chitchat responses
"""

import json
import logging
from typing import Dict, Any
import random

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def extract_parameters(event: Dict) -> Dict[str, Any]:
    """Extract parameters from Bedrock Agent event"""
    try:
        if 'parameters' in event and event['parameters']:
            params = {p['name']: p['value'] for p in event['parameters']}
        elif 'requestBody' in event:
            content = event['requestBody'].get('content', {})
            app_json = content.get('application/json', {})

            if isinstance(app_json, dict) and 'properties' in app_json:
                params = {p['name']: p['value'] for p in app_json['properties']}
            elif isinstance(app_json, str):
                params = json.loads(app_json)
            else:
                params = app_json
        else:
            body = event.get('body', '{}')
            if isinstance(body, str):
                params = json.loads(body)
            else:
                params = body

        session_attrs = event.get('sessionAttributes', {})
        for key, value in params.items():
            if isinstance(value, str) and value.startswith('$'):
                attr_name = value[1:]
                if attr_name in session_attrs:
                    params[key] = session_attrs[attr_name]

        return params
    except Exception as e:
        logger.error(f"Error extracting parameters: {e}")
        return {}


def handle_greet(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle greeting messages"""
    greetings = [
        "Hello! I'm here to help you schedule appointments with our property management team. What would you like to do today?",
        "Hi there! How can I help you with your projects today?",
        "Hello! I can help you view your projects, check available dates, and schedule appointments. What would you like to do?",
        "Hi! Ready to help you manage your projects. What can I do for you?"
    ]

    response_text = random.choice(greetings)

    return {
        "message": response_text,
        "action": "greet"
    }


def handle_help(params: Dict[str, Any]) -> Dict[str, Any]:
    """Provide help information"""
    help_text = """I can help you with:
 View your projects (list my projects)
 Get project details (details for project 7751744)
 Check available dates (what dates are available for project 7751744)
 View time slots (show me time slots for Nov 25)
 Schedule appointments (schedule project 7751744)

Just ask me what you'd like to do!"""

    return {
        "message": help_text,
        "action": "help"
    }


def handle_general(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle general chitchat"""
    message = params.get('message', '').lower()

    responses = {
        'thanks': [
            "You're welcome! Is there anything else I can help you with?",
            "Happy to help! Let me know if you need anything else.",
            "No problem! What else can I do for you?"
        ],
        'bye': [
            "Goodbye! Feel free to come back if you need help with your projects.",
            "Take care! Let me know if you need anything.",
            "Bye! Have a great day!"
        ],
        'default': [
            "I'm here to help you with scheduling appointments and managing your projects. What would you like to do?",
            "I specialize in helping with project scheduling. How can I assist you today?",
            "I can help you view projects, check availability, and schedule appointments. What do you need?"
        ]
    }

    # Determine response type
    if any(word in message for word in ['thank', 'thanks', 'appreciate']):
        response_list = responses['thanks']
    elif any(word in message for word in ['bye', 'goodbye', 'see you', 'later']):
        response_list = responses['bye']
    else:
        response_list = responses['default']

    response_text = random.choice(response_list)

    return {
        "message": response_text,
        "action": "general_chitchat"
    }


def create_response(body: Dict[str, Any]) -> Dict[str, Any]:
    """Create Lambda response in Bedrock Agent format"""
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': 'chitchat-actions',
            'function': body.get('action', 'general'),
            'functionResponse': {
                'responseBody': {
                    'TEXT': {
                        'body': json.dumps(body)
                    }
                }
            }
        }
    }


def lambda_handler(event, context):
    """Main Lambda handler"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Extract function name and parameters
        function = event.get('function', event.get('apiPath', 'greet'))
        params = extract_parameters(event)

        logger.info(f"Function: {function}, Params: {params}")

        # Route to appropriate handler
        if function in ['greet', 'greeting', 'hello']:
            result = handle_greet(params)
        elif function in ['help', 'assistance']:
            result = handle_help(params)
        else:
            # Default to general chitchat
            result = handle_general(params)

        logger.info(f"Response: {result}")

        return create_response(result)

    except Exception as e:
        logger.error(f"Error in lambda_handler: {e}", exc_info=True)
        error_response = {
            "message": "I'm here to help with scheduling. What would you like to do?",
            "action": "error_recovery"
        }
        return create_response(error_response)
