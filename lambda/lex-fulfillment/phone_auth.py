"""
Phone-based authentication module for Voice and SMS channels.

This module:
1. Checks Secrets Manager for existing valid credentials
2. If not found or expired, calls ProjectsForce phone-call-login API
3. Stores new credentials in Secrets Manager
4. All other Lambdas read credentials from Secrets Manager
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
CREDENTIALS_SECRET = os.environ.get('PF_SECRET_NAME', 'projectforce/api/credentials')
# Use SECRETS_REGION for cross-region access (secrets are in us-east-2, Lambda may be in us-east-1)
SECRETS_REGION = os.environ.get('SECRETS_REGION', os.environ.get('AWS_REGION', 'us-east-1'))


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
    Get existing credentials from Secrets Manager or authenticate via API.

    Flow:
    1. Check Secrets Manager for existing credentials
    2. If found and valid (same phone, not expired) -> return existing
    3. If not found or expired -> call API, store in Secrets Manager, return new

    Args:
        from_phone: Caller's phone number (from AWS Connect CustomerNumber or SMS originationNumber)
        to_phone: System phone number they called/texted (from AWS Connect SystemNumber or SMS destinationNumber)

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

    secrets = boto3.client('secretsmanager', region_name=SECRETS_REGION)

    # Step 1: Check Secrets Manager for existing credentials
    existing = _get_existing_credentials(secrets, from_clean)
    if existing:
        logger.info(f"[PHONE_AUTH] Using existing credentials for ***{from_clean[-4:]}")
        return existing

    # Step 2: Call API to authenticate
    logger.info(f"[PHONE_AUTH] Authenticating ***{from_clean[-4:]} via ***{to_clean[-4:]}")
    credentials = _call_auth_api(from_clean, to_clean)

    # Step 3: Store in Secrets Manager
    _store_credentials(secrets, credentials)
    logger.info(f"[PHONE_AUTH] Stored NEW credentials for user {credentials['user_id']}")

    return credentials


def _get_existing_credentials(secrets, from_phone: str) -> Optional[Dict]:
    """
    Check Secrets Manager for existing valid credentials.

    Returns credentials if:
    - Secret exists
    - Credentials are for the same phone number
    - Token has at least 2 minutes remaining (TOKEN_REFRESH_BUFFER_SECONDS)

    Returns None otherwise (triggering a fresh authentication).
    """
    # Refresh token if less than 2 minutes remaining
    TOKEN_REFRESH_BUFFER_SECONDS = 120

    try:
        response = secrets.get_secret_value(SecretId=CREDENTIALS_SECRET)
        existing = json.loads(response['SecretString'])

        # Check if credentials are for this phone
        stored_phone = existing.get('user_phone', '')
        if normalize_phone(stored_phone) != from_phone:
            logger.info(f"[PHONE_AUTH] Different phone - stored: ***{stored_phone[-4:] if stored_phone else 'none'}, current: ***{from_phone[-4:]}")
            return None

        # Check if token is expired or close to expiring
        exp = existing.get('exp', 0)
        now = datetime.utcnow().timestamp()
        remaining_seconds = exp - now
        remaining_mins = remaining_seconds / 60

        if remaining_seconds <= 0:
            logger.info(f"[PHONE_AUTH] Token EXPIRED - exp: {exp}, now: {now}")
            return None

        if remaining_seconds < TOKEN_REFRESH_BUFFER_SECONDS:
            logger.info(f"[PHONE_AUTH] Token expiring soon - {remaining_seconds:.0f}s ({remaining_mins:.1f}m) remaining, refreshing proactively")
            return None

        logger.info(f"[PHONE_AUTH] Token valid - {remaining_seconds:.0f}s ({remaining_mins:.1f}m) remaining")
        return existing

    except secrets.exceptions.ResourceNotFoundException:
        logger.info(f"[PHONE_AUTH] Secret {CREDENTIALS_SECRET} not found")
        return None
    except Exception as e:
        logger.warning(f"[PHONE_AUTH] Error reading credentials: {e}")
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
                logger.error(f"[PHONE_AUTH] API failed: {status_code} - {error_msg}")
                raise AuthenticationError(f"Authentication failed: {error_msg}")

            data = json.loads(response_body)

            if 'accesstoken' not in data:
                error_msg = data.get('message', 'No access token in response')
                logger.error(f"[PHONE_AUTH] Invalid response: {error_msg}")
                raise AuthenticationError(f"Authentication failed: {error_msg}")

            # Format credentials for storage
            user = data.get('user', {})
            credentials = {
                'bearer_token': data['accesstoken'],
                'refresh_token': data.get('refrestoken', ''),  # Note: API typo 'refrestoken'
                'client_id': user.get('client_id', ''),
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
            logger.error(f"[PHONE_AUTH] API HTTP error {e.code}: {error_body[:200]}")
            raise AuthenticationError(f"Authentication failed with status {e.code}: {error_body[:100]}")
        else:
            # URLError - network error
            logger.error(f"[PHONE_AUTH] API request error: {e.reason}")
            raise AuthenticationError(f"Authentication request failed: {e.reason}")
    except TimeoutError:
        logger.error("[PHONE_AUTH] API timeout")
        raise AuthenticationError("Authentication timed out")
    except json.JSONDecodeError as e:
        logger.error(f"[PHONE_AUTH] Invalid JSON response: {e}")
        raise AuthenticationError(f"Invalid response from authentication API")


def _store_credentials(secrets, credentials: Dict):
    """
    Store credentials in Secrets Manager.

    Creates or updates the secret.
    """
    try:
        secrets.put_secret_value(
            SecretId=CREDENTIALS_SECRET,
            SecretString=json.dumps(credentials)
        )
    except secrets.exceptions.ResourceNotFoundException:
        # Secret doesn't exist, create it
        logger.info(f"[PHONE_AUTH] Creating new secret {CREDENTIALS_SECRET}")
        secrets.create_secret(
            Name=CREDENTIALS_SECRET,
            SecretString=json.dumps(credentials)
        )
    except Exception as e:
        logger.error(f"[PHONE_AUTH] Failed to store credentials: {e}")
        # Don't raise - credentials are still valid for this request
        # They just won't be cached for next time
