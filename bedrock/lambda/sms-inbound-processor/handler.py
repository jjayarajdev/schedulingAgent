"""
Lambda Function: SMS Inbound Processor
Processes inbound SMS messages from AWS End User Messaging via SNS
Invokes Bedrock Agent and sends reply back to customer
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
SUPERVISOR_AGENT_ID = os.environ['SUPERVISOR_AGENT_ID']
SUPERVISOR_ALIAS_ID = os.environ['SUPERVISOR_ALIAS_ID']
ORIGINATION_NUMBER = os.environ['ORIGINATION_NUMBER']
CONSENT_TABLE = os.environ['CONSENT_TABLE']
OPT_OUT_TRACKING_TABLE = os.environ['OPT_OUT_TRACKING_TABLE']
MESSAGES_TABLE = os.environ['MESSAGES_TABLE']
SESSIONS_TABLE = os.environ['SESSIONS_TABLE']
AWS_REGION = os.environ.get('AWS_REGION_NAME', 'us-east-1')

# AWS clients
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
sms_client = boto3.client('pinpoint-sms-voice-v2', region_name=AWS_REGION)
bedrock_agent = boto3.client('bedrock-agent-runtime', region_name=AWS_REGION)

# DynamoDB tables
consent_table = dynamodb.Table(CONSENT_TABLE)
opt_out_table = dynamodb.Table(OPT_OUT_TRACKING_TABLE)
messages_table = dynamodb.Table(MESSAGES_TABLE)
sessions_table = dynamodb.Table(SESSIONS_TABLE)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for inbound SMS processing

    Args:
        event: SNS event containing SMS message
        context: Lambda context

    Returns:
        Response dictionary
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Process each SNS record
        for record in event.get('Records', []):
            process_sms_record(record)

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'SMS processed successfully'})
        }

    except Exception as e:
        logger.error(f"Error processing SMS: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def process_sms_record(record: Dict[str, Any]) -> None:
    """
    Process a single SNS record containing an SMS message

    Args:
        record: SNS record
    """
    try:
        # Parse SNS message
        sns_message = json.loads(record['Sns']['Message'])

        phone_number = sns_message['originationNumber']
        destination_number = sns_message['destinationNumber']
        message_body = sns_message['messageBody']
        message_id = sns_message['inboundMessageId']

        logger.info(f"Processing SMS from {phone_number}: {message_body[:50]}")

        # Check for opt-out keywords
        if is_opt_out_keyword(message_body):
            handle_opt_out(phone_number, message_body, message_id)
            return

        # Check if customer has opted out
        if is_opted_out(phone_number):
            logger.info(f"Customer {phone_number} has opted out. Not processing message.")
            return

        # Store inbound message
        store_message(
            phone_number=phone_number,
            direction='inbound',
            message_body=message_body,
            message_id=message_id,
            status='received'
        )

        # Get or create session
        session_id = get_or_create_session(phone_number)

        # Invoke Bedrock Agent
        agent_response = invoke_bedrock_agent(
            session_id=session_id,
            input_text=message_body
        )

        # Send reply
        if agent_response:
            send_sms_reply(
                phone_number=phone_number,
                message=agent_response,
                session_id=session_id
            )

    except Exception as e:
        logger.error(f"Error processing SMS record: {str(e)}", exc_info=True)
        # Don't raise - we don't want to fail the entire batch


def is_opt_out_keyword(message: str) -> bool:
    """
    Check if message contains opt-out keyword

    Args:
        message: SMS message body

    Returns:
        True if message is an opt-out request
    """
    opt_out_keywords = [
        'STOP', 'QUIT', 'END', 'REVOKE',
        'OPT OUT', 'OPTOUT', 'CANCEL', 'UNSUBSCRIBE'
    ]

    message_upper = message.upper().strip()
    return any(keyword in message_upper for keyword in opt_out_keywords)


def handle_opt_out(phone_number: str, message: str, message_id: str) -> None:
    """
    Handle opt-out request

    Args:
        phone_number: Customer phone number
        message: Original message
        message_id: SMS message ID
    """
    try:
        logger.info(f"Processing opt-out for {phone_number}")

        # Record opt-out in consent table
        now = datetime.utcnow()
        deadline = now + timedelta(days=10)  # TCPA 2025 requirement

        consent_table.put_item(
            Item={
                'phone_number': phone_number,
                'consent_status': 'opted_out',
                'opt_out_method': 'sms',
                'opt_out_requested_at': now.isoformat(),
                'opt_out_deadline': deadline.isoformat(),
                'applies_to_channels': ['sms', 'voice'],  # TCPA universal opt-out
                'original_message': message,
                'message_id': message_id,
                'processed_at': now.isoformat(),
                'ttl': int((now + timedelta(days=1460)).timestamp())  # 4 years retention
            }
        )

        # Track in opt-out tracking table
        opt_out_table.put_item(
            Item={
                'tracking_id': f"{phone_number}#{now.isoformat()}",
                'timestamp': now.isoformat(),
                'phone_number': phone_number,
                'method': 'sms',
                'status': 'pending_processing',
                'deadline': deadline.isoformat(),
                'original_request': message
            }
        )

        # Send confirmation
        confirmation = (
            "You have been unsubscribed from SMS messages. "
            "Your request will be processed within 10 business days. "
            "Reply START to resubscribe."
        )

        send_sms_reply(
            phone_number=phone_number,
            message=confirmation,
            session_id=None
        )

        logger.info(f"Opt-out processed for {phone_number}")

    except Exception as e:
        logger.error(f"Error handling opt-out: {str(e)}", exc_info=True)


def is_opted_out(phone_number: str) -> bool:
    """
    Check if customer has opted out

    Args:
        phone_number: Customer phone number

    Returns:
        True if customer has opted out
    """
    try:
        response = consent_table.get_item(
            Key={'phone_number': phone_number}
        )

        if 'Item' in response:
            consent_status = response['Item'].get('consent_status')
            return consent_status == 'opted_out'

        return False

    except Exception as e:
        logger.error(f"Error checking opt-out status: {str(e)}", exc_info=True)
        return False  # Fail open to avoid blocking legitimate messages


def store_message(
    phone_number: str,
    direction: str,
    message_body: str,
    message_id: str,
    status: str,
    session_id: Optional[str] = None
) -> None:
    """
    Store message in DynamoDB

    Args:
        phone_number: Customer phone number
        direction: 'inbound' or 'outbound'
        message_body: Message content
        message_id: Message ID
        status: Message status
        session_id: Optional session ID
    """
    try:
        now = datetime.utcnow()
        ttl = int((now + timedelta(days=1460)).timestamp())  # 4 years retention

        messages_table.put_item(
            Item={
                'message_id': message_id,
                'timestamp': now.isoformat(),
                'phone_number': phone_number,
                'direction': direction,
                'message_body': message_body,
                'status': status,
                'session_id': session_id,
                'ttl': ttl
            }
        )

        logger.info(f"Stored {direction} message {message_id}")

    except Exception as e:
        logger.error(f"Error storing message: {str(e)}", exc_info=True)


def get_or_create_session(phone_number: str) -> str:
    """
    Get existing session or create new one

    Args:
        phone_number: Customer phone number

    Returns:
        Session ID
    """
    try:
        # Query sessions by phone number
        response = sessions_table.query(
            IndexName='phone-index',
            KeyConditionExpression='phone_number = :phone',
            ExpressionAttributeValues={
                ':phone': phone_number
            },
            Limit=1,
            ScanIndexForward=False  # Get most recent
        )

        # Check if active session exists
        if response.get('Items'):
            session = response['Items'][0]
            session_id = session['session_id']

            # Check if session is still valid (within 24 hours)
            created_at = datetime.fromisoformat(session['created_at'])
            if datetime.utcnow() - created_at < timedelta(hours=24):
                logger.info(f"Using existing session {session_id}")
                return session_id

        # Create new session
        now = datetime.utcnow()
        session_id = f"sms-{phone_number}-{int(now.timestamp())}"
        ttl = int((now + timedelta(hours=24)).timestamp())

        sessions_table.put_item(
            Item={
                'session_id': session_id,
                'phone_number': phone_number,
                'created_at': now.isoformat(),
                'last_activity': now.isoformat(),
                'channel': 'sms',
                'ttl': ttl
            }
        )

        logger.info(f"Created new session {session_id}")
        return session_id

    except Exception as e:
        logger.error(f"Error managing session: {str(e)}", exc_info=True)
        # Fallback to generated session ID
        return f"sms-{phone_number}-{int(datetime.utcnow().timestamp())}"


def invoke_bedrock_agent(session_id: str, input_text: str) -> Optional[str]:
    """
    Invoke Bedrock Agent with customer message

    Args:
        session_id: Session ID
        input_text: Customer message

    Returns:
        Agent response or None
    """
    try:
        logger.info(f"Invoking Bedrock Agent {SUPERVISOR_AGENT_ID}")

        response = bedrock_agent.invoke_agent(
            agentId=SUPERVISOR_AGENT_ID,
            agentAliasId=SUPERVISOR_ALIAS_ID,
            sessionId=session_id,
            inputText=input_text
        )

        # Extract response from completion stream
        response_text = ""
        for event in response.get('completion', []):
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    response_text += chunk['bytes'].decode('utf-8')

        logger.info(f"Agent response: {response_text[:100]}")
        return response_text.strip()

    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"AWS error invoking agent: {error_code} - {str(e)}")
        return "Sorry, I'm having trouble processing your request. Please try again later."

    except Exception as e:
        logger.error(f"Error invoking Bedrock Agent: {str(e)}", exc_info=True)
        return "Sorry, I'm having trouble processing your request. Please try again later."


def send_sms_reply(
    phone_number: str,
    message: str,
    session_id: Optional[str] = None
) -> None:
    """
    Send SMS reply to customer

    Args:
        phone_number: Customer phone number
        message: Message to send
        session_id: Optional session ID
    """
    try:
        # Truncate message to 160 characters for single segment
        # For longer messages, AWS will automatically segment
        if len(message) > 1600:  # Max 10 segments
            message = message[:1597] + "..."

        logger.info(f"Sending SMS to {phone_number}")

        response = sms_client.send_text_message(
            DestinationPhoneNumber=phone_number,
            OriginationIdentity=ORIGINATION_NUMBER,
            MessageBody=message,
            MessageType='TRANSACTIONAL'
        )

        message_id = response['MessageId']

        # Store outbound message
        store_message(
            phone_number=phone_number,
            direction='outbound',
            message_body=message,
            message_id=message_id,
            status='sent',
            session_id=session_id
        )

        logger.info(f"SMS sent successfully: {message_id}")

    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"AWS error sending SMS: {error_code} - {str(e)}")

    except Exception as e:
        logger.error(f"Error sending SMS: {str(e)}", exc_info=True)
