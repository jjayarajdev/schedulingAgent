"""
VAPI Dashboard - API Lambda
Fetches call data from VAPI API, filtered by tenant
"""
import json
import os
import urllib.request
import urllib.error
import boto3
import logging
import hashlib
import hmac
import base64
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
REGION = os.environ.get('AWS_REGION', 'us-east-1')
TENANTS_TABLE = os.environ.get('TENANTS_TABLE', f'pf-syn-vapi-dashboard-tenants-{ENVIRONMENT}')
REPORTS_TABLE = os.environ.get('REPORTS_TABLE', f'pf-syn-vapi-dashboard-reports-{ENVIRONMENT}')
VAPI_API_KEY = os.environ.get('VAPI_API_KEY', '')
JWT_SECRET = os.environ.get('JWT_SECRET', 'change-this-secret-in-production')

# DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name=REGION)
tenants_table = dynamodb.Table(TENANTS_TABLE)
reports_table = dynamodb.Table(REPORTS_TABLE)

# VAPI API base URL
VAPI_BASE_URL = 'https://api.vapi.ai'


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler."""
    try:
        logger.info(f"API request: {json.dumps(event)[:500]}")

        # Verify auth token
        user = verify_auth(event)
        if not user:
            return response(401, {'error': 'Unauthorized'})

        # Parse request
        path = event.get('rawPath', event.get('path', '/'))
        query_params = event.get('queryStringParameters', {}) or {}

        # Get tenant info
        tenant_id = user.get('tenant_id')
        tenant = get_tenant(tenant_id)

        if not tenant:
            return response(400, {'error': 'Tenant not found'})

        # Route request
        if '/calls' in path:
            return handle_get_calls(tenant, query_params, user)
        elif '/call/' in path:
            call_id = path.split('/call/')[-1].split('/')[0]
            return handle_get_call(tenant, call_id, user)
        elif '/stats' in path:
            return handle_get_stats(tenant, query_params, user)
        elif '/costs' in path:
            return handle_get_costs(tenant, query_params, user)
        elif '/reports' in path:
            return handle_get_reports(tenant, query_params, user)
        elif '/tenants' in path and user.get('role') == 'admin':
            return handle_get_tenants(user)
        else:
            return response(404, {'error': 'Not found'})

    except Exception as e:
        logger.error(f"API error: {e}", exc_info=True)
        return response(500, {'error': 'Internal server error'})


def handle_get_calls(tenant: Dict, query_params: Dict, user: Dict) -> Dict:
    """
    Get calls list from VAPI, filtered by tenant's phone number.
    Query params: limit, start_date, end_date
    """
    phone_number_id = tenant.get('vapi_phone_number_id')
    if not phone_number_id:
        return response(400, {'error': 'Tenant has no VAPI phone number configured'})

    # Build VAPI API request
    limit = min(int(query_params.get('limit', 100)), 1000)

    # Date filtering
    start_date = query_params.get('start_date', '')
    end_date = query_params.get('end_date', '')

    # Fetch from VAPI
    params = {
        'phoneNumberId': phone_number_id,
        'limit': str(limit)
    }

    if start_date:
        params['createdAtGe'] = start_date
    if end_date:
        params['createdAtLe'] = end_date

    calls = vapi_request('GET', '/call', params)

    if calls is None:
        return response(500, {'error': 'Failed to fetch calls from VAPI'})

    # Process calls - extract relevant fields
    processed_calls = []
    for call in calls:
        processed_calls.append(process_call(call))

    return response(200, {
        'calls': processed_calls,
        'count': len(processed_calls),
        'tenant': {
            'id': tenant.get('tenant_id'),
            'name': tenant.get('name')
        }
    })


def handle_get_call(tenant: Dict, call_id: str, user: Dict) -> Dict:
    """Get single call details including transcript."""
    phone_number_id = tenant.get('vapi_phone_number_id')

    # Fetch call from VAPI
    call = vapi_request('GET', f'/call/{call_id}')

    if call is None:
        return response(404, {'error': 'Call not found'})

    # Verify call belongs to this tenant
    call_phone_id = call.get('phoneNumberId', '')
    if call_phone_id != phone_number_id and user.get('role') != 'admin':
        return response(403, {'error': 'Access denied to this call'})

    # Return full call details
    return response(200, {
        'call': process_call(call, include_transcript=True)
    })


def handle_get_stats(tenant: Dict, query_params: Dict, user: Dict) -> Dict:
    """Get aggregated statistics for tenant."""
    phone_number_id = tenant.get('vapi_phone_number_id')
    if not phone_number_id:
        return response(400, {'error': 'Tenant has no VAPI phone number configured'})

    # Date range (default: last 30 days)
    days = int(query_params.get('days', 30))
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%dT00:00:00Z')

    # Fetch calls
    calls = vapi_request('GET', '/call', {
        'phoneNumberId': phone_number_id,
        'limit': '1000',
        'createdAtGe': start_date
    })

    if calls is None:
        return response(500, {'error': 'Failed to fetch calls from VAPI'})

    # Calculate stats
    total_calls = len(calls)
    successful_calls = 0
    failed_calls = 0
    total_duration = 0
    total_cost = 0
    end_reasons = {}
    daily_counts = {}

    for call in calls:
        # Success evaluation
        analysis = call.get('analysis') or {}
        success = analysis.get('successEvaluation')
        if success == 'true' or success == True:
            successful_calls += 1
        elif success == 'false' or success == False:
            failed_calls += 1

        # Duration
        cost_data = call.get('cost') or {}
        duration = cost_data.get('totalDuration', 0) or 0
        total_duration += duration

        # Cost
        cost = sum([
            cost_data.get('llm', 0) or 0,
            cost_data.get('stt', 0) or 0,
            cost_data.get('tts', 0) or 0,
            cost_data.get('vapi', 0) or 0,
            cost_data.get('transport', 0) or 0
        ])
        total_cost += cost

        # End reasons
        end_reason = call.get('endedReason', 'unknown')
        end_reasons[end_reason] = end_reasons.get(end_reason, 0) + 1

        # Daily counts
        created_at = call.get('createdAt', '')
        if created_at:
            date_key = created_at[:10]  # YYYY-MM-DD
            daily_counts[date_key] = daily_counts.get(date_key, 0) + 1

    # Calculate averages
    avg_duration = total_duration / total_calls if total_calls > 0 else 0
    avg_cost = total_cost / total_calls if total_calls > 0 else 0
    success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0

    return response(200, {
        'stats': {
            'total_calls': total_calls,
            'successful_calls': successful_calls,
            'failed_calls': failed_calls,
            'success_rate': round(success_rate, 1),
            'total_duration_seconds': round(total_duration, 1),
            'avg_duration_seconds': round(avg_duration, 1),
            'total_cost': round(total_cost, 4),
            'avg_cost_per_call': round(avg_cost, 4),
            'end_reasons': end_reasons,
            'daily_counts': daily_counts
        },
        'period': {
            'days': days,
            'start_date': start_date,
            'end_date': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        },
        'tenant': {
            'id': tenant.get('tenant_id'),
            'name': tenant.get('name')
        }
    })


def handle_get_costs(tenant: Dict, query_params: Dict, user: Dict) -> Dict:
    """Get detailed cost breakdown for tenant."""
    phone_number_id = tenant.get('vapi_phone_number_id')
    if not phone_number_id:
        return response(400, {'error': 'Tenant has no VAPI phone number configured'})

    # Date range
    days = int(query_params.get('days', 30))
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%dT00:00:00Z')

    # Fetch calls
    calls = vapi_request('GET', '/call', {
        'phoneNumberId': phone_number_id,
        'limit': '1000',
        'createdAtGe': start_date
    })

    if calls is None:
        return response(500, {'error': 'Failed to fetch calls from VAPI'})

    # Calculate cost breakdown
    total_llm = 0
    total_stt = 0
    total_tts = 0
    total_vapi = 0
    total_transport = 0
    daily_costs = {}

    for call in calls:
        cost_data = call.get('cost') or {}

        llm = cost_data.get('llm', 0) or 0
        stt = cost_data.get('stt', 0) or 0
        tts = cost_data.get('tts', 0) or 0
        vapi = cost_data.get('vapi', 0) or 0
        transport = cost_data.get('transport', 0) or 0

        total_llm += llm
        total_stt += stt
        total_tts += tts
        total_vapi += vapi
        total_transport += transport

        # Daily costs
        created_at = call.get('createdAt', '')
        if created_at:
            date_key = created_at[:10]
            if date_key not in daily_costs:
                daily_costs[date_key] = 0
            daily_costs[date_key] += llm + stt + tts + vapi + transport

    total_cost = total_llm + total_stt + total_tts + total_vapi + total_transport

    return response(200, {
        'costs': {
            'total': round(total_cost, 4),
            'breakdown': {
                'llm': round(total_llm, 4),
                'stt': round(total_stt, 4),
                'tts': round(total_tts, 4),
                'vapi': round(total_vapi, 4),
                'transport': round(total_transport, 4)
            },
            'daily': daily_costs,
            'call_count': len(calls),
            'avg_per_call': round(total_cost / len(calls), 4) if calls else 0
        },
        'period': {
            'days': days,
            'start_date': start_date,
            'end_date': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        },
        'tenant': {
            'id': tenant.get('tenant_id'),
            'name': tenant.get('name')
        }
    })


def handle_get_tenants(user: Dict) -> Dict:
    """Get all tenants (admin only)."""
    try:
        result = tenants_table.scan()
        tenants = result.get('Items', [])

        return response(200, {
            'tenants': [{
                'id': t.get('tenant_id'),
                'name': t.get('name'),
                'phone_number': t.get('vapi_phone_number')
            } for t in tenants]
        })
    except Exception as e:
        logger.error(f"Error fetching tenants: {e}")
        return response(500, {'error': 'Failed to fetch tenants'})


def handle_get_reports(tenant: Dict, query_params: Dict, user: Dict) -> Dict:
    """
    Get reports for tenant.
    Query params: date (YYYY-MM-DD), limit (default 30)
    """
    tenant_id = tenant.get('tenant_id')

    # If specific date requested
    report_date = query_params.get('date')

    if report_date:
        # Get single report
        try:
            result = reports_table.get_item(
                Key={'tenant_id': tenant_id, 'report_date': report_date}
            )
            report = result.get('Item')

            if not report:
                return response(404, {'error': f'No report found for {report_date}'})

            return response(200, {
                'report': {
                    'date': report.get('report_date'),
                    'generated_at': report.get('generated_at'),
                    'total_calls': report.get('total_calls', 0),
                    'markdown': report.get('markdown', ''),
                    'metrics': report.get('metrics', {})
                },
                'tenant': {
                    'id': tenant_id,
                    'name': tenant.get('name')
                }
            })
        except Exception as e:
            logger.error(f"Error fetching report: {e}")
            return response(500, {'error': 'Failed to fetch report'})
    else:
        # List recent reports
        limit = min(int(query_params.get('limit', 30)), 100)

        try:
            result = reports_table.query(
                KeyConditionExpression='tenant_id = :tid',
                ExpressionAttributeValues={':tid': tenant_id},
                ScanIndexForward=False,  # Most recent first
                Limit=limit
            )
            reports = result.get('Items', [])

            return response(200, {
                'reports': [{
                    'date': r.get('report_date'),
                    'generated_at': r.get('generated_at'),
                    'total_calls': r.get('total_calls', 0),
                    'metrics': r.get('metrics', {})
                } for r in reports],
                'count': len(reports),
                'tenant': {
                    'id': tenant_id,
                    'name': tenant.get('name')
                }
            })
        except Exception as e:
            logger.error(f"Error listing reports: {e}")
            return response(500, {'error': 'Failed to list reports'})


# ===========================================================================
# Helper Functions
# ===========================================================================

def process_call(call: Dict, include_transcript: bool = False) -> Dict:
    """Process a VAPI call record into our format."""
    cost_data = call.get('cost') or {}
    analysis = call.get('analysis') or {}
    customer = call.get('customer') or {}

    total_cost = sum([
        cost_data.get('llm', 0) or 0,
        cost_data.get('stt', 0) or 0,
        cost_data.get('tts', 0) or 0,
        cost_data.get('vapi', 0) or 0,
        cost_data.get('transport', 0) or 0
    ])

    processed = {
        'id': call.get('id'),
        'status': call.get('status'),
        'ended_reason': call.get('endedReason'),
        'duration_seconds': cost_data.get('totalDuration', 0) or 0,
        'cost': round(total_cost, 4),
        'customer_number': customer.get('number', ''),
        'success_evaluation': analysis.get('successEvaluation'),
        'summary': analysis.get('summary', ''),
        'created_at': call.get('createdAt'),
        'started_at': call.get('startedAt'),
        'ended_at': call.get('endedAt')
    }

    if include_transcript:
        processed['transcript'] = call.get('transcript', '')
        processed['messages'] = call.get('messages', [])
        processed['cost_breakdown'] = {
            'llm': cost_data.get('llm', 0) or 0,
            'stt': cost_data.get('stt', 0) or 0,
            'tts': cost_data.get('tts', 0) or 0,
            'vapi': cost_data.get('vapi', 0) or 0,
            'transport': cost_data.get('transport', 0) or 0
        }

    return processed


def get_tenant(tenant_id: str) -> Optional[Dict]:
    """Get tenant from DynamoDB."""
    try:
        result = tenants_table.get_item(Key={'tenant_id': tenant_id})
        return result.get('Item')
    except Exception as e:
        logger.error(f"Error getting tenant: {e}")
        return None


def vapi_request(method: str, endpoint: str, params: Dict = None) -> Optional[Any]:
    """Make request to VAPI API."""
    if not VAPI_API_KEY:
        logger.error("VAPI_API_KEY not configured")
        return None

    url = f"{VAPI_BASE_URL}{endpoint}"

    if params and method == 'GET':
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        url = f"{url}?{query_string}"

    try:
        req = urllib.request.Request(url, method=method)
        req.add_header('Authorization', f'Bearer {VAPI_API_KEY}')
        req.add_header('Content-Type', 'application/json')

        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())

    except urllib.error.HTTPError as e:
        logger.error(f"VAPI API error: {e.code} - {e.read().decode()}")
        return None
    except Exception as e:
        logger.error(f"VAPI request error: {e}")
        return None


def verify_auth(event: Dict) -> Optional[Dict]:
    """Verify JWT token and return user info."""
    headers = event.get('headers', {})
    auth_header = headers.get('authorization') or headers.get('Authorization', '')

    if not auth_header.startswith('Bearer '):
        return None

    token = auth_header[7:]

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
            return None

        # Decode payload
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding

        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        # Check expiry
        if payload.get('exp', 0) < time.time():
            return None

        return payload

    except Exception as e:
        logger.error(f"Token verification error: {e}")
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
