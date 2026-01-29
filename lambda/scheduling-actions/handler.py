"""
Scheduling Actions Lambda Handler
Handles 8 scheduling-related actions for Bedrock Agent

Actions:
1. list_projects - Show available projects for customer
2. get_available_dates - Get available dates for scheduling
3. get_time_slots - Get available time slots for a date
4. confirm_appointment - Confirm/schedule an appointment
5. reschedule_appointment - Reschedule an existing appointment
6. cancel_appointment - Cancel an appointment
7. add_note - Add a note to a project
8. list_notes - List all notes for a project

Supports both MOCK and REAL API modes via USE_MOCK_API environment variable
"""

import json
import logging
import re
import requests
import boto3
import calendar
from datetime import datetime
from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError

# Import configuration and mock data
from config import (
    USE_MOCK_API,
    get_api_config,
    get_auth_headers,
    ENABLE_REAL_CONFIRM,
    ENABLE_REAL_CANCEL,
    DYNAMODB_NOTES_TABLE
)
from mock_data import (
    get_mock_projects,
    get_mock_available_dates,
    get_mock_time_slots,
    get_mock_confirm_appointment,
    get_mock_cancel_appointment,
    get_mock_rescheduler_slots,
    get_mock_business_hours
)

# DSPy LLM-based date interpreter (optional - falls back to regex if unavailable)
import os
USE_LLM_DATE_INTERPRETER = os.environ.get('USE_LLM_DATE_INTERPRETER', 'false').lower() == 'true'
LLM_DATE_AVAILABLE = False
try:
    from dspy_date_interpreter import interpret_date, convert_to_legacy_format
    LLM_DATE_AVAILABLE = True
    print(f"[DATE-LLM] Module loaded successfully, USE_LLM_DATE_INTERPRETER={USE_LLM_DATE_INTERPRETER}")
except Exception as e:
    print(f"[DATE-LLM] Failed to load module: {type(e).__name__}: {e}")

# Voice session cache for preloaded projects (optional)
VOICE_CACHE_AVAILABLE = False
VOICE_CACHE_TABLE = os.environ.get('VOICE_CREDENTIALS_TABLE', f'pf-syn-phone-credentials-{os.environ.get("ENVIRONMENT", "dev")}')
try:
    import boto3
    _dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
    VOICE_CACHE_AVAILABLE = True
    print(f"[VOICE-CACHE] DynamoDB available, table: {VOICE_CACHE_TABLE}")
except Exception as e:
    print(f"[VOICE-CACHE] DynamoDB not available: {type(e).__name__}: {e}")

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def extract_date_range(date_str: str) -> Optional[Dict[str, str]]:
    """
    Extract start and end dates from a date range expression.

    Handles patterns like:
    - "between 09th Jan to 18th Jan"
    - "between Jan 9 and Jan 18"
    - "from 9th to 18th January"
    - "dates from Jan 9 to Jan 18"
    - "9th Jan to 18th Jan"

    Returns:
        Dict with 'start_date' and 'end_date' in YYYY-MM-DD format, or None
    """
    import re

    if not date_str:
        return None

    date_lower = date_str.lower().strip()
    today = datetime.now()

    # Month mapping
    months = {
        'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
        'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6,
        'jul': 7, 'july': 7, 'aug': 8, 'august': 8, 'sep': 9, 'september': 9,
        'oct': 10, 'october': 10, 'nov': 11, 'november': 11, 'dec': 12, 'december': 12
    }

    # Pattern: "between X and/to Y" or "from X to Y" or "X to Y"
    # Use explicit date patterns instead of lazy .+? which fails to capture properly
    # Date patterns: "14th Jan", "Jan 14", "14 Jan", etc.
    date_part = r'(\d{1,2}(?:st|nd|rd|th)?\s+\w+|\w+\s+\d{1,2}(?:st|nd|rd|th)?)'
    range_patterns = [
        rf'between\s+{date_part}\s+(?:and|to)\s+{date_part}',  # between 14th Jan and/to 18th Jan
        rf'from\s+{date_part}\s+to\s+{date_part}',              # from 14th Jan to 18th Jan
        rf'{date_part}\s+to\s+{date_part}',                     # 14th Jan to 18th Jan
    ]

    def parse_single_date(date_expr: str) -> Optional[str]:
        """Parse a single date expression like '9th Jan' or 'Jan 18' to YYYY-MM-DD"""
        date_expr = date_expr.strip().lower()

        # Try to find day and month
        day_match = re.search(r'(\d{1,2})(?:st|nd|rd|th)?', date_expr)
        if not day_match:
            return None

        day = int(day_match.group(1))
        day = max(1, min(day, 31))

        # Find month
        month_num = None
        for month_name, num in months.items():
            if month_name in date_expr:
                month_num = num
                break

        if not month_num:
            return None

        # Determine year (if month is in the past, use next year)
        year = today.year if month_num >= today.month else today.year + 1

        return f"{year}-{month_num:02d}-{day:02d}"

    for pattern in range_patterns:
        match = re.search(pattern, date_lower)
        if match:
            start_expr = match.group(1)
            end_expr = match.group(2)

            start_date = parse_single_date(start_expr)
            end_date = parse_single_date(end_expr)

            if start_date and end_date:
                logger.info(f"[DATE RANGE] Extracted range: '{date_str}' -> start={start_date}, end={end_date}")
                return {
                    'start_date': start_date,
                    'end_date': end_date
                }

    return None


def convert_natural_date(date_str: str, return_strategy: bool = False) -> Optional[str]:
    """
    Convert natural language date to YYYY-MM-DD format.

    Handles:
    - Already formatted dates (YYYY-MM-DD) - passthrough
    - "next month" - first day of next month
    - "next week" - next Monday
    - Month names ("january", "feb") - first day of that month

    Args:
        date_str: Natural language date string
        return_strategy: If True, returns tuple (date, strategy, days_to_fetch)
                        strategy: 'specific_day', 'week', or 'month'
                        days_to_fetch: 1 for specific day, 7 for week, 30 for month

    Returns:
        If return_strategy=False: date string or None
        If return_strategy=True: tuple (date, strategy, days_to_fetch) or (None, None, None)
    """
    import re
    from datetime import timedelta

    if not date_str:
        return (None, None, None) if return_strategy else None

    today = datetime.now()
    date_lower = date_str.lower().strip()
    strategy = 'month'  # Default strategy
    days_to_fetch = 10  # Default: 10 days for better availability

    # Already in YYYY-MM-DD format? Pass through - treat as specific day
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        if return_strategy:
            return (date_str, 'specific_day', 1)
        return date_str

    # YYYY-MM format (e.g., "2026-01") - if current month, start from tomorrow
    yyyy_mm_match = re.match(r'^(\d{4})-(\d{2})$', date_str)
    if yyyy_mm_match:
        year = int(yyyy_mm_match.group(1))
        month = int(yyyy_mm_match.group(2))
        if year == today.year and month == today.month:
            # Current month - start from tomorrow
            from datetime import timedelta
            tomorrow = today + timedelta(days=1)
            result = tomorrow.strftime("%Y-%m-%d")
            logger.info(f"[DATE] Converted '{date_str}' (YYYY-MM, current month) -> {result} (tomorrow)")
        else:
            result = f"{year}-{month:02d}-01"
            logger.info(f"[DATE] Converted '{date_str}' (YYYY-MM) -> {result}")
        if return_strategy:
            return (result, 'week', 10)  # Month format = 10 days
        return result

    # "this month" - first day of current month (or tomorrow if we're at start of month)
    if 'this month' in date_lower:
        # Use tomorrow as start to avoid showing past dates
        from datetime import timedelta
        tomorrow = today + timedelta(days=1)
        result = tomorrow.strftime("%Y-%m-%d")
        logger.info(f"[DATE] Converted 'this month' -> {result} (tomorrow)")
        if return_strategy:
            return (result, 'week', 10)  # "this month" = show 10 days
        return result

    # "next month" - first day of next month
    if 'next month' in date_lower:
        if today.month == 12:
            result = f"{today.year + 1}-01-01"
        else:
            result = f"{today.year}-{today.month + 1:02d}-01"
        logger.info(f"[DATE] Converted 'next month' -> {result}")
        if return_strategy:
            return (result, 'week', 10)  # "next month" = show 10 days
        return result

    # "next week" - next Monday
    if 'next week' in date_lower:
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7  # If today is Monday, go to next Monday
        next_monday = today + timedelta(days=days_until_monday)
        result = next_monday.strftime("%Y-%m-%d")
        logger.info(f"[DATE] Converted 'next week' -> {result}")
        if return_strategy:
            return (result, 'week', 7)  # "next week" = show 7 days (full week)
        return result

    # "last week of [month]" - dynamically calculate based on days in month
    last_week_match = re.search(r'last week of (\w+)', date_lower)
    if last_week_match:
        month_name = last_week_match.group(1)[:3].lower()
        months_map = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                      'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
        if month_name in months_map:
            month_num = months_map[month_name]
            year = today.year if month_num >= today.month else today.year + 1
            # Dynamic calculation: last 7 days of month
            days_in_month = calendar.monthrange(year, month_num)[1]
            start_day = days_in_month - 6  # Last 7 days
            result = f"{year}-{month_num:02d}-{start_day:02d}"
            logger.info(f"[DATE] Converted 'last week of {month_name}' -> {result} (month has {days_in_month} days)")
            if return_strategy:
                return (result, 'week', 7)  # Last week = 7 days
            return result

    # Ordinal week of month: "1st week of/for", "2nd week of/for", "3rd week of/for", etc.
    # Also handles "3rd week feb" without of/for
    # Uses actual calendar weeks (Monday-based, first FULL week = week 1)
    ordinal_week_match = re.search(r'(1st|2nd|3rd|4th|5th|first|second|third|fourth|fifth)\s+week\s+(?:of|for)?\s*(\w+)', date_lower)
    if ordinal_week_match:
        week_ord = ordinal_week_match.group(1).lower()
        month_name = ordinal_week_match.group(2)[:3].lower()
        months_map = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                      'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
        week_num_map = {'1st': 1, 'first': 1, '2nd': 2, 'second': 2, '3rd': 3, 'third': 3,
                        '4th': 4, 'fourth': 4, '5th': 5, 'fifth': 5}
        if month_name in months_map and week_ord in week_num_map:
            month_num = months_map[month_name]
            week_num = week_num_map[week_ord]
            year = today.year if month_num >= today.month else today.year + 1

            # Calculate actual calendar week (Monday-based)
            # Week 1 = first FULL week starting on Monday
            first_day = datetime(year, month_num, 1)
            first_weekday = first_day.weekday()  # 0=Monday, 6=Sunday

            # Find the first Monday of the month
            if first_weekday == 0:  # Month starts on Monday
                first_monday = 1
            else:
                # Days until next Monday
                first_monday = 8 - first_weekday

            # Calculate start of requested week
            # Week 1 = partial week if month doesn't start on Monday (calendar weeks)
            # Week 2+ = subsequent Monday-Sunday weeks
            # Example: Jan 2026 starts Thu, so Week 1 = Jan 1-4, Week 2 = Jan 5-11, Week 3 = Jan 12-18
            if week_num == 1:
                start_day = 1  # Week 1 always starts on day 1
            else:
                # Week 2+ starts from first Monday, then subsequent Mondays
                start_day = first_monday + (week_num - 2) * 7

            # Clamp to valid days in month
            days_in_month = calendar.monthrange(year, month_num)[1]
            start_day = min(start_day, days_in_month)

            result = f"{year}-{month_num:02d}-{start_day:02d}"
            result_date = datetime.strptime(result, "%Y-%m-%d")

            # Calculate the week's end date (Saturday = 6 days after Monday start)
            # For week 1 (partial), end on the first Saturday
            if week_num == 1:
                # Week 1 ends on the first Saturday (or last day before first Monday)
                week_end_day = first_monday - 1 if first_monday > 1 else min(6, days_in_month)
            else:
                # Full week ends 6 days after start (Saturday)
                week_end_day = min(start_day + 5, days_in_month)  # Mon + 5 = Sat
            week_end_date = datetime(year, month_num, week_end_day)

            # If calculated start date is in the past, use tomorrow instead
            tomorrow = today + timedelta(days=1)
            if result_date.date() < tomorrow.date():
                # Calculate remaining days in the week from tomorrow
                days_remaining = (week_end_date.date() - tomorrow.date()).days + 1

                # If entire week is in the past, return None (no dates available for this week)
                if days_remaining <= 0:
                    logger.info(f"[DATE] '{week_ord} week of {month_name}' is entirely in the past (week ended {week_end_day}, today is {today.day})")
                    if return_strategy:
                        return (None, 'week_past', 0)
                    return None

                result = tomorrow.strftime("%Y-%m-%d")
                logger.info(f"[DATE] Converted '{week_ord} week of {month_name}' -> {result} (adjusted to tomorrow, {days_remaining} days left in week ending {week_end_day})")
                if return_strategy:
                    return (result, 'week', days_remaining, week_end_date.strftime("%Y-%m-%d"))
                return result
            else:
                logger.info(f"[DATE] Converted '{week_ord} week of {month_name}' -> {result} (week {week_num}, first_monday={first_monday}, ends {week_end_day})")
            if return_strategy:
                # Calculate actual days in this week
                days_in_week = week_end_day - start_day + 1
                return (result, 'week', days_in_week, week_end_date.strftime("%Y-%m-%d"))
            return result

    # "end of [month]" - dynamically calculate last 5 days of month
    end_of_match = re.search(r'end of (\w+)', date_lower)
    if end_of_match:
        month_name = end_of_match.group(1)[:3].lower()
        months_map = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                      'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
        if month_name in months_map:
            month_num = months_map[month_name]
            year = today.year if month_num >= today.month else today.year + 1
            # Dynamic calculation: last 7 days of month
            days_in_month = calendar.monthrange(year, month_num)[1]
            start_day = days_in_month - 6  # Last 7 days
            result = f"{year}-{month_num:02d}-{start_day:02d}"
            logger.info(f"[DATE] Converted 'end of {month_name}' -> {result} (month has {days_in_month} days)")
            if return_strategy:
                return (result, 'week', 7)  # End of month = 7 days
            return result

    # Month names: "january", "feb", etc. with optional day number
    # Examples: "Jan 10", "10th Jan", "January 15", "feb 20th"
    months = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    for name, num in months.items():
        if name in date_lower:
            # Try to extract day number from string like "Jan 10", "10th Jan", "january 15"
            day_match = re.search(r'(\d{1,2})(?:st|nd|rd|th)?', date_lower)

            # Determine strategy: specific day vs month request
            if day_match:
                # User specified a day number (e.g., "Jan 10", "the 15th of March")
                day = int(day_match.group(1))
                day = max(1, min(day, 31))  # Clamp to valid range
                strategy = 'specific_day'
                days_to_fetch = 1
                # If month is in the past this year, use next year
                year = today.year if num >= today.month else today.year + 1
                result = f"{year}-{num:02d}-{day:02d}"
                logger.info(f"[DATE STRATEGY] Specific day request: {day_match.group()} -> 1 day only")
            else:
                # User only said month name (e.g., "January", "March")
                # If we're already in that month, start from tomorrow
                # If it's a future month, start from the first day of that month
                strategy = 'day'
                days_to_fetch = 10  # Default: 10 days for better availability
                if num == today.month:
                    # Same month - start from tomorrow
                    from datetime import timedelta
                    tomorrow = today + timedelta(days=1)
                    result = tomorrow.strftime("%Y-%m-%d")
                    logger.info(f"[DATE STRATEGY] Current month request: {name} -> tomorrow (1 day)")
                else:
                    # Future/past month - start from 1st of that month
                    year = today.year if num > today.month else today.year + 1
                    result = f"{year}-{num:02d}-01"
                    logger.info(f"[DATE STRATEGY] Month request: {name} -> 1 day from 1st")

            logger.info(f"[DATE] Converted '{date_str}' -> {result}")
            if return_strategy:
                return (result, strategy, days_to_fetch)
            return result

    logger.warning(f"[DATE] Could not parse date preference: '{date_str}'")
    return (None, None, None) if return_strategy else None


# DynamoDB client for notes storage
dynamodb = boto3.resource('dynamodb')

# ============================================================================
# OPTIMIZATION: Connection Pooling (Module-level session for reuse)
# ============================================================================

# Initialize session with connection pooling OUTSIDE handler for reuse across warm invocations
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(
    pool_connections=10,
    pool_maxsize=10,
    max_retries=requests.adapters.Retry(
        total=2,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504]
    )
)
session.mount('http://', adapter)
session.mount('https://', adapter)

# ============================================================================
# Helper Functions
# ============================================================================

def safe_get(obj: Any, *keys, default=None) -> Any:
    """
    OPTIMIZATION: Safely navigate nested dictionaries - CRITICAL for performance
    Avoids try-except overhead in tight loops
    """
    result = obj
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
            if result is None:
                return default
        else:
            return default
    return result if result is not None else default

def extract_parameters(event: Dict) -> Dict[str, Any]:
    """
    Extract parameters from Bedrock Agent event
    Handles both actionGroup and requestBody formats
    Resolves session attribute references (e.g., "session.customer_id" -> actual value from sessionAttributes)
    """
    try:
        # Bedrock Agent passes parameters in different ways
        if 'parameters' in event and event['parameters']:
            params = {p['name']: p['value'] for p in event['parameters']}
        elif 'requestBody' in event:
            content = event['requestBody'].get('content', {})
            app_json = content.get('application/json', {})

            # Check if properties array format (from action groups)
            if isinstance(app_json, dict) and 'properties' in app_json:
                params = {p['name']: p['value'] for p in app_json['properties']}
            # Check if JSON string format
            elif isinstance(app_json, str):
                params = json.loads(app_json)
            # Already a dict
            else:
                params = app_json
        else:
            # Fallback: try to parse body
            body = event.get('body', '{}')
            if isinstance(body, str):
                params = json.loads(body)
            else:
                params = body

        # Resolve session attribute references
        # Handles: "$attr_name", "session.attr", "$session.attr", "{{session.attr}}", "${session.attr}"
        session_attrs = event.get('sessionAttributes', {})
        for key, value in params.items():
            if isinstance(value, str):
                # Handle $param_name format (e.g., $customer_id)
                if value.startswith('$') and not value.startswith('$session.'):
                    attr_name = value[1:]  # Remove the $ prefix
                    if attr_name in session_attrs:
                        params[key] = session_attrs[attr_name]
                        logger.info(f"Resolved ${attr_name} -> {params[key]}")
                # Handle session.attr format
                elif 'session.' in value:
                    # Remove template markers: $, {{, }}, ${, }
                    clean_value = value.strip('{}').strip('$').strip('{}')
                    if clean_value.startswith('session.'):
                        attr_name = clean_value.replace('session.', '')
                        if attr_name in session_attrs:
                            params[key] = session_attrs[attr_name]
                            logger.info(f"Resolved {value} -> {params[key]}")

        logger.info(f"Extracted parameters: {params}")
        return params

    except Exception as e:
        logger.error(f"Error extracting parameters: {str(e)}")
        return {}


def get_voice_cached_projects(phone_number: str) -> Optional[Dict]:
    """
    Get cached projects from voice session cache (DynamoDB).

    Used for voice channel optimization - projects preloaded at call start.

    Args:
        phone_number: Normalized phone number (E.164 format)

    Returns:
        Dict with 'projects' list and 'project_mapping' dict, or None if not cached
    """
    if not VOICE_CACHE_AVAILABLE or not phone_number:
        return None

    try:
        table = _dynamodb.Table(VOICE_CACHE_TABLE)
        response = table.get_item(Key={'phone_number': phone_number})

        if 'Item' not in response:
            logger.info(f"[VOICE-CACHE] No cache for ***{phone_number[-4:]}")
            return None

        item = response['Item']

        # Check if projects are cached
        projects_json = item.get('projects_cache')
        if not projects_json:
            logger.info(f"[VOICE-CACHE] No projects in cache for ***{phone_number[-4:]}")
            return None

        # Check TTL
        projects_ttl = item.get('projects_ttl', 0)
        if hasattr(projects_ttl, '__float__'):
            projects_ttl = float(projects_ttl)

        now = datetime.utcnow().timestamp()
        if projects_ttl and now > projects_ttl:
            logger.info(f"[VOICE-CACHE] Cache expired for ***{phone_number[-4:]}")
            return None

        # Parse cached data
        projects = json.loads(projects_json)
        mapping_json = item.get('project_mapping', '{}')
        project_mapping = json.loads(mapping_json)

        logger.info(f"[VOICE-CACHE] Cache hit for ***{phone_number[-4:]}: {len(projects)} projects")

        return {
            'projects': projects,
            'project_mapping': project_mapping
        }

    except Exception as e:
        logger.warning(f"[VOICE-CACHE] Failed to get cache: {e}")
        return None


def make_api_request_with_retry(
    method: str,
    url: str,
    headers: Dict[str, str],
    client_id: str = None,
    user_id: str = None,
    environment: str = 'dev',
    **kwargs
) -> requests.Response:
    """
    Make API request with connection pooling.
    Uses module-level session object for TCP connection reuse (100-300ms savings)

    Args:
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        headers: Request headers (including Authorization)
        client_id: ProjectForce client ID (for logging)
        user_id: ProjectForce user/customer ID (for logging)
        environment: Environment (dev/staging/prod)
        **kwargs: Additional arguments for requests (json, timeout, etc.)

    Returns:
        Response object

    Raises:
        requests.HTTPError: If request fails
    """
    # OPTIMIZATION: Add compression header if not present
    if 'Accept-Encoding' not in headers:
        headers['Accept-Encoding'] = 'gzip, deflate'

    # Use session for connection reuse
    response = session.request(method, url, headers=headers, **kwargs)
    response.raise_for_status()
    return response

def format_success_response(event: Dict, action: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """OPTIMIZED: Format successful response for Bedrock Agent - supports both OpenAPI and Function formats"""
    # Check if this is function calling format (new format)
    if 'function' in event:
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': event.get('actionGroup', 'scheduling'),
                'function': event.get('function', action),
                'functionResponse': {
                    'responseBody': {
                        'TEXT': {
                            # OPTIMIZATION: Use compact JSON (20% smaller payload)
                            'body': json.dumps(result, separators=(',', ':'))
                        }
                    }
                }
            }
        }

    # Fall back to OpenAPI format (old format)
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event.get('actionGroup', 'scheduling'),
            'apiPath': event.get('apiPath', f'/{action}'),
            'httpMethod': event.get('httpMethod', 'POST'),
            'httpStatusCode': 200,
            'responseBody': {
                'application/json': {
                    # OPTIMIZATION: Use compact JSON (20% smaller payload)
                    'body': json.dumps(result, separators=(',', ':'))
                }
            }
        }
    }

def format_error_response(event: Dict, action: str, error_message: str, status_code: int = 500) -> Dict[str, Any]:
    """Format error response for Bedrock Agent - supports both OpenAPI and Function formats"""
    error_body = {'error': error_message, 'action': action, 'pf_http_status_code': status_code}

    # Check if this is function calling format (new format)
    if 'function' in event:
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': event.get('actionGroup', 'scheduling'),
                'function': event.get('function', action),
                'functionResponse': {
                    'responseBody': {
                        'TEXT': {
                            'body': json.dumps(error_body)
                        }
                    }
                }
            }
        }

    # Fall back to OpenAPI format (old format)
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event.get('actionGroup', 'scheduling'),
            'apiPath': event.get('apiPath', f'/{action}'),
            'httpMethod': event.get('httpMethod', 'POST'),
            'httpStatusCode': status_code,
            'responseBody': {
                'application/json': {
                    'body': json.dumps(error_body)
                }
            }
        }
    }

# ============================================================================
# Action Handlers
# ============================================================================

def resolve_project_id(project_ref: str, projects: List[Dict]) -> Optional[str]:
    """
    Resolve a project reference (Order Number or internal ID) to the internal project ID.

    This is format-agnostic - works with:
    - Internal IDs: "90000079"
    - Order Numbers: "AI-PRO-1000010"
    - Any alphanumeric format

    Args:
        project_ref: The project reference to resolve (could be Order Number or internal ID)
        projects: List of raw project data from the API

    Returns:
        The internal project ID if found, None otherwise
    """
    if not project_ref or not projects:
        return None

    project_ref_lower = str(project_ref).lower()

    for item in projects:
        item_project_id = str(safe_get(item, "project_project_id", default=""))
        item_project_number = str(safe_get(item, "project_project_number", default=""))

        # Match by internal ID (exact) or Order Number (case-insensitive)
        if item_project_id == str(project_ref) or item_project_number.lower() == project_ref_lower:
            logger.info(f"Resolved project reference '{project_ref}' to internal ID '{item_project_id}'")
            return item_project_id

    return None


def extract_project_minimal(item: Dict) -> Dict[str, Any]:
    """
    OPTIMIZATION: Extract comprehensive project data with conditional fields
    Extracts 15+ fields (vs previous 9) while keeping payload minimal
    """
    # Core fields (always present)
    # Try multiple field names for project type (API may use different names per client)
    project_type = (
        safe_get(item, "project_type_project_type", default="") or
        safe_get(item, "project_type", default="") or
        safe_get(item, "projectType", default="") or
        safe_get(item, "work_type", default="") or
        safe_get(item, "workType", default="")
    )
    project = {
        "id": str(safe_get(item, "project_project_id", default="")),
        "projectNumber": safe_get(item, "project_project_number", default=""),
        "status": safe_get(item, "status_info_status", default=""),
        "category": safe_get(item, "project_category_category", default=""),
        "projectType": project_type,
    }

    # Conditional fields - only add if present
    # Use pre-formatted dates from API (already formatted!)
    scheduled_date = safe_get(item, "convertedProjectStartScheduledDate")
    if scheduled_date:
        project["scheduledDate"] = scheduled_date
        project["scheduledEndDate"] = safe_get(item, "convertedProjectEndScheduledDate", default="")

    # Installer info - only if assigned
    installer_name = safe_get(item, "user_idata_first_name")
    if installer_name:
        installer_last = safe_get(item, "user_idata_last_name", default="")
        project["installer"] = {
            "name": f"{installer_name} {installer_last}".strip(),
            "id": str(safe_get(item, "installer_details_installer_id", default=""))
        }

    # Address - compact format, remove empty values
    address = {
        "address1": safe_get(item, "installation_address_address1", default=""),
        "city": safe_get(item, "installation_address_city", default=""),
        "state": safe_get(item, "installation_address_state", default=""),
        "zipcode": safe_get(item, "installation_address_zipcode", default="")
    }
    project["address"] = {k: v for k, v in address.items() if v}

    # Store, source, date
    project["store"] = {
        "storeName": safe_get(item, "store_info_store_name", default=""),
        "storeNumber": safe_get(item, "store_info_store_number", default="")
    }
    project["sourceSystem"] = safe_get(item, "source_system_source_name", default="")

    date_sold = safe_get(item, "project_date_sold")
    if date_sold:
        # Format date as MM/DD/YYYY for UI display
        raw_date = date_sold.split("T")[0] if "T" in date_sold else date_sold
        try:
            from datetime import datetime
            date_obj = datetime.strptime(raw_date, "%Y-%m-%d")
            project["dateSold"] = date_obj.strftime("%m/%d/%Y")  # 01/30/2025
        except:
            project["dateSold"] = raw_date  # Keep original if parsing fails

    project["hasDocuments"] = bool(safe_get(item, "projectDocument"))

    return project

def format_projects_for_agent(projects: list, customer_id: str = "", pf_http_status_code: int = 200) -> Dict[str, Any]:
    """
    OPTIMIZATION: Pre-format exactly as agent instructions expect
    Agent receives this ready for UI - NO additional formatting needed
    """
    project_count = len(projects)

    if project_count == 0:
        return {
            "message": "No projects found for this customer.",
            "projects": [],
            "pf_http_status_code": pf_http_status_code
        }

    # Get address from first project for message
    first_address = ""
    if projects and "address" in projects[0]:
        addr = projects[0]["address"]
        city = addr.get("city", "")
        if city:
            first_address = f" at {addr.get('address1', '')}, {city}"

    # Get category and type from first project
    category = projects[0].get("category", "") if projects else ""
    project_type = projects[0].get("projectType", "") if projects else ""

    return {
        "message": f"You have {project_count} {category} {project_type} project{'s' if project_count != 1 else ''}{first_address}:",
        "projects": projects,
        "pf_http_status_code": pf_http_status_code
    }

def handle_list_projects(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    OPTIMIZED Action: list_projects

    KEY OPTIMIZATIONS:
    1. Processes large API response in Lambda (not agent)
    2. Extracts 15+ fields efficiently (vs previous 9)
    3. Pre-formats for UI consumption (agent does zero formatting)
    4. Uses connection pooling + compression
    5. Supports filtering by status, category, and projectType
    6. VOICE: Uses preloaded cache for instant response (no API call)

    Before: ~2000 lines to agent  agent formats  ~200 lines to UI
    After: ~200 lines to agent (already formatted)  pass-through to UI
    """
    customer_id = params.get('customer_id')
    client_id = params.get('client_id', 'default')

    # Extract filter parameters
    filter_status = params.get('status')
    filter_category = params.get('category')
    filter_project_type = params.get('projectType')
    filter_scheduled_month = params.get('scheduled_month')  # e.g., "January", "February"
    filter_scheduled_date = params.get('scheduled_date')  # e.g., "2026-01-13" (exact date)

    if not customer_id:
        raise ValueError("Missing required parameter: customer_id")

    # Start timing for monitoring
    import time
    start_time = time.time()

    # VOICE OPTIMIZATION: Check preloaded cache first (instant response)
    # Use cache for ALL voice requests, apply filters locally
    from_phone = params.get('_from_phone', '')
    if from_phone:
        # Normalize phone number to match cache key format (digits only, no country code)
        normalized_phone = ''.join(c for c in from_phone if c.isdigit())
        if len(normalized_phone) == 11 and normalized_phone.startswith('1'):
            normalized_phone = normalized_phone[1:]  # Remove US country code
        logger.info(f"[VOICE-CACHE] Looking up cache for normalized phone: ***{normalized_phone[-4:]}")

        # Voice channel - try cache first
        cached = get_voice_cached_projects(normalized_phone)
        if cached:
            projects = cached.get('projects', [])
            original_count = len(projects)

            # Apply filters locally to cached projects (same logic as API path)
            if filter_status or filter_category or filter_project_type or filter_scheduled_month or filter_scheduled_date:
                filtered_projects = []
                for project in projects:
                    include = True

                    if filter_status:
                        project_status = project.get('status', '').lower()
                        filter_status_lower = filter_status.lower()
                        # Handle 'schedulable' status (New + Ready To Schedule)
                        if filter_status_lower == 'schedulable':
                            if project_status not in ['new', 'ready to schedule']:
                                include = False
                        elif filter_status_lower not in project_status:
                            include = False

                    if include and filter_category:
                        project_category = project.get('category', '').lower()
                        if filter_category.lower() not in project_category:
                            include = False

                    if include and filter_project_type:
                        project_type = project.get('projectType', '').lower()
                        if filter_project_type.lower() not in project_type:
                            include = False

                    if include and filter_scheduled_month:
                        scheduled_date = project.get('scheduledDate', '')
                        if not scheduled_date or filter_scheduled_month not in scheduled_date:
                            include = False

                    if include and filter_scheduled_date:
                        scheduled_date = project.get('scheduledDate', '')
                        if not scheduled_date:
                            include = False
                        else:
                            # Match date using same logic as API path (handles multiple formats)
                            try:
                                from datetime import datetime
                                filter_date = datetime.strptime(filter_scheduled_date, "%Y-%m-%d")
                                filter_day = filter_date.day
                                filter_month = filter_date.month
                                filter_year = filter_date.year
                                date_matched = False
                                # Format 1: "Jan 13, 2026 1:00 PM"
                                match = re.search(r'(\w{3})\s+(\d{1,2}),?\s+(\d{4})', scheduled_date)
                                if match:
                                    month_abbr = match.group(1).lower()
                                    day = int(match.group(2))
                                    year = int(match.group(3))
                                    month_map = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                                                 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
                                    if month_map.get(month_abbr) == filter_month and day == filter_day and year == filter_year:
                                        date_matched = True
                                # Format 2: ISO "2026-01-13" or "2026-01-13T..."
                                if not date_matched and filter_scheduled_date in scheduled_date:
                                    date_matched = True
                                if not date_matched:
                                    include = False
                            except (ValueError, AttributeError):
                                if filter_scheduled_date not in scheduled_date:
                                    include = False

                    if include:
                        filtered_projects.append(project)

                # HELPFUL MESSAGE: If filtering returns empty, explain why based on actual status
                # Status lists match statuses.json config
                if not filtered_projects and cached.get('projects'):
                    all_projects = cached.get('projects', [])
                    # From statuses.json - exact matches
                    scheduled_statuses = ['scheduled', 'tentatively scheduled', 'customer scheduled', 'store scheduled', 'install scheduled', 'hdms scheduled']
                    cancelled_statuses = ['cancelled', 'cancelled/surge', 'ready to cancel']
                    completed_statuses = ['completed', 'work complete', 'project completed', 'work order completed', 'done', 'completed-archived']
                    on_hold_statuses = ['on hold', 'waiting for product', 'waiting product', 'missing product', 'paused - missing product', 'paused - waiting on product', 'waiting for permit', 'needs permit', 'product ordered', 'pending']

                    # Categorize projects by status
                    scheduled_projects = [p for p in all_projects if p.get('status', '').lower() in scheduled_statuses]
                    cancelled_projects = [p for p in all_projects if p.get('status', '').lower() in cancelled_statuses]
                    completed_projects = [p for p in all_projects if p.get('status', '').lower() in completed_statuses]
                    on_hold_projects = [p for p in all_projects if any(s in p.get('status', '').lower() for s in on_hold_statuses)]

                    cache_duration = (time.time() - start_time) * 1000

                    if scheduled_projects:
                        logger.info(f"[VOICE-CACHE] No schedulable projects, but found {len(scheduled_projects)} already scheduled")
                        scheduled_info = []
                        for p in scheduled_projects[:3]:
                            cat = p.get('category', 'Project')
                            date = p.get('scheduledDate', 'upcoming')
                            scheduled_info.append(f"{cat} scheduled for {date}")
                        return {
                            "message": f"I found {len(scheduled_projects)} project(s), but they're already scheduled: {'; '.join(scheduled_info)}. Would you like to reschedule, cancel, or check the details?",
                            "projects": scheduled_projects,
                            "already_scheduled": True,
                            "_source": "voice_cache",
                            "pf_http_status_code": 200
                        }

                    if cancelled_projects:
                        logger.info(f"[VOICE-CACHE] No schedulable projects, found {len(cancelled_projects)} cancelled")
                        cat = cancelled_projects[0].get('category', 'Your project')
                        return {
                            "message": f"Your {cat} project has been cancelled and cannot be scheduled. Would you like more information or to speak with customer service?",
                            "projects": cancelled_projects,
                            "status_reason": "cancelled",
                            "_source": "voice_cache",
                            "pf_http_status_code": 200
                        }

                    if completed_projects:
                        logger.info(f"[VOICE-CACHE] No schedulable projects, found {len(completed_projects)} completed")
                        cat = completed_projects[0].get('category', 'Your project')
                        return {
                            "message": f"Your {cat} project has been completed. Is there anything else I can help you with?",
                            "projects": completed_projects,
                            "status_reason": "completed",
                            "_source": "voice_cache",
                            "pf_http_status_code": 200
                        }

                    if on_hold_projects:
                        logger.info(f"[VOICE-CACHE] No schedulable projects, found {len(on_hold_projects)} on hold")
                        cat = on_hold_projects[0].get('category', 'Your project')
                        status = on_hold_projects[0].get('status', 'on hold')
                        return {
                            "message": f"Your {cat} project is currently {status} and cannot be scheduled yet. Would you like more details?",
                            "projects": on_hold_projects,
                            "status_reason": "on_hold",
                            "_source": "voice_cache",
                            "pf_http_status_code": 200
                        }

                    # Fallback: show all projects with their actual status
                    logger.info(f"[VOICE-CACHE] No schedulable projects, showing {len(all_projects)} with current status")
                    project_info = [f"{p.get('category', 'Project')} ({p.get('status', 'Unknown')})" for p in all_projects[:3]]
                    return {
                        "message": f"I found {len(all_projects)} project(s): {'; '.join(project_info)}. None are ready to schedule. Would you like more details?",
                        "projects": all_projects,
                        "status_reason": "not_schedulable",
                        "_source": "voice_cache",
                        "pf_http_status_code": 200
                    }

                projects = filtered_projects

            cache_duration = (time.time() - start_time) * 1000
            logger.info(f"[VOICE-CACHE] Returning {len(projects)}/{original_count} cached projects (filtered) in {cache_duration:.2f}ms")

            # Format response same as API path
            formatted_response = format_projects_for_agent(projects, customer_id, 200)
            formatted_response['_source'] = 'voice_cache'
            return formatted_response

    # Track PF API HTTP status code
    pf_http_status_code = 200  # Default for mock/success

    if USE_MOCK_API:
        logger.info(f"[MOCK] Fetching projects for customer {customer_id}")
        response = get_mock_projects(customer_id)
    else:
        logger.info(f"[REAL] Fetching projects for customer {customer_id} and client {client_id}")
        # OLD Portal API format: /dashboard/get/{client_id}/{customer_id}
        url = f"{config['dashboard_url']}/{client_id}/{customer_id}"
        logger.info(f"Making API request to: {url}")

        # Use make_api_request_with_retry for connection pooling
        api_start = time.time()
        try:
            res = make_api_request_with_retry(
                "GET",
                url,
                {**auth_headers, 'Accept-Encoding': 'gzip, deflate'},
                client_id=client_id,
                user_id=customer_id,
                timeout=(5, 45)  # (connect timeout, read timeout) - increased to 45s
            )
            api_duration = (time.time() - api_start) * 1000
            pf_http_status_code = res.status_code
            logger.info(f"API call took {api_duration:.2f}ms")
            logger.info(f"Response status: {pf_http_status_code}")
            logger.info(f"Response headers: {dict(res.headers)}")
            logger.info(f"Response text (first 2000 chars): {res.text[:2000]}")
            response = res.json()
        except requests.HTTPError as e:
            api_duration = (time.time() - api_start) * 1000
            pf_http_status_code = e.response.status_code
            logger.error(f"HTTP error fetching projects after {api_duration:.2f}ms: {e}")
            if e.response.status_code == 401:
                raise ValueError("SESSION_EXPIRED: Your session has expired. Please log out and log back in to continue.")
            elif e.response.status_code == 403:
                raise ValueError("SESSION_EXPIRED: Your session has expired. Please log out and log back in to continue.")
            else:
                raise ValueError(f"Failed to fetch projects: HTTP {e.response.status_code}")

    # OPTIMIZATION: Extract and format projects efficiently
    processing_start = time.time()

    raw_data = response.get("data", [])
    logger.info(f"Processing {len(raw_data)} projects from API")

    # DEBUG: Log raw fields from first project to check installer data
    if raw_data:
        first_item = raw_data[0]
        installer_fields = {k: v for k, v in first_item.items() if 'user' in k.lower() or 'installer' in k.lower()}
        logger.info(f"[DEBUG] First project installer-related fields: {installer_fields}")
        # DEBUG: Log all type-related fields
        type_fields = {k: v for k, v in first_item.items() if 'type' in k.lower()}
        logger.info(f"[DEBUG] First project type-related fields: {type_fields}")

    # Extract comprehensive fields from each project (fast iteration)
    projects = [extract_project_minimal(item) for item in raw_data]

    # Filter out closed/cancelled/completed projects (not actionable via any channel)
    # This applies to ALL channels: voice, SMS, chat
    excluded_statuses = ['closed', 'cancelled', 'completed', 'work complete', 'done', 'archived',
                         'completed-archived', 'cancelled/surge', 'ready to cancel']
    original_count = len(projects)
    projects = [p for p in projects if p.get('status', '').lower() not in excluded_statuses]
    if original_count != len(projects):
        logger.info(f"[FILTER] Excluded {original_count - len(projects)} closed/cancelled/completed projects from {original_count} total")

    # Apply filters if provided (case-insensitive matching)
    if filter_status or filter_category or filter_project_type or filter_scheduled_month or filter_scheduled_date:
        logger.info(f"Applying filters: status={filter_status}, category={filter_category}, projectType={filter_project_type}, scheduled_month={filter_scheduled_month}, scheduled_date={filter_scheduled_date}")

        # Month name mapping for scheduled_month filter
        month_names = {
            'january': '01', 'february': '02', 'march': '03', 'april': '04',
            'may': '05', 'june': '06', 'july': '07', 'august': '08',
            'september': '09', 'october': '10', 'november': '11', 'december': '12',
            'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
            'jun': '06', 'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
        }

        filtered_projects = []
        for project in projects:
            # Check status filter (simple substring match, case-insensitive)
            if filter_status:
                project_status = project.get('status', '').lower()
                filter_status_lower = filter_status.lower()

                # Special handling for "schedulable" - matches "New" or "Ready To Schedule"
                if filter_status_lower == 'schedulable':
                    if project_status not in ['new', 'ready to schedule']:
                        continue
                elif filter_status_lower not in project_status:
                    continue

            # Check category filter
            if filter_category:
                project_category = project.get('category', '').lower()
                if filter_category.lower() not in project_category:
                    continue

            # Check projectType filter
            if filter_project_type:
                project_type = project.get('projectType', '').lower()
                if filter_project_type.lower() not in project_type:
                    continue

            # Check scheduled_month filter (filter by appointment month)
            if filter_scheduled_month:
                scheduled_date = project.get('scheduledDate', '')
                if not scheduled_date:
                    # No scheduled date - doesn't match month filter
                    continue

                # Try to match month from scheduled date
                # Formats: "Jan 5, 2026 5:00 PM", "2026-01-05", "01-05-2026 08:00 AM"
                filter_month_lower = filter_scheduled_month.lower()
                month_num = month_names.get(filter_month_lower, '')

                # Check if month matches in various date formats
                month_matched = False

                # Format 1: Month name in string (e.g., "Jan" in "Jan 5, 2026")
                if filter_month_lower[:3] in scheduled_date.lower():
                    month_matched = True
                elif month_num:
                    # Format 2: ISO format "2026-01-05" (month in middle with dashes)
                    if f"-{month_num}-" in scheduled_date:
                        month_matched = True
                    # Format 3: MM-DD-YYYY format "01-05-2026" (month at start)
                    elif scheduled_date.startswith(f"{month_num}-"):
                        month_matched = True
                    # Format 4: MM/DD/YYYY format "01/05/2026"
                    elif scheduled_date.startswith(f"{month_num}/"):
                        month_matched = True

                if not month_matched:
                    continue

            # Check scheduled_date filter (filter by exact date)
            if filter_scheduled_date:
                scheduled_date = project.get('scheduledDate', '')
                if not scheduled_date:
                    # No scheduled date - doesn't match date filter
                    continue

                # Parse the filter date (expected format: YYYY-MM-DD)
                try:
                    from datetime import datetime
                    filter_date = datetime.strptime(filter_scheduled_date, "%Y-%m-%d")
                    filter_day = filter_date.day
                    filter_month = filter_date.month
                    filter_year = filter_date.year

                    # Try to match date in various formats
                    date_matched = False

                    # Format 1: "Jan 13, 2026 1:00 PM" - Month Day, Year
                    import re
                    match = re.search(r'(\w{3})\s+(\d{1,2}),?\s+(\d{4})', scheduled_date)
                    if match:
                        month_abbr = match.group(1).lower()
                        day = int(match.group(2))
                        year = int(match.group(3))
                        month_map = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                                     'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
                        if month_map.get(month_abbr) == filter_month and day == filter_day and year == filter_year:
                            date_matched = True

                    # Format 2: ISO format "2026-01-13" or "2026-01-13T..."
                    if not date_matched and filter_scheduled_date in scheduled_date:
                        date_matched = True

                    # Format 3: MM-DD-YYYY or MM/DD/YYYY at start
                    if not date_matched:
                        mm_dd_pattern = f"{filter_month:02d}[-/]{filter_day:02d}[-/]{filter_year}"
                        if re.match(mm_dd_pattern, scheduled_date):
                            date_matched = True

                    if not date_matched:
                        continue
                except (ValueError, AttributeError):
                    # Invalid date format - skip filter
                    pass

            # All filters passed, include this project
            filtered_projects.append(project)

        logger.info(f"Filtered {len(projects)} projects down to {len(filtered_projects)} projects")

        # HELPFUL MESSAGE: If filtering for schedulable returns empty, check for scheduled projects
        if filter_status and filter_status.lower() == 'schedulable' and not filtered_projects and projects:
            # Check if any projects are already scheduled
            scheduled_statuses = ['scheduled', 'tentatively scheduled', 'customer scheduled', 'store scheduled', 'install scheduled']
            scheduled_projects = [
                p for p in projects
                if p.get('status', '').lower() in scheduled_statuses
            ]

            if scheduled_projects:
                # Build helpful message about scheduled projects
                logger.info(f"No schedulable projects, but found {len(scheduled_projects)} already scheduled")
                scheduled_info = []
                for p in scheduled_projects[:3]:  # Limit to first 3
                    cat = p.get('category', 'Project')
                    date = p.get('scheduledDate', 'upcoming')
                    scheduled_info.append(f"{cat} scheduled for {date}")

                return {
                    "message": f"All your projects are already scheduled. {'; '.join(scheduled_info)}. Would you like to reschedule or check the appointment details?",
                    "projects": scheduled_projects,
                    "already_scheduled": True,
                    "pf_http_status_code": pf_http_status_code
                }

        projects = filtered_projects

    # FALLBACK: If NO projects after filtering, but we had projects before filtering,
    # check if there are scheduled projects to inform user about
    if not projects and raw_data:
        all_projects = [extract_project_minimal(item) for item in raw_data]
        scheduled_statuses = ['scheduled', 'tentatively scheduled', 'customer scheduled', 'store scheduled', 'install scheduled']
        scheduled_projects = [
            p for p in all_projects
            if p.get('status', '').lower() in scheduled_statuses
        ]

        if scheduled_projects:
            logger.info(f"No projects after filter, but found {len(scheduled_projects)} scheduled projects")
            scheduled_info = []
            for p in scheduled_projects[:3]:
                cat = p.get('category', 'Project')
                date = p.get('scheduledDate', 'upcoming')
                scheduled_info.append(f"{cat} scheduled for {date}")

            # Return scheduled projects with info
            return {
                "message": f"I found {len(scheduled_projects)} project(s), but they're already scheduled: {'; '.join(scheduled_info)}. Would you like to reschedule, cancel, or check the details?",
                "projects": scheduled_projects,
                "already_scheduled": True,
                "pf_http_status_code": pf_http_status_code
            }

        # Check for any other projects (not scheduled) to show
        other_projects = [p for p in all_projects if p.get('status', '').lower() not in scheduled_statuses]
        if other_projects:
            logger.info(f"No matching projects, but found {len(other_projects)} other projects")
            return format_projects_for_agent(other_projects, customer_id, pf_http_status_code)

    # Pre-format exactly as agent expects (no agent work needed)
    formatted_response = format_projects_for_agent(projects, customer_id, pf_http_status_code)

    processing_duration = (time.time() - processing_start) * 1000
    total_duration = (time.time() - start_time) * 1000

    logger.info(f"Processing took {processing_duration:.2f}ms, Total: {total_duration:.2f}ms")

    # DEBUG: Log what we're returning to agent
    logger.info(f"Returning formatted response with {len(projects)} projects")
    logger.info(f"Sample response structure: {json.dumps(formatted_response, separators=(',', ':'))[:500]}")

    # OPTIMIZATION: Return pre-formatted data
    # Agent receives this ready for UI - NO additional formatting needed
    return formatted_response


def _build_project_details_response(
    project: Dict,
    project_id: str,
    client_id: str,
    customer_id: str,
    extra_key: str = None,
    extra_value: str = None
) -> Dict[str, Any]:
    """
    Build project details response from a project dict.

    Used by both API path and voice cache path to ensure consistent response format.
    """
    # Extract fields from the project (works with both API and cached format)
    project_id_str = project.get("id", project_id)
    project_number = project.get("projectNumber", "")
    status = project.get("status", "Unknown")
    project_category = project.get("category", "Not specified")
    project_type = project.get("projectType", "Not specified")

    # Address information - handle both formats
    address_info = project.get("address", {})
    address1 = address_info.get("address1", address_info.get("address_1", ""))
    city = address_info.get("city", "")
    state = address_info.get("state", "")
    zipcode = address_info.get("zipcode", "")

    # Build full address
    city_state_zip = f"{city}, {state} {zipcode}".strip()
    if city_state_zip and city_state_zip != ", ":
        full_address = f"{address1}, {city_state_zip}" if address1 else city_state_zip
    else:
        full_address = address1 or "Address not available"

    # Scheduling information - handle both formats
    scheduled_start = project.get("scheduledDate", "")
    scheduled_end = project.get("scheduledEndDate", "")
    scheduled_time = project.get("scheduledTime", "")

    if scheduled_start and scheduled_end:
        scheduling_status = f"Scheduled from {scheduled_start} to {scheduled_end}"
    elif scheduled_start:
        if scheduled_time:
            scheduling_status = f"Scheduled for {scheduled_start} at {scheduled_time}"
        else:
            scheduling_status = f"Scheduled for {scheduled_start}"
    else:
        scheduling_status = "Not yet scheduled"

    # Store information
    store_info = project.get("store", {})
    store_number = store_info.get("storeNumber", "")
    store_name = store_info.get("storeName", "")
    store_display = f"{store_name} (#{store_number})" if store_number and store_name else store_name or store_number or "Not specified"

    # Installer/technician information - handle both formats
    installer_info = project.get("installer", {})
    technician_name = installer_info.get("name", project.get("installerName", ""))
    technician_id = installer_info.get("id", "")

    # Format technician display
    if technician_name:
        technician_display = f"{technician_name}"
        if technician_id:
            technician_display += f" (ID: {technician_id})"
    else:
        technician_display = "Not assigned"

    # Get additional fields
    date_sold = project.get("dateSold", "")

    # Create a human-readable summary for the agent
    summary = f"""Project #{project_number or 'Unknown'} - {project_category} ({project_type})
Status: {status}
Installation Address: {full_address}
Store: {store_display}
{scheduling_status}"""

    if technician_name:
        summary += f"\nTechnician: {technician_display}"

    if date_sold:
        summary += f"\nSold Date: {date_sold}"

    # Build response
    response = {
        "action": "get_project_details",
        "project": project,

        # Legacy fields for backward compatibility
        "project_id": project_id_str,
        "project_number": project_number,
        "client_id": client_id,
        "customer_id": customer_id,
        "summary": summary,
        "full_address": full_address,
        "scheduling_status": scheduling_status,
        "store_display": store_display,
        "technician_display": technician_display,
        "category": project_category,
        "type": project_type,
        "status": status,
        "status_id": project.get("status_id"),
        "scheduled_start": scheduled_start,
        "scheduled_end": scheduled_end,
        "date_sold": date_sold,
        "customer": {
            "customer_id": customer_id,
            "first_name": "",
            "last_name": "",
            "full_name": "Unknown Customer",
            "email": None,
            "phone": None
        },
        "installation_address": {
            "address_id": None,
            "address1": address1,
            "address2": "",
            "city": city,
            "state": state,
            "zipcode": zipcode,
            "full_address": full_address
        },
        "store_info": {
            "store_id": None,
            "store_number": store_number,
            "store_name": store_name,
            "display_name": store_display
        },
        "technician": {
            "technician_id": technician_id,
            "name": technician_name,
            "email": None,
            "phone": None,
            "bio": None,
            "display_name": technician_display
        } if technician_name else None,
        "service_time": None,
        "service_time_unit": "hours",
        "default_service_time": None,
        "client_timezone": "US/Eastern"
    }

    # Add extra field if provided (e.g., '_source': 'voice_cache')
    if extra_key and extra_value:
        response[extra_key] = extra_value

    return response


def handle_get_project_details(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: get_project_details
    Returns detailed information for a specific project with enhanced formatting and validation

    VOICE OPTIMIZATION: Uses preloaded cache to avoid API call
    """
    project_id = params.get('project_id')
    client_id = params.get('client_id', 'default')

    # Validation
    if not project_id:
        raise ValueError("Missing required parameter: project_id")

    # Get customer_id from session attributes if available
    customer_id = params.get('customer_id')
    if not customer_id:
        logger.warning("customer_id not provided in parameters, this may cause issues")

    logger.info(f"[REAL] Fetching project details for project {project_id}, client {client_id}, customer {customer_id}")

    # VOICE OPTIMIZATION: Check preloaded cache first
    from_phone = params.get('_from_phone', '')
    if from_phone:
        cached = get_voice_cached_projects(from_phone)
        if cached:
            projects = cached.get('projects', [])
            project_mapping = cached.get('project_mapping', {})

            # Try to find project by ID, projectNumber, or ordinal
            project = None
            project_id_str = str(project_id)

            # Check ordinal mapping first (e.g., "1", "2", "first", "last")
            ordinal_key = f'ordinal:{project_id_str}'
            if ordinal_key in project_mapping:
                mapped_id = project_mapping[ordinal_key]
                project = next((p for p in projects if p.get('id') == mapped_id), None)
                if project:
                    logger.info(f"[VOICE-CACHE] Resolved ordinal '{project_id}' to project {mapped_id}")

            # Check projectNumber mapping
            if not project:
                pn_key = f'projectNumber:{project_id_str}'
                if pn_key in project_mapping:
                    mapped_id = project_mapping[pn_key]
                    project = next((p for p in projects if p.get('id') == mapped_id), None)
                    if project:
                        logger.info(f"[VOICE-CACHE] Resolved projectNumber '{project_id}' to project {mapped_id}")

            # Direct ID/projectNumber match
            if not project:
                for p in projects:
                    if p.get('id') == project_id_str or p.get('projectNumber', '').lower() == project_id_str.lower():
                        project = p
                        logger.info(f"[VOICE-CACHE] Found project by direct match: {project_id}")
                        break

            if project:
                # Build response from cached project
                return _build_project_details_response(project, project_id, client_id, customer_id, '_source', 'voice_cache')

            logger.info(f"[VOICE-CACHE] Project {project_id} not found in cache, falling back to API")

    try:
        # Use the same endpoint as list_projects which returns full project details
        # Then filter for the specific project_id
        url = f"{config['dashboard_url']}/{client_id}/{customer_id}"
        logger.info(f"Making API request to: {url}")

        # Use make_api_request_with_retry for connection pooling
        res = make_api_request_with_retry(
            "GET",
            url,
            auth_headers,
            client_id=client_id,
            user_id=customer_id,
            timeout=30
        )
        response = res.json()

        # Extract projects from response
        raw_data = response.get("data", [])
        logger.info(f"Received {len(raw_data)} projects from API, filtering for project_id {project_id}")

        # Find the specific project - match by internal ID OR Order Number
        project_data = None
        for item in raw_data:
            # Check if this is the project we're looking for
            item_project_id = str(safe_get(item, "project_project_id", default=""))
            item_project_number = str(safe_get(item, "project_project_number", default=""))

            # Match by internal ID or Order Number (case-insensitive for Order Numbers)
            if item_project_id == str(project_id) or item_project_number.lower() == str(project_id).lower():
                project_data = item
                match_type = 'internal ID' if item_project_id == str(project_id) else 'Order Number'
                logger.info(f"Found project {project_id} in results (matched by {match_type})")
                break

        if not project_data:
            raise ValueError(f"Project {project_id} not found in customer's projects")

        # Use the same extraction function as list_projects to get full details
        # This returns a properly formatted project with all fields extracted
        project = extract_project_minimal(project_data)

        # Extract fields from the formatted project (all at top level now)
        project_id_str = project.get("id", project_id)
        project_number = project.get("projectNumber", "")
        status = project.get("status", "Unknown")
        project_category = project.get("category", "Not specified")
        project_type = project.get("projectType", "Not specified")

        # Address information
        address_info = project.get("address", {})
        address1 = address_info.get("address1", "")
        city = address_info.get("city", "")
        state = address_info.get("state", "")
        zipcode = address_info.get("zipcode", "")

        # Build full address
        city_state_zip = f"{city}, {state} {zipcode}".strip()
        if city_state_zip and city_state_zip != ", ":
            full_address = f"{address1}, {city_state_zip}" if address1 else city_state_zip
        else:
            full_address = address1 or "Address not available"

        # Scheduling information
        scheduled_start = project.get("scheduledDate", "")
        scheduled_end = project.get("scheduledEndDate", "")
        if scheduled_start and scheduled_end:
            scheduling_status = f"Scheduled from {scheduled_start} to {scheduled_end}"
        elif scheduled_start:
            scheduling_status = f"Scheduled for {scheduled_start}"
        else:
            scheduling_status = "Not yet scheduled"

        # Store information
        store_info = project.get("store", {})
        store_number = store_info.get("storeNumber", "")
        store_name = store_info.get("storeName", "")
        store_display = f"{store_name} (#{store_number})" if store_number and store_name else store_name or store_number or "Not specified"

        # Installer/technician information
        installer_info = project.get("installer", {})
        technician_name = installer_info.get("name", "")
        technician_id = installer_info.get("id", "")

        # Format technician display
        if technician_name:
            technician_display = f"{technician_name}"
            if technician_id:
                technician_display += f" (ID: {technician_id})"
        else:
            technician_display = "Not assigned"

        # Get additional fields
        source_system = project.get("sourceSystem", "")
        date_sold = project.get("dateSold", "")
        has_documents = project.get("hasDocuments", False)

        # Create a human-readable summary for the agent
        summary = f"""Project #{project_number or 'Unknown'} - {project_category} ({project_type})
Status: {status}
Installation Address: {full_address}
Store: {store_display}
{scheduling_status}"""

        if technician_name:
            summary += f"\nTechnician: {technician_display}"

        if date_sold:
            summary += f"\nSold Date: {date_sold}"

        # Update the project object with additional fields
        project["address"]["fullAddress"] = full_address

        # Add technician info if available
        if technician_name:
            project["technician"] = {
                "id": technician_id,
                "name": technician_name,
                "display_name": technician_display
            }

        # Return enhanced response with both legacy and new format
        return {
            "action": "get_project_details",
            "project": project,

            # Legacy fields for backward compatibility
            "project_id": project_id_str,
            "project_number": project_number,
            "client_id": client_id,
            "customer_id": customer_id,
            "summary": summary,
            "full_address": full_address,
            "scheduling_status": scheduling_status,
            "store_display": store_display,
            "technician_display": technician_display,
            "category": project_category,
            "type": project_type,
            "status": status,
            "status_id": None,
            "scheduled_start": scheduled_start,
            "scheduled_end": scheduled_end,
            "date_sold": date_sold,
            "customer": {
                "customer_id": customer_id,
                "first_name": "",
                "last_name": "",
                "full_name": "Unknown Customer",
                "email": None,
                "phone": None
            },
            "installation_address": {
                "address_id": None,
                "address1": address1,
                "address2": "",
                "city": city,
                "state": state,
                "zipcode": zipcode,
                "full_address": full_address
            },
            "store_info": {
                "store_id": None,
                "store_number": store_number,
                "store_name": store_name,
                "display_name": store_display
            },
            "technician": {
                "technician_id": technician_id,
                "name": technician_name,
                "email": None,
                "phone": None,
                "bio": None,
                "display_name": technician_display
            } if technician_name else None,
            "service_time": None,
            "service_time_unit": "hours",
            "default_service_time": None,
            "client_timezone": "US/Eastern",
            "full_data": project_data
        }

    except requests.HTTPError as e:
        if e.response.status_code == 404:
            raise ValueError(f"Project {project_id} not found")
        elif e.response.status_code == 401:
            raise ValueError("SESSION_EXPIRED: Your session has expired. Please log out and log back in to continue.")
        elif e.response.status_code == 403:
            raise ValueError("SESSION_EXPIRED: Your session has expired. Please log out and log back in to continue.")
        else:
            logger.error(f"HTTP error fetching project details: {str(e)}")
            raise ValueError(f"Failed to fetch project details: {e.response.status_code}")
    except requests.RequestException as e:
        logger.error(f"Request error fetching project details: {str(e)}")
        raise ValueError(f"Unable to connect to project API: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_project_details: {str(e)}", exc_info=True)
        raise

def handle_get_available_dates(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: get_available_dates
    Returns available dates for scheduling or rescheduling a project

    API Selection:
    - is_reschedule=False (default): Uses slotsChatbot API for NEW scheduling
    - is_reschedule=True: Uses get-rescheduler-slots API for RESCHEDULING
      (ignores current status, shows alternative slots)

    Real API Endpoints:
    - New scheduling: GET /scheduler/.../slotsChatbot
    - Rescheduling: GET /scheduler/.../get-rescheduler-slots
    """
    project_id = params.get('project_id')
    client_id = params.get('client_id')
    customer_id = params.get('customer_id')

    # RESCHEDULE MODE: Use get-rescheduler-slots API (ignores current status)
    is_reschedule = params.get('is_reschedule', False)
    if isinstance(is_reschedule, str):
        is_reschedule = is_reschedule.lower() in ['true', '1', 'yes']

    # Track PF API HTTP status code
    pf_http_status_code = 200  # Default for mock/success

    if not project_id:
        raise ValueError("Missing required parameter: project_id")

    # Resolve Order Number to internal ID if needed (scheduler API requires internal ID)
    # Check if project_id contains non-digit characters (likely an Order Number)
    if not str(project_id).isdigit() and not USE_MOCK_API and customer_id and client_id:
        logger.info(f"Project ID '{project_id}' appears to be an Order Number, resolving to internal ID...")
        try:
            # Fetch projects to resolve Order Number
            url = f"{config['dashboard_url']}/{client_id}/{customer_id}"
            res = make_api_request_with_retry("GET", url, auth_headers, client_id=client_id, user_id=customer_id, timeout=30)
            raw_data = res.json().get("data", [])
            resolved_id = resolve_project_id(project_id, raw_data)
            if resolved_id:
                logger.info(f"Resolved Order Number '{project_id}' to internal ID '{resolved_id}'")
                project_id = resolved_id
            else:
                logger.warning(f"Could not resolve Order Number '{project_id}', proceeding with original value")
        except Exception as e:
            logger.warning(f"Failed to resolve Order Number '{project_id}': {e}, proceeding with original value")

    # Determine start_date and date limiting strategy (used for both mock and real API)
    # Strategy determines how many dates to return:
    # - 'specific_day': user asked for "Jan 10" -> return only that 1 day
    # - 'week': user asked for "January" or "next month" -> return 7 days
    # - 'date_range': user asked for "between Jan 9 and Jan 18" -> use exact range
    # - None: default "schedule this" -> return 7 days
    start_date = params.get('start_date')
    explicit_end_date = params.get('end_date')  # User-provided end date for range queries
    date_strategy = None
    days_to_fetch = 10  # Default: 10 days for better availability

    if not start_date:
        # Check if 'date' parameter has a natural language value (e.g., "next month")
        date_param = params.get('date')
        if date_param:
            # First try to extract a date range (e.g., "between Jan 9 and Jan 18")
            date_range = extract_date_range(date_param)
            if date_range:
                start_date = date_range['start_date']
                explicit_end_date = date_range['end_date']
                date_strategy = 'date_range'
                logger.info(f"[DATE RANGE] Using explicit range: '{date_param}' -> start={start_date}, end={explicit_end_date}")
            else:
                use_regex_fallback = True  # Default to regex

                # Try LLM-based date interpreter first (if enabled and available)
                if USE_LLM_DATE_INTERPRETER and LLM_DATE_AVAILABLE:
                    try:
                        logger.info(f"[DATE-LLM] Interpreting '{date_param}' with LLM")
                        llm_result = interpret_date(date_param)
                        llm_tuple = convert_to_legacy_format(llm_result)
                        start_date = llm_tuple[0]
                        date_strategy = llm_tuple[1]
                        days_to_fetch = llm_tuple[2]
                        explicit_end_date = llm_tuple[3] if len(llm_tuple) > 3 else None
                        logger.info(f"[DATE-LLM] Result: start={start_date}, strategy={date_strategy}, days={days_to_fetch}, end={explicit_end_date}")
                        logger.info(f"[DATE-LLM] Interpretation: {llm_result.get('interpretation', 'N/A')}")
                        use_regex_fallback = False  # LLM succeeded
                    except Exception as e:
                        logger.warning(f"[DATE-LLM] Failed: {e}, falling back to regex")

                # Fall back to regex-based conversion
                if use_regex_fallback:
                    result = convert_natural_date(date_param, return_strategy=True)
                    # Unpack result - may have 3 or 4 elements (week queries include week_end_date)
                    if result and len(result) >= 3:
                        start_date = result[0]
                        date_strategy = result[1]
                        days_to_fetch = result[2]
                        # Week queries may include explicit week_end_date
                        if len(result) == 4:
                            explicit_end_date = result[3]
                            logger.info(f"[DATE] Using date preference: '{date_param}' -> start_date={start_date}, strategy={date_strategy}, days={days_to_fetch}, week_end={explicit_end_date}")
                        else:
                            logger.info(f"[DATE] Using date preference: '{date_param}' -> start_date={start_date}, strategy={date_strategy}, days={days_to_fetch}")
                    else:
                        start_date = None
                        date_strategy = None
                        days_to_fetch = 10

    # Handle week_past strategy - the entire requested week is in the past
    if date_strategy == 'week_past':
        logger.info(f"[DATE] Requested week is entirely in the past - returning no dates")
        return {
            "action": "get_available_dates",
            "project_id": project_id,
            "available_dates": [],
            "message": "The requested week has already passed. No dates are available for that time period.",
            "week_in_past": True,
            "pf_http_status_code": 200
        }

    if not start_date:
        # Use tomorrow as default - today rarely has available slots
        from datetime import timedelta
        start_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        date_strategy = 'day'
        days_to_fetch = 10  # Check 10 days for better availability
        logger.info(f"[DATE] Using tomorrow as start_date: {start_date}, strategy={date_strategy}")

    if USE_MOCK_API:
        logger.info(f"[MOCK] Fetching available dates for project {project_id}")
        response = get_mock_available_dates(project_id)
    # ========================================================================
    # RESCHEDULE MODE: Use get-rescheduler-slots API as PRIMARY
    # This API ignores current status and shows alternative slots for
    # projects that are already scheduled.
    # ========================================================================
    elif is_reschedule:
        if not client_id:
            raise ValueError("Missing required parameter for rescheduler API: client_id")

        logger.info(f"[RESCHEDULE] Using get-rescheduler-slots API for project {project_id}")

        from datetime import timedelta
        if not start_date:
            start_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        resched_end_date = explicit_end_date or (start_dt + timedelta(days=21)).strftime('%Y-%m-%d')

        try:
            resched_result = handle_get_rescheduler_slots(
                {
                    'project_id': project_id,
                    'client_id': client_id,
                    'customer_id': customer_id,
                    'date': start_date,
                    'selected_date': resched_end_date
                },
                config,
                auth_headers
            )

            resched_dates = resched_result.get('available_dates', [])
            resched_formatted = resched_result.get('dates', [])

            logger.info(f"[RESCHEDULE] Rescheduler API returned {len(resched_dates)} dates")

            # Return rescheduler result directly with consistent format
            return {
                "action": "get_available_dates",
                "project_id": project_id,
                "available_dates": sorted(resched_dates) if resched_dates else [],
                "dates": resched_formatted,
                "dateCount": len(resched_dates),
                "request_id": resched_result.get('request_id'),
                "start_date": start_date,
                "is_reschedule": True,
                "mock_mode": False,
                "pf_http_status_code": resched_result.get('pf_http_status_code', 200)
            }
        except Exception as e:
            logger.error(f"[RESCHEDULE] Rescheduler API failed: {e}")
            raise ValueError(f"Unable to fetch reschedule dates: {str(e)}")
    else:
        # Validate client_id is present for real API calls
        if not client_id:
            raise ValueError("Missing required parameter for real API: client_id")

        logger.info(f"[REAL] Fetching available dates for client {client_id}, project {project_id}")

        # Calculate end_date based on strategy:
        # - 'date_range': use explicit_end_date provided by user (e.g., "between Jan 9 and Jan 18")
        # - 'specific_day': end = start (same day)
        # - 'week'/default: end = start + days_to_fetch - 1
        from datetime import timedelta
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")

        if explicit_end_date:
            # User explicitly specified end date (date range query)
            end_date = explicit_end_date
            logger.info(f"[DATE RANGE] Using explicit end_date from user: {end_date}")
        elif date_strategy == 'specific_day':
            # For specific day, end = start (same day)
            end_date = start_date
        else:
            # For week/default, end = start + days_to_fetch - 1
            end_date = (start_dt + timedelta(days=days_to_fetch - 1)).strftime("%Y-%m-%d")

        # Construct URL with new date range format: startDate/endDate/slotsChatbot
        url = f"{config['scheduler_base_url']}/scheduler/client/{client_id}/project/{project_id}/startDate/{start_date}/endDate/{end_date}/slotsChatbot"

        logger.info(f"[DATE RANGE] startDate={start_date}, endDate={end_date}")
        logger.info(f"GET {url}")

        try:
            # Make API request with connection pooling
            res = make_api_request_with_retry("GET", url, auth_headers, client_id=client_id, user_id=customer_id, timeout=30)
            pf_http_status_code = res.status_code
            response = res.json()
            logger.info(f"Available dates retrieved successfully")
        except requests.HTTPError as e:
            status_code = e.response.status_code
            pf_http_status_code = status_code
            error_body = e.response.text
            logger.error(f"HTTP {status_code} error fetching available dates: {error_body}")

            # Handle specific error codes
            if status_code == 400:
                # Check for various "already scheduled" error patterns from the API
                error_lower = error_body.lower()
                if ("already requested" in error_lower or
                    "already scheduled" in error_lower or
                    "already contains a technician" in error_lower or
                    "technician already assigned" in error_lower):
                    # Return structured response indicating project is already scheduled
                    # This allows the orchestrator to offer reschedule instead of showing an error
                    logger.info(f"[ALREADY_SCHEDULED] Project {project_id} is already scheduled: {error_body}")
                    return {
                        "action": "get_available_dates",
                        "project_id": project_id,
                        "already_scheduled": True,
                        "error_message": "This project is already scheduled.",
                        "available_dates": [],
                        "dates": [],
                        "dateCount": 0,
                        "mock_mode": USE_MOCK_API,
                        "pf_http_status_code": pf_http_status_code
                    }
                raise ValueError(f"Invalid project: {error_body}")
            elif status_code == 404:
                raise ValueError("No available dates for this project")
            elif status_code == 401:
                raise ValueError("Authentication failed - token may be expired (after retry)")
            else:
                raise ValueError(f"Failed to fetch available dates: HTTP {status_code}")
        except requests.RequestException as e:
            logger.error(f"Request error fetching available dates: {str(e)}")
            raise ValueError(f"Unable to connect to scheduling API: {str(e)}")

    data = response.get("data", {})
    raw_dates = data.get("dates", [])
    raw_slots = data.get("slots", [])

    # NOTE: Don't filter dates based on slots count here
    # The correct flow is: show dates → user picks date → fetch time slots for that date
    # The slots array at this stage may be empty/incomplete - real slots come from get_time_slots
    if raw_dates:
        logger.info(f"[DATES] API returned {len(raw_dates)} dates, {len(raw_slots)} slots preview")

    # Sort dates chronologically
    raw_dates = sorted(raw_dates)

    # Track original count before filtering for logging
    original_count = len(raw_dates)
    auto_expanded = False

    # ========================================================================
    # AUTO-EXPAND DATE RANGE: If no dates found in default 10-day window,
    # automatically expand to 21 days before returning "no dates available"
    # This prevents "booked up" dead ends that frustrate customers.
    # Only applies to default queries (not explicit date ranges or specific days)
    # ========================================================================
    if (len(raw_dates) == 0 and
        not USE_MOCK_API and
        days_to_fetch == 10 and
        date_strategy not in ['date_range', 'specific_day', 'week_past']):

        logger.info(f"[AUTO-EXPAND] No dates in 10-day window, expanding to 21 days")

        # Re-calculate end_date for 21-day range
        expanded_days = 21
        expanded_end_date = (start_dt + timedelta(days=expanded_days - 1)).strftime("%Y-%m-%d")

        # Construct expanded URL
        expanded_url = f"{config['scheduler_base_url']}/scheduler/client/{client_id}/project/{project_id}/startDate/{start_date}/endDate/{expanded_end_date}/slotsChatbot"
        logger.info(f"[AUTO-EXPAND] GET {expanded_url}")

        try:
            expanded_res = make_api_request_with_retry("GET", expanded_url, auth_headers, client_id=client_id, user_id=customer_id, timeout=30)
            pf_http_status_code = expanded_res.status_code
            expanded_response = expanded_res.json()
            expanded_data = expanded_response.get("data", {})
            expanded_dates = sorted(expanded_data.get("dates", []))
            expanded_slots = expanded_data.get("slots", [])

            # NOTE: Don't filter dates based on slots - show dates, let user pick, then fetch slots
            logger.info(f"[AUTO-EXPAND] API returned {len(expanded_dates)} dates, {len(expanded_slots)} slots preview")

            raw_dates = expanded_dates
            original_count = len(raw_dates)
            auto_expanded = True

            if raw_dates:
                logger.info(f"[AUTO-EXPAND] Found {len(raw_dates)} dates in 14-day window: {raw_dates[:5]}...")
            else:
                logger.info(f"[AUTO-EXPAND] Still no dates in 14-day window - truly booked up")
        except Exception as e:
            logger.warning(f"[AUTO-EXPAND] Failed to fetch expanded range: {e}")

    # SMART DATE LIMITING: Filter dates based on user's request strategy
    # This reduces response payload and focuses on relevant dates
    if date_strategy == 'date_range':
        # User specified explicit date range (e.g., "between Jan 9 and Jan 18") - return ALL dates in range
        logger.info(f"[DATE LIMIT] Date range: returning all {original_count} dates (user specified explicit range)")
    elif days_to_fetch and days_to_fetch < len(raw_dates):
        if date_strategy == 'specific_day':
            # User asked for specific date (e.g., "Jan 10") - only return that day if available
            if start_date in raw_dates:
                raw_dates = [start_date]
                logger.info(f"[DATE LIMIT] Specific day: filtered {original_count} dates to 1 (requested date {start_date})")
            else:
                # Requested date not available - return first available as fallback
                raw_dates = raw_dates[:1] if raw_dates else []
                logger.info(f"[DATE LIMIT] Specific day {start_date} not available, showing first available: {raw_dates}")
        else:
            # Week strategy - return up to 7 days
            raw_dates = raw_dates[:days_to_fetch]
            logger.info(f"[DATE LIMIT] Week strategy: filtered {original_count} dates to {len(raw_dates)}")
    else:
        logger.info(f"[DATE LIMIT] No filtering needed: {original_count} dates (days_to_fetch={days_to_fetch})")

    # Format dates with day names and group by week for better UI rendering
    formatted_dates = []
    for date_str in raw_dates:
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            formatted_dates.append({
                "date": date_str,
                "displayDate": date_obj.strftime("%m/%d/%Y"),  # 01/15/2026 - standard display format
                "dayName": date_obj.strftime("%A"),  # Monday, Tuesday, etc.
                "dayShort": date_obj.strftime("%a"),  # Mon, Tue, etc.
                "monthDay": date_obj.strftime("%m/%d"),  # 01/15
                "formatted": date_obj.strftime("%a %m/%d/%Y")  # Mon 01/15/2026
            })
        except:
            # Fallback if date parsing fails
            formatted_dates.append({
                "date": date_str,
                "dayName": "",
                "dayShort": "",
                "monthDay": date_str,
                "formatted": date_str
            })

    result = {
        "action": "get_available_dates",
        "project_id": project_id,
        "available_dates": raw_dates,  # Keep original for compatibility
        "dates": formatted_dates,  # Enhanced format for UI
        "dateCount": len(raw_dates),
        "request_id": data.get("request_id"),
        "start_date": start_date,  # IMPORTANT: Base date used for URL - needed for get_time_slots
        "date_strategy": date_strategy,  # 'specific_day' or 'week' - for debugging
        "dates_filtered_from": original_count,  # How many dates the API returned before filtering
        "mock_mode": USE_MOCK_API,
        "pf_http_status_code": pf_http_status_code
    }

    # Include auto-expand info if we expanded the search
    if auto_expanded:
        result["auto_expanded"] = True
        result["expanded_from_days"] = 5
        result["expanded_to_days"] = 14
        if len(raw_dates) == 0:
            result["message"] = "No appointments available in the next 2 weeks. Would you like me to check further out?"

    return result

def handle_get_time_slots(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: get_time_slots
    Returns available time slots for a specific date

    API Selection:
    - is_reschedule=False (default): Uses slotsChatbot API for NEW scheduling
    - is_reschedule=True: Uses get-rescheduler-slots API for RESCHEDULING

    Real API Endpoints:
    - New scheduling: GET /scheduler/.../slotsChatbot
    - Rescheduling: GET /scheduler/client/{client_id}/project/{project_id}/date/{date}/selected/{date}/get-rescheduler-slots

    IMPORTANT: The 'date' param in URL must be the SAME base_date used in get_available_dates,
    while 'selected' is the user's chosen date. They are NOT the same!
    """
    project_id = params.get('project_id')
    client_id = params.get('client_id')
    selected_date = params.get('date')  # User's selected date
    base_date = params.get('base_date') or params.get('start_date')  # Original start_date from get_available_dates
    request_id = params.get('request_id')
    customer_id = params.get('customer_id')

    # RESCHEDULE MODE: Use get-rescheduler-slots API (works for already-scheduled projects)
    is_reschedule = params.get('is_reschedule', False)
    if isinstance(is_reschedule, str):
        is_reschedule = is_reschedule.lower() in ['true', '1', 'yes']

    # Track PF API HTTP status code
    pf_http_status_code = 200  # Default for mock/success

    if not all([project_id, selected_date]):
        raise ValueError("Missing required parameters: project_id, date")

    # ========================================================================
    # RESCHEDULE MODE: Use get-rescheduler-slots API directly
    # This API works for already-scheduled projects (slotsChatbot returns 400)
    # ========================================================================
    if is_reschedule and not USE_MOCK_API and client_id:
        logger.info(f"[get_time_slots] RESCHEDULE MODE: Using get-rescheduler-slots API for project {project_id}, date {selected_date}")

        # Rescheduler API endpoint - use selected_date for both date and selected_date to get slots for that specific day
        url = f"{config['scheduler_base_url']}/scheduler/client/{client_id}/project/{project_id}/date/{selected_date}/selected/{selected_date}/get-rescheduler-slots"
        logger.info(f"[get_time_slots] GET {url}")

        try:
            res = make_api_request_with_retry("GET", url, auth_headers, client_id=client_id, user_id=customer_id, timeout=30)
            pf_http_status_code = res.status_code
            response = res.json()
            data = response.get("data", {})
            raw_slots = data.get("slots", [])
            resched_request_id = data.get("request_id")
            logger.info(f"[get_time_slots] Rescheduler API returned {len(raw_slots)} slots, request_id={resched_request_id}")

            # Group time slots by time of day (same as regular flow)
            morning_slots = []
            afternoon_slots = []
            evening_slots = []
            for slot in raw_slots:
                try:
                    time_parts = slot.split(":")
                    hour = int(time_parts[0])
                    if 6 <= hour < 12:
                        morning_slots.append(slot)
                    elif 12 <= hour < 17:
                        afternoon_slots.append(slot)
                    elif 17 <= hour < 21:
                        evening_slots.append(slot)
                except:
                    afternoon_slots.append(slot)

            time_slots_grouped = {
                "morning": {"label": "Morning (6 AM - 12 PM)", "slots": morning_slots, "count": len(morning_slots)},
                "afternoon": {"label": "Afternoon (12 PM - 5 PM)", "slots": afternoon_slots, "count": len(afternoon_slots)},
                "evening": {"label": "Evening (5 PM - 9 PM)", "slots": evening_slots, "count": len(evening_slots)}
            }

            return {
                "action": "get_time_slots",
                "project_id": project_id,
                "date": selected_date,
                "available_slots": raw_slots,
                "timeSlots": raw_slots,
                "timeSlotsGrouped": time_slots_grouped,
                "slotCount": len(raw_slots),
                "request_id": resched_request_id,
                "is_reschedule": True,
                "mock_mode": USE_MOCK_API,
                "pf_http_status_code": pf_http_status_code
            }
        except requests.HTTPError as e:
            status_code = e.response.status_code
            pf_http_status_code = status_code
            error_body = e.response.text
            logger.error(f"[get_time_slots] Rescheduler API error HTTP {status_code}: {error_body}")
            if status_code == 400:
                raise ValueError(f"Invalid date or project: {error_body}")
            elif status_code == 404:
                raise ValueError("No time slots available for this date")
            elif status_code in [401, 403]:
                raise ValueError("SESSION_EXPIRED: Your session has expired. Please log out and log back in to continue.")
            else:
                raise ValueError(f"Failed to fetch time slots: HTTP {status_code}")
        except requests.RequestException as e:
            logger.error(f"[get_time_slots] Request error: {str(e)}")
            raise ValueError(f"Unable to connect to scheduling API: {str(e)}")

    # ========================================================================
    # REGULAR MODE: Use slotsChatbot API (for NEW scheduling)
    # ========================================================================
    # ALWAYS fetch fresh request_id to avoid stale request_id issues
    # This ensures direct slot queries work reliably
    if not USE_MOCK_API and client_id:
        old_request_id = request_id
        logger.info(f"[get_time_slots] Fetching fresh request_id for {selected_date} (old: {old_request_id})")
        try:
            # Call slotsChatbot to get fresh request_id
            prefetch_url = f"{config['scheduler_base_url']}/scheduler/client/{client_id}/project/{project_id}/startDate/{selected_date}/endDate/{selected_date}/slotsChatbot"
            logger.info(f"[get_time_slots] Prefetch GET {prefetch_url}")
            prefetch_res = make_api_request_with_retry("GET", prefetch_url, auth_headers, client_id=client_id, user_id=customer_id, timeout=30)
            prefetch_data = prefetch_res.json().get("data", {})
            request_id = prefetch_data.get("request_id")
            logger.info(f"[get_time_slots] Got fresh request_id: {request_id}")
        except Exception as e:
            logger.error(f"[get_time_slots] Failed to prefetch request_id: {e}")
            raise ValueError("Unable to fetch scheduling data. Please try again.")

    if not request_id:
        raise ValueError("Missing required parameter: request_id")

    # If base_date not provided, fall back to selected_date (less accurate but maintains backward compat)
    if not base_date:
        logger.warning(f"[get_time_slots] base_date not provided, falling back to selected_date: {selected_date}")
        base_date = selected_date

    # Resolve Order Number to internal ID if needed (scheduler API requires internal ID)
    if not str(project_id).isdigit() and not USE_MOCK_API and customer_id and client_id:
        logger.info(f"[get_time_slots] Project ID '{project_id}' appears to be an Order Number, resolving to internal ID...")
        try:
            url = f"{config['dashboard_url']}/{client_id}/{customer_id}"
            res = make_api_request_with_retry("GET", url, auth_headers, client_id=client_id, user_id=customer_id, timeout=30)
            raw_data = res.json().get("data", [])
            resolved_id = resolve_project_id(project_id, raw_data)
            if resolved_id:
                logger.info(f"Resolved Order Number '{project_id}' to internal ID '{resolved_id}'")
                project_id = resolved_id
            else:
                logger.warning(f"Could not resolve Order Number '{project_id}', proceeding with original value")
        except Exception as e:
            logger.warning(f"Failed to resolve Order Number '{project_id}': {e}, proceeding with original value")

    if USE_MOCK_API:
        logger.info(f"[MOCK] Fetching time slots for project {project_id} on {selected_date} (base: {base_date})")
        response = get_mock_time_slots(project_id, selected_date, request_id)
    else:
        # Validate client_id is present for real API calls
        if not client_id:
            raise ValueError("Missing required parameter for real API: client_id")

        logger.info(f"[REAL] Fetching time slots for client {client_id}, project {project_id}, selected: {selected_date}, base: {base_date}")

        # Construct URL with new slotsChatbot endpoint - use selected_date for both start and end (single day)
        url = f"{config['scheduler_base_url']}/scheduler/client/{client_id}/project/{project_id}/startDate/{selected_date}/endDate/{selected_date}/slotsChatbot?request_id={request_id}"

        logger.info(f"GET {url}")

        try:
            # Make API request with connection pooling
            res = make_api_request_with_retry("GET", url, auth_headers, client_id=client_id, user_id=customer_id, timeout=30)
            pf_http_status_code = res.status_code
            response = res.json()
            logger.info(f"Time slots retrieved successfully: {len(response.get('data', {}).get('slots', []))} slots")
        except requests.HTTPError as e:
            status_code = e.response.status_code
            pf_http_status_code = status_code
            error_body = e.response.text
            logger.error(f"HTTP {status_code} error fetching time slots: {error_body}")

            # Handle specific error codes
            if status_code == 400:
                raise ValueError(f"Invalid date or project: {error_body}")
            elif status_code == 404:
                raise ValueError("No time slots available for this date")
            elif status_code == 401:
                raise ValueError("SESSION_EXPIRED: Your session has expired. Please log out and log back in to continue.")
            elif status_code == 403:
                raise ValueError("SESSION_EXPIRED: Your session has expired. Please log out and log back in to continue.")
            else:
                raise ValueError(f"Failed to fetch time slots: HTTP {status_code}")
        except requests.RequestException as e:
            logger.error(f"Request error fetching time slots: {str(e)}")
            raise ValueError(f"Unable to connect to scheduling API: {str(e)}")

    data = response.get("data", {})
    raw_slots = data.get("slots", [])
    # Extract request_id from API response - this may be different from the input request_id
    new_request_id = data.get("request_id") or request_id
    logger.info(f"Time slots API returned request_id: {new_request_id} (input was: {request_id})")

    # ========================================================================
    # STALE DATE REFRESH: If selected date has 0 slots, re-fetch available dates
    # This handles the case where dates become unavailable between when user
    # first saw them and when they tried to select a time slot.
    # ========================================================================
    if len(raw_slots) == 0 and not USE_MOCK_API and client_id:
        logger.info(f"[STALE-REFRESH] Selected date {selected_date} has 0 slots - refreshing available dates")

        try:
            # Re-fetch available dates for next 14 days
            from datetime import timedelta
            refresh_start = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            refresh_end = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

            refresh_url = f"{config['scheduler_base_url']}/scheduler/client/{client_id}/project/{project_id}/startDate/{refresh_start}/endDate/{refresh_end}/slotsChatbot"
            logger.info(f"[STALE-REFRESH] GET {refresh_url}")

            refresh_res = make_api_request_with_retry("GET", refresh_url, auth_headers, client_id=client_id, user_id=customer_id, timeout=30)
            refresh_data = refresh_res.json().get("data", {})
            fresh_dates = sorted(refresh_data.get("dates", []))
            fresh_request_id = refresh_data.get("request_id")

            if fresh_dates:
                # Format fresh dates for display
                formatted_fresh_dates = []
                for date_str in fresh_dates[:5]:  # Limit to first 5 dates
                    try:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                        formatted_fresh_dates.append({
                            "date": date_str,
                            "displayDate": date_obj.strftime("%m/%d/%Y"),
                            "dayName": date_obj.strftime("%A"),
                            "dayShort": date_obj.strftime("%a"),
                            "monthDay": date_obj.strftime("%m/%d"),
                            "formatted": date_obj.strftime("%a %m/%d/%Y")
                        })
                    except:
                        formatted_fresh_dates.append({"date": date_str, "formatted": date_str})

                logger.info(f"[STALE-REFRESH] Found {len(fresh_dates)} fresh dates: {fresh_dates[:5]}")

                return {
                    "action": "get_time_slots",
                    "project_id": project_id,
                    "date": selected_date,
                    "available_slots": [],
                    "timeSlots": [],
                    "slotCount": 0,
                    "date_no_longer_available": True,
                    "message": f"Sorry, {selected_date} is no longer available. Here are the current available dates:",
                    "fresh_dates": fresh_dates[:5],
                    "fresh_dates_formatted": formatted_fresh_dates,
                    "fresh_date_count": len(fresh_dates),
                    "request_id": fresh_request_id,
                    "start_date": refresh_start,
                    "mock_mode": USE_MOCK_API,
                    "pf_http_status_code": pf_http_status_code
                }
            else:
                logger.info(f"[STALE-REFRESH] No dates available in next 14 days")
                return {
                    "action": "get_time_slots",
                    "project_id": project_id,
                    "date": selected_date,
                    "available_slots": [],
                    "timeSlots": [],
                    "slotCount": 0,
                    "date_no_longer_available": True,
                    "message": f"Sorry, {selected_date} is no longer available and there are no other dates available in the next 2 weeks. Please try again later or contact us for assistance.",
                    "fresh_dates": [],
                    "fresh_date_count": 0,
                    "mock_mode": USE_MOCK_API,
                    "pf_http_status_code": pf_http_status_code
                }

        except Exception as e:
            logger.warning(f"[STALE-REFRESH] Failed to refresh dates: {e}")
            # Fall through to return normal 0-slots response

    # Group time slots by time of day for better UI rendering
    morning_slots = []  # 6 AM - 11:59 AM
    afternoon_slots = []  # 12 PM - 4:59 PM
    evening_slots = []  # 5 PM - 8:59 PM

    for slot in raw_slots:
        try:
            # Parse time (format: "HH:MM" or "HH:MM:SS")
            time_parts = slot.split(":")
            hour = int(time_parts[0])

            if 6 <= hour < 12:
                morning_slots.append(slot)
            elif 12 <= hour < 17:
                afternoon_slots.append(slot)
            elif 17 <= hour < 21:
                evening_slots.append(slot)
        except:
            # Fallback: add to afternoon if parsing fails
            afternoon_slots.append(slot)

    # Format time slots for display
    time_slots_grouped = {
        "morning": {
            "label": "Morning (6 AM - 12 PM)",
            "slots": morning_slots,
            "count": len(morning_slots)
        },
        "afternoon": {
            "label": "Afternoon (12 PM - 5 PM)",
            "slots": afternoon_slots,
            "count": len(afternoon_slots)
        },
        "evening": {
            "label": "Evening (5 PM - 9 PM)",
            "slots": evening_slots,
            "count": len(evening_slots)
        }
    }

    return {
        "action": "get_time_slots",
        "project_id": project_id,
        "date": selected_date,
        "available_slots": raw_slots,  # Keep original for compatibility
        "timeSlots": raw_slots,  # Alias for UI compatibility
        "timeSlotsGrouped": time_slots_grouped,  # Grouped format for enhanced UI
        "slotCount": len(raw_slots),
        "request_id": new_request_id,  # IMPORTANT: Return the request_id for confirm_appointment
        "mock_mode": USE_MOCK_API,
        "pf_http_status_code": pf_http_status_code
    }

def handle_confirm_appointment(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: confirm_appointment
    Confirms/schedules an appointment for a project using TWO-STEP flow:

    Step 1 (Initial - no confirmed param):
        - Return appointment details for user to confirm
        - Status: "awaiting_confirmation"
        - DO NOT call the API yet

    Step 2 (User confirms - confirmed=True):
        - Actually call the API to confirm the appointment
        - Status: "confirmed"

    Real API Endpoint: POST /scheduler/client/{client_id}/project/{project_id}/schedule
    Request Body:
    {
        "created_at": "MM-DD-YYYY HH:MM:SS",
        "date": "YYYY-MM-DD",
        "time": "HH:MM:SS",
        "request_id": int
    }
    """
    project_id = params.get('project_id')
    date = params.get('date')
    time = params.get('time')
    request_id = params.get('request_id')
    client_id = params.get('client_id')  # Extract client_id from parameters
    customer_id = params.get('customer_id')
    category = params.get('category', '')  # Project category for confirmation message

    # Check if user has confirmed
    confirmed_raw = params.get('confirmed', False)
    confirmed = confirmed_raw in [True, 'True', 'true', '1']

    # Track PF API HTTP status code
    pf_http_status_code = 200  # Default for mock/success

    if not all([project_id, date, time]):
        raise ValueError("Missing required parameters: project_id, date, time")

    # STEP 1: If not confirmed, return details for user to confirm
    # request_id is only needed for Step 2 (actual API call), not for Step 1 (preview)
    if not confirmed:
        logger.info(f"[CONFIRM STEP 1] Returning appointment details for confirmation: project={project_id}, date={date}, time={time}")

        # Format date and time for display
        # NOTE: Using module-level datetime import (line 24), NOT local import
        # Local imports here caused "cannot access local variable 'datetime'" bug
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%B %d")  # e.g., "February 04"
            day_of_week = date_obj.strftime("%A")  # e.g., "Tuesday"
        except:
            formatted_date = date
            day_of_week = ""

        # Build confirmation message
        category_str = f" for your {category} project" if category else ""
        date_display = f"{day_of_week}, {formatted_date}" if day_of_week else formatted_date

        return {
            "action": "confirm_appointment",
            "status": "awaiting_confirmation",
            "project_id": project_id,
            "date": date,
            "time": time,
            "request_id": request_id,
            "formatted_date": formatted_date,
            "day_of_week": day_of_week,
            "category": category,
            "message": f"I have {date_display} at {time}{category_str}. Should I confirm this appointment?",
            "mock_mode": USE_MOCK_API
        }

    # STEP 2: User confirmed - proceed with actual API call
    # request_id is required for the actual scheduling API call
    if not request_id:
        raise ValueError("Missing request_id - cannot confirm appointment without a valid time slot request_id from get_available_dates")

    logger.info(f"[CONFIRM STEP 2] User confirmed - calling API to schedule: project={project_id}, date={date}, time={time}, request_id={request_id}")

    # Resolve Order Number to internal ID if needed (scheduler API requires internal ID)
    if not str(project_id).isdigit() and not USE_MOCK_API and customer_id and client_id:
        logger.info(f"[confirm_appointment] Project ID '{project_id}' appears to be an Order Number, resolving to internal ID...")
        try:
            url = f"{config['dashboard_url']}/{client_id}/{customer_id}"
            res = make_api_request_with_retry("GET", url, auth_headers, client_id=client_id, user_id=customer_id, timeout=30)
            raw_data = res.json().get("data", [])
            resolved_id = resolve_project_id(project_id, raw_data)
            if resolved_id:
                logger.info(f"Resolved Order Number '{project_id}' to internal ID '{resolved_id}'")
                project_id = resolved_id
            else:
                logger.warning(f"Could not resolve Order Number '{project_id}', proceeding with original value")
        except Exception as e:
            logger.warning(f"Failed to resolve Order Number '{project_id}': {e}, proceeding with original value")

    # Use mock if global flag is set OR if real confirm is not enabled
    use_mock = USE_MOCK_API or not ENABLE_REAL_CONFIRM

    if use_mock:
        logger.info(f"[MOCK] Confirming appointment for project {project_id} on {date} at {time}")
        response = get_mock_confirm_appointment(project_id, date, time, request_id)
    else:
        # Validate client_id is present for real API calls
        if not client_id:
            raise ValueError("Missing required parameter for real API: client_id")

        logger.info(f"[REAL] Confirming appointment for client {client_id}, project {project_id} on {date} at {time}")

        # Construct URL matching HAR file format: /scheduler/client/{client_id}/project/{project_id}/schedule
        url = f"{config['scheduler_base_url']}/scheduler/client/{client_id}/project/{project_id}/schedule"

        # Convert time from 12-hour AM/PM format to 24-hour format if needed
        # Examples: "8:00 AM" -> "08:00:00", "1:00 PM" -> "13:00:00", "8:00" -> "08:00:00"
        import re
        time_match = re.match(r'(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(AM|PM)?', time.strip(), re.IGNORECASE)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            second = int(time_match.group(3)) if time_match.group(3) else 0
            am_pm = time_match.group(4)

            # Convert to 24-hour format if AM/PM is present
            if am_pm:
                am_pm = am_pm.upper()
                if am_pm == 'PM' and hour != 12:
                    hour += 12
                elif am_pm == 'AM' and hour == 12:
                    hour = 0

            time = f"{hour:02d}:{minute:02d}:{second:02d}"
            logger.info(f"Converted time to 24-hour format: {time}")
        elif len(time.split(':')) == 2:
            time = f"{time}:00"  # Add seconds if missing

        payload = {
            "created_at": datetime.now().strftime("%m/%d/%Y %H:%M:%S"),
            "date": date,
            "time": time,
            "request_id": int(request_id),  # Ensure request_id is integer
        }

        logger.info(f"POST {url}")
        logger.info(f"Payload: {json.dumps(payload)}")

        try:
            # Make API request with connection pooling
            res = make_api_request_with_retry("POST", url, auth_headers, client_id=client_id, user_id=customer_id, json=payload, timeout=30)
            pf_http_status_code = res.status_code
            response = res.json()
            logger.info(f"Confirmation successful: {response}")
        except requests.HTTPError as e:
            status_code = e.response.status_code
            pf_http_status_code = status_code
            error_body = e.response.text
            logger.error(f"HTTP {status_code} error confirming appointment: {error_body}")

            # Handle specific error codes
            if status_code == 400:
                raise ValueError(f"Invalid appointment details: {error_body}")
            elif status_code == 409:
                raise ValueError("Time slot already booked or conflict detected")
            elif status_code == 401:
                raise ValueError("Authentication failed - token may be expired (after retry)")
            else:
                raise ValueError(f"Failed to confirm appointment: HTTP {status_code}")
        except requests.RequestException as e:
            logger.error(f"Request error confirming appointment: {str(e)}")
            raise ValueError(f"Unable to connect to scheduling API: {str(e)}")

    # Format date and time for better UI display
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%a %m/%d/%Y")  # Mon 01/15/2026
        day_of_week = date_obj.strftime("%A")
    except:
        formatted_date = date
        day_of_week = ""

    # Format time (convert 24h to 12h with AM/PM)
    try:
        time_parts = time.split(":")
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        am_pm = "AM" if hour < 12 else "PM"
        display_hour = hour if hour <= 12 else hour - 12
        display_hour = 12 if display_hour == 0 else display_hour
        formatted_time = f"{display_hour}:{minute:02d} {am_pm}"
    except:
        formatted_time = time

    # Extract additional data from API response
    # API may return data as True (boolean) or a dict with details
    confirmation_details = response.get("data", {})
    if not isinstance(confirmation_details, dict):
        confirmation_details = {}  # Handle case where data is True/False/None

    # Build enhanced appointment object
    appointment = {
        "projectId": project_id,
        "date": date,
        "time": time,
        "formattedDate": formatted_date,
        "formattedTime": formatted_time,
        "dayOfWeek": day_of_week,
        "confirmationNumber": confirmation_details.get("confirmation_number", f"CONF-{project_id}-{date.replace('-', '')}"),
        "status": "confirmed"
    }

    return {
        "action": "confirm_appointment",
        "status": "confirmed",
        "project_id": project_id,
        "scheduled_date": date,
        "scheduled_time": time,
        "message": response.get("message", "Appointment confirmed successfully. We will send you a confirmation to your registered email and phone number."),
        "appointment": appointment,  # Enhanced appointment object for UI
        "confirmation_data": confirmation_details,
        "mock_mode": use_mock,
        "pf_http_status_code": pf_http_status_code
    }

def handle_reschedule_appointment(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: reschedule_appointment
    Reschedules an existing appointment using a THREE-STEP interactive flow:

    Step 1 (Initial request - no confirmed param):
        - Ask user to confirm they want to reschedule (DO NOT cancel yet!)
        - Return status "awaiting_reschedule_confirm" to get user consent

    Step 2 (User confirms - confirmed=True):
        - Cancel existing appointment via cancel-reschedule endpoint
        - Immediately fetch available dates
        - Return status "awaiting_date_selection" with dates

    Step 3 (User selects date/time):
        - Confirm new appointment with the new date/time

    Required Parameters: project_id, client_id
    Optional Parameters:
        - confirmed: True to proceed with cancel+fetch dates (Step 2)
        - new_date, new_time, request_id: For confirming appointment (Step 3)
    """
    project_id = params.get('project_id')
    client_id = params.get('client_id')
    customer_id = params.get('customer_id')
    new_date = params.get('new_date')
    new_time = params.get('new_time')
    request_id = params.get('request_id')
    user_message = params.get('message', '').lower()  # User's original message for intent detection

    # confirmed comes as string "True" from Lambda event params
    confirmed_raw = params.get('confirmed', False)
    confirmed = confirmed_raw in [True, 'True', 'true', '1']
    # Legacy support: fetch_dates also triggers confirmed flow
    fetch_dates_raw = params.get('fetch_dates', False)
    fetch_dates = fetch_dates_raw in [True, 'True', 'true', '1']
    if fetch_dates:
        confirmed = True

    # SMART INTENT DETECTION: If user's message clearly indicates reschedule intent,
    # skip confirmation step and go straight to fetching dates.
    # This prevents the annoying "Would you like to reschedule?" when user already said "reschedule"
    reschedule_intent_words = ['reschedule', 'change date', 'change time', 'change the date',
                               'change the time', 'move appointment', 'move the appointment',
                               'different date', 'different time', 'new date', 'new time',
                               'change my appointment', 'move my appointment']
    if not confirmed and user_message:
        for intent_word in reschedule_intent_words:
            if intent_word in user_message:
                logger.info(f"[RESCHEDULE] Auto-confirming based on user intent: '{intent_word}' found in message")
                confirmed = True
                break

    if not project_id:
        raise ValueError("Missing required parameter: project_id")

    logger.info(f"Rescheduling appointment for project {project_id}, confirmed={confirmed}, message='{user_message[:50]}...'" if len(user_message) > 50 else f"Rescheduling appointment for project {project_id}, confirmed={confirmed}, message='{user_message}'")

    # STEP 2: If confirmed=True, user consented - fetch dates FIRST, then cancel only if dates available
    if confirmed and not new_date:
        logger.info(f"[RESCHEDULE STEP 2] User confirmed - checking available dates BEFORE cancelling for project {project_id}")

        # First, check current project status
        current_scheduled_date = None
        is_currently_scheduled = False
        try:
            project_info = handle_get_project_details(
                {'project_id': project_id, 'client_id': client_id, 'customer_id': customer_id},
                config, auth_headers
            )
            project = project_info.get('project', {})
            current_status = project.get('status', '').lower()
            current_scheduled_date = project.get('scheduledDate', '')

            # Determine if project is currently scheduled
            scheduled_statuses = ['scheduled', 'customer scheduled', 'tentatively scheduled']
            is_currently_scheduled = current_status in scheduled_statuses or bool(current_scheduled_date)
            logger.info(f"[RESCHEDULE] Project status: {current_status}, scheduledDate: {current_scheduled_date}, is_scheduled: {is_currently_scheduled}")
        except Exception as e:
            logger.warning(f"[RESCHEDULE] Could not fetch project status: {e}")

        # CRITICAL: Fetch available dates FIRST (before cancelling)
        # Use rescheduler API which can get dates even for scheduled projects
        try:
            # Calculate date range for rescheduler search (today + 12 days)
            from datetime import datetime, timedelta
            today = datetime.now().strftime('%Y-%m-%d')
            end_date = (datetime.now() + timedelta(days=12)).strftime('%Y-%m-%d')

            dates_result = handle_get_rescheduler_slots(
                {
                    'project_id': project_id,
                    'client_id': client_id,
                    'customer_id': customer_id,
                    'date': today,  # Start date of search range
                    'selected_date': end_date  # End date of search range (12 days out)
                },
                config,
                auth_headers
            )
            logger.info(f"Rescheduler dates result: {dates_result}")

            available_dates = dates_result.get('available_dates', [])
            available_dates_sorted = sorted(available_dates) if available_dates else []

        except Exception as e:
            logger.warning(f"[RESCHEDULE] Rescheduler API failed, trying regular dates: {e}")
            # Fallback: If rescheduler fails, try regular get_available_dates
            # This may fail for scheduled projects, but worth trying
            try:
                dates_result = handle_get_available_dates(
                    {'project_id': project_id, 'client_id': client_id},
                    config, auth_headers
                )
                available_dates = dates_result.get('available_dates', [])
                available_dates_sorted = sorted(available_dates) if available_dates else []
            except Exception as e2:
                logger.error(f"[RESCHEDULE] Both date APIs failed: {e2}")
                available_dates_sorted = []
                dates_result = {'dates': [], 'available_dates': []}

        # DECISION POINT: Only cancel if we have alternative dates
        if not available_dates_sorted:
            # NO DATES AVAILABLE - DO NOT CANCEL, keep existing appointment
            logger.info(f"[RESCHEDULE] No alternative dates - keeping existing appointment")

            if current_scheduled_date:
                message = f"No alternative dates are available right now. Your current appointment on {current_scheduled_date} remains unchanged. Would you like me to check again later, or would you prefer our office number?"
            else:
                message = "No alternative dates are available right now. Would you like me to check again in a few days, or would you prefer to call our office?"

            return {
                "action": "reschedule_appointment",
                "project_id": project_id,
                "status": "no_dates_available",
                "available_dates": [],
                "dates": [],
                "dateCount": 0,
                "current_appointment_kept": True,
                "current_scheduled_date": current_scheduled_date,
                "message": message,
                "mock_mode": USE_MOCK_API
            }

        # DATES AVAILABLE - Now safe to cancel existing appointment
        if is_currently_scheduled:
            logger.info(f"[RESCHEDULE] Dates available ({len(available_dates_sorted)}) - now cancelling existing appointment")
            try:
                cancel_result = handle_cancel_appointment(
                    {
                        'project_id': project_id,
                        'client_id': client_id,
                        'customer_id': customer_id,
                        'confirmed': True
                    },
                    config,
                    auth_headers
                )
                logger.info(f"Cancel result: {cancel_result}")

                if cancel_result.get('status') in ['cannot_cancel', 'error']:
                    error_msg = cancel_result.get('message') or cancel_result.get('error', '')
                    # If it's just a status issue, proceed anyway (project may already be unscheduled)
                    if not ('status' in error_msg.lower() or 'not scheduled' in error_msg.lower()):
                        return {
                            "action": "reschedule_appointment",
                            "project_id": project_id,
                            "status": "cannot_reschedule",
                            "message": error_msg or 'Cannot reschedule this project',
                            "mock_mode": USE_MOCK_API
                        }
            except Exception as e:
                error_str = str(e)
                # Only fail if it's not a status-related error
                if not ('status' in error_str.lower() or 'not scheduled' in error_str.lower()):
                    logger.error(f"Cancel failed: {error_str}")
                    return {
                        "action": "reschedule_appointment",
                        "project_id": project_id,
                        "status": "error",
                        "message": f"Failed to cancel existing appointment: {error_str}",
                        "mock_mode": USE_MOCK_API
                    }
        else:
            logger.info(f"[RESCHEDULE] Project not currently scheduled - skipping cancel step")

        # Return available dates
        formatted_dates = dates_result.get('dates', [])
        formatted_dates_sorted = sorted(formatted_dates, key=lambda x: x.get('date', '')) if formatted_dates else []

        return {
            "action": "reschedule_appointment",
            "project_id": project_id,
            "status": "awaiting_date_selection",
            "available_dates": available_dates_sorted,
            "dates": formatted_dates_sorted,
            "dateCount": len(available_dates_sorted),
            "request_id": dates_result.get('request_id'),
            "start_date": dates_result.get('start_date'),
            "message": "Here are the available dates for rescheduling. Please select a date.",
            "mock_mode": USE_MOCK_API
        }

    # STEP 3: If date/time provided, confirm the new appointment
    if new_date:
        if not new_time:
            raise ValueError("Missing required parameter: new_time")
        if not request_id:
            raise ValueError("Missing required parameter: request_id")

        confirm_result = handle_confirm_appointment(
            {
                'project_id': project_id,
                'client_id': client_id,
                'date': new_date,
                'time': new_time,
                'request_id': request_id
            },
            config,
            auth_headers
        )

        return {
            "action": "reschedule_appointment",
            "project_id": project_id,
            "status": "rescheduled",
            "scheduled_date": new_date,
            "scheduled_time": new_time,
            "message": "Your appointment has been successfully rescheduled!",
            "appointment": confirm_result.get('appointment', {}),
            "mock_mode": USE_MOCK_API
        }

    # STEP 1: Initial reschedule request - ASK for confirmation (DO NOT cancel yet!)
    logger.info(f"[RESCHEDULE STEP 1] Asking user to confirm reschedule for project {project_id}")

    # Return confirmation prompt - DO NOT cancel until user confirms
    return {
        "action": "reschedule_appointment",
        "project_id": project_id,
        "status": "awaiting_reschedule_confirm",
        "message": "This project already has a scheduled appointment. Would you like to reschedule it? Say 'yes' to proceed or 'no' to keep the current appointment.",
        "mock_mode": USE_MOCK_API
    }


def handle_cancel_appointment(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: cancel_appointment
    Cancels/initiates reschedule for a scheduled appointment

    Real API Endpoint: GET /scheduler/client/{client_id}/project/{project_id}/cancel-reschedule
    Required Parameters: project_id, client_id
    Optional Parameters: confirmed (bool) - if True, skip validation and proceed with cancel

    TWO-STEP FLOW:
    1. If confirmed=False: Fetch project details from API, validate status, return project info for confirmation
    2. If confirmed=True: Proceed with actual cancellation

    Response indicates if project can be cancelled based on its status.
    Project status must be "Customer Scheduled" or "Scheduled" to allow cancellation.
    """
    project_id = params.get('project_id')
    client_id = params.get('client_id')
    customer_id = params.get('customer_id')
    confirmed = params.get('confirmed', False)
    # Handle string 'true'/'false' from params
    if isinstance(confirmed, str):
        confirmed = confirmed.lower() == 'true'

    if not project_id:
        raise ValueError("Missing required parameter: project_id")

    # Resolve Order Number to internal ID if needed (scheduler API requires internal ID)
    if not str(project_id).isdigit() and not USE_MOCK_API and customer_id and client_id:
        logger.info(f"[cancel_appointment] Project ID '{project_id}' appears to be an Order Number, resolving to internal ID...")
        try:
            url = f"{config['dashboard_url']}/{client_id}/{customer_id}"
            res = make_api_request_with_retry("GET", url, auth_headers, client_id=client_id, user_id=customer_id, timeout=30)
            raw_data = res.json().get("data", [])
            resolved_id = resolve_project_id(project_id, raw_data)
            if resolved_id:
                logger.info(f"Resolved Order Number '{project_id}' to internal ID '{resolved_id}'")
                project_id = resolved_id
            else:
                logger.warning(f"Could not resolve Order Number '{project_id}', proceeding with original value")
        except Exception as e:
            logger.warning(f"Failed to resolve Order Number '{project_id}': {e}, proceeding with original value")

    # STEP 1: Pre-flight validation - fetch project details to validate before cancel
    if not confirmed:
        logger.info(f"[CANCEL] Step 1: Validating project {project_id} before cancellation")
        try:
            # Fetch project details to validate
            project_info = handle_get_project_details(
                {'project_id': project_id, 'client_id': client_id, 'customer_id': customer_id},
                config, auth_headers
            )
            project = project_info.get('project', {})
            status = project.get('status', '')
            scheduled_date = project.get('scheduledDate', '')
            category = project.get('category', '')
            project_type = project.get('projectType', '')

            logger.info(f"[CANCEL] Project {project_id} status: {status}, scheduled: {scheduled_date}")

            # Check if project can be cancelled (must be scheduled)
            cancelable_statuses = ['Customer Scheduled', 'Scheduled', 'Customer to Schedule']
            if status and status not in cancelable_statuses:
                return {
                    "action": "cancel_appointment",
                    "project_id": project_id,
                    "status": "cannot_cancel",
                    "message": f"Project #{project_id} is in '{status}' status and cannot be cancelled. Only scheduled appointments can be cancelled.",
                    "project": project,
                    "mock_mode": USE_MOCK_API
                }

            # Check if there's actually a scheduled date
            if not scheduled_date:
                return {
                    "action": "cancel_appointment",
                    "project_id": project_id,
                    "status": "not_scheduled",
                    "message": f"Project #{project_id} ({category} - {project_type}) doesn't have a scheduled appointment to cancel.",
                    "project": project,
                    "mock_mode": USE_MOCK_API
                }

            # Return project details for confirmation
            return {
                "action": "cancel_appointment",
                "project_id": project_id,
                "status": "awaiting_confirmation",
                "message": f"Found project #{project_id} ({category} - {project_type}) scheduled for {scheduled_date}. Please confirm you want to cancel this appointment.",
                "project": project,
                "requires_confirmation": True,
                "mock_mode": USE_MOCK_API
            }

        except Exception as e:
            logger.error(f"[CANCEL] Failed to validate project {project_id}: {str(e)}")
            return {
                "action": "cancel_appointment",
                "project_id": project_id,
                "status": "error",
                "error": f"Could not find project {project_id}: {str(e)}",
                "mock_mode": USE_MOCK_API
            }

    # STEP 2: Confirmed - proceed with actual cancellation
    logger.info(f"[CANCEL] Step 2: User confirmed, proceeding with cancellation for project {project_id}")

    if USE_MOCK_API:
        logger.info(f"[MOCK] Cancelling appointment for project {project_id}")
        response = get_mock_cancel_appointment(project_id)
    else:
        # Validate client_id for real API calls
        if not client_id:
            raise ValueError("Missing required parameter for real API: client_id")

        logger.info(f"[REAL] Cancelling appointment for project {project_id}, client {client_id}")

        # API endpoint from documentation
        url = f"{config['scheduler_base_url']}/scheduler/client/{client_id}/project/{project_id}/cancel-reschedule"

        logger.info(f"GET {url}")

        try:
            # Make API request with connection pooling
            # NOTE: API uses GET method (not POST) for cancel-reschedule
            res = make_api_request_with_retry("GET", url, auth_headers, timeout=30)
            response = res.json()
            logger.info(f"Cancel/Reschedule API response: {response}")
        except requests.HTTPError as e:
            status_code = e.response.status_code
            error_body = e.response.text
            logger.error(f"HTTP {status_code} error canceling appointment: {error_body}")

            # Handle specific error codes
            if status_code == 400:
                raise ValueError(f"Invalid cancellation request: {error_body}")
            elif status_code == 404:
                raise ValueError("No appointment found to cancel")
            elif status_code == 401:
                raise ValueError("Authentication failed - token may be expired (after retry)")
            else:
                raise ValueError(f"Failed to cancel appointment: HTTP {status_code}")
        except requests.RequestException as e:
            logger.error(f"Request error canceling appointment: {str(e)}")
            raise ValueError(f"Unable to connect to scheduling API: {str(e)}")

    # Handle the "Project status should be Customer to Schedule" response
    message = response.get("message", "")
    if "Project status should be" in message:
        return {
            "action": "cancel_appointment",
            "project_id": project_id,
            "status": "cannot_cancel",
            "message": f"This project cannot be cancelled. {message}",
            "mock_mode": USE_MOCK_API
        }

    return {
        "action": "cancel_appointment",
        "project_id": project_id,
        "status": "success",
        "message": response.get("message", "Appointment cancelled successfully"),
        "cancellation_data": response.get("data", {}),
        "mock_mode": USE_MOCK_API
    }

# ============================================================================
# Rescheduler Slots Action Handler
# ============================================================================

def handle_get_rescheduler_slots(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: get_rescheduler_slots
    Gets available slots specifically for rescheduling a project

    Real API Endpoint: GET /scheduler/client/{client_id}/project/{project_id}/date/{date}/selected/{selected_date}/get-rescheduler-slots

    Required Parameters: project_id, client_id, date
    Optional Parameters: selected_date (defaults to date)

    Response format:
    {
        "data": {
            "slots": [],
            "dates": ["2025-10-29", "2025-10-30", "2025-10-31"],
            "request_id": 1619
        },
        "message": "Slots fetched successfully"
    }
    """
    project_id = params.get('project_id')
    client_id = params.get('client_id')
    customer_id = params.get('customer_id')
    date = params.get('date')  # Format: YYYY-MM-DD
    selected_date = params.get('selected_date', date)  # Defaults to date

    if not project_id:
        raise ValueError("Missing required parameter: project_id")
    if not date:
        raise ValueError("Missing required parameter: date")

    # Resolve Order Number to internal ID if needed (scheduler API requires internal ID)
    if not str(project_id).isdigit() and not USE_MOCK_API and customer_id and client_id:
        logger.info(f"[get_rescheduler_slots] Project ID '{project_id}' appears to be an Order Number, resolving to internal ID...")
        try:
            url = f"{config['dashboard_url']}/{client_id}/{customer_id}"
            res = make_api_request_with_retry("GET", url, auth_headers, client_id=client_id, user_id=customer_id, timeout=30)
            raw_data = res.json().get("data", [])
            resolved_id = resolve_project_id(project_id, raw_data)
            if resolved_id:
                logger.info(f"Resolved Order Number '{project_id}' to internal ID '{resolved_id}'")
                project_id = resolved_id
            else:
                logger.warning(f"Could not resolve Order Number '{project_id}', proceeding with original value")
        except Exception as e:
            logger.warning(f"Failed to resolve Order Number '{project_id}': {e}, proceeding with original value")

    if USE_MOCK_API:
        logger.info(f"[MOCK] Getting rescheduler slots for project {project_id}, date {date}")
        response = get_mock_rescheduler_slots(project_id, date)
    else:
        if not client_id:
            raise ValueError("Missing required parameter for real API: client_id")

        logger.info(f"[REAL] Getting rescheduler slots for project {project_id}, date {date}")

        # API endpoint from documentation
        url = f"{config['scheduler_base_url']}/scheduler/client/{client_id}/project/{project_id}/date/{date}/selected/{selected_date}/get-rescheduler-slots"

        logger.info(f"GET {url}")

        try:
            # Use shorter timeout (15s) to allow error handling before Lambda times out
            res = make_api_request_with_retry("GET", url, auth_headers, timeout=(5, 15))
            response = res.json()
            logger.info(f"Rescheduler slots response: {response}")
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout getting rescheduler slots: {str(e)}")
            # Return a user-friendly response instead of raising
            return {
                "action": "get_rescheduler_slots",
                "project_id": project_id,
                "status": "timeout",
                "message": "The rescheduling service is taking too long to respond. This may happen if the project was just scheduled. Please try again in a few minutes.",
                "slots": [],
                "available_dates": [],
                "mock_mode": USE_MOCK_API
            }
        except requests.HTTPError as e:
            status_code = e.response.status_code
            error_body = e.response.text
            logger.error(f"HTTP {status_code} error getting rescheduler slots: {error_body}")

            if status_code == 400:
                raise ValueError(f"Invalid request: {error_body}")
            elif status_code == 404:
                raise ValueError("Project not found")
            elif status_code == 401:
                raise ValueError("Authentication failed - token may be expired")
            else:
                raise ValueError(f"Failed to get rescheduler slots: HTTP {status_code}")
        except requests.RequestException as e:
            logger.error(f"Request error getting rescheduler slots: {str(e)}")
            raise ValueError(f"Unable to connect to scheduling API: {str(e)}")

    # Handle status constraint message (same as cancel)
    message = response.get("message", "")
    if "Project status should be" in message:
        return {
            "action": "get_rescheduler_slots",
            "project_id": project_id,
            "status": "cannot_reschedule",
            "message": f"Cannot get reschedule slots. {message}",
            "slots": [],
            "available_dates": [],
            "mock_mode": USE_MOCK_API
        }

    # Extract data from response
    data = response.get("data", {})
    slots = data.get("slots", [])
    available_dates = data.get("dates", [])
    request_id = data.get("request_id")

    return {
        "action": "get_rescheduler_slots",
        "project_id": project_id,
        "date": date,
        "slots": slots,
        "available_dates": available_dates,
        "request_id": request_id,
        "message": response.get("message", "Rescheduler slots fetched successfully"),
        "mock_mode": USE_MOCK_API
    }


# ============================================================================
# Business Hours Action Handler
# ============================================================================

def handle_get_business_hours(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: get_business_hours
    Returns business working hours for scheduling

    Real API Endpoint: GET /scheduler/client/{client_id}/business-hours

    Required Parameters: client_id
    """
    client_id = params.get('client_id')
    customer_id = params.get('customer_id')

    if not client_id:
        raise ValueError("Missing required parameter: client_id")

    if USE_MOCK_API:
        logger.info(f"[MOCK] Fetching business hours for client {client_id}")
        response = get_mock_business_hours(client_id)
    else:
        logger.info(f"[REAL] Fetching business hours for client {client_id}")

        # Construct URL matching real portal API
        url = f"{config['scheduler_base_url']}/scheduler/client/{client_id}/business-hours"

        logger.info(f"GET {url}")

        try:
            # Make API request with connection pooling
            res = make_api_request_with_retry("GET", url, auth_headers, client_id=client_id, user_id=customer_id, timeout=30)
            response = res.json()
            logger.info(f"Business hours retrieved successfully")
        except requests.HTTPError as e:
            status_code = e.response.status_code
            error_body = e.response.text
            logger.error(f"HTTP {status_code} error fetching business hours: {error_body}")

            # Handle specific error codes
            if status_code == 404:
                raise ValueError("Business hours not configured for this client")
            elif status_code == 401:
                raise ValueError("Authentication failed - token may be expired (after retry)")
            else:
                raise ValueError(f"Failed to fetch business hours: HTTP {status_code}")
        except requests.RequestException as e:
            logger.error(f"Request error fetching business hours: {str(e)}")
            raise ValueError(f"Unable to connect to scheduling API: {str(e)}")

    data = response.get("data", {})
    work_hours = data.get("workHours", [])

    # Format for better UI display
    working_days = []
    non_working_days = []

    for day_info in work_hours:
        if day_info.get("is_working"):
            working_days.append({
                "day": day_info.get("day"),
                "start": day_info.get("start"),
                "end": day_info.get("end")
            })
        else:
            non_working_days.append(day_info.get("day"))

    return {
        "action": "get_business_hours",
        "client_id": client_id,
        "work_hours": work_hours,
        "working_days": working_days,
        "non_working_days": non_working_days,
        "working_days_count": len(working_days),
        "mock_mode": USE_MOCK_API
    }

# ============================================================================
# Notes Action Handlers
# ============================================================================

def store_note_in_dynamodb(table_name: str, project_id: str, note_text: str, author: str) -> Dict[str, Any]:
    """Store note in DynamoDB"""
    table = dynamodb.Table(table_name)

    note = {
        'project_id': project_id,
        'timestamp': datetime.now().isoformat(),
        'note_text': note_text,
        'author': author,
        'created_at': datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    }

    table.put_item(Item=note)
    return note

def get_notes_from_dynamodb(table_name: str, project_id: str) -> List[Dict[str, Any]]:
    """Retrieve notes from DynamoDB"""
    table = dynamodb.Table(table_name)

    try:
        response = table.query(
            KeyConditionExpression='project_id = :pid',
            ExpressionAttributeValues={
                ':pid': project_id
            },
            ScanIndexForward=False  # Sort by timestamp descending
        )
        return response.get('Items', [])
    except ClientError as e:
        logger.error(f"DynamoDB query failed: {str(e)}")
        return []

def handle_add_note(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: add_note
    Add a note to a project

    Notes are stored in DynamoDB for quick retrieval.
    Optionally can also call PF360 API if add_note endpoint exists.
    """
    project_id = params.get('project_id')
    note_text = params.get('note_text')
    author = params.get('author', 'Customer')  # Default to Customer since notes come from customer chat

    if not all([project_id, note_text]):
        raise ValueError("Missing required parameters: project_id, note_text")

    logger.info(f"Adding note to project {project_id} from author {author}")

    # Get DynamoDB table name from config (with dynamic default from config module)
    dynamodb_table = config.get('dynamodb_notes_table', DYNAMODB_NOTES_TABLE)

    try:
        # Store in DynamoDB
        note = store_note_in_dynamodb(dynamodb_table, project_id, note_text, author)

        return {
            "action": "add_note",
            "project_id": project_id,
            "note_text": note_text,
            "author": author,
            "message": f"Note added successfully to project {project_id}",
            "note_data": note
        }
    except ClientError as e:
        logger.error(f"Failed to add note to DynamoDB: {str(e)}")
        raise ValueError(f"Failed to save note: {str(e)}")

def handle_list_notes(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: list_notes
    List all notes for a project

    Notes are retrieved from DynamoDB.
    """
    project_id = params.get('project_id')

    if not project_id:
        raise ValueError("Missing required parameter: project_id")

    logger.info(f"Listing notes for project {project_id}")

    # Get DynamoDB table name from config (with dynamic default from config module)
    dynamodb_table = config.get('dynamodb_notes_table', DYNAMODB_NOTES_TABLE)

    try:
        # Get notes from DynamoDB
        notes = get_notes_from_dynamodb(dynamodb_table, project_id)

        return {
            "action": "list_notes",
            "project_id": project_id,
            "notes": notes,
            "total_count": len(notes),
            "source": "dynamodb"
        }
    except ClientError as e:
        logger.error(f"Failed to retrieve notes from DynamoDB: {str(e)}")
        raise ValueError(f"Failed to retrieve notes: {str(e)}")

# ============================================================================
# Lambda Handler
# ============================================================================

def lambda_handler(event, context):
    """
    Main Lambda handler for scheduling actions
    Routes to appropriate action handler based on apiPath
    """
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # Extract action from event
        # Function calling format uses 'function', OpenAPI format uses 'apiPath'
        action = event.get('function', event.get('apiPath', '')).lstrip('/')
        if not action:
            # Fallback: check for action in parameters
            params = extract_parameters(event)
            action = params.get('action', '')

        # Normalize action name: convert underscores to hyphens for handler matching
        action = action.replace('_', '-')

        if not action:
            return format_error_response(
                event,
                'unknown',
                'No action specified in event',
                400
            )

        logger.info(f"Processing action: {action}")

        # Extract parameters
        params = extract_parameters(event)

        # Extract session attributes (passed from Bedrock Agent)
        session_attributes = event.get('sessionAttributes', {})
        logger.info(f"Session attributes: {session_attributes}")

        # Get ProjectForce token from session attributes
        pf_bearer_token = session_attributes.get('pf_bearer_token', '')
        pf_api_base = session_attributes.get('pf_api_base', '')
        customer_id = session_attributes.get('customer_id', params.get('customer_id', ''))
        client_id = session_attributes.get('client_id', params.get('client_id', 'default'))

        # Add customer_id and client_id to params if not already present
        if customer_id and 'customer_id' not in params:
            params['customer_id'] = customer_id
        if client_id and 'client_id' not in params:
            params['client_id'] = client_id

        # Add from_phone for voice channel cache lookup
        from_phone = session_attributes.get('from_phone', '')
        if from_phone:
            params['_from_phone'] = from_phone
            logger.info(f"[VOICE] Detected voice channel, phone: ***{from_phone[-4:]}")

        # Get configuration
        config = get_api_config(client_id)

        # Override base URL if provided in session attributes
        if pf_api_base:
            config['base_url'] = pf_api_base
            config['dashboard_url'] = f"{pf_api_base}/dashboard/get"  # OLD Portal API format
            config['scheduler_url'] = f"{pf_api_base}/system/client-details"
            logger.info(f"Using ProjectForce API base: {pf_api_base}")

        # Get auth headers (if not using mock)
        auth_headers = {}
        if not USE_MOCK_API:
            # Use token from session attributes if available and not a placeholder
            # If it's PLACEHOLDER_TOKEN, let TokenManager retrieve the real token from Secrets Manager
            authorization = None
            if pf_bearer_token and pf_bearer_token != 'PLACEHOLDER_TOKEN':
                authorization = pf_bearer_token
                logger.info("Using ProjectForce Bearer token from session attributes")
            elif not pf_bearer_token:
                # Try params or event
                authorization = params.get('authorization', event.get('authorization', ''))
                if authorization:
                    logger.info("Using authorization from params/event")

            # If no valid token provided, get_auth_headers will use TokenManager
            if not authorization:
                logger.info("No valid token in session, will use TokenManager/Secrets Manager")

            auth_headers = get_auth_headers(authorization, client_id)

        # Route to appropriate handler
        handlers = {
            'list-projects': handle_list_projects,
            'get-project-details': handle_get_project_details,
            'get-business-hours': handle_get_business_hours,
            'get-available-dates': handle_get_available_dates,
            'get-time-slots': handle_get_time_slots,
            'confirm-appointment': handle_confirm_appointment,
            'reschedule-appointment': handle_reschedule_appointment,
            'cancel-appointment': handle_cancel_appointment,
            'get-rescheduler-slots': handle_get_rescheduler_slots,
            'add-note': handle_add_note,
            'list-notes': handle_list_notes
        }

        handler = handlers.get(action)
        if not handler:
            return format_error_response(
                event,
                action,
                f'Unknown action: {action}',
                400
            )

        # Execute handler
        result = handler(params, config, auth_headers)

        # Return formatted response
        return format_success_response(event, action, result)

    except ValueError as e:
        error_msg = str(e)
        logger.error(f"Validation error: {error_msg}")

        # Return 401 for session expired errors (not 400)
        if 'SESSION_EXPIRED' in error_msg:
            status_code = 401
        else:
            status_code = 400

        return format_error_response(
            event,
            action if 'action' in locals() else 'unknown',
            error_msg,
            status_code
        )

    except requests.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        return format_error_response(
            event,
            action if 'action' in locals() else 'unknown',
            f'API request failed: {str(e)}',
            502
        )

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return format_error_response(
            event,
            action if 'action' in locals() else 'unknown',
            f'Internal error: {str(e)}',
            500
        )

# For local testing
if __name__ == "__main__":
    # Test event
    test_event = {
        "apiPath": "/list-projects",
        "httpMethod": "POST",
        "parameters": [
            {"name": "customer_id", "value": "1645975"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    }

    response = lambda_handler(test_event, None)
    print(json.dumps(response, indent=2))
