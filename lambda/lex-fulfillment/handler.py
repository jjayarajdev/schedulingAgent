"""
Lambda Function: Lex Fulfillment Handler (Production)

Fulfills simple Lex intents directly without calling Bedrock for fast responses.
Handles: Welcome, ProjectInquiry, CheckAvailability
Complex intents are handed off to voice-bedrock-bridge Lambda.

Environment Variables:
    DYNAMODB_TABLE: Session storage table
    SCHEDULING_LAMBDA: Scheduling actions Lambda function name
    INFORMATION_LAMBDA: Information actions Lambda function name
    VOICE_BRIDGE_LAMBDA: Voice-Bedrock bridge Lambda function name
    CUSTOMER_LOOKUP_LAMBDA: Customer lookup Lambda function name
    MAX_VOICE_RESPONSE_LENGTH: Maximum response length (default: 500)
    LOG_LEVEL: Logging level (default: INFO)
"""

import json
import boto3
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from decimal import Decimal

# Simple credentials helper - read from Secrets Manager with env fallback
def get_credentials_from_secrets():
    """Get all credentials from Secrets Manager (bearer_token, client_id, user_id)"""
    try:
        secrets_client = boto3.client('secretsmanager', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        response = secrets_client.get_secret_value(SecretId='projectforce/api/credentials')
        secret = json.loads(response['SecretString'])

        credentials = {
            'bearer_token': secret.get('bearer_token', ''),
            'client_id': secret.get('client_id', '09PF05VD'),
            'user_id': secret.get('user_id', '1646085')
        }

        logger.info(f"Using credentials from Secrets Manager - client_id: {credentials['client_id']}, user_id: {credentials['user_id']}")
        return credentials
    except Exception as e:
        logger.warning(f"Failed to get credentials from Secrets Manager: {e}, using fallback values")

        # Fallback to environment variables or defaults
        return {
            'bearer_token': os.environ.get('BEARER_TOKEN', ''),
            'client_id': os.environ.get('PF_CLIENT_ID', '09PF05VD'),
            'user_id': os.environ.get('PF_USER_ID', '1646085')
        }

# Pydantic models removed for simplicity - using raw dictionaries
# from models import (
#     LexEvent, LexResponse, Message, CustomerInfo,
#     ProjectListResponse, AvailabilityResponse,
#     LambdaInvocationRequest, BedrockHandoffRequest,
#     BedrockHandoffResponse, Project
# )
# from pydantic import ValidationError

# Configure logging
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

# Environment variables
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'pf-sessions-dev')
SCHEDULING_LAMBDA = os.environ.get('SCHEDULING_LAMBDA', 'pf-scheduling-actions')
INFORMATION_LAMBDA = os.environ.get('INFORMATION_LAMBDA', 'pf-information-actions')
ORCHESTRATOR_LAMBDA = os.environ.get('ORCHESTRATOR_LAMBDA', 'pf-orchestrator')
VOICE_BRIDGE_LAMBDA = os.environ.get('VOICE_BRIDGE_LAMBDA', 'pf-voice-bedrock-bridge-dev')
CUSTOMER_LOOKUP_LAMBDA = os.environ.get('CUSTOMER_LOOKUP_LAMBDA', 'pf-customer-lookup-dev')
DEFAULT_CUSTOMER_ID = os.environ.get('DEFAULT_CUSTOMER_ID')

# Feature flag: Use orchestrator for complex voice queries instead of voice-bridge
USE_ORCHESTRATOR_FOR_VOICE = os.environ.get('USE_ORCHESTRATOR_FOR_VOICE', 'true').lower() == 'true'
MAX_RESPONSE_LENGTH = int(os.environ.get('MAX_VOICE_RESPONSE_LENGTH', '500'))

# DynamoDB table
table = dynamodb.Table(DYNAMODB_TABLE)


class LexResponseBuilder:
    """Builds properly formatted Lex V2 responses"""

    @staticmethod
    def build_response(
        event: Dict[str, Any],
        message: str,
        should_end_session: bool = False,
        session_attributes: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Build a Lex V2 response

        Args:
            event: Original Lex event
            message: Response message text
            should_end_session: Whether to end the session
            session_attributes: Session attributes to maintain

        Returns:
            Properly formatted Lex V2 response dictionary
        """
        if session_attributes is None:
            session_attributes = event.get('sessionState', {}).get('sessionAttributes', {})

        # Truncate message if too long
        if len(message) > MAX_RESPONSE_LENGTH:
            message = message[:MAX_RESPONSE_LENGTH - 30] + "... Would you like more details?"

        intent = event['sessionState']['intent'].copy()
        intent['state'] = 'Fulfilled' if should_end_session else 'InProgress'

        response = {
            'sessionState': {
                'sessionAttributes': session_attributes,
                'dialogAction': {
                    'type': 'Close' if should_end_session else 'ElicitIntent'
                },
                'intent': intent
            },
            'messages': [
                {
                    'contentType': 'PlainText',
                    'content': message
                }
            ]
        }

        logger.debug(f"Built response: {json.dumps(response, default=str)}")
        return response

    @staticmethod
    def build_error_response(
        event: Dict[str, Any],
        error_message: str = "I'm experiencing technical difficulties. Please try again.",
        transfer_to_agent: bool = False
    ) -> Dict[str, Any]:
        """Build an error response with optional agent transfer"""
        if transfer_to_agent:
            error_message += " Press 0 to speak with a live agent."

        return LexResponseBuilder.build_response(event, error_message, should_end_session=False)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for Lex fulfillment

    Processes Lex V2 events and routes to appropriate intent handlers.

    Args:
        event: Lex V2 event dictionary
        context: Lambda context object

    Returns:
        Lex V2 response dictionary
    """
    request_id = context.request_id if hasattr(context, 'request_id') else 'unknown'
    logger.info(f"Request {request_id}: Processing Lex event")

    try:
        # Extract key information directly from event dictionary
        intent_name = event.get('sessionState', {}).get('intent', {}).get('name')
        session_id = event.get('sessionId', 'unknown')
        input_transcript = event.get('inputTranscript', '')

        # Get session attributes
        session_attributes = event.get('sessionState', {}).get('sessionAttributes', {})
        customer_id = session_attributes.get('customer_id')
        request_attributes = event.get('requestAttributes', {})
        customer_phone = (
            request_attributes.get('CustomerNumber') or
            session_attributes.get('customer_phone', 'unknown')
        )

        logger.info(
            f"Intent: {intent_name}, Session: {session_id}, "
            f"Customer: {customer_id or 'unknown'}, Phone: {_mask_phone(customer_phone)}"
        )

        # Route to intent handler
        if intent_name == "Welcome":
            response = handle_welcome(event, session_id, customer_id, customer_phone)

        elif intent_name == "ProjectInquiry":
            response = handle_project_inquiry(event, session_id, customer_id)

        elif intent_name == "ProjectStatusInquiry":
            response = handle_project_status_inquiry(event, session_id, customer_id)

        elif intent_name == "AppointmentInquiry":
            response = handle_appointment_inquiry(event, session_id, customer_id)

        elif intent_name == "CheckAvailability":
            response = handle_check_availability(event, session_id, customer_id)

        elif intent_name == "WeatherInquiry":
            response = handle_weather_inquiry(event, session_id, customer_id)

        elif intent_name in ["ScheduleAppointment", "UrgentRequest", "FallbackIntent"]:
            response = hand_off_to_bedrock(event, session_id, customer_id, input_transcript)

        else:
            logger.warning(f"Unknown intent: {intent_name}")
            response = LexResponseBuilder.build_response(
                event,
                "I'm not sure how to help with that. Let me transfer you to my advanced assistant."
            )

        logger.info(f"Request {request_id}: Successfully processed intent {intent_name}")
        return response

    except Exception as e:
        logger.exception(f"Request {request_id}: Error processing Lex event")
        return LexResponseBuilder.build_error_response(
            event,
            "I apologize, but I'm having trouble processing your request.",
            transfer_to_agent=True
        )


def handle_welcome(
    event: Dict[str, Any],
    session_id: str,
    customer_id: Optional[str],
    customer_phone: str
) -> Dict[str, Any]:
    """
    Handle Welcome intent - greet the caller

    If customer_id is not available, attempts to look up by phone number.

    Args:
        event: Lex event
        session_id: Session ID
        customer_id: Customer ID (if known)
        customer_phone: Customer phone number

    Returns:
        Lex response with greeting
    """
    logger.info(f"Handling Welcome intent for session {session_id}")

    # Try to lookup customer if not provided
    if not customer_id and customer_phone != 'unknown':
        logger.info(f"Attempting customer lookup by phone")
        customer_id = lookup_customer_by_phone(customer_phone)

        if customer_id:
            # Update session attributes
            session_attributes = event.get('sessionState', {}).get('sessionAttributes', {})
            session_attributes['customer_id'] = customer_id
            event['sessionState']['sessionAttributes'] = session_attributes
            logger.info(f"Customer found: {customer_id}")

    if customer_id:
        message = (
            "Hello! Welcome to ProjectForce. I'm your AI scheduling assistant. "
            "I can help you check your projects, schedule appointments, or answer questions. "
            "What would you like to do today?"
        )
    else:
        message = (
            "Hello! Welcome to ProjectForce. I'm your AI scheduling assistant. "
            "To get started, I'll need your customer ID. You can say it, "
            "or it might be on your recent invoice. What's your customer ID?"
        )

    return LexResponseBuilder.build_response(event, message)


def handle_project_inquiry(
    event: Dict[str, Any],
    session_id: str,
    customer_id: Optional[str]
) -> Dict[str, Any]:
    """
    Handle ProjectInquiry intent - list customer's projects

    Calls the scheduling-actions Lambda to retrieve projects.
    Supports optional status filter slot.

    Args:
        event: Lex event
        session_id: Session ID
        customer_id: Customer ID

    Returns:
        Lex response with project list or error
    """
    # Get credentials from Secrets Manager
    credentials = get_credentials_from_secrets()

    # Use user_id from Secrets Manager if customer_id not provided
    if not customer_id:
        customer_id = credentials['user_id']
        logger.info(f"Using customer ID from Secrets Manager: {customer_id}")

    # If still no customer_id (Secrets Manager was empty), ask user
    if not customer_id:
        return LexResponseBuilder.build_response(
            event,
            "I'll need your customer ID to look up your projects. What's your customer ID?"
        )

    logger.info(f"Handling ProjectInquiry for customer {customer_id}")

    # Extract status filter from slots if provided
    slots = event.get('sessionState', {}).get('intent', {}).get('slots', {})
    status_filter = slots.get('status', {}).get('value', {}).get('interpretedValue') if slots.get('status') else None

    try:
        # Get credentials from Secrets Manager
        client_id = credentials['client_id']
        pf_token = credentials['bearer_token']

        # Build Lambda invocation request
        payload = {
            'apiPath': '/list_projects',
            'httpMethod': 'POST',
            'requestContext': {'authorizer': {}},
            'sessionAttributes': {
                'customer_id': customer_id,
                'client_id': client_id,
                'pf_bearer_token': pf_token
            },
            'parameters': [
                {'name': 'customer_id', 'value': customer_id},
                {'name': 'client_id', 'value': client_id},
                {'name': 'pf_token', 'value': pf_token}
            ]
        }

        # Add status filter if provided
        if status_filter:
            payload['parameters'].append({'name': 'status', 'value': status_filter})
            logger.info(f"Filtering projects by status: {status_filter}")

        logger.debug(f"Invoking {SCHEDULING_LAMBDA} with payload: {json.dumps(payload)}")

        # Call scheduling-actions Lambda
        response = lambda_client.invoke(
            FunctionName=SCHEDULING_LAMBDA,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        result = json.loads(response['Payload'].read())

        # Parse Bedrock agent response format
        response_obj = result.get('response', {})
        http_status = response_obj.get('httpStatusCode')
        logger.info(f"Scheduling Lambda response: httpStatusCode={http_status}")

        # Parse response
        if http_status == 200:
            # Extract the body from Bedrock agent format
            response_body = response_obj.get('responseBody', {}).get('application/json', {}).get('body', '{}')
            if isinstance(response_body, str):
                response_data = json.loads(response_body)
            else:
                response_data = response_body

            # Store project IDs in session for follow-up questions
            projects = response_data.get('projects', [])
            project_ids = [str(p.get('id', '')) for p in projects if p.get('id')]

            # Get existing session attributes
            session_attributes = event.get('sessionState', {}).get('sessionAttributes', {}) or {}
            # Store project IDs as comma-separated string
            session_attributes['last_project_ids'] = ','.join(project_ids)

            message = _format_projects_for_voice(response_data)

            # Build response with updated session attributes
            response = LexResponseBuilder.build_response(event, message)
            if 'sessionState' in response:
                response['sessionState']['sessionAttributes'] = session_attributes

            return response

        else:
            logger.error(f"Invalid response from scheduling Lambda: {result}")
            return LexResponseBuilder.build_error_response(
                event,
                "I'm having trouble accessing your projects right now. Please try again."
            )

    except Exception as e:
        logger.exception("Error getting projects")
        return LexResponseBuilder.build_error_response(
            event,
            "I encountered an error looking up your projects. Let me transfer you to my advanced assistant."
        )


def handle_check_availability(
    event: Dict[str, Any],
    session_id: str,
    customer_id: Optional[str]
) -> Dict[str, Any]:
    """
    Handle CheckAvailability intent - get available appointment dates

    Requires project_id from slot values.

    Args:
        event: Lex event
        session_id: Session ID
        customer_id: Customer ID

    Returns:
        Lex response with availability or error
    """
    # Get credentials from Secrets Manager for customer_id fallback
    credentials = get_credentials_from_secrets()

    # Use user_id from Secrets Manager if customer_id not provided
    if not customer_id:
        customer_id = credentials['user_id']
        logger.info(f"Using customer ID from Secrets Manager: {customer_id}")

    logger.info(f"Handling CheckAvailability for customer {customer_id}")

    # Extract slots
    slots = event['sessionState']['intent'].get('slots', {})
    project_id_slot = slots.get('ProjectId', {}).get('value', {})
    project_id = project_id_slot.get('interpretedValue') if project_id_slot else None

    if not customer_id:
        return LexResponseBuilder.build_response(
            event,
            "I'll need your customer ID first. What's your customer ID?"
        )

    if not project_id:
        return LexResponseBuilder.build_response(
            event,
            "Which project would you like to check availability for? You can say the project number."
        )

    try:
        # Build Lambda invocation request
        payload = {
            'apiPath': '/get_available_dates',
            'httpMethod': 'POST',
            'sessionAttributes': {'customer_id': customer_id},
            'parameters': [
                {'name': 'project_id', 'value': str(project_id)}
            ]
        }

        logger.debug(f"Checking availability for project {project_id}")

        # Call scheduling-actions Lambda
        response = lambda_client.invoke(
            FunctionName=SCHEDULING_LAMBDA,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        result = json.loads(response['Payload'].read())

        # Parse Bedrock agent response format
        response_obj = result.get('response', {})
        http_status = response_obj.get('httpStatusCode')

        if http_status == 200:
            # Extract the body from Bedrock agent format
            response_body = response_obj.get('responseBody', {}).get('application/json', {}).get('body', '{}')
            if isinstance(response_body, str):
                response_data = json.loads(response_body)
            else:
                response_data = response_body

            message = _format_availability_for_voice(response_data)
            return LexResponseBuilder.build_response(event, message)

        else:
            return LexResponseBuilder.build_error_response(
                event,
                "I couldn't find availability for that project. Please verify the project number."
            )

    except Exception as e:
        logger.exception("Error checking availability")
        return LexResponseBuilder.build_error_response(
            event,
            "I encountered an error checking availability. Please try again."
        )


def handle_project_status_inquiry(
    event: Dict[str, Any],
    session_id: str,
    customer_id: Optional[str]
) -> Dict[str, Any]:
    """
    Handle ProjectStatusInquiry intent - Get status of a specific project

    Utterances: "What's the status of project 123", "Status of my project",
                "Tell me about the first project", "Who is the technician for second project"
    Slots: project_id (optional), status_filter (optional)

    Supports ordinal references (first, second, third, etc.) using session memory
    """
    session_attributes = event.get('sessionState', {}).get('sessionAttributes', {}) or {}
    slots = event.get('sessionState', {}).get('intent', {}).get('slots', {})

    # Get credentials from Secrets Manager for customer_id fallback
    credentials = get_credentials_from_secrets()

    # Use user_id from Secrets Manager if customer_id not provided
    if not customer_id:
        customer_id = credentials['user_id']
        logger.info(f"Using customer ID from Secrets Manager: {customer_id}")

    # If still no customer_id (Secrets Manager was empty), ask user
    if not customer_id:
        return LexResponseBuilder.build_response(
            event,
            "I'll need your customer ID to look up project details. What's your customer ID?"
        )

    # Extract project_id and status filter from slots
    project_id_raw = slots.get('project_id', {}).get('value', {}).get('interpretedValue') if slots.get('project_id') else None
    status_filter = slots.get('status', {}).get('value', {}).get('interpretedValue') if slots.get('status') else None

    try:
        # Resolve ordinal references (first, second, third, etc.)
        project_id = None
        if project_id_raw:
            ordinal_map = {
                'first': 0, '1st': 0, 'one': 0,
                'second': 1, '2nd': 1, 'two': 1,
                'third': 2, '3rd': 2, 'three': 2,
                'fourth': 3, '4th': 3, 'four': 3,
                'fifth': 4, '5th': 4, 'five': 4,
                'sixth': 5, '6th': 5, 'six': 5,
                'seventh': 6, '7th': 6, 'seven': 6,
                'eighth': 7, '8th': 7, 'eight': 7,
            }

            project_id_lower = project_id_raw.lower()
            if project_id_lower in ordinal_map:
                # Get stored project IDs from session
                last_project_ids = session_attributes.get('last_project_ids', '')
                if last_project_ids:
                    ids_list = last_project_ids.split(',')
                    index = ordinal_map[project_id_lower]
                    if index < len(ids_list):
                        project_id = ids_list[index]
                        logger.info(f"Resolved '{project_id_raw}' to project ID: {project_id}")
                    else:
                        return LexResponseBuilder.build_response(
                            event,
                            f"You only have {len(ids_list)} projects. Please ask about a valid project."
                        )
                else:
                    return LexResponseBuilder.build_response(
                        event,
                        "I don't have your project list in memory. Could you ask me to list your projects first?"
                    )
            else:
                # Direct project ID or number
                project_id = project_id_raw

        # Use credentials already fetched at start of function
        client_id = credentials['client_id']
        pf_token = credentials['bearer_token']

        # If we have a specific project ID, get details
        if project_id:
            payload = {
                'apiPath': f'/project_details/{project_id}',
                'httpMethod': 'GET',
                'requestContext': {'authorizer': {}},
                'sessionAttributes': {
                    'customer_id': customer_id,
                    'client_id': client_id,
                    'pf_bearer_token': pf_token
                },
                'parameters': [
                    {'name': 'project_id', 'value': project_id},
                    {'name': 'client_id', 'value': client_id}
                ]
            }

            logger.debug(f"Getting details for project {project_id}")

            # Call scheduling-actions Lambda
            response = lambda_client.invoke(
                FunctionName=SCHEDULING_LAMBDA,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )

            result = json.loads(response['Payload'].read())
            response_obj = result.get('response', {})
            http_status = response_obj.get('httpStatusCode')

            if http_status == 200:
                response_body = response_obj.get('responseBody', {}).get('application/json', {}).get('body', '{}')
                if isinstance(response_body, str):
                    response_body = json.loads(response_body)

                project = response_body.get('project', {})

                # Format detailed response
                message = f"Project {project.get('projectNumber', project_id)} is {project.get('status', 'unknown')}. "
                message += f"It's a {project.get('category', 'general')} project"

                if project.get('scheduledDate'):
                    message += f" scheduled for {project.get('scheduledDate')}"

                installer = project.get('installer', {})
                if installer and installer.get('name'):
                    message += f". The technician is {installer.get('name')}"

                address = project.get('address', {})
                if address and address.get('address1'):
                    message += f". Location: {address.get('address1')}, {address.get('city', '')} {address.get('state', '')}"

                message += ". Would you like to make any changes?"

                return LexResponseBuilder.build_response(event, message)
            else:
                return LexResponseBuilder.build_response(
                    event,
                    f"I couldn't find details for project {project_id}. Would you like me to list all your projects?"
                )

        # Otherwise, list projects with optional status filter
        else:
            payload = {
                'apiPath': '/list_projects',
                'httpMethod': 'POST',
                'requestContext': {'authorizer': {}},
                'sessionAttributes': {
                    'customer_id': customer_id,
                    'client_id': client_id,
                    'pf_bearer_token': pf_token
                },
                'parameters': [
                    {'name': 'customer_id', 'value': customer_id},
                    {'name': 'client_id', 'value': client_id}
                ]
            }

            # Add filters if provided
            if status_filter:
                payload['parameters'].append({'name': 'status', 'value': status_filter})

            logger.debug(f"Listing projects with status filter: {status_filter}")

            # Call scheduling-actions Lambda
            response = lambda_client.invoke(
                FunctionName=SCHEDULING_LAMBDA,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )

            result = json.loads(response['Payload'].read())
            response_obj = result.get('response', {})
            http_status = response_obj.get('httpStatusCode')

            if http_status == 200:
                response_body = response_obj.get('responseBody', {}).get('application/json', {}).get('body', '{}')
                if isinstance(response_body, str):
                    response_body = json.loads(response_body)

                projects = response_body.get('projects', [])

                # If status filter specified, filter and report
                if status_filter:
                    filtered = [p for p in projects if status_filter.lower() in p.get('status', '').lower()]
                    if filtered:
                        message = f"You have {len(filtered)} {status_filter} projects. "
                        if len(filtered) <= 5:
                            for i, p in enumerate(filtered, 1):
                                message += f"{i}. {p.get('category')} project {p.get('projectNumber')}, {p.get('status')}. "
                        else:
                            message += "Would you like me to list them all?"
                    else:
                        message = f"You don't have any {status_filter} projects right now."
                else:
                    message = f"You have {len(projects)} total projects. Would you like details on a specific one?"

                return LexResponseBuilder.build_response(event, message)
            else:
                return LexResponseBuilder.build_error_response(
                    event,
                    "I'm having trouble accessing your projects. Please try again."
                )

    except Exception as e:
        logger.exception("Error in project status inquiry")
        return LexResponseBuilder.build_error_response(
            event,
            "I encountered an error. Please try again."
        )


def handle_appointment_inquiry(
    event: Dict[str, Any],
    session_id: str,
    customer_id: Optional[str]
) -> Dict[str, Any]:
    """
    Handle AppointmentInquiry intent - List appointments/scheduled projects

    Utterances: "Do I have any appointments", "Show my appointments", "What's scheduled"
    """
    session_attributes = event.get('sessionState', {}).get('sessionAttributes', {})

    # Get credentials from Secrets Manager
    credentials = get_credentials_from_secrets()

    # Use user_id from Secrets Manager if customer_id not provided
    if not customer_id:
        customer_id = credentials['user_id']
        logger.info(f"Using customer ID from Secrets Manager: {customer_id}")

    # If still no customer_id (Secrets Manager was empty), ask user
    if not customer_id:
        return LexResponseBuilder.build_response(
            event,
            "I'll need your customer ID to check your appointments. What's your customer ID?"
        )

    try:
        client_id = credentials['client_id']
        pf_token = credentials['bearer_token']

        # Build Lambda invocation request with status filter for "Scheduled"
        payload = {
            'apiPath': '/list_projects',
            'httpMethod': 'POST',
            'requestContext': {'authorizer': {}},
            'sessionAttributes': {
                'customer_id': customer_id,
                'client_id': client_id,
                'pf_bearer_token': pf_token
            },
            'parameters': [
                {'name': 'customer_id', 'value': customer_id},
                {'name': 'client_id', 'value': client_id},
                {'name': 'status', 'value': 'Scheduled'}
            ]
        }

        logger.debug(f"Invoking {SCHEDULING_LAMBDA} for appointments")

        # Call scheduling-actions Lambda
        response = lambda_client.invoke(
            FunctionName=SCHEDULING_LAMBDA,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        result = json.loads(response['Payload'].read())
        response_obj = result.get('response', {})
        http_status = response_obj.get('httpStatusCode')

        if http_status == 200:
            response_body = response_obj.get('responseBody', {}).get('application/json', {}).get('body', '{}')
            if isinstance(response_body, str):
                response_body = json.loads(response_body)

            projects = response_body.get('projects', [])
            scheduled = [p for p in projects if 'scheduled' in p.get('status', '').lower() and p.get('scheduledDate')]

            if not scheduled:
                message = "You don't have any scheduled appointments at the moment. Would you like to schedule one?"
            elif len(scheduled) == 1:
                appt = scheduled[0]
                message = f"You have 1 appointment scheduled: {appt.get('category')} project on {appt.get('scheduledDate')}. Would you like to reschedule or cancel it?"
            else:
                message = f"You have {len(scheduled)} appointments scheduled. "
                for i, appt in enumerate(scheduled[:3], 1):
                    message += f"{i}. {appt.get('category')} project on {appt.get('scheduledDate')}. "
                if len(scheduled) > 3:
                    message += f"You have {len(scheduled) - 3} more appointments. "
                message += "Would you like to make any changes?"

            return LexResponseBuilder.build_response(event, message)

        else:
            return LexResponseBuilder.build_response(
                event,
                "I'm having trouble accessing your appointments right now. Please try again."
            )

    except Exception as e:
        logger.exception("Error in appointment inquiry")
        return LexResponseBuilder.build_error_response(
            event,
            "I encountered an error checking your appointments. Please try again."
        )


def handle_weather_inquiry(
    event: Dict[str, Any],
    session_id: str,
    customer_id: Optional[str]
) -> Dict[str, Any]:
    """
    Handle WeatherInquiry intent - Get weather forecast

    Utterances: "What's the weather", "How's the weather tomorrow", "Weather forecast"
    """
    try:
        # Extract location from slots if provided
        slots = event.get('sessionState', {}).get('intent', {}).get('slots', {})
        location_slot = slots.get('location', {}).get('value', {}) if slots.get('location') else None
        location = location_slot.get('interpretedValue') if location_slot else None

        # Get bearer token from Secrets Manager
        credentials = get_credentials_from_secrets()
        pf_token = credentials['bearer_token']

        # Build parameters - include location if provided
        parameters = []
        if location:
            parameters.append({'name': 'location', 'value': location})
            logger.info(f"Weather query for location: {location}")

        # Call information-actions Lambda for weather
        payload = {
            'apiPath': '/get-weather',
            'httpMethod': 'POST',
            'requestContext': {'authorizer': {}},
            'sessionAttributes': {
                'pf_bearer_token': pf_token
            },
            'parameters': parameters
        }

        logger.debug(f"Invoking information-actions Lambda for weather")

        response = lambda_client.invoke(
            FunctionName=INFORMATION_LAMBDA,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        result = json.loads(response['Payload'].read())
        logger.info(f"Weather Lambda response: httpStatusCode={result.get('statusCode')}")

        if result.get('statusCode') == 200:
            body = json.loads(result['body']) if isinstance(result.get('body'), str) else result.get('body', {})
            weather = body.get('weather', {})
            current = weather.get('current', {})

            # Format weather for voice
            location = weather.get('location', 'your area')
            temp = current.get('temp_f', 'unknown')
            condition = current.get('condition', 'unknown')

            message = f"The current temperature in {location} is {temp} degrees Fahrenheit with {condition} conditions."

            # Add forecast if available
            forecast = weather.get('forecast', [])
            if forecast:
                tomorrow = forecast[0]
                message += f" Tomorrow's forecast: high of {tomorrow.get('high_f')} degrees, low of {tomorrow.get('low_f')} degrees, {tomorrow.get('condition')}."

            return LexResponseBuilder.build_response(event, message)
        else:
            return LexResponseBuilder.build_response(
                event,
                "I'm having trouble getting the weather right now. Please try again."
            )

    except Exception as e:
        logger.exception("Error in weather inquiry")
        return LexResponseBuilder.build_error_response(
            event,
            "I encountered an error checking the weather. Please try again."
        )


# Voice-specific prompt wrapper for natural, elderly-friendly responses
VOICE_RESPONSE_INSTRUCTIONS = """
[VOICE CHANNEL - Respond as if speaking on a phone call to someone who may be elderly]

IMPORTANT VOICE GUIDELINES:
- Speak naturally and conversationally, like a friendly human assistant
- Be concise but complete - 2-3 short sentences max for the main answer
- NO technical jargon - use simple everyday words
- Lead with the most important information first
- For lists: mention the count, then highlight 2-3 most relevant items
- Offer to give more details: "Would you like to hear more about any of these?"
- Use natural pauses with commas
- Dates: say "November twenty-sixth" not "2025-11-26"
- Times: say "eight in the morning" not "08:00"
- Don't say "I found" or "I see" - just state the facts directly

USER'S SPOKEN REQUEST: {input_text}
"""


def wrap_for_voice(input_text: str) -> str:
    """
    Wrap user input with voice-specific instructions for Claude.
    This ensures natural, elderly-friendly responses without modifying orchestrator code.
    """
    return VOICE_RESPONSE_INSTRUCTIONS.format(input_text=input_text)


def hand_off_to_bedrock(
    event: Dict[str, Any],
    session_id: str,
    customer_id: Optional[str],
    input_text: str
) -> Dict[str, Any]:
    """
    Hand off complex queries to intelligent orchestrator (Claude-based routing)

    ARCHITECTURE CHANGE: Now routes through pf-orchestrator instead of pf-voice-bedrock-bridge
    This gives voice queries the same intelligent Claude Sonnet 3.7 routing as chat queries.

    VOICE ENHANCEMENT: Wraps user input with voice-specific instructions for natural responses.

    Used for: ScheduleAppointment, UrgentRequest, FallbackIntent

    Args:
        event: Lex event
        session_id: Session ID
        customer_id: Customer ID
        input_text: User's spoken input

    Returns:
        Lex response with orchestrator's response
    """
    logger.info(f"Routing complex query through orchestrator for session {session_id}")

    try:
        # Get all credentials from Secrets Manager
        credentials = get_credentials_from_secrets()
        pf_client_id = credentials['client_id']
        pf_token = credentials['bearer_token']

        # Get session attributes for context (e.g., last_project_ids)
        session_attributes = event.get('sessionState', {}).get('sessionAttributes', {}) or {}

        # Decide which routing to use based on feature flag
        if USE_ORCHESTRATOR_FOR_VOICE:
            # NEW: Route through intelligent orchestrator (Claude-based)
            logger.info(f"Routing through pf-orchestrator (intelligent Claude routing)")

            # Build context from session (for ordinal references like "second project")
            context_parts = []
            if session_attributes.get('last_project_ids'):
                project_ids = session_attributes['last_project_ids'].split(',')
                context_parts.append(f"[Context: User's project IDs from last query: {', '.join(project_ids)}. 'first'=ID {project_ids[0] if project_ids else 'none'}, 'second'=ID {project_ids[1] if len(project_ids) > 1 else 'none'}]")

            # Wrap input with voice-specific instructions for natural responses
            context_prefix = ' '.join(context_parts) + ' ' if context_parts else ''
            voice_enhanced_message = wrap_for_voice(context_prefix + input_text)
            logger.info(f"Voice-enhanced message prepared for Claude with context")

            # Build orchestrator payload
            payload = {
                'body': json.dumps({
                    'message': voice_enhanced_message,
                    'session_id': session_id,
                    'pf_token': pf_token,
                    'pf_client_id': pf_client_id,
                    'pf_user_id': customer_id or '0',
                    'channel': 'voice',
                    'session_context': session_attributes  # Pass Lex session context
                })
            }

            # Invoke pf-orchestrator Lambda
            response = lambda_client.invoke(
                FunctionName=ORCHESTRATOR_LAMBDA,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )

            result = json.loads(response['Payload'].read())
            logger.info(f"Orchestrator response: status={result.get('statusCode')}")

            # Parse orchestrator response
            if result.get('statusCode') == 200:
                body = result.get('body', '{}')
                if isinstance(body, str):
                    body = json.loads(body)

                orchestrator_message = body.get('response', 'I can help you with that.')

                # Strip any JSON code blocks for voice (orchestrator returns markdown-wrapped JSON)
                if '```json' in orchestrator_message:
                    # Extract just the user-facing message
                    import re
                    match = re.search(r'```json\s*({.*?})\s*```', orchestrator_message, re.DOTALL)
                    if match:
                        json_content = json.loads(match.group(1))
                        orchestrator_message = json_content.get('message', orchestrator_message)

                return LexResponseBuilder.build_response(event, orchestrator_message)
            else:
                logger.error(f"Orchestrator returned error: {result}")
                return LexResponseBuilder.build_error_response(
                    event,
                    "I'm experiencing technical difficulties. Please try again."
                )

        else:
            # OLD: Route through voice-bedrock-bridge (keyword matching) - DEPRECATED
            logger.warning(f"Using legacy voice-bridge routing (keyword matching)")

            session_attributes = event.get('sessionState', {}).get('sessionAttributes', {})

            payload = {
                'session_id': session_id,
                'customer_id': customer_id,
                'input_text': input_text,
                'channel': 'voice',
                'lex_event': event,
                'session_attributes': session_attributes
            }

            response = lambda_client.invoke(
                FunctionName=VOICE_BRIDGE_LAMBDA,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )

            result = json.loads(response['Payload'].read())
            logger.info(f"Voice bridge response: status={result.get('statusCode')}")

            if result.get('statusCode') == 200:
                bridge_message = result.get('response', 'I can help you with that.')
                return LexResponseBuilder.build_response(event, bridge_message)
            else:
                logger.error(f"Voice bridge returned error: {result}")
                return LexResponseBuilder.build_error_response(
                    event,
                    "I'm experiencing technical difficulties. Please try again."
                )

    except Exception as e:
        logger.exception("Error in complex query routing")
        return LexResponseBuilder.build_error_response(
            event,
            "I'm experiencing technical difficulties. Please try again in a moment."
        )


def lookup_customer_by_phone(phone_number: str) -> Optional[str]:
    """
    Look up customer ID by phone number

    Calls the customer-lookup Lambda function.

    Args:
        phone_number: Customer's phone number

    Returns:
        Customer ID if found, None otherwise
    """
    logger.info(f"Looking up customer by phone: {_mask_phone(phone_number)}")

    try:
        response = lambda_client.invoke(
            FunctionName=CUSTOMER_LOOKUP_LAMBDA,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'action': 'lookup_by_phone',
                'phone_number': phone_number
            })
        )

        result = json.loads(response['Payload'].read())

        if result.get('statusCode') == 200 and 'customer_id' in result:
            customer_id = result['customer_id']
            logger.info(f"Customer found: {customer_id}")
            return customer_id

        else:
            logger.warning("Customer not found")
            return None

    except Exception as e:
        logger.exception("Error looking up customer")
        return None


# ============================================================================
# Helper Functions
# ============================================================================

def _format_projects_for_voice(response_body: Dict[str, Any]) -> str:
    """
    Format projects response for voice output - ELDERLY FRIENDLY

    Natural, conversational format optimized for phone calls.
    Prioritizes clarity over completeness - offers to elaborate.
    """
    try:
        if isinstance(response_body, str):
            response_body = json.loads(response_body)

        projects_data = response_body.get('projects', [])
        projects = [p for p in projects_data if isinstance(p, dict)]

        if not projects:
            return "You don't have any active projects right now. Would you like to start a new one?"

        project_count = len(projects)

        # Group by status for smart summary
        scheduled = [p for p in projects if 'scheduled' in p.get('status', '').lower()]
        # Everything not scheduled needs scheduling
        not_scheduled = [p for p in projects if 'scheduled' not in p.get('status', '').lower()]

        if project_count == 1:
            p = projects[0]
            status = p.get('status', 'unknown').lower()
            category = p.get('category', 'home improvement')

            if 'scheduled' in status:
                date = p.get('scheduledDate', 'soon')
                return f"You have one {category} project scheduled for {date}. Would you like to change this appointment?"
            else:
                return f"You have one {category} project that needs scheduling. Would you like me to find available dates?"

        # Multiple projects - give smart summary
        message = f"You have {project_count} projects. "

        if scheduled:
            message += f"{len(scheduled)} already scheduled"
            if not_scheduled:
                message += f", and {len(not_scheduled)} waiting to be scheduled. "
            else:
                message += ". "
        elif not_scheduled:
            message += f"{len(not_scheduled)} need scheduling. "

        # Highlight the most actionable items (max 2)
        if not_scheduled:
            top_project = not_scheduled[0]
            message += f"Your {top_project.get('category', 'first')} project is ready to schedule. "

        message += "Would you like details on any of these, or shall we schedule one?"

        return message

    except Exception as e:
        logger.exception("Error formatting projects")
        return "I found your projects but had trouble reading them. Please try again."


def _format_availability_for_voice(response_body: Dict[str, Any]) -> str:
    """
    Format availability response for voice output - ELDERLY FRIENDLY

    Natural date reading optimized for phone calls.
    """
    try:
        if isinstance(response_body, str):
            response_body = json.loads(response_body)

        dates = response_body.get('available_dates', [])

        if not dates:
            return "No appointments are available right now. Would you like me to check again next week?"

        # Format dates naturally
        def format_date_natural(date_obj):
            """Convert date to natural speech like 'Monday the twenty-fifth' """
            try:
                date_str = date_obj.get('date') if isinstance(date_obj, dict) else str(date_obj)
                day_name = date_obj.get('day_name', '') if isinstance(date_obj, dict) else ''

                dt = datetime.strptime(date_str, '%Y-%m-%d')

                # Natural day format
                day = dt.day
                month = dt.strftime('%B')

                # Add ordinal suffix
                if 4 <= day <= 20 or 24 <= day <= 30:
                    suffix = "th"
                else:
                    suffix = ["st", "nd", "rd"][day % 10 - 1] if day % 10 <= 3 else "th"

                if day_name:
                    return f"{day_name} the {day}{suffix}"
                else:
                    return f"{month} {day}{suffix}"
            except:
                return str(date_obj)

        if len(dates) == 1:
            date_text = format_date_natural(dates[0])
            return f"I have one opening on {date_text}. Would you like to book it?"

        # Show first 3 dates max for voice
        top_dates = dates[:3]
        date_texts = [format_date_natural(d) for d in top_dates]

        if len(dates) <= 3:
            message = f"I have {len(dates)} openings: {', '.join(date_texts[:-1])}, and {date_texts[-1]}. Which works best for you?"
        else:
            message = f"I have {len(dates)} openings. The soonest are {', '.join(date_texts[:-1])}, and {date_texts[-1]}. "
            message += "Would you like one of these, or should I check later dates?"

        return message

    except Exception as e:
        logger.exception("Error formatting availability")
        return "I found some openings but had trouble reading them. Please try again."


def _mask_phone(phone: str) -> str:
    """Mask phone number for logging (PII protection)"""
    if not phone or phone == 'unknown':
        return 'unknown'

    if len(phone) > 4:
        return '*' * (len(phone) - 4) + phone[-4:]

    return '*' * len(phone)
