"""
Lambda Function: Amazon Connect Phone Authentication
Name: pf-syn-connect-auth-dev

Authenticates callers via phone number before transferring to Vapi.
Stores credentials in DynamoDB for the orchestrator to retrieve.

Flow:
1. Amazon Connect invokes this Lambda with caller phone numbers
2. Lambda calls phone-call-login API to authenticate
3. Stores credentials in DynamoDB (keyed by phone number)
4. Returns greeting to Connect
5. Connect transfers call to Vapi
6. When Vapi calls orchestrator, it passes caller_phone
7. Orchestrator looks up credentials from DynamoDB

Environment Variables:
    SESSIONS_TABLE: DynamoDB table for storing auth sessions (default: pf-syn-sessions-dev)
    ENVIRONMENT: Environment name (default: dev)
    AWS_REGION: AWS region (default: us-east-1)
"""

import json
import boto3
import os
import sys
import logging
import time
from typing import Dict, Any
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Import phone_auth from shared module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
try:
    from phone_auth import get_or_authenticate, AuthenticationError, normalize_phone
    PHONE_AUTH_AVAILABLE = True
except ImportError:
    PHONE_AUTH_AVAILABLE = False
    logger.warning("phone_auth module not available - will use inline implementation")

# Configuration
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
SESSIONS_TABLE = os.environ.get('SESSIONS_TABLE', f'pf-syn-sessions-{ENVIRONMENT}')

# DynamoDB
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(SESSIONS_TABLE)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle Amazon Connect authentication request.

    Amazon Connect sends:
    {
        "Details": {
            "ContactData": {
                "ContactId": "abc-123-def",
                "CustomerEndpoint": {"Address": "+15104137024", "Type": "TELEPHONE_NUMBER"},
                "SystemEndpoint": {"Address": "+18446076163", "Type": "TELEPHONE_NUMBER"},
                ...
            },
            "Parameters": {}
        }
    }

    Returns to Connect:
    {
        "authenticated": true/false,
        "user_name": "John",
        "greeting": "Hello John! How can I help you today?"
    }
    """
    try:
        logger.info(f"[CONNECT_AUTH] Received event: {json.dumps(event)[:500]}")

        # Extract contact data
        details = event.get('Details', {})
        contact_data = details.get('ContactData', {})
        parameters = details.get('Parameters', {})

        # Get phone numbers
        customer_endpoint = contact_data.get('CustomerEndpoint', {})
        system_endpoint = contact_data.get('SystemEndpoint', {})

        from_phone = customer_endpoint.get('Address', '')
        to_phone = system_endpoint.get('Address', '')
        contact_id = contact_data.get('ContactId', '')

        logger.info(f"[CONNECT_AUTH] Contact: {contact_id}, From: {from_phone}, To: {to_phone}")

        if not from_phone:
            logger.error("[CONNECT_AUTH] Missing caller phone number")
            return {
                "authenticated": False,
                "greeting": "Welcome to ProjectForce. How can I help you today?"
            }

        # Normalize phone numbers
        from_phone_clean = normalize_phone_inline(from_phone)
        to_phone_clean = normalize_phone_inline(to_phone)

        # Authenticate via phone-call-login API
        if PHONE_AUTH_AVAILABLE:
            try:
                credentials = get_or_authenticate(from_phone_clean, to_phone_clean)
            except AuthenticationError as e:
                logger.error(f"[CONNECT_AUTH] Authentication failed: {e}")
                credentials = None
        else:
            credentials = authenticate_inline(from_phone_clean, to_phone_clean)

        if credentials:
            user_name = credentials.get('user_name', '').split()[0]  # First name only
            user_id = credentials.get('user_id', '')
            client_id = credentials.get('client_id', '')

            # Store in DynamoDB for orchestrator to retrieve
            store_phone_session(
                phone_number=from_phone_clean,
                contact_id=contact_id,
                credentials=credentials
            )

            logger.info(f"[CONNECT_AUTH] Authenticated: {user_name} (ID: {user_id})")

            # Personalized greeting
            if user_name:
                greeting = f"Hello {user_name}! Welcome to ProjectForce. How can I help you today?"
            else:
                greeting = "Hello! Welcome to ProjectForce. How can I help you today?"

            return {
                "authenticated": True,
                "user_name": user_name,
                "user_id": user_id,
                "client_id": client_id,
                "greeting": greeting
            }
        else:
            logger.warning(f"[CONNECT_AUTH] Could not authenticate {from_phone_clean}")
            return {
                "authenticated": False,
                "greeting": "Welcome to ProjectForce. I couldn't find an account with your phone number, but I can still help you. What would you like to do?"
            }

    except Exception as e:
        logger.error(f"[CONNECT_AUTH] Error: {e}", exc_info=True)
        return {
            "authenticated": False,
            "greeting": "Welcome to ProjectForce. How can I help you today?"
        }


def normalize_phone_inline(phone: str) -> str:
    """Normalize phone number - strip to digits, remove country code."""
    if not phone:
        return ''

    # Keep only digits
    digits = ''.join(c for c in phone if c.isdigit())

    # Remove leading 1 for US numbers (11 digits starting with 1)
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]

    return digits


def authenticate_inline(from_phone: str, to_phone: str) -> Dict:
    """
    Inline authentication if phone_auth module not available.
    Calls the phone-call-login API directly.
    """
    import urllib.request
    import urllib.error

    API_BASE_URLS = {
        "dev": "https://api-cx-portal.dev.projectsforce.com",
        "staging": "https://api-cx-portal.staging.projectsforce.com",
        "prod": "https://api-cx-portal.apps.projectsforce.com"
    }
    api_base = API_BASE_URLS.get(ENVIRONMENT, API_BASE_URLS["dev"])
    auth_url = f"{api_base}/authentication/phone-call-login"

    try:
        payload = json.dumps({'from_phone': from_phone, 'to_phone': to_phone}).encode('utf-8')
        req = urllib.request.Request(
            auth_url,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            if response.getcode() != 200:
                return None

            data = json.loads(response.read().decode('utf-8'))

            if 'accesstoken' not in data:
                return None

            user = data.get('user', {})
            return {
                'bearer_token': data['accesstoken'],
                'refresh_token': data.get('refrestoken', ''),
                'client_id': user.get('client_id', ''),
                'user_id': str(user.get('customer_id', '')),
                'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                'user_phone': from_phone,
                'exp': data.get('exp', 0)
            }

    except Exception as e:
        logger.error(f"[CONNECT_AUTH] Inline auth failed: {e}")
        return None


def store_phone_session(phone_number: str, contact_id: str, credentials: Dict):
    """
    Store authenticated session in DynamoDB.

    Uses session_id = "phone:{phone_number}" for easy lookup.
    """
    try:
        session_id = f"phone:{phone_number}"
        ttl = int(time.time()) + 3600  # 1 hour expiry

        item = {
            'session_id': session_id,
            'contact_id': contact_id,
            'phone_number': phone_number,
            'bearer_token': credentials.get('bearer_token', ''),
            'client_id': credentials.get('client_id', ''),
            'user_id': credentials.get('user_id', ''),
            'user_name': credentials.get('user_name', ''),
            'exp': credentials.get('exp', 0),
            'created_at': datetime.utcnow().isoformat(),
            'ttl': ttl,
            'channel': 'voice'
        }

        table.put_item(Item=item)
        logger.info(f"[CONNECT_AUTH] Stored session {session_id} in DynamoDB")

    except Exception as e:
        logger.error(f"[CONNECT_AUTH] Failed to store session: {e}")


def get_phone_session(phone_number: str) -> Dict:
    """
    Retrieve authenticated session from DynamoDB by phone number.
    Called by orchestrator when Vapi passes caller_phone.
    """
    try:
        phone_clean = normalize_phone_inline(phone_number)
        session_id = f"phone:{phone_clean}"

        response = table.get_item(Key={'session_id': session_id})

        if 'Item' in response:
            item = response['Item']
            # Check TTL
            if item.get('ttl', 0) > time.time():
                logger.info(f"[CONNECT_AUTH] Found valid session for {phone_clean}")
                return item
            else:
                logger.info(f"[CONNECT_AUTH] Session expired for {phone_clean}")
                return None

        logger.info(f"[CONNECT_AUTH] No session found for {phone_clean}")
        return None

    except Exception as e:
        logger.error(f"[CONNECT_AUTH] Failed to get session: {e}")
        return None
