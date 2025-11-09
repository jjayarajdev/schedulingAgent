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

def make_api_request_with_retry(
    method: str,
    url: str,
    headers: Dict[str, str],
    **kwargs
) -> requests.Response:
    """
    OPTIMIZED: Make API request with connection pooling and automatic token refresh on 401 errors
    Uses module-level session object for TCP connection reuse (100-300ms savings)

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
    # OPTIMIZATION: Add compression header if not present
    if 'Accept-Encoding' not in headers:
        headers['Accept-Encoding'] = 'gzip, deflate'

    try:
        # OPTIMIZATION: Use session instead of requests directly (reuses TCP connections)
        response = session.request(method, url, headers=headers, **kwargs)
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

            # Retry once with fresh token (using session)
            try:
                response = session.request(method, url, headers=headers, **kwargs)
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

def extract_project_minimal(item: Dict) -> Dict[str, Any]:
    """
    OPTIMIZATION: Extract comprehensive project data with conditional fields
    Extracts 15+ fields (vs previous 9) while keeping payload minimal
    """
    # Core fields (always present)
    project = {
        "id": str(safe_get(item, "project_project_id", default="")),
        "projectNumber": safe_get(item, "project_project_number", default=""),
        "status": safe_get(item, "status_info_status", default=""),
        "category": safe_get(item, "project_category_category", default=""),
        "projectType": safe_get(item, "project_type_project_type", default=""),
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
        project["dateSold"] = date_sold.split("T")[0] if "T" in date_sold else date_sold

    project["hasDocuments"] = bool(safe_get(item, "projectDocument"))

    return project

def format_projects_for_agent(projects: list, customer_id: str = "") -> Dict[str, Any]:
    """
    OPTIMIZATION: Pre-format exactly as agent instructions expect
    Agent receives this ready for UI - NO additional formatting needed
    """
    project_count = len(projects)

    if project_count == 0:
        return {
            "message": "No projects found for this customer.",
            "projects": []
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
        "projects": projects
    }

def handle_list_projects(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    OPTIMIZED Action: list_projects

    KEY OPTIMIZATIONS:
    1. Processes large API response in Lambda (not agent)
    2. Extracts 15+ fields efficiently (vs previous 9)
    3. Pre-formats for UI consumption (agent does zero formatting)
    4. Uses connection pooling + compression

    Before: ~2000 lines to agent → agent formats → ~200 lines to UI
    After: ~200 lines to agent (already formatted) → pass-through to UI
    """
    customer_id = params.get('customer_id')
    client_id = params.get('client_id', 'default')

    if not customer_id:
        raise ValueError("Missing required parameter: customer_id")

    # Start timing for monitoring
    import time
    start_time = time.time()

    if USE_MOCK_API:
        logger.info(f"[MOCK] Fetching projects for customer {customer_id}")
        response = get_mock_projects(customer_id)
    else:
        logger.info(f"[REAL] Fetching projects for customer {customer_id} and client {client_id}")
        # OLD Portal API format: /dashboard/get/{client_id}/{customer_id}
        url = f"{config['dashboard_url']}/{client_id}/{customer_id}"
        logger.info(f"Making API request to: {url}")

        # OPTIMIZATION: Use session with compression, longer timeout
        api_start = time.time()
        res = session.get(
            url,
            headers={**auth_headers, 'Accept-Encoding': 'gzip, deflate'},
            timeout=(5, 45)  # (connect timeout, read timeout) - increased to 45s
        )
        res.raise_for_status()
        api_duration = (time.time() - api_start) * 1000
        logger.info(f"API call took {api_duration:.2f}ms")

        response = res.json()

    # OPTIMIZATION: Extract and format projects efficiently
    processing_start = time.time()

    raw_data = response.get("data", [])
    logger.info(f"Processing {len(raw_data)} projects from API")

    # Extract comprehensive fields from each project (fast iteration)
    projects = [extract_project_minimal(item) for item in raw_data]

    # Pre-format exactly as agent expects (no agent work needed)
    formatted_response = format_projects_for_agent(projects, customer_id)

    processing_duration = (time.time() - processing_start) * 1000
    total_duration = (time.time() - start_time) * 1000

    logger.info(f"Processing took {processing_duration:.2f}ms, Total: {total_duration:.2f}ms")

    # DEBUG: Log what we're returning to agent
    logger.info(f"Returning formatted response with {len(projects)} projects")
    logger.info(f"Sample response structure: {json.dumps(formatted_response, separators=(',', ':'))[:500]}")

    # OPTIMIZATION: Return pre-formatted data
    # Agent receives this ready for UI - NO additional formatting needed
    return formatted_response

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

    logger.info(f"[REAL] Fetching project details for project {project_id}, client {client_id}")

    try:
        # Use the dedicated getdata endpoint for single project details
        url = f"{config['base_url']}/dashboard/getdata/{client_id}/{project_id}"
        logger.info(f"Making API request to: {url}")

        res = requests.get(url, headers=auth_headers, timeout=30)
        res.raise_for_status()
        response = res.json()

        # DEBUG: Log the response structure
        logger.info(f"API response keys: {list(response.keys()) if isinstance(response, dict) else 'not a dict'}")
        logger.info(f"Full API response: {json.dumps(response, indent=2)[:500]}...")

        # Extract the project data
        # Try different possible structures
        data = response.get("data")
        if not data and "dashboard" in response:
            # Some endpoints return dashboard directly
            data = response.get("dashboard")
        if not data and isinstance(response, dict):
            # Maybe the response itself is the data
            data = response

        # Validate we got project data
        if not data:
            raise ValueError(f"Project {project_id} not found or no data returned from API")

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

        # Extract technician/installer information
        technician_info = safe_get(data, "technician", default={})
        installer_info = safe_get(data, "installer", default={})

        # Try both "technician" and "installer" keys (API may use either)
        tech_data = technician_info if technician_info else installer_info

        technician_id = safe_get(tech_data, "technician_id") or safe_get(tech_data, "installer_id")
        technician_name = safe_get(tech_data, "name") or safe_get(tech_data, "technician_name") or safe_get(tech_data, "installer_name")
        technician_email = safe_get(tech_data, "email")
        technician_phone = safe_get(tech_data, "phone")
        technician_bio = safe_get(tech_data, "bio") or safe_get(tech_data, "description")

        # Format technician display
        if technician_name:
            technician_display = f"{technician_name}"
            if technician_id:
                technician_display += f" (ID: {technician_id})"
        else:
            technician_display = "Not assigned"

        # Create a human-readable summary for the agent
        summary = f"""Project #{safe_get(data, 'project_number', default='Unknown')} - {project_category} ({project_type})
Status: {status}
Customer: {customer_name}
Installation Address: {full_address}
Store: {store_display}
{scheduling_status}
Service Time: {service_time_display}"""

        if technician_name:
            summary += f"\nTechnician: {technician_display}"

        if date_sold:
            summary += f"\nSold Date: {date_sold}"

        # Build camelCase project object for UI compatibility
        project = {
            "id": safe_get(data, "project_id"),
            "projectNumber": safe_get(data, "project_number"),
            "status": status,
            "category": project_category,
            "projectType": project_type,
            "scheduledDate": scheduled_start,
            "scheduledEndDate": scheduled_end,
            "address": {
                "address1": address1,
                "address2": address2,
                "city": city,
                "state": state,
                "zipcode": zipcode,
                "fullAddress": full_address
            },
            "store": {
                "storeName": store_name,
                "storeNumber": store_number
            },
            "sourceSystem": safe_get(data, "source_system"),
            "dateSold": date_sold,
            "hasDocuments": safe_get(data, "has_documents", default=False),
            "estimatedDuration": service_time_display
        }

        # Add technician only if assigned
        if technician_name:
            project["technician"] = {
                "technician_id": technician_id,
                "name": technician_name,
                "email": technician_email,
                "phone": technician_phone,
                "bio": technician_bio,
                "display_name": technician_display
            }

        # Remove None values
        project = {k: v for k, v in project.items() if v is not None}
        if "address" in project:
            project["address"] = {k: v for k, v in project["address"].items() if v is not None}
        if "store" in project:
            project["store"] = {k: v for k, v in project["store"].items() if v is not None}

        # Return enhanced response with both legacy and new format
        return {
            "action": "get_project_details",
            "project": project,

            # Legacy fields for backward compatibility
            "project_id": safe_get(data, "project_id"),
            "project_number": safe_get(data, "project_number"),
            "client_id": safe_get(data, "client_id"),
            "customer_id": safe_get(data, "customer_id"),
            "summary": summary,
            "customer_name": customer_name,
            "full_address": full_address,
            "scheduling_status": scheduling_status,
            "store_display": store_display,
            "service_time_display": service_time_display,
            "technician_display": technician_display,
            "category": project_category,
            "type": project_type,
            "status": status,
            "status_id": safe_get(data, "status_id"),
            "scheduled_start": scheduled_start,
            "scheduled_end": scheduled_end,
            "date_sold": date_sold,
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
            "technician": {
                "technician_id": technician_id,
                "name": technician_name,
                "email": technician_email,
                "phone": technician_phone,
                "bio": technician_bio,
                "display_name": technician_display
            } if technician_name else None,
            "service_time": service_duration,
            "service_time_unit": service_unit,
            "default_service_time": safe_get(data, "default_service_time"),
            "client_timezone": safe_get(data, "client_timezone"),
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
    raw_dates = data.get("dates", [])

    # Format dates with day names and group by week for better UI rendering
    formatted_dates = []
    for date_str in raw_dates:
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            formatted_dates.append({
                "date": date_str,
                "dayName": date_obj.strftime("%A"),  # Monday, Tuesday, etc.
                "dayShort": date_obj.strftime("%a"),  # Mon, Tue, etc.
                "monthDay": date_obj.strftime("%b %d"),  # Jan 15
                "formatted": date_obj.strftime("%A, %B %d, %Y")  # Monday, January 15, 2024
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

    return {
        "action": "get_available_dates",
        "project_id": project_id,
        "available_dates": raw_dates,  # Keep original for compatibility
        "dates": formatted_dates,  # Enhanced format for UI
        "dateCount": len(raw_dates),
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
    raw_slots = data.get("slots", [])

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
        "date": date,
        "available_slots": raw_slots,  # Keep original for compatibility
        "timeSlots": raw_slots,  # Alias for UI compatibility
        "timeSlotsGrouped": time_slots_grouped,  # Grouped format for enhanced UI
        "slotCount": len(raw_slots),
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

    # Format date and time for better UI display
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%A, %B %d, %Y")  # Monday, January 15, 2024
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
    confirmation_details = response.get("data", {})

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
        "message": response.get("message", "Appointment confirmed successfully"),
        "appointment": appointment,  # Enhanced appointment object for UI
        "confirmation_data": confirmation_details,
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
