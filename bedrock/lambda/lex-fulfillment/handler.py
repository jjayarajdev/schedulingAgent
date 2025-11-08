"""
Lambda Function: Lex Fulfillment Handler
Purpose: Fulfill simple Lex intents directly without calling Bedrock
Author: ProjectForce Team
Phase: 3 - Voice Integration
"""

import json
import boto3
import os
from typing import Dict, Any
from datetime import datetime

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

# Environment variables
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'pf-session-data-dev')
INFORMATION_LAMBDA = os.environ.get('INFORMATION_LAMBDA', 'pf-information-actions')
VOICE_BRIDGE_LAMBDA = os.environ.get('VOICE_BRIDGE_LAMBDA', 'pf-voice-bedrock-bridge')

# DynamoDB table
table = dynamodb.Table(DYNAMODB_TABLE)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for Lex fulfillment

    Routes based on intent:
    - Simple intents: Fulfill directly
    - Complex intents: Hand off to Bedrock bridge
    """
    print(f"Received Lex event: {json.dumps(event)}")

    # Extract Lex event details
    intent_name = event['sessionState']['intent']['name']
    session_id = event['sessionId']

    # Get customer info from session attributes
    session_attributes = event.get('sessionState', {}).get('sessionAttributes', {})
    customer_id = session_attributes.get('customer_id')
    customer_phone = event.get('requestAttributes', {}).get('CustomerNumber', 'unknown')

    print(f"Intent: {intent_name}, Session: {session_id}, Customer: {customer_id}")

    # Route based on intent
    if intent_name == "Welcome":
        return handle_welcome(event, session_id, customer_id)

    elif intent_name == "ProjectInquiry":
        return handle_project_inquiry(event, session_id, customer_id)

    elif intent_name == "ScheduleAppointment":
        # Complex - hand off to Bedrock
        return hand_off_to_bedrock(event, session_id, customer_id)

    elif intent_name == "UrgentRequest":
        # Complex - hand off to Bedrock
        return hand_off_to_bedrock(event, session_id, customer_id)

    elif intent_name == "FallbackIntent":
        # Always hand off fallback to Bedrock
        return hand_off_to_bedrock(event, session_id, customer_id)

    else:
        return create_lex_response(
            event,
            "I'm not sure how to help with that. Let me transfer you to my advanced assistant.",
            should_end_session=False
        )


def handle_welcome(event: Dict[str, Any], session_id: str, customer_id: str = None) -> Dict[str, Any]:
    """Handle welcome/greeting intent"""

    if customer_id:
        message = (
            f"Hello! Welcome to ProjectForce. I'm your AI scheduling assistant. "
            f"I can help you check your projects, schedule appointments, or answer questions. "
            f"What would you like to do today?"
        )
    else:
        message = (
            "Hello! Welcome to ProjectForce. I'm your AI scheduling assistant. "
            "To get started, I'll need to look up your account. What's your customer ID or project number?"
        )

    return create_lex_response(event, message, should_end_session=False)


def handle_project_inquiry(event: Dict[str, Any], session_id: str, customer_id: str = None) -> Dict[str, Any]:
    """Handle project inquiry intent - list projects"""

    if not customer_id:
        return create_lex_response(
            event,
            "I'll need your customer ID to look up your projects. What's your customer ID?",
            should_end_session=False
        )

    try:
        # Call information-actions Lambda to get projects
        response = lambda_client.invoke(
            FunctionName=INFORMATION_LAMBDA,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'apiPath': '/get_projects',
                'httpMethod': 'POST',
                'parameters': [
                    {'name': 'customer_id', 'value': customer_id}
                ]
            })
        )

        result = json.loads(response['Payload'].read())
        print(f"Information Lambda response: {result}")

        # Parse the response
        if 'response' in result and 'responseBody' in result['response']:
            body_str = result['response']['responseBody']['application/json']['body']
            projects_data = json.loads(body_str)
            projects = projects_data.get('projects', [])

            if not projects:
                message = "You don't have any projects in the system right now."
            elif len(projects) == 1:
                project = projects[0]
                message = (
                    f"You have 1 project: {project.get('category', 'Unknown')} project "
                    f"{project.get('project_id', '')}, currently {project.get('status', 'pending')}."
                )
            else:
                project_list = []
                for i, project in enumerate(projects[:5], 1):  # Limit to 5 for voice
                    status = project.get('status', 'pending')
                    category = project.get('category', 'Unknown')
                    project_list.append(f"{i}. {category} project, {status}")

                message = f"You have {len(projects)} projects. Here are your first {min(len(projects), 5)}: " + ", ".join(project_list)

                if len(projects) > 5:
                    message += f". You have {len(projects) - 5} more projects."

            return create_lex_response(event, message, should_end_session=False)

        else:
            return create_lex_response(
                event,
                "I'm having trouble accessing your projects right now. Please try again.",
                should_end_session=False
            )

    except Exception as e:
        print(f"Error getting projects: {e}")
        return create_lex_response(
            event,
            "I encountered an error looking up your projects. Let me transfer you to my advanced assistant.",
            should_end_session=False
        )


def hand_off_to_bedrock(event: Dict[str, Any], session_id: str, customer_id: str = None) -> Dict[str, Any]:
    """Hand off complex query to Bedrock bridge Lambda"""

    try:
        # Get the user's input text
        input_text = event.get('inputTranscript', '')

        # Invoke voice-bedrock-bridge Lambda
        response = lambda_client.invoke(
            FunctionName=VOICE_BRIDGE_LAMBDA,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'session_id': session_id,
                'customer_id': customer_id,
                'input_text': input_text,
                'channel': 'voice',
                'lex_event': event
            })
        )

        result = json.loads(response['Payload'].read())
        print(f"Bedrock bridge response: {result}")

        # Extract Bedrock response
        bedrock_message = result.get('response', 'I can help you with that. Let me check...')

        return create_lex_response(event, bedrock_message, should_end_session=False)

    except Exception as e:
        print(f"Error calling Bedrock bridge: {e}")
        return create_lex_response(
            event,
            "I'm experiencing technical difficulties. Please try again in a moment.",
            should_end_session=False
        )


def create_lex_response(
    event: Dict[str, Any],
    message: str,
    should_end_session: bool = False
) -> Dict[str, Any]:
    """Create a properly formatted Lex V2 response"""

    session_attributes = event.get('sessionState', {}).get('sessionAttributes', {})

    response = {
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Close' if should_end_session else 'ElicitIntent'
            },
            'intent': event['sessionState']['intent']
        },
        'messages': [
            {
                'contentType': 'PlainText',
                'content': message
            }
        ]
    }

    return response


def save_voice_session(session_id: str, customer_id: str, data: Dict[str, Any]) -> None:
    """Save voice session data to DynamoDB"""

    try:
        table.put_item(
            Item={
                'session_id': session_id,
                'customer_id': customer_id,
                'channel': 'voice',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'session_data': data
            }
        )
    except Exception as e:
        print(f"Error saving session: {e}")
