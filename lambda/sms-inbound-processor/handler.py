"""
Lambda Function: SMS Inbound Processor
Processes inbound SMS messages from AWS End User Messaging via SNS
Uses multi-agent orchestration system for intelligent responses
Sends SMS replies back to customers
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

# Configure logging with structured output
logger = logging.getLogger()
log_level = os.environ.get('LOG_LEVEL', 'INFO')
logger.setLevel(getattr(logging, log_level))

# Environment variables with validation
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
ORCHESTRATOR_LAMBDA = os.environ.get('ORCHESTRATOR_LAMBDA', '')
ORIGINATION_NUMBER = os.environ.get('ORIGINATION_NUMBER', '')
CONSENT_TABLE = os.environ.get('CONSENT_TABLE', '')
OPT_OUT_TRACKING_TABLE = os.environ.get('OPT_OUT_TRACKING_TABLE', '')
MESSAGES_TABLE = os.environ.get('MESSAGES_TABLE', '')
SESSIONS_TABLE = os.environ.get('SESSIONS_TABLE', '')
AWS_REGION = os.environ.get('AWS_REGION_NAME', 'us-east-1')
PF_SECRET_NAME = os.environ.get('PF_SECRET_NAME', 'projectforce/api/credentials')
SMS_CONFIGURATION_SET = os.environ.get('SMS_CONFIGURATION_SET', f'scheduling-agent-sms-config-{ENVIRONMENT}')

# Configuration constants
MAX_MESSAGE_LENGTH = 1600  # SMS character limit (10 segments)
SESSION_TTL_HOURS = 24
MAX_RETRY_ATTEMPTS = 3
ORCHESTRATOR_TIMEOUT_SECONDS = 30

# AWS clients
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
sms_client = boto3.client('pinpoint-sms-voice-v2', region_name=AWS_REGION)
lambda_client = boto3.client('lambda', region_name=AWS_REGION)
secrets_client = boto3.client('secretsmanager', region_name=AWS_REGION)

# Cache for PF credentials (avoids repeated Secrets Manager calls)
_pf_credentials_cache = None

# DynamoDB tables
consent_table = dynamodb.Table(CONSENT_TABLE)
opt_out_table = dynamodb.Table(OPT_OUT_TRACKING_TABLE)
messages_table = dynamodb.Table(MESSAGES_TABLE)
sessions_table = dynamodb.Table(SESSIONS_TABLE)


def get_pf_credentials() -> Dict[str, str]:
    """
    Get ProjectForce API credentials from AWS Secrets Manager
    Uses in-memory caching to avoid repeated Secrets Manager calls

    Returns:
        Dictionary with bearer_token, client_id, and user_id
    """
    global _pf_credentials_cache

    # Return cached credentials if available
    if _pf_credentials_cache:
        logger.debug("Using cached PF credentials")
        return _pf_credentials_cache

    try:
        logger.info(f"Fetching PF credentials from Secrets Manager")
        response = secrets_client.get_secret_value(SecretId=PF_SECRET_NAME)
        secret = json.loads(response['SecretString'])

        # Extract credentials
        credentials = {
            'bearer_token': secret.get('bearer_token', ''),
            'client_id': secret.get('client_id', ''),
            'user_id': secret.get('user_id', '')
        }

        # Validate credentials
        if not credentials['bearer_token'] or not credentials['client_id']:
            logger.error("Invalid PF credentials in Secrets Manager")
            raise ValueError("Missing bearer_token or client_id in secret")

        # Cache for Lambda container reuse
        _pf_credentials_cache = credentials

        logger.info(f"PF credentials loaded successfully")
        return credentials

    except Exception as e:
        logger.error(f"Failed to get PF credentials: {str(e)}")
        raise


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
        logger.debug(f"Received event with {len(event.get('Records', []))} record(s)")

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

        # Get or create session FIRST (needed for storing message)
        session_id = get_or_create_session(phone_number)

        # Store inbound message with session_id
        store_message(
            phone_number=phone_number,
            direction='inbound',
            message_body=message_body,
            message_id=message_id,
            status='received',
            session_id=session_id
        )

        # Invoke multi-agent orchestrator
        orchestrator_response = invoke_orchestrator(
            message=message_body,
            session_id=session_id,
            phone_number=phone_number
        )

        # Send reply
        if orchestrator_response:
            send_sms_reply(
                phone_number=phone_number,
                message=orchestrator_response,
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


def sanitize_phone_for_session(phone_number: str) -> str:
    """
    Sanitize phone number for use in session ID
    Bedrock agent session IDs must match pattern: [0-9a-zA-Z._:-]+

    Args:
        phone_number: Phone number (e.g., +15555551234)

    Returns:
        Sanitized phone number (e.g., 15555551234)
    """
    # Remove + and any other special characters
    return phone_number.replace('+', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '')


def get_or_create_session(phone_number: str) -> str:
    """
    Get existing session or create new one

    Args:
        phone_number: Customer phone number

    Returns:
        Session ID (compatible with Bedrock agent pattern)
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
                logger.debug(f"Using existing session {session_id}")
                return session_id

        # Create new session with sanitized phone number
        now = datetime.utcnow()
        sanitized_phone = sanitize_phone_for_session(phone_number)
        session_id = f"sms-{sanitized_phone}-{int(now.timestamp())}"
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
        # Fallback to generated session ID with sanitized phone
        sanitized_phone = sanitize_phone_for_session(phone_number)
        return f"sms-{sanitized_phone}-{int(datetime.utcnow().timestamp())}"


def invoke_orchestrator(
    message: str,
    session_id: str,
    phone_number: str
) -> Optional[str]:
    """
    Invoke multi-agent orchestrator lambda for intelligent response

    Args:
        message: Customer message
        session_id: Session ID
        phone_number: Customer phone number (used as customer_id)

    Returns:
        Orchestrator response or None
    """
    try:
        logger.info(f"Invoking orchestrator lambda: {ORCHESTRATOR_LAMBDA}")

        # Get ProjectForce credentials from Secrets Manager
        pf_creds = get_pf_credentials()

        # Prepare payload for orchestrator with real PF credentials
        payload = {
            'body': json.dumps({
                'message': message,
                'session_id': session_id,
                'pf_token': pf_creds['bearer_token'],
                'pf_client_id': pf_creds['client_id'],
                'pf_user_id': pf_creds['user_id'],
                'channel': 'sms'  # Indicate this is from SMS channel
            })
        }

        # Invoke orchestrator lambda synchronously
        response = lambda_client.invoke(
            FunctionName=ORCHESTRATOR_LAMBDA,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        # Parse response
        response_payload = json.loads(response['Payload'].read())
        logger.debug(f"Orchestrator response status: {response_payload.get('statusCode')}")

        if response_payload.get('statusCode') == 200:
            body = json.loads(response_payload['body'])
            response_text = body.get('response', '')

            # Format for SMS (remove markdown, limit length)
            formatted_response = format_for_sms(response_text)

            logger.info(f"Orchestrator responded successfully")
            return formatted_response
        else:
            logger.error(f"Orchestrator returned error status: {response_payload.get('statusCode')}")
            return "Sorry, I'm having trouble processing your request. Please try again later."

    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"AWS error invoking orchestrator: {error_code} - {str(e)}")
        return "Sorry, I'm having trouble processing your request. Please try again later."

    except Exception as e:
        logger.error(f"Error invoking orchestrator: {str(e)}", exc_info=True)
        return "Sorry, I'm having trouble processing your request. Please try again later."


def format_for_sms(text: str) -> str:
    """
    Format text for SMS delivery

    Args:
        text: Raw text response

    Returns:
        SMS-formatted text
    """
    # Remove markdown formatting
    text = text.replace('**', '').replace('*', '').replace('__', '').replace('_', '')

    # Remove bullet points and numbered lists formatting
    text = text.replace('- ', '• ').replace('* ', '• ')

    # Collapse multiple newlines
    while '\n\n\n' in text:
        text = text.replace('\n\n\n', '\n\n')

    # Truncate if too long (SMS has 1600 char limit for 10 segments)
    if len(text) > 1600:
        text = text[:1597] + "..."

    return text.strip()


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
        logger.info(f"Sending SMS to {phone_number}")

        response = sms_client.send_text_message(
            DestinationPhoneNumber=phone_number,
            OriginationIdentity=ORIGINATION_NUMBER,
            MessageBody=message,
            MessageType='TRANSACTIONAL',
            ConfigurationSetName=SMS_CONFIGURATION_SET
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
