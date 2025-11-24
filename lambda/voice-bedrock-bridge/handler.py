"""
Lambda Function: Voice-Bedrock Bridge (Production)

Bridges AWS Connect/Lex with Bedrock agents for complex voice interactions.
Handles agent selection, session management, and response formatting for voice.

Environment Variables:
    SUPERVISOR_AGENT_ID: Bedrock Supervisor agent ID
    SUPERVISOR_AGENT_ALIAS_ID: Agent alias ID
    SCHEDULING_AGENT_ID: Scheduling agent ID
    INFORMATION_AGENT_ID: Information agent ID
    CHITCHAT_AGENT_ID: Chitchat agent ID
    DYNAMODB_TABLE: Session storage table
    USE_SUPERVISOR: Use supervisor for routing (default: false)
    MAX_VOICE_RESPONSE_LENGTH: Max response chars (default: 500)
    ENABLE_SSML: Enable SSML formatting (default: false)
    LOG_LEVEL: Logging level (default: INFO)
"""

import json
import boto3
import os
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import uuid
import re
import logging

# Pydantic models removed for simplicity - using raw dictionaries
# from models import VoiceSession, BedrockRequest, BedrockResponse, AgentSelection
# from pydantic import ValidationError

# Configure logging
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)

# Initialize AWS clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
dynamodb = boto3.resource('dynamodb')

# Environment variables
SUPERVISOR_AGENT_ID = os.environ.get('SUPERVISOR_AGENT_ID')
SUPERVISOR_AGENT_ALIAS_ID = os.environ.get('SUPERVISOR_AGENT_ALIAS_ID', 'TSTALIASID')
SCHEDULING_AGENT_ID = os.environ.get('SCHEDULING_AGENT_ID')
INFORMATION_AGENT_ID = os.environ.get('INFORMATION_AGENT_ID')
CHITCHAT_AGENT_ID = os.environ.get('CHITCHAT_AGENT_ID')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'pf-sessions-dev')
USE_SUPERVISOR = os.environ.get('USE_SUPERVISOR', 'false').lower() == 'true'
MAX_RESPONSE_LENGTH = int(os.environ.get('MAX_VOICE_RESPONSE_LENGTH', '500'))
ENABLE_SSML = os.environ.get('ENABLE_SSML', 'false').lower() == 'true'

# DynamoDB table
table = dynamodb.Table(DYNAMODB_TABLE)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for voice-bedrock bridge

    Routes based on action:
    - Default: Bedrock agent invocation
    - lookup_customer: Customer lookup
    - call_start: Call initiation
    - call_end: Call termination

    Args:
        event: Lambda event
        context: Lambda context

    Returns:
        Response dictionary
    """
    request_id = context.request_id if hasattr(context, 'request_id') else 'unknown'
    logger.info(f"Request {request_id}: Processing voice-bedrock bridge")

    # Handle different event types
    action = event.get('action')

    try:
        if action == 'lookup_customer':
            return handle_customer_lookup(event)

        elif action == 'call_start':
            return handle_call_start(event)

        elif action == 'call_end':
            return handle_call_end(event)

        else:
            # Normal Bedrock invocation
            return handle_bedrock_invocation(event, request_id)

    except Exception as e:
        logger.exception(f"Request {request_id}: Error processing bridge request")
        return {
            'statusCode': 500,
            'error': 'Internal server error',
            'message': str(e)
        }


def handle_bedrock_invocation(event: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """
    Handle Bedrock agent invocation

    Args:
        event: Lambda event
        request_id: Request ID for logging

    Returns:
        Bedrock response
    """
    try:
        # Parse request from dictionary
        session_id = event.get('session_id', str(uuid.uuid4()))
        customer_id = event.get('customer_id')
        input_text = event.get('input_text', '')
        channel = event.get('channel', 'voice')
        session_attributes = event.get('session_attributes', {})

        logger.info(
            f"Request {request_id}: Session={session_id}, "
            f"Customer={customer_id or 'unknown'}, Input={input_text[:50]}..."
        )

        # Get or create session
        session = get_or_create_session(session_id, customer_id, channel)

        # Prepare session attributes
        session_attrs = prepare_session_attributes(
            customer_id,
            session,
            session_attributes
        )

        # Select appropriate agent
        agent_selection = select_agent(input_text, session)

        logger.info(f"Selected agent: {agent_selection['agent_type']} ({agent_selection['agent_id']})")

        # Invoke Bedrock agent
        start_time = datetime.utcnow()

        response_text = invoke_bedrock_agent(
            agent_id=agent_selection['agent_id'],
            agent_alias_id=agent_selection['agent_alias_id'],
            session_id=session_id,
            input_text=input_text,
            session_attributes=session_attrs
        )

        duration = (datetime.utcnow() - start_time).total_seconds()

        # Format for voice
        voice_response = format_for_voice(response_text)

        # Update session
        update_session(session_id, customer_id, input_text, voice_response)

        logger.info(f"Request {request_id}: Completed in {duration:.2f}s")

        # Build response
        return {
            'statusCode': 200,
            'session_id': session_id,
            'response': voice_response,
            'should_end_session': False,
            'agent_used': agent_selection['agent_id'],
            'duration_seconds': duration
        }

    except Exception as e:
        logger.exception(f"Request {request_id}: Error in Bedrock invocation")
        return {
            'statusCode': 500,
            'session_id': event.get('session_id', 'unknown'),
            'response': "I'm experiencing technical difficulties. Please try again, or press 0 to speak with an agent.",
            'should_end_session': False,
            'error': str(e)
        }


def invoke_bedrock_agent(
    agent_id: str,
    agent_alias_id: str,
    session_id: str,
    input_text: str,
    session_attributes: Dict[str, str]
) -> str:
    """
    Invoke Bedrock agent and stream response

    Args:
        agent_id: Bedrock agent ID
        agent_alias_id: Agent alias ID
        session_id: Session ID
        input_text: User input text
        session_attributes: Session attributes

    Returns:
        Full response text from agent
    """
    logger.info(f"Invoking Bedrock agent {agent_id}")

    try:
        response = bedrock_agent_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=input_text,
            sessionState={
                'sessionAttributes': session_attributes
            }
        )

        # Process streaming response
        full_response = ""
        event_stream = response['completion']

        for event in event_stream:
            if 'chunk' in event:
                chunk_data = event['chunk']
                if 'bytes' in chunk_data:
                    text = chunk_data['bytes'].decode('utf-8')
                    full_response += text

        logger.info(f"Received response ({len(full_response)} chars)")

        return full_response

    except Exception as e:
        logger.exception(f"Error invoking Bedrock agent {agent_id}")
        raise


def select_agent(input_text: str, session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Select appropriate Bedrock agent based on input

    Uses keyword matching for fast routing. Can be enhanced with ML classification.

    Args:
        input_text: User's input text
        session: Session data

    Returns:
        AgentSelection with agent ID and metadata
    """
    if USE_SUPERVISOR:
        return {
            'agent_id': SUPERVISOR_AGENT_ID,
            'agent_alias_id': SUPERVISOR_AGENT_ALIAS_ID,
            'agent_type': 'supervisor',
            'reason': 'Supervisor routing enabled'
        }

    # Direct agent selection based on keywords
    input_lower = input_text.lower()

    # Scheduling keywords
    scheduling_keywords = [
        'schedule', 'appointment', 'book', 'reschedule', 'cancel',
        'available', 'dates', 'times', 'slots', 'project', 'confirm'
    ]

    # Information keywords
    information_keywords = [
        'weather', 'forecast', 'temperature', 'rain', 'snow',
        'details', 'information', 'what is', 'tell me about'
    ]

    # Chitchat keywords
    chitchat_keywords = [
        'hello', 'hi', 'hey', 'thank', 'thanks', 'bye', 'goodbye',
        'help', 'how are you', 'good morning', 'good afternoon'
    ]

    # Count keyword matches
    scheduling_score = sum(1 for kw in scheduling_keywords if kw in input_lower)
    information_score = sum(1 for kw in information_keywords if kw in input_lower)
    chitchat_score = sum(1 for kw in chitchat_keywords if kw in input_lower)

    # Select agent with highest score
    if scheduling_score >= information_score and scheduling_score >= chitchat_score and scheduling_score > 0:
        return {
            'agent_id': SCHEDULING_AGENT_ID,
            'agent_alias_id': SUPERVISOR_AGENT_ALIAS_ID,
            'agent_type': 'scheduling',
            'confidence': min(1.0, scheduling_score / 3.0),
            'reason': f'Matched {scheduling_score} scheduling keywords'
        }

    elif information_score > chitchat_score and information_score > 0:
        return {
            'agent_id': INFORMATION_AGENT_ID,
            'agent_alias_id': SUPERVISOR_AGENT_ALIAS_ID,
            'agent_type': 'information',
            'confidence': min(1.0, information_score / 3.0),
            'reason': f'Matched {information_score} information keywords'
        }

    elif chitchat_score > 0:
        return {
            'agent_id': CHITCHAT_AGENT_ID,
            'agent_alias_id': SUPERVISOR_AGENT_ALIAS_ID,
            'agent_type': 'chitchat',
            'confidence': min(1.0, chitchat_score / 2.0),
            'reason': f'Matched {chitchat_score} chitchat keywords'
        }

    # Default to scheduling (most common)
    else:
        return {
            'agent_id': SCHEDULING_AGENT_ID,
            'agent_alias_id': SUPERVISOR_AGENT_ALIAS_ID,
            'agent_type': 'scheduling',
            'confidence': 0.5,
            'reason': 'Default routing (no clear keywords)'
        }


def format_for_voice(text: str) -> str:
    """
    Format Bedrock response for voice output

    Removes markdown, simplifies language, adds pauses, limits length.

    Args:
        text: Raw text from Bedrock agent

    Returns:
        Voice-optimized text
    """
    # Remove markdown formatting
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *italic*
    text = re.sub(r'`([^`]+)`', r'\1', text)        # `code`
    text = re.sub(r'#{1,6}\s*', '', text)           # # headers
    text = re.sub(r'>\s*', '', text)                # > quotes

    # Remove JSON/code blocks
    text = re.sub(r'```json.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)

    # Replace newlines
    text = text.replace('\n\n', '. ')
    text = text.replace('\n', '. ')

    # Simplify phrases for voice
    replacements = {
        'Let me': "I'll",
        'I would recommend': 'I recommend',
        'Please note that': 'Note:',
        'In order to': 'To',
        'It is important to': 'Important:',
        'You should': 'Please',
        'project ID': 'project',
        'ID number': 'number',
        'appointment': 'booking'
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Clean up spacing
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\.+', '.', text)
    text = text.strip()

    # Limit length
    if len(text) > MAX_RESPONSE_LENGTH:
        # Find last complete sentence within limit
        truncated = text[:MAX_RESPONSE_LENGTH]
        last_period = truncated.rfind('.')

        if last_period > MAX_RESPONSE_LENGTH * 0.7:
            text = text[:last_period + 1]
        else:
            text = truncated

        text += " Would you like me to continue?"

    # Add SSML if enabled
    if ENABLE_SSML:
        text = wrap_with_ssml(text)

    return text


def wrap_with_ssml(text: str) -> str:
    """
    Wrap text with SSML tags for better voice output

    Args:
        text: Plain text

    Returns:
        SSML-formatted text
    """
    # Add pauses after sentences
    text = text.replace('. ', '. <break time="500ms"/> ')

    # Emphasize important words
    emphasis_words = ['important', 'urgent', 'required', 'must', 'critical']

    for word in emphasis_words:
        pattern = rf'\b{word}\b'
        replacement = f'<emphasis level="strong">{word}</emphasis>'
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Wrap in speak tags
    return f'<speak>{text}</speak>'


def prepare_session_attributes(
    customer_id: Optional[str],
    session: Dict[str, Any],
    extra_attributes: Dict[str, str]
) -> Dict[str, str]:
    """
    Prepare session attributes for Bedrock

    Args:
        customer_id: Customer ID
        session: Session data
        extra_attributes: Additional attributes

    Returns:
        Combined session attributes
    """
    attributes = {
        'channel': 'voice',
        'interaction_type': 'voice_call'
    }

    if customer_id:
        attributes['customer_id'] = str(customer_id)

    # Add session context
    if session.get('context'):
        attributes['context'] = json.dumps(session['context'])

    # Merge extra attributes
    attributes.update(extra_attributes)

    return attributes


def get_or_create_session(
    session_id: str,
    customer_id: Optional[str],
    channel: str
) -> Dict[str, Any]:
    """
    Get existing session or create new one

    Args:
        session_id: Session ID
        customer_id: Customer ID
        channel: Communication channel

    Returns:
        Session data
    """
    try:
        response = table.get_item(Key={'session_id': session_id})

        if 'Item' in response:
            logger.info("Found existing session")
            return response['Item']

        else:
            # Create new session
            logger.info("Creating new session")

            session = {
                'session_id': session_id,
                'customer_id': customer_id,
                'channel': channel,
                'created_at': int(datetime.utcnow().timestamp() * 1000),
                'last_activity': int(datetime.utcnow().timestamp() * 1000),
                'messages': [],
                'message_count': 0
            }

            table.put_item(Item=session)

            return session

    except Exception as e:
        logger.exception("Error accessing DynamoDB")

        # Return minimal session data
        return {
            'session_id': session_id,
            'customer_id': customer_id,
            'channel': channel,
            'created_at': int(datetime.utcnow().timestamp() * 1000),
            'last_activity': int(datetime.utcnow().timestamp() * 1000),
            'messages': [],
            'message_count': 0
        }


def update_session(
    session_id: str,
    customer_id: Optional[str],
    user_input: str,
    agent_response: str
) -> None:
    """
    Update session with new conversation turn

    Args:
        session_id: Session ID
        customer_id: Customer ID
        user_input: User's input
        agent_response: Agent's response
    """
    try:
        current_time = int(datetime.utcnow().timestamp() * 1000)

        # Create message objects
        user_message = {
            'role': 'user',
            'content': user_input,
            'timestamp': current_time
        }

        agent_message = {
            'role': 'assistant',
            'content': agent_response,
            'timestamp': current_time + 1
        }

        # Update DynamoDB
        table.update_item(
            Key={'session_id': session_id},
            UpdateExpression='SET last_activity = :time, messages = list_append(if_not_exists(messages, :empty), :new_msgs), message_count = if_not_exists(message_count, :zero) + :two',
            ExpressionAttributeValues={
                ':time': current_time,
                ':empty': [],
                ':new_msgs': [user_message, agent_message],
                ':zero': 0,
                ':two': 2
            }
        )

        logger.info("Session updated successfully")

    except Exception as e:
        logger.exception("Error updating session")


# ============================================================================
# Event Handlers
# ============================================================================

def handle_customer_lookup(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle customer lookup by phone number"""
    phone_number = event.get('phone_number')

    logger.info(f"Customer lookup requested")

    # TODO: Integrate with customer-lookup Lambda
    # For now, return not implemented

    return {
        'statusCode': 501,
        'customer_id': None,
        'customer_found': False,
        'message': 'Customer lookup not yet implemented - integrate with customer-lookup Lambda'
    }


def handle_call_start(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle call initiation event from Connect

    Args:
        event: Connect event

    Returns:
        Response with session ID and greeting
    """
    contact_id = event.get('Details', {}).get('ContactData', {}).get('ContactId')
    customer_phone = event.get('Details', {}).get('ContactData', {}).get('CustomerEndpoint', {}).get('Address')

    logger.info(f"Call started: Contact={contact_id}")

    session_id = f"voice-{contact_id}"

    get_or_create_session(session_id, None, 'voice')

    return {
        'statusCode': 200,
        'session_id': session_id,
        'greeting': "Thank you for calling ProjectForce. How can I help you today?"
    }


def handle_call_end(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle call termination event from Connect

    Args:
        event: Connect event

    Returns:
        Response confirming call ended
    """
    contact_id = event.get('Details', {}).get('ContactData', {}).get('ContactId')
    session_id = f"voice-{contact_id}"

    logger.info(f"Call ended: Contact={contact_id}")

    try:
        table.update_item(
            Key={'session_id': session_id},
            UpdateExpression='SET call_status = :status, ended_at = :ended_at',
            ExpressionAttributeValues={
                ':status': 'completed',
                ':ended_at': int(datetime.utcnow().timestamp() * 1000)
            }
        )
    except Exception as e:
        logger.exception("Error updating session on call end")

    return {
        'statusCode': 200,
        'session_id': session_id,
        'message': 'Call ended successfully'
    }
