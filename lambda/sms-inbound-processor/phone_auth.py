"""
Phone-based authentication module for SMS channel.

This module (SMS-specific):
1. Checks DynamoDB for existing valid credentials BY PHONE NUMBER
2. If not found or expired, calls ProjectsForce phone-call-login API
3. Stores new credentials in DynamoDB (per phone number)
4. Supports multiple concurrent users (each phone has its own credentials)

Key difference from Voice/VAPI:
- Voice uses Secrets Manager (single user at a time)
- SMS uses DynamoDB (multiple concurrent users)
"""
import boto3
import json
import urllib.request
import urllib.error
import logging
import os
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Environment-specific API URLs
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")
API_BASE_URLS = {
    "dev": "https://api-cx-portal.dev.projectsforce.com",
    "staging": "https://api-cx-portal.staging.projectsforce.com",
    "prod": "https://api-cx-portal.apps.projectsforce.com"
}

def get_api_base_url():
    """Get the API base URL for the current environment"""
    return API_BASE_URLS.get(ENVIRONMENT, API_BASE_URLS["dev"])

# Configuration
PF_AUTH_API = os.environ.get(
    'PF_AUTH_API',
    f'{get_api_base_url()}/authentication/phone-call-login'
)

# DynamoDB table for SMS credentials (per phone number)
CREDENTIALS_TABLE = os.environ.get('SMS_CREDENTIALS_TABLE', f'pf-syn-sms-credentials-{ENVIRONMENT}')

# Region configuration
# SMS Lambda runs in us-east-1 (VOICE_REGION), DynamoDB tables are in DYNAMODB_REGION
DYNAMODB_REGION = os.environ.get('DYNAMODB_REGION', os.environ.get('AWS_REGION', 'us-east-1'))

# Token refresh buffer - refresh if less than this many seconds remaining
TOKEN_REFRESH_BUFFER_SECONDS = 120


class AuthenticationError(Exception):
    """Raised when phone authentication fails."""
    pass


def normalize_phone(phone: str) -> str:
    """
    Strip phone to digits only, remove country code prefix.

    Examples:
        +14702832382 -> 4702832382
        +918008455667 -> 8008455667
        1-470-283-2382 -> 4702832382
    """
    if not phone:
        return ''

    # Keep only digits
    digits = ''.join(c for c in phone if c.isdigit())

    # Remove leading 1 for US numbers (11 digits starting with 1)
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]

    # Remove leading 91 for India numbers (12 digits starting with 91)
    if len(digits) == 12 and digits.startswith('91'):
        digits = digits[2:]

    return digits


def get_or_authenticate(from_phone: str, to_phone: str) -> Dict:
    """
    Get existing credentials from DynamoDB or authenticate via API.

    Flow:
    1. Check DynamoDB for existing credentials FOR THIS PHONE NUMBER
    2. If found and valid (not expired) -> return existing
    3. If not found or expired -> call API, store in DynamoDB, return new

    Args:
        from_phone: Caller's phone number (SMS originationNumber)
        to_phone: System phone number (SMS destinationNumber)

    Returns:
        Dict with: bearer_token, refresh_token, client_id, user_id, user_name, user_phone, timezone, exp

    Raises:
        AuthenticationError: If phone numbers are missing or API call fails
    """
    if not from_phone:
        raise AuthenticationError("Missing caller phone number (from_phone)")
    if not to_phone:
        raise AuthenticationError("Missing system phone number (to_phone)")

    from_clean = normalize_phone(from_phone)
    to_clean = normalize_phone(to_phone)

    if not from_clean:
        raise AuthenticationError(f"Invalid caller phone number: {from_phone}")
    if not to_clean:
        raise AuthenticationError(f"Invalid system phone number: {to_phone}")

    # Use DynamoDB for per-phone-number credential storage
    dynamodb = boto3.resource('dynamodb', region_name=DYNAMODB_REGION)
    table = dynamodb.Table(CREDENTIALS_TABLE)

    # Step 1: Check DynamoDB for existing credentials for THIS phone number
    existing = _get_existing_credentials(table, from_clean)
    if existing:
        logger.info(f"[SMS_AUTH] Using existing credentials for ***{from_clean[-4:]}")
        return existing

    # Step 2: Call API to authenticate
    logger.info(f"[SMS_AUTH] Authenticating ***{from_clean[-4:]} via ***{to_clean[-4:]}")
    credentials = _call_auth_api(from_clean, to_clean)

    # Step 3: Store in DynamoDB (keyed by phone number)
    _store_credentials(table, from_clean, credentials)
    logger.info(f"[SMS_AUTH] Stored NEW credentials for user {credentials['user_id']} (phone: ***{from_clean[-4:]})")

    return credentials


def _get_existing_credentials(table, from_phone: str) -> Optional[Dict]:
    """
    Check DynamoDB for existing valid credentials for this phone number.

    Returns credentials if:
    - Item exists for this phone number
    - Token has at least TOKEN_REFRESH_BUFFER_SECONDS remaining

    Returns None otherwise (triggering a fresh authentication).
    """
    try:
        response = table.get_item(Key={'phone_number': from_phone})

        if 'Item' not in response:
            logger.info(f"[SMS_AUTH] No credentials found for ***{from_phone[-4:]}")
            return None

        existing = response['Item']

        # Check if token is expired or close to expiring
        exp = existing.get('exp', 0)
        # Handle Decimal from DynamoDB
        if hasattr(exp, '__float__'):
            exp = float(exp)

        now = datetime.utcnow().timestamp()
        remaining_seconds = exp - now
        remaining_mins = remaining_seconds / 60

        if remaining_seconds <= 0:
            logger.info(f"[SMS_AUTH] Token EXPIRED for ***{from_phone[-4:]} - exp: {exp}, now: {now}")
            return None

        if remaining_seconds < TOKEN_REFRESH_BUFFER_SECONDS:
            logger.info(f"[SMS_AUTH] Token expiring soon for ***{from_phone[-4:]} - {remaining_seconds:.0f}s ({remaining_mins:.1f}m) remaining, refreshing proactively")
            return None

        logger.info(f"[SMS_AUTH] Token valid for ***{from_phone[-4:]} - {remaining_seconds:.0f}s ({remaining_mins:.1f}m) remaining")

        # Convert DynamoDB types to Python types
        credentials = {
            'bearer_token': existing.get('bearer_token', ''),
            'refresh_token': existing.get('refresh_token', ''),
            'client_id': existing.get('client_id', ''),
            'client_name': existing.get('client_name', 'ProjectForce'),
            'user_id': existing.get('user_id', ''),
            'user_name': existing.get('user_name', ''),
            'user_phone': existing.get('user_phone', ''),
            'user_email': existing.get('user_email', ''),
            'timezone': existing.get('timezone', 'US/Eastern'),
            'exp': float(exp) if hasattr(exp, '__float__') else exp,
            'updated_at': existing.get('updated_at', '')
        }

        return credentials

    except Exception as e:
        logger.warning(f"[SMS_AUTH] Error reading credentials from DynamoDB: {e}")
        return None


def _call_auth_api(from_phone: str, to_phone: str) -> Dict:
    """
    Call ProjectsForce phone-call-login API.

    Args:
        from_phone: Normalized caller phone (digits only)
        to_phone: Normalized system phone (digits only)

    Returns:
        Formatted credentials dict

    Raises:
        AuthenticationError: If API call fails
    """
    try:
        payload = json.dumps({'from_phone': from_phone, 'to_phone': to_phone}).encode('utf-8')
        req = urllib.request.Request(
            PF_AUTH_API,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            status_code = response.getcode()
            response_body = response.read().decode('utf-8')

            if status_code != 200:
                error_msg = response_body[:200]
                logger.error(f"[SMS_AUTH] API failed: {status_code} - {error_msg}")
                raise AuthenticationError(f"Authentication failed: {error_msg}")

            data = json.loads(response_body)

            if 'accesstoken' not in data:
                error_msg = data.get('message', 'No access token in response')
                logger.error(f"[SMS_AUTH] Invalid response: {error_msg}")
                raise AuthenticationError(f"Authentication failed: {error_msg}")

            # Format credentials for storage
            user = data.get('user', {})
            credentials = {
                'bearer_token': data['accesstoken'],
                'refresh_token': data.get('refrestoken', ''),  # Note: API typo 'refrestoken'
                'client_id': data.get('client_id', user.get('client_id', '')),
                'client_name': data.get('client_name', 'ProjectForce'),
                'user_id': str(user.get('customer_id', '')),
                'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                'user_phone': from_phone,
                'user_email': user.get('email', ''),
                'timezone': data.get('timezone', 'US/Eastern'),
                'exp': data.get('exp', 0),
                'updated_at': datetime.utcnow().isoformat()
            }

            return credentials

    except urllib.error.URLError as e:
        if hasattr(e, 'code'):
            # HTTPError - server returned error status
            error_body = e.read().decode('utf-8') if hasattr(e, 'read') else str(e)
            logger.error(f"[SMS_AUTH] API HTTP error {e.code}: {error_body[:200]}")
            raise AuthenticationError(f"Authentication failed with status {e.code}: {error_body[:100]}")
        else:
            # URLError - network error
            logger.error(f"[SMS_AUTH] API request error: {e.reason}")
            raise AuthenticationError(f"Authentication request failed: {e.reason}")
    except TimeoutError:
        logger.error("[SMS_AUTH] API timeout")
        raise AuthenticationError("Authentication timed out")
    except json.JSONDecodeError as e:
        logger.error(f"[SMS_AUTH] Invalid JSON response: {e}")
        raise AuthenticationError(f"Invalid response from authentication API")


def _store_credentials(table, phone_number: str, credentials: Dict):
    """
    Store credentials in DynamoDB, keyed by phone number.

    Each phone number gets its own row, so multiple users can have
    concurrent active sessions.
    """
    try:
        # Calculate TTL based on token expiration (with some buffer for cleanup)
        exp = credentials.get('exp', 0)
        # Add 1 hour buffer after expiration for TTL cleanup
        ttl = int(exp) + 3600 if exp else int(datetime.utcnow().timestamp()) + 86400

        item = {
            'phone_number': phone_number,
            'bearer_token': credentials['bearer_token'],
            'refresh_token': credentials.get('refresh_token', ''),
            'client_id': credentials.get('client_id', ''),
            'client_name': credentials.get('client_name', 'ProjectForce'),
            'user_id': credentials.get('user_id', ''),
            'user_name': credentials.get('user_name', ''),
            'user_phone': credentials.get('user_phone', phone_number),
            'user_email': credentials.get('user_email', ''),
            'timezone': credentials.get('timezone', 'US/Eastern'),
            'exp': credentials.get('exp', 0),
            'updated_at': credentials.get('updated_at', datetime.utcnow().isoformat()),
            'ttl': ttl
        }

        table.put_item(Item=item)
        logger.info(f"[SMS_AUTH] Stored credentials for ***{phone_number[-4:]} (TTL: {ttl})")

    except Exception as e:
        logger.error(f"[SMS_AUTH] Failed to store credentials in DynamoDB: {e}")
        # Don't raise - credentials are still valid for this request
        # They just won't be cached for next time
