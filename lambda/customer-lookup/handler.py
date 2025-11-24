"""
Lambda Function: Customer Lookup Service

Provides customer identification services by phone number, customer ID, or email.
Integrates with DynamoDB for customer data storage and lookup.

Environment Variables:
    CUSTOMER_TABLE: DynamoDB table for customer data
    LOG_LEVEL: Logging level (default: INFO)
    CACHE_TTL_SECONDS: Cache TTL for lookups (default: 300)
"""

import json
import boto3
import os
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta

# Pydantic models removed for simplicity - using raw dictionaries
# from models import (
#     CustomerLookupRequest, CustomerLookupResponse,
#     Customer, PhoneNumber
# )
# from pydantic import ValidationError

# Configure logging
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Environment variables
CUSTOMER_TABLE = os.environ.get('CUSTOMER_TABLE', 'pf-customers-dev')
CACHE_TTL_SECONDS = int(os.environ.get('CACHE_TTL_SECONDS', '300'))

# In-memory cache (Lambda container reuse)
_customer_cache: Dict[str, tuple[Dict, datetime]] = {}

# DynamoDB table
try:
    customer_table = dynamodb.Table(CUSTOMER_TABLE)
except Exception as e:
    logger.error(f"Failed to initialize DynamoDB table {CUSTOMER_TABLE}: {e}")
    customer_table = None


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for customer lookup

    Supports multiple lookup methods:
    - lookup_by_phone: Find customer by phone number
    - lookup_by_id: Find customer by customer ID
    - lookup_by_email: Find customer by email address
    - create_customer: Create new customer record
    - update_customer: Update existing customer record

    Args:
        event: Lambda event with action and lookup parameters
        context: Lambda context object

    Returns:
        Customer data or error response
    """
    request_id = context.request_id if hasattr(context, 'request_id') else 'unknown'
    logger.info(f"Request {request_id}: Processing customer lookup")

    try:
        # Extract action
        action = event.get('action', 'lookup_by_phone')

        logger.info(f"Action: {action}")

        # Route to appropriate handler
        if action == 'lookup_by_phone':
            return handle_lookup_by_phone(event)

        elif action == 'lookup_by_id':
            return handle_lookup_by_id(event)

        elif action == 'lookup_by_email':
            return handle_lookup_by_email(event)

        elif action == 'create_customer':
            return handle_create_customer(event)

        elif action == 'update_customer':
            return handle_update_customer(event)

        else:
            return {
                'statusCode': 400,
                'error': f'Unknown action: {action}'
            }

    except Exception as e:
        logger.exception(f"Request {request_id}: Error processing customer lookup")
        return {
            'statusCode': 500,
            'error': 'Internal server error',
            'message': str(e)
        }


def handle_lookup_by_phone(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Look up customer by phone number

    Args:
        event: Event with phone_number field

    Returns:
        Customer data if found, error otherwise
    """
    phone_number = event.get('phone_number')

    if not phone_number:
        return {
            'statusCode': 400,
            'error': 'phone_number is required'
        }

    # Normalize phone number
    normalized_phone = _normalize_phone(phone_number)

    logger.info(f"Looking up customer by phone: {_mask_phone(normalized_phone)}")

    # Check cache first
    cached_customer = _get_from_cache(f"phone:{normalized_phone}")
    if cached_customer:
        logger.info("Customer found in cache")
        return {
            'statusCode': 200,
            'customer_id': cached_customer.get('customer_id'),
            'customer': cached_customer,
            'source': 'cache'
        }

    # Query DynamoDB
    try:
        if not customer_table:
            # Mock mode - return test customer for development
            logger.warning("DynamoDB table not available, using mock data")
            return _get_mock_customer_by_phone(normalized_phone)

        response = customer_table.query(
            IndexName='phone-index',
            KeyConditionExpression='phone_number = :phone',
            ExpressionAttributeValues={
                ':phone': normalized_phone
            },
            Limit=1
        )

        items = response.get('Items', [])

        if items:
            customer_data = items[0]

            # Cache the result
            _put_in_cache(f"phone:{normalized_phone}", customer_data)

            logger.info(f"Customer found: {customer_data.get('customer_id')}")

            return {
                'statusCode': 200,
                'customer_id': customer_data.get('customer_id'),
                'customer': customer_data,
                'source': 'dynamodb'
            }

        else:
            logger.info("Customer not found")
            return {
                'statusCode': 404,
                'error': 'Customer not found',
                'customer_found': False
            }

    except Exception as e:
        logger.exception("Error querying DynamoDB")
        return {
            'statusCode': 500,
            'error': 'Database error',
            'message': str(e)
        }


def handle_lookup_by_id(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Look up customer by customer ID

    Args:
        event: Event with customer_id field

    Returns:
        Customer data if found, error otherwise
    """
    customer_id = event.get('customer_id')

    if not customer_id:
        return {
            'statusCode': 400,
            'error': 'customer_id is required'
        }

    logger.info(f"Looking up customer by ID: {customer_id}")

    # Check cache
    cached_customer = _get_from_cache(f"id:{customer_id}")
    if cached_customer:
        logger.info("Customer found in cache")
        return {
            'statusCode': 200,
            'customer': cached_customer,
            'source': 'cache'
        }

    # Query DynamoDB
    try:
        if not customer_table:
            return _get_mock_customer_by_id(customer_id)

        response = customer_table.get_item(
            Key={'customer_id': customer_id}
        )

        if 'Item' in response:
            customer_data = response['Item']

            # Cache the result
            _put_in_cache(f"id:{customer_id}", customer_data)

            logger.info(f"Customer found: {customer_data.get('customer_id')}")

            return {
                'statusCode': 200,
                'customer': customer_data,
                'source': 'dynamodb'
            }

        else:
            logger.info("Customer not found")
            return {
                'statusCode': 404,
                'error': 'Customer not found'
            }

    except Exception as e:
        logger.exception("Error querying DynamoDB")
        return {
            'statusCode': 500,
            'error': 'Database error',
            'message': str(e)
        }


def handle_lookup_by_email(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Look up customer by email address

    Args:
        event: Event with email field

    Returns:
        Customer data if found, error otherwise
    """
    email = event.get('email')

    if not email:
        return {
            'statusCode': 400,
            'error': 'email is required'
        }

    logger.info(f"Looking up customer by email: {_mask_email(email)}")

    # Query DynamoDB
    try:
        if not customer_table:
            return _get_mock_customer_by_email(email)

        response = customer_table.query(
            IndexName='email-index',
            KeyConditionExpression='email = :email',
            ExpressionAttributeValues={
                ':email': email.lower()
            },
            Limit=1
        )

        items = response.get('Items', [])

        if items:
            customer_data = items[0]

            logger.info(f"Customer found: {customer_data.get('customer_id')}")

            return {
                'statusCode': 200,
                'customer': customer_data,
                'source': 'dynamodb'
            }

        else:
            logger.info("Customer not found")
            return {
                'statusCode': 404,
                'error': 'Customer not found'
            }

    except Exception as e:
        logger.exception("Error querying DynamoDB")
        return {
            'statusCode': 500,
            'error': 'Database error',
            'message': str(e)
        }


def handle_create_customer(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create new customer record

    Args:
        event: Event with customer data

    Returns:
        Created customer data
    """
    logger.info("Creating new customer")

    try:
        # Get customer data (Pydantic validation removed for simplicity)
        customer_data = event.get('customer', {})

        # Basic validation
        if not customer_data.get('customer_id'):
            return {
                'statusCode': 400,
                'error': 'Invalid customer data',
                'details': 'customer_id is required'
            }

        # Store in DynamoDB
        if not customer_table:
            logger.warning("DynamoDB table not available, skipping storage")
        else:
            customer_table.put_item(
                Item=customer_data
            )

        logger.info(f"Customer created: {customer_data.get('customer_id')}")

        return {
            'statusCode': 201,
            'customer_id': customer_data.get('customer_id'),
            'customer': customer_data
        }

    except Exception as e:
        logger.exception("Error creating customer")
        return {
            'statusCode': 500,
            'error': 'Database error',
            'message': str(e)
        }


def handle_update_customer(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update existing customer record

    Args:
        event: Event with customer_id and update data

    Returns:
        Updated customer data
    """
    customer_id = event.get('customer_id')
    updates = event.get('updates', {})

    if not customer_id:
        return {
            'statusCode': 400,
            'error': 'customer_id is required'
        }

    logger.info(f"Updating customer: {customer_id}")

    try:
        if not customer_table:
            return {
                'statusCode': 503,
                'error': 'Service unavailable'
            }

        # Build update expression
        update_expr = "SET "
        expr_values = {}
        expr_names = {}

        for key, value in updates.items():
            if key not in ['customer_id', 'created_at']:  # Don't update these
                attr_name = f"#{key}"
                attr_value = f":{key}"
                update_expr += f"{attr_name} = {attr_value}, "
                expr_names[attr_name] = key
                expr_values[attr_value] = value

        update_expr = update_expr.rstrip(', ')
        update_expr += ", updated_at = :updated_at"
        expr_values[':updated_at'] = int(datetime.utcnow().timestamp() * 1000)

        # Update DynamoDB
        response = customer_table.update_item(
            Key={'customer_id': customer_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names if expr_names else None,
            ExpressionAttributeValues=expr_values,
            ReturnValues='ALL_NEW'
        )

        updated_customer = response['Attributes']

        # Invalidate cache
        _invalidate_cache(customer_id)

        logger.info(f"Customer updated: {customer_id}")

        return {
            'statusCode': 200,
            'customer': updated_customer
        }

    except Exception as e:
        logger.exception("Error updating customer")
        return {
            'statusCode': 500,
            'error': 'Database error',
            'message': str(e)
        }


# ============================================================================
# Cache Functions
# ============================================================================

def _get_from_cache(key: str) -> Optional[Dict]:
    """Get customer from cache if not expired"""
    if key in _customer_cache:
        customer, expires_at = _customer_cache[key]
        if datetime.utcnow() < expires_at:
            return customer
        else:
            # Expired, remove from cache
            del _customer_cache[key]

    return None


def _put_in_cache(key: str, customer: Dict) -> None:
    """Put customer in cache with TTL"""
    expires_at = datetime.utcnow() + timedelta(seconds=CACHE_TTL_SECONDS)
    _customer_cache[key] = (customer, expires_at)


def _invalidate_cache(customer_id: str) -> None:
    """Invalidate all cache entries for a customer"""
    keys_to_remove = [k for k in _customer_cache.keys() if customer_id in k]
    for key in keys_to_remove:
        del _customer_cache[key]


# ============================================================================
# Helper Functions
# ============================================================================

def _normalize_phone(phone: str) -> str:
    """Normalize phone number to E.164 format"""
    # Remove all non-digit characters
    digits = ''.join(c for c in phone if c.isdigit())

    # Add +1 if missing (US numbers)
    if len(digits) == 10:
        digits = '1' + digits

    return '+' + digits


def _mask_phone(phone: str) -> str:
    """Mask phone number for logging"""
    if len(phone) > 4:
        return '*' * (len(phone) - 4) + phone[-4:]
    return '*' * len(phone)


def _mask_email(email: str) -> str:
    """Mask email for logging"""
    if '@' in email:
        local, domain = email.split('@')
        if len(local) > 2:
            masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
        else:
            masked_local = '*' * len(local)
        return f"{masked_local}@{domain}"
    return email


# ============================================================================
# Mock Data (for testing without DynamoDB)
# ============================================================================

def _get_mock_customer_by_phone(phone: str) -> Dict[str, Any]:
    """Return mock customer data for testing"""
    logger.warning("Using mock customer data")

    mock_customer = {
        'customer_id': "MOCK123",
        'phone_number': phone,
        'first_name': "Test",
        'last_name': "Customer",
        'email': "test@example.com",
        'customer_type': "B2C",
        'created_at': int(datetime.utcnow().timestamp() * 1000)
    }

    return {
        'statusCode': 200,
        'customer_id': mock_customer['customer_id'],
        'customer': mock_customer,
        'source': 'mock'
    }


def _get_mock_customer_by_id(customer_id: str) -> Dict[str, Any]:
    """Return mock customer data for testing"""
    logger.warning("Using mock customer data")

    mock_customer = {
        'customer_id': customer_id,
        'phone_number': "+18005551234",
        'first_name': "Test",
        'last_name': "Customer",
        'email': "test@example.com",
        'customer_type': "B2C",
        'created_at': int(datetime.utcnow().timestamp() * 1000)
    }

    return {
        'statusCode': 200,
        'customer': mock_customer,
        'source': 'mock'
    }


def _get_mock_customer_by_email(email: str) -> Dict[str, Any]:
    """Return mock customer data for testing"""
    logger.warning("Using mock customer data")

    mock_customer = {
        'customer_id': "MOCK123",
        'phone_number': "+18005551234",
        'first_name': "Test",
        'last_name': "Customer",
        'email': email,
        'customer_type': "B2C",
        'created_at': int(datetime.utcnow().timestamp() * 1000)
    }

    return {
        'statusCode': 200,
        'customer': mock_customer,
        'source': 'mock'
    }
