"""
VAPI Dashboard - Auth Lambda
Handles: login, logout, token verification
"""
import json
import os
import hashlib
import hmac
import base64
import time
import boto3
import logging
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
REGION = os.environ.get('AWS_REGION', 'us-east-1')
USERS_TABLE = os.environ.get('USERS_TABLE', f'pf-syn-vapi-dashboard-users-{ENVIRONMENT}')
TENANTS_TABLE = os.environ.get('TENANTS_TABLE', f'pf-syn-vapi-dashboard-tenants-{ENVIRONMENT}')
JWT_SECRET = os.environ.get('JWT_SECRET', 'change-this-secret-in-production')
JWT_EXPIRY_HOURS = int(os.environ.get('JWT_EXPIRY_HOURS', '24'))

# DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name=REGION)
users_table = dynamodb.Table(USERS_TABLE)
tenants_table = dynamodb.Table(TENANTS_TABLE)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler."""
    try:
        logger.info(f"Auth request: {json.dumps(event)[:500]}")

        # Parse request
        http_method = event.get('requestContext', {}).get('http', {}).get('method', 'POST')
        path = event.get('rawPath', event.get('path', '/'))

        # Parse body
        body = event.get('body', '{}')
        if isinstance(body, str):
            try:
                body = json.loads(body) if body else {}
            except json.JSONDecodeError:
                body = {}

        # Route request
        if '/login' in path:
            return handle_login(body)
        elif '/verify' in path:
            return handle_verify(event)
        elif '/logout' in path:
            return handle_logout(event)
        else:
            return response(404, {'error': 'Not found'})

    except Exception as e:
        logger.error(f"Auth error: {e}", exc_info=True)
        return response(500, {'error': 'Internal server error'})


def handle_login(body: Dict) -> Dict:
    """
    Handle login request.
    Expects: { username, password, tenant_id }
    Returns: { token, user, tenant }
    """
    username = body.get('username', '').strip().lower()
    password = body.get('password', '')
    tenant_id = body.get('tenant_id', '').strip().lower()

    if not username or not password:
        return response(400, {'error': 'Username and password required'})

    # Get user from DynamoDB
    try:
        result = users_table.get_item(Key={'username': username})
        user = result.get('Item')

        if not user:
            logger.warning(f"Login failed: user not found - {username}")
            return response(401, {'error': 'Invalid username or password'})

        # Verify password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if user.get('password_hash') != password_hash:
            logger.warning(f"Login failed: wrong password - {username}")
            return response(401, {'error': 'Invalid username or password'})

        # If tenant_id provided, verify user has access
        user_tenant_id = user.get('tenant_id', '')
        user_role = user.get('role', 'user')

        # Admin can access any tenant, others must match
        if tenant_id:
            if user_role != 'admin' and user_tenant_id != tenant_id:
                logger.warning(f"Login failed: tenant mismatch - {username} tried {tenant_id}")
                return response(401, {'error': 'Access denied to this tenant'})
            effective_tenant_id = tenant_id
        else:
            effective_tenant_id = user_tenant_id

        # Get tenant info
        tenant = None
        if effective_tenant_id:
            tenant_result = tenants_table.get_item(Key={'tenant_id': effective_tenant_id})
            tenant = tenant_result.get('Item')

        # Generate JWT token
        token = generate_jwt({
            'username': username,
            'tenant_id': effective_tenant_id,
            'role': user_role,
            'name': user.get('name', username)
        })

        logger.info(f"Login successful: {username} -> {effective_tenant_id}")

        return response(200, {
            'token': token,
            'user': {
                'username': username,
                'name': user.get('name', username),
                'role': user_role,
                'tenant_id': effective_tenant_id
            },
            'tenant': {
                'id': tenant.get('tenant_id') if tenant else None,
                'name': tenant.get('name') if tenant else None
            } if tenant else None
        })

    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return response(500, {'error': 'Login failed'})


def handle_verify(event: Dict) -> Dict:
    """
    Verify JWT token.
    Token should be in Authorization header: Bearer <token>
    """
    token = extract_token(event)

    if not token:
        return response(401, {'error': 'No token provided'})

    payload = verify_jwt(token)

    if not payload:
        return response(401, {'error': 'Invalid or expired token'})

    return response(200, {
        'valid': True,
        'user': {
            'username': payload.get('username'),
            'name': payload.get('name'),
            'role': payload.get('role'),
            'tenant_id': payload.get('tenant_id')
        }
    })


def handle_logout(event: Dict) -> Dict:
    """Handle logout - just return success (client clears token)."""
    return response(200, {'message': 'Logged out successfully'})


# ===========================================================================
# JWT Utilities (simple implementation without external dependencies)
# ===========================================================================

def generate_jwt(payload: Dict) -> str:
    """Generate a simple JWT token."""
    header = {'alg': 'HS256', 'typ': 'JWT'}

    # Add expiry
    payload['exp'] = int(time.time()) + (JWT_EXPIRY_HOURS * 3600)
    payload['iat'] = int(time.time())

    # Encode
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')

    # Sign
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        JWT_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def verify_jwt(token: str) -> Optional[Dict]:
    """Verify JWT token and return payload if valid."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature_b64 = parts

        # Verify signature
        message = f"{header_b64}.{payload_b64}"
        expected_signature = hmac.new(
            JWT_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        expected_signature_b64 = base64.urlsafe_b64encode(expected_signature).decode().rstrip('=')

        if signature_b64 != expected_signature_b64:
            logger.warning("JWT signature mismatch")
            return None

        # Decode payload
        # Add padding if needed
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding

        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        # Check expiry
        if payload.get('exp', 0) < time.time():
            logger.warning("JWT expired")
            return None

        return payload

    except Exception as e:
        logger.error(f"JWT verification error: {e}")
        return None


def extract_token(event: Dict) -> Optional[str]:
    """Extract JWT token from Authorization header."""
    headers = event.get('headers', {})

    # Try different header formats (API Gateway normalizes to lowercase)
    auth_header = headers.get('authorization') or headers.get('Authorization', '')

    if auth_header.startswith('Bearer '):
        return auth_header[7:]

    return None


def response(status_code: int, body: Dict) -> Dict:
    """Create API Gateway response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps(body)
    }
