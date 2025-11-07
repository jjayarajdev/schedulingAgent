"""
Scheduling Actions Lambda Handler
Handles 6 scheduling-related actions for Bedrock Agent

Actions:
1. list_projects - Show available projects for customer
2. get_available_dates - Get available dates for scheduling
3. get_time_slots - Get available time slots for a date
4. confirm_appointment - Confirm/schedule an appointment
5. reschedule_appointment - Reschedule an existing appointment
6. cancel_appointment - Cancel an appointment

Supports both MOCK and REAL API modes via USE_MOCK_API environment variable
"""

import json
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional

# Import configuration and mock data
from config import (
    USE_MOCK_API,
    get_api_config,
    get_auth_headers,
    ENABLE_REAL_CONFIRM,
    ENABLE_REAL_CANCEL
)
from mock_data import (
    get_mock_projects,
    get_mock_available_dates,
    get_mock_time_slots,
    get_mock_confirm_appointment,
    get_mock_cancel_appointment,
    get_mock_business_hours
)

# Import TokenManager for cache invalidation on auth failures
try:
    from token_manager import get_token_manager
    TOKEN_MANAGER_AVAILABLE = True
except ImportError:
    TOKEN_MANAGER_AVAILABLE = False
    logger.warning("TokenManager not available for cache invalidation")

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ============================================================================
# Helper Functions
# ============================================================================

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

def make_api_request_with_retry(
    method: str,
    url: str,
    headers: Dict[str, str],
    **kwargs
) -> requests.Response:
    """
    Make API request with automatic token refresh on 401 errors

    Args:
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        headers: Request headers (including Authorization)
        **kwargs: Additional arguments for requests (json, timeout, etc.)

    Returns:
        Response object

    Raises:
        requests.HTTPError: If request fails after retry
    """
    try:
        # First attempt
        response = requests.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response

    except requests.HTTPError as e:
        # If 401 Unauthorized, try once more with fresh token
        if e.response.status_code == 401 and TOKEN_MANAGER_AVAILABLE:
            logger.warning("Received 401 Unauthorized, invalidating token cache and retrying...")

            # Invalidate cached token
            token_manager = get_token_manager()
            token_manager.invalidate_cache()

            # Get fresh auth headers
            fresh_headers = get_auth_headers()

            # Merge with original headers (preserve client_id, etc.)
            headers.update(fresh_headers)

            # Retry once with fresh token
            try:
                response = requests.request(method, url, headers=headers, **kwargs)
                response.raise_for_status()
                logger.info("Request succeeded after token refresh")
                return response
            except requests.HTTPError as retry_error:
                logger.error(f"Request failed even after token refresh: {retry_error}")
                raise
        else:
            # Not a 401 or TokenManager not available, re-raise original error
            raise

def format_success_response(event: Dict, action: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Format successful response for Bedrock Agent - supports both OpenAPI and Function formats"""
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
                            'body': json.dumps(result)
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
                    'body': json.dumps(result)
                }
            }
        }
    }

def format_error_response(event: Dict, action: str, error_message: str, status_code: int = 500) -> Dict[str, Any]:
    """Format error response for Bedrock Agent - supports both OpenAPI and Function formats"""
    error_body = {'error': error_message, 'action': action}

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

def handle_list_projects(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: list_projects
    Returns list of projects for the customer
    """
    customer_id = params.get('customer_id')
    client_id = params.get('client_id', 'default')

    if not customer_id:
        raise ValueError("Missing required parameter: customer_id")

    if USE_MOCK_API:
        logger.info(f"[MOCK] Fetching projects for customer {customer_id}")
        response = get_mock_projects(customer_id)
    else:
        logger.info(f"[REAL] Fetching projects for customer {customer_id} and client {client_id}")
        # OLD Portal API format: /dashboard/get/{client_id}/{customer_id}
        url = f"{config['dashboard_url']}/{client_id}/{customer_id}"
        logger.info(f"Making API request to: {url}")
        res = requests.get(url, headers=auth_headers, timeout=30)
        res.raise_for_status()
        response = res.json()

    # Extract and simplify project data
    projects = []
    for i, item in enumerate(response.get("data", [])):
        projects.append({
            "project_number": i + 1,
            "project_id": item.get("project_project_id"),
            "order_number": item.get("project_project_number"),
            "project_type": item.get("project_type_project_type"),
            "category": item.get("project_category_category"),
            "status": item.get("status_info_status"),
            "store": item.get("project_store_store_number"),
            "address": item.get("installation_address_full_address"),
            "scheduled_date": item.get("project_date_scheduled_date")
        })

    return {
        "action": "list_projects",
        "customer_id": customer_id,
        "project_count": len(projects),
        "projects": projects,
        "mock_mode": USE_MOCK_API
    }

def handle_get_project_details(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: get_project_details
    Returns detailed information for a specific project with enhanced formatting and validation
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

    try:
        # Use the same endpoint as list_projects, then filter for the specific project
        # This approach is more reliable since we know /dashboard/get works
        url = f"{config['base_url']}/dashboard/get/{client_id}/{customer_id}"
        logger.info(f"Making API request to: {url}")

        res = requests.get(url, headers=auth_headers, timeout=30)
        res.raise_for_status()
        response = res.json()

        # Extract the projects array
        projects = response.get("data", {}).get("records", [])

        # Find the specific project by project_id
        data = None
        for project in projects:
            if str(project.get("project_id")) == str(project_id):
                data = project
                break

        # Validate we found the project
        if not data:
            raise ValueError(f"Project {project_id} not found in the customer's project list")

        # Helper function to safely get nested values
        def safe_get(obj, *keys, default=None):
            """Safely navigate nested dictionaries"""
            result = obj
            for key in keys:
                if isinstance(result, dict):
                    result = result.get(key)
                else:
                    return default
                if result is None:
                    return default
            return result if result is not None else default

        # Extract customer information
        customer_info = safe_get(data, "customer", default={})
        customer_first = safe_get(customer_info, "firstName", default="")
        customer_last = safe_get(customer_info, "lastName", default="")
        customer_name = f"{customer_first} {customer_last}".strip() or "Unknown Customer"

        # Extract address information
        address_info = safe_get(data, "installation_address", default={})
        address1 = safe_get(address_info, "address1", default="")
        address2 = safe_get(address_info, "address2", default="")
        city = safe_get(address_info, "city", default="")
        state = safe_get(address_info, "state", default="")
        zipcode = safe_get(address_info, "zipcode", default="")

        # Build full address with proper formatting
        address_parts = [address1]
        if address2:
            address_parts.append(address2)
        city_state_zip = f"{city}, {state} {zipcode}".strip()
        if city_state_zip and city_state_zip != ", ":
            address_parts.append(city_state_zip)
        full_address = ", ".join(filter(None, address_parts)) or "Address not available"

        # Extract project details
        project_category = safe_get(data, "project_category", "category", default="Not specified")
        project_type = safe_get(data, "project_type", "project_type", default="Not specified")
        status = safe_get(data, "status_info", "status", default="Unknown")

        # Extract and format dates
        scheduled_start = safe_get(data, "date_scheduled_start")
        scheduled_end = safe_get(data, "date_scheduled_end")
        date_sold = safe_get(data, "date_sold")

        # Create human-readable scheduling status
        if scheduled_start and scheduled_end:
            scheduling_status = f"Scheduled from {scheduled_start} to {scheduled_end}"
        elif scheduled_start:
            scheduling_status = f"Scheduled for {scheduled_start}"
        else:
            scheduling_status = "Not yet scheduled"

        # Extract store information
        store_info = safe_get(data, "store_info", default={})
        store_number = safe_get(store_info, "store_number", default="")
        store_name = safe_get(store_info, "store_name", default="")
        store_display = f"{store_name} (#{store_number})" if store_number and store_name else store_name or store_number or "Not specified"

        # Extract service time
        service_duration = safe_get(data, "service_time", "duration_value")
        service_unit = safe_get(data, "service_time", "duration_type", default="hours")
        service_time_display = f"{service_duration} {service_unit}" if service_duration else safe_get(data, "default_service_time", default="Not specified")

        # Create a human-readable summary for the agent
        summary = f"""Project #{safe_get(data, 'project_number', default='Unknown')} - {project_category} ({project_type})
Status: {status}
Customer: {customer_name}
Installation Address: {full_address}
Store: {store_display}
{scheduling_status}
Service Time: {service_time_display}"""

        if date_sold:
            summary += f"\nSold Date: {date_sold}"

        # Return enhanced response
        return {
            "action": "get_project_details",
            "project_id": safe_get(data, "project_id"),
            "project_number": safe_get(data, "project_number"),
            "client_id": safe_get(data, "client_id"),
            "customer_id": safe_get(data, "customer_id"),

            # Enhanced fields for better agent responses
            "summary": summary,
            "customer_name": customer_name,
            "full_address": full_address,
            "scheduling_status": scheduling_status,
            "store_display": store_display,
            "service_time_display": service_time_display,

            # Original detailed fields
            "category": project_category,
            "type": project_type,
            "status": status,
            "status_id": safe_get(data, "status_id"),
            "scheduled_start": scheduled_start,
            "scheduled_end": scheduled_end,
            "date_sold": date_sold,

            # Nested objects with validation
            "customer": {
                "customer_id": safe_get(customer_info, "customerId"),
                "first_name": customer_first,
                "last_name": customer_last,
                "full_name": customer_name,
                "email": safe_get(customer_info, "email"),
                "phone": safe_get(customer_info, "phone")
            },
            "installation_address": {
                "address_id": safe_get(address_info, "address_id"),
                "address1": address1,
                "address2": address2,
                "city": city,
                "state": state,
                "zipcode": zipcode,
                "full_address": full_address
            },
            "store_info": {
                "store_id": safe_get(store_info, "store_id"),
                "store_number": store_number,
                "store_name": store_name,
                "display_name": store_display
            },
            "service_time": service_duration,
            "service_time_unit": service_unit,
            "default_service_time": safe_get(data, "default_service_time"),
            "client_timezone": safe_get(data, "client_timezone"),

            # Complete API response for complex queries
            "full_data": data
        }

    except requests.HTTPError as e:
        if e.response.status_code == 404:
            raise ValueError(f"Project {project_id} not found")
        elif e.response.status_code == 401:
            raise ValueError("Authentication failed - invalid or expired token")
        elif e.response.status_code == 403:
            raise ValueError("Access denied - insufficient permissions for this project")
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
    Returns available dates for scheduling a project

    Real API Endpoint: GET /scheduler/client/{client_id}/project/{project_id}/date/{date}/selected/{selected_date}/slots
    (Returns both available dates and slots)
    """
    project_id = params.get('project_id')
    client_id = params.get('client_id')

    if not project_id:
        raise ValueError("Missing required parameter: project_id")

    if USE_MOCK_API:
        logger.info(f"[MOCK] Fetching available dates for project {project_id}")
        response = get_mock_available_dates(project_id)
    else:
        # Validate client_id is present for real API calls
        if not client_id:
            raise ValueError("Missing required parameter for real API: client_id")

        logger.info(f"[REAL] Fetching available dates for client {client_id}, project {project_id}")

        # Use today's date as starting point for available dates
        today = datetime.now().strftime("%Y-%m-%d")

        # Construct URL matching real portal API
        url = f"{config['scheduler_base_url']}/scheduler/client/{client_id}/project/{project_id}/date/{today}/selected/{today}/slots"

        logger.info(f"GET {url}")

        try:
            # Use retry logic with automatic token refresh on 401
            res = make_api_request_with_retry("GET", url, auth_headers, timeout=30)
            response = res.json()
            logger.info(f"Available dates retrieved successfully")
        except requests.HTTPError as e:
            status_code = e.response.status_code
            error_body = e.response.text
            logger.error(f"HTTP {status_code} error fetching available dates: {error_body}")

            # Handle specific error codes
            if status_code == 400:
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
    return {
        "action": "get_available_dates",
        "project_id": project_id,
        "available_dates": data.get("dates", []),
        "request_id": data.get("request_id"),
        "mock_mode": USE_MOCK_API
    }

def handle_get_time_slots(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: get_time_slots
    Returns available time slots for a specific date

    Real API Endpoint: GET /scheduler/client/{client_id}/project/{project_id}/date/{date}/selected/{selected_date}/slots
    """
    project_id = params.get('project_id')
    client_id = params.get('client_id')
    date = params.get('date')
    request_id = params.get('request_id')

    if not all([project_id, date, request_id]):
        raise ValueError("Missing required parameters: project_id, date, request_id")

    if USE_MOCK_API:
        logger.info(f"[MOCK] Fetching time slots for project {project_id} on {date}")
        response = get_mock_time_slots(project_id, date, request_id)
    else:
        # Validate client_id is present for real API calls
        if not client_id:
            raise ValueError("Missing required parameter for real API: client_id")

        logger.info(f"[REAL] Fetching time slots for client {client_id}, project {project_id} on {date}")

        # Construct URL matching real portal API: /scheduler/client/{client_id}/project/{project_id}/date/{date}/selected/{date}/slots
        url = f"{config['scheduler_base_url']}/scheduler/client/{client_id}/project/{project_id}/date/{date}/selected/{date}/slots"

        logger.info(f"GET {url}")

        try:
            # Use retry logic with automatic token refresh on 401
            res = make_api_request_with_retry("GET", url, auth_headers, timeout=30)
            response = res.json()
            logger.info(f"Time slots retrieved successfully: {len(response.get('data', {}).get('slots', []))} slots")
        except requests.HTTPError as e:
            status_code = e.response.status_code
            error_body = e.response.text
            logger.error(f"HTTP {status_code} error fetching time slots: {error_body}")

            # Handle specific error codes
            if status_code == 400:
                raise ValueError(f"Invalid date or project: {error_body}")
            elif status_code == 404:
                raise ValueError("No time slots available for this date")
            elif status_code == 401:
                raise ValueError("Authentication failed - token may be expired (after retry)")
            else:
                raise ValueError(f"Failed to fetch time slots: HTTP {status_code}")
        except requests.RequestException as e:
            logger.error(f"Request error fetching time slots: {str(e)}")
            raise ValueError(f"Unable to connect to scheduling API: {str(e)}")

    data = response.get("data", {})
    return {
        "action": "get_time_slots",
        "project_id": project_id,
        "date": date,
        "available_slots": data.get("slots", []),
        "mock_mode": USE_MOCK_API
    }

def handle_confirm_appointment(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: confirm_appointment
    Confirms/schedules an appointment for a project

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

    if not all([project_id, date, time, request_id]):
        raise ValueError("Missing required parameters: project_id, date, time, request_id")

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

        # Ensure time format includes seconds (HH:MM:SS)
        if len(time.split(':')) == 2:
            time = f"{time}:00"  # Add seconds if missing

        payload = {
            "created_at": datetime.now().strftime("%m-%d-%Y %H:%M:%S"),
            "date": date,
            "time": time,
            "request_id": int(request_id),  # Ensure request_id is integer
        }

        logger.info(f"POST {url}")
        logger.info(f"Payload: {json.dumps(payload)}")

        try:
            # Use retry logic with automatic token refresh on 401
            res = make_api_request_with_retry("POST", url, auth_headers, json=payload, timeout=30)
            response = res.json()
            logger.info(f"Confirmation successful: {response}")
        except requests.HTTPError as e:
            status_code = e.response.status_code
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

    return {
        "action": "confirm_appointment",
        "project_id": project_id,
        "scheduled_date": date,
        "scheduled_time": time,
        "message": response.get("message", "Appointment confirmed successfully"),
        "confirmation_data": response.get("data", {}),
        "mock_mode": use_mock
    }

def handle_reschedule_appointment(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: reschedule_appointment
    Reschedules an existing appointment (cancel + confirm)

    Real API Flow:
    1. Cancel existing appointment (if exists)
    2. Confirm new appointment with the new date/time

    Required Parameters: project_id, client_id, new_date, new_time, request_id
    """
    project_id = params.get('project_id')
    client_id = params.get('client_id')
    new_date = params.get('new_date')
    new_time = params.get('new_time')
    request_id = params.get('request_id')

    if not all([project_id, new_date, new_time, request_id]):
        raise ValueError("Missing required parameters: project_id, new_date, new_time, request_id")

    logger.info(f"Rescheduling appointment for project {project_id}")

    # Step 1: Cancel existing appointment - DISABLED (cancel endpoint not available)
    # NOTE: For now, reschedule only creates a new appointment without canceling the old one
    # Users should manually cancel via support if needed
    logger.warning("⚠️ Cancel step skipped - cancel endpoint not yet available. Only scheduling new appointment.")
    cancel_result = {
        "status": "skipped",
        "message": "Cancel endpoint not available. Creating new appointment only."
    }

    # # COMMENTED OUT - Cancel step (uncomment when cancel endpoint is available)
    # try:
    #     cancel_result = handle_cancel_appointment(
    #         {
    #             'project_id': project_id,
    #             'client_id': client_id
    #         },
    #         config,
    #         auth_headers
    #     )
    #     logger.info(f"Successfully canceled existing appointment: {cancel_result}")
    # except Exception as e:
    #     logger.warning(f"Cancel failed (might not have existing appointment): {str(e)}")
    #     cancel_result = {"status": "skipped", "message": str(e)}

    # Step 2: Confirm new appointment
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

    logger.info(f"Reschedule complete: {confirm_result}")

    return {
        "action": "reschedule_appointment",
        "project_id": project_id,
        "new_date": new_date,
        "new_time": new_time,
        "cancel_result": cancel_result,
        "confirm_result": confirm_result,
        "message": f"Appointment rescheduled to {new_date} at {new_time}",
        "mock_mode": USE_MOCK_API
    }

def handle_cancel_appointment(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: cancel_appointment
    TEMPORARILY DISABLED - Cancel endpoint not yet available in production API

    # Real API Endpoint: GET /scheduler/client/{client_id}/project/{project_id}/cancel-reschedule
    # (Assuming similar pattern to schedule endpoint)
    # Required Parameters: project_id, client_id (for real API)
    """
    project_id = params.get('project_id')

    logger.warning(f"⚠️ Cancel appointment feature is currently disabled for project {project_id}")

    return {
        "action": "cancel_appointment",
        "project_id": project_id,
        "message": "Cancel appointment feature is temporarily disabled. Please contact support to cancel appointments.",
        "status": "disabled",
        "mock_mode": False
    }

    # COMMENTED OUT - Real API implementation (uncomment when endpoint is available)
    # client_id = params.get('client_id')
    #
    # if not project_id:
    #     raise ValueError("Missing required parameter: project_id")
    #
    # # Use mock if global flag is set OR if real cancel is not enabled
    # use_mock = USE_MOCK_API or not ENABLE_REAL_CANCEL
    #
    # if use_mock:
    #     logger.info(f"[MOCK] Cancelling appointment for project {project_id}")
    #     response = get_mock_cancel_appointment(project_id)
    # else:
    #     # Validate client_id for real API calls
    #     if not client_id:
    #         raise ValueError("Missing required parameter for real API: client_id")
    #
    #     logger.info(f"[REAL] Cancelling appointment for project {project_id}, client {client_id}")
    #
    #     # Updated URL to include client_id (matching schedule endpoint pattern)
    #     url = f"{config['scheduler_base_url']}/scheduler/client/{client_id}/project/{project_id}/cancel-reschedule"
    #
    #     logger.info(f"GET {url}")
    #
    #     try:
    #         # Use retry logic with automatic token refresh on 401
    #         res = make_api_request_with_retry("GET", url, auth_headers, timeout=30)
    #         response = res.json()
    #         logger.info(f"Cancellation successful: {response}")
    #     except requests.HTTPError as e:
    #         status_code = e.response.status_code
    #         error_body = e.response.text
    #         logger.error(f"HTTP {status_code} error canceling appointment: {error_body}")
    #
    #         # Handle specific error codes
    #         if status_code == 400:
    #             raise ValueError(f"Invalid cancellation request: {error_body}")
    #         elif status_code == 404:
    #             raise ValueError("No appointment found to cancel")
    #         elif status_code == 401:
    #             raise ValueError("Authentication failed - token may be expired (after retry)")
    #         else:
    #             raise ValueError(f"Failed to cancel appointment: HTTP {status_code}")
    #     except requests.RequestException as e:
    #         logger.error(f"Request error canceling appointment: {str(e)}")
    #         raise ValueError(f"Unable to connect to scheduling API: {str(e)}")
    #
    # return {
    #     "action": "cancel_appointment",
    #     "project_id": project_id,
    #     "message": response.get("message", "Appointment cancelled"),
    #     "cancellation_data": response.get("data", {}),
    #     "mock_mode": use_mock
    # }

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
            'get-available-dates': handle_get_available_dates,
            'get-time-slots': handle_get_time_slots,
            'confirm-appointment': handle_confirm_appointment,
            'reschedule-appointment': handle_reschedule_appointment,
            'cancel-appointment': handle_cancel_appointment
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
        logger.error(f"Validation error: {str(e)}")
        return format_error_response(
            event,
            action if 'action' in locals() else 'unknown',
            f'Validation error: {str(e)}',
            400
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
