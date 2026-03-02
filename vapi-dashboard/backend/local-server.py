#!/usr/bin/env python3
"""
Local development server for VAPI Dashboard
Mocks the AWS Lambda backend for local testing
"""
import json
import hashlib
import hmac
import base64
import time
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests

# Configuration
PORT = 8080
JWT_SECRET = 'local-dev-secret'
VAPI_API_KEY = os.environ.get('VAPI_KEY', 'a4ed6edd-9a1c-4a67-ba61-2a1fa2186c6c')

# Set environment variable for report handler module
os.environ['VAPI_API_KEY'] = VAPI_API_KEY
VAPI_BASE_URL = 'https://api.vapi.ai'

# Simple cache with TTL
CACHE = {}
CACHE_TTL = 60  # seconds

def get_cached(key):
    if key in CACHE:
        data, timestamp = CACHE[key]
        if time.time() - timestamp < CACHE_TTL:
            return data
        del CACHE[key]
    return None

def set_cached(key, data):
    CACHE[key] = (data, time.time())

# Mock data
USERS = {
    'admin': {
        'username': 'admin',
        'password_hash': hashlib.sha256('admin123'.encode()).hexdigest(),
        'tenant_id': 'wtu',
        'role': 'admin',
        'name': 'Admin User'
    }
}

TENANTS = {
    'wtu': {
        'tenant_id': 'wtu',
        'name': 'Window Treatment Universe',
        'vapi_phone_number_id': '04839e46-2cbc-467e-8e01-638900654c36',
        'vapi_phone_number': '+12038946599'
    },
    'pf': {
        'tenant_id': 'pf',
        'name': 'ProjectsForce',
        'vapi_phone_number_id': '6b7ac954-1f6e-460d-962a-48883d31c1f0',
        'vapi_phone_number': '+12185516488'
    }
}

# All available phone numbers for filtering
PHONE_NUMBERS = [
    {'id': '6b7ac954-1f6e-460d-962a-48883d31c1f0', 'number': '+1 (218) 551-6488', 'name': 'PF-Agent'},
    {'id': '1c99c266-9778-4809-bf5e-dba30326a0ae', 'number': '+1 (862) 420-0502', 'name': 'PF-Agent-Dev'},
    {'id': '04839e46-2cbc-467e-8e01-638900654c36', 'number': '+1 (203) 894-6599', 'name': 'WTU Tenant'},
    {'id': '974ad56c-15b8-4c8f-8536-6a8df7fefc8c', 'number': '+1 (980) 277-7384', 'name': 'Tradeshow Agent'},
    {'id': '54b0973a-930b-45c4-ba4e-5b3cc789aac2', 'number': '+1 (572) 552-9606', 'name': 'PF AI Support'},
]


def create_jwt(payload):
    """Create a simple JWT token."""
    header = base64.urlsafe_b64encode(json.dumps({'alg': 'HS256', 'typ': 'JWT'}).encode()).decode().rstrip('=')
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    message = f"{header}.{payload_b64}"
    signature = hmac.new(JWT_SECRET.encode(), message.encode(), hashlib.sha256).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')
    return f"{header}.{payload_b64}.{signature_b64}"


def verify_jwt(token):
    """Verify JWT token and return payload."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature_b64 = parts
        message = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(JWT_SECRET.encode(), message.encode(), hashlib.sha256).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip('=')
        if signature_b64 != expected_sig_b64:
            return None
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        if payload.get('exp', 0) < time.time():
            return None
        return payload
    except:
        return None


def vapi_request(method, endpoint, params=None, use_cache=True):
    """Make request to VAPI API with caching."""
    # Create cache key from request params
    cache_key = f"{method}:{endpoint}:{json.dumps(params, sort_keys=True) if params else ''}"

    # Check cache for GET requests
    if method == 'GET' and use_cache:
        cached = get_cached(cache_key)
        if cached is not None:
            return cached

    url = f"{VAPI_BASE_URL}{endpoint}"
    headers = {
        'Authorization': f'Bearer {VAPI_API_KEY}',
        'Content-Type': 'application/json'
    }
    try:
        if method == 'GET':
            resp = requests.get(url, headers=headers, params=params, timeout=30)
        else:
            resp = requests.request(method, url, headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()

        # Cache GET results
        if method == 'GET':
            set_cached(cache_key, result)

        return result
    except Exception as e:
        print(f"VAPI API error: {e}")
        import traceback
        traceback.print_exc()
        return None


def process_call(call, include_transcript=False):
    """Process a VAPI call record."""
    # Handle both old and new VAPI API response formats
    cost_breakdown = call.get('costBreakdown') or {}
    analysis = call.get('analysis') or {}
    customer = call.get('customer') or {}

    # Get total cost - either from 'cost' field (float) or calculate from breakdown
    total_cost = call.get('cost', 0)
    if isinstance(total_cost, dict):
        # Old format where cost was a dict
        total_cost = sum([
            total_cost.get('llm', 0) or 0,
            total_cost.get('stt', 0) or 0,
            total_cost.get('tts', 0) or 0,
            total_cost.get('vapi', 0) or 0,
            total_cost.get('transport', 0) or 0
        ])

    # Calculate duration from startedAt/endedAt if not in costBreakdown
    duration = 0
    if call.get('startedAt') and call.get('endedAt'):
        from datetime import datetime
        try:
            started = datetime.fromisoformat(call['startedAt'].replace('Z', '+00:00'))
            ended = datetime.fromisoformat(call['endedAt'].replace('Z', '+00:00'))
            duration = (ended - started).total_seconds()
        except:
            pass

    processed = {
        'id': call.get('id'),
        'status': call.get('status'),
        'ended_reason': call.get('endedReason'),
        'duration_seconds': duration,
        'cost': round(total_cost, 4) if total_cost else 0,
        'customer_number': customer.get('number', ''),
        'success_evaluation': analysis.get('successEvaluation'),
        'summary': analysis.get('summary', '') or call.get('summary', ''),
        'created_at': call.get('createdAt'),
        'started_at': call.get('startedAt'),
        'ended_at': call.get('endedAt')
    }

    if include_transcript:
        processed['transcript'] = call.get('transcript', '')
        processed['messages'] = call.get('messages', [])
        processed['cost_breakdown'] = {
            'llm': cost_breakdown.get('llm', 0) or 0,
            'stt': cost_breakdown.get('stt', 0) or 0,
            'tts': cost_breakdown.get('tts', 0) or 0,
            'vapi': cost_breakdown.get('vapi', 0) or 0,
            'transport': cost_breakdown.get('transport', 0) or 0
        }

    return processed


class RequestHandler(BaseHTTPRequestHandler):
    def send_json(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.end_headers()

    def get_user_from_token(self):
        auth = self.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return None
        return verify_jwt(auth[7:])

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        # Auth verify
        if path == '/auth/verify':
            user = self.get_user_from_token()
            if user:
                self.send_json(200, {'valid': True, 'user': user})
            else:
                self.send_json(401, {'error': 'Invalid token'})
            return

        # Protected routes
        user = self.get_user_from_token()
        if not user:
            self.send_json(401, {'error': 'Unauthorized'})
            return

        tenant = TENANTS.get(user.get('tenant_id'))
        if not tenant:
            self.send_json(400, {'error': 'Tenant not found'})
            return

        # Allow phoneNumberId override from query params (for admin users)
        phone_number_id = params.get('phoneNumberId') or tenant.get('vapi_phone_number_id')

        # Get phone numbers list
        if path == '/api/phone-numbers':
            self.send_json(200, {'phoneNumbers': PHONE_NUMBERS})
            return

        # Get calls
        if path == '/api/calls':
            limit = params.get('limit', '100')
            vapi_params = {'phoneNumberId': phone_number_id, 'limit': limit}
            if params.get('start_date'):
                vapi_params['createdAtGe'] = params['start_date']
            if params.get('end_date'):
                vapi_params['createdAtLe'] = params['end_date']

            calls = vapi_request('GET', '/call', vapi_params)
            if calls is None:
                self.send_json(500, {'error': 'Failed to fetch calls'})
                return

            processed = [process_call(c) for c in calls]
            self.send_json(200, {
                'calls': processed,
                'count': len(processed),
                'tenant': {'id': tenant['tenant_id'], 'name': tenant['name']}
            })
            return

        # Get single call
        if path.startswith('/api/call/'):
            call_id = path.split('/api/call/')[-1]
            call = vapi_request('GET', f'/call/{call_id}')
            if call is None:
                self.send_json(404, {'error': 'Call not found'})
                return
            self.send_json(200, {'call': process_call(call, include_transcript=True)})
            return

        # Get stats
        if path == '/api/stats':
            days = min(int(params.get('days', '14')), 14)  # VAPI limits to 14 days
            from datetime import datetime, timedelta
            start_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%dT00:00:00Z')

            calls = vapi_request('GET', '/call', {
                'phoneNumberId': phone_number_id,
                'limit': '100',
                'createdAtGe': start_date
            })

            if calls is None:
                self.send_json(500, {'error': 'Failed to fetch calls'})
                return

            total_calls = len(calls)
            successful = failed = 0
            total_duration = total_cost = 0
            end_reasons = {}
            daily_counts = {}

            for call in calls:
                analysis = call.get('analysis') or {}
                success = analysis.get('successEvaluation')
                if success == 'true' or success == True:
                    successful += 1
                elif success == 'false' or success == False:
                    failed += 1

                # Handle new format: cost is float, costBreakdown is dict
                cost = call.get('cost', 0)
                if isinstance(cost, (int, float)):
                    total_cost += cost
                else:
                    # Old format
                    total_cost += sum([
                        cost.get('llm', 0) or 0,
                        cost.get('stt', 0) or 0,
                        cost.get('tts', 0) or 0,
                        cost.get('vapi', 0) or 0,
                        cost.get('transport', 0) or 0
                    ])

                # Calculate duration from timestamps
                if call.get('startedAt') and call.get('endedAt'):
                    try:
                        started = datetime.fromisoformat(call['startedAt'].replace('Z', '+00:00'))
                        ended = datetime.fromisoformat(call['endedAt'].replace('Z', '+00:00'))
                        total_duration += (ended - started).total_seconds()
                    except:
                        pass

                end_reason = call.get('endedReason', 'unknown')
                end_reasons[end_reason] = end_reasons.get(end_reason, 0) + 1

                created_at = call.get('createdAt', '')
                if created_at:
                    date_key = created_at[:10]
                    daily_counts[date_key] = daily_counts.get(date_key, 0) + 1

            self.send_json(200, {
                'stats': {
                    'total_calls': total_calls,
                    'successful_calls': successful,
                    'failed_calls': failed,
                    'success_rate': round((successful / total_calls * 100) if total_calls else 0, 1),
                    'total_duration_seconds': round(total_duration, 1),
                    'avg_duration_seconds': round(total_duration / total_calls if total_calls else 0, 1),
                    'total_cost': round(total_cost, 4),
                    'avg_cost_per_call': round(total_cost / total_calls if total_calls else 0, 4),
                    'end_reasons': end_reasons,
                    'daily_counts': daily_counts
                },
                'tenant': {'id': tenant['tenant_id'], 'name': tenant['name']}
            })
            return

        # Get costs
        if path == '/api/costs':
            days = min(int(params.get('days', '14')), 14)  # VAPI limits to 14 days
            from datetime import datetime, timedelta
            start_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%dT00:00:00Z')

            calls = vapi_request('GET', '/call', {
                'phoneNumberId': phone_number_id,
                'limit': '100',
                'createdAtGe': start_date
            })

            if calls is None:
                self.send_json(500, {'error': 'Failed to fetch calls'})
                return

            total_llm = total_stt = total_tts = total_vapi = total_transport = 0
            daily_costs = {}

            for call in calls:
                # Use costBreakdown for detailed breakdown (new format)
                cost_breakdown = call.get('costBreakdown') or {}
                llm = cost_breakdown.get('llm', 0) or 0
                stt = cost_breakdown.get('stt', 0) or 0
                tts = cost_breakdown.get('tts', 0) or 0
                vapi = cost_breakdown.get('vapi', 0) or 0
                transport = cost_breakdown.get('transport', 0) or 0

                total_llm += llm
                total_stt += stt
                total_tts += tts
                total_vapi += vapi
                total_transport += transport

                # Use total cost from 'cost' field for daily costs
                call_cost = call.get('cost', 0)
                if isinstance(call_cost, (int, float)):
                    daily_cost = call_cost
                else:
                    daily_cost = llm + stt + tts + vapi + transport

                created_at = call.get('createdAt', '')
                if created_at:
                    date_key = created_at[:10]
                    if date_key not in daily_costs:
                        daily_costs[date_key] = 0
                    daily_costs[date_key] += daily_cost

            total_cost = total_llm + total_stt + total_tts + total_vapi + total_transport

            self.send_json(200, {
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
                'tenant': {'id': tenant['tenant_id'], 'name': tenant['name']}
            })
            return

        # Get reports
        if path == '/api/reports':
            from datetime import datetime, timedelta
            import sys
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from reports.handler import fetch_vapi_calls, analyze_call, calculate_metrics, generate_markdown_report

            date_param = params.get('date')

            if date_param:
                # Get specific report for a date
                try:
                    target_date = datetime.strptime(date_param, '%Y-%m-%d')
                    start_date = target_date.strftime('%Y-%m-%dT00:00:00Z')
                    end_date = target_date.strftime('%Y-%m-%dT23:59:59Z')

                    calls = fetch_vapi_calls(phone_number_id, start_date, end_date)

                    if not calls:
                        self.send_json(200, {
                            'report': {
                                'date': date_param,
                                'generated_at': datetime.utcnow().isoformat(),
                                'total_calls': 0,
                                'markdown': f"# Report for {date_param}\n\nNo calls found for this date.",
                                'metrics': {}
                            }
                        })
                        return

                    analyzed_calls = [analyze_call(c) for c in calls]
                    metrics = calculate_metrics(analyzed_calls)
                    markdown = generate_markdown_report(
                        tenant['name'], tenant['tenant_id'], target_date, analyzed_calls, metrics
                    )

                    self.send_json(200, {
                        'report': {
                            'date': date_param,
                            'generated_at': datetime.utcnow().isoformat(),
                            'total_calls': len(calls),
                            'markdown': markdown,
                            'metrics': metrics
                        }
                    })
                except Exception as e:
                    print(f"Error generating report: {e}")
                    import traceback
                    traceback.print_exc()
                    self.send_json(500, {'error': str(e)})
                return

            else:
                # List available reports - fetch all calls in one request and group by date
                start_date = (datetime.utcnow() - timedelta(days=14)).strftime('%Y-%m-%dT00:00:00Z')

                all_calls = vapi_request('GET', '/call', {
                    'phoneNumberId': phone_number_id,
                    'limit': '100',
                    'createdAtGe': start_date
                }) or []

                # Group calls by date
                calls_by_date = {}
                for call in all_calls:
                    created_at = call.get('createdAt', '')
                    if created_at:
                        date_key = created_at[:10]  # YYYY-MM-DD
                        if date_key not in calls_by_date:
                            calls_by_date[date_key] = []
                        calls_by_date[date_key].append(call)

                # Build reports list
                reports_list = []
                for date_key in sorted(calls_by_date.keys(), reverse=True):
                    day_calls = calls_by_date[date_key]
                    total_cost = 0
                    successful = 0

                    for call in day_calls:
                        cost = call.get('cost', 0)
                        if isinstance(cost, (int, float)):
                            total_cost += cost
                        analysis = call.get('analysis') or {}
                        if analysis.get('successEvaluation') in ['true', True]:
                            successful += 1

                    reports_list.append({
                        'date': date_key,
                        'total_calls': len(day_calls),
                        'generated_at': datetime.utcnow().isoformat(),
                        'metrics': {
                            'total_cost': round(total_cost, 2),
                            'success_rate': round(successful / len(day_calls) * 100 if day_calls else 0, 1)
                        }
                    })

                self.send_json(200, {'reports': reports_list})
                return

        self.send_json(404, {'error': 'Not found'})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(content_length)) if content_length else {}

        # Login
        if path == '/auth/login':
            username = body.get('username', '')
            password = body.get('password', '')

            user = USERS.get(username)
            if not user:
                self.send_json(401, {'error': 'Invalid credentials'})
                return

            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if password_hash != user['password_hash']:
                self.send_json(401, {'error': 'Invalid credentials'})
                return

            # Create JWT
            token = create_jwt({
                'username': user['username'],
                'tenant_id': user['tenant_id'],
                'role': user['role'],
                'name': user['name'],
                'exp': time.time() + 86400  # 24 hours
            })

            self.send_json(200, {
                'token': token,
                'user': {
                    'username': user['username'],
                    'name': user['name'],
                    'role': user['role'],
                    'tenant_id': user['tenant_id']
                }
            })
            return

        # Logout
        if path == '/auth/logout':
            self.send_json(200, {'message': 'Logged out'})
            return

        self.send_json(404, {'error': 'Not found'})

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")


if __name__ == '__main__':
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║         VAPI Dashboard - Local Development Server         ║
╠═══════════════════════════════════════════════════════════╣
║  Server:  http://localhost:{PORT}                            ║
║  Login:   admin / admin123                                ║
║  Tenant:  WTU (Window Treatment Universe)                 ║
╚═══════════════════════════════════════════════════════════╝
""")
    server = HTTPServer(('localhost', PORT), RequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
