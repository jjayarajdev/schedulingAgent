"""
Lambda Function: SMS Inbound Processor
Processes inbound SMS messages from AWS End User Messaging via SNS
Uses multi-agent orchestration system for intelligent responses
Sends SMS replies back to customers
"""

import json
import os
import sys
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

# Add shared module to path for phone_auth import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
try:
    from phone_auth import get_or_authenticate, AuthenticationError
    PHONE_AUTH_AVAILABLE = True
except ImportError:
    PHONE_AUTH_AVAILABLE = False

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


def clean_phone_number(phone: str) -> str:
    """
    Clean and format phone number to E.164 format

    Args:
        phone: Raw phone number string

    Returns:
        Cleaned phone number in E.164 format (+1XXXXXXXXXX)
    """
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)

    # Add + if not present and number looks like US number
    if not cleaned.startswith('+'):
        if len(cleaned) == 10:
            cleaned = '+1' + cleaned
        elif len(cleaned) == 11 and cleaned.startswith('1'):
            cleaned = '+' + cleaned

    return cleaned


def extract_phone_number_from_sns(sns_message: Dict[str, Any]) -> Optional[str]:
    """
    Extract phone number from SNS message based on AWS documentation
    Handles multiple message formats:
    - AWS End User Messaging inbound SMS (originationNumber)
    - Delivery status messages (delivery.destination)
    - Custom test formats (phone_number, phoneNumber)
    - Pattern matching as fallback

    Args:
        sns_message: Parsed SNS message dict

    Returns:
        Cleaned phone number in E.164 format, or None if not found
    """
    phone_number = None

    # 1. Two-Way SMS Message (Incoming) - AWS End User Messaging format
    if 'originationNumber' in sns_message:
        phone_number = sns_message['originationNumber']
        logger.debug(f"Phone from originationNumber: {phone_number}")

    # 2. SMS Delivery Status Message
    elif 'delivery' in sns_message and 'destination' in sns_message['delivery']:
        phone_number = sns_message['delivery']['destination']
        logger.debug(f"Phone from delivery.destination: {phone_number}")

    # 3. Custom test format - direct phone_number field
    elif 'phone_number' in sns_message:
        phone_number = sns_message['phone_number']
        logger.debug(f"Phone from phone_number: {phone_number}")

    # 4. Alternative phoneNumber field
    elif 'phoneNumber' in sns_message:
        phone_number = sns_message['phoneNumber']
        logger.debug(f"Phone from phoneNumber: {phone_number}")

    # 5. Nested user data
    elif 'user' in sns_message:
        user_data = sns_message['user']
        phone_number = (user_data.get('phone') or
                      user_data.get('mobile') or
                      user_data.get('phoneNumber'))
        logger.debug(f"Phone from user data: {phone_number}")

    # 6. Nested contact data
    elif 'contact' in sns_message:
        contact_data = sns_message['contact']
        phone_number = (contact_data.get('phone') or
                      contact_data.get('mobile') or
                      contact_data.get('phoneNumber'))
        logger.debug(f"Phone from contact data: {phone_number}")

    # 7. Fallback: Search for phone number patterns in the entire message
    else:
        message_str = json.dumps(sns_message)
        phone_pattern = r'\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        match = re.search(phone_pattern, message_str)
        if match:
            phone_number = match.group(0)
            logger.debug(f"Phone from pattern match: {phone_number}")

    # Clean and return phone number
    if phone_number:
        cleaned = clean_phone_number(phone_number)
        logger.info(f"Extracted phone: {cleaned} (original: {phone_number})")
        return cleaned

    return None


def get_pf_credentials() -> Dict[str, str]:
    """
    Get ProjectForce API credentials from AWS Secrets Manager
    ALWAYS fetches fresh credentials from Secrets Manager (no caching)

    Returns:
        Dictionary with bearer_token, client_id, and user_id
    """
    global _pf_credentials_cache

    # DISABLED: Return cached credentials if available
    # Caching causes issues when token is refreshed in Secrets Manager
    # if _pf_credentials_cache:
    #     logger.debug("Using cached PF credentials")
    #     return _pf_credentials_cache

    try:
        logger.info(f"Fetching FRESH PF credentials from Secrets Manager (no cache)")
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

        # DISABLED: Cache for Lambda container reuse
        # _pf_credentials_cache = credentials

        logger.info(f"PF credentials loaded successfully (token length: {len(credentials['bearer_token'])})")
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

        logger.info(f"Parsed SNS message keys: {list(sns_message.keys())}")

        # Check if this is a delivery receipt - handle separately
        event_type = sns_message.get('eventType', '')
        if event_type:
            logger.info(f"Received delivery receipt: {event_type}")
            handle_delivery_receipt(sns_message)
            return

        # Extract phone number using robust AWS-documented approach
        phone_number = extract_phone_number_from_sns(sns_message)

        # Validate phone_number was extracted
        if not phone_number:
            logger.error(f"Could not extract phone number from SNS message")
            logger.error(f"SNS message keys: {list(sns_message.keys())}")
            logger.error(f"SNS message sample: {str(sns_message)[:500]}")
            return  # Cannot process without phone number

        # Extract other fields (support both AWS and test formats)
        destination_number = sns_message.get('destinationNumber', ORIGINATION_NUMBER)
        message_body = sns_message.get('messageBody') or sns_message.get('message', '')
        message_id = sns_message.get('inboundMessageId') or sns_message.get('message_id', f'test-{int(datetime.utcnow().timestamp())}')

        logger.info(f"Processing SMS from {phone_number}: {message_body[:50] if message_body else '(empty)'}")

        # PHONE-BASED AUTHENTICATION: Authenticate sender via phone numbers
        # This calls phone-call-login API and returns fresh credentials
        pf_user_id = None
        phone_auth_credentials = None  # Store fresh credentials from phone auth
        if PHONE_AUTH_AVAILABLE and phone_number and destination_number:
            try:
                logger.info(f"[PHONE_AUTH] Authenticating SMS sender {phone_number[-4:]} via {destination_number[-4:]}")
                credentials = get_or_authenticate(phone_number, destination_number)
                pf_user_id = credentials.get('user_id')
                phone_auth_credentials = credentials  # Store fresh credentials for use in invoke_orchestrator
                logger.info(f"[PHONE_AUTH] Authenticated user {pf_user_id} ({credentials.get('user_name', 'unknown')})")
            except AuthenticationError as auth_err:
                logger.error(f"[PHONE_AUTH] Authentication failed: {auth_err}")
                # For SMS, we fail closed - send error message and stop processing
                send_sms_reply(
                    phone_number=phone_number,
                    message="Sorry, I couldn't verify your phone number. Please contact us for assistance.",
                    session_id=None
                )
                return
            except Exception as auth_ex:
                logger.warning(f"[PHONE_AUTH] Unexpected error: {auth_ex}, falling back to Secrets Manager")

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

        # Invoke multi-agent orchestrator with fresh credentials from phone auth
        orchestrator_response = invoke_orchestrator(
            message=message_body,
            session_id=session_id,
            phone_number=phone_number,
            pf_credentials=phone_auth_credentials  # Pass fresh credentials from phone-sms-login
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
    Check if message is an exact opt-out keyword

    Uses exact matching to avoid false positives (e.g., "cancel all slots" should NOT trigger opt-out).
    AWS End User Messaging will also recognize these keywords and automatically add the number
    to the Default opt-out list, but we need to detect them here to update our internal systems.

    Args:
        message: SMS message body

    Returns:
        True if message is an opt-out request (exact match only)
    """
    opt_out_keywords = [
        'STOP', 'QUIT', 'END', 'REVOKE',
        'OPT OUT', 'OPTOUT', 'CANCEL', 'UNSUBSCRIBE'
    ]

    message_upper = message.upper().strip()
    # Use exact match instead of substring to avoid false positives
    # e.g., "cancel all slots on dec9" should NOT be treated as opt-out
    return message_upper in opt_out_keywords


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

        # NOTE: AWS End User Messaging automatically sends opt-out confirmation
        # and adds the number to the Default opt-out list. We don't need to send
        # a duplicate confirmation message here.
        logger.info(f"Opt-out processed for {phone_number}. AWS will handle confirmation and opt-out list update.")

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


def handle_delivery_receipt(delivery_receipt: Dict[str, Any]) -> None:
    """
    Process SMS delivery receipt and update message status in DynamoDB

    Delivery receipt format from AWS End User Messaging:
    {
        "eventType": "TEXT_SENT" | "TEXT_DELIVERED" | "TEXT_INVALID" | "TEXT_UNREACHABLE" | etc.,
        "eventVersion": "1.0",
        "destinationPhoneNumber": "+1234567890",
        "messageId": "...",
        "isoCountryCode": "US",
        "mcc": "...",
        "mnc": "...",
        "carrierName": "...",
        "timestamp": "..."
    }

    Args:
        delivery_receipt: Delivery receipt data from SNS
    """
    try:
        event_type = delivery_receipt.get('eventType', '')
        destination_phone = delivery_receipt.get('destinationPhoneNumber', '')
        message_id = delivery_receipt.get('messageId', '')
        timestamp = delivery_receipt.get('timestamp', datetime.utcnow().isoformat())

        logger.info(f"Processing delivery receipt: {event_type} for {destination_phone}, messageId: {message_id}")

        # Map AWS event types to our message statuses
        status_mapping = {
            'TEXT_QUEUED': 'queued',
            'TEXT_SENT': 'sent',
            'TEXT_DELIVERED': 'delivered',
            'TEXT_INVALID': 'failed',
            'TEXT_UNREACHABLE': 'failed',
            'TEXT_BLOCKED': 'failed',
            'TEXT_CARRIER_BLOCKED': 'failed',
            'TEXT_SPAM': 'failed',
            'TEXT_UNKNOWN': 'unknown',
            'TEXT_CARRIER_UNREACHABLE': 'failed',
            'TEXT_TTL_EXPIRED': 'failed',
            'TEXT_PENDING': 'pending'
        }

        new_status = status_mapping.get(event_type, 'unknown')

        # If we don't have a message_id from the delivery receipt, we can't update
        # This should be rare, but we'll log it
        if not message_id:
            logger.warning(f"Delivery receipt missing messageId - cannot update status. Event: {event_type}, Phone: {destination_phone}")
            return

        # Update message status in DynamoDB
        # The table has composite key: message_id (HASH) + timestamp (RANGE)
        # We need to query by message_id to find the item, then update it
        try:
            # Query for messages with this message_id
            response = messages_table.query(
                KeyConditionExpression='message_id = :mid',
                ExpressionAttributeValues={
                    ':mid': message_id
                },
                Limit=1  # Should only be one message with this ID
            )

            if response.get('Items'):
                item = response['Items'][0]
                item_timestamp = item['timestamp']

                # Update the existing message with new status
                messages_table.update_item(
                    Key={
                        'message_id': message_id,
                        'timestamp': item_timestamp
                    },
                    UpdateExpression='SET #status = :status, delivery_timestamp = :ts, delivery_event_type = :event',
                    ExpressionAttributeNames={
                        '#status': 'status'
                    },
                    ExpressionAttributeValues={
                        ':status': new_status,
                        ':ts': timestamp,
                        ':event': event_type
                    }
                )
                logger.info(f"Updated message {message_id} status to '{new_status}' (event: {event_type})")
            else:
                # Message not found - this might be a delivery receipt for a message we didn't store
                # This could happen if the message was sent before our system was deployed
                logger.warning(f"Message {message_id} not found in messages table. Delivery receipt: {event_type}")

        except ClientError as e:
            logger.error(f"DynamoDB error updating message {message_id}: {str(e)}", exc_info=True)

    except Exception as e:
        logger.error(f"Error processing delivery receipt: {str(e)}", exc_info=True)
        # Don't raise - we don't want delivery receipt processing errors to affect inbound message processing


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
    phone_number: str,
    pf_credentials: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Invoke multi-agent orchestrator lambda for intelligent response

    Args:
        message: Customer message
        session_id: Session ID
        phone_number: Customer phone number (used as customer_id)
        pf_credentials: Optional fresh credentials from phone-sms-login (preferred)

    Returns:
        Orchestrator response or None
    """
    try:
        logger.info(f"Invoking orchestrator lambda: {ORCHESTRATOR_LAMBDA}")

        # Use fresh credentials from phone auth if available, otherwise fall back to Secrets Manager
        if pf_credentials and pf_credentials.get('bearer_token'):
            logger.info(f"Using FRESH credentials from phone-sms-login (token length: {len(pf_credentials.get('bearer_token', ''))})")
            pf_creds = {
                'bearer_token': pf_credentials.get('bearer_token', ''),
                'client_id': pf_credentials.get('client_id', ''),
                'user_id': pf_credentials.get('user_id', '')
            }
        else:
            logger.info(f"Fetching FRESH PF credentials from Secrets Manager (no cache)")
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

        logger.info(f"Sending to orchestrator - message: '{message[:50]}...', session: {session_id}, user: {pf_creds['user_id']}")

        # Invoke orchestrator lambda synchronously
        response = lambda_client.invoke(
            FunctionName=ORCHESTRATOR_LAMBDA,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        # Parse response
        response_payload = json.loads(response['Payload'].read())
        logger.info(f"Orchestrator full response payload: {json.dumps(response_payload)[:500]}")
        logger.debug(f"Orchestrator response status: {response_payload.get('statusCode')}")

        if response_payload.get('statusCode') == 200:
            body = json.loads(response_payload['body'])
            response_text = body.get('response', '')

            logger.info(f"Orchestrator raw response length: {len(response_text)} chars")

            # Format for SMS (remove markdown, limit length)
            formatted_response = format_for_sms(response_text)

            logger.info(f"Formatted SMS response length: {len(formatted_response)} chars")

            # Validate response is not empty
            if not formatted_response or len(formatted_response.strip()) == 0:
                logger.error(f"Empty response after formatting. Raw response: {response_text[:200]}")
                return "I received your message but don't have a response at the moment. Please try again."

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
    Format text for SMS delivery with simple truncation

    Args:
        text: Raw text response

    Returns:
        SMS-formatted text (max 320 chars for 2 messages)
    """
    # Remove markdown formatting
    text = text.replace('**', '').replace('*', '').replace('__', '').replace('_', '')
    text = text.replace('- ', '• ').replace('* ', '• ')

    # Remove excessive newlines
    while '\n\n\n' in text:
        text = text.replace('\n\n\n', '\n\n')

    # Truncate if needed (320 chars = 2 SMS messages)
    if len(text) > 320:
        text = text[:317] + "..."

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
