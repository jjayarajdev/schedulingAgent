"""
Lambda Function: Voice-Bedrock Bridge
Purpose: Bridge between AWS Connect/Lex and Bedrock Supervisor Agent
Author: ProjectForce Team
Phase: 3 - Voice Integration
"""

import json
import boto3
import os
from typing import Dict, Any, List
from datetime import datetime
import uuid

# Initialize AWS clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
dynamodb = boto3.resource('dynamodb')

# Environment variables
SUPERVISOR_AGENT_ID = os.environ.get('SUPERVISOR_AGENT_ID')
SUPERVISOR_AGENT_ALIAS_ID = os.environ.get('SUPERVISOR_AGENT_ALIAS_ID', 'TSTALIASID')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'pf-session-data-dev')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

# DynamoDB table
table = dynamodb.Table(DYNAMODB_TABLE)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for voice-bedrock bridge

    Receives input from Lex or Connect, sends to Bedrock Supervisor,
    returns formatted response suitable for voice
    """
    print(f"Received event: {json.dumps(event)}")

    # Extract parameters
    session_id = event.get('session_id', str(uuid.uuid4()))
    customer_id = event.get('customer_id')
    input_text = event.get('input_text', '')
    channel = event.get('channel', 'voice')

    # Get or create session
    session_data = get_or_create_session(session_id, customer_id, channel)

    # Prepare session attributes for Bedrock
    session_attributes = prepare_session_attributes(customer_id, session_data)

    try:
        # Invoke Bedrock Supervisor Agent
        response = invoke_bedrock_agent(
            agent_id=SUPERVISOR_AGENT_ID,
            agent_alias_id=SUPERVISOR_AGENT_ALIAS_ID,
            session_id=session_id,
            input_text=input_text,
            session_attributes=session_attributes
        )

        # Extract and format response for voice
        voice_response = format_for_voice(response)

        # Update session
        update_session(session_id, customer_id, input_text, voice_response)

        return {
            'statusCode': 200,
            'session_id': session_id,
            'response': voice_response,
            'should_end_session': False
        }

    except Exception as e:
        print(f"Error invoking Bedrock: {e}")
        return {
            'statusCode': 500,
            'session_id': session_id,
            'response': "I'm experiencing technical difficulties. Please try again in a moment, or press 0 to speak with an agent.",
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
    Invoke Bedrock Supervisor Agent and stream response
    """
    print(f"Invoking Bedrock agent {agent_id} with session {session_id}")

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
                print(f"Received chunk: {text}")

    print(f"Full Bedrock response: {full_response}")
    return full_response


def format_for_voice(text: str) -> str:
    """
    Format Bedrock response for voice output

    - Remove markdown formatting
    - Simplify complex sentences
    - Add pauses for better speech
    - Limit length for voice
    """

    # Remove markdown
    text = text.replace('**', '').replace('*', '').replace('`', '')
    text = text.replace('#', '').replace('>', '')

    # Replace newlines with pauses (for SSML)
    text = text.replace('\n\n', '. ')
    text = text.replace('\n', '. ')

    # Simplify common phrases
    text = text.replace('Let me', "I'll")
    text = text.replace('I would recommend', "I recommend")
    text = text.replace('Please note that', 'Note:')

    # Limit length for voice (max ~500 chars per response)
    if len(text) > 500:
        # Find last sentence within 500 chars
        truncated = text[:500]
        last_period = truncated.rfind('.')
        if last_period > 0:
            text = text[:last_period + 1]
        else:
            text = truncated + "..."

        text += " Would you like me to continue?"

    return text.strip()


def prepare_session_attributes(customer_id: str, session_data: Dict[str, Any]) -> Dict[str, str]:
    """Prepare session attributes for Bedrock"""

    attributes = {
        'channel': 'voice',
        'interaction_type': 'voice_call'
    }

    if customer_id:
        attributes['customer_id'] = str(customer_id)

    # Add any existing session context
    if session_data.get('context'):
        attributes['context'] = json.dumps(session_data['context'])

    return attributes


def get_or_create_session(session_id: str, customer_id: str, channel: str) -> Dict[str, Any]:
    """Get existing session or create new one"""

    try:
        response = table.get_item(Key={'session_id': session_id})

        if 'Item' in response:
            return response['Item']
        else:
            # Create new session
            new_session = {
                'session_id': session_id,
                'customer_id': customer_id,
                'channel': channel,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'conversation_history': [],
                'context': {}
            }
            table.put_item(Item=new_session)
            return new_session

    except Exception as e:
        print(f"Error accessing DynamoDB: {e}")
        # Return minimal session data
        return {
            'session_id': session_id,
            'customer_id': customer_id,
            'channel': channel,
            'conversation_history': [],
            'context': {}
        }


def update_session(session_id: str, customer_id: str, user_input: str, agent_response: str) -> None:
    """Update session with new conversation turn"""

    try:
        # Add to conversation history
        conversation_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'user': user_input,
            'agent': agent_response
        }

        table.update_item(
            Key={'session_id': session_id},
            UpdateExpression='SET updated_at = :updated_at, conversation_history = list_append(if_not_exists(conversation_history, :empty_list), :new_entry)',
            ExpressionAttributeValues={
                ':updated_at': datetime.utcnow().isoformat(),
                ':empty_list': [],
                ':new_entry': [conversation_entry]
            }
        )

    except Exception as e:
        print(f"Error updating session: {e}")


def extract_project_context(bedrock_response: str) -> Dict[str, Any]:
    """
    Extract project-related context from Bedrock response
    for maintaining conversation state
    """

    context = {}

    # Simple keyword extraction (can be enhanced with NLP)
    if 'project' in bedrock_response.lower():
        context['discussing_projects'] = True

    if 'schedule' in bedrock_response.lower():
        context['scheduling_intent'] = True

    if 'urgent' in bedrock_response.lower():
        context['urgency_level'] = 'high'

    return context


# ============================================================================
# Call Event Handlers (for Connect integration)
# ============================================================================

def handle_call_start(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle call initiation event from Connect"""

    contact_id = event.get('Details', {}).get('ContactData', {}).get('ContactId')
    customer_phone = event.get('Details', {}).get('ContactData', {}).get('CustomerEndpoint', {}).get('Address')

    print(f"Call started: {contact_id}, Phone: {customer_phone}")

    # Create session for this call
    session_id = f"voice-{contact_id}"

    # TODO: Look up customer by phone number
    # For now, return generic greeting

    return {
        'statusCode': 200,
        'session_id': session_id,
        'greeting': "Thank you for calling ProjectForce. How can I help you today?"
    }


def handle_call_end(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle call termination event from Connect"""

    contact_id = event.get('Details', {}).get('ContactData', {}).get('ContactId')
    session_id = f"voice-{contact_id}"

    print(f"Call ended: {contact_id}")

    # Mark session as completed
    try:
        table.update_item(
            Key={'session_id': session_id},
            UpdateExpression='SET call_status = :status, ended_at = :ended_at',
            ExpressionAttributeValues={
                ':status': 'completed',
                ':ended_at': datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        print(f"Error updating session: {e}")

    return {
        'statusCode': 200,
        'session_id': session_id,
        'message': 'Call ended successfully'
    }
