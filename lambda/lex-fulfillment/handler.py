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
VOICE_BRIDGE_LAMBDA = os.environ.get('VOICE_BRIDGE_LAMBDA', 'pf-voice-bedrock-bridge-dev')
CUSTOMER_LOOKUP_LAMBDA = os.environ.get('CUSTOMER_LOOKUP_LAMBDA', 'pf-customer-lookup-dev')
DEFAULT_CUSTOMER_ID = os.environ.get('DEFAULT_CUSTOMER_ID')
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

        elif intent_name == "CheckAvailability":
            response = handle_check_availability(event, session_id, customer_id)

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

    Args:
        event: Lex event
        session_id: Session ID
        customer_id: Customer ID

    Returns:
        Lex response with project list or error
    """
    # Use default customer ID if not provided
    if not customer_id and DEFAULT_CUSTOMER_ID:
        customer_id = DEFAULT_CUSTOMER_ID
        logger.info(f"Using default customer ID: {customer_id}")

    logger.info(f"Handling ProjectInquiry for customer {customer_id}")

    if not customer_id:
        return LexResponseBuilder.build_response(
            event,
            "I'll need your customer ID to look up your projects. What's your customer ID?"
        )

    try:
        # Get client_id from environment variable
        client_id = os.environ.get('PF_CLIENT_ID', '09PF05VD')

        # Build Lambda invocation request
        payload = {
            'apiPath': '/list_projects',
            'httpMethod': 'POST',
            'requestContext': {'authorizer': {}},
            'sessionAttributes': {'customer_id': customer_id},
            'parameters': [
                {'name': 'customer_id', 'value': customer_id},
                {'name': 'client_id', 'value': client_id}
            ]
        }

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

            message = _format_projects_for_voice(response_data)
            return LexResponseBuilder.build_response(event, message)

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
    # Use default customer ID if not provided
    if not customer_id and DEFAULT_CUSTOMER_ID:
        customer_id = DEFAULT_CUSTOMER_ID
        logger.info(f"Using default customer ID: {customer_id}")

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


def hand_off_to_bedrock(
    event: Dict[str, Any],
    session_id: str,
    customer_id: Optional[str],
    input_text: str
) -> Dict[str, Any]:
    """
    Hand off complex queries to Bedrock bridge Lambda

    Used for: ScheduleAppointment, UrgentRequest, FallbackIntent

    Args:
        event: Lex event
        session_id: Session ID
        customer_id: Customer ID
        input_text: User's spoken input

    Returns:
        Lex response with Bedrock agent's response
    """
    logger.info(f"Handing off to Bedrock bridge for session {session_id}")

    try:
        # Get session attributes
        session_attributes = event.get('sessionState', {}).get('sessionAttributes', {})

        # Build handoff request
        payload = {
            'session_id': session_id,
            'customer_id': customer_id,
            'input_text': input_text,
            'channel': 'voice',
            'lex_event': event,
            'session_attributes': session_attributes
        }

        logger.debug(f"Invoking {VOICE_BRIDGE_LAMBDA}")

        # Invoke voice-bedrock-bridge Lambda
        response = lambda_client.invoke(
            FunctionName=VOICE_BRIDGE_LAMBDA,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        result = json.loads(response['Payload'].read())
        logger.info(f"Bedrock bridge response: status={result.get('statusCode')}")

        # Parse response
        if result.get('statusCode') == 200:
            bedrock_message = result.get('response', 'I can help you with that. Let me check...')
            return LexResponseBuilder.build_response(event, bedrock_message)

        else:
            logger.error(f"Bedrock bridge returned error: {result}")
            return LexResponseBuilder.build_error_response(
                event,
                "I'm experiencing technical difficulties. Please try again."
            )

    except Exception as e:
        logger.exception("Error calling Bedrock bridge")
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
    Format projects response for voice output

    Converts structured project data into natural speech format.
    Limits to 5 projects to avoid overwhelming the caller.
    """
    try:
        if isinstance(response_body, str):
            response_body = json.loads(response_body)

        projects_data = response_body.get('projects', [])

        # Use raw dictionary data (Pydantic removed for simplicity)
        projects = [p for p in projects_data if isinstance(p, dict)]

        if not projects:
            return "You don't have any projects in the system right now."

        elif len(projects) == 1:
            project = projects[0]
            return (
                f"You have 1 project: {project.get('category', 'unknown')} project {project.get('project_id', 'N/A')}, "
                f"currently {project.get('status', 'unknown')}. Would you like to schedule an appointment for it?"
            )

        else:
            project_count = len(projects)

            # Strategy: Read all projects if ≤10, use smart summarization if >10
            if project_count <= 10:
                # Read ALL projects in detail (up to 10 is manageable for voice)
                descriptions = []
                for i, project in enumerate(projects, 1):
                    descriptions.append(
                        f"{i}. {project.get('category', 'unknown')} project {project.get('project_id', 'N/A')}, {project.get('status', 'unknown')}"
                    )

                message = f"You have {project_count} projects. Here are your projects: "
                message += ". ".join(descriptions)
                message += ". Would you like to schedule an appointment for any of these?"

            else:
                # >10 projects: Use smart summarization with status breakdown
                # Group projects by status for better voice UX
                status_counts = {}
                for p in projects:
                    status = p.get('status', 'Unknown')
                    status_counts[status] = status_counts.get(status, 0) + 1

                # Read first 5 in detail, summarize the rest
                max_detailed = 5
                projects_to_detail = projects[:max_detailed]

                # Start with summary including status breakdown
                message = f"You have {project_count} projects: "
                status_parts = [f"{count} {status}" for status, count in status_counts.items()]
                message += f"{', '.join(status_parts)}. "

                # Read first 5 in detail
                message += f"Here are the first {max_detailed}: "
                descriptions = []
                for i, project in enumerate(projects_to_detail, 1):
                    descriptions.append(
                        f"{i}. {project.get('category', 'unknown')} project, {project.get('status', 'unknown')}"
                    )
                message += ". ".join(descriptions)

                # Mention remaining
                message += f". You have {project_count - max_detailed} more projects. Would you like to schedule an appointment?"

            return message

    except Exception as e:
        logger.exception("Error formatting projects")
        return "I found your projects but had trouble reading them. Please try again."


def _format_availability_for_voice(response_body: Dict[str, Any]) -> str:
    """
    Format availability response for voice output

    Converts available dates into natural speech format.
    """
    try:
        if isinstance(response_body, str):
            response_body = json.loads(response_body)

        # Use raw dictionary data (Pydantic removed for simplicity)
        dates = response_body.get('available_dates', [])

        if not dates:
            return "I'm sorry, there are no available dates for that project at the moment. Please check back later."

        # Limit to 5 dates
        dates_to_announce = dates[:5]

        date_list = []
        for date_obj in dates_to_announce:
            date_str = date_obj.get('date') if isinstance(date_obj, dict) else date_obj.date
            day_name = date_obj.get('day_name') if isinstance(date_obj, dict) else date_obj.day_name

            # Format for voice: "Monday, December 15th"
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                formatted_date = dt.strftime('%B %d')
                date_list.append(f"{day_name}, {formatted_date}")
            except:
                date_list.append(f"{day_name}, {date_str}")

        if len(dates_to_announce) == 1:
            message = f"There's 1 available date: {date_list[0]}. Would you like to book this date?"
        else:
            message = f"I found {len(dates)} available dates. Here are the first {len(dates_to_announce)}: "
            message += ", ".join(date_list[:-1])
            message += f", and {date_list[-1]}. "

            if len(dates) > 5:
                message += f"There are {len(dates) - 5} more dates available. "

            message += "Which date would you prefer?"

        return message

    except Exception as e:
        logger.exception("Error formatting availability")
        return "I found available dates but had trouble reading them. Please try again."


def _mask_phone(phone: str) -> str:
    """Mask phone number for logging (PII protection)"""
    if not phone or phone == 'unknown':
        return 'unknown'

    if len(phone) > 4:
        return '*' * (len(phone) - 4) + phone[-4:]

    return '*' * len(phone)
